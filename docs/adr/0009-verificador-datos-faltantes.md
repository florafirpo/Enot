# ADR-0009: Qué hace el verificador cuando a la ficha le falta un dato

**Estado:** Propuesto
**Fecha:** 2026-11-24
**Decide:** Flora (propuesto por el agente nocturno en la spec 002; queda a confirmar en el PR)

## Contexto
El verificador (ADR-0003) es el criterio del loop de reintento y del *hard pass rate* (ADR-0007). Muchas
fichas del corpus no publican horario, capacidad, precio, accesibilidad o idiomas, sobre todo las de
bodegas chicas. Para cada restricción hay que decidir si "no se sabe" cuenta como violación. Si se decide
mal hacia un lado, el sistema descarta a los productores chicos (lo contrario de lo que busca el PRD); si
se decide mal hacia el otro, le garantiza al turista algo que no sabemos (un dato inventado).

## Decisión
Una regla única, según de quién es la restricción:
- **Límite de la bodega** (horario, coordenadas para el traslado, capacidad, precio): solo viola si hay
  evidencia del límite. Sin dato, no se marca.
- **Necesidad del turista** (accesibilidad, restricción alimentaria, idioma): solo se cumple con evidencia
  positiva. `None` o lista vacía cuenta como violación.

Además, nombrar una experiencia que la bodega no publica es una violación propia
(`experiencia_inexistente`): si no, la tool de costos la saltea y el presupuesto se puede esquivar.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Regla según de quién es la restricción (elegida) | Una sola regla explicable; protege al turista donde el error es caro (silla de ruedas, celiaquía) y no castiga la falta de datos donde el error es barato (un horario a confirmar) | Bodegas sin idiomas publicados quedan afuera de cualquier pedido con idioma, aunque en Borgoña casi todas hablen francés |
| Todo dato faltante es violación | Máxima seguridad | Con la completitud actual del corpus casi ningún itinerario pasaría; sesga hacia bodegas grandes |
| Ningún dato faltante es violación | Más itinerarios válidos | El sistema afirmaría accesibilidad o dieta sin evidencia: es una alucinación con otro nombre |
| Un tercer estado "a confirmar" (advertencias) | Más información para la respuesta | Más superficie; no cambia el criterio de pase. Se puede agregar después sin romper `Violacion` |

## Consecuencias
- El *hard pass rate* mide factibilidad "con lo que sabemos". La respuesta al turista debería decir
  "horario a confirmar" cuando la bodega no lo publica (ítem 004).
- Si la completitud de `idiomas` resulta muy baja en el EDA, conviene revisar la regla para el francés.
- Revisar con los resultados de dev (ítem 007): cuántos itinerarios fallan solo por datos faltantes.

## Cómo se verifica
`tests/test_verificador.py`: `test_sin_horario_publicado_no_es_violacion`, `test_capacidad_no_publicada`,
`test_sin_coordenadas_y_sin_superposicion_no_es_violacion`, `test_presupuesto_no_cuenta_precios_sin_eur`
(límites sin dato → no viola) y `test_accesibilidad_no_declarada[None]`, `test_dieta_None_es_violacion`,
`test_idioma_sin_datos_es_violacion` (necesidades sin dato → viola).
