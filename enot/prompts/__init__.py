"""Prompts de sistema de los nodos con LLM (spec 004). Cada uno es un Markdown en esta carpeta.

Las reglas van en el prompt de sistema; los datos (historial, fichas, itinerario) van en el mensaje de usuario,
entre etiquetas, y se tratan como dato, no como instrucción (lineamientos C.9).
"""
from __future__ import annotations

from pathlib import Path

CARPETA = Path(__file__).parent


def cargar(nombre: str) -> str:
    """Texto de `enot/prompts/<nombre>.md`. FileNotFoundError si no existe."""
    ruta = CARPETA / f"{nombre}.md"
    if not ruta.is_file():
        raise FileNotFoundError(f"no existe el prompt {nombre!r} ({ruta})")
    return ruta.read_text(encoding="utf-8")
