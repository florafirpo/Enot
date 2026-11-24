# ADR-0004: Retrieval híbrido (filtros + BM25 + embeddings con RRF), evaluado por separado

**Estado:** Aceptado
**Fecha:** 2026-11-23
**Decide:** Flora

## Contexto
El corpus es chico (del orden de cientos de bodegas) y estable: se regenera cuando se corre el
pipeline, no en cada consulta. Las consultas mezclan restricciones duras (subzona, precio, días
abiertos, accesibilidad) con preferencias semánticas ("familiar", "biodinámico", "grands crus") y
nombres propios (comunas, appellations), donde importan las coincidencias exactas.
La consigna pide evaluar el retrieval por separado de la generación.

## Decisión
1. **Filtros duros por metadatos** sobre las fichas (código).
2. Sobre las candidatas, **BM25** y **embeddings** en paralelo, combinados con
   **Reciprocal Rank Fusion** (c = 60).
3. Índice local en archivos (embeddings en `.npy` + metadatos en JSON); sin base vectorial externa.
4. El re-ranking con LLM queda como mejora opcional si Recall@10 no alcanza.
5. Evaluación propia: Recall@10 y nDCG@10 contra 30 consultas con bodegas relevantes etiquetadas.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Híbrido + RRF (elegida) | Captura nombres exactos y conceptos; RRF no exige calibrar escalas | Dos índices que mantener |
| Solo embeddings | Simple | Pierde coincidencias exactas (comunas, appellations) |
| Solo BM25 | Barato, explicable | No entiende sinónimos ni descripciones en otro idioma |
| Base vectorial (Chroma, pgvector) | Escala | Sobreingeniería para cientos de documentos; otro servicio que levantar |

## Consecuencias
- Con cientos de documentos, la búsqueda exhaustiva en memoria tarda milisegundos: la latencia la
  domina el LLM, no el retrieval.
- Si el corpus creciera a decenas de miles, se reemplaza el índice local por una base vectorial sin
  cambiar la interfaz `buscar(perfil, k) -> list[Candidata]`.
- El modelo de embeddings tiene que ser multilingüe (consultas en español, textos en francés).

## Cómo se verifica
`tests/test_retrieval.py` (RRF, filtros) con documentos sintéticos; `eval/retrieval.py` reporta
Recall@10 y nDCG@10 sobre el set etiquetado.
