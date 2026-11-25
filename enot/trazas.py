"""Traza JSONL de las llamadas al LLM (spec 004, ADR-0006, lineamientos D2).

Una traza por conversación (un archivo en `data/trazas/`), un evento por llamada al modelo, salga bien o mal.
Lo que se registra alimenta el reporte de costo y latencia (ítem 008): tokens, latencia, intentos y errores.
"""
from __future__ import annotations

import secrets
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from corpus import config

__all__ = ["EventoTraza", "NodoLLM", "Traza"]

NodoLLM = Literal["relevamiento", "planificador", "respuesta"]


class EventoTraza(BaseModel):
    conversacion: str
    nodo: NodoLLM
    intento: int = Field(ge=1, description="Intento del loop de verificación (005); 1 fuera del loop")
    proveedor: str
    modelo: str
    inicio: str = Field(description="ISO 8601, UTC")
    latencia_s: float = Field(ge=0)
    # None = desconocido: si el cliente falla, puede haber hecho llamadas pagas que no informa. Nunca 0 inventado.
    tokens_in: Optional[int] = Field(None, ge=0)
    tokens_out: Optional[int] = Field(None, ge=0)
    intentos_validacion: Optional[int] = Field(None, ge=0, description="Llamadas que hizo ClienteLLM hasta validar")
    estado: Literal["ok", "error"]
    error: Optional[str] = None

    @model_validator(mode="after")
    def _tokens_si_ok(self):
        # una llamada que salió bien siempre informa sus tokens; None solo puede venir de un error (spec 008)
        if self.estado == "ok" and (self.tokens_in is None or self.tokens_out is None):
            raise ValueError("un evento con estado 'ok' tiene que traer tokens_in y tokens_out")
        return self


class Traza:
    """Archivo JSONL de una conversación. Solo agrega líneas; nunca reescribe."""

    def __init__(self, ruta: Path, conversacion: Optional[str] = None):
        self.ruta = Path(ruta)
        self.conversacion = conversacion or self.ruta.stem

    @classmethod
    def nueva(cls, carpeta: Optional[Path] = None) -> "Traza":
        carpeta = Path(carpeta) if carpeta else config.DATA / "trazas"
        nombre = f"{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(4)}"
        return cls(carpeta / f"{nombre}.jsonl")

    def registrar(self, evento: EventoTraza) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with self.ruta.open("a", encoding="utf-8") as f:
            f.write(evento.model_dump_json() + "\n")

    def eventos(self) -> list[EventoTraza]:
        if not self.ruta.exists():
            return []
        return [EventoTraza.model_validate_json(linea)
                for linea in self.ruta.read_text(encoding="utf-8").splitlines() if linea.strip()]
