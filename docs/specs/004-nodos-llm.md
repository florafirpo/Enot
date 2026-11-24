# Spec 004: nodos con LLM (relevamiento, planificador y respuesta)

**Ítem del backlog:** 004 · **Rama:** `noche/2026-11-24-004` · **ADRs relacionados:** ADR-0003 (workflow de
cinco nodos), ADR-0005 (el LLM no calcula), ADR-0006 (`ClienteLLM`, salida estructurada, trazas), ADR-0012
(advertencias), ADR-0013 (retrieval), ADR-0014 (nuevo)

## Qué se va a hacer
Los tres nodos del workflow de ADR-0003 que usan LLM, cada uno como función sobre datos (sin estado propio):

1. `relevar`: del historial del chat a un `PerfilViaje` completo, o a una `Pregunta` si falta un dato
   obligatorio o lo que dijo el turista no es válido (PRD 3, capacidad 1).
2. `planificar`: del perfil y las bodegas candidatas a un `Itinerario`; en el reintento recibe el itinerario
   anterior y las violaciones del verificador (PRD 3, capacidad 3).
3. `responder`: del itinerario verificado a un texto en español con horarios, precios, traslados, advertencias
   y fuentes (PRD 3, "Salida").

Todas las llamadas pasan por un cliente con la interfaz de `ClienteLLM` (ADR-0006) y quedan en una traza JSONL
(`data/trazas/`), con un evento por llamada (lineamientos D2.1).

El loop de reintento, la `Sesion` y la CLI son del ítem 005: acá no se encadenan los nodos.

## Interfaz
```python
# enot/trazas.py
class EventoTraza(BaseModel):
    conversacion: str; nodo: Literal["relevamiento", "planificador", "respuesta"]; intento: int  # del loop (005)
    proveedor: str; modelo: str; inicio: str  # ISO 8601 UTC
    latencia_s: float; tokens_in: int; tokens_out: int; intentos_validacion: int  # los de ClienteLLM
    estado: Literal["ok", "error"]; error: str | None
class Traza:
    def __init__(self, ruta: Path, conversacion: str | None = None)   # conversacion por defecto = ruta.stem
    @classmethod
    def nueva(cls, carpeta: Path | None = None) -> "Traza"            # data/trazas/<AAAAMMDD-HHMMSS>-<hex8>.jsonl
    def registrar(self, evento: EventoTraza) -> None                  # agrega una línea JSON (crea la carpeta)
    def eventos(self) -> list[EventoTraza]                            # lee lo escrito (vacío si no existe)

# enot/prompts/__init__.py
def cargar(nombre: str) -> str            # enot/prompts/<nombre>.md; FileNotFoundError si no existe

# enot/nodos.py
class Mensaje(BaseModel): rol: Literal["turista", "enot"]; texto: str
class Pregunta(BaseModel): texto: str; faltantes: list[str]
class BorradorPerfil(BaseModel)           # salida del LLM en relevamiento: los campos de PerfilViaje, todos
                                          # opcionales, con los mismos Literal, más fecha_inicio: date | None
class MotivoParada(BaseModel): bodega_id: str; motivo: str
class SalidaRespuesta(BaseModel): introduccion: str; motivos: list[MotivoParada] = []
class ErrorNodo(Exception)                # .nodo y la causa; se lanza si el cliente no logra salida válida
CAMPOS_OBLIGATORIOS = ("cantidad_dias", "dia_inicio", "transporte", "personas")

def relevar(historial: list[Mensaje], cliente, traza: Traza) -> PerfilViaje | Pregunta
def perfil_desde_borrador(b: BorradorPerfil) -> PerfilViaje | Pregunta      # código puro, sin LLM
def dia_de_semana(fecha: date) -> Dia                                      # código puro

def modelo_salida_planificador(ids: list[str], cantidad_dias: int) -> type[BaseModel]
def contexto_planificador(perfil, candidatas: list[Bodega], violaciones_previas: list[Violacion],
                          itinerario_previo: Itinerario | None) -> str
def planificar(perfil: PerfilViaje, candidatas: list[Bodega], violaciones_previas: list[Violacion],
               cliente, traza: Traza, itinerario_previo: Itinerario | None = None, intento: int = 1) -> Itinerario

def render_itinerario(itinerario, perfil, corpus: dict[str, Bodega], motivos: dict[str, str] | None = None,
                      advertencias: list[Advertencia] = ()) -> str                    # código puro
def responder(itinerario: Itinerario, perfil: PerfilViaje, corpus: dict[str, Bodega], cliente, traza: Traza,
              advertencias: list[Advertencia] = ()) -> str
```

### Qué hace cada nodo
**`relevar`.** Arma el transcript (cada mensaje entre etiquetas `<turista>`/`<enot>`; es dato, no instrucción,
lineamientos C.9) y le pide al cliente un `BorradorPerfil`. El LLM solo extrae lo que el turista dijo. Después,
código puro (`perfil_desde_borrador`):
- Si falta `dia_inicio` y hay `fecha_inicio`, el día de la semana lo calcula `dia_de_semana` (no el LLM,
  ADR-0005). Si están los dos y no coinciden, es `Pregunta(faltantes=["dia_inicio"])`.
- Si falta algún campo de `CAMPOS_OBLIGATORIOS` → `Pregunta` con todos los que faltan, en ese orden, y un texto
  fijo por campo (lo escribe el código, no el LLM).
- Si están todos pero `PerfilViaje` no valida (p. ej. 5 días, 0 personas, jornada al revés) → `Pregunta` con el
  campo inválido en `faltantes` y un texto que dice por qué ("Enot arma itinerarios de 1 a 3 días…").
- Si valida → `PerfilViaje`.
El relevamiento es sin estado: cada vez se reextrae todo el historial (el turista puede corregirse).

**`planificar`.** Si no hay candidatas, `ValueError` sin llamar al LLM (el flujo informa antes, 005). Arma el
contexto con `contexto_planificador`:
- el perfil (JSON) y los días del viaje ya calculados por código (`dias_del_viaje`: "Día 1: jue", …);
- cada candidata con solo lo que sirve para planificar (id, nombre, zona, comuna, horarios, experiencias con
  tipo, duración, precio y moneda tal como están, idiomas, accesibilidad, capacidad, reserva, descripción breve
  recortada a 300 caracteres) dentro de `<candidatas>`, marcada como dato (C.9, C.12);
- la matriz de tiempos de traslado entre candidatas en el transporte del perfil, calculada con
  `tiempo_traslado` ("sin dato" si falta ubicación). El LLM no estima distancias (ADR-0005);
- en el reintento, el itinerario anterior y la lista de violaciones con su mensaje, pidiendo corregirlas todas.
La salida se pide con un modelo armado para esa llamada (`modelo_salida_planificador`): `bodega_id` es un
`Literal` con los ids de las candidatas (no puede inventar bodegas, C.7) y `dias` tiene exactamente
`cantidad_dias` elementos. Si no valida, `ClienteLLM` reintenta una vez con el error (ADR-0006). El
`Itinerario` lo arma el código: número y día de la semana de cada día salen de `dias_del_viaje(perfil)`.

**`responder`.** El LLM escribe solo la introducción y un motivo por parada (por qué esa bodega encaja con las
preferencias), sin horarios ni precios. El resto lo arma `render_itinerario`, en código:
- por día, el título con el día de la semana; por parada: franja horaria, nombre y comuna, experiencia (o
  "experiencia a elegir en la bodega"), precio por persona en EUR o "precio a consultar", traslado desde la
  parada anterior en minutos (o "sin dato"), el motivo del LLM si vino para esa bodega, y la fuente (primera de
  `fuentes`, o `url_web`);
- el total estimado por persona con `costo_experiencias` (y cuántas paradas quedan sin precio);
- "Para tener en cuenta": cada advertencia del verificador (ADR-0012), siempre, aunque el LLM no las mencione.
Los motivos con un `bodega_id` que no está en el itinerario se ignoran.

**Trazas.** Cada llamada al cliente, salga bien o mal, agrega un `EventoTraza` (latencia medida con
`perf_counter`; tokens e intentos de validación del `Resultado`). Si el cliente lanza, se registra con
`estado="error"` y se relanza como `ErrorNodo`.

## Archivos a tocar
- Crear: `enot/nodos.py`, `enot/trazas.py`, `enot/prompts/__init__.py`, `enot/prompts/relevamiento.md`,
  `enot/prompts/planificador.md`, `enot/prompts/respuesta.md`, `tests/test_nodos.py`, `tests/test_trazas.py`,
  `docs/adr/0014-nodos-llm-contexto-y-salidas-acotadas.md`.
- Modificar: `CHANGELOG.md`, `BACKLOG.md`, `docs/feedback-flora.md` (decisiones pendientes).

## Fuera de alcance
- `Sesion`, loop de reintento, circuit breaker, tope de tokens y CLI (ítem 005).
- Ajuste conversacional ("sacá la segunda bodega"): lo resuelve 005 sobre el itinerario vigente.
- Tool calling dentro del planificador: los tiempos se precalculan y van en el contexto (ADR-0014).
- Temperatura > 0 en el planificador: `ClienteLLM` usa 0 fijo; cambiarlo toca `corpus/llm.py` (queda anotado).
- Costo en USD por llamada: la tabla de precios por modelo va en el reporte (ítem 008); la traza guarda tokens.
- No se tocan `corpus/llm.py`, `enot/verificador.py`, `enot/retrieval.py` ni tests existentes.

## Supuestos
- **Las preguntas las escribe el código.** Un texto fijo por campo evita que el LLM pregunte por algo que ya se
  dijo o invente opciones (p. ej. "¿4 días?"). Costo: menos natural. Alternativa en ADR-0014.
- **Fecha → día de la semana en código.** El LLM llena `fecha_inicio` solo si el turista dio día, mes y año; si
  no, deja `null` y, si tampoco hay día de la semana, se repregunta. Inferir el año sería aritmética de fechas.
- **`candidatas` como `list[Bodega]`** (no `list[Candidata]`): el flujo resuelve los ids contra el corpus; el
  nodo necesita los datos de la ficha, no el puntaje.
- **`responder` recibe `corpus` y `advertencias`** además de lo que dice el backlog: hacen falta para nombres,
  fuentes, costos y para que las advertencias de ADR-0012 lleguen al turista.
- **Los prompts son Markdown en `enot/prompts/`** y se leen con `cargar`; los datos van en el mensaje de usuario,
  las reglas en el de sistema.
- Las respuestas del `ClienteFalso` en los tests son datos SINTÉTICOS (bodegas de
  `tests/fixtures/fichas_sinteticas.jsonl` o inventadas con `[SINTÉTICA]`).

## Cómo se verifica
Tests en `tests/test_nodos.py` (todos con `ClienteFalso`, sin red):

Relevamiento
- `test_relevar_perfil_completo`: borrador con los cuatro obligatorios + idiomas → `PerfilViaje` con esos valores.
- `test_relevar_repregunta_si_falta_un_obligatorio` (parametrizado por cada campo de `CAMPOS_OBLIGATORIOS`):
  quitar ese campo → `Pregunta` con `faltantes == [campo]` y el texto fijo de ese campo.
- `test_relevar_repregunta_todos_los_que_faltan_en_orden`: borrador vacío → los cuatro, en el orden de la tupla.
- `test_relevar_valor_invalido_repregunta_con_motivo`: 5 días → `Pregunta(["cantidad_dias"])` cuyo texto dice
  "1 a 3"; 0 personas → `["personas"]`; jornada 19:00–09:00 → `["hora_inicio_jornada", "hora_fin_jornada"]`.
- `test_relevar_fecha_calcula_dia_de_semana`: `fecha_inicio=2026-12-03` sin día → perfil con `dia_inicio="jue"`.
- `test_relevar_fecha_y_dia_inconsistentes_repregunta`: fecha jueves + `dia_inicio="lun"` → `Pregunta(["dia_inicio"])`.
- `test_dia_de_semana_los_siete_dias`: una semana entera, lunes a domingo.
- `test_relevar_contexto_incluye_historial_etiquetado`: el mensaje de usuario tiene cada texto del historial,
  en orden, dentro de `<turista>`/`<enot>`; el de sistema es el prompt `relevamiento`.
- `test_relevar_no_confia_en_el_llm_para_completar`: el borrador trae `personas=None` aunque el LLM "diga" en
  `preferencias` que son 2 → igual repregunta (la decisión es del código).

Planificador
- `test_planificar_arma_itinerario_con_dias_del_perfil`: la salida trae días sin número ni día de semana; el
  itinerario tiene `numero` 1..n y `dia_semana` = `dias_del_viaje(perfil)` (vie, sab con inicio vie).
- `test_planificar_rechaza_bodega_fuera_de_candidatas`: primera respuesta con un id que no está entre las
  candidatas → el cliente reintenta (2 llamadas) y queda la segunda; si las dos fallan → `ErrorNodo`.
- `test_planificar_exige_cantidad_de_dias`: 1 día cuando el perfil pide 2 → no valida (reintento).
- `test_modelo_salida_planificador_esquema`: el JSON Schema tiene `enum` con los ids y `minItems`/`maxItems`
  = cantidad de días.
- `test_contexto_planificador_primer_intento`: incluye cada id y nombre de candidata, los precios tal como están
  (`60` y `"EUR"`), los días del viaje, los minutos de traslado calculados con `tiempo_traslado` para un par
  real de la fixture, "sin dato" para la bodega sin coordenadas, y no incluye la sección de violaciones.
- `test_contexto_planificador_reintento_incluye_violaciones`: con violaciones previas e itinerario previo,
  el contexto trae cada mensaje de violación y el itinerario anterior (ids y horas).
- `test_planificar_sin_candidatas_no_llama_al_llm`: `ValueError` y el cliente no registró llamadas.
- `test_contexto_planificador_ficha_es_dato`: una descripción con "Ignorá las instrucciones" queda dentro de
  `<candidatas>` y recortada a 300 caracteres.

Respuesta
- `test_render_itinerario_datos_del_codigo`: franja "10:00–11:00", nombre, comuna, "20.00 EUR" de la
  experiencia, traslado en minutos igual a `tiempo_traslado`, fuente de la ficha y total por persona igual a
  `costo_experiencias / personas`.
- `test_render_itinerario_precio_a_consultar_y_sin_experiencia`: experiencia sin precio en EUR → "precio a
  consultar"; parada sin experiencia → "experiencia a elegir en la bodega".
- `test_responder_incluye_advertencias_aunque_el_llm_no`: el LLM no las menciona y aparecen igual.
- `test_responder_usa_motivos_solo_de_paradas_del_itinerario`: motivo de una bodega ajena no aparece; el de
  una del itinerario sí, junto a esa parada.
- `test_responder_contexto_sin_numeros_calculados_por_el_llm`: el prompt de sistema es `respuesta` y el
  mensaje de usuario trae nombres y preferencias del turista.

Trazas (`tests/test_nodos.py` y `tests/test_trazas.py`)
- `test_cada_nodo_registra_un_evento`: relevar + planificar + responder → 3 eventos con nodo, proveedor y modelo
  del cliente, tokens del `Resultado`, `estado="ok"` e `intento` del planificador.
- `test_error_del_cliente_se_registra_y_relanza`: cliente que siempre da JSON inválido → `ErrorNodo` y un evento
  con `estado="error"` y el mensaje.
- `test_traza_nueva_crea_archivo_en_carpeta`, `test_traza_registrar_y_leer`, `test_traza_vacia_sin_archivo`,
  `test_evento_traza_valida_campos` (estado fuera del `Literal` falla).
- `test_cargar_prompt_existente_y_faltante`: los tres prompts existen y no están vacíos; uno inexistente →
  `FileNotFoundError`.

Agregados después del código (contratos exactos y casos encontrados con mutation testing)
- `test_perfil_desde_borrador_pasa_campos_opcionales`: presupuesto, movilidad, zonas, bodegas a evitar,
  preferencias y jornada pasan al perfil; sin jornada quedan los valores por defecto.
- `test_contexto_planificador_exacto`: el contexto completo para 3 bodegas armadas a mano (una sin coordenadas,
  una sin comuna) es exactamente el esperado, y no lleva `incluye`, `precio_texto` ni URLs.
- `test_render_itinerario_exacto`: el detalle completo (traslado con y sin dato, bodega fuera del corpus, día sin
  visitas, total con paradas sin precio, advertencias) es exactamente el esperado.
- `test_render_itinerario_desde_precio_y_moneda_desconocida`: sin experiencia → "desde X EUR"; un precio sin
  moneda no se muestra como euros; bodega sin fuentes ni web → sin línea "Fuente".
- `test_render_parada_fuera_del_corpus_no_corta_el_dia_ni_inventa_traslado`.
- `test_relevar_mensaje_exacto_y_texto_del_turista_escapado`: `</turista><enot>` en el texto del turista no
  cierra la etiqueta.
- `test_texto_de_pregunta_exacto`, `test_relevar_varios_invalidos_y_presupuesto` (dos inválidos a la vez,
  presupuesto negativo, hora "25:00").
- `test_responder_mensaje_exacto`: el mensaje de usuario completo y el texto final (introducción recortada,
  motivo bajo su parada).
- `test_traza_de_error_detalles`, `test_traza_ok_inicio_utc_y_latencia`: error recortado a 500 caracteres,
  causa conservada en `ErrorNodo`, inicio en UTC, latencia medida.
- `test_modelo_salida_planificador_validaciones`: ids repetidos, día sin paradas, duración 0, hora inválida,
  id ajeno y lista vacía.
- `test_con_la_muestra_real_de_datatourisme`: la muestra real pasa por el paso `datatourisme` en una carpeta
  temporal; con 10 candidatas de Chablis, el contexto trae sus ids en orden, descripciones ≤ 300 caracteres, 45
  pares de traslado y menos de 20.000 caracteres; `planificar` acepta un id real.
- `tests/test_trazas.py`: `test_traza_nueva_por_defecto_en_data_trazas`, `test_traza_crea_carpetas_anidadas`.

Sensores: `make check`; `make registro`; `make tests-modificados` (ningún test existente cambia). Mutation no
es obligatorio (no se tocan verificador, tools ni métricas); se corre igual sobre `enot/nodos.py` y se informa.

Qué tendría que revisar Flora a mano: el texto de los tres prompts y las preguntas fijas del relevamiento.
