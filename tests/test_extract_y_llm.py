"""Extracción de fichas (paso 4) y cliente LLM (ADR-0006)."""
from __future__ import annotations

import json
import types

import pytest

from corpus import config, extract, llm
from corpus import datatourisme as dt
from corpus.schema import FichaBodega
from corpus.utils import leer_jsonl

from .conftest import FIXTURES, ClienteFalso, respuesta_openai


def ficha(nombre: str, cita: str, url: str = "u") -> dict:
    return {"nombre": nombre, "experiencias": [
        {"nombre": "Dégustation", "tipo": "degustacion", "precio_por_persona": 20, "moneda": "EUR"}],
        "evidencias": [{"campo": "experiencias[0].precio_por_persona", "cita": cita, "url": url}]}


def test_verificar_evidencias_detecta_citas_inventadas():
    f = {"evidencias": [{"cita": "dégustation de 6 vins : 20 € par personne"},
                        {"cita": "menú celíaco completo"}]}
    texto = "Visite des caves et DÉGUSTATION de 6 vins :   20 € par personne, sur réservation."
    assert extract.verificar_evidencias(f, texto) == (1, 2)
    assert [e["verificada"] for e in f["evidencias"]] == [True, False]


def test_extract_escribe_fichas_con_metadatos_y_costos(entorno):
    dt.run(str(FIXTURES / "datatourisme_simulado.csv"))
    falso = ClienteFalso([lambda s, u: ficha(u.split("\n")[0].replace("Bodega: ", ""),
                                             "20 € par personne")])
    extract.run(cliente=falso)
    fichas = leer_jsonl(config.FICHAS_JSONL)
    assert len(fichas) == 5
    rt = next(f for f in fichas if f["nombre"] == "Domaine Rossignol-Trapet")
    assert rt["_meta"]["zona"] == "Côte de Nuits"
    assert rt["_meta"]["evidencias_verificadas"] == 1      # la cita está en su descripción
    otra = next(f for f in fichas if f["nombre"] == "Domaine Laroche")
    assert otra["_meta"]["evidencias_verificadas"] == 0    # su descripción está vacía
    assert config.COSTOS_CSV.read_text().count("\n") == 6  # encabezado + 5 filas


def test_extract_no_reprocesa_sin_force(entorno):
    dt.run(str(FIXTURES / "datatourisme_simulado.csv"), departamentos=["89"])
    falso = ClienteFalso([ficha("Domaine Laroche", "x")])
    extract.run(cliente=falso)
    extract.run(cliente=falso)
    assert len(falso.llamadas) == 1


def test_esquema_sin_refs():
    s = llm.esquema_sin_refs(FichaBodega)
    assert "$ref" not in json.dumps(s) and "$defs" not in s
    assert s["properties"]["experiencias"]["items"]["properties"]["tipo"]["enum"]


def _cliente_openai(respuestas: list, errores: list[str] | None = None):
    """ClienteLLM con un backend OpenAI simulado. `errores` se lanzan en orden antes de responder."""
    errores = list(errores or [])
    pedidos = []

    def create(**kw):
        pedidos.append(kw)
        if errores:
            raise Exception(errores.pop(0))
        return respuesta_openai(respuestas.pop(0))

    c = llm.ClienteLLM.__new__(llm.ClienteLLM)
    c.provider, c.model, c._json_schema_ok = "openai", "m", True
    c.cli = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))
    return c, pedidos


def test_reintenta_si_la_salida_no_valida():
    c, pedidos = _cliente_openai(['{"nombre": "X", "perfil": "inexistente"}', json.dumps({"nombre": "X"})])
    r = c.estructurado("s", "u", FichaBodega)
    assert r.intentos == 2 and r.objeto.nombre == "X"
    assert "no valida" in pedidos[1]["messages"][-1]["content"]
    assert r.tokens_in == 20 and r.tokens_out == 10


def test_falla_tras_max_intentos():
    c, _ = _cliente_openai(["no es json", "tampoco"])
    with pytest.raises(RuntimeError):
        c.estructurado("s", "u", FichaBodega)


def test_se_adapta_a_modelos_sin_temperature_ni_max_tokens():
    c, pedidos = _cliente_openai([json.dumps({"nombre": "X"})],
                                 ["Unsupported parameter: 'temperature'",
                                  "Unsupported parameter: 'max_tokens'. Use 'max_completion_tokens'"])
    c.estructurado("s", "u", FichaBodega)
    ultimo = pedidos[-1]
    assert "temperature" not in ultimo and "max_completion_tokens" in ultimo
