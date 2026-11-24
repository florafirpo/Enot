"""Spec 003: retrieval híbrido (ADR-0004). Bodegas SINTÉTICAS salvo el test con la muestra real de DATAtourisme."""
from __future__ import annotations

import contextlib
import csv
import io
import json
import math
import types
from pathlib import Path

import numpy as np
import pytest

from enot.modelos import Bodega, Experiencia, Horario, PerfilViaje
from enot.retrieval import (
    BM25,
    Candidata,
    EmbedderConCache,
    EmbedderOpenAI,
    Indice,
    consulta_desde_perfil,
    dias_del_viaje,
    filtrar,
    motivo_exclusion,
    rrf,
    texto_bodega,
    tokenizar,
)

from .dobles import EmbedderFalso

TODOS = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
MUESTRA = Path(__file__).resolve().parents[1] / "data" / "datatourisme" / "muestra.csv"


def bodega(id_: str, **campos) -> Bodega:
    """Bodega inventada, abierta todos los días, sin datos de capacidad, accesibilidad ni idiomas."""
    base = dict(id=id_, nombre=f"[SINTÉTICA] {id_}", zona="Côte de Beaune", comuna="Beaune",
                lat=47.0, lon=4.8, horarios=[Horario(dias=TODOS, apertura="09:00", cierre="19:00")])
    base.update(campos)
    return Bodega(**base)


def exp(nombre: str, precio: float | None = 20, moneda: str | None = "EUR", idiomas=None, **kw) -> Experiencia:
    return Experiencia(nombre=nombre, tipo=kw.pop("tipo", "degustacion"), duracion_min=60,
                       precio_por_persona=precio, moneda=moneda, idiomas=idiomas or [], **kw)


def perfil(**campos) -> PerfilViaje:
    base = dict(cantidad_dias=1, dia_inicio="lun", transporte="auto", personas=2)
    base.update(campos)
    return PerfilViaje(**base)


def ids(bodegas) -> list[str]:
    return [b.id for b in bodegas]


# --- tokenizar y BM25 --------------------------------------------------------------------

def test_tokenizar_saca_tildes_y_mayusculas():
    assert tokenizar("Côte de BEAUNE, Mâcon!") == ["cote", "de", "beaune", "macon"]
    assert tokenizar("1er cru: Pouilly-Fuissé") == ["1er", "cru", "pouilly", "fuisse"]
    assert tokenizar("") == []


# Corpus a mano: d0 = vino tinto · d1 = vino blanco blanco · d2 = queso. N = 3, largo medio = 2.
DOCS = [["vino", "tinto"], ["vino", "blanco", "blanco"], ["queso"]]


def test_bm25_idf_a_mano():
    bm = BM25(DOCS)
    # idf = ln((N - n + 0.5) / (n + 0.5) + 1)
    assert bm.idf("blanco") == pytest.approx(math.log(2.5 / 1.5 + 1))   # n = 1 → 0.98083
    assert bm.idf("vino") == pytest.approx(math.log(1.5 / 2.5 + 1))     # n = 2 → 0.47000
    assert bm.idf("blanco") == pytest.approx(0.98083, abs=1e-5)
    assert bm.idf("vino") == pytest.approx(0.47000, abs=1e-5)


def test_bm25_puntaje_a_mano():
    bm = BM25(DOCS)  # k1 = 1.5, b = 0.75
    # d1, "blanco": tf = 2, |d| = 3 → 2·2.5 / (2 + 1.5·(0.25 + 0.75·3/2)) = 5 / 4.0625 = 1.230769
    # score = 0.980829 · 1.230769 = 1.207174
    assert bm.puntajes(["blanco"]) == pytest.approx([0.0, 1.207174, 0.0], abs=1e-5)
    # "vino": d0 tf=1, |d|=2 → 2.5/(1+1.5) = 1 → 0.470004 ; d1 tf=1, |d|=3 → 2.5/(1+2.0625) = 0.816327 → 0.383677
    assert bm.puntajes(["vino"]) == pytest.approx([0.470004, 0.383677, 0.0], abs=1e-5)
    # la consulta suma término a término
    assert bm.puntajes(["vino", "blanco"])[1] == pytest.approx(1.207174 + 0.383677, abs=1e-5)


def test_bm25_satura_y_normaliza_por_largo():
    bm = BM25([["kiwi"], ["kiwi"] * 10, ["kiwi", "x", "y", "z"], ["otro"]])
    uno, diez, largo, _ = bm.puntajes(["kiwi"])
    assert diez > uno            # más frecuencia, más puntaje...
    assert diez < 10 * uno       # ...pero no proporcional (saturación)
    assert diez < (1.5 + 1) * bm.idf("kiwi")   # cota k1 + 1
    assert largo < uno           # misma frecuencia en un documento más largo puntúa menos
    sin_largo = BM25([["kiwi"], ["kiwi", "x", "y", "z"], ["otro"]], b=0)
    assert sin_largo.puntajes(["kiwi"])[0] == pytest.approx(sin_largo.puntajes(["kiwi"])[1])


def test_bm25_termino_desconocido_da_cero():
    bm = BM25(DOCS)
    assert bm.idf("chablis") == pytest.approx(math.log(3.5 / 0.5 + 1))
    assert bm.puntajes(["chablis"]) == [0.0, 0.0, 0.0]
    assert bm.puntajes([]) == [0.0, 0.0, 0.0]


def test_bm25_corpus_vacio():
    assert BM25([]).puntajes(["vino"]) == []
    assert BM25([[]]).puntajes(["vino"]) == [0.0]


# --- RRF ---------------------------------------------------------------------------------

def test_rrf_ejemplo_de_clase():
    # clase del 01/10: c = 60, top 2 de cada método. BM25: A, B (C afuera); embeddings: C, B (A afuera)
    r = rrf([["A", "B", "C"], ["C", "B", "A"]], c=60, top=2)
    assert [d for d, _ in r] == ["B", "A", "C"]
    puntajes = dict(r)
    assert puntajes["B"] == pytest.approx(2 / 62)
    assert puntajes["A"] == pytest.approx(1 / 61) and puntajes["C"] == pytest.approx(1 / 61)


def test_rrf_sin_top_usa_todo():
    r = dict(rrf([["A", "B", "C"], ["C", "B", "A"]]))
    assert r["A"] == pytest.approx(1 / 61 + 1 / 63)
    assert r["B"] == pytest.approx(2 / 62)
    assert r["C"] == pytest.approx(1 / 63 + 1 / 61)


def test_rrf_c_cambia_los_puntajes():
    r = dict(rrf([["A", "B"]], c=0))
    assert r == pytest.approx({"A": 1.0, "B": 0.5})
    # un documento en un solo ranking suma solo ese aporte
    assert dict(rrf([["A"], ["B"]], c=10)) == pytest.approx({"A": 1 / 11, "B": 1 / 11})


def test_rrf_desempate_por_id():
    assert [d for d, _ in rrf([["zeta", "alfa"], ["alfa", "zeta"]])] == ["alfa", "zeta"]
    assert [d for d, _ in rrf([["b"], ["a"]])] == ["a", "b"]


def test_rrf_vacio():
    assert rrf([]) == []
    assert rrf([[], []]) == []


# --- filtros duros -----------------------------------------------------------------------

def test_dias_del_viaje():
    assert dias_del_viaje(perfil(cantidad_dias=3, dia_inicio="sab")) == ["sab", "dom", "lun"]
    assert dias_del_viaje(perfil(cantidad_dias=1, dia_inicio="mie")) == ["mie"]


def test_filtro_bodegas_evitar():
    bs = [bodega("a"), bodega("b", nombre="Domaine Famoso"), bodega("c")]
    assert ids(filtrar(bs, perfil(bodegas_evitar=["a", "domaine famoso"]))) == ["c"]
    assert ids(filtrar(bs, perfil(bodegas_evitar=[]))) == ["a", "b", "c"]


def test_filtro_zona():
    bs = [bodega("a", zona="Côte de Nuits"), bodega("b", zona="Chablis y Grand Auxerrois"), bodega("c", zona="")]
    assert ids(filtrar(bs, perfil(zonas_preferidas=["cote de nuits"]))) == ["a"]
    assert ids(filtrar(bs, perfil(zonas_preferidas=["Côte de Nuits", "Chablis y Grand Auxerrois"]))) == ["a", "b"]
    assert ids(filtrar(bs, perfil())) == ["a", "b", "c"]


def test_filtro_capacidad():
    bs = [bodega("chica", capacidad_max_grupo=4), bodega("justa", capacidad_max_grupo=6), bodega("sin-dato")]
    assert ids(filtrar(bs, perfil(personas=6))) == ["justa", "sin-dato"]
    assert ids(filtrar(bs, perfil(personas=4))) == ["chica", "justa", "sin-dato"]


def test_filtro_accesibilidad():
    bs = [bodega("si", accesible_movilidad_reducida=True), bodega("no", accesible_movilidad_reducida=False),
          bodega("sin-dato")]
    assert ids(filtrar(bs, perfil(movilidad_reducida=True))) == ["si", "sin-dato"]
    assert ids(filtrar(bs, perfil(movilidad_reducida=False))) == ["si", "no", "sin-dato"]


def test_filtro_idioma():
    bs = [bodega("fr-de", idiomas=["fr", "de"]),
          bodega("en", idiomas=["EN"]),
          bodega("sin-lista"),
          bodega("exp-en", idiomas=["fr"], experiencias=[exp("Tour", idiomas=["en"])]),
          bodega("exp-sin-lista", idiomas=[], experiencias=[exp("Tour", idiomas=["de"]), exp("Otra")])]
    assert ids(filtrar(bs, perfil(idiomas=["en"]))) == ["en", "sin-lista", "exp-en", "exp-sin-lista"]
    assert ids(filtrar(bs, perfil(idiomas=["en", "de"]))) == ids(bs)
    for frances in (["fr"], ["francés"], ["ja", "Français"]):
        assert ids(filtrar(bs, perfil(idiomas=frances))) == ids(bs)
    assert ids(filtrar(bs, perfil(idiomas=[]))) == ids(bs)


def test_filtro_dias():
    finde = [Horario(dias=["sab", "dom"], apertura="10:00", cierre="18:00")]
    bs = [bodega("finde", horarios=finde), bodega("todos"), bodega("sin-horario", horarios=[])]
    assert ids(filtrar(bs, perfil(dia_inicio="lun", cantidad_dias=3))) == ["todos", "sin-horario"]
    assert ids(filtrar(bs, perfil(dia_inicio="vie", cantidad_dias=2))) == ids(bs)   # vie, sab
    assert ids(filtrar(bs, perfil(dia_inicio="dom", cantidad_dias=1))) == ids(bs)


def test_filtro_presupuesto():
    bs = [bodega("cara", experiencias=[exp("A", 60), exp("B", 45)]),
          bodega("justa", experiencias=[exp("A", 40), exp("B", 90)]),
          bodega("a-consultar", experiencias=[exp("A", 60), exp("B", None, None)]),
          bodega("otra-moneda", experiencias=[exp("A", 60, "USD")]),
          bodega("sin-experiencias")]
    assert ids(filtrar(bs, perfil(presupuesto_max_por_persona=40))) == [
        "justa", "a-consultar", "otra-moneda", "sin-experiencias"]
    assert ids(filtrar(bs, perfil(presupuesto_max_por_persona=39.99))) == [
        "a-consultar", "otra-moneda", "sin-experiencias"]
    assert ids(filtrar(bs, perfil())) == ids(bs)


def test_filtro_idioma_y_presupuesto_juntos():
    # la visita en alemán es barata y la en inglés es cara: nadie cumple las dos cosas a la vez
    b = bodega("mixta", idiomas=["de"], experiencias=[exp("A", 10, idiomas=["de"]), exp("B", 50, idiomas=["en"])])
    p = perfil(idiomas=["en"], presupuesto_max_por_persona=30)
    m = motivo_exclusion(b, p)
    assert m is not None and "a la vez" in m
    assert motivo_exclusion(b, perfil(idiomas=["en"], presupuesto_max_por_persona=50)) is None
    assert motivo_exclusion(b, perfil(idiomas=["de"], presupuesto_max_por_persona=30)) is None
    # sin experiencia se cobra la más barata en EUR y valen los idiomas de la bodega
    b = bodega("sin-exp-ok", idiomas=["en"], experiencias=[exp("A", 10, idiomas=["de"])])
    assert motivo_exclusion(b, p) is None


def test_sin_perfil_no_filtra():
    bs = [bodega("a", capacidad_max_grupo=1), bodega("b", accesible_movilidad_reducida=False)]
    assert ids(filtrar(bs, None)) == ["a", "b"]


def test_motivo_exclusion_explica():
    p = perfil(personas=8, movilidad_reducida=True, idiomas=["en"], presupuesto_max_por_persona=10,
               zonas_preferidas=["Côte de Nuits"], bodegas_evitar=["evitar"])
    assert motivo_exclusion(bodega("ok", zona="Côte de Nuits"), p) is None
    casos = {
        "evitar": bodega("evitar", zona="Côte de Nuits"),
        "zona": bodega("z"),
        "8": bodega("c", zona="Côte de Nuits", capacidad_max_grupo=6),
        "accesib": bodega("x", zona="Côte de Nuits", accesible_movilidad_reducida=False),
        "en": bodega("i", zona="Côte de Nuits", idiomas=["fr"]),
        "10": bodega("p", zona="Côte de Nuits", experiencias=[exp("A", 30)]),
        "lun": bodega("d", zona="Côte de Nuits", horarios=[Horario(dias=["sab"], apertura="10:00", cierre="18:00")]),
    }
    for palabra, b in casos.items():
        m = motivo_exclusion(b, p)
        assert m is not None and palabra in m.casefold(), (b.id, m)


def test_filtros_coinciden_con_el_verificador():
    """Si el filtro deja pasar una bodega, existe una visita sin violaciones de esas reglas; si la excluye, no."""
    from enot.modelos import DiaItinerario, Itinerario, Parada
    from enot.verificador import verificar

    p = perfil(personas=4, movilidad_reducida=True, idiomas=["en"], presupuesto_max_por_persona=30)
    reglas = {"grupo_excede_capacidad", "accesibilidad", "idioma_no_disponible", "presupuesto_excedido"}
    variantes = [
        bodega("v1", capacidad_max_grupo=3), bodega("v2", capacidad_max_grupo=4),
        bodega("v3", accesible_movilidad_reducida=False), bodega("v4", accesible_movilidad_reducida=None),
        bodega("v5", idiomas=["fr", "de"]), bodega("v6", idiomas=["fr"], experiencias=[exp("T", 25, idiomas=["en"])]),
        bodega("v7", experiencias=[exp("A", 31), exp("B", 50)]), bodega("v8", experiencias=[exp("A", 31), exp("B", None)]),
        bodega("v9", idiomas=["de"], experiencias=[exp("A", 10, idiomas=["de"]), exp("B", 50, idiomas=["en"])]),
    ]
    for b in variantes:
        corpus = {b.id: b}
        visitas = [None] + [e.nombre for e in b.experiencias]
        alguna_ok = False
        for v in visitas:
            it = Itinerario(dias=[DiaItinerario(numero=1, dia_semana="lun", paradas=[
                Parada(bodega_id=b.id, hora_inicio="10:00", duracion_min=60, experiencia=v)])])
            if not reglas & {x.tipo for x in verificar(it, p, corpus)}:
                alguna_ok = True
        assert (motivo_exclusion(b, p) is None) == alguna_ok, b.id


# --- texto y consulta --------------------------------------------------------------------

def test_texto_bodega_incluye_lo_indexable():
    b = bodega("t", nombre="Domaine Ejemplo", zona="Chablis y Grand Auxerrois", comuna="Chablis", perfil="familiar",
               descripcion_breve="Bodega biodinámica", vinos_o_varietales_destacados=["Chablis Premier Cru"],
               experiencias=[exp("Dégustation", tipo="maridaje", incluye="quesos de la zona")])
    t = texto_bodega(b)
    for parte in ("Domaine Ejemplo", "Chablis y Grand Auxerrois", "familiar", "biodinámica",
                  "Chablis Premier Cru", "Dégustation", "maridaje", "quesos de la zona"):
        assert parte in t
    assert "no_informado" not in texto_bodega(bodega("u"))


def test_consulta_desde_perfil():
    p = perfil(preferencias="algo chico y biodinámico", zonas_preferidas=["Chablis y Grand Auxerrois"])
    c = consulta_desde_perfil(p)
    assert "biodinámico" in c and "Chablis" in c
    assert consulta_desde_perfil(perfil()) == ""


def test_bodega_lee_descripcion_y_vinos_de_la_ficha():
    ficha = {"id": "f", "nombre": "[SINTÉTICA] F", "descripcion_breve": "Pequeño domaine",
             "vinos_o_varietales_destacados": ["Aligoté"], "_meta": {"zona": "Côte Chalonnaise"}}
    b = Bodega.desde_ficha(ficha)
    assert b.descripcion_breve == "Pequeño domaine" and b.vinos_o_varietales_destacados == ["Aligoté"]


# --- índice ------------------------------------------------------------------------------

@pytest.fixture
def bodegas() -> list[Bodega]:
    return [
        bodega("ambas", zona="Chablis y Grand Auxerrois", comuna="Chablis", descripcion_breve="bodega familiar"),
        bodega("palabra", zona="Mâconnais", comuna="Mâcon", descripcion_breve="cooperativa grande, nada familiar"),
        bodega("sinonimo", zona="Côte de Nuits", comuna="Gevrey", descripcion_breve="domaine familial"),
        bodega("nada", zona="Côte Chalonnaise", comuna="Givry", descripcion_breve="négociant histórico"),
    ]


@pytest.fixture
def embedder() -> EmbedderFalso:
    return EmbedderFalso(sinonimos={"familial": "familiar"})


def test_buscar_combina_bm25_y_embeddings(bodegas, embedder):
    r = Indice(bodegas, embedder).buscar(None, k=4, consulta="familiar chablis")
    assert all(isinstance(c, Candidata) for c in r)
    por_id = {c.bodega_id: c for c in r}
    assert r[0].bodega_id == "ambas"
    assert r[0].puesto_bm25 == 1 and r[0].puesto_embeddings == 1
    assert por_id["palabra"].puesto_bm25 == 2           # coincide por palabra
    assert por_id["sinonimo"].puesto_bm25 is None       # BM25 no ve el sinónimo...
    assert por_id["sinonimo"].puesto_embeddings is not None   # ...los embeddings sí
    assert por_id["sinonimo"].puesto_embeddings < por_id["nada"].puesto_embeddings
    assert [c.score for c in r] == sorted((c.score for c in r), reverse=True)
    assert r[0].score == pytest.approx(2 / 61)


def test_bm25_solo_vota_documentos_con_coincidencias(bodegas, embedder):
    r = Indice(bodegas, embedder).buscar(None, k=4, consulta="givry")
    por_id = {c.bodega_id: c for c in r}
    assert por_id["nada"].puesto_bm25 == 1
    assert [c.bodega_id for c in r if c.puesto_bm25 is not None] == ["nada"]
    assert len(r) == 4


def test_buscar_respeta_filtros(bodegas, embedder):
    bodegas[0] = bodegas[0].model_copy(update={"capacidad_max_grupo": 2})
    r = Indice(bodegas, embedder).buscar(perfil(personas=5), k=4, consulta="familiar chablis")
    assert "ambas" not in [c.bodega_id for c in r]
    assert len(r) == 3
    r = Indice(bodegas, embedder).buscar(perfil(zonas_preferidas=["Côte de Nuits"]), consulta="chablis")
    assert [c.bodega_id for c in r] == ["sinonimo"]


def test_buscar_k(bodegas, embedder):
    ind = Indice(bodegas, embedder)
    assert len(ind.buscar(None, k=2, consulta="familiar")) == 2
    assert len(ind.buscar(None, k=10, consulta="familiar")) == 4
    assert ind.buscar(None, k=1, consulta="familiar chablis")[0].bodega_id == "ambas"


def test_buscar_sin_candidatas(bodegas, embedder):
    assert Indice(bodegas, embedder).buscar(perfil(zonas_preferidas=["Jura"]), consulta="vino") == []
    assert Indice([], embedder).buscar(None, consulta="vino") == []


def test_buscar_sin_consulta_usa_el_perfil(bodegas, embedder):
    ind = Indice(bodegas, embedder)
    p = perfil(preferencias="algo familiar en chablis")
    assert ind.buscar(p, k=4) == ind.buscar(p, k=4, consulta=consulta_desde_perfil(p))
    assert ind.buscar(p, k=1)[0].bodega_id == "ambas"


def test_buscar_top_por_metodo(bodegas, embedder):
    r = Indice(bodegas, embedder).buscar(None, k=4, consulta="familiar chablis", top_por_metodo=1)
    # solo el primero de cada método suma; el resto queda con puntaje 0 y puestos fuera del top se informan igual
    assert r[0].bodega_id == "ambas" and r[0].score == pytest.approx(2 / 61)
    assert all(c.score == 0 for c in r[1:])


def test_indice_embebe_el_corpus_una_vez(bodegas, embedder):
    ind = Indice(bodegas, embedder)
    assert len(embedder.llamadas) == 1 and len(embedder.llamadas[0]) == 4
    ind.buscar(None, consulta="familiar")
    assert len(embedder.llamadas) == 2 and embedder.llamadas[1] == ["familiar"]


# --- caché de embeddings -----------------------------------------------------------------

def test_cache_no_recalcula(tmp_path):
    base = EmbedderFalso()
    cache = EmbedderConCache(base, carpeta=tmp_path)
    a = cache.embeber(["uno", "dos"])
    b = cache.embeber(["dos", "uno"])
    assert len(base.llamadas) == 1
    assert np.allclose(b, a[::-1])
    assert cache.nombre == base.nombre


def test_cache_texto_nuevo(tmp_path):
    base = EmbedderFalso()
    cache = EmbedderConCache(base, carpeta=tmp_path)
    cache.embeber(["uno"])
    r = cache.embeber(["uno", "tres"])
    assert base.llamadas == [["uno"], ["tres"]]
    assert np.allclose(r, base.embeber(["uno", "tres"]))
    assert cache.embeber([]).shape[0] == 0


def test_cache_persiste_entre_instancias(tmp_path):
    EmbedderConCache(EmbedderFalso(), carpeta=tmp_path).embeber(["uno", "dos"])
    otro = EmbedderFalso()
    r = EmbedderConCache(otro, carpeta=tmp_path).embeber(["dos"])
    assert otro.llamadas == []
    assert np.allclose(r, EmbedderFalso().embeber(["dos"]))


def test_cache_separa_por_modelo(tmp_path):
    EmbedderConCache(EmbedderFalso(nombre="m1"), carpeta=tmp_path).embeber(["uno"])
    m2 = EmbedderFalso(nombre="m2", dim=8)
    r = EmbedderConCache(m2, carpeta=tmp_path).embeber(["uno"])
    assert m2.llamadas == [["uno"]] and r.shape == (1, 8)


# --- embedder real (con un cliente falso: sin red) ---------------------------------------

class _ClienteEmbeddings:
    def __init__(self):
        self.pedidos = []
        self.embeddings = types.SimpleNamespace(create=self._create)

    def _create(self, model, input):
        self.pedidos.append((model, list(input)))
        datos = [types.SimpleNamespace(index=i, embedding=[float(i), 1.0]) for i in range(len(input))]
        return types.SimpleNamespace(data=list(reversed(datos)))   # desordenado a propósito


def test_embedder_openai_pide_el_modelo_y_respeta_el_orden(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_MODEL", "modelo-de-prueba")
    cli = _ClienteEmbeddings()
    e = EmbedderOpenAI(cliente=cli)
    assert e.nombre == "modelo-de-prueba"
    r = e.embeber(["a", "b", "c"])
    assert cli.pedidos == [("modelo-de-prueba", ["a", "b", "c"])]
    assert r.tolist() == [[0.0, 1.0], [1.0, 1.0], [2.0, 1.0]]
    assert EmbedderOpenAI(modelo="otro", cliente=cli).nombre == "otro"


def test_embedder_openai_lista_vacia():
    cli = _ClienteEmbeddings()
    assert EmbedderOpenAI(cliente=cli).embeber([]).shape[0] == 0
    assert cli.pedidos == []


def test_embedder_openai_modelo_por_defecto(monkeypatch):
    monkeypatch.delenv("EMBEDDINGS_MODEL", raising=False)
    assert EmbedderOpenAI(cliente=_ClienteEmbeddings()).nombre == "text-embedding-3-small"


# --- con datos reales: muestra de DATAtourisme ---------------------------------------------

@pytest.mark.skipif(not MUESTRA.exists(), reason="falta data/datatourisme/muestra.csv")
def test_con_la_muestra_real_de_datatourisme(entorno):
    """Pasa la muestra real por el paso `datatourisme` (en una carpeta temporal) y busca sobre esas bodegas."""
    from corpus import config, datatourisme

    with contextlib.redirect_stdout(io.StringIO()):
        datatourisme.run(str(MUESTRA))
    filas = list(csv.DictReader(config.SEED_CSV.open(encoding="utf-8")))
    assert len(filas) > 100
    bodegas = []
    for f in filas:
        texto = json.loads((config.BASE_DIR / f"{f['id']}.json").read_text(encoding="utf-8"))[0]["texto"]
        bodegas.append(Bodega(id=f["id"], nombre=f["nombre"], zona=f["zona"], comuna=f["comuna"],
                              lat=float(f["lat"]) if f["lat"] else None, lon=float(f["lon"]) if f["lon"] else None,
                              descripcion_breve=texto.split("Descripción:", 1)[-1].strip()))
    zona_de = {b.id: b.zona for b in bodegas}
    ind = Indice(bodegas, EmbedderFalso())

    r = ind.buscar(None, k=5, consulta="Chablis")
    assert len(r) == 5
    assert all(zona_de[c.bodega_id] == "Chablis y Grand Auxerrois" for c in r)
    assert all(c.puesto_bm25 is not None for c in r)

    r = ind.buscar(perfil(zonas_preferidas=["Mâconnais"]), k=50, consulta="vin blanc")
    assert r and all(zona_de[c.bodega_id] == "Mâconnais" for c in r)
    assert len(r) == sum(1 for b in bodegas if b.zona == "Mâconnais")
