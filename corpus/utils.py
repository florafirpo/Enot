"""Funciones chicas que usan varios pasos."""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

SEED_COLUMNS = [
    "id", "nombre", "zona", "departamento", "comuna", "lat", "lon", "url_web", "direccion",
    "tipos", "fuente", "uri_fuente", "actualizado", "place_id", "tipos_places",
    "abre_turismo", "notas",
]


def slugify(texto: str) -> str:
    """'Bodega Ñandú & Cía.' -> 'bodega-nandu-cia'"""
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t or "sin-nombre"


def dominio(url: str | None) -> str:
    """Dominio sin 'www.' para deduplicar bodegas que aparecen dos veces."""
    if not url:
        return ""
    netloc = urlparse(url if "://" in url else f"http://{url}").netloc.lower()
    return netloc.removeprefix("www.")


def normalizar_url(url: str | None) -> str:
    if not url:
        return ""
    url = url.strip()
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    return url


def leer_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def escribir_csv(path: Path, filas: list[dict], columnas: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        for fila in filas:
            w.writerow({c: fila.get(c, "") for c in columnas})


def leer_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def escribir_jsonl(path: Path, filas: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for fila in filas:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")


def bodegas_a_procesar(filas: list[dict], zona: str | None = None,
                       ids: list[str] | None = None, limite: int | None = None) -> list[dict]:
    """Filtro común: excluye las marcadas abre_turismo='no', y aplica --zona / --ids / --limite."""
    out = [f for f in filas if f.get("abre_turismo", "").strip().lower() not in {"no", "n", "false", "0"}]
    if zona:
        out = [f for f in out if f.get("zona", "").lower() == zona.lower()]
    if ids:
        quiero = set(ids)
        out = [f for f in out if f["id"] in quiero]
    if limite:
        out = out[:limite]
    return out


def normalizar_texto(t: str) -> str:
    """Para comparar citas contra el texto fuente: minúsculas, sin tildes, espacios colapsados."""
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


def rel(path: Path) -> str:
    """Ruta relativa a la raíz del repo para mostrar; absoluta si está afuera (p. ej. en tests)."""
    raiz = Path(__file__).resolve().parent.parent
    try:
        return str(Path(path).resolve().relative_to(raiz))
    except ValueError:
        return str(path)
