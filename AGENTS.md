# AGENTS.md — Enot

Agente que arma itinerarios de enoturismo en Borgoña. TP de IA Agéntica (Maestría UBA).
Lo que el sistema debe hacer está en `docs/PRD.md`; por qué está armado así, en `docs/adr/`.

## Cómo se trabaja acá (spec → tests → código → revisión)

1. Cada tarea sale de `BACKLOG.md` (o de `docs/feedback-flora.md`, que va primero). Antes de programar,
   escribí la spec en `docs/specs/NNN-nombre.md` con `docs/specs/TEMPLATE.md`. "Cómo se verifica" es obligatoria.
2. Escribí primero los tests de la spec y commitealos solos ("tests: …"). Después el código.
3. Una tarea = una rama `noche/AAAA-MM-DD-NNN` que sale de `desarrollo`. Nunca commitees ni pushees a `main`.
4. **Registro obligatorio en todo cambio, sin excepción:** una entrada nueva arriba de todo en
   `CHANGELOG.md` (`## AAAA-MM-DD · rama · …`) **y** un ADR nuevo en `docs/adr/` con el formato de
   `docs/adr/0000-template.md`, que explique qué se decidió en ese cambio y por qué. Si el cambio no trae
   una decisión de arquitectura, el ADR registra las decisiones de diseño que sí tomaste y las alternativas
   descartadas. `make registro` lo verifica; sin eso la rama no se integra.
5. Al terminar: `make check` y `make registro` en verde, y revisión del agente `companero`
   (`.claude/agents/companero.md`). Solo con su `APROBADO` la rama se integra a `desarrollo`;
   Flora integra `desarrollo` a `main` (ADR-0010). El procedimiento completo está en la skill `tarea-nocturna`.

## Comandos

- `make check` = `ruff check .` + `pytest -q`. Tiene que pasar antes de pedir revisión.
- `make registro` = verifica que la rama trae entrada de CHANGELOG y ADR nuevo.
- `make mutation MODULO=enot/verificador.py` = mutation testing sobre un módulo (mutmut).
  Obligatorio para `enot/verificador.py`, `enot/tools/` y `eval/metricas.py`.
- `python -m corpus <paso>` = pipeline del corpus (ver `README.md`).

## Reglas que no se deducen del código

- **Los tests tienen que ser significativos.** Un test que pasa con una implementación vacía o
  trivial no sirve. Para la lógica crítica, el resultado de mutation testing va en el reporte de la corrida.
- **Nunca cambies un test existente para que pase.** Si un test viejo está mal, decilo en el PR y
  explicá por qué en el reporte; no lo edites en el mismo commit que el código.
- **La partición de test (`data/eval/test/`) no se toca** después de creada. Un hook lo bloquea.
- **Nada de red ni de claves en los tests.** Los LLM y las APIs se reemplazan por dobles
  (ver `tests/conftest.py`). Los tests corren offline en menos de 60 s.
- **El LLM no hace aritmética ni manejo de horarios**: distancias, horarios, costos y validación de
  restricciones son código determinístico (ADR-0003, ADR-0005).
- **Los datos de bodegas son reales** (DATAtourisme). Nunca inventes bodegas, precios ni horarios en
  código, prompts o fixtures que no estén marcados como sintéticos.
- **Python 3.11+, tipado con Pydantic** para todo lo que cruza un borde (tools, LLM, archivos).
- **Idioma:** código e identificadores en español, como el resto del repo.
- **Si te trabás**, no improvises alcance: dejá la rama sin integrar, marcá el ítem `[!]` y anotá en
  `docs/feedback-flora.md` qué falta y qué decisión necesitás.

## Registro entre sesiones

- `CHANGELOG.md`: qué cambió y cuándo (obligatorio: una entrada por cada cambio, arriba de todo).
- `docs/adr/`: por qué se decidió algo (obligatorio: un ADR nuevo por cada cambio). Leelos antes de proponer una alternativa.
- `docs/noches/AAAA-MM-DD-HHMM.md`: reporte de cada corrida.
- `docs/revisiones/`: veredictos del compañero, tal cual (un hook impide editarlos).
- `docs/feedback-flora.md`: pedidos y decisiones de Flora; se lee al empezar cada corrida.
- `docs/catedra/`: clases y consigna; la rúbrica está en `docs/catedra/lineamientos.md`.
