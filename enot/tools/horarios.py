"""Tool `abierta_en` (ADR-0005): ¿la bodega recibe visitas en ese día y franja?

Una visita está dentro del horario si empieza en o después de la apertura y termina en o antes del
cierre. Si la bodega no publica horario (o lo publica sin horas), la respuesta es `None`: no se sabe.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from ..modelos import Bodega, a_minutos


class ResultadoHorario(BaseModel):
    abierta: Optional[bool]
    motivo: str


def abierta_en(corpus: dict[str, Bodega], bodega_id: str, dia: str, hora_inicio: str,
               duracion_min: int) -> ResultadoHorario:
    b = corpus.get(bodega_id)
    if b is None:
        return ResultadoHorario(abierta=None, motivo=f"error: bodega inexistente en el corpus: {bodega_id}")
    try:
        inicio = a_minutos(hora_inicio)
    except ValueError as e:
        return ResultadoHorario(abierta=None, motivo=f"error: {e}")
    fin = inicio + duracion_min
    if not b.horarios:
        return ResultadoHorario(abierta=None, motivo="la bodega no publica horario")

    del_dia = [h for h in b.horarios if dia in h.dias]
    if not del_dia:
        return ResultadoHorario(abierta=False, motivo=f"cerrada los {dia}")

    franjas = []
    for h in del_dia:
        if not h.apertura or not h.cierre:
            return ResultadoHorario(abierta=None, motivo=f"horario de los {dia} publicado sin horas")
        a, c = a_minutos(h.apertura), a_minutos(h.cierre)
        if a <= inicio and fin <= c:
            return ResultadoHorario(abierta=True, motivo=f"abierta de {h.apertura} a {h.cierre}")
        franjas.append(f"{h.apertura}–{h.cierre}")
    return ResultadoHorario(abierta=False, motivo=f"fuera de horario: los {dia} abre {', '.join(franjas)}")
