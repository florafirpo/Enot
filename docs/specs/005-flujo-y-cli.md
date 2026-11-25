# Spec 005: flujo completo con loop de verificación y CLI (tracer bullet)

**Ítem del backlog:** 005 · **Rama:** `noche/2026-11-24-005` · **ADRs relacionados:** ADR-0003 (workflow con
verificador y circuit breaker), ADR-0004/0013 (retrieval), ADR-0006 (`ClienteLLM`), ADR-0012 (advertencias),
ADR-0014 (nodos), ADR-0015 (nuevo)

## Qué se va a hacer
Conectar de punta a punta los cinco nodos de ADR-0003 (relevar → buscar → planificar → verificar → responder) en
un turno de conversación sobre una `Sesion` serializable, con el loop de reintento acotado por un circuit breaker
(intentos y tokens), y un chat por consola (`python -m enot`) que puede retomar una sesión guardada.
Cubre el PRD 3 (capacidades 1–4, incluido el ajuste conversacional) y es el tracer bullet de lineamientos C.10.

## Interfaz
```python
# enot/flujo.py
MAX_INTENTOS = 3          # ADR-0003; 1 = ablación B2 (sin loop de verificación)
TOPE_TOKENS = 200_000     # por conversación (tokens de entrada + salida conocidos en la traza)
K_CANDIDATAS = 10

class Sesion(BaseModel):                       # todo el estado de una conversación; JSON ida y vuelta
    conversacion: str
    ruta_traza: str                            # la traza sigue en el mismo archivo al retomar
    historial: list[Mensaje] = []
    perfil: PerfilViaje | None = None          # el último perfil completo
    itinerario: Itinerario | None = None       # el vigente: siempre uno que pasó el verificador
    advertencias: list[Advertencia] = []       # las del itinerario vigente
    @classmethod
    def nueva(cls, carpeta_trazas: Path | None = None) -> "Sesion"
    def traza(self) -> Traza
    def guardar(self, ruta: Path) -> None
    @classmethod
    def cargar(cls, ruta: Path) -> "Sesion"

TipoRespuesta = Literal["pregunta", "itinerario", "infactible", "zona_desconocida", "sin_candidatas",
                        "tope_tokens", "error"]

class Respuesta(BaseModel):
    tipo: TipoRespuesta
    texto: str                                  # lo que ve el turista
    intentos: int = 0                           # llamadas al planificador en este turno
    itinerario: Itinerario | None = None        # la última propuesta (válida o no): sirve para evaluar B2
    violaciones: list[Violacion] = []           # las de la última propuesta
    advertencias: list[Advertencia] = []

def tokens_usados(traza: Traza) -> int          # suma tokens_in + tokens_out conocidos (None no suma)
DESCRIPCION_VIOLACION: dict[TipoViolacion, str] # cada tipo, en palabras del turista
def explicar_infactible(violaciones: list[Violacion], intentos: int, hay_vigente: bool) -> str
def explicar_sin_candidatas(bodegas: Iterable[Bodega], perfil: PerfilViaje) -> str
def avisar_zonas_desconocidas(zonas: list[str], conocidas: Iterable[str]) -> str

class Flujo:
    def __init__(self, cliente, corpus: dict[str, Bodega], indice: Indice, max_intentos: int = MAX_INTENTOS,
                 tope_tokens: int = TOPE_TOKENS, k: int = K_CANDIDATAS)    # ValueError si max_intentos o tope < 1
    def turno(self, sesion: Sesion, texto: str) -> Respuesta               # modifica la sesión

# enot/nodos.py (cambio compatible)
def contexto_planificador(..., itinerario_previo, pedido_ajuste: str | None = None) -> str
def planificar(..., intento: int = 1, pedido_ajuste: str | None = None) -> Itinerario

# enot/__main__.py
def main(argv: list[str] | None = None, leer=input, escribir=print, construir_flujo=None) -> int
#   python -m enot [--sesion archivo.json] [--fichas ruta] [--max-intentos N] [--tope-tokens N] [--k N]
```

### Un turno (`Flujo.turno`)
1. Si `tokens_usados(traza) >= tope_tokens`: responde `tope_tokens` sin llamar al LLM.
2. Agrega el mensaje del turista al historial y llama a `relevar`. Si devuelve `Pregunta`: responde `pregunta`.
3. Guarda el perfil. Si `Indice.zonas_desconocidas(perfil)` no está vacía: responde `zona_desconocida`
   ("No reconozco la zona X…", con las zonas que sí conoce) sin buscar ni planificar.
4. Candidatas = `Indice.buscar(perfil, k)`. Si hay itinerario vigente (es un **ajuste**), antes se suman sus
   bodegas que siguen pasando los filtros duros del perfil (`motivo_exclusion is None`), para que el planificador
   pueda conservarlas (el esquema de salida solo acepta ids de candidatas). Sin candidatas: responde
   `sin_candidatas` con los motivos de exclusión más frecuentes.
5. Loop `intento = 1..max_intentos`: chequea el tope de tokens (si se alcanzó, corta con `tope_tokens`),
   `planificar` (en un ajuste, con `itinerario_previo` = vigente y `pedido_ajuste` = el mensaje del turista; en los
   reintentos, con la propuesta anterior y sus violaciones) y `verificar_completo`. Sin violaciones → sale.
6. Si hubo itinerario factible: pasa a ser el vigente (con sus advertencias) y se responde con `responder`.
   Si el tope de tokens se alcanzó justo antes o `responder` falla, el texto es `render_itinerario` (código, sin
   LLM): un itinerario válido no se tira.
7. Si no: responde `infactible` con `explicar_infactible`; el vigente anterior (si había) no cambia.
8. La respuesta del sistema se agrega al historial como mensaje `enot`. Si un nodo lanza `ErrorNodo` (antes de
   tener un itinerario válido), se responde `error` y el historial queda como estaba antes del turno.

## Archivos a tocar
- Crear: `enot/flujo.py`, `enot/__main__.py`, `tests/test_flujo.py`, `tests/test_cli.py`, ADR-0015.
- Modificar: `enot/nodos.py` (parámetro `pedido_ajuste`), `enot/prompts/planificador.md` (cómo usar el pedido),
  `BACKLOG.md`, `CHANGELOG.md`, `docs/noches/…`.

## Fuera de alcance
- Clasificar la intención del mensaje: con un itinerario vigente, todo mensaje se trata como ajuste.
- Ignorar palabras vacías en `_coincide_zona` (opcional en el ítem; no hace falta para el aviso de zonas).
- Temperatura > 0 en el reintento, tool calling, invariante "ok ⇒ tokens" en `EventoTraza` (ítem 008).
- Interfaz web (ítem 009). No se tocan `corpus/llm.py`, el verificador ni las tools.

## Supuestos
- **Ajuste = replanificar sobre el vigente.** El planificador recibe el itinerario vigente y el pedido textual, y la
  regla "cambiá lo menos posible" (prompt). Editar en código ("sacá la 2.ª") exigiría interpretar lenguaje natural
  sin LLM. El resultado pasa por el mismo verificador; si no es factible, el vigente se conserva.
- **Tope de tokens = tokens conocidos de la traza de la conversación.** Una sola fuente de verdad, que sobrevive al
  retomar. Los eventos con error (`None`) no suman: el tope queda subestimado en esos casos, pero el tope de
  intentos los acota igual. Se chequea antes de cada llamada, así que una llamada puede pasarlo (no se corta a la
  mitad). 200 000: un turno peor caso (relevamiento + 3 planificaciones + respuesta) ronda 25 000 tokens con
  k = 10; alcanza para unos 6–8 turnos con itinerario.
- **El mensaje de infactible lo escribe el código** (sin LLM): enumera qué condición no se pudo cumplir
  (`DESCRIPCION_VIOLACION`) y el detalle del último intento, y propone cambiar alguna.
- **Error de un nodo:** se informa y no queda nada a medias en la sesión, para que el turista pueda repetir.

## Cómo se verifica
Tests en `tests/test_flujo.py` (corpus SINTÉTICO, `ClienteFalso` con un guion por nodo, `EmbedderFalso`):
- `test_turno_pregunta_si_falta_un_dato`: relevamiento sin `personas` → `pregunta` con el texto fijo; no se llama
  al planificador; el historial queda con el mensaje del turista y la pregunta.
- `test_flujo_reintenta_y_termina_valido`: el planificador propone primero algo inválido (fuera de horario) y
  después algo válido → `itinerario`, `intentos == 2`, el vigente es el segundo; el contexto del 2.º intento trae
  las violaciones del verificador y el itinerario anterior; la traza tiene planificador con intento 1 y 2.
- `test_flujo_corta_en_max_intentos_y_explica`: siempre inválido → exactamente 3 llamadas al planificador,
  `infactible`, el texto nombra la condición incumplida y el detalle; no hay vigente ni llamada a `respuesta`.
- `test_max_intentos_1_es_la_ablacion_b2`: una sola llamada; `Respuesta.itinerario` es la propuesta inválida y
  trae sus violaciones.
- `test_max_intentos_y_tope_invalidos`: `max_intentos=0` o `tope_tokens=0` → `ValueError`.
- `test_ajuste_edita_el_itinerario_vigente`: después de un itinerario de 2 paradas, "sacá la segunda bodega" → el
  planificador recibe el vigente y el pedido (`<pedido>…</pedido>`); el nuevo vigente tiene 1 parada.
- `test_ajuste_suma_las_bodegas_vigentes_a_las_candidatas`: con `k=1`, las bodegas del vigente siguen entre las
  candidatas; una que el turista ahora pidió evitar, no.
- `test_ajuste_infactible_conserva_el_vigente`: el ajuste no se logra en 3 intentos → el vigente no cambia y el
  texto lo dice.
- `test_zona_desconocida_avisa_sin_buscar`: "Alsacia" → `zona_desconocida`, "No reconozco la zona Alsacia", sin
  planificador; "Chablis" no dispara el aviso.
- `test_sin_candidatas_explica_por_que`: ninguna bodega abre ese día en esa zona → `sin_candidatas` con el motivo;
  sin planificador.
- `test_tope_de_tokens_corta_el_loop`: con un tope que se alcanza tras el 1.er intento inválido → `tope_tokens`, una
  sola llamada al planificador; el turno siguiente no llama al LLM.
- `test_tope_antes_de_responder_entrega_el_detalle_sin_llm`: tope alcanzado con un itinerario válido → el texto es
  `render_itinerario`, el vigente se guarda y no se llama a `respuesta`.
- `test_error_de_nodo_no_ensucia_la_sesion`: el relevamiento falla → `error`, historial sin cambios.
- `test_error_en_respuesta_degrada_al_detalle`: `respuesta` falla → `itinerario` con el texto de `render_itinerario`.
- `test_sesion_ida_y_vuelta_y_tokens_continuan`: guardar y cargar da la misma sesión; la traza sigue en el mismo
  archivo y `tokens_usados` no vuelve a 0.
- `test_tokens_usados_ignora_desconocidos`: suma solo tokens conocidos.
- `test_descripcion_violacion_cubre_todos_los_tipos` y `test_explicar_infactible_texto` (descripciones sin repetir y
  en orden, detalle, cantidad de intentos, "sigue vigente" solo si hay vigente).
- `test_avisar_zonas_desconocidas_texto` y `test_contexto_planificador_con_pedido_de_ajuste` (sección exacta, `<` y
  `>` del pedido neutralizados; sin pedido, el contexto no cambia).
- `test_con_la_muestra_real_de_datatourisme`: un turno completo sobre las bodegas de `data/datatourisme/muestra.csv`
  (se saltea si no está).

Tests en `tests/test_cli.py` (sin red: el flujo se inyecta):
- `test_cli_conversa_y_guarda_la_sesion` (una línea vacía no es un turno; "salir" corta; la traza va a
  `data/trazas/`), `test_cli_termina_con_eof_sin_sesion`, `test_cli_retoma_la_sesion` (el relevamiento ve el
  historial anterior y la traza sigue en el mismo archivo), `test_cli_pasa_las_opciones_al_flujo` (`--fichas`,
  `--max-intentos`, `--tope-tokens`, `--k` y sus valores por defecto), `test_cli_sin_corpus_sale_con_error` (sin
  fichas: mensaje y código 1, sin construir el cliente LLM), `test_cli_rechaza_valores_no_positivos`.

Sensores: `make check`; mutation sobre `enot/flujo.py` (no obligatorio; resultado en el reporte). Flora: probar
`python -m enot` con su clave (26–27/11) y leer los textos fijos de `enot/flujo.py`.
