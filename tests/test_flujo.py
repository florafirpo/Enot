"""Spec 005: flujo completo (relevar → buscar → planificar → verificar → responder) con circuit breaker.

Todo offline: `ClienteFalso` con un guion por nodo, `EmbedderFalso` y bodegas SINTÉTICAS
(`tests/fixtures/fichas_sinteticas.jsonl`). Cada llamada del `ClienteFalso` informa 100 + 50 = 150 tokens.
"""
from __future__ import annotations

import json
from typing import get_args

import pytest

from enot import prompts
from enot.corpus_local import cargar_corpus
from enot.flujo import (
    DESCRIPCION_VIOLACION,
    MAX_INTENTOS,
    Flujo,
    Respuesta,
    Sesion,
    avisar_zonas_desconocidas,
    explicar_infactible,
    explicar_sin_candidatas,
    tokens_usados,
)
from enot.modelos import Bodega, DiaItinerario, Itinerario, Parada, PerfilViaje
from enot.nodos import PREGUNTAS, contexto_planificador, render_itinerario
from enot.retrieval import Indice
from enot.trazas import EventoTraza, Traza
from enot.verificador import TipoViolacion, Violacion, verificar_completo
from tests.conftest import FIXTURES, ClienteFalso
from tests.dobles import EmbedderFalso

TOKENS_POR_LLAMADA = 150


class Guion:
    """Respuestas guionadas por nodo: reconoce el nodo por el prompt de sistema y devuelve, en orden, la siguiente
    respuesta de ese nodo (la última se repite; una función se llama con `(sistema, usuario)`). Registra el mensaje de usuario que recibió cada nodo."""

    def __init__(self, relevamiento=(), planificador=(), respuesta=()):
        self.colas = {"relevamiento": list(relevamiento), "planificador": list(planificador),
                      "respuesta": list(respuesta)}
        self.recibido: dict[str, list[str]] = {n: [] for n in self.colas}

    def __call__(self, sistema, usuario):
        nodo = next(n for n in self.colas if sistema == prompts.cargar(n))
        self.recibido[nodo].append(usuario)
        cola = self.colas[nodo]
        assert cola, f"el guion no tiene respuestas para {nodo}"
        r = cola.pop(0) if len(cola) > 1 else cola[0]
        return r(sistema, usuario) if callable(r) else r


def cliente(guion: Guion) -> ClienteFalso:
    return ClienteFalso([guion])


PERFIL = {"cantidad_dias": 1, "dia_inicio": "vie", "transporte": "auto", "personas": 2}
VALIDO = {"dias": [{"paradas": [
    {"bodega_id": "sint-beaune", "hora_inicio": "10:00", "duracion_min": 60, "experiencia": "Dégustation classique"},
    {"bodega_id": "sint-pommard", "hora_inicio": "11:30", "duracion_min": 60, "experiencia": "Visite et dégustation"},
]}]}
UNA_PARADA = {"dias": [{"paradas": [
    {"bodega_id": "sint-beaune", "hora_inicio": "10:00", "duracion_min": 60, "experiencia": "Dégustation classique"},
]}]}
# fuera del horario de la bodega (abre 10:00) y de la jornada del turista (09:30)
INVALIDO = {"dias": [{"paradas": [{"bodega_id": "sint-beaune", "hora_inicio": "08:00", "duracion_min": 60}]}]}
SALIDA_RESPUESTA = {"introduccion": "Te armé este recorrido.", "motivos": []}


@pytest.fixture
def corpus() -> dict[str, Bodega]:
    return cargar_corpus(FIXTURES / "fichas_sinteticas.jsonl")


@pytest.fixture
def indice(corpus) -> Indice:
    return Indice(list(corpus.values()), EmbedderFalso())


@pytest.fixture
def sesion(tmp_path) -> Sesion:
    return Sesion.nueva(tmp_path / "trazas")


def itinerario(datos: dict, dia: str = "vie") -> Itinerario:
    return Itinerario(dias=[DiaItinerario(numero=n, dia_semana=dia, paradas=[Parada(**p) for p in d["paradas"]])
                            for n, d in enumerate(datos["dias"], 1)])


def nodos_llamados(sesion: Sesion) -> list[tuple[str, int]]:
    return [(e.nodo, e.intento) for e in sesion.traza().eventos()]


# --- turno: relevamiento ------------------------------------------------------------------

def test_turno_pregunta_si_falta_un_dato(corpus, indice, sesion):
    g = Guion(relevamiento=[{k: v for k, v in PERFIL.items() if k != "personas"}])
    r = Flujo(cliente(g), corpus, indice).turno(sesion, "Un día en auto, el viernes")
    assert r.tipo == "pregunta"
    assert PREGUNTAS["personas"] in r.texto
    assert r.intentos == 0 and r.itinerario is None
    assert g.recibido["planificador"] == []
    assert [(m.rol, m.texto) for m in sesion.historial] == [("turista", "Un día en auto, el viernes"),
                                                            ("enot", r.texto)]
    assert sesion.perfil is None and sesion.itinerario is None


# --- turno: loop de verificación ----------------------------------------------------------

def test_flujo_reintenta_y_termina_valido(corpus, indice, sesion):
    g = Guion(relevamiento=[PERFIL], planificador=[INVALIDO, VALIDO], respuesta=[SALIDA_RESPUESTA])
    r = Flujo(cliente(g), corpus, indice).turno(sesion, "Un día el viernes en auto, somos 2")

    assert r.tipo == "itinerario"
    assert r.intentos == 2
    assert r.violaciones == []
    assert sesion.itinerario == itinerario(VALIDO) == r.itinerario
    assert r.texto.startswith("Te armé este recorrido.")
    assert "[SINTÉTICA] Château Pommard Test" in r.texto

    perfil = PerfilViaje(**PERFIL)
    esperadas = verificar_completo(itinerario(INVALIDO), perfil, corpus).violaciones
    assert {v.tipo for v in esperadas} == {"cerrada", "jornada_excedida"}
    primero, segundo = g.recibido["planificador"]
    assert "## Itinerario anterior" not in primero and "Problemas que encontró el verificador" not in primero
    assert "## Itinerario anterior" in segundo
    assert itinerario(INVALIDO).model_dump_json(indent=2) in segundo
    assert all(f"- {v.mensaje}" in segundo for v in esperadas)
    assert nodos_llamados(sesion) == [("relevamiento", 1), ("planificador", 1), ("planificador", 2),
                                      ("respuesta", 1)]
    assert sesion.historial[-1].rol == "enot" and sesion.historial[-1].texto == r.texto


def test_flujo_corta_en_max_intentos_y_explica(corpus, indice, sesion):
    g = Guion(relevamiento=[PERFIL], planificador=[INVALIDO], respuesta=[SALIDA_RESPUESTA])
    r = Flujo(cliente(g), corpus, indice).turno(sesion, "Un día el viernes en auto, somos 2")

    assert MAX_INTENTOS == 3
    assert r.tipo == "infactible"
    assert r.intentos == 3
    assert len(g.recibido["planificador"]) == 3
    assert g.recibido["respuesta"] == []
    assert sesion.itinerario is None
    assert r.itinerario == itinerario(INVALIDO)
    assert {v.tipo for v in r.violaciones} == {"cerrada", "jornada_excedida"}
    assert r.texto == explicar_infactible(r.violaciones, 3, hay_vigente=False)
    assert DESCRIPCION_VIOLACION["cerrada"] in r.texto
    assert r.violaciones[0].mensaje in r.texto
    assert [n for n, _ in nodos_llamados(sesion)] == ["relevamiento"] + ["planificador"] * 3


def test_max_intentos_1_es_la_ablacion_b2(corpus, indice, sesion):
    g = Guion(relevamiento=[PERFIL], planificador=[INVALIDO, VALIDO], respuesta=[SALIDA_RESPUESTA])
    r = Flujo(cliente(g), corpus, indice, max_intentos=1).turno(sesion, "Un día el viernes en auto, somos 2")
    assert len(g.recibido["planificador"]) == 1
    assert r.tipo == "infactible" and r.intentos == 1
    assert r.itinerario == itinerario(INVALIDO)
    assert r.violaciones and all(isinstance(v, Violacion) for v in r.violaciones)
    assert sesion.itinerario is None


@pytest.mark.parametrize("kwargs", [{"max_intentos": 0}, {"tope_tokens": 0}])
def test_max_intentos_y_tope_invalidos(corpus, indice, kwargs):
    with pytest.raises(ValueError):
        Flujo(ClienteFalso([{}]), corpus, indice, **kwargs)
    minimo = Flujo(ClienteFalso([{}]), corpus, indice, max_intentos=1, tope_tokens=1)  # el borde vale
    assert (minimo.max_intentos, minimo.tope_tokens) == (1, 1)


# --- turno: ajuste conversacional ---------------------------------------------------------

def test_ajuste_edita_el_itinerario_vigente(corpus, indice, sesion):
    g = Guion(relevamiento=[PERFIL], planificador=[VALIDO, UNA_PARADA], respuesta=[SALIDA_RESPUESTA])
    flujo = Flujo(cliente(g), corpus, indice)
    assert flujo.turno(sesion, "Un día el viernes en auto, somos 2").tipo == "itinerario"
    vigente = sesion.itinerario
    assert len(vigente.dias[0].paradas) == 2

    r = flujo.turno(sesion, "sacá la segunda bodega")
    assert r.tipo == "itinerario" and r.intentos == 1
    contexto = g.recibido["planificador"][1]
    assert "## Itinerario anterior" in contexto
    assert vigente.model_dump_json(indent=2) in contexto
    assert "<pedido>sacá la segunda bodega</pedido>" in contexto
    assert "<pedido>" not in g.recibido["planificador"][0]
    assert sesion.itinerario == itinerario(UNA_PARADA)
    # el relevamiento del ajuste vio toda la conversación, incluida la respuesta anterior
    assert "sacá la segunda bodega" in g.recibido["relevamiento"][1]
    assert "<enot>" in g.recibido["relevamiento"][1]


def _candidatas_del_contexto(contexto: str) -> list[str]:
    bloque = contexto[contexto.index("<candidatas>"):contexto.index("</candidatas>")].splitlines()[1:]
    return [json.loads(linea)["id"] for linea in bloque]


def test_ajuste_suma_las_bodegas_vigentes_a_las_candidatas(corpus, indice, sesion):
    evitar = {**PERFIL, "bodegas_evitar": ["sint-pommard"]}
    g = Guion(relevamiento=[PERFIL, PERFIL, evitar], planificador=[UNA_PARADA], respuesta=[SALIDA_RESPUESTA])
    flujo = Flujo(cliente(g), corpus, indice, k=1)
    assert flujo.turno(sesion, "Un día el viernes en auto, somos 2").tipo == "itinerario"
    assert _candidatas_del_contexto(g.recibido["planificador"][0]) == ["sint-beaune"]  # k = 1, sin vigente

    sesion.itinerario = itinerario(VALIDO)  # vigente de 2 paradas (beaune + pommard)
    flujo.turno(sesion, "cambiá el horario de la primera")
    assert _candidatas_del_contexto(g.recibido["planificador"][1]) == ["sint-beaune", "sint-pommard"]

    sesion.itinerario = itinerario(VALIDO)
    flujo.turno(sesion, "mejor evitá Pommard")  # ya no pasa los filtros duros del perfil
    assert _candidatas_del_contexto(g.recibido["planificador"][2]) == ["sint-beaune"]


AJUSTE = "## Pedido de ajuste del turista (editá el itinerario anterior: cambiá solo lo que pide)"
YA_APLICADO = ("## Pedido de ajuste del turista (ya aplicado en el itinerario anterior: no lo apliques de nuevo; "
               "corregí los problemas sin deshacerlo)")
REFERENCIA = "## Itinerario vigente antes del ajuste (referencia: es lo que el turista tenía)"


def test_ajuste_reintento_no_reaplica_el_pedido(corpus, indice, sesion):
    g = Guion(relevamiento=[PERFIL], planificador=[VALIDO, INVALIDO, UNA_PARADA], respuesta=[SALIDA_RESPUESTA])
    flujo = Flujo(cliente(g), corpus, indice)
    flujo.turno(sesion, "Un día el viernes en auto, somos 2")
    vigente = sesion.itinerario

    r = flujo.turno(sesion, "sacá la segunda bodega")
    assert r.tipo == "itinerario" and r.intentos == 2
    primero, segundo = g.recibido["planificador"][1:]
    assert AJUSTE in primero and YA_APLICADO not in primero and REFERENCIA not in primero
    assert AJUSTE not in segundo
    assert f"{YA_APLICADO}\n<pedido>sacá la segunda bodega</pedido>" in segundo
    # la propuesta fallida es el "itinerario anterior"; el vigente va aparte, como referencia
    anterior = segundo[segundo.index("## Itinerario anterior"):segundo.index("## Problemas")]
    assert itinerario(INVALIDO).model_dump_json(indent=2) in anterior
    assert f"{REFERENCIA}\n{vigente.model_dump_json(indent=2)}" in segundo
    assert sesion.itinerario == itinerario(UNA_PARADA)


def test_ajuste_infactible_conserva_el_vigente(corpus, indice, sesion):
    g = Guion(relevamiento=[PERFIL], planificador=[VALIDO, INVALIDO], respuesta=[SALIDA_RESPUESTA])
    flujo = Flujo(cliente(g), corpus, indice)
    flujo.turno(sesion, "Un día el viernes en auto, somos 2")
    advertencias = list(sesion.advertencias)

    r = flujo.turno(sesion, "empezá a las 8")
    assert r.tipo == "infactible" and r.intentos == 3
    assert sesion.itinerario == itinerario(VALIDO)
    assert sesion.advertencias == advertencias
    assert r.texto == explicar_infactible(r.violaciones, 3, hay_vigente=True)
    assert "sigue vigente" in r.texto


# --- turno: casos sin planificación -------------------------------------------------------

def test_zona_desconocida_avisa_sin_buscar(corpus, indice, sesion, tmp_path):
    g = Guion(relevamiento=[{**PERFIL, "zonas_preferidas": ["Alsacia"]}], planificador=[VALIDO],
              respuesta=[SALIDA_RESPUESTA])
    r = Flujo(cliente(g), corpus, indice).turno(sesion, "Quiero ir a Alsacia")
    assert r.tipo == "zona_desconocida"
    assert "No reconozco la zona Alsacia" in r.texto
    assert "Côte de Beaune" in r.texto  # le dice cuáles conoce
    assert g.recibido["planificador"] == []
    assert sesion.perfil is not None and sesion.perfil.zonas_preferidas == ["Alsacia"]

    otra = Sesion.nueva(tmp_path / "otras")
    g2 = Guion(relevamiento=[{**PERFIL, "zonas_preferidas": ["Chablis"]}],
               planificador=[{"dias": [{"paradas": [{"bodega_id": "sint-chablis", "hora_inicio": "10:00",
                                                     "duracion_min": 60, "experiencia": "Visite USD"}]}]}],
               respuesta=[SALIDA_RESPUESTA])
    r2 = Flujo(cliente(g2), corpus, indice).turno(otra, "Quiero ir a Chablis")
    assert r2.tipo == "itinerario"
    assert _candidatas_del_contexto(g2.recibido["planificador"][0]) == ["sint-chablis"]


def test_sin_candidatas_explica_por_que(corpus, indice, sesion):
    pedido = {**PERFIL, "dia_inicio": "lun", "zonas_preferidas": ["Côte Chalonnaise"]}
    g = Guion(relevamiento=[pedido], planificador=[VALIDO], respuesta=[SALIDA_RESPUESTA])
    r = Flujo(cliente(g), corpus, indice).turno(sesion, "El lunes en la Côte Chalonnaise")
    assert r.tipo == "sin_candidatas"
    assert "no abre ninguno de los días del viaje (lun)" in r.texto
    assert "fuera de las pedidas" not in r.texto  # que las otras zonas queden afuera es lo que pidió
    assert g.recibido["planificador"] == []
    assert sesion.historial[-1].texto == r.texto


# --- circuit breaker de tokens ------------------------------------------------------------

def test_tope_de_tokens_corta_el_loop(corpus, indice, sesion):
    g = Guion(relevamiento=[PERFIL], planificador=[INVALIDO, VALIDO], respuesta=[SALIDA_RESPUESTA])
    cli = cliente(g)
    flujo = Flujo(cli, corpus, indice, tope_tokens=2 * TOKENS_POR_LLAMADA)
    r = flujo.turno(sesion, "Un día el viernes en auto, somos 2")
    assert r.tipo == "tope_tokens"
    assert r.intentos == 1
    assert len(g.recibido["planificador"]) == 1
    assert sesion.itinerario is None
    assert str(2 * TOKENS_POR_LLAMADA) in r.texto
    assert r.itinerario == itinerario(INVALIDO)  # la propuesta que se alcanzó a verificar, con sus violaciones
    assert {v.tipo for v in r.violaciones} == {"cerrada", "jornada_excedida"}

    llamadas = len(cli.llamadas)
    r2 = flujo.turno(sesion, "¿y ahora?")
    assert r2.tipo == "tope_tokens"
    assert str(2 * TOKENS_POR_LLAMADA) in r2.texto
    assert len(cli.llamadas) == llamadas


def test_tope_alcanzado_por_el_relevamiento_no_planifica(corpus, indice, sesion):
    g = Guion(relevamiento=[PERFIL], planificador=[VALIDO], respuesta=[SALIDA_RESPUESTA])
    r = Flujo(cliente(g), corpus, indice, tope_tokens=TOKENS_POR_LLAMADA).turno(sesion, "Un día el viernes, auto, 2")
    assert r.tipo == "tope_tokens"
    assert (r.intentos, r.itinerario, r.violaciones) == (0, None, [])
    assert g.recibido["planificador"] == []


def test_tope_antes_de_responder_entrega_el_detalle_sin_llm(corpus, indice, sesion):
    g = Guion(relevamiento=[PERFIL], planificador=[VALIDO], respuesta=[SALIDA_RESPUESTA])
    r = Flujo(cliente(g), corpus, indice, tope_tokens=2 * TOKENS_POR_LLAMADA).turno(
        sesion, "Un día el viernes en auto, somos 2")
    assert r.tipo == "itinerario"
    assert g.recibido["respuesta"] == []
    assert sesion.itinerario == itinerario(VALIDO)
    assert r.texto == render_itinerario(itinerario(VALIDO), PerfilViaje(**PERFIL), corpus, advertencias=[])


# --- errores ------------------------------------------------------------------------------

def test_error_de_nodo_no_ensucia_la_sesion(corpus, indice, sesion):
    g = Guion(relevamiento=["{no es json"])
    r = Flujo(cliente(g), corpus, indice).turno(sesion, "hola")
    assert r.tipo == "error"
    assert "relevamiento" in r.texto
    assert sesion.historial == []
    assert sesion.perfil is None
    assert [e.estado for e in sesion.traza().eventos()] == ["error"]


def test_error_en_respuesta_degrada_al_detalle(corpus, indice, sesion):
    con_silla = {**PERFIL, "movilidad_reducida": True}
    g = Guion(relevamiento=[con_silla], planificador=[VALIDO], respuesta=["{no es json"])
    r = Flujo(cliente(g), corpus, indice).turno(sesion, "Un día el viernes en auto, somos 2, silla de ruedas")
    assert r.tipo == "itinerario"
    perfil = PerfilViaje(**con_silla)
    advertencias = verificar_completo(itinerario(VALIDO), perfil, corpus).advertencias
    assert advertencias  # el detalle armado por código no pierde las advertencias
    assert r.texto == render_itinerario(itinerario(VALIDO), perfil, corpus, advertencias=advertencias)
    assert "Para tener en cuenta" in r.texto
    assert sesion.itinerario == itinerario(VALIDO)
    assert sesion.historial[-1].texto == r.texto


# --- sesión y tokens ----------------------------------------------------------------------

def test_sesion_ida_y_vuelta_y_tokens_continuan(corpus, indice, sesion, tmp_path):
    g = Guion(relevamiento=[{**PERFIL, "movilidad_reducida": True}], planificador=[VALIDO],
              respuesta=[SALIDA_RESPUESTA])
    r = Flujo(cliente(g), corpus, indice).turno(sesion, "Un día el viernes en auto, somos 2, silla de ruedas")
    assert r.tipo == "itinerario"
    assert [a.tipo for a in sesion.advertencias] == ["accesibilidad_sin_confirmar"]  # Pommard no publica el dato
    assert r.advertencias == sesion.advertencias
    assert "Para tener en cuenta" in r.texto and sesion.advertencias[0].mensaje in r.texto
    assert sesion.traza().ruta.parent == tmp_path / "trazas"

    ruta = tmp_path / "carpeta" / "nueva" / "sesion.json"
    sesion.guardar(ruta)
    retomada = Sesion.cargar(ruta)
    assert retomada == sesion
    assert retomada.traza().ruta == sesion.traza().ruta
    assert tokens_usados(retomada.traza()) == 3 * TOKENS_POR_LLAMADA


def test_tokens_usados_ignora_desconocidos(tmp_path):
    traza = Traza(tmp_path / "t.jsonl")
    assert tokens_usados(traza) == 0
    comunes = dict(conversacion="t", intento=1, proveedor="p", modelo="m", inicio="2026-11-24T00:00:00+00:00",
                   latencia_s=0.1)
    traza.registrar(EventoTraza(**comunes, nodo="relevamiento", tokens_in=100, tokens_out=20, intentos_validacion=1,
                                estado="ok"))
    traza.registrar(EventoTraza(**comunes, nodo="planificador", estado="error", error="x"))
    traza.registrar(EventoTraza(**comunes, nodo="planificador", tokens_in=7, tokens_out=3, intentos_validacion=2,
                                estado="ok"))
    assert tokens_usados(traza) == 130


# --- textos fijos -------------------------------------------------------------------------

def test_descripcion_violacion_cubre_todos_los_tipos():
    assert set(DESCRIPCION_VIOLACION) == set(get_args(TipoViolacion))
    assert all(t.strip() for t in DESCRIPCION_VIOLACION.values())
    assert len(set(DESCRIPCION_VIOLACION.values())) == len(DESCRIPCION_VIOLACION)


def test_explicar_infactible_texto():
    vs = [Violacion(tipo="presupuesto_excedido", mensaje="Día 1: te pasás 10 EUR."),
          Violacion(tipo="cerrada", mensaje="Día 1: X cierra a las 17:00."),
          Violacion(tipo="presupuesto_excedido", mensaje="Día 2: te pasás 5 EUR.")]
    t = explicar_infactible(vs, 3, hay_vigente=False)
    assert "3 intentos" in t
    p, c = DESCRIPCION_VIOLACION["presupuesto_excedido"], DESCRIPCION_VIOLACION["cerrada"]
    assert t.count(p) == 1 and t.count(c) == 1 and t.index(p) < t.index(c)
    assert all(f"- {v.mensaje}" in t for v in vs)
    assert "sigue vigente" not in t
    con_vigente = explicar_infactible(vs[:2], 1, hay_vigente=True)
    assert con_vigente.splitlines() == [
        "No pude armar un itinerario que cumpla todo lo que pediste (1 intento).",
        f"Lo que no logré cumplir: {p}, {c}.",
        "Detalle del último intento:",
        "- Día 1: te pasás 10 EUR.",
        "- Día 1: X cierra a las 17:00.",
        "Si querés, cambiá alguna de esas condiciones (días, horario, presupuesto, zona) y lo intento de nuevo.",
        "Tu itinerario anterior sigue vigente.",
    ]


def test_explicar_sin_candidatas_cuenta_motivos(corpus):
    # sin zona pedida cuentan todas las bodegas: 3 cierran los lunes, 1 la pidió evitar
    perfil = PerfilViaje(**{**PERFIL, "dia_inicio": "lun", "bodegas_evitar": ["sint-gevrey"]})
    assert explicar_sin_candidatas(corpus.values(), perfil, cuantos=2).splitlines() == [
        "No encontré bodegas que cumplan a la vez todo lo que pediste.",
        "Los motivos más frecuentes:",
        "- no abre ninguno de los días del viaje (lun) (3 bodegas)",
        "- el turista pidió evitarla (1 bodega)",
        "Si cambiás alguna condición (días, zona, presupuesto, idioma), lo intento de nuevo.",
    ]
    assert explicar_sin_candidatas(corpus.values(), perfil, cuantos=1).splitlines()[2:] == [
        "- no abre ninguno de los días del viaje (lun) (3 bodegas)",
        "Si cambiás alguna condición (días, zona, presupuesto, idioma), lo intento de nuevo.",
    ]
    assert explicar_sin_candidatas([], perfil).splitlines() == [
        "No encontré bodegas que cumplan a la vez todo lo que pediste.",
        "Si cambiás alguna condición (días, zona, presupuesto, idioma), lo intento de nuevo.",
    ]


def test_avisar_zonas_desconocidas_texto():
    conocidas = ["Côte de Nuits", "Chablis y Grand Auxerrois", "Côte de Nuits", ""]
    # sin repetir, sin vacías, en orden alfabético; singular o plural según cuántas zonas no reconoce
    assert avisar_zonas_desconocidas(["Alsacia", "Loira"], conocidas) == (
        "No reconozco las zonas Alsacia, Loira. Las zonas de Borgoña que conozco son: Chablis y Grand "
        "Auxerrois, Côte de Nuits. ¿En cuál querés visitar bodegas?")
    assert avisar_zonas_desconocidas(["Alsacia"], conocidas).startswith("No reconozco la zona Alsacia. Las zonas")


def test_contexto_planificador_con_pedido_de_ajuste(corpus):
    perfil = PerfilViaje(**PERFIL)
    cands = [corpus["sint-beaune"], corpus["sint-pommard"]]
    previo = itinerario(VALIDO)
    sin = contexto_planificador(perfil, cands, [], previo)
    assert contexto_planificador(perfil, cands, [], previo, pedido_ajuste=None) == sin
    con = contexto_planificador(perfil, cands, [], previo, pedido_ajuste="sacá <la> segunda")
    assert con == sin + ("\n## Pedido de ajuste del turista (editá el itinerario anterior: cambiá solo lo que pide)"
                         "\n<pedido>sacá ‹la› segunda</pedido>")


def test_contexto_planificador_reintento_de_ajuste(corpus):
    perfil = PerfilViaje(**PERFIL)
    cands = [corpus["sint-beaune"], corpus["sint-pommard"]]
    fallida, vigente = itinerario(INVALIDO), itinerario(VALIDO)
    vs = [Violacion(tipo="cerrada", mensaje="Día 1: cerrada.")]
    base = contexto_planificador(perfil, cands, vs, fallida)
    ctx = contexto_planificador(perfil, cands, vs, fallida, pedido_ajuste="sacá >la< segunda", vigente_ajuste=vigente)
    assert ctx == base + (f"\n{REFERENCIA}\n{vigente.model_dump_json(indent=2)}"
                          f"\n{YA_APLICADO}\n<pedido>sacá ›la‹ segunda</pedido>")
    # sin pedido, el vigente de referencia no se agrega
    assert contexto_planificador(perfil, cands, vs, fallida, vigente_ajuste=vigente) == base


# --- formato real -------------------------------------------------------------------------

def test_con_la_muestra_real_de_datatourisme(entorno, tmp_path):
    """Muestra real → paso `datatourisme` → un turno completo con LLM falso. Sin copiar datos a fixtures."""
    import contextlib
    import csv
    import io

    from corpus import config, datatourisme

    muestra = FIXTURES.parent.parent / "data" / "datatourisme" / "muestra.csv"
    if not muestra.exists():
        pytest.skip("sin data/datatourisme/muestra.csv")
    with contextlib.redirect_stdout(io.StringIO()):
        datatourisme.run(str(muestra))
    bodegas = [Bodega(id=f["id"], nombre=f["nombre"], zona=f["zona"], comuna=f["comuna"],
                      lat=float(f["lat"]) if f["lat"] else None, lon=float(f["lon"]) if f["lon"] else None)
               for f in csv.DictReader(config.SEED_CSV.open(encoding="utf-8"))]
    corpus = {b.id: b for b in bodegas}
    indice = Indice(bodegas, EmbedderFalso())
    perfil = {**PERFIL, "dia_inicio": "sab", "zonas_preferidas": ["Chablis"]}

    def proponer(sistema, usuario):
        primera = _candidatas_del_contexto(usuario)[0]
        return {"dias": [{"paradas": [{"bodega_id": primera, "hora_inicio": "10:00", "duracion_min": 60}]}]}

    g = Guion(relevamiento=[perfil], planificador=[proponer], respuesta=[SALIDA_RESPUESTA])
    sesion = Sesion.nueva(tmp_path / "trazas")
    r = Flujo(cliente(g), corpus, indice).turno(sesion, "Un sábado en Chablis, en auto, somos 2")
    assert isinstance(r, Respuesta)
    assert r.tipo == "itinerario", r.texto
    ids = _candidatas_del_contexto(g.recibido["planificador"][0])
    assert len(ids) == 10 and all(i in corpus for i in ids)
    assert all("Chablis" in corpus[i].zona for i in ids)
    assert corpus[ids[0]].nombre in r.texto
