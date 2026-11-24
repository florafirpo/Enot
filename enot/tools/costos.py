"""Tool `costo_experiencias` (ADR-0005): costo total en EUR de las experiencias elegidas.

Solo suma precios en EUR. Un precio sin moneda o en otra moneda no se convierte ni se asume: se
informa en `sin_precio` para que el planificador lo diga ("precio a consultar").
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from ..modelos import Bodega, Experiencia


class ItemCosto(BaseModel):
    bodega_id: str
    experiencia: Optional[str] = Field(None, description="Nombre de la experiencia; None = la más barata en EUR")


class LineaCosto(BaseModel):
    bodega_id: str
    experiencia: str
    precio_por_persona_eur: float
    subtotal_eur: float


class ResultadoCosto(BaseModel):
    total_eur: float = 0.0
    detalle: list[LineaCosto] = Field(default_factory=list)
    sin_precio: list[str] = Field(default_factory=list)
    errores: list[str] = Field(default_factory=list)


def _en_eur(e: Experiencia) -> bool:
    return e.precio_por_persona is not None and e.moneda == "EUR"


def costo_experiencias(corpus: dict[str, Bodega], items: list[ItemCosto], personas: int) -> ResultadoCosto:
    r = ResultadoCosto()
    if personas < 1:
        r.errores.append(f"cantidad de personas inválida: {personas}")
        return r
    for it in items:
        b = corpus.get(it.bodega_id)
        if b is None:
            r.errores.append(f"bodega inexistente en el corpus: {it.bodega_id}")
            continue
        if it.experiencia is None:
            con_precio = [e for e in b.experiencias if _en_eur(e)]
            if not con_precio:
                r.sin_precio.append(f"{b.id}: sin experiencias con precio en EUR")
                continue
            exp = min(con_precio, key=lambda e: e.precio_por_persona)
        else:
            exp = next((e for e in b.experiencias if e.nombre.casefold() == it.experiencia.casefold()), None)
            if exp is None:
                r.errores.append(f"{b.id}: no existe la experiencia {it.experiencia!r}")
                continue
            if not _en_eur(exp):
                r.sin_precio.append(f"{b.id}: {exp.nombre} sin precio en EUR")
                continue
        subtotal = exp.precio_por_persona * personas
        r.detalle.append(LineaCosto(bodega_id=b.id, experiencia=exp.nombre,
                                    precio_por_persona_eur=exp.precio_por_persona, subtotal_eur=subtotal))
        r.total_eur += subtotal
    return r
