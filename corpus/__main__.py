"""Punto de entrada único: `python -m corpus <paso> [opciones]`.

Pasos, en orden:
  datatourisme 1. semilla + texto desde DATAtourisme (Borgoña, datos abiertos)  ← camino recomendado
  seed       1'. (alternativa) semilla con Google Places + manual.csv
  crawl      2. (opcional) descarga de las webs de las bodegas para enriquecer
  clean      3. limpieza a texto
  extract    4. extracción de fichas con LLM
  eda        5a. reporte de exploración y completitud
  muestra    5b. planilla para validar fichas a mano
  precision  5c. precisión a partir de la planilla revisada
  todo       2 a 5a seguidos (después de revisar la semilla)
"""
from __future__ import annotations

import argparse

from . import clean, crawl, datatourisme, eda, extract, seed


def _filtros(p: argparse.ArgumentParser) -> None:
    p.add_argument("--zona", help='Solo una zona, ej. "Luján de Cuyo"')
    p.add_argument("--ids", nargs="+", help="Solo estos ids de bodega")
    p.add_argument("--limite", type=int, help="Procesar como máximo N bodegas (para probar)")


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m corpus", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="paso", required=True)

    p = sub.add_parser("datatourisme", help="Paso 1: semilla y texto desde el CSV de DATAtourisme")
    p.add_argument("csv", help="Ruta al CSV regional, ej. data/datatourisme/datatourisme-reg-bfc.csv")
    p.add_argument("--departamentos", nargs="+", help="Códigos de departamento (default: 21 71 89 58)")
    p.add_argument("--columnas", action="store_true", help="Solo mostrar las columnas detectadas")

    p = sub.add_parser("seed", help="Paso 1 alternativo: semilla con Google Places")
    p.add_argument("--zonas", nargs="+", help="Solo estas zonas")
    p.add_argument("--sin-places", action="store_true", help="Usar solo data/seed/manual.csv")

    p = sub.add_parser("crawl", help="Paso 2: descargar webs")
    _filtros(p)
    p.add_argument("--force", action="store_true", help="Volver a bajar aunque haya snapshot de hoy")
    p.add_argument("--playwright", action="store_true", help="Renderizar webs con JavaScript")

    p = sub.add_parser("clean", help="Paso 3: limpiar a texto")
    _filtros(p)

    p = sub.add_parser("extract", help="Paso 4: extraer fichas con LLM")
    _filtros(p)
    p.add_argument("--force", action="store_true", help="Re-extraer aunque ya haya ficha")
    p.add_argument("--dry-run", action="store_true", help="No llama al LLM; muestra tamaños")

    sub.add_parser("eda", help="Paso 5a: reporte de exploración")

    p = sub.add_parser("muestra", help="Paso 5b: planilla de validación manual")
    p.add_argument("--n", type=int, default=30, help="Cantidad de fichas (default 30)")

    p = sub.add_parser("precision", help="Paso 5c: precisión desde la planilla revisada")
    p.add_argument("archivo", help="CSV de data/validacion/ ya completado")

    p = sub.add_parser("todo", help="Pasos 2 a 5a seguidos")
    _filtros(p)
    p.add_argument("--playwright", action="store_true")

    a = ap.parse_args()
    if a.paso == "datatourisme":
        datatourisme.run(a.csv, a.departamentos, a.columnas)
    elif a.paso == "seed":
        seed.run(a.zonas, a.sin_places)
    elif a.paso == "crawl":
        crawl.run(a.zona, a.ids, a.limite, a.force, a.playwright)
    elif a.paso == "clean":
        clean.run(a.zona, a.ids, a.limite)
    elif a.paso == "extract":
        extract.run(a.zona, a.ids, a.limite, a.force, a.dry_run)
    elif a.paso == "eda":
        eda.run()
    elif a.paso == "muestra":
        eda.muestra(a.n)
    elif a.paso == "precision":
        eda.precision(a.archivo)
    elif a.paso == "todo":
        crawl.run(a.zona, a.ids, a.limite, playwright=a.playwright)
        clean.run(a.zona, a.ids, a.limite)
        extract.run(a.zona, a.ids, a.limite)
        eda.run()


if __name__ == "__main__":
    main()
