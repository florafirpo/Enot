"""Corre el benchmark sobre un split y guarda el reporte (spec 007, ADR-0007, ADR-0017).

Uso: python -m eval.correr --split dev|test [--sistemas B0,B1,B2,enot] [--limite N] [--fichas RUTA] [--set CARPETA]
     make eval SPLIT=dev SISTEMAS=B1

Escribe `reports/eval_<split>_<AAAA-MM-DD-HHMMSS>.json` con la configuración que lo produjo, las métricas por sistema,
la evaluación de cada consulta y lo que entregó cada sistema (tokens y latencia incluidos, para el ítem 008).
Solo crea el cliente LLM y el embedder si algún sistema pedido los necesita: `--sistemas B1` corre sin claves.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from corpus import config
from enot.corpus_local import cargar_corpus
from enot.flujo import K_CANDIDATAS, MAX_INTENTOS, TOPE_TOKENS
from enot.modelos import Bodega
from enot.retrieval import Indice
from eval.baselines import BaselineB0, BaselineB1, Sistema, crear_b2, crear_enot
from eval.generador import Consulta
from eval.metricas import EvaluacionConsulta, Metricas, SalidaSistema, resumir

__all__ = ["SISTEMAS", "SPLITS", "Reporte", "SetInexistente", "cargar_consultas", "escribir_reporte", "evaluar",
           "main"]

SPLITS = ("dev", "test")
SISTEMAS = ("B0", "B1", "B2", "enot")
CON_LLM = {"B0", "B2", "enot"}
CON_INDICE = {"B2", "enot"}


class SetInexistente(Exception):
    """Todavía no se generó el set de evaluación."""


def _carpeta_set(carpeta: Optional[Path]) -> Path:
    return Path(carpeta) if carpeta else config.DATA / "eval"


def cargar_consultas(split: str, carpeta: Optional[Path] = None) -> list[Consulta]:
    if split not in SPLITS:
        raise ValueError(f"split desconocido: {split!r} (opciones: {', '.join(SPLITS)})")
    ruta = _carpeta_set(carpeta) / split / "consultas.jsonl"
    if not ruta.exists():
        raise SetInexistente(f"no existe {ruta}: generá el set con `python -m eval.generador` (ver "
                             f"docs/feedback-flora.md, la decisión de congelar test es de Flora).")
    return [Consulta.model_validate_json(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()
            if linea.strip()]


class Reporte(BaseModel):
    split: str
    fecha: str
    configuracion: dict
    metricas: dict[str, Metricas]
    evaluaciones: dict[str, list[EvaluacionConsulta]]
    salidas: dict[str, list[SalidaSistema]]


def evaluar(sistemas: Sequence[Sistema], consultas: Sequence[Consulta], corpus: dict[str, Bodega], split: str,
            configuracion: Optional[dict] = None) -> Reporte:
    """Corre cada sistema sobre cada consulta. Una excepción en una consulta deja una salida `error` y sigue."""
    metricas, evaluaciones, salidas = {}, {}, {}
    for sistema in sistemas:
        propias = []
        for c in consultas:
            try:
                propias.append(sistema.correr(c))
            except Exception as e:  # noqa: BLE001 — un proveedor caído no tira la corrida entera
                propias.append(SalidaSistema(consulta_id=c.id, sistema=sistema.nombre, tipo="error",
                                             texto=f"{type(e).__name__}: {e}"[:500]))
        metricas[sistema.nombre], evaluaciones[sistema.nombre] = resumir(consultas, propias, corpus)
        salidas[sistema.nombre] = propias
    return Reporte(split=split, fecha=datetime.now().strftime("%Y-%m-%d-%H%M%S"), configuracion=configuracion or {},
                   metricas=metricas, evaluaciones=evaluaciones, salidas=salidas)


def escribir_reporte(reporte: Reporte, carpeta: Optional[Path] = None) -> Path:
    """`reports/eval_<split>_<fecha>.json`. Nunca pisa un reporte anterior: si ya existe, agrega `-2`, `-3`…"""
    carpeta = Path(carpeta) if carpeta else config.REPORTS_DIR
    carpeta.mkdir(parents=True, exist_ok=True)
    base = f"eval_{reporte.split}_{reporte.fecha}"
    ruta, n = carpeta / f"{base}.json", 1
    while ruta.exists():
        n += 1
        ruta = carpeta / f"{base}-{n}.json"
    ruta.write_text(reporte.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return ruta


def _commit() -> Optional[str]:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False)
    except OSError:  # pragma: no cover - sin git instalado
        return None
    return r.stdout.strip() or None


def _version_generador(carpeta: Path) -> Optional[str]:
    ruta = carpeta / "generacion.json"
    if not ruta.exists():
        return None
    return json.loads(ruta.read_text(encoding="utf-8")).get("version")


def _cliente_llm():  # pragma: no cover - necesita clave; en tests se inyecta una fábrica
    from corpus.llm import ClienteLLM
    return ClienteLLM()


def _embedder():  # pragma: no cover - necesita clave o caché; en tests se inyecta una fábrica
    from enot.retrieval import EmbedderConCache, EmbedderOpenAI
    return EmbedderConCache(EmbedderOpenAI())


def main(argv: Optional[list[str]] = None, crear_cliente: Optional[Callable[[], object]] = None,
         crear_embedder: Optional[Callable[[], object]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m eval.correr", description=__doc__.splitlines()[0])
    ap.add_argument("--split", choices=SPLITS, default="dev")
    ap.add_argument("--sistemas", default=",".join(SISTEMAS), help=f"separados por coma ({', '.join(SISTEMAS)})")
    ap.add_argument("--limite", type=int, default=None, help="solo las primeras N consultas (pruebas)")
    ap.add_argument("--fichas", type=Path, default=None, help="corpus (por defecto data/fichas/fichas.jsonl)")
    ap.add_argument("--set", dest="carpeta_set", type=Path, default=None, help="carpeta del set (data/eval)")
    args = ap.parse_args(argv)

    pedidos = [s.strip() for s in args.sistemas.split(",") if s.strip()]
    desconocidos = [s for s in pedidos if s not in SISTEMAS]
    if desconocidos or not pedidos:
        print(f"[eval] sistemas desconocidos: {', '.join(desconocidos) or '(ninguno pedido)'} "
              f"(opciones: {', '.join(SISTEMAS)})", file=sys.stderr)
        return 1
    carpeta_set = _carpeta_set(args.carpeta_set)
    try:
        consultas = cargar_consultas(args.split, carpeta_set)
    except SetInexistente as e:
        print(f"[eval] {e}", file=sys.stderr)
        return 1
    if args.limite is not None:
        consultas = consultas[:args.limite]
    ruta_fichas = args.fichas or config.FICHAS_JSONL
    if not Path(ruta_fichas).exists():
        print(f"[eval] no existe el corpus de fichas {ruta_fichas} (`make extract`).", file=sys.stderr)
        return 1
    corpus = cargar_corpus(ruta_fichas)

    cliente = (crear_cliente or _cliente_llm)() if CON_LLM & set(pedidos) else None
    indice = Indice(list(corpus.values()), (crear_embedder or _embedder)()) if CON_INDICE & set(pedidos) else None
    trazas = config.DATA / "trazas" / f"eval-{args.split}-{datetime.now():%Y%m%d-%H%M%S}"
    fabricas = {"B0": lambda: BaselineB0(cliente, corpus), "B1": lambda: BaselineB1(corpus),
                "B2": lambda: crear_b2(cliente, corpus, indice, trazas / "B2"),
                "enot": lambda: crear_enot(cliente, corpus, indice, trazas / "enot")}
    sistemas = [fabricas[s]() for s in pedidos]
    configuracion = {
        "split": args.split, "sistemas": pedidos, "consultas": len(consultas), "limite": args.limite,
        "version_generador": _version_generador(carpeta_set), "bodegas_corpus": len(corpus),
        "fichas": str(ruta_fichas), "commit": _commit(),
        "proveedor": getattr(cliente, "provider", None), "modelo": getattr(cliente, "model", None),
        "embeddings": getattr(getattr(indice, "embedder", None), "nombre", None),
        "max_intentos": MAX_INTENTOS, "tope_tokens": TOPE_TOKENS, "k_candidatas": K_CANDIDATAS,
        "trazas": str(trazas) if CON_INDICE & set(pedidos) else None,
    }
    reporte = evaluar(sistemas, consultas, corpus, args.split, configuracion)
    ruta = escribir_reporte(reporte)
    print(f"[eval] {len(consultas)} consultas de {args.split}, sistemas {', '.join(pedidos)} → {ruta}")
    for nombre, m in reporte.metricas.items():
        print(f"  {nombre}: hard pass {m.hard_pass_rate}, alucinación {m.tasa_alucinacion}, "
              f"cobertura {m.cobertura_corpus:.2f}, infactibles detectados {m.infactibles_detectados}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
