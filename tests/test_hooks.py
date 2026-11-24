"""Las políticas del hook (ADR-0008) tienen que bloquear lo prohibido y dejar pasar lo normal."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "proteger.py"
spec = importlib.util.spec_from_file_location("proteger", HOOK)
proteger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proteger)


@pytest.mark.parametrize("tool,entrada", [
    ("Read", {"file_path": ".env"}),
    ("Edit", {"file_path": "/x/y/.env.local"}),
    ("Bash", {"command": "cat .env"}),
    ("Bash", {"command": "git push origin main"}),
    ("Bash", {"command": "git push -f origin noche/x"}),
    ("Bash", {"command": "rm -rf corpus"}),
])
def test_bloquea(tool, entrada):
    assert proteger.revisar(tool, entrada) is not None


@pytest.mark.parametrize("tool,entrada", [
    ("Read", {"file_path": ".env.example"}),
    ("Edit", {"file_path": "corpus/extract.py"}),
    ("Bash", {"command": "git push -u origin noche/2026-11-24-001"}),
    ("Bash", {"command": "pytest -q"}),
    ("Bash", {"command": "rm -rf /tmp/algo"}),
])
def test_permite(tool, entrada):
    assert proteger.revisar(tool, entrada) is None


def test_particion_de_test_inmutable(monkeypatch, tmp_path):
    test_dir = tmp_path / "data/eval/test"
    test_dir.mkdir(parents=True)
    (test_dir / "consultas.jsonl").write_text("{}")
    monkeypatch.setattr(proteger, "RAIZ", tmp_path)
    monkeypatch.setattr(proteger, "TEST_DIR", test_dir.resolve())
    assert proteger.revisar("Edit", {"file_path": "data/eval/test/consultas.jsonl"}) is not None
    # crear un archivo nuevo sí se permite (la primera vez que se genera la partición)
    assert proteger.revisar("Write", {"file_path": "data/eval/test/nuevo.jsonl"}) is None


def test_el_script_sale_con_codigo_2_al_bloquear():
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(
        {"tool_name": "Read", "tool_input": {"file_path": ".env"}}), capture_output=True, text=True)
    assert r.returncode == 2 and "BLOQUEADO" in r.stderr
