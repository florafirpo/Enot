# Revisión · 010 · ronda 1
**Veredicto:** APROBADO
**Rama:** noche/2026-11-24-010 · **Commits revisados:** 0426676..f8587f6

## Sensores (corridos por mí)
- ruff: All checks passed!
- pytest: 179 passed, 0 fallas (exit 0; 22 tests nuevos en `tests/test_verificador_advertencias.py`; 172 − 15 + 22 = 179, coincide con el CHANGELOG)
- registro (CHANGELOG + ADR): OK (entrada nueva arriba en CHANGELOG + ADR-0012 con todas las secciones)
- mutation: enot/verificador.py 270/270 (ningún sobreviviente)
- tests existentes modificados: `tests/test_modelos.py`, `tests/test_verificador.py`. Están justificados caso por caso en el reporte (`docs/noches/2026-11-24-1056.md`, tabla "Tests de 002 modificados y por qué") y en la spec 010. Van en el commit 7ee9659, que solo toca tests y está separado del código (c75dd95). Los cambios responden a que la regla cambió por pedido de Flora (dieta fuera de alcance; sin dato pasa a ser advertencia; el francés siempre se cumple). No se ablandaron tests para que pasen: los casos que siguen siendo violación (`False`) se mantienen.

## Hallazgos
1. [menor] docs/adr/0012-advertencias-para-datos-faltantes-del-turista.md (Consecuencias) — El ADR reconoce que el *hard pass rate* (H1) pasa a medir "factible con lo que sabemos" y propone reportar en el 007 el promedio de advertencias por itinerario. Esa mitigación no quedó registrada en ningún lugar que la haga cumplir: ni en el ítem 007 de `BACKLOG.md` ni en la tabla de métricas del PRD. Si se pierde, la métrica de H1 queda más laxa y la incertidumbre no se ve (lineamientos D.6 Goodhart; A, "regla madre").
   Cómo resolverlo: agregar en el ítem 007 del backlog, o como decisión pendiente en `docs/feedback-flora.md` si Flora tiene que aprobar el cambio de alcance, una línea que pida "advertencias promedio por itinerario, por tipo" junto al hard pass rate.
2. [menor] docs/specs/002-verificador.md:16,23,35 — La spec 002 sigue describiendo `restriccion_alimentaria`, `TIPOS_COMIDA` y la regla "sin dato = violación" para accesibilidad e idioma, sin aclarar que la spec 010 la reemplaza en parte. Quien la lea en la defensa puede tomarla como vigente (G.2 registro).
   Cómo resolverlo: una línea arriba de la spec 002, del tipo "Reemplazada parcialmente por la spec 010 / ADR-0012 (necesidades del turista)".

## Lo que está bien
- El orden SDD está limpio y es verificable en `git log`: spec → tests nuevos → tests de 002 que cambian de sentido (aparte, con justificación caso por caso) → feat → test para el único mutante sobreviviente. Mutation testing 270/270, confirmado por mí.
- Diseño de la API: `Advertencia` es un modelo propio y no un flag dentro de `Violacion`, y `verificar` mantiene su contrato. Así el loop de reintento (005) y el hard pass rate (007) no pueden confundir una advertencia con una violación por olvidarse de filtrar. El ADR-0012 documenta de verdad esa decisión, con seis alternativas descartadas y sus razones (C.5, C.7, A "diseño 25%").
- Los tests son significativos. `test_accesibilidad_sin_dato_es_advertencia`, `test_frances_siempre_cumple` (bodega sin idiomas y bodega solo con `de`) y `test_otro_idioma_sin_lista_es_advertencia` fallan con una implementación vacía, con la regla vieja de ADR-0009 y con una que ignore el francés o el `None`. `test_verificar_devuelve_solo_las_violaciones` usa un caso que tiene violaciones y advertencias a la vez. Las fixtures nuevas están marcadas `[SINTÉTICA]`, no hay red y no se tocó `data/eval/test/`.

## Preguntas que haría la cátedra en la defensa
- "¿No inflaste el hard pass rate al sacar los 'sin dato' de las violaciones?" → El cambio responde a la completitud real de DATAtourisme. Con la regla vieja, cualquier pedido con silla de ruedas daba cero itinerarios y se sesgaba contra las bodegas chicas (va contra H3). La incertidumbre no se esconde: sale como advertencia explícita al turista y se va a reportar como métrica aparte en el 007 (ADR-0012).
- "¿Por qué no dejar que el LLM decida si la bodega es accesible?" → Es una regla de negocio con tres estados exactos (`True`/`False`/`None`): va en código determinístico y se prueba con mutation testing (C.2, B.3). Dejar que el LLM complete el dato es justamente la alucinación por omisión que se quiere evitar (C.11).
- "¿Por qué dos funciones, `verificar` y `verificar_completo`?" → Para no romper el contrato que consumen el loop de reintento y la métrica, y para no editar unos 60 tests de 002 que no cambian de sentido (AGENTS.md). Las advertencias tienen otro destino: la respuesta al turista, no el reintento.
- "¿Qué pasa si el relevamiento (LLM) igual devuelve `restricciones_alimentarias`?" → Pydantic lo ignora por defecto. Está anotado en el ADR-0012: el prompt del 004 no la pregunta, y si aparece en las trazas se evalúa `extra="forbid"`.
