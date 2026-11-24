"""Paso 2 — Descargar las webs de las bodegas (crudo, con fecha).

Por cada bodega baja la home y las páginas internas que parecen relevantes
(visitas, experiencias, restaurante, reservas...) hasta MAX_PAGINAS_POR_BODEGA.
Guarda el HTML/PDF tal cual en data/raw/<id>/<fecha>/ con un manifest.json.

- Respeta robots.txt y pone una pausa entre pedidos.
- Si una web arma el contenido con JavaScript y requests trae casi nada,
  corré con --playwright (hay que instalarlo una vez: `playwright install chromium`).
- No vuelve a bajar una bodega que ya tiene snapshot de hoy, salvo --force.
"""
from __future__ import annotations

import json
import time
from urllib import robotparser
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from . import config
from .utils import bodegas_a_procesar, dominio, leer_csv

REDES = ("facebook.com", "instagram.com", "linktr.ee", "wa.me", "whatsapp.com",
         "tripadvisor", "booking.com", "google.com", "youtube.com", "twitter.com", "x.com")
EXT_DESCARTAR = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".mp4", ".zip", ".mp3", ".ico")
MIN_CHARS_TEXTO = 800  # menos que esto en la home => probablemente es una web armada con JS


class Descargador:
    def __init__(self, usar_playwright: bool = False):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": config.USER_AGENT,
                               "Accept-Language": "es-AR,es;q=0.9,en;q=0.8"})
        self.usar_playwright = usar_playwright
        self._pw = None
        self._browser = None
        self._robots: dict[str, robotparser.RobotFileParser | None] = {}

    # robots.txt -----------------------------------------------------------
    def permitido(self, url: str) -> bool:
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        if base not in self._robots:
            rp = robotparser.RobotFileParser()
            try:
                r = self.s.get(base + "/robots.txt", timeout=config.TIMEOUT_S)
                if r.status_code == 200:
                    rp.parse(r.text.splitlines())
                    self._robots[base] = rp
                else:
                    self._robots[base] = None  # sin robots.txt => permitido
            except requests.RequestException:
                self._robots[base] = None
        rp = self._robots[base]
        return True if rp is None else rp.can_fetch(config.USER_AGENT, url)

    # descarga -----------------------------------------------------------------
    def get(self, url: str) -> tuple[int, str, bytes, str]:
        """Devuelve (status, content_type, contenido, url_final)."""
        r = self.s.get(url, timeout=config.TIMEOUT_S, allow_redirects=True)
        return r.status_code, r.headers.get("Content-Type", ""), r.content, r.url

    def get_renderizado(self, url: str) -> tuple[int, str, bytes, str]:
        if self._browser is None:
            from playwright.sync_api import sync_playwright  # import perezoso
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch()
        page = self._browser.new_page(user_agent=config.USER_AGENT)
        try:
            resp = page.goto(url, timeout=config.TIMEOUT_S * 1000, wait_until="networkidle")
            html = page.content()
            return (resp.status if resp else 200), "text/html", html.encode("utf-8"), page.url
        finally:
            page.close()

    def cerrar(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()


def texto_visible(html: bytes) -> str:
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    return soup.get_text(" ", strip=True)


def links_relevantes(html: bytes, url_base: str) -> list[str]:
    """Links internos (mismo dominio) cuyo href o texto contiene alguna palabra clave."""
    soup = BeautifulSoup(html, "lxml")
    dom = dominio(url_base)
    puntuados: dict[str, int] = {}
    for a in soup.find_all("a", href=True):
        href = urldefrag(urljoin(url_base, a["href"]))[0]
        if not href.startswith("http") or dominio(href) != dom:
            continue
        low = href.lower()
        if low.endswith(EXT_DESCARTAR) or any(r in low for r in REDES):
            continue
        texto = (a.get_text(" ", strip=True) or "").lower()
        score = sum(1 for p in config.PALABRAS_CLAVE if p in low or p in texto)
        if low.endswith(".pdf"):
            score += 1  # las cartas de experiencias suelen estar en PDF
        if score:
            puntuados[href] = max(puntuados.get(href, 0), score)
    return [u for u, _ in sorted(puntuados.items(), key=lambda kv: -kv[1])]


def extension(content_type: str, url: str) -> str:
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        return "pdf"
    return "html"


def crawl_bodega(b: dict, d: Descargador, force: bool = False) -> dict:
    destino = config.RAW_DIR / b["id"] / config.HOY
    manifest_path = destino / "manifest.json"
    if manifest_path.exists() and not force:
        return {"id": b["id"], "estado": "ya_descargada_hoy"}

    url = b.get("url_web", "").strip()
    if not url:
        return {"id": b["id"], "estado": "sin_web"}
    if any(r in url.lower() for r in REDES):
        return {"id": b["id"], "estado": "solo_redes"}

    destino.mkdir(parents=True, exist_ok=True)
    paginas: list[dict] = []
    pendientes = [url]
    vistos: set[str] = set()

    while pendientes and len(paginas) < config.MAX_PAGINAS_POR_BODEGA:
        u = pendientes.pop(0)
        if u in vistos:
            continue
        vistos.add(u)
        if not d.permitido(u):
            paginas.append({"url": u, "estado": "bloqueada_robots"})
            continue
        try:
            status, ctype, contenido, url_final = d.get(u)
            es_home = not paginas
            if (d.usar_playwright and "html" in ctype
                    and len(texto_visible(contenido)) < MIN_CHARS_TEXTO):
                status, ctype, contenido, url_final = d.get_renderizado(u)
        except Exception as e:  # noqa: BLE001 — queremos seguir con la próxima bodega
            paginas.append({"url": u, "estado": f"error: {type(e).__name__}: {e}"[:300]})
            continue
        finally:
            time.sleep(config.PAUSA_ENTRE_PEDIDOS_S)

        if status != 200:
            paginas.append({"url": u, "estado": f"http_{status}"})
            continue

        ext = extension(ctype, url_final)
        nombre = f"{len([p for p in paginas if 'archivo' in p]):02d}.{ext}"
        (destino / nombre).write_bytes(contenido)
        paginas.append({"url": url_final, "url_pedida": u, "archivo": nombre,
                        "content_type": ctype, "bytes": len(contenido), "estado": "ok",
                        "descargado": config.HOY})
        vistos.add(url_final)

        if ext == "html" and es_home:
            # Solo expandimos desde la home: alcanza para encontrar las secciones relevantes
            pendientes.extend(x for x in links_relevantes(contenido, url_final) if x not in vistos)

    manifest = {"id": b["id"], "nombre": b["nombre"], "zona": b.get("zona", ""),
                "url_web": url, "fecha": config.HOY, "user_agent": config.USER_AGENT,
                "paginas": paginas}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for p in paginas if p.get("estado") == "ok")
    return {"id": b["id"], "estado": "ok" if ok else "sin_paginas", "paginas_ok": ok}


def run(zona: str | None = None, ids: list[str] | None = None, limite: int | None = None,
        force: bool = False, playwright: bool = False) -> None:
    bodegas = bodegas_a_procesar(leer_csv(config.SEED_CSV), zona, ids, limite)
    if not bodegas:
        raise SystemExit("No hay bodegas para procesar. ¿Corriste `python -m corpus seed`?")
    d = Descargador(usar_playwright=playwright)
    resumen: dict[str, int] = {}
    try:
        for i, b in enumerate(bodegas, 1):
            res = crawl_bodega(b, d, force)
            resumen[res["estado"]] = resumen.get(res["estado"], 0) + 1
            print(f"[crawl] {i}/{len(bodegas)} {b['id']}: {res['estado']} "
                  f"{res.get('paginas_ok', '')}")
    finally:
        d.cerrar()
    print(f"[crawl] resumen: {resumen}")
