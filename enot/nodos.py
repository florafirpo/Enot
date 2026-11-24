"""Nodos con LLM del workflow (spec 004, ADR-0003, ADR-0014).

- `relevar`: historial del chat → `PerfilViaje` o `Pregunta`. El LLM extrae; qué falta y qué es válido lo
  decide el código (`perfil_desde_borrador`).
- `planificar`: perfil + candidatas (+ violaciones del intento anterior) → `Itinerario`. El LLM elige bodegas y
  horarios con los tiempos de traslado ya calculados; la salida está acotada a las candidatas y a la cantidad
  de días del perfil.
- `responder`: itinerario verificado → texto. El LLM escribe la introducción y los motivos; horarios, precios,
  traslados, advertencias y fuentes los pone `render_itinerario` (código).

Todas las llamadas pasan por un cliente con la interfaz de `ClienteLLM` (ADR-0006) y quedan en la traza.
El LLM no hace aritmética ni manejo de horarios (ADR-0005).
"""
from __future__ import annotations

import json
import time
from datetime import date, datetime, timezone
from typing import Literal, Optional, Sequence, Type

from pydantic import BaseModel, Field, ValidationError, create_model

from . import prompts
from .modelos import Bodega, Dia, DiaItinerario, Hora, Itinerario, Parada, PerfilViaje, Transporte, a_hora, a_minutos
from .retrieval import dias_del_viaje
from .tools import ItemCosto, costo_experiencias, tiempo_traslado
from .trazas import EventoTraza, NodoLLM, Traza
from .verificador import Advertencia, Violacion

__all__ = ["CAMPOS_OBLIGATORIOS", "PREGUNTAS", "BorradorPerfil", "ErrorNodo", "Mensaje", "MotivoParada", "Pregunta",
           "SalidaRespuesta", "contexto_planificador", "dia_de_semana", "modelo_salida_planificador",
           "perfil_desde_borrador", "planificar", "relevar", "render_itinerario", "responder"]

DIAS_SEMANA: tuple[Dia, ...] = ("lun", "mar", "mie", "jue", "vie", "sab", "dom")
DIA_LARGO = {"lun": "lunes", "mar": "martes", "mie": "miércoles", "jue": "jueves", "vie": "viernes",
             "sab": "sábado", "dom": "domingo"}
LARGO_DESCRIPCION = 300


class ErrorNodo(Exception):
    """El cliente no logró una salida válida (o falló el proveedor). Ya quedó registrado en la traza."""

    def __init__(self, nodo: str, causa: Exception):
        super().__init__(f"{nodo}: {causa}")
        self.nodo = nodo
        self.causa = causa


def _llamar(cliente, traza: Traza, nodo: NodoLLM, usuario: str, modelo: Type[BaseModel], intento: int = 1):
    """Única puerta de los nodos al LLM: llama, mide y registra un evento en la traza, salga bien o mal."""
    inicio = datetime.now(timezone.utc).isoformat(timespec="seconds")
    t0 = time.perf_counter()
    comunes = dict(conversacion=traza.conversacion, nodo=nodo, intento=intento, proveedor=cliente.provider,
                   modelo=cliente.model, inicio=inicio)
    try:
        r = cliente.estructurado(prompts.cargar(nodo), usuario, modelo)
    except Exception as e:  # noqa: BLE001 — errores del proveedor o de validación: se registran y se tipifican
        traza.registrar(EventoTraza(**comunes, latencia_s=time.perf_counter() - t0, tokens_in=0, tokens_out=0,
                                    intentos_validacion=0, estado="error", error=str(e)[:500]))
        raise ErrorNodo(nodo, e) from e
    traza.registrar(EventoTraza(**comunes, latencia_s=time.perf_counter() - t0, tokens_in=r.tokens_in,
                                tokens_out=r.tokens_out, intentos_validacion=r.intentos, estado="ok"))
    return r


# --- relevamiento ------------------------------------------------------------------------

class Mensaje(BaseModel):
    rol: Literal["turista", "enot"]
    texto: str


class Pregunta(BaseModel):
    """Lo que el relevamiento le devuelve al turista cuando el perfil no está completo o no es válido."""
    texto: str
    faltantes: list[str]


class BorradorPerfil(BaseModel):
    """Salida del LLM en el relevamiento: lo que el turista dijo, sin completar nada. Validar es del código."""
    cantidad_dias: Optional[int] = None
    dia_inicio: Optional[Dia] = None
    fecha_inicio: Optional[date] = Field(None, description="Solo si el turista dio día, mes y año")
    transporte: Optional[Transporte] = None
    personas: Optional[int] = None
    presupuesto_max_por_persona: Optional[float] = Field(None, description="EUR")
    movilidad_reducida: Optional[bool] = None
    idiomas: list[str] = Field(default_factory=list)
    zonas_preferidas: list[str] = Field(default_factory=list)
    bodegas_evitar: list[str] = Field(default_factory=list)
    preferencias: Optional[str] = None
    hora_inicio_jornada: Optional[str] = Field(None, description="HH:MM")
    hora_fin_jornada: Optional[str] = Field(None, description="HH:MM")


CAMPOS_OBLIGATORIOS = ("cantidad_dias", "dia_inicio", "transporte", "personas")

PREGUNTAS = {
    "cantidad_dias": "cuántos días querés recorrer bodegas (de 1 a 3)",
    "dia_inicio": "qué día de la semana empezás",
    "transporte": "cómo te vas a mover: auto, traslado con chofer, bici o a pie",
    "personas": "cuántas personas viajan, contándote",
}

_JORNADA = "La jornada tiene que empezar antes de terminar (HH:MM): ¿desde y hasta qué hora querés visitar bodegas?"
MOTIVOS_INVALIDO = {
    "cantidad_dias": "Enot arma itinerarios de 1 a 3 días: ¿cuántos días querés recorrer bodegas?",
    "personas": "Tiene que viajar al menos una persona: ¿cuántas personas son, contándote?",
    "presupuesto_max_por_persona": "El presupuesto no puede ser negativo: ¿cuánto querés gastar por persona en "
                                   "las visitas, en euros?",
    "hora_inicio_jornada": _JORNADA,
    "hora_fin_jornada": _JORNADA,
}


def dia_de_semana(fecha: date) -> Dia:
    return DIAS_SEMANA[fecha.weekday()]


def _texto_pregunta(faltantes: Sequence[str]) -> str:
    return "Para armar el itinerario me falta saber:\n" + "\n".join(f"- {PREGUNTAS[c]}" for c in faltantes)


def perfil_desde_borrador(b: BorradorPerfil) -> PerfilViaje | Pregunta:
    """Código puro: decide si el borrador alcanza para un `PerfilViaje` y, si no, qué preguntar."""
    datos = b.model_dump(exclude={"fecha_inicio"}, exclude_none=True)
    if b.fecha_inicio is not None:
        dia = dia_de_semana(b.fecha_inicio)
        if b.dia_inicio is None:
            datos["dia_inicio"] = dia
        elif b.dia_inicio != dia:
            return Pregunta(texto=f"El {b.fecha_inicio:%d/%m/%Y} cae {DIA_LARGO[dia]}, no {DIA_LARGO[b.dia_inicio]}: "
                                  f"¿qué día empezás?", faltantes=["dia_inicio"])

    faltan = [c for c in CAMPOS_OBLIGATORIOS if c not in datos]
    if faltan:
        return Pregunta(texto=_texto_pregunta(faltan), faltantes=faltan)

    try:
        return PerfilViaje(**datos)
    except ValidationError as e:
        campos: list[str] = []
        for err in e.errors():
            # el validador de la jornada no tiene campo: es la combinación de las dos horas
            for c in (err["loc"][:1] or ("hora_inicio_jornada", "hora_fin_jornada")):
                if c not in campos:
                    campos.append(str(c))
        textos = list(dict.fromkeys(MOTIVOS_INVALIDO.get(c, f"No pude usar el dato {c!r}: ¿me lo repetís?")
                                    for c in campos))
        return Pregunta(texto=" ".join(textos), faltantes=campos)


def _etiquetar(m: Mensaje) -> str:
    # el texto del turista es dato: que no pueda cerrar la etiqueta ni abrir otra (C.9)
    texto = m.texto.replace("<", "‹").replace(">", "›")
    return f"<{m.rol}>{texto}</{m.rol}>"


def relevar(historial: list[Mensaje], cliente, traza: Traza) -> PerfilViaje | Pregunta:
    usuario = "<conversacion>\n" + "\n".join(_etiquetar(m) for m in historial) + "\n</conversacion>"
    r = _llamar(cliente, traza, "relevamiento", usuario, BorradorPerfil)
    return perfil_desde_borrador(r.objeto)


# --- planificador ------------------------------------------------------------------------

def modelo_salida_planificador(ids: list[str], cantidad_dias: int) -> Type[BaseModel]:
    """Esquema de salida para una llamada: `bodega_id` ∈ candidatas y exactamente `cantidad_dias` días."""
    unicos = tuple(dict.fromkeys(ids))
    if not unicos:
        raise ValueError("hace falta al menos una candidata")
    id_candidata = Literal[unicos]  # type: ignore[valid-type]
    parada = create_model("ParadaPropuesta", bodega_id=(id_candidata, ...), hora_inicio=(Hora, ...),
                          duracion_min=(int, Field(gt=0)), experiencia=(Optional[str], None))
    dia = create_model("DiaPropuesto", paradas=(list[parada], Field(default_factory=list)))
    return create_model("PropuestaItinerario",
                        dias=(list[dia], Field(min_length=cantidad_dias, max_length=cantidad_dias)),
                        notas=(Optional[str], None))


def _ficha_para_planificar(b: Bodega) -> dict:
    """Solo lo que sirve para planificar (C.12): nada de evidencias, contactos ni texto largo."""
    exp_campos = {"nombre", "tipo", "duracion_min", "precio_por_persona", "moneda", "idiomas", "requiere_reserva"}
    return {
        "id": b.id, "nombre": b.nombre, "zona": b.zona, "comuna": b.comuna,
        "horarios": [h.model_dump() for h in b.horarios],
        "experiencias": [e.model_dump(include=exp_campos) for e in b.experiencias],
        "idiomas": b.idiomas, "accesible_movilidad_reducida": b.accesible_movilidad_reducida,
        "capacidad_max_grupo": b.capacidad_max_grupo, "requiere_reserva": b.requiere_reserva,
        "descripcion_breve": (b.descripcion_breve or "")[:LARGO_DESCRIPCION] or None,
    }


def contexto_planificador(perfil: PerfilViaje, candidatas: list[Bodega], violaciones_previas: list[Violacion],
                          itinerario_previo: Optional[Itinerario]) -> str:
    corpus = {b.id: b for b in candidatas}
    partes = ["## Perfil del turista", perfil.model_dump_json(indent=2),
              "## Días del viaje", *(f"Día {n}: {d}" for n, d in enumerate(dias_del_viaje(perfil), 1)),
              "## Bodegas candidatas", "<candidatas>",
              *(json.dumps(_ficha_para_planificar(b), ensure_ascii=False) for b in candidatas),
              "</candidatas>",
              f"## Tiempos de traslado en {perfil.transporte} (calculados por código)"]
    for i, a in enumerate(candidatas):
        for b in candidatas[i + 1:]:
            t = tiempo_traslado(corpus, a.id, b.id, perfil.transporte)
            partes.append(f"{a.id} ↔ {b.id}: " + (f"{t.minutos} min" if t.minutos is not None else "sin dato"))
    if itinerario_previo is not None:
        partes += ["## Itinerario anterior", itinerario_previo.model_dump_json(indent=2)]
    if violaciones_previas:
        partes += ["## Problemas que encontró el verificador en el itinerario anterior (corregilos todos)",
                   *(f"- {v.mensaje}" for v in violaciones_previas)]
    return "\n".join(partes)


def planificar(perfil: PerfilViaje, candidatas: list[Bodega], violaciones_previas: list[Violacion], cliente,
               traza: Traza, itinerario_previo: Optional[Itinerario] = None, intento: int = 1) -> Itinerario:
    if not candidatas:
        raise ValueError("no hay candidatas para planificar: el flujo tiene que informarlo antes de llamar al LLM")
    modelo = modelo_salida_planificador([b.id for b in candidatas], perfil.cantidad_dias)
    usuario = contexto_planificador(perfil, candidatas, violaciones_previas, itinerario_previo)
    propuesta = _llamar(cliente, traza, "planificador", usuario, modelo, intento).objeto
    # número y día de la semana los pone el código, no el LLM
    dias = dias_del_viaje(perfil)
    return Itinerario(
        dias=[DiaItinerario(numero=n, dia_semana=dias[n - 1], paradas=[Parada(**p.model_dump()) for p in d.paradas])
              for n, d in enumerate(propuesta.dias, 1)],
        notas=propuesta.notas,
    )


# --- respuesta ---------------------------------------------------------------------------

class MotivoParada(BaseModel):
    bodega_id: str
    motivo: str


class SalidaRespuesta(BaseModel):
    introduccion: str
    motivos: list[MotivoParada] = Field(default_factory=list)


def _en_eur(e) -> bool:
    return e.precio_por_persona is not None and e.moneda == "EUR"


def _precio(b: Bodega, p: Parada) -> str:
    if p.experiencia is None:
        con_precio = [e.precio_por_persona for e in b.experiencias if _en_eur(e)]
        return f"desde {min(con_precio):.2f} EUR por persona" if con_precio else "precio a consultar"
    exp = next((e for e in b.experiencias if e.nombre.casefold() == p.experiencia.casefold()), None)
    return f"{exp.precio_por_persona:.2f} EUR por persona" if exp is not None and _en_eur(exp) else "precio a consultar"


def _fuente(b: Bodega) -> Optional[str]:
    for f in b.fuentes:
        if f.get("url"):
            return f["url"]
    return b.url_web or None


def render_itinerario(itinerario: Itinerario, perfil: PerfilViaje, corpus: dict[str, Bodega],
                      motivos: Optional[dict[str, str]] = None, advertencias: Sequence[Advertencia] = ()) -> str:
    """El detalle del itinerario, armado por código: todo número sale de las tools."""
    motivos = motivos or {}
    lineas: list[str] = []
    items: list[ItemCosto] = []
    for d in itinerario.dias:
        lineas += ["", f"**Día {d.numero} · {DIA_LARGO[d.dia_semana]}**"]
        if not d.paradas:
            lineas.append("- Sin visitas este día.")
        anterior: Optional[Parada] = None
        for p in d.paradas:
            franja = f"{p.hora_inicio}–{a_hora(a_minutos(p.hora_inicio) + p.duracion_min)}"
            b = corpus.get(p.bodega_id)
            if b is None:
                lineas.append(f"- {franja} · {p.bodega_id} (no está en el corpus)")
                anterior = None
                continue
            items.append(ItemCosto(bodega_id=b.id, experiencia=p.experiencia))
            exp = p.experiencia or "experiencia a elegir en la bodega"
            lugar = f" ({b.comuna})" if b.comuna else ""
            lineas.append(f"- {franja} · {b.nombre}{lugar} · {exp} · {_precio(b, p)}")
            if anterior is not None:
                t = tiempo_traslado(corpus, anterior.bodega_id, b.id, perfil.transporte)
                lineas.append(f"  (traslado de {t.minutos} min en {perfil.transporte} desde la parada anterior)"
                              if t.minutos is not None else "  (traslado: sin dato, falta la ubicación de una bodega)")
            if b.id in motivos:
                lineas.append(f"  {motivos[b.id]}")
            fuente = _fuente(b)
            if fuente:
                lineas.append(f"  Fuente: {fuente}")
            anterior = p

    c = costo_experiencias(corpus, items, perfil.personas)
    total = f"Total estimado: {c.total_eur / perfil.personas:.2f} EUR por persona"
    if c.sin_precio:
        total += f" (sin contar {len(c.sin_precio)} parada(s) sin precio publicado)"
    lineas += ["", total]
    if advertencias:
        lineas += ["", "**Para tener en cuenta**", *(f"- {a.mensaje}" for a in advertencias)]
    return "\n".join(lineas).strip()


def responder(itinerario: Itinerario, perfil: PerfilViaje, corpus: dict[str, Bodega], cliente, traza: Traza,
              advertencias: Sequence[Advertencia] = ()) -> str:
    paradas = [p for d in itinerario.dias for p in d.paradas]
    datos = []
    for p in paradas:
        b = corpus.get(p.bodega_id)
        if b is not None:
            datos.append(json.dumps({"bodega_id": b.id, "nombre": b.nombre, "zona": b.zona, "comuna": b.comuna,
                                     "experiencia": p.experiencia,
                                     "descripcion_breve": (b.descripcion_breve or "")[:LARGO_DESCRIPCION] or None,
                                     "vinos": b.vinos_o_varietales_destacados}, ensure_ascii=False))
    usuario = "\n".join(["## Perfil del turista", perfil.model_dump_json(indent=2),
                         "## Paradas", "<itinerario>", *datos, "</itinerario>"])
    salida = _llamar(cliente, traza, "respuesta", usuario, SalidaRespuesta).objeto
    en_itinerario = {p.bodega_id for p in paradas}
    motivos = {m.bodega_id: m.motivo.strip() for m in salida.motivos if m.bodega_id in en_itinerario}
    detalle = render_itinerario(itinerario, perfil, corpus, motivos, advertencias)
    return f"{salida.introduccion.strip()}\n\n{detalle}"
