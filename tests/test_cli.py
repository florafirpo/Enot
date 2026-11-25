"""Spec 005: chat por consola (`python -m enot`). Sin red: el flujo se arma con dobles (bodegas SINTÉTICAS)."""
from __future__ import annotations

import pytest

from enot.__main__ import flujo_desde_args, main
from enot.corpus_local import cargar_corpus
from enot.flujo import K_CANDIDATAS, MAX_INTENTOS, TOPE_TOKENS, Flujo, Mensaje, Sesion
from enot.retrieval import Indice
from tests.conftest import FIXTURES, ClienteFalso
from tests.dobles import EmbedderFalso
from tests.test_flujo import PERFIL, SALIDA_RESPUESTA, VALIDO, Guion


def consola(entradas: list[str]):
    """`leer` que devuelve las entradas en orden (EOFError al final) y `escribir` que junta la salida."""
    pendientes = list(entradas)
    salida: list[str] = []

    def leer(_prompt: str = "") -> str:
        if not pendientes:
            raise EOFError
        return pendientes.pop(0)

    return leer, salida.append, salida


def flujo_falso(guion: Guion):
    corpus = cargar_corpus(FIXTURES / "fichas_sinteticas.jsonl")
    return lambda _args: Flujo(ClienteFalso([guion]), corpus, Indice(list(corpus.values()), EmbedderFalso()))


def test_cli_conversa_y_guarda_la_sesion(entorno, tmp_path):
    g = Guion(relevamiento=[PERFIL], planificador=[VALIDO], respuesta=[SALIDA_RESPUESTA])
    leer, escribir, salida = consola(["Un día el viernes en auto, somos 2", "  ", "salir", "no se lee"])
    ruta = tmp_path / "sesion.json"
    assert main(["--sesion", str(ruta)], leer, escribir, flujo_falso(g)) == 0

    texto = "\n".join(salida)
    assert "Te armé este recorrido." in texto and "[SINTÉTICA] Domaine Beaune Centre" in texto
    sesion = Sesion.cargar(ruta)
    assert [m.rol for m in sesion.historial] == ["turista", "enot"]  # la línea vacía no es un turno
    assert sesion.itinerario is not None
    assert len(g.recibido["relevamiento"]) == 1  # "no se lee" quedó después de "salir"
    assert sesion.traza().ruta.parent == entorno / "data" / "trazas"


def test_cli_termina_con_eof_sin_sesion(entorno):
    g = Guion(relevamiento=[{"cantidad_dias": 1}])
    leer, escribir, salida = consola(["hola"])
    assert main([], leer, escribir, flujo_falso(g)) == 0
    assert any("me falta saber" in s for s in salida)


def test_cli_retoma_la_sesion(entorno, tmp_path):
    ruta = tmp_path / "sesion.json"
    previa = Sesion.nueva(tmp_path / "trazas")
    previa.historial = [Mensaje(rol="turista", texto="Somos 2 y vamos en auto"),
                        Mensaje(rol="enot", texto="¿Cuántos días?")]
    previa.guardar(ruta)

    g = Guion(relevamiento=[PERFIL], planificador=[VALIDO], respuesta=[SALIDA_RESPUESTA])
    leer, escribir, _ = consola(["Un día, el viernes"])
    assert main(["--sesion", str(ruta)], leer, escribir, flujo_falso(g)) == 0
    contexto = g.recibido["relevamiento"][0]
    assert "Somos 2 y vamos en auto" in contexto and "Un día, el viernes" in contexto
    retomada = Sesion.cargar(ruta)
    assert len(retomada.historial) == 4
    assert retomada.ruta_traza == previa.ruta_traza


def test_cli_pasa_las_opciones_al_flujo(entorno):
    armados: list[Flujo] = []

    def construir(args):
        f = flujo_desde_args(args, cliente=ClienteFalso([{}]), embedder=EmbedderFalso())
        armados.append(f)
        return f

    leer, escribir, _ = consola([])
    argv = ["--fichas", str(FIXTURES / "fichas_sinteticas.jsonl"), "--max-intentos", "1", "--tope-tokens", "500",
            "--k", "4"]
    assert main(argv, leer, escribir, construir) == 0
    (f,) = armados
    assert (f.max_intentos, f.tope_tokens, f.k) == (1, 500, 4)
    assert set(f.corpus) == set(cargar_corpus(FIXTURES / "fichas_sinteticas.jsonl"))

    armados.clear()
    assert main(["--fichas", str(FIXTURES / "fichas_sinteticas.jsonl")], leer, escribir, construir) == 0
    (f,) = armados  # valores por defecto, pasando por argparse
    assert (f.max_intentos, f.tope_tokens, f.k) == (MAX_INTENTOS, TOPE_TOKENS, K_CANDIDATAS) == (3, 200_000, 10)


def test_cli_sin_corpus_sale_con_error(entorno, monkeypatch):
    def explota(*_a, **_k):
        raise AssertionError("no tiene que construir el cliente LLM sin corpus")

    monkeypatch.setattr("corpus.llm.ClienteLLM", explota)
    leer, escribir, salida = consola(["hola"])
    assert main([], leer, escribir) == 1
    assert any("fichas" in s for s in salida)


def test_cli_error_del_cliente_llm_sale_con_error(entorno, monkeypatch):
    def sin_clave(*_a, **_k):
        raise RuntimeError("falta OPENAI_API_KEY")

    monkeypatch.setattr("corpus.llm.ClienteLLM", sin_clave)
    leer, escribir, salida = consola(["hola"])
    assert main(["--fichas", str(FIXTURES / "fichas_sinteticas.jsonl")], leer, escribir) == 1
    assert any("cliente del LLM" in s and "falta OPENAI_API_KEY" in s for s in salida)


def test_cli_ctrl_c_en_un_turno_no_guarda_el_turno_a_medias(entorno, tmp_path):
    ruta = tmp_path / "sesion.json"
    g = Guion(relevamiento=[PERFIL], planificador=[VALIDO], respuesta=[SALIDA_RESPUESTA])
    real = flujo_falso(g)

    class Interrumpe(Flujo):
        def turno(self, sesion, texto):
            if texto == "corte":
                sesion.historial.append(Mensaje(rol="turista", texto=texto))  # quedó a medias
                raise KeyboardInterrupt
            return super().turno(sesion, texto)

    def construir(args):
        f = real(args)
        return Interrumpe(f.cliente, f.corpus, f.indice)

    leer, escribir, salida = consola(["Un día el viernes en auto, somos 2", "corte", "no se lee"])
    assert main(["--sesion", str(ruta)], leer, escribir, construir) == 0
    guardada = Sesion.cargar(ruta)
    assert [m.texto for m in guardada.historial][-1] != "corte"
    assert len(guardada.historial) == 2
    assert any("interrump" in s for s in salida)
    assert len(g.recibido["relevamiento"]) == 1


@pytest.mark.parametrize("opcion", ["--max-intentos", "--tope-tokens", "--k"])
def test_cli_rechaza_valores_no_positivos(entorno, opcion):
    leer, escribir, _ = consola([])
    with pytest.raises(SystemExit):
        main([opcion, "0"], leer, escribir, flujo_falso(Guion()))
