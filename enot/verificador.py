"""Verificador de restricciones duras (specs 002 y 010, ADR-0003).

Código puro: recibe un itinerario, el perfil y el corpus, y devuelve las violaciones (y, con
`verificar_completo`, también las advertencias). Sin violaciones = itinerario factible. Cada mensaje de
violación está escrito para que el planificador pueda corregir en el reintento; cada advertencia, para
mostrársela al turista.

Usa las tools de `enot/tools/` para horarios, traslados y costos: una sola fuente de verdad (ADR-0005).

Regla para lo que no se sabe:
- un *límite de la bodega* (horario, coordenadas, capacidad, precio) solo viola con evidencia del límite
  (ADR-0009);
- una *necesidad del turista* (accesibilidad, idioma) viola con evidencia en contra (`False`, o una lista de
  idiomas publicada sin el pedido) y, sin dato, genera una advertencia (ADR-0012). El francés se da por
  cumplido en todas las bodegas.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from .modelos import Bodega, Experiencia, Itinerario, Parada, PerfilViaje, a_hora, a_minutos
from .tools import ItemCosto, abierta_en, costo_experiencias, tiempo_traslado

__all__ = ["IDIOMA_BASE", "Advertencia", "ResultadoVerificacion", "TipoAdvertencia", "TipoViolacion",
           "Violacion", "verificar", "verificar_completo"]

TipoViolacion = Literal[
    "bodega_inexistente", "experiencia_inexistente", "cerrada", "traslado_imposible", "jornada_excedida",
    "presupuesto_excedido", "grupo_excede_capacidad", "accesibilidad", "idioma_no_disponible",
]
TipoAdvertencia = Literal["accesibilidad_sin_confirmar", "idioma_sin_confirmar"]

# El francés se habla en todas las bodegas de Borgoña: formas en que el perfil puede nombrarlo.
IDIOMA_BASE = frozenset({"fr", "fra", "fre", "francés", "frances", "français", "francais", "french"})


class Violacion(BaseModel):
    tipo: TipoViolacion
    mensaje: str
    dia: Optional[int] = None
    bodega_id: Optional[str] = None


class Advertencia(BaseModel):
    """Una necesidad del turista que la ficha no permite confirmar ni descartar. No dispara reintento."""
    tipo: TipoAdvertencia
    mensaje: str
    dia: Optional[int] = None
    bodega_id: Optional[str] = None


class ResultadoVerificacion(BaseModel):
    violaciones: list[Violacion]
    advertencias: list[Advertencia]

    @property
    def factible(self) -> bool:
        """Las advertencias no cuentan: factible = sin violaciones."""
        return not self.violaciones


def _fin(p: Parada) -> int:
    return a_minutos(p.hora_inicio) + p.duracion_min


def _franja(p: Parada) -> str:
    return f"de {p.hora_inicio} a {a_hora(_fin(p))}"


def _experiencia(b: Bodega, nombre: str) -> Optional[Experiencia]:
    return next((e for e in b.experiencias if e.nombre.casefold() == nombre.casefold()), None)


def _chequear_parada(p: Parada, b: Bodega, dia: str, perfil: PerfilViaje, corpus: dict[str, Bodega],
                     nueva, advertir) -> None:
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

    if perfil.movilidad_reducida:
        if b.accesible_movilidad_reducida is False:
            nueva("accesibilidad", f"{b.nombre} no es accesible para movilidad reducida. Elegí otra bodega.")
        elif b.accesible_movilidad_reducida is None:
            advertir("accesibilidad_sin_confirmar",
                     f"no pude confirmar que {b.nombre} sea accesible para movilidad reducida: la bodega no lo "
                     f"publica. Conviene consultarle antes de ir.")

    pedidos = {i.casefold() for i in perfil.idiomas}
    if pedidos and not pedidos & IDIOMA_BASE:
        disponibles = (exp.idiomas if exp is not None and exp.idiomas else None) or b.idiomas
        if not disponibles:
            advertir("idioma_sin_confirmar",
                     f"no pude confirmar que {b.nombre} reciba visitas en {', '.join(perfil.idiomas)}: no publica "
                     f"idiomas (en francés, seguro). Conviene consultarle antes de ir.")
        elif not pedidos & {i.casefold() for i in disponibles}:
            de = f"{exp.nombre!r} en {b.nombre}" if exp is not None and exp.idiomas else b.nombre
            nueva("idioma_no_disponible",
                  f"{de} no informa visitas en {', '.join(perfil.idiomas)} "
                  f"(idiomas publicados: {', '.join(disponibles)}).")


def verificar(itinerario: Itinerario, perfil: PerfilViaje, corpus: dict[str, Bodega]) -> list[Violacion]:
    """Devuelve las restricciones duras que el itinerario no cumple, en orden determinístico.

    Es lo que mira el loop de reintento y el *hard pass rate*; las advertencias, en `verificar_completo`."""
    return verificar_completo(itinerario, perfil, corpus).violaciones


def verificar_completo(itinerario: Itinerario, perfil: PerfilViaje,
                       corpus: dict[str, Bodega]) -> ResultadoVerificacion:
    """Violaciones (restricciones duras incumplidas) y advertencias (necesidades sin dato), por separado."""
    violaciones: list[Violacion] = []
    advertencias: list[Advertencia] = []
    items_costo: list[ItemCosto] = []
    inicio_jornada, fin_jornada = a_minutos(perfil.hora_inicio_jornada), a_minutos(perfil.hora_fin_jornada)

    for d in itinerario.dias:
        def nueva(tipo, mensaje, bodega_id=None, _dia=d.numero):
            violaciones.append(Violacion(tipo=tipo, mensaje=f"Día {_dia}: {mensaje}", dia=_dia,
                                         bodega_id=bodega_id))

        def advertir(tipo, mensaje, bodega_id, _dia=d.numero):
            advertencias.append(Advertencia(tipo=tipo, mensaje=f"Día {_dia}: {mensaje}", dia=_dia,
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
                             lambda tipo, msg, _b=b.id: nueva(tipo, msg, _b),
                             lambda tipo, msg, _b=b.id: advertir(tipo, msg, _b))
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
    return ResultadoVerificacion(violaciones=violaciones, advertencias=advertencias)
