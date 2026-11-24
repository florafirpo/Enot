# ADR-0006: Cliente de LLM propio, agnóstico al proveedor, con salida estructurada y trazas

**Estado:** Aceptado
**Fecha:** 2026-11-23
**Decide:** Flora

## Contexto
La consigna pide justificar el modelo y comparar costo y latencia, idealmente contra un modelo local.
Hay que poder cambiar de proveedor sin tocar los nodos, y registrar tokens y latencia de cada llamada.

## Decisión
`corpus/llm.py` (`ClienteLLM`) es la única puerta al LLM: OpenAI, Anthropic o cualquier endpoint
compatible con OpenAI (Ollama, vLLM) según `.env`. Toda salida se pide estructurada (JSON Schema
desde Pydantic), se valida y, si no valida, se reintenta una vez devolviendo el error.
Cada llamada se registra en una traza JSONL (nodo, modelo, tokens, latencia, intento).
Temperatura 0 en extracción y verificación; el planificador puede usar temperatura > 0 para que los
reintentos exploren alternativas (clase del 05/11).

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Cliente propio mínimo (elegida) | ~200 líneas explicables; sin dependencias pesadas | Hay que mantenerlo |
| LangChain / LiteLLM | Muchos proveedores resueltos | Capa extra que hay que poder explicar en la defensa |
| SDK de un solo proveedor | Simple | Impide comparar modelos |

## Consecuencias
- Los tests usan un `ClienteFalso` con respuestas guionadas (`tests/conftest.py`).
- No se le pide al modelo su "confianza": no es una medida real (clase del 05/11).

## Cómo se verifica
`tests/test_llm.py`: el reintento ante JSON inválido, la adaptación de parámetros por proveedor y que
el esquema no tenga `$ref`.
