# ADR-0016: Set de evaluación desde plantillas, infactibles probados por código y set congelado por decisión de Flora

**Estado:** Propuesto
**Fecha:** 2026-11-25
**Decide:** Flora

## Contexto
ADR-0007 fija el qué: 100 consultas sintéticas con restricciones en JSON, 60 dev / 40 test, semilla fija, test
inmutable y el 20% revisado a mano. Faltaba el cómo (ítem 006), y hay cuatro fuerzas:
- La consigna exige que, si los datos son sintéticos, el generador se evalúe (lineamientos F). Una etiqueta mal
  puesta contamina la métrica principal sin que nadie lo note (Goodhart, lineamientos D.6).
- "Infactibles bien detectados" (PRD 6) necesita pedidos que sean imposibles de verdad. Si el generador marca como
  infactible algo que con el corpus real sí entra, el agente queda penalizado por resolverlo.
- Las consultas tienen que alcanzar para un turno: si al texto le falta un dato obligatorio, el relevamiento
  repregunta (ADR-0014) y la evaluación pasa a depender de un simulador de turista.
- Crear `data/eval/test/` es irreversible (hook, ADR-0007), y la paráfrasis con LLM (PRD 6) necesita la clave de
  Flora. Las dos cosas tienen que decidirse antes de escribir el set.

## Decisión
1. **Plantillas por escenario, etiqueta como `PerfilViaje`.** Cada consulta sale de una plantilla con slots y su
   etiqueta es el mismo modelo que produce el relevamiento, así el ítem 007 compara contra el verificador sin
   traducir. Todas traen los cuatro campos obligatorios. Cuotas 15/15/15/15/10/10/20 (días, transporte, presupuesto,
   grupo, idioma, accesibilidad, infactibles): múltiplos de 5, así 60/40 y 20% son exactos en cada escenario.
2. **Infactible solo con certificado.** `certificado_infactible` demuestra la imposibilidad para cualquier corpus y
   usa las mismas constantes que la tool de traslados (ADR-0005). Hay tres motivos:
   - más visitas de 30 min que minutos de jornada;
   - dos zonas el mismo día cuyo traslado más corto (par de comunas de referencia más cercano) no entra en la jornada;
   - una zona fuera de Borgoña.

   Un test exige que toda consulta infactible tenga certificado y que ninguna factible lo tenga. El ejemplo del PRD
   "8 bodegas entre Chablis y el Mâconnais" se reformula, porque con auto y 9 horas no es demostrablemente imposible.
3. **Paráfrasis opcional y controlada.** Una paráfrasis se acepta solo si conserva las anclas de la consulta, es
   decir los valores con que se llenó la plantilla (números, días, horas, zonas, idioma, transporte), y si no repite
   otra consulta. Si no, queda la plantilla. Las etiquetas nunca las toca el LLM.
4. **El set se versiona por huella.** Un test fija el hash del set de la semilla por defecto junto a
   `VERSION_GENERADOR`: si cambia una plantilla, hay que subir la versión.
5. **Escritura todo o nada, y el set real lo genera Flora.** `escribir_set` no escribe nada si `dev/` o `test/` ya
   existen, para no regenerar dev con otra versión y filtrar consultas de test. En esta corrida no se escribe
   `data/eval/`: congelar test, y antes decidir si se parafrasea, le corresponde a Flora (`docs/feedback-flora.md`).

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Plantillas + certificado + paráfrasis con anclas (elegida) | Etiquetas correctas por construcción; infactibles demostrables; reproducible; la tasa de error se mide sobre lo que de verdad puede fallar (redacción) | Textos más regulares que pedidos reales; el certificado solo cubre tres tipos de imposibilidad |
| El LLM genera consulta y etiqueta | Más variedad de lenguaje | Etiquetas sin garantía; no reproducible; el benchmark mediría al generador |
| Infactibles según el corpus real (correr el verificador con todas las combinaciones) | Captura más casos (presupuesto, idioma) | Depende de un corpus que todavía cambia (extracción del 24–25/11); la etiqueta cambiaría con cada corrida del pipeline |
| Escribir y congelar el set en esta corrida | El ítem 007 lo tiene ya | Irreversible sin Flora; sin paráfrasis ya no se puede agregar después |
| Pedidos multi-turno con simulador de turista | Prueba el relevamiento | Otro LLM en la evaluación; fuera del alcance del 006 |

## Consecuencias
- El ítem 007 puede leer `Consulta.restricciones` y `infactible` directamente y medir "infactibles bien detectados"
  sobre 8 casos de test (no 4).
- Idioma y accesibilidad casi siempre van a terminar en advertencias (ADR-0012): con 10 consultas cada uno, aportan
  poco a H1 y mucho al análisis de fallas.
- Las consultas factibles no tienen garantía de factibilidad con el corpus real: un "factible" puede no tener
  solución. El ítem 007 tiene que reportar esos casos aparte (el verificador lo dice) y no contarlos como
  alucinación.
- Si Flora decide parafrasear, el set deja de ser reproducible bit a bit (`generacion.json` registra cuántas
  paráfrasis se aceptaron). Las etiquetas siguen siendo las mismas.
- **Limitación (revisión 006 ronda 1).** Hoy el sistema no puede detectar 14 de los 20 infactibles, y la
  consulta guarda esas restricciones sin que el sistema las lea:
  - `bodegas_por_dia` y `zonas_mismo_dia` son campos de `Consulta`, no de `PerfilViaje`. Ni el relevamiento ni el
    verificador los conocen. Con "7 bodegas en 3 horas", Enot puede armar 3 visitas, el verificador las da por
    válidas y el flujo responde con un itinerario.
  - `zona_fuera_de_borgona` sale como `zona_desconocida` (ADR-0015), no como "infactible".

  El certificado demuestra que el pedido es imposible, pero no que el sistema lo pueda detectar. Antes de congelar
  test, Flora decide si el perfil y el verificador se extienden o con qué criterio cuenta el 007 una "detección"
  (`docs/feedback-flora.md`).
- Las anclas y las marcas `[singular|plural]` de las plantillas son parte de la versión: con una persona, el texto
  va en singular (revisión ronda 1, versión 006.2).
- Revisar después de la revisión manual del 28/11: si la tasa de error de alguna plantilla es alta, se corrige, se
  sube `VERSION_GENERADOR` y, si test ya existe, se documenta como limitación (test no se regenera).

## Cómo se verifica
`tests/test_generador.py` cubre:
- determinismo y huella por versión;
- cuotas, unicidad, y que la etiqueta coincida con el texto;
- que todo infactible tenga certificado y ningún factible lo tenga, con los bordes del certificado;
- la partición 60/40 y la muestra del 20%, estratificadas;
- la escritura todo o nada;
- la tasa de error desde la planilla;
- la paráfrasis aceptada, rechazada o duplicada.

Mutation sobre `eval/generador.py` en el reporte de la corrida. La tasa de error real sale de
`tasa_error_revision(data/eval/revision_manual.csv)` cuando Flora complete la columna `correcta`.
