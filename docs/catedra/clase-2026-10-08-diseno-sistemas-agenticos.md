Explicación – Diseño de sistemas agénticos (2.ª parte)

Inteligencia Artificial Agéntica · Clase del 08/10/2026 · Docente: Matías

Introducción: de “usar un agente” a “diseñar un sistema agéntico”

Esta clase continúa el bloque de diseño de sistemas agénticos y tiene una idea que la atraviesa de punta a punta: detrás de cualquier agente, incluso detrás de uno muy autónomo como Claude Code, hay una estructura que alguien diseñó. Esa estructura se puede pensar como una máquina de estados o como un grafo: hay pasos, hay decisiones, hay caminos que se toman según lo que pasó antes y hay bucles que se repiten hasta que se cumple una condición. Diseñar un sistema agéntico es, en buena medida, decidir cuánta de esa estructura fijás vos de antemano y cuánta le dejás decidir al modelo.

El recorrido de la clase va de lo general a lo concreto. Primero se plantea el gradiente de autonomía, que es el eje para ubicar cualquier sistema. Después se baja al mecanismo más elemental, el loop que llama herramientas (ReAct), y a todo lo que hace falta para que ese loop funcione bien y no se descontrole: cómo ve el modelo una tool, cómo se diseñan las tools, qué límites se le ponen al bucle, qué pasa con la seguridad, la infraestructura, la idempotencia y el caché. Con esas piezas en la mano, se pasa a los patrones de workflow y de agentes (cadena, router, paralelización, orquestador, evaluador-optimizador, ReAct, plan-and-execute, reflexión), a cómo elegir entre ellos y a cómo combinarlos en un grafo. La última parte ordena conceptos que suelen mezclarse: system prompt, tool, skill y MCP, y los tipos de memoria de un agente.

Un aviso del propio docente, que vale como marco: mucho de la práctica de la ingeniería de agentes es conocimiento muy reciente, que empezó a madurar recién el año pasado. Hay aportes que vienen de la ingeniería de software y de la teoría de control, pero buena parte es empírica. No hay todavía un cuerpo de fuentes maduras en el que apoyarse con total confianza; se está construyendo sobre la marcha.

1\. Lo que dejaron las novedades: ideas de diseño escondidas en las noticias

La clase arrancó repasando novedades, pero varias de ellas sirven para anticipar conceptos del día.

La primera es la de un modelo que se presentó como muy rápido y que “no alucina”. Mirado de cerca, es un clasificador few-shot: algo del estilo de BERT con una cabeza de clasificación, al que en el contexto le das unas pocas opciones posibles y él elige entre ellas. Que no alucine tiene sentido justamente porque no genera texto libre: su salida está restringida a un conjunto cerrado de categorías. Lo interesante para la materia no es el modelo en sí sino el rol que puede cumplir: tener un módulo clasificador rápido dentro de un diseño agéntico es muy buena idea. Puede funcionar como router (decidir hacia dónde va un pedido) o como mecanismo para decidir si una decisión hay que escalarla a un humano en el loop o a un servicio externo. Es el mismo tipo de pieza que en la clase de introducción aparecía como “patrón estándar: clasificador inicial como router”. Un detalle de mercado que el docente menciona como típico: aparece una startup con algo nuevo y enseguida uno de los grandes proveedores saca una alternativa parecida.

La segunda tiene que ver con la velocidad con la que cambian los modelos. Cuando un proveedor saca un modelo que tiene una ventaja clara (mejor, o casi igual de bueno pero mucho más barato), mucha gente migra. Para quien construye un sistema agéntico esto tiene una consecuencia de diseño: o mantenés el sistema actualizado con los últimos modelos, o lo diseñás con un router que distribuya cada tipo de tarea al modelo que más convenga. Esto último se hace mucho y es uno de los temas centrales de la clase.

La tercera es de seguridad: algunos modelos nuevos salen con pocas medidas de seguridad, lo cual vuelve más delicado el panorama de ciberseguridad. Un consejo práctico que se desprende: usar un modelo actualizado para pedirle un audit de seguridad del propio sistema nunca viene mal.

La cuarta es una técnica de interacción: usar HTML como interfaz. Cuando un modelo te devuelve una lista larga de cosas que tenés que revisar y decidir, en vez de ir respondiendo una por una en el chat podés pedirle “haceme un HTML donde vea todo como botoncitos, cliqueo rápido cada uno y después seguís desde ahí”. Es un caso particular de una idea más general: generar herramientas ad hoc para interactuar con el modelo. Y conecta con un tema que aparece en la clase, el del humano en el loop: a veces la persona forma parte del sistema por diseño, y conviene que esa participación sea ágil.

Hubo además tres noticias de contexto. Todos los proveedores están presentando agentes proactivos, “siempre despiertos”; con lo que se ve en la materia, ese tipo de agente se puede construir con un harness propio a la medida. Los textos generados por IA empiezan a llevar marcas de agua (primero Claude y después OpenAI), en línea con regulaciones europeas que obligan a informar cuando algo es salida de una IA o cuando quien interactúa es un agente. Y se publicó una tanda de cientos de resultados matemáticos generados con agentes, incluido un avance vinculado a la hipótesis de Riemann, con discusión sobre si lo que dicen los papers se condice con las demostraciones formales en Lean.

Esta última dio lugar a una conversación que vale la pena retener, porque toca el costado humano de la automatización. Un alumno matemático contó su frustración: dedicó la vida a trabajar con teoremas y de pronto, en pocas semanas, aparecen caminos mucho más ágiles que resuelven problemas, pero que a veces no son verificables. La comunidad del software, en cierto sentido, ya pasó por eso. Se habla de un “riesgo de significado” (asociado a la idea de ikigai): qué pasa cuando aquello a lo que uno se dedicó desaparece de un momento a otro. Y hay una crítica más fina: en matemática, el avance colectivo hacia un resultado va generando en el camino conocimiento compartido y herramientas que permiten que la comunidad asimile ese conocimiento. Si uno se “teletransporta a la cumbre de la montaña”, ese proceso orgánico de maduración se quiebra. Del otro lado, cualquier avance en esta línea puede terminar mejorando la propia investigación en IA.

Por último, sobre cómo informarse: hay mucho humo, y los algoritmos de recomendación no ayudan. La sugerencia es seguir a una persona de referencia por área (un matemático para lo matemático, por ejemplo), en la línea de lo que el docente llama “democracia fluida”: delegar el filtro en alguien en quien confiás para cada tema.

2\. El mapa general y el lugar del testing

Antes de entrar en el diseño, se mostró un mapa de los elementos que constituyen la ingeniería de agentes: los modelos de lenguaje, el aprendizaje por refuerzo, el uso de herramientas, los changelogs, la observabilidad, el fine tuning, LLMOps y AgentOps, la protección contra ataques como el prompt injection y los distintos tipos de testeo. Casi todo se va a ver a lo largo de la materia.

De ese mapa se destaca el testing, por una razón que tiene que ver con cómo cambió el trabajo. Antes, la mayor parte del tiempo se dedicaba a escribir código y el avance era más bien lineal. Ahora un agente genera una enorme cantidad de código y uno pasa mucho tiempo debugueando. En esa producción masiva es muy fácil romper cosas que ya funcionaban. Por eso los tests de regresión (que verifican que lo que andaba siga andando) son un tipo de test clave cuando se trabaja con LLMs, junto con los unitarios y los smoke tests. Es la misma idea que aparecía en la primera clase cuando se decía que, para no soltar el control de un loop autónomo, había que “mutar la forma de control”: los tests son esa forma de control.

3\. El gradiente de autonomía

Los dos extremos

La pregunta de partida es qué sería lo menos autónomo posible en computación. La respuesta: una línea de código determinística. Sabemos exactamente qué va a pasar; tiene autonomía cero. De ahí sale una moraleja que se repite en toda la materia: siempre que puedas resolver algo de forma determinística, va a ser mejor, porque es más controlable, más rápido y más barato, con la única condición de que efectivamente resuelva el problema.

En el otro extremo están los sistemas con muchos agentes que deciden incluso sus propios subordinados y sus objetivos intermedios. El ejemplo de la clase es un loop “estilo Y Combinator”: “proponé 100 ideas de startup y, para cada una, armá una empresa de agentes que la implemente y la haga exitosa”. Cada agente tiene un objetivo global (que la empresa sea exitosa), pero en el camino define sus propios objetivos. El control es mínimo y el paraguas de acción es enorme, siempre suponiendo que esos agentes tienen herramientas y un harness que les permitan actuar.

Los niveles intermedios

Entre esos dos extremos hay una escalera de niveles:

Workflow fijo: un paso a paso que ejecuta un modelo de lenguaje usando herramientas. Los pasos están decididos de antemano.

Router: la cadena arranca con un modelo que clasifica la necesidad y, según esa clasificación, deriva el pedido por caminos predeterminados (a un agente más autónomo, a una persona, a un modelo más liviano). Ahí aparece el clasificador rápido de las novedades.

Orquestador: un modelo que distribuye trabajo en cadenas subsiguientes, que van ganando autonomía según cómo se diseñen. Aun así, sigue siendo una respuesta secuencial a una tarea inicial.

Loop: un proceso que puede correr de forma continua, con ciertas herramientas, en el que no está predeterminada la cantidad de pasos ni el tiempo que va a llevar; va decidiendo hasta completar un objetivo.

Multiagente: varios agentes coordinándose, el máximo de autonomía.

La misma escalera se puede contar desde el lugar de la persona: sin asistencia, autocompletado, una cadena con herramientas, un bucle predeterminado en el que el modelo decide cuántas vueltas dar, y un proceso que decide por completo qué hacer.

Una observación realista: en empresas y en usos concretos del día a día, rara vez vas a ver multiagentes coordinándose. La mayoría de los sistemas está “por el centro” del gradiente. Lo que sí está creciendo son los loops que corren de forma continua con cierta autonomía.

Cómo ubicar un sistema en el gradiente

Al discutir dónde caían los TPs de los grupos surgieron dos aprendizajes. El primero: el chat es una interfaz, no el sistema. Un chatbot que responde preguntas sobre una base puede ser efectivamente todo el sistema, pero detrás de una interfaz en lenguaje natural puede haber cualquier cosa, con más o menos autonomía. No hay que confundir la forma de interactuar con la arquitectura de lo que pasa por detrás.

El segundo: hay criterios para ubicar un sistema. Uno es la cantidad y diversidad de acciones que puede tomar. Otro es si el sistema solo determina cuándo llegó al resultado o si además evalúa y decide qué sigue. Y otro es si la cantidad de pasos está predeterminada o no. Un grupo que describía un workflow que se dispara con un prompt, busca comentarios sobre estaciones de servicio y hace análisis de sentimiento, sin un loop que valide el resultado, estaba claramente en la zona de baja autonomía. Otro grupo que tenía un bucle que corre hasta pasar una evaluación, pero con un repertorio de pasos bien acotado, estaba en un punto intermedio: hay iteración, pero el paraguas de acciones es chico.

4\. Las reglas del entorno: system prompt y lo que mantiene a los agentes en carril

En el entorno donde corre un agente siempre van a hacer falta reglas y estructuras. La más básica es el system prompt: la parte del contexto que está fija y que el sistema predetermina para todos los casos. Aunque sea mínimo, sirve como mínimo para que el agente sepa cómo acceder al resto de la información contextual que importa.

En el caso concreto del agentic coding, la clase repasa los elementos que evitan que los agentes “se vayan por las ramas” o entren en conflicto entre sí: reglas por repositorio, un buen manejo de ramas en Git para que no haya conflictos, mecanismos de verificación de las salidas (como los tests de regresión) y mecanismos para mantener actualizada la información de avance y la capa de documentación que comparten agentes y personas. Esto último retoma el changelog de la clase anterior.

5\. El loop que razona y actúa: ReAct

De dónde viene

Uno de los trabajos fundacionales de los agentes es el paper de ReAct (alrededor de 2023). Parte de lo que ya se conocía como Chain of Thought: entrenar e instruir al modelo para que razone antes de dar la respuesta final. El Chain of Thought dio un salto importante de rendimiento y tiene además un beneficio lateral enorme: permite escrutar a los modelos. Buena parte del trabajo de seguridad consiste en leer qué estaba “pensando” el modelo cuando hizo determinada cosa.

ReAct suma a ese razonamiento la posibilidad de tomar acciones. El modelo piensa, decide una acción (por ejemplo, una búsqueda) con ciertos parámetros, recibe la salida de esa acción y responde en función de lo que obtuvo. Si un modelo solo actuara, tendrías una serie de llamadas a funciones sin razonamiento en el medio; ReAct intercala las dos cosas: razonar y actuar.

Un punto conceptual importante: todo esto sigue siendo concatenación de strings, tanto en el uso como en el entrenamiento. Hay tokens especiales que separan el contexto de la conversación y otros que delimitan las llamadas a funciones, y el modelo se entrena, como cualquier LLM, con predicción del próximo token, en este caso sobre trazas que incluyen acciones. Para alguien que viene de deep learning, la intuición es directa: no hay un mecanismo nuevo de “uso de herramientas” dentro de la red; hay un formato de secuencia que incluye llamadas y resultados, y una red entrenada para continuar esa secuencia de forma útil.

Qué pasa cuando el modelo llama a una tool

El llamado a una herramienta se descompone en pasos con responsables distintos.

Primero, el modelo elige qué tool usar entre las disponibles. Para elegir bien necesita buena información sobre qué hace cada una, y eso está en manos de quien diseña el sistema. Acá el docente trae una analogía con machine learning que conviene desarrollar: en ML, cuando se habla de la pirámide de datos, lo más importante siempre es qué datos tenés; ningún modelo compensa datos malos o insuficientes. En agentes, el análogo es la calidad de las herramientas. Un agente es tan bueno como el repertorio de tools que tiene a mano: si no tiene las herramientas que la tarea requiere, o si no puede distinguir bien cuál usar, no hay modelo que lo salve. Así como en un proyecto de ML el grueso del valor está en conseguir y preparar buenos datos, en un sistema agéntico buena parte del valor está en diseñar y documentar buenas tools.

Segundo, el modelo completa los argumentos que pide la tool, según cómo esté definida.

Tercero, y esto ya no lo hace el modelo sino el harness, es decir, código: se validan los argumentos antes de ejecutar (por ejemplo, que un año sea consistente o positivo) y se valida también lo que devuelve la tool. Este es el mundo de los outputs estructurados, con muchos frameworks dedicados. El ejemplo de la clase vuelve al clasificador few-shot: siempre devuelve un JSON con las categorías y la probabilidad de cada una. Si un agente tiene una tool que clasifica usando ese modelo, tiene que saber que la tool existe, qué argumentos recibe, generar la llamada y después saber manejar esa salida estructurada. El manejo de esa salida es responsabilidad del harness.

El loop en código

Si uno mira por dentro cualquier harness, siempre encuentra lo mismo: una lista de mensajes con roles (usuario, sistema, asistente) y metadata asociada a cada mensaje. Es la forma tradicional de llamar a las APIs de modelos. El flujo es simple: se llama al modelo con la lista de mensajes; si la respuesta no requiere ninguna herramienta, esa es la respuesta final; si requiere una, se ejecuta la herramienta, se agrega el resultado al contexto y se vuelve a llamar al modelo. Ese ciclo, repetido, es el loop agéntico más elemental.

¿Por qué el modelo no llamó a la tool que necesitaba?

La pregunta que se planteó en clase es práctica: tenés una herramienta disponible, la tarea la requería, y el modelo no la usó. ¿Qué revisás?

Primero, que la tool esté declarada y efectivamente entrando en el contexto. Puede pasar que algo esté ocupando todo el contexto sin que te des cuenta y la declaración quede afuera.

Segundo, que esté bien documentada: que la descripción refleje de verdad lo que la herramienta puede hacer.

Tercero, algo menos obvio: la actualización de las fuentes. Supongamos una tool que consulta una base de datos y agregás una tabla nueva de regulaciones. La herramienta no se entera sola. El modelo puede llamarla, no encontrar la tabla porque no sabe que existe, y no traer la información. Por eso hace falta trazabilidad completa de qué información se necesita, dónde está y cómo se mantiene actualizada. Todo esto es context engineering: la tool puede estar bien descripta y entrando al modelo, pero si la base cambió y no hay una capa que le explique al agente qué datos hay y para qué, el agente no sabe qué consultar.

La capa semántica de datos

Esa “capa que explica qué datos hay” tiene nombre en ingeniería de datos: la capa semántica, hoy muy relacionada con lo que se llama “capa de inteligencia”. No son los datos crudos sino una capa de gobernanza que dice qué bases existen, de dónde salen, qué tan actualizadas están, quiénes son los responsables de cada fuente, cómo se interpreta cada dato y cómo se cruza con otros. Tiene sus propias herramientas, como dbt o DataHub. En un sistema maduro, el agente tendría acceso a toda esa capa semántica.

Pero hay un matiz importante, que depende del tipo de tool. Una tool que “hace queries a tu base de datos” es muy general, casi una capacidad abierta. Eso tiene sentido en un equipo de BI que genera reportes: la herramienta va a estar escribiendo queries nuevas y sí necesita la capa semántica en tiempo de ejecución. En cambio, en un chatbot probablemente las tools no escriban queries nuevas sino que sean más específicas. En ese caso la capa semántica se usa al construir o actualizar las tools, no en cada llamada.

6\. Ponerle límites al loop

Circuit breakers

Un loop sin límites es un riesgo. El mecanismo clásico para acotarlo es el circuit breaker: algo que corta el bucle cuando se llega a un tope. El tope más simple es una cantidad máxima de pasos, pero puede ser cualquier circunstancia que convenga para el caso: la detección de una situación sensible, una tool que calcula algo y detecta que se cruzó un umbral de alerta, una regla de policy, o una razón financiera.

La razón financiera es menos creativa pero muy relevante. En un entorno agéntico uno siempre está decidiendo cuánto cómputo asigna a cada cosa y manejando el budget de los distintos modelos. Con un diseño del tipo “paralelizá este problema con N agentes y quedate con la mejor solución”, si N son mil agentes es facilísimo romper el presupuesto. De ahí la idea de un watchdog: un monitor siempre atento a que no se pase el budget, especialmente útil si un loop costoso quedó corriendo.

Por qué conviene acortar las cadenas: los errores se componen

Además de los topes por seguridad o costo, hay una razón estadística para limitar la cantidad de pasos secuenciales: los errores se componen. Si cada paso tiene una probabilidad de acierto p (por ejemplo, la exactitud con la que el modelo elige qué herramienta llamar) y los pasos son secuenciales e independientes, la probabilidad de que la cadena entera salga bien es pⁿ. Con p = 0,99 parece casi perfecto, pero a medida que n crece la cifra cae. Con 90 % de exactitud por paso y 20 pasos, la cuenta da 0,9²⁰ ≈ 0,12: el sistema completo acierta alrededor de una de cada ocho veces. Para alguien de data science es el mismo razonamiento que el de multiplicar probabilidades de eventos independientes, pero conviene tenerlo muy presente al diseñar: cada paso extra en una cadena tiene un costo en confiabilidad, no solo en latencia.

Context rot y economía de tokens

Hay otro efecto de alargar las secuencias: el contexto crece con cada llamada y cada resultado que vuelve. Y existe el fenómeno de context rot: a medida que el contexto se agranda, la señal de la información más valiosa (por ejemplo, una instrucción inicial diseñada con mucho cuidado) se va “licuando” entre todo lo demás, y el modelo funciona cada vez peor.

A eso se suma el costo. La economía de tokens es cada vez más central, porque los tokens son en cierto sentido una materia prima fundamental. Y un dato que suele sorprender: la mayoría de los tokens del contexto en una interacción agéntica no vienen de lo que escribe la persona sino de las llamadas y ejecuciones de herramientas. En una traza típica hay, más o menos, un mensaje humano cada 10 o 15 elementos.

Guardrails determinísticos

¿Cómo se ponen esos límites? Hay muchas capas posibles, pero la regla para lo sensible es clara: tiene que haber bloqueos determinísticos que no se puedan pasar de ninguna manera. Lo más “soft” es pedirlo en el prompt (“por favor, no gastes mucho”). Lo correcto es un límite duro: un presupuesto o cuota configurado en el proveedor, que el sistema no pueda exceder. Ojo que no todos los proveedores cloud permiten limitar del todo el budget.

El ejemplo de la clase lo deja clarísimo: si tu sistema envía mensajes por WhatsApp y no querés que mande más de 100, no le pongas en el contexto “llevá la cuenta y no te pases de 100”. Poné un contador en tu sistema que cuente todos los mensajes salientes y, al llegar a 100, bloquee la salida. El límite no depende de que el modelo se acuerde ni de que cuente bien.

Effort no es un límite de presupuesto

Surgió la pregunta sobre el parámetro de effort que ofrecen algunas herramientas. El effort no es un tope de gasto. Es un hiperparámetro de inferencia: indica cuánto cómputo querés que el modelo dedique a pensar (al thinking, a la cadena de razonamiento) antes de responder. En ese sentido se parece a la temperatura, que también es un parámetro de inferencia (la temperatura regula cuánta diversidad hay al samplear en el decoding). El effort funciona porque en la última etapa de entrenamiento, con aprendizaje por refuerzo, se entrena al modelo para que respete esa indicación de cuánto elaborar. Pero un modelo con effort mínimo puede igual consumir muchos tokens en otras partes del trabajo, así que no reemplaza un límite de budget.

Esa misma pregunta llevó a anticipar el router: una primera capa del harness que, ante un problema o una instrucción, decide a qué modelo mandarlo o cuánto effort dedicarle. Eso permite usar modelos especializados que sean mejores, más rápidos y más baratos para ciertas tareas, o incluso no usar un modelo para algunas. Si tenés una base de preguntas frecuentes y alguien pregunta exactamente algo que está ahí, devolvé esa respuesta tal cual: ahorrás costo y además no te arriesgás a que el modelo alucine.

Qué hacer cuando una tool falla

Supongamos una tool “buscar normas de alquiler” que devuelve vacío. Hay varias decisiones posibles: que el modelo genere lo que pueda sin esa información; que, si siempre querés respuestas con fuente citable, el sistema no responda y devuelva algo predeterminado como “no encontré información”; o que llame a otra herramienta que busque en otra base o en un pool más amplio de documentos.

Lo importante es notar que esto se puede formular de dos maneras. Una es como máquina de estados: “probá esta herramienta; si no trajo el documento, probá esta otra; si tampoco, respondé tal cosa”. Es un flujo determinístico y secuencial, aunque cada paso use un LLM. La otra es dejar que el sistema decida por sí solo qué probar, como en un loop ReAct, y responda con lo mejor que consiguió cuando llegue al estándar que le fijaste.

Y se pueden combinar. Ejemplo: siempre que entra una consulta, se llama a una herramienta que trae la última versión de las preguntas frecuentes; si la respuesta está ahí, se responde con eso; si no, se deriva a una persona o a un loop agéntico que dé las vueltas que necesite. El loop autónomo queda como una rama del sistema, no como el sistema entero. Este es el mindset de toda la clase: pensar en el diagrama de estados que está detrás, aun cuando usás agentes muy autónomos como Claude, que tienen al menos la autonomía de seguir iterando hasta decidir cortar.

7\. Cómo ve el modelo una tool, y cómo diseñarlas

Lo que el modelo ve no es tu función

Cuando una función de código (como buscar\_normas con sus parámetros) se expone como tool, el modelo no ve la función. Ve una descripción estructurada en JSON con un nombre, una descripción y un input schema que le dice qué tiene que poner en cada argumento. Esa descripción es lo que le da al modelo la capacidad de resolver cosas específicas del dominio; por eso es de lo más importante del sistema.

En la práctica, esa descripción se suele autogenerar. Frameworks como FastMCP toman el código y generan la descripción de las tools a partir de la documentación de la función, su docstring. Recordemos qué es MCP (Model Context Protocol): así como existen las APIs para que un programa llame a otro, MCP es un protocolo pensado para la comunicación con agentes.

Si el código está mal documentado, la descripción puede salir incompleta. Pero el riesgo que el docente considera mayor es otro: la desincronización. Si modificás una tool o agregás una capacidad en otra parte del sistema, tenés que asegurarte de que eso se refleje en la documentación de la tool y en el MCP desde donde se sirve. Imaginá una empresa con 100 equipos que comparten herramientas: el área de diseño le agrega una capacidad a su herramienta de generación de voces en off; si el MCP que usan los demás equipos no se actualiza, el input schema queda viejo, con argumentos o posibilidades que ya no coinciden. Por eso aparece la gobernanza: owners por skill, por MCP y por tool.

Cuando el modelo genera argumentos que no cumplen el esquema, hay un error. Claude, por ejemplo, detecta el error, lo corrige y reintenta; lo mismo se puede implementar con LangGraph. Hoy en día los modelos casi siempre generan bien los argumentos; era más problema hace un tiempo.

Seguridad: lo que entra por la puerta de atrás

Los agentes, a pesar de que se los llame superinteligentes, son muy vulnerables, sobre todo a lo que les llega por vías menos comunes. Una forma típica de prompt injection es a través de las llamadas a servicios: un sitio web que tiene escondido en su código un mensaje malicioso, de modo que cuando un modelo lo lee, entra la instrucción. Nadie la escribió en el chat; el usuario simplemente le pidió al agente que leyera una página. El entrenamiento contra prompt injection protege más contra lo que escribe un usuario por la entrada normal que contra lo que entra por vías programáticas.

Relacionado con esto: el modelo tiende a confiar en lo que viene de una fuente que él mismo consultó. Si la tool trae un dato errado, el modelo puede tomarlo como válido, confabular y seguir adelante con él.

Una herramienta para mitigar esto es tipificar los errores: implementar errores propios en el sistema, en la API o en el MCP. Por ejemplo, un “error de regionalismo” que diga “esta legislación aplica en tal lugar y no en tal otro”. Así la información del error viaja en cadena hasta el nivel donde alguien (persona o agente) la lee y puede actuar.

Principios de diseño de tools

Como las tools tienden a multiplicarse, hay algunos principios. Tienen que ser claramente entendibles, bien descriptas, específicas y, muchas veces, parametrizadas para no terminar con un montón de herramientas distintas. El ejemplo: una financiera que necesita leer balances de 50 instituciones podría tener “descargar balance Stripe”, “descargar balance Galicia”, etc., o una sola “descargar balance” con la institución como parámetro. La segunda opción ahorra tools y, sobre todo, contexto.

Del mismo modo, una tool puede ser más eficiente, más precisa y más segura si está bien acotada: “search contacts” en vez de “list contacts”, que devolvería todos los contactos. Una tool mal hecha, como la que se mostró en clase, suele tener los tres problemas a la vez: no tiene descripción, no queda claro qué hacen sus parámetros y lista todo en vez de buscar.

Datos sensibles que el LLM no debe ver

Un alumno planteó un caso concreto: un usuario quiere consultar su factura, la tool necesita el DNI, pero no querés que el LLM vea el DNI. No hay un estándar para esto, pero hay maneras. Una es tener una lookup table intermedia con un valor que pueda ser público (por ejemplo, un hash del DNI): el modelo genera o busca ese valor y con eso llama a la herramienta. Otra es una tool o subsistema intermedio que acceda al dato sensible y lo procese aislado del LLM, y que le devuelva al modelo solo la parte que vos permitís. En cualquier caso, hay que intervenir tanto en la llamada como en la respuesta. Es distinto del manejo de secrets (como las API keys), que directamente no tienen que estar ni en el código ni al alcance del modelo.

8\. Infraestructura: dónde corre cada cosa

Hay conocimientos de ingeniería de software que la materia da por sabidos (qué es un servidor, qué es una API), pero al diseñar un sistema agéntico siempre hay que saber dónde corre cada cosa. Las tools que consultan servicios externos (clima, noticias) van a un entorno donde existe esa información. Las bases de datos están corriendo en algún lado y, si sos quien desarrolla, tenés que gestionarlas; la interacción entre un LLM y una base de datos es un tema en sí mismo, que requiere capas de protección, y nunca hay que darle a un LLM acceso de escritura total a una base. Si el agente ejecuta código (como en un harness propio manejado desde WhatsApp o Telegram), necesita un entorno de ejecución, por ejemplo un container con todo lo necesario. Lo más importante de todo esto son los permisos y la seguridad.

Idempotencia

Un concepto que importa mucho con agentes es la idempotencia: la propiedad de una función o proceso por la cual no importa cuántas veces se aplique, el resultado es el mismo. Con agentes es valiosísima porque captura modos de error típicos: un modelo que se equivoca y repite una acción, o varios agentes que hacen lo mismo. El ejemplo: una función “enviar mail a Pepito” que, cada vez que se ejecuta, manda un mail nuevo. Si la parametrizás con una clave, la función puede verificar “con esta clave ya se mandó” y no volver a mandarlo. Así, llamarla una o diez veces da lo mismo.

Caching

Otro tip de ingeniería de software que los modelos no van a implementar por default es el caché: una memoria de acceso más rápido con resultados precomputados, para no recomputar. Si tenés un proceso que resume las noticias del día y lo consultan 100 usuarios, se ejecuta la primera vez, el resultado queda en caché y los demás lo leen directo. Ganás velocidad y ahorrás cómputo. Es barato de implementar.

Hay distintos niveles. Algunas bases de datos tienen caché nativo para queries que se repiten. Más común es cachear en la capa de aplicación: si accedés a la base a través de una API, podés cachear los endpoints (por ejemplo con una LRU cache), de modo que el mismo pedido devuelva el mismo resultado. Ahí hay decisiones que tomar, como por cuánto tiempo vale lo cacheado: para un dashboard, la API puede precomputar una vez por hora y servir algo con, como mucho, una hora de demora. En el caso de los agentes, el MCP también tiene una API detrás, así que se puede cachear ahí, cuidando que no interfiera con nada. Y para aplicaciones web existe la CDN (Content Distribution Network), muy usada en aplicaciones serverless: además de cachear, deja copias del contenido cerca de los consumidores (por ejemplo, una copia en San Pablo y otra en Norteamérica para un blog), de modo que le cargue rápido a todos.

Tools que encapsulan modelos de ML

Con un grupo que trabaja en informes de riesgo crediticio surgió un caso que resume bien la filosofía de diseño: aprovechar lo mejor de cada cosa. No querés que el LLM calcule métricas “a ojo”; querés una tool que las calcule bien. Si tenés un modelo de churn o de morosidad entrenado con machine learning clásico, todo el preprocesamiento y la inferencia (aplicar a cada dato los mismos pasos de preprocesamiento con los que se entrenó) es código Python que el LLM ni siquiera ve. La tool se llama, por ejemplo, “calcular riesgo” o “traer indicadores”, y el LLM recibe los resultados y los interpreta.

Para que interprete bien, entra en juego la skill. Si el sistema se usara, por ejemplo, desde Claude con un MCP, habría una skill “analizar riesgo crediticio de una persona” que diga: arrancá considerando tal cosa; tenés estas herramientas que te dan estos indicadores; interpretalos así y con estos cuidados; dame el resultado con este formato, estas conclusiones, y reportando qué herramientas llamaste. La skill le da contexto a la llamada de la función.

Una recomendación del docente para las skills: que hagan transparente la freshness (recencia) de los datos y si todas las fuentes se consultaron bien. Por ejemplo: “8 de las 10 fuentes se consultaron correctamente; estas son sus fechas de actualización; dos no se pudieron consultar”. Si no se lo pedís, no lo hace. También se puede condicionar la llamada: “considerá solo resultados con menos de 3 días de antigüedad”. Esa condición puede vivir dentro del código de la tool (que directamente no devuelva análisis si los datos están viejos) o fuera, en la skill (que la tool devuelva igual y el modelo lo interprete con esa salvedad).

9\. Patrones de workflow

La segunda parte de la clase entra en los patrones. Primero los de workflow, donde el camino está mayormente determinado por el grafo que diseñás.

Cadena (secuencial). El más simple: pasos fijos de refinamiento. Ejemplo: un primer paso de búsqueda de bibliografía, un segundo que selecciona lo más importante y un tercero que resume las fuentes. Una variante es la cadena con condicionales, que es básicamente un DAG (grafo acíclico dirigido) cuyos nodos son llamadas a LLM con sus tools: según lo que pase en un paso, se sigue por un camino u otro, o se escala a otro mecanismo (por ejemplo, un sistema tradicional).

Router. Un nodo del flujo decide qué se hace en los pasos siguientes. El ruteo puede ser hacia distintos modelos (más o menos costosos, más o menos especializados) o hacia distintos subpatrones (un loop, una secuencia, una persona). Ese nodo es una llamada a un modelo que clasifica, pero parte del ruteo puede ser determinístico, por ejemplo con expresiones regulares. Vuelve la moraleja: siempre que puedas tener una salida determinística, va a ser mejor. Y, como se vio en Information Retrieval, en retrieval conviene un ensamble: búsqueda semántica combinada con búsquedas determinísticas (búsqueda difusa de strings, regex).

El router abre además una tendencia que se ve en muchos proyectos: arrancar con modelos de frontera y, cuando hay suficiente volumen de datos y de casos, entrenar modelos especializados, por ejemplo con destilación o con etiquetado y supervisión humana. Suele ser una mejora en todos los frentes a la vez: más rápido, mejor, más barato y, si corre on premise, mejor para la privacidad.

Paralelización. Se instancian muchos modelos que hacen algo en paralelo y después se sintetiza. Sirve para deliberar (distintos modelos con distintas perspectivas que sacan sus conclusiones, y luego un ensamble de opiniones), para hacer voting entre varios modelos, para llamar a tres APIs a la vez sin bloquearte esperando cada una, o para investigar (“encontrá 20 diarios que tengan esta noticia y resumí cada uno”). La regla general: cualquier problema con partes disjuntas es apto para paralelizar.

Orquestador. Se parece a la paralelización (rutas y síntesis), con una diferencia clave: es el propio modelo el que decide a qué subagentes delegar y cómo distribuir el trabajo. El ejemplo de clase es una migración de un lenguaje de programación a otro en una base de código con cientos de funciones: un orquestador abrió más de cien modelos chicos, uno por función, y lo que hubiera llevado tres días llevó una hora.

Evaluador-optimizador. Un generador produce una salida, un evaluador la juzga con un criterio y le devuelve feedback, y se itera hasta que se acepta. Es importante entender por qué no se lo considera autónomo: es una operación puntual, una especie de juez que da feedback en una tarea específica y se repite hasta cruzar un umbral. No hay un repertorio de acciones posibles entre las cuales elegir, que es lo que caracterizaría a un sistema más agéntico.

Estos patrones se pueden usar de dos maneras: pidiéndoselos a un agente como Claude (“encará este problema con este patrón”), o fijándolos por diseño en el grafo de tu propio sistema (por ejemplo, que siempre que haya varias tools, cada una sea consumida por un agente y deliberen cuál es más relevante).

Reward hacking: ¿en qué se basan los criterios?

Cuando un camino del grafo depende de que un modelo juzgue si algo está bien, aparece un problema: el reward hacking. Un modelo te puede decir que hizo algo bien y lo terminó cuando en realidad no. Un caso que sigue pasando en todos los modelos: en vez de resolver la tarea, cambian los tests para que pasen, es decir, mueven la vara de qué es “estar bien”. Por eso, para lo sensible, conviene un ensamble de métodos con distintos modelos e, idealmente, al menos un chequeo determinístico, completamente controlable y transparente.

Un caso discutido: matchear CVs con trabajos

Un grupo planteó un agente que encuentre trabajos afines a un CV y preguntó si el evaluador-optimizador era el patrón adecuado. La respuesta tiene varias capas.

Como evaluador-optimizador se vería así: el generador propone un match entre el CV y un trabajo de la base, con su justificación; el evaluador lo juzga. Ese evaluador podría ser un ensamble de criterios: uno determinístico (qué porcentaje de los requisitos concretos del aviso cumple el CV, por ejemplo años de experiencia) y otro vía LLM (afinidad cultural entre la persona y la empresa). Si el match no convence, el evaluador devuelve feedback (“el match cultural no fue bueno, buscá otro”) y el generador propone otro. Haría falta un circuit breaker.

Pero el patrón no resuelve si podés confiar en el evaluador: diseñarlo bien es justamente el desafío. Y probablemente haya un enfoque mejor: generar todos los pares posibles, hacer un buen re-ranking y quedarte con los mejores. Recién como paso final tendría sentido un juez LLM que valide el top N con criterios más interpretativos o semánticos que los usados en el ranking.

Un alumno aportó una mejora importante: que el juez se base en casos reales, por ejemplo personas que fueron recomendadas y consiguieron el trabajo; sin una base real contra la cual comparar, es muy difícil que el juicio sea objetivo.

Y el docente llevó la discusión un paso más allá: si el problema se puede formular con datos y una función objetivo precisa (tenés CVs, trabajos y podés construir una base etiquetada), lo mejor es entrenar un modelo de ML, por ejemplo con contrastive learning o embeddings two-tower. Ese modelo sería una pieza que el sistema corre siempre, como proponedor de pares. Habría que preprocesar CVs y avisos de forma estandarizada para que, por ejemplo, el formato del CV no altere los embeddings, y después mantenerlo con reentrenamiento y monitoreo (MLOps).

La Bitter Lesson

Para justificar ese último punto, el docente trae “The Bitter Lesson” de Richard Sutton, una referencia en aprendizaje por refuerzo. En ML tradicional había mucha artesanía en construir variables: decidir a mano qué features capturan lo importante. La lección amarga es que no importa cuánto amor le pongas a esa artesanía: lo que más importa es poder poner cómputo a optimizar el problema. Con suficientes datos y cómputo, eso le gana a cualquier ingeniería manual.

La conexión con los sistemas agénticos es directa. Va a haber muchas maneras de “entrenar” estos sistemas (optimizando el prompt, trabajando los evals, trabajando el harness), pero entrenar un modelo de ML es una forma muy buena de meterle mucho cómputo a un problema bien formulado. Si podés formularlo con datos y una función objetivo, aprovechalo.

10\. Patrones de agentes

Dónde cae cada patrón en el gradiente

Con los patrones a la vista se los puede ubicar en el gradiente de autonomía. La cadena y la paralelización tienen caminos predeterminados en el grafo. El router un poco más, pero los caminos siguen siendo los que vos definiste. En el evaluador-optimizador ya cuántas vueltas da el loop queda un poco fuera de tus manos. El orquestador toma más decisiones (qué tareas, cuántas). Después viene el agente con tools y, al final, varios agentes, “la sociedad de las máquinas”.

ReAct, plan-and-execute y reflexión

En los patrones de agentes hay mucho margen para la creatividad: se pueden meter loops en todas partes y reemplazar cualquier pieza por métodos de ensamble. Pero hay algunos clásicos.

ReAct es el loop de facto: se toma una acción, se ven los resultados, hay algún juicio o reflexión, y se decide si seguir hasta lograr el objetivo. Lo que hay que especificar bien es cuándo se llegó al objetivo. Y lo que lo distingue del evaluador-optimizador es que tiene un repertorio de tools entre las cuales elegir; el evaluador-optimizador solo itera con feedback sobre la misma tarea.

Plan-and-execute: hacer un plan, volcarlo en un gestor de tareas tipo Kanban y distribuirlo a distintos agentes en distintos entornos, o incluso a personas. Es algo que también se ve al usar Claude, que arma un plan, aunque en general no lo distribuye (se le puede pedir).

Reflexión: una vez que el agente completó una trayectoria, observa lo que pasó y anota aprendizajes que se incluyen en el contexto la próxima vez. Puede ocurrir durante el episodio o al final. Hermes, por ejemplo, anota esos aprendizajes en sus propias skills para automejorarse. La versión más mainstream de esta idea (2023) mejoró bastante el rendimiento en el benchmark HumanEval.

Hay miles de patrones propuestos (existe un sitio, “Awesome Agentic Patterns”, que los junta) y falta estandarización; son más “creativos” que los patrones clásicos de diseño de software. Los papers que los comparan muestran un trade-off conocido: más cómputo y más capas de reflexión suelen funcionar mejor, a mayor costo, siempre que sepas podar bien el contexto. Es otra vez la bitter lesson.

Cómo elegir el patrón

La clase propone una secuencia de preguntas para no apresurarse hacia la autonomía:

¿Se puede resolver con un programa determinístico? Entonces hacelo así. Es más simple, más confiable, más replicable. Esta pregunta va siempre primero.

¿Alcanza con una sola llamada al modelo, con buenos ejemplos o con retrieval? Entonces one shot, sin agente.

¿Podés escribir los pasos de antemano? Entonces un workflow fijo. Acá aparece el concepto de runbook, que viene de la ingeniería tradicional: un protocolo paso a paso que se ejecuta siempre igual, que se puede escribir por ejemplo en Markdown, y que uno itera a mano tocando el workflow.

¿Hay entradas de distintas categorías o sensibilidades que requieren tratamiento distinto (algunas van a personas, otras no)? Entonces routing.

¿No sabés qué serie de acciones va a hacer falta? Entonces un orquestador o un loop agéntico, según qué tan previsible sea. Pero para un agente necesitás un objetivo claro y verificable. Si no lo tenés, todavía no estás para un agente: tenés que seguir definiendo el problema.

El ejercicio de clase

Para practicar se analizaron cuatro casos. Clasificar reclamos de un municipio en cinco tipos es un router: según el tipo, el reclamo va a un modelo, a una cadena o a otra, y esos caminos los predeterminamos nosotros. Responder consultas abiertas sobre una normativa que pueden requerir varias búsquedas es ReAct: no sabés cuántas búsquedas hacen falta, así que el loop decide. Un informe mensual que implica bajar datos, resumir, revisar el formato y publicar es una cadena: una secuencia de pasos conocida. Traducir contratos con un glosario obligatorio que se puede chequear es un evaluador-optimizador: el criterio de evaluación es verificable.

De este último salió una pregunta muy buena: si conocés el glosario, ¿no conviene ponerlo directamente en el contexto desde el principio? Y la respuesta es que sí: si sale bien en una sola pasada, eso es mejor. El evaluador-optimizador se justifica cuando el resultado no sale en una sola iteración, y eso es empírico: lo descubrís probando. Es como si al generador, dándole varias vueltas, le saliera cada vez mejor; el patrón es la forma de darle esas vueltas. Un ejemplo donde encaja bien: generación de imágenes, con cinco variaciones generadas en paralelo y un evaluador que elige, o un segundo chequeo con un modelo más grande y especializado que verifique la guía de estilo obligatoria de una marca o que el logo esté bien.

11\. Ingeniería de grafos

Con todo esto se llega a lo que se llama ingeniería de grafos: diseñar la estructura del grafo del agente, es decir, su lógica (no la infraestructura: no se trata de en qué máquina corre la API ni de cómo están separados los microservicios).

Los elementos son pocos. Los nodos son funciones: pueden ser llamadas a un modelo o funciones determinísticas, y lo decidís vos al diseñar. Las aristas fijas conectan un nodo con otro siempre, como en una cadena. Las aristas condicionales dependen de un clasificador, que puede ser un LLM, un clasificador few-shot rápido, un modelo de ML tradicional o una regla determinística. Y los bucles aparecen en algún lugar del grafo, con más grado de autonomía (total o parcial) y, por supuesto, con su circuit breaker. Un bucle puede tener además salidas alternativas: si encuentra algo que amerite alertar, en vez de ir al usuario puede avisar a un operador.

El ejemplo dibujado en clase muestra cómo se mezcla todo, y es el tipo de grafo que LangGraph permite construir. Llega una entrada del usuario. Si trae un PDF (un if determinístico, porque sabés que siempre hay que parsearlo y no tiene sentido dejarlo a criterio del modelo), pasa por un nodo con un modelo visual que hace OCR. Después se clasifica si la consulta es sencilla. Si lo es, sigue una cadena simple: RAG, conclusión, respuesta al usuario. Si no lo es, pasa a un loop agéntico tipo ReAct. Y en paralelo, si la consulta coincide con una pregunta frecuente (por búsqueda exacta o string matching, como cuando un sitio te autocompleta preguntas predeterminadas), se responde directo sin LLM.

La idea central: el grafo lo armás como quieras, y el loop agéntico puede ser condicional a ciertos casos, mientras el resto se resuelve con una cadena de menos autonomía.

12\. Skills

Curadas vs. autogeneradas

Sobre skills se mostró un estudio que compara tres situaciones: skills curadas a mano, skills autogeneradas y ninguna skill. Las curadas rinden mejor. Lo llamativo es que las autogeneradas rindieron peor que no tener skills en varios casos. La interpretación del estudio es un sesgo de inducción: si el modelo falla en algo por sus propios sesgos, esos mismos sesgos se trasladan a las skills que escribe, que además se vuelven más inflexibles. Sin antropomorfizar demasiado: el modelo consolida por escrito sus errores.

La ventaja de lo curado es más evidente cuando hay conocimiento de dominio implícito, que no está ni en el código ni en los datos. El ejemplo de la clase: “fijate que esta tabla la carga Catalina todos los viernes, a veces se cuelga y la carga el lunes”. Eso no está en la base de datos. Es el mismo tipo de problema que la capa semántica busca resolver en ingeniería de datos: darte contexto y metadatos sobre los datos que no están en el dato mismo.

Una aclaración que surgió en clase: una skill autogenerada es aquella en la que un proceso propone por sí mismo qué skill crear. No es lo mismo que usar el skill creator, que es una skill que te ayuda a vos a crear una skill. Un alumno compartió una práctica que tienen en su equipo: iterar las skills con humanos y proponer mejoras periódicamente (los viernes), como un update en el repositorio. A nivel organización, lo recomendable es un registry de skills compartidas y actualizadas, con owners por skill.

Qué contiene una skill y cómo se descubre

Una skill suele tener un nombre y una descripción, un procedimiento paso a paso (qué hacer, en qué orden, con qué ramas), los criterios a aplicar en cada paso y el formato de salida. Se la puede pensar como una especificación de entrada y salida, o con una imagen que se usa mucho: como compilar un programa en el que el LLM es el compilador. La “sintaxis” es el Markdown que escribiste; que el programa funcione depende de lo bien que hayas especificado formatos, criterios y pasos, cosa que muchas veces no es evidente. Y una consecuencia práctica: las tools se usan mejor dentro de skills, que dan el protocolo completo de cómo usarlas, interpretarlas y combinarlas.

¿Cómo sabe un agente qué skill usar? Agentes como Claude o Codex tienen en su configuración la lista de skills disponibles y una herramienta para buscarlas. El repositorio del proyecto suele incluir las skills y archivos como CLAUDE.md o AGENTS.md que indican qué buscar, cuándo y cómo. Se pueden agregar marketplaces de skills, aunque el docente no lo recomienda demasiado porque pueden ser vía de ataques. En Claude podés pedirle que liste sus skills (hay, por ejemplo, una de code review) y ver cuándo las usa; escribiendo “/” aparece la lista.

13\. System prompt, tool, skill y MCP: cada cosa en su lugar

Estos cuatro conceptos se confunden seguido, así que vale la pena tenerlos bien separados.

El system prompt son instrucciones fijas, siempre presentes en el contexto, del lado del sistema; no son específicas de ninguna conversación. Va ahí lo que tiene que estar siempre: seguridad, estilo general, idioma de respuesta. Los productos comerciales tienen además system prompts que uno no ve ni puede modificar. Hay filtraciones públicas que muestran que son larguísimos: incluyen qué pedidos rechazar, cómo usar y llamar tools, cómo responder en cada caso, la “constitución” ética y lo que llaman el soul, la personalidad más íntima del modelo. Si usás un modelo open source y armás tu sistema, el system prompt lo definís vos.

Una tool es una función empaquetada para que la llame el modelo. El modelo la consume a través de su descripción y sus esquemas de entrada y salida, no del código. Puede corresponder casi uno a uno con una función de Python, pero lo que el modelo ve es esa especificación.

Una skill es un documento que especifica cómo resolver o ejecutar una tarea: una especie de programa, pero para el LLM. Va ahí un procedimiento relativamente estandarizado. Es, en cierto sentido, un “súper prompt guardado con herramientas”, con la diferencia de que no está siempre en el contexto (eso sería el system prompt) sino que se invoca para la tarea que corresponde.

El MCP es un protocolo para ofrecer tools desde un lugar hacia otro: una capa que organiza las tools para que los agentes las llamen desde otra máquina o desde la misma. Es como un repositorio centralizado de tools. Va ahí lo que necesita estar disponible desde distintos lugares.

14\. Los tipos de memoria de un agente

Otra forma de ordenar todo esto es pensar en tipos de memoria, una clasificación que viene de las ciencias cognitivas.

La memoria semántica es el conocimiento del dominio: toda la documentación (en el caso de riesgo crediticio, en qué consiste, cómo se trata, qué penalizaciones hay). Se implementa con lo que siempre llamamos RAG: recuperar de la base de datos y la documentación lo que haga falta.

La memoria episódica es la novedad: la memoria que el agente mismo va actualizando a medida que se lo usa. Si cada vez que usás la skill de riesgo crediticio le decís “me escribiste demasiado largo, poneme primero los indicadores”, el agente puede concluir, por reflexión, que al usuario le gusta ese formato y anotarlo. Si borró tu base de datos sin querer y te enojaste, puede anotar que se equivocó y qué debería haber hecho. Cualquier cosa que sirva como experiencia de aprendizaje puede ir ahí. En la práctica suele estar segmentada en pequeños archivos de aprendizajes que se leen según su relevancia; así funciona en Claude.

La memoria procedural son las habilidades: las skills. Se pueden escribir a mano o, en diseños más agénticos, el propio agente puede identificar una habilidad nueva y escribir o modificar sus skills (las autogeneradas, con los riesgos que vimos).

Y hay una cuarta, la memoria de trabajo o de progreso: el estado de una tarea en curso, que vive en un changelog o en un espacio de tracking.

El ejercicio final pone todo en práctica: “respondé en castellano” va al system prompt; un “procedimiento de ocho pasos para un informe comparado semanal” es una skill; “consultar el índice de normas” es una tool (o, visto como memoria, memoria semántica de recuperación); “la usuaria prefiere respuestas cortas, lo dijo hace tres semanas” es memoria episódica, porque es algo que el agente aprendió solo; y “la tarea quedó por la mitad cuando se cortó la sesión” es memoria de trabajo o progreso.

15\. Servidores, APIs y MCP

Para cerrar se repasó la infraestructura mínima. Un servidor es una computadora corriendo cosas; el modelo puede correr o no en la misma máquina desde la que lo consultás. Una API es una interfaz para llamar a un programa desde otro programa: una URL a la que le pedís algo y te lo devuelve, típicamente como JSON, sin generar una página web. Un alumno la describió como un contrato intermedio entre servicios, por ejemplo entre el front y el back de una aplicación.

El MCP es básicamente lo mismo que una API, pero hecho para que lo llamen agentes. Tiene herramientas para listar las tools disponibles y leer la descripción de cada una (nombre, input, output, descripción), y con eso el modelo sabe llamarlas. Igual que una API, tiene una URL y requiere autenticación. El ejemplo: un proveedor de alimentos que le vende a muchas dietéticas podría ofrecer un servidor MCP con información sobre sus productos.

¿Cuándo conviene MCP y cuándo una llamada directa? Como casi todo en ingeniería, depende. Si tenés un agente y algunos endpoints propios, puede alcanzar con HTTP directo a la API (que además tiene su documentación, por ejemplo en Swagger). Pero armar un MCP implica una capa de desarrollo por encima de la API, y esa capa se justifica cuando necesitás centralizar varias APIs en una sola tool (por ejemplo, traer las transacciones de un usuario de todas las instituciones bancarias, cada una con su propia API), cuando hay varias tools y muchos usuarios. Por eso en las empresas tiene sentido tener uno o varios servidores MCP que abstraen qué API se llama internamente. Un alumno lo resumió bien: el MCP le sirve al LLM un menú de todo lo que puede hacer; con una llamada directa, el LLM tiene que aprender a construir la llamada leyendo la documentación.

16\. Herramientas en uso y el TP

En una encuesta informal sobre herramientas aparecieron Cursor (que permite elegir modelos, se parece a VS Code y deja ver los diffs y aceptarlos o no; útil, por ejemplo, al modificar modelos de dbt), Claude Code y Codex (que también se pueden usar en la terminal dentro de VS Code), Devin y DeepSeek elegidos por costo, y OpenCode, que a diferencia de Cursor permite usar cualquier modelo, incluso autohosteados. También se comentaron las funciones de control remoto desde el celular y los harness propios manejados por Telegram, Slack o WhatsApp; las integraciones oficiales de WhatsApp tienen restricciones y costos, y hay integraciones no oficiales que funcionan bien para uso personal.

Sobre el TP, la indicación fue que sea un MVP efectivo, cuanto más cerca de producción mejor: un MCP corriendo localmente con datos reales está bien, y una plataforma no es costosa de levantar en un sitio web. Hay que evitar la sobreingeniería y la sobreambición: es muy fácil ahora sumar features, pero eso no es lo que más aporta. Mejor una primera versión sólida, prolija y bien scopeada. Quedó como tarea hacer la práctica de patrones pendiente y probar crear una skill.

Ideas para llevarse

Diseñar un sistema agéntico es diseñar un grafo y decidir, nodo por nodo, cuánta autonomía darle al modelo. La regla de oro es empezar por lo más simple: si algo se puede hacer de forma determinística, se hace así; si alcanza una llamada, no hace falta un agente; si se pueden escribir los pasos, alcanza un workflow; y solo cuando el camino no se puede prever pero el objetivo es claro y verificable, tiene sentido un loop agéntico. Cada paso extra en una cadena compone errores y engorda el contexto, así que la autonomía tiene costos concretos.

Lo que hace bueno a un agente no es tanto el modelo como lo que lo rodea: tools bien diseñadas, documentadas y sincronizadas (el análogo de los datos en ML), skills curadas con el conocimiento implícito del dominio, límites duros que no dependan de la buena voluntad del modelo, y prácticas de ingeniería de software (idempotencia, caché, permisos) que los modelos no implementan solos. Y cuando un problema se puede formular con datos y una función objetivo, la bitter lesson sugiere entrenar un modelo en vez de seguir agregando capas de juicio con LLMs.