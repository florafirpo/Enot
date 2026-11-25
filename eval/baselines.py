"""Sistemas que se comparan en el benchmark (spec 007, PRD 6, ADR-0007, ADR-0017).

- **B0, LLM zero-shot**: el texto del turista directo al modelo, sin corpus ni tools. Lo que haría un turista con un
  chatbot general; mide también cuánto inventa sobre domaines reales.
- **B1, determinístico**: formulario (el perfil etiquetado) + filtros duros + armado greedy por cercanía, sin LLM.
  Usa el verificador como oráculo: una sola fuente de verdad para las reglas (ADR-0005).
- **B2, ablación**: Enot con un solo intento y sin el verificador como guardia (entrega la primera propuesta).
- **Enot**: el flujo completo de ADR-0003.

Todos devuelven una `SalidaSistema` por consulta.
"""
from __future__ import annotations

import re
import time
import unicodedata
from pathlib import Path
from typing import Optional, Protocol

from pydantic import BaseModel, Field

from enot.flujo import MAX_INTENTOS, Flujo, Sesion
from enot.modelos import Bodega, Dia, DiaItinerario, Hora, Itinerario, Parada, a_hora, a_minutos
from enot.retrieval import Indice, dias_del_viaje, filtrar
from enot.tools import tiempo_traslado
from enot.verificador import verificar
from eval.generador import Consulta
from eval.metricas import PrecioAfirmado, SalidaSistema

__all__ = ["PROMPT_B0", "BaselineB0", "BaselineB1", "SalidaB0", "Sistema", "SistemaEnot", "crear_b2", "crear_enot",
           "resolver_bodega"]


class Sistema(Protocol):
    nombre: str

    def correr(self, consulta: Consulta) -> SalidaSistema: ...


# --- B0: zero-shot -----------------------------------------------------------------------------

PROMPT_B0 = """Sos un asistente de viajes. Un turista te pide un itinerario de visitas a bodegas (domaines) de \
Borgoña, Francia. Armá el itinerario día por día: para cada visita, el nombre de la bodega, la hora de inicio \
(HH:MM), la duración en minutos y, si querés, la experiencia y su precio por persona en euros. Usá el día de la \
semana de cada día del viaje (lun, mar, mie, jue, vie, sab, dom). Respetá todo lo que pide el turista. Si el pedido \
es imposible de cumplir, poné es_posible en false y explicá por qué en motivo. Respondé solo con el JSON pedido."""


class ParadaB0(BaseModel):
    bodega: str = Field(description="Nombre de la bodega")
    hora_inicio: Hora
    duracion_min: int = Field(gt=0)
    experiencia: Optional[str] = None
    precio_por_persona_eur: Optional[float] = Field(None, ge=0)


class DiaB0(BaseModel):
    dia_semana: Dia
    paradas: list[ParadaB0] = Field(default_factory=list)


class SalidaB0(BaseModel):
    es_posible: bool
    motivo: Optional[str] = None
    dias: list[DiaB0] = Field(default_factory=list)


def _clave_nombre(nombre: str) -> str:
    """Sin lo que va entre corchetes, sin acentos, sin mayúsculas y sin puntuación."""
    t = re.sub(r"\[[^\]]*\]", " ", nombre)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().casefold()
    return " ".join(re.findall(r"[a-z0-9]+", t))


def resolver_bodega(nombre: str, corpus: dict[str, Bodega]) -> Optional[str]:
    """El id de la bodega del corpus con el mismo nombre (normalizado), o None. Con nombres repetidos, el menor id."""
    clave = _clave_nombre(nombre)
    if not clave:
        return None
    return next((i for i in sorted(corpus) if _clave_nombre(corpus[i].nombre) == clave), None)


class BaselineB0:
    nombre = "B0"

    def __init__(self, cliente, corpus: dict[str, Bodega]):
        self.cliente = cliente
        self.corpus = corpus

    def correr(self, consulta: Consulta) -> SalidaSistema:
        t0 = time.perf_counter()
        r = self.cliente.estructurado(PROMPT_B0, f"Pedido del turista:\n{consulta.texto}", SalidaB0)
        latencia = time.perf_counter() - t0
        salida: SalidaB0 = r.objeto
        comunes = dict(consulta_id=consulta.id, sistema=self.nombre, intentos=1, tokens_in=r.tokens_in,
                       tokens_out=r.tokens_out, latencia_s=latencia)
        if not salida.es_posible:
            return SalidaSistema(**comunes, tipo="infactible", texto=salida.motivo or "")
        dias, precios = [], []
        for n, d in enumerate(salida.dias, 1):
            paradas = []
            for p in d.paradas:
                # una bodega que no está en el corpus queda con un id que el verificador marca como inexistente
                bodega_id = resolver_bodega(p.bodega, self.corpus) or f"b0:{p.bodega}"
                paradas.append(Parada(bodega_id=bodega_id, hora_inicio=p.hora_inicio, duracion_min=p.duracion_min,
                                      experiencia=p.experiencia))
                if p.precio_por_persona_eur is not None:
                    precios.append(PrecioAfirmado(bodega_id=bodega_id, experiencia=p.experiencia,
                                                  precio_por_persona_eur=p.precio_por_persona_eur))
            dias.append(DiaItinerario(numero=n, dia_semana=d.dia_semana, paradas=paradas))
        return SalidaSistema(**comunes, tipo="itinerario", itinerario=Itinerario(dias=dias), precios_afirmados=precios,
                             texto=salida.motivo or "")


# --- B1: filtros + greedy por cercanía ----------------------------------------------------------

class BaselineB1:
    """El turista carga sus restricciones en un formulario (el perfil etiquetado): no hay relevamiento."""
    nombre = "B1"

    def __init__(self, corpus: dict[str, Bodega], duracion_defecto: int = 60, max_paradas_dia: int = 4):
        self.corpus = corpus
        self.duracion_defecto = duracion_defecto
        self.max_paradas_dia = max_paradas_dia

    def _variantes(self, b: Bodega, dia: str, desde: int) -> list[Parada]:
        """Paradas posibles en `b`, en orden de preferencia: sin experiencia y después cada experiencia; a la hora
        `desde` o, si la bodega abre más tarde ese día, a la hora de apertura."""
        aperturas = sorted({a_minutos(h.apertura) for h in b.horarios if dia in h.dias and h.apertura})
        horas = [desde] + [a for a in aperturas if a > desde]
        opciones = [(None, self.duracion_defecto)]
        opciones += [(e.nombre, e.duracion_min or self.duracion_defecto) for e in b.experiencias]
        return [Parada(bodega_id=b.id, hora_inicio=a_hora(h), duracion_min=dur, experiencia=exp)
                for exp, dur in opciones for h in horas if h + dur < 24 * 60]

    def _orden(self, candidatas: list[Bodega], desde: Optional[str], transporte: str) -> list[Bodega]:
        """Por cercanía a `desde` (sin dato de traslado, al final); empates y primera parada del viaje, por id."""
        if desde is None:
            return sorted(candidatas, key=lambda b: b.id)

        def clave(b: Bodega):
            m = tiempo_traslado(self.corpus, desde, b.id, transporte).minutos
            return (m is None, m or 0, b.id)
        return sorted(candidatas, key=clave)

    def correr(self, consulta: Consulta) -> SalidaSistema:
        t0 = time.perf_counter()
        perfil = consulta.restricciones
        comunes = dict(consulta_id=consulta.id, sistema=self.nombre)
        candidatas = filtrar(sorted(self.corpus.values(), key=lambda b: b.id), perfil)
        if not candidatas:
            return SalidaSistema(**comunes, tipo="sin_candidatas", latencia_s=time.perf_counter() - t0,
                                 texto="Ninguna bodega cumple los filtros del formulario.")
        itinerario = Itinerario(dias=[])
        usadas: set[str] = set()
        ultima: Optional[str] = None
        for n, dia in enumerate(dias_del_viaje(perfil), 1):
            d = DiaItinerario(numero=n, dia_semana=dia, paradas=[])
            itinerario.dias.append(d)
            while len(d.paradas) < self.max_paradas_dia:
                elegida = self._siguiente(itinerario, d, candidatas, usadas, ultima, perfil)
                if elegida is None:
                    break
                usadas.add(elegida.bodega_id)
                ultima = elegida.bodega_id
            if not d.paradas:
                return SalidaSistema(**comunes, tipo="infactible", latencia_s=time.perf_counter() - t0,
                                     texto=f"No encontré ninguna visita posible para el día {n} ({dia}).")
        return SalidaSistema(**comunes, tipo="itinerario", itinerario=itinerario, latencia_s=time.perf_counter() - t0)

    def _siguiente(self, itinerario: Itinerario, d: DiaItinerario, candidatas: list[Bodega], usadas: set[str],
                   ultima: Optional[str], perfil) -> Optional[Parada]:
        """Agrega a `d` la primera parada que el verificador acepta, de la bodega no usada más cercana a la última."""
        reloj = a_minutos(perfil.hora_inicio_jornada)
        if d.paradas:
            anterior = d.paradas[-1]
            reloj = a_minutos(anterior.hora_inicio) + anterior.duracion_min
        for b in self._orden([b for b in candidatas if b.id not in usadas], ultima, perfil.transporte):
            traslado = tiempo_traslado(self.corpus, d.paradas[-1].bodega_id, b.id, perfil.transporte).minutos \
                if d.paradas else 0
            for p in self._variantes(b, d.dia_semana, reloj + (traslado or 0)):
                d.paradas.append(p)
                if not verificar(itinerario, perfil, self.corpus):
                    return p
                d.paradas.pop()
        return None


# --- Enot y B2 ---------------------------------------------------------------------------------

class SistemaEnot:
    """Un turno de `Flujo` por consulta, con una sesión (y una traza) nueva cada vez."""

    def __init__(self, flujo: Flujo, nombre: str, carpeta_trazas: Path, entregar_sin_verificar: bool = False):
        self.flujo = flujo
        self.nombre = nombre
        self.carpeta_trazas = Path(carpeta_trazas)
        self.entregar_sin_verificar = entregar_sin_verificar

    def correr(self, consulta: Consulta) -> SalidaSistema:
        sesion = Sesion.nueva(self.carpeta_trazas)
        t0 = time.perf_counter()
        r = self.flujo.turno(sesion, consulta.texto)
        latencia = time.perf_counter() - t0
        eventos = sesion.traza().eventos()
        tipo, itinerario = r.tipo, (r.itinerario if r.tipo == "itinerario" else None)
        if self.entregar_sin_verificar and r.tipo == "infactible" and r.itinerario is not None:
            # sin loop no hay guardia: la primera propuesta llega al turista aunque el verificador la rechace
            tipo, itinerario = "itinerario", r.itinerario
        return SalidaSistema(consulta_id=consulta.id, sistema=self.nombre, tipo=tipo, itinerario=itinerario,
                             texto=r.texto, intentos=r.intentos, latencia_s=latencia,
                             tokens_in=sum(e.tokens_in or 0 for e in eventos),
                             tokens_out=sum(e.tokens_out or 0 for e in eventos))


def crear_enot(cliente, corpus: dict[str, Bodega], indice: Indice, carpeta_trazas: Path) -> SistemaEnot:
    return SistemaEnot(Flujo(cliente, corpus, indice, max_intentos=MAX_INTENTOS), "enot", carpeta_trazas)


def crear_b2(cliente, corpus: dict[str, Bodega], indice: Indice, carpeta_trazas: Path) -> SistemaEnot:
    """Ablación de ADR-0003: un solo intento y sin el verificador como guardia."""
    return SistemaEnot(Flujo(cliente, corpus, indice, max_intentos=1), "B2", carpeta_trazas,
                       entregar_sin_verificar=True)
