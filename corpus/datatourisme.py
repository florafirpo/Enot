"""Paso 1 (alternativa abierta) — Semilla y texto base desde DATAtourisme.

DATAtourisme es la base nacional francesa de información turística en open data
(Licence Ouverte 2.0). Publica un CSV por región en data.gouv.fr. Este script:

1. Lee el CSV de la región Bourgogne-Franche-Comté.
2. Se queda con las bodegas: puntos de interés de tipo core:Cellar ("Cave ou caveau")
   y, entre los demás proveedores de degustación (productores, cooperativas,
   négociants), los que mencionan vino en el nombre o la descripción.
3. Filtra por departamento (por defecto los de Borgoña: 21, 71, 89, 58).
4. Asigna una subzona vitivinícola (Côte de Nuits, Côte de Beaune, Chablis...).
5. Escribe data/seed/bodegas.csv y el texto de cada bodega en data/base/ y data/clean/,
   listo para `python -m corpus extract`.

Las coordenadas sí se guardan: la licencia lo permite y las necesita el cálculo de
distancias. Como el CSV es "simplificado", los horarios y precios suelen venir
dentro de la descripción en texto libre: por eso el paso de extracción con LLM
sigue siendo necesario.

Uso:
    python -m corpus datatourisme data/datatourisme/datatourisme-reg-bfc.csv
    python -m corpus datatourisme <csv> --departamentos 21 71   # solo Côte-d'Or y Saône-et-Loire
    python -m corpus datatourisme <csv> --columnas               # solo muestra las columnas detectadas
"""
from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

from . import config
from .clean import escribir_limpio
from .utils import SEED_COLUMNS, escribir_csv, leer_csv, normalizar_url, slugify

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))  # descripciones largas

# --- Columnas ------------------------------------------------------------------
# Para cada dato, posibles fragmentos del nombre de columna (normalizado, sin tildes).
CANDIDATAS = {
    "nombre": ["nom_du_poi", "nom du poi", "nom", "name", "titre", "label"],
    "tipos": ["categories_de_poi", "categories de poi", "categorie", "type"],
    "lat": ["latitude", "lat"],
    "lon": ["longitude", "lon", "lng"],
    "direccion": ["adresse_postale", "adresse postale", "adresse", "address"],
    "cp_comuna": ["code_postal_et_commune", "code postal et commune", "code_postal", "code postal", "commune"],
    "descripcion": ["description", "descriptif"],
    "contacto": ["contacts_du_poi", "contacts du poi", "contact"],
    "clasificaciones": ["classements_du_poi", "classements du poi", "classement"],
    "uri": ["uri_id_du_poi", "uri id du poi", "uri", "identifiant"],
    "actualizado": ["date_de_mise_a_jour", "date de mise a jour", "mise_a_jour", "mise a jour", "update"],
}


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


def detectar_columnas(encabezados: list[str]) -> dict[str, str | None]:
    norm = {h: _norm(h) for h in encabezados}
    mapa: dict[str, str | None] = {}
    usadas: set[str] = set()
    for clave, cands in CANDIDATAS.items():
        if clave in config.COLUMNAS_DATATOURISME:
            mapa[clave] = config.COLUMNAS_DATATOURISME[clave]
            continue
        elegido = None
        for c in cands:  # orden = prioridad
            for h, n in norm.items():
                if h in usadas:
                    continue
                if n == c or c in n:
                    elegido = h
                    break
            if elegido:
                break
        mapa[clave] = elegido
        if elegido:
            usadas.add(elegido)
    return mapa


# --- Filtros -------------------------------------------------------------------
RE_VINO = re.compile(
    r"\b(vins?|vign\w*|viticult\w*|domaine|chateau|caveau|caves?|cuvees?|pinot|chardonnay|"
    r"cremant|aligote|gamay|grands? crus?|premiers? crus?|degustation|oenolog\w*|wines?|winery)\b")
TIPOS_CAVE = ("cellar", "cave ou caveau")
TIPOS_PROVEEDOR = ("tastingprovider", "producer", "cooperative", "trader", "producersgroup",
                   "fournisseur de degustation", "producteur", "negociant")


def es_bodega(tipos: str, nombre: str, descripcion: str) -> tuple[bool, str]:
    t = _norm(tipos)
    texto = _norm(f"{nombre} {descripcion}")
    if any(x in t for x in TIPOS_CAVE):
        return True, "cellar"
    if any(x in t for x in TIPOS_PROVEEDOR) and RE_VINO.search(texto):
        return True, "proveedor_con_vino"
    return False, ""


# --- Subzonas de Borgoña -----------------------------------------------------
COMUNAS_ZONA = {
    "Côte de Nuits": ["marsannay", "couchey", "fixin", "brochon", "gevrey", "morey", "chambolle",
                      "vougeot", "flagey", "vosne", "nuits-saint-georges", "nuits saint georges",
                      "premeaux", "comblanchien", "corgoloin", "dijon", "chenove"],
    "Côte de Beaune": ["ladoix", "aloxe", "pernand", "savigny-les-beaune", "savigny les beaune",
                       "chorey", "beaune", "pommard", "volnay", "monthelie", "auxey", "meursault",
                       "saint-romain", "saint romain", "puligny", "chassagne", "saint-aubin",
                       "saint aubin", "santenay", "maranges", "dezize", "cheilly", "sampigny"],
    "Hautes-Côtes": ["hautes-cotes", "nantoux", "echevronne", "magny-les-villers", "villers-la-faye"],
    "Chablis y Grand Auxerrois": ["chablis", "irancy", "chitry", "saint-bris", "saint bris",
                                  "auxerre", "tonnerre", "epineuil", "vezelay", "coulanges",
                                  "courgis", "fleys", "milly", "poinchy", "prehy", "maligny",
                                  "beines", "fontenay-pres-chablis", "joigny"],
    "Côte Chalonnaise": ["bouzeron", "rully", "mercurey", "givry", "montagny", "buxy", "jambles",
                         "saint-vallerin", "chalon", "chagny", "dracy", "aluze"],
    "Mâconnais": ["macon", "fuisse", "solutre", "vergisson", "chaintre", "davaye", "vire", "clesse",
                  "lugny", "saint-verand", "saint verand", "pierreclos", "charnay", "prisse",
                  "azé", "aze", "cruzille", "chardonnay", "tournus", "igé", "ige", "bussieres"],
}
NOMBRE_DEPTO = {"21": "Côte-d'Or", "71": "Saône-et-Loire", "89": "Yonne", "58": "Nièvre",
                "39": "Jura", "25": "Doubs", "70": "Haute-Saône", "90": "Territoire de Belfort"}


def subzona(comuna: str, depto: str, lat: float | None) -> str:
    c = _norm(comuna)
    for zona, comunas in COMUNAS_ZONA.items():
        if any(_norm(x) in c for x in comunas):
            return zona
    # Aproximación por latitud cuando la comuna no está en la lista
    if depto == "21" and lat is not None:
        return "Côte de Nuits" if lat >= 47.10 else "Côte de Beaune"
    if depto == "71" and lat is not None:
        return "Côte Chalonnaise" if lat >= 46.60 else "Mâconnais"
    if depto == "89":
        return "Chablis y Grand Auxerrois"
    if depto == "58":
        return "Nièvre (Pouilly-sur-Loire)"
    return NOMBRE_DEPTO.get(depto, depto or "sin_zona")


# --- Parseo de campos ----------------------------------------------------------
RE_CP = re.compile(r"\b(\d{5})\b")
RE_URL = re.compile(r"https?://[^\s|#<>\"']+", re.I)
REDES = ("facebook.", "instagram.", "twitter.", "x.com", "youtube.", "tripadvisor.", "linkedin.")


def cp_y_comuna(*campos: str) -> tuple[str, str]:
    for campo in campos:
        if not campo:
            continue
        m = RE_CP.search(campo)
        if m:
            cp = m.group(1)
            resto = campo[m.end():]
            comuna = re.split(r"[|<>]", resto.replace("#", " "))[0].strip(" ,-")
            if not comuna:
                previo = campo[:m.start()].replace("#", " ").strip(" ,-")
                comuna = previo.split(",")[-1].strip()
            return cp, comuna
    return "", ""


def web_principal(contacto: str) -> str:
    urls = [u.rstrip(".,);") for u in RE_URL.findall(contacto or "")]
    urls = [u for u in urls if "datatourisme" not in u.lower()]
    propias = [u for u in urls if not any(r in u.lower() for r in REDES)]
    return normalizar_url((propias or urls or [""])[0])


def a_float(x: str) -> float | None:
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None


RE_ONTO = re.compile(r"https?://www\.datatourisme\.(?:fr|gouv\.fr)/ontology/core#?/?")


def legible(valor: str) -> str:
    """Convierte la codificación multi-valor del CSV en texto legible.
    '|' separa objetos, '#' propiedades de un objeto, '<>' valores de una propiedad."""
    objetos = []
    for obj in RE_ONTO.sub("", valor or "").split("|"):
        props = [p.replace("<>", ", ").strip() for p in obj.split("#")]
        props = [p for p in props if p]
        if props:
            objetos.append(" · ".join(props))
    return "\n- ".join(objetos)


# --- Principal ---------------------------------------------------------------
def run(csv_path: str, departamentos: list[str] | None = None, solo_columnas: bool = False) -> None:
    path = Path(csv_path)
    if not path.exists():
        raise SystemExit(f"No encuentro {path}. Bajalo de data.gouv.fr (ver README).")
    deptos = departamentos or config.DEPARTAMENTOS

    with path.open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        col = detectar_columnas(lector.fieldnames or [])
        print("[datatourisme] columnas detectadas:")
        for k, v in col.items():
            print(f"   {k:16s} -> {v}")
        faltan = [k for k in ("nombre", "tipos") if not col.get(k)]
        if faltan:
            raise SystemExit(f"No detecté las columnas {faltan}. Fijalas en COLUMNAS_DATATOURISME (config.py). "
                             f"Encabezados del archivo: {lector.fieldnames}")
        if solo_columnas:
            return

        g = lambda fila, k: (fila.get(col[k]) or "") if col.get(k) else ""  # noqa: E731
        total = cand = 0
        filas: dict[str, dict] = {}
        textos: dict[str, dict] = {}
        motivos = {"cellar": 0, "proveedor_con_vino": 0}
        for fila in lector:
            total += 1
            nombre = g(fila, "nombre").strip()
            descripcion = g(fila, "descripcion")
            ok, motivo = es_bodega(g(fila, "tipos"), nombre, descripcion)
            if not ok or not nombre:
                continue
            cp, comuna = cp_y_comuna(g(fila, "cp_comuna"), g(fila, "direccion"))
            depto = cp[:2]
            if deptos and depto not in deptos:
                continue
            lat, lon = a_float(g(fila, "lat")), a_float(g(fila, "lon"))
            uri = g(fila, "uri").strip()
            clave = uri or f"{_norm(nombre)}|{_norm(comuna)}"
            if clave in filas:
                continue
            cand += 1
            motivos[motivo] += 1
            filas[clave] = {
                "nombre": nombre,
                "zona": subzona(comuna, depto, lat),
                "departamento": NOMBRE_DEPTO.get(depto, depto),
                "comuna": comuna,
                "lat": "" if lat is None else lat,
                "lon": "" if lon is None else lon,
                "url_web": web_principal(g(fila, "contacto")),
                "direccion": legible(g(fila, "direccion")).replace("\n- ", " · "),
                "tipos": motivo,
                "fuente": "datatourisme",
                "uri_fuente": uri,
                "actualizado": g(fila, "actualizado")[:10],
                "abre_turismo": "si",
                "notas": "",
            }
            partes = [f"Nombre: {nombre}",
                      f"Comuna: {comuna} ({cp})" if cp else "",
                      f"Dirección: {legible(g(fila, 'direccion'))}" if g(fila, "direccion") else "",
                      f"Tipos: {legible(g(fila, 'tipos'))}",
                      f"Contacto:\n- {legible(g(fila, 'contacto'))}" if g(fila, "contacto") else "",
                      f"Clasificaciones:\n- {legible(g(fila, 'clasificaciones'))}" if g(fila, "clasificaciones") else "",
                      f"Descripción:\n{descripcion.strip()}" if descripcion.strip() else "Descripción: (vacía)"]
            textos[clave] = {"url": uri or filas[clave]["url_web"],
                             "fecha": filas[clave]["actualizado"] or config.HOY,
                             "texto": "\n".join(p for p in partes if p)}

    # Preservar ediciones manuales de una corrida anterior (abre_turismo, notas, zona)
    previas = {f.get("uri_fuente") or f["id"]: f for f in leer_csv(config.SEED_CSV)
               if f.get("fuente") == "datatourisme"}
    lista = []
    for clave, f in filas.items():
        prev = previas.get(f["uri_fuente"] or clave)
        if prev:
            f["id"] = prev["id"]
            for c in ("abre_turismo", "notas", "zona", "url_web"):
                if prev.get(c):
                    f[c] = prev[c]
        lista.append(f)
    lista.sort(key=lambda f: (f["zona"], f["nombre"]))
    # ids legibles y únicos: nombre + comuna (hay muchos "Domaine X" repetidos entre pueblos)
    usados = {f["id"] for f in lista if f.get("id")}
    for f in lista:
        if f.get("id"):
            continue
        base = slugify(f"{f['nombre']} {f['comuna']}")
        cand, n = base, 2
        while cand in usados:
            cand, n = f"{base}-{n}", n + 1
        f["id"] = cand
        usados.add(cand)
    escribir_csv(config.SEED_CSV, lista, SEED_COLUMNS)

    sin_desc = 0
    for clave, f in filas.items():
        pagina = textos[clave]
        if "Descripción: (vacía)" in pagina["texto"]:
            sin_desc += 1
        (config.BASE_DIR / f"{f['id']}.json").write_text(
            json.dumps([pagina], ensure_ascii=False, indent=2), encoding="utf-8")
        escribir_limpio(f, [pagina])

    por_zona: dict[str, int] = {}
    for f in lista:
        por_zona[f["zona"]] = por_zona.get(f["zona"], 0) + 1
    con_web = sum(1 for f in lista if f["url_web"])
    con_coord = sum(1 for f in lista if f["lat"] != "")
    print(f"[datatourisme] {total:,} puntos de interés leídos → {len(lista)} bodegas "
          f"en departamentos {', '.join(deptos)} "
          f"({motivos['cellar']} caves, {motivos['proveedor_con_vino']} productores con vino)")
    print(f"[datatourisme] con web: {con_web} · con coordenadas: {con_coord} · sin descripción: {sin_desc}")
    print("[datatourisme] por subzona: " + ", ".join(f"{z} {n}" for z, n in sorted(por_zona.items())))
    print("[datatourisme] siguiente paso: python -m corpus extract --dry-run")
