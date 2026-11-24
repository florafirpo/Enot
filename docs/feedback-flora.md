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
