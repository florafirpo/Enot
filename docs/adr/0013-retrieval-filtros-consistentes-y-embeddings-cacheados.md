# ADR-0013: Retrieval: filtros con las reglas del verificador, BM25 propio y embeddings cacheados fuera de ClienteLLM

**Estado:** Propuesto
**Fecha:** 2026-11-24
**Decide:** Flora (propuesto por el agente en el ítem 003; spec 003)
**Complementa:** ADR-0004 (que fija la arquitectura: filtros + BM25 + embeddings + RRF c=60)

## Contexto
ADR-0004 decidió el qué del retrieval. Al implementarlo (ítem 003) aparecieron decisiones de diseño que no
estaban escritas y que cambian qué candidatas ve el planificador:
1. Qué hacen los filtros duros cuando a la ficha le falta un dato, y cómo se relacionan con el verificador.
2. Cómo se calcula BM25 y cómo se fusiona con los embeddings cuando una bodega no comparte ninguna palabra.
3. Por dónde pasan las llamadas al modelo de embeddings (ADR-0006 dice que `ClienteLLM` es la única puerta al
   LLM) y cómo se evita recalcularlas.
4. Qué variante de nDCG se reporta.

## Decisión
1. **Filtros = reglas del verificador, por visita posible.** Cada filtro aplica el mismo criterio que
   `enot/verificador.py`: un límite de la bodega solo excluye con evidencia (ADR-0009) y una necesidad del turista
   solo excluye con evidencia en contra (ADR-0012). Idioma y presupuesto se evalúan sobre cada visita posible
   (sin experiencia, o con cada experiencia) y la bodega pasa si **alguna** visita cumple las dos. Invariante:
   el filtro nunca descarta una bodega para la que existe una visita que el verificador aceptaría en esas
   reglas, y nunca deja pasar una para la que no existe. `zonas_preferidas` es filtro duro (ADR-0004 nombra la
   subzona entre los filtros duros). `motivo_exclusion` devuelve el porqué, para que el flujo (005) pueda
   explicar un pedido infactible.
2. **BM25 propio** (Okapi, k1 = 1.5, b = 0.75, IDF con +1 dentro del logaritmo). BM25 solo vota por las bodegas con
   puntaje > 0; los embeddings rankean todas. RRF con c = 60 y empates por id.
3. **Embeddings por la API compatible con OpenAI** (`EmbedderOpenAI`, modelo en `EMBEDDINGS_MODEL`, por defecto
   `text-embedding-3-small`, multilingüe; con `OPENAI_BASE_URL` sirve Ollama), **envueltos en `EmbedderConCache`**:
   un vector por hash sha256 del texto, un archivo `.npy` + `.json` por modelo en `data/indice/` (ADR-0004 punto 3).
   No pasan por `ClienteLLM`: ese cliente resuelve salidas estructuradas de chat (esquema, validación, reintento),
   que acá no aplican. El embedder es una interfaz (`Protocol`) inyectable; en tests, `tests/dobles.py::EmbedderFalso`.
4. **nDCG con ganancia lineal** (grado / log2(puesto + 1)), relevancia graduada opcional (lista = grado 1).

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Filtros con las reglas del verificador, por visita (elegida) | El planificador nunca recibe una candidata imposible ni pierde una posible; una sola regla para explicar | Hay que mantener la coherencia con el verificador (la cuida `test_filtros_coinciden_con_el_verificador`) |
| Filtros más estrictos que el verificador (sin dato = afuera) | Menos reintentos | Vuelve el sesgo contra bodegas chicas que ADR-0012 sacó del verificador |
| Cada regla por separado (no por visita) | Más simple | Deja pasar bodegas donde la visita en inglés es la cara y la barata es en alemán: el test de coherencia lo encontró |
| Reusar `verificar` como filtro (armar un itinerario de una parada) | Cero duplicación | Necesita una hora y un día concretos, y mezcla reglas de tiempo que el filtro no puede decidir sin armar el plan |
| `rank_bm25` | Probado | Dependencia nueva por 30 líneas; menos explicable en la defensa; no se puede verificar a mano igual de fácil |
| Embeddings por `ClienteLLM` | Una sola puerta, traza uniforme | Habría que agregarle un modo sin esquema ni reintento; las llamadas son pocas (se cachean) y no tienen la variabilidad de una salida de chat |
| Modelo local (sentence-transformers) | Sin clave, sin costo | Dependencia pesada (torch) para la imagen Docker; se puede usar igual vía Ollama con `OPENAI_BASE_URL` |
| nDCG con ganancia exponencial (2^g − 1) | Premia más lo muy relevante | Con relevancia binaria da lo mismo; la lineal es la de clase |

## Consecuencias
- Más fácil: el loop de reintento (005) no gasta intentos en bodegas que el filtro ya sabía imposibles; el
  retrieval se evalúa solo con `python -m eval.retrieval` (lineamientos D.5).
- Más difícil: un cambio en una regla del verificador obliga a cambiar el filtro; el test de coherencia falla si
  se olvida.
- Las llamadas de embeddings no quedan en la traza de `ClienteLLM`. El costo se acota con la caché (una llamada
  por ficha nueva o cambiada, más una por consulta). Si el reporte de costos (008) las necesita, se agrega un
  contador a `EmbedderOpenAI`.
- `zonas_preferidas` como filtro duro puede dejar cero candidatas; lo resuelve el flujo (005) explicando el motivo.
- Revisar con el set etiquetado (Recall@10 y nDCG@10): si BM25 domina por los nombres de comuna en el texto
  indexado, evaluar sacarlos del texto o bajar su peso.

## Cómo se verifica
`tests/test_retrieval.py`: `test_rrf_ejemplo_de_clase`, `test_bm25_puntaje_a_mano`, `test_filtro_*`,
`test_filtro_idioma_y_presupuesto_juntos`, `test_filtros_coinciden_con_el_verificador`,
`test_buscar_combina_bm25_y_embeddings`, `test_bm25_solo_vota_documentos_con_coincidencias`, `test_cache_*`,
`test_embedder_openai_*`, `test_con_la_muestra_real_de_datatourisme`. `tests/test_eval_retrieval.py`:
`test_ndcg_a_mano`, `test_recall_a_mano`. Mutation: `enot/retrieval.py` 440/461, `eval/retrieval.py` 174/196.
