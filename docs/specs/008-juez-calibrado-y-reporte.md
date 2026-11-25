# Spec 008: juez LLM calibrado y reporte de costos y latencia

**Ítem del backlog:** 008 · **Rama:** `noche/2026-11-25-008` · **ADRs relacionados:** ADR-0007 (evaluación),
ADR-0006 (cliente LLM), ADR-0014 (tokens desconocidos como `None`), ADR-0017 (métricas y reporte del benchmark),
ADR-0018 (nuevo)

## Qué se va a hacer
La mitad "no verificable" de la evaluación y la economía del sistema (PRD 6 y 9, área de profundización 4):
- un juez LLM con rúbrica 1–5 que mide el ajuste a las preferencias blandas (H2);
- su calibración contra la anotación humana de Flora (Spearman y kappa), con una planilla para anotar;
- el reporte final `reports/resultados.md`: métricas por sistema, preference score, costo (tokens y USD) y latencia
  (media y p95), contados desde las trazas.

Además, los dos pendientes de la revisión 004 que el backlog asignó a este ítem: las llamadas fallidas se cuentan (no
se suman como 0), el error de `ClienteLLM` trae los tokens consumidos, y `EventoTraza` exige tokens cuando
`estado == "ok"`.

## Interfaz
```python
# corpus/llm.py
class ErrorSalidaInvalida(RuntimeError):      # ClienteLLM agotó los intentos de validación
    tokens_in: int; tokens_out: int; intentos: int   # lo que se gastó en esas llamadas (exacto)
# ClienteLLM.estructurado lanza ErrorSalidaInvalida en vez de RuntimeError (es subclase: no rompe a nadie).
# Un error del proveedor (red, clave) sigue saliendo tal cual: ahí no se sabe cuánto se gastó.

# enot/trazas.py
EventoTraza  # model_validator: estado == "ok" exige tokens_in y tokens_out (no None)

# enot/nodos.py — _llamar: si la causa trae tokens (ErrorSalidaInvalida), el evento de error los registra;
# si no, quedan en None como hasta ahora.

# eval/metricas.py
SalidaSistema.traza: str | None = None        # ruta de la traza de esa consulta (Enot y B2)
# eval/baselines.py — SistemaEnot.correr completa `traza`.

# eval/juez.py
class SalidaJuez(BaseModel): justificacion: str; puntaje: Literal[1, 2, 3, 4, 5]   # justificación antes del puntaje
class Juicio(BaseModel):
    consulta_id: str; sistema: str; estado: Literal["ok", "error"]
    puntaje: int | None; justificacion: str = ""; error: str | None = None
    tokens_in: int | None; tokens_out: int | None; latencia_s: float
class Juicios(BaseModel):
    reporte: str; split: str; fecha: str; proveedor: str | None; modelo: str | None; juicios: list[Juicio]
def juzgable(consulta: Consulta, salida: SalidaSistema) -> bool
    # consulta factible, con `preferencias` en la etiqueta, y el sistema entregó un itinerario con paradas
def contexto_juez(consulta: Consulta, itinerario: Itinerario, corpus) -> str
    # pedido del turista + preferencias etiquetadas + por parada: nombre, zona, comuna, experiencia,
    # descripción breve y vinos DEL CORPUS (mismo dato para todos los sistemas); sin precios, horarios ni
    # nombre del sistema (juez ciego). Bodega fuera del corpus: "fuera del corpus, sin datos".
def juzgar(cliente, consulta, salida, corpus) -> Juicio   # error del cliente → estado "error", puntaje None
def juzgar_reporte(cliente, reporte: Reporte, consultas, corpus, origen: str) -> Juicios   # solo juzgables
# python -m eval.juez REPORTE [--set data/eval] [--fichas …] → reports/juez_<split>_<fecha>.json (no pisa)

# eval/calibrar.py
UMBRAL_SPEARMAN = 0.6; UMBRAL_KAPPA = 0.6; MINIMO_CASOS = 30; PUNTAJES = (1, 2, 3, 4, 5)
COLUMNAS_PLANILLA = ("consulta_id", "sistema", "pedido", "itinerario", "puntaje_humano", "comentario")
def rangos(valores) -> list[float]                        # rango promedio en los empates
def spearman(x, y) -> float | None                        # None con < 3 pares o una serie constante
def kappa(a, b, ponderacion: Literal["ninguna", "cuadratica"] = "ninguna") -> float | None
    # Cohen sobre las categorías 1–5 fijas; None si el acuerdo esperado es 1
class Anotacion(BaseModel): consulta_id: str; sistema: str; puntaje_humano: int | None   # 1–5 o vacío
def armar_planilla(reporte, consultas, corpus, n=30, semilla=2026) -> list[dict]
    # solo split dev (ValueError con test); casos juzgables repartidos por sistema; sin el puntaje del juez
def escribir_planilla(filas, ruta) -> Path               # FileExistsError si ya existe (no pisa a Flora)
def leer_anotaciones(ruta) -> list[Anotacion]
class Calibracion(BaseModel):
    pares: int; sin_anotar: int; sin_juicio: int
    spearman: float | None; kappa: float | None; kappa_cuadratico: float | None
    apto: bool; motivo: str
def calibrar(anotaciones, juicios: Juicios) -> Calibracion
    # apto = pares ≥ MINIMO_CASOS y spearman ≥ UMBRAL_SPEARMAN y kappa_cuadratico ≥ UMBRAL_KAPPA
# python -m eval.calibrar planilla REPORTE [--n 30] [--destino data/eval/anotacion_humana.csv]
# python -m eval.calibrar calibrar JUICIOS [--anotaciones …] → reports/calibracion_<fecha>.json

# eval/reporte.py
class Precio(BaseModel): entrada_usd_por_millon: float ≥ 0; salida_usd_por_millon: float ≥ 0
def cargar_precios(ruta) -> dict[str, Precio]            # {"<modelo>": {...}}; los pone Flora
def media(valores) -> float | None; def percentil_95(valores) -> float | None   # p95 por rango más cercano
class CostoConsulta(BaseModel):
    consulta_id: str; llamadas: int | None; fallidas: int | None; sin_tokens: int
    tokens_in: int | None; tokens_out: int | None; usd: float | None
def costo_consulta(salida, eventos: list[EventoTraza] | None, con_llm: bool, modelo: str | None,
                   precios: dict[str, Precio]) -> CostoConsulta
    # sin LLM (B1) → 0; con traza → suma por evento con el precio de event.modelo; sin traza (B0) → tokens de la
    # salida. Tokens desconocidos o modelo sin precio → usd None (nunca 0 inventado)
class FilaSistema(BaseModel): sistema; hard_pass_rate; tasa_alucinacion; cobertura_corpus; gini;
    infactibles_detectados; preferencia_media; preferencia_media_hard_pass; juicios; juicios_error;
    tokens_medios; usd_medio; usd_p95; consultas_con_costo; consultas; latencia_media; latencia_p95;
    intentos_medios; llamadas; llamadas_fallidas; llamadas_sin_tokens; salidas_error
def filas_sistemas(reporte, juicios=None, precios=None, leer_eventos=…) -> list[FilaSistema]
def render_markdown(reporte, filas, origen, calibracion=None, precios_cargados=False) -> str
# python -m eval.reporte REPORTE [--juicios] [--calibracion] [--precios] [--salida reports/resultados.md]
```

## Archivos a tocar
- Crear: `eval/juez.py`, `eval/prompts/juez.md`, `eval/calibrar.py`, `eval/reporte.py`, `tests/test_juez.py`,
  `tests/test_calibrar.py`, `tests/test_reporte.py`, `tests/test_tokens_fallidas.py`, ADR-0018.
- Modificar: `corpus/llm.py` (error con tokens), `enot/trazas.py` (validador), `enot/nodos.py` (registrar tokens
  del error), `eval/metricas.py` (campo `traza`), `eval/baselines.py` (completar `traza`), `Makefile`
  (`juez`, `calibrar`, `planilla`, `reporte`), `README.md`, `CHANGELOG.md`, `BACKLOG.md`.

## Fuera de alcance
- No se escribe `data/eval/` ni `data/eval/anotacion_humana.csv` con puntajes: el set lo congela Flora y la
  anotación es suya.
- No se cargan precios de modelos en el repo: cambian y no los puedo verificar sin red. El reporte los recibe con
  `--precios`; sin precios, la columna USD dice "s/d" y los tokens igual se reportan.
- B0 no pasa a tener traza (sus tokens vienen de la salida). Costo fijo de extracción (`costos_extraccion.csv`) y
  comparación de modelos (PRD 9): no.
- No se integra el juez a `make eval`: es un paso aparte que se corre sobre un reporte ya escrito.

## Supuestos
- **Juzgable = factible + preferencias etiquetadas + itinerario entregado.** H2 es sobre preferencias blandas; sin
  preferencias (58 de 100 consultas) la rúbrica no tiene qué medir. Se juzgan todos los sistemas, incluso sin hard
  pass, y el reporte da la media total y la media sobre las que pasaron el hard pass ("a igual factibilidad").
- **El juez ve lo mismo para todos los sistemas**: los datos de la bodega salen del corpus, no del texto que
  escribió cada sistema, y no ve el nombre del sistema. Así mide la elección de bodegas, no la prosa.
- **Rúbrica sin "confianza"** (lineamientos C.8): solo justificación y puntaje 1–5, justificación primero.
- **Kappa:** se reportan el de Cohen sin ponderar y el ponderado cuadrático. Para el umbral se usa el cuadrático,
  porque la escala es ordinal (un 4 contra un 5 no es lo mismo que un 1 contra un 5).
- **Umbrales 0,6** (acuerdo "sustancial" de Landis y Koch) y **30 casos** (PRD). Son constantes: si Flora quiere
  otros, se cambian en un lugar. Si no es apto, el reporte lo dice y marca el preference score como evidencia débil
  (ADR-0007).
- **La planilla sale solo de dev**: calibrar el juez mirando test sería ajustar la vara al examen.
- **p95 por rango más cercano** (`ceil(0,95·n)`-ésimo valor ordenado): con 40 consultas devuelve un valor observado,
  sin interpolar.
- **Latencia** = `latencia_s` de cada salida (medida de punta a punta por consulta), sin las salidas `error`, que no
  la miden. **Costo** por consulta (un turno), sobre las que tienen todos los tokens conocidos; las demás se cuentan.
- **`resultados.md` se reescribe**: es derivado y lleva en el encabezado de qué reportes sale; los reportes de
  entrada (`eval_*.json`, `juez_*.json`) nunca se pisan.

## Cómo se verifica
Tests nuevos (archivos nuevos; ningún test existente se modifica):

`tests/test_tokens_fallidas.py`
- `test_cliente_llm_error_trae_tokens_consumidos`: dos salidas inválidas de 10+5 tokens → `ErrorSalidaInvalida` con
  20/10 tokens e `intentos == 2`, y sigue siendo `RuntimeError`.
- `test_nodo_registra_tokens_del_error`: un cliente que lanza `ErrorSalidaInvalida(…, 30, 7, 2)` → el evento de error
  tiene 30/7/2; con un error sin tokens siguen en `None`.
- `test_evento_ok_exige_tokens`: `estado="ok"` con `tokens_in=None` o `tokens_out=None` → `ValidationError`; error sin
  tokens sigue valiendo.
- `test_sistema_enot_guarda_la_ruta_de_la_traza`: la salida de Enot trae `traza` y ese archivo tiene los eventos.

`tests/test_juez.py`
- `test_juzgable`: falso con infactible, sin preferencias, tipo no itinerario o itinerario sin paradas; verdadero con
  las tres condiciones.
- `test_contexto_juez_usa_datos_del_corpus_y_es_ciego`: incluye pedido, preferencias, nombre, zona y vinos del corpus;
  no incluye precios, horarios, el id del sistema ni el texto del sistema; bodega fuera del corpus marcada.
- `test_juzgar_devuelve_puntaje_y_tokens`: ClienteFalso → puntaje 4, tokens 100/50, estado ok; el prompt de sistema
  es la rúbrica.
- `test_juzgar_error_del_cliente`: el cliente falla → estado error, puntaje None, sin lanzar.
- `test_salida_juez_rechaza_fuera_de_rango`: 0 y 6 → `ValidationError`.
- `test_juzgar_reporte_solo_juzgables`: de un reporte con 4 salidas, juzga solo las 2 juzgables, con el modelo y el
  origen.
- `test_cli_juez_escribe_sin_pisar`: dos corridas → dos archivos `juez_dev_*`.

`tests/test_calibrar.py`
- `test_rangos_con_empates`: `[10, 20, 20, 30]` → `[1, 2.5, 2.5, 4]`.
- `test_spearman_valores_conocidos`: perfecto (1), inverso (−1), sin empates (0,8) y con empates
  (8,5/√95), calculados a mano, y coincide con `scipy.stats.spearmanr` si está instalado.
- `test_spearman_indefinido`: menos de 3 pares o una serie constante → `None`; largos distintos → `ValueError`.
- `test_kappa_valores_conocidos`: acuerdo perfecto 1; caso de libro calculado a mano (sin ponderar y cuadrático);
  el cuadrático castiga más un desacuerdo 1–5 que uno 4–5; coincide con sklearn si está.
- `test_kappa_indefinido_y_fuera_de_escala`: todos iguales en ambos → `None`; un 0 o un 6 → `ValueError`.
- `test_leer_anotaciones`: vacío → `None`; "4" → 4; "7" o "a" → `ValueError`.
- `test_calibrar_cuenta_pares_y_faltantes`: une por (consulta, sistema); cuenta sin anotar, sin juicio y juicios en
  error como sin juicio.
- `test_calibrar_apto_y_no_apto`: 30 pares concordantes → apto; 29 → no apto por cantidad; 30 discordantes → no apto
  por acuerdo, con el motivo.
- `test_armar_planilla_estratificada_y_ciega`: n casos, todos juzgables, repartidos por sistema, sin columna del juez,
  reproducible con la semilla; con split test → `ValueError`.
- `test_escribir_planilla_no_pisa`: la segunda escritura → `FileExistsError` y el archivo queda igual.

`tests/test_reporte.py`
- `test_percentil_95_y_media`: valores conocidos (1..20 → 19; 1..40 → 38; un valor; vacío → `None`).
- `test_costo_sin_llm_es_cero`: B1 → 0 tokens y 0 USD.
- `test_costo_desde_la_traza`: dos eventos ok → suma de tokens y USD con la fórmula del PRD; usa el modelo de cada
  evento.
- `test_costo_con_llamada_fallida_sin_tokens`: un evento de error con tokens `None` → `fallidas == 1`,
  `sin_tokens == 1`, usd `None` y tokens conocidos sumados aparte; con tokens en el error, se suman y hay USD.
- `test_costo_sin_precio_del_modelo`: modelo fuera de la tabla → usd `None`, tokens sí.
- `test_costo_b0_desde_la_salida`: sin traza, tokens de la salida y precio del modelo del reporte; salida error →
  sin costo.
- `test_filas_sistemas`: métricas, preference score (total y con hard pass), media y p95 de USD y latencia (sin
  las salidas error), intentos medios y conteos de llamadas fallidas, sobre un reporte armado a mano.
- `test_render_markdown`: tabla con una fila por sistema, "s/d" donde falta el dato, aviso si el juez no está
  calibrado o no es apto, y el origen.
- `test_cli_reporte_escribe_resultados`: escribe el Markdown en la ruta pedida desde un reporte, juicios y precios
  en disco.

Sensores: `make check`; `make mutation MODULO=eval/metricas.py` (lógica crítica tocada) y, aunque no sea
obligatorio, `eval/calibrar.py` y `eval/reporte.py` (son las métricas nuevas). `make registro`, `make tests-modificados`.

Qué tiene que revisar Flora a mano: la rúbrica (`eval/prompts/juez.md`), los umbrales de calibración, y cargar los
precios de su modelo en un JSON para `--precios`.
