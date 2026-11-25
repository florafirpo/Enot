"""Calibración del juez contra la anotación humana: Spearman y kappa (spec 008, ADR-0007, ADR-0018).

ADR-0007: el juez LLM se calibra contra 30 casos anotados a mano; si el acuerdo es bajo, se reporta y el preference
score no se usa como evidencia fuerte. Este módulo arma la planilla que anota Flora (solo con casos de **dev**: calibrar
mirando test sería ajustar la vara al examen), la lee y calcula el acuerdo.

- `spearman`: correlación de rangos (rango promedio en los empates). Mide si el juez **ordena** igual que el humano.
- `kappa`: Cohen sobre las categorías 1–5 fijas, sin ponderar y ponderado cuadrático. Mide si **puntúa** igual,
  descontando el acuerdo por azar. El cuadrático castiga más un 1 contra un 5 que un 4 contra un 5 (escala ordinal).
- Apto si hay al menos `MINIMO_CASOS` pares, Spearman ≥ `UMBRAL_SPEARMAN` y kappa cuadrático ≥ `UMBRAL_KAPPA`.

Uso: python -m eval.calibrar planilla reports/eval_dev_<fecha>.json [--n 30] [--destino data/eval/anotacion_humana.csv]
     python -m eval.calibrar calibrar reports/juez_dev_<fecha>.json [--anotaciones data/eval/anotacion_humana.csv]
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

from corpus import config
from enot.modelos import Bodega
from eval.correr import Reporte
from eval.generador import Consulta
from eval.juez import Juicios, cargar_entradas, escribir_sin_pisar, juzgable, texto_itinerario

__all__ = ["COLUMNAS_PLANILLA", "MINIMO_CASOS", "PUNTAJES", "UMBRAL_KAPPA", "UMBRAL_SPEARMAN", "Anotacion",
           "Calibracion", "armar_planilla", "calibrar", "escribir_planilla", "kappa", "leer_anotaciones", "main",
           "rangos", "spearman"]

PUNTAJES = (1, 2, 3, 4, 5)
UMBRAL_SPEARMAN = 0.6       # acuerdo "sustancial" (Landis y Koch: 0,61–0,80)
UMBRAL_KAPPA = 0.6
MINIMO_CASOS = 30           # PRD 6
COLUMNAS_PLANILLA = ("consulta_id", "sistema", "pedido", "itinerario", "puntaje_humano", "comentario")


# --- estadísticos -------------------------------------------------------------------------------------------------

def rangos(valores: Sequence[float]) -> list[float]:
    """Rango de cada valor (desde 1); los empatados reciben el promedio de los rangos que ocupan."""
    orden = sorted(range(len(valores)), key=lambda i: valores[i])
    r = [0.0] * len(valores)
    i = 0
    while i < len(orden):
        j = i
        while j + 1 < len(orden) and valores[orden[j + 1]] == valores[orden[i]]:
            j += 1
        promedio = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[orden[k]] = promedio
        i = j + 1
    return r


def spearman(x: Sequence[float], y: Sequence[float]) -> Optional[float]:
    """Pearson de los rangos. None con menos de 3 pares o si una serie es constante (no está definida)."""
    if len(x) != len(y):
        raise ValueError(f"series de largo distinto: {len(x)} y {len(y)}")
    if len(x) < 3:
        return None
    rx, ry = rangos(x), rangos(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    vx, vy = sum((a - mx) ** 2 for a in rx), sum((b - my) ** 2 for b in ry)
    if vx == 0 or vy == 0:
        return None
    return cov / math.sqrt(vx * vy)


def kappa(a: Sequence[int], b: Sequence[int],
          ponderacion: Literal["ninguna", "cuadratica"] = "ninguna") -> Optional[float]:
    """Kappa de Cohen sobre `PUNTAJES`: 1 − Σ w·O / Σ w·E, con w = 1 si difieren (sin ponderar) o
    w = (i − j)² / (k − 1)² (cuadrático). None si no hay pares o si el desacuerdo esperado es 0."""
    if len(a) != len(b):
        raise ValueError(f"series de largo distinto: {len(a)} y {len(b)}")
    if ponderacion not in ("ninguna", "cuadratica"):
        raise ValueError(f"ponderación desconocida: {ponderacion!r}")
    fuera = [v for v in (*a, *b) if v not in PUNTAJES]
    if fuera:
        raise ValueError(f"puntajes fuera de la escala 1–5: {fuera}")
    n = len(a)
    if n == 0:
        return None
    k = len(PUNTAJES)

    def peso(i: int, j: int) -> float:
        if ponderacion == "cuadratica":
            return (i - j) ** 2 / (k - 1) ** 2
        return 0.0 if i == j else 1.0

    observado = sum(peso(x, y) for x, y in zip(a, b, strict=True)) / n
    pa = {c: a.count(c) / n for c in PUNTAJES}
    pb = {c: b.count(c) / n for c in PUNTAJES}
    esperado = sum(peso(i, j) * pa[i] * pb[j] for i in PUNTAJES for j in PUNTAJES)
    if esperado == 0:
        return None
    return 1 - observado / esperado


# --- anotación humana ----------------------------------------------------------------------------------------------

class Anotacion(BaseModel):
    consulta_id: str
    sistema: str
    puntaje_humano: Optional[int] = Field(None, ge=1, le=5, description="Vacío = todavía sin anotar")


def armar_planilla(reporte: Reporte, consultas: Sequence[Consulta], corpus: dict[str, Bodega], n: int = MINIMO_CASOS,
                   semilla: int = 2026) -> list[dict]:
    """`n` casos juzgables repartidos por sistema (ronda sobre los sistemas, cada uno barajado con la semilla).

    Cada fila trae lo mismo que ve el juez (pedido e itinerario con datos del corpus) y no trae su puntaje ni el
    nombre del sistema dentro del texto: la anotación es a ciegas. Si hay menos de `n` juzgables, van todos.
    """
    if reporte.split != "dev":
        raise ValueError(f"la planilla de calibración sale de dev, no de {reporte.split!r}: calibrar mirando test "
                         "sería ajustar la vara al examen")
    por_id = {c.id: c for c in consultas}
    rng = random.Random(semilla)
    colas: dict[str, list[tuple[Consulta, object]]] = {}
    for sistema in sorted(reporte.salidas):
        cola = [(por_id[s.consulta_id], s) for s in reporte.salidas[sistema]
                if s.consulta_id in por_id and juzgable(por_id[s.consulta_id], s)]
        rng.shuffle(cola)
        colas[sistema] = cola
    elegidos = []
    while len(elegidos) < n and any(colas.values()):
        for sistema in sorted(colas):
            if colas[sistema] and len(elegidos) < n:
                elegidos.append(colas[sistema].pop())
    rng.shuffle(elegidos)   # el orden de la planilla no delata el sistema
    return [{"consulta_id": c.id, "sistema": s.sistema,
             "pedido": f"{c.texto}\nPreferencias: {c.restricciones.preferencias}",
             "itinerario": texto_itinerario(s.itinerario, corpus), "puntaje_humano": "", "comentario": ""}
            for c, s in elegidos]


def escribir_planilla(filas: Sequence[dict], ruta: Path) -> Path:
    """Escribe el CSV. Nunca pisa uno existente: puede tener la anotación de Flora."""
    ruta = Path(ruta)
    if ruta.exists():
        raise FileExistsError(f"ya existe {ruta}: no se pisa una planilla que puede estar anotada")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("x", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS_PLANILLA)
        w.writeheader()
        w.writerows(filas)
    return ruta


def leer_anotaciones(ruta: Path) -> list[Anotacion]:
    """Lee la planilla. Un puntaje vacío es "sin anotar"; uno que no sea un entero de 1 a 5 es un error."""
    anotaciones = []
    with Path(ruta).open(encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            crudo = (fila.get("puntaje_humano") or "").strip()
            if crudo and crudo not in {str(p) for p in PUNTAJES}:
                raise ValueError(f"puntaje_humano inválido para {fila['consulta_id']}/{fila['sistema']}: {crudo!r} "
                                 "(tiene que ser un entero de 1 a 5, o vacío)")
            anotaciones.append(Anotacion(consulta_id=fila["consulta_id"], sistema=fila["sistema"],
                                         puntaje_humano=int(crudo) if crudo else None))
    return anotaciones


# --- calibración ---------------------------------------------------------------------------------------------------

class Calibracion(BaseModel):
    pares: int
    sin_anotar: int
    sin_juicio: int = Field(description="Anotados sin juicio ok del juez (no juzgado o juicio en error)")
    spearman: Optional[float]
    kappa: Optional[float]
    kappa_cuadratico: Optional[float]
    apto: bool
    motivo: str


def _motivo(pares: int, rho: Optional[float], kq: Optional[float]) -> tuple[bool, str]:
    problemas = []
    if pares < MINIMO_CASOS:
        problemas.append(f"{pares} pares < {MINIMO_CASOS}")
    if rho is None or rho < UMBRAL_SPEARMAN:
        problemas.append(f"Spearman {'s/d' if rho is None else f'{rho:.2f}'} < {UMBRAL_SPEARMAN}")
    if kq is None or kq < UMBRAL_KAPPA:
        problemas.append(f"kappa cuadrático {'s/d' if kq is None else f'{kq:.2f}'} < {UMBRAL_KAPPA}")
    if problemas:
        return False, "; ".join(problemas)
    return True, f"{pares} pares, Spearman {rho:.2f} y kappa cuadrático {kq:.2f} sobre los umbrales"


def calibrar(anotaciones: Sequence[Anotacion], juicios: Juicios) -> Calibracion:
    """Une anotación y juicio por (consulta, sistema) y calcula el acuerdo."""
    del_juez = {(j.consulta_id, j.sistema): j.puntaje for j in juicios.juicios if j.estado == "ok"}
    humanos, juez = [], []
    sin_anotar = sin_juicio = 0
    for a in anotaciones:
        if a.puntaje_humano is None:
            sin_anotar += 1
            continue
        p = del_juez.get((a.consulta_id, a.sistema))
        if p is None:
            sin_juicio += 1
            continue
        humanos.append(a.puntaje_humano)
        juez.append(p)
    rho = spearman(humanos, juez)
    kq = kappa(humanos, juez, "cuadratica")
    apto, motivo = _motivo(len(humanos), rho, kq)
    return Calibracion(pares=len(humanos), sin_anotar=sin_anotar, sin_juicio=sin_juicio, spearman=rho,
                       kappa=kappa(humanos, juez), kappa_cuadratico=kq, apto=apto, motivo=motivo)


# --- CLI -----------------------------------------------------------------------------------------------------------

def _ruta_planilla(carpeta_set: Optional[Path]) -> Path:
    return (Path(carpeta_set) if carpeta_set else config.DATA / "eval") / "anotacion_humana.csv"


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m eval.calibrar", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="comando", required=True)
    pl = sub.add_parser("planilla", help="arma la planilla para anotar a mano (solo dev)")
    pl.add_argument("reporte", type=Path)
    pl.add_argument("--n", type=int, default=MINIMO_CASOS)
    pl.add_argument("--semilla", type=int, default=2026)
    pl.add_argument("--set", dest="carpeta_set", type=Path, default=None)
    pl.add_argument("--fichas", type=Path, default=None)
    pl.add_argument("--destino", type=Path, default=None, help="por defecto data/eval/anotacion_humana.csv")
    ca = sub.add_parser("calibrar", help="Spearman y kappa entre la planilla anotada y los juicios")
    ca.add_argument("juicios", type=Path, help="reports/juez_dev_<fecha>.json")
    ca.add_argument("--anotaciones", type=Path, default=None, help="por defecto data/eval/anotacion_humana.csv")
    args = ap.parse_args(argv)

    try:
        if args.comando == "planilla":
            reporte, consultas, corpus = cargar_entradas(args.reporte, args.carpeta_set, args.fichas)
            filas = armar_planilla(reporte, consultas, corpus, n=args.n, semilla=args.semilla)
            ruta = escribir_planilla(filas, args.destino or _ruta_planilla(args.carpeta_set))
            print(f"[calibrar] planilla con {len(filas)} casos → {ruta}. Completá `puntaje_humano` (1 a 5).")
            return 0
        juicios = Juicios.model_validate_json(Path(args.juicios).read_text(encoding="utf-8"))
        anotaciones = leer_anotaciones(args.anotaciones or _ruta_planilla(None))
    except Exception as e:  # noqa: BLE001 — archivo faltante, planilla existente o mal anotada: mensaje y código 1
        print(f"[calibrar] {e}", file=sys.stderr)
        return 1
    c = calibrar(anotaciones, juicios)
    ruta = escribir_sin_pisar(c.model_dump_json(indent=2) + "\n", config.REPORTS_DIR,
                              f"calibracion_{datetime.now():%Y-%m-%d-%H%M%S}")
    print(f"[calibrar] {c.pares} pares · Spearman {c.spearman} · kappa {c.kappa} · kappa cuadrático "
          f"{c.kappa_cuadratico} · {'apto' if c.apto else 'NO apto'} ({c.motivo}) → {ruta}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
