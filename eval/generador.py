"""Generador del set de evaluación (spec 006, ADR-0007, ADR-0016).

100 consultas sintéticas de turistas armadas desde plantillas, cada una con sus restricciones etiquetadas como un
`PerfilViaje`, estratificadas por escenario (PRD 6) y con semilla fija. Se parten 60 dev / 40 test por escenario y
se separa una muestra del 20% para revisión manual (con eso se mide la tasa de error del generador).

Los pedidos infactibles se etiquetan solo si `certificado_infactible` puede probar, con código y las mismas
constantes que las tools, que son imposibles para cualquier corpus.

Uso: python -m eval.generador [--destino data/eval] [--semilla 2026] [--parafrasear]
No pisa nada: si `dev/` o `test/` ya existen, no escribe (la partición de test es inmutable, ADR-0007).
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import random
import re
import string
import sys
import unicodedata
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from corpus import config
from corpus.datatourisme import COMUNAS_ZONA
from enot.modelos import PerfilViaje, a_hora, a_minutos
from enot.retrieval import _coincide_zona
from enot.tools.distancias import FACTOR_RUTA, VELOCIDAD_KMH, haversine_km

__all__ = ["CUOTAS", "FRACCION_DEV", "FRACCION_REVISION", "SEMILLA", "VERSION_GENERADOR", "VISITA_MINIMA_MIN",
           "Consulta", "Escenario", "MotivoInfactible", "ResumenRevision", "ResumenSet", "SetExistente",
           "certificado_infactible", "conserva_anclas", "escribir_set", "generar", "main", "muestra_revision",
           "parafraseador_llm", "particionar", "tasa_error_revision"]

VERSION_GENERADOR = "006.1"
SEMILLA = 2026
FRACCION_DEV = 0.6
FRACCION_REVISION = 0.2
VISITA_MINIMA_MIN = 30

Escenario = Literal["dias", "transporte", "presupuesto", "grupo", "idioma", "accesibilidad", "infactible"]
MotivoInfactible = Literal["demasiadas_bodegas", "zonas_lejanas", "zona_fuera_de_borgona"]
EstadoParafrasis = Literal["no", "aceptada", "rechazada"]

CUOTAS: dict[str, int] = {"dias": 15, "transporte": 15, "presupuesto": 15, "grupo": 15, "idioma": 10,
                          "accesibilidad": 10, "infactible": 20}

# Comunas de referencia por subzona: centro aproximado de cada comuna (geografía pública, no bodegas). El
# certificado de zonas lejanas usa el par más cercano entre dos zonas, así que es una cota conservadora.
REFERENCIAS_ZONA: dict[str, dict[str, tuple[float, float]]] = {
    "Côte de Nuits": {"Marsannay-la-Côte": (47.271, 5.000), "Gevrey-Chambertin": (47.226, 4.968),
                      "Nuits-Saint-Georges": (47.137, 4.949), "Corgoloin": (47.087, 4.913)},
    "Côte de Beaune": {"Ladoix-Serrigny": (47.067, 4.883), "Beaune": (47.025, 4.840),
                       "Meursault": (46.978, 4.770), "Santenay": (46.910, 4.698)},
    "Hautes-Côtes": {"Villers-la-Faye": (47.100, 4.869), "Nantoux": (47.044, 4.756)},
    "Chablis y Grand Auxerrois": {"Joigny": (47.982, 3.397), "Auxerre": (47.799, 3.567),
                                  "Chablis": (47.814, 3.799), "Tonnerre": (47.856, 3.974),
                                  "Vézelay": (47.466, 3.747)},
    "Côte Chalonnaise": {"Chagny": (46.909, 4.754), "Mercurey": (46.839, 4.717), "Givry": (46.782, 4.744),
                         "Buxy": (46.714, 4.700)},
    "Mâconnais": {"Tournus": (46.562, 4.909), "Lugny": (46.474, 4.811), "Mâcon": (46.307, 4.828),
                  "Fuissé": (46.283, 4.744)},
}
assert set(REFERENCIAS_ZONA) == set(COMUNAS_ZONA), "las referencias tienen que cubrir las subzonas del corpus"

# --- vocabulario de las plantillas --------------------------------------------------------------------------------
DIAS = ("lun", "mar", "mie", "jue", "vie", "sab", "dom")
NOMBRE_DIA = {"lun": "lunes", "mar": "martes", "mie": "miércoles", "jue": "jueves", "vie": "viernes",
              "sab": "sábado", "dom": "domingo"}
CANTIDAD_DIAS = {1: ("un día", "un solo día"), 2: ("dos días", "2 días"), 3: ("tres días", "3 días")}
# (frase, ancla): el ancla es la palabra que una paráfrasis no puede perder
TRANSPORTE_FRASES = {
    "auto": (("en auto", "auto"), ("con un auto alquilado", "auto")),
    "traslado": (("con chofer", "chofer"), ("con un traslado contratado", "traslado")),
    "bici": (("en bici", "bici"), ("alquilando bicis", "bicis")),
    "a_pie": (("a pie", "a pie"), ("caminando, sin auto", "caminando")),
}
ZONA_CORTA = {"Côte de Nuits": "la Côte de Nuits", "Côte de Beaune": "la Côte de Beaune",
              "Hautes-Côtes": "las Hautes-Côtes", "Chablis y Grand Auxerrois": "Chablis",
              "Côte Chalonnaise": "la Côte Chalonnaise", "Mâconnais": "el Mâconnais"}
ZONAS_LENTAS = ("Côte de Nuits", "Côte de Beaune", "Chablis y Grand Auxerrois", "Côte Chalonnaise", "Mâconnais")
PARES_VECINOS = (("Côte de Nuits", "Côte de Beaune"), ("Côte de Beaune", "Hautes-Côtes"),
                 ("Côte de Beaune", "Côte Chalonnaise"), ("Côte Chalonnaise", "Mâconnais"),
                 ("Côte de Nuits", "Hautes-Côtes"))
ZONAS_FUERA = ("Champagne", "Jura", "Beaujolais", "Alsacia", "Burdeos")
NOMBRE_IDIOMA = {"en": "inglés", "de": "alemán", "es": "español", "it": "italiano", "pt": "portugués",
                 "fr": "francés"}
# (texto que escribe el turista, etiqueta en `preferencias`)
PREFERENCIAS = (
    ("Buscamos algo familiar, nada de casas grandes.", "domaines familiares, no casas grandes"),
    ("Nos interesan los vinos biodinámicos.", "vinos biodinámicos"),
    ("Queremos probar algún grand cru.", "probar grands crus"),
    ("Preferimos productores chicos y poco conocidos.", "productores chicos y poco conocidos"),
    ("Tomamos más que nada blancos, sobre todo chardonnay.", "vinos blancos, chardonnay"),
    ("Nos encanta el pinot noir.", "tintos de pinot noir"),
    ("Nos gustaría ver la bodega por dentro, no solo catar.", "visita a la bodega además de la cata"),
)
PRESUPUESTOS = (10, 15, 20, 25, 30, 40, 50, 60, 80, 100)
FRANJAS = (("10:00", "17:00"), ("14:00", "18:30"), ("09:00", "13:00"), ("11:00", "19:00"), ("10:30", "16:00"))

PLANTILLAS: dict[str, tuple[str, ...]] = {
    "dias": (
        "¡Hola! Quiero hacer {dias} de bodegas arrancando el {inicio}. {personas} y nos movemos {transporte}.",
        "Tengo {dias} libres desde el {inicio} para recorrer domaines en Borgoña. {personas}, {transporte}.",
        "Vamos a estar {dias} desde el {inicio}, pero solo podemos visitar bodegas de {h1} a {h2}. "
        "{personas}, {transporte}.",
    ),
    "transporte": (
        "Llegamos el {inicio} y tenemos {dias} para bodegas. {personas}; nos movemos {transporte}.",
        "¿Me armás un recorrido de {dias} por bodegas {transporte}? Empezamos el {inicio}. {personas}.",
        "{personas}. La idea es moverse {transporte}: {dias} de catas a partir del {inicio}.",
    ),
    "presupuesto": (
        "Quiero {dias} de bodegas desde el {inicio}. {personas}, {transporte}. "
        "Presupuesto: hasta {presupuesto} euros por persona en las visitas.",
        "{personas}, nos movemos {transporte}. Tenemos {dias} a partir del {inicio} y no queremos gastar más de "
        "{presupuesto} € por persona.",
        "Busco {dias} de catas empezando el {inicio}, {transporte}. {personas}. Tenemos un tope de {presupuesto} "
        "euros por cabeza para las degustaciones.",
    ),
    "grupo": (
        "Somos un grupo de {n} amigos y queremos {dias} de bodegas desde el {inicio}, {transporte}.",
        "Viaje de la oficina: vamos {n} personas, {dias} a partir del {inicio}, {transporte}.",
        "Es un viaje en grupo, {n} personas en total. Queremos recorrer domaines {dias} desde el {inicio}, "
        "{transporte}.",
    ),
    "idioma": (
        "Quiero {dias} de bodegas desde el {inicio}. {personas}, {transporte}. {idioma_frase}",
        "{personas}, nos movemos {transporte}, {dias} desde el {inicio}. {idioma_frase}",
    ),
    "accesibilidad": (
        "{personas} y una persona va en silla de ruedas. Queremos {dias} de bodegas desde el {inicio}, "
        "{transporte}.",
        "Mi papá tiene movilidad reducida, así que necesitamos lugares accesibles. {personas}, {dias} desde el "
        "{inicio}, {transporte}.",
        "Somos {n}, una persona del grupo va en silla de ruedas y las visitas tienen que ser en inglés. "
        "Queremos {dias} desde el {inicio}, {transporte}.",
    ),
}
IDIOMA_FRASES = ("Las visitas tienen que ser en {idioma}.",
                 "No hablamos francés, así que necesitamos visitas en {idioma}.")
FRASE_FRANCES = "Las visitas pueden ser en francés, lo hablamos bien."
PLANTILLAS_INFACTIBLES: dict[str, str] = {
    "demasiadas_bodegas": "Queremos visitar {n_bodegas} bodegas en un solo día, el {inicio}, entre las {h1} y "
                          "las {h2}. {personas}, {transporte}.",
    "zonas_lejanas": "Tenemos un solo día, el {inicio}, y vamos {transporte}. {personas}. Queremos visitar una "
                     "bodega en {z1} y otra en {z2} ese mismo día.",
    "zona_fuera_de_borgona": "Quiero hacer {dias} de bodegas en {zona_fuera} desde el {inicio}. {personas}, "
                             "{transporte}.",
}
FRASE_ZONA = (" Nos interesa {z}.", " La idea es recorrer {z}.")
FRASE_DOS_ZONAS = " Queremos conocer {z1} y {z2}."


class Consulta(BaseModel):
    """Una consulta del set: el mensaje del turista y su etiqueta."""
    id: str
    escenario: Escenario
    plantilla: str
    texto: str
    restricciones: PerfilViaje
    bodegas_por_dia: Optional[int] = Field(None, ge=1)
    zonas_mismo_dia: list[str] = Field(default_factory=list)
    infactible: bool = False
    motivo_infactible: Optional[MotivoInfactible] = None
    texto_plantilla: Optional[str] = None
    anclas: list[str] = Field(default_factory=list)
    parafrasis: EstadoParafrasis = "no"

    @model_validator(mode="after")
    def _motivo_si_infactible(self):
        if self.infactible != (self.motivo_infactible is not None):
            raise ValueError("una consulta infactible necesita motivo_infactible, y una factible no lo lleva")
        return self


# --- certificado de infactibilidad -------------------------------------------------------------------------------

def _zona_borgona(pedida: str) -> Optional[str]:
    return next((z for z in COMUNAS_ZONA if _coincide_zona(pedida, z)), None)


def _traslado_minimo(zona_a: str, zona_b: str, transporte: str) -> tuple[int, str, str]:
    """Minutos del traslado más corto posible entre dos zonas (par de comunas de referencia más cercano)."""
    pares = itertools.product(REFERENCIAS_ZONA[zona_a].items(), REFERENCIAS_ZONA[zona_b].items())
    km, a, b = min((haversine_km(*ca, *cb), na, nb) for (na, ca), (nb, cb) in pares)
    return round(km * FACTOR_RUTA / VELOCIDAD_KMH[transporte] * 60), a, b


def certificado_infactible(c: Consulta) -> Optional[str]:
    """Por qué el pedido es imposible para cualquier corpus, o None si el código no lo puede probar."""
    r = c.restricciones
    fuera = [z for z in r.zonas_preferidas if _zona_borgona(z) is None]
    if fuera:
        return f"{', '.join(fuera)} no es una subzona de Borgoña (fuera de alcance, PRD 8)."
    jornada = a_minutos(r.hora_fin_jornada) - a_minutos(r.hora_inicio_jornada)
    if c.bodegas_por_dia is not None and c.bodegas_por_dia * VISITA_MINIMA_MIN > jornada:
        return (f"{c.bodegas_por_dia} visitas de al menos {VISITA_MINIMA_MIN} min suman "
                f"{c.bodegas_por_dia * VISITA_MINIMA_MIN} min y la jornada tiene {jornada} min, sin contar traslados.")
    zonas = [_zona_borgona(z) for z in c.zonas_mismo_dia]
    for za, zb in itertools.combinations(dict.fromkeys(zonas), 2):
        minutos, a, b = _traslado_minimo(za, zb, r.transporte)
        if minutos > jornada:
            return (f"entre {za} y {zb} el traslado más corto ({a}–{b}) lleva {minutos} min "
                    f"({r.transporte}) y la jornada tiene {jornada} min.")
    return None


# --- generación ---------------------------------------------------------------------------------------------------

def _normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.casefold())
    return "".join(ch for ch in t if not unicodedata.combining(ch))


def _palabras(t: str) -> str:
    """Texto normalizado como secuencia de palabras; una hora (18:30) es una sola palabra."""
    return " " + " ".join(re.findall(r"\d{1,2}:\d{2}|[a-z0-9]+", _normalizar(t))) + " "


def conserva_anclas(parafrasis: str, anclas: Sequence[str]) -> bool:
    """Cada ancla aparece como palabras enteras en la paráfrasis (sin mayúsculas ni tildes)."""
    texto = _palabras(parafrasis)
    return all(_palabras(a) in texto for a in anclas)


def _clave(t: str) -> str:
    return " ".join(_normalizar(t).split())


class _Borrador:
    """Lo que arma una plantilla antes de ser una `Consulta`."""

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.slots: dict[str, str] = {}
        self.anclas_slot: dict[str, str] = {}   # ancla de cada slot: cuenta solo si la plantilla usa el slot
        self.anclas: list[str] = []             # anclas que no dependen de un slot (zonas, accesibilidad…)
        self.perfil: dict = {}
        self.extras: dict = {}

    def poner(self, slot: str, texto: str, ancla: Optional[str] = None) -> None:
        self.slots[slot] = texto
        if ancla is not None:
            self.anclas_slot[slot] = ancla

    def redactar(self, plantilla: str) -> str:
        """Llena la plantilla y deja en `anclas` las de los slots que usó, sin repetir."""
        usados = [campo for _, campo, _, _ in string.Formatter().parse(plantilla) if campo]
        self.anclas = list(dict.fromkeys([self.anclas_slot[c] for c in usados if c in self.anclas_slot]
                                         + self.anclas))
        return plantilla.format(**self.slots)

    def base(self, dias: int, inicio: str, personas: int, transporte: str) -> None:
        rng = self.rng
        self.perfil.update(cantidad_dias=dias, dia_inicio=inicio, personas=personas, transporte=transporte)
        frase_dias = rng.choice(CANTIDAD_DIAS[dias])
        self.poner("dias", frase_dias, frase_dias)
        self.poner("inicio", NOMBRE_DIA[inicio], NOMBRE_DIA[inicio])
        frase, ancla = rng.choice(TRANSPORTE_FRASES[transporte])
        self.poner("transporte", frase, ancla)
        if personas == 1:
            frase = rng.choice(("Viajo solo", "Viajo sola", "Voy sola"))
            self.poner("personas", frase, frase.casefold())
        elif personas == 2:
            self.poner("personas", rng.choice(("Somos dos", "Vamos con mi pareja, somos dos")), "dos")
        else:
            self.poner("personas", rng.choice(("Somos {n}", "Vamos {n} personas")).format(n=personas), str(personas))
        self.poner("n", str(personas), str(personas))


def _rotar(valores: Sequence, rot: int):
    """Rotación sobre los valores de la dimensión foco: varía sin repetir de más (`rot` arranca al azar)."""
    return valores[rot % len(valores)]


def _sin_articulo(zona: str) -> str:
    """'la Côte de Nuits' → 'Côte de Nuits': el ancla es el nombre, el artículo lo puede cambiar una paráfrasis."""
    corta = ZONA_CORTA[zona]
    return corta.split(" ", 1)[1] if corta.split(" ", 1)[0] in {"la", "las", "el"} else corta


def _personas_chicas(rng: random.Random) -> int:
    return rng.choice((1, 2, 2, 2, 3, 4))


def _zonas_opcionales(b: _Borrador, transporte: str) -> str:
    """Zona(s) de Borgoña opcionales; bici y a pie siempre con una sola zona."""
    rng = b.rng
    if transporte in ("bici", "a_pie"):
        zonas = [rng.choice(ZONAS_LENTAS)]
    else:
        zonas = rng.choice(([], [], [rng.choice(list(COMUNAS_ZONA))], list(rng.choice(PARES_VECINOS))))
    b.perfil["zonas_preferidas"] = zonas
    b.anclas += [_sin_articulo(z) for z in zonas]
    if not zonas:
        return ""
    if len(zonas) == 1:
        return rng.choice(FRASE_ZONA).format(z=ZONA_CORTA[zonas[0]])
    return FRASE_DOS_ZONAS.format(z1=ZONA_CORTA[zonas[0]], z2=ZONA_CORTA[zonas[1]])


def _preferencia_opcional(b: _Borrador) -> str:
    if b.rng.random() < 0.5:
        return ""
    texto, etiqueta = b.rng.choice(PREFERENCIAS)
    b.perfil["preferencias"] = etiqueta
    return " " + texto


def _factible(rng: random.Random, escenario: str, i: int, rot: int) -> tuple[str, tuple[str, _Borrador]]:
    plantillas = PLANTILLAS[escenario]
    num = i % len(plantillas)
    b = _Borrador(rng)
    dias, inicio = rng.choice((1, 2, 3)), rng.choice(DIAS)
    transporte = rng.choice(("auto", "auto", "traslado", "bici", "a_pie"))
    personas = _personas_chicas(rng)

    if escenario == "dias":
        dias = _rotar((1, 2, 3), rot)
    elif escenario == "transporte":
        transporte = _rotar(tuple(TRANSPORTE_FRASES), rot)
    elif escenario == "grupo":
        personas = rng.randint(6, 15)
        transporte = rng.choice(("auto", "traslado", "traslado"))
    elif escenario == "accesibilidad":
        # el caso del PRD es un grupo de 6; "mi papá…" implica al menos tres personas
        personas = {0: rng.choice((2, 3, 4)), 1: rng.choice((3, 4)), 2: 6}[num]
        transporte = rng.choice(("auto", "traslado"))
    b.base(dias, inicio, personas, transporte)

    if escenario == "dias" and num == 2:
        h1, h2 = rng.choice(FRANJAS)
        b.perfil.update(hora_inicio_jornada=h1, hora_fin_jornada=h2)
        b.poner("h1", h1, h1)
        b.poner("h2", h2, h2)
    elif escenario == "presupuesto":
        p = _rotar(PRESUPUESTOS, rot)
        b.perfil["presupuesto_max_por_persona"] = float(p)
        b.poner("presupuesto", str(p), str(p))
    elif escenario == "idioma":
        idioma = _rotar(tuple(NOMBRE_IDIOMA), rot)
        b.perfil["idiomas"] = [idioma]
        frase = FRASE_FRANCES if idioma == "fr" else rng.choice(IDIOMA_FRASES).format(idioma=NOMBRE_IDIOMA[idioma])
        b.poner("idioma_frase", frase, NOMBRE_IDIOMA[idioma])
    elif escenario == "accesibilidad":
        b.perfil["movilidad_reducida"] = True
        b.anclas.append("silla de ruedas" if num != 1 else "movilidad reducida")
        if num == 2:
            b.perfil["idiomas"] = ["en"]
            b.anclas.append("inglés")

    texto = b.redactar(plantillas[num])
    texto = texto[0].upper() + texto[1:]
    texto += _zonas_opcionales(b, transporte) + _preferencia_opcional(b)
    return f"{escenario}-{num + 1}", (texto, b)


def _pares_lejanos(transporte: str) -> list[tuple[str, str]]:
    jornada = a_minutos("18:30") - a_minutos("09:30")
    return [(a, b) for a, b in itertools.combinations(REFERENCIAS_ZONA, 2)
            if _traslado_minimo(a, b, transporte)[0] > jornada]


def _infactible(rng: random.Random, i: int) -> tuple[str, tuple[str, _Borrador]]:
    motivo = ("demasiadas_bodegas", "zonas_lejanas", "zona_fuera_de_borgona")[i % 3]
    b = _Borrador(rng)
    inicio, personas = rng.choice(DIAS), _personas_chicas(rng)
    b.extras.update(infactible=True, motivo_infactible=motivo)
    if motivo == "demasiadas_bodegas":
        b.base(1, inicio, personas, rng.choice(("auto", "traslado")))
        n = rng.randint(7, 10)
        h1 = rng.choice(("09:00", "10:00", "14:00", "15:00"))
        h2 = a_hora(a_minutos(h1) + 180)
        b.perfil.update(hora_inicio_jornada=h1, hora_fin_jornada=h2)
        b.extras["bodegas_por_dia"] = n
        b.poner("n_bodegas", str(n), f"{n} bodegas")
        b.poner("h1", h1, h1)
        b.poner("h2", h2, h2)
    elif motivo == "zonas_lejanas":
        transporte = rng.choice(("bici", "a_pie"))
        b.base(1, inicio, personas, transporte)
        z1, z2 = rng.sample(rng.choice(_pares_lejanos(transporte)), 2)
        b.perfil["zonas_preferidas"] = [z1, z2]
        b.extras["zonas_mismo_dia"] = [z1, z2]
        b.poner("z1", ZONA_CORTA[z1], _sin_articulo(z1))
        b.poner("z2", ZONA_CORTA[z2], _sin_articulo(z2))
    else:
        transporte = rng.choice(("auto", "auto", "traslado"))
        b.base(rng.choice((1, 2, 3)), inicio, personas, transporte)
        zona = rng.choice(ZONAS_FUERA)
        b.perfil["zonas_preferidas"] = [zona]
        b.poner("zona_fuera", zona, zona)
    if motivo != "zona_fuera_de_borgona":
        b.anclas.append("un solo día")   # está escrito en la plantilla, no en un slot
    texto = b.redactar(PLANTILLAS_INFACTIBLES[motivo])
    return f"infactible-{motivo}", (texto, b)


def _parafrasear(consultas: list[Consulta], parafraseador: Callable[[str], str]) -> list[Consulta]:
    usados = {_clave(c.texto) for c in consultas}
    salida = []
    for c in consultas:
        try:
            nuevo = parafraseador(c.texto).strip()
        except Exception:  # noqa: BLE001 - una paráfrasis fallida no corta el set: queda la plantilla
            nuevo = ""
        if nuevo and _clave(nuevo) not in usados and conserva_anclas(nuevo, c.anclas):
            usados.add(_clave(nuevo))
            salida.append(c.model_copy(update={"texto": nuevo, "texto_plantilla": c.texto, "parafrasis": "aceptada"}))
        else:
            salida.append(c.model_copy(update={"parafrasis": "rechazada"}))
    return salida


def generar(semilla: int = SEMILLA, parafraseador: Optional[Callable[[str], str]] = None) -> list[Consulta]:
    """Las 100 consultas, en orden de escenario. Sin parafraseador, misma semilla → mismo set."""
    rng = random.Random(semilla)
    consultas: list[Consulta] = []
    vistos: set[str] = set()
    for escenario, cuota in CUOTAS.items():
        inicio_rotacion = rng.randrange(1000)
        for i in range(cuota):
            for _ in range(200):
                plantilla, (texto, b) = _infactible(rng, i) if escenario == "infactible" else \
                    _factible(rng, escenario, i, inicio_rotacion + i)
                if _clave(texto) not in vistos:
                    break
            else:  # pragma: no cover - con estas plantillas no pasa; si pasa, mejor fallar que repetir
                raise RuntimeError(f"no pude generar una consulta nueva para {escenario}")
            vistos.add(_clave(texto))
            consultas.append(Consulta(id=f"q{len(consultas) + 1:03d}", escenario=escenario, plantilla=plantilla,
                                      texto=texto, restricciones=PerfilViaje(**b.perfil), anclas=b.anclas,
                                      **b.extras))
    if parafraseador is not None:
        consultas = _parafrasear(consultas, parafraseador)
    return consultas


# --- partición y muestra ------------------------------------------------------------------------------------------

def _por_escenario(consultas: Sequence[Consulta]) -> dict[str, list[Consulta]]:
    return {e: [c for c in consultas if c.escenario == e] for e in CUOTAS}


def particionar(consultas: Sequence[Consulta], semilla: int = SEMILLA) -> tuple[list[Consulta], list[Consulta]]:
    """(dev, test) estratificado: en cada escenario, el 60% a dev; cada partición ordenada por id."""
    rng = random.Random(semilla)
    dev, test = [], []
    for grupo in _por_escenario(consultas).values():
        grupo = list(grupo)
        rng.shuffle(grupo)
        corte = round(len(grupo) * FRACCION_DEV)
        dev += grupo[:corte]
        test += grupo[corte:]
    return sorted(dev, key=lambda c: c.id), sorted(test, key=lambda c: c.id)


def muestra_revision(dev: Sequence[Consulta], test: Sequence[Consulta],
                     semilla: int = SEMILLA) -> list[tuple[str, Consulta]]:
    """El 20% de cada escenario, repartido entre dev y test en proporción 60/40, para revisar a mano."""
    rng = random.Random(semilla)
    pdev, ptest = _por_escenario(dev), _por_escenario(test)
    muestra: list[tuple[str, Consulta]] = []
    for e in CUOTAS:
        k = round((len(pdev[e]) + len(ptest[e])) * FRACCION_REVISION)
        k_dev = round(k * FRACCION_DEV)
        muestra += [("dev", c) for c in rng.sample(pdev[e], k_dev)]
        muestra += [("test", c) for c in rng.sample(ptest[e], k - k_dev)]
    return sorted(muestra, key=lambda pc: pc[1].id)


# --- escritura ----------------------------------------------------------------------------------------------------

class SetExistente(Exception):
    """El set ya fue generado: no se pisa (ADR-0007)."""


class ResumenSet(BaseModel):
    dev: int
    test: int
    revision: int
    parafrasis: dict[str, int]


COLUMNAS_REVISION = ["id", "particion", "escenario", "plantilla", "texto", "restricciones", "bodegas_por_dia",
                     "zonas_mismo_dia", "infactible", "motivo_infactible", "correcta", "comentario"]


def _jsonl(ruta: Path, consultas: Sequence[Consulta]) -> None:
    ruta.parent.mkdir(parents=True)
    ruta.write_text("".join(c.model_dump_json() + "\n" for c in consultas), encoding="utf-8")


def escribir_set(destino: Path, semilla: int = SEMILLA,
                 parafraseador: Optional[Callable[[str], str]] = None) -> ResumenSet:
    """Genera y escribe dev, test, la planilla de revisión y la configuración. Todo o nada."""
    destino = Path(destino)
    existentes = [p for p in ("dev", "test") if (destino / p).exists()]
    if existentes:
        raise SetExistente(f"ya existe {', '.join(str(destino / p) for p in existentes)}: el set no se regenera "
                           f"(la partición de test es inmutable, ADR-0007).")
    consultas = generar(semilla, parafraseador)
    dev, test = particionar(consultas, semilla)
    muestra = muestra_revision(dev, test, semilla)

    _jsonl(destino / "dev" / "consultas.jsonl", dev)
    _jsonl(destino / "test" / "consultas.jsonl", test)
    with open(destino / "revision_manual.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS_REVISION)
        w.writeheader()
        for particion, c in muestra:
            w.writerow({"id": c.id, "particion": particion, "escenario": c.escenario, "plantilla": c.plantilla,
                        "texto": c.texto, "restricciones": c.restricciones.model_dump_json(),
                        "bodegas_por_dia": c.bodegas_por_dia or "", "zonas_mismo_dia": "; ".join(c.zonas_mismo_dia),
                        "infactible": "sí" if c.infactible else "no", "motivo_infactible": c.motivo_infactible or "",
                        "correcta": "", "comentario": ""})
    cuenta = Counter(c.parafrasis for c in consultas)
    parafrasis = {k: cuenta[k] for k in ("no", "aceptada", "rechazada")}
    meta = {"version": VERSION_GENERADOR, "semilla": semilla, "cuotas": CUOTAS,
            "fraccion_dev": FRACCION_DEV, "fraccion_revision": FRACCION_REVISION,
            "visita_minima_min": VISITA_MINIMA_MIN,
            "conteos": {"dev": dict(Counter(c.escenario for c in dev)), "test": dict(Counter(c.escenario for c in test))},
            "infactibles": {"dev": sum(c.infactible for c in dev), "test": sum(c.infactible for c in test)},
            "parafrasis": parafrasis}
    (destino / "generacion.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ResumenSet(dev=len(dev), test=len(test), revision=len(muestra), parafrasis=parafrasis)


# --- tasa de error del generador (lo completa Flora en la planilla) -----------------------------------------------

class ResumenRevision(BaseModel):
    revisadas: int
    con_error: int
    tasa_error: Optional[float]
    por_escenario: dict[str, dict[str, int]]


_SI = {"si", "s", "ok", "1", "true"}
_NO = {"no", "n", "0", "false"}


def tasa_error_revision(ruta_csv: Path) -> ResumenRevision:
    """Tasa de error del generador según la columna `correcta` (sí/no; vacía = sin revisar)."""
    revisadas = con_error = 0
    por: dict[str, dict[str, int]] = {}
    with open(ruta_csv, encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            valor = _normalizar((fila.get("correcta") or "").strip())
            if not valor:
                continue
            if valor not in _SI | _NO:
                raise ValueError(f"{fila.get('id')}: 'correcta' tiene que ser sí, no o vacía (vino {fila['correcta']!r})")
            error = valor in _NO
            e = por.setdefault(fila.get("escenario", ""), {"revisadas": 0, "con_error": 0})
            e["revisadas"] += 1
            e["con_error"] += error
            revisadas += 1
            con_error += error
    return ResumenRevision(revisadas=revisadas, con_error=con_error,
                           tasa_error=con_error / revisadas if revisadas else None, por_escenario=por)


# --- paráfrasis con LLM (opcional) ----------------------------------------------------------------------------------

PROMPT_PARAFRASIS = """Reescribí el pedido de un turista hispanohablante que quiere visitar bodegas en Borgoña, como \
lo escribiría otra persona en un chat (español rioplatense, informal, una sola línea).
Reglas: conservá exactamente cada dato: todo número tal cual está escrito (en cifras o en letras), los días de la \
semana, las horas, los nombres de zonas y lugares, el idioma, el medio de transporte y cuántas personas viajan. No \
agregues datos ni restricciones nuevas y no saques ninguna."""


class SalidaParafrasis(BaseModel):
    texto: str


def parafraseador_llm(cliente) -> Callable[[str], str]:
    """Parafraseador que usa `ClienteLLM.estructurado` (ADR-0006). Las anclas las controla `generar`."""
    def parafrasear(texto: str) -> str:
        return cliente.estructurado(PROMPT_PARAFRASIS, f"Pedido original:\n{texto}", SalidaParafrasis).objeto.texto
    return parafrasear


def _cliente_llm():  # pragma: no cover - necesita clave; en tests se inyecta una fábrica
    from corpus.llm import ClienteLLM
    return ClienteLLM()


def main(argv: Optional[list[str]] = None, crear_cliente: Optional[Callable[[], object]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m eval.generador", description=__doc__.splitlines()[0])
    ap.add_argument("--destino", type=Path, default=None, help="carpeta del set (por defecto data/eval)")
    ap.add_argument("--semilla", type=int, default=SEMILLA)
    ap.add_argument("--parafrasear", action="store_true", help="reescribir cada consulta con el LLM de .env")
    args = ap.parse_args(argv)
    destino = args.destino or config.DATA / "eval"
    parafraseador = None
    if args.parafrasear:
        parafraseador = parafraseador_llm((crear_cliente or _cliente_llm)())
    try:
        r = escribir_set(destino, args.semilla, parafraseador)
    except SetExistente as e:
        print(f"[generador] {e}", file=sys.stderr)
        return 1
    print(f"[generador] {r.dev} consultas en dev, {r.test} en test, {r.revision} para revisión manual en {destino} "
          f"(semilla {args.semilla}, paráfrasis {r.parafrasis}).")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
