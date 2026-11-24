"""Evaluación del retrieval por separado (spec 003, ADR-0004; lineamientos D.5).

Recall@k (¿cuánto de lo relevante trajo?) y nDCG@k (¿lo trajo arriba?) contra consultas con bodegas relevantes
etiquetadas. nDCG con ganancia lineal: grado / log2(puesto + 1); con relevancia binaria coincide con la exponencial.

Uso: python -m eval.retrieval <consultas.jsonl> [--k 10]
Cada línea: {"id": "q1", "consulta": "...", "perfil": {...} | null, "relevantes": ["id", ...] | {"id": grado}}
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, field_validator

from corpus import config
from enot.modelos import PerfilViaje

__all__ = ["ConsultaEtiquetada", "ResultadoConsulta", "ResultadoEval", "cargar_consultas", "dcg_at_k", "evaluar",
           "main", "ndcg_at_k", "recall_at_k"]


class ConsultaEtiquetada(BaseModel):
    id: str
    consulta: str
    perfil: Optional[PerfilViaje] = None
    relevantes: dict[str, int]

    @field_validator("relevantes", mode="before")
    @classmethod
    def _lista_a_grados(cls, v):
        return {x: 1 for x in v} if isinstance(v, list) else v

    @field_validator("relevantes")
    @classmethod
    def _al_menos_uno(cls, v):
        if not any(g > 0 for g in v.values()):
            raise ValueError("la consulta necesita al menos una bodega relevante (grado > 0)")
        return v


def _validar(relevantes: dict[str, int], k: int) -> None:
    if k < 1:
        raise ValueError(f"k tiene que ser ≥ 1 (vino {k})")
    if not any(g > 0 for g in relevantes.values()):
        raise ValueError("sin bodegas relevantes la métrica no está definida")


def _top(recuperados: list[str], k: int) -> list[str]:
    """Los primeros k distintos: un duplicado no cuenta dos veces."""
    return list(dict.fromkeys(recuperados))[:k]


def recall_at_k(recuperados: list[str], relevantes: dict[str, int], k: int) -> float:
    _validar(relevantes, k)
    rel = {d for d, g in relevantes.items() if g > 0}
    return len(rel & set(_top(recuperados, k))) / len(rel)


def dcg_at_k(recuperados: list[str], relevantes: dict[str, int], k: int) -> float:
    return sum(max(relevantes.get(d, 0), 0) / math.log2(i + 1) for i, d in enumerate(_top(recuperados, k), start=1))


def ndcg_at_k(recuperados: list[str], relevantes: dict[str, int], k: int) -> float:
    _validar(relevantes, k)
    ideal = sorted((g for g in relevantes.values() if g > 0), reverse=True)[:k]
    idcg = sum(g / math.log2(i + 1) for i, g in enumerate(ideal, start=1))
    return dcg_at_k(recuperados, relevantes, k) / idcg


def cargar_consultas(ruta: Path) -> list[ConsultaEtiquetada]:
    lineas = Path(ruta).read_text(encoding="utf-8").splitlines()
    return [ConsultaEtiquetada.model_validate_json(linea) for linea in lineas if linea.strip()]


class ResultadoConsulta(BaseModel):
    id: str
    recall: float
    ndcg: float
    recuperados: list[str]


class ResultadoEval(BaseModel):
    k: int
    n: int
    recall_medio: float
    ndcg_medio: float
    por_consulta: list[ResultadoConsulta]


def evaluar(buscar: Callable[[ConsultaEtiquetada, int], list[str]], consultas: list[ConsultaEtiquetada],
            k: int = 10) -> ResultadoEval:
    """Corre `buscar(consulta, k)` para cada consulta y promedia las métricas."""
    if not consultas:
        raise ValueError("no hay consultas para evaluar")
    filas = []
    for q in consultas:
        rec = list(buscar(q, k))
        filas.append(ResultadoConsulta(id=q.id, recall=recall_at_k(rec, q.relevantes, k),
                                       ndcg=ndcg_at_k(rec, q.relevantes, k), recuperados=rec))
    n = len(filas)
    return ResultadoEval(k=k, n=n, recall_medio=sum(f.recall for f in filas) / n,
                         ndcg_medio=sum(f.ndcg for f in filas) / n, por_consulta=filas)


def main(argv: Optional[list[str]] = None, embedder=None) -> int:
    """Evalúa el índice híbrido sobre el corpus (`fichas.jsonl`) y deja el reporte en reports/."""
    from enot.corpus_local import cargar_corpus
    from enot.retrieval import EmbedderConCache, EmbedderOpenAI, Indice

    ap = argparse.ArgumentParser(prog="python -m eval.retrieval")
    ap.add_argument("consultas", type=Path)
    ap.add_argument("--k", type=int, default=10)
    args = ap.parse_args(argv)

    embedder = embedder or EmbedderConCache(EmbedderOpenAI())
    indice = Indice(cargar_corpus().values(), embedder)
    r = evaluar(lambda q, k: [c.bodega_id for c in indice.buscar(q.perfil, k=k, consulta=q.consulta)],
                cargar_consultas(args.consultas), k=args.k)
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    salida = config.REPORTS_DIR / f"retrieval_{config.HOY}.json"
    salida.write_text(json.dumps(r.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{r.n} consultas · recall@{r.k} = {r.recall_medio:.3f} · ndcg@{r.k} = {r.ndcg_medio:.3f} → {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
