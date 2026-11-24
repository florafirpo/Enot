"""Dobles para los tests de retrieval (ítem 003). Sin red, sin modelos, determinísticos."""
from __future__ import annotations

import hashlib
import re
import unicodedata

import numpy as np


def _tokens(texto: str) -> list[str]:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]+", t)


class EmbedderFalso:
    """Embedder determinístico: bolsa de palabras hasheada (md5) a `dim` dimensiones, normalizada.

    `sinonimos` mapea palabras a una forma canónica antes de hashear: así se puede simular que el embedder
    "entiende" que dos palabras distintas significan lo mismo (lo que BM25 no ve). Registra cada llamada.
    """

    def __init__(self, sinonimos: dict[str, str] | None = None, dim: int = 256, nombre: str = "falso"):
        self.sinonimos = sinonimos or {}
        self.dim = dim
        self.nombre = nombre
        self.llamadas: list[list[str]] = []

    def embeber(self, textos: list[str]) -> np.ndarray:
        self.llamadas.append(list(textos))
        m = np.zeros((len(textos), self.dim))
        for i, texto in enumerate(textos):
            for tok in _tokens(texto):
                tok = self.sinonimos.get(tok, tok)
                m[i, int(hashlib.md5(tok.encode()).hexdigest(), 16) % self.dim] += 1.0
            norma = np.linalg.norm(m[i])
            if norma:
                m[i] /= norma
        return m
