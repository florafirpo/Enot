# BACKLOG

Entrega y exposición: **3/12/2026**. El agente nocturno toma el **primer ítem `[ ]`** de la lista,
lo pasa a `[~]` en su rama y abre un PR. Flora lo pasa a `[x]` al aprobar el PR.
Estados: `[ ]` pendiente · `[~]` en PR · `[x]` aprobado · `[!]` bloqueado (ver PR).

Cada ítem respeta los ADRs. Si un ítem necesita algo de un ítem anterior que todavía no está aprobado,
el agente trabaja sobre la rama de ese PR y lo aclara en la descripción.

---

- [ ] **001 · Modelos de dominio y tools determinísticas** (noche del 23/11)
  - `enot/modelos.py`: `Bodega` (se construye desde una línea de `fichas.jsonl` + `_meta`), `PerfilViaje`,
    `Parada`, `DiaItinerario`, `Itinerario`. Pydantic, con validaciones (horas HH:MM, días válidos).
  - `enot/corpus_local.py`: carga `data/fichas/fichas.jsonl` → `dict[id, Bodega]`.
  - `enot/tools/`: `tiempo_traslado`, `abierta_en`, `costo_experiencias` (ADR-0005). Errores como valor.
  - Fixture SINTÉTICA `tests/fixtures/fichas_sinteticas.jsonl` (6–10 bodegas inventadas, marcadas como tales,
    con coordenadas en Borgoña y casos borde: sin horario, sin precio, cerrada los lunes).
  - Aceptación: tests de bordes (abre 10:00 y la visita empieza 9:59; cruza el cierre por 1 minuto; bodega
    sin coordenadas). Mutation testing sobre `enot/tools/` ≥ 80%.

- [ ] **002 · Verificador de restricciones duras** (24/11)
  - `enot/verificador.py`: `verificar(itinerario, perfil, corpus) -> list[Violacion]` con tipos: bodega
    inexistente, cerrada en ese horario, traslado imposible (no entra entre paradas), jornada excedida,
    presupuesto excedido, grupo mayor a capacidad, restricción alimentaria o de accesibilidad no declarada,
    idioma no disponible. Cada violación trae un mensaje accionable para el planificador.
  - Usa las tools de 001 (una sola fuente de verdad).
  - Aceptación: por cada tipo, un test que lo detecta y uno que no lo confunde. Mutation ≥ 80%.

- [ ] **003 · Retrieval híbrido y su evaluación** (25/11)
  - `enot/retrieval.py`: filtros duros por perfil + BM25 + embeddings + RRF (ADR-0004).
    El embedder es inyectable; en tests, un embedder falso determinístico. El real (multilingüe) se
    configura en `.env` y se cachea en `data/indice/`.
  - `eval/retrieval.py`: Recall@k y nDCG@k contra un JSONL de consultas con relevantes etiquetados.
  - Aceptación: RRF con el ejemplo de clase (A, B, C con c=60 → B primero); los filtros excluyen lo que
    deben; métricas con casos calculados a mano.

- [ ] **004 · Nodos con LLM: relevamiento, planificador y respuesta** (26/11)
  - `enot/nodos.py`: `relevar(historial) -> PerfilViaje | Pregunta`, `planificar(perfil, candidatas,
    violaciones_previas) -> Itinerario`, `responder(itinerario, perfil) -> str`. Prompts en `enot/prompts/`.
  - Todas las llamadas pasan por `ClienteLLM` (ADR-0006) y quedan en una traza JSONL (`data/trazas/`).
  - Aceptación: con `ClienteFalso`, cada nodo arma el contexto esperado (incluye las violaciones previas en
    el reintento) y valida la salida; el relevamiento repregunta si falta un dato obligatorio.

- [ ] **005 · Flujo completo con loop de verificación + CLI (tracer bullet)** (27/11)
  - `enot/flujo.py`: `Sesion` serializable y el workflow de ADR-0003 con circuit breaker
    (`max_intentos=3`, tope de tokens). `max_intentos=1` = ablación B2.
  - `python -m enot`: chat por consola; `--sesion archivo.json` para retomar.
  - Aceptación: con un LLM falso que primero propone algo inválido, el flujo reintenta y termina válido;
    con uno que siempre falla, corta en 3 y explica la restricción que no se pudo cumplir; un ajuste
    ("sacá la segunda bodega") edita el itinerario vigente.

- [ ] **006 · Generador del set de evaluación** (28/11)
  - `eval/generador.py`: 100 consultas desde plantillas (+ paráfrasis opcional con LLM), estratificadas
    por escenario (PRD 6), restricciones en JSON, semilla fija. Escribe `data/eval/dev/` (60) y
    `data/eval/test/` (40) solo si no existen (el hook protege test).
  - Incluye pedidos infactibles etiquetados como tales. Muestra del 20% en `data/eval/revision_manual.csv`.
  - Aceptación: misma semilla → mismo set; proporciones por escenario; ninguna consulta repetida.

- [ ] **007 · Baselines, métricas y `make eval`** (29/11)
  - `eval/baselines.py`: B0 (LLM zero-shot, sin corpus), B1 (filtros + greedy por cercanía, sin LLM),
    B2 (Enot con `max_intentos=1`).
  - `eval/metricas.py`: hard pass rate, tasa de alucinación, cobertura del corpus + Gini, infactibles bien
    detectados. `eval/correr.py` y `make eval SPLIT=dev|test` → `reports/eval_<split>_<fecha>.json`.
  - Aceptación: métricas con casos armados a mano; mutation sobre `eval/metricas.py` ≥ 80%.

- [ ] **008 · Juez LLM calibrado y reporte de costos/latencia** (30/11)
  - `eval/juez.py`: rúbrica 1–5 de ajuste a preferencias; `eval/calibrar.py`: Spearman y kappa contra
    `data/eval/anotacion_humana.csv` (lo completa Flora).
  - `eval/reporte.py`: tabla final (métricas por sistema, costo y latencia media y p95 desde las trazas)
    en `reports/resultados.md`.
  - Aceptación: Spearman y kappa con valores conocidos; el reporte se arma con trazas de ejemplo.

- [ ] **009 · Cierre: README, Docker, interfaz mínima y guion** (1/12)
  - README con instrucciones de punta a punta; `Dockerfile`; interfaz web mínima opcional (Streamlit) sobre
    `enot/flujo.py`; `docs/presentacion.md` con el esqueleto de la exposición (problema, arquitectura,
    áreas de profundización, resultados, costos, limitaciones, relato del desarrollo).
  - Aceptación: `docker build` y `make check` pasan; el README se puede seguir en una máquina limpia.

---

## Tareas de Flora (de día)
- 24/11: bajar el CSV de DATAtourisme, `make datatourisme`, `make extract` con su clave, subir
  `data/datatourisme/muestra.csv` (unas 200 filas) para que el agente trabaje sobre el formato real.
- 25/11: validar ~30 fichas (`python -m corpus muestra`), revisar el PR de la noche.
- 26–27/11: probar el flujo con pedidos propios.
- 28/11: revisar el 20% del set de evaluación.
- 29/11: correr `make eval SPLIT=dev` con su clave.
- 30/11: anotar 30 casos para calibrar el juez.
- 1/12: correr `make eval SPLIT=test`.
- 2/12: armar y ensayar la presentación.
