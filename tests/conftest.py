"""Fixtures compartidas. Los tests corren offline: sin red, sin claves, sin LLM real."""
from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

from corpus import config

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """Redirige todas las carpetas de datos del pipeline a un directorio temporal."""
    rutas = {
        "DATA": tmp_path / "data",
        "SEED_DIR": tmp_path / "data/seed",
        "RAW_DIR": tmp_path / "data/raw",
        "CLEAN_DIR": tmp_path / "data/clean",
        "BASE_DIR": tmp_path / "data/base",
        "FICHAS_DIR": tmp_path / "data/fichas",
        "VALIDACION_DIR": tmp_path / "data/validacion",
        "REPORTS_DIR": tmp_path / "reports",
    }
    for nombre, ruta in rutas.items():
        ruta.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(config, nombre, ruta)
    monkeypatch.setattr(config, "SEED_CSV", rutas["SEED_DIR"] / "bodegas.csv")
    monkeypatch.setattr(config, "SEED_MANUAL_CSV", rutas["SEED_DIR"] / "manual.csv")
    monkeypatch.setattr(config, "FICHAS_JSONL", rutas["FICHAS_DIR"] / "fichas.jsonl")
    monkeypatch.setattr(config, "COSTOS_CSV", rutas["FICHAS_DIR"] / "costos_extraccion.csv")
    monkeypatch.setattr(config, "COLUMNAS_DATATOURISME", {})
    return tmp_path


class ClienteFalso:
    """Doble de `ClienteLLM`: devuelve respuestas guionadas, en orden, y registra lo que recibió.

    Cada respuesta puede ser un dict (se serializa a JSON), un str (se devuelve tal cual, sirve para
    simular JSON inválido) o una función `f(sistema, usuario) -> dict | str`.
    """

    provider = "falso"
    model = "modelo-falso"

    def __init__(self, respuestas: list):
        self.respuestas = list(respuestas)
        self.llamadas: list[dict] = []

    def estructurado(self, sistema, usuario, modelo, max_intentos=2):
        from corpus.llm import Resultado

        ultimo_error = None
        for intento in range(1, max_intentos + 1):
            self.llamadas.append({"sistema": sistema, "usuario": usuario, "intento": intento})
            r = self.respuestas.pop(0) if len(self.respuestas) > 1 else self.respuestas[0]
            if callable(r):
                r = r(sistema, usuario)
            try:
                datos = r if isinstance(r, dict) else json.loads(r)
                return Resultado(modelo.model_validate(datos), 100, 50, 0.01, intento)
            except Exception as e:  # noqa: BLE001
                ultimo_error = e
        raise RuntimeError(f"salida inválida: {ultimo_error}")


@pytest.fixture
def cliente_falso():
    return ClienteFalso


def respuesta_openai(contenido: str, tin: int = 10, tout: int = 5):
    """Arma un objeto con la forma de una respuesta de chat.completions de OpenAI."""
    msg = types.SimpleNamespace(content=contenido)
    return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)],
                                 usage=types.SimpleNamespace(prompt_tokens=tin, completion_tokens=tout))
