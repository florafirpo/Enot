#!/usr/bin/env python3
"""Sensor (ADR-0008): lista los tests que ya existían en origin/main y se modificaron en esta rama.

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
    git("fetch", "--depth=50", "origin", "main")
    base = git("merge-base", "HEAD", "origin/main").strip() or "origin/main"
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
