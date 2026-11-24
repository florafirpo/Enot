# Revisión · 004 · ronda 2
**Veredicto:** APROBADO
**Rama:** noche/2026-11-24-004 · **Commits revisados:** 7b3dff9..5539c25

## Sensores (corridos por mí)
- ruff: All checks passed!
- pytest: 302 passed, 0 fallas (301 de la ronda 1 + `test_evento_traza_tokens_desconocidos`)
- registro (CHANGELOG + ADR): OK. La entrada de CHANGELOG suma la ronda 2 y ADR-0014 está actualizado en la decisión 4, en "Consecuencias" y en "Cómo se verifica".
- mutation: no es obligatoria (la rama no toca verificador, tools ni métricas). Este fix no la justificaba, así que no la volví a correr. El reporte informa `enot/nodos.py` 531/559. Los 3 sobrevivientes nuevos borran un `tokens_in=None` explícito que coincide con el valor por defecto, así que son equivalentes (ver hallazgo 1).
- tests existentes modificados: "OK: no se modificó ningún test existente." Esta ronda cambia dos tests (`test_error_del_cliente_se_registra_y_relanza` y `test_traza_de_error_detalles`), pero los dos nacieron en esta rama y no existen en `desarrollo`. El cambio va en su propio commit `tests:` (bbb09a7), antes del fix (da68ea5), y el reporte explica por qué el 0 estaba mal. Lo da por resuelto la ronda 1, que pedía esto mismo.

## Hallazgos
1. [menor] enot/trazas.py:31-33 — `tokens_in`, `tokens_out` e `intentos_validacion` tienen `None` por defecto. Por eso un evento `estado="ok"` sin tokens también valida (lo probé: `EventoTraza(..., estado="ok")` se construye con los tres en `None`). Si en el futuro el camino OK se olvida de pasar los tokens, el reporte de 008 contaría ese evento como "desconocido" sin que nada falle. Por el mismo motivo, los 3 mutantes de `nodos.py` que borran `tokens_in=None` sobreviven. Hoy el camino OK está cubierto por `test_cada_nodo_registra_un_evento`, así que el riesgo es bajo. — Conviene que el invariante "ok ⇒ tokens conocidos" lo garantice el modelo y no la disciplina de quien lo llama (lineamientos C.4, el límite en el código; Pydantic en los bordes, AGENTS.md).
   Cómo resolverlo (opcional, puede ir en 005 o 008): declarar los campos `Optional[int]` sin default (obligatorios aunque puedan ser `None`), o agregar un `model_validator` que exija enteros cuando `estado == "ok"`, con un test que verifique que un evento ok sin tokens falla.

## Lo que está bien
- El hallazgo importante de la ronda 1 quedó bien resuelto y sin salirse del alcance. Una llamada fallida ya no aparece como gratuita: queda con `None`, que se escribe en el JSONL como `null` y se lee igual (`test_evento_traza_tokens_desconocidos` lo verifica sobre el archivo). No se tocó `corpus/llm.py` y el pendiente quedó anotado en el ítem 008: contar los eventos con tokens desconocidos y no sumarlos como 0 (lineamientos D2.1, regla "nada fabricado").
- ADR-0014 dejó de prometer de más. Ahora separa el detalle, que sale de las tools, de la introducción y los motivos, que solo restringe el prompt. También explica por qué no se agregó el filtro por dígitos: descartaría motivos legítimos como "1er cru" o "desde 1850". Es un argumento razonable y defendible para un hallazgo menor.
- La ronda respeta SDD: `revision` → `spec` → `tests` (fallaban sin el fix) → `fix` → `docs`. La spec nombra el test nuevo y el reporte de la noche coincide con el diff: 302 tests, mutation y criterios.

## Preguntas que haría la cátedra en la defensa
- ¿Por qué `None` y no 0 en los tokens de una llamada fallida? → Porque `ClienteLLM` puede haber hecho hasta 2 llamadas pagas antes de lanzar el error y no las informa. Un 0 sería un número inventado que abarata el costo justo en el peor caso. `None` dice "no lo sabemos" y obliga al reporte de 008 a contar esos eventos aparte.
- Entonces, ¿el costo por itinerario que van a reportar está subestimado? → Le faltan las llamadas fallidas, pero el reporte va a decir cuántas son. Para medirlas, el error de `ClienteLLM` tiene que traer los tokens consumidos, y eso quedó anotado en el ítem 008.
- ¿Qué impide que la introducción del itinerario diga un horario falso? → Hoy lo impide solo el prompt, y el ADR lo dice así. Todo el detalle (horarios, precios, traslados, total) sale de las tools. Si en las pruebas aparecen números en la introducción o en los motivos, el paso siguiente es un chequeo en código.
