"""Spec 007: baselines B0 (zero-shot), B1 (filtros + greedy) y B2 (Enot sin loop), y Enot completo como sistema.

Todo offline: `ClienteFalso`, `EmbedderFalso` y la fixture SINTÉTICA de bodegas.
"""
from __future__ import annotations

import pytest

from enot.corpus_local import cargar_corpus
from enot.flujo import Flujo
from enot.modelos import PerfilViaje, a_minutos
from enot.retrieval import Indice
from enot.tools import ItemCosto, costo_experiencias, tiempo_traslado
from enot.verificador import verificar
from eval.baselines import (
    PROMPT_B0,
    BaselineB0,
    BaselineB1,
    SistemaEnot,
    crear_b2,
    crear_enot,
    resolver_bodega,
)
from eval.generador import Consulta
from eval.metricas import detecta_infactible, evaluar_consulta, faltantes_estructurales
from tests.conftest import FIXTURES, ClienteFalso
from tests.dobles import EmbedderFalso
from tests.test_flujo import INVALIDO, PERFIL, SALIDA_RESPUESTA, VALIDO, Guion, cliente


@pytest.fixture
def corpus():
    return cargar_corpus(FIXTURES / "fichas_sinteticas.jsonl")


@pytest.fixture
def indice(corpus):
    return Indice(list(corpus.values()), EmbedderFalso())


def consulta(texto="Un día el viernes en auto, somos 2", escenario="dias", infactible=False, motivo=None,
             **kw) -> Consulta:
    return Consulta(id="q1", escenario=escenario, plantilla="t", texto=texto,
                    restricciones=PerfilViaje(**{**PERFIL, **kw}), infactible=infactible, motivo_infactible=motivo)


# --- B0 ----------------------------------------------------------------------------------------

def test_resolver_bodega(corpus):
    assert resolver_bodega("Domaine Beaune Centre", corpus) == "sint-beaune"
    assert resolver_bodega("  domaine   BEAUNE centre ", corpus) == "sint-beaune"
    assert resolver_bodega("Chateau Pommard-Test", corpus) == "sint-pommard"
    assert resolver_bodega("[SINTÉTICA] Château Pommard Test", corpus) == "sint-pommard"
    assert resolver_bodega("[SINTÉTICA] Domaine Inventado B0", corpus) is None
    assert resolver_bodega("Domaine Beaune", corpus) is None      # no alcanza con una parte del nombre
    assert resolver_bodega("", corpus) is None


# [SINTÉTICA] respuesta guionada de B0: una bodega y un precio inventados a propósito (simulan una alucinación)
SALIDA_B0 = {"es_posible": True, "motivo": None, "dias": [{"dia_semana": "vie", "paradas": [
    {"bodega": "Domaine Beaune Centre", "hora_inicio": "10:00", "duracion_min": 60,
     "experiencia": "Dégustation classique", "precio_por_persona_eur": 20},
    {"bodega": "[SINTÉTICA] Domaine Inventado B0", "hora_inicio": "12:00", "duracion_min": 90,
     "experiencia": None, "precio_por_persona_eur": 250},
    {"bodega": "Château Pommard Test", "hora_inicio": "15:00", "duracion_min": 60,
     "experiencia": None, "precio_por_persona_eur": None},
]}]}


def test_b0_salida(corpus):
    cli = ClienteFalso([SALIDA_B0])
    s = BaselineB0(cli, corpus).correr(consulta(texto="Quiero bodegas el viernes"))
    assert s.sistema == "B0" and s.consulta_id == "q1" and s.tipo == "itinerario"
    assert (s.tokens_in, s.tokens_out) == (100, 50) and s.intentos == 1
    assert s.latencia_s >= 0
    [dia] = s.itinerario.dias
    assert (dia.numero, dia.dia_semana) == (1, "vie")
    assert [p.bodega_id for p in dia.paradas] == ["sint-beaune", "b0:[SINTÉTICA] Domaine Inventado B0", "sint-pommard"]
    assert [(p.hora_inicio, p.duracion_min, p.experiencia) for p in dia.paradas] == [
        ("10:00", 60, "Dégustation classique"), ("12:00", 90, None), ("15:00", 60, None)]
    assert [(p.bodega_id, p.experiencia, p.precio_por_persona_eur) for p in s.precios_afirmados] == [
        ("sint-beaune", "Dégustation classique", 20), ("b0:[SINTÉTICA] Domaine Inventado B0", None, 250)]
    [llamada] = cli.llamadas
    assert llamada["sistema"] == PROMPT_B0
    assert "Quiero bodegas el viernes" in llamada["usuario"]
    assert not any(i in llamada["usuario"] or i in llamada["sistema"] for i in corpus)  # sin corpus


def test_b0_imposible_es_infactible(corpus):
    cli = ClienteFalso([{"es_posible": False, "motivo": "no entra en un día", "dias": []}])
    s = BaselineB0(cli, corpus).correr(consulta())
    assert s.tipo == "infactible" and s.itinerario is None and "no entra en un día" in s.texto
    assert detecta_infactible(s.tipo, "demasiadas_bodegas")


def test_b0_inventado_no_pasa(corpus):
    s = BaselineB0(ClienteFalso([SALIDA_B0]), corpus).correr(consulta())
    e = evaluar_consulta(consulta(), s, corpus)
    # 3 bodegas + 1 experiencia + 2 precios; inventadas: la bodega SINTÉTICA inventada y su precio
    assert (e.afirmaciones, e.inventadas) == (6, 2)
    assert "bodega_inexistente" in e.violaciones
    assert e.hard_pass is False


# --- B1 ----------------------------------------------------------------------------------------

def _visitas(s):
    return [p for d in s.itinerario.dias for p in d.paradas]


def test_b1_itinerario_factible_y_por_cercania(corpus):
    c = consulta()
    s = BaselineB1(corpus).correr(c)
    assert s.sistema == "B1" and s.tipo == "itinerario" and s.tokens_in is None
    perfil = c.restricciones
    assert verificar(s.itinerario, perfil, corpus) == []
    assert faltantes_estructurales(s.itinerario, perfil) == []
    paradas = _visitas(s)
    assert 2 <= len(paradas) <= 4
    # la primera, por id (beaune abre 10:00: espera la apertura); la segunda, la más cercana a la primera
    assert (paradas[0].bodega_id, paradas[0].hora_inicio) == ("sint-beaune", "10:00")
    assert paradas[1].bodega_id == "sint-pommard"
    # empieza apenas termina el traslado
    t = tiempo_traslado(corpus, "sint-beaune", "sint-pommard", "auto").minutos
    assert a_minutos(paradas[1].hora_inicio) == a_minutos("11:00") + t
    assert len({p.bodega_id for p in paradas}) == len(paradas)
    assert evaluar_consulta(c, s, corpus).hard_pass is True


def test_b1_respeta_presupuesto(corpus):
    sin_tope = BaselineB1(corpus).correr(consulta(zonas_preferidas=["Côte de Beaune"]))
    assert [p.bodega_id for p in _visitas(sin_tope)] == ["sint-beaune", "sint-pommard"]
    c = consulta(zonas_preferidas=["Côte de Beaune"], presupuesto_max_por_persona=20)
    s = BaselineB1(corpus).correr(c)
    assert [p.bodega_id for p in _visitas(s)] == ["sint-beaune"]
    costo = costo_experiencias(corpus, [ItemCosto(bodega_id=p.bodega_id, experiencia=p.experiencia)
                                        for p in _visitas(s)], 2)
    assert costo.total_eur <= 40
    assert verificar(s.itinerario, c.restricciones, corpus) == []


def test_b1_prueba_las_experiencias_si_sin_experiencia_no_sirve(corpus):
    # variante SINTÉTICA de beaune que publica solo francés: en inglés, solo sirve "Grands crus" (fr, en)
    solo_fr = {**corpus, "sint-beaune": corpus["sint-beaune"].model_copy(update={"idiomas": ["fr"]})}
    c = consulta(zonas_preferidas=["Côte de Beaune"], idiomas=["en"])
    s = BaselineB1(solo_fr).correr(c)
    beaune = next(p for p in _visitas(s) if p.bodega_id == "sint-beaune")
    assert beaune.experiencia == "Grands crus" and beaune.duracion_min == 90
    assert verificar(s.itinerario, c.restricciones, solo_fr) == []


def test_b1_espera_la_apertura(corpus):
    c = consulta(zonas_preferidas=["Côte de Nuits"], hora_inicio_jornada="09:00")
    s = BaselineB1(corpus).correr(c)
    paradas = _visitas(s)
    assert (paradas[0].bodega_id, paradas[0].hora_inicio) == ("sint-gevrey", "10:00")
    assert verificar(s.itinerario, c.restricciones, corpus) == []


def test_b1_espera_la_segunda_franja(corpus):
    # gevrey cierra 12:00–14:00: si la mañana no alcanza, espera a la franja de la tarde
    c = consulta(zonas_preferidas=["Côte de Nuits"], hora_inicio_jornada="11:30")
    paradas = _visitas(BaselineB1(corpus).correr(c))
    assert (paradas[0].bodega_id, paradas[0].hora_inicio) == ("sint-gevrey", "14:00")


def test_b1_sin_candidatas(corpus):
    c = consulta(escenario="infactible", infactible=True, motivo="zona_fuera_de_borgona", zonas_preferidas=["Champagne"])
    s = BaselineB1(corpus).correr(c)
    assert s.tipo == "sin_candidatas" and s.itinerario is None
    assert evaluar_consulta(c, s, corpus).infactible_detectado is True


def test_b1_dia_sin_paradas_es_infactible(corpus):
    c = consulta(cantidad_dias=2, dia_inicio="dom", zonas_preferidas=["Chablis"])
    s = BaselineB1(corpus).correr(c)
    assert s.tipo == "infactible" and s.itinerario is None and "2" in s.texto


def test_b1_no_repite_y_respeta_maximo(corpus):
    c = consulta(cantidad_dias=2, zonas_preferidas=["Côte de Beaune"])
    s = BaselineB1(corpus, max_paradas_dia=1).correr(c)
    assert [[p.bodega_id for p in d.paradas] for d in s.itinerario.dias] == [["sint-beaune"], ["sint-pommard"]]
    assert [d.dia_semana for d in s.itinerario.dias] == ["vie", "sab"]
    assert verificar(s.itinerario, c.restricciones, corpus) == []


def test_b1_duracion_por_defecto(corpus):
    c = consulta(zonas_preferidas=["Mâconnais"])   # sin horario ni experiencias: dura lo que diga el parámetro
    s = BaselineB1(corpus, duracion_defecto=45).correr(c)
    [p] = _visitas(s)
    assert (p.bodega_id, p.duracion_min, p.experiencia, p.hora_inicio) == ("sint-sin-horario", 45, None, "09:30")


# --- Enot y B2 ---------------------------------------------------------------------------------

def test_enot_entrega_itinerario_valido(corpus, indice, tmp_path):
    g = Guion(relevamiento=[PERFIL], planificador=[VALIDO], respuesta=[SALIDA_RESPUESTA])
    sistema = crear_enot(cliente(g), corpus, indice, tmp_path / "trazas")
    assert sistema.nombre == "enot"
    s = sistema.correr(consulta())
    assert s.tipo == "itinerario" and s.intentos == 1
    assert [p.bodega_id for p in s.itinerario.dias[0].paradas] == ["sint-beaune", "sint-pommard"]
    assert (s.tokens_in, s.tokens_out) == (300, 150)   # relevamiento + planificador + respuesta
    assert s.texto.startswith("Te armé este recorrido.")
    assert evaluar_consulta(consulta(), s, corpus).hard_pass is True


def test_enot_infactible_no_entrega_itinerario(corpus, indice, tmp_path):
    g = Guion(relevamiento=[PERFIL], planificador=[INVALIDO], respuesta=[SALIDA_RESPUESTA])
    s = crear_enot(cliente(g), corpus, indice, tmp_path / "trazas").correr(consulta())
    assert s.tipo == "infactible" and s.itinerario is None and s.intentos == 3


def test_b2_entrega_la_primera_propuesta(corpus, indice, tmp_path):
    def guion():
        return Guion(relevamiento=[PERFIL], planificador=[INVALIDO, VALIDO], respuesta=[SALIDA_RESPUESTA])

    b2 = crear_b2(cliente(guion()), corpus, indice, tmp_path / "b2")
    assert b2.nombre == "B2" and b2.flujo.max_intentos == 1
    s2 = b2.correr(consulta())
    assert s2.tipo == "itinerario" and s2.intentos == 1
    assert s2.itinerario.dias[0].paradas[0].hora_inicio == "08:00"   # la propuesta inválida
    assert evaluar_consulta(consulta(), s2, corpus).hard_pass is False

    s3 = crear_enot(cliente(guion()), corpus, indice, tmp_path / "enot").correr(consulta())
    assert s3.tipo == "itinerario" and s3.intentos == 2
    assert evaluar_consulta(consulta(), s3, corpus).hard_pass is True


def test_sistema_enot_sin_entregar_sin_verificar_no_cambia_el_tipo(corpus, indice, tmp_path):
    g = Guion(relevamiento=[PERFIL], planificador=[INVALIDO], respuesta=[SALIDA_RESPUESTA])
    sistema = SistemaEnot(Flujo(cliente(g), corpus, indice, max_intentos=1), "x", tmp_path / "t")
    s = sistema.correr(consulta())
    assert s.tipo == "infactible" and s.itinerario is None and s.sistema == "x"


def test_cada_consulta_tiene_su_propia_sesion(corpus, indice, tmp_path):
    g = Guion(relevamiento=[PERFIL], planificador=[VALIDO], respuesta=[SALIDA_RESPUESTA])
    sistema = crear_enot(cliente(g), corpus, indice, tmp_path / "trazas")
    a, b = sistema.correr(consulta()), sistema.correr(consulta())
    # la segunda no es un ajuste de la primera ni suma sus tokens
    assert (a.tokens_in, b.tokens_in) == (300, 300)
    assert len(list((tmp_path / "trazas").glob("*.jsonl"))) == 2


# --- latencia y tokens (sobrevivientes de mutation) ---------------------------------------------

class _Reloj:
    """`time.perf_counter` falso: avanza 1,5 s en cada lectura."""

    def __init__(self):
        self.t = 100.0

    def __call__(self):
        self.t += 1.5
        return self.t


def test_latencia_medida(corpus, indice, tmp_path, monkeypatch):
    import eval.baselines as baselines

    g = Guion(relevamiento=[PERFIL], planificador=[VALIDO], respuesta=[SALIDA_RESPUESTA])
    enot = crear_enot(cliente(g), corpus, indice, tmp_path / "t")
    b0 = BaselineB0(ClienteFalso([SALIDA_B0]), corpus)
    # `time` es un solo módulo: los nodos de Enot también leen este reloj (2 lecturas por llamada al LLM)
    monkeypatch.setattr(baselines.time, "perf_counter", _Reloj())
    salidas = [BaselineB1(corpus).correr(consulta()),
               BaselineB1(corpus).correr(consulta(zonas_preferidas=["Champagne"])),
               BaselineB1(corpus).correr(consulta(cantidad_dias=2, dia_inicio="dom", zonas_preferidas=["Chablis"])),
               b0.correr(consulta()), enot.correr(consulta())]
    assert [s.tipo for s in salidas] == ["itinerario", "sin_candidatas", "infactible", "itinerario", "itinerario"]
    # B0 y B1 leen el reloj al empezar y al terminar: una lectura de diferencia = 1,5 s. En Enot, entre medio leen
    # los 3 nodos (relevamiento, planificador, respuesta): 1 + 3 × 2 = 7 lecturas = 10,5 s
    assert [s.latencia_s for s in salidas] == pytest.approx([1.5, 1.5, 1.5, 1.5, 10.5])
    assert all(s.texto for s in salidas[1:3])


def test_tokens_desconocidos_si_una_llamada_fallo(corpus, indice, tmp_path):
    # el relevamiento devuelve basura: la traza registra el error con tokens None (ADR-0014); no se inventa un 0
    g = Guion(relevamiento=["esto no es JSON"])
    s = crear_enot(cliente(g), corpus, indice, tmp_path / "t").correr(consulta())
    assert s.tipo == "error"
    assert s.tokens_in is None and s.tokens_out is None


# --- formato real -------------------------------------------------------------------------------

# huella de la muestra con la que se midieron las cifras del reporte de la corrida 2026-11-25-1039 y de ADR-0017
HUELLA_MUESTRA = "2e0a198d4559745f55c9ee3858e570fec74e61068f27606866e34b6377e6a122"


def test_b1_sobre_la_muestra_real(entorno):
    """Muestra real → paso `datatourisme` → B1 sobre las 100 consultas del generador, en memoria (sin data/eval/).

    Reproduce las cifras citadas en ADR-0017. Si Flora cambia la muestra, solo se chequean los invariantes."""
    import contextlib
    import csv
    import hashlib
    import io

    from corpus import config, datatourisme
    from enot.modelos import Bodega
    from eval.generador import generar
    from eval.metricas import resumir

    muestra = FIXTURES.parent.parent / "data" / "datatourisme" / "muestra.csv"
    if not muestra.exists():
        pytest.skip("sin data/datatourisme/muestra.csv")
    with contextlib.redirect_stdout(io.StringIO()):
        datatourisme.run(str(muestra))
    bodegas = [Bodega(id=f["id"], nombre=f["nombre"], zona=f["zona"], comuna=f["comuna"],
                      lat=float(f["lat"]) if f["lat"] else None, lon=float(f["lon"]) if f["lon"] else None)
               for f in csv.DictReader(config.SEED_CSV.open(encoding="utf-8"))]
    corpus = {b.id: b for b in bodegas}
    consultas = generar()
    m, evals = resumir(consultas, [BaselineB1(corpus).correr(c) for c in consultas], corpus)

    # invariantes con cualquier muestra: B1 no inventa y detecta las zonas fuera de Borgoña (sin candidatas)
    assert m.consultas == 100 and m.inventadas == 0 and m.tasa_alucinacion == 0
    assert m.infactibles_detectados_por_motivo["zona_fuera_de_borgona"] == 1.0
    assert m.infactibles_detectados_representables == 1.0

    if hashlib.sha256(muestra.read_bytes()).hexdigest() == HUELLA_MUESTRA:
        assert m.hard_pass_rate == pytest.approx(79 / 80)
        assert [e.consulta_id for e in evals if e.hard_pass is False] == ["q047"]   # 3 días, una sola bodega
        assert m.cobertura_corpus == pytest.approx(0.41)
        assert m.gini == pytest.approx(0.8166, abs=1e-4)
        assert m.infactibles_detectados == pytest.approx(0.3)
        assert m.infactibles_detectados_por_motivo == pytest.approx(
            {"demasiadas_bodegas": 0.0, "zona_fuera_de_borgona": 1.0, "zonas_lejanas": 0.0})
