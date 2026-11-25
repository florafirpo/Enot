# ADR-0017: Métricas del benchmark en código y baselines B0/B1/B2 comparables

**Estado:** Propuesto
**Fecha:** 2026-11-25
**Decide:** Flora

## Contexto
ADR-0007 fija qué se mide (hard pass rate, alucinación, cobertura + Gini, infactibles bien detectados) y contra qué
(B0 zero-shot, B1 determinístico, B2 ablación), pero no cómo se calcula cada cosa. Hay varios huecos donde un número
podría verse bien sin significar nada (lineamientos D.3 y D.6):
- **Itinerario vacío.** El verificador no mira la estructura: uno vacío, o con los días cambiados, no tiene
  violaciones.
- **B2.** Con `max_intentos = 1`, el flujo igual rechaza la propuesta inválida y responde "infactible", así que B2
  parecería honesto y no aislaría el aporte del verificador.
- **Infactibles.** 14 de 20 dependen de restricciones que `PerfilViaje` no tiene (ADR-0016). Cómo contarlos es una
  decisión pendiente de Flora.
- **B0.** Habla de bodegas por nombre y afirma precios: hay que poder decir cuánto inventa.

## Decisión
1. **Hard pass, todo o nada, contra la etiqueta.** Solo sobre consultas factibles. Cuenta como acierto si se cumplen
   las cuatro condiciones:
   - el sistema entregó un itinerario (tipo `itinerario`);
   - la estructura es la que pide el perfil: un día por día del viaje, el día de la semana correcto y al menos una
     visita por día;
   - el verificador de producción no marca violaciones contra `consulta.restricciones`, no contra el perfil que
     extrajo el sistema;
   - no hay afirmaciones inventadas (el "chequeo extra" de ADR-0007).

   Las advertencias no cuentan (ADR-0012). Una consulta sin salida es una falla.
2. **Alucinación = inventadas / afirmaciones verificables.** Se cuenta una afirmación por cada visita (la bodega),
   por cada experiencia nombrada y por cada precio afirmado. Un precio es inventado si difiere en más de 0,01 EUR del
   precio en EUR del corpus; sin experiencia, se compara con la más barata, como la tool de costos. Lo que se afirma
   sobre una bodega inexistente es todo inventado. Los horarios inventados aparecen como `cerrada` en el hard pass:
   el itinerario propone horas de visita, no afirma horarios de apertura.
3. **Cobertura y Gini** sobre los itinerarios entregados. Solo cuentan las bodegas del corpus y el Gini incluye las
   que nunca se recomendaron (ceros).
4. **Infactibles bien detectados, sin depender de la decisión pendiente.** Cuenta como detectado si la respuesta es
   `infactible` o `sin_candidatas`, o `zona_desconocida` cuando el motivo es una zona fuera de Borgoña. Esta última
   es la opción (b) que el feedback recomendó para "mientras tanto". El reporte trae tres números: la tasa sobre
   todos los infactibles, la tasa por motivo y la tasa sobre los representables (hoy solo zona fuera de Borgoña).
   Si Flora elige (a), las métricas no cambian: los infactibles pasan a salir como `infactible`. Si elige (c), se
   reporta la tasa de representables.
5. **Baselines:**
   - **B0**: una llamada con el texto del turista, sin corpus. Los nombres se resuelven contra el corpus por nombre
     normalizado; lo que no se resuelve queda como `b0:<nombre>`, que el verificador marca como inexistente.
   - **B1**: el perfil etiquetado (un formulario), los filtros de `retrieval.filtrar` y un greedy por cercanía que
     usa el **verificador como oráculo** sobre el itinerario parcial, así que no reimplementa ninguna regla.
   - **B2**: un intento y **entrega la primera propuesta aunque el verificador la rechace**: sin loop no hay
     guardia.
   - **Enot**: el flujo completo.
6. **Reporte reproducible.** `reports/eval_<split>_<fecha-hora>.json`, que nunca pisa una corrida anterior. Guarda
   la configuración (versión del generador, commit, modelo, embeddings, `max_intentos`, `k`, tope de tokens), las
   métricas, la evaluación por consulta y las salidas con tokens y latencia, para el ítem 008. Una excepción de un
   sistema deja una salida `error` y la corrida sigue.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Hard pass con estructura + verificador + alucinación, contra la etiqueta (elegida) | Un itinerario vacío o inventado no suma; mide el sistema entero, relevamiento incluido | Comparte código con el sistema que mide (ya declarado en ADR-0007; lo mitigan los tests de mutation) |
| Hard pass = solo `verificar(...) == []` | Es literal a ADR-0007 | Un itinerario vacío, o con días corridos, cuenta como acierto |
| Verificar contra el perfil que extrajo el sistema | No penaliza dos veces | Esconde los errores del relevamiento, que son errores reales frente al turista |
| B2 = `max_intentos=1` del flujo tal cual | No hay que agregar código | El verificador sigue de guardia, así que no aísla su aporte; B2 sumaría infactibles "detectados" falsos |
| B1 que reimplementa las reglas en el greedy | Más rápido | Dos fuentes de verdad: B1 podría "pasar" por una regla mal copiada |
| B1 por ranking de retrieval (BM25 + embeddings) | Mejor ajuste blando | Necesita embeddings y deja de ser "sin LLM ni modelos" |
| Infactibles con juez LLM ("explica por qué no entra") | Captura respuestas que explican sin decir `infactible` | Juez sin calibrar todavía (ítem 008); depende de la decisión de Flora |

## Consecuencias
- Más fácil: comparar los cuatro sistemas con el mismo código; `make eval SISTEMAS=B1` corre sin claves; el reporte
  alcanza para el 008 sin volver a correr.
- **B1 tiene ventaja.** Recibe el perfil etiquetado y no paga errores de relevamiento. Hay que decirlo al presentar
  H1/H2.
- **Con fichas sin horarios ni precios, el hard pass es alto para todos.** Con la regla de ADR-0009 (sin evidencia no
  hay violación), B1 sobre las 200 bodegas de la muestra real, que solo tienen coordenadas, da 98,75%. El número
  solo dice algo cuando la extracción completa horarios y precios. Hay que reportarlo junto con la completitud del
  corpus.
- **Infactibles.** Mientras `PerfilViaje` no tenga `bodegas_por_dia` ni `zonas_mismo_dia`, la tasa total va a ser
  baja para todos los sistemas, salvo B0, que puede decir "imposible". Se lee junto con el desglose.
- **B0 por nombre.** La resolución exige el nombre completo normalizado. Un nombre real con otra grafía ("Dom." por
  "Domaine") cuenta como inventado. Conviene revisar a mano las bodegas `b0:` de una corrida antes de reportar la
  tasa de alucinación de B0.
- Hay que revisarlo cuando Flora decida (a), (b) o (c) para los infactibles, y cuando exista el juez (008).

## Cómo se verifica
- `tests/test_eval.py`: casos armados a mano para cada métrica (estructura, afirmaciones, hard pass contra la
  etiqueta, advertencias que no cuentan, Gini, cobertura, infactibles por tipo y motivo, resumen por escenario).
- `tests/test_baselines.py`: B0 resuelve e inventa, B1 factible por construcción (presupuesto, idioma, apertura,
  segunda franja, máximo por día, sin repetir), B2 entrega la propuesta inválida y Enot la válida.
- `tests/test_correr_eval.py`: la corrida con el set real del generador y el corpus sintético, los errores de un
  sistema, el reporte que no pisa y que B1 no crea cliente LLM.
- `make mutation MODULO=eval/metricas.py`: 326/328.
