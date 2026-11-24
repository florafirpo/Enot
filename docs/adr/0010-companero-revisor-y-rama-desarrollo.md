# ADR-0010: Un agente compañero revisa cada entrega y solo lo aprobado se integra a `desarrollo`

**Estado:** Propuesto
**Fecha:** 2026-11-24
**Decide:** Flora

## Contexto
Flora hace el TP sola y puede mirar el repo cada 7 horas, no todos los días a la mañana. Con ADR-0008 cada
tarea esperaba su aprobación en un PR, así que el agente avanzaba un ítem por día y quedaban PRs
encadenados (002 salía de la rama de 001). Además, en clase (10/01 §6) Charlie planteó que el objetivo es
reducir el human-in-the-loop haciendo que otro sistema verifique, y que la revisión por otro modelo es un
tipo de sensor (10/01 §7). Matías advirtió que no se suelta el control: se cambia de lugar (08/20 §3).
Flora pidió además que todo cambio deje entrada de CHANGELOG y ADR.

## Decisión
- Dos agentes con roles separados: el **desarrollador** (skill `tarea-nocturna`) escribe spec, tests y código;
  el **compañero** (`.claude/agents/companero.md`) conoce las clases y la consigna (`docs/catedra/`), corre
  los sensores por su cuenta y devuelve `APROBADO`, `CAMBIOS` o `ESCALAR A FLORA`. No tiene herramientas de
  edición.
- Hasta 3 rondas de revisión por ítem (circuit breaker, como en ADR-0003). Sin `APROBADO`, no se integra.
- Rama de integración `desarrollo`: las ramas aprobadas se mergean ahí con `--no-ff`. **Solo Flora integra
  `desarrollo` a `main`** (el hook sigue bloqueando cualquier push a `main`).
- Las revisiones se guardan tal cual en `docs/revisiones/NNN-ronda-K.md` y un hook impide editarlas: el
  desarrollador no puede retocar el veredicto de su revisor.
- Registro obligatorio en todo cambio: entrada en `CHANGELOG.md` y ADR nuevo, verificado por el sensor
  determinístico `scripts/registro_obligatorio.py` (`make registro`).
- Canal de Flora: `docs/feedback-flora.md`, que se lee al empezar cada corrida y va antes que el backlog.
- Cadencia: la tarea programada corre cada 7 horas (01:38, 08:38, 15:38 y 22:38, hora de Buenos Aires),
  un ítem por corrida.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Compañero revisor + `desarrollo` (elegida) | Avanza sin esperar a Flora; cada entrega tiene una revisión independiente con la rúbrica de la cátedra; `main` sigue bajo control humano | El revisor es otro LLM: puede aprobar algo mal. Se mitiga porque corre los sensores él mismo y porque Flora revisa `desarrollo` antes de `main` |
| Seguir con ADR-0008 (un PR por día que aprueba Flora) | Control humano por ítem | Un ítem por día no llega al 3/12 con margen; PRs encadenados |
| Un solo agente que se autoaprueba | Más simple | Se corrige a sí mismo con el mismo contexto: no es una verificación independiente |
| Compañero en una tarea programada aparte, revisando PRs en GitHub | Separación total | Coordinación entre corridas más frágil; el token de `gh` no puede crear ni comentar PRs hoy |

## Consecuencias
- Más fácil: el backlog avanza unas 4 veces por día; cada entrega llega con su revisión escrita y preguntas
  de defensa.
- Más difícil: Flora tiene que leer revisiones agregadas en lugar de PRs chicos; si el compañero es laxo,
  los errores llegan a `desarrollo`. Por eso `main` sigue siendo de Flora.
- Más uso del plan por corrida (dos agentes, mutation testing dos veces en lógica crítica).
- Revisar después del 1/12: borrar la tarea programada.

## Cómo se verifica
- `tests/test_hooks.py`: las revisiones existentes no se pueden editar (Edit/Write ni por shell) y la ronda
  siguiente sí se puede crear.
- `tests/test_registro_obligatorio.py`: una rama sin entrada de CHANGELOG o sin ADR nuevo completo no pasa.
- Cada merge a `desarrollo` tiene en su mensaje la ronda aprobada y su revisión en `docs/revisiones/`;
  `git log --merges desarrollo` lo muestra.
