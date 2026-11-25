# Revisión · 005 · ronda 2
**Veredicto:** APROBADO
**Rama:** noche/2026-11-24-005 · **Commits revisados:** 17eaaf8..37f5aac (ronda de arreglos posterior a 6a78c4e; contexto completo e0c968b..37f5aac)

## Sensores (corridos por mí)
- ruff: All checks passed!
- pytest: 338 passed, exit 0, offline. La ronda 1 terminó con 334, así que hay 4 tests nuevos: 2 en `test_flujo.py` y 2 en `test_cli.py`. El `-q` de `addopts` sumado al `-q` de la línea de comandos oculta el resumen; el total lo saqué contando los puntos.
- registro (CHANGELOG + ADR): OK. El CHANGELOG suma una sub-entrada "Ronda 2" y ADR-0015 actualiza la decisión 3 y la sección "Cómo se verifica".
- mutation: no aplica, porque el diff no toca `enot/verificador.py`, `enot/tools/` ni `eval/metricas.py`. El reporte informa 361/378 sobre `enot/flujo.py`; no lo volví a correr.
- tests existentes modificados: "OK: no se modificó ningún test existente." En la ronda cambiaron dos tests: `test_avisar_zonas_desconocidas_texto` y `test_cli_pasa_las_opciones_al_flujo`. Los dos nacieron en esta rama, los cambios van en el commit `tests:` (e15d2e2), separado del `fix:` (8dc2da1), y los dos se vuelven más estrictos.
- TDD comprobado: corrí los tests de e15d2e2 contra el código anterior al fix, con un `git archive` en el scratchpad y sin hacer checkout. Fallan los 4 nuevos y el que se reforzó: `test_ajuste_reintento_no_reaplica_el_pedido`, `test_contexto_planificador_reintento_de_ajuste`, `test_avisar_zonas_desconocidas_texto` y `test_cli_error_del_cliente_llm_sale_con_error`. Además `test_cli_ctrl_c_en_un_turno_no_guarda_el_turno_a_medias` corta la corrida con KeyboardInterrupt. Con el fix pasan todos.

## Hallazgos
1. [menor] enot/__main__.py:61-62 — Un error de los embeddings sigue saliendo con traceback. El caso es: falta la clave de OpenAI o el SDK, y `data/indice/` no tiene caché. `EmbedderOpenAI` crea su cliente recién en `embeber`, y `Indice.__init__` (retrieval.py:280) llama a `embeber` fuera del `try`. En cambio, el error de `ClienteLLM` ya se convierte en mensaje. Esto pega justo si Flora prueba el 26–27/11 con `LLM_PROVIDER` distinto de OpenAI y sin `OPENAI_API_KEY`. No bloquea porque el hallazgo 5 de la ronda 1 nombraba solo a `ClienteLLM`.
   Cómo resolverlo: envolver `Indice(...)` en `flujo_desde_args` con el mismo `except` → `ErrorConfiguracion` (que mencione `EMBEDDINGS_MODEL`/`OPENAI_API_KEY`), con su test. O, como mínimo, avisarle a Flora en el PR que precalcule el índice.
2. [menor] docs/noches/2026-11-24-2338.md:12 — En "Qué cambió", la línea de `enot/nodos.py` todavía nombra solo `pedido_ajuste`. Le falta `vigente_ajuste`, que sí aparece más abajo, en los hallazgos resueltos.
   Cómo resolverlo: sumar `vigente_ajuste` a esa línea.

## Lo que está bien
- El hallazgo importante de la ronda 1 quedó bien resuelto y probado donde importa:
  - En el reintento, el contexto tiene la propuesta fallida como "Itinerario anterior", el vigente aparte como referencia y el pedido marcado "ya aplicado". El encabezado "editá el itinerario anterior" ya no aparece.
  - `test_ajuste_reintento_no_reaplica_el_pedido` mira el contexto real del 2.º intento: delimita la sección "Itinerario anterior" hasta "Problemas" y compara el JSON exacto de la propuesta inválida y del vigente.
  - `test_contexto_planificador_reintento_de_ajuste` compara el contexto entero por igualdad, controla que `‹›` siga neutralizado (C.9) y que, sin pedido, no se agregue nada.
  - Con el código viejo los dos fallan (B.2).
- Spec (paso 5 y firmas), ADR-0015 (decisión 3), prompt del planificador (regla 9) y reporte cuentan lo mismo, y citan la revisión que motivó el cambio. El orden spec → tests → fix → registro se respetó también en esta ronda.
- Los cuatro menores se cerraron con tests que de verdad muerden:
  - El test de valores por defecto ahora pasa por `argparse` y compara con las constantes y con los literales.
  - El test de Ctrl-C comprueba que el archivo de sesión conserva el último turno completo (2 mensajes) y que no queda "corte".
  - El error de `ClienteLLM` se convierte en mensaje con código 1.
  - "las zonas" en plural tiene tests para el singular y el plural.

## Preguntas que haría la cátedra en la defensa
- Si el 1.er intento de un ajuste falla, ¿qué ve el planificador en el 2.º? → La propuesta fallida (que ya aplicó el pedido) con las violaciones del verificador, el vigente original como referencia aparte y el pedido marcado "ya aplicado: no lo apliques de nuevo". Así "sacá la segunda bodega" no saca otra más. Lo prueba `test_ajuste_reintento_no_reaplica_el_pedido`.
- ¿Por qué no volver a planificar desde el vigente en cada reintento? → Porque se perderían las correcciones parciales y el feedback del verificador quedaría colgando de un itinerario que el planificador no ve. Editar la propuesta fallida con el vigente como ancla corrige lo mínimo (regla 8 del prompt).
- ¿Qué pasa si el turista corta con Ctrl-C a mitad de un turno? → La CLI avisa y sale sin guardar. El archivo de sesión conserva el último turno completo, así que al retomar no queda un mensaje del turista sin respuesta.
- ¿Qué pasa si falta una clave? → Para el LLM, mensaje claro y código 1. Para los embeddings, hoy hay traceback si no hay caché del índice (hallazgo 1, menor).
