#!/usr/bin/env python3
"""Sensor (ADR-0010): toda rama de tarea trae su entrada de CHANGELOG y su ADR.

Regla de Flora: cada cambio queda registrado en `CHANGELOG.md` (qué cambió y cuándo) y en un ADR
nuevo en `docs/adr/` (qué se decidió y por qué). La clase del 20/08 lo planteó como "chequeo antes
del PR que verifica si el changelog se actualizó"; acá se extiende al ADR.

Uso: python scripts/registro_obligatorio.py [rama_base]   (por defecto origin/desarrollo)
Sale con 0 si está todo, 1 si falta algo (y dice qué).
"""
from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

RE_ADR = re.compile(r"^docs/adr/(\d{4})-[\w\-]+\.md$")
SECCIONES_ADR = ("## Contexto", "## Decisión", "## Opciones consideradas", "## Consecuencias",
                 "## Cómo se verifica")


def revisar(cambios: list[tuple[str, str]], leer: Callable[[str], str],
            changelog_agregado: str) -> list[str]:
    """Devuelve la lista de faltantes. `cambios` = [(estado git, ruta)], `changelog_agregado` = líneas
    nuevas del CHANGELOG en la rama, `leer(ruta)` = contenido de un archivo en HEAD."""
    faltan: list[str] = []
    if not any(r == "CHANGELOG.md" for _, r in cambios) or not changelog_agregado.strip():
        faltan.append("CHANGELOG.md no tiene una entrada nueva en esta rama.")
    elif not re.search(r"^## \d{4}-\d{2}-\d{2} · ", changelog_agregado, re.M):
        faltan.append("la entrada nueva del CHANGELOG no sigue el formato '## AAAA-MM-DD · rama · …'.")

    adrs_nuevos = [r for e, r in cambios if e.startswith("A") and RE_ADR.match(r)
                   and not r.endswith("0000-template.md")]
    if not adrs_nuevos:
        faltan.append("no hay un ADR nuevo en docs/adr/ (formato de docs/adr/0000-template.md).")
    for ruta in adrs_nuevos:
        texto = leer(ruta)
        sin = [s for s in SECCIONES_ADR if s not in texto]
        if sin:
            faltan.append(f"{ruta} no tiene las secciones: {', '.join(sin)}.")
        if not re.search(r"^\*\*Estado:\*\* (Propuesto|Aceptado)", texto, re.M):
            faltan.append(f"{ruta} no declara '**Estado:** Propuesto' o 'Aceptado'.")
    return faltan


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout


def main() -> int:
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "origin/desarrollo"
    base = git("merge-base", "HEAD", base_ref).strip() or base_ref
    cambios = [tuple(l.split("\t")[:2]) for l in git("diff", "--name-status", base, "HEAD").splitlines()
               if "\t" in l]
    diff_cl = git("diff", "-U0", base, "HEAD", "--", "CHANGELOG.md")
    agregado = "\n".join(l[1:] for l in diff_cl.splitlines() if l.startswith("+") and not l.startswith("+++"))
    raiz = Path(git("rev-parse", "--show-toplevel").strip() or ".")
    faltan = revisar(cambios, lambda r: (raiz / r).read_text(encoding="utf-8"), agregado)
    if not faltan:
        print("OK: la rama trae entrada de CHANGELOG y ADR.")
        return 0
    print("FALTA REGISTRO (AGENTS.md, ADR-0010):")
    for f in faltan:
        print(f"  - {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
