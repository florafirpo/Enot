"""Spec 008: llamadas fallidas con los tokens que se gastaron (pendientes de la revisión 004, ADR-0014, ADR-0018).

- `ClienteLLM` que agota los intentos de validación lanza `ErrorSalidaInvalida` con los tokens consumidos.
- El nodo los registra en el evento de error; un error sin tokens (proveedor caído) sigue en `None`.
- `EventoTraza` con `estado == "ok"` exige tokens.
- La salida de Enot en el benchmark trae la ruta de su traza (el reporte cuenta las fallidas desde ahí).
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from corpus.llm import ErrorSalidaInvalida
from corpus.schema import FichaBodega
from enot.corpus_local import cargar_corpus
from enot.modelos import PerfilViaje
from enot.nodos import ErrorNodo, Mensaje, relevar
from enot.retrieval import Indice
from enot.trazas import EventoTraza, Traza
from eval.baselines import crear_enot
from eval.generador import Consulta
from tests.conftest import FIXTURES
from tests.dobles import EmbedderFalso
from tests.test_extract_y_llm import _cliente_openai
from tests.test_flujo import PERFIL, SALIDA_RESPUESTA, VALIDO, Guion, cliente

HISTORIAL = [Mensaje(rol="turista", texto="Un día el viernes en auto, somos 2")]


def test_cliente_llm_error_trae_tokens_consumidos():
    # cada respuesta simulada cuesta 10 tokens de entrada y 5 de salida (respuesta_openai)
    c, pedidos = _cliente_openai(['{"nombre": 1}', "no es json"])
    with pytest.raises(ErrorSalidaInvalida) as exc:
        c.estructurado("s", "u", FichaBodega, max_intentos=2)
    e = exc.value
    assert isinstance(e, RuntimeError)                  # quien atrapaba RuntimeError sigue funcionando
    assert (e.tokens_in, e.tokens_out, e.intentos) == (20, 10, 2)
    assert len(pedidos) == 2
    assert "No se obtuvo una salida válida tras 2 intentos" in str(e)


def test_cliente_llm_error_con_un_intento():
    c, _ = _cliente_openai(["no es json"])
    with pytest.raises(ErrorSalidaInvalida) as exc:
        c.estructurado("s", "u", FichaBodega, max_intentos=1)
    assert (exc.value.tokens_in, exc.value.tokens_out, exc.value.intentos) == (10, 5, 1)


class _ClienteQueLanza:
    provider = "falso"
    model = "modelo-falso"

    def __init__(self, error: Exception):
        self.error = error

    def estructurado(self, sistema, usuario, modelo, max_intentos=2):
        raise self.error


def test_nodo_registra_tokens_del_error(tmp_path):
    traza = Traza(tmp_path / "t.jsonl", conversacion="c")
    with pytest.raises(ErrorNodo):
        relevar(HISTORIAL, _ClienteQueLanza(ErrorSalidaInvalida("no valida", 30, 7, 2)), traza)
    (ev,) = traza.eventos()
    assert ev.estado == "error"
    assert (ev.tokens_in, ev.tokens_out, ev.intentos_validacion) == (30, 7, 2)

    otra = Traza(tmp_path / "u.jsonl", conversacion="c")
    with pytest.raises(ErrorNodo):
        relevar(HISTORIAL, _ClienteQueLanza(ConnectionError("sin red")), otra)
    (ev,) = otra.eventos()
    assert (ev.tokens_in, ev.tokens_out, ev.intentos_validacion) == (None, None, None)


def _evento(**cambios) -> EventoTraza:
    base = dict(conversacion="c", nodo="planificador", intento=1, proveedor="p", modelo="m",
                inicio="2026-11-25T20:00:00+00:00", latencia_s=1.0, tokens_in=10, tokens_out=5,
                intentos_validacion=1, estado="ok")
    base.update(cambios)
    return EventoTraza(**base)


def test_evento_ok_exige_tokens():
    assert _evento().tokens_in == 10
    with pytest.raises(ValidationError):
        _evento(tokens_in=None)
    with pytest.raises(ValidationError):
        _evento(tokens_out=None)
    e = _evento(estado="error", error="x", tokens_in=None, tokens_out=None, intentos_validacion=None)
    assert e.tokens_in is None
    assert _evento(estado="ok", tokens_in=0, tokens_out=0).tokens_out == 0   # 0 informado es un dato válido


def test_sistema_enot_guarda_la_ruta_de_la_traza(tmp_path):
    corpus = cargar_corpus(FIXTURES / "fichas_sinteticas.jsonl")
    indice = Indice(list(corpus.values()), EmbedderFalso())
    g = Guion(relevamiento=[PERFIL], planificador=[VALIDO], respuesta=[SALIDA_RESPUESTA])
    consulta = Consulta(id="q1", escenario="dias", plantilla="t", texto="Un día el viernes en auto, somos 2",
                        restricciones=PerfilViaje(**PERFIL))
    s = crear_enot(cliente(g), corpus, indice, tmp_path / "trazas").correr(consulta)
    assert s.traza is not None
    eventos = Traza(s.traza).eventos()
    assert [e.nodo for e in eventos] == ["relevamiento", "planificador", "respuesta"]
    assert sum(e.tokens_in for e in eventos) == s.tokens_in
