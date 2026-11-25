"""Reporte final del benchmark: métricas, preference score, costo y latencia por sistema (spec 008, PRD 6 y 9, ADR-0018).

Lee un reporte de `make eval` (`reports/eval_<split>_<fecha>.json`) y, si están, los juicios del juez, la calibración y
una tabla de precios; escribe `reports/resultados.md`. No vuelve a correr ningún sistema.

- **Costo por consulta** (un turno), desde la traza de cada consulta (Enot, B2): C = Σ t_in·p_in + t_out·p_out con el
  precio del modelo de cada llamada (PRD 9). B0 no tiene traza: sus tokens vienen de la salida. B1 no usa LLM: 0.
- **Nunca un 0 inventado**: una llamada fallida sin tokens se cuenta (`llamadas_sin_tokens`) y deja esa consulta sin
  costo; un modelo sin precio deja el costo en USD sin dato. Media y p95 se calculan sobre las consultas con costo
  completo, y se dice sobre cuántas.
- **Latencia** de punta a punta por consulta (medida por `eval.correr`), sin las salidas `error`, que no la miden.
- **p95 por rango más cercano**: el valor observado en la posición ceil(0,95·n) de la lista ordenada.
- Los precios no están en el repo (cambian y no se pueden verificar offline): se pasan con `--precios`, un JSON
  `{"<modelo>": {"entrada_usd_por_millon": x, "salida_usd_por_millon": y}}`.

Uso: python -m eval.reporte reports/eval_test_<fecha>.json [--juicios reports/juez_….json]
       [--calibracion reports/calibracion_….json] [--precios precios.json] [--salida reports/resultados.md]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError

from corpus import config
from enot.trazas import EventoTraza, Traza
from eval.calibrar import Calibracion
from eval.correr import CON_LLM, Reporte
from eval.juez import Juicios
from eval.metricas import SalidaSistema

__all__ = ["CONSULTAS_POR_MES", "CostoConsulta", "FilaSistema", "Precio", "cargar_precios", "costo_consulta",
           "filas_sistemas", "main", "media", "percentil_95", "render_markdown"]

CONSULTAS_POR_MES = 1000    # volumen hipotético para la proyección mensual (PRD 9)


class Precio(BaseModel):
    entrada_usd_por_millon: float = Field(ge=0)
    salida_usd_por_millon: float = Field(ge=0)


def cargar_precios(ruta: Path) -> dict[str, Precio]:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    try:
        return {modelo: Precio.model_validate(p) for modelo, p in datos.items()}
    except ValidationError as e:
        raise ValueError(f"tabla de precios inválida en {ruta}: {e}") from e


def media(valores: Sequence[float]) -> Optional[float]:
    return sum(valores) / len(valores) if valores else None


def percentil_95(valores: Sequence[float]) -> Optional[float]:
    if not valores:
        return None
    ordenados = sorted(valores)
    return ordenados[math.ceil(0.95 * len(ordenados)) - 1]


# --- costo por consulta --------------------------------------------------------------------------------------------

class CostoConsulta(BaseModel):
    consulta_id: str
    llamadas: Optional[int] = Field(description="None si el sistema no tiene traza (B0)")
    fallidas: Optional[int]
    sin_tokens: int = Field(description="Llamadas (o salidas, sin traza) cuyos tokens no se conocen")
    tokens_in: Optional[int] = Field(description="Suma de los tokens conocidos")
    tokens_out: Optional[int]
    usd: Optional[float] = Field(description="None si falta algún token o el precio de algún modelo")

    @property
    def completo(self) -> bool:
        return self.sin_tokens == 0 and self.tokens_in is not None and self.tokens_out is not None


def _usd(tin: int, tout: int, modelo: Optional[str], precios: dict[str, Precio]) -> Optional[float]:
    p = precios.get(modelo) if modelo else None
    if p is None:
        return None
    return (tin * p.entrada_usd_por_millon + tout * p.salida_usd_por_millon) / 1_000_000


def costo_consulta(salida: SalidaSistema, eventos: Optional[list[EventoTraza]], con_llm: bool, modelo: Optional[str],
                   precios: dict[str, Precio]) -> CostoConsulta:
    """Costo de una consulta. `eventos` = la traza de esa consulta, o None si el sistema no tiene traza."""
    cid = salida.consulta_id
    if not con_llm:
        return CostoConsulta(consulta_id=cid, llamadas=0, fallidas=0, sin_tokens=0, tokens_in=0, tokens_out=0, usd=0.0)
    if eventos is None:
        if salida.tokens_in is None or salida.tokens_out is None:
            return CostoConsulta(consulta_id=cid, llamadas=None, fallidas=None, sin_tokens=1, tokens_in=None,
                                 tokens_out=None, usd=None)
        return CostoConsulta(consulta_id=cid, llamadas=None, fallidas=None, sin_tokens=0, tokens_in=salida.tokens_in,
                             tokens_out=salida.tokens_out,
                             usd=_usd(salida.tokens_in, salida.tokens_out, modelo, precios))
    conocidos = [e for e in eventos if e.tokens_in is not None and e.tokens_out is not None]
    sin_tokens = len(eventos) - len(conocidos)
    usd: Optional[float] = 0.0
    for e in conocidos:
        parcial = _usd(e.tokens_in, e.tokens_out, e.modelo, precios)
        usd = None if parcial is None or usd is None else usd + parcial
    return CostoConsulta(consulta_id=cid, llamadas=len(eventos), fallidas=sum(e.estado == "error" for e in eventos),
                         sin_tokens=sin_tokens, tokens_in=sum(e.tokens_in for e in conocidos),
                         tokens_out=sum(e.tokens_out for e in conocidos), usd=None if sin_tokens else usd)


# --- tabla por sistema ---------------------------------------------------------------------------------------------

class FilaSistema(BaseModel):
    sistema: str
    hard_pass_rate: Optional[float]
    tasa_alucinacion: Optional[float]
    cobertura_corpus: float
    gini: Optional[float]
    infactibles_detectados: Optional[float]
    preferencia_media: Optional[float]
    preferencia_media_hard_pass: Optional[float] = Field(description="Solo consultas con hard pass ('a igual "
                                                                     "factibilidad', H2)")
    juicios: int
    juicios_error: int
    consultas: int
    consultas_con_costo: int
    tokens_medios: Optional[float]
    usd_medio: Optional[float]
    usd_p95: Optional[float]
    latencia_media: Optional[float]
    latencia_p95: Optional[float]
    intentos_medios: Optional[float]
    llamadas: Optional[int]
    llamadas_fallidas: Optional[int]
    llamadas_sin_tokens: int
    salidas_error: int


def _leer_eventos(ruta: str) -> list[EventoTraza]:
    return Traza(Path(ruta)).eventos()


def _suma_opcional(valores: list[Optional[int]]) -> Optional[int]:
    return None if any(v is None for v in valores) else sum(valores)


def filas_sistemas(reporte: Reporte, juicios: Optional[Juicios] = None, precios: Optional[dict[str, Precio]] = None,
                   leer_eventos: Callable[[str], list[EventoTraza]] = _leer_eventos) -> list[FilaSistema]:
    precios = precios or {}
    modelo = reporte.configuracion.get("modelo")
    filas = []
    for sistema, salidas in reporte.salidas.items():
        m = reporte.metricas[sistema]
        hard_pass = {e.consulta_id: e.hard_pass for e in reporte.evaluaciones.get(sistema, [])}
        propios = [j for j in (juicios.juicios if juicios else []) if j.sistema == sistema]
        ok = [j for j in propios if j.estado == "ok"]
        con_llm = sistema in CON_LLM
        costos = [costo_consulta(s, leer_eventos(s.traza) if s.traza else None, con_llm, modelo, precios)
                  for s in salidas]
        completos = [c for c in costos if c.completo]
        usd = [c.usd for c in completos if c.usd is not None]
        medidas = [s for s in salidas if s.tipo != "error"]
        intentos = [s.intentos for s in medidas if s.intentos > 0]
        filas.append(FilaSistema(
            sistema=sistema, hard_pass_rate=m.hard_pass_rate, tasa_alucinacion=m.tasa_alucinacion,
            cobertura_corpus=m.cobertura_corpus, gini=m.gini, infactibles_detectados=m.infactibles_detectados,
            preferencia_media=media([j.puntaje for j in ok]),
            preferencia_media_hard_pass=media([j.puntaje for j in ok if hard_pass.get(j.consulta_id) is True]),
            juicios=len(ok), juicios_error=len(propios) - len(ok),
            consultas=len(salidas), consultas_con_costo=len(usd),
            tokens_medios=media([c.tokens_in + c.tokens_out for c in completos]),
            usd_medio=media(usd), usd_p95=percentil_95(usd),
            latencia_media=media([s.latencia_s for s in medidas]),
            latencia_p95=percentil_95([s.latencia_s for s in medidas]),
            intentos_medios=media(intentos),
            llamadas=_suma_opcional([c.llamadas for c in costos]),
            llamadas_fallidas=_suma_opcional([c.fallidas for c in costos]),
            llamadas_sin_tokens=sum(c.sin_tokens for c in costos if c.llamadas is not None),
            salidas_error=len(salidas) - len(medidas)))
    return filas


# --- Markdown ------------------------------------------------------------------------------------------------------

def _pct(v: Optional[float]) -> str:
    return "s/d" if v is None else f"{100 * v:.1f}%"


def _num(v: Optional[float], decimales: int = 2) -> str:
    return "s/d" if v is None else f"{v:.{decimales}f}"


def _ent(v: Optional[int]) -> str:
    return "s/d" if v is None else str(v)


def render_markdown(reporte: Reporte, filas: Sequence[FilaSistema], origen: str,
                    calibracion: Optional[Calibracion] = None, precios_cargados: bool = False) -> str:
    cfg = reporte.configuracion
    lineas = [
        f"# Resultados del benchmark · split {reporte.split}",
        "",
        f"Generado por `python -m eval.reporte` desde `{origen}` (corrida {reporte.fecha}, commit "
        f"`{cfg.get('commit') or 's/d'}`, modelo `{cfg.get('modelo') or 's/d'}`, "
        f"{cfg.get('consultas', 's/d')} consultas, corpus de {cfg.get('bodegas_corpus', 's/d')} bodegas).",
        "",
        "## Calidad",
        "",
        "| Sistema | Hard pass | Alucinación | Cobertura | Gini | Infactibles detectados | Preferencia (1–5) | "
        "Preferencia con hard pass | Juicios (error) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for f in filas:
        lineas.append(f"| {f.sistema} | {_pct(f.hard_pass_rate)} | {_pct(f.tasa_alucinacion)} | "
                      f"{_pct(f.cobertura_corpus)} | {_num(f.gini)} | {_pct(f.infactibles_detectados)} | "
                      f"{_num(f.preferencia_media)} | {_num(f.preferencia_media_hard_pass)} | "
                      f"{f.juicios} ({f.juicios_error}) |")
    lineas += ["", "### Juez del preference score", ""]
    if calibracion is None:
        lineas.append("Juez **sin calibrar** contra la anotación humana: el preference score no es evidencia fuerte "
                      "(ADR-0007). Calibrar con `python -m eval.calibrar`.")
    else:
        lineas.append(f"Calibración sobre {calibracion.pares} pares: Spearman {_num(calibracion.spearman)}, kappa "
                      f"{_num(calibracion.kappa)}, kappa cuadrático {_num(calibracion.kappa_cuadratico)}.")
        if calibracion.apto:
            lineas.append(f"Apto: {calibracion.motivo}.")
        else:
            lineas.append(f"**El juez no es apto** ({calibracion.motivo}): el preference score se reporta, pero no es "
                          "evidencia fuerte (ADR-0007).")
    lineas += [
        "",
        "## Costo y latencia (por consulta)",
        "",
        "| Sistema | Consultas con costo | Tokens medios | USD medio | USD p95 | Latencia media (s) | Latencia p95 (s) | "
        "Intentos medios | Llamadas (fallidas, sin tokens) | Salidas error |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for f in filas:
        llamadas = ("s/t" if f.llamadas is None
                    else f"{f.llamadas} ({_ent(f.llamadas_fallidas)}, {f.llamadas_sin_tokens})")
        lineas.append(f"| {f.sistema} | {f.consultas_con_costo}/{f.consultas} | {_num(f.tokens_medios, 0)} | "
                      f"{_num(f.usd_medio, 4)} | {_num(f.usd_p95, 4)} | {_num(f.latencia_media)} | "
                      f"{_num(f.latencia_p95)} | {_num(f.intentos_medios)} | {llamadas} | {f.salidas_error} |")
    lineas += [""]
    if not precios_cargados:
        lineas.append("Sin tabla de precios: USD queda s/d. Pasala con `--precios precios.json` "
                      "(`{\"<modelo>\": {\"entrada_usd_por_millon\": x, \"salida_usd_por_millon\": y}}`).")
    proyeccion = [f"{f.sistema} {f.usd_medio * CONSULTAS_POR_MES:.2f} USD" for f in filas if f.usd_medio is not None]
    if proyeccion:
        lineas.append(f"Proyección a {CONSULTAS_POR_MES} consultas por mes con el costo medio: "
                      + ", ".join(proyeccion) + ".")
    lineas += [
        "",
        "Notas: costo desde la traza de cada consulta (B0 sin traza: tokens de la salida; B1 no usa LLM). Una llamada "
        "sin tokens informados deja la consulta fuera del costo medio (nunca se suma como 0). La latencia no cuenta "
        "las salidas `error`. p95 por rango más cercano. s/d = sin dato; s/t = sin traza.",
    ]
    return "\n".join(lineas) + "\n"


# --- CLI -----------------------------------------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m eval.reporte", description=__doc__.splitlines()[0])
    ap.add_argument("reporte", type=Path, help="reports/eval_<split>_<fecha>.json")
    ap.add_argument("--juicios", type=Path, default=None)
    ap.add_argument("--calibracion", type=Path, default=None)
    ap.add_argument("--precios", type=Path, default=None)
    ap.add_argument("--salida", type=Path, default=None, help="por defecto reports/resultados.md")
    args = ap.parse_args(argv)
    try:
        reporte = Reporte.model_validate_json(args.reporte.read_text(encoding="utf-8"))
        juicios = Juicios.model_validate_json(args.juicios.read_text(encoding="utf-8")) if args.juicios else None
        calibracion = (Calibracion.model_validate_json(args.calibracion.read_text(encoding="utf-8"))
                       if args.calibracion else None)
        precios = cargar_precios(args.precios) if args.precios else {}
    except (OSError, ValueError) as e:
        print(f"[reporte] {e}", file=sys.stderr)
        return 1
    filas = filas_sistemas(reporte, juicios, precios)
    salida = args.salida or config.REPORTS_DIR / "resultados.md"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(render_markdown(reporte, filas, str(args.reporte), calibracion, bool(precios)), encoding="utf-8")
    print(f"[reporte] {len(filas)} sistemas → {salida}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
