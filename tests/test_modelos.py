"""Spec 001: modelos de dominio y carga del corpus. Fixtures SINTÉTICAS (bodegas inventadas)."""
from __future__ import annotations

import json

import pytest
from enot.corpus_local import cargar_corpus
from enot.modelos import Bodega, Parada, PerfilViaje, a_hora, a_minutos
from pydantic import ValidationError

from .conftest import FIXTURES

FICHAS = FIXTURES / "fichas_sinteticas.jsonl"


def test_hora_valida_e_invalida():
    assert Parada(bodega_id="x", hora_inicio="09:05", duracion_min=60).hora_inicio == "09:05"
    for mala in ["25:00", "9:5", "10h", "12:60", ""]:
        with pytest.raises(ValidationError):
            Parada(bodega_id="x", hora_inicio=mala, duracion_min=60)
    with pytest.raises(ValidationError):
        Parada(bodega_id="x", hora_inicio="10:00", duracion_min=0)


def test_a_minutos_y_a_hora_son_inversas():
    assert a_minutos("00:00") == 0
    assert a_minutos("09:30") == 570
    assert a_minutos("23:59") == 1439
    assert a_hora(570) == "09:30"
    for m in (0, 61, 600, 1439):
        assert a_minutos(a_hora(m)) == m
    with pytest.raises(ValueError):
        a_minutos("24:00")


def test_bodega_desde_ficha_toma_meta():
    lineas = [json.loads(line) for line in FICHAS.read_text(encoding="utf-8").splitlines()]
    b = Bodega.desde_ficha(lineas[0])
    assert b.id == "sint-beaune"
    assert b.zona == "Côte de Beaune" and b.comuna == "Beaune"
    assert b.lat == pytest.approx(47.026) and b.lon == pytest.approx(4.84)
    assert b.capacidad_max_grupo == 12 and b.accesible_movilidad_reducida is True
    assert b.experiencias[1].precio_por_persona == 60
    sin_coord = Bodega.desde_ficha(next(x for x in lineas if x["id"] == "sint-sin-coord"))
    assert sin_coord.lat is None and sin_coord.lon is None


def test_bodega_desde_ficha_usa_meta_id_si_falta_id_raiz():
    linea = json.loads(FICHAS.read_text(encoding="utf-8").splitlines()[0])
    del linea["id"]
    assert Bodega.desde_ficha(linea).id == "sint-beaune"


def test_perfil_valida_rangos():
    ok = PerfilViaje(cantidad_dias=2, dia_inicio="jue", transporte="bici", personas=2)
    assert ok.hora_inicio_jornada == "09:30" and ok.hora_fin_jornada == "18:30"
    for malo in [dict(cantidad_dias=0), dict(cantidad_dias=4), dict(personas=0),
                 dict(transporte="helicoptero"), dict(dia_inicio="lunes"),
                 dict(restricciones_alimentarias=["sin_gluten"]), dict(hora_fin_jornada="25:00")]:
        datos = dict(cantidad_dias=1, dia_inicio="lun", transporte="auto", personas=1) | malo
        with pytest.raises(ValidationError):
            PerfilViaje(**datos)


def test_perfil_rechaza_jornada_invertida():
    with pytest.raises(ValidationError):
        PerfilViaje(cantidad_dias=1, dia_inicio="lun", transporte="auto", personas=1,
                    hora_inicio_jornada="18:00", hora_fin_jornada="10:00")


def test_cargar_corpus(tmp_path):
    corpus = cargar_corpus(FICHAS)
    assert len(corpus) == 7
    assert corpus["sint-gevrey"].comuna == "Gevrey-Chambertin"


def test_cargar_corpus_saltea_lineas_invalidas(tmp_path):
    ruta = tmp_path / "fichas.jsonl"
    validas = FICHAS.read_text(encoding="utf-8").splitlines()[:2]
    ruta.write_text("\n".join([validas[0], "{no es json", '{"nombre": "sin id"}', validas[1], ""]),
                    encoding="utf-8")
    corpus = cargar_corpus(ruta)
    assert set(corpus) == {"sint-beaune", "sint-pommard"}


def test_cargar_corpus_inexistente_devuelve_vacio(tmp_path):
    assert cargar_corpus(tmp_path / "no-existe.jsonl") == {}
