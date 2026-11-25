# Spec 007: baselines, métricas y `make eval`

**Ítem del backlog:** 007 · **Rama:** `noche/2026-11-25-007` · **ADRs relacionados:** ADR-0007 (evaluación),
ADR-0003 (workflow y B2), ADR-0005 (tools), ADR-0012 (advertencias no cuentan), ADR-0015 (zona desconocida),
ADR-0016 (set e infactibles no representables), ADR-0017 (nuevo)

## Qué se va a hacer
La mitad de "correr" del benchmark (PRD 6, área de profundización 3): los tres baselines (B0 LLM zero-shot sin
corpus, B1 filtros + greedy por cercanía sin LLM, B2 Enot sin el loop de verificación), Enot completo, las métricas
verificables en código (hard pass rate, tasa de alucinación, cobertura del corpus + Gini, infactibles bien
detectados) y `make eval SPLIT=dev|test`, que deja `reports/eval_<split>_<fecha>.json` con la configuración que lo
produjo. El juez LLM y el costo en USD son del ítem 008.

## Interfaz
```python
# eval/metricas.py — funciones puras: ninguna llama a un LLM ni lee archivos
TipoSalida = Literal["itinerario", "infactible", "zona_desconocida", "sin_candidatas", "pregunta",
                     "tope_tokens", "error"]          # los tipos de `enot.flujo.Respuesta`
DETECTAN_INFACTIBLE = {"infactible", "sin_candidatas"}
REPRESENTABLES = {"zona_fuera_de_borgona"}            # motivos que Enot puede detectar hoy (ADR-0016)
TOLERANCIA_PRECIO_EUR = 0.01

class PrecioAfirmado(BaseModel): bodega_id: str; experiencia: str | None; precio_por_persona_eur: float
class SalidaSistema(BaseModel):
    consulta_id: str; sistema: str; tipo: TipoSalida
    itinerario: Itinerario | None = None              # lo que el sistema le entrega al turista
    precios_afirmados: list[PrecioAfirmado] = []      # precios que el sistema dice (B0); Enot y B1 no inventan
    texto: str = ""; intentos: int = 0
    tokens_in: int | None = None; tokens_out: int | None = None; latencia_s: float = 0.0

def faltantes_estructurales(itinerario, perfil) -> list[str]
    # cantidad de días == perfil.cantidad_dias; día k es dias_del_viaje(perfil)[k-1]; cada día con ≥ 1 parada
def afirmaciones(salida, corpus) -> tuple[int, int]   # (afirmaciones, inventadas)
    # una por parada (bodega), una por experiencia nombrada y una por precio afirmado
class EvaluacionConsulta(BaseModel):
    consulta_id; escenario; infactible: bool; motivo_infactible; tipo: TipoSalida
    faltantes: list[str]; violaciones: list[TipoViolacion]; afirmaciones: int; inventadas: int
    hard_pass: bool | None              # None en consultas infactibles
    infactible_detectado: bool | None   # None en consultas factibles
def evaluar_consulta(consulta: Consulta, salida: SalidaSistema | None, corpus) -> EvaluacionConsulta
    # se verifica contra la ETIQUETA (consulta.restricciones), no contra el perfil que extrajo el sistema;
    # sin salida = tipo "error"
def detecta_infactible(tipo, motivo) -> bool
    # tipo ∈ DETECTAN_INFACTIBLE, o tipo == "zona_desconocida" y motivo == "zona_fuera_de_borgona"
def hard_pass_rate(evals) -> float | None              # sobre consultas factibles
def tasa_alucinacion(evals) -> float | None            # Σ inventadas / Σ afirmaciones
def recomendaciones_por_bodega(salidas, corpus) -> dict[str, int]   # todas las bodegas del corpus, con ceros
def gini(valores) -> float | None                      # None si la suma es 0
def cobertura_corpus(salidas, corpus) -> float
def infactibles_detectados(evals) -> float | None
class Metricas(BaseModel):
    consultas; factibles; infactibles; hard_pass_rate; hard_pass_por_escenario: dict[str, float]
    tasa_alucinacion; afirmaciones; inventadas; cobertura_corpus; gini
    infactibles_detectados; infactibles_detectados_por_motivo: dict[str, float]
    infactibles_detectados_representables: float | None; tipos: dict[str, int]
def resumir(consultas, salidas, corpus) -> tuple[Metricas, list[EvaluacionConsulta]]
    # ValueError si hay dos salidas para la misma consulta o una salida de una consulta que no está

# eval/baselines.py
class Sistema(Protocol): nombre: str; def correr(self, consulta: Consulta) -> SalidaSistema
def resolver_bodega(nombre: str, corpus) -> str | None   # nombre normalizado == nombre del corpus normalizado
class BaselineB0:   # (cliente, corpus): una llamada con el texto del turista, sin corpus ni tools
class BaselineB1:   # (corpus, duracion_defecto=60, max_paradas_dia=4): usa consulta.restricciones (formulario)
class SistemaEnot:  # (flujo, nombre, carpeta_trazas, entregar_sin_verificar=False): un turno de `Flujo`
def crear_enot(cliente, corpus, indice, carpeta_trazas) -> SistemaEnot   # max_intentos = MAX_INTENTOS
def crear_b2(cliente, corpus, indice, carpeta_trazas) -> SistemaEnot     # max_intentos = 1, entrega sin verificar

# eval/correr.py
class SetInexistente(Exception)
def cargar_consultas(split: str, carpeta: Path | None = None) -> list[Consulta]
class Reporte(BaseModel): split; fecha; configuracion: dict; metricas: dict[str, Metricas];
                          evaluaciones: dict[str, list[EvaluacionConsulta]]; salidas: dict[str, list[SalidaSistema]]
def evaluar(sistemas, consultas, corpus, split, configuracion=None) -> Reporte
    # una excepción de un sistema en una consulta → SalidaSistema(tipo="error"); la corrida sigue
def escribir_reporte(reporte, carpeta=None) -> Path   # reports/eval_<split>_<AAAA-MM-DD-HHMMSS>.json, nunca pisa
def main(argv=None, crear_cliente=None, crear_embedder=None) -> int
    # python -m eval.correr --split dev|test [--sistemas B0,B1,B2,enot] [--limite N] [--fichas] [--set]
```
`make eval SPLIT=dev SISTEMAS=B0,B1,B2,enot` llama a `python -m eval.correr`.

### B0 (zero-shot)
Prompt de sistema fijo en `eval/baselines.py` ("armá un itinerario de bodegas en Borgoña para este pedido; si es
imposible, decilo"), el texto del turista como mensaje de usuario y salida estructurada `SalidaB0`:
`es_posible`, `motivo`, `dias[{dia_semana, paradas[{bodega, hora_inicio, duracion_min, experiencia,
precio_por_persona_eur}]}]`. Cada nombre se resuelve contra el corpus con `resolver_bodega` (sin acentos, sin
mayúsculas, sin puntuación, sin lo que va entre corchetes); si no está, `bodega_id = "b0:<nombre>"`, que el
verificador marca como `bodega_inexistente`. `es_posible = False` → tipo `infactible`.

### B1 (determinístico)
Filtros duros de `enot.retrieval.filtrar` sobre el perfil etiquetado (B1 es un formulario: el turista carga sus
restricciones a mano). Por día, desde `hora_inicio_jornada`: elige la bodega no usada más cercana a la última
parada (la primera del viaje, por `id`), con la primera variante que el **verificador** acepta sobre el itinerario
parcial. Variantes, en orden: sin experiencia y después cada experiencia publicada; empieza apenas termina el
traslado o, si la bodega abre más tarde ese día, a la hora de apertura. Duración: la de la experiencia o 60 min.
Hasta `max_paradas_dia`. Sin candidatas → `sin_candidatas`; un día sin paradas → `infactible`.

### Enot y B2
Un turno de `Flujo.turno` con una `Sesion` nueva por consulta y el texto del turista. Tokens: suma de los eventos
de la traza de esa sesión. Enot entrega el itinerario solo si `tipo == "itinerario"`. B2 es la ablación de
ADR-0003: `max_intentos = 1` **y** entrega la primera propuesta aunque el verificador la rechace (sin loop no hay
guardia); su `tipo` pasa de `infactible` a `itinerario` cuando hay propuesta.

## Archivos a tocar
- Crear: `eval/metricas.py`, `eval/baselines.py`, `eval/correr.py`, `tests/test_eval.py`, `tests/test_baselines.py`,
  `tests/test_correr_eval.py`, `docs/adr/0017-…`.
- Modificar: `Makefile` (objetivo `eval`), `README.md` (sección evaluación), `eval/generador.py` (solo el docstring
  de `escribir_set`: el movimiento final no es atómico entre los cuatro elementos; menor de la revisión 006 ronda 2).

## Fuera de alcance
- Juez LLM, preference score, Spearman/kappa, costo en USD y p95 de latencia (ítem 008). El reporte guarda tokens y
  latencia por salida para que 008 los use.
- Escribir `data/eval/` (decisión pendiente de Flora) y tocar `data/eval/test/`.
- Agregar `bodegas_por_dia`/`zonas_mismo_dia` a `PerfilViaje` (opción (a) de la decisión pendiente).
- La métrica de advertencias promedio por itinerario (decisión pendiente de Flora del 24/11).
- Recall@10/nDCG@10 (ya en `eval/retrieval.py`, ítem 003).

## Supuestos
1. **Hard pass = todo o nada**: itinerario entregado, estructura completa, cero violaciones del verificador contra la
   etiqueta y cero afirmaciones inventadas (el "chequeo extra" de ADR-0007). La estructura se agrega porque el
   verificador no la mira: un itinerario vacío no tiene violaciones y no puede contar como acierto.
2. **Se verifica contra la etiqueta**, no contra el perfil que extrajo el relevamiento: un error de relevamiento es
   un error del sistema.
3. El hard pass rate se calcula **solo sobre consultas factibles**; las infactibles se miden con "infactibles bien
   detectados". Una consulta sin salida cuenta como falla.
4. **Infactibles bien detectados, independiente de la decisión pendiente**: cuenta si el sistema responde
   `infactible` o `sin_candidatas`, o `zona_desconocida` cuando el motivo es zona fuera de Borgoña (la opción (b)
   que el feedback recomienda "mientras tanto"). El reporte trae la tasa sobre todos los infactibles, el desglose
   por motivo y la tasa sobre los representables. Si Flora elige (a), el código de métricas no cambia: los
   infactibles pasan a salir como `infactible`. Si elige (c), se lee la tasa de representables. El criterio con
   juez ("explica por qué no entra") de (b) no se implementa.
5. **Alucinación**: se cuentan las afirmaciones verificables de un itinerario (bodega, experiencia nombrada, precio
   afirmado). Un precio es inventado si no coincide (±0,01 EUR) con el de la experiencia en EUR del corpus (sin
   experiencia: la más barata en EUR, como la tool de costos). Los horarios inventados aparecen como `cerrada` en el
   hard pass: el itinerario propone horas de visita, no afirma horarios de apertura.
6. **Cobertura y Gini** sobre los itinerarios entregados (tipo `itinerario`), contando solo bodegas del corpus; el
   Gini incluye las bodegas nunca recomendadas (ceros). Sin recomendaciones, Gini = None.
7. **B1 recibe el perfil etiquetado** (es un formulario): no paga errores de relevamiento. Se declara como ventaja de
   B1 en el ADR.
8. **B1 usa el verificador como oráculo** en el greedy (una sola fuente de verdad, ADR-0005): no reimplementa reglas.
9. **B2 entrega sin verificar** (ver arriba). Con el flujo tal cual, `max_intentos = 1` todavía rechaza la propuesta
   inválida y B2 parecería "honesto"; eso no aísla el aporte del verificador.
10. Un sistema que lanza una excepción en una consulta deja una salida `error` y la corrida sigue.
11. Nombre del reporte con fecha y hora (`eval_dev_2026-11-29-153000.json`) para no pisar corridas del mismo día.
12. `make eval` solo crea el cliente LLM y el embedder si algún sistema pedido los necesita: `SISTEMAS=B1` corre sin
    claves.

## Cómo se verifica
### `tests/test_eval.py` (métricas, casos armados a mano sobre la fixture SINTÉTICA)
- `test_faltantes_estructurales_itinerario_completo` — un itinerario de 2 días bien armado no tiene faltantes.
- `test_faltantes_estructurales_cantidad_de_dias` — 1 día cuando el perfil pide 2 → un faltante que lo dice.
- `test_faltantes_estructurales_dia_de_semana` — el día 1 es sábado y el viaje empieza el viernes → faltante.
- `test_faltantes_estructurales_dia_sin_paradas` — el día 2 vacío → faltante (y el día 1 no).
- `test_afirmaciones_correctas` — bodega + experiencia + precio del corpus: 3 afirmaciones, 0 inventadas.
- `test_afirmaciones_bodega_inexistente` — parada a una bodega que no está, con experiencia y precio: 3 y 3.
- `test_afirmaciones_experiencia_inexistente` — experiencia no publicada: cuenta 1 inventada de 2.
- `test_afirmaciones_sin_itinerario` — una salida sin itinerario ni precios no afirma nada.
- `test_afirmaciones_precio` — parametrizado: precio exacto, sin experiencia = la más barata en EUR, borde de la
  tolerancia (20,009 ok; 20,02 inventado), precio de una experiencia sin precio en EUR (inventado).
- `test_hard_pass_itinerario_valido` — itinerario factible y completo → `hard_pass` True.
- `test_hard_pass_falla` — parametrizado: una violación (cerrada), estructura incompleta, precio inventado, tipo
  `infactible` en una consulta factible, sin salida.
- `test_hard_pass_tipo_no_itinerario_con_itinerario_valido_falla` — cuenta lo que se entrega: un `infactible` no
  entrega itinerario aunque traiga uno.
- `test_hard_pass_usa_la_etiqueta` — el mismo itinerario pasa con 2 personas y falla si la etiqueta dice 15
  (capacidad 12).
- `test_hard_pass_ignora_advertencias` — un itinerario con advertencia de accesibilidad sin confirmar pasa (ADR-0012).
- `test_hard_pass_rate_solo_factibles` — 3 factibles (2 pasan) + 1 infactible → 2/3; sin factibles → None.
- `test_tasa_alucinacion_agrega` — dos salidas con 5 y 2 afirmaciones, 1 y 1 inventadas → 2/7; sin afirmaciones →
  None.
- `test_gini_casos_a_mano` — [1,1,1,1] → 0; [0,0,0,4] → 0,75; [1,2,3] → 2/9 y en otro orden igual; [] y [0,0] → None.
- `test_cobertura_y_recomendaciones` — dos salidas, una no-itinerario y una bodega inventada: cuentas por bodega con
  ceros, cobertura 2/7 y el Gini correspondiente.
- `test_detecta_infactible` — parametrizado por tipo y motivo (incluye `zona_desconocida` con y sin zona fuera).
- `test_constantes_de_infactibles` — los tipos que detectan y los motivos representables, explícitos.
- `test_infactibles_detectados_y_desglose` — tasa total, por motivo y sobre representables, calculadas a mano;
  `infactible_detectado` es None en factibles y `hard_pass` es None en infactibles.
- `test_representables_none_sin_infactibles_representables`.
- `test_resumir_por_escenario_y_tipos` — hard pass por escenario y conteo de tipos de salida.
- `test_resumir_consulta_sin_salida_es_error` — falta la salida de una consulta → `error`, cuenta como falla.
- `test_resumir_rechaza_salidas_duplicadas_o_ajenas` — ValueError.
- `test_afirmaciones_solo_cuentan_lo_entregado` y `test_recomendaciones_siguen_despues_de_una_salida_sin_itinerario`
  (sobrevivientes de mutation).

### `tests/test_baselines.py`
- `test_resolver_bodega` — acentos, mayúsculas, puntuación y corchetes; nombre desconocido → None.
- `test_b0_salida` — con `ClienteFalso`: bodegas resueltas e inventadas (`b0:`), precios afirmados, tokens, días
  numerados; el prompt lleva el texto del turista y ningún id del corpus.
- `test_b0_imposible_es_infactible`.
- `test_b0_inventado_no_pasa` — integración con `evaluar_consulta`: inventadas > 0 y hard pass False.
- `test_b1_itinerario_factible_y_por_cercania` — Côte de Beaune un viernes: pasa el verificador y la estructura, y la
  segunda parada es la más cercana a la primera.
- `test_b1_respeta_presupuesto` — con 20 EUR solo entra lo que cuesta ≤ 20 y el verificador no marca presupuesto.
- `test_b1_prueba_las_experiencias_si_sin_experiencia_no_sirve` — variante sintética que publica solo francés:
  en inglés elige la experiencia que lo ofrece, con su duración.
- `test_b1_espera_la_apertura` — jornada desde las 09:00 y la bodega abre a las 10:00 → primera parada a las 10:00.
- `test_b1_espera_la_segunda_franja` — si la mañana no alcanza, la visita va a la franja de la tarde (14:00).
- `test_b1_sin_candidatas` — zona fuera de Borgoña → `sin_candidatas` (y cuenta como infactible detectado).
- `test_b1_dia_sin_paradas_es_infactible` — domingo + lunes en Chablis (cerrada los lunes).
- `test_b1_no_repite_y_respeta_maximo` — 2 días con `max_paradas_dia=1`: una por día, distintas.
- `test_b1_duracion_por_defecto` — bodega sin experiencias: dura `duracion_defecto`.
- `test_enot_entrega_itinerario_valido` — `Flujo` con guion: tipo itinerario, tokens desde la traza.
- `test_enot_infactible_no_entrega_itinerario` — propuestas siempre inválidas → itinerario None.
- `test_b2_entrega_la_primera_propuesta` — con una propuesta inválida y después una válida: B2 entrega la inválida
  (hard pass False) y Enot la válida (hard pass True).
- `test_sistema_enot_sin_entregar_sin_verificar_no_cambia_el_tipo`.
- `test_cada_consulta_tiene_su_propia_sesion` — una sesión y una traza por consulta; los tokens no se acumulan.
- `test_latencia_medida` — con un reloj falso que avanza 1,5 s por lectura: B0 y B1 (en sus tres salidas) miden
  exactamente 1,5 s y Enot 10,5 s (sus nodos leen el mismo reloj).
- `test_tokens_desconocidos_si_una_llamada_fallo` — si un evento de la traza tiene tokens `None` (llamada fallida),
  los tokens de la salida quedan en `None`: no se inventa un 0 (mismo criterio que ADR-0014).
- `test_b1_sobre_la_muestra_real` (revisión ronda 1) — `skip` sin `data/datatourisme/muestra.csv`: B1 sobre las 100
  consultas del generador y la muestra real; invariantes (no inventa, detecta zona fuera) y, si la huella de la muestra
  coincide, las cifras de ADR-0017 (hard pass 79/80, falla solo q047; cobertura 0,41; infactibles 0,3).

### `tests/test_correr_eval.py`
- `test_cargar_consultas_sin_set` — `SetInexistente` con un mensaje que nombra el generador.
- `test_cargar_consultas` — lee 60 de dev y 40 de test de un set generado.
- `test_evaluar_sigue_si_un_sistema_falla` — un sistema que lanza deja salidas `error` y las métricas se calculan.
- `test_main_b1_sin_llm` — set escrito con `escribir_set` en una carpeta temporal y corpus sintético: corre B1 con
  `--limite 5`, no crea cliente LLM, y el JSON trae métricas, 5 salidas y la configuración (versión del generador,
  split, sistemas).
- `test_main_todos_los_sistemas` — fábricas falsas de cliente y embedder: el reporte trae B0, B1, B2 y enot.
- `test_main_sin_set_sale_con_1`.
- `test_main_sistema_desconocido_sale_con_1` y `test_main_sin_corpus_sale_con_1`.
- `test_escribir_reporte_no_pisa` — dos reportes en el mismo segundo → dos archivos.

### Sensores
- `make check` en verde. `make mutation MODULO=eval/metricas.py` ≥ 80% (obligatorio por AGENTS.md).
- Flora a mano: correr `make eval SPLIT=dev SISTEMAS=B1` una vez que exista `data/eval/` y mirar el JSON.
