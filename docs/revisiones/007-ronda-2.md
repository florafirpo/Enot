# Revisión · 007 · ronda 2
**Veredicto:** APROBADO
**Rama:** noche/2026-11-25-007 · **Commits revisados:** 32a2858..12e43d2

## Sensores (corridos por mí)
- ruff: All checks passed!
- pytest: 467 passed en 2,48 s (offline). `test_b1_sobre_la_muestra_real` corre: no se saltea, porque `muestra.csv` está versionada y su sha256 coincide con `HUELLA_MUESTRA`, así que también se chequean las cifras exactas.
- registro (CHANGELOG + ADR): OK ("la rama trae entrada de CHANGELOG y ADR"). La entrada del 007 suma una viñeta de la ronda 2, y ADR-0017 suma la consecuencia "factible no certificado" y el test en "Cómo se verifica".
- mutation: eval/metricas.py 326/328 (99%). Sobreviven los mismos dos equivalentes de la ronda 1 (`x_afirmaciones__mutmut_53`, `x_evaluar_consulta__mutmut_9`). La justificación del primero ya es correcta en el reporte. Esta ronda no tocó código de `eval/`, `enot/` ni `corpus/`.
- tests existentes modificados: "OK: no se modificó ningún test existente." Los tests editados (`test_resolver_bodega`, `test_b0_salida`, `test_b0_inventado_no_pasa`, `test_latencia_medida`) son nuevos de esta rama. Se cambiaron en un commit `tests:` aparte, sin código.

## Hallazgos
1. [menor] tests/test_baselines.py:273-275 — El 10,5 s de Enot depende de cuántas veces se lee `time.perf_counter` dentro del flujo: 1 + 3 nodos × 2 lecturas. Como se parchea el módulo `time` global, cualquier lectura nueva rompe el test aunque la latencia se siga midiendo bien, sea de un nodo nuevo, de un reintento o de una librería. Eso incluye cosas fuera de la rama. Es frágil, pero el comentario lo explica y cumple lo que pidió la ronda 1: detecta que se saque el `perf_counter()`. (lineamientos B.2)
   Cómo resolverlo: opcional, no bloquea. Para Enot alcanza con afirmar `latencia_s > 1.5`, o parchear solo el reloj que usa `eval.baselines` si en algún momento se importa como nombre propio.

## Lo que está bien
- Se resolvieron los cuatro hallazgos de la ronda 1, en orden SDD: spec (32a2858) → tests (d95bfa9) → registro (12e43d2). La bodega y el precio que inventa B0 quedaron marcados `[SINTÉTICA]` en el nombre y en un comentario explícito. Con eso se cumple la regla de AGENTS.md sobre datos inventados.
- `test_b1_sobre_la_muestra_real` está bien pensado. Usa la fixture `entorno`, así que no escribe en `data/`, y corre en memoria. Siempre chequea los invariantes (cero inventadas, zona fuera de Borgoña detectada) y solo si la huella sha256 coincide fija las cifras exactas: 79/80, solo q047, cobertura 0,41, Gini 0,8166 e infactibles 0,3. Las cifras del ADR pasan a ser verificables en el repo (lineamientos A, regla madre) y el test no se rompe si Flora cambia la muestra.
- El ADR-0017 suma una consecuencia honesta y útil para la defensa: "factible" no está certificado contra el corpus. Usa el caso concreto q047 y dice qué hacer con el corpus completo, que es mirar los factibles que fallan en todos los sistemas (lineamientos D.3).

## Preguntas que haría la cátedra en la defensa
- "¿Cómo sé que el 98,75% de B1 no es un número copiado a mano?" → Lo reproduce `test_b1_sobre_la_muestra_real` en cada `pytest`, atado a la huella sha256 de la muestra. Si la muestra cambia, siguen corriendo los invariantes y las cifras exactas se dejan de chequear.
- "¿Por qué falla q047 si es factible?" → Pide 3 días en las Hautes-Côtes, y en la muestra hay una sola bodega en esa zona. B1 no repite bodegas. El generador solo certifica los infactibles (ADR-0016), así que con el corpus completo los factibles que fallan en todos los sistemas se revisan antes de culpar a un sistema.
- "¿El test de latencia mide algo o pasa con 0?" → Usa un reloj falso que avanza 1,5 s por lectura y afirma valores exactos. Si alguien saca la medición, la latencia queda en 0 y el test falla.
- "¿Por qué hay una bodega inventada en los tests si la regla lo prohíbe?" → Representa justamente una alucinación de B0, para probar que se cuenta como inventada. Está marcada `[SINTÉTICA]`, que es lo que pide la regla.
