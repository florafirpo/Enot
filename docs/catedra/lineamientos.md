# Lineamientos de la cátedra (rúbrica del compañero)

Destilado de la consigna y de las clases que están en esta carpeta. Cada punto dice de dónde sale, para
que el compañero lo pueda citar en una revisión y Flora en la defensa. Si un punto choca con `AGENTS.md`,
manda `AGENTS.md` (son reglas de Flora para este repo).

Abreviaturas: **C** = `consigna-tp.md` · **08/20**, **10/01**, **10/08**, **11/05**, **11/12** = archivos
`clase-2026-MM-DD-*.md`.

## A. Lo que se evalúa (C, "Criterios de evaluación")

| Peso | Criterio | Qué mira el compañero en cada entrega |
|---|---|---|
| 15% | Problema, utilidad e hipótesis | ¿La tarea acerca a medir H1–H3 del PRD? ¿Cambia el alcance sin decirlo? |
| 25% | Diseño del sistema y uso de LLMs | Contexto, contratos (Pydantic), manejo de errores, decisiones justificadas en ADR. |
| 25% | Evaluación, evidencia y costos | Baseline simple medido, partición fija dev/test, comparación honesta, análisis de fallas, costo y latencia. **Nada fabricado para la demo.** |
| 10% | Ingeniería | El sistema y la evaluación corren siguiendo el README; git prolijo. |
| 25% | Exposición y defensa | Flora tiene que poder explicar todo y razonar alternativas: cada PR trae "Para la defensa". |

Regla madre (C): **lo que se declara en el PRD, el informe o la exposición tiene que ser verificable en el
repo.** Una afirmación en un PR sin un test, un número o un archivo que la respalde es un hallazgo.

Áreas de profundización elegidas en el PRD (C pide ≥2, "sustantivas, no decorativas"): retrieval evaluado
por separado de la generación; tools con contratos y errores; orquestación con loop de verificación y
reintento contra un criterio automático; evaluación con juez calibrado contra humanos.

## B. Verificar (10/01 §6–7, 10/08 §2)

1. **Sin verificación no hay confianza.** La spec define "Cómo se verifica" antes del código (SDD).
2. **Tests significativos:** un test vale si fallaría ante un error real, no si "la función funciona por
   funcionar". Prueba concreta: ¿pasaría con una implementación vacía, constante o que ignora un parámetro?
3. **Coverage no alcanza; mutation testing sí mide** si los tests detectan errores. Obligatorio en
   `enot/verificador.py`, `enot/tools/`, `eval/metricas.py` (AGENTS.md). Sobrevivientes: test nuevo o
   explicación de por qué el mutante es equivalente.
4. **Tests de regresión**: con agentes es fácil romper lo que andaba. Nunca se edita un test viejo para
   que pase (AGENTS.md); `make tests-modificados` lo delata.
5. **Fallas silenciosas** (10/01 §1): commit vacío o que solo agrega un comentario mientras el agente dice
   "terminé". El compañero compara lo que el reporte dice con el diff real.
6. **Guía, hook, sensor o humano** (10/01 §7): convención → AGENTS.md; "nunca" → hook determinístico;
   regla de negocio → test; decisión de arquitectura no cuantificable → revisión humana (Flora).

## C. Diseño del sistema agéntico (10/08, 08/20 §9, 11/05 §3)

1. **Empezar por lo más simple** (10/08, ideas finales): determinístico si se puede; una llamada si alcanza;
   workflow si los pasos se pueden escribir; loop agéntico solo si el camino no se prevé y el objetivo es
   verificable. Agregar autonomía tiene que justificarse.
2. **El LLM no hace aritmética, horarios ni cronologías** (08/20 §9 "caja negra mágica"; AGENTS.md):
   distancias, horarios, costos y restricciones son código.
3. **Los errores se componen** (10/08 §6): 0,9²⁰ ≈ 0,12. Cada paso extra en una cadena cuesta confiabilidad.
4. **Circuit breakers y límites duros** (10/08 §6): tope de intentos, de costo; el límite vive en el código,
   no en el prompt ("no te pases de 100" → contador que bloquea).
5. **Tools** (10/08 §7): nombre y descripción claros, input schema, parametrizadas (una tool con parámetro
   antes que N tools), acotadas ("buscar" antes que "listar todo"), **errores tipificados** que viajan hasta
   quien puede actuar. Docstring y schema sincronizados con el código.
6. **Lo que trae una tool no es verdad por venir de una tool** (10/08 §7): el modelo confía en sus fuentes y
   confabula. Por eso se verifican citas y se marcan datos faltantes.
7. **Programa = input, output y types** (11/05 §3): outputs acotados (enums, JSON con schema) evitan
   "soluciones" fuera de especificación; un enum impide inventar categorías (11/12 §14).
8. **La confianza que el modelo "dice" es inventada** (11/05 §5): nunca pedirle un score de confianza en el
   prompt y reportarlo como métrica.
9. **Prompt injection por la puerta de atrás** (10/08 §7): texto que viene de webs o fichas es dato, no
   instrucción.
10. **MVP sólido, sin sobreingeniería ni sobreambición** (10/08 §16). Tracer bullet antes que fases
    (08/20 §9): conectar todo de punta a punta temprano (ítem 005 del backlog).

## D. Evaluación y benchmarks (11/12 §14–15, 10/01 §10, C)

1. **Partición fija dev/test**; test no se toca (hook). Un resultado sobre test se reporta tal cual.
2. **Baseline simple** contra el que se mide (C: zero-shot, script determinístico o proceso manual).
3. **Scoring function = lógica de negocio**: ponderar lo que importa (una restricción dura violada pesa más
   que un detalle de redacción).
4. **Tareas verificables → función que comprueba**; no verificables → juez (LLM o humano), y el juez LLM se
   calibra contra anotación humana (C).
5. **Retrieval se evalúa por separado** con métricas de ranking (NDCG, recall@k), no solo precision/recall
   sin orden (10/01 §10). En un RAG, el retrieval suele ser el cuello de botella.
6. **Ley de Goodhart** (11/12 §9): si la métrica pasa a ser el objetivo, deja de medir. El compañero
   desconfía de cambios que "mejoran el número" tocando el set o la scoring function.

## E. Economía (C, 11/05 §13, 11/12 §6)

Costo por tarea en tokens y dinero, latencia, y por qué ese modelo frente a alternativas. Primero que
funcione, después abaratar (evitar optimización prematura), pero el costo se mide desde que hay LLM en el
camino.

## F. Datos (C, AGENTS.md)

Fuente, volumen, actualización y licencia identificados (DATAtourisme, Licence Ouverte 2.0). **Nunca
inventar bodegas, precios ni horarios** fuera de fixtures marcadas `[SINTÉTICA]`. Si hay datos sintéticos
en la evaluación, el generador se evalúa.

## G. Trabajo con agentes y registro (10/01 §4–5, §9; 08/20 §6, §9)

1. Archivos de reglas **cortos**, con lo que el agente no puede deducir. Si una regla falla seguido, el
   problema es el archivo.
2. **Changelog y ADRs** son la memoria entre sesiones: toda entrega actualiza CHANGELOG; toda decisión de
   arquitectura nueva tiene ADR.
3. **PRs chicos y entendibles**: "PRs kilométricos" y "slop" son síntomas de que la producción va por
   delante de la comprensión. Una tarea = un PR.
4. **Ownership selectivo** (08/20 §6): la lógica de negocio central (verificador, scoring, reglas de
   restricciones) Flora tiene que entenderla línea por línea; ahí el compañero pide explicaciones claras.
5. **Nunca soltar el control, mutarlo** (08/20 §3): el control pasa de leer todo a tests, mutation, hooks
   y revisión por otro agente, con Flora revisando el resultado agregado.
6. La consigna exige el uso de asistentes de IA y que el repo incluya **skills, reglas y artefactos**
   usados (C, "Entrega final"): todo lo del harness queda versionado.

## Clases sin explicación escrita

Las clases del 13/08 y del 27/08 solo están como transcripción en el Drive de Flora y no se versionan acá.
Si una revisión necesita algo de esas clases, el compañero lo marca como pregunta para Flora.
