#!/usr/bin/env python3
"""Hook PreToolUse: políticas que se cumplen siempre, decida lo que decida el modelo (ADR-0008).

Claude Code le pasa por stdin un JSON con `tool_name` y `tool_input`.
Salir con código 2 bloquea la acción y el mensaje de stderr le llega al agente.

Políticas:
1. Nunca leer ni escribir `.env` (secretos).
2. La partición de test `data/eval/test/` no se modifica una vez creada (ADR-0007).
3. Nunca pushear a `main`, ni forzar un push.
4. Nada de borrados recursivos fuera de carpetas temporales.
5. Las revisiones del compañero (`docs/revisiones/`) no se editan una vez escritas (ADR-0010):
   el desarrollador no puede retocar el veredicto de su revisor.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
TEST_DIR = (RAIZ / "data" / "eval" / "test").resolve()
REVISIONES_DIR = (RAIZ / "docs" / "revisiones").resolve()


def bloquear(motivo: str) -> None:
    print(f"BLOQUEADO por política del repo: {motivo}", file=sys.stderr)
    sys.exit(2)


def es_env(ruta: str) -> bool:
    nombre = Path(ruta).name
    return nombre == ".env" or (nombre.startswith(".env.") and nombre != ".env.example")


def _resolver(ruta: str) -> Path | None:
    try:
        return (RAIZ / ruta).resolve() if not Path(ruta).is_absolute() else Path(ruta).resolve()
    except OSError:
        return None


def dentro_de(ruta: str, carpeta: Path) -> bool:
    p = _resolver(ruta)
    return p is not None and (p == carpeta or carpeta in p.parents)


def dentro_de_test(ruta: str) -> bool:
    return dentro_de(ruta, TEST_DIR)


def revisar(tool: str, entrada: dict) -> str | None:
    """Devuelve el motivo de bloqueo, o None si la acción está permitida."""
    ruta = entrada.get("file_path") or entrada.get("path") or entrada.get("notebook_path") or ""

    if tool in {"Read", "Edit", "Write", "MultiEdit", "NotebookEdit"} and ruta and es_env(ruta):
        return "los archivos .env tienen secretos y no se leen ni se editan."

    if tool in {"Edit", "Write", "MultiEdit", "NotebookEdit"} and ruta and dentro_de_test(ruta):
        p = (RAIZ / ruta) if not Path(ruta).is_absolute() else Path(ruta)
        if p.exists():
            return "la partición de test (data/eval/test/) es inmutable una vez creada (ADR-0007)."

    if tool in {"Edit", "Write", "MultiEdit"} and ruta and dentro_de(ruta, REVISIONES_DIR):
        p = (RAIZ / ruta) if not Path(ruta).is_absolute() else Path(ruta)
        if p.exists():
            return ("las revisiones del compañero no se editan (ADR-0010): "
                    "si hace falta otra, va en un archivo nuevo de la ronda siguiente.")

    if tool == "Bash":
        cmd = entrada.get("command", "")
        if re.search(r"(^|[\s;&|])(cat|less|more|head|tail|source|\.)\s+[^\s;&|]*\.env(\s|$)", cmd):
            return "no se leen archivos .env."
        if re.search(r"git\s+push\b.*(--force|\s-f\b)", cmd):
            return "no se fuerza un push."
        if re.search(r"git\s+push\b[^;&|]*\b(origin\s+)?(HEAD:)?main\b", cmd):
            return "nunca se pushea a main: abrí un PR desde una rama noche/…"
        if re.search(r"rm\s+-[a-zA-Z]*r[a-zA-Z]*\s+(?!/tmp/)(?!\.mutmut-cache)(?!mutants)", cmd):
            return "borrado recursivo bloqueado; si es necesario, pedíselo a Flora en el PR."
        if re.search(r"data/eval/test", cmd) and re.search(r"(>|\brm\b|\bmv\b|\bsed\s+-i)", cmd):
            return "la partición de test es inmutable (ADR-0007)."
        if re.search(r"docs/revisiones/\S+", cmd) and re.search(r"(\bsed\s+-i|\brm\b|\bmv\b|>>?\s*\S*docs/revisiones/)", cmd):
            return "las revisiones del compañero no se modifican (ADR-0010)."
    return None


def main() -> None:
    try:
        datos = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # entrada inesperada: no bloqueamos por error del hook
    motivo = revisar(datos.get("tool_name", ""), datos.get("tool_input") or {})
    if motivo:
        bloquear(motivo)
    sys.exit(0)


if __name__ == "__main__":
    main()
