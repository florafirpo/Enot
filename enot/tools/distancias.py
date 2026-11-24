"""Tool `tiempo_traslado` (ADR-0005): distancia en línea recta × factor de ruta, con velocidad por modo.

Supuestos (spec 001): factor de ruta 1,3; 45 km/h en auto o traslado, 15 km/h en bici, 4,5 km/h a pie.
Una ruta real (OSRM) puede reemplazar esto sin cambiar la interfaz.
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel

from ..modelos import Bodega

RADIO_TIERRA_KM = 6371.0
FACTOR_RUTA = 1.3
VELOCIDAD_KMH = {"auto": 45.0, "traslado": 45.0, "bici": 15.0, "a_pie": 4.5}


class ResultadoTraslado(BaseModel):
    minutos: Optional[int] = None
    km: Optional[float] = None
    error: Optional[str] = None


@lru_cache(maxsize=4096)
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en línea recta sobre la esfera terrestre, en km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(a))


def tiempo_traslado(corpus: dict[str, Bodega], origen_id: str, destino_id: str,
                    modo: str) -> ResultadoTraslado:
    """Minutos estimados para ir de una bodega a otra. Los errores vuelven en `error`."""
    if modo not in VELOCIDAD_KMH:
        return ResultadoTraslado(error=f"modo desconocido: {modo!r} (opciones: {', '.join(VELOCIDAD_KMH)})")
    faltan = [i for i in (origen_id, destino_id) if i not in corpus]
    if faltan:
        return ResultadoTraslado(error=f"bodega inexistente en el corpus: {', '.join(faltan)}")
    if origen_id == destino_id:
        return ResultadoTraslado(minutos=0, km=0.0)
    o, d = corpus[origen_id], corpus[destino_id]
    sin = [b.id for b in (o, d) if b.lat is None or b.lon is None]
    if sin:
        return ResultadoTraslado(error=f"sin coordenadas: {', '.join(sin)}")
    km = haversine_km(o.lat, o.lon, d.lat, d.lon) * FACTOR_RUTA
    minutos = math.ceil(km / VELOCIDAD_KMH[modo] * 60)
    return ResultadoTraslado(minutos=minutos, km=round(km, 3))
