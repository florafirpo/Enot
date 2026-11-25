"""Tests del generador del set de evaluación (spec 006, ADR-0007, ADR-0016).

Offline: el parafraseador es una función falsa y el LLM, `ClienteFalso`.
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter

import pytest
from pydantic import ValidationError

from enot.modelos import PerfilViaje
from eval import generador as g
from eval.generador import (
    CUOTAS,
    Consulta,
    SetExistente,
    certificado_infactible,
    conserva_anclas,
    escribir_set,
    generar,
    muestra_revision,
    parafraseador_llm,
    particionar,
    tasa_error_revision,
)


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.casefold())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.split())


def contiene(texto: str, *opciones: str) -> bool:
    """Alguna de las opciones aparece como palabras enteras en el texto (sin mayúsculas ni tildes)."""
    def palabras(t):
        return " " + " ".join(re.findall(r"\d{1,2}:\d{2}|[a-z0-9]+", norm(t))) + " "
    n = palabras(texto)
    return any(palabras(o) in n for o in opciones)


@pytest.fixture
def consultas():
    # por test y no por módulo: mutmut atribuye la llamada a generar() solo al primer test de un fixture de módulo
    return generar()


def consulta(escenario="infactible", **perfil) -> Consulta:
    """Consulta armada a mano para probar el certificado."""
    extras = {k: perfil.pop(k) for k in ("bodegas_por_dia", "zonas_mismo_dia", "infactible", "motivo_infactible")
              if k in perfil}
    base = dict(cantidad_dias=1, dia_inicio="jue", transporte="auto", personas=2)
    base.update(perfil)
    return Consulta(id="q999", escenario=escenario, plantilla="manual", texto="texto de prueba",
                    restricciones=PerfilViaje(**base), anclas=[], **extras)


# --- determinismo, cuotas, unicidad -----------------------------------------------------------------------------

def test_misma_semilla_mismo_set():
    a, b = generar(7), generar(7)
    assert [c.model_dump() for c in a] == [c.model_dump() for c in b]


HUELLA = "eaf68a96e809d9db"  # sha256 (16 primeros) del set de la semilla por defecto, versión 006.2


def test_huella_del_set_por_defecto():
    """El set de la semilla por defecto queda fijo para esta versión del generador: si cambia una plantilla, una
    cuota o el orden de los sorteos, este test obliga a subir VERSION_GENERADOR (el set se versiona, ADR-0007)."""
    import hashlib
    datos = json.dumps([c.model_dump(mode="json") for c in generar()], ensure_ascii=False, sort_keys=True)
    assert (g.VERSION_GENERADOR, hashlib.sha256(datos.encode()).hexdigest()[:16]) == ("006.2", HUELLA)


def test_otra_semilla_otro_set():
    a, b = generar(7), generar(8)
    assert [c.texto for c in a] != [c.texto for c in b]
    assert sum(x.texto != y.texto for x, y in zip(a, b, strict=True)) > 50


def test_cien_consultas_con_cuotas_por_escenario(consultas):
    assert sum(CUOTAS.values()) == 100
    assert CUOTAS == {"dias": 15, "transporte": 15, "presupuesto": 15, "grupo": 15, "idioma": 10,
                      "accesibilidad": 10, "infactible": 20}
    assert len(consultas) == 100
    assert Counter(c.escenario for c in consultas) == CUOTAS


@pytest.mark.parametrize("semilla", [g.SEMILLA, 1, 2, 3, 4, 5])
def test_ninguna_consulta_repetida(semilla):
    textos = [norm(c.texto) for c in generar(semilla)]
    assert len(set(textos)) == len(textos) == 100


def test_ids_unicos_y_correlativos(consultas):
    assert [c.id for c in consultas] == [f"q{i:03d}" for i in range(1, 101)]


# --- la etiqueta coincide con el texto ---------------------------------------------------------------------------

DIA = {"lun": "lunes", "mar": "martes", "mie": "miércoles", "jue": "jueves", "vie": "viernes", "sab": "sábado",
       "dom": "domingo"}
CANT_DIAS = {1: ("un día", "1 día", "un solo día"), 2: ("dos días", "2 días"), 3: ("tres días", "3 días")}
TRANSPORTE = {"auto": ("auto",), "traslado": ("chofer", "traslado"), "bici": ("bici", "bicis"),
              "a_pie": ("a pie", "caminando")}
IDIOMA = {"en": "inglés", "de": "alemán", "es": "español", "it": "italiano", "pt": "portugués", "fr": "francés"}
ZONA_CORTA = {"Côte de Nuits": "Côte de Nuits", "Côte de Beaune": "Côte de Beaune", "Hautes-Côtes": "Hautes-Côtes",
              "Chablis y Grand Auxerrois": "Chablis", "Côte Chalonnaise": "Côte Chalonnaise",
              "Mâconnais": "Mâconnais"}


def personas_en_texto(texto: str, n: int) -> bool:
    if n == 1:
        return contiene(texto, "viajo solo", "viajo sola", "voy solo", "voy sola")
    if n == 2:
        return contiene(texto, "dos", "2")
    return contiene(texto, str(n))


def test_texto_contiene_los_datos_obligatorios(consultas):
    for c in consultas:
        r = c.restricciones
        assert contiene(c.texto, DIA[r.dia_inicio]), (c.id, c.texto)
        assert contiene(c.texto, *CANT_DIAS[r.cantidad_dias]), (c.id, c.texto)
        assert contiene(c.texto, *TRANSPORTE[r.transporte]), (c.id, c.texto)
        assert personas_en_texto(c.texto, r.personas), (c.id, c.texto)


def test_etiqueta_coincide_con_el_texto_por_escenario(consultas):
    for c in consultas:
        r = c.restricciones
        if r.presupuesto_max_por_persona is not None:
            assert contiene(c.texto, str(int(r.presupuesto_max_por_persona))), (c.id, c.texto)
        for i in r.idiomas:
            assert contiene(c.texto, IDIOMA[i]), (c.id, c.texto)
        assert r.movilidad_reducida == contiene(c.texto, "silla de ruedas", "movilidad reducida"), (c.id, c.texto)
        for z in r.zonas_preferidas:
            assert contiene(c.texto, ZONA_CORTA.get(z, z)), (c.id, c.texto)
        if (r.hora_inicio_jornada, r.hora_fin_jornada) != ("09:30", "18:30"):
            assert contiene(c.texto, r.hora_inicio_jornada) and contiene(c.texto, r.hora_fin_jornada), (c.id, c.texto)
        if c.bodegas_por_dia is not None:
            assert contiene(c.texto, f"{c.bodegas_por_dia} bodegas"), (c.id, c.texto)
    por = {e: [c for c in consultas if c.escenario == e] for e in CUOTAS}
    assert all(c.restricciones.presupuesto_max_por_persona is not None for c in por["presupuesto"])
    assert all(c.restricciones.idiomas for c in por["idioma"])
    assert all(c.restricciones.movilidad_reducida for c in por["accesibilidad"])
    fuera = [c for e, cs in por.items() if e not in {"presupuesto"} for c in cs]
    assert all(c.restricciones.presupuesto_max_por_persona is None for c in fuera)
    assert not any(c.restricciones.movilidad_reducida for e, cs in por.items() if e != "accesibilidad" for c in cs)


def test_escenarios_varian_su_dimension(consultas):
    por = {e: [c.restricciones for c in consultas if c.escenario == e] for e in CUOTAS}
    assert {r.cantidad_dias for r in por["dias"]} == {1, 2, 3}
    assert len({r.dia_inicio for r in por["dias"]}) >= 3
    assert any((r.hora_inicio_jornada, r.hora_fin_jornada) != ("09:30", "18:30") for r in por["dias"])
    assert {r.transporte for r in por["transporte"]} == {"auto", "traslado", "bici", "a_pie"}
    assert len({r.presupuesto_max_por_persona for r in por["presupuesto"]}) >= 3
    assert len({r.personas for r in por["grupo"]}) >= 3
    assert all(r.personas >= 6 for r in por["grupo"])
    assert len({tuple(r.idiomas) for r in por["idioma"]}) >= 3
    otros = [r for e, rs in por.items() if e not in {"grupo", "accesibilidad"} for r in rs]
    assert all(r.personas <= 4 for r in otros)
    assert any(r.personas == 1 for r in otros) and any(r.personas == 2 for r in otros)
    con_pref = [c for c in consultas if not c.infactible and c.restricciones.preferencias]
    assert 10 <= len(con_pref) <= 70


PLURAL = ("tenemos", "queremos", "nos movemos", "buscamos", "preferimos", "tomamos", "hablamos", "llegamos",
          "empezamos", "podemos", "nos interesa", "nos encanta", "nos gustaria", "vamos", "somos")


@pytest.mark.parametrize("semilla", [g.SEMILLA, 1, 2])
def test_una_persona_habla_en_singular(semilla):
    cs = generar(semilla)
    solos = [c for c in cs if c.restricciones.personas == 1]
    assert len(solos) >= 5
    for c in solos:
        assert not contiene(c.texto, *PLURAL), (c.id, c.texto)
    # el plural sigue ahí para los grupos (no se "arregló" pasando todo a singular)
    assert sum(contiene(c.texto, *PLURAL) for c in cs if c.restricciones.personas > 1) >= 60
    assert not any("[" in c.texto or "]" in c.texto or "|" in c.texto for c in cs)


def test_bici_y_a_pie_factibles_con_una_sola_zona(consultas):
    lentas = [c for c in consultas if not c.infactible and c.restricciones.transporte in {"bici", "a_pie"}]
    assert lentas
    assert all(len(c.restricciones.zonas_preferidas) == 1 for c in lentas)
    assert all(z in ZONA_CORTA for c in consultas if not c.infactible for z in c.restricciones.zonas_preferidas)


# --- infactibles y su certificado --------------------------------------------------------------------------------

def test_infactibles_tienen_certificado(consultas):
    infactibles = [c for c in consultas if c.infactible]
    assert len(infactibles) == 20 and all(c.escenario == "infactible" for c in infactibles)
    for c in infactibles:
        assert certificado_infactible(c), (c.id, c.texto)


def test_factibles_no_tienen_certificado(consultas):
    factibles = [c for c in consultas if not c.infactible]
    assert len(factibles) == 80
    for c in factibles:
        assert certificado_infactible(c) is None, (c.id, c.texto)


def test_infactibles_cubren_los_tres_motivos(consultas):
    motivos = Counter(c.motivo_infactible for c in consultas if c.infactible)
    assert set(motivos) == {"demasiadas_bodegas", "zonas_lejanas", "zona_fuera_de_borgona"}
    assert all(n >= 6 for n in motivos.values())
    for c in consultas:
        if c.motivo_infactible == "demasiadas_bodegas":
            assert c.bodegas_por_dia and c.restricciones.cantidad_dias == 1
        if c.motivo_infactible == "zonas_lejanas":
            assert len(c.zonas_mismo_dia) == 2 and c.restricciones.transporte in {"bici", "a_pie"}
            assert c.restricciones.cantidad_dias == 1


def test_certificado_demasiadas_bodegas_borde():
    assert g.VISITA_MINIMA_MIN == 30
    justo = consulta(bodegas_por_dia=6, hora_inicio_jornada="10:00", hora_fin_jornada="13:00")
    assert certificado_infactible(justo) is None
    pasado = consulta(bodegas_por_dia=7, hora_inicio_jornada="10:00", hora_fin_jornada="13:00")
    texto = certificado_infactible(pasado)
    assert texto and "7" in texto and "180" in texto and "210" in texto
    assert certificado_infactible(consulta(bodegas_por_dia=None, hora_inicio_jornada="10:00",
                                           hora_fin_jornada="10:30")) is None
    # varios días no cambian la cota: bodegas_por_dia es por día
    assert certificado_infactible(consulta(cantidad_dias=3, bodegas_por_dia=7, hora_inicio_jornada="10:00",
                                           hora_fin_jornada="13:00"))


def test_certificado_zonas_lejanas():
    lejos = ["Chablis y Grand Auxerrois", "Mâconnais"]
    a_pie = consulta(transporte="a_pie", zonas_preferidas=lejos, zonas_mismo_dia=lejos)
    texto = certificado_infactible(a_pie)
    assert texto and "Chablis" in texto and "Mâconnais" in texto
    assert certificado_infactible(consulta(transporte="bici", zonas_preferidas=lejos, zonas_mismo_dia=lejos))
    assert certificado_infactible(consulta(transporte="auto", zonas_preferidas=lejos, zonas_mismo_dia=lejos)) is None
    cerca = ["Côte de Nuits", "Côte de Beaune"]
    assert certificado_infactible(consulta(transporte="bici", zonas_preferidas=cerca, zonas_mismo_dia=cerca)) is None
    assert certificado_infactible(consulta(transporte="a_pie", zonas_preferidas=lejos[:1],
                                           zonas_mismo_dia=lejos[:1])) is None
    # pedir las dos zonas sin exigirlas el mismo día no es infactible
    assert certificado_infactible(consulta(transporte="a_pie", zonas_preferidas=lejos)) is None
    # la jornada importa: Chablis–Côte Chalonnaise en bici entra en 9 h por el par de comunas más cercano
    medio = ["Chablis y Grand Auxerrois", "Côte Chalonnaise"]
    assert certificado_infactible(consulta(transporte="bici", zonas_preferidas=medio, zonas_mismo_dia=medio)) is None
    assert certificado_infactible(consulta(transporte="bici", zonas_preferidas=medio, zonas_mismo_dia=medio,
                                           hora_inicio_jornada="10:00", hora_fin_jornada="14:00"))


def test_certificado_zonas_lejanas_minutos_y_borde():
    """Los minutos salen del par de comunas más cercano con las constantes de la tool; jornada igual no alcanza."""
    import itertools

    from enot.tools.distancias import FACTOR_RUTA, VELOCIDAD_KMH, haversine_km
    za, zb = "Chablis y Grand Auxerrois", "Mâconnais"
    km, a, b = min((haversine_km(*ca, *cb), na, nb) for (na, ca), (nb, cb) in
                   itertools.product(g.REFERENCIAS_ZONA[za].items(), g.REFERENCIAS_ZONA[zb].items()))
    esperado = round(km * FACTOR_RUTA / VELOCIDAD_KMH["bici"] * 60)
    texto = certificado_infactible(consulta(transporte="bici", zonas_preferidas=[za, zb], zonas_mismo_dia=[za, zb]))
    assert f"{esperado} min" in texto and a in texto and b in texto and "540" in texto
    assert (a, b) == ("Vézelay", "Tournus")
    # con una jornada exactamente igual al traslado, entra; con un minuto menos, no
    from enot.modelos import a_hora
    igual = consulta(transporte="bici", zonas_preferidas=[za, zb], zonas_mismo_dia=[za, zb],
                     hora_inicio_jornada="06:00", hora_fin_jornada=a_hora(360 + esperado))
    assert certificado_infactible(igual) is None
    menos = consulta(transporte="bici", zonas_preferidas=[za, zb], zonas_mismo_dia=[za, zb],
                     hora_inicio_jornada="06:01", hora_fin_jornada=a_hora(360 + esperado))
    assert certificado_infactible(menos)


def test_certificado_zona_fuera():
    texto = certificado_infactible(consulta(zonas_preferidas=["Champagne"]))
    assert texto and "Champagne" in texto
    assert "Jura, Burdeos" in certificado_infactible(consulta(zonas_preferidas=["Jura", "Chablis", "Burdeos"]))
    assert certificado_infactible(consulta(zonas_preferidas=["Chablis"])) is None
    assert certificado_infactible(consulta(zonas_preferidas=["Côte de Beaune", "cote de nuits"])) is None
    assert certificado_infactible(consulta(zonas_preferidas=["Côte de Beaune", "Jura"]))
    assert certificado_infactible(consulta(zonas_preferidas=[])) is None


def test_consulta_valida_motivo_con_infactible():
    with pytest.raises(ValidationError):
        consulta(infactible=True)
    with pytest.raises(ValidationError):
        consulta(infactible=False, motivo_infactible="zonas_lejanas")
    assert consulta(infactible=True, motivo_infactible="zonas_lejanas").infactible


# --- partición y muestra ------------------------------------------------------------------------------------------

def test_particion_60_40_estratificada(consultas):
    dev, test = particionar(consultas)
    assert len(dev) == 60 and len(test) == 40
    assert not {c.id for c in dev} & {c.id for c in test}
    assert sorted(c.id for c in dev + test) == [c.id for c in consultas]
    cdev, ctest = Counter(c.escenario for c in dev), Counter(c.escenario for c in test)
    for e, n in CUOTAS.items():
        assert cdev[e] == n * 3 // 5 and ctest[e] == n * 2 // 5
    assert [c.id for c in dev] == sorted(c.id for c in dev)


def test_particion_determinista(consultas):
    a, b = particionar(consultas, semilla=3), particionar(consultas, semilla=3)
    assert [c.id for c in a[0]] == [c.id for c in b[0]]
    otra = particionar(consultas, semilla=4)
    assert [c.id for c in a[0]] != [c.id for c in otra[0]]


def test_muestra_revision_20_por_ciento_estratificada(consultas):
    dev, test = particionar(consultas)
    muestra = muestra_revision(dev, test)
    assert len(muestra) == 20
    ids = [c.id for _, c in muestra]
    assert len(set(ids)) == 20
    assert Counter(c.escenario for _, c in muestra) == {e: n // 5 for e, n in CUOTAS.items()}
    ids_dev, ids_test = {c.id for c in dev}, {c.id for c in test}
    for particion, c in muestra:
        assert c.id in (ids_dev if particion == "dev" else ids_test)
    assert Counter(p for p, _ in muestra) == {"dev": 12, "test": 8}
    assert [c.id for _, c in muestra_revision(dev, test)] == ids


# --- escritura ----------------------------------------------------------------------------------------------------

def _cargar(ruta):
    return [Consulta.model_validate_json(linea) for linea in ruta.read_text(encoding="utf-8").splitlines() if linea]


def test_escribir_set_crea_archivos(tmp_path):
    resumen = escribir_set(tmp_path / "eval", semilla=11)
    base = tmp_path / "eval"
    dev, test = _cargar(base / "dev" / "consultas.jsonl"), _cargar(base / "test" / "consultas.jsonl")
    esperado_dev, esperado_test = particionar(generar(11), semilla=11)
    assert [c.model_dump() for c in dev] == [c.model_dump() for c in esperado_dev]
    assert [c.model_dump() for c in test] == [c.model_dump() for c in esperado_test]
    assert (resumen.dev, resumen.test, resumen.revision) == (60, 40, 20)

    with open(base / "revision_manual.csv", encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    assert len(filas) == 20
    assert {"id", "particion", "escenario", "plantilla", "texto", "restricciones", "infactible",
            "motivo_infactible", "correcta", "comentario"} <= set(filas[0])
    assert all(f["correcta"] == "" and f["comentario"] == "" for f in filas)
    por_id = {c.id: c for c in dev + test}
    assert [(f["particion"], f["id"]) for f in filas] == [(p, c.id) for p, c in muestra_revision(dev, test, 11)]
    for f in filas:
        c = por_id[f["id"]]
        assert json.loads(f["restricciones"]) == c.restricciones.model_dump(mode="json")
        assert (f["escenario"], f["plantilla"], f["texto"]) == (c.escenario, c.plantilla, c.texto)
        assert f["infactible"] == ("sí" if c.infactible else "no")
        assert f["motivo_infactible"] == (c.motivo_infactible or "")
        assert f["bodegas_por_dia"] == (str(c.bodegas_por_dia) if c.bodegas_por_dia else "")
        assert f["zonas_mismo_dia"] == "; ".join(c.zonas_mismo_dia)
    assert any(f["infactible"] == "sí" and f["motivo_infactible"] for f in filas)
    assert any(f["bodegas_por_dia"] for f in filas) or any(f["zonas_mismo_dia"] for f in filas)

    meta = json.loads((base / "generacion.json").read_text(encoding="utf-8"))
    assert meta == {
        "version": g.VERSION_GENERADOR, "semilla": 11, "cuotas": CUOTAS, "fraccion_dev": 0.6,
        "fraccion_revision": 0.2, "visita_minima_min": 30,
        "conteos": {"dev": {e: n * 3 // 5 for e, n in CUOTAS.items()},
                    "test": {e: n * 2 // 5 for e, n in CUOTAS.items()}},
        "infactibles": {"dev": 12, "test": 8},
        "parafrasis": {"no": 100, "aceptada": 0, "rechazada": 0},
    }


@pytest.mark.parametrize("existente", ["test", "dev"])
def test_escribir_set_no_pisa_test(tmp_path, existente):
    base = tmp_path / "eval"
    (base / existente).mkdir(parents=True)
    previo = base / existente / "consultas.jsonl"
    previo.write_bytes(b'{"original": true}\n')
    with pytest.raises(SetExistente):
        escribir_set(base)
    assert previo.read_bytes() == b'{"original": true}\n'
    otra = "dev" if existente == "test" else "test"
    assert not (base / otra).exists()
    assert not (base / "revision_manual.csv").exists() and not (base / "generacion.json").exists()


def test_escribir_set_falla_a_mitad_no_deja_nada(tmp_path, monkeypatch):
    base = tmp_path / "eval"

    def falla(*a, **k):
        raise OSError("disco lleno")
    monkeypatch.setattr(g.json, "dumps", falla)
    with pytest.raises(OSError):
        escribir_set(base)
    assert not (base / "dev").exists() and not (base / "test").exists()
    assert not (base / "revision_manual.csv").exists()
    assert not base.exists() or list(base.iterdir()) == []
    monkeypatch.undo()
    assert escribir_set(base).test == 40
    assert sorted(p.name for p in base.iterdir()) == ["dev", "generacion.json", "revision_manual.csv", "test"]


def test_tasa_error_revision(tmp_path):
    ruta = tmp_path / "rev.csv"
    filas = [("q001", "dias", "no"), ("q005", "grupo", ""), ("q002", "dias", "Sí"), ("q003", "idioma", "no"),
             ("q004", "idioma", "si"), ("q006", "idioma", "ok")]
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "escenario", "correcta", "comentario"])
        for i, e, ok in filas:
            w.writerow([i, e, ok, ""])
    r = tasa_error_revision(ruta)
    assert (r.revisadas, r.con_error, r.tasa_error) == (5, 2, 0.4)
    assert r.por_escenario == {"dias": {"revisadas": 2, "con_error": 1}, "idioma": {"revisadas": 3, "con_error": 1}}

    with open(ruta, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([["id", "escenario", "correcta"], ["q1", "dias", " "]])
    vacia = tasa_error_revision(ruta)
    assert (vacia.revisadas, vacia.con_error, vacia.tasa_error) == (0, 0, None)

    with open(ruta, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([["id", "escenario", "correcta"], ["q1", "dias", "tal vez"]])
    with pytest.raises(ValueError, match="q1"):
        tasa_error_revision(ruta)


def test_tasa_error_revision_sobre_el_csv_generado(tmp_path):
    escribir_set(tmp_path / "eval")
    r = tasa_error_revision(tmp_path / "eval" / "revision_manual.csv")
    assert (r.revisadas, r.tasa_error) == (0, None)


# --- paráfrasis ---------------------------------------------------------------------------------------------------

def test_conserva_anclas():
    anclas = ["jueves", "2", "Côte de Beaune", "18:30"]
    assert conserva_anclas("El JUEVES arrancamos, somos 2, cote de beaune hasta las 18:30.", anclas)
    assert not conserva_anclas("El jueves arrancamos, somos 12, Côte de Beaune hasta las 18:30.", anclas)
    assert not conserva_anclas("El viernes arrancamos, somos 2, Côte de Beaune hasta las 18:30.", anclas)
    assert not conserva_anclas("El jueves, somos 2, Côte de Beaune hasta las 18.", anclas)
    assert conserva_anclas("cualquier cosa", [])


def test_parafrasis_aceptada_y_rechazada():
    base = generar(5)
    buena = generar(5, parafraseador=lambda t: "Hola, te cuento: " + t)
    assert all(c.parafrasis == "aceptada" for c in buena)
    for b, p in zip(base, buena, strict=True):
        assert p.texto == "Hola, te cuento: " + b.texto and p.texto_plantilla == b.texto
        assert p.restricciones == b.restricciones and p.anclas == b.anclas and p.infactible == b.infactible

    def cambia_numeros(t: str) -> str:
        return re.sub(r"\d+", "99", t) + " Gracias."
    mala = generar(5, parafraseador=cambia_numeros)
    con_numeros = [(b, m) for b, m in zip(base, mala, strict=True) if re.search(r"\d", b.texto)]
    assert con_numeros
    for b, m in con_numeros:
        assert m.parafrasis == "rechazada" and m.texto == b.texto and m.texto_plantilla is None
        assert m.restricciones == b.restricciones
    assert all(c.parafrasis == "no" and c.texto_plantilla is None for c in base)


def test_parafrasis_duplicada_se_rechaza(monkeypatch):
    monkeypatch.setattr(g, "conserva_anclas", lambda parafrasis, anclas: True)
    res = generar(5, parafraseador=lambda t: "Quiero visitar bodegas.")
    assert [c.parafrasis for c in res] == ["aceptada"] + ["rechazada"] * 99
    assert res[0].texto == "Quiero visitar bodegas."
    assert len({norm(c.texto) for c in res}) == 100

    # tampoco se acepta una paráfrasis igual al texto de plantilla de otra consulta
    base = generar(5)
    copia = {base[i].texto: base[i + 1].texto for i in range(len(base) - 1)}
    res = generar(5, parafraseador=lambda t: copia.get(t, t + " Gracias."))
    assert len({norm(c.texto) for c in res}) == 100
    assert res[0].parafrasis == "rechazada"


def test_parafrasis_que_falla_deja_la_plantilla():
    def explota(t):
        raise RuntimeError("sin red")
    res = generar(5, parafraseador=explota)
    assert all(c.parafrasis == "rechazada" for c in res)
    assert [c.texto for c in res] == [c.texto for c in generar(5)]


def test_parafraseador_llm_usa_el_cliente(cliente_falso):
    cliente = cliente_falso([{"texto": "Che, somos dos y arrancamos el jueves."}])
    parafrasear = parafraseador_llm(cliente)
    assert parafrasear("Somos dos, arrancamos el jueves.") == "Che, somos dos y arrancamos el jueves."
    assert "Somos dos, arrancamos el jueves." in cliente.llamadas[0]["usuario"]
    assert "número" in cliente.llamadas[0]["sistema"].casefold() or "numero" in cliente.llamadas[0]["sistema"]


# --- CLI ----------------------------------------------------------------------------------------------------------

def test_main_escribe_y_devuelve_0(tmp_path, capsys):
    assert g.main(["--destino", str(tmp_path / "eval"), "--semilla", "3"]) == 0
    assert len(_cargar(tmp_path / "eval" / "dev" / "consultas.jsonl")) == 60
    meta = json.loads((tmp_path / "eval" / "generacion.json").read_text(encoding="utf-8"))
    assert meta["semilla"] == 3
    assert "60" in capsys.readouterr().out


def test_main_usa_la_semilla_por_defecto(tmp_path):
    assert g.main(["--destino", str(tmp_path / "eval")]) == 0
    meta = json.loads((tmp_path / "eval" / "generacion.json").read_text(encoding="utf-8"))
    assert meta["semilla"] == g.SEMILLA == 2026


def test_main_destino_por_defecto_es_data_eval(entorno):
    from corpus import config
    assert g.main([]) == 0
    assert (config.DATA / "eval" / "test" / "consultas.jsonl").exists()


def test_main_con_set_existente_devuelve_1(tmp_path, capsys):
    (tmp_path / "eval" / "test").mkdir(parents=True)
    assert g.main(["--destino", str(tmp_path / "eval")]) == 1
    assert "test" in capsys.readouterr().err
    assert not (tmp_path / "eval" / "dev").exists()


def test_main_parafrasear_sin_cliente_usa_cliente_llm(tmp_path, cliente_falso):
    creados = []

    def fabrica():
        c = cliente_falso([lambda s, u: {"texto": u.split("\n")[-1] + " ¡Gracias!"}])
        creados.append(c)
        return c
    assert g.main(["--destino", str(tmp_path / "eval"), "--parafrasear"], crear_cliente=fabrica) == 0
    assert len(creados) == 1 and len(creados[0].llamadas) == 100
    meta = json.loads((tmp_path / "eval" / "generacion.json").read_text(encoding="utf-8"))
    assert meta["parafrasis"]["aceptada"] == 100


def test_main_sin_parafrasear_no_crea_cliente(tmp_path):
    def fabrica():
        raise AssertionError("no debería crear el cliente")
    assert g.main(["--destino", str(tmp_path / "eval")], crear_cliente=fabrica) == 0
