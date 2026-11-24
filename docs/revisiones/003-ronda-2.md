# Revisión · 003 · ronda 2
**Veredicto:** APROBADO
**Rama:** noche/2026-11-24-003 · **Commits revisados:** 6d3beb9..0cd887c (arreglos de la ronda 1; el resto de la rama ya se revisó en la ronda 1, 9e2872f..051f731)

## Sensores (corridos por mí)
- ruff: All checks passed
- pytest: 254 passed, offline (eran 250: suma 4 tests nuevos)
- registro (CHANGELOG + ADR): OK. La entrada de CHANGELOG suma un párrafo "Ronda 2" y ADR-0013 se actualizó con el criterio de zona, la alternativa `Literal` descartada y los tests nuevos.
- mutation: no es obligatorio, porque el diff no toca `enot/verificador.py`, `enot/tools/` ni `eval/metricas.py`. Igual lo corrí para chequear el reporte: `enot/retrieval.py` da 459/479 (95,8%), igual que el reporte. Ningún sobreviviente cae en `_coincide_zona`, `motivo_exclusion` ni `zonas_desconocidas`. Todos están en `EmbedderOpenAI`, `EmbedderConCache`, `_normalizar` e `Indice.__init__`, como en la ronda 1. `eval/retrieval.py` no lo volví a correr (el reporte dice 177/196).
- tests existentes modificados: "OK: no se modificó ningún test existente." Los cambios son solo agregados al final de `tests/test_retrieval.py` y `tests/test_eval_retrieval.py`.

## Estado de los hallazgos de la ronda 1
1. [importante, zona "Chablis"] **Resuelto.** `enot/retrieval.py:137-142` agrega `_coincide_zona`: todas las palabras de la zona pedida tienen que estar en la zona de la bodega. `enot/retrieval.py:282-286` agrega `Indice.zonas_desconocidas`, que da la señal que pedía C.11. ADR-0013 explica por qué se descartó el `Literal` con un motivo concreto: ataría `PerfilViaje` al pipeline y rechazaría "Chablis" en vez de entenderlo. La tabla de filtros de la spec está actualizada.
2. [menor, línea de la spec] **Resuelto.** `docs/specs/003-retrieval-hibrido.md:111-113`
3. [menor, k por defecto y `recuperados`] **Resuelto.** `test_buscar_k_por_defecto_es_10` (12 bodegas → 10) y `test_main_k_por_defecto_y_recuperados_cortados` (7 candidatas → 2 con `--k 2`) matan los mutantes `k=11` y `k=None`.
4. [menor, decisiones de Flora] **Resuelto.** Las tres decisiones están en `docs/feedback-flora.md` → "Decisiones pendientes", cada una con su recomendación.

## Hallazgos
1. [menor] enot/retrieval.py:137-142 — Las palabras de enlace también cuentan como palabras obligatorias. Probé `tokenizar`: "Chablis et Grand Auxerrois" (en francés), "Côte des Nuits" y "Hautes-Côtes de Nuits" (una denominación real) no coinciden con ninguna zona del corpus. No es una falla silenciosa porque `zonas_desconocidas` las informa (C.11). Pero el turista que escribe en francés, que es el idioma de los datos, va a recibir un "no reconozco la zona" evitable. — Lineamientos C.11: el sistema avisa, no adivina. Esto ya se cumple, así que es solo prolijidad.
   Cómo resolverlo (opcional, puede ir en 004 o 005): ignorar en `_coincide_zona` un conjunto chico de palabras vacías (y, et, de, des, du, la, le), con un caso en `test_filtro_zona_por_palabras`. No bloquea.
2. [menor] BACKLOG.md:62 — El arreglo del hallazgo 1 solo cierra el problema si el flujo (005) llama a `zonas_desconocidas` antes de declarar un pedido infactible. Hoy eso está escrito en la spec 003 y en ADR-0013, pero no en el ítem 005. Si 005 se olvida, vuelve el caso "Chablis → cero candidatas presentado como infactible", aunque con menos probabilidad gracias a la coincidencia por palabras. — Lineamientos B.6/C.11: lo que una tarea le deja a la siguiente tiene que llegar por el canal.
   Cómo resolverlo: sumar una línea al ítem 005 ("si `zonas_desconocidas(perfil)` no está vacía, avisar antes de buscar") o anotarlo en la spec de 005 cuando se escriba.

## Lo que está bien
- El orden SDD de la ronda está limpio: spec (6d3beb9, solo la spec) → tests (b8d3fed, solo tests) → fix (2a69760, solo `enot/retrieval.py`) → registro. Los tests nuevos están nombrados en "Cómo se verifica".
- Los tests nuevos son significativos. `test_filtro_zona_por_palabras` cubre el caso positivo ("Chablis", "grand auxerrois", "nuits"), el amplio ("Côte" → Nuits y Beaune, y no Hautes-Côtes), el negativo ("Jura"), el de "todas las palabras" ("Chablis Côte de Nuits" → nada) y el vacío ("  " → nada, que mata el `bool(palabras) and`). `test_zonas_desconocidas` mantiene el orden y falla con una implementación constante, con "devolver todas" o con una que ignore el perfil. Además prueba de punta a punta que `buscar` con "Chablis" ya no queda vacío.
- La decisión es defendible y queda registrada. Se eligió una combinación de las dos opciones propuestas, con la alternativa descartada en la tabla del ADR y la decisión de producto (filtro duro o blando) derivada a Flora con una recomendación.

## Preguntas que haría la cátedra en la defensa
- ¿Por qué no un enum de zonas en `PerfilViaje`, si C.7 dice que un enum impide inventar categorías? → Porque las zonas las genera el pipeline del corpus (incluso con zonas de respaldo por departamento) y el modelo de dominio quedaría atado a eso. Además, un enum rechazaría "Chablis" en vez de entenderlo. En su lugar, lo que el sistema no reconoce se informa con `zonas_desconocidas`, así que no se inventa nada ni se vacía nada en silencio (ADR-0013).
- ¿Qué pasa si el turista pide "Côte"? → Entran Côte de Nuits, Côte de Beaune y Côte Chalonnaise, y Hautes-Côtes no entra. Es una búsqueda amplia, pero explícita y probada en `test_filtro_zona_por_palabras`. El ranking (BM25 + embeddings + RRF) ordena después.
- ¿Y si pide una zona que no existe, como "Jura"? → `buscar` devuelve cero candidatas, pero `zonas_desconocidas` devuelve ["Jura"]. El flujo dice "no reconozco la zona Jura" en vez de "no hay itinerario posible".
- ¿Cómo sabés que k = 10 es el valor por defecto que pide ADR-0004? → Lo fijan `test_buscar_k_por_defecto_es_10` y `test_main_k_por_defecto_y_recuperados_cortados`, que se escribieron porque mutation testing mostró que `k=11` sobrevivía.
