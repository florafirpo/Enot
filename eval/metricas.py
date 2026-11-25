"""Métricas verificables del benchmark (spec 007, ADR-0007, ADR-0017).

Funciones puras: reciben las consultas etiquetadas (ítem 006), lo que entregó cada sistema y el corpus. Ninguna llama
a un LLM ni lee archivos. El preference score (juez LLM) y el costo en USD son del ítem 008.

- **Hard pass rate** (H1), sobre consultas factibles, todo o nada: el sistema entregó un itinerario, con la estructura
  que pide el perfil, sin violaciones del verificador **contra la etiqueta** y sin afirmaciones inventadas.
- **Tasa de alucinación**: afirmaciones inventadas / afirmaciones verificables (bodega, experiencia, precio).
- **Cobertura del corpus + Gini** (H3), sobre los itinerarios entregados.
- **Infactibles bien detectados**: el sistema dice que no se puede (o que la zona no existe) en vez de entregar algo.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from typing import Literal, Optional

from pydantic import BaseModel, Field

from enot.modelos import Bodega, Itinerario, PerfilViaje
from enot.retrieval import dias_del_viaje
from enot.verificador import TipoViolacion, verificar
from eval.generador import Consulta, Escenario, MotivoInfactible

__all__ = ["DETECTAN_INFACTIBLE", "REPRESENTABLES", "TOLERANCIA_PRECIO_EUR", "EvaluacionConsulta", "Metricas",
           "PrecioAfirmado", "SalidaSistema", "TipoSalida", "afirmaciones", "cobertura_corpus", "detecta_infactible",
           "evaluar_consulta", "faltantes_estructurales", "gini", "hard_pass_rate", "infactibles_detectados",
           "recomendaciones_por_bodega", "resumir", "tasa_alucinacion"]

# Los tipos de `enot.flujo.Respuesta`; los baselines usan los mismos.
TipoSalida = Literal["itinerario", "infactible", "zona_desconocida", "sin_candidatas", "pregunta", "tope_tokens",
                     "error"]
DETECTAN_INFACTIBLE = frozenset({"infactible", "sin_candidatas"})
# Motivos de infactibilidad que el sistema puede representar hoy (ADR-0016): los demás dependen de restricciones que
# `PerfilViaje` no tiene (decisión pendiente de Flora).
REPRESENTABLES = frozenset({"zona_fuera_de_borgona"})
TOLERANCIA_PRECIO_EUR = 0.01


class PrecioAfirmado(BaseModel):
    """Un precio que el sistema le dice al turista. `experiencia=None` = la visita más barata en EUR."""
    bodega_id: str
    experiencia: Optional[str] = None
    precio_por_persona_eur: float


class SalidaSistema(BaseModel):
    """Lo que un sistema le entregó al turista para una consulta (un turno)."""
    consulta_id: str
    sistema: str
    tipo: TipoSalida
    itinerario: Optional[Itinerario] = Field(None, description="Lo que se le entrega al turista")
    precios_afirmados: list[PrecioAfirmado] = Field(default_factory=list,
                                                    description="Solo B0: Enot y B1 sacan los precios del corpus")
    texto: str = ""
    intentos: int = 0
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    latencia_s: float = 0.0
    traza: Optional[str] = Field(None, description="Ruta de la traza de la consulta (Enot y B2), para el reporte")


class EvaluacionConsulta(BaseModel):
    consulta_id: str
    escenario: Escenario
    infactible: bool
    motivo_infactible: Optional[MotivoInfactible] = None
    tipo: TipoSalida
    faltantes: list[str] = Field(default_factory=list)
    violaciones: list[TipoViolacion] = Field(default_factory=list)
    afirmaciones: int = 0
    inventadas: int = 0
    hard_pass: Optional[bool] = Field(None, description="None en consultas infactibles")
    infactible_detectado: Optional[bool] = Field(None, description="None en consultas factibles")


# --- estructura --------------------------------------------------------------------------------

def faltantes_estructurales(itinerario: Itinerario, perfil: PerfilViaje) -> list[str]:
    """Lo que el verificador no mira y un itinerario entregado tiene que cumplir: un día por día del viaje, en orden, y
    al menos una visita por día (un itinerario vacío no tiene violaciones y no puede contar como acierto)."""
    faltan: list[str] = []
    if len(itinerario.dias) != perfil.cantidad_dias:
        faltan.append(f"tiene {len(itinerario.dias)} días y el viaje es de {perfil.cantidad_dias}")
    esperados = dias_del_viaje(perfil)
    for n, d in enumerate(itinerario.dias, 1):
        if n <= len(esperados) and d.dia_semana != esperados[n - 1]:
            faltan.append(f"el día {n} es {d.dia_semana} y tenía que ser {esperados[n - 1]}")
        if not d.paradas:
            faltan.append(f"el día {n} no tiene visitas")
    return faltan


# --- alucinación -------------------------------------------------------------------------------

def _experiencia(b: Bodega, nombre: str):
    return next((e for e in b.experiencias if e.nombre.casefold() == nombre.casefold()), None)


def _precio_corpus(b: Bodega, experiencia: Optional[str]) -> Optional[float]:
    """El precio en EUR que el corpus respalda, con el mismo criterio que la tool de costos."""
    if experiencia is None:
        en_eur = [e.precio_por_persona for e in b.experiencias if e.precio_por_persona is not None and e.moneda == "EUR"]
        return min(en_eur) if en_eur else None
    e = _experiencia(b, experiencia)
    if e is None or e.precio_por_persona is None or e.moneda != "EUR":
        return None
    return e.precio_por_persona


def afirmaciones(salida: SalidaSistema, corpus: dict[str, Bodega]) -> tuple[int, int]:
    """(afirmaciones verificables, inventadas): una por parada (la bodega), una por experiencia nombrada y una por
    precio afirmado. Sobre una bodega que no está en el corpus, todo lo que se afirma es inventado. Del itinerario
    cuenta solo lo entregado (tipo `itinerario`)."""
    total = inventadas = 0
    entregado = salida.itinerario if salida.tipo == "itinerario" else None
    paradas = [p for d in entregado.dias for p in d.paradas] if entregado is not None else []
    for p in paradas:
        b = corpus.get(p.bodega_id)
        total += 1
        inventadas += b is None
        if p.experiencia is not None:
            total += 1
            inventadas += b is None or _experiencia(b, p.experiencia) is None
    for pa in salida.precios_afirmados:
        b = corpus.get(pa.bodega_id)
        real = _precio_corpus(b, pa.experiencia) if b is not None else None
        total += 1
        inventadas += real is None or abs(real - pa.precio_por_persona_eur) > TOLERANCIA_PRECIO_EUR
    return total, inventadas


# --- por consulta ------------------------------------------------------------------------------

def detecta_infactible(tipo: str, motivo: Optional[str]) -> bool:
    """El sistema dijo que no se puede: `infactible` o `sin_candidatas`; o, si el motivo es una zona fuera de
    Borgoña, `zona_desconocida` ("no reconozco la zona X", ADR-0015)."""
    return tipo in DETECTAN_INFACTIBLE or (tipo == "zona_desconocida" and motivo == "zona_fuera_de_borgona")


def evaluar_consulta(consulta: Consulta, salida: Optional[SalidaSistema],
                     corpus: dict[str, Bodega]) -> EvaluacionConsulta:
    """Evalúa lo entregado contra la etiqueta (`consulta.restricciones`), no contra el perfil que extrajo el sistema:
    un error de relevamiento es un error del sistema. Sin salida, la consulta cuenta como `error`."""
    if salida is None:
        salida = SalidaSistema(consulta_id=consulta.id, sistema="", tipo="error")
    perfil = consulta.restricciones
    entregado = salida.itinerario if salida.tipo == "itinerario" else None
    faltantes = faltantes_estructurales(entregado, perfil) if entregado is not None else []
    violaciones = [v.tipo for v in verificar(entregado, perfil, corpus)] if entregado is not None else []
    total, inventadas = afirmaciones(salida, corpus)
    e = EvaluacionConsulta(consulta_id=consulta.id, escenario=consulta.escenario, infactible=consulta.infactible,
                           motivo_infactible=consulta.motivo_infactible, tipo=salida.tipo, faltantes=faltantes,
                           violaciones=violaciones, afirmaciones=total, inventadas=inventadas)
    if consulta.infactible:
        e.infactible_detectado = detecta_infactible(salida.tipo, consulta.motivo_infactible)
    else:
        e.hard_pass = entregado is not None and not faltantes and not violaciones and inventadas == 0
    return e


# --- agregados ---------------------------------------------------------------------------------

def _tasa(valores: Iterable[bool]) -> Optional[float]:
    valores = list(valores)
    return sum(valores) / len(valores) if valores else None


def hard_pass_rate(evals: Sequence[EvaluacionConsulta]) -> Optional[float]:
    """Fracción de consultas factibles con hard pass. None si no hay factibles."""
    return _tasa(e.hard_pass for e in evals if not e.infactible)


def tasa_alucinacion(evals: Sequence[EvaluacionConsulta]) -> Optional[float]:
    total = sum(e.afirmaciones for e in evals)
    return sum(e.inventadas for e in evals) / total if total else None


def infactibles_detectados(evals: Sequence[EvaluacionConsulta]) -> Optional[float]:
    return _tasa(e.infactible_detectado for e in evals if e.infactible)


def recomendaciones_por_bodega(salidas: Sequence[SalidaSistema], corpus: dict[str, Bodega]) -> dict[str, int]:
    """Veces que cada bodega del corpus aparece en un itinerario entregado (con ceros). Las inventadas no cuentan."""
    cuenta = dict.fromkeys(corpus, 0)
    for s in salidas:
        if s.tipo != "itinerario" or s.itinerario is None:
            continue
        for d in s.itinerario.dias:
            for p in d.paradas:
                if p.bodega_id in cuenta:
                    cuenta[p.bodega_id] += 1
    return cuenta


def gini(valores: Sequence[float]) -> Optional[float]:
    """Índice de Gini: 0 = todas las bodegas igual de recomendadas; cerca de 1 = todo en pocas. None si suma 0."""
    x = sorted(valores)
    n, total = len(x), sum(x)
    if total == 0:
        return None
    return 2 * sum(i * v for i, v in enumerate(x, 1)) / (n * total) - (n + 1) / n


def cobertura_corpus(salidas: Sequence[SalidaSistema], corpus: dict[str, Bodega]) -> float:
    """Fracción de las bodegas del corpus recomendadas al menos una vez."""
    cuenta = recomendaciones_por_bodega(salidas, corpus)
    return sum(1 for v in cuenta.values() if v > 0) / len(cuenta) if cuenta else 0.0


class Metricas(BaseModel):
    consultas: int
    factibles: int
    infactibles: int
    hard_pass_rate: Optional[float]
    hard_pass_por_escenario: dict[str, float]
    tasa_alucinacion: Optional[float]
    afirmaciones: int
    inventadas: int
    cobertura_corpus: float
    gini: Optional[float]
    infactibles_detectados: Optional[float]
    infactibles_detectados_por_motivo: dict[str, float]
    infactibles_detectados_representables: Optional[float]
    tipos: dict[str, int]


def resumir(consultas: Sequence[Consulta], salidas: Sequence[SalidaSistema],
            corpus: dict[str, Bodega]) -> tuple[Metricas, list[EvaluacionConsulta]]:
    """Métricas de un sistema sobre un split y la evaluación de cada consulta, en el orden de las consultas."""
    ids = {c.id for c in consultas}
    por_id: dict[str, SalidaSistema] = {}
    for s in salidas:
        if s.consulta_id not in ids:
            raise ValueError(f"salida para una consulta que no está en el split: {s.consulta_id}")
        if s.consulta_id in por_id:
            raise ValueError(f"dos salidas para la consulta {s.consulta_id}")
        por_id[s.consulta_id] = s
    evals = [evaluar_consulta(c, por_id.get(c.id), corpus) for c in consultas]

    por_escenario: dict[str, list[EvaluacionConsulta]] = defaultdict(list)
    por_motivo: dict[str, list[EvaluacionConsulta]] = defaultdict(list)
    for e in evals:
        if e.infactible:
            por_motivo[e.motivo_infactible].append(e)
        else:
            por_escenario[e.escenario].append(e)
    representables = [e for e in evals if e.infactible and e.motivo_infactible in REPRESENTABLES]
    cuenta = recomendaciones_por_bodega(list(por_id.values()), corpus)
    metricas = Metricas(
        consultas=len(evals),
        factibles=sum(not e.infactible for e in evals),
        infactibles=sum(e.infactible for e in evals),
        hard_pass_rate=hard_pass_rate(evals),
        hard_pass_por_escenario={k: hard_pass_rate(v) for k, v in sorted(por_escenario.items())},
        tasa_alucinacion=tasa_alucinacion(evals),
        afirmaciones=sum(e.afirmaciones for e in evals),
        inventadas=sum(e.inventadas for e in evals),
        cobertura_corpus=cobertura_corpus(list(por_id.values()), corpus),
        gini=gini(list(cuenta.values())),
        infactibles_detectados=infactibles_detectados(evals),
        infactibles_detectados_por_motivo={k: infactibles_detectados(v) for k, v in sorted(por_motivo.items())},
        infactibles_detectados_representables=infactibles_detectados(representables),
        tipos=dict(Counter(e.tipo for e in evals)),
    )
    return metricas, evals
