# Revisión · 005 · ronda 1
**Veredicto:** CAMBIOS
**Rama:** noche/2026-11-24-005 · **Commits revisados:** e0c968b..991a9ca

## Sensores (corridos por mí)
- ruff: All checks passed!
- pytest: 334 passed (1.74 s, offline, 0 skipped; antes eran 302, así que son 32 nuevos: 26 en `test_flujo.py` y 6 en `test_cli.py`)
- registro (CHANGELOG + ADR): OK (entrada nueva arriba en CHANGELOG + ADR-0015 con todas las secciones del template)
- mutation: no aplica (el diff no toca `enot/verificador.py`, `enot/tools/` ni `eval/metricas.py`). El reporte dice que `enot/flujo.py` dio 344/361 de forma voluntaria. No lo volví a correr.
- tests existentes modificados: "OK: no se modificó ningún test existente." El commit `6aa2611` cambia tests nuevos de esta misma rama después del `feat:`. Lo revisé línea por línea: todos los cambios agregan aserciones (textos exactos, advertencias en el detalle, carpeta anidada) y ninguno debilita una.

## Hallazgos
1. [importante] enot/flujo.py:195-207 — En un ajuste que necesita reintento, el pedido se aplica dos veces. `pedido` se pasa en todos los intentos, pero desde el 2.º `previo` deja de ser el vigente y pasa a ser la propuesta fallida, que ya tiene el ajuste aplicado. El contexto del 2.º intento dice entonces "editá el itinerario anterior: cambiá solo lo que pide" + `<pedido>sacá la segunda bodega</pedido>` sobre un itinerario donde la segunda bodega ya no está. El planificador puede sacar otra parada, y además ya no ve el vigente original. Ningún test lo cubre: `test_ajuste_infactible_conserva_el_vigente` pasa por ese camino pero no mira el contexto de los intentos 2 y 3. Es justo el tipo de error que se compone en una cadena (C.3), y el área "orquestación con loop de verificación" es una de las profundizaciones declaradas en el PRD (A). — La cátedra pediría que el reintento corrija las violaciones sin volver a aplicar el pedido (B.2: un test que falle ante este error).
   Cómo resolverlo: en los reintentos de un ajuste, pasar el vigente original y el pedido marcados como referencia, separados de la propuesta fallida y sus violaciones. O, como mínimo, cambiar el encabezado de la sección del pedido cuando hay violaciones previas, algo como "este pedido ya está aplicado en el itinerario anterior; solo corregí los problemas". Agregar un test (commit `tests:` aparte) que verifique el contexto del 2.º intento de un ajuste fallido. Aclararlo en la spec (paso 5, hoy ambiguo) y en ADR-0015, decisión 3.
2. [menor] tests/test_cli.py:86-90 — La segunda mitad de `test_cli_pasa_las_opciones_al_flujo` dice probar "sus valores por defecto", pero arma un namespace a mano con 3 / 200 000 / 10 y no pasa por `argparse`. Si los `default=` de `_argumentos` estuvieran mal, el test seguiría pasando (B.2: ignora el parámetro que dice probar).
   Cómo resolverlo: llamar a `main(["--fichas", …], …)` sin opciones, con un `construir` que capture `args`, y verificar `args.max_intentos`, `args.tope_tokens` y `args.k`.
3. [menor] docs/specs/005-flujo-y-cli.md:108-147 — `test_tope_alcanzado_por_el_relevamiento_no_planifica` existe y ADR-0015 lo cita, pero no figura en "Cómo se verifica" de la spec.
   Cómo resolverlo: agregarlo a la lista.
4. [menor] enot/flujo.py:132 — Con dos zonas o más el texto dice "No reconozco la zona Alsacia, Loira" (singular). Este texto lo lee el turista tal cual.
   Cómo resolverlo: usar "las zonas" cuando `len(zonas) > 1`. Es parte de la revisión de textos que ya tiene pendiente Flora.
5. [menor] enot/__main__.py:84-90 — Un Ctrl-C durante `flujo.turno` corta con traceback, porque el `except` solo envuelve `leer`. Un error al construir `ClienteLLM` (falta la clave) tampoco se convierte en mensaje. Para un tracer bullet alcanza, pero conviene saberlo antes de las pruebas de Flora del 26–27/11.
   Cómo resolverlo: atrapar `KeyboardInterrupt` alrededor del turno y los errores de configuración del cliente dentro de `flujo_desde_args`.

## Lo que está bien
- El circuit breaker vive en código y se cuenta desde la traza (C.4). Se chequea antes de cada llamada, sobrevive al retomar la sesión, y hay tests que cortan en cada punto: antes del relevamiento, a mitad del loop y antes de `responder`. La ablación B2 es un parámetro, y `Respuesta` devuelve la propuesta inválida con sus violaciones, que es lo que va a necesitar el ítem 007.
- Los textos de los bordes los escribe el código y no el LLM: infactible, zona desconocida, sin candidatas y tope (C.11). Un itinerario válido no se pierde aunque falle `responder` o se llegue al tope (`render_itinerario`). Un `ErrorNodo` deja la sesión como estaba antes del turno. Todo eso tiene tests con texto exacto.
- El orden SDD está limpio: spec → tests → `feat` → refuerzo por mutation → registro. Uno de los tests encontró un error real antes del código (los motivos de "sin candidatas" dentro de la zona pedida). Hay un turno completo sobre la muestra real de DATAtourisme sin copiar datos a fixtures. El pedido del turista se neutraliza como dato (`<`/`>` → `‹`/`›`, C.9). El alcance coincide con el ítem, incluido el aviso de zona desconocida de la revisión 003, y no hay sobreingeniería (C.10). ADR-0015 tiene alternativas reales y consecuencias honestas: un "gracias" cuesta un turno entero y el tope de tokens se subestima cuando hay llamadas con error.

## Preguntas que haría la cátedra en la defensa
- ¿Qué impide que el loop gaste sin límite? → Dos contadores en código: a lo sumo `max_intentos` llamadas al planificador por turno, y un tope de tokens por conversación sumado desde la traza antes de cada llamada. `test_tope_de_tokens_corta_el_loop` lo muestra cortando a mitad del loop.
- Si una llamada falla, ¿sus tokens cuentan para el tope? → No: `ClienteLLM` no informa tokens cuando lanza un error, así que esos eventos quedan en `None` y el tope se subestima. Lo acota igual `max_intentos`, y con la tabla de precios del ítem 008 se pasa a un tope en USD.
- ¿Por qué el ajuste lo resuelve el LLM y no una regla? → "Sacá la 2.ª" se podría hacer con una regla, pero "algo más chico y familiar" no. El resultado pasa por el mismo verificador y el vigente solo se reemplaza por otro factible.
- ¿Qué pasa si el ajuste falla en el 1.er intento? → Hoy el pedido se vuelve a aplicar sobre la propuesta fallida (hallazgo 1). Después del arreglo: el reintento solo corrige las violaciones y conserva el pedido como referencia.
- ¿Cómo miden el aporte del loop? → `max_intentos=1` es la ablación B2, y `Respuesta.itinerario` + `violaciones` dan el hard pass rate de cada configuración en el ítem 007.
