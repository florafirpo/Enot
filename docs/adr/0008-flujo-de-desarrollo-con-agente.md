# ADR-0008: Desarrollo con un agente nocturno bajo spec → tests → código, sensores y hooks

**Estado:** Aceptado
**Fecha:** 2026-11-23
**Decide:** Flora

## Contexto
Una sola persona, plazo 3/12. Un agente avanza de noche sin supervisión. La pregunta de la clase del
01/10 es cómo confiar en lo que dice que hizo sin leer cada línea.

## Decisión
- **Guías** (texto, el agente puede no cumplirlas): `AGENTS.md` corto, specs en `docs/specs/`,
  la skill `tarea-nocturna`.
- **Hooks** (determinísticos, `.claude/settings.json`): bloquean leer `.env`, editar la partición de
  test, pushear a `main` y comandos destructivos.
- **Sensores** (miden el resultado): `ruff`, `pytest`, mutation testing (`mutmut`) sobre la lógica
  crítica, y `scripts/tests_modificados.py`, que lista tests existentes modificados en la rama.
- **Revisión humana:** cada tarea es un PR que Flora aprueba a la mañana. Lo que no se puede
  cuantificar (separación de módulos, decisiones de arquitectura) se revisa a mano.
- Cada PR trae una sección "Para la defensa" con qué hace, por qué así y qué alternativas se descartaron.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Agente nocturno con PR obligatorio (elegida) | Avanza sin supervisión; todo pasa por revisión | Hay que revisar un PR por día |
| Agente con push directo a `main` | Más rápido | Sin red de seguridad; contradice la consigna de poder explicar todo |
| Sin agente | Control total | No llega al plazo |

## Consecuencias
- El historial de Git refleja el trabajo del agente y las revisiones; se explica en la exposición.
- La calidad depende de la calidad de los tests: por eso los tests van antes que el código y la lógica
  crítica pasa por mutation testing.

## Cómo se verifica
Los hooks tienen su test (`tests/test_hooks.py`). Cada PR muestra la salida de `make check` y, si
toca lógica crítica, el puntaje de mutation testing.
