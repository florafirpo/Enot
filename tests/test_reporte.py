"""Spec 008: reporte final con métricas, preference score, costo y latencia desde las trazas (PRD 9, ADR-0018).

Los precios de estos tests son SINTÉTICOS (números redondos para calcular a mano): el repo no trae precios de modelos.
"""
from __future__ import annotations

import json

import pytest

from corpus import config
from enot.trazas import EventoTraza, Traza
from eval import reporte as rep
from eval.correr import Reporte
from eval.juez import Juicio, Juicios
from eval.metricas import EvaluacionConsulta, Metricas, SalidaSistema
from eval.reporte import (
    CostoConsulta,
    Precio,
    cargar_precios,
    costo_consulta,
    filas_sistemas,
    media,
    percentil_95,
    render_markdown,
)

# [SINTÉTICO] 1 USD por millón de tokens de entrada y 4 por millón de salida
PRECIOS = {"modelo-a": Precio(entrada_usd_por_millon=1.0, salida_usd_por_millon=4.0),
           "modelo-b": Precio(entrada_usd_por_millon=10.0, salida_usd_por_millon=20.0)}


def evento(modelo="modelo-a", estado="ok", tin=1000, tout=500, nodo="planificador") -> EventoTraza:
    return EventoTraza(conversacion="c", nodo=nodo, intento=1, proveedor="p", modelo=modelo,
                       inicio="2026-11-29T10:00:00+00:00", latencia_s=1.0, tokens_in=tin, tokens_out=tout,
                       intentos_validacion=1 if estado == "ok" else None, estado=estado,
                       error=None if estado == "ok" else "falló")


def sal(sistema="enot", id="q1", tipo="itinerario", tin=None, tout=None, lat=1.0, intentos=1, traza=None):
    return SalidaSistema(consulta_id=id, sistema=sistema, tipo=tipo, tokens_in=tin, tokens_out=tout, latencia_s=lat,
                         intentos=intentos, traza=traza)


def test_percentil_95_y_media():
    assert percentil_95(list(range(1, 21))) == 19          # ceil(0.95·20) = 19.º valor
    assert percentil_95(list(range(40, 0, -1))) == 38      # ordena antes: ceil(0.95·40) = 38.º
    assert percentil_95([7.5]) == 7.5
    assert percentil_95([3, 1, 2]) == 3                    # ceil(2.85) = 3.º
    assert percentil_95([]) is None
    assert media([1, 2, 3, 6]) == 3
    assert media([]) is None


def test_costo_sin_llm_es_cero():
    c = costo_consulta(sal("B1"), None, con_llm=False, modelo=None, precios={})
    assert c == CostoConsulta(consulta_id="q1", llamadas=0, fallidas=0, sin_tokens=0, tokens_in=0, tokens_out=0,
                              usd=0.0)


def test_costo_desde_la_traza():
    eventos = [evento("modelo-a", tin=1000, tout=500), evento("modelo-b", tin=2000, tout=100, nodo="respuesta")]
    c = costo_consulta(sal(), eventos, con_llm=True, modelo="modelo-a", precios=PRECIOS)
    assert (c.llamadas, c.fallidas, c.sin_tokens, c.tokens_in, c.tokens_out) == (2, 0, 0, 3000, 600)
    # Σ t_in·p_in + t_out·p_out (PRD 9), con el precio del modelo de CADA llamada:
    # (1000·1 + 500·4)/1e6 + (2000·10 + 100·20)/1e6 = 0.003 + 0.022
    assert c.usd == pytest.approx(0.025)


def test_costo_con_llamada_fallida_sin_tokens():
    eventos = [evento(tin=1000, tout=500), evento(estado="error", tin=None, tout=None)]
    c = costo_consulta(sal(), eventos, con_llm=True, modelo="modelo-a", precios=PRECIOS)
    assert (c.llamadas, c.fallidas, c.sin_tokens) == (2, 1, 1)
    assert (c.tokens_in, c.tokens_out) == (1000, 500)      # los conocidos, sin inventar 0 para la fallida
    assert c.usd is None                                   # costo incompleto: no se reporta un número falso

    con_tokens = [evento(tin=1000, tout=500), evento(estado="error", tin=300, tout=100)]
    c2 = costo_consulta(sal(), con_tokens, con_llm=True, modelo="modelo-a", precios=PRECIOS)
    assert (c2.fallidas, c2.sin_tokens, c2.tokens_in, c2.tokens_out) == (1, 0, 1300, 600)
    assert c2.usd == pytest.approx((1300 * 1 + 600 * 4) / 1e6)


def test_costo_sin_precio_del_modelo():
    c = costo_consulta(sal(), [evento("modelo-desconocido")], con_llm=True, modelo="modelo-a", precios=PRECIOS)
    assert (c.tokens_in, c.tokens_out) == (1000, 500) and c.usd is None
    assert costo_consulta(sal(), [evento()], con_llm=True, modelo=None, precios={}).usd is None


def test_costo_traza_vacia():
    c = costo_consulta(sal(), [], con_llm=True, modelo="modelo-a", precios=PRECIOS)
    assert (c.llamadas, c.tokens_in, c.usd) == (0, 0, 0.0)


def test_costo_b0_desde_la_salida():
    c = costo_consulta(sal("B0", tin=2000, tout=1000), None, con_llm=True, modelo="modelo-a", precios=PRECIOS)
    assert (c.llamadas, c.fallidas, c.sin_tokens) == (None, None, 0)
    assert (c.tokens_in, c.tokens_out) == (2000, 1000)
    assert c.usd == pytest.approx((2000 + 4000) / 1e6)
    assert costo_consulta(sal("B0", tin=2000, tout=1000), None, con_llm=True, modelo="otro", precios=PRECIOS).usd is None
    err = costo_consulta(sal("B0", tipo="error"), None, con_llm=True, modelo="modelo-a", precios=PRECIOS)
    assert (err.tokens_in, err.tokens_out, err.usd, err.sin_tokens) == (None, None, None, 1)


def _metricas(hp: float, **kw) -> Metricas:
    base = dict(consultas=3, factibles=3, infactibles=0, hard_pass_rate=hp, hard_pass_por_escenario={},
                tasa_alucinacion=0.0, afirmaciones=3, inventadas=0, cobertura_corpus=0.5, gini=0.2,
                infactibles_detectados=None, infactibles_detectados_por_motivo={},
                infactibles_detectados_representables=None, tipos={})
    base.update(kw)
    return Metricas(**base)


def _eval(id: str, hard_pass: bool) -> EvaluacionConsulta:
    return EvaluacionConsulta(consulta_id=id, escenario="dias", infactible=False, tipo="itinerario",
                              hard_pass=hard_pass)


@pytest.fixture
def escenario(tmp_path):
    """Reporte armado a mano: enot con trazas (una llamada fallida en q3), B1 sin LLM y B0 con un error."""
    trazas = {}
    for id, eventos in {"q1": [evento(tin=1000, tout=500)],
                        "q2": [evento(tin=3000, tout=500), evento(tin=1000, tout=500)],
                        "q3": [evento(tin=1000, tout=500), evento(estado="error", tin=None, tout=None)]}.items():
        t = Traza(tmp_path / f"{id}.jsonl")
        for e in eventos:
            t.registrar(e)
        trazas[id] = str(t.ruta)
    salidas = {
        "enot": [sal("enot", "q1", lat=10, intentos=1, traza=trazas["q1"]),
                 sal("enot", "q2", lat=20, intentos=2, traza=trazas["q2"]),
                 sal("enot", "q3", tipo="infactible", lat=30, intentos=3, traza=trazas["q3"])],
        "B1": [sal("B1", "q1", lat=0.5, intentos=0), sal("B1", "q2", lat=0.25, intentos=0),
               sal("B1", "q3", lat=0.75, intentos=0)],
        "B0": [sal("B0", "q1", tin=500, tout=250, lat=4), sal("B0", "q2", tipo="error", lat=0.0),
               sal("B0", "q3", tin=1500, tout=250, lat=6)],
    }
    reporte = Reporte(
        split="dev", fecha="2026-11-29-120000", configuracion={"modelo": "modelo-a", "commit": "abc1234"},
        metricas={"enot": _metricas(2 / 3), "B1": _metricas(1.0, tasa_alucinacion=None), "B0": _metricas(0.0)},
        evaluaciones={"enot": [_eval("q1", True), _eval("q2", True), _eval("q3", False)],
                      "B1": [_eval("q1", True), _eval("q2", True), _eval("q3", True)],
                      "B0": [_eval("q1", False), _eval("q2", False), _eval("q3", False)]},
        salidas=salidas)
    juicios = Juicios(reporte="r", split="dev", fecha="f", proveedor="p", modelo="modelo-a", juicios=[
        Juicio(consulta_id="q1", sistema="enot", estado="ok", puntaje=5, tokens_in=1, tokens_out=1, latencia_s=0),
        Juicio(consulta_id="q2", sistema="enot", estado="ok", puntaje=3, tokens_in=1, tokens_out=1, latencia_s=0),
        Juicio(consulta_id="q1", sistema="B1", estado="ok", puntaje=2, tokens_in=1, tokens_out=1, latencia_s=0),
        Juicio(consulta_id="q2", sistema="B1", estado="error", puntaje=None, error="x", tokens_in=None,
               tokens_out=None, latencia_s=0),
        Juicio(consulta_id="q1", sistema="B0", estado="ok", puntaje=4, tokens_in=1, tokens_out=1, latencia_s=0),
    ])
    return reporte, juicios


def test_filas_sistemas(escenario):
    reporte, juicios = escenario
    filas = {f.sistema: f for f in filas_sistemas(reporte, juicios, PRECIOS)}
    assert list(filas) == ["enot", "B1", "B0"]

    e = filas["enot"]
    assert e.hard_pass_rate == pytest.approx(2 / 3) and e.cobertura_corpus == 0.5 and e.gini == 0.2
    assert e.preferencia_media == pytest.approx(4) and e.juicios == 2 and e.juicios_error == 0
    assert e.preferencia_media_hard_pass == pytest.approx(4)
    # costo: q1 = 0.003; q2 = (4000·1 + 1000·4)/1e6 = 0.008; q3 incompleto (llamada sin tokens) → fuera
    assert e.consultas == 3 and e.consultas_con_costo == 2
    assert e.usd_medio == pytest.approx(0.0055) and e.usd_p95 == pytest.approx(0.008)
    assert e.tokens_medios == pytest.approx((1500 + 5000) / 2)
    assert e.latencia_media == pytest.approx(20) and e.latencia_p95 == 30
    assert e.intentos_medios == pytest.approx(2)
    assert (e.llamadas, e.llamadas_fallidas, e.llamadas_sin_tokens, e.salidas_error) == (5, 1, 1, 0)

    b1 = filas["B1"]
    assert b1.usd_medio == 0 and b1.tokens_medios == 0 and b1.consultas_con_costo == 3
    assert b1.preferencia_media == 2 and b1.juicios == 1 and b1.juicios_error == 1
    assert b1.latencia_media == pytest.approx(0.5) and b1.latencia_p95 == 0.75
    assert b1.intentos_medios is None                      # sin loop: no hay reintentos que contar
    assert b1.tasa_alucinacion is None and b1.llamadas == 0

    b0 = filas["B0"]
    assert b0.salidas_error == 1 and b0.consultas_con_costo == 2
    assert b0.usd_medio == pytest.approx(((500 + 1000) + (1500 + 1000)) / 1e6 / 2)
    assert b0.latencia_media == pytest.approx(5)            # la salida error (latencia sin medir) no cuenta
    assert b0.preferencia_media == 4 and b0.preferencia_media_hard_pass is None
    assert b0.llamadas is None                              # B0 no tiene traza


def test_filas_sin_juicios_ni_precios(escenario):
    reporte, _ = escenario
    filas = {f.sistema: f for f in filas_sistemas(reporte)}
    assert filas["enot"].preferencia_media is None and filas["enot"].juicios == 0
    assert filas["enot"].usd_medio is None and filas["enot"].consultas_con_costo == 0
    assert filas["enot"].tokens_medios == pytest.approx(3250)   # los tokens no dependen de los precios
    assert filas["B1"].usd_medio == 0


def test_render_markdown(escenario):
    reporte, juicios = escenario
    filas = filas_sistemas(reporte, juicios, PRECIOS)
    md = render_markdown(reporte, filas, origen="reports/eval_dev_x.json", calibracion=None, precios_cargados=True)
    assert "reports/eval_dev_x.json" in md and "abc1234" in md and "modelo-a" in md
    lineas_tabla = [ln for ln in md.splitlines() if ln.startswith("| ")]
    for s in ("enot", "B1", "B0"):
        assert sum(ln.startswith(f"| {s} |") for ln in lineas_tabla) >= 2   # métricas y economía
    assert "66.7%" in md and "0.0055" in md
    assert "s/d" in md                                    # B1 sin alucinación medible, B0 sin hard pass en juicios
    assert "sin calibrar" in md.lower()
    assert "1000" in md                                   # proyección a 1.000 consultas por mes

    from eval.calibrar import Calibracion
    mala = Calibracion(pares=30, sin_anotar=0, sin_juicio=0, spearman=0.3, kappa=0.1, kappa_cuadratico=0.2,
                       apto=False, motivo="Spearman 0.30 < 0.6")
    md2 = render_markdown(reporte, filas, origen="r", calibracion=mala, precios_cargados=True)
    assert "no es apto" in md2.lower() and "Spearman 0.30 < 0.6" in md2
    buena = mala.model_copy(update={"spearman": 0.8, "kappa_cuadratico": 0.75, "apto": True, "motivo": "ok"})
    md3 = render_markdown(reporte, filas, origen="r", calibracion=buena, precios_cargados=True)
    assert "no es apto" not in md3.lower() and "sin calibrar" not in md3.lower() and "0.80" in md3

    sin_precios = render_markdown(reporte, filas_sistemas(reporte, juicios), origen="r", precios_cargados=False)
    assert "--precios" in sin_precios


def test_cargar_precios(tmp_path):
    ruta = tmp_path / "p.json"
    ruta.write_text(json.dumps({"m": {"entrada_usd_por_millon": 0.5, "salida_usd_por_millon": 2}}), encoding="utf-8")
    assert cargar_precios(ruta) == {"m": Precio(entrada_usd_por_millon=0.5, salida_usd_por_millon=2)}
    ruta.write_text(json.dumps({"m": {"entrada_usd_por_millon": -1, "salida_usd_por_millon": 2}}), encoding="utf-8")
    with pytest.raises(ValueError):
        cargar_precios(ruta)


def test_cli_reporte_escribe_resultados(entorno, escenario):
    reporte, juicios = escenario
    r = config.REPORTS_DIR / "eval_dev_x.json"
    r.write_text(reporte.model_dump_json(), encoding="utf-8")
    j = config.REPORTS_DIR / "juez_dev_x.json"
    j.write_text(juicios.model_dump_json(), encoding="utf-8")
    p = entorno / "precios.json"
    p.write_text(json.dumps({k: v.model_dump() for k, v in PRECIOS.items()}), encoding="utf-8")
    assert rep.main([str(r), "--juicios", str(j), "--precios", str(p)]) == 0
    md = (config.REPORTS_DIR / "resultados.md").read_text(encoding="utf-8")
    assert "| enot |" in md and "0.0055" in md
    destino = entorno / "otro.md"
    assert rep.main([str(r), "--salida", str(destino)]) == 0
    assert destino.exists()
    assert rep.main([str(entorno / "no-existe.json")]) == 1
