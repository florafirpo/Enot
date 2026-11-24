# Spec 002: Verificador de restricciones duras

> **Reemplazada parcialmente por la spec 010 / ADR-0012** (24/11): la dieta salió del alcance y las
> necesidades del turista sin dato (accesibilidad, idioma) pasan a ser advertencias. El francés se cumple siempre.

**Ítem del backlog:** 002 · **Rama:** `noche/2026-11-24-002` (sale de `noche/2026-11-23-001`, todavía sin
aprobar) · **ADRs relacionados:** ADR-0003, ADR-0005, ADR-0007, ADR-0009 (nuevo)

## Qué se va a hacer
El nodo `verificador` del workflow (ADR-0003): código puro que recibe un itinerario, el perfil del viaje y
el corpus, y devuelve la lista de restricciones duras que no se cumplen, cada una con un mensaje que el
planificador pueda usar para corregir. Lista vacía = itinerario factible. Es también el criterio del
*hard pass rate* (PRD 6, ADR-0007).

## Interfaz

`enot/verificador.py`
- `TipoViolacion = Literal["bodega_inexistente", "experiencia_inexistente", "cerrada", "traslado_imposible",
  "jornada_excedida", "presupuesto_excedido", "grupo_excede_capacidad", "restriccion_alimentaria",
  "accesibilidad", "idioma_no_disponible"]`
- `Violacion(BaseModel)`: `tipo: TipoViolacion`, `mensaje: str` (accionable, en español),
  `dia: int | None` (número de día del itinerario; `None` si es global), `bodega_id: str | None`.
- `verificar(itinerario: Itinerario, perfil: PerfilViaje, corpus: dict[str, Bodega]) -> list[Violacion]`.
  Nunca lanza excepciones por datos del itinerario (errores como valor, igual que las tools).
  El orden es determinístico: día por día, parada por parada, y el presupuesto (global) al final.
- `TIPOS_COMIDA = {"almuerzo", "cena", "picnic", "maridaje"}`: experiencias que incluyen comida.

## Reglas (una por tipo)
| Tipo | Se viola cuando… | No se viola cuando… |
|---|---|---|
| `bodega_inexistente` | el `bodega_id` no está en el corpus | está. (Las demás reglas de esa parada se saltean.) |
| `experiencia_inexistente` | la parada nombra una experiencia que la bodega no publica | no nombra ninguna, o la nombra sin distinguir mayúsculas |
| `cerrada` | `abierta_en` devuelve `abierta=False` para ese día de la semana, hora y duración | devuelve `True`, o `None` (la bodega no publica horario: no se sabe) |
| `traslado_imposible` | entre dos paradas consecutivas del mismo día (en el orden del itinerario), la siguiente empieza antes de `fin anterior + tiempo_traslado(modo del perfil)`; o se superponen aunque no se pueda calcular el traslado | entra justo (inicio siguiente = fin + traslado) |
| `jornada_excedida` | la primera visita del día empieza antes de `hora_inicio_jornada` o la última termina después de `hora_fin_jornada` (una violación por día) | empieza y termina justo en los bordes |
| `presupuesto_excedido` | hay presupuesto y el costo por persona de todo el itinerario (con `costo_experiencias`) lo supera | es igual o menor, o el perfil no tiene presupuesto |
| `grupo_excede_capacidad` | la bodega publica `capacidad_max_grupo` y `perfil.personas` la supera | es igual o menor, o la capacidad no está publicada |
| `restriccion_alimentaria` | la parada es una experiencia con comida (`TIPOS_COMIDA`) y la bodega no declara (`True`) la opción para cada restricción del perfil | la experiencia no tiene comida, no se eligió experiencia, o la opción está declarada. Vegano declarado cubre vegetariano |
| `accesibilidad` | el perfil pide movilidad reducida y la bodega no declara `accesible_movilidad_reducida=True` | lo declara, o el perfil no lo pide |
| `idioma_no_disponible` | el perfil pide idiomas y ninguno figura en los idiomas de la experiencia elegida (o, si no se eligió o no los publica, en los de la bodega) | alguno coincide (sin distinguir mayúsculas), o el perfil no pide idioma |

## Archivos a tocar
- Crear: `enot/verificador.py`, `tests/test_verificador.py`, `docs/specs/002-verificador.md`.
- Modificar: `CHANGELOG.md`, `BACKLOG.md`, `docs/noches/2026-11-24.md`.

## Fuera de alcance
- Llamar al planificador o reintentar (eso es el flujo, ítem 005).
- Chequear que la cantidad de días o los días de la semana coincidan con el perfil, y `bodegas_evitar`:
  no están en la lista del backlog; quedan anotados como posibles agregados.
- Que la duración de la parada coincida con la duración publicada de la experiencia.
- No se tocan las tools ni los modelos de 001.

## Supuestos
- **Dos criterios para lo desconocido, con una regla única.** Lo que es un *límite de la bodega* (horario,
  coordenadas para el traslado, capacidad, precio) solo viola si hay evidencia del límite: sin dato no se
  marca, porque marcarlo descartaría justo a las bodegas chicas, que publican menos (PRD 1). Lo que es una
  *necesidad del turista* (accesibilidad, dieta, idioma) solo se cumple con evidencia positiva: `None` o
  ausencia cuenta como violación, porque garantizar algo que no sabemos sería inventar datos.
- **Experiencia sin nombrar:** para el costo se usa la más barata en EUR (como `costo_experiencias`); para
  la dieta no se chequea (no sabemos si come); para el idioma se usan los idiomas de la bodega.
- **`experiencia_inexistente` es un tipo que no estaba en el backlog.** Se agrega porque sin él el
  presupuesto se puede esquivar: si el planificador inventa una experiencia, la tool de costos la saltea y
  el total baja. Además es una alucinación que el PRD quiere medir.
- **Traslado:** se usa el orden de las paradas tal como vienen (es la secuencia que se le muestra al
  turista). Paradas desordenadas en el tiempo se detectan como superposición.
- **Presupuesto:** se compara `total_eur > presupuesto × personas` para no dividir floats.
- **Datos de los tests:** las bodegas se construyen en el test o vienen de `fichas_sinteticas.jsonl`;
  todas son inventadas y lo dicen en el nombre.

## Cómo se verifica
`tests/test_verificador.py` (por cada tipo, un caso que lo detecta y uno que no lo confunde):
- `test_itinerario_valido_no_tiene_violaciones` / `test_itinerario_vacio_es_valido`.
- `test_valido_con_la_fixture_de_fichas`: un día real con bodegas de `fichas_sinteticas.jsonl`.
- Inexistente: `test_detecta_bodega_inexistente`, `test_bodega_inexistente_no_genera_otras_violaciones`.
- Experiencia: `test_detecta_experiencia_inexistente`, `test_experiencia_por_nombre_sin_mayusculas`.
- Horario: `test_detecta_visita_antes_de_abrir` (9:59 con apertura 10:00), `test_cruza_el_cierre_por_un_minuto`,
  `test_dia_cerrado`, `test_usa_el_dia_de_la_semana_del_itinerario`, `test_sin_horario_publicado_no_es_violacion`,
  `test_mensaje_de_cerrada_explica_el_horario`.
- Traslado: `test_traslado_entra_justo`, `test_traslado_falta_un_minuto`, `test_traslado_usa_el_modo_del_perfil`
  (lo que entra en auto no entra a pie), `test_superposicion_sin_coordenadas`,
  `test_sin_coordenadas_y_sin_superposicion_no_es_violacion`, `test_traslado_solo_entre_paradas_del_mismo_dia`,
  `test_paradas_desordenadas_se_detectan`.
- Jornada: `test_jornada_bordes_exactos`, `test_jornada_empieza_antes`, `test_jornada_termina_despues`,
  `test_jornada_una_violacion_por_dia`.
- Presupuesto: `test_presupuesto_igual_no_es_violacion`, `test_presupuesto_excedido_por_un_euro`,
  `test_presupuesto_suma_todos_los_dias`, `test_sin_presupuesto_no_se_chequea`,
  `test_presupuesto_no_cuenta_precios_sin_eur`, `test_presupuesto_es_por_persona`.
- Capacidad: `test_grupo_igual_a_capacidad`, `test_grupo_supera_capacidad`, `test_capacidad_no_publicada`.
- Dieta: `test_almuerzo_sin_opcion_declarada`, `test_almuerzo_con_opcion_declarada`,
  `test_degustacion_no_chequea_dieta`, `test_vegano_cubre_vegetariano`, `test_vegetariano_no_cubre_vegano`,
  `test_dieta_None_es_violacion`, `test_dieta_una_violacion_por_restriccion`.
- Accesibilidad: `test_accesibilidad_no_declarada`, `test_accesibilidad_declarada`,
  `test_accesibilidad_no_pedida`.
- Idioma: `test_idioma_de_la_experiencia`, `test_idioma_no_disponible_en_la_experiencia`,
  `test_idioma_cae_a_la_bodega`, `test_idioma_sin_datos_es_violacion`, `test_idioma_sin_mayusculas`,
  `test_idioma_no_pedido`.
- Generales: `test_cada_violacion_trae_dia_bodega_y_mensaje`, `test_orden_determinista`.

Sensores: `make check`; `make mutation MODULO=enot/verificador.py` con al menos 80% de mutantes muertos.

Revisión de Flora: la regla de "lo desconocido" (tabla de supuestos) y el tipo nuevo `experiencia_inexistente`.
