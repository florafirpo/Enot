"""Configuración compartida del pipeline del corpus de Enot.

Todo lo que cambia entre corridas (claves, modelo) va en el archivo .env.
Lo que es parte del diseño (zonas, palabras clave, límites) vive acá, versionado.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# --- Carpetas -------------------------------------------------------------
DATA = ROOT / "data"
SEED_DIR = DATA / "seed"
RAW_DIR = DATA / "raw"
CLEAN_DIR = DATA / "clean"
FICHAS_DIR = DATA / "fichas"
VALIDACION_DIR = DATA / "validacion"
REPORTS_DIR = ROOT / "reports"

SEED_CSV = SEED_DIR / "bodegas.csv"
SEED_MANUAL_CSV = SEED_DIR / "manual.csv"  # agregados a mano (Wineobs, Winemap, etc.)
FICHAS_JSONL = FICHAS_DIR / "fichas.jsonl"
COSTOS_CSV = FICHAS_DIR / "costos_extraccion.csv"

for _d in (SEED_DIR, RAW_DIR, CLEAN_DIR, FICHAS_DIR, VALIDACION_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

HOY = date.today().isoformat()

# --- Región del MVP ----------------------------------------------------------
REGION_NOMBRE = os.getenv("REGION_NOMBRE", "Borgoña (Bourgogne, Francia)")
BASE_DIR = DATA / "base"  # texto de fuentes abiertas (DATAtourisme) por bodega
BASE_DIR.mkdir(parents=True, exist_ok=True)

# DATAtourisme: departamentos de Borgoña dentro de la región Bourgogne-Franche-Comté.
# 21 Côte-d'Or, 71 Saône-et-Loire, 89 Yonne, 58 Nièvre. Sumar "39" para incluir Jura.
DEPARTAMENTOS = ["21", "71", "89", "58"]

# Si DATAtourisme cambia los nombres de columna del CSV, se pueden fijar acá
# (clave lógica -> nombre exacto de la columna). Vacío = autodetección.
COLUMNAS_DATATOURISME: dict[str, str] = {}

# --- (Opcional) Semilla con Google Places, pensada originalmente para Mendoza ---
# Cada zona tiene las consultas que se mandan a Google Places.
ZONAS: dict[str, list[str]] = {
    "Luján de Cuyo": [
        "bodega Luján de Cuyo Mendoza",
        "winery Luján de Cuyo Mendoza",
        "bodega visitas degustación Luján de Cuyo",
        "bodega Agrelo Mendoza",
        "bodega Perdriel Mendoza",
        "bodega Vistalba Mendoza",
    ],
    "Maipú": [
        "bodega Maipú Mendoza",
        "winery Maipú Mendoza",
        "bodega visitas degustación Maipú Mendoza",
        "bodega Coquimbito Mendoza",
        "bodega Russell Maipú",
    ],
    "Valle de Uco": [
        "bodega Valle de Uco Mendoza",
        "winery Valle de Uco",
        "bodega Tupungato Mendoza",
        "bodega Tunuyán Mendoza",
        "bodega San Carlos Mendoza",
        "bodega Gualtallary",
        "bodega Los Chacayes",
    ],
}

# --- Crawl -----------------------------------------------------------------
# Una página interna se baja si su URL o el texto del link contiene alguna de estas palabras.
PALABRAS_CLAVE = [
    "visita", "visit", "experiencia", "experience", "turismo", "tourism", "tour",
    "degusta", "tasting", "cata", "restaurant", "restaurante", "almuerzo", "lunch",
    "gastronom", "reserva", "booking", "book", "enoturismo", "wine-tour", "picnic",
    "maridaje", "pairing", "horario", "hours", "contacto", "contact", "tarifa", "precio",
    "price", "actividades", "activities", "bodega", "winery", "nosotros", "about",
    # francés (Borgoña)
    "visite", "degustation", "dégustation", "caveau", "cave", "horaires", "tarif", "oenotourisme",
    "œnotourisme", "domaine", "boutique", "accueil", "reservation", "réservation", "acces", "accès",
]
MAX_PAGINAS_POR_BODEGA = 10
PAUSA_ENTRE_PEDIDOS_S = 1.5
TIMEOUT_S = 20
CONTACTO = os.getenv("CONTACT_EMAIL", "sin-contacto@example.com")
USER_AGENT = f"EnotBot/0.1 (proyecto academico IA Agentica UBA; contacto: {CONTACTO})"

# --- Extracción ------------------------------------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai | anthropic | openai_compatible
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")  # para Ollama, OpenRouter, Groq, etc.
MAX_CHARS_POR_BODEGA = int(os.getenv("MAX_CHARS_POR_BODEGA", "60000"))
MAX_TOKENS_SALIDA = 4096

# Precio en USD por millón de tokens, para estimar el costo de la extracción.
# Completar con la página de precios del proveedor que usen (no lo inventamos acá).
# Ejemplo de formato: {"gpt-4o-mini": {"in": 0.0, "out": 0.0}}
PRECIOS_USD_POR_MTOK: dict[str, dict[str, float]] = {}

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# --- Validación manual (paso 5) ---------------------------------------------
# Quién revisa la muestra de cada zona (vacío = sin asignar).
REVISORES: dict[str, str] = {}
UMBRAL_PLAN_B = 0.60  # PRD, sección 7: completitud < 60% en precio u horario => plan B
