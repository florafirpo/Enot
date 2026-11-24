# ADR-0007: Evaluación con set sintético fijo, validador en código y juez LLM calibrado

**Estado:** Aceptado
**Fecha:** 2026-11-23
**Decide:** Flora

## Contexto
La hipótesis principal (PRD 6) compara la tasa de itinerarios factibles de Enot contra un LLM
zero-shot (B0), un filtro determinístico (B1) y Enot sin verificador (B2). Optimizar contra un
benchmark mal definido arruina todo lo demás (clase del 05/11), y un juez LLM sin calibrar mide lo
que quiere (reward hacking, clase del 08/10).

## Decisión
- **Set:** 100 consultas sintéticas con restricciones etiquetadas en JSON, partición fija 60 dev / 40
  test, semilla fija. El generador (`eval/generador.py`) es parte del sistema y su tasa de error se
  mide revisando a mano el 20%.
- **La partición de test es inmutable** una vez creada: un hook bloquea cualquier edición en
  `data/eval/test/` (`.claude/hooks/proteger.py`).
- **Métrica principal** (hard pass rate): la calcula el mismo verificador determinístico del sistema,
  con chequeo extra de que cada bodega, precio y horario exista en el corpus.
- **Preferencias blandas:** juez LLM con rúbrica 1–5, calibrado contra 30 casos anotados a mano
  (Spearman y kappa). Si la correlación es baja, se reporta y no se usa como evidencia fuerte.
- Todo corre con `make eval`, y los resultados se guardan con la configuración que los produjo.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Set sintético + verificador + juez calibrado (elegida) | Reproducible; la métrica principal no depende de un LLM | El set sintético puede no parecerse a pedidos reales |
| Solo juez LLM | Rápido | No es confiable sin calibración; mueve la vara |
| Pedidos reales de usuarios | Realista | No hay usuarios ni tiempo para conseguirlos |

## Consecuencias
- Que el verificador sea a la vez parte del sistema y de la métrica es una limitación: se mitiga con
  mutation testing y con la revisión manual de una muestra de itinerarios.

## Cómo se verifica
`tests/test_eval.py` (métricas con casos armados a mano) y el hook de protección del test.
