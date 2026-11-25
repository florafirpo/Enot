# Revisión · 007 · ronda 1
**Veredicto:** CAMBIOS
**Rama:** noche/2026-11-25-007 · **Commits revisados:** f6df183..c76aea1

## Sensores (corridos por mí)
- ruff: All checks passed!
- pytest: 466 passed en 1,81 s (offline)
- registro (CHANGELOG + ADR): OK. Hay entrada nueva arriba en CHANGELOG y ADR-0017 tiene todas las secciones del template.
- mutation: eval/metricas.py 326/328 (99%). Sobreviven `x_afirmaciones__mutmut_53` (`>` por `>=` en la tolerancia de precio) y `x_evaluar_consulta__mutmut_9` (`sistema=""` por `"XXXX"` en la salida sintética). Los dos son equivalentes en la práctica (ver hallazgo 4).
- tests existentes modificados: "OK: no se modificó ningún test existente."

## Hallazgos
1. [importante] tests/test_baselines.py:59-66, 81, 98 — La respuesta falsa de B0 (`SALIDA_B0`) pone una bodega real, "Domaine de la Romanée-Conti", con un precio inventado (`precio_por_persona_eur: 250`). Ese dato no está marcado como sintético. El docstring del archivo dice que la fixture de bodegas es SINTÉTICA, pero este dict no viene de esa fixture. AGENTS.md no admite precios inventados en fixtures sin marcar, aunque acá el dato represente justamente una alucinación de B0. No lo pongo como bloqueante porque nunca llega al corpus ni a un prompt, y el test afirma que se cuenta como inventado. Igual Flora no podría defenderlo frente a su propia regla. (regla de AGENTS.md "Los datos de bodegas son reales… Nunca inventes bodegas, precios ni horarios… en fixtures que no estén marcados como sintéticos"; lineamientos F)
   Cómo resolverlo: reemplazar el nombre por uno claramente ficticio y marcado (por ejemplo "[SINTÉTICA] Domaine Inventado B0") en `SALIDA_B0`, `test_resolver_bodega` y los asserts que lo nombran, o marcar el dict y su precio como `[SINTÉTICA]` en un comentario explícito. Como es un test nuevo de esta rama, se puede editar. Va en un commit `tests:` aparte.

2. [menor] tests/test_baselines.py:248-257 — `test_latencia_medida` pide `0 <= s.latencia_s < 60`. Ese assert pasa con una implementación que nunca mide nada, porque `SalidaSistema.latencia_s` vale 0.0 por defecto. La spec dice "miden una latencia", y el test no detectaría que alguien saque el `time.perf_counter()`. (lineamientos B.2 "¿pasaría con una implementación constante?")
   Cómo resolverlo: hacer monkeypatch de `eval.baselines.time.perf_counter` con un reloj falso que avance, por ejemplo 1,5 s por llamada, y afirmar el valor exacto. Alternativa más débil: `> 0`.

3. [menor] docs/adr/0017-metricas-y-baselines-del-benchmark.md (Consecuencias), docs/feedback-flora.md y el reporte — La cifra "B1 sobre la muestra real da 98,75%" (cobertura 41%, Gini 0,82, infactibles 30%) no se puede reproducir desde el repo: no hay comando, script ni test que la genere. La reproduje con un script propio (datatourisme.run sobre `muestra.csv` en un directorio temporal, `generar()` y `BaselineB1`) y da exactamente esos números. El único factible que falla es q047: 3 días en Hautes-Côtes, donde la muestra tiene una sola bodega y B1 no repite. (lineamientos A, regla madre: "lo que se declara… tiene que ser verificable en el repo")
   Cómo resolverlo: agregar un test con `skipif` sin `muestra.csv`, igual que `test_con_la_muestra_real_de_datatourisme` en test_flujo, que corra B1 sobre la muestra y afirme las métricas. Si no, dejar el comando exacto en el reporte o el README. Conviene anotar en el ADR que la etiqueta "factible" del generador no está certificada contra el corpus (caso q047).

4. [menor] docs/noches/2026-11-25-1039.md (mutation) — El reporte justifica el mutante `>`/`>=` diciendo que "con floats, la diferencia nunca da exactamente 0,01". No es cierto en general: `abs(0.02 - 0.01) == 0.01` da True. Entre 0 y 200 EUR, en pasos de un centavo, solo pasa con los pares (0,00; 0,01) y (0,01; 0,02), así que el mutante es equivalente para precios reales. La justificación tiene que ser correcta para que Flora la pueda defender. (lineamientos B.3)
   Cómo resolverlo: corregir la explicación en el reporte, por ejemplo: "solo difiere con precios de 1–2 centavos, que no existen en el corpus".

## Lo que está bien
- El hard pass corrige un hueco real de ADR-0007. Suma la estructura (días, día de la semana, al menos una visita por día) y cero inventadas a `verificar() == []`, y se calcula contra la etiqueta, no contra el perfil extraído. `test_hard_pass_usa_la_etiqueta` y `test_hard_pass_falla` lo prueban con casos que una implementación trivial no pasaría (D.3, D.6).
- La comparación es honesta y las decisiones están escaladas bien. B1 usa el verificador como oráculo (una sola fuente de verdad). La ventaja de B1, que recibe el perfil etiquetado, está declarada. Para B2 se tomó la interpretación del PRD ("aislar el aporte del verificador") en vez de la literal del backlog, con el parámetro `entregar_sin_verificar` para la alternativa, y se escaló a Flora con opciones. Infactibles: tasa total, por motivo y representables, sin esperar la decisión (a)/(b)/(c) (C.13, D.2).
- Proceso limpio: spec → tests → código en commits separados. Mutation al 99% sobre `eval/metricas.py`, y los sobrevivientes de `baselines.py` destaparon un bug real: tokens en 0 cuando una llamada falló, ahora en `None`. `make eval SISTEMAS=B1` corre sin claves. El reporte nunca pisa uno anterior y guarda configuración y commit (E, D2).

## Preguntas que haría la cátedra en la defensa
- "Si el verificador es parte de Enot y de la métrica, ¿no se corrige solo?" → La métrica suma dos chequeos que el verificador no hace (estructura y alucinación). El verificador tiene mutation testing. B0 no lo usa y se mide con el mismo código. Lo que no cubre (cantidad de bodegas, zonas el mismo día) aparece en el desglose de infactibles por motivo.
- "¿Por qué B1 da 98,75% de hard pass?" → Las fichas de la muestra no tienen horarios ni precios, y por ADR-0009 sin evidencia no hay violación. El número solo discrimina cuando la extracción completa esos campos, así que se reporta junto con la completitud del corpus.
- "¿Por qué B2 no es simplemente `max_intentos=1`?" → Con eso el flujo sigue rechazando la propuesta inválida y responde "infactible". El verificador seguiría actuando de guardia y no se aislaría su aporte. Por eso B2 entrega la primera propuesta (ADR-0017). La alternativa B2a/B2b es un parámetro.
- "¿La tasa de alucinación de Enot mira lo que lee el turista?" → Mira el itinerario estructurado. Horarios, precios y duraciones los escribe el código (`render_itinerario`). El LLM de respuesta solo redacta la introducción y los motivos, con prohibición de poner cifras. Lo que pueda inventar en prosa queda para el juez del 008.
- "¿Cómo cuenta los infactibles que el sistema no puede representar?" → Hay tres números: total, por motivo y sobre representables (hoy solo zona fuera de Borgoña). Si Flora elige (a), las métricas no cambian; si elige (c), se lee la tasa de representables.
