# ADR-0015: Flujo por turnos sobre una `Sesion`: circuit breaker contado desde la traza y ajuste como replanificación verificada

**Estado:** Propuesto
**Fecha:** 2026-11-24
**Decide:** Flora (propuesto por el agente en el ítem 005; spec 005)
**Complementa:** ADR-0003 (workflow con verificador y circuit breaker), ADR-0012 (advertencias), ADR-0014 (nodos)

## Contexto
ADR-0003 fija el workflow (relevar → buscar → planificar → verificar → responder), el loop con un tope de 3
intentos y "un tope de tokens por conversación", y pide una `Sesion` serializable. ADR-0014 dejó los nodos como
funciones sin estado. Al encadenarlos (ítem 005, tracer bullet) hubo que decidir:
- **Dónde vive el límite.** Lineamientos C.4: el tope tiene que ser un contador en el código, no una instrucción en
  el prompt. ¿Qué se cuenta y desde dónde?
- **Qué es un ajuste** ("sacá la segunda bodega", PRD 3.4). El planificador solo acepta ids de las candidatas
  (ADR-0014), así que si la búsqueda nueva no devuelve una bodega del itinerario vigente, el planificador no puede
  conservarla.
- **Qué ve el turista cuando no se puede.** Si el LLM redacta la explicación de un fracaso, puede suavizarlo o
  inventar una causa (C.11).
- **Qué pasa con lo ya hecho** si falla el modelo o se alcanza el tope a mitad de turno.
- Lo que se reporta en la evaluación (ítem 007): B2 necesita la propuesta del único intento aunque no sea válida.

## Decisión
1. **Un turno = `Flujo.turno(sesion, texto) -> Respuesta`.** Todo el estado vive en `Sesion` (historial, último
   perfil completo, itinerario vigente con sus advertencias, ruta de la traza) y se guarda como JSON. `Flujo` solo
   tiene configuración (cliente, corpus, índice, `max_intentos`, `tope_tokens`, `k`). `Respuesta.tipo` es un enum
   (`pregunta`, `itinerario`, `infactible`, `zona_desconocida`, `sin_candidatas`, `tope_tokens`, `error`) y trae la
   última propuesta y sus violaciones aunque no sea factible.
2. **Circuit breaker en código, contado desde la traza.** `max_intentos` (3; 1 = ablación B2) acota las llamadas al
   planificador por turno. `tope_tokens` (200 000 por conversación) se compara, antes de cada llamada al LLM, con la
   suma de tokens conocidos de la traza de la conversación (`tokens_usados`). La traza es la única fuente de verdad
   y sigue en el mismo archivo al retomar la sesión, así que el tope no se reinicia con `--sesion`.
3. **Ajuste = replanificar sobre el vigente, con el mismo verificador.** Con un itinerario vigente, el mensaje del
   turista se trata como pedido de ajuste: se vuelve a relevar (el perfil puede cambiar), las bodegas del vigente
   que siguen pasando los filtros duros se suman primero a las candidatas, y el planificador recibe el vigente como
   "itinerario anterior" y el pedido entre `<pedido>…</pedido>` (texto del turista como dato, C.9). En los
   reintentos, el itinerario anterior es la propuesta fallida, que ya trae el pedido aplicado: el vigente va aparte
   como referencia y el pedido se marca "ya aplicado: no lo apliques de nuevo; corregí los problemas", para que un
   "sacá la segunda bodega" no saque otra en el 2.º intento (revisión 005 ronda 1). El vigente solo se reemplaza
   por una propuesta factible; si el ajuste no se logra, el anterior sigue vigente y se le dice.
4. **Textos de borde escritos por código.** Infactible (qué condición no se cumplió, con `DESCRIPCION_VIOLACION`
   por tipo, más el detalle del último intento), zona desconocida (con las zonas que sí hay), sin candidatas (los
   motivos de exclusión más frecuentes dentro de la zona pedida) y tope alcanzado.
5. **No se tira trabajo válido ni se deja trabajo a medias.** Si hay un itinerario factible pero se alcanzó el tope
   o falla el nodo de respuesta, se entrega `render_itinerario` (detalle por código, con advertencias). Si un nodo
   falla antes de tener un itinerario válido, la sesión vuelve a como estaba antes del turno (historial y perfil).
6. **CLI** `python -m enot` con `--sesion`, `--fichas`, `--max-intentos`, `--tope-tokens` y `--k`; el flujo se
   inyecta para poder probarla sin red.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Tope de tokens sumado desde la traza (elegida) | Una sola fuente de verdad; sobrevive al retomar; es lo que se reporta en costos | Las llamadas con error no informan tokens (`None`, ADR-0014) y no suman: el tope se subestima en ese caso (lo acota igual `max_intentos`) |
| Contador de tokens dentro de `Sesion` | No relee el archivo | Dos fuentes que pueden divergir; hay que propagar el `Resultado` desde cada nodo |
| Tope en USD | Es lo que importa en la economía | Necesita tabla de precios por modelo; entra con el reporte del ítem 008 |
| Ajuste: replanificar con el vigente y el pedido (elegida) | El LLM interpreta el pedido; lo verifica el mismo código; reutiliza el reintento | Una llamada más por ajuste; el planificador puede cambiar más de lo pedido (solo lo frena el prompt) |
| Ajuste: edición determinística ("sacá la 2.ª" → borrar parada) | Sin LLM, barata | Hay que interpretar lenguaje natural con reglas; no cubre "más chico y familiar" |
| Ajuste: rehacer el itinerario desde cero | Simple | Contradice PRD 3.4 ("edita el vigente en lugar de rehacerlo") |
| Mensaje de infactible redactado por el LLM | Más natural | Puede suavizar o inventar la causa (C.11); una llamada más justo cuando ya se gastaron 3 |
| Clasificar la intención del mensaje (ajuste, pregunta, charla) | Evita replanificar ante un "gracias" | Una llamada y un nodo más; no lo pide el ítem (C.10) |
| Framework de grafos (LangGraph) | Estado y trazas resueltos | ADR-0003 ya lo descartó: el grafo es lineal y el flujo entero son ~250 líneas |

## Consecuencias
- El loop y los topes se prueban sin LLM real (`tests/test_flujo.py`) y la ablación B2 sale de un parámetro.
- `Respuesta.itinerario` + `violaciones` alcanzan para calcular el hard pass rate de Enot y de B2 en el ítem 007.
- Con un itinerario vigente, cualquier mensaje dispara relevamiento + planificación (+ respuesta): un "gracias"
  cuesta un turno entero. Si las pruebas de Flora (26–27/11) lo muestran, el paso siguiente es un clasificador de
  intención barato antes del planificador.
- El tope de 200 000 tokens es una estimación (un turno peor caso ≈ 25 000 tokens con k = 10): hay que revisarlo con
  las trazas reales de dev (ítem 007/008) y, cuando exista la tabla de precios, pasar a un tope en USD.
- Las bodegas del vigente se suman a las candidatas sin pasar por el ranking: en un ajuste el planificador puede
  ver hasta k + (paradas del vigente) candidatas, y el contexto crece (ADR-0014, k²).
- El historial guarda el texto completo de cada respuesta, que el relevamiento vuelve a leer en cada turno: el costo
  del relevamiento crece con la conversación.

## Cómo se verifica
- `tests/test_flujo.py`: `test_flujo_reintenta_y_termina_valido`, `test_flujo_corta_en_max_intentos_y_explica`,
  `test_max_intentos_1_es_la_ablacion_b2` (decisión 2, intentos); `test_tope_de_tokens_corta_el_loop`,
  `test_tope_alcanzado_por_el_relevamiento_no_planifica`, `test_sesion_ida_y_vuelta_y_tokens_continuan`,
  `test_tokens_usados_ignora_desconocidos` (decisión 2, tokens); `test_ajuste_edita_el_itinerario_vigente`,
  `test_ajuste_suma_las_bodegas_vigentes_a_las_candidatas`, `test_ajuste_reintento_no_reaplica_el_pedido`,
  `test_contexto_planificador_reintento_de_ajuste`, `test_ajuste_infactible_conserva_el_vigente` (decisión 3);
  `test_explicar_infactible_texto`, `test_descripcion_violacion_cubre_todos_los_tipos`,
  `test_zona_desconocida_avisa_sin_buscar`, `test_sin_candidatas_explica_por_que` (decisión 4);
  `test_tope_antes_de_responder_entrega_el_detalle_sin_llm`, `test_error_en_respuesta_degrada_al_detalle`,
  `test_error_de_nodo_no_ensucia_la_sesion` (decisión 5); `test_con_la_muestra_real_de_datatourisme` (formato real).
- `tests/test_cli.py` (decisión 6).
- Mutation sobre `enot/flujo.py` (no obligatorio): 361/378 (95%); los sobrevivientes son equivalentes (ver el reporte).
