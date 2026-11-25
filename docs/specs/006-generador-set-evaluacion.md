# Spec 006: generador del set de evaluación

**Ítem del backlog:** 006 · **Rama:** `noche/2026-11-25-006` · **ADRs relacionados:** ADR-0007 (decide el set),
ADR-0005 (tiempos de traslado), ADR-0006 (`ClienteLLM`), ADR-0012 (idioma/accesibilidad), ADR-0015 (zona
desconocida), ADR-0016 (nuevo)

## Qué se va a hacer
El benchmark propio del PRD (sección 6, área de profundización 3): un generador versionado que arma 100 consultas
sintéticas de turistas desde plantillas, cada una con sus restricciones etiquetadas en JSON, estratificadas por
escenario, con semilla fija, y las parte en 60 dev / 40 test. Incluye pedidos infactibles etiquetados y una muestra
del 20% para que Flora revise a mano (con eso se mide la tasa de error del generador: consigna "si los datos son
sintéticos, el generador es parte del sistema y se evalúa", lineamientos F).

## Interfaz
```python
# eval/generador.py
Escenario = Literal["dias", "transporte", "presupuesto", "grupo", "idioma", "accesibilidad", "infactible"]
MotivoInfactible = Literal["demasiadas_bodegas", "zonas_lejanas", "zona_fuera_de_borgona"]
CUOTAS: dict[Escenario, int]          # dias 15, transporte 15, presupuesto 15, grupo 15, idioma 10,
                                      # accesibilidad 10, infactible 20  (suma 100)
FRACCION_DEV = 0.6                    # por escenario: 15 → 9/6, 10 → 6/4, 20 → 12/8
FRACCION_REVISION = 0.2               # por escenario: 15 → 3, 10 → 2, 20 → 4
SEMILLA = 2026
VISITA_MINIMA_MIN = 30                # cota inferior de una visita, para el certificado de infactibilidad

class Consulta(BaseModel):
    id: str                           # "q001" … "q100"
    escenario: Escenario
    plantilla: str                    # id de la plantilla que la generó (para medir error por plantilla)
    texto: str                        # lo que escribe el turista (un solo mensaje, con los 4 datos obligatorios)
    restricciones: PerfilViaje        # la etiqueta: el perfil que el relevamiento debería extraer
    bodegas_por_dia: int | None       # si el turista pidió una cantidad de bodegas por día
    zonas_mismo_dia: list[str]        # zonas que pidió visitar todas en el mismo día
    infactible: bool
    motivo_infactible: MotivoInfactible | None   # obligatorio si infactible, prohibido si no
    texto_plantilla: str | None       # el texto antes de la paráfrasis, si se parafraseó
    anclas: list[str]                 # valores con que se llenó la plantilla ("jueves", "tres días", "25"…)
    parafrasis: Literal["no", "aceptada", "rechazada"]

def certificado_infactible(c: Consulta) -> str | None
    # Explica por qué el pedido es imposible para CUALQUIER corpus, o None si no puede probarlo:
    # - bodegas_por_dia × VISITA_MINIMA_MIN > minutos de la jornada (sin contar traslados);
    # - zonas_mismo_dia: el traslado mínimo entre las comunas de referencia de dos zonas (haversine × FACTOR_RUTA ÷
    #   VELOCIDAD_KMH del transporte, las mismas constantes de `enot/tools/distancias.py`) supera la jornada;
    # - alguna zona pedida no coincide con ninguna subzona de Borgoña (`corpus.datatourisme.COMUNAS_ZONA`, mismo
    #   criterio por palabras que `enot.retrieval._coincide_zona`).
def generar(semilla: int = SEMILLA, parafraseador: Callable[[str], str] | None = None) -> list[Consulta]
def particionar(consultas, semilla=SEMILLA) -> tuple[list[Consulta], list[Consulta]]   # (dev, test), estratificado
def muestra_revision(dev, test, semilla=SEMILLA) -> list[tuple[str, Consulta]]       # [("dev"|"test", c)], 20%
def conserva_anclas(parafrasis: str, anclas: list[str]) -> bool   # cada ancla aparece como palabras enteras
def parafraseador_llm(cliente) -> Callable[[str], str]   # usa cliente.estructurado (ADR-0006)
def escribir_set(destino: Path, semilla=SEMILLA, parafraseador=None) -> ResumenSet
    # Escribe destino/dev/consultas.jsonl, destino/test/consultas.jsonl, destino/revision_manual.csv y
    # destino/generacion.json. Si dev/ o test/ ya existen, no escribe nada y lanza SetExistente.
class ResumenRevision(BaseModel): revisadas: int; con_error: int; tasa_error: float | None; por_escenario: dict
def tasa_error_revision(ruta_csv: Path) -> ResumenRevision   # lee la columna `correcta` que completa Flora
def main(argv=None, cliente=None) -> int   # python -m eval.generador [--destino data/eval] [--semilla] [--parafrasear]
```

### Escenarios y plantillas
Todas las consultas traen en el texto los cuatro campos obligatorios del relevamiento (`CAMPOS_OBLIGATORIOS`:
días, día de inicio, transporte, personas), para que un solo mensaje alcance y la evaluación no dependa de
repreguntas. Cada escenario pone el foco en una dimensión (PRD 6) con varias plantillas de redacción:

| Escenario | Qué varía | Etiqueta |
|---|---|---|
| dias | 1–3 días, día de inicio, a veces la franja horaria ("de 14 a 18:30") | `cantidad_dias`, `dia_inicio`, `hora_*_jornada` |
| transporte | auto, traslado, bici, a pie (bici y a pie con una sola zona) | `transporte` |
| presupuesto | tope por persona en EUR | `presupuesto_max_por_persona` |
| grupo | 6 a 15 personas | `personas` |
| idioma | un idioma de visita (en, de, es, it, pt, y fr como caso trivial) | `idiomas` |
| accesibilidad | silla de ruedas / movilidad reducida, a veces con grupo e idioma (caso del PRD) | `movilidad_reducida` |
| infactible | ver abajo | `infactible`, `motivo_infactible` |

Opcionales en todos los escenarios factibles: una zona de Borgoña (etiqueta con el nombre canónico de la subzona)
y una preferencia blanda ("algo familiar", "vinos biodinámicos"…) en `preferencias`, para el juez del ítem 008.

Infactibles (20, repartidos entre los tres motivos):
- `demasiadas_bodegas`: 1 día, 7 a 10 bodegas en una franja de 3 horas (7 × 30 = 210 > 180 min).
- `zonas_lejanas`: 1 día, a pie o en bici, una bodega en cada una de dos zonas lejanas (solo se aceptan pares
  cuyo certificado se cumple).
- `zona_fuera_de_borgona`: pide Champagne, Jura, Beaujolais, Alsacia o Burdeos (PRD 8, fuera de alcance).

### Paráfrasis (opcional, con LLM)
Si se pasa un `parafraseador`, cada texto se reescribe; la paráfrasis se acepta solo si conserva todas las
**anclas** de la consulta (números, días, zonas, idioma, transporte: los valores que se usaron para llenar la
plantilla), comparando sin mayúsculas ni tildes, y si no repite otra consulta. Si no, queda el texto de la
plantilla y se marca `parafrasis="rechazada"`. Sin parafraseador, la salida es determinística.

## Archivos a tocar
- Crear: `eval/generador.py`, `tests/test_generador.py`, `docs/adr/0016-…`.
- Modificar: `BACKLOG.md`, `CHANGELOG.md`, `docs/feedback-flora.md`, `README.md` (comando nuevo).

## Fuera de alcance
- **Escribir `data/eval/dev/` y `data/eval/test/` en esta corrida.** Crear test es irreversible (hook, ADR-0007)
  y la decisión de parafrasear (que necesita la clave de Flora) tiene que tomarse antes. El generador queda listo y
  la decisión va a `docs/feedback-flora.md`.
- Relevantes etiquetados por consulta para el retrieval (subset de 30 del PRD): dependen del corpus real.
- Baselines, métricas y `make eval` (ítem 007); juez (ítem 008).
- No se toca `enot/` (el generador solo importa constantes y modelos).

## Supuestos
- **Cuotas 15/15/15/15/10/10/20.** Múltiplos de 5 para que 60/40 y 20% salgan exactos por escenario. Infactibles
  con 20 (8 en test) para que "infactibles bien detectados" no se mida sobre 4 casos; idioma y accesibilidad con 10
  porque con DATAtourisme casi siempre terminan en advertencia (ADR-0012) y discriminan menos.
- **Infactible = imposible para cualquier corpus**, demostrado por código (`certificado_infactible`), no por
  opinión del generador. Por eso el caso del PRD "8 bodegas entre Chablis y el Mâconnais" se reformula: con auto y
  9 horas no es demostrablemente imposible.
- **`VISITA_MINIMA_MIN = 30`**: una cata de menos de media hora no es una visita; es una cota conservadora.
- **Comunas de referencia por zona** con coordenadas aproximadas de su centro (geografía pública, no bodegas). El
  certificado de `zonas_lejanas` usa el par de comunas **más cercano** entre las dos zonas, así es conservador.
- **Etiqueta de zona = nombre canónico de la subzona** del corpus ("Chablis y Grand Auxerrois"), aunque el texto
  diga "Chablis": el filtro de retrieval coincide por palabras, así que la etiqueta canónica y el nombre corto
  encuentran las mismas bodegas.
- **Idiomas como código de dos letras**, igual que el prompt del relevamiento.
- **Todo o nada al escribir:** si existe dev/ o test/, no se escribe ninguna partición (regenerar solo dev con
  otra versión del generador podría filtrar consultas de test a dev).

## Cómo se verifica
Tests en `tests/test_generador.py` (offline, sin LLM real; el parafraseador es una función falsa):
- `test_misma_semilla_mismo_set`: dos `generar(7)` dan listas iguales (textos y etiquetas).
- `test_otra_semilla_otro_set`: `generar(7)` y `generar(8)` difieren en los textos.
- `test_cien_consultas_con_cuotas_por_escenario`: 100 consultas y el conteo por escenario es exactamente `CUOTAS`.
- `test_ninguna_consulta_repetida`: los 100 textos normalizados (sin mayúsculas, tildes ni espacios extra) son
  distintos; también para otras 5 semillas.
- `test_ids_unicos_y_correlativos`: ids `q001`…`q100`, sin repetidos.
- `test_texto_contiene_los_datos_obligatorios`: en cada consulta el texto menciona el día de inicio, la cantidad de
  días, un indicio del transporte y la cantidad de personas de su etiqueta (falla si la etiqueta y el texto se
  desacoplan).
- `test_etiqueta_coincide_con_el_texto_por_escenario`: presupuesto → el número del tope aparece en el texto;
  idioma → el nombre del idioma; accesibilidad → `movilidad_reducida` y la mención; zona → el nombre corto.
- `test_escenarios_varian_su_dimension`: en cada escenario la dimensión foco toma al menos 3 valores distintos
  (o los 2 posibles); grupo siempre ≥ 6 personas; fuera de grupo y accesibilidad ≤ 4 (el caso del PRD de
  accesibilidad es un grupo de 6).
- `test_bici_y_a_pie_factibles_con_una_sola_zona`.
- `test_infactibles_tienen_certificado`: toda consulta infactible tiene `certificado_infactible` no vacío.
- `test_factibles_no_tienen_certificado`: ninguna factible lo tiene (el generador no etiqueta de más ni de menos).
- `test_infactibles_cubren_los_tres_motivos`: los tres motivos aparecen, al menos 6 cada uno.
- `test_certificado_demasiadas_bodegas_borde`: 6 bodegas en 180 min → None (180 = 180); 7 → texto.
- `test_certificado_zonas_lejanas`: Chablis + Mâconnais a pie → texto; en auto → None; Côte de Nuits + Côte de
  Beaune en bici → None; una sola zona → None.
- `test_certificado_zona_fuera`: "Champagne" → texto; "Chablis" y "Côte de Beaune" → None.
- `test_consulta_valida_motivo_con_infactible`: `infactible=True` sin motivo y `False` con motivo → ValidationError.
- `test_particion_60_40_estratificada`: dev 60, test 40, por escenario 3/5 exacto, sin ids compartidos, y la unión
  es el set.
- `test_particion_determinista`: misma semilla → mismas particiones.
- `test_muestra_revision_20_por_ciento_estratificada`: 20 consultas, por escenario el 20% exacto, de las dos
  particiones, sin repetidos.
- `test_escribir_set_crea_archivos`: escribe los 4 archivos en un `tmp_path`; los JSONL vuelven a cargar como
  `Consulta` y coinciden con `particionar(generar())`; el CSV tiene 20 filas y las columnas para Flora vacías;
  `generacion.json` trae semilla, conteos y versión.
- `test_escribir_set_no_pisa_test`: con `test/` ya existente (con un archivo), lanza `SetExistente`, no crea dev/
  y el archivo de test queda intacto byte a byte. Ídem con `dev/` existente.
- `test_tasa_error_revision`: CSV armado a mano con 5 filas (2 "no", 2 "sí", 1 vacía) → revisadas 4, con_error 2,
  tasa 0.5, por escenario correcto; sin revisadas → `tasa_error` None; un valor que no es sí/no/vacío ("tal vez")
  → ValueError (un error de tipeo no se cuenta como revisada).
- `test_conserva_anclas`: acepta una paráfrasis con las anclas (con otra capitalización y sin tildes) y rechaza
  la que pierde un número o cambia el día.
- `test_parafrasis_aceptada_y_rechazada`: un parafraseador falso que conserva anclas → `aceptada` y
  `texto_plantilla` guardado; uno que cambia los números → `rechazada` y el texto queda el de la plantilla; las
  etiquetas no cambian en ningún caso.
- `test_parafrasis_duplicada_se_rechaza`: un parafraseador que devuelve siempre lo mismo → solo la primera se acepta.
- `test_parafraseador_llm_usa_el_cliente`: con `ClienteFalso`, devuelve el texto de la salida estructurada y el
  prompt de usuario contiene el texto original.
- `test_main_escribe_y_devuelve_0` / `test_main_con_set_existente_devuelve_1`.
- `test_main_parafrasear_sin_cliente_usa_cliente_llm`: `--parafrasear` arma el cliente con la fábrica inyectada.

Sensores: `make check`. Mutation sobre `eval/generador.py` (no es obligatorio por AGENTS.md, pero etiqueta la
métrica principal): objetivo ≥ 80%.

Qué tendría que revisar Flora a mano: el texto de las plantillas (es lo que va a leer la cátedra en el set), las
cuotas, y la decisión de generar y congelar test (`docs/feedback-flora.md`).
