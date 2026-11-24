"""Paso 3 — Limpiar el crudo a texto.

Toma el snapshot más reciente de cada bodega en data/raw/<id>/ y escribe:
- data/clean/<id>.json : lista de páginas {url, fecha, texto}
- data/clean/<id>.md   : todo junto, con un encabezado por fuente (lo que lee el LLM)

Saca menús, footers y avisos repetidos: una línea que aparece en la mitad o más
de las páginas de esa bodega se considera "plantilla" y se elimina.
"""
from __future__ import annotations

import io
import json
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from . import config
from .utils import bodegas_a_procesar, leer_csv


def ultimo_snapshot(id_bodega: str) -> Path | None:
    carpeta = config.RAW_DIR / id_bodega
    if not carpeta.exists():
        return None
    fechas = sorted(p for p in carpeta.iterdir() if (p / "manifest.json").exists())
    return fechas[-1] if fechas else None


BLOQUES = ["p", "div", "section", "article", "li", "tr", "td", "th", "br", "dd", "dt",
           "table", "ul", "ol", "header", "footer", "main", "aside"]


def html_a_texto(html: bytes, url: str = "") -> str:
    """HTML -> texto con títulos en markdown.

    Preferimos recall a precisión: en las webs de bodegas el nombre de cada
    experiencia suele estar en un título y los horarios en el footer, y los
    extractores de "contenido principal" (tipo trafilatura) a veces los tiran.
    El ruido que queda (menús, cookies) lo saca quitar_plantilla().
    """
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript", "svg", "iframe", "nav", "form", "button",
                   "select", "input", "template"]):
        t.decompose()
    for img in soup.find_all("img"):
        alt = (img.get("alt") or "").strip()
        img.replace_with(f" {alt} " if len(alt) > 15 else " ")
    for nivel in range(1, 7):
        for h in soup.find_all(f"h{nivel}"):
            h.replace_with(f"\n\n{'#' * min(nivel + 2, 6)} {h.get_text(' ', strip=True)}\n\n")
    for li in soup.find_all("li"):
        li.insert_before("\n- ")
    for b in soup.find_all(BLOQUES):
        b.insert_after("\n")
    texto = soup.get_text()
    lineas = [" ".join(l.split()) for l in texto.splitlines()]
    out, vacia = [], False
    for l in lineas:
        if l in {"", "-"}:
            if not vacia and out:
                out.append("")
            vacia = True
        else:
            out.append(l)
            vacia = False
    return "\n".join(out).strip()


def pdf_a_texto(contenido: bytes) -> str:
    import pdfplumber
    partes = []
    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        for pag in pdf.pages:
            partes.append(pag.extract_text() or "")
    return "\n".join(partes)


def quitar_plantilla(paginas: list[dict]) -> None:
    """Elimina las líneas que se repiten en >= 50% de las páginas (menú, footer, cookies)."""
    if len(paginas) < 3:
        return
    conteo: Counter[str] = Counter()
    for p in paginas:
        conteo.update({l.strip() for l in p["texto"].splitlines() if l.strip()})
    umbral = len(paginas) / 2
    repetidas = {l for l, n in conteo.items() if n >= umbral and len(l) < 200}
    for i, p in enumerate(paginas):
        if i == 0:
            continue  # la home conserva todo una vez, para no perder datos de contacto
        p["texto"] = "\n".join(l for l in p["texto"].splitlines() if l.strip() not in repetidas)


def paginas_base(id_bodega: str) -> list[dict]:
    """Texto de fuentes abiertas ya estructuradas (DATAtourisme), si existe."""
    p = config.BASE_DIR / f"{id_bodega}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def escribir_limpio(b: dict, paginas: list[dict]) -> int:
    """Escribe data/clean/<id>.json y .md (lo que lee el LLM). Devuelve los caracteres."""
    (config.CLEAN_DIR / f"{b['id']}.json").write_text(
        json.dumps(paginas, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [f"# {b['nombre']} ({b.get('zona', '')})\n"]
    for p in paginas:
        md.append(f"\n## Fuente: {p['url']} (fecha {p['fecha']})\n\n{p['texto']}\n")
    (config.CLEAN_DIR / f"{b['id']}.md").write_text("".join(md), encoding="utf-8")
    return sum(len(p["texto"]) for p in paginas)


def limpiar_bodega(b: dict) -> dict:
    base = paginas_base(b["id"])
    snap = ultimo_snapshot(b["id"])
    if snap is None and not base:
        return {"id": b["id"], "estado": "sin_snapshot"}
    paginas = []
    if snap is not None:
        manifest = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
        for p in manifest["paginas"]:
            if p.get("estado") != "ok":
                continue
            contenido = (snap / p["archivo"]).read_bytes()
            try:
                texto = pdf_a_texto(contenido) if p["archivo"].endswith(".pdf") \
                    else html_a_texto(contenido, p["url"])
            except Exception as e:  # noqa: BLE001
                texto = ""
                print(f"[clean] {b['id']} {p['archivo']}: no se pudo leer ({e})")
            if texto.strip():
                paginas.append({"url": p["url"], "fecha": manifest["fecha"], "texto": texto.strip()})
        quitar_plantilla(paginas)
        paginas = [p for p in paginas if len(p["texto"]) > 50]

    paginas = base + paginas  # la ficha oficial va primero
    if not paginas:
        return {"id": b["id"], "estado": "sin_texto"}
    chars = escribir_limpio(b, paginas)
    return {"id": b["id"], "estado": "ok", "paginas": len(paginas), "chars": chars}


def run(zona: str | None = None, ids: list[str] | None = None, limite: int | None = None) -> None:
    bodegas = bodegas_a_procesar(leer_csv(config.SEED_CSV), zona, ids, limite)
    resumen: dict[str, int] = {}
    for b in bodegas:
        res = limpiar_bodega(b)
        resumen[res["estado"]] = resumen.get(res["estado"], 0) + 1
        if res["estado"] == "ok":
            print(f"[clean] {b['id']}: {res['paginas']} páginas, {res['chars']:,} caracteres")
    print(f"[clean] resumen: {resumen}")
