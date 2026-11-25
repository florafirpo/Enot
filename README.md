# Enot · agente de rutas de enoturismo en Borgoña

TP final de IA Agéntica (Maestría en Explotación de Datos, UBA). Enot arma itinerarios de 1 a 3 días por
bodegas de Borgoña a partir de las preferencias del turista, con un workflow LLM + tools determinísticas +
verificador de restricciones.

| Documento | Para qué |
|---|---|
| `docs/PRD.md` | Qué hace el sistema, hipótesis, métricas, riesgos |
| `docs/adr/` | Por qué está armado así (una decisión por archivo) |
| `BACKLOG.md` | Plan de trabajo hasta el 3/12 |
| `CHANGELOG.md` | Qué cambió y cuándo |
| `AGENTS.md` | Reglas para los agentes que trabajan en el repo |

## Estructura

```
corpus/   pipeline de datos: DATAtourisme → fichas de bodegas (este README, abajo)
enot/     el agente: modelos, tools, verificador, retrieval, nodos, flujo (se construye según BACKLOG)
eval/     generador del set, baselines, métricas, juez (ADR-0007)
tests/    tests offline (sin red ni claves)
docs/     PRD, ADRs, specs por tarea, reportes nocturnos
```

## Cómo se desarrolla

Spec → tests → código, una tarea por PR (ADR-0008). Un agente toma cada noche el próximo ítem de
`BACKLOG.md`; los hooks de `.claude/` bloquean lo prohibido y `make check` (ruff + pytest) y
`make mutation` miden la calidad. Todo pasa por revisión antes de llegar a `main`.

```bash
make install   # dependencias
make check     # lint + tests (tiene que pasar siempre)
make mutation MODULO=enot/verificador.py   # ¿los tests detectarían un error?
```

## Set de evaluación

`python -m eval.generador [--parafrasear]` escribe en `data/eval/` las particiones `dev/` (60 consultas) y `test/`
(40), la planilla `revision_manual.csv` (20% para revisar a mano) y `generacion.json` (ADR-0007, ADR-0016). Se corre
**una sola vez**: si `dev/` o `test/` ya existen, no escribe nada, y la partición de test no se toca más.
`--parafrasear` reescribe cada consulta con el LLM de `.env` y conserva las etiquetas. La tasa de error del generador
sale de la columna `correcta` de la planilla (`eval.generador.tasa_error_revision`).

## Correr la evaluación

`make eval SPLIT=dev` (o `python -m eval.correr --split dev [--sistemas B0,B1,B2,enot] [--limite N]`) corre los
cuatro sistemas sobre el split y escribe `reports/eval_<split>_<fecha>.json` con la configuración, las métricas por
sistema, la evaluación de cada consulta y lo que entregó cada sistema (spec 007, ADR-0017):

- **B0**: el pedido directo al LLM, sin corpus. **B1**: formulario + filtros + greedy por cercanía, sin LLM.
  **B2**: Enot con un intento y sin verificador de guardia. **enot**: el flujo completo.
- Métricas: hard pass rate (todo o nada, contra la etiqueta), tasa de alucinación, cobertura del corpus + Gini e
  infactibles bien detectados (total, por motivo y sobre los que el sistema puede representar).
- Necesita `data/eval/` (generador) y `data/fichas/fichas.jsonl`. B0, B2 y enot usan el LLM y los embeddings de
  `.env`; `make eval SISTEMAS=B1` corre sin claves.

---

# Pipeline del corpus

Pipeline para armar las fichas de bodegas que usa el agente Enot (IA Agéntica,
Maestría UBA). La región del MVP es **Borgoña (Bourgogne, Francia)** y la fuente
principal es **DATAtourisme**, la base nacional francesa de información turística
en datos abiertos (Licence Ouverte 2.0). Cada ficha se puede rastrear hasta su
fuente y todo se vuelve a correr desde cero con los comandos de abajo.

```
datatourisme  →  (crawl + clean, opcional)  →  extract  →  eda / muestra / precision
     (1)                    (2-3)                 (4)                (5)
```

| Paso | Comando | Lee | Escribe |
|---|---|---|---|
| 1. Semilla y texto | `python -m corpus datatourisme <csv>` | CSV regional de DATAtourisme | `data/seed/bodegas.csv`, `data/base/`, `data/clean/` |
| 2. Webs (opcional) | `python -m corpus crawl` | `bodegas.csv` | `data/raw/<id>/<fecha>/` |
| 3. Limpieza (opcional) | `python -m corpus clean` | `data/base/` + `data/raw/` | `data/clean/` (ficha oficial + web) |
| 4. Extracción | `python -m corpus extract` | `data/clean/` | `data/fichas/fichas.jsonl`, `costos_extraccion.csv` |
| 5a. EDA | `python -m corpus eda` | todo lo anterior | `reports/eda.md`, `reports/completitud.csv` |
| 5b. Muestra | `python -m corpus muestra --n 30` | `fichas.jsonl` | `data/validacion/muestra_<fecha>.csv` |
| 5c. Precisión | `python -m corpus precision <muestra revisada>` | la muestra | `reports/precision_extraccion.md` |

## Instalación (VS Code)

1. Abrí esta carpeta en VS Code (`File > Open Folder`).
2. `Ctrl+Shift+P` → **Python: Create Environment** → Venv → marcá `requirements.txt`.
   O en la terminal:
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate     Mac/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copiá `.env.example` como `.env` y completá la clave del LLM (Google Places ya no hace falta).
4. Corré cada paso desde la terminal o desde **Run and Debug** (`Ctrl+Shift+D`).

## Paso 1: bajar los datos de DATAtourisme

1. Entrá a la página del dataset en data.gouv.fr:
   https://www.data.gouv.fr/fr/datasets/datatourisme-2/
2. En la lista de recursos (apretá "Charger plus" para ver todos) bajá el CSV de la región
   **Bourgogne-Franche-Comté**. Los archivos se llaman `datatourisme-reg-<código>.csv`;
   el de esta región debería ser `datatourisme-reg-bfc.csv`.
3. Guardalo en `data/datatourisme/`.
4. Primero mirá qué columnas detecta el script:
   ```bash
   python -m corpus datatourisme data/datatourisme/datatourisme-reg-bfc.csv --columnas
   ```
   Si alguna columna sale `None`, fijala en `COLUMNAS_DATATOURISME` (`corpus/config.py`).
5. Generá la semilla y el texto:
   ```bash
   python -m corpus datatourisme data/datatourisme/datatourisme-reg-bfc.csv
   ```

**Qué filtra:** puntos de interés de tipo `core:Cellar` ("cave ou caveau") y, entre los otros
proveedores de degustación (productores, cooperativas, négociants), los que mencionan vino en el
nombre o la descripción. Por defecto se queda con los departamentos de Borgoña: 21 Côte-d'Or,
71 Saône-et-Loire, 89 Yonne y 58 Nièvre (`--departamentos 21 71 89 58 39` suma Jura).

**Subzonas:** asigna Côte de Nuits, Côte de Beaune, Hautes-Côtes, Chablis y Grand Auxerrois,
Côte Chalonnaise o Mâconnais según la comuna. Si la comuna no está en la lista, usa una
aproximación por latitud (está en `corpus/datatourisme.py` y conviene revisarla en el EDA).

Después abrí `data/seed/bodegas.csv`: podés marcar `abre_turismo = no` para descartar
alguna, o corregir `zona`. Si volvés a correr el paso 1, esas ediciones se conservan.

## Pasos siguientes (prueba chica primero)

```bash
python -m corpus extract --dry-run       # cuánto texto se manda, sin gastar
python -m corpus extract --limite 10     # 10 fichas para mirar la calidad
python -m corpus eda
```

Mirá algunas fichas de `fichas.jsonl` contra el texto de `data/clean/`. Si algo está mal,
ajustá el prompt (`SISTEMA` en `corpus/extract.py`) o el esquema (`corpus/schema.py`) y
re-extraé con `--force`. Con eso bien: `python -m corpus extract` para todas.

**Opcional, para enriquecer:** el CSV de DATAtourisme es "simplificado" y muchas veces los
horarios y precios vienen solo en la descripción. Si en el EDA la completitud de precio u
horario queda baja, bajá las webs de las bodegas que tienen una:
```bash
python -m corpus crawl            # baja las webs (respeta robots.txt)
python -m corpus clean            # combina ficha oficial + web
python -m corpus extract --force  # re-extrae con más texto
```

## Decisiones de diseño (para la defensa)

- **Datos abiertos y oficiales.** DATAtourisme lo alimentan las oficinas de turismo francesas;
  licencia abierta, actualización diaria. Coordenadas incluidas, que se usan para las distancias.
- **El LLM extrae, no inventa.** El CSV trae descripciones en texto libre (en francés); el LLM las
  convierte en una ficha estructurada. Si un dato no está, va `null`, y cada dato importante trae
  su cita textual y fuente.
- **Verificación de citas en código.** `extract` chequea que cada cita aparezca en el texto
  fuente (`evidencias_verificadas` en `_meta`): primera medida de alucinación. La precisión real
  sale de la muestra revisada a mano (pasos 5b y 5c).
- **Extracción sin framework.** `corpus/llm.py` usa `json_schema` (OpenAI y compatibles) o una
  tool forzada (Anthropic), valida con Pydantic y reintenta una vez devolviéndole el error al modelo.
- **Costos medidos.** Tokens, latencia e intentos por bodega en `costos_extraccion.csv`. Para el
  costo en USD, completá `PRECIOS_USD_POR_MTOK` en `corpus/config.py`.
- **Comparación de modelos.** Corré `extract --force` con otro `LLM_MODEL`/`LLM_PROVIDER` (por
  ejemplo un modelo local con Ollama) y compará completitud, precisión, costo y latencia.
- **Camino alternativo para Mendoza.** `python -m corpus seed` (Google Places) + `crawl` + `clean`
  sigue funcionando si en algún momento se vuelve a una región sin datos abiertos.

## Problemas comunes

| Síntoma | Qué hacer |
|---|---|
| `No detecté las columnas ['nombre', 'tipos']` | Corré con `--columnas`, mirá los encabezados y fijalos en `COLUMNAS_DATATOURISME` |
| Muy pocas bodegas | Revisá que el CSV sea el de Bourgogne-Franche-Comté y los departamentos elegidos |
| Se cuelan productores que no son de vino (quesos, cerveza) | Marcalos `abre_turismo = no` en la semilla, o ajustá `RE_VINO` en `corpus/datatourisme.py` |
| Subzona mal asignada | Corregila en `bodegas.csv` (se conserva) o sumá la comuna a `COMUNAS_ZONA` |
| El LLM no devuelve JSON válido (modelos locales) | Probá un modelo más grande o bajá `MAX_CHARS_POR_BODEGA` |
| `crawl` trae casi nada de una web | `pip install playwright`, `playwright install chromium` y `crawl --ids <id> --force --playwright` |
