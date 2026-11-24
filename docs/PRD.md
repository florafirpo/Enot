# PRD – Enot: agente de rutas de enoturismo en Borgoña

IA Agéntica · Maestría UBA · trabajo individual (ex Grupo 9) · Nov 23,
2026 · @Flora

## 1. Resumen y problema

> **Cambio de alcance (23/11/2026).** El grupo se disolvió y el TP pasa
> a ser individual. Para no depender de scrapear cientos de webs, la
> región cambia de Mendoza a **Borgoña (Francia)**, donde existe una
> base oficial y abierta de oferta turística (DATAtourisme). El producto
> y el problema son los mismos. Este cambio queda pendiente de
> validación por la cátedra.

Enot es un agente conversacional que arma itinerarios de 1 a 3 días por
bodegas de Borgoña a partir de las preferencias del turista. Cruza un
corpus propio, construido desde datos abiertos oficiales, con
herramientas determinísticas de distancia, horario y costo. La hipótesis
central: un agente con RAG, tools y un verificador de restricciones
produce itinerarios factibles y ajustados al perfil con más frecuencia
que un LLM consultado en zero-shot.

**Usuario objetivo.** Turista hispanohablante que planifica por su
cuenta una visita de 1 a 3 días a la Borgoña vitivinícola, con o sin
auto, y que no habla francés con fluidez. Usuario secundario, fuera del
MVP: agencias de turismo gastronómico que arman viajes a medida.

**Problema.** La oferta de Borgoña está muy fragmentada: muchos domaines
chicos y familiares, información repartida entre oficinas de turismo
locales, la mayoría en francés. Hoy el turista arma la visita:

- buscando domaine por domaine, sin saber cuáles reciben visitas, con
  qué horario y si hace falta reservar;

- adivinando distancias entre subzonas (Côte de Nuits, Côte de Beaune,
  Chablis, Mâconnais), con riesgo de pasar el día manejando;

- sin filtros reales por presupuesto, tipo de experiencia, idioma,
  tamaño del grupo o accesibilidad;

- con tours y listas que repiten las mismas casas conocidas y dejan
  afuera a los productores chicos.

**Tarea acotada.** Dada una consulta en lenguaje natural, devolver un
itinerario día por día (bodegas, horarios, traslados, costo estimado)
que cumpla las restricciones duras del usuario y permita ajustes
conversacionales.

## 2. Por qué un LLM y no software convencional

El LLM resuelve lo que un buscador con filtros no puede; lo
determinístico queda en herramientas. La división es explícita:

| Parte del problema                                                                                          | Quién lo resuelve             | Por qué                                                                                                                                              |
|-------------------------------------------------------------------------------------------------------------|-------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| Entender pedidos vagos y mixtos ("algo familiar, no la más conocida, almuerzo maridado, presupuesto medio") | LLM                           | Lenguaje natural ambiguo, preferencias implícitas, distintos idiomas                                                                                 |
| Normalizar información heterogénea (descripciones oficiales, webs de bodegas) a atributos comparables       | LLM (extracción estructurada) | Texto libre sin esquema común; las descripciones oficiales vienen en texto libre y en francés, cargadas por decenas de oficinas de turismo distintas |
| Leer señal cualitativa de las descripciones ("domaine familial", "biodynamie", "grands crus")               | LLM + embeddings              | Semántica, no palabras clave                                                                                                                         |
| Ajustar el plan por conversación ("más chico", "cambiá el día 2")                                           | LLM con memoria de sesión     | Edición incremental sobre un estado                                                                                                                  |
| Distancias, tiempos de traslado, horarios, suma de costos                                                   | Tools determinísticas         | Aritmética y cronologías: los LLM fallan; tienen que ser exactas y auditables                                                                        |
| Validar que el itinerario cumple las restricciones duras                                                    | Verificador en código         | Criterio automático para el loop de reintento                                                                                                        |

Un sistema de reglas con formulario cubriría los filtros duros, pero no
la interpretación del pedido, la extracción desde fuentes desordenadas
ni el ajuste conversacional. Ese formulario es, justamente, uno de
nuestros baselines (sección 6).

## 3. Solución: alcance funcional y casos de uso

Toda la interacción es por chat de texto. El MVP cubre cuatro
capacidades:

1.  **Relevamiento de preferencias.** El agente pregunta hasta completar
    un perfil estructurado (JSON): cantidad de días, fechas, transporte
    (auto propio / traslado / sin auto), presupuesto, tamaño del grupo,
    tipo de experiencia, preferencias de vino, zonas, bodegas a incluir
    o evitar, interés en bodegas poco conocidas, restricciones
    alimentarias y accesibilidad.

2.  **Recuperación de candidatas.** Búsqueda híbrida sobre el corpus:
    filtros duros por metadatos (zona, precio, días de apertura) +
    similitud semántica contra la descripción y las reseñas.

3.  **Armado del itinerario.** El planificador agrupa por zona, ordena
    por cercanía, asigna horarios respetando apertura y traslados, y
    suma el costo. Un verificador chequea las restricciones duras y, si
    falla, devuelve el error al planificador para reintentar (máximo 3
    vueltas).

4.  **Ajuste conversacional.** El usuario pide cambios ("más chico y
    familiar", "sacá el almuerzo") y el agente edita el itinerario
    vigente en lugar de rehacerlo.

**Casos de uso de referencia** (son también semillas del set de
evaluación):

- *Turista sin auto, 2 días:* "Llego a Beaune el jueves y me voy el
  sábado. Quiero 4 bodegas y un almuerzo con vinos, presupuesto medio,
  sin auto." → Día 1 en Côte de Beaune a distancia caminable o en bici
  desde Beaune; día 2 en Côte de Nuits.

- *Descubrimiento:* "Busco un domaine chico y familiar en Chablis, no
  una casa grande." → recomienda por ajuste al perfil (subzona, precio,
  tipo de experiencia), no por fama.

- *Restricciones duras:* grupo de 6 con una persona en silla de ruedas,
  visitas en inglés → solo bodegas con capacidad para grupo,
  accesibilidad declarada e idioma disponible.

- *Pedido infactible:* "8 bodegas en un día entre Chablis y el
  Mâconnais" → el agente explica por qué no entra (las subzonas están a
  horas de distancia) y propone una alternativa.

**Salida:** itinerario por día con bodega, horario, experiencia
sugerida, precio estimado por persona, tiempo de traslado y link a la
fuente de cada dato.

## 4. Arquitectura y áreas de profundización

El LLM interpreta, extrae y redacta; la factibilidad la decide código.
Es el patrón generar-verificar (LLM-Modulo, sección 10).

<img src="media/image1.png" style="width:6in;height:3.8125in"
alt="arquitectura de Enot · ingesta offline + flujo por consulta" />

arquitectura de Enot · ingesta offline + flujo por consulta

Si el verificador encuentra una violación, le devuelve al planificador
el error concreto ("Bodega X cierra a las 17, la visita termina 17:30")
y reintenta hasta 3 veces; si no lo logra, explica qué restricción no se
puede cumplir.

**Áreas de profundización** (la consigna pide al menos 2; elegimos 3
como núcleo):

1.  **Recuperación y context engineering sobre corpus propio.** Fichas
    extraídas de webs de bodegas, búsqueda híbrida (metadatos +
    embeddings), y retrieval evaluado por separado de la generación
    (Recall@10, nDCG@10).

2.  **Orquestación con loop de verificación y reintento** contra un
    criterio automático: el validador de restricciones duras. Medimos su
    aporte con la ablación B2.

3.  **Evaluación:** benchmark propio del dominio (100 consultas con
    restricciones etiquetadas) y juez LLM con rúbrica calibrada contra
    anotación humana.

Como soporte, sin ser área de profundización: tools con contratos
tipados y manejo de errores (distancias, horarios, costo) y trazas con
registro de costos.

**Stack propuesto:** Python, Docker, base vectorial local (por ejemplo
Chroma o pgvector), OSRM para distancias, y un framework de agentes que
podamos explicar por dentro (o un loop propio, que es corto).

## 5. Datos y corpus

La fuente principal es
[DATAtourisme](https://www.data.gouv.fr/fr/datasets/datatourisme-2/), la
base nacional francesa de información turística en datos abiertos: la
alimentan las oficinas de turismo locales, se actualiza a diario y usa
la Licence Ouverte 2.0. Publica un CSV por región; el corpus sale del de
Bourgogne-Franche-Comté, filtrado a los departamentos de Borgoña (21
Côte-d'Or, 71 Saône-et-Loire, 89 Yonne, 58 Nièvre).

| Fuente                             | Qué aporta                                                                                   | Uso en el sistema                                              | Actualización                                   | Licencia                                    |
|------------------------------------|----------------------------------------------------------------------------------------------|----------------------------------------------------------------|-------------------------------------------------|---------------------------------------------|
| DATAtourisme, CSV regional         | Nombre, tipo, coordenadas, dirección, contacto, clasificaciones y descripción en texto libre | Semilla + corpus del RAG (ficha estructurada extraída con LLM) | Diaria en origen; snapshot con fecha en el repo | Licence Ouverte 2.0                         |
| Webs de los domaines (opcional)    | Experiencias, precios y horarios que no están en la descripción                              | Enriquecimiento del corpus si la completitud queda baja        | Snapshot con fecha                              | Contenido público; se respeta robots.txt    |
| Distancias / tiempos de traslado   | Matriz entre bodegas a partir de las coordenadas                                             | Tool determinística (OSRM sobre OpenStreetMap)                 | Precalculable                                   | ODbL                                        |
| Consultas de evaluación sintéticas | Pedidos de turistas con restricciones etiquetadas                                            | Set de dev/test                                                | Fijo                                            | Generador en el repo y evaluado (sección 6) |

**Qué cuenta como bodega.** Los puntos de interés de tipo core:Cellar
("cave ou caveau") de la ontología DATAtourisme y, entre los demás
proveedores de degustación (productores, cooperativas, négociants), los
que mencionan vino en el nombre o la descripción. Cada bodega se asigna
a una subzona (Côte de Nuits, Côte de Beaune, Hautes-Côtes, Chablis y
Grand Auxerrois, Côte Chalonnaise, Mâconnais) por comuna, con una
aproximación por latitud cuando la comuna no está en la lista.

**Limitación conocida.** El CSV es "simplificado": los horarios y
precios muchas veces vienen solo dentro de la descripción, en francés y
en texto libre. Por eso la extracción con LLM es parte del núcleo, y la
web del domaine queda como fuente de respaldo.

**Esquema de la ficha por bodega** (lo que el LLM extrae): perfil,
horarios, si requiere reserva, experiencias (tipo, duración, precio y
moneda, idiomas, turnos), restaurante y opciones alimentarias,
accesibilidad, grupos, idiomas, vinos destacados, contacto, y una
evidencia (cita textual + fuente) por cada dato importante. Las
coordenadas, la subzona y la fuente las agrega el código, no el LLM.

**Estado de exploración (completar al correr el pipeline):**

- [ ] Cantidad de bodegas por subzona y cuántas tienen descripción, web
  y coordenadas

- [ ] Completitud por campo después de la extracción, sobre todo precio
  y horario

- [ ] Distribución de precios por subzona (EUR)

- [ ] Tamaño del corpus en caracteres y tokens

- [ ] Precisión de la extracción en una muestra revisada a mano

## 6. Hipótesis, métricas y evaluación

**H1 (principal).** Enot (RAG + tools + verificador con reintento) logra
una tasa de itinerarios que cumplen todas las restricciones duras al
menos 30 puntos porcentuales mayor que el mismo LLM en zero-shot sin
herramientas, sobre el set de test. *(El umbral de 30 pp es nuestra
propuesta; lo ajustamos con los resultados de dev.)*

**H2.** A igual factibilidad, Enot ajusta mejor a las preferencias
blandas que un filtro determinístico tipo formulario.

**H3.** Enot reparte las recomendaciones sobre una parte mayor del
corpus que el LLM zero-shot, que tiende a repetir las casas más
conocidas, sin bajar el ajuste al perfil.

**Set de evaluación.** 100 consultas sintéticas, partición fija 60 dev /
40 test, estratificadas por escenario (días, transporte, presupuesto,
grupo, idioma, accesibilidad, pedidos infactibles). Cada consulta trae
sus restricciones en JSON como etiqueta. Se generan con plantillas +
paráfrasis por LLM, y valido a mano un 20% (el generador se versiona y
se reporta su tasa de error). El tamaño está pensado para que la
anotación la haga una sola persona.

| Métrica                     | Qué mide                               | Cómo se calcula                                                                                                                                                                                     |
|-----------------------------|----------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Hard pass rate (H1)         | Itinerario factible                    | Validador en código: bodega existe en el corpus, abierta en día y hora, traslados entran en la jornada, presupuesto, capacidad, restricción alimentaria y accesibilidad. Todo o nada por itinerario |
| Tasa de alucinación         | Datos inventados                       | % de bodegas, precios u horarios que no están en el corpus ni en las tools                                                                                                                          |
| Preference score (H2)       | Ajuste a lo pedido                     | Juez LLM con rúbrica 1–5, calibrado contra anotación humana en 30 casos (Spearman y kappa)                                                                                                          |
| Cobertura del corpus (H3)   | Equidad entre bodegas chicas y grandes | % de bodegas del corpus recomendadas al menos una vez en el test, e índice de Gini de las recomendaciones                                                                                           |
| Recall@10 y nDCG@10         | Calidad del retrieval, aislado         | Contra bodegas relevantes etiquetadas por consulta (subset de 30)                                                                                                                                   |
| Costo y latencia            | Economía                               | Tokens, USD y segundos por itinerario, desde las trazas                                                                                                                                             |
| Infactibles bien detectados | Honestidad                             | % de pedidos imposibles en que el agente lo explica en vez de inventar                                                                                                                              |

**Baselines** (todos sobre el mismo test y, donde aplica, el mismo
modelo):

- **B0 – LLM zero-shot:** el pedido directo al modelo, sin corpus ni
  tools. Es lo que hoy haría un turista con un chatbot general; en este
  caso también mide cuánto inventa sobre domaines reales.

- **B1 – Determinístico:** formulario con filtros duros sobre las
  fichas + armado greedy por cercanía. Sin LLM.

- **B2 – Ablación:** Enot sin el loop de verificación (un solo intento),
  para aislar el aporte del verificador.

## 7. Riesgos técnicos y plan B

El mayor riesgo es que las descripciones de DATAtourisme no traigan
precio ni horario en forma extraíble: sin eso, el agente no puede
garantizar factibilidad.

| Riesgo                                                                            | Señal temprana                                                      | Plan B                                                                                                                                                                              |
|-----------------------------------------------------------------------------------|---------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Descripciones incompletas** (sin precio u horario)                              | Completitud \< 60% en precio u horario en el EDA                    | Bajar las webs de los domaines que tienen una (el pipeline ya lo soporta); si no alcanza, acotar a las bodegas con datos completos y marcar "precio a consultar" en vez de inventar |
| **El LLM viola restricciones o inventa datos**                                    | Hard pass rate bajo en dev aun con verificador                      | Mover la planificación a un solver determinístico (el LLM solo interpreta el pedido y redacta); el verificador ya está en código                                                    |
| **Errores al extraer desde francés**                                              | Precisión baja en la muestra revisada en campos de precio u horario | Ajustar el prompt con ejemplos en francés; comparar con un modelo más grande solo para la extracción (es un costo fijo, no por consulta)                                            |
| **Filtro de bodegas impreciso** (entran queserías o cervecerías, faltan domaines) | Revisión manual de la semilla                                       | Ajustar la regla de filtrado y marcar a mano las dudosas; queda documentado en el repo                                                                                              |
| **Retrieval irrelevante**                                                         | Recall@10 bajo en el subset etiquetado                              | Subir el peso de filtros por metadatos, búsqueda híbrida BM25 + embeddings, re-ranker                                                                                               |
| **Alcance excesivo para una sola persona**                                        | Atraso respecto del plan (sección 11)                               | Recortar a una o dos subzonas (Côte de Nuits + Côte de Beaune) y a dos áreas de profundización                                                                                      |

## 8. Fuera de alcance

- Reservas y pagos: el agente sugiere, no reserva.

- Alojamiento, vuelos y transporte interurbano; solo traslados entre
  bodegas el mismo día.

- Regiones fuera de Borgoña (Jura, Champagne, Beaujolais); el filtro por
  departamento lo permite, pero no se evalúan.

- Viajes de más de 3 días.

- Restaurantes y actividades que no estén dentro de una bodega.

- Disponibilidad en tiempo real de cupos.

- App móvil y despliegue productivo: el entregable es un chat en web o
  CLI, dockerizado.

- Calendario de eventos (ferias, días de puertas abiertas): pasa a
  próximos pasos.

- Mendoza: el pipeline conserva el camino con Google Places y scraping,
  pero no forma parte de esta entrega.

## 9. Estimación de costos y latencia

El costo se mide desde las trazas, no se estima a mano: cada llamada
registra modelo, tokens de entrada y salida, latencia y llamadas a APIs
externas.

C\_{itinerario} = \sum\_{i \in llamadas} \left( t^{in}\_i \cdot
p^{in}\_{m} + t^{out}\_i \cdot p^{out}\_{m} \right)

- **Costo fijo (una vez):** scraping, extracción de fichas con LLM y
  embeddings del corpus. Se reporta total y por bodega.

- **Costo variable:** por itinerario completo (relevamiento + armado +
  reintentos) y por ajuste conversacional. Se reporta media y p95 sobre
  el set de test, junto con la cantidad media de reintentos del
  verificador.

- **Comparación de modelos:** el relevamiento de preferencias y la
  extracción de fichas son tareas acotadas; comparamos un modelo de API
  de frontera contra uno barato o abierto corrido localmente (calidad,
  costo, latencia). El planificador usa el modelo que gane en dev.

- **Objetivo de latencia propuesto:** menos de 30 s por itinerario
  inicial y menos de 10 s por ajuste.

- **Escala:** proyectamos el costo mensual para un volumen hipotético
  (por ejemplo, 1.000 itinerarios por mes) con el costo medio medido.

## 10. Antecedentes

**Mercado.** Hay directorios y reservas por un lado, y planificadores
genéricos con IA por el otro. Ninguno de los relevados arma un
itinerario a medida verificando restricciones sobre un corpus completo
de bodegas.

| Producto                                                                                                             | Qué hace                                                                                                         | Diferencia con Enot                                                                        |
|----------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| [Rue des Vignerons](https://www.ruedesvignerons.com/fr/pays/france?page=4)                                           | Plataforma de reservas de visitas y degustaciones en domaines franceses, incluida Borgoña, con precio por adulto | Catálogo de las bodegas adheridas; el turista arma el recorrido a mano                     |
| [Winalist](https://www.winalist.fr/llms.txt)                                                                         | Reservas de visitas de caves y degustaciones por región vitivinícola, con cancelación gratuita                   | Ídem: reserva puntual, sin planificación de varios días ni restricciones                   |
| [Layla.ai](https://layla.ai/trip/rutas-del-vino-en-mendoza/01JE1C1XZX9DFEZK4GKKQGK57G) y otros planificadores con IA | Itinerarios por chat para cualquier destino                                                                      | Se apoyan en tours comercializables; sin verificación de horarios ni corpus local trazable |
| Oficinas de turismo y tours guiados                                                                                  | Folletos, mapas y salidas grupales fijas                                                                         | No personalizan; en francés o inglés                                                       |

**Literatura.** La planificación de viajes multi-restricción es un
problema conocido y difícil para agentes LLM:

- [TravelPlanner](https://arxiv.org/abs/2402.01622) (Xie et al., ICML
  2024): 1.225 consultas con restricciones duras y de sentido común;
  GPT-4 logró 0,6% de *final pass rate*. Tomamos de acá la métrica
  todo-o-nada y la separación restricciones duras / blandas.

- [LLM-Modulo para planificación de
  viajes](https://arxiv.org/abs/2405.20625) (Gundawar et al., 2024): el
  LLM genera y un conjunto de críticos externos verifica y devuelve el
  error; es el patrón de nuestro loop. Según [Hao et
  al.](https://arxiv.org/pdf/2404.11891), lleva el pass rate a 20% con
  GPT-4-Turbo y 65% con o1-preview.

- [Hao et al., 2024](https://arxiv.org/pdf/2404.11891): el LLM traduce
  el pedido a un problema formal y lo resuelve un solver SMT, con 93,9%
  en TravelPlanner. Es nuestro plan B si el loop no alcanza.

- [TravelBench](https://arxiv.org/html/2512.22673v1) (2025): agrega
  interacción multi-turno y pedidos irresolubles; inspira nuestro
  escenario de pedidos infactibles.

**Diferenciación.** Corpus trazable de bodegas de Borgoña desde datos
oficiales abiertos (incluidos los productores chicos), en español para
el turista, verificador de restricciones en código y recomendación por
ajuste al perfil en lugar de por visibilidad comercial.

## 11. Plan de trabajo y responsables

El trabajo lo hago sola, así que el plan prioriza llegar a una
evaluación honesta sobre test antes que sumar funcionalidades. Arranco
con un *tracer bullet*: una consulta que atraviese relevamiento →
retrieval → planificador → verificador → respuesta con las bodegas de
una sola subzona, antes de escalar.

| Semana        | Entregable                                                                                                                                |
|---------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| 24 al 28/11   | Corpus: CSV de DATAtourisme → semilla, extracción de fichas, EDA y muestra validada a mano. Tracer bullet con Côte de Beaune              |
| 29/11 al 4/12 | Retrieval híbrido, planificador con tools (distancias OSRM, horarios, costo) y verificador con reintento. Generador del set de evaluación |
| 5 al 8/12     | Evaluación sobre test contra B0, B1 y B2; juez LLM calibrado; costos y latencia; análisis de fallas. Docker, README y Makefile            |
| 9 al 11/12    | Presentación y ensayo de la defensa (exposición el 10 u 11/12, a confirmar)                                                               |

**A confirmar con la cátedra**

- Que el TP se pueda hacer de forma individual, con el alcance reducido
  de este documento.

- El cambio de región de Mendoza a Borgoña por disponibilidad de datos
  abiertos.

- La fecha de entrega final: la consigna decía 19/11, antes del cambio
  de equipo.
