"""Modelos de dominio del agente (spec 001, ADR-0003).

Todo lo que cruza un borde (archivos, tools, LLM) es un modelo Pydantic validado.
`Horario` y `Experiencia` vienen del esquema de la ficha (corpus/schema.py): una sola definición.
"""
from __future__ import annotations

import re
from typing import Annotated, Literal, Optional

from pydantic import AfterValidator, BaseModel, Field, model_validator

from corpus.schema import Dia, Experiencia, Horario

__all__ = ["Bodega", "DiaItinerario", "Dia", "Experiencia", "Horario", "Itinerario", "Parada",
           "PerfilViaje", "a_hora", "a_minutos"]

_RE_HORA = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def a_minutos(hora: str) -> int:
    """'09:30' → 570. Lanza ValueError si no es una hora HH:MM válida."""
    m = _RE_HORA.match(hora or "")
    if not m:
        raise ValueError(f"hora inválida: {hora!r} (formato HH:MM, 00:00 a 23:59)")
    return int(m.group(1)) * 60 + int(m.group(2))


def a_hora(minutos: int) -> str:
    """570 → '09:30'."""
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def _validar_hora(v: str) -> str:
    a_minutos(v)
    return v


Hora = Annotated[str, AfterValidator(_validar_hora)]
Transporte = Literal["auto", "traslado", "bici", "a_pie"]


def _num(v) -> Optional[float]:
    if v in (None, ""):
        return None
    return float(v)


class Bodega(BaseModel):
    """Una bodega del corpus, lista para que la usen las tools y el verificador."""
    id: str
    nombre: str
    zona: str = ""
    comuna: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    perfil: str = "no_informado"
    horarios: list[Horario] = Field(default_factory=list)
    experiencias: list[Experiencia] = Field(default_factory=list)
    requiere_reserva: Optional[bool] = None
    tiene_restaurante: Optional[bool] = None
    opciones_sin_tacc: Optional[bool] = None
    opciones_vegetarianas: Optional[bool] = None
    opciones_veganas: Optional[bool] = None
    accesible_movilidad_reducida: Optional[bool] = None
    acepta_grupos: Optional[bool] = None
    capacidad_max_grupo: Optional[int] = None
    idiomas: list[str] = Field(default_factory=list)
    url_web: str = ""
    fuentes: list[dict] = Field(default_factory=list)

    @classmethod
    def desde_ficha(cls, ficha: dict) -> "Bodega":
        """Convierte una línea de data/fichas/fichas.jsonl (ficha extraída + `_meta`)."""
        meta = ficha.get("_meta", {})
        campos = {k: v for k, v in ficha.items() if k in cls.model_fields and k not in {"lat", "lon"}}
        campos.update(
            id=ficha.get("id") or meta.get("id"),
            zona=meta.get("zona", ""),
            comuna=meta.get("comuna", ""),
            lat=_num(meta.get("lat")),
            lon=_num(meta.get("lon")),
            url_web=meta.get("url_web", ""),
            fuentes=meta.get("fuentes", []),
        )
        return cls.model_validate(campos)


class PerfilViaje(BaseModel):
    """Lo que el relevamiento obtiene del turista (PRD sección 3)."""
    cantidad_dias: int = Field(ge=1, le=3)
    dia_inicio: Dia
    transporte: Transporte
    personas: int = Field(ge=1)
    presupuesto_max_por_persona: Optional[float] = Field(None, ge=0, description="EUR")
    movilidad_reducida: bool = False
    idiomas: list[str] = Field(default_factory=list)
    zonas_preferidas: list[str] = Field(default_factory=list)
    bodegas_evitar: list[str] = Field(default_factory=list)
    preferencias: Optional[str] = None
    hora_inicio_jornada: Hora = "09:30"
    hora_fin_jornada: Hora = "18:30"

    @model_validator(mode="after")
    def _jornada_ordenada(self):
        if a_minutos(self.hora_inicio_jornada) >= a_minutos(self.hora_fin_jornada):
            raise ValueError("la jornada tiene que empezar antes de terminar")
        return self


class Parada(BaseModel):
    bodega_id: str
    hora_inicio: Hora
    duracion_min: int = Field(gt=0)
    experiencia: Optional[str] = None


class DiaItinerario(BaseModel):
    numero: int = Field(ge=1)
    dia_semana: Dia
    paradas: list[Parada] = Field(default_factory=list)


class Itinerario(BaseModel):
    dias: list[DiaItinerario] = Field(default_factory=list)
    notas: Optional[str] = None
