"""Spec 001: tools determinísticas (ADR-0005). Fixtures SINTÉTICAS (bodegas inventadas)."""
from __future__ import annotations

import pytest
from enot.corpus_local import cargar_corpus
from enot.modelos import Bodega
from enot.tools import ItemCosto, abierta_en, costo_experiencias, tiempo_traslado
from enot.tools.distancias import haversine_km

from .conftest import FIXTURES


@pytest.fixture(scope="module")
def corpus():
    return cargar_corpus(FIXTURES / "fichas_sinteticas.jsonl")


def bodega_en(id_, lat, lon) -> Bodega:
    return Bodega(id=id_, nombre=id_, lat=lat, lon=lon)


# --- traslados ------------------------------------------------------------------

def test_haversine_caso_conocido():
    assert haversine_km(0, 0, 0, 1) == pytest.approx(111.195, abs=0.01)
    assert haversine_km(0, 0, 1, 0) == pytest.approx(111.195, abs=0.01)
    assert haversine_km(47.0, 4.8, 47.0, 4.8) == 0


def test_misma_bodega_tarda_cero(corpus):
    r = tiempo_traslado(corpus, "sint-beaune", "sint-beaune", "auto")
    assert r.minutos == 0 and r.km == 0 and r.error is None


@pytest.mark.parametrize("modo,minutos", [("auto", 20), ("traslado", 20), ("bici", 58), ("a_pie", 193)])
def test_minutos_calculados_a_mano(modo, minutos):
    # 0,1° de longitud en el ecuador = 11,1195 km; × 1,3 = 14,455 km
    # auto 45 km/h → 19,27 → 20 · bici 15 km/h → 57,8 → 58 · a pie 4,5 km/h → 192,7 → 193
    corpus = {"a": bodega_en("a", 0.0, 0.0), "b": bodega_en("b", 0.0, 0.1)}
    r = tiempo_traslado(corpus, "a", "b", modo)
    assert r.error is None
    assert r.km == pytest.approx(14.455, abs=0.01)
    assert r.minutos == minutos


def test_traslado_es_simetrico(corpus):
    ida = tiempo_traslado(corpus, "sint-beaune", "sint-gevrey", "auto")
    vuelta = tiempo_traslado(corpus, "sint-gevrey", "sint-beaune", "auto")
    assert ida.minutos == vuelta.minutos and ida.minutos > 0


def test_traslado_sin_coordenadas_da_error(corpus):
    r = tiempo_traslado(corpus, "sint-beaune", "sint-sin-coord", "auto")
    assert r.minutos is None and r.km is None and "coordenadas" in r.error


def test_traslado_bodega_inexistente_da_error(corpus):
    r = tiempo_traslado(corpus, "sint-beaune", "no-existe", "auto")
    assert r.minutos is None and "no-existe" in r.error


def test_traslado_modo_invalido_da_error(corpus):
    r = tiempo_traslado(corpus, "sint-beaune", "sint-pommard", "teletransporte")
    assert r.minutos is None and "modo" in r.error


# --- horarios -------------------------------------------------------------------

@pytest.mark.parametrize("inicio,duracion,esperado", [
    ("09:59", 60, False),   # empieza 1 minuto antes de abrir
    ("10:00", 60, True),    # empieza justo al abrir
    ("17:00", 60, True),    # termina justo al cerrar (18:00)
    ("17:01", 60, False),   # termina 1 minuto después del cierre
    ("18:00", 30, False),   # empieza al cierre
])
def test_bordes_de_horario(corpus, inicio, duracion, esperado):
    r = abierta_en(corpus, "sint-beaune", "mar", inicio, duracion)
    assert r.abierta is esperado


def test_dia_sin_horario_esta_cerrada(corpus):
    r = abierta_en(corpus, "sint-beaune", "lun", "11:00", 60)
    assert r.abierta is False and "lun" in r.motivo


def test_horario_partido_respeta_la_pausa(corpus):
    assert abierta_en(corpus, "sint-gevrey", "lun", "10:30", 60).abierta is True
    assert abierta_en(corpus, "sint-gevrey", "lun", "11:30", 60).abierta is False   # cruza el mediodía
    assert abierta_en(corpus, "sint-gevrey", "lun", "14:00", 60).abierta is True


def test_cerrada_fuera_de_horario_explica_el_horario(corpus):
    r = abierta_en(corpus, "sint-beaune", "mar", "08:00", 60)
    assert r.abierta is False and "10:00" in r.motivo and "18:00" in r.motivo


def test_bodega_sin_horario_publicado_es_desconocido(corpus):
    r = abierta_en(corpus, "sint-sin-horario", "mar", "11:00", 60)
    assert r.abierta is None and "horario" in r.motivo


def test_horario_sin_horas_es_desconocido(corpus):
    r = abierta_en(corpus, "sint-horario-incompleto", "sab", "11:00", 60)
    assert r.abierta is None


def test_horario_hora_invalida(corpus):
    r = abierta_en(corpus, "sint-beaune", "mar", "25:00", 60)
    assert r.abierta is None and "hora" in r.motivo


def test_horario_bodega_inexistente(corpus):
    r = abierta_en(corpus, "no-existe", "mar", "11:00", 60)
    assert r.abierta is None and "no-existe" in r.motivo


# --- costos ---------------------------------------------------------------------

def test_costo_suma_por_personas(corpus):
    r = costo_experiencias(corpus, [ItemCosto(bodega_id="sint-beaune", experiencia="Grands crus"),
                                    ItemCosto(bodega_id="sint-pommard", experiencia="visite et dégustation")], 2)
    assert r.total_eur == pytest.approx((60 + 35) * 2)
    assert r.sin_precio == [] and r.errores == []
    assert [d.subtotal_eur for d in r.detalle] == [120, 70]


def test_costo_sin_experiencia_elige_la_mas_barata_en_eur(corpus):
    r = costo_experiencias(corpus, [ItemCosto(bodega_id="sint-beaune")], 3)
    assert r.total_eur == pytest.approx(60)  # 20 € × 3
    assert r.detalle[0].experiencia == "Dégustation classique"


def test_costo_precios_sin_moneda_o_en_otra_moneda_no_se_suman(corpus):
    r = costo_experiencias(corpus, [ItemCosto(bodega_id="sint-chablis", experiencia="Dégustation"),
                                    ItemCosto(bodega_id="sint-chablis", experiencia="Visite USD"),
                                    ItemCosto(bodega_id="sint-sin-coord")], 1)
    assert r.total_eur == 0
    assert len(r.sin_precio) == 3


def test_costo_bodega_sin_experiencias_va_a_sin_precio(corpus):
    r = costo_experiencias(corpus, [ItemCosto(bodega_id="sint-sin-horario")], 2)
    assert r.total_eur == 0 and r.sin_precio and r.errores == []


def test_costo_errores_por_bodega_o_experiencia_inexistente(corpus):
    r = costo_experiencias(corpus, [ItemCosto(bodega_id="no-existe"),
                                    ItemCosto(bodega_id="sint-beaune", experiencia="Paseo en globo"),
                                    ItemCosto(bodega_id="sint-gevrey")], 1)
    assert r.total_eur == pytest.approx(25)
    assert len(r.errores) == 2


def test_costo_personas_invalidas(corpus):
    r = costo_experiencias(corpus, [ItemCosto(bodega_id="sint-beaune")], 0)
    assert r.total_eur == 0 and r.errores
