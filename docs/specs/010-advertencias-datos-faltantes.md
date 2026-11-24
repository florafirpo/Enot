# Spec 010: datos faltantes del turista: advertencias en vez de violaciones

**Ítem del backlog:** 010 · **Rama:** `noche/2026-11-24-010` · **ADRs relacionados:** ADR-0003, ADR-0005,
ADR-0009 (se reemplaza en parte), ADR-0012 (nuevo)

## Qué se va a hacer
DATAtourisme casi nunca publica accesibilidad ni dieta, y con ADR-0009 tal como está cualquier pedido con esas
necesidades da cero bodegas (pedido de Flora del 24/11). Se sacan las restricciones alimentarias del alcance y
el verificador pasa a distinguir **violaciones** (hay evidencia de que la bodega no cumple) de **advertencias**
(no hay dato para confirmar). Las advertencias no disparan el reintento del planificador: van a la respuesta al
turista ("no pude confirmar…").

## Interfaz
```python
# enot/verificador.py
TipoViolacion = Literal["bodega_inexistente", "experiencia_inexistente", "cerrada", "traslado_imposible",
                        "jornada_excedida", "presupuesto_excedido", "grupo_excede_capacidad",
                        "accesibilidad", "idioma_no_disponible"]          # sin "restriccion_alimentaria"
TipoAdvertencia = Literal["accesibilidad_sin_confirmar", "idioma_sin_confirmar"]
IDIOMA_BASE: frozenset[str]   # formas de nombrar el francés: "fr", "francés", "français", "french", …

class Violacion(BaseModel):   tipo: TipoViolacion; mensaje: str; dia: int | None; bodega_id: str | None
class Advertencia(BaseModel): tipo: TipoAdvertencia; mensaje: str; dia: int | None; bodega_id: str | None
class ResultadoVerificacion(BaseModel):
    violaciones: list[Violacion]
    advertencias: list[Advertencia]
    @property factible -> bool        # sin violaciones (las advertencias no cuentan)

def verificar_completo(itinerario, perfil, corpus) -> ResultadoVerificacion
def verificar(itinerario, perfil, corpus) -> list[Violacion]   # = verificar_completo(...).violaciones
```
`PerfilViaje` pierde `restricciones_alimentarias` (y el alias `Restriccion`).

### Reglas nuevas
| Necesidad | Dato de la ficha | Resultado |
|---|---|---|
| movilidad reducida | `accesible_movilidad_reducida = True` | nada |
| movilidad reducida | `False` | violación `accesibilidad` |
| movilidad reducida | `None` | advertencia `accesibilidad_sin_confirmar` |
| idiomas pedidos incluyen el francés | cualquiera (aunque la lista esté vacía o no diga `fr`) | nada |
| otros idiomas | la experiencia o la bodega publica idiomas y alguno pedido está | nada |
| otros idiomas | publica idiomas y ninguno pedido está | violación `idioma_no_disponible` |
| otros idiomas | no publica ninguno (ni la experiencia ni la bodega) | advertencia `idioma_sin_confirmar` |

Como hasta ahora: los idiomas de la experiencia, si los publica, mandan sobre los de la bodega; basta con que
uno de los pedidos esté; la comparación ignora mayúsculas.

## Archivos a tocar
- Modificar: `enot/verificador.py`, `enot/modelos.py`, `docs/PRD.md` (alcance, relevamiento, H1, caso de uso),
  `docs/adr/0009-…` (estado), `BACKLOG.md`, `CHANGELOG.md`, `docs/feedback-flora.md`.
- Tests: crear `tests/test_verificador_advertencias.py`; modificar `tests/test_verificador.py` (los de 002 que cambian de sentido) y `tests/test_modelos.py`.
- Crear: `docs/adr/0012-advertencias-para-datos-faltantes-del-turista.md`, reporte en `docs/noches/`.

## Fuera de alcance
- Los campos `opciones_*` de la ficha (`corpus/schema.py`, `Bodega`) se quedan: son del corpus y los puede usar
  la respuesta como información, pero ya no se verifican.
- Normalizar nombres de otros idiomas ("inglés" vs "en"): eso corresponde al corpus o al relevamiento.
- Redactar las advertencias en la respuesta al turista (ítem 004) y decidir qué hace el flujo con ellas (005).
- Cambiar los demás "límites de la bodega" de ADR-0009 (horario, capacidad, precio, coordenadas): siguen igual.

## Supuestos
- **API compatible.** `verificar` sigue devolviendo `list[Violacion]` y se agrega `verificar_completo`. Así el
  loop de reintento (005) y el *hard pass rate* (007) siguen leyendo solo violaciones sin tocar sus llamadas, y
  los 60+ tests de 002 que no cambian de sentido no se editan.
- **Francés.** Se reconoce por código o nombre en español, francés o inglés (`fr`, `fra`, `fre`, `francés`,
  `frances`, `français`, `francais`, `french`), sin mayúsculas. El perfil lo llena el relevamiento (LLM), que
  puede escribir cualquiera de esas formas.
- **Dieta fuera del perfil.** Al sacar el campo, un `PerfilViaje` que todavía lo traiga lo ignora (comportamiento
  por defecto de Pydantic), igual que cualquier otro campo desconocido. No se agrega `extra="forbid"` para no
  ampliar el alcance; queda anotado en el ADR.
- `TIPOS_COMIDA` existía solo para el chequeo de dieta: se elimina junto con su test.
- Una advertencia por parada y por necesidad (si la misma bodega aparece dos veces, dos advertencias, igual que
  las violaciones), con `dia` y `bodega_id`, para que la respuesta pueda decir en qué visita falta confirmar.

## Cómo se verifica
Tests nuevos en `tests/test_verificador_advertencias.py` (archivo nuevo, para que el diff de los tests de 002 quede aislado):
- `test_accesibilidad_false_es_violacion` — `False` + movilidad reducida → violación `accesibilidad`, sin advertencias.
- `test_accesibilidad_sin_dato_es_advertencia` — `None` → ninguna violación y una advertencia
  `accesibilidad_sin_confirmar` con `dia`, `bodega_id` y un mensaje que dice "no pude confirmar" y nombra la bodega.
- `test_accesibilidad_sin_dato_no_pedida_no_advierte` — `None` sin movilidad reducida → sin advertencias.
- `test_accesibilidad_declarada_no_advierte` — `True` → resultado vacío.
- `test_frances_siempre_cumple` (parametrizado `fr`, `FR`, `francés`, `français`, `french`) — bodega con
  idiomas `[]` y otra con `["de"]` → ni violaciones ni advertencias.
- `test_frances_basta_entre_varios_pedidos` — pedidos `["ja", "fr"]` en bodega que publica `["de"]` → nada.
- `test_otro_idioma_con_lista_sin_el_pedido_es_violacion` — bodega publica `["fr", "de"]`, piden `en` → violación,
  sin advertencias.
- `test_otro_idioma_con_lista_que_lo_incluye` — piden `de` → nada.
- `test_otro_idioma_sin_lista_es_advertencia` — bodega y experiencia sin idiomas, piden `en` → ninguna violación,
  advertencia `idioma_sin_confirmar` que nombra el idioma y la bodega.
- `test_otro_idioma_sin_lista_en_la_experiencia_cae_a_la_bodega` — la experiencia no publica idiomas pero la
  bodega sí y no incluye el pedido → violación (no advertencia).
- `test_idioma_de_la_experiencia_manda_sobre_la_bodega` — experiencia publica `["fr"]`, bodega `["fr","en"]`, piden
  `en` → violación.
- `test_advertencias_no_cuentan_para_factible` — itinerario con solo advertencias → `factible is True`; con una
  violación → `False`.
- `test_verificar_devuelve_solo_las_violaciones` — `verificar(...) == verificar_completo(...).violaciones` en un caso
  que tiene ambas.
- `test_advertencias_en_orden_y_por_parada` — dos días con bodegas sin datos → advertencias ordenadas por día,
  una por parada y necesidad.
- `test_bodega_inexistente_no_advierte` — bodega fuera del corpus → solo `bodega_inexistente`, sin advertencias.
- `test_perfil_sin_restricciones_alimentarias` — `PerfilViaje` ya no tiene el campo; `"restriccion_alimentaria"`
  ya no es un tipo de violación (se valida contra `Violacion`).
- `test_idioma_base_reconoce_el_frances` — el conjunto contiene las formas listadas en Supuestos y no contiene `en`.

Tests de 002 que cambian de sentido (commit separado, justificados en el reporte):
- Se borran los de dieta (`test_almuerzo_*`, `test_cada_tipo_de_comida_chequea_dieta`, `test_degustacion_*`,
  `test_parada_sin_experiencia_no_chequea_dieta`, `test_vegano_*`, `test_vegetariano_*`, `test_dieta_*`) y
  `test_tipos_comida`: la regla deja de existir.
- `test_accesibilidad_no_declarada[None]`: pasa a ser advertencia (queda solo `[False]`).
- `test_idioma_sin_datos_es_violacion`: pedía `fr`, que ahora se cumple siempre → se reemplaza por los tests nuevos.
- `test_detecta_varias_en_la_misma_parada`, `test_mensaje_de_accesibilidad_nombra_la_bodega` y el segundo caso de
  `test_mensaje_de_idioma_nombra_la_experiencia_o_la_bodega`: usaban "sin dato" como violación; pasan a usar `False`
  / la advertencia.
- `test_bodega_inexistente_no_genera_otras_violaciones`: se saca el argumento de dieta (ya no existe).
- `tests/test_modelos.py::test_perfil_valida_rangos`: se saca el caso `restricciones_alimentarias=["sin_gluten"]`.

Sensores: `make check`; `make mutation MODULO=enot/verificador.py` (≥ 80%); `make registro`; `make tests-modificados`.

Flora a mano: que la redacción de las advertencias sirva para mostrarle al turista, y que esté de acuerdo con
sacar la dieta del alcance.
