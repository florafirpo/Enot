# ADR-0005: Distancias, horarios y costos como tools determinísticas con contratos tipados

**Estado:** Aceptado
**Fecha:** 2026-11-23
**Decide:** Flora

## Contexto
Los LLM fallan en aritmética y en cronologías (clase del 20/08). La factibilidad de un itinerario
depende justamente de sumas de tiempos, horarios de apertura y costos. Las tools son lo que el
modelo "ve": tienen que ser pocas, específicas, bien descriptas y parametrizadas (clase del 08/10).

## Decisión
Cuatro tools en `enot/tools/`, cada una con entrada y salida Pydantic y errores devueltos como valor
(no excepciones que corten el loop):

| Tool | Entrada | Salida |
|---|---|---|
| `tiempo_traslado` | dos ids de bodega, modo (auto / bici / a pie) | minutos estimados |
| `abierta_en` | id de bodega, día, hora inicio, duración | sí/no + motivo |
| `costo_experiencias` | lista de (bodega, experiencia), personas | total en EUR + ítems sin precio |
| `buscar_bodegas` | filtros + texto libre | candidatas (envuelve el retrieval, ADR-0004) |

- **Distancias:** haversine entre coordenadas × factor de ruta, con velocidad por modo. OSRM local es
  una mejora opcional detrás de la misma interfaz.
- **Idempotentes y cacheadas** (`functools.lru_cache`): llamar dos veces da lo mismo y no cuesta.
- El verificador (ADR-0003) usa estas mismas funciones: una sola fuente de verdad.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Tools propias en Python (elegida) | Testeables, explicables, sin red | Distancia aproximada (no por ruta real) |
| Google Distance Matrix | Tiempos reales | Costo, clave, términos de uso, red en los tests |
| Servidor MCP con las tools | Reutilizable desde otros agentes | Complejidad extra sin beneficio para un solo cliente |

## Consecuencias
- El factor de ruta y las velocidades son supuestos: se documentan en el código y se reportan como
  limitación.
- Exponer estas tools por MCP más adelante no cambia los contratos.

## Cómo se verifica
`tests/test_tools.py` con casos conocidos (distancia entre dos comunas de coordenadas fijas, bordes de
horario: abre 10:00 y la visita empieza 9:59). Mutation testing obligatorio sobre `enot/tools/`.
