"""Retrieval híbrido de candidatas (spec 003, ADR-0004, ADR-0013).

1. Filtros duros por metadatos (código): misma regla que el verificador para lo que no se sabe — un límite de la
   bodega solo excluye con evidencia (ADR-0009); una necesidad del turista solo excluye con evidencia en contra
   (ADR-0012). Así el filtro nunca descarta una bodega que el verificador aceptaría.
2. Sobre las que quedan, BM25 (palabras exactas: comunas, appellations) y embeddings (conceptos, otro idioma).
3. Los dos rankings se combinan con Reciprocal Rank Fusion (c = 60): se suman rankings, no puntajes.

El embedder es inyectable: en tests, uno falso y determinístico; en uso real, `EmbedderOpenAI` envuelto en
`EmbedderConCache` (data/indice/).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Optional, Protocol

import numpy as np
from pydantic import BaseModel

from corpus import config
from corpus.utils import slugify

from .modelos import Bodega, PerfilViaje
from .verificador import IDIOMA_BASE

__all__ = ["BM25", "Candidata", "Embedder", "EmbedderConCache", "EmbedderOpenAI", "Indice",
           "consulta_desde_perfil", "dias_del_viaje", "filtrar", "motivo_exclusion", "rrf", "texto_bodega",
           "tokenizar"]

DIAS = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
C_RRF = 60


# --- texto -------------------------------------------------------------------------------

def _plano(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()


def tokenizar(texto: str) -> list[str]:
    """Minúsculas, sin tildes, secuencias alfanuméricas: 'Mâcon-Villages' → ['macon', 'villages']."""
    return re.findall(r"[a-z0-9]+", _plano(texto))


def texto_bodega(b: Bodega) -> str:
    """Lo que se indexa de cada bodega: nombre, lugar, perfil, descripción, vinos y experiencias."""
    partes = [b.nombre, b.zona, b.comuna]
    if b.perfil != "no_informado":
        partes.append(b.perfil)
    partes.append(b.descripcion_breve or "")
    partes += b.vinos_o_varietales_destacados
    for e in b.experiencias:
        partes += [e.nombre, e.tipo, e.incluye or ""]
    return "\n".join(p for p in partes if p)


def consulta_desde_perfil(perfil: PerfilViaje) -> str:
    """Texto de búsqueda cuando no hay consulta explícita: preferencias y zonas del perfil."""
    return " ".join(p for p in [perfil.preferencias or "", *perfil.zonas_preferidas] if p).strip()


# --- BM25 --------------------------------------------------------------------------------

class BM25:
    """Okapi BM25 sobre documentos ya tokenizados (clase del 01/10)."""

    def __init__(self, documentos: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.frecuencias = [Counter(d) for d in documentos]
        self.largos = [len(d) for d in documentos]
        self.n = len(documentos)
        self.largo_medio = (sum(self.largos) / self.n) if self.n else 0.0
        self.df: Counter[str] = Counter(t for f in self.frecuencias for t in f)

    def idf(self, termino: str) -> float:
        """ln((N - n + 0.5) / (n + 0.5) + 1): rareza del término; nunca negativa."""
        n = self.df.get(termino, 0)
        return math.log((self.n - n + 0.5) / (n + 0.5) + 1)

    def puntajes(self, consulta: list[str]) -> list[float]:
        res = [0.0] * self.n
        for t in consulta:
            if t not in self.df:
                continue
            idf = self.idf(t)
            for i, f in enumerate(self.frecuencias):
                tf = f.get(t, 0)
                if tf:
                    norma = 1 - self.b + self.b * self.largos[i] / self.largo_medio
                    res[i] += idf * tf * (self.k1 + 1) / (tf + self.k1 * norma)
        return res


# --- RRF ---------------------------------------------------------------------------------

def rrf(rankings: Sequence[Sequence[str]], c: int = C_RRF, top: Optional[int] = None) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion: cada ranking suma 1 / (c + puesto) a los documentos de su top.

    Devuelve (id, puntaje) de mayor a menor; los empates se ordenan por id para que sea determinístico.
    """
    puntajes: dict[str, float] = {}
    for ranking in rankings:
        for puesto, doc in enumerate(ranking[:top] if top is not None else ranking, start=1):
            puntajes[doc] = puntajes.get(doc, 0.0) + 1 / (c + puesto)
    return sorted(puntajes.items(), key=lambda x: (-x[1], x[0]))


# --- filtros duros -----------------------------------------------------------------------

def dias_del_viaje(perfil: PerfilViaje) -> list[str]:
    i = DIAS.index(perfil.dia_inicio)
    return [DIAS[(i + n) % 7] for n in range(perfil.cantidad_dias)]


def _en_eur(e) -> bool:
    return e.precio_por_persona is not None and e.moneda == "EUR"


def _visitas(b: Bodega) -> list[tuple[list[str], float]]:
    """Cada visita posible como (idiomas que valen, costo conocido por persona), con las reglas del verificador:
    sin experiencia valen los idiomas de la bodega y el precio de la experiencia más barata en EUR; con una
    experiencia, sus idiomas (o los de la bodega) y su precio si está en EUR (si no, no se sabe → 0)."""
    con_precio = [e.precio_por_persona for e in b.experiencias if _en_eur(e)]
    visitas = [(b.idiomas, min(con_precio) if con_precio else 0.0)]
    visitas += [(e.idiomas or b.idiomas, e.precio_por_persona if _en_eur(e) else 0.0) for e in b.experiencias]
    return visitas


def _coincide_zona(pedida: str, zona: str) -> bool:
    """Todas las palabras de la zona pedida están en la zona de la bodega: 'Chablis' → 'Chablis y Grand Auxerrois'.

    Las zonas del corpus tienen nombres largos y el perfil lo llena un LLM o el turista con texto libre."""
    palabras = set(tokenizar(pedida))
    return bool(palabras) and palabras <= set(tokenizar(zona))


def motivo_exclusion(b: Bodega, perfil: PerfilViaje) -> Optional[str]:
    """Por qué el perfil descarta la bodega, o None si pasa los filtros duros."""
    evitar = {x.casefold() for x in perfil.bodegas_evitar}
    if b.id.casefold() in evitar or b.nombre.casefold() in evitar:
        return "el turista pidió evitarla"
    if perfil.zonas_preferidas and not any(_coincide_zona(z, b.zona) for z in perfil.zonas_preferidas):
        return f"zona {b.zona or 'sin zona'} fuera de las pedidas"
    if b.capacidad_max_grupo is not None and perfil.personas > b.capacidad_max_grupo:
        return f"recibe hasta {b.capacidad_max_grupo} personas y el grupo es de {perfil.personas}"
    if perfil.movilidad_reducida and b.accesible_movilidad_reducida is False:
        return "declara no ser accesible para movilidad reducida"
    dias = dias_del_viaje(perfil)
    if b.horarios and not any(d in h.dias for h in b.horarios for d in dias):
        return f"no abre ninguno de los días del viaje ({', '.join(dias)})"

    # idioma y presupuesto dependen de qué visita se elija: tiene que existir una que cumpla las dos
    pedidos = {i.casefold() for i in perfil.idiomas}
    tope = perfil.presupuesto_max_por_persona

    def idioma_ok(idiomas: list[str]) -> bool:
        return not pedidos or bool(pedidos & IDIOMA_BASE) or not idiomas or bool(pedidos & {i.casefold() for i in idiomas})

    def precio_ok(costo: float) -> bool:
        return tope is None or costo <= tope

    visitas = _visitas(b)
    if not any(idioma_ok(i) for i, _ in visitas):
        return f"publica idiomas y no incluye {', '.join(perfil.idiomas)}"
    if not any(precio_ok(c) for _, c in visitas):
        minimo = min(c for _, c in visitas)
        return f"la experiencia más barata cuesta {minimo:.2f} EUR y el máximo es {tope:.2f} EUR por persona"
    if not any(idioma_ok(i) and precio_ok(c) for i, c in visitas):
        return f"ninguna visita cumple a la vez el idioma ({', '.join(perfil.idiomas)}) y el máximo de {tope:.2f} EUR"
    return None


def filtrar(bodegas: Iterable[Bodega], perfil: Optional[PerfilViaje]) -> list[Bodega]:
    """Las bodegas que pasan los filtros duros del perfil, en el orden recibido. Sin perfil, todas."""
    return [b for b in bodegas if perfil is None or motivo_exclusion(b, perfil) is None]


# --- embeddings --------------------------------------------------------------------------

class Embedder(Protocol):
    nombre: str

    def embeber(self, textos: list[str]) -> np.ndarray: ...


class EmbedderOpenAI:
    """Embeddings por la API compatible con OpenAI (OpenAI, Ollama, vLLM vía OPENAI_BASE_URL).

    Modelo en `.env` (EMBEDDINGS_MODEL); por defecto uno multilingüe. El cliente es inyectable (tests sin red).
    """

    def __init__(self, modelo: Optional[str] = None, cliente=None):
        self.nombre = modelo or os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small")
        self._cliente = cliente

    def embeber(self, textos: list[str]) -> np.ndarray:
        if not textos:
            return np.zeros((0, 0))
        if self._cliente is None:
            from openai import OpenAI

            self._cliente = OpenAI(base_url=config.OPENAI_BASE_URL)
        r = self._cliente.embeddings.create(model=self.nombre, input=list(textos))
        return np.array([d.embedding for d in sorted(r.data, key=lambda d: d.index)], dtype=float)


class EmbedderConCache:
    """Envuelve otro embedder y guarda cada vector por hash del texto, un archivo por modelo.

    `<carpeta>/embeddings_<modelo>.npy` (matriz) + `claves_<modelo>.json` (hash de cada fila). Si cambia una
    ficha, solo se recalcula esa.
    """

    def __init__(self, embedder: Embedder, carpeta: Optional[Path] = None):
        self.embedder = embedder
        self.nombre = embedder.nombre
        self.carpeta = Path(carpeta) if carpeta else config.DATA / "indice"
        slug = slugify(self.nombre)
        self._npy = self.carpeta / f"embeddings_{slug}.npy"
        self._json = self.carpeta / f"claves_{slug}.json"
        self._claves: list[str] = []
        self._matriz: Optional[np.ndarray] = None
        if self._npy.exists() and self._json.exists():
            self._claves = json.loads(self._json.read_text(encoding="utf-8"))
            self._matriz = np.load(self._npy)
        self._fila = {k: i for i, k in enumerate(self._claves)}

    @staticmethod
    def _clave(texto: str) -> str:
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()

    def embeber(self, textos: list[str]) -> np.ndarray:
        claves = [self._clave(t) for t in textos]
        faltan = list(dict.fromkeys(k for k in claves if k not in self._fila))
        if faltan:
            texto_de = dict(zip(claves, textos, strict=True))
            nuevos = self.embedder.embeber([texto_de[k] for k in faltan])
            self._matriz = nuevos if self._matriz is None else np.vstack([self._matriz, nuevos])
            for k in faltan:
                self._fila[k] = len(self._claves)
                self._claves.append(k)
            self.carpeta.mkdir(parents=True, exist_ok=True)
            np.save(self._npy, self._matriz)
            self._json.write_text(json.dumps(self._claves), encoding="utf-8")
        if not claves:
            return np.zeros((0, 0))
        return self._matriz[[self._fila[k] for k in claves]]


# --- índice ------------------------------------------------------------------------------

class Candidata(BaseModel):
    bodega_id: str
    score: float
    puesto_bm25: Optional[int] = None
    puesto_embeddings: Optional[int] = None


def _normalizar(m: np.ndarray) -> np.ndarray:
    normas = np.linalg.norm(m, axis=1, keepdims=True)
    return m / np.where(normas == 0, 1, normas)


class Indice:
    """Índice en memoria sobre el corpus: tokens para BM25 y una matriz de embeddings normalizada."""

    def __init__(self, bodegas: Iterable[Bodega], embedder: Embedder):
        self.bodegas = list(bodegas)
        self.embedder = embedder
        textos = [texto_bodega(b) for b in self.bodegas]
        self._tokens = [tokenizar(t) for t in textos]
        self._vectores = _normalizar(embedder.embeber(textos)) if textos else np.zeros((0, 0))

    def zonas_desconocidas(self, perfil: PerfilViaje) -> list[str]:
        """Zonas pedidas que no coinciden con ninguna zona del corpus: el flujo las informa ("no reconozco la zona
        X") en vez de presentar el pedido como infactible."""
        zonas = {b.zona for b in self.bodegas}
        return [z for z in perfil.zonas_preferidas if not any(_coincide_zona(z, zona) for zona in zonas)]

    def buscar(self, perfil: Optional[PerfilViaje], k: int = 10, consulta: Optional[str] = None,
               top_por_metodo: Optional[int] = None) -> list[Candidata]:
        """Filtros duros → BM25 y embeddings sobre las candidatas → RRF → las k mejores."""
        if consulta is None:
            consulta = consulta_desde_perfil(perfil) if perfil is not None else ""
        pos = [i for i, b in enumerate(self.bodegas) if perfil is None or motivo_exclusion(b, perfil) is None]
        if not pos:
            return []
        ids = [self.bodegas[i].id for i in pos]

        bm = BM25([self._tokens[i] for i in pos]).puntajes(tokenizar(consulta))
        orden_bm = sorted((j for j in range(len(pos)) if bm[j] > 0), key=lambda j: (-bm[j], ids[j]))
        ranking_bm = [ids[j] for j in orden_bm]

        q = _normalizar(np.atleast_2d(self.embedder.embeber([consulta])))[0]
        sim = self._vectores[pos] @ q
        ranking_emb = [ids[j] for j in sorted(range(len(pos)), key=lambda j: (-sim[j], ids[j]))]

        puestos_bm = {d: n for n, d in enumerate(ranking_bm, 1)}
        puestos_emb = {d: n for n, d in enumerate(ranking_emb, 1)}
        fusion = dict(rrf([ranking_bm, ranking_emb], top=top_por_metodo))
        orden = sorted(ids, key=lambda d: (-fusion.get(d, 0.0), d))
        return [Candidata(bodega_id=d, score=fusion.get(d, 0.0), puesto_bm25=puestos_bm.get(d),
                          puesto_embeddings=puestos_emb.get(d)) for d in orden[:k]]
