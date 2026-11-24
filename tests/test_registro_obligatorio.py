"""El sensor de registro (ADR-0010) exige CHANGELOG y ADR en cada rama, y deja pasar una rama completa."""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "registro_obligatorio.py"
spec = importlib.util.spec_from_file_location("registro_obligatorio", SCRIPT)
reg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reg)

ADR_OK = """# ADR-0011: Algo
**Estado:** Propuesto
**Fecha:** 2026-11-25
## Contexto
x
## Decisión
x
## Opciones consideradas
x
## Consecuencias
x
## Cómo se verifica
x
"""
CL_OK = "## 2026-11-25 · noche/2026-11-25-003\n- retrieval híbrido"


def leer_de(contenidos: dict[str, str]):
    return lambda ruta: contenidos[ruta]


def test_rama_completa_pasa():
    cambios = [("M", "CHANGELOG.md"), ("A", "docs/adr/0011-algo.md"), ("A", "enot/retrieval.py")]
    assert reg.revisar(cambios, leer_de({"docs/adr/0011-algo.md": ADR_OK}), CL_OK) == []


def test_falta_changelog():
    cambios = [("A", "docs/adr/0011-algo.md")]
    faltan = reg.revisar(cambios, leer_de({"docs/adr/0011-algo.md": ADR_OK}), "")
    assert len(faltan) == 1 and "CHANGELOG" in faltan[0]


def test_changelog_tocado_sin_lineas_nuevas_no_cuenta():
    cambios = [("M", "CHANGELOG.md"), ("A", "docs/adr/0011-algo.md")]
    faltan = reg.revisar(cambios, leer_de({"docs/adr/0011-algo.md": ADR_OK}), "   \n")
    assert any("CHANGELOG" in f for f in faltan)


def test_changelog_con_formato_incorrecto():
    cambios = [("M", "CHANGELOG.md"), ("A", "docs/adr/0011-algo.md")]
    faltan = reg.revisar(cambios, leer_de({"docs/adr/0011-algo.md": ADR_OK}), "- cosas varias")
    assert any("formato" in f for f in faltan)


def test_falta_adr():
    faltan = reg.revisar([("M", "CHANGELOG.md")], leer_de({}), CL_OK)
    assert len(faltan) == 1 and "ADR" in faltan[0]


def test_modificar_un_adr_viejo_no_reemplaza_uno_nuevo():
    cambios = [("M", "CHANGELOG.md"), ("M", "docs/adr/0009-verificador-datos-faltantes.md")]
    assert any("ADR nuevo" in f for f in reg.revisar(cambios, leer_de({}), CL_OK))


def test_el_template_no_cuenta_como_adr():
    cambios = [("M", "CHANGELOG.md"), ("A", "docs/adr/0000-template.md")]
    assert any("ADR nuevo" in f for f in reg.revisar(cambios, leer_de({}), CL_OK))


def test_adr_incompleto_se_marca_con_las_secciones_que_faltan():
    adr = ADR_OK.replace("## Cómo se verifica\nx\n", "").replace("## Contexto\nx\n", "")
    cambios = [("M", "CHANGELOG.md"), ("A", "docs/adr/0011-algo.md")]
    faltan = reg.revisar(cambios, leer_de({"docs/adr/0011-algo.md": adr}), CL_OK)
    assert len(faltan) == 1 and "## Contexto" in faltan[0] and "## Cómo se verifica" in faltan[0]


def test_adr_sin_estado():
    adr = ADR_OK.replace("**Estado:** Propuesto\n", "")
    cambios = [("M", "CHANGELOG.md"), ("A", "docs/adr/0011-algo.md")]
    faltan = reg.revisar(cambios, leer_de({"docs/adr/0011-algo.md": adr}), CL_OK)
    assert len(faltan) == 1 and "Estado" in faltan[0]
