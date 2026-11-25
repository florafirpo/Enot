"""Chat por consola con Enot (spec 005): `python -m enot [--sesion archivo.json] …`.

Con `--sesion`, la conversación se guarda después de cada turno y, si el archivo ya existe, se retoma (historial,
perfil, itinerario vigente y la misma traza). "salir" o fin de entrada (Ctrl-D) terminan.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Optional

from corpus import config

from .corpus_local import cargar_corpus
from .flujo import K_CANDIDATAS, MAX_INTENTOS, TOPE_TOKENS, Flujo, Sesion
from .retrieval import EmbedderConCache, EmbedderOpenAI, Indice

SALUDO = ("Hola, soy Enot: armo itinerarios de 1 a 3 días por bodegas de Borgoña. Contame cuántos días, desde qué "
          "día, cómo te movés y cuántas personas viajan. Escribí \"salir\" para terminar.")
SALIR = {"salir", "chau", "exit", "quit"}


class ErrorConfiguracion(Exception):
    """Falta algo para arrancar (por ejemplo, las fichas del corpus)."""


def _positivo(valor: str) -> int:
    n = int(valor)
    if n < 1:
        raise argparse.ArgumentTypeError("tiene que ser un entero positivo")
    return n


def _argumentos(argv: Optional[list[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m enot", description="Chat por consola con Enot.")
    p.add_argument("--sesion", help="archivo JSON de la sesión: se retoma si existe y se guarda en cada turno")
    p.add_argument("--fichas", help="fichas.jsonl del corpus (por defecto, data/fichas/fichas.jsonl)")
    p.add_argument("--max-intentos", type=_positivo, default=MAX_INTENTOS,
                   help="intentos del loop de verificación (1 = sin loop, ablación B2)")
    p.add_argument("--tope-tokens", type=_positivo, default=TOPE_TOKENS, help="tope de tokens por conversación")
    p.add_argument("--k", type=_positivo, default=K_CANDIDATAS, help="bodegas candidatas para el planificador")
    return p.parse_args(argv)


def flujo_desde_args(args, cliente=None, embedder=None) -> Flujo:
    """Arma el flujo real: corpus local, `ClienteLLM` según `.env` y embeddings cacheados en `data/indice/`."""
    ruta = Path(args.fichas) if args.fichas else config.FICHAS_JSONL
    corpus = cargar_corpus(ruta)
    if not corpus:
        raise ErrorConfiguracion(f"No encontré fichas en {ruta}. Generalas con el pipeline del corpus "
                                 f"(ver README) o indicá otra ruta con --fichas.")
    if cliente is None:
        from corpus.llm import ClienteLLM

        cliente = ClienteLLM()
    if embedder is None:
        embedder = EmbedderConCache(EmbedderOpenAI())
    indice = Indice(list(corpus.values()), embedder)
    return Flujo(cliente, corpus, indice, max_intentos=args.max_intentos, tope_tokens=args.tope_tokens, k=args.k)


def main(argv: Optional[list[str]] = None, leer: Callable[[str], str] = input, escribir: Callable[[str], None] = print,
         construir_flujo: Optional[Callable[[argparse.Namespace], Flujo]] = None) -> int:
    args = _argumentos(argv)
    try:
        flujo = (construir_flujo or flujo_desde_args)(args)
    except ErrorConfiguracion as e:
        escribir(str(e))
        return 1

    ruta = Path(args.sesion) if args.sesion else None
    if ruta is not None and ruta.exists():
        sesion = Sesion.cargar(ruta)
        escribir(f"(retomo la conversación guardada en {ruta})")
    else:
        sesion = Sesion.nueva()
        escribir(SALUDO)

    while True:
        try:
            texto = leer("\nvos> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not texto:
            continue
        if texto.casefold() in SALIR:
            break
        respuesta = flujo.turno(sesion, texto)
        escribir(f"\nenot> {respuesta.texto}")
        if ruta is not None:
            sesion.guardar(ruta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
