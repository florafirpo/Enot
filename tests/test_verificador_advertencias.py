"""Spec 010: necesidades del turista sin dato → advertencias, no violaciones (ADR-0012). Bodegas SINTÉTICAS.

Regla: dato `False` (o lista publicada sin lo pedido) = violación; dato ausente = advertencia; el francés se da
por cumplido en todas las bodegas.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from enot.modelos import Bodega, DiaItinerario, Experiencia, Horario, Itinerario, Parada, PerfilViaje
from enot.verificador import (
    IDIOMA_BASE,
    Advertencia,
    ResultadoVerificacion,
    Violacion,
    verificar,
    verificar_completo,
)

TODOS = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]


def bodega(id_: str, **campos) -> Bodega:
    """Bodega inventada, abierta todos los días de 09:00 a 19:00, accesible y con idiomas fr/en."""
    base = dict(id=id_, nombre=f"[SINTÉTICA] {id_}", lat=47.0, lon=4.80,
                horarios=[Horario(dias=TODOS, apertura="09:00", cierre="19:00")],
                accesible_movilidad_reducida=True, idiomas=["fr", "en"])
    base.update(campos)
    return Bodega(**base)


def exp(nombre: str, idiomas: list[str] | None = None) -> Experiencia:
    return Experiencia(nombre=nombre, tipo="degustacion", duracion_min=60, precio_por_persona=20, moneda="EUR",
                       idiomas=idiomas or [])


@pytest.fixture
def corpus() -> dict[str, Bodega]:
    bodegas = [
        bodega("a", experiencias=[exp("Dégustation", idiomas=["fr"]), exp("Visite")]),
        bodega("b", lon=4.81, idiomas=["fr", "de"]),
        bodega("muda", lon=4.82, idiomas=[], accesible_movilidad_reducida=None, experiencias=[exp("Visite")]),
    ]
    return {b.id: b for b in bodegas}


def perfil(**campos) -> PerfilViaje:
    base = dict(cantidad_dias=1, dia_inicio="lun", transporte="auto", personas=2)
    base.update(campos)
    return PerfilViaje(**base)


def parada(bodega_id: str, hora: str = "10:00", experiencia: str | None = None) -> Parada:
    return Parada(bodega_id=bodega_id, hora_inicio=hora, duracion_min=60, experiencia=experiencia)


def un_dia(*paradas: Parada) -> Itinerario:
    return Itinerario(dias=[DiaItinerario(numero=1, dia_semana="lun", paradas=list(paradas))])


def tipos(xs) -> list[str]:
    return [x.tipo for x in xs]


# --- accesibilidad --------------------------------------------------------------------

def test_accesibilidad_false_es_violacion(corpus):
    corpus["a"] = corpus["a"].model_copy(update={"accesible_movilidad_reducida": False})
    r = verificar_completo(un_dia(parada("a")), perfil(movilidad_reducida=True), corpus)
    assert tipos(r.violaciones) == ["accesibilidad"]
    assert r.advertencias == []


def test_accesibilidad_sin_dato_es_advertencia(corpus):
    corpus["a"] = corpus["a"].model_copy(update={"accesible_movilidad_reducida": None})
    r = verificar_completo(un_dia(parada("a")), perfil(movilidad_reducida=True), corpus)
    assert r.violaciones == []
    [w] = r.advertencias
    assert w.tipo == "accesibilidad_sin_confirmar"
    assert w.dia == 1 and w.bodega_id == "a"
    assert "no pude confirmar" in w.mensaje.casefold() and "[SINTÉTICA] a" in w.mensaje


def test_accesibilidad_sin_dato_no_pedida_no_advierte(corpus):
    r = verificar_completo(un_dia(parada("muda")), perfil(movilidad_reducida=False), corpus)
    assert r.violaciones == [] and r.advertencias == []


def test_accesibilidad_declarada_no_advierte(corpus):
    r = verificar_completo(un_dia(parada("a")), perfil(movilidad_reducida=True), corpus)
    assert r == ResultadoVerificacion(violaciones=[], advertencias=[])


# --- idioma: el francés ---------------------------------------------------------------

@pytest.mark.parametrize("frances", ["fr", "FR", "francés", "français", "french"])
def test_frances_siempre_cumple(corpus, frances):
    corpus["b"] = corpus["b"].model_copy(update={"idiomas": ["de"]})
    for b in ("muda", "b"):  # sin idiomas publicados / publica solo otros
        r = verificar_completo(un_dia(parada(b)), perfil(idiomas=[frances]), corpus)
        assert r.violaciones == [] and r.advertencias == [], b


def test_frances_basta_entre_varios_pedidos(corpus):
    corpus["b"] = corpus["b"].model_copy(update={"idiomas": ["de"]})
    r = verificar_completo(un_dia(parada("b")), perfil(idiomas=["ja", "fr"]), corpus)
    assert r.violaciones == [] and r.advertencias == []


def test_idioma_base_reconoce_el_frances():
    for forma in ("fr", "fra", "fre", "francés", "frances", "français", "francais", "french"):
        assert forma in IDIOMA_BASE
    assert "en" not in IDIOMA_BASE and "de" not in IDIOMA_BASE


# --- idioma: otros idiomas ------------------------------------------------------------

def test_otro_idioma_con_lista_sin_el_pedido_es_violacion(corpus):
    r = verificar_completo(un_dia(parada("b")), perfil(idiomas=["en"]), corpus)
    assert tipos(r.violaciones) == ["idioma_no_disponible"]
    assert r.advertencias == []


def test_otro_idioma_con_lista_que_lo_incluye(corpus):
    r = verificar_completo(un_dia(parada("b")), perfil(idiomas=["de"]), corpus)
    assert r.violaciones == [] and r.advertencias == []


def test_otro_idioma_sin_lista_es_advertencia(corpus):
    r = verificar_completo(un_dia(parada("muda", experiencia="Visite")), perfil(idiomas=["en"]), corpus)
    assert r.violaciones == []
    [w] = r.advertencias
    assert w.tipo == "idioma_sin_confirmar" and w.dia == 1 and w.bodega_id == "muda"
    assert "en" in w.mensaje and "[SINTÉTICA] muda" in w.mensaje
    assert "no pude confirmar" in w.mensaje.casefold()


def test_otro_idioma_sin_lista_en_la_experiencia_cae_a_la_bodega(corpus):
    # "Visite" no publica idiomas; la bodega "a" publica fr, en → se piden en alemán
    r = verificar_completo(un_dia(parada("a", experiencia="Visite")), perfil(idiomas=["de"]), corpus)
    assert tipos(r.violaciones) == ["idioma_no_disponible"]
    assert r.advertencias == []
    r = verificar_completo(un_dia(parada("a", experiencia="Visite")), perfil(idiomas=["en"]), corpus)
    assert r.violaciones == [] and r.advertencias == []


def test_idioma_de_la_experiencia_manda_sobre_la_bodega(corpus):
    # la bodega habla inglés, pero "Dégustation" solo publica francés
    r = verificar_completo(un_dia(parada("a", experiencia="Dégustation")), perfil(idiomas=["en"]), corpus)
    assert tipos(r.violaciones) == ["idioma_no_disponible"]
    assert r.advertencias == []


# --- resultado ------------------------------------------------------------------------

def test_advertencias_no_cuentan_para_factible(corpus):
    p = perfil(movilidad_reducida=True, idiomas=["en"])
    r = verificar_completo(un_dia(parada("muda")), p, corpus)
    assert r.violaciones == [] and len(r.advertencias) == 2
    assert r.factible is True
    r = verificar_completo(un_dia(parada("muda"), parada("fantasma", "12:00")), p, corpus)
    assert r.factible is False


def test_verificar_devuelve_solo_las_violaciones(corpus):
    p = perfil(movilidad_reducida=True, idiomas=["en"], personas=3)
    corpus["b"] = corpus["b"].model_copy(update={"capacidad_max_grupo": 2})
    it = un_dia(parada("muda"), parada("b", "12:00"))
    r = verificar_completo(it, p, corpus)
    assert r.violaciones and r.advertencias
    assert verificar(it, p, corpus) == r.violaciones
    assert all(isinstance(v, Violacion) for v in verificar(it, p, corpus))


def test_advertencias_en_orden_y_por_parada(corpus):
    it = Itinerario(dias=[
        DiaItinerario(numero=1, dia_semana="lun", paradas=[parada("muda"), parada("a", "12:00")]),
        DiaItinerario(numero=2, dia_semana="mar", paradas=[parada("muda", "10:00"), parada("muda", "12:00")]),
    ])
    r = verificar_completo(it, perfil(cantidad_dias=2, movilidad_reducida=True, idiomas=["en"]), corpus)
    assert r.violaciones == []
    assert [(w.dia, w.bodega_id) for w in r.advertencias] == [(1, "muda")] * 2 + [(2, "muda")] * 4
    assert tipos(r.advertencias) == ["accesibilidad_sin_confirmar", "idioma_sin_confirmar"] * 3
    assert all(isinstance(w, Advertencia) and w.mensaje.startswith(f"Día {w.dia}: ") for w in r.advertencias)


def test_bodega_inexistente_no_advierte(corpus):
    r = verificar_completo(un_dia(parada("fantasma")), perfil(movilidad_reducida=True, idiomas=["en"]), corpus)
    assert tipos(r.violaciones) == ["bodega_inexistente"]
    assert r.advertencias == []


# --- dieta fuera de alcance -----------------------------------------------------------

def test_perfil_sin_restricciones_alimentarias():
    assert "restricciones_alimentarias" not in PerfilViaje.model_fields
    with pytest.raises(ValidationError):
        Violacion(tipo="restriccion_alimentaria", mensaje="x")
