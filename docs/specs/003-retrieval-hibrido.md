# Spec 003: retrieval híbrido y su evaluación

**Ítem del backlog:** 003 · **Rama:** `noche/2026-11-24-003` · **ADRs relacionados:** ADR-0004 (decide la
arquitectura), ADR-0006, ADR-0009, ADR-0012, ADR-0013 (nuevo)

## Qué se va a hacer
La capacidad 2 del PRD ("recuperación de candidatas"): dado el perfil del turista (y opcionalmente un texto de
consulta), devolver las bodegas candidatas que el planificador va a usar. Filtros duros por metadatos en código,
y sobre lo que queda BM25 y embeddings combinados con Reciprocal Rank Fusion (c = 60), como decide ADR-0004.
Además, la evaluación del retrieval por separado (lineamientos D.5): Recall@k y nDCG@k contra consultas con
bodegas relevantes etiquetadas.

## Interfaz
```python
# enot/retrieval.py
def tokenizar(texto: str) -> list[str]                 # minúsculas, sin tildes, [a-z0-9]+
def texto_bodega(b: Bodega) -> str                     # lo que se indexa (BM25 y embeddings)
class BM25:                                            # Okapi BM25 propio (k1=1.5, b=0.75)
    def __init__(self, documentos: list[list[str]], k1=1.5, b=0.75)
    def idf(self, termino: str) -> float               # ln((N - n + 0.5) / (n + 0.5) + 1)
    def puntajes(self, consulta: list[str]) -> list[float]
def rrf(rankings: Sequence[Sequence[str]], c: int = 60, top: int | None = None) -> list[tuple[str, float]]
def dias_del_viaje(perfil: PerfilViaje) -> list[str]
def motivo_exclusion(b: Bodega, perfil: PerfilViaje) -> str | None   # None = pasa los filtros
def filtrar(bodegas: Iterable[Bodega], perfil: PerfilViaje | None) -> list[Bodega]
def consulta_desde_perfil(perfil: PerfilViaje) -> str
class Embedder(Protocol): nombre: str; def embeber(self, textos: list[str]) -> np.ndarray
class EmbedderOpenAI:      # API de embeddings compatible con OpenAI; modelo en .env (EMBEDDINGS_MODEL)
class EmbedderConCache:    # envuelve otro embedder; cachea por hash del texto en data/indice/
class Candidata(BaseModel): bodega_id: str; score: float; puesto_bm25: int | None; puesto_embeddings: int | None
class Indice:
    def __init__(self, bodegas: Iterable[Bodega], embedder: Embedder)
    def buscar(self, perfil: PerfilViaje | None, k: int = 10, consulta: str | None = None,
               top_por_metodo: int | None = None) -> list[Candidata]

# eval/retrieval.py
class ConsultaEtiquetada(BaseModel): id: str; consulta: str; perfil: PerfilViaje | None; relevantes: dict[str, int]
def recall_at_k(recuperados: list[str], relevantes: dict[str, int], k: int) -> float
def dcg_at_k(...) -> float;  def ndcg_at_k(...) -> float       # ganancia lineal: grado / log2(puesto + 1)
def cargar_consultas(ruta: Path) -> list[ConsultaEtiquetada]
def evaluar(buscar: Callable[[ConsultaEtiquetada, int], list[str]], consultas, k: int = 10) -> ResultadoEval
def main(argv=None, embedder=None) -> int    # python -m eval.retrieval <consultas.jsonl> [--k 10]
```

### Filtros duros (código, una regla por restricción del perfil)
Mismo criterio que el verificador (ADR-0009, ADR-0012): un límite de la bodega solo excluye con evidencia; una
necesidad del turista solo excluye con evidencia en contra. Así el filtro nunca descarta algo que el verificador
aceptaría.
| Regla | Excluye | No excluye |
|---|---|---|
| `bodegas_evitar` | id o nombre coincide (sin mayúsculas) | — |
| `zonas_preferidas` (si hay) | zona distinta (sin mayúsculas ni tildes) | zona en la lista |
| capacidad | `personas > capacidad_max_grupo` | igual, o capacidad sin dato |
| accesibilidad (si `movilidad_reducida`) | `False` | `True` o sin dato |
| idioma (si pide alguno y no es francés) | publica idiomas (bodega o alguna experiencia) y ninguno pedido está | sin lista publicada |
| días de apertura | publica horarios y no abre ninguno de los días del viaje | abre al menos uno, o sin horario |
| presupuesto | todas sus experiencias tienen precio en EUR y la más barata supera el máximo por persona | alguna sin precio (o en otra moneda), sin experiencias, igual al máximo |

### Combinación
BM25 rankea solo las candidatas con puntaje > 0 (si no comparte ninguna palabra, BM25 no la vota); los embeddings
rankean todas las candidatas por coseno. `rrf` suma `1 / (c + puesto)` por cada ranking en el que el documento
aparece dentro de `top`. Empates: por id (determinístico).

## Archivos a tocar
- Crear: `enot/retrieval.py`, `eval/retrieval.py`, `tests/test_retrieval.py`, `tests/test_eval_retrieval.py`,
  `tests/dobles.py` (`EmbedderFalso`; archivo nuevo para no tocar `conftest.py`, que es un test existente),
  ADR-0013, reporte en `docs/noches/`.
- Modificar: `enot/modelos.py` (`Bodega` suma `descripcion_breve` y `vinos_o_varietales_destacados`, que ya vienen
  en la ficha y hacen falta para indexar), `BACKLOG.md`, `CHANGELOG.md`.

## Fuera de alcance
- Re-ranking con LLM (ADR-0004 lo deja como mejora si Recall@10 no alcanza).
- El set etiquetado de 30 consultas: lo arma Flora o el ítem 006; acá solo el formato y el evaluador.
- Usar el retrieval desde el flujo (ítem 005) o desde los nodos (004).
- Un conversor semilla → `Bodega` en código de producción: el corpus del agente sigue siendo `fichas.jsonl`.

## Supuestos
- **BM25 propio (≈30 líneas)** en vez de `rank_bm25`: sin dependencia nueva, explicable en la defensa, y se puede
  verificar con valores calculados a mano. IDF con el `+1` dentro del logaritmo (variante de Lucene) para que
  nunca sea negativo con corpus chicos.
- **`zonas_preferidas` es filtro duro**: ADR-0004 nombra la subzona entre los filtros duros. Si deja cero
  candidatas, el flujo (005) decide qué hacer.
- **Embeddings reales por la API compatible con OpenAI** (`openai` ya está en requirements; con `OPENAI_BASE_URL`
  sirve también Ollama). Modelo en `.env` (`EMBEDDINGS_MODEL`, por defecto `text-embedding-3-small`, multilingüe).
  No pasa por `ClienteLLM`, que es para salidas estructuradas de chat; queda anotado en ADR-0013.
- **Caché por hash del texto** (sha256) y por modelo: si cambia una ficha se recalcula solo esa.
- **Ganancia lineal en nDCG** (grado / log2(puesto+1)): con relevancia binaria es igual a la exponencial y es la
  que se explica en clase.
- **Datos reales:** un test corre el paso `datatourisme` sobre `data/datatourisme/muestra.csv` (200 bodegas reales)
  en una carpeta temporal y arma las `Bodega` con la descripción de DATAtourisme, para probar el tokenizador y los
  filtros con texto francés y zonas reales. No se copian datos a fixtures. Si el archivo no está, el test se saltea.

## Cómo se verifica
`tests/test_retrieval.py` (bodegas `[SINTÉTICA]`, `EmbedderFalso` determinístico):
- `test_tokenizar_saca_tildes_y_mayusculas` — "Côte de BEAUNE, Mâcon!" → `["cote", "de", "beaune", "macon"]`.
- `test_bm25_idf_a_mano`, `test_bm25_puntaje_a_mano` — corpus de 3 documentos con valores calculados a mano.
- `test_bm25_satura_y_normaliza_por_largo` — más frecuencia suma menos que proporcional; mismo tf en documento más
  largo puntúa menos; tope (k1+1)·idf.
- `test_bm25_termino_desconocido_da_cero`, `test_bm25_corpus_vacio`.
- `test_rrf_ejemplo_de_clase` — rankings A,B,C y C,B,A con c=60 y top=2 → B primero (2/62), A y C con 1/61.
- `test_rrf_sin_top_usa_todo`, `test_rrf_c_cambia_los_puntajes`, `test_rrf_desempate_por_id`, `test_rrf_vacio`.
- `test_dias_del_viaje` — 3 días desde sábado → sab, dom, lun.
- Filtros, cada uno con el caso que excluye y el que no: `test_filtro_bodegas_evitar`, `test_filtro_zona`,
  `test_filtro_capacidad`, `test_filtro_accesibilidad`, `test_filtro_idioma`, `test_filtro_dias`,
  `test_filtro_presupuesto`, `test_sin_perfil_no_filtra`, `test_motivo_exclusion_explica`.
- `test_filtros_coinciden_con_el_verificador` — una bodega que pasa los filtros no da violación de capacidad,
  accesibilidad, idioma ni presupuesto en una visita a la experiencia más barata; una excluida sí.
- `test_texto_bodega_incluye_lo_indexable`, `test_consulta_desde_perfil`.
- `test_buscar_combina_bm25_y_embeddings` — una bodega que solo coincide por palabra y otra que solo coincide por
  sinónimo aparecen; la que coincide en ambos sale primera.
- `test_bm25_solo_vota_documentos_con_coincidencias` — `puesto_bm25` es `None` si no comparte palabras.
- `test_buscar_respeta_filtros`, `test_buscar_k`, `test_buscar_sin_candidatas`, `test_buscar_sin_consulta_usa_el_perfil`,
  `test_buscar_top_por_metodo`.
- Caché: `test_cache_no_recalcula`, `test_cache_texto_nuevo`, `test_cache_persiste_entre_instancias`,
  `test_cache_separa_por_modelo`.
- `test_embedder_openai_pide_el_modelo_y_respeta_el_orden` (cliente falso), `test_embedder_openai_lista_vacia`.
- `test_con_la_muestra_real_de_datatourisme` — "Chablis" trae primero bodegas de la zona Chablis; con
  `zonas_preferidas=["Mâconnais"]` todo lo devuelto es de esa zona.

`tests/test_eval_retrieval.py`:
- `test_recall_a_mano`, `test_ndcg_a_mano` (relevantes {b:2, c:1, d:3}, recuperados [a, b, c], k=3 → 0,3700),
  `test_ndcg_perfecto_es_uno`, `test_ndcg_sin_aciertos_es_cero`, `test_metricas_respetan_k`,
  `test_duplicados_cuentan_una_vez`, `test_sin_relevantes_es_error`, `test_consulta_acepta_lista_de_relevantes`,
  `test_cargar_consultas`, `test_evaluar_promedia`, `test_main_escribe_el_reporte`.

Sensores: `make check`; `make mutation MODULO=enot/retrieval.py` y `MODULO=eval/retrieval.py` (≥ 80%, no son
obligatorios por AGENTS.md pero es lógica que decide qué ve el planificador); `make registro`.

Flora a mano: correr `python -m eval.retrieval` con su clave cuando exista el set etiquetado; mirar si
`zonas_preferidas` como filtro duro le parece bien.
