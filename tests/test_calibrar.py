"""Spec 008: calibración del juez contra la anotación humana (Spearman y kappa, ADR-0007, ADR-0018).

Los valores de referencia están calculados a mano en los comentarios y, si están instaladas, se comparan además con
scipy y scikit-learn (no son dependencias del repo).
"""
from __future__ import annotations

import csv
import math

import pytest

from enot.corpus_local import cargar_corpus
from eval import calibrar as cal
from eval.calibrar import (
    COLUMNAS_PLANILLA,
    MINIMO_CASOS,
    Anotacion,
    armar_planilla,
    calibrar,
    escribir_planilla,
    kappa,
    leer_anotaciones,
    rangos,
    spearman,
)
from eval.correr import Reporte
from eval.juez import Juicio, Juicios
from tests.conftest import FIXTURES
from tests.test_juez import consulta, salida


def test_rangos_con_empates():
    assert rangos([10, 20, 20, 30]) == [1, 2.5, 2.5, 4]
    assert rangos([3, 1, 2]) == [3, 1, 2]
    assert rangos([5, 5, 5]) == [2, 2, 2]
    assert rangos([]) == []


def test_spearman_valores_conocidos():
    assert spearman([1, 2, 3, 4, 5], [2, 4, 6, 8, 10]) == pytest.approx(1)
    assert spearman([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) == pytest.approx(-1)
    # sin empates: 1 - 6·Σd² / (n(n²-1)) = 1 - 6·4/120 = 0,8
    assert spearman([1, 2, 3, 4, 5], [2, 1, 4, 3, 5]) == pytest.approx(0.8)
    # con empates: rangos de y = [1, 3, 2, 4.5, 4.5]; Pearson de los rangos = 8.5 / sqrt(10 · 9.5)
    assert spearman([1, 2, 3, 4, 5], [1, 3, 2, 4, 4]) == pytest.approx(8.5 / math.sqrt(95))


def test_spearman_coincide_con_scipy():
    stats = pytest.importorskip("scipy.stats")
    x = [1, 2, 2, 3, 4, 5, 5, 3, 1, 4]
    y = [2, 2, 3, 3, 5, 4, 5, 1, 1, 4]
    assert spearman(x, y) == pytest.approx(stats.spearmanr(x, y).statistic)


def test_spearman_indefinido():
    assert spearman([1, 2], [1, 2]) is None              # menos de 3 pares
    assert spearman([3, 3, 3], [1, 2, 3]) is None        # serie constante: la correlación no está definida
    assert spearman([1, 2, 3], [4, 4, 4]) is None
    with pytest.raises(ValueError):
        spearman([1, 2, 3], [1, 2])


def test_kappa_valores_conocidos():
    assert kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]) == pytest.approx(1)
    assert kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5], "cuadratica") == pytest.approx(1)
    # a = [1,2,3,4], b = [2,2,3,5]
    # sin ponderar: po = 2/4; pe = .25·.5 (cat. 2) + .25·.25 (cat. 3) = .1875 → (.5 - .1875) / .8125 = 5/13
    a, b = [1, 2, 3, 4], [2, 2, 3, 5]
    assert kappa(a, b) == pytest.approx(5 / 13)
    # cuadrático, w = (i-j)²/16: Σw·O = (1+1)/16 · .25 = 1/32; Σw·E = (.75 + .375 + 1.875)/16 = 3/16
    # → 1 - (1/32)/(3/16) = 5/6. Los dos desacuerdos son de un punto: el ponderado los castiga poco.
    assert kappa(a, b, "cuadratica") == pytest.approx(5 / 6)


def test_kappa_cuadratico_castiga_mas_lo_lejano():
    cerca = kappa([1, 2, 3, 4, 5, 3], [1, 2, 3, 4, 5, 4], "cuadratica")
    lejos = kappa([1, 2, 3, 4, 5, 3], [1, 2, 3, 4, 5, 5], "cuadratica")
    assert cerca > lejos
    sin = kappa([1, 2, 3, 4, 5, 1], [1, 2, 3, 4, 5, 5])
    con = kappa([1, 2, 3, 4, 5, 1], [1, 2, 3, 4, 5, 5], "cuadratica")
    assert con < sin                                     # un 1 contra un 5 pesa más con ponderación


def test_kappa_coincide_con_sklearn():
    metrics = pytest.importorskip("sklearn.metrics")
    a = [1, 2, 2, 3, 4, 5, 5, 3, 1, 4, 2, 3]
    b = [2, 2, 3, 3, 5, 4, 5, 1, 1, 4, 2, 4]
    assert kappa(a, b) == pytest.approx(metrics.cohen_kappa_score(a, b))
    assert kappa(a, b, "cuadratica") == pytest.approx(
        metrics.cohen_kappa_score(a, b, weights="quadratic", labels=[1, 2, 3, 4, 5]))


def test_kappa_indefinido_y_fuera_de_escala():
    assert kappa([3, 3, 3], [3, 3, 3]) is None           # acuerdo esperado = 1: kappa no está definido
    assert kappa([3, 3, 3], [3, 3, 3], "cuadratica") is None
    assert kappa([], []) is None
    with pytest.raises(ValueError):
        kappa([0, 1], [1, 1])
    with pytest.raises(ValueError):
        kappa([1, 6], [1, 1])
    with pytest.raises(ValueError):
        kappa([1, 2], [1])
    with pytest.raises(ValueError):
        kappa([1, 2], [1, 2], "lineal")


def _escribir_csv(ruta, filas):
    with ruta.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS_PLANILLA)
        w.writeheader()
        for fila in filas:
            w.writerow({c: fila.get(c, "") for c in COLUMNAS_PLANILLA})


def test_leer_anotaciones(tmp_path):
    ruta = tmp_path / "a.csv"
    _escribir_csv(ruta, [{"consulta_id": "q1", "sistema": "enot", "puntaje_humano": "4"},
                         {"consulta_id": "q2", "sistema": "B1", "puntaje_humano": ""},
                         {"consulta_id": "q3", "sistema": "B1", "puntaje_humano": " 2 "}])
    assert leer_anotaciones(ruta) == [Anotacion(consulta_id="q1", sistema="enot", puntaje_humano=4),
                                      Anotacion(consulta_id="q2", sistema="B1", puntaje_humano=None),
                                      Anotacion(consulta_id="q3", sistema="B1", puntaje_humano=2)]
    for malo in ("7", "0", "a", "3.5"):
        _escribir_csv(ruta, [{"consulta_id": "q1", "sistema": "enot", "puntaje_humano": malo}])
        with pytest.raises(ValueError, match="q1"):
            leer_anotaciones(ruta)


def _juicios(puntajes: list[int | None], sistema="enot") -> Juicios:
    js = [Juicio(consulta_id=f"q{i}", sistema=sistema, estado="ok" if p is not None else "error", puntaje=p,
                 error=None if p is not None else "x", tokens_in=1, tokens_out=1, latencia_s=0.0)
          for i, p in enumerate(puntajes)]
    return Juicios(reporte="r", split="dev", fecha="f", proveedor="p", modelo="m", juicios=js)


def _anotaciones(puntajes: list[int | None], sistema="enot") -> list[Anotacion]:
    return [Anotacion(consulta_id=f"q{i}", sistema=sistema, puntaje_humano=p) for i, p in enumerate(puntajes)]


def test_calibrar_cuenta_pares_y_faltantes():
    juicios = _juicios([1, 2, None, 4, 5])               # q2: el juez falló
    anot = _anotaciones([1, 2, 3, None, 5]) + [Anotacion(consulta_id="q9", sistema="enot", puntaje_humano=3)]
    anot.append(Anotacion(consulta_id="q0", sistema="B1", puntaje_humano=2))   # otro sistema: sin juicio
    c = calibrar(anot, juicios)
    assert c.pares == 3                                  # q0, q1 y q4 de enot
    assert c.sin_anotar == 1                             # q3
    assert c.sin_juicio == 3                             # q2 (juicio en error), q9 y q0 de B1
    assert c.spearman == pytest.approx(1) and c.kappa == pytest.approx(1)
    assert c.apto is False and "3" in c.motivo


def test_calibrar_apto_y_no_apto():
    puntajes = [1 + i % 5 for i in range(MINIMO_CASOS)]
    ok = calibrar(_anotaciones(puntajes), _juicios(puntajes))
    assert ok.pares == MINIMO_CASOS and ok.apto is True
    assert ok.kappa_cuadratico == pytest.approx(1)

    pocos = calibrar(_anotaciones(puntajes[:-1]), _juicios(puntajes[:-1]))
    assert pocos.apto is False and str(MINIMO_CASOS) in pocos.motivo

    opuestos = calibrar(_anotaciones([6 - p for p in puntajes]), _juicios(puntajes))
    assert opuestos.spearman == pytest.approx(-1)
    assert opuestos.apto is False and "Spearman" in opuestos.motivo

    # Spearman alto pero kappa bajo: el juez ordena igual pero puntúa sistemáticamente 2 puntos más arriba
    corridos = [min(5, p + 2) for p in puntajes]
    sesgado = calibrar(_anotaciones(puntajes), _juicios(corridos))
    assert sesgado.spearman >= cal.UMBRAL_SPEARMAN
    assert sesgado.kappa_cuadratico < cal.UMBRAL_KAPPA
    assert sesgado.apto is False and "kappa" in sesgado.motivo


def test_calibrar_en_el_umbral_es_apto(monkeypatch):
    puntajes = [1 + i % 5 for i in range(MINIMO_CASOS)]
    c = calibrar(_anotaciones(puntajes), _juicios(puntajes))
    monkeypatch.setattr(cal, "UMBRAL_SPEARMAN", c.spearman)
    monkeypatch.setattr(cal, "UMBRAL_KAPPA", c.kappa_cuadratico)
    assert calibrar(_anotaciones(puntajes), _juicios(puntajes)).apto is True


@pytest.fixture
def corpus():
    return cargar_corpus(FIXTURES / "fichas_sinteticas.jsonl")


def _reporte_planilla(split="dev") -> tuple[Reporte, list]:
    consultas = [consulta(f"q{i}") for i in range(6)] + [consulta("q9", preferencias=None)]
    salidas = {s: [salida(s, c.id) for c in consultas] for s in ("B0", "B1", "enot")}
    salidas["B1"][0] = salida("B1", "q0", tipo="infactible", it=None)
    return Reporte(split=split, fecha="f", configuracion={}, metricas={}, evaluaciones={}, salidas=salidas), consultas


def test_armar_planilla_estratificada_y_ciega(corpus):
    reporte, consultas = _reporte_planilla()
    filas = armar_planilla(reporte, consultas, corpus, n=7, semilla=1)
    assert len(filas) == 7
    assert all(list(f) == list(COLUMNAS_PLANILLA) for f in filas)
    assert all(f["puntaje_humano"] == "" and f["comentario"] == "" for f in filas)
    claves = [(f["consulta_id"], f["sistema"]) for f in filas]
    assert len(set(claves)) == 7
    assert all(c != "q9" for c, _ in claves)              # sin preferencias: no juzgable
    assert ("q0", "B1") not in claves                     # B1 no entregó itinerario
    por_sistema = {s: sum(1 for _, x in claves if x == s) for s in ("B0", "B1", "enot")}
    assert max(por_sistema.values()) - min(por_sistema.values()) <= 1
    # el humano ve lo mismo que el juez: pedido e itinerario con datos del corpus, sin el sistema
    assert all("Día 1" in f["itinerario"] and f["sistema"] not in f["itinerario"] for f in filas)
    assert all(f["pedido"] for f in filas)
    assert armar_planilla(reporte, consultas, corpus, n=7, semilla=1) == filas
    assert len(armar_planilla(reporte, consultas, corpus, n=100)) == 17   # todas las juzgables


def test_armar_planilla_rechaza_test(corpus):
    reporte, consultas = _reporte_planilla(split="test")
    with pytest.raises(ValueError, match="dev"):
        armar_planilla(reporte, consultas, corpus)


def test_escribir_planilla_no_pisa(tmp_path, corpus):
    reporte, consultas = _reporte_planilla()
    filas = armar_planilla(reporte, consultas, corpus, n=3)
    ruta = escribir_planilla(filas, tmp_path / "sub" / "anotacion_humana.csv")
    contenido = ruta.read_text(encoding="utf-8")
    assert contenido.splitlines()[0] == ",".join(COLUMNAS_PLANILLA)
    assert [a.puntaje_humano for a in leer_anotaciones(ruta)] == [None, None, None]
    with pytest.raises(FileExistsError):
        escribir_planilla(filas[:1], ruta)
    assert ruta.read_text(encoding="utf-8") == contenido


def test_cli_planilla_y_calibrar(entorno, corpus):
    from corpus import config

    reporte, consultas = _reporte_planilla()
    carpeta = config.DATA / "eval" / "dev"
    carpeta.mkdir(parents=True)
    (carpeta / "consultas.jsonl").write_text("".join(c.model_dump_json() + "\n" for c in consultas), encoding="utf-8")
    ruta_rep = config.REPORTS_DIR / "eval_dev_x.json"
    ruta_rep.write_text(reporte.model_dump_json(), encoding="utf-8")
    fichas = config.DATA / "fichas.jsonl"
    fichas.write_text((FIXTURES / "fichas_sinteticas.jsonl").read_text(encoding="utf-8"), encoding="utf-8")

    assert cal.main(["planilla", str(ruta_rep), "--n", "4", "--fichas", str(fichas)]) == 0
    destino = config.DATA / "eval" / "anotacion_humana.csv"
    filas = list(csv.DictReader(destino.open(encoding="utf-8")))
    assert len(filas) == 4
    assert cal.main(["planilla", str(ruta_rep), "--fichas", str(fichas)]) == 1   # no pisa la anotación

    for f in filas:
        f["puntaje_humano"] = "3"
    _escribir_csv(destino, filas)
    juicios = Juicios(reporte=str(ruta_rep), split="dev", fecha="f", proveedor="p", modelo="m", juicios=[
        Juicio(consulta_id=f["consulta_id"], sistema=f["sistema"], estado="ok", puntaje=3, tokens_in=1, tokens_out=1,
               latencia_s=0.0) for f in filas])
    ruta_j = config.REPORTS_DIR / "juez_dev_x.json"
    ruta_j.write_text(juicios.model_dump_json(), encoding="utf-8")
    assert cal.main(["calibrar", str(ruta_j)]) == 0
    (salida_cal,) = config.REPORTS_DIR.glob("calibracion_*.json")
    leida = cal.Calibracion.model_validate_json(salida_cal.read_text(encoding="utf-8"))
    assert leida.pares == 4 and leida.apto is False


# --- sobrevivientes de mutation (eval/calibrar.py) --------------------------------------------------------------------
# Equivalentes (no se agregan tests, se explican en el reporte): en `spearman`, (a + mx) en vez de (a − mx) da la misma
# covarianza porque Σ(b − my) = 0; en `kappa`, el divisor (k − 1)² y el peso 2 en vez de 1 escalan por igual Σw·O y
# Σw·E y se cancelan; el valor inicial de `rangos` se pisa siempre; `strict` en zip ya está cubierto por el chequeo de
# largos.

def test_errores_con_mensaje():
    with pytest.raises(ValueError, match="largo distinto"):
        spearman([1, 2, 3], [1, 2])
    with pytest.raises(ValueError, match="largo distinto"):
        kappa([1, 2], [1])
    with pytest.raises(ValueError, match="ponderación"):
        kappa([1, 2], [1, 2], "lineal")
    with pytest.raises(ValueError, match="escala"):
        kappa([1, 6], [1, 1])


def test_calibrar_cuenta_cada_faltante_y_usa_el_kappa_cuadratico():
    juicios = _juicios([1, 2, 3, 4, 5, 1])
    anot = _anotaciones([1, 2, 4, 5, None, None])            # dos sin anotar
    c = calibrar(anot, juicios)
    assert c.sin_anotar == 2 and c.pares == 4
    assert c.kappa == pytest.approx(kappa([1, 2, 4, 5], [1, 2, 3, 4]))
    assert c.kappa_cuadratico == pytest.approx(kappa([1, 2, 4, 5], [1, 2, 3, 4], "cuadratica"))
    assert c.kappa != pytest.approx(c.kappa_cuadratico)


def test_motivo_sin_dato():
    c = calibrar(_anotaciones([3, 3, 3]), _juicios([3, 3, 3]))   # todo constante: ni Spearman ni kappa definidos
    assert c.spearman is None and c.kappa_cuadratico is None and c.apto is False
    assert c.motivo == "3 pares < 30; Spearman s/d < 0.6; kappa cuadrático s/d < 0.6"
    ok = calibrar(_anotaciones([1 + i % 5 for i in range(30)]), _juicios([1 + i % 5 for i in range(30)]))
    assert ok.motivo == "30 pares, Spearman 1.00 y kappa cuadrático 1.00 sobre los umbrales"


def test_planilla_semilla_por_defecto_y_carpetas(tmp_path, corpus):
    reporte, consultas = _reporte_planilla()
    assert armar_planilla(reporte, consultas, corpus, n=5) == armar_planilla(reporte, consultas, corpus, n=5,
                                                                              semilla=2026)
    ruta = escribir_planilla(armar_planilla(reporte, consultas, corpus, n=2), tmp_path / "a" / "b" / "p.csv")
    assert len(leer_anotaciones(ruta)) == 2
    with pytest.raises(FileExistsError, match="ya existe"):
        escribir_planilla([], ruta)
    with pytest.raises(ValueError, match="test"):
        armar_planilla(_reporte_planilla("test")[0], consultas, corpus)


def test_cli_planilla_por_defecto_y_con_carpetas(entorno, corpus, capsys):
    from corpus import config

    reporte, consultas = _reporte_planilla()
    carpeta = entorno / "otro_set"
    (carpeta / "dev").mkdir(parents=True)
    (carpeta / "dev" / "consultas.jsonl").write_text("".join(c.model_dump_json() + "\n" for c in consultas),
                                                     encoding="utf-8")
    ruta_rep = config.REPORTS_DIR / "eval_dev_x.json"
    ruta_rep.write_text(reporte.model_dump_json(), encoding="utf-8")
    fichas = entorno / "fichas.jsonl"
    fichas.write_text((FIXTURES / "fichas_sinteticas.jsonl").read_text(encoding="utf-8"), encoding="utf-8")

    # sin --n ni --semilla: 30 casos (hay 17 juzgables) con la semilla 2026; sin --destino, va a la carpeta del set
    assert cal.main(["planilla", str(ruta_rep), "--set", str(carpeta), "--fichas", str(fichas)]) == 0
    filas = list(csv.DictReader((carpeta / "anotacion_humana.csv").open(encoding="utf-8")))
    esperadas = armar_planilla(reporte, consultas, corpus, n=30, semilla=2026)
    assert [(f["consulta_id"], f["sistema"]) for f in filas] == [(f["consulta_id"], f["sistema"]) for f in esperadas]

    destino = entorno / "x" / "y.csv"
    assert cal.main(["planilla", str(ruta_rep), "--set", str(carpeta), "--fichas", str(fichas), "--n", "3",
                     "--semilla", "7", "--destino", str(destino)]) == 0
    assert len(leer_anotaciones(destino)) == 3
    capsys.readouterr()
    assert cal.main(["calibrar", str(entorno / "no-existe.json")]) == 1
    assert capsys.readouterr().err.startswith("[calibrar] ")


def test_motivo_con_valores_bajo_el_umbral():
    puntajes = [1 + i % 5 for i in range(MINIMO_CASOS)]
    opuestos = calibrar(_anotaciones([6 - p for p in puntajes]), _juicios(puntajes))
    assert opuestos.motivo == "Spearman -1.00 < 0.6; kappa cuadrático -1.00 < 0.6"
