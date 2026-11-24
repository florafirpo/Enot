# ADR-0003: Workflow fijo con verificador determinístico (generar → verificar), no un agente ReAct libre

**Estado:** Aceptado
**Fecha:** 2026-11-23
**Decide:** Flora

## Contexto
Preguntas de arquitectura (clase del 01/10):
- **Quién lo usa:** un turista hispanohablante, por chat, una conversación a la vez. No hay usuarios
  concurrentes en el MVP.
- **Con qué sistemas se comunica:** un proveedor de LLM (API o modelo local), el corpus en archivos
  locales, un índice de búsqueda local y, opcionalmente, OSRM para distancias. Nada más.
- **Qué latencia se busca:** menos de 30 s para el primer itinerario y menos de 10 s por ajuste (PRD 9).
- **Qué tiene que ser confiable:** que el itinerario sea factible (horarios, traslados, presupuesto).
  Es una tarea verificable, así que se puede tener un criterio automático.

Siguiendo la secuencia de la clase del 08/10 para elegir el patrón: los pasos se pueden escribir de
antemano (relevar → buscar → planificar → verificar → responder), así que no hace falta un orquestador
autónomo. Además, encadenar muchos pasos decididos por el modelo compone errores (0,9²⁰ ≈ 0,12).

## Decisión
Un **workflow fijo** de cinco nodos con un único loop acotado:

1. `relevamiento` (LLM, salida estructurada `PerfilViaje`)
2. `retrieval` (código: filtros + búsqueda híbrida, ADR-0004)
3. `planificador` (LLM con tools de cálculo, salida estructurada `Itinerario`)
4. `verificador` (código puro: devuelve la lista de violaciones)
5. `respuesta` (LLM redacta en español con las fuentes)

Si el verificador encuentra violaciones, se las devuelve al planificador y se reintenta, con un
**circuit breaker de 3 intentos** y un tope de tokens por conversación. Si no se logra, el sistema
explica qué restricción no se puede cumplir. Es el patrón evaluador-optimizador / LLM-Modulo.

El estado de la conversación (perfil + itinerario vigente) vive en un objeto `Sesion` serializable;
los nodos son funciones puras sobre ese estado, lo que permite testearlos por separado.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Workflow fijo + verificador en código (elegida) | Testeable por nodo; criterio de corte objetivo; costo y latencia acotados | Menos flexible ante pedidos fuera del guion |
| Agente ReAct con todas las tools | Flexible | Errores compuestos, costo variable, difícil de evaluar; el LLM puede declarar éxito sin serlo (reward hacking) |
| Solver determinístico puro (sin LLM en la planificación) | Factibilidad garantizada | No entiende preferencias blandas; es el plan B (PRD 7) y la base del baseline B1 |
| Framework de grafos (LangGraph u otro) | Trazas y estado resueltos | Dependencia extra que hay que poder explicar; el grafo es lineal y cabe en ~100 líneas |

## Consecuencias
- Cada nodo tiene contrato Pydantic de entrada y salida y su propio test.
- La ablación B2 (sin loop de verificación) sale de un parámetro (`max_intentos=1`).
- Agregar autonomía después (por ejemplo, que el planificador decida cuándo buscar más bodegas) es
  posible sin cambiar los contratos.

## Cómo se verifica
- `tests/test_verificador.py`: cada tipo de violación tiene un caso que debe detectarse y uno que no.
  Mutation testing obligatorio sobre `enot/verificador.py`.
- `tests/test_flujo.py`: con un LLM falso que primero propone un itinerario inválido, el flujo
  reintenta y termina con uno válido; con uno que siempre falla, corta en 3 intentos.
