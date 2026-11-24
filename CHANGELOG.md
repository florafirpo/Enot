# CHANGELOG

Una entrada por PR, la más reciente arriba. Formato: fecha · rama/PR · qué cambió · ADRs.

## 2026-11-24 · noche/2026-11-24-004 · nodos con LLM (relevamiento, planificador, respuesta) y trazas
- `enot/nodos.py`: `relevar(historial) -> PerfilViaje | Pregunta` (el LLM extrae un `BorradorPerfil`; qué falta, qué
  es inválido y el día de la semana de una fecha los decide el código, con preguntas fijas por campo);
  `planificar(perfil, candidatas, violaciones_previas, …) -> Itinerario` (tiempos de traslado precalculados en el
  contexto; salida con `bodega_id` ∈ candidatas y exactamente `cantidad_dias` días; en el reintento recibe el
  itinerario anterior y las violaciones); `responder(itinerario, perfil, corpus, …) -> str` (el LLM escribe
  introducción y motivos; horarios, precios, traslados, advertencias y fuentes los arma `render_itinerario`).
- `enot/prompts/`: prompts de sistema `relevamiento.md`, `planificador.md`, `respuesta.md` y `cargar(nombre)`.
- `enot/trazas.py`: `Traza` (un JSONL por conversación en `data/trazas/`) y `EventoTraza` (nodo, intento, proveedor,
  modelo, inicio UTC, latencia, tokens, intentos de validación, estado, error). Errores del cliente → `ErrorNodo`.
- ADR-0014 (propuesto). Spec 004.
- 47 tests nuevos (254 → 301), ningún test existente modificado; uno corre la muestra real de DATAtourisme por el
  contexto del planificador. Mutation (no obligatorio): `enot/nodos.py` 540/565 (96%), `enot/trazas.py` 33/38 (87%).

## 2026-11-24 · noche/2026-11-24-003 · retrieval híbrido y su evaluación
- `enot/retrieval.py`: filtros duros por perfil (`filtrar`, `motivo_exclusion`) con las reglas del verificador
  evaluadas por visita posible; BM25 propio; embeddings inyectables (`EmbedderOpenAI` + `EmbedderConCache` en
  `data/indice/`); RRF c = 60; `Indice.buscar(perfil, k, consulta) -> list[Candidata]`. ADR-0004.
- `eval/retrieval.py`: Recall@k y nDCG@k (ganancia lineal, relevancia graduada opcional), `evaluar` y
  `python -m eval.retrieval <consultas.jsonl> [--k]` con reporte en `reports/retrieval_<fecha>.json`.
- `enot/modelos.py`: `Bodega` suma `descripcion_breve` y `vinos_o_varietales_destacados` (vienen en la ficha).
- `tests/dobles.py`: `EmbedderFalso` determinístico. Un test corre la muestra real de DATAtourisme por el paso
  `datatourisme` y busca sobre esas 200 bodegas.
- ADR-0013 (propuesto). Spec 002 marcada como reemplazada en parte por la 010 (hallazgo menor de la revisión 010).
- 71 tests nuevos (179 → 250), ningún test existente modificado. Mutation: `enot/retrieval.py` 440/461 (95%),
  `eval/retrieval.py` 174/196 (89%).
- Ronda 2 (revisión 003 ronda 1, CAMBIOS): zonas pedidas por palabras ("Chablis" encuentra "Chablis y Grand
  Auxerrois") e `Indice.zonas_desconocidas`; tests de k = 10 por defecto y de `recuperados` cortado en k; spec y
  decisiones pendientes en `docs/feedback-flora.md`. 254 tests. Mutation: 459/479 y 177/196.

## 2026-11-24 · noche/2026-11-24-010 · datos faltantes del turista: advertencias en vez de violaciones
- `enot/verificador.py`: `verificar_completo(...) -> ResultadoVerificacion(violaciones, advertencias)` y
  `factible`; `verificar` sigue devolviendo solo violaciones. Accesibilidad `False` viola y `None` advierte;
  el francés (`IDIOMA_BASE`) se cumple siempre; otros idiomas: lista publicada sin el pedido viola, sin lista
  advierte. Se quitan `restriccion_alimentaria` y `TIPOS_COMIDA`.
- `enot/modelos.py`: `PerfilViaje` pierde `restricciones_alimentarias`. PRD: dieta fuera de alcance; caso de uso
  y H1 actualizados.
- ADR-0012 (propuesto); ADR-0009 queda reemplazado parcialmente.
- 22 tests nuevos (`tests/test_verificador_advertencias.py`); de los de 002, 15 casos borrados y 5 ajustados en commits
  aparte porque la regla cambió (ver spec 010 y el reporte). Total 172 → 179. Mutation sobre `enot/verificador.py`: 270/270.

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
