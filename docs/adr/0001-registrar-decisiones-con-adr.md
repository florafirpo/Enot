# ADR-0001: Registrar las decisiones de arquitectura con ADRs y la historia con un changelog

**Estado:** Aceptado
**Fecha:** 2026-11-23
**Decide:** Flora

## Contexto
El TP lo desarrolla una sola persona con ayuda de un agente que trabaja de noche, en sesiones que no
comparten memoria. Cada sesión nueva arranca sin saber por qué el sistema está armado como está.
La defensa exige poder explicar cada decisión y las alternativas descartadas.

## Decisión
Cada decisión que afecta la estructura del sistema se registra en `docs/adr/NNNN-*.md` (formato de
`0000-template.md`). Cada cambio que llega a `main` suma una entrada en `CHANGELOG.md`.
`AGENTS.md` obliga al agente a leer ambos y a mantenerlos.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| ADR + changelog en el repo (elegida) | Persisten entre sesiones; versionados con el código; sirven de guion para la defensa | Hay que mantenerlos |
| Solo el historial de Git | Cero esfuerzo extra | No explica el porqué; difícil de leer para un agente |
| Wiki o doc externo | Más cómodo de editar | El agente no lo ve; se desincroniza del código |

## Consecuencias
- Cualquier sesión del agente puede retomar el trabajo leyendo `docs/adr/` y `CHANGELOG.md`.
- Proponer una alternativa a algo ya decidido implica escribir un ADR que reemplace al anterior.

## Cómo se verifica
Revisión en cada PR: si cambia la estructura (un módulo nuevo, una dependencia, un contrato), tiene que
haber ADR. Si no hay entrada en `CHANGELOG.md`, el PR no se aprueba.
