# Feedback de Flora

Canal de Flora hacia los agentes. El desarrollador lo lee **al empezar cada corrida** y lo que está acá va
antes que el backlog. Flora lo edita desde la web de GitHub (rama `desarrollo`, ícono del lápiz).
Los agentes marcan `[x]` lo que resolvieron, con la rama, y no borran lo que escribió Flora.

## Pedidos
- [x] (24/11) El francés es el idioma base: está en todas las bodegas. No hay datos de accesibilidad ni de
  dieta en DATAtourisme, así que el verificador no puede basarse en eso para descartar bodegas.
  → Se traduce en el ítem 010 del backlog. Si Flora no está de acuerdo con la propuesta del 010, lo escribe
  acá abajo antes de la próxima corrida.
  → Resuelto en `noche/2026-11-24-010` (spec 010, ADR-0012).
- [ ] (24/11) Obligatorio en todo cambio: entrada en `CHANGELOG.md` y ADR nuevo (ya en `AGENTS.md`,
  sensor `make registro`).

## Decisiones pendientes (las escriben los agentes cuando algo le corresponde a Flora)
- (25/11, ítem 008) **Precios del modelo para el reporte.** No puse precios en el repo: cambian y no los puedo
  verificar sin red. Para que `reports/resultados.md` traiga USD, armá un `precios.json` con el modelo de tu `.env`
  (`{"<modelo>": {"entrada_usd_por_millon": x, "salida_usd_por_millon": y}}`) y pasalo con `make reporte … PRECIOS=…`.
  Sin precios, el reporte trae tokens y latencia y dice "s/d" en USD.
- (25/11, ítem 008) **Rúbrica del juez y anotación del 30/11.** Revisá `eval/prompts/juez.md` antes de anotar: vos
  puntuás con la misma rúbrica y viendo el mismo texto que el juez. Pasos: `make eval SPLIT=dev` → `make planilla
  EVAL=reports/eval_dev_….json` (30 casos en `data/eval/anotacion_humana.csv`) → completar `puntaje_humano` → `make
  juez EVAL=…` → `make calibrar JUICIOS=…`.
- (25/11, ítem 008) ADR-0018 en "Propuesto". Decide:
  - juez ciego, con los datos de las bodegas tomados del corpus (no la prosa de cada sistema);
  - se juzgan solo consultas factibles con preferencias (42 de 100) y el reporte da la media total y la media con
    hard pass;
  - apto con 30 pares, Spearman ≥ 0,6 y **kappa cuadrático** ≥ 0,6 (escala ordinal); la planilla sale solo de dev;
  - costo desde la traza de cada consulta; una llamada sin tokens o un modelo sin precio deja la consulta sin costo
    (se cuenta, nunca 0); p95 por rango más cercano.

  Recomendación: aceptarlo. Alternativas: que el juez lea la respuesta completa (mide la prosa, B1 queda en
  desventaja), o umbral con kappa sin ponderar (más exigente).
- (25/11, ítem 007) **Qué es B2.** Con `max_intentos=1` tal cual, el flujo igual rechaza la propuesta inválida y
  responde "infactible": B2 tendría casi el mismo hard pass que Enot y sumaría infactibles "detectados" falsos. Así
  no aísla el aporte del verificador.
  - Lo que se hizo: B2 = un intento y **entrega la primera propuesta aunque el verificador la rechace** (sin loop no
    hay guardia). Está en ADR-0017.
  - Recomendación: aceptarlo.
  - Alternativa: reportar dos ablaciones, B2a (un intento, con guardia) y B2b (sin guardia). Es un parámetro
    (`entregar_sin_verificar`) y no hace falta código nuevo.
- (25/11, ítem 007) **Infactibles en las métricas.** No esperé tu respuesta sobre (a)/(b)/(c). El reporte trae la
  tasa total, la tasa por motivo y la tasa sobre los representables.
  - Cuenta como detectado `infactible`, `sin_candidatas` o `zona_desconocida` con una zona fuera de Borgoña (la
    opción (b) de "mientras tanto").
  - Si elegís (a), no hay que tocar las métricas. Si elegís (c), se lee la tasa de representables. El criterio con
    juez de (b) no está implementado.
- (25/11, ítem 007) ADR-0017 en "Propuesto". Decide cuatro cosas:
  - hard pass = estructura + verificador contra la etiqueta + cero inventados;
  - alucinación sobre bodegas, experiencias y precios;
  - B1 con el perfil etiquetado (tiene ventaja sobre Enot) y el verificador como oráculo;
  - reporte con fecha y hora que nunca pisa.

  Ojo: con fichas sin horarios ni precios, el hard pass es alto para todos. B1 sobre la muestra real da 98,75%.
  Conviene reportarlo junto con la completitud del corpus.
- (25/11, ítem 006) **Generar y congelar el set de evaluación.** El generador está listo, pero `data/eval/` no se
  escribió: crear la partición de test es irreversible (hook, ADR-0007). Antes hay que decidir si se parafrasea con
  el LLM, porque después de congelar test ya no se puede.
  - Recomendación: mirá las plantillas (`PLANTILLAS` en `eval/generador.py`, o corré `python -m eval.generador
    --destino /tmp/prueba` y leé los JSONL). Si te parecen bien, corré **sin paráfrasis** `python -m eval.generador`
    y commiteá `data/eval/` en `desarrollo`, o respondé acá "generar set" y lo hace la próxima corrida.
  - Por qué sin paráfrasis: es reproducible bit a bit y la revisión del 28/11 mide la tasa de error sobre textos
    fijos.
  - Alternativa: `python -m eval.generador --parafrasear` con tu clave. Da textos más variados; las etiquetas no
    cambian, y la paráfrasis que pierde un dato se descarta.
  - El ítem 007 se puede hacer antes con fixtures.
- (25/11, ítem 006, revisión ronda 1) **Cómo se cuentan los infactibles que el sistema no puede representar.**
  Conviene decidirlo antes de congelar test. Hay 14 de 20:
  - 7 piden "N bodegas en un día" que no entran en la jornada;
  - 7 piden "dos zonas lejanas el mismo día" a pie o en bici.

  Esas restricciones están en la etiqueta (`bodegas_por_dia`, `zonas_mismo_dia`), pero no en `PerfilViaje`: el
  verificador no las conoce y Enot puede responder un itinerario "válido" que las ignora. Los 6 de zona fuera de
  Borgoña salen como `zona_desconocida`, no como `infactible`. Opciones:
  - (a) Ítem nuevo antes del 007: sumar `bodegas_por_dia` y `zonas_mismo_dia` a `PerfilViaje`, al relevamiento y al
    verificador. Es la opción completa: el agente los detectaría con código.
  - (b) En el 007, contar como bien detectado si la respuesta es `infactible` o `zona_desconocida`, o si cumple un
    criterio para "explica por qué no entra y propone una alternativa" (PRD). Ese criterio lo tiene que aplicar el
    código o el juez.
  - (c) Reportarlo como limitación y medir "infactibles bien detectados" solo sobre lo que el sistema representa.

  Recomendación: (a), que es chico (dos campos, dos reglas del verificador y una línea del prompt de relevamiento) y
  hace honesta la métrica. Mientras tanto, (b) para `zona_desconocida`.
- (25/11, ítem 006) ADR-0016 en "Propuesto". Resume las decisiones del generador:
  - cuotas 15/15/15/15/10/10/20, con 20 infactibles para tener 8 en test;
  - infactible solo si el código lo demuestra, con tres motivos: demasiadas visitas para la jornada, dos zonas
    lejanas el mismo día a pie o en bici, y zona fuera de Borgoña;
  - el ejemplo del PRD "8 bodegas entre Chablis y el Mâconnais" se reformuló, porque con auto y 9 h no es
    demostrablemente imposible;
  - etiqueta de zona con el nombre canónico de la subzona;
  - visita mínima de 30 min.

  Recomendación: aceptarlo. Si querés pedidos infactibles por presupuesto o idioma, dependen del corpus real y
  conviene sumarlos en el 007 una vez que esté la extracción.
- (24/11, ítem 005) ADR-0015 en "Propuesto": con un itinerario vigente, **todo mensaje se trata como ajuste** (se
  replanifica sobre el vigente con el pedido y se verifica igual; el vigente solo cambia por otro factible), y el
  **tope de tokens es 200 000 por conversación**, contado desde la traza. Recomendación: aceptarlo y revisar el tope con
  las trazas de tus pruebas del 26–27/11. Alternativas: un clasificador de intención antes del planificador (evita que
  un "gracias" cueste un turno entero) o un tope en USD cuando exista la tabla de precios (ítem 008).
  Para probar `python -m enot` (26–27/11): los embeddings van por la API compatible con OpenAI (`OPENAI_API_KEY`,
  `EMBEDDINGS_MODEL`); sin clave ni caché en `data/indice/` hoy sale un traceback (anotado en el ítem 009).
- (24/11, ítem 004) ADR-0014 en "Propuesto": el relevamiento repregunta con **textos fijos escritos en código**
  (no los redacta el LLM) y el planificador recibe los **tiempos de traslado precalculados** en el contexto, en vez
  de tools. Recomendación: aceptarlo para el tracer bullet (005) y revisar después de tus pruebas del 26–27/11.
  Alternativas: que el LLM reescriba las preguntas (los `faltantes` siguen saliendo del código) o extender
  `ClienteLLM` con tool calling.
- (24/11, ítem 004) Revisá el texto de los prompts (`enot/prompts/*.md`) y las preguntas fijas (`PREGUNTAS` y
  `MOTIVOS_INVALIDO` en `enot/nodos.py`): están en rioplatense y son lo único que el turista ve escrito por código.
- (24/11, ítem 003) `zonas_preferidas` es **filtro duro** (ADR-0004 pone la subzona entre los filtros); una zona
  pedida coincide por palabras ("Chablis" → "Chablis y Grand Auxerrois") y las que no existen se informan con
  `Indice.zonas_desconocidas`. Recomendación: aceptarlo. Alternativa: usarla solo como preferencia blanda
  (sumaría a la consulta, sin excluir).
- (24/11, ítem 003) ADR-0013 (retrieval: filtros con las reglas del verificador, BM25 propio, embeddings cacheados
  fuera de `ClienteLLM`) en "Propuesto". Recomendación: aceptarlo.
- (24/11, ítem 003) Agregar `EMBEDDINGS_MODEL=text-embedding-3-small` a `.env.example` (el agente no puede leer ni
  editar `.env*` por la política de permisos). Recomendación: sí; con Ollama, un modelo multilingüe local.
- (24/11, ítem 010) ¿Sumar al ítem 007 la métrica "advertencias promedio por itinerario, por tipo" junto al hard
  pass rate? Con ADR-0012 un itinerario factible puede llevar advertencias; sin esa métrica, H1 esconde la
  incertidumbre (hallazgo menor del compañero, `docs/revisiones/010-ronda-1.md`). Recomendación: sí. Además,
  la próxima corrida marca la spec 002 como reemplazada en parte por la 010 (prolijidad).
- (24/11, ítem 010) Dieta fuera de alcance (en vez de dejarla como advertencia) y ADR-0012 en "Propuesto":
  aceptarlos o decir qué cambiar.
- (24/11) `experiencia_inexistente` (ítem 002): se agregó un tipo de violación que no estaba en el backlog,
  para que una experiencia inventada por el planificador no esquive el chequeo de presupuesto.
  Recomendación: aceptarlo. Si Flora no lo quiere, lo dice acá.

## Respuestas de Flora
<!-- Escribí acá abajo. Una línea con fecha alcanza. -->
