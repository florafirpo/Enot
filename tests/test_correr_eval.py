"""Spec 007: `python -m eval.correr` y `make eval` (ADR-0007, ADR-0017).

El set se genera con el generador real (ítem 006) en una carpeta temporal; el corpus es la fixture SINTÉTICA.
Nunca se lee ni se escribe `data/eval/` del repo.
"""
from __future__ import annotations

import json

import pytest

from corpus import config
from enot import prompts
from enot.corpus_local import cargar_corpus
from eval.baselines import PROMPT_B0
from eval.correr import Reporte, SetInexistente, cargar_consultas, escribir_reporte, evaluar, main
from eval.generador import VERSION_GENERADOR, escribir_set
from eval.metricas import SalidaSistema
from tests.conftest import FIXTURES, ClienteFalso
from tests.dobles import EmbedderFalso
from tests.test_flujo import SALIDA_RESPUESTA

FICHAS = str(FIXTURES / "fichas_sinteticas.jsonl")


@pytest.fixture
def set_dev(entorno):
    escribir_set(config.DATA / "eval")
    return config.DATA / "eval"


def _reportes():
    return sorted(config.REPORTS_DIR.glob("eval_*.json"))


def test_cargar_consultas_sin_set(entorno):
    with pytest.raises(SetInexistente, match="eval.generador"):
        cargar_consultas("dev")
    with pytest.raises(ValueError):
        cargar_consultas("otro")


def test_cargar_consultas(set_dev):
    dev = cargar_consultas("dev")
    assert len(dev) == 60 and dev[0].id.startswith("q")
    assert len(cargar_consultas("test", set_dev)) == 40


class _SistemaQueFalla:
    nombre = "roto"

    def __init__(self):
        self.llamadas = 0

    def correr(self, consulta):
        self.llamadas += 1
        if self.llamadas == 1:
            raise RuntimeError("se cayó el proveedor")
        return SalidaSistema(consulta_id=consulta.id, sistema=self.nombre, tipo="pregunta")


def test_evaluar_sigue_si_un_sistema_falla(set_dev):
    consultas = cargar_consultas("dev")[:3]
    corpus = cargar_corpus(FIXTURES / "fichas_sinteticas.jsonl")
    r = evaluar([_SistemaQueFalla()], consultas, corpus, "dev", {"x": 1})
    assert isinstance(r, Reporte) and r.split == "dev" and r.configuracion == {"x": 1}
    salidas = r.salidas["roto"]
    assert [s.tipo for s in salidas] == ["error", "pregunta", "pregunta"]
    assert "se cayó el proveedor" in salidas[0].texto
    assert [s.consulta_id for s in salidas] == [c.id for c in consultas]
    assert r.metricas["roto"].tipos == {"error": 1, "pregunta": 2}
    assert len(r.evaluaciones["roto"]) == 3


def _sin_llm():
    raise AssertionError("B1 no tiene que crear el cliente LLM")


def test_main_b1_sin_llm(set_dev, capsys):
    codigo = main(["--split", "dev", "--sistemas", "B1", "--limite", "5", "--fichas", FICHAS],
                  crear_cliente=_sin_llm, crear_embedder=_sin_llm)
    assert codigo == 0
    [ruta] = _reportes()
    assert ruta.name.startswith("eval_dev_")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert set(datos["metricas"]) == {"B1"}
    assert len(datos["salidas"]["B1"]) == 5 and len(datos["evaluaciones"]["B1"]) == 5
    conf = datos["configuracion"]
    assert conf["split"] == "dev" and conf["sistemas"] == ["B1"] and conf["consultas"] == 5
    assert conf["version_generador"] == VERSION_GENERADOR
    assert conf["bodegas_corpus"] == 7
    assert datos["metricas"]["B1"]["consultas"] == 5
    assert str(ruta) in capsys.readouterr().out


def _responder(sistema, usuario):
    if sistema == PROMPT_B0:
        return {"es_posible": True, "motivo": None, "dias": [{"dia_semana": "vie", "paradas": [
            {"bodega": "Domaine Inventado", "hora_inicio": "10:00", "duracion_min": 60}]}]}
    if sistema == prompts.cargar("relevamiento"):
        return {"cantidad_dias": 1, "dia_inicio": "vie", "transporte": "auto", "personas": 2}
    if sistema == prompts.cargar("planificador"):
        return {"dias": [{"paradas": []}]}
    return SALIDA_RESPUESTA


def test_main_todos_los_sistemas(set_dev):
    creados = []

    def crear_cliente():
        creados.append("cliente")
        return ClienteFalso([_responder])

    codigo = main(["--split", "dev", "--limite", "2", "--fichas", FICHAS], crear_cliente=crear_cliente,
                  crear_embedder=EmbedderFalso)
    assert codigo == 0 and creados == ["cliente"]
    [ruta] = _reportes()
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert list(datos["metricas"]) == ["B0", "B1", "B2", "enot"]
    assert all(len(v) == 2 for v in datos["salidas"].values())
    assert {s["tipo"] for s in datos["salidas"]["B0"]} == {"itinerario"}
    assert datos["metricas"]["B0"]["inventadas"] == 2
    assert datos["configuracion"]["modelo"] == "modelo-falso"
    assert datos["configuracion"]["max_intentos"] == 3


def test_main_sin_set_sale_con_1(entorno, capsys):
    assert main(["--split", "dev", "--sistemas", "B1", "--fichas", FICHAS]) == 1
    assert "eval.generador" in capsys.readouterr().err
    assert _reportes() == []


def test_main_sistema_desconocido_sale_con_1(set_dev, capsys):
    assert main(["--split", "dev", "--sistemas", "B1,B7", "--fichas", FICHAS]) == 1
    assert "B7" in capsys.readouterr().err


def test_main_sin_corpus_sale_con_1(set_dev, capsys):
    assert main(["--split", "dev", "--sistemas", "B1"]) == 1   # FICHAS_JSONL del entorno no existe
    assert "fichas" in capsys.readouterr().err


def test_escribir_reporte_no_pisa(entorno):
    r = Reporte(split="test", fecha="2026-11-29-153000", configuracion={}, metricas={}, evaluaciones={}, salidas={})
    a, b = escribir_reporte(r), escribir_reporte(r)
    assert a != b and a.exists() and b.exists()
    assert a.name == "eval_test_2026-11-29-153000.json"
    assert a.parent == config.REPORTS_DIR
    assert Reporte.model_validate_json(b.read_text(encoding="utf-8")) == r
