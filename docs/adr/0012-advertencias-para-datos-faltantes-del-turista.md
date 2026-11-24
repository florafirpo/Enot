# ADR-0012: Las necesidades del turista sin dato generan advertencias, no violaciones

**Estado:** Propuesto
**Fecha:** 2026-11-24
**Decide:** Flora (lo pidió el 24/11 en `docs/feedback-flora.md`; ítem 010, spec 010)
**Reemplaza parcialmente:** ADR-0009, en la parte de "necesidades del turista"

## Contexto
ADR-0009 decidió que una necesidad del turista (accesibilidad, dieta, idioma) solo se cumple con evidencia
positiva: `None` o lista vacía era violación. Flora señaló que DATAtourisme casi nunca publica accesibilidad ni
dieta y que el francés se habla en todas las bodegas de Borgoña. Con la regla vieja, cualquier pedido con silla
de ruedas o con dieta daba cero itinerarios válidos, y un pedido "en francés" descartaba a las bodegas que no
listan idiomas (las chicas, justamente las que el PRD quiere hacer visibles). Además, en Borgoña la visita es una
cata, no una comida: la restricción alimentaria casi no aplica.

## Decisión
1. **Dieta fuera de alcance.** `PerfilViaje` pierde `restricciones_alimentarias`; el verificador pierde el tipo
   `restriccion_alimentaria` (y `TIPOS_COMIDA`, que solo servía para eso). Los campos `opciones_*` de la ficha
   se conservan en el corpus como información, sin verificarse.
2. **Tres estados para las necesidades del turista.** Evidencia en contra → **violación**; sin dato →
   **advertencia**; evidencia a favor → nada.
   - Accesibilidad: `False` viola; `None` advierte (`accesibilidad_sin_confirmar`).
   - Idioma: si el perfil pide francés (en cualquiera de sus formas, `IDIOMA_BASE`), se cumple siempre. Para
     otros idiomas: lista publicada sin el pedido viola; sin lista advierte (`idioma_sin_confirmar`).
3. **API.** `verificar_completo(...) -> ResultadoVerificacion(violaciones, advertencias)`, con `factible` =
   sin violaciones. `verificar(...)` sigue devolviendo solo `list[Violacion]`: es lo que consumen el loop de
   reintento (ADR-0003) y el *hard pass rate* (ADR-0007). Las advertencias van a la respuesta al turista (ítem 004).

Los "límites de la bodega" de ADR-0009 (horario, capacidad, precio, coordenadas) no cambian.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Advertencias aparte + `verificar` compatible (elegida) | El reintento y la métrica no cambian de contrato; el planificador no gasta intentos en algo que no puede arreglar (no hay bodega con el dato); el turista recibe la duda en vez de un silencio | Dos funciones públicas en vez de una |
| `verificar` devuelve directamente `ResultadoVerificacion` | Una sola entrada | Rompe el contrato de 002 y obliga a reescribir ~60 tests que no cambian de sentido (AGENTS.md: no tocar tests existentes sin motivo) |
| Mantener ADR-0009 (sin dato = violación) | Máxima seguridad para el turista | Con la completitud real del corpus, cero itinerarios para pedidos con accesibilidad; sesga hacia bodegas grandes (lo contrario de H3) |
| Ignorar el dato faltante sin avisar | Más itinerarios válidos | El sistema daría a entender una accesibilidad que no sabe: alucinación por omisión |
| Advertencia como un tipo más de `Violacion` con un campo `grave: bool` | Un solo modelo | Cada consumidor tendría que acordarse de filtrar; un olvido convierte advertencias en reintentos o en fallas de la métrica |
| Dieta como advertencia (en vez de sacarla) | No pierde la necesidad | Casi nunca aplica a una cata y casi nunca hay dato: sería una advertencia en todas las paradas, ruido para el turista |

## Consecuencias
- Más fácil: pedidos con silla de ruedas o en inglés devuelven itinerarios con bodegas chicas, marcadas "a
  confirmar". El francés deja de filtrar.
- Más difícil: el *hard pass rate* mide "factible con lo que sabemos"; un itinerario factible puede llevar
  advertencias. Conviene reportar en la evaluación (ítem 007) cuántas advertencias tiene en promedio cada
  itinerario, para que la métrica no esconda la incertidumbre.
- `PerfilViaje` ignora campos desconocidos (comportamiento por defecto de Pydantic): si el relevamiento (LLM)
  devuelve `restricciones_alimentarias`, se descarta en silencio. El prompt de relevamiento (ítem 004) no debe
  preguntarla; si aparece igual en las trazas, evaluar `extra="forbid"`.
- Otros idiomas se comparan por texto (`"en"` ≠ `"inglés"`); la normalización le corresponde al corpus.
- Revisar con los resultados de dev (ítem 007): proporción de paradas con advertencias por tipo.

## Cómo se verifica
`tests/test_verificador_advertencias.py`: `test_accesibilidad_false_es_violacion`,
`test_accesibilidad_sin_dato_es_advertencia`, `test_frances_siempre_cumple`,
`test_otro_idioma_con_lista_sin_el_pedido_es_violacion`, `test_otro_idioma_sin_lista_es_advertencia`,
`test_advertencias_no_cuentan_para_factible`, `test_verificar_devuelve_solo_las_violaciones`,
`test_perfil_sin_restricciones_alimentarias`. Mutation sobre `enot/verificador.py`: 270/270.
