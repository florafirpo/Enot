"""Paso 5 — Validar y explorar el corpus.

`python -m corpus eda`     -> reports/eda.md + reports/completitud.csv
`python -m corpus muestra` -> data/validacion/muestra.csv para revisar fichas a mano

Los números de reports/eda.md son los que van en la sección 5 del PRD
("Estado de exploración") y los que dicen si se dispara el plan B.
"""
from __future__ import annotations

import json
import random
from collections import Counter

import pandas as pd

from . import config
from .schema import CAMPOS_COMPLETITUD
from .utils import escribir_csv, leer_csv, leer_jsonl, rel


# --- helpers ----------------------------------------------------------------
def tiene(ficha: dict, campo: str) -> bool:
    if campo == "precio (alguna experiencia)":
        return any(e.get("precio_por_persona") is not None for e in ficha.get("experiencias", []))
    if "|" in campo:
        return any(tiene(ficha, c) for c in campo.split("|"))
    v = ficha.get(campo)
    if campo == "perfil":
        return v not in (None, "no_informado")
    if isinstance(v, list):
        return len(v) > 0
    return v is not None and v != ""


def estado_crawl(id_bodega: str) -> str:
    carpeta = config.RAW_DIR / id_bodega
    if not carpeta.exists():
        return "sin_crawl"
    snaps = sorted(p for p in carpeta.iterdir() if (p / "manifest.json").exists())
    if not snaps:
        return "sin_crawl"
    m = json.loads((snaps[-1] / "manifest.json").read_text(encoding="utf-8"))
    return "ok" if any(p.get("estado") == "ok" for p in m["paginas"]) else "fallido"


def tabla_md(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lineas = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, fila in df.iterrows():
        lineas.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in fila) + " |")
    return "\n".join(lineas)


def pct(x: float) -> str:
    return f"{x:.0%}"


# --- EDA --------------------------------------------------------------------
def run() -> None:
    seed = leer_csv(config.SEED_CSV)
    fichas = leer_jsonl(config.FICHAS_JSONL)
    if not seed:
        raise SystemExit("No hay semilla. Corré los pasos anteriores.")
    por_id = {f["id"]: f for f in fichas}
    ZONAS = sorted({b.get("zona", "") for b in seed if b.get("zona")})
    salida: list[str] = [f"# EDA del corpus de bodegas — {config.HOY}\n"]

    # 1. Embudo por zona
    filas = []
    for z in ZONAS + ["Total"]:
        bs = seed if z == "Total" else [b for b in seed if b.get("zona") == z]
        abre = [b for b in bs if b.get("abre_turismo", "").strip().lower() not in {"no", "n", "false", "0"}]
        filas.append({
            "zona": z,
            "semilla": len(bs),
            "con web": sum(1 for b in bs if b.get("url_web")),
            "no descartadas": len(abre),
            "crawl ok": sum(1 for b in abre if estado_crawl(b["id"]) == "ok"),
            "texto limpio": sum(1 for b in abre if (config.CLEAN_DIR / f"{b['id']}.md").exists()),
            "con ficha": sum(1 for b in abre if b["id"] in por_id),
        })
    salida += ["## 1. Embudo por zona\n", tabla_md(pd.DataFrame(filas)), ""]

    if not fichas:
        salida.append("_Todavía no hay fichas extraídas._")
        (config.REPORTS_DIR / "eda.md").write_text("\n".join(salida), encoding="utf-8")
        print("\n".join(salida))
        return

    # 2. Completitud por campo (global y por zona)
    comp = []
    for campo in CAMPOS_COMPLETITUD:
        fila = {"campo": campo, "total": pct(sum(tiene(f, campo) for f in fichas) / len(fichas))}
        for z in ZONAS:
            fz = [f for f in fichas if f["_meta"]["zona"] == z]
            fila[z] = pct(sum(tiene(f, campo) for f in fz) / len(fz)) if fz else "–"
        comp.append(fila)
    df_comp = pd.DataFrame(comp)
    df_comp.to_csv(config.REPORTS_DIR / "completitud.csv", index=False)
    salida += [f"## 2. Completitud por campo (n = {len(fichas)} fichas)\n", tabla_md(df_comp), ""]

    # Chequeo de plan B (PRD sección 7)
    c_precio = sum(tiene(f, "precio (alguna experiencia)") for f in fichas) / len(fichas)
    c_horario = sum(tiene(f, "horarios|horario_texto") for f in fichas) / len(fichas)
    alerta = c_precio < config.UMBRAL_PLAN_B or c_horario < config.UMBRAL_PLAN_B
    salida += ["## 3. Chequeo del plan B\n",
               f"- Completitud de precio: **{pct(c_precio)}**",
               f"- Completitud de horario: **{pct(c_horario)}**",
               f"- Umbral: {pct(config.UMBRAL_PLAN_B)} → "
               + ("**se dispara el plan B** (ver PRD sección 7)" if alerta else "no se dispara"), ""]

    # 4. Precios (precio mínimo por bodega, por moneda y zona)
    precios = []
    for f in fichas:
        for e in f.get("experiencias", []):
            if e.get("precio_por_persona") is not None:
                precios.append({"id": f["id"], "zona": f["_meta"]["zona"],
                                "moneda": e.get("moneda") or "sin_moneda",
                                "precio": e["precio_por_persona"], "tipo": e.get("tipo")})
    if precios:
        dp = pd.DataFrame(precios)
        minimo = dp.groupby(["zona", "moneda", "id"])["precio"].min().reset_index()
        resumen = (minimo.groupby(["zona", "moneda"])["precio"]
                   .describe(percentiles=[.25, .5, .75])[["count", "min", "25%", "50%", "75%", "max"]]
                   .round(0).reset_index())
        resumen["count"] = resumen["count"].astype(int)
        salida += ["## 4. Precio de entrada por bodega (experiencia más barata)\n",
                   "Los precios se comparan solo dentro de la misma moneda y fecha de descarga.\n",
                   tabla_md(resumen), ""]

    # 5. Experiencias y perfil
    tipos = Counter(e.get("tipo") for f in fichas for e in f.get("experiencias", []))
    perfiles = Counter(f.get("perfil", "no_informado") for f in fichas)
    n_exp = [len(f.get("experiencias", [])) for f in fichas]
    salida += ["## 5. Experiencias y perfil\n",
               f"- Experiencias por bodega: media {sum(n_exp)/len(n_exp):.1f}, "
               f"bodegas sin ninguna: {sum(1 for n in n_exp if n == 0)}",
               "- Por tipo: " + ", ".join(f"{k} {v}" for k, v in tipos.most_common()),
               "- Perfil: " + ", ".join(f"{k} {v}" for k, v in perfiles.most_common()), ""]

    # 6. Tamaño del corpus
    chars = paginas = 0
    for f in fichas:
        p = config.CLEAN_DIR / f"{f['id']}.json"
        if p.exists():
            pags = json.loads(p.read_text(encoding="utf-8"))
            paginas += len(pags)
            chars += sum(len(x["texto"]) for x in pags)
    truncadas = sum(1 for f in fichas if f["_meta"].get("texto_truncado"))
    salida += ["## 6. Tamaño del corpus\n",
               f"- Páginas limpias: {paginas:,}",
               f"- Caracteres: {chars:,} (~{chars // 4:,} tokens, estimando 4 caracteres por token)",
               f"- Fichas con texto truncado al extraer: {truncadas}", ""]

    # 7. Evidencias y costos de extracción
    ev_ok = sum(f["_meta"].get("evidencias_verificadas", 0) for f in fichas)
    ev_tot = sum(f["_meta"].get("evidencias_total", 0) for f in fichas)
    salida += ["## 7. Evidencias y costo de extracción\n",
               f"- Citas de evidencia encontradas textualmente en la fuente: {ev_ok}/{ev_tot}"
               + (f" ({pct(ev_ok / ev_tot)})" if ev_tot else "")]
    if config.COSTOS_CSV.exists():
        dc = pd.read_csv(config.COSTOS_CSV).drop_duplicates("id", keep="last")
        salida += [f"- Tokens entrada / salida: {int(dc.tokens_in.sum()):,} / {int(dc.tokens_out.sum()):,}",
                   f"- Latencia por bodega: media {dc.latencia_s.mean():.1f} s, p95 {dc.latencia_s.quantile(.95):.1f} s",
                   f"- Reintentos por validación: {int((dc.intentos > 1).sum())} bodegas"]
        if dc.costo_usd.notna().any():
            salida.append(f"- Costo estimado: USD {dc.costo_usd.sum():.4f} "
                          f"(USD {dc.costo_usd.mean():.5f} por bodega)")
        else:
            salida.append("- Costo en USD: completar PRECIOS_USD_POR_MTOK en config.py")
    salida.append("")

    texto = "\n".join(salida)
    (config.REPORTS_DIR / "eda.md").write_text(texto, encoding="utf-8")
    print(texto)
    print(f"\n[eda] reporte en {rel(config.REPORTS_DIR / 'eda.md')}")


# --- Muestra para validación manual ------------------------------------------
CAMPOS_MUESTRA = ["horario_texto", "requiere_reserva", "tiene_restaurante", "opciones_sin_tacc",
                  "accesible_movilidad_reducida", "acepta_grupos", "perfil"]


def muestra(n: int = 30, semilla: int = 42) -> None:
    """Arma una planilla para revisar fichas contra la web: una fila por dato."""
    fichas = leer_jsonl(config.FICHAS_JSONL)
    if not fichas:
        raise SystemExit("No hay fichas todavía.")
    rnd = random.Random(semilla)
    por_zona: dict[str, list[dict]] = {}
    for f in fichas:
        por_zona.setdefault(f["_meta"]["zona"], []).append(f)
    elegidas: list[dict] = []
    cupo = max(1, n // max(1, len(por_zona)))
    for fs in por_zona.values():
        elegidas += rnd.sample(fs, min(cupo, len(fs)))

    filas = []
    for f in elegidas:
        ev = {e["campo"]: e for e in f.get("evidencias", [])}
        base = {"id": f["id"], "zona": f["_meta"]["zona"], "url_web": f["_meta"]["url_web"],
                "revisor": config.REVISORES.get(f["_meta"]["zona"], "")}
        for c in CAMPOS_MUESTRA:
            e = ev.get(c, {})
            filas.append({**base, "campo": c, "valor": f.get(c), "cita": e.get("cita", ""),
                          "url_cita": e.get("url", ""), "cita_verificada": e.get("verificada", "")})
        for i, x in enumerate(f.get("experiencias", [])[:3]):
            c = f"experiencias[{i}].precio_por_persona"
            e = ev.get(c, {})
            filas.append({**base, "campo": f"{c} ({x['nombre']})",
                          "valor": f"{x.get('precio_por_persona')} {x.get('moneda') or ''}".strip(),
                          "cita": e.get("cita", ""), "url_cita": e.get("url", ""),
                          "cita_verificada": e.get("verificada", "")})
    columnas = ["revisor", "zona", "id", "url_web", "campo", "valor", "cita", "url_cita",
                "cita_verificada", "correcto (si/no/no_esta_en_web)", "comentario"]
    destino = config.VALIDACION_DIR / f"muestra_{config.HOY}.csv"
    escribir_csv(destino, filas, columnas)
    print(f"[muestra] {len(elegidas)} fichas, {len(filas)} datos a revisar → "
          f"{rel(destino)}")


def precision(path: str) -> None:
    """Lee una muestra ya revisada y calcula la precisión por campo."""
    df = pd.read_csv(path)
    col = "correcto (si/no/no_esta_en_web)"
    df = df[df[col].notna()]
    if df.empty:
        raise SystemExit("La muestra no tiene ninguna fila revisada todavía.")
    df["campo_base"] = df["campo"].str.replace(r"\[\d+\].*", "[i].precio", regex=True)
    df["ok"] = df[col].str.strip().str.lower().eq("si")
    tabla = (df.groupby("campo_base")["ok"].agg(["count", "mean"])
             .rename(columns={"count": "revisados", "mean": "precision"}).reset_index())
    tabla["precision"] = tabla["precision"].map(pct)
    texto = (f"# Precisión de la extracción (muestra revisada a mano)\n\n"
             f"Datos revisados: {len(df)} · precisión global: {pct(df['ok'].mean())}\n\n"
             + tabla_md(tabla) + "\n")
    destino = config.REPORTS_DIR / "precision_extraccion.md"
    destino.write_text(texto, encoding="utf-8")
    print(texto)
