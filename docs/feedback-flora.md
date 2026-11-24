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
