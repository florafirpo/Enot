"""Spec 008: juez LLM con rúbrica 1–5 de ajuste a preferencias (H2, ADR-0007, ADR-0018).

Todo offline: `ClienteFalso` y la fixture SINTÉTICA de bodegas. El juez ve lo mismo para cada sistema (datos del
corpus) y no sabe qué sistema produjo el itinerario.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from corpus import config
from enot.corpus_local import cargar_corpus
from enot.modelos import DiaItinerario, Itinerario, Parada, PerfilViaje
from eval import juez
from eval.correr import Reporte
from eval.generador import Consulta
from eval.juez import Juicio, SalidaJuez, contexto_juez, juzgable, juzgar, juzgar_reporte
from eval.metricas import SalidaSistema
from tests.conftest import FIXTURES, ClienteFalso

PERFIL = {"cantidad_dias": 1, "dia_inicio": "vie", "transporte": "auto", "personas": 2}
TEXTO_PEDIDO = "Un día el viernes en auto, somos 2. Nos encanta el pinot noir."


@pytest.fixture
def corpus():
    c = cargar_corpus(FIXTURES / "fichas_sinteticas.jsonl")
    # [SINTÉTICA] vinos y descripción agregados para ver que el juez los recibe del corpus
    c["sint-gevrey"] = c["sint-gevrey"].model_copy(update={
        "vinos_o_varietales_destacados": ["[SINTÉTICO] pinot noir de prueba"],
        "descripcion_breve": "[SINTÉTICA] descripción de prueba del domaine."})
    return c


def consulta(id="q1", preferencias="tintos de pinot noir", infactible=False, **kw) -> Consulta:
    perfil = PerfilViaje(**{**PERFIL, "preferencias": preferencias, **kw})
    return Consulta(id=id, escenario="dias", plantilla="t", texto=TEXTO_PEDIDO, restricciones=perfil,
                    infactible=infactible, motivo_infactible="zona_fuera_de_borgona" if infactible else None)


def itinerario(*ids: str) -> Itinerario:
    paradas = [Parada(bodega_id=b, hora_inicio=f"{10 + 2 * i:02d}:00", duracion_min=60,
                      experiencia="Dégustation 6 vins" if b == "sint-gevrey" else None) for i, b in enumerate(ids)]
    return Itinerario(dias=[DiaItinerario(numero=1, dia_semana="vie", paradas=paradas)])


def salida(sistema="enot", id="q1", tipo="itinerario", it=None, texto="TEXTO-DEL-SISTEMA-XYZ") -> SalidaSistema:
    if tipo == "itinerario" and it is None:
        it = itinerario("sint-gevrey", "sint-beaune")
    return SalidaSistema(consulta_id=id, sistema=sistema, tipo=tipo, itinerario=it, texto=texto)


def test_juzgable():
    assert juzgable(consulta(), salida()) is True
    assert juzgable(consulta(infactible=True), salida()) is False
    assert juzgable(consulta(preferencias=None), salida()) is False
    assert juzgable(consulta(preferencias="  "), salida()) is False
    assert juzgable(consulta(), salida(tipo="infactible")) is False
    vacio = Itinerario(dias=[DiaItinerario(numero=1, dia_semana="vie", paradas=[])])
    assert juzgable(consulta(), salida(it=vacio)) is False


def test_contexto_juez_usa_datos_del_corpus_y_es_ciego(corpus):
    it = itinerario("sint-gevrey", "b0:Domaine Que No Existe")
    ctx = contexto_juez(consulta(), it, corpus)
    assert TEXTO_PEDIDO in ctx
    assert "tintos de pinot noir" in ctx
    assert "[SINTÉTICA] Domaine Gevrey Prueba" in ctx
    assert "Côte de Nuits" in ctx and "Gevrey-Chambertin" in ctx
    assert "[SINTÉTICO] pinot noir de prueba" in ctx
    assert "[SINTÉTICA] descripción de prueba" in ctx
    assert "Dégustation 6 vins" in ctx
    assert "Domaine Que No Existe" in ctx and "fuera del corpus" in ctx
    # ciego y sin datos duros: ni precios, ni horarios, ni el sistema, ni la prosa del sistema
    assert "25" not in ctx and "EUR" not in ctx and "€" not in ctx
    assert "10:00" not in ctx and "12:00" not in ctx
    assert "enot" not in ctx.lower() and "TEXTO-DEL-SISTEMA" not in ctx
    assert "Día 1" in ctx


def test_juzgar_devuelve_puntaje_y_tokens(corpus):
    cli = ClienteFalso([{"justificacion": "Las dos bodegas son de pinot noir.", "puntaje": 4}])
    j = juzgar(cli, consulta(), salida(sistema="B1"), corpus)
    assert isinstance(j, Juicio)
    assert (j.consulta_id, j.sistema, j.estado, j.puntaje) == ("q1", "B1", "ok", 4)
    assert j.justificacion.startswith("Las dos bodegas")
    assert (j.tokens_in, j.tokens_out) == (100, 50) and j.latencia_s >= 0
    (llamada,) = cli.llamadas
    assert llamada["sistema"] == juez.cargar_rubrica()
    assert "1" in llamada["sistema"] and "5" in llamada["sistema"]
    assert "Domaine Gevrey Prueba" in llamada["usuario"]


def test_juzgar_error_del_cliente(corpus):
    j = juzgar(ClienteFalso(["no es json"]), consulta(), salida(), corpus)
    assert j.estado == "error" and j.puntaje is None
    assert "salida inválida" in j.error
    assert j.tokens_in is None and j.tokens_out is None


def test_juzgar_error_trae_tokens_si_el_cliente_los_informa(corpus):
    from corpus.llm import ErrorSalidaInvalida

    class Lanza:
        provider, model = "falso", "m"

        def estructurado(self, *a, **k):
            raise ErrorSalidaInvalida("no valida", 40, 9, 2)

    j = juzgar(Lanza(), consulta(), salida(), corpus)
    assert j.estado == "error" and (j.tokens_in, j.tokens_out) == (40, 9)


def test_salida_juez_rechaza_fuera_de_rango():
    assert SalidaJuez(justificacion="ok", puntaje=1).puntaje == 1
    assert SalidaJuez(justificacion="ok", puntaje=5).puntaje == 5
    for malo in (0, 6, 3.5):
        with pytest.raises(ValidationError):
            SalidaJuez(justificacion="x", puntaje=malo)
    # la justificación va antes del puntaje en el esquema (el modelo razona y después puntúa)
    assert list(SalidaJuez.model_json_schema()["properties"]) == ["justificacion", "puntaje"]


def _reporte(split="dev") -> Reporte:
    salidas = {
        "enot": [salida("enot", "q1"), salida("enot", "q2")],
        "B1": [salida("B1", "q1", tipo="sin_candidatas", it=None), salida("B1", "q2")],
    }
    return Reporte(split=split, fecha="2026-11-29-120000", configuracion={}, metricas={}, evaluaciones={},
                   salidas=salidas)


def test_juzgar_reporte_solo_juzgables(corpus):
    consultas = [consulta("q1"), consulta("q2", preferencias=None)]
    # q2 no tiene preferencias: no se juzga; de q1, B1 no entregó itinerario
    cli = ClienteFalso([{"justificacion": "bien", "puntaje": 3}])
    js = juzgar_reporte(cli, _reporte(), consultas, corpus, origen="reports/eval_dev_x.json")
    assert [(j.consulta_id, j.sistema) for j in js.juicios] == [("q1", "enot")]
    assert (js.reporte, js.split, js.proveedor, js.modelo) == ("reports/eval_dev_x.json", "dev", "falso",
                                                               "modelo-falso")
    assert len(cli.llamadas) == 1


def test_juzgar_reporte_consulta_desconocida(corpus):
    with pytest.raises(ValueError, match="q2"):
        juzgar_reporte(ClienteFalso([{"justificacion": "x", "puntaje": 3}]), _reporte(), [consulta("q1")], corpus,
                       origen="r")


def test_cli_juez_escribe_sin_pisar(entorno, corpus, monkeypatch):
    carpeta_set = config.DATA / "eval" / "dev"
    carpeta_set.mkdir(parents=True)
    (carpeta_set / "consultas.jsonl").write_text(consulta("q1").model_dump_json() + "\n"
                                                 + consulta("q2").model_dump_json() + "\n", encoding="utf-8")
    ruta_reporte = config.REPORTS_DIR / "eval_dev_2026-11-29-120000.json"
    ruta_reporte.write_text(_reporte().model_dump_json(), encoding="utf-8")
    fichas = config.DATA / "fichas.jsonl"
    fichas.write_text((FIXTURES / "fichas_sinteticas.jsonl").read_text(encoding="utf-8"), encoding="utf-8")

    def fabrica():
        return ClienteFalso([{"justificacion": "bien", "puntaje": 5}])

    args = [str(ruta_reporte), "--fichas", str(fichas)]
    assert juez.main(args, crear_cliente=fabrica) == 0
    assert juez.main(args, crear_cliente=fabrica) == 0
    salidas = sorted(config.REPORTS_DIR.glob("juez_dev_*.json"))
    assert len(salidas) == 2
    leido = juez.Juicios.model_validate_json(salidas[0].read_text(encoding="utf-8"))
    # q1: enot; q2: enot y B1 (los tres juzgables)
    assert sorted((j.consulta_id, j.sistema) for j in leido.juicios) == [("q1", "enot"), ("q2", "B1"), ("q2", "enot")]
    assert all(j.puntaje == 5 for j in leido.juicios)


def test_cli_juez_reporte_inexistente(entorno, capsys):
    assert juez.main([str(config.REPORTS_DIR / "no-existe.json")], crear_cliente=lambda: None) == 1
    assert "no existe" in capsys.readouterr().err
