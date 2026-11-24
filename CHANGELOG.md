# CHANGELOG

Una entrada por PR, la más reciente arriba. Formato: fecha · rama/PR · qué cambió · ADRs.

## 2026-11-23 · setup inicial (main)
- Pipeline del corpus (`corpus/`): adaptador DATAtourisme para Borgoña, crawl y limpieza opcionales,
  extracción de fichas con LLM y verificación de citas, EDA y validación manual.
- Tests offline del corpus y de los hooks (`tests/`), con un `ClienteFalso` para el LLM.
- Harness del agente: `AGENTS.md`, hooks de políticas (`.claude/`), skill `tarea-nocturna`,
  sensores (`make check`, `make mutation`, `make tests-modificados`).
- ADRs 0001–0008, PRD en `docs/PRD.md`, `BACKLOG.md` con el plan hasta el 3/12.
