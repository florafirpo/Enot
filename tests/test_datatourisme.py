"""Adaptador DATAtourisme (ADR-0002). El CSV de fixtures es SINTÉTICO: imita el formato documentado
en data.gouv.fr ('|' separa objetos, '#' propiedades, '<>' valores) con bodegas inventadas."""
from __future__ import annotations

import csv
import json

import pytest

from corpus import config
from corpus import datatourisme as dt
from corpus.utils import leer_csv

from .conftest import FIXTURES

CSV = FIXTURES / "datatourisme_simulado.csv"


def test_detecta_columnas_con_nombres_de_datatourisme():
    encabezados = ["Nom_du_POI", "Categories_de_POI", "Latitude", "Longitude", "Adresse_postale",
                   "Code_postal_et_commune", "Description", "Contacts_du_POI", "URI_ID_du_POI"]
    col = dt.detectar_columnas(encabezados)
    assert col["nombre"] == "Nom_du_POI"
    assert col["tipos"] == "Categories_de_POI"
    assert col["lat"] == "Latitude" and col["lon"] == "Longitude"
    assert col["cp_comuna"] == "Code_postal_et_commune"
    assert col["uri"] == "URI_ID_du_POI"
    assert col["clasificaciones"] is None


@pytest.mark.parametrize("tipos,nombre,desc,esperado", [
    ("https://www.datatourisme.fr/ontology/core#Cellar", "Domaine X", "", (True, "cellar")),
    ("core#Cooperative|core#TastingProvider", "Cave de Lugny", "vins du Mâconnais", (True, "proveedor_con_vino")),
    ("core#Producer|core#TastingProvider", "Fromagerie", "fabrication de l'Époisses", (False, "")),
    ("core#Restaurant", "Bistrot", "carte des vins", (False, "")),
])
def test_es_bodega(tipos, nombre, desc, esperado):
    assert dt.es_bodega(tipos, nombre, desc) == esperado


@pytest.mark.parametrize("comuna,depto,lat,zona", [
    ("Gevrey-Chambertin", "21", 47.22, "Côte de Nuits"),
    ("Pommard", "21", 47.01, "Côte de Beaune"),
    ("Chablis", "89", 47.81, "Chablis y Grand Auxerrois"),
    ("Lugny", "71", 46.47, "Mâconnais"),
    ("Pueblo Desconocido", "21", 47.20, "Côte de Nuits"),     # por latitud
    ("Pueblo Desconocido", "21", 47.00, "Côte de Beaune"),    # por latitud
    ("Pueblo Desconocido", "71", 46.70, "Côte Chalonnaise"),  # por latitud
])
def test_subzona(comuna, depto, lat, zona):
    assert dt.subzona(comuna, depto, lat) == zona


def test_cp_y_comuna_con_formato_multivalor():
    assert dt.cp_y_comuna("21220#Gevrey-Chambertin") == ("21220", "Gevrey-Chambertin")
    assert dt.cp_y_comuna("", "4 rue X, 21630 Pommard") == ("21630", "Pommard")
    assert dt.cp_y_comuna("") == ("", "")


def test_web_principal_prefiere_la_propia_sobre_redes():
    contacto = "#https://www.facebook.com/x|#+33 3 80#https://www.domaine.example"
    assert dt.web_principal(contacto) == "https://www.domaine.example"


def test_legible_saca_prefijo_de_ontologia_y_props_vacias():
    v = "https://www.datatourisme.fr/ontology/core#Cellar|#+33 1#mail@x.fr"
    assert dt.legible(v) == "Cellar\n- +33 1 · mail@x.fr"


def test_run_filtra_deduplica_y_escribe_semilla_y_texto(entorno):
    dt.run(str(CSV))
    semilla = leer_csv(config.SEED_CSV)
    nombres = {f["nombre"] for f in semilla}
    # entran caves y cooperativa con vino; quedan afuera queso, restaurante, Jura y el duplicado
    assert nombres == {"Domaine Rossignol-Trapet", "Cave de Lugny", "Château de Pommard",
                       "Domaine Laroche", "Domaine du Village Raro"}
    assert len(semilla) == 5
    rt = next(f for f in semilla if f["nombre"] == "Domaine Rossignol-Trapet")
    assert rt["zona"] == "Côte de Nuits"
    assert rt["url_web"] == "https://www.rossignol-trapet.example"
    assert float(rt["lat"]) == pytest.approx(47.2245)
    md = (config.CLEAN_DIR / f"{rt['id']}.md").read_text(encoding="utf-8")
    assert "20 € par personne" in md
    base = json.loads((config.BASE_DIR / f"{rt['id']}.json").read_text(encoding="utf-8"))
    assert base[0]["url"].startswith("https://data.datatourisme.fr/")


def test_run_conserva_ediciones_manuales(entorno):
    dt.run(str(CSV))
    filas = leer_csv(config.SEED_CSV)
    for f in filas:
        if f["nombre"] == "Domaine du Village Raro":
            f["abre_turismo"], f["notas"] = "no", "cerrado al público"
    with config.SEED_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    dt.run(str(CSV))
    raro = next(f for f in leer_csv(config.SEED_CSV) if f["nombre"] == "Domaine du Village Raro")
    assert raro["abre_turismo"] == "no" and raro["notas"] == "cerrado al público"


def test_run_por_departamento(entorno):
    dt.run(str(CSV), departamentos=["89"])
    assert [f["nombre"] for f in leer_csv(config.SEED_CSV)] == ["Domaine Laroche"]
