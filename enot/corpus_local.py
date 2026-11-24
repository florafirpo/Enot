"""Carga del corpus de fichas para el agente (spec 001)."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from corpus import config

from .modelos import Bodega

log = logging.getLogger(__name__)


def cargar_corpus(ruta: Path | None = None) -> dict[str, Bodega]:
    """Lee `fichas.jsonl` y devuelve {id: Bodega}. Las líneas inválidas se saltean y se informan."""
    ruta = Path(ruta) if ruta else config.FICHAS_JSONL
    if not ruta.exists():
        return {}
    corpus: dict[str, Bodega] = {}
    invalidas = 0
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        if not linea.strip():
            continue
        try:
            b = Bodega.desde_ficha(json.loads(linea))
        except (json.JSONDecodeError, ValidationError, TypeError) as e:
            invalidas += 1
            log.warning("línea %d de %s inválida: %s", n, ruta, str(e)[:200])
            continue
        corpus[b.id] = b
    if invalidas:
        log.warning("%d líneas inválidas salteadas en %s", invalidas, ruta)
    return corpus
