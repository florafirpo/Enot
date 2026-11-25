# Revisión · 006 · ronda 2
**Veredicto:** APROBADO
**Rama:** noche/2026-11-25-006 · **Commits revisados:** 6fc140c..7e6cea6

## Sensores (corridos por mí)
- ruff: All checks passed!
- pytest: 384 passed, 0 fallas (exit 0, offline). Son 380 de la ronda 1 más 3 parametrizaciones de `test_una_persona_habla_en_singular` y `test_escribir_set_falla_a_mitad_no_deja_nada`.
- registro (CHANGELOG + ADR): OK ("la rama trae entrada de CHANGELOG y ADR").
  - CHANGELOG: entrada de la ronda 2 dentro de la entrada del PR, que sigue arriba de todo.
  - ADR-0016: sumó en "Consecuencias" la limitación de los infactibles y la de las marcas `[singular|plural]`.
- mutation: eval/generador.py 1153/1221 (94%), 68 sobrevivientes. Coincide con el CHANGELOG.
  - Revisé uno por uno los 19 sobrevivientes de `escribir_set`. Todos son equivalentes o cosméticos: `encoding="UTF-8"`/`None`, `newline`, `indent`/`ensure_ascii` de `generacion.json`, `ignore_errors` del `rmtree` y el texto del mensaje de `SetExistente`.
  - `_numero` no tiene sobrevivientes.
- tests existentes modificados: "OK: no se modificó ningún test existente." Un detalle:
  - `HUELLA` y la versión de `test_huella_del_set_por_defecto` cambiaron en 6a230ef, que es un commit `tests:` separado. Ahí la huella quedó como `"PENDIENTE"`, y el valor real se completó en el commit `fix:` b6967b1.
  - Es un valor de regresión (snapshot) que solo se conoce con el código nuevo. Está declarado en el mensaje del commit y en el reporte, y el archivo es nuevo en la rama. No lo considero una violación.

## Hallazgos
1. [menor] eval/generador.py:551-552: la atomicidad cubre casi todo, pero no el paso final.
   - Si falla el `replace` en el segundo, tercer o cuarto elemento, `dev/` ya quedó movido a `destino` y la próxima corrida da `SetExistente`. Pasaría, por ejemplo, si alguien crea `test/` entre el chequeo y el movimiento.
   - Si el proceso muere con SIGKILL, queda una `.generando-<pid>` huérfana. No bloquea la próxima corrida, pero ensucia `data/eval/`.
   - El test fuerza la falla en `json.dumps`, antes de mover nada, así que no ejercita este caso. Es una ventana mínima y el docstring promete "no deja nada" (lineamientos F, prolijidad del generador).
   Cómo resolverlo: alcanza con una línea en el docstring que diga que el movimiento final no es atómico entre los cuatro elementos. Otra opción es mover `test/` primero y, si falla un `replace` posterior, revertir los anteriores. No hace falta otra ronda por esto.

## Lo que está bien
- El hallazgo importante de la ronda 1 quedó bien resuelto y sin inventar alcance:
  - ADR-0016 declara que `bodegas_por_dia` y `zonas_mismo_dia` no viajan en `PerfilViaje` y que `zona_fuera` sale como `zona_desconocida`.
  - Se corrigió la frase inexacta del reporte: ahora dice que el test compara el generador con su propio certificado, no con el verificador.
  - En `docs/feedback-flora.md` quedó la decisión con las tres opciones y una recomendación justificada, marcada para antes de congelar test (A regla madre, D.3, D.6, B.6).
- El arreglo de singular/plural es general, no un parche caso por caso: marcas `[sg|pl]` resueltas por `_numero` según `personas == 1`.
  - El test es significativo: falla si se ignora `personas` en cualquiera de las dos direcciones (todo en plural, o todo pasado a singular, por el `>= 60` de los grupos). También falla si quedan corchetes sin resolver.
  - Lo verifiqué generando el set en memoria: las 11 consultas de una persona de la semilla por defecto (q006, q026, q042, q045, q068, q094, q100…) quedan en primera del singular y suenan naturales.
  - Se subió `VERSION_GENERADOR` a 006.2 con huella nueva, como pide ADR-0007.
- El orden SDD se mantuvo en la ronda: spec 6fc140c → tests 6a230ef → fix b6967b1 → registro 7e6cea6. Además:
  - Los dos tests nuevos figuran por nombre en la spec.
  - `json.dumps` solo se usa dentro de la carpeta temporal, así que la falla forzada sí prueba la limpieza y no pasa por accidente.
  - `data/eval/` sigue sin tocarse.

## Preguntas que haría la cátedra en la defensa
- "Si el turista pide 7 bodegas en 3 horas y Enot le arma 3, ¿cuenta como acierto?" → Hoy el perfil no guarda la cantidad pedida, así que el verificador no lo detecta. Está declarado en ADR-0016. Decidí [extender `PerfilViaje` y el verificador / criterio de "bien detectado" en el 007 / limitación reportada] antes de congelar test.
- "¿Cómo garantizan que el set no se escriba a medias?" → `escribir_set` arma todo en una carpeta temporal hermana y lo mueve al final; si algo falla, la borra. Lo prueba un test con una falla forzada que después vuelve a correr y genera el set completo. El único hueco es el movimiento final entre los cuatro archivos.
- "¿Por qué cambiaron la huella del set?" → Porque cambió el texto de las consultas de una persona (singular). Cada cambio de texto sube `VERSION_GENERADOR`, y el test de huella obliga a hacerlo. Test todavía no existe, así que no se regeneró nada congelado.
