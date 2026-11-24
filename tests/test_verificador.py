"""Spec 002: verificador de restricciones duras (ADR-0003). Bodegas SINTÉTICAS (inventadas).

Por cada tipo de violación hay un caso que la detecta y uno que no la confunde con un itinerario válido.
"""
from __future__ import annotations

import pytest

from enot.corpus_local import cargar_corpus
from enot.modelos import (
    Bodega,
    DiaItinerario,
    Experiencia,
    Horario,
    Itinerario,
    Parada,
    PerfilViaje,
    a_hora,
    a_minutos,
)
from enot.tools import tiempo_traslado
from enot.verificador import TIPOS_COMIDA, Violacion, verificar

from .conftest import FIXTURES

TODOS = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]


def bodega(id_: str, **campos) -> Bodega:
    """Bodega inventada, abierta todos los días de 09:00 a 19:00 salvo que se diga otra cosa."""
    base = dict(
        id=id_,
        nombre=f"[SINTÉTICA] {id_}",
        lat=47.0,
        lon=4.80,
        horarios=[Horario(dias=TODOS, apertura="09:00", cierre="19:00")],
        accesible_movilidad_reducida=True,
        idiomas=["fr", "en"],
    )
    base.update(campos)
    return Bodega(**base)


def exp(nombre: str, tipo: str = "degustacion", precio: float | None = 20, moneda: str | None = "EUR",
        idiomas: list[str] | None = None) -> Experiencia:
    return Experiencia(nombre=nombre, tipo=tipo, duracion_min=60, precio_por_persona=precio, moneda=moneda,
                       idiomas=idiomas or [])


@pytest.fixture
def corpus() -> dict[str, Bodega]:
    bodegas = [
        bodega("a", experiencias=[exp("Dégustation", idiomas=["fr", "en"]),
                                  exp("Déjeuner", tipo="almuerzo", precio=50, idiomas=["fr"])]),
        # ~3,8 km al este de "a": 7 min en auto, 67 min a pie
        bodega("b", lon=4.85, experiencias=[exp("Visite", tipo="visita_guiada", precio=30)],
               idiomas=["fr", "de"]),
        bodega("sin-coord", lat=None, lon=None),
        bodega("sin-horario", horarios=[], lon=4.81),
    ]
    return {b.id: b for b in bodegas}


def perfil(**campos) -> PerfilViaje:
    base = dict(cantidad_dias=1, dia_inicio="lun", transporte="auto", personas=2)
    base.update(campos)
    return PerfilViaje(**base)


def parada(bodega_id: str, hora: str, dur: int = 60, experiencia: str | None = None) -> Parada:
    return Parada(bodega_id=bodega_id, hora_inicio=hora, duracion_min=dur, experiencia=experiencia)


def un_dia(*paradas: Parada, dia: str = "lun", numero: int = 1) -> Itinerario:
    return Itinerario(dias=[DiaItinerario(numero=numero, dia_semana=dia, paradas=list(paradas))])


def tipos(violaciones: list[Violacion]) -> list[str]:
    return [v.tipo for v in violaciones]


def de_tipo(violaciones: list[Violacion], tipo: str) -> list[Violacion]:
    return [v for v in violaciones if v.tipo == tipo]


def minutos_traslado(corpus, origen, destino, modo="auto") -> int:
    r = tiempo_traslado(corpus, origen, destino, modo)
    assert r.error is None
    return r.minutos


# --- generales -------------------------------------------------------------------

def test_itinerario_valido_no_tiene_violaciones(corpus):
    it = un_dia(parada("a", "10:00", 60, "Dégustation"), parada("b", "14:00", 90, "Visite"))
    assert verificar(it, perfil(presupuesto_max_por_persona=100, idiomas=["fr"]), corpus) == []


def test_itinerario_vacio_es_valido(corpus):
    assert verificar(Itinerario(), perfil(), corpus) == []
    assert verificar(un_dia(), perfil(), corpus) == []


def test_valido_con_la_fixture_de_fichas():
    corpus = cargar_corpus(FIXTURES / "fichas_sinteticas.jsonl")
    # martes en la Côte de Beaune: Beaune abre 10–18 (mar a dom), Pommard 9:30–17:30 (lun a sab)
    it = un_dia(parada("sint-beaune", "10:00", 60, "Dégustation classique"),
                parada("sint-pommard", "14:00", 60, "Visite et dégustation"), dia="mar")
    assert verificar(it, perfil(dia_inicio="mar", personas=4, presupuesto_max_por_persona=55,
                                idiomas=["fr"]), corpus) == []


def test_cada_violacion_trae_dia_bodega_y_mensaje(corpus):
    it = Itinerario(dias=[DiaItinerario(numero=1, dia_semana="lun", paradas=[parada("a", "10:00")]),
                          DiaItinerario(numero=2, dia_semana="mar", paradas=[parada("fantasma", "10:00")])])
    [v] = verificar(it, perfil(cantidad_dias=2), corpus)
    assert v.tipo == "bodega_inexistente"
    assert v.dia == 2 and v.bodega_id == "fantasma"
    assert "fantasma" in v.mensaje and "2" in v.mensaje


def test_orden_determinista(corpus):
    corpus["a"] = corpus["a"].model_copy(update={"capacidad_max_grupo": 1, "accesible_movilidad_reducida": False})
    it = Itinerario(dias=[
        DiaItinerario(numero=1, dia_semana="lun", paradas=[parada("fantasma", "10:00"), parada("a", "11:00")]),
        DiaItinerario(numero=2, dia_semana="mar", paradas=[parada("a", "08:00", 60, "Dégustation")]),
    ])
    p = perfil(cantidad_dias=2, movilidad_reducida=True, presupuesto_max_por_persona=1)
    v = verificar(it, p, corpus)
    assert v == verificar(it, p, corpus)
    assert [x.dia or 99 for x in v] == sorted(x.dia or 99 for x in v)  # día por día; lo global (None) al final
    assert v[0].tipo == "bodega_inexistente"
    assert v[-1].tipo == "presupuesto_excedido" and v[-1].dia is None and v[-1].bodega_id is None


def test_tipos_comida():
    assert TIPOS_COMIDA == {"almuerzo", "cena", "picnic", "maridaje"}


# --- bodega y experiencia inexistentes -------------------------------------------

def test_detecta_bodega_inexistente(corpus):
    v = verificar(un_dia(parada("a", "10:00"), parada("fantasma", "12:00")), perfil(), corpus)
    assert tipos(v) == ["bodega_inexistente"]
    assert v[0].bodega_id == "fantasma"


def test_bodega_inexistente_no_genera_otras_violaciones(corpus):
    # con requisitos que ninguna bodega cumpliría: de una bodega inexistente solo se informa que no existe
    p = perfil(movilidad_reducida=True, idiomas=["ja"], restricciones_alimentarias=["vegano"],
               presupuesto_max_por_persona=0)
    v = verificar(un_dia(parada("fantasma", "10:00", 60, "Inventada")), p, corpus)
    assert tipos(v) == ["bodega_inexistente"]


def test_detecta_experiencia_inexistente(corpus):
    v = verificar(un_dia(parada("a", "10:00", 60, "Vuelo en globo")), perfil(), corpus)
    assert tipos(v) == ["experiencia_inexistente"]
    assert v[0].bodega_id == "a" and "Vuelo en globo" in v[0].mensaje
    assert "Dégustation" in v[0].mensaje  # sugiere las que sí existen


def test_experiencia_por_nombre_sin_mayusculas(corpus):
    assert verificar(un_dia(parada("a", "10:00", 60, "DÉGUSTATION")), perfil(), corpus) == []


# --- horario -----------------------------------------------------------------------

@pytest.fixture
def corpus_10a18(corpus):
    corpus["h"] = bodega("h", horarios=[Horario(dias=["mar", "mie", "jue", "vie", "sab", "dom"],
                                                apertura="10:00", cierre="18:00")])
    return corpus


def test_detecta_visita_antes_de_abrir(corpus_10a18):
    v = verificar(un_dia(parada("h", "09:59"), dia="mar"), perfil(dia_inicio="mar"), corpus_10a18)
    assert tipos(v) == ["cerrada"]


def test_abre_justo_y_termina_justo_al_cierre(corpus_10a18):
    p = perfil(dia_inicio="mar")
    assert verificar(un_dia(parada("h", "10:00"), dia="mar"), p, corpus_10a18) == []
    assert verificar(un_dia(parada("h", "17:00"), dia="mar"), p, corpus_10a18) == []


def test_cruza_el_cierre_por_un_minuto(corpus_10a18):
    v = verificar(un_dia(parada("h", "17:01"), dia="mar"), perfil(dia_inicio="mar"), corpus_10a18)
    assert tipos(v) == ["cerrada"]


def test_dia_cerrado(corpus_10a18):
    v = verificar(un_dia(parada("h", "11:00"), dia="lun"), perfil(), corpus_10a18)
    assert tipos(v) == ["cerrada"]
    assert "lun" in v[0].mensaje


def test_usa_el_dia_de_la_semana_del_itinerario(corpus_10a18):
    it = Itinerario(dias=[DiaItinerario(numero=1, dia_semana="dom", paradas=[parada("h", "11:00")]),
                          DiaItinerario(numero=2, dia_semana="lun", paradas=[parada("h", "11:00")])])
    v = verificar(it, perfil(cantidad_dias=2, dia_inicio="dom"), corpus_10a18)
    assert tipos(v) == ["cerrada"] and v[0].dia == 2


def test_sin_horario_publicado_no_es_violacion(corpus):
    assert verificar(un_dia(parada("sin-horario", "11:00")), perfil(), corpus) == []


def test_mensaje_de_cerrada_explica_el_horario(corpus_10a18):
    [v] = verificar(un_dia(parada("h", "17:30"), dia="mar"), perfil(dia_inicio="mar"), corpus_10a18)
    assert "17:30" in v.mensaje and "18:30" in v.mensaje  # la visita
    assert "10:00" in v.mensaje and "18:00" in v.mensaje  # el horario de la bodega


# --- traslados ---------------------------------------------------------------------

def test_traslado_entra_justo(corpus):
    m = minutos_traslado(corpus, "a", "b")
    assert m > 0
    it = un_dia(parada("a", "10:00", 60), parada("b", a_hora(a_minutos("11:00") + m)))
    assert verificar(it, perfil(), corpus) == []


def test_traslado_falta_un_minuto(corpus):
    m = minutos_traslado(corpus, "a", "b")
    it = un_dia(parada("a", "10:00", 60), parada("b", a_hora(a_minutos("11:00") + m - 1)))
    v = verificar(it, perfil(), corpus)
    assert tipos(v) == ["traslado_imposible"]
    assert v[0].bodega_id == "b" and v[0].dia == 1
    assert str(m) in v[0].mensaje  # dice cuánto tarda


def test_traslado_usa_el_modo_del_perfil(corpus):
    m_auto = minutos_traslado(corpus, "a", "b", "auto")
    m_pie = minutos_traslado(corpus, "a", "b", "a_pie")
    assert m_pie > m_auto
    it = un_dia(parada("a", "10:00", 60), parada("b", a_hora(a_minutos("11:00") + m_auto)))
    assert verificar(it, perfil(transporte="auto"), corpus) == []
    assert tipos(verificar(it, perfil(transporte="a_pie"), corpus)) == ["traslado_imposible"]


def test_traslado_en_la_misma_bodega_no_necesita_tiempo(corpus):
    it = un_dia(parada("a", "10:00", 60, "Dégustation"), parada("a", "11:00", 120, "Déjeuner"))
    assert verificar(it, perfil(), corpus) == []


def test_superposicion_sin_coordenadas(corpus):
    v = verificar(un_dia(parada("a", "10:00", 60), parada("sin-coord", "10:30")), perfil(), corpus)
    assert tipos(v) == ["traslado_imposible"]


def test_sin_coordenadas_y_sin_superposicion_no_es_violacion(corpus):
    it = un_dia(parada("a", "10:00", 60), parada("sin-coord", "11:00"))
    assert verificar(it, perfil(), corpus) == []


def test_traslado_solo_entre_paradas_del_mismo_dia(corpus):
    it = Itinerario(dias=[DiaItinerario(numero=1, dia_semana="lun", paradas=[parada("a", "17:00", 60)]),
                          DiaItinerario(numero=2, dia_semana="mar", paradas=[parada("b", "10:00")])])
    assert verificar(it, perfil(cantidad_dias=2), corpus) == []


def test_paradas_desordenadas_se_detectan(corpus):
    v = verificar(un_dia(parada("a", "14:00", 60), parada("b", "10:00", 60)), perfil(), corpus)
    assert tipos(v) == ["traslado_imposible"]


def test_traslado_chequea_cada_par_consecutivo(corpus):
    m = minutos_traslado(corpus, "a", "b")
    it = un_dia(parada("a", "10:00", 60), parada("b", "13:00", 60),
                parada("a", a_hora(a_minutos("14:00") + m - 1), 60))
    v = verificar(it, perfil(), corpus)
    assert tipos(v) == ["traslado_imposible"] and v[0].bodega_id == "a"


def test_traslado_salta_la_bodega_inexistente(corpus):
    # a → fantasma → b: no se calcula traslado con la inexistente, pero sí se informa que no existe
    it = un_dia(parada("a", "10:00", 60), parada("fantasma", "11:00", 30), parada("b", "11:30", 60))
    assert tipos(verificar(it, perfil(), corpus)) == ["bodega_inexistente"]


# --- jornada -----------------------------------------------------------------------

def test_jornada_bordes_exactos(corpus):
    it = un_dia(parada("a", "09:30", 60), parada("b", "17:30", 60))
    assert verificar(it, perfil(), corpus) == []


def test_jornada_empieza_antes(corpus):
    v = verificar(un_dia(parada("a", "09:29", 60)), perfil(), corpus)
    assert tipos(v) == ["jornada_excedida"]
    assert "09:29" in v[0].mensaje and "09:30" in v[0].mensaje


def test_jornada_termina_despues(corpus):
    v = verificar(un_dia(parada("a", "10:00"), parada("b", "17:31", 60)), perfil(), corpus)
    assert tipos(v) == ["jornada_excedida"]
    assert "18:31" in v[0].mensaje and "18:30" in v[0].mensaje


def test_jornada_respeta_el_perfil(corpus):
    it = un_dia(parada("a", "11:00", 60))
    assert verificar(it, perfil(hora_inicio_jornada="11:00", hora_fin_jornada="12:00"), corpus) == []
    assert tipos(verificar(it, perfil(hora_inicio_jornada="11:01"), corpus)) == ["jornada_excedida"]
    assert tipos(verificar(it, perfil(hora_fin_jornada="11:59"), corpus)) == ["jornada_excedida"]


def test_jornada_una_violacion_por_dia(corpus):
    v = verificar(un_dia(parada("a", "09:00", 30), parada("b", "18:00", 60)), perfil(), corpus)
    assert tipos(v) == ["jornada_excedida"]
    assert v[0].dia == 1 and v[0].bodega_id is None


def test_jornada_mira_la_ultima_en_terminar(corpus):
    # la segunda parada empieza después pero termina antes que la primera (está superpuesta)
    it = un_dia(parada("a", "15:00", 240), parada("a", "16:00", 30))
    assert "jornada_excedida" in tipos(verificar(it, perfil(), corpus))


# --- presupuesto ---------------------------------------------------------------------

def test_presupuesto_igual_no_es_violacion(corpus):
    it = un_dia(parada("a", "10:00", 60, "Dégustation"), parada("b", "14:00", 60, "Visite"))
    assert verificar(it, perfil(presupuesto_max_por_persona=50), corpus) == []


def test_presupuesto_excedido_por_un_euro(corpus):
    it = un_dia(parada("a", "10:00", 60, "Dégustation"), parada("b", "14:00", 60, "Visite"))
    v = verificar(it, perfil(presupuesto_max_por_persona=49), corpus)
    assert tipos(v) == ["presupuesto_excedido"]
    assert v[0].dia is None and v[0].bodega_id is None
    assert "50" in v[0].mensaje and "49" in v[0].mensaje


def test_presupuesto_es_por_persona(corpus):
    it = un_dia(parada("a", "10:00", 60, "Dégustation"))
    assert verificar(it, perfil(personas=6, presupuesto_max_por_persona=20), corpus) == []
    assert tipos(verificar(it, perfil(personas=6, presupuesto_max_por_persona=19.99), corpus)) == [
        "presupuesto_excedido"]


def test_presupuesto_suma_todos_los_dias(corpus):
    it = Itinerario(dias=[
        DiaItinerario(numero=1, dia_semana="lun", paradas=[parada("a", "10:00", 60, "Dégustation")]),
        DiaItinerario(numero=2, dia_semana="mar", paradas=[parada("b", "10:00", 60, "Visite")]),
    ])
    assert tipos(verificar(it, perfil(cantidad_dias=2, presupuesto_max_por_persona=30), corpus)) == [
        "presupuesto_excedido"]


def test_presupuesto_sin_experiencia_usa_la_mas_barata(corpus):
    it = un_dia(parada("a", "10:00", 60))  # Dégustation 20 < Déjeuner 50
    assert verificar(it, perfil(presupuesto_max_por_persona=20), corpus) == []
    assert tipos(verificar(it, perfil(presupuesto_max_por_persona=19), corpus)) == ["presupuesto_excedido"]


def test_sin_presupuesto_no_se_chequea(corpus):
    it = un_dia(parada("a", "11:00", 120, "Déjeuner"))
    assert verificar(it, perfil(presupuesto_max_por_persona=None), corpus) == []


def test_presupuesto_cero(corpus):
    it = un_dia(parada("a", "10:00", 60, "Dégustation"))
    assert tipos(verificar(it, perfil(presupuesto_max_por_persona=0), corpus)) == ["presupuesto_excedido"]
    assert verificar(un_dia(parada("sin-horario", "10:00")), perfil(presupuesto_max_por_persona=0), corpus) == []


def test_presupuesto_no_cuenta_precios_sin_eur(corpus):
    corpus["usd"] = bodega("usd", lon=4.801, experiencias=[exp("Visit", precio=500, moneda="USD"),
                                                         exp("Libre", precio=None, moneda=None)])
    it = un_dia(parada("usd", "10:00", 60, "Visit"), parada("usd", "11:00", 60, "Libre"))
    assert verificar(it, perfil(presupuesto_max_por_persona=10), corpus) == []


def test_experiencia_inventada_no_esquiva_el_presupuesto(corpus):
    it = un_dia(parada("a", "11:00", 120, "Déjeuner gratuit"))
    assert "experiencia_inexistente" in tipos(verificar(it, perfil(presupuesto_max_por_persona=1), corpus))


# --- capacidad -----------------------------------------------------------------------

def test_grupo_igual_a_capacidad(corpus):
    corpus["a"] = corpus["a"].model_copy(update={"capacidad_max_grupo": 6})
    assert verificar(un_dia(parada("a", "10:00")), perfil(personas=6), corpus) == []


def test_grupo_supera_capacidad(corpus):
    corpus["a"] = corpus["a"].model_copy(update={"capacidad_max_grupo": 6})
    v = verificar(un_dia(parada("a", "10:00")), perfil(personas=7), corpus)
    assert tipos(v) == ["grupo_excede_capacidad"]
    assert v[0].bodega_id == "a" and "7" in v[0].mensaje and "6" in v[0].mensaje


def test_capacidad_no_publicada(corpus):
    assert verificar(un_dia(parada("a", "10:00")), perfil(personas=40), corpus) == []


# --- restricciones alimentarias -------------------------------------------------------

def con_dieta(corpus, **opciones):
    corpus["a"] = corpus["a"].model_copy(update=opciones)
    return corpus


def test_almuerzo_sin_opcion_declarada(corpus):
    con_dieta(corpus, opciones_sin_tacc=False)
    v = verificar(un_dia(parada("a", "12:00", 120, "Déjeuner")), perfil(restricciones_alimentarias=["sin_tacc"]),
                  corpus)
    assert tipos(v) == ["restriccion_alimentaria"]
    assert v[0].bodega_id == "a" and "sin_tacc" in v[0].mensaje


def test_almuerzo_con_opcion_declarada(corpus):
    con_dieta(corpus, opciones_sin_tacc=True)
    it = un_dia(parada("a", "12:00", 120, "Déjeuner"))
    assert verificar(it, perfil(restricciones_alimentarias=["sin_tacc"]), corpus) == []


@pytest.mark.parametrize("tipo", ["almuerzo", "cena", "picnic", "maridaje"])
def test_cada_tipo_de_comida_chequea_dieta(corpus, tipo):
    corpus["a"] = corpus["a"].model_copy(update={"experiencias": [exp("Comida", tipo=tipo)]})
    v = verificar(un_dia(parada("a", "12:00", 60, "Comida")), perfil(restricciones_alimentarias=["vegano"]), corpus)
    assert tipos(v) == ["restriccion_alimentaria"]


def test_degustacion_no_chequea_dieta(corpus):
    con_dieta(corpus, opciones_sin_tacc=False)
    it = un_dia(parada("a", "10:00", 60, "Dégustation"))
    assert verificar(it, perfil(restricciones_alimentarias=["sin_tacc"]), corpus) == []


def test_parada_sin_experiencia_no_chequea_dieta(corpus):
    con_dieta(corpus, opciones_sin_tacc=False)
    assert verificar(un_dia(parada("a", "12:00", 120)), perfil(restricciones_alimentarias=["sin_tacc"]), corpus) == []


def test_vegano_cubre_vegetariano(corpus):
    con_dieta(corpus, opciones_vegetarianas=None, opciones_veganas=True)
    it = un_dia(parada("a", "12:00", 120, "Déjeuner"))
    assert verificar(it, perfil(restricciones_alimentarias=["vegetariano"]), corpus) == []


def test_vegetariano_no_cubre_vegano(corpus):
    con_dieta(corpus, opciones_vegetarianas=True, opciones_veganas=None)
    it = un_dia(parada("a", "12:00", 120, "Déjeuner"))
    assert verificar(it, perfil(restricciones_alimentarias=["vegetariano"]), corpus) == []
    assert tipos(verificar(it, perfil(restricciones_alimentarias=["vegano"]), corpus)) == ["restriccion_alimentaria"]


def test_dieta_None_es_violacion(corpus):
    con_dieta(corpus, opciones_vegetarianas=None, opciones_veganas=None)
    it = un_dia(parada("a", "12:00", 120, "Déjeuner"))
    assert tipos(verificar(it, perfil(restricciones_alimentarias=["vegetariano"]), corpus)) == [
        "restriccion_alimentaria"]


def test_dieta_una_violacion_por_restriccion(corpus):
    con_dieta(corpus, opciones_sin_tacc=True, opciones_vegetarianas=False, opciones_veganas=False)
    it = un_dia(parada("a", "12:00", 120, "Déjeuner"))
    v = verificar(it, perfil(restricciones_alimentarias=["sin_tacc", "vegetariano", "vegano"]), corpus)
    assert tipos(v) == ["restriccion_alimentaria", "restriccion_alimentaria"]
    assert "vegetariano" in v[0].mensaje and "vegano" in v[1].mensaje


# --- accesibilidad --------------------------------------------------------------------

@pytest.mark.parametrize("valor", [False, None])
def test_accesibilidad_no_declarada(corpus, valor):
    corpus["a"] = corpus["a"].model_copy(update={"accesible_movilidad_reducida": valor})
    v = verificar(un_dia(parada("a", "10:00")), perfil(movilidad_reducida=True), corpus)
    assert tipos(v) == ["accesibilidad"] and v[0].bodega_id == "a"


def test_accesibilidad_declarada(corpus):
    assert verificar(un_dia(parada("a", "10:00")), perfil(movilidad_reducida=True), corpus) == []


def test_accesibilidad_no_pedida(corpus):
    corpus["a"] = corpus["a"].model_copy(update={"accesible_movilidad_reducida": False})
    assert verificar(un_dia(parada("a", "10:00")), perfil(movilidad_reducida=False), corpus) == []


# --- idioma ---------------------------------------------------------------------------

def test_idioma_de_la_experiencia(corpus):
    it = un_dia(parada("a", "10:00", 60, "Dégustation"))  # fr, en
    assert verificar(it, perfil(idiomas=["en"]), corpus) == []


def test_idioma_no_disponible_en_la_experiencia(corpus):
    # la bodega habla inglés, pero el almuerzo solo es en francés
    v = verificar(un_dia(parada("a", "12:00", 60, "Déjeuner")), perfil(idiomas=["en"]), corpus)
    assert tipos(v) == ["idioma_no_disponible"]
    assert v[0].bodega_id == "a" and "en" in v[0].mensaje and "fr" in v[0].mensaje


def test_idioma_cae_a_la_bodega(corpus):
    # "Visite" no publica idiomas: valen los de la bodega (fr, de); sin experiencia, también
    assert verificar(un_dia(parada("b", "10:00", 60, "Visite")), perfil(idiomas=["de"]), corpus) == []
    assert verificar(un_dia(parada("b", "10:00")), perfil(idiomas=["de"]), corpus) == []
    assert tipos(verificar(un_dia(parada("b", "10:00")), perfil(idiomas=["en"]), corpus)) == ["idioma_no_disponible"]


def test_idioma_basta_uno(corpus):
    assert verificar(un_dia(parada("b", "10:00")), perfil(idiomas=["en", "de"]), corpus) == []


def test_idioma_sin_datos_es_violacion(corpus):
    corpus["a"] = corpus["a"].model_copy(update={"idiomas": []})
    v = verificar(un_dia(parada("a", "10:00")), perfil(idiomas=["fr"]), corpus)
    assert tipos(v) == ["idioma_no_disponible"]


def test_idioma_sin_mayusculas(corpus):
    corpus["a"] = corpus["a"].model_copy(update={"idiomas": ["FR"]})
    assert verificar(un_dia(parada("a", "10:00")), perfil(idiomas=["fr"]), corpus) == []
    assert verificar(un_dia(parada("b", "10:00")), perfil(idiomas=["DE"]), corpus) == []


def test_idioma_no_pedido(corpus):
    corpus["a"] = corpus["a"].model_copy(update={"idiomas": []})
    assert verificar(un_dia(parada("a", "10:00")), perfil(idiomas=[]), corpus) == []


# --- varias a la vez --------------------------------------------------------------------

def test_detecta_varias_en_la_misma_parada(corpus):
    corpus["a"] = corpus["a"].model_copy(update={"capacidad_max_grupo": 2, "accesible_movilidad_reducida": None})
    p = perfil(personas=3, movilidad_reducida=True, idiomas=["ja"])
    v = verificar(un_dia(parada("a", "10:00")), p, corpus)
    assert sorted(tipos(v)) == ["accesibilidad", "grupo_excede_capacidad", "idioma_no_disponible"]
    assert all(x.bodega_id == "a" and x.dia == 1 and x.mensaje for x in v)
