"""Spec 007: métricas del benchmark con casos armados a mano (ADR-0007, ADR-0017).

Corpus: la fixture SINTÉTICA `tests/fixtures/fichas_sinteticas.jsonl` (7 bodegas inventadas).
- sint-beaune: mar–dom 10:00–18:00, capacidad 12, accesible; "Dégustation classique" 20 EUR, "Grands crus" 60 EUR.
- sint-pommard: lun–sáb 09:30–17:30, accesibilidad sin dato; "Visite et dégustation" 35 EUR.
- sint-chablis: "Dégustation" sin precio, "Visite USD" 30 USD.
"""
from __future__ import annotations

import pytest

from enot.corpus_local import cargar_corpus
from enot.modelos import DiaItinerario, Itinerario, Parada, PerfilViaje
from eval.generador import Consulta
from eval.metricas import (
    DETECTAN_INFACTIBLE,
    REPRESENTABLES,
    PrecioAfirmado,
    SalidaSistema,
    afirmaciones,
    cobertura_corpus,
    detecta_infactible,
    evaluar_consulta,
    faltantes_estructurales,
    gini,
    hard_pass_rate,
    infactibles_detectados,
    recomendaciones_por_bodega,
    resumir,
    tasa_alucinacion,
)
from tests.conftest import FIXTURES


@pytest.fixture(scope="module")
def corpus():
    return cargar_corpus(FIXTURES / "fichas_sinteticas.jsonl")


def perfil(**kw) -> PerfilViaje:
    base = {"cantidad_dias": 2, "dia_inicio": "vie", "transporte": "auto", "personas": 2}
    return PerfilViaje(**{**base, **kw})


def consulta(id="q1", escenario="dias", infactible=False, motivo=None, **kw) -> Consulta:
    return Consulta(id=id, escenario=escenario, plantilla="t", texto="pedido", restricciones=perfil(**kw),
                    infactible=infactible, motivo_infactible=motivo)


def parada(bodega, hora="10:00", dur=60, exp=None) -> Parada:
    return Parada(bodega_id=bodega, hora_inicio=hora, duracion_min=dur, experiencia=exp)


def itinerario(*dias) -> Itinerario:
    """dias = (dia_semana, [paradas]) en orden."""
    return Itinerario(dias=[DiaItinerario(numero=n, dia_semana=d, paradas=list(ps))
                            for n, (d, ps) in enumerate(dias, 1)])


VALIDO = itinerario(("vie", [parada("sint-beaune", "10:00", 60, "Dégustation classique"),
                             parada("sint-pommard", "11:30", 60)]),
                    ("sab", [parada("sint-pommard", "10:00", 60)]))


def salida(itin=VALIDO, tipo="itinerario", id="q1", precios=(), sistema="S") -> SalidaSistema:
    return SalidaSistema(consulta_id=id, sistema=sistema, tipo=tipo, itinerario=itin, precios_afirmados=list(precios))


# --- estructura ------------------------------------------------------------------------------

def test_faltantes_estructurales_itinerario_completo():
    assert faltantes_estructurales(VALIDO, perfil()) == []


def test_faltantes_estructurales_cantidad_de_dias():
    uno = itinerario(("vie", [parada("sint-beaune")]))
    f = faltantes_estructurales(uno, perfil())
    assert len(f) == 1 and "1" in f[0] and "2" in f[0]
    assert faltantes_estructurales(uno, perfil(cantidad_dias=1)) == []


def test_faltantes_estructurales_dia_de_semana():
    corrido = itinerario(("sab", [parada("sint-beaune")]), ("dom", [parada("sint-beaune")]))
    f = faltantes_estructurales(corrido, perfil())
    assert len(f) == 2
    assert "sab" in f[0] and "vie" in f[0]
    assert faltantes_estructurales(corrido, perfil(dia_inicio="sab")) == []


def test_faltantes_estructurales_dia_sin_paradas():
    vacio = itinerario(("vie", [parada("sint-beaune")]), ("sab", []))
    f = faltantes_estructurales(vacio, perfil())
    assert len(f) == 1 and "2" in f[0]
    assert faltantes_estructurales(itinerario(("vie", []), ("sab", [parada("sint-beaune")])), perfil()) != []


# --- afirmaciones ----------------------------------------------------------------------------

def test_afirmaciones_correctas(corpus):
    it = itinerario(("vie", [parada("sint-beaune", exp="Dégustation classique")]))
    s = salida(it, precios=[PrecioAfirmado(bodega_id="sint-beaune", experiencia="Dégustation classique",
                                           precio_por_persona_eur=20)])
    assert afirmaciones(s, corpus) == (3, 0)


def test_afirmaciones_bodega_inexistente(corpus):
    it = itinerario(("vie", [parada("b0:Domaine Inventado", exp="Cata"), parada("sint-beaune", "12:00")]))
    s = salida(it, precios=[PrecioAfirmado(bodega_id="b0:Domaine Inventado", experiencia="Cata",
                                           precio_por_persona_eur=20)])
    # inventada: la bodega, su experiencia y su precio; sint-beaune es una afirmación correcta
    assert afirmaciones(s, corpus) == (4, 3)


def test_afirmaciones_experiencia_inexistente(corpus):
    it = itinerario(("vie", [parada("sint-beaune", exp="Cata nocturna")]))
    assert afirmaciones(salida(it), corpus) == (2, 1)


def test_afirmaciones_sin_itinerario(corpus):
    assert afirmaciones(salida(None, tipo="infactible"), corpus) == (0, 0)


@pytest.mark.parametrize("bodega, exp, precio, inventadas", [
    ("sint-beaune", "Dégustation classique", 20, 0),
    ("sint-beaune", "Grands crus", 60, 0),
    ("sint-beaune", "grands CRUS", 60, 0),           # el nombre se compara sin mayúsculas, como el verificador
    ("sint-beaune", "Grands crus", 20, 1),           # precio de otra experiencia
    ("sint-beaune", None, 20, 0),                    # sin experiencia: la más barata en EUR
    ("sint-beaune", None, 60, 1),
    ("sint-beaune", "Dégustation classique", 20.009, 0),   # dentro de la tolerancia
    ("sint-beaune", "Dégustation classique", 19.991, 0),
    ("sint-beaune", "Dégustation classique", 20.02, 1),
    ("sint-beaune", "Dégustation classique", 19.98, 1),
    ("sint-chablis", "Visite USD", 30, 1),           # el corpus no tiene precio en EUR
    ("sint-chablis", "Dégustation", 0, 1),           # el corpus no tiene precio
    ("sint-chablis", None, 30, 1),                   # ninguna experiencia en EUR
    ("sint-beaune", "Inexistente", 20, 1),
    ("b0:Otra", None, 20, 1),
])
def test_afirmaciones_precio(corpus, bodega, exp, precio, inventadas):
    s = salida(None, tipo="itinerario", precios=[PrecioAfirmado(bodega_id=bodega, experiencia=exp,
                                                               precio_por_persona_eur=precio)])
    assert afirmaciones(s, corpus) == (1, inventadas)


# --- hard pass -------------------------------------------------------------------------------

def test_hard_pass_itinerario_valido(corpus):
    e = evaluar_consulta(consulta(), salida(), corpus)
    assert e.hard_pass is True
    assert e.faltantes == [] and e.violaciones == [] and e.inventadas == 0
    assert e.afirmaciones == 4 and e.tipo == "itinerario"
    assert e.infactible_detectado is None


@pytest.mark.parametrize("caso", ["cerrada", "incompleto", "precio", "tipo_infactible", "sin_salida"])
def test_hard_pass_falla(corpus, caso):
    if caso == "cerrada":
        it = itinerario(("vie", [parada("sint-beaune", "17:30", 60)]), ("sab", [parada("sint-pommard")]))
        s = salida(it)
    elif caso == "incompleto":
        s = salida(itinerario(("vie", [parada("sint-beaune")])))
    elif caso == "precio":
        s = salida(precios=[PrecioAfirmado(bodega_id="sint-pommard", experiencia=None, precio_por_persona_eur=5)])
    elif caso == "tipo_infactible":
        s = salida(None, tipo="infactible")
    else:
        s = None
    e = evaluar_consulta(consulta(), s, corpus)
    assert e.hard_pass is False
    if caso == "cerrada":
        assert e.violaciones == ["cerrada"] and e.faltantes == []
    if caso == "incompleto":
        assert e.violaciones == [] and len(e.faltantes) == 1
    if caso == "precio":
        assert e.violaciones == [] and e.faltantes == [] and e.inventadas == 1
    if caso == "sin_salida":
        assert e.tipo == "error"


def test_hard_pass_tipo_no_itinerario_con_itinerario_valido_falla(corpus):
    # lo que cuenta es lo que se le entrega al turista: un "infactible" no entrega itinerario
    assert evaluar_consulta(consulta(), salida(tipo="infactible"), corpus).hard_pass is False


def test_hard_pass_usa_la_etiqueta(corpus):
    it = itinerario(("vie", [parada("sint-beaune")]))
    s = salida(it)
    assert evaluar_consulta(consulta(cantidad_dias=1), s, corpus).hard_pass is True
    e = evaluar_consulta(consulta(cantidad_dias=1, personas=15), s, corpus)
    assert e.hard_pass is False and e.violaciones == ["grupo_excede_capacidad"]


def test_hard_pass_ignora_advertencias(corpus):
    it = itinerario(("vie", [parada("sint-pommard")]))
    e = evaluar_consulta(consulta(cantidad_dias=1, movilidad_reducida=True), salida(it), corpus)
    assert e.hard_pass is True and e.violaciones == []


def test_hard_pass_rate_solo_factibles(corpus):
    malo = salida(itinerario(("vie", [parada("sint-beaune")])), id="q2")
    evals = [evaluar_consulta(consulta("q1"), salida(id="q1"), corpus),
             evaluar_consulta(consulta("q2"), malo, corpus),
             evaluar_consulta(consulta("q3"), salida(id="q3"), corpus),
             evaluar_consulta(consulta("q4", "infactible", True, "demasiadas_bodegas"), salida(id="q4"), corpus)]
    assert hard_pass_rate(evals) == pytest.approx(2 / 3)
    assert hard_pass_rate(evals[3:]) is None
    assert hard_pass_rate([]) is None


def test_tasa_alucinacion_agrega(corpus):
    a = salida(itinerario(("vie", [parada("sint-beaune", exp="Dégustation classique"), parada("b0:X", "12:00"),
                                   parada("sint-pommard", "14:00")])),
               precios=[PrecioAfirmado(bodega_id="sint-beaune", experiencia="Dégustation classique",
                                       precio_por_persona_eur=20)])
    b = salida(itinerario(("vie", [parada("sint-beaune", exp="Inventada")])), id="q2")
    evals = [evaluar_consulta(consulta("q1", cantidad_dias=1), a, corpus),
             evaluar_consulta(consulta("q2", cantidad_dias=1), b, corpus)]
    assert (evals[0].afirmaciones, evals[0].inventadas) == (5, 1)
    assert (evals[1].afirmaciones, evals[1].inventadas) == (2, 1)
    assert tasa_alucinacion(evals) == pytest.approx(2 / 7)
    assert tasa_alucinacion([evaluar_consulta(consulta(), salida(None, tipo="error"), corpus)]) is None


# --- cobertura y Gini ------------------------------------------------------------------------

def test_gini_casos_a_mano():
    assert gini([1, 1, 1, 1]) == pytest.approx(0)
    assert gini([0, 0, 0, 4]) == pytest.approx(0.75)
    assert gini([1, 2, 3]) == pytest.approx(2 / 9)
    assert gini([3, 1, 2]) == pytest.approx(2 / 9)
    assert gini([0, 5]) == pytest.approx(0.5)
    assert gini([]) is None
    assert gini([0, 0]) is None


def test_cobertura_y_recomendaciones(corpus):
    salidas = [salida(itinerario(("vie", [parada("sint-beaune"), parada("sint-pommard", "12:00")]))),
               salida(itinerario(("vie", [parada("sint-beaune"), parada("b0:Inventada", "12:00")])), id="q2"),
               salida(itinerario(("vie", [parada("sint-gevrey")])), tipo="infactible", id="q3")]
    cuentas = recomendaciones_por_bodega(salidas, corpus)
    assert set(cuentas) == set(corpus)
    assert cuentas["sint-beaune"] == 2 and cuentas["sint-pommard"] == 1
    assert cuentas["sint-gevrey"] == 0 and sum(cuentas.values()) == 3
    assert cobertura_corpus(salidas, corpus) == pytest.approx(2 / 7)
    assert gini(list(cuentas.values())) == pytest.approx(16 / 21)
    assert cobertura_corpus([], corpus) == 0
    assert cobertura_corpus(salidas, {}) == 0


# --- infactibles -----------------------------------------------------------------------------

@pytest.mark.parametrize("tipo, motivo, esperado", [
    ("infactible", "demasiadas_bodegas", True),
    ("sin_candidatas", "zonas_lejanas", True),
    ("zona_desconocida", "zona_fuera_de_borgona", True),
    ("zona_desconocida", "demasiadas_bodegas", False),
    ("zona_desconocida", None, False),
    ("itinerario", "zona_fuera_de_borgona", False),
    ("pregunta", "demasiadas_bodegas", False),
    ("error", "demasiadas_bodegas", False),
    ("tope_tokens", "zonas_lejanas", False),
])
def test_detecta_infactible(tipo, motivo, esperado):
    assert detecta_infactible(tipo, motivo) is esperado


def test_constantes_de_infactibles():
    assert DETECTAN_INFACTIBLE == {"infactible", "sin_candidatas"}
    assert REPRESENTABLES == {"zona_fuera_de_borgona"}


def test_infactibles_detectados_y_desglose(corpus):
    casos = [("i1", "demasiadas_bodegas", salida(None, tipo="infactible", id="i1")),
             ("i2", "demasiadas_bodegas", salida(id="i2")),
             ("i3", "zona_fuera_de_borgona", salida(None, tipo="zona_desconocida", id="i3")),
             ("i4", "zonas_lejanas", salida(id="i4"))]
    consultas = [consulta(i, "infactible", True, m) for i, m, _ in casos] + [consulta("f1")]
    salidas = [s for *_, s in casos] + [salida(id="f1")]
    evals = [evaluar_consulta(c, s, corpus) for c, s in zip(consultas, salidas, strict=True)]
    assert [e.infactible_detectado for e in evals] == [True, False, True, False, None]
    assert [e.hard_pass for e in evals] == [None, None, None, None, True]
    assert infactibles_detectados(evals) == pytest.approx(0.5)
    assert infactibles_detectados(evals[4:]) is None

    m, _ = resumir(consultas, salidas, corpus)
    assert m.infactibles == 4 and m.factibles == 1 and m.consultas == 5
    assert m.infactibles_detectados == pytest.approx(0.5)
    assert m.infactibles_detectados_por_motivo == pytest.approx(
        {"demasiadas_bodegas": 0.5, "zona_fuera_de_borgona": 1.0, "zonas_lejanas": 0.0})
    assert m.infactibles_detectados_representables == pytest.approx(1.0)


def test_representables_none_sin_infactibles_representables(corpus):
    consultas = [consulta("i1", "infactible", True, "zonas_lejanas")]
    m, _ = resumir(consultas, [salida(None, tipo="infactible", id="i1")], corpus)
    assert m.infactibles_detectados == pytest.approx(1.0)
    assert m.infactibles_detectados_representables is None


# --- resumen ---------------------------------------------------------------------------------

def test_resumir_por_escenario_y_tipos(corpus):
    consultas = [consulta("q1", "dias"), consulta("q2", "dias"), consulta("q3", "grupo"),
                 consulta("q4", "grupo"), consulta("q5", "infactible", True, "zonas_lejanas")]
    salidas = [salida(id="q1"), salida(None, tipo="pregunta", id="q2"), salida(id="q3"),
               salida(id="q4"), salida(None, tipo="infactible", id="q5")]
    m, evals = resumir(consultas, salidas, corpus)
    assert [e.consulta_id for e in evals] == ["q1", "q2", "q3", "q4", "q5"]
    assert m.hard_pass_rate == pytest.approx(3 / 4)
    assert m.hard_pass_por_escenario == pytest.approx({"dias": 0.5, "grupo": 1.0})
    assert m.tipos == {"itinerario": 3, "pregunta": 1, "infactible": 1}
    assert m.afirmaciones == 12 and m.inventadas == 0 and m.tasa_alucinacion == 0
    assert m.cobertura_corpus == pytest.approx(2 / 7)
    assert m.gini == pytest.approx(gini([3, 6, 0, 0, 0, 0, 0]))


def test_resumir_consulta_sin_salida_es_error(corpus):
    m, evals = resumir([consulta("q1"), consulta("q2")], [salida(id="q1")], corpus)
    assert evals[1].tipo == "error" and evals[1].hard_pass is False
    assert m.hard_pass_rate == pytest.approx(0.5)
    assert m.tipos == {"itinerario": 1, "error": 1}


def test_resumir_rechaza_salidas_duplicadas_o_ajenas(corpus):
    with pytest.raises(ValueError, match="q1"):
        resumir([consulta("q1")], [salida(id="q1"), salida(id="q1")], corpus)
    with pytest.raises(ValueError, match="q9"):
        resumir([consulta("q1")], [salida(id="q1"), salida(id="q9")], corpus)


# --- sobrevivientes de mutation -----------------------------------------------------------------

def test_afirmaciones_solo_cuentan_lo_entregado(corpus):
    # un "infactible" que trae una propuesta no le afirma nada al turista
    inventado = itinerario(("vie", [parada("b0:X", exp="Cata")]))
    assert afirmaciones(salida(inventado, tipo="infactible"), corpus) == (0, 0)
    assert afirmaciones(salida(inventado), corpus) == (2, 2)


def test_recomendaciones_siguen_despues_de_una_salida_sin_itinerario(corpus):
    salidas = [salida(None, tipo="error", id="q0"),
               salida(itinerario(("vie", [parada("sint-gevrey")])), tipo="pregunta", id="q1"),
               salida(itinerario(("vie", [parada("sint-beaune")])), id="q2")]
    cuentas = recomendaciones_por_bodega(salidas, corpus)
    assert cuentas["sint-beaune"] == 1 and cuentas["sint-gevrey"] == 0
