"""Spec 004: traza JSONL de las llamadas al LLM (ADR-0006, lineamientos D2)."""
from __future__ import annotations

import json
import re

import pytest
from pydantic import ValidationError

from enot.trazas import EventoTraza, Traza


def evento(**cambios) -> EventoTraza:
    base = dict(conversacion="c1", nodo="planificador", intento=2, proveedor="openai", modelo="m",
                inicio="2026-11-24T20:00:00+00:00", latencia_s=1.5, tokens_in=1200, tokens_out=300,
                intentos_validacion=1, estado="ok", error=None)
    base.update(cambios)
    return EventoTraza(**base)


def test_traza_nueva_crea_archivo_en_carpeta(tmp_path):
    t = Traza.nueva(tmp_path / "trazas")
    assert t.ruta.parent == tmp_path / "trazas"
    assert re.fullmatch(r"\d{8}-\d{6}-[0-9a-f]{8}\.jsonl", t.ruta.name)
    assert t.conversacion == t.ruta.stem
    otra = Traza.nueva(tmp_path / "trazas")
    assert otra.ruta != t.ruta


def test_traza_nueva_por_defecto_en_data_trazas(monkeypatch, tmp_path):
    from corpus import config
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    t = Traza.nueva()
    assert t.ruta.parent == tmp_path / "data" / "trazas"


def test_traza_registrar_y_leer(tmp_path):
    t = Traza(tmp_path / "sub" / "x.jsonl", conversacion="conv-1")
    e1, e2 = evento(), evento(nodo="respuesta", estado="error", error="timeout", tokens_in=0, tokens_out=0)
    t.registrar(e1)
    t.registrar(e2)
    lineas = t.ruta.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 2
    assert json.loads(lineas[1])["error"] == "timeout"
    assert t.eventos() == [e1, e2]


def test_traza_vacia_sin_archivo(tmp_path):
    t = Traza(tmp_path / "no-existe.jsonl")
    assert t.eventos() == []
    assert not t.ruta.exists()
    assert t.conversacion == "no-existe"


def test_evento_traza_valida_campos():
    with pytest.raises(ValidationError):
        evento(estado="quizas")
    with pytest.raises(ValidationError):
        evento(nodo="retrieval")
    with pytest.raises(ValidationError):
        evento(tokens_in=-1)
    with pytest.raises(ValidationError):
        evento(intento=0)


def test_traza_crea_carpetas_anidadas(tmp_path):
    t = Traza(tmp_path / "a" / "b" / "c" / "x.jsonl")
    t.registrar(evento(error="Côte de Nuits — ñ"))
    assert t.eventos()[0].error == "Côte de Nuits — ñ"
