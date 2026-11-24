# ADR-0014: Nodos con LLM: el código decide, el LLM extrae, elige y redacta dentro de salidas acotadas

**Estado:** Propuesto
**Fecha:** 2026-11-24
**Decide:** Flora (propuesto por el agente en el ítem 004; spec 004)
**Complementa:** ADR-0003 (workflow de cinco nodos), ADR-0005 (el LLM no calcula), ADR-0006 (`ClienteLLM` y trazas)

## Contexto
ADR-0003 fija tres nodos con LLM (relevamiento, planificador, respuesta) y ADR-0006 la puerta única al modelo.
Al implementarlos (ítem 004) hubo que decidir, en cada nodo, qué parte es del modelo y qué parte es código.
Lo que estaba en juego:
- **Confiabilidad.** El LLM completa lo que falta con algo plausible (lineamientos C.11), inventa categorías si
  la salida es libre (C.7) y no hace bien aritmética de fechas, distancias ni sumas (C.2, ADR-0005).
- **Testeabilidad.** Cada nodo tiene que poder probarse con un `ClienteFalso` (ADR-0003) y lo que se decide en
  código, sin LLM.
- **Contexto.** Pasar solo lo que sirve de cada ficha (C.12) y tratar el texto de fichas y del turista como dato
  (C.9).
- **Observabilidad.** Un evento por llamada con tokens, latencia y errores, base del reporte de costos (D2, E).
- `ClienteLLM.estructurado` no soporta tool calling: solo pide una salida que valide contra un esquema.

## Decisión
1. **Relevamiento: el LLM extrae un `BorradorPerfil` (todo opcional) y el código decide.**
   `perfil_desde_borrador` calcula qué obligatorios faltan (`cantidad_dias`, `dia_inicio`, `transporte`,
   `personas`), valida contra `PerfilViaje` y, si algo falta o no valida, devuelve una `Pregunta` con **texto fijo
   por campo** escrito en código. Si el turista dio una fecha completa, el día de la semana lo calcula el código;
   si la fecha y el día que dijo no coinciden, se repregunta. El relevamiento es sin estado: reextrae todo el
   historial en cada turno.
2. **Planificador: tiempos precalculados en el contexto y salida acotada por esquema.** En vez de darle tools,
   el contexto trae la matriz de tiempos de traslado entre candidatas, calculada con `tiempo_traslado` en el
   transporte del perfil (con k = 10 candidatas son 45 pares), y los días del viaje ya resueltos. La salida se
   pide con un modelo Pydantic armado para esa llamada: `bodega_id` es un `Literal` con los ids de las
   candidatas (en el JSON Schema, un `enum`) y `dias` tiene exactamente `cantidad_dias` elementos. Si el modelo
   se sale, no valida y `ClienteLLM` reintenta con el error (ADR-0006); no hace falta que el verificador lo
   descubra. Número y día de la semana de cada día los pone el código.
3. **Respuesta: el LLM redacta introducción y motivos; los números los pone el código.** `render_itinerario`
   arma horarios, precios (con `costo_experiencias`), traslados (con `tiempo_traslado`), fuentes y la sección
   "Para tener en cuenta" con todas las advertencias del verificador (ADR-0012). Los motivos de bodegas que no
   están en el itinerario se descartan.
4. **Trazas.** `enot/trazas.py`: un JSONL por conversación en `data/trazas/`, un `EventoTraza` por llamada
   (nodo, intento del loop, proveedor, modelo, inicio UTC, latencia, tokens, intentos de validación, estado y
   error). Los errores del cliente se registran y se relanzan como `ErrorNodo`, que dice qué nodo falló. En un
   evento con error, tokens e intentos quedan en `None` (desconocidos), no en 0: `ClienteLLM` puede haber hecho
   llamadas pagas antes de lanzar y no las informa (revisión 004 ronda 1).
5. **Prompts** en `enot/prompts/*.md` (reglas en el mensaje de sistema); los datos van en el mensaje de usuario
   entre etiquetas (`<conversacion>`, `<candidatas>`, `<itinerario>`). En el texto del turista se neutralizan
   `<` y `>` para que no pueda cerrar la etiqueta.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Relevamiento: el código decide qué falta y escribe la pregunta (elegida) | Determinístico y testeable; el LLM no puede dar por completo un perfil incompleto | Preguntas menos naturales |
| Relevamiento: el LLM devuelve "perfil o pregunta" | Conversación más fluida | El LLM decide cuándo alcanza (C.11); difícil de testear sin LLM real |
| Planificador: tiempos precalculados en el contexto (elegida) | Sin tool calling, una sola llamada, costo y latencia acotados; el LLM no estima distancias | El contexto crece con k² pares (con k = 10, ~45 líneas) |
| Planificador: tools (`tiempo_traslado`, `abierta_en`) en un loop de tool calling | Escala a muchas candidatas; es lo que nombra ADR-0003 | Hay que extender `ClienteLLM` para tres proveedores; más llamadas y trayectorias variables (C.3) |
| Salida del planificador con `bodega_id: str` libre | Esquema fijo, reutilizable | El LLM puede inventar ids; lo descubre recién el verificador y gasta un intento del loop |
| Respuesta: el LLM escribe todo el texto | Más natural | Puede copiar mal horarios o precios, u omitir advertencias (C.11, ADR-0012) |
| Trazas con MLflow o Langfuse | Interfaz para consultar | Dependencia y servicio extra; D2.4 dice que lo que importa es qué se registra |

## Consecuencias
- Todo número del detalle del itinerario (horarios, precios, traslados, total) sale de las tools (ADR-0005) y el
  detalle no puede contradecir al verificador. La introducción y los motivos son texto libre del LLM: que no
  traigan horarios ni precios lo pide solo el prompt `respuesta.md`, no lo controla el código (revisión 004 ronda 1).
  Si en las pruebas aparecen números ahí, el próximo paso es un chequeo en código que descarte el motivo.
- El costo de las llamadas que fallan no se mide: el evento queda con tokens `None`. Para medirlo, el error de
  `ClienteLLM` tiene que traer los tokens consumidos (toca `corpus/llm.py`; anotado en el ítem 008). El reporte de
  costos tiene que contar los eventos con tokens desconocidos en vez de sumarlos como 0.
- Agregar candidatas hace crecer el contexto del planificador de forma cuadrática. Si en dev hace falta k > 15,
  hay que revisar esto: pasar a tools o mandar solo los pares de la misma zona.
- Las preguntas fijas son poco naturales. Si las pruebas de Flora (26–27/11) muestran que molestan, el LLM puede
  reescribirlas sin cambiar los `faltantes`, que siguen saliendo del código.
- ADR-0006 permite temperatura > 0 en el planificador, pero `ClienteLLM` usa 0 fijo. Cambiarlo toca
  `corpus/llm.py` y queda para cuando el loop (005) muestre que los reintentos repiten la misma salida.
- El costo en USD se calcula en el reporte (ítem 008) a partir de los tokens de la traza.

## Cómo se verifica
- `tests/test_nodos.py`: `test_relevar_repregunta_si_falta_un_obligatorio`, `test_relevar_no_confia_en_el_llm_para_completar`,
  `test_relevar_fecha_calcula_dia_de_semana` (decisión 1); `test_planificar_rechaza_bodega_fuera_de_candidatas`,
  `test_planificar_exige_cantidad_de_dias`, `test_modelo_salida_planificador_esquema`, `test_contexto_planificador_exacto`
  (decisión 2); `test_render_itinerario_exacto`, `test_responder_incluye_advertencias_aunque_el_llm_no`,
  `test_responder_usa_motivos_solo_de_paradas_del_itinerario` (decisión 3); `test_cada_nodo_registra_un_evento`,
  `test_error_del_cliente_se_registra_y_relanza` y `test_evento_traza_tokens_desconocidos` (decisión 4); `test_relevar_mensaje_exacto_y_texto_del_turista_escapado`,
  `test_contexto_planificador_ficha_es_dato` (decisión 5); `test_con_la_muestra_real_de_datatourisme` (formato real).
- `tests/test_trazas.py`: escritura, lectura y validación de eventos.
- Mutation testing sobre `enot/nodos.py` y `enot/trazas.py` (no obligatorio; resultados en el reporte de la corrida).
