# CHANGELOG

Una entrada por PR, la más reciente arriba. Formato: fecha · rama/PR · qué cambió · ADRs.

## 2026-11-24 · desarrollo · explicaciones de todas las clases para el compañero
- `docs/catedra/`: se suman las explicaciones del 13/08, 27/08, 3/09, 17/09 y 22/10, y la versión nueva del
  1/10 (con knowledge graphs). Índice actualizado.
- `lineamientos.md`: puntos nuevos sobre contexto y alucinaciones (08/13), comparar diseños de lo simple a
  lo complejo y human in the loop (10/22), y una sección de observabilidad con trazas (10/22).
- ADR-0011: la base de conocimiento del compañero se versiona en el repo.

## 2026-11-24 · desarrollo · agente compañero revisor, rama de integración y registro obligatorio
- `.claude/agents/companero.md`: agente revisor que conoce las clases y la consigna; corre los sensores por su
  cuenta y devuelve APROBADO / CAMBIOS / ESCALAR A FLORA. Sin herramientas de edición.
- `docs/catedra/`: consigna, explicaciones de las clases del 20/08, 01/10, 08/10, 05/11 y 12/11, y
  `lineamientos.md` (rúbrica destilada con citas).
- Skill `tarea-nocturna` reescrita: corrida cada 7 h, `docs/feedback-flora.md` primero, hasta 3 rondas de
  revisión, merge `--no-ff` a `desarrollo` solo con APROBADO. `main` sigue siendo de Flora.
- Registro obligatorio en todo cambio (pedido de Flora): CHANGELOG + ADR nuevo, verificado por
  `scripts/registro_obligatorio.py` (`make registro`); `AGENTS.md` actualizado.
- Hook: las revisiones en `docs/revisiones/` no se editan. `make tests-modificados` compara contra `desarrollo`.
- BACKLOG: 001 y 002 integrados; ítem nuevo 010 (datos faltantes del turista como advertencias). ADR-0010;
  ADR-0008 queda modificado por ADR-0010.
- 13 tests nuevos (`tests/test_hooks.py`, `tests/test_registro_obligatorio.py`).

## 2026-11-24 · noche/2026-11-24-002 (sale de noche/2026-11-23-001)
- `enot/verificador.py`: `verificar(itinerario, perfil, corpus) -> list[Violacion]` con 10 tipos (los del backlog,
  con alimentaria y accesibilidad separadas, más `experiencia_inexistente`), mensajes accionables y orden
  determinístico. Usa `abierta_en`, `tiempo_traslado` y `costo_experiencias`. ADR-0003, ADR-0005.
- ADR-0009 (propuesto): qué hace el verificador cuando a la ficha le falta un dato.
- 76 tests nuevos en `tests/test_verificador.py`; mutation sobre `enot/verificador.py`: 243/243 (100%).
- `pyproject.toml`: ruff reconoce `enot`, `corpus` y `eval` como propios (el orden de imports no cambia
  según exista o no el módulo); se reordenaron los imports de `tests/test_modelos.py` (sin cambiar el test).

## 2026-11-23 · noche/2026-11-23-001
- `enot/modelos.py`: `Bodega` (desde `fichas.jsonl`), `PerfilViaje`, `Parada`, `DiaItinerario`, `Itinerario`,
  con validación de horas HH:MM y de rangos.
- `enot/corpus_local.py`: carga del corpus tolerante a líneas inválidas.
- `enot/tools/`: `tiempo_traslado`, `abierta_en`, `costo_experiencias` (errores como valor). ADR-0005.
- Fixture sintética `tests/fixtures/fichas_sinteticas.jsonl`; 37 tests nuevos; mutation sobre `enot/tools`:
  146/152 mutantes muertos (96%).
- `make mutation` muestra el resumen del módulo.

## 2026-11-23 · setup inicial (main)
- Pipeline del corpus (`corpus/`): adaptador DATAtourisme para Borgoña, crawl y limpieza opcionales,
  extracción de fichas con LLM y verificación de citas, EDA y validación manual.
- Tests offline del corpus y de los hooks (`tests/`), con un `ClienteFalso` para el LLM.
- Harness del agente: `AGENTS.md`, hooks de políticas (`.claude/`), skill `tarea-nocturna`,
  sensores (`make check`, `make mutation`, `make tests-modificados`).
- ADRs 0001–0008, PRD en `docs/PRD.md`, `BACKLOG.md` con el plan hasta el 3/12.
