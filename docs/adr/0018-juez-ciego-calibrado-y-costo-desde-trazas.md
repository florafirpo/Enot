# ADR-0018: Juez ciego sobre datos del corpus, calibración con kappa cuadrático y costo desde las trazas sin ceros inventados

**Estado:** Propuesto
**Fecha:** 2026-11-25
**Decide:** Flora

## Contexto
ADR-0007 fija que las preferencias blandas (H2) las mide un juez LLM con rúbrica 1–5 calibrado contra 30 casos
anotados a mano (Spearman y kappa), y el PRD (sección 9) pide costo en tokens y USD y latencia media y p95 "desde las
trazas". Quedaban sin decidir varias cosas que cambian el número:
- **Qué ve el juez.** Si lee la prosa de cada sistema, premia al que escribe lindo (B1 no escribe nada) y puede
  reconocer el sistema. Si lee datos que el sistema inventó (B0), juzga sobre ficción.
- **Qué se juzga.** 58 de las 100 consultas no tienen preferencias blandas: ahí la rúbrica no tiene qué medir.
- **Qué kappa.** La escala 1–5 es ordinal; el kappa de Cohen sin ponderar trata igual un 4 contra un 5 que un 1
  contra un 5.
- **Cuándo el juez "sirve".** ADR-0007 dice "si la correlación es baja, se reporta", sin umbral.
- **Llamadas fallidas.** La traza las registraba con tokens `None` (revisión 004) y `ClienteLLM` no informaba lo que
  gastó antes de fallar; sumarlas como 0 abarata el sistema justo en los casos difíciles.
- **Precios.** Cambian y no se pueden verificar sin red; ponerlos en el código sería un dato inventado.

## Decisión
1. **Juez ciego y con el mismo contexto para todos.** Recibe el pedido, las preferencias etiquetadas y, por parada,
   nombre, zona, comuna, experiencia, descripción y vinos **tomados del corpus**. Sin precios, horarios, nombre del
   sistema ni texto del sistema. Una bodega fuera del corpus aparece como "fuera del corpus, sin datos". Salida
   `justificacion` y después `puntaje` (`Literal[1..5]`), sin "confianza" (lineamientos C.8).
2. **Juzgable = consulta factible con `preferencias` + itinerario entregado con paradas**, de cualquier sistema. El
   reporte da la media total y la media sobre las consultas con hard pass ("a igual factibilidad", H2).
3. **Calibración:** Spearman (rangos promedio en empates) y kappa de Cohen sin ponderar y **ponderado cuadrático**
   sobre las categorías 1–5 fijas. **Apto** si hay al menos 30 pares, Spearman ≥ 0,6 y kappa cuadrático ≥ 0,6
   (acuerdo "sustancial" de Landis y Koch). Si no es apto, el reporte lo dice y marca el preference score como
   evidencia débil.
4. **La planilla de anotación sale solo de dev**, a ciegas (sin el puntaje del juez ni el sistema en el texto), con el
   mismo texto que ve el juez, repartida por sistema con semilla fija, y nunca pisa un CSV existente.
5. **Costo por consulta desde la traza de esa consulta** (la salida guarda la ruta), con el precio del modelo de cada
   llamada: C = Σ t_in·p_in + t_out·p_out (PRD 9). `ClienteLLM` lanza `ErrorSalidaInvalida` con los tokens exactos
   que gastó al agotar los intentos de validación, y el nodo los registra. Un error del proveedor sigue con `None`.
   Una consulta con alguna llamada sin tokens, o con un modelo sin precio, queda **sin costo** y se cuenta aparte; media
   y p95 se calculan sobre las que tienen costo completo. `EventoTraza` con `estado == "ok"` exige tokens.
6. **Precios fuera del repo**: el reporte los recibe con `--precios`; sin precios, USD dice "s/d" y los tokens igual
   se reportan. **p95 por rango más cercano** (un valor observado, sin interpolar). La latencia es la de punta a
   punta por consulta, sin las salidas `error`.

## Opciones consideradas
| Opción | A favor | En contra |
|---|---|---|
| Juez ciego sobre datos del corpus (elegida) | Mide la elección de bodegas, igual para los cuatro sistemas | No ve cómo cada sistema le explica el porqué al turista |
| Juez sobre la respuesta completa de cada sistema | Mide lo que lee el turista | Premia la prosa; B1 no escribe; el juez puede reconocer el sistema |
| Juzgar todas las consultas factibles | Más casos | Sin preferencias la rúbrica no discrimina: infla todo a 3 |
| Kappa sin ponderar como criterio | Es el "kappa" literal del PRD | Escala ordinal: castiga igual un error de 1 punto que uno de 4 |
| Spearman solo | Simple | Un juez que ordena bien pero puntúa 2 puntos de más pasa (lo detecta el kappa) |
| Calibrar con casos de test | Más representativo del resultado final | Ajustar la vara mirando el examen (lineamientos D.1, D.6) |
| Fallidas como 0 tokens | Siempre hay un número | Abarata el sistema justo cuando reintenta o falla; dato inventado |
| Precios en el código | El reporte sale con USD sin pasos extra | Precios sin verificar y que cambian: dato inventado (AGENTS.md) |
| p95 interpolado (numpy por defecto) | Estándar en librerías | Con 40 consultas inventa un valor entre dos observados |

## Consecuencias
- Más fácil: comparar el ajuste a preferencias de B1 (sin LLM) contra Enot con el mismo juez; defender que el juez no
  sabe qué sistema juzga; reportar costos honestos aunque haya llamadas fallidas.
- **El juez sólo ve lo que dicen las fichas.** Con fichas pobres (la muestra real casi no tiene descripción ni vinos)
  muchos puntajes van a ser 3 ("las fichas dicen poco"): el preference score depende de la completitud del corpus,
  igual que el hard pass (ADR-0017). Hay que reportarlo junto.
- **B0** con bodegas fuera del corpus suma poco ajuste por construcción: es coherente (no hay datos que respalden la
  elección) y conviene decirlo al presentar H2/H3.
- Los umbrales (0,6 y 30) son constantes en `eval/calibrar.py`; si Flora los cambia, lo anota acá.
- El costo de B0 sale de la salida (no tiene traza): no cuenta llamadas fallidas, solo salidas `error`.
- Revisar cuando Flora anote los 30 casos (30/11): si el juez no es apto, ajustar la rúbrica **en dev** y volver a
  calibrar con casos nuevos, no con los mismos.

## Cómo se verifica
- `tests/test_juez.py`: juzgable, contexto ciego y con datos del corpus, rango 1–5, errores con y sin tokens, CLI
  que no pisa.
- `tests/test_calibrar.py`: rangos, Spearman y kappa con valores calculados a mano y contra scipy y scikit-learn,
  casos indefinidos, umbrales (apto, pocos pares, discordante, sesgado), planilla estratificada, ciega, solo dev y que
  no pisa.
- `tests/test_reporte.py`: costo sin LLM, desde la traza, con fallidas sin tokens, sin precio, de B0; media y p95; las
  filas y el Markdown exactos de un reporte armado a mano.
- `tests/test_tokens_fallidas.py`: `ErrorSalidaInvalida` con tokens, el nodo los registra, `EventoTraza` ok exige
  tokens, la salida de Enot trae su traza.
- Mutation: `eval/metricas.py`, `eval/calibrar.py`, `eval/reporte.py`, `eval/juez.py` (cifras en el reporte de la
  corrida).
