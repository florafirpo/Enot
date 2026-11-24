# CHANGELOG

Una entrada por PR, la más reciente arriba. Formato: fecha · rama/PR · qué cambió · ADRs.

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
