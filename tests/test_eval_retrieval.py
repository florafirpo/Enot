"""Spec 003: métricas del retrieval (Recall@k, nDCG@k) calculadas a mano. Datos SINTÉTICOS."""
from __future__ import annotations

import json
import math

import pytest
from pydantic import ValidationError

from eval.retrieval import (
    ConsultaEtiquetada,
    cargar_consultas,
    dcg_at_k,
    evaluar,
    main,
    ndcg_at_k,
    recall_at_k,
)

from .conftest import FIXTURES
from .dobles import EmbedderFalso


def test_recall_a_mano():
    rel = {"b": 1, "c": 1, "d": 1}
    assert recall_at_k(["a", "b", "c"], rel, 3) == pytest.approx(2 / 3)
    assert recall_at_k(["a", "b", "c"], rel, 1) == 0.0
    assert recall_at_k(["d", "b", "c"], rel, 3) == 1.0
    assert recall_at_k(["d"], rel, 10) == pytest.approx(1 / 3)


def test_ndcg_a_mano():
    rel = {"b": 2, "c": 1, "d": 3}
    # DCG@3 = 0/log2(2) + 2/log2(3) + 1/log2(4) = 1.261860 + 0.5 = 1.761860
    assert dcg_at_k(["a", "b", "c"], rel, 3) == pytest.approx(2 / math.log2(3) + 0.5)
    # IDCG@3 = 3/1 + 2/log2(3) + 1/2 = 4.761860 → nDCG = 1.761860 / 4.761860 = 0.369994
    assert ndcg_at_k(["a", "b", "c"], rel, 3) == pytest.approx(0.369994, abs=1e-6)


def test_ndcg_perfecto_es_uno():
    rel = {"b": 2, "c": 1, "d": 3}
    assert ndcg_at_k(["d", "b", "c"], rel, 3) == pytest.approx(1.0)
    assert ndcg_at_k(["d", "b", "c", "x"], rel, 10) == pytest.approx(1.0)
    # con k menor que los relevantes, el ideal también se corta en k
    assert ndcg_at_k(["d"], rel, 1) == pytest.approx(1.0)
    assert ndcg_at_k(["b"], rel, 1) == pytest.approx(2 / 3)


def test_ndcg_sin_aciertos_es_cero():
    assert ndcg_at_k(["x", "y"], {"a": 1}, 2) == 0.0
    assert ndcg_at_k([], {"a": 1}, 2) == 0.0


def test_metricas_respetan_k():
    rel = {"a": 1}
    assert recall_at_k(["x", "a"], rel, 1) == 0.0 and recall_at_k(["x", "a"], rel, 2) == 1.0
    assert ndcg_at_k(["x", "a"], rel, 1) == 0.0
    assert ndcg_at_k(["x", "a"], rel, 2) == pytest.approx(1 / math.log2(3))


def test_duplicados_cuentan_una_vez():
    rel = {"a": 1, "b": 1}
    assert recall_at_k(["a", "a"], rel, 2) == 0.5
    assert ndcg_at_k(["a", "a", "b"], rel, 2) == pytest.approx(ndcg_at_k(["a", "b"], rel, 2))
    assert ndcg_at_k(["a", "a", "b"], rel, 2) == pytest.approx(1.0)


def test_sin_relevantes_es_error():
    for f in (recall_at_k, ndcg_at_k):
        with pytest.raises(ValueError):
            f(["a"], {}, 3)
        with pytest.raises(ValueError):
            f(["a"], {"a": 0}, 3)
        with pytest.raises(ValueError):
            f(["a"], {"a": 1}, 0)
    with pytest.raises(ValidationError):
        ConsultaEtiquetada(id="q", consulta="x", relevantes={})


def test_grado_cero_no_es_relevante():
    rel = {"a": 0, "b": 1}
    assert recall_at_k(["a"], rel, 1) == 0.0
    assert ndcg_at_k(["a", "b"], rel, 2) == pytest.approx(1 / math.log2(3))


def test_consulta_acepta_lista_de_relevantes():
    q = ConsultaEtiquetada(id="q1", consulta="familiar", relevantes=["a", "b"])
    assert q.relevantes == {"a": 1, "b": 1} and q.perfil is None
    q = ConsultaEtiquetada(id="q2", consulta="x", relevantes={"a": 3},
                           perfil={"cantidad_dias": 1, "dia_inicio": "lun", "transporte": "auto", "personas": 2})
    assert q.perfil.personas == 2


def test_cargar_consultas(tmp_path):
    ruta = tmp_path / "consultas.jsonl"
    ruta.write_text('{"id": "q1", "consulta": "familiar", "relevantes": ["a"]}\n\n'
                    '{"id": "q2", "consulta": "chablis", "relevantes": {"b": 2}}\n', encoding="utf-8")
    qs = cargar_consultas(ruta)
    assert [q.id for q in qs] == ["q1", "q2"] and qs[1].relevantes == {"b": 2}


def test_evaluar_promedia():
    qs = [ConsultaEtiquetada(id="q1", consulta="x", relevantes=["a", "b"]),
          ConsultaEtiquetada(id="q2", consulta="y", relevantes=["c"])]
    respuestas = {"q1": ["a", "z"], "q2": ["z", "c"]}
    pedidos = []

    def buscar(q, k):
        pedidos.append((q.id, k))
        return respuestas[q.id]

    r = evaluar(buscar, qs, k=2)
    assert pedidos == [("q1", 2), ("q2", 2)]
    assert r.k == 2 and r.n == 2
    assert [p.recall for p in r.por_consulta] == [0.5, 1.0]
    assert r.recall_medio == pytest.approx(0.75)
    assert r.ndcg_medio == pytest.approx((1 / (1 + 1 / math.log2(3)) + 1 / math.log2(3)) / 2)
    assert r.por_consulta[0].recuperados == ["a", "z"]
    with pytest.raises(ValueError):
        evaluar(buscar, [], k=2)


def test_main_escribe_el_reporte(tmp_path, monkeypatch, capsys):
    from corpus import config

    monkeypatch.setattr(config, "FICHAS_JSONL", FIXTURES / "fichas_sinteticas.jsonl")
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "reports")
    consultas = tmp_path / "consultas.jsonl"
    consultas.write_text(json.dumps({"id": "q1", "consulta": "Pommard", "relevantes": ["sint-pommard"]}) + "\n",
                         encoding="utf-8")
    assert main([str(consultas), "--k", "3"], embedder=EmbedderFalso()) == 0
    [reporte] = list((tmp_path / "reports").glob("retrieval_*.json"))
    datos = json.loads(reporte.read_text(encoding="utf-8"))
    assert datos["k"] == 3 and datos["n"] == 1 and datos["recall_medio"] == 1.0
    assert "recall@3" in capsys.readouterr().out


# --- casos encontrados con mutation testing ----------------------------------------------

def test_mensajes_de_error():
    with pytest.raises(ValueError, match="sin bodegas relevantes"):
        recall_at_k(["a"], {}, 1)
    with pytest.raises(ValueError, match="k tiene que ser"):
        ndcg_at_k(["a"], {"a": 1}, 0)
    with pytest.raises(ValueError, match="no hay consultas"):
        evaluar(lambda q, k: [], [])


def test_k_por_defecto_es_10():
    q = ConsultaEtiquetada(id="q", consulta="x", relevantes=["a"])
    vistos = []
    assert evaluar(lambda c, k: vistos.append(k) or ["a"], [q]).k == 10
    assert vistos == [10]


def test_main_usa_perfil_k_y_carpetas(tmp_path, monkeypatch):
    import enot.retrieval
    from corpus import config

    class _Real(EmbedderFalso):
        def __init__(self):
            super().__init__(nombre="real-falso")

    monkeypatch.setattr(enot.retrieval, "EmbedderOpenAI", _Real)   # el embedder por defecto, sin red
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "FICHAS_JSONL", FIXTURES / "fichas_sinteticas.jsonl")
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "a" / "reports")
    perfil = {"cantidad_dias": 1, "dia_inicio": "lun", "transporte": "auto", "personas": 2,
              "zonas_preferidas": ["Côte de Beaune"]}
    consultas = tmp_path / "consultas.jsonl"
    consultas.write_text(json.dumps({"id": "q1", "consulta": "Pommard", "perfil": perfil,
                                     "relevantes": ["sint-pommard"]}) + "\n", encoding="utf-8")
    assert main([str(consultas)]) == 0
    assert main([str(consultas), "--k", "1"]) == 0          # segunda corrida: la carpeta ya existe
    datos = json.loads(next((tmp_path / "a" / "reports").glob("retrieval_*.json")).read_text(encoding="utf-8"))
    assert datos["k"] == 1 and len(datos["por_consulta"][0]["recuperados"]) == 1
    assert (tmp_path / "data" / "indice" / "embeddings_real-falso.npy").exists()   # cacheó los embeddings
    from enot.corpus_local import cargar_corpus
    zonas = {b.id: b.zona for b in cargar_corpus(FIXTURES / "fichas_sinteticas.jsonl").values()}
    main([str(consultas), "--k", "10"])
    datos = json.loads(next((tmp_path / "a" / "reports").glob("retrieval_*.json")).read_text(encoding="utf-8"))
    assert datos["por_consulta"][0]["recuperados"]
    assert all(zonas[i] == "Côte de Beaune" for i in datos["por_consulta"][0]["recuperados"])  # usó el perfil
    assert len(datos["por_consulta"][0]["recuperados"]) < len(zonas)
