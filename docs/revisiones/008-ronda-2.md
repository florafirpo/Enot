# Revisión · 008 · ronda 2
**Veredicto:** APROBADO
**Rama:** noche/2026-11-25-008 · **Commits revisados:** 2bc09a6..4708095 (lo nuevo de la ronda 2: e788fef..4708095)

## Sensores (corridos por mí)
- ruff: All checks passed!
- pytest: 533 passed (3,0 s, offline)
- registro (CHANGELOG + ADR): OK ("la rama trae entrada de CHANGELOG y ADR"). ADR-0018 actualizado con la planilla de id opaco, el cruce de juicios con el reporte, una alternativa descartada nueva y la limitación de `usage`.
- mutation: eval/metricas.py 326/328. Sobreviven `x_afirmaciones__mutmut_53` y `x_evaluar_consulta__mutmut_9`, los mismos 2 equivalentes justificados en el 007. La rama solo agrega el campo `traza` a `SalidaSistema`.
- tests existentes modificados: "OK: no se modificó ningún test existente." Los tests que cambiaron en la ronda 2 son de esta misma rama, no de `desarrollo`. Van en su propio commit (425f57d), separado de los fixes, y el reporte explica por qué cambiaron.

## Seguimiento de la ronda 1
1. Experiencia del sistema en el contexto del juez → **resuelto** (5791615). `_experiencia_de_la_ficha` muestra la experiencia solo si coincide con la ficha, sin distinguir mayúsculas como `eval.metricas`, y con el nombre que figura en la ficha. Como la planilla usa el mismo `texto_itinerario`, el arreglo también le llega a ella. `test_contexto_juez_no_muestra_experiencias_inventadas` usa una experiencia `[SINTÉTICA]` inventada sobre una bodega del corpus, y fallaría con el código anterior.
2. Juicios de otra corrida en el reporte → **resuelto** (110d783):
   - `filas_sistemas` solo cuenta los juicios de (consulta, sistema) que corresponden a una salida `itinerario` del reporte.
   - `verificar_juicios` rechaza otro split u otro archivo de origen, y el CLI sale con 1 sin escribir `resultados.md`.
   - Los tres tests nuevos fallarían sin el filtro o sin el chequeo.
3. Columna `sistema` a la vista en la planilla → **resuelto** (c46c227):
   - Cada caso lleva un id `caso_NN` y la correspondencia queda en `anotacion_humana_claves.csv`.
   - Ninguno de los dos archivos se pisa.
   - `leer_anotaciones` cruza la planilla con las claves y da error si falta el archivo de claves o si un caso no figura en él.
   - `test_planilla_ciega_ningun_sistema_a_la_vista` verifica que ningún nombre de sistema aparezca en el CSV visible.
4. `usage` ausente = 0 tokens → **justificado** por el camino mínimo. Está declarado en ADR-0018 (Consecuencias) y en las notas de `render_markdown`, y quedó como decisión pendiente en `docs/feedback-flora.md` con las opciones (a)/(b) y una recomendación. Cambiar el validador de `EventoTraza` le toca a Flora.
5. (menor) Makefile → **resuelto** (5a4cc38). `$(error …)` corta si falta `EVAL`/`JUICIOS` en `juez`, `planilla`, `calibrar` y `reporte`.

## Hallazgos
Ninguno.

## Lo que está bien
- Orden SDD también en la ronda 2: la spec (e788fef, sección "Cambios por la revisión 008 ronda 1" con cada test por nombre) va antes que los tests (425f57d), y los tests antes que los fixes. Hay un fix por hallazgo, cada uno en su commit.
- Los tests nuevos no pasan con una implementación trivial:
  - el juicio extra con puntaje 1 de una consulta ajena (q77) o de una consulta infactible (enot/q3) bajaría la media de 4;
  - `verificar_juicios` se prueba por split y por archivo;
  - la planilla se revisa sobre el CSV escrito, no sobre el dict.
- La planilla ahora es defendible: id opaco, orden barajado con semilla, las claves aparte y ninguno de los dos archivos se pisa (también se cubre el caso en que solo quedó el de claves).

## Preguntas que haría la cátedra en la defensa
- "¿El juez es realmente ciego?" → Ve el pedido, las preferencias y, por bodega, solo datos de la ficha del corpus. Una experiencia aparece solo si está en la ficha y con el nombre de la ficha. No ve precios, horarios, el nombre del sistema ni su prosa. Hay un test con una experiencia inventada que no llega al contexto.
- "¿Cómo anotaste sin sesgo si sos la autora de Enot?" → La planilla tiene ids opacos `caso_NN` en orden barajado y no muestra el sistema. La correspondencia está en un archivo aparte que no se abre hasta calibrar. Muestra el mismo texto que ve el juez.
- "¿Cómo saben que el preference score sale de la misma corrida?" → Los juicios guardan de qué reporte y de qué split salen. El reporte rechaza los de otro archivo o de otro split, y solo cruza los de (consulta, sistema) que entregaron itinerario en ese reporte.
- "¿Y si el proveedor no informa tokens?" → Con OpenAI o Anthropic no pasa. Con un endpoint compatible sin `usage` hoy se registran 0 tokens. Está declarado como limitación en ADR-0018 y en `resultados.md`, y la decisión de marcarlo como "desconocido" está pendiente de Flora.
- "¿Por qué kappa cuadrático?" → La escala 1–5 es ordinal: 4 contra 5 es casi acuerdo y 1 contra 5 es desacuerdo total. Se reportan los dos kappas. Spearman solo no detecta un juez con sesgo constante, y hay un test con ese caso.
