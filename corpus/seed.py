"""Paso 1 — Lista semilla de bodegas.

Busca bodegas por zona con Google Places API (New) - Text Search, las deduplica,
las mezcla con los agregados manuales (data/seed/manual.csv) y escribe
data/seed/bodegas.csv.

Sobre los términos de Google: lo único que se puede guardar sin límite es el
place_id. Por eso NO guardamos coordenadas, rating ni reseñas: eso se consulta en
vivo como tool del agente. Nombre y web los guardamos como punto de partida para
el crawl y se verifican contra la web oficial de cada bodega.

Si volvés a correrlo, se preservan las columnas que completaste a mano
(abre_turismo, notas, zona corregida, url_web corregida).
"""
from __future__ import annotations

import time

import requests

from . import config
from .utils import SEED_COLUMNS, dominio, escribir_csv, leer_csv, normalizar_url, rel, slugify

URL_TEXT_SEARCH = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.websiteUri",
    "places.types",
    "nextPageToken",
])
# Rectángulo aproximado de la provincia de Mendoza para no traer resultados de San Juan.
MENDOZA_BBOX = {
    "rectangle": {
        "low": {"latitude": -37.6, "longitude": -70.6},
        "high": {"latitude": -32.0, "longitude": -66.5},
    }
}


def buscar(query: str, api_key: str, max_paginas: int = 3) -> list[dict]:
    """Devuelve hasta 60 lugares (20 por página x 3 páginas) para una consulta."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    body = {
        "textQuery": query,
        "languageCode": "es",
        "regionCode": "AR",
        "pageSize": 20,
        "locationRestriction": MENDOZA_BBOX,
    }
    resultados: list[dict] = []
    for _ in range(max_paginas):
        r = requests.post(URL_TEXT_SEARCH, json=body, headers=headers, timeout=config.TIMEOUT_S)
        if r.status_code != 200:
            raise RuntimeError(f"Places respondió {r.status_code}: {r.text[:500]}")
        data = r.json()
        resultados.extend(data.get("places", []))
        token = data.get("nextPageToken")
        if not token:
            break
        body["pageToken"] = token
        time.sleep(2)  # el token tarda un poco en activarse
    return resultados


def place_a_fila(p: dict, zona: str) -> dict:
    nombre = (p.get("displayName") or {}).get("text", "").strip()
    return {
        "nombre": nombre,
        "zona": zona,
        "place_id": p.get("id", ""),
        "url_web": normalizar_url(p.get("websiteUri")),
        "direccion": p.get("formattedAddress", ""),
        "tipos_places": "|".join(p.get("types", [])),
        "fuente": "google_places",
        "abre_turismo": "",
        "notas": "",
    }


def asignar_ids(filas: list[dict]) -> None:
    usados: set[str] = set()
    for f in filas:
        if f.get("id"):
            usados.add(f["id"])
    for f in filas:
        if f.get("id"):
            continue
        base = slugify(f["nombre"])
        cand, n = base, 2
        while cand in usados:
            cand, n = f"{base}-{n}", n + 1
        f["id"] = cand
        usados.add(cand)


def clave(f: dict) -> str:
    """Clave de deduplicación: place_id si hay; si no, dominio web; si no, nombre."""
    return f.get("place_id") or dominio(f.get("url_web")) or slugify(f.get("nombre", ""))


def run(zonas: list[str] | None = None, sin_places: bool = False) -> None:
    previas = {clave(f): f for f in leer_csv(config.SEED_CSV)}
    nuevas: dict[str, dict] = {}

    if not sin_places:
        if not config.GOOGLE_MAPS_API_KEY:
            raise SystemExit("Falta GOOGLE_MAPS_API_KEY en .env (o corré con --sin-places).")
        for zona, consultas in config.ZONAS.items():
            if zonas and zona not in zonas:
                continue
            for q in consultas:
                lugares = buscar(q, config.GOOGLE_MAPS_API_KEY)
                print(f"[seed] {zona} · '{q}': {len(lugares)} resultados")
                for p in lugares:
                    fila = place_a_fila(p, zona)
                    nuevas.setdefault(clave(fila), fila)

    # Agregados a mano (Wineobs, Winemap, recorridas, etc.)
    for m in leer_csv(config.SEED_MANUAL_CSV):
        m = {**{c: "" for c in SEED_COLUMNS}, **m}
        m["url_web"] = normalizar_url(m.get("url_web"))
        m["fuente"] = m.get("fuente") or "manual"
        nuevas.setdefault(clave(m), m)

    # Segunda pasada de deduplicación por dominio web (misma bodega con dos fichas de Places)
    por_dominio: dict[str, dict] = {}
    for k, f in list(nuevas.items()):
        d = dominio(f.get("url_web"))
        if d and d in por_dominio and d not in {"facebook.com", "instagram.com", "linktr.ee"}:
            print(f"[seed] duplicado por web ({d}): '{f['nombre']}' se une a "
                  f"'{por_dominio[d]['nombre']}'. Si son bodegas distintas, cargala en manual.csv con otra URL.")
            del nuevas[k]
        elif d:
            por_dominio[d] = f

    # Merge con lo previo: lo que se editó a mano gana
    final: dict[str, dict] = dict(previas)
    for k, f in nuevas.items():
        if k in final:
            prev = final[k]
            for col in ("url_web", "direccion", "tipos_places", "nombre"):
                if not prev.get(col):
                    prev[col] = f.get(col, "")
        else:
            final[k] = f

    filas = sorted(final.values(), key=lambda f: (f.get("zona", ""), f.get("nombre", "")))
    asignar_ids(filas)
    escribir_csv(config.SEED_CSV, filas, SEED_COLUMNS)

    con_web = sum(1 for f in filas if f.get("url_web"))
    print(f"[seed] {len(filas)} bodegas en {rel(config.SEED_CSV)} "
          f"({con_web} con web). Revisá la columna abre_turismo antes del crawl.")
