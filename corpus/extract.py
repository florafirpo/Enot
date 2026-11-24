"""Paso 4 — Extraer la ficha estructurada de cada bodega con un LLM.

Lee data/clean/<id>.md, le pide al LLM una FichaBodega (schema.py) y escribe
data/fichas/fichas.jsonl (una línea por bodega). Además:
- verifica en código que cada cita de evidencia aparezca en el texto fuente
  (sirve como primera medida de alucinación);
- registra tokens, latencia y costo estimado por bodega en
  data/fichas/costos_extraccion.csv.

No vuelve a extraer una bodega que ya tiene ficha, salvo --force.
Con --dry-run no llama al LLM: solo muestra cuánto texto mandaría.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime

from . import config
from .schema import FichaBodega
from .utils import bodegas_a_procesar, escribir_jsonl, leer_csv, leer_jsonl, normalizar_texto, rel

SISTEMA = f"""Sos un extractor de datos de bodegas de {config.REGION_NOMBRE} para un sistema de turismo.
Vas a recibir el texto de UNA bodega (ficha oficial de turismo y/o su web), dividido en secciones "## Fuente: <url>".
Completá la ficha siguiendo estas reglas, sin excepción:

1. Usá SOLO información que esté en el texto. Si un dato no aparece, dejalo en null (o lista vacía).
   No completes con conocimiento general ni con lo que "suele" pasar en las bodegas.
2. Precios: copiá el número tal como figura y su moneda. Si dice "consultar" o no hay precio, null.
   No conviertas monedas ni actualices precios.
3. Horarios en formato 24 h HH:MM. Días con las abreviaturas lun, mar, mie, jue, vie, sab, dom.
4. Para cada dato importante (horarios, cada precio, reserva, restaurante, sin TACC, accesibilidad,
   grupos) agregá una evidencia: la cita COPIADA TEXTUAL del texto (no la parafrasees, máximo ~200
   caracteres) y la URL de la sección "Fuente:" donde está.
5. perfil: "boutique" o "familiar" solo si el texto lo dice o lo describe claramente; si no, "no_informado".
6. descripcion_breve: 1 o 2 oraciones con tus palabras, basadas en el texto.
7. Si el texto está en francés, inglés u otro idioma, completá la ficha en español (las citas quedan en el idioma original).
8. Una "cave" o "caveau" de degustación cuenta como experiencia de tipo "degustacion" solo si el texto la ofrece al público.
"""


def armar_usuario(b: dict, texto: str) -> tuple[str, bool]:
    truncado = len(texto) > config.MAX_CHARS_POR_BODEGA
    if truncado:
        texto = texto[: config.MAX_CHARS_POR_BODEGA] + "\n\n[TEXTO TRUNCADO]"
    return (f"Bodega: {b['nombre']}\nZona: {b.get('zona', '')}\nComuna: {b.get('comuna', '')}\n"
            f"Web: {b.get('url_web', '')}\n\n"
            f"--- TEXTO DE LA WEB ---\n{texto}"), truncado


def verificar_evidencias(ficha: dict, texto_fuente: str) -> tuple[int, int]:
    """Cuenta cuántas citas aparecen literalmente (normalizadas) en el texto fuente."""
    fuente = normalizar_texto(texto_fuente)
    total = ok = 0
    for ev in ficha.get("evidencias", []):
        total += 1
        cita = normalizar_texto(ev.get("cita", ""))
        encontrada = bool(cita) and cita in fuente
        ev["verificada"] = encontrada
        ok += encontrada
    return ok, total


def costo_usd(modelo: str, tin: int, tout: int) -> float | None:
    precios = config.PRECIOS_USD_POR_MTOK.get(modelo)
    if not precios:
        return None
    return tin / 1e6 * precios["in"] + tout / 1e6 * precios["out"]


def registrar_costo(fila: dict) -> None:
    nuevo = not config.COSTOS_CSV.exists()
    with config.COSTOS_CSV.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fila))
        if nuevo:
            w.writeheader()
        w.writerow(fila)


def run(zona: str | None = None, ids: list[str] | None = None, limite: int | None = None,
        force: bool = False, dry_run: bool = False, cliente=None) -> None:
    bodegas = bodegas_a_procesar(leer_csv(config.SEED_CSV), zona, ids, limite)
    fichas = {f["id"]: f for f in leer_jsonl(config.FICHAS_JSONL)}

    if not dry_run and cliente is None:
        from .llm import ClienteLLM
        cliente = ClienteLLM()

    hechas = errores = 0
    for b in bodegas:
        md = config.CLEAN_DIR / f"{b['id']}.md"
        if not md.exists():
            continue
        if b["id"] in fichas and not force:
            continue
        texto = md.read_text(encoding="utf-8")
        usuario, truncado = armar_usuario(b, texto)

        if dry_run:
            print(f"[extract] {b['id']}: {len(usuario):,} caracteres (~{len(usuario)//4:,} tokens)"
                  f"{' TRUNCADO' if truncado else ''}")
            continue

        try:
            res = cliente.estructurado(SISTEMA, usuario, FichaBodega)
        except Exception as e:  # noqa: BLE001
            errores += 1
            print(f"[extract] {b['id']}: ERROR {type(e).__name__}: {str(e)[:300]}")
            continue

        ficha = res.objeto.model_dump()
        ok, total = verificar_evidencias(ficha, texto)
        paginas = json.loads((config.CLEAN_DIR / f"{b['id']}.json").read_text(encoding="utf-8"))
        ficha["_meta"] = {
            "id": b["id"],
            "zona": b.get("zona", ""),
            "place_id": b.get("place_id", ""),
            "comuna": b.get("comuna", ""),
            "lat": b.get("lat", ""),
            "lon": b.get("lon", ""),
            "fuente_semilla": b.get("fuente", ""),
            "uri_fuente": b.get("uri_fuente", ""),
            "url_web": b.get("url_web", ""),
            "fuentes": [{"url": p["url"], "fecha": p["fecha"]} for p in paginas],
            "extraido": datetime.now().isoformat(timespec="seconds"),
            "proveedor": cliente.provider,
            "modelo": cliente.model,
            "texto_truncado": truncado,
            "evidencias_verificadas": ok,
            "evidencias_total": total,
        }
        ficha["id"] = b["id"]
        fichas[b["id"]] = ficha
        # Guardamos en cada iteración para no perder trabajo si se corta
        escribir_jsonl(config.FICHAS_JSONL, list(fichas.values()))

        usd = costo_usd(cliente.model, res.tokens_in, res.tokens_out)
        registrar_costo({
            "fecha": datetime.now().isoformat(timespec="seconds"), "id": b["id"],
            "proveedor": cliente.provider, "modelo": cliente.model,
            "tokens_in": res.tokens_in, "tokens_out": res.tokens_out,
            "latencia_s": round(res.latencia_s, 2), "intentos": res.intentos,
            "costo_usd": "" if usd is None else round(usd, 6),
        })
        hechas += 1
        print(f"[extract] {b['id']}: {len(ficha['experiencias'])} experiencias, "
              f"evidencias {ok}/{total} verificadas, {res.tokens_in}+{res.tokens_out} tokens, "
              f"{res.latencia_s:.1f}s")

    if not dry_run:
        print(f"[extract] listo: {hechas} fichas nuevas, {errores} errores. "
              f"Total en {rel(config.FICHAS_JSONL)}: {len(fichas)}")
