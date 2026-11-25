"""Juez LLM del preference score (H2): rúbrica 1–5 de ajuste a las preferencias blandas (spec 008, ADR-0007, ADR-0018).

Lo que es verificable lo mide el código (`eval/metricas.py`); el juez mide solo lo que no se puede comprobar con una
función: si las bodegas elegidas responden a lo que el turista dijo que le gusta.

- **Juzgable**: consulta factible, con `preferencias` en la etiqueta, y el sistema entregó un itinerario con paradas.
- **Mismo contexto para todos los sistemas** y **juez ciego**: los datos de cada bodega salen del corpus (no de la
  prosa del sistema), sin precios ni horarios, y el juez no sabe qué sistema armó el itinerario.
- **Sin "confianza"** (lineamientos C.8): justificación y después el puntaje, nada más.

Uso: python -m eval.juez reports/eval_dev_<fecha>.json [--set data/eval] [--fichas data/fichas/fichas.jsonl]
     → reports/juez_<split>_<fecha>.json (nunca pisa uno anterior)
"""
from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

from corpus import config
from corpus.llm import ErrorSalidaInvalida
from enot.corpus_local import cargar_corpus
from enot.modelos import Bodega, Itinerario
from enot.nodos import DIA_LARGO, LARGO_DESCRIPCION
from eval.correr import Reporte, cargar_consultas
from eval.generador import Consulta
from eval.metricas import SalidaSistema

__all__ = ["Juicio", "Juicios", "SalidaJuez", "cargar_rubrica", "contexto_juez", "juzgable", "juzgar",
           "juzgar_reporte", "main", "texto_itinerario"]

RUBRICA = Path(__file__).parent / "prompts" / "juez.md"


def cargar_rubrica() -> str:
    return RUBRICA.read_text(encoding="utf-8")


class SalidaJuez(BaseModel):
    """Salida del LLM. La justificación va primero: el modelo razona y después puntúa."""
    justificacion: str
    puntaje: Literal[1, 2, 3, 4, 5]


class Juicio(BaseModel):
    consulta_id: str
    sistema: str
    estado: Literal["ok", "error"]
    puntaje: Optional[int] = Field(None, ge=1, le=5)
    justificacion: str = ""
    error: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    latencia_s: float = 0.0


class Juicios(BaseModel):
    """Lo que escribe `python -m eval.juez`: los juicios de un reporte del benchmark, con el modelo que juzgó."""
    reporte: str
    split: str
    fecha: str
    proveedor: Optional[str] = None
    modelo: Optional[str] = None
    juicios: list[Juicio]


def juzgable(consulta: Consulta, salida: SalidaSistema) -> bool:
    return (not consulta.infactible and bool((consulta.restricciones.preferencias or "").strip())
            and salida.tipo == "itinerario" and salida.itinerario is not None
            and any(d.paradas for d in salida.itinerario.dias))


def texto_itinerario(itinerario: Itinerario, corpus: dict[str, Bodega]) -> str:
    """Las bodegas de cada día con los datos de su ficha. Sin horarios, precios ni duraciones."""
    lineas: list[str] = []
    for d in itinerario.dias:
        lineas.append(f"Día {d.numero} ({DIA_LARGO[d.dia_semana]}):")
        for p in d.paradas:
            b = corpus.get(p.bodega_id)
            if b is None:
                nombre = p.bodega_id.removeprefix("b0:")
                lineas.append(f"- {nombre}: fuera del corpus, sin datos.")
                continue
            datos = [f"zona {b.zona}" if b.zona else "", f"comuna {b.comuna}" if b.comuna else "",
                     f"experiencia: {p.experiencia}" if p.experiencia else "",
                     f"vinos: {', '.join(b.vinos_o_varietales_destacados)}" if b.vinos_o_varietales_destacados else "",
                     f"descripción: {(b.descripcion_breve or '')[:LARGO_DESCRIPCION]}" if b.descripcion_breve else ""]
            lineas.append(f"- {b.nombre}: " + "; ".join(x for x in datos if x) + ".")
    return "\n".join(lineas)


def contexto_juez(consulta: Consulta, itinerario: Itinerario, corpus: dict[str, Bodega]) -> str:
    return (f"<pedido>\n{consulta.texto}\nPreferencias: {consulta.restricciones.preferencias}\n</pedido>\n\n"
            f"<itinerario>\n{texto_itinerario(itinerario, corpus)}\n</itinerario>")


def juzgar(cliente, consulta: Consulta, salida: SalidaSistema, corpus: dict[str, Bodega]) -> Juicio:
    """Un juicio. Si el cliente falla, devuelve un juicio en `error` (con los tokens si el cliente los informa)."""
    comunes = dict(consulta_id=consulta.id, sistema=salida.sistema)
    t0 = time.perf_counter()
    try:
        r = cliente.estructurado(cargar_rubrica(), contexto_juez(consulta, salida.itinerario, corpus), SalidaJuez)
    except Exception as e:  # noqa: BLE001 — un juicio fallido se cuenta, no tira la corrida
        gasto = e if isinstance(e, ErrorSalidaInvalida) else None
        return Juicio(**comunes, estado="error", error=str(e)[:500], latencia_s=time.perf_counter() - t0,
                      tokens_in=gasto.tokens_in if gasto else None, tokens_out=gasto.tokens_out if gasto else None)
    return Juicio(**comunes, estado="ok", puntaje=r.objeto.puntaje, justificacion=r.objeto.justificacion,
                  tokens_in=r.tokens_in, tokens_out=r.tokens_out, latencia_s=time.perf_counter() - t0)


def juzgar_reporte(cliente, reporte: Reporte, consultas: Sequence[Consulta], corpus: dict[str, Bodega],
                   origen: str) -> Juicios:
    """Juzga las salidas juzgables de todos los sistemas del reporte."""
    por_id = {c.id: c for c in consultas}
    juicios = []
    for salidas in reporte.salidas.values():
        for s in salidas:
            c = por_id.get(s.consulta_id)
            if c is None:
                raise ValueError(f"la salida {s.sistema}/{s.consulta_id} no tiene consulta en el set")
            if juzgable(c, s):
                juicios.append(juzgar(cliente, c, s, corpus))
    return Juicios(reporte=origen, split=reporte.split, fecha=datetime.now().strftime("%Y-%m-%d-%H%M%S"),
                   proveedor=getattr(cliente, "provider", None), modelo=getattr(cliente, "model", None),
                   juicios=juicios)


def escribir_sin_pisar(texto: str, carpeta: Path, base: str, extension: str = ".json") -> Path:
    """`<carpeta>/<base><extension>`; si ya existe, `-2`, `-3`…"""
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta, n = carpeta / f"{base}{extension}", 1
    while ruta.exists():
        n += 1
        ruta = carpeta / f"{base}-{n}{extension}"
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def cargar_entradas(ruta_reporte: Path, carpeta_set: Optional[Path], fichas: Optional[Path]):
    """Reporte, consultas de su split y corpus. FileNotFoundError con un mensaje claro si falta algo."""
    if not Path(ruta_reporte).exists():
        raise FileNotFoundError(f"no existe el reporte {ruta_reporte}")
    reporte = Reporte.model_validate_json(Path(ruta_reporte).read_text(encoding="utf-8"))
    ruta_fichas = Path(fichas) if fichas else config.FICHAS_JSONL
    if not ruta_fichas.exists():
        raise FileNotFoundError(f"no existe el corpus de fichas {ruta_fichas}")
    consultas = cargar_consultas(reporte.split, carpeta_set)
    return reporte, consultas, cargar_corpus(ruta_fichas)


def _cliente_llm():  # pragma: no cover - necesita clave; en tests se inyecta una fábrica
    from corpus.llm import ClienteLLM
    return ClienteLLM()


def main(argv: Optional[list[str]] = None, crear_cliente: Optional[Callable[[], object]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m eval.juez", description=__doc__.splitlines()[0])
    ap.add_argument("reporte", type=Path, help="reports/eval_<split>_<fecha>.json")
    ap.add_argument("--set", dest="carpeta_set", type=Path, default=None, help="carpeta del set (data/eval)")
    ap.add_argument("--fichas", type=Path, default=None, help="corpus (por defecto data/fichas/fichas.jsonl)")
    args = ap.parse_args(argv)
    try:
        reporte, consultas, corpus = cargar_entradas(args.reporte, args.carpeta_set, args.fichas)
    except Exception as e:  # noqa: BLE001 — falta un archivo o el set: mensaje y código 1
        print(f"[juez] {e}", file=sys.stderr)
        return 1
    juicios = juzgar_reporte((crear_cliente or _cliente_llm)(), reporte, consultas, corpus, str(args.reporte))
    ruta = escribir_sin_pisar(juicios.model_dump_json(indent=2) + "\n", config.REPORTS_DIR,
                              f"juez_{reporte.split}_{juicios.fecha}")
    errores = sum(j.estado == "error" for j in juicios.juicios)
    print(f"[juez] {len(juicios.juicios)} juicios ({errores} con error) → {ruta}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
