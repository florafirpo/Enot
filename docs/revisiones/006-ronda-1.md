# Revisión · 006 · ronda 1
**Veredicto:** CAMBIOS
**Rama:** noche/2026-11-25-006 · **Commits revisados:** bd8cb46..27d20f5

## Sensores (corridos por mí)
- ruff: All checks passed!
- pytest: 380 passed, 0 fallas (exit 0; offline, ~2 s; la configuración oculta la línea de resumen, conté los 380 puntos)
- registro (CHANGELOG + ADR): OK ("la rama trae entrada de CHANGELOG y ADR"), con entrada nueva arriba en CHANGELOG y ADR-0016 con todas las secciones del template
- mutation: eval/generador.py 1115/1178 (95%), 63 sobrevivientes. Coincide con el reporte. No es obligatorio por AGENTS.md, pero se justifica porque el módulo etiqueta la métrica principal.
- tests existentes modificados: "OK: no se modificó ningún test existente." (79bb365 y los dos commits `tests:` posteriores solo tocan `tests/test_generador.py`, que es nuevo en esta rama)

## Hallazgos
1. [importante] eval/generador.py:376-394 (más ADR-0016 "Consecuencias" y "Para la defensa" del reporte): 14 de los 20 infactibles dependen de restricciones que el sistema no puede representar. Son los 7 de `demasiadas_bodegas` y los 7 de `zonas_lejanas`.
   - La imposibilidad sale de `bodegas_por_dia` y `zonas_mismo_dia`, que son campos de `Consulta`, no de `PerfilViaje` (enot/modelos.py:91-104). Ni el relevamiento, ni el verificador, ni ningún prompt de `enot/` tienen un concepto de "N bodegas" o de "zonas el mismo día" (lo verifiqué con grep).
   - Ejemplo concreto: con q090 ("7 bodegas en un solo día… entre las 10:00 y las 13:00"), Enot extrae un perfil con jornada 10–13 y sin cantidad de bodegas. Arma, digamos, 3 visitas, el verificador lo da por factible y el flujo responde `tipo="itinerario"`. Con q085 (Chablis y Côte de Nuits a pie), el filtro de zonas admite bodegas de cualquiera de las dos, y un itinerario en una sola zona pasa el verificador.
   - Los 6 de `zona_fuera_de_borgona` salen por `tipo="zona_desconocida"` (ADR-0015), no por "infactible".
   - Por eso "infactibles bien detectados" en el 007 mediría por construcción algo que ninguna pieza determinística del sistema puede detectar.
   - Además, el reporte dice en "Para la defensa" que el certificado usa "las mismas constantes que usa el verificador, y un test exige que coincidan en los 100 casos". Eso es inexacto: el test compara el generador con su propio certificado, no con el verificador. La cátedra pide que la etiqueta y la métrica estén alineadas con la lógica de negocio y que lo declarado sea verificable (A, regla madre; D.3 scoring function = lógica de negocio; D.6 Goodhart; F "el generador se evalúa").
   Cómo resolverlo: no hace falta tocar `enot/` en este PR.
   - (a) Corregir la frase del reporte.
   - (b) Agregar a "Consecuencias" de ADR-0016 que esas restricciones no viajan en `PerfilViaje` y que `zona_fuera` sale como `zona_desconocida`.
   - (c) Sumar una decisión pendiente en `docs/feedback-flora.md` con las opciones:
     - extender `PerfilViaje` y el verificador con `bodegas_por_dia` y `zonas_mismo_dia` (ítem nuevo, antes del 007);
     - definir en el 007 que la respuesta cuenta como bien detectada si es `infactible` o `zona_desconocida`, o si el itinerario explica que no entra y propone una alternativa (PRD: "explica por qué no entra y propone una alternativa"), lo cual exige un criterio en código o en el juez;
     - dejarlo como limitación reportada.
   - Esto conviene decidirlo **antes** de congelar test, porque es el mismo momento irreversible que ya se le pide decidir a Flora.
2. [menor] eval/generador.py:269-271, 96-102 y plantillas con "Tenemos/Queremos": algunas consultas mezclan singular y plural. Lo vi corriendo el generador en el scratchpad: q026 "Viajo solo. Tomamos más que nada blancos", q042 y q045 "Viajo sola. Tenemos un tope…", q068 "Voy sola, nos movemos…", q094 y q100 "Viajo solo/sola. Queremos visitar…". La revisión manual del 20% lo va a marcar como error de redacción y, una vez congelado test, ya no se corrige. Además, "Viajo sola… Tenemos" deja ambigua la cantidad de personas justo en un campo obligatorio. (lineamientos F, D.1)
   Cómo resolverlo: con `personas == 1`, que las frases de preferencia y las plantillas usen la primera persona del singular, o excluir 1 persona de las plantillas en plural. Después subir `VERSION_GENERADOR` y la huella.
3. [menor] eval/generador.py:514-533: la escritura "todo o nada" no es atómica. Si falla algo después de `_jsonl(dev)`, por ejemplo al escribir test o `generacion.json`, queda `dev/` escrito y `escribir_set` ya no se puede volver a correr sin borrar a mano.
   Cómo resolverlo: escribir en un directorio temporal hermano y renombrar al final, o documentarlo en el docstring como limitación conocida.

## Lo que está bien
- El certificado de infactibilidad como prueba en código, conservador (par de comunas más cercano, cota de 30 min sin traslados) y con bordes testeados (6×30 = 180 → None, 7 → texto; Côte de Nuits + Beaune en bici → None). Se tomó la decisión de reformular el ejemplo del PRD en lugar de etiquetar algo que no se puede demostrar, y se explica en el ADR. Es exactamente C.2 y D.6.
- Disciplina SDD y de verificación impecable: spec → tests → código en commits separados, los 30 tests de "Cómo se verifica" existen con ese nombre, huella del set por versión, y mutation reproducido por mí (1115/1178) con los sobrevivientes explicados uno por uno en el reporte.
- Buen criterio de alcance con lo irreversible: no se escribió `data/eval/` (no aparece en el diff ni en el working tree), la escritura no pisa nada si `dev/` o `test/` existen (con test byte a byte), y la decisión sobre paráfrasis y congelamiento se escaló a Flora con recomendación y alternativa (B.6, D.1).

## Preguntas que haría la cátedra en la defensa
- "Si el turista pide 7 bodegas en 3 horas y Enot le arma 3, ¿eso cuenta como acierto o como error?" → Hoy el perfil no guarda la cantidad pedida, así que el verificador no puede marcarlo. Decidí [extender el perfil / evaluarlo en el 007 con el criterio X / reportarlo como limitación], y por eso los infactibles se miden así.
- "¿Cómo saben que un infactible lo es de verdad?" → `certificado_infactible` lo demuestra con código para cualquier corpus (visitas mínimas contra la jornada, o traslado mínimo entre las comunas más cercanas de dos zonas usando las constantes de `enot/tools/distancias.py`). Un test exige que los 20 infactibles tengan certificado y que ninguno de los 80 factibles lo tenga.
- "¿Cómo miden la calidad de un set sintético?" → Con la revisión manual estratificada del 20% (12 dev + 8 test): `tasa_error_revision` da la tasa global y por escenario, y cada consulta guarda su plantilla para ubicar dónde falla el generador.
- "¿Por qué no parafrasear siempre con el LLM?" → Rompe la reproducibilidad bit a bit y puede perder datos. Por eso es opcional y solo se acepta si conserva las anclas (números, días, horas, zonas, idioma, transporte) y no duplica otra consulta. Las etiquetas nunca las toca el LLM.
