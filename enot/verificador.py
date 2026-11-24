"""Verificador de restricciones duras (spec 002, ADR-0003).

Código puro: recibe un itinerario, el perfil y el corpus, y devuelve las violaciones. Lista vacía =
itinerario factible. Cada mensaje está escrito para que el planificador pueda corregir en el reintento.

Usa las tools de `enot/tools/` para horarios, traslados y costos: una sola fuente de verdad (ADR-0005).

Regla para lo que no se sabe (ver supuestos de la spec):
- un *límite de la bodega* (horario, coordenadas, capacidad, precio) solo viola con evidencia del límite;
- una *necesidad del turista* (accesibilidad, dieta, idioma) solo se cumple con evidencia positiva.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from .modelos import Bodega, Experiencia, Itinerario, Parada, PerfilViaje, a_hora, a_minutos
from .tools import ItemCosto, abierta_en, costo_experiencias, tiempo_traslado

__all__ = ["TIPOS_COMIDA", "TipoViolacion", "Violacion", "verificar"]

TipoViolacion = Literal[
    "bodega_inexistente", "experiencia_inexistente", "cerrada", "traslado_imposible", "jornada_excedida",
    "presupuesto_excedido", "grupo_excede_capacidad", "restriccion_alimentaria", "accesibilidad",
    "idioma_no_disponible",
]

TIPOS_COMIDA = {"almuerzo", "cena", "picnic", "maridaje"}

# restricción del perfil → campos de la bodega que la cubren (vegano declarado cubre vegetariano)
_OPCIONES_DIETA = {
    "sin_tacc": ("opciones_sin_tacc",),
    "vegetariano": ("opciones_vegetarianas", "opciones_veganas"),
    "vegano": ("opciones_veganas",),
}


class Violacion(BaseModel):
    tipo: TipoViolacion
    mensaje: str
    dia: Optional[int] = None
    bodega_id: Optional[str] = None


def _fin(p: Parada) -> int:
    return a_minutos(p.hora_inicio) + p.duracion_min


def _franja(p: Parada) -> str:
    return f"de {p.hora_inicio} a {a_hora(_fin(p))}"


def _experiencia(b: Bodega, nombre: str) -> Optional[Experiencia]:
    return next((e for e in b.experiencias if e.nombre.casefold() == nombre.casefold()), None)


def _chequear_parada(p: Parada, b: Bodega, dia: str, perfil: PerfilViaje, corpus: dict[str, Bodega],
                     nueva) -> None:
    """Reglas que dependen de una sola parada (todo menos traslados, jornada y presupuesto)."""
    exp: Optional[Experiencia] = None
    if p.experiencia is not None:
        exp = _experiencia(b, p.experiencia)
        if exp is None:
            publicadas = ", ".join(e.nombre for e in b.experiencias) or "ninguna"
            nueva("experiencia_inexistente",
                  f"{b.nombre} no ofrece la experiencia {p.experiencia!r}. Publicadas: {publicadas}.")

    h = abierta_en(corpus, b.id, dia, p.hora_inicio, p.duracion_min)
    if h.abierta is False:
        nueva("cerrada", f"{b.nombre}: la visita {_franja(p)} del {dia} no entra en su horario "
                         f"({h.motivo}). Cambiá la hora, el día o la bodega.")

    if b.capacidad_max_grupo is not None and perfil.personas > b.capacidad_max_grupo:
        nueva("grupo_excede_capacidad",
              f"{b.nombre} recibe grupos de hasta {b.capacidad_max_grupo} personas y el grupo es de "
              f"{perfil.personas}. Elegí otra bodega.")

    if exp is not None and exp.tipo in TIPOS_COMIDA:
        for r in perfil.restricciones_alimentarias:
            if not any(getattr(b, campo) is True for campo in _OPCIONES_DIETA[r]):
                nueva("restriccion_alimentaria",
                      f"{b.nombre} no declara opciones {r} para {exp.nombre!r} ({exp.tipo}). "
                      f"Elegí una experiencia sin comida u otra bodega.")

    if perfil.movilidad_reducida and b.accesible_movilidad_reducida is not True:
        nueva("accesibilidad", f"{b.nombre} no declara accesibilidad para movilidad reducida. Elegí otra bodega.")

    if perfil.idiomas:
        disponibles = (exp.idiomas if exp is not None and exp.idiomas else None) or b.idiomas
        pedidos = {i.casefold() for i in perfil.idiomas}
        if not pedidos & {i.casefold() for i in disponibles}:
            de = f"{exp.nombre!r} en {b.nombre}" if exp is not None and exp.idiomas else b.nombre
            nueva("idioma_no_disponible",
                  f"{de} no informa visitas en {', '.join(perfil.idiomas)} "
                  f"(idiomas publicados: {', '.join(disponibles) or 'ninguno'}).")


def verificar(itinerario: Itinerario, perfil: PerfilViaje, corpus: dict[str, Bodega]) -> list[Violacion]:
    """Devuelve las restricciones duras que el itinerario no cumple, en orden determinístico."""
    violaciones: list[Violacion] = []
    items_costo: list[ItemCosto] = []
    inicio_jornada, fin_jornada = a_minutos(perfil.hora_inicio_jornada), a_minutos(perfil.hora_fin_jornada)

    for d in itinerario.dias:
        def nueva(tipo, mensaje, bodega_id=None, _dia=d.numero):
            violaciones.append(Violacion(tipo=tipo, mensaje=f"Día {_dia}: {mensaje}", dia=_dia,
                                         bodega_id=bodega_id))

        anterior: Optional[Parada] = None
        for p in d.paradas:
            b = corpus.get(p.bodega_id)
            if b is None:
                nueva("bodega_inexistente", f"la bodega {p.bodega_id!r} no está en el corpus. "
                                            f"Usá solo bodegas de las candidatas.", p.bodega_id)
                anterior = None
                continue

            _chequear_parada(p, b, d.dia_semana, perfil, corpus,
                             lambda tipo, msg, _b=b.id: nueva(tipo, msg, _b))
            items_costo.append(ItemCosto(bodega_id=b.id, experiencia=p.experiencia))

            if anterior is not None:
                libre = a_minutos(p.hora_inicio) - _fin(anterior)
                t = tiempo_traslado(corpus, anterior.bodega_id, b.id, perfil.transporte)
                if t.minutos is not None and libre < t.minutos:
                    nueva("traslado_imposible",
                          f"de {corpus[anterior.bodega_id].nombre} (termina {a_hora(_fin(anterior))}) a "
                          f"{b.nombre} ({p.hora_inicio}) hay {libre} min y el traslado en {perfil.transporte} "
                          f"tarda {t.minutos} min. Empezá {b.nombre} a las {a_hora(_fin(anterior) + t.minutos)} "
                          f"o más tarde.", b.id)
                elif t.minutos is None and libre < 0:
                    nueva("traslado_imposible",
                          f"la visita a {b.nombre} ({p.hora_inicio}) empieza antes de que termine la de "
                          f"{corpus[anterior.bodega_id].nombre} ({a_hora(_fin(anterior))}).", b.id)
            anterior = p

        if d.paradas:
            primera = min(a_minutos(p.hora_inicio) for p in d.paradas)
            ultima = max(_fin(p) for p in d.paradas)
            if primera < inicio_jornada or ultima > fin_jornada:
                nueva("jornada_excedida",
                      f"las visitas van de {a_hora(primera)} a {a_hora(ultima)} y la jornada del turista es de "
                      f"{perfil.hora_inicio_jornada} a {perfil.hora_fin_jornada}. Sacá o mové paradas.")

    if perfil.presupuesto_max_por_persona is not None and items_costo:
        c = costo_experiencias(corpus, items_costo, perfil.personas)
        if c.total_eur > perfil.presupuesto_max_por_persona * perfil.personas:
            violaciones.append(Violacion(
                tipo="presupuesto_excedido",
                mensaje=(f"El itinerario cuesta {c.total_eur / perfil.personas:.2f} EUR por persona y el máximo es "
                         f"{perfil.presupuesto_max_por_persona:.2f} EUR. Elegí experiencias más baratas o "
                         f"sacá paradas."),
            ))
    return violaciones
