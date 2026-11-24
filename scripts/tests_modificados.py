#!/usr/bin/env python3
"""Sensor (ADR-0008): lista los tests que ya existían en la rama base y se modificaron en esta rama.

Uso: python scripts/tests_modificados.py [rama_base]   (por defecto origin/desarrollo; ADR-0010)

Un agente puede "hacer pasar" una tarea cambiando los tests en vez del código (reward hacking).
Este script no lo prohíbe, pero lo hace visible en el PR: cada test viejo modificado tiene que
estar justificado en la descripción.
"""
from __future__ import annotations

import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout


def main() -> int:
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "origin/desarrollo"
    git("fetch", "--depth=50", "origin", base_ref.removeprefix("origin/"))
    base = git("merge-base", "HEAD", base_ref).strip() or base_ref
    cambiados = git("diff", "--name-status", base, "HEAD", "--", "tests/").splitlines()
    modificados = [l.split("\t")[-1] for l in cambiados if l.startswith(("M", "D", "R"))]
    if not modificados:
        print("OK: no se modificó ningún test existente.")
        return 0
    print("ATENCIÓN: tests existentes modificados o borrados (justificar en el PR):")
    for f in modificados:
        print(f"  - {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
