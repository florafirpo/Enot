# Revisión · 008 · ronda 1
**Veredicto:** CAMBIOS
**Rama:** noche/2026-11-25-008 · **Commits revisados:** 2bc09a6..1b70ab1

## Sensores (corridos por mí)
- ruff: All checks passed!
- pytest: 527 passed (2,4 s, offline)
- registro (CHANGELOG + ADR): OK (entrada nueva arriba en CHANGELOG + ADR-0018 con todas las secciones del template)
- mutation: eval/metricas.py 326/328 (sobreviven `x_afirmaciones__mutmut_53` y `x_evaluar_consulta__mutmut_9`, los mismos 2 equivalentes que se justificaron en el 007)
- tests existentes modificados: "OK: no se modificó ningún test existente."

## Hallazgos
1. [importante] eval/juez.py:91 — El contexto del juez incluye `p.experiencia`, que es el texto libre que escribió cada sistema en la parada, no un dato del corpus. B0 (zero-shot) o el LLM de Enot pueden poner "Dégustation de grands crus en cave familiale" en una bodega real, y el juez lo lee como si fuera parte de la ficha. Eso contradice dos cosas que declaran la spec y el ADR-0018 ("datos… tomados del corpus", "sin texto del sistema"), y el juez puede premiar una experiencia inventada aunque la métrica de alucinación la marque. El test `test_contexto_juez_usa_datos_del_corpus_y_es_ciego` no lo detecta porque la fixture usa justo un nombre que existe en el corpus. — La regla madre pide que lo declarado sea verificable en el repo, y lo que traen los sistemas no es verdad por venir de ellos (lineamientos A "regla madre", C.6, C.11).
   Cómo resolverlo: mostrar la experiencia solo si coincide con un `e.nombre` de `b.experiencias` y, si no coincide, omitirla o marcarla como "experiencia no está en la ficha". Agregar un test con una experiencia inventada sobre una bodega del corpus que verifique que ese texto no aparece en el contexto (el mismo arreglo vale para la planilla, que usa `texto_itinerario`).

2. [importante] eval/reporte.py:159 — `filas_sistemas` filtra los juicios solo por `sistema`. No cruza `consulta_id` con las salidas del reporte, y `main` no compara `juicios.reporte`/`juicios.split` con el reporte que recibe. Hay dos casos en que el preference score de `resultados.md` sale de otra corrida sin ningún aviso:
   - Flora corre `make reporte EVAL=reports/eval_test_….json JUICIOS=reports/juez_dev_….json`.
   - Vuelve a correr `make eval` y reusa los juicios viejos. Los ids coinciden pero los itinerarios son otros.
   — Es una falla silenciosa en el número central de H2, y la comparación tiene que ser honesta (lineamientos A "Evaluación, evidencia y costos", D.1).
   Cómo resolverlo:
   - en `filas_sistemas`, usar solo los juicios cuyo (consulta_id, sistema) esté en las salidas del reporte;
   - en `main`, dar error (código 1) si `juicios.split != reporte.split` o si `juicios.reporte` no apunta al mismo archivo;
   - test con juicios de otra consulta o de otro split.

3. [importante] eval/calibrar.py:141 — La planilla "a ciegas" tiene una columna `sistema` con B0/B1/B2/enot a la vista de quien anota. Flora es la autora de Enot, así que ese sesgo es justo lo que una anotación ciega tiene que evitar. El ADR dice "sin… el sistema en el texto", que técnicamente es cierto, pero en la defensa no alcanza. — El juez se calibra contra anotación humana, y esa anotación tiene que ser defendible (lineamientos D.4, A "Exposición y defensa").
   Cómo resolverlo: en el CSV poner un id opaco (por ejemplo `caso_01`) en vez de `sistema`, guardar la correspondencia caso→(consulta_id, sistema) en un archivo aparte que no se abre al anotar, y que `leer_anotaciones`/`calibrar` hagan el cruce. Ajustar `test_armar_planilla_estratificada_y_ciega` para que verifique que el nombre del sistema no aparece en ninguna columna visible.

4. [importante] corpus/llm.py:138 — `getattr(u, "prompt_tokens", 0) or 0` convierte en 0 un `usage` ausente, algo frecuente en endpoints `openai_compatible`. Esa llamada queda "ok" con 0 tokens y la consulta cuenta como de costo completo. El código es anterior a esta tarea, pero ahora el ADR-0018 y el CHANGELOG afirman "nunca un 0 inventado" y "tokens exactos", y esa afirmación no se sostiene con este proveedor. — Nada fabricado en costos (lineamientos A, E; regla madre).
   Cómo resolverlo: hay dos caminos.
   - Mínimo: anotar la limitación en ADR-0018 (Consecuencias) y en las notas de `render_markdown`.
   - Mejor: que `_openai` devuelva `None` cuando falta `usage`. Como el validador de `EventoTraza` exige tokens en "ok", habría que decidir si esa llamada se registra como ok con tokens desconocidos (relajar el validador para ese caso con un campo explícito) o no. Si eso choca con el pedido de la revisión 004, dejarlo escrito como decisión pendiente para Flora.

5. [menor] Makefile (`juez`, `planilla`, `calibrar`) — con `EVAL`/`JUICIOS` vacíos, argparse falla con un mensaje genérico. Un `$(if $(EVAL),,$(error Falta EVAL=reports/eval_…json))` sería más claro para seguir el README.

## Lo que está bien
- `spearman` y `kappa` se testean con valores calculados a mano (incluido 8,5/√95 con empates) y contra scipy/sklearn cuando están instalados. También hay un caso de juez "sesgado" que ordena bien y puntúa 2 puntos de más: Spearman alto, kappa bajo, no apto. Esos tests no pasarían con una implementación constante o que ignore un parámetro.
- Costo honesto en el reporte:
  - `costo_consulta` separa llamadas fallidas, llamadas sin tokens y modelos sin precio;
  - media y p95 se calculan solo sobre las consultas con costo completo, y se dice sobre cuántas;
  - `ErrorSalidaInvalida` trae los tokens exactos y el nodo los registra;
  - el `model_validator` de `EventoTraza` cierra el pendiente de la revisión 004.
- Orden SDD prolijo: spec (y su corrección) → tests → código → tests de sobrevivientes. Todos los tests que nombra "Cómo se verifica" existen. La planilla se rechaza con split test y nunca pisa un CSV existente. La rúbrica trata las fichas como dato (C.9) y no pide confianza (C.8).

## Preguntas que haría la cátedra en la defensa
- "¿El juez es realmente ciego y ve lo mismo para los cuatro sistemas?" → Ve el pedido y los datos de ficha del corpus por bodega, sin precios, horarios, nombre ni prosa del sistema. Hoy la experiencia de la parada viene del sistema, y eso hay que filtrarlo contra la ficha (hallazgo 1).
- "¿Por qué calibran con dev y reportan sobre test?" → Ajustar la rúbrica mirando test es ajustar la vara al examen (D.1, D.6). Con dev se decide si el juez es apto, y sobre test se reporta tal cual.
- "¿Por qué kappa cuadrático para el umbral?" → La escala 1–5 es ordinal: 4 contra 5 es casi acuerdo y 1 contra 5 es desacuerdo total. Se reportan los dos kappas. Spearman solo no alcanza para un juez con sesgo constante.
- "¿El juez usa el mismo modelo que Enot? ¿No se favorece a sí mismo?" → `Juicios` guarda proveedor y modelo. El juez ve datos del corpus, no la prosa de Enot, y la calibración contra la anotación humana es la que dice si el sesgo importa. Si Flora tiene acceso a otro modelo, conviene juzgar con ese.
- "¿Cuánto cuesta un itinerario y cómo saben que no hay ceros inventados?" → Σ t_in·p_in + t_out·p_out por llamada, desde la traza. Las consultas con tokens desconocidos se cuentan aparte. Hay que poder explicar el caso del proveedor que no informa `usage` (hallazgo 4).
