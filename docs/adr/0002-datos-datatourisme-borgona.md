# ADR-0002: Corpus desde DATAtourisme (Borgoña) en lugar de scrapear bodegas de Mendoza

**Estado:** Aceptado (pendiente de validación de la cátedra)
**Fecha:** 2026-11-23
**Decide:** Flora

## Contexto
La propuesta original era Mendoza, pero no existe una base abierta con la oferta turística de sus
bodegas: había que scrapear ~200 webs heterogéneas. El grupo se disolvió y el plazo es el 3/12.
La consigna exige datos verificados, con licencia y volumen identificados.

## Decisión
La región del MVP es Borgoña y la fuente principal es el CSV regional de DATAtourisme
(Bourgogne-Franche-Comté, Licence Ouverte 2.0), filtrado a bodegas (`core:Cellar` y proveedores de
degustación que mencionan vino) en los departamentos 21, 71, 89 y 58. Las webs de los domaines quedan
como enriquecimiento opcional.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| DATAtourisme Borgoña (elegida) | Oficial, abierta, actualización diaria, coordenadas incluidas, sin scraping | Cambia la región; descripciones en francés y en texto libre; precios y horarios a veces ausentes |
| Mendoza, scraping de webs | Contexto local, relato original | Semanas de trabajo; calidad desigual; sin licencia clara |
| Mendoza, OpenStreetMap + atributos sintéticos | Mantiene la región | Atributos inventados: debilita la evaluación y el criterio de datos verificados |

## Consecuencias
- El esquema de la ficha (`corpus/schema.py`) es independiente de la región: volver a Mendoza implica
  solo otra fuente de semilla (`python -m corpus seed`).
- La extracción con LLM pasa a ser parte del núcleo: convierte descripciones en francés a fichas.
- Riesgo de completitud baja en precio y horario: se mide en el EDA (umbral 60%, PRD sección 7).

## Cómo se verifica
`tests/test_datatourisme.py` cubre el filtrado, la asignación de subzona y la deduplicación sobre un
CSV simulado con el formato documentado. El EDA (`python -m corpus eda`) reporta la completitud real.
