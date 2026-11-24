# ADR-0011: La base de conocimiento del compañero son las explicaciones de clase versionadas en el repo

**Estado:** Propuesto
**Fecha:** 2026-11-24
**Decide:** Flora

## Contexto
El agente compañero (ADR-0010) tiene que revisar cada entrega con los criterios de la cátedra. Corre en una
sesión en la nube que solo ve el repo: no tiene acceso al Drive de Flora ni a las grabaciones. Flora tiene
explicaciones escritas de las 10 clases (13/08 a 12/11) y la consigna. Las transcripciones crudas pesan
entre 140 y 280 KB cada una y tienen voces de otras personas.

## Decisión
Versionar en `docs/catedra/` la consigna y las explicaciones escritas de todas las clases, convertidas a
Markdown, más `lineamientos.md`: una rúbrica corta con citas a la clase y la sección de donde sale cada
criterio. El compañero empieza por la rúbrica y busca con `grep` en las explicaciones cuando necesita el
detalle (búsqueda exacta sobre texto, como en 10/01 §2). No se versionan las transcripciones.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Explicaciones + rúbrica en el repo (elegida) | El agente las lee siempre, sin conectores; la rúbrica es corta y citable; Flora la puede corregir con un commit | El repo es público: las notas de Flora quedan visibles |
| Solo la rúbrica, sin las explicaciones | Repo más liviano | El compañero no puede verificar el detalle ni contestar preguntas de defensa con la fuente |
| Leer del Drive en cada corrida | Siempre la última versión | Depende de un conector en la sesión programada; más lento y frágil |
| Transcripciones crudas | Nada se pierde en el resumen | Mucho texto y ruido para cada revisión (context rot, 10/08 §6); voces de terceros |

## Consecuencias
- El compañero puede citar la clase exacta en cada hallazgo, y Flora usar esas citas en la defensa.
- Si Flora cambia una explicación en el Drive, hay que volver a copiarla al repo.
- Si no quiere que sus notas sean públicas, la salida es hacer el repo privado.

## Cómo se verifica
Cada revisión en `docs/revisiones/` cita puntos de `lineamientos.md`. `docs/catedra/README.md` lista una
explicación por cada clase.
