# CHANGELOG

Una entrada por PR, la más reciente arriba. Formato: fecha · rama/PR · qué cambió · ADRs.

## 2026-11-25 · noche/2026-11-25-008 · juez LLM calibrado y reporte de costos y latencia
- `eval/juez.py` + `eval/prompts/juez.md`: juez con rúbrica 1–5 de ajuste a preferencias blandas (H2). Juzga solo
  consultas factibles con preferencias y con itinerario; a ciegas (sin el sistema ni su texto) y con los datos de cada
  bodega tomados del corpus, sin precios ni horarios. Salida `justificacion` + `puntaje`, sin "confianza".
  `python -m eval.juez` / `make juez EVAL=…` → `reports/juez_<split>_<fecha>.json` (no pisa).
- `eval/calibrar.py`: Spearman (rangos promedio en empates) y kappa de Cohen sin ponderar y cuadrático sobre 1–5;
  apto con 30 pares, Spearman ≥ 0,6 y kappa cuadrático ≥ 0,6. Planilla de anotación (`make planilla`) solo de dev, a
  ciegas, repartida por sistema, que nunca pisa `data/eval/anotacion_humana.csv`. `make calibrar JUICIOS=…`.
- `eval/reporte.py` / `make reporte`: `reports/resultados.md` con métricas, preference score (total y con hard pass),
  tokens, USD (media y p95), latencia (media y p95), intentos medios, llamadas fallidas y sin tokens, y proyección a
  1000 consultas por mes. Costo por consulta desde su traza con el precio de cada modelo (PRD 9); precios por
  `--precios` (no están en el repo). Una consulta con tokens desconocidos o modelo sin precio queda sin costo y se
  cuenta: nunca un 0 inventado.
- Pendientes de la revisión 004: `ClienteLLM` lanza `ErrorSalidaInvalida` (subclase de `RuntimeError`) con los tokens
  gastados y el nodo los registra en el evento de error; `EventoTraza` con `estado == "ok"` exige tokens.
  `SalidaSistema.traza` guarda la ruta de la traza de cada consulta de Enot/B2.
- Makefile (`juez`, `planilla`, `calibrar`, `reporte`) y README. ADR-0018 (propuesto). Spec 008.
- 60 tests nuevos (467 → 527; 533 tras la ronda 2) en archivos nuevos, ningún test existente modificado. Mutation: `eval/metricas.py`
  326/328; `eval/calibrar.py` 444/536, `eval/reporte.py` 457/530, `eval/juez.py` 251/301 (los sobrevivientes son
  textos de ayuda del CLI, prosa del Markdown, `encoding` y mutantes matemáticamente equivalentes; detalle en el
  reporte).
- Ronda 2 (revisión 008 ronda 1, CAMBIOS): el juez solo ve experiencias que están en la ficha; la planilla de
  anotación usa un id opaco por caso y guarda consulta y sistema en `anotacion_humana_claves.csv`; el reporte usa solo
  juicios del mismo reporte y split (el CLI rechaza los de otra corrida); la limitación de `usage` ausente en
  endpoints compatibles queda declarada (ADR-0018 y notas del reporte); el Makefile avisa si falta `EVAL`/`JUICIOS`.
  533 tests. Mutation: `eval/calibrar.py` 467/560, `eval/reporte.py` 476/557, `eval/juez.py` 260/310 (los
  sobrevivientes siguen siendo CLI, prosa, `encoding` y equivalentes).

## 2026-11-25 · noche/2026-11-25-007 · baselines, métricas y `make eval`
- `eval/metricas.py` (funciones puras):
  - hard pass todo o nada contra la etiqueta: itinerario entregado, estructura completa (días, día de la semana y al
    menos una visita por día), cero violaciones del verificador y cero afirmaciones inventadas;
  - tasa de alucinación sobre bodegas, experiencias y precios afirmados;
  - cobertura del corpus + Gini;
  - infactibles bien detectados (total, por motivo y sobre los representables), que no dependen de la decisión
    pendiente de Flora;
  - desglose por escenario y conteo de tipos de salida.
- `eval/baselines.py`:
  - B0 zero-shot sin corpus: nombres resueltos contra el corpus y `b0:<nombre>` si no existen;
  - B1 formulario + filtros + greedy por cercanía, con el verificador como oráculo;
  - B2 un intento, entrega la primera propuesta aunque no pase el verificador;
  - Enot completo, con una sesión y una traza por consulta.
- `eval/correr.py` y `make eval SPLIT=dev|test SISTEMAS=…` escriben `reports/eval_<split>_<fecha-hora>.json` con la
  configuración, las métricas, la evaluación por consulta y las salidas (tokens y latencia para el 008). Sin
  `data/eval/` sale con un mensaje; `SISTEMAS=B1` corre sin claves.
- `eval/generador.py`: el docstring de `escribir_set` declara que el movimiento final no es atómico entre los cuatro
  elementos (menor de la revisión 006 ronda 2). README: sección "Correr la evaluación".
- ADR-0017 (propuesto). Spec 007.
- 82 tests nuevos (384 → 466), ningún test existente modificado. Mutation: `eval/metricas.py` 326/328 (99%),
  `eval/baselines.py` 395/419 (94%, no obligatorio).
- Ronda 2 (revisión 007 ronda 1, CAMBIOS): la bodega inventada de B0 en los tests está marcada `[SINTÉTICA]`; la
  latencia se prueba con un reloj falso; `test_b1_sobre_la_muestra_real` reproduce las cifras de la muestra real
  (ADR-0017 suma que "factible" no está certificado contra el corpus, caso q047); se corrigió la justificación de un
  mutante equivalente. 467 tests.

## 2026-11-25 · noche/2026-11-25-006 · generador del set de evaluación
- `eval/generador.py`: 100 consultas desde plantillas, con la etiqueta como `PerfilViaje` (más `bodegas_por_dia`,
  `zonas_mismo_dia`, `infactible` y `motivo_infactible`). Cuotas por escenario 15/15/15/15/10/10/20 (días,
  transporte, presupuesto, grupo, idioma, accesibilidad, infactibles). Semilla fija (2026).
- `certificado_infactible`: un pedido se etiqueta infactible solo si el código prueba que es imposible para cualquier
  corpus, con las constantes de la tool de traslados. Tres motivos: demasiadas visitas para la jornada, dos zonas
  lejanas el mismo día a pie o en bici, zona fuera de Borgoña.
- `particionar` (60/40 estratificado), `muestra_revision` (20% estratificado), `escribir_set` (todo o nada: no
  escribe si `dev/` o `test/` existen), `tasa_error_revision` (lee la columna `correcta` de la planilla) y
  paráfrasis opcional con `ClienteLLM`, que se acepta solo si conserva las anclas y no repite otra consulta.
- `python -m eval.generador [--destino] [--semilla] [--parafrasear]`; sección en el README.
- **No se escribió `data/eval/`**: congelar la partición de test es irreversible y le corresponde a Flora (decisión
  pendiente en `docs/feedback-flora.md`).
- ADR-0016 (propuesto). Spec 006.
- 42 tests nuevos (338 → 380), ningún test existente modificado. Mutation: `eval/generador.py` 1115/1178 (95%).
- Ronda 2 (revisión 006 ronda 1, CAMBIOS):
  - Con una persona, el texto va en singular (marcas `[singular|plural]`); versión 006.2 con huella nueva.
  - La escritura del set es atómica (carpeta temporal y se mueve al final).
  - ADR-0016 y el reporte declaran que 14 infactibles dependen de restricciones que `PerfilViaje` no tiene y que
    `zona_fuera` sale como `zona_desconocida`; la decisión quedó en `docs/feedback-flora.md`.
  - 384 tests. Mutation: 1153/1221 (94%).

## 2026-11-24 · noche/2026-11-24-005 · flujo completo con loop de verificación, ajuste conversacional y CLI
- `enot/flujo.py`: `Sesion` serializable (historial, perfil, itinerario vigente, advertencias, ruta de la traza) y
  `Flujo.turno(sesion, texto) -> Respuesta`: relevar → zonas conocidas → buscar → [planificar → verificar] × hasta
  `max_intentos` (3; 1 = ablación B2) → responder. Tope de tokens por conversación (200 000) sumado desde la traza y
  chequeado antes de cada llamada. Ajuste: con itinerario vigente, el planificador recibe el vigente y el pedido, y
  las bodegas del vigente se suman a las candidatas; el vigente solo cambia por otro factible. Textos de infactible,
  zona desconocida ("No reconozco la zona X", revisión 003 ronda 2), sin candidatas y tope escritos por código.
- `enot/__main__.py`: `python -m enot [--sesion archivo.json] [--fichas] [--max-intentos] [--tope-tokens] [--k]`.
- `enot/nodos.py`: `planificar` y `contexto_planificador` aceptan `pedido_ajuste` (compatible: sin pedido, el
  contexto no cambia); `prompts/planificador.md` explica cómo usarlo.
- ADR-0015 (propuesto). Spec 005.
- 32 tests nuevos (302 → 334), ningún test existente modificado; uno corre la muestra real de DATAtourisme por un
  turno completo. Mutation (no obligatorio): `enot/flujo.py` 344/361 (95%; sobrevivientes equivalentes).
- Ronda 2 (revisión 005 ronda 1, CAMBIOS): en el reintento de un ajuste, el pedido se marca "ya aplicado" y el vigente
  va aparte como referencia (`vigente_ajuste` en `planificar`), para no aplicarlo dos veces; "las zonas" en plural;
  la CLI convierte en mensaje un error al crear el cliente LLM y un Ctrl-C a mitad de turno no guarda el turno a
  medias; el test de valores por defecto pasa por `argparse`. 338 tests. Mutation: 361/378.

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
- Ronda 2 (revisión 004 ronda 1, CAMBIOS): en los eventos con error, tokens e intentos quedan en `None`
  (desconocidos) y no en 0; ADR-0014 lo explica y aclara que introducción y motivos solo los restringe el prompt;
  pendiente anotado en el ítem 008. 302 tests.

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
