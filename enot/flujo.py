"""Flujo completo de Enot (spec 005, ADR-0003, ADR-0015): un turno de conversación sobre una `Sesion`.

relevar → (zonas conocidas) → buscar → [planificar → verificar] × hasta `max_intentos` → responder

- El loop de verificación es el patrón evaluador-optimizador de ADR-0003: si el verificador encuentra violaciones,
  vuelven al planificador. `max_intentos=1` es la ablación B2 (sin loop).
- Circuit breaker (lineamientos C.4): tope de intentos por turno y tope de tokens por conversación, contados en
  código desde la traza, nunca en el prompt.
- Con un itinerario vigente, el mensaje del turista es un ajuste: el planificador recibe el vigente y el pedido, y
  el resultado pasa por el mismo verificador. El vigente solo se reemplaza por otro factible.
- Los textos que no son el itinerario (infactible, zona desconocida, sin candidatas, tope) los escribe el código.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable, Literal, Optional, Sequence

from pydantic import BaseModel, Field

from .modelos import Bodega, Itinerario, PerfilViaje
from .nodos import ErrorNodo, Mensaje, Pregunta, planificar, relevar, render_itinerario, responder
from .retrieval import Indice, motivo_exclusion
from .trazas import Traza
from .verificador import Advertencia, TipoViolacion, Violacion, verificar_completo

__all__ = ["DESCRIPCION_VIOLACION", "K_CANDIDATAS", "MAX_INTENTOS", "TOPE_TOKENS", "Flujo", "Mensaje", "Respuesta",
           "Sesion", "TipoRespuesta", "avisar_zonas_desconocidas", "explicar_infactible", "explicar_sin_candidatas",
           "tokens_usados"]

MAX_INTENTOS = 3          # ADR-0003
TOPE_TOKENS = 200_000     # por conversación; ver ADR-0015
K_CANDIDATAS = 10         # ADR-0014: con k = 10, 45 pares de traslado en el contexto


class Sesion(BaseModel):
    """Todo el estado de una conversación. Se guarda y se retoma como JSON."""
    conversacion: str
    ruta_traza: str
    historial: list[Mensaje] = Field(default_factory=list)
    perfil: Optional[PerfilViaje] = None
    itinerario: Optional[Itinerario] = Field(None, description="El vigente: siempre uno que pasó el verificador")
    advertencias: list[Advertencia] = Field(default_factory=list, description="Las del itinerario vigente")

    @classmethod
    def nueva(cls, carpeta_trazas: Optional[Path] = None) -> "Sesion":
        t = Traza.nueva(carpeta_trazas)
        return cls(conversacion=t.conversacion, ruta_traza=str(t.ruta))

    def traza(self) -> Traza:
        return Traza(Path(self.ruta_traza), self.conversacion)

    def guardar(self, ruta: Path) -> None:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def cargar(cls, ruta: Path) -> "Sesion":
        return cls.model_validate_json(Path(ruta).read_text(encoding="utf-8"))


TipoRespuesta = Literal["pregunta", "itinerario", "infactible", "zona_desconocida", "sin_candidatas",
                        "tope_tokens", "error"]


class Respuesta(BaseModel):
    tipo: TipoRespuesta
    texto: str
    intentos: int = Field(0, description="Llamadas al planificador en este turno")
    itinerario: Optional[Itinerario] = Field(None, description="La última propuesta, válida o no (sirve para B2)")
    violaciones: list[Violacion] = Field(default_factory=list, description="Las de la última propuesta")
    advertencias: list[Advertencia] = Field(default_factory=list)


def tokens_usados(traza: Traza) -> int:
    """Tokens de entrada + salida conocidos de la conversación. Los eventos con error (`None`) no suman."""
    return sum((e.tokens_in or 0) + (e.tokens_out or 0) for e in traza.eventos())


# --- textos fijos para el turista ---------------------------------------------------------

DESCRIPCION_VIOLACION: dict[TipoViolacion, str] = {
    "bodega_inexistente": "usar solo bodegas de mi base (propuse una que no está)",
    "experiencia_inexistente": "usar solo experiencias que las bodegas ofrecen",
    "cerrada": "los horarios de apertura de las bodegas",
    "traslado_imposible": "los tiempos de traslado entre bodegas",
    "jornada_excedida": "tu horario de visitas",
    "presupuesto_excedido": "tu presupuesto por persona",
    "grupo_excede_capacidad": "la cantidad de personas del grupo",
    "accesibilidad": "la accesibilidad para movilidad reducida",
    "idioma_no_disponible": "el idioma de las visitas",
}


def explicar_infactible(violaciones: Sequence[Violacion], intentos: int, hay_vigente: bool) -> str:
    """Qué no se pudo cumplir, escrito por código a partir de las violaciones del último intento."""
    condiciones = list(dict.fromkeys(DESCRIPCION_VIOLACION[v.tipo] for v in violaciones))
    veces = f"{intentos} intento" if intentos == 1 else f"{intentos} intentos"
    lineas = [f"No pude armar un itinerario que cumpla todo lo que pediste ({veces}).",
              f"Lo que no logré cumplir: {', '.join(condiciones)}.",
              "Detalle del último intento:", *(f"- {v.mensaje}" for v in violaciones),
              "Si querés, cambiá alguna de esas condiciones (días, horario, presupuesto, zona) y lo intento de nuevo."]
    if hay_vigente:
        lineas.append("Tu itinerario anterior sigue vigente.")
    return "\n".join(lineas)


def explicar_sin_candidatas(bodegas: Iterable[Bodega], perfil: PerfilViaje, cuantos: int = 3) -> str:
    """Ninguna bodega pasa los filtros duros: los motivos de exclusión más frecuentes.

    Si el turista pidió zonas, solo cuentan las bodegas de esas zonas: que las demás queden afuera es lo que pidió,
    no el problema. Una bodega está en la zona si su motivo no cambia al sacar la zona del perfil."""
    sin_zona = perfil.model_copy(update={"zonas_preferidas": []})
    motivos: Counter[str] = Counter()
    for b in bodegas:
        m = motivo_exclusion(b, perfil)
        if m is not None and m == motivo_exclusion(b, sin_zona):
            motivos[m] += 1
    lineas = ["No encontré bodegas que cumplan a la vez todo lo que pediste."]
    if motivos:
        lineas += ["Los motivos más frecuentes:",
                   *(f"- {m} ({n} bodega{'s' if n != 1 else ''})" for m, n in motivos.most_common(cuantos))]
    lineas.append("Si cambiás alguna condición (días, zona, presupuesto, idioma), lo intento de nuevo.")
    return "\n".join(lineas)


def avisar_zonas_desconocidas(zonas: Sequence[str], conocidas: Iterable[str]) -> str:
    """En vez de presentar el pedido como infactible, decir que la zona no está en la base (revisión 003)."""
    nombres = ", ".join(zonas)
    lista = ", ".join(sorted({z for z in conocidas if z}))
    return (f"No reconozco la zona {nombres}. Las zonas de Borgoña que conozco son: {lista}. "
            f"¿En cuál querés visitar bodegas?")


def _texto_tope(tope: int) -> str:
    return (f"Llegué al tope de consumo de esta conversación ({tope} tokens), así que no puedo seguir "
            f"planificando acá. Si querés seguir, empezá una conversación nueva.")


# --- flujo -------------------------------------------------------------------------------

class Flujo:
    """Workflow fijo de ADR-0003. Sin estado propio: todo lo de la conversación vive en la `Sesion`."""

    def __init__(self, cliente, corpus: dict[str, Bodega], indice: Indice, max_intentos: int = MAX_INTENTOS,
                 tope_tokens: int = TOPE_TOKENS, k: int = K_CANDIDATAS):
        if max_intentos < 1:
            raise ValueError("max_intentos tiene que ser al menos 1 (1 = sin loop de verificación)")
        if tope_tokens < 1:
            raise ValueError("tope_tokens tiene que ser positivo")
        self.cliente = cliente
        self.corpus = corpus
        self.indice = indice
        self.max_intentos = max_intentos
        self.tope_tokens = tope_tokens
        self.k = k

    def _sin_tope(self, traza: Traza) -> bool:
        return tokens_usados(traza) < self.tope_tokens

    def turno(self, sesion: Sesion, texto: str) -> Respuesta:
        traza = sesion.traza()
        historial, perfil = list(sesion.historial), sesion.perfil
        sesion.historial.append(Mensaje(rol="turista", texto=texto))
        try:
            r = self._turno(sesion, texto, traza)
        except ErrorNodo as e:
            # nada a medias: el turista puede repetir el mensaje (el error ya quedó en la traza)
            sesion.historial, sesion.perfil = historial, perfil
            return Respuesta(tipo="error", texto=f"Tuve un problema con el modelo en el paso de {e.nodo} y no pude "
                                                 f"terminar. Probá de nuevo en un rato.")
        sesion.historial.append(Mensaje(rol="enot", texto=r.texto))
        return r

    def _turno(self, sesion: Sesion, texto: str, traza: Traza) -> Respuesta:
        if not self._sin_tope(traza):
            return Respuesta(tipo="tope_tokens", texto=_texto_tope(self.tope_tokens))

        resultado = relevar(sesion.historial, self.cliente, traza)
        if isinstance(resultado, Pregunta):
            return Respuesta(tipo="pregunta", texto=resultado.texto)
        perfil = sesion.perfil = resultado

        desconocidas = self.indice.zonas_desconocidas(perfil)
        if desconocidas:
            return Respuesta(tipo="zona_desconocida",
                             texto=avisar_zonas_desconocidas(desconocidas, (b.zona for b in self.indice.bodegas)))

        candidatas = self._candidatas(perfil, sesion.itinerario)
        if not candidatas:
            return Respuesta(tipo="sin_candidatas", texto=explicar_sin_candidatas(self.indice.bodegas, perfil))

        vigente = sesion.itinerario
        pedido = texto if vigente is not None else None
        previo, violaciones = vigente, []
        propuesta: Optional[Itinerario] = None
        for intento in range(1, self.max_intentos + 1):
            if not self._sin_tope(traza):
                return Respuesta(tipo="tope_tokens", texto=_texto_tope(self.tope_tokens), intentos=intento - 1,
                                 itinerario=propuesta, violaciones=violaciones)
            propuesta = planificar(perfil, candidatas, violaciones, self.cliente, traza, itinerario_previo=previo,
                                   intento=intento, pedido_ajuste=pedido)
            v = verificar_completo(propuesta, perfil, self.corpus)
            if v.factible:
                return self._entregar(sesion, perfil, propuesta, v.advertencias, intento, traza)
            previo, violaciones = propuesta, v.violaciones

        texto_infactible = explicar_infactible(violaciones, self.max_intentos, hay_vigente=vigente is not None)
        return Respuesta(tipo="infactible", texto=texto_infactible, intentos=self.max_intentos, itinerario=propuesta,
                         violaciones=violaciones)

    def _candidatas(self, perfil: PerfilViaje, vigente: Optional[Itinerario]) -> list[Bodega]:
        ids: list[str] = []
        if vigente is not None:
            # en un ajuste, las bodegas del vigente tienen que poder quedarse (el esquema solo acepta candidatas)
            ids += [p.bodega_id for d in vigente.dias for p in d.paradas
                    if p.bodega_id in self.corpus and motivo_exclusion(self.corpus[p.bodega_id], perfil) is None]
        ids += [c.bodega_id for c in self.indice.buscar(perfil, k=self.k)]
        return [self.corpus[i] for i in dict.fromkeys(ids) if i in self.corpus]

    def _entregar(self, sesion: Sesion, perfil: PerfilViaje, itinerario: Itinerario,
                  advertencias: list[Advertencia], intento: int, traza: Traza) -> Respuesta:
        sesion.itinerario, sesion.advertencias = itinerario, list(advertencias)
        texto: Optional[str] = None
        if self._sin_tope(traza):
            try:
                texto = responder(itinerario, perfil, self.corpus, self.cliente, traza, advertencias)
            except ErrorNodo:
                texto = None  # ya quedó en la traza; el itinerario es válido y se entrega igual
        if texto is None:
            texto = render_itinerario(itinerario, perfil, self.corpus, advertencias=advertencias)
        return Respuesta(tipo="itinerario", texto=texto, intentos=intento, itinerario=itinerario,
                         advertencias=list(advertencias))
