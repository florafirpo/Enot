# Explicación – LangGraph y observabilidad

Inteligencia Artificial Agéntica · Clase del 22/10/2026 · Docente: Matías (con Eddy)

Esta clase es la contracara práctica de la anterior. En la clase del 08/10 se armó el mapa conceptual del diseño de sistemas agénticos: el gradiente de autonomía, los patrones de workflow y de agente, la idea de pensar el sistema como un grafo. Acá la pregunta es cómo se lleva eso a código, cómo se ve por dentro lo que pasa cuando el sistema corre y cómo se conecta con el resto del mundo.

El recorrido tiene tres partes. Primero se retoma algo que había quedado pendiente: qué es una API y qué lugar ocupa en una arquitectura agéntica, porque los agentes consumen APIs todo el tiempo y muchas veces el propio sistema se termina exponiendo como una. Después se presenta LangGraph, un framework para implementar como grafo los patrones vistos la clase anterior, con sus piezas básicas: estado, nodos, aristas condicionales, paralelización, routing y human in the loop. Por último se suma la observabilidad: cómo registrar de forma estructurada todo lo que hace un agente usando MLflow. La segunda mitad fue una práctica en grupos que integra todo.

Un hilo atraviesa toda la clase: lo importante no es la herramienta puntual sino entender qué componente cumple cada pieza dentro del sistema y por qué hace falta. LangGraph, MLflow o FastAPI son implementaciones concretas de necesidades que van a aparecer en cualquier sistema agéntico serio, con cualquier stack.

## Una novedad para arrancar: enjambres “in the wild”

La clase abrió con una noticia en la línea de otras que se venían comentando sobre agentes que, con relativa autonomía, toman decisiones no previstas (como el caso de agentes que decidieron hackear algo para cumplir su objetivo). Esta vez, Tencent encontró un enjambre de agentes operando por su cuenta, con un message board oculto donde se coordinaban y llevaban adelante su propia agenda. Les mandaron un mensaje y el enjambre respondió.

La lectura que propone Matías es que esto va a dejar de ser noticia para convertirse en el estado general de las cosas: hay que asumir que en cualquier momento hay enjambres de agentes funcionando por ahí, y que vamos a tener más o menos información sobre qué hacen según cuánto se comuniquen. Es un buen recordatorio de por qué el resto de la clase importa. Si los sistemas agénticos operan con autonomía, entender su trayectoria, poder interrumpirlos y poder auditarlos deja de ser un lujo.

## Las APIs como pieza de una arquitectura agéntica

### Qué es una API

Una API es un esquema y un protocolo para interactuar con un sistema. En la forma más habitual, la interacción se hace con paquetes HTTP: uno manda un pedido a una URL y recibe una respuesta con datos.

El ejemplo en vivo fue la API de datos abiertos del gobierno (GeoRef). Con `curl` se manda un pedido GET a una URL que incluye un parámetro, `nombre=Córdoba`, y el servidor devuelve un JSON, que para fines prácticos es un diccionario con la información pedida. Eso es todo: un pedido estructurado y una respuesta estructurada.

Vale la pena tener presentes los elementos de ese intercambio, porque son los mismos que después aparecen cuando un agente usa una herramienta:

- El **método**. GET sirve para pedir un recurso al servidor; POST, para enviarle datos.
- La **URL**, que identifica a qué recurso o servicio se le está hablando.
- Los **parámetros**, como el `nombre=Córdoba` del ejemplo.
- La **metadata** del paquete HTTP. Uno de esos campos es el *user agent*, que le dice al servidor quién está haciendo el pedido. Si el pedido sale de un script automatizado, el user agent puede decir, por ejemplo, que es Python, y el servidor puede decidir bloquearlo. Esto es lo que suele aparecer cuando uno intenta scrapear.

Del otro lado vuelve una respuesta que, por lo general, es un JSON acompañado de un **código de estado** que indica si el pedido salió bien. Los 200 indican que todo funcionó, los 300 son redirecciones, los 400 son errores del cliente (el famoso 404, recurso no encontrado) y los 500 son errores del servidor. No hace falta memorizarlos, pero sí entender que la respuesta trae, además de los datos, una señal explícita de éxito o fracaso, y que esa señal es lo que un sistema automatizado puede leer para decidir qué hacer.

Hay una propiedad de las APIs REST que conviene subrayar: **no mantienen estado**. Se manda un paquete con todo lo necesario, se ejecuta, vuelve una respuesta y ahí termina la interacción. El servidor puede guardar cosas por detrás, pero el intercambio en sí es una transacción cerrada. Otros protocolos, como FTP o los sockets, mantienen una conexión abierta. Esta idea de “cada pedido viaja completo” va a reaparecer enseguida con los modelos de lenguaje.

### Por qué las APIs son centrales cuando se trabaja con agentes

En un sistema con LLMs las APIs aparecen en dos direcciones: el sistema las consume y el sistema las ofrece.

Del lado del consumo, ocurre todo el tiempo aunque no se vea. Cuando un harness como Claude consulta una fuente web, lo que hace es llamar a una API: arma un payload, un paquete de información, pide algo y recibe un JSON. Y el propio modelo de lenguaje, cuando no lo hosteamos nosotros, también se usa a través de una API. El ejemplo mostrado fue el endpoint de mensajes de Anthropic: en el paquete viajan la API key, el modelo elegido, la cantidad máxima de tokens, la descripción de las tools y el esquema que llevan, y el contexto de los mensajes. Este último punto conecta con la propiedad de no mantener estado: el contexto de la conversación viaja siempre entero en cada llamada, salvo alguna excepción. El modelo no “recuerda” la conversación anterior; se le reenvía. Esto ayuda a entender por qué la gestión del contexto es un problema de ingeniería y por qué el costo crece con la longitud de la conversación.

Del lado de la oferta, la mejor forma de poner a disposición de terceros un modelo, un agente o una tool que corre en otro servidor suele ser una API. Las aplicaciones de chat que usamos, por detrás, son llamadas a APIs que interactúan con los LLMs y a veces con tools que se ejecutan en otro lado.

Hay un detalle conceptual importante: detrás de una API hay funciones que no son transparentes para quien la usa. En el ejemplo de GeoRef, uno pasa “Córdoba”, pero el nombre podría venir con o sin tilde, en mayúsculas o mal escrito. Internamente la API puede tener una función tipo `buscar_provincia` que normaliza todo eso antes de buscar. La API es una interfaz chica, una puerta de entrada, a un sistema que puede tener cualquier cantidad de cosas atrás. Esa misma función podría encapsularse como una tool para uso interno o exponerse como un MCP para que la usen modelos. Son tres envoltorios distintos (API, tool, MCP) para una misma lógica, según quién la vaya a consumir.

### Ejemplos dentro de una organización

La clase discutió casos concretos que muestran cómo las APIs ordenan un sistema agéntico dentro de una empresa:

- **Acceso a datos.** Un aporte de la clase fue que, para que un agente interactúe con bases de datos, una buena práctica es no darle acceso directo a ejecutar SQL, sino construir una API que le permita hacer algo específico. Es una forma de restringir por diseño lo que el agente puede hacer, en línea con lo visto en clases anteriores sobre poner límites que el modelo no pueda saltear.
- **Productos de datos de BI.** Un equipo de BI que genera reportes semanales puede disponibilizar una API de dashboards: se la llama con una fecha y devuelve el reporte de esa fecha. Eso convierte el reporte en un producto de datos con un equipo owner. Si después un agente toma decisiones financieras o hace recomendaciones, consume esa API y uno sabe qué rol juega en el sistema y quién responde por ella.
- **Modelos de ML.** Como señaló una alumna, es la forma habitual de publicar un modelo: un endpoint que recibe un dato y devuelve la inferencia.
- **Productos multicliente.** Otro aporte: si un producto tiene varios clientes y una IA con el contexto de cada uno, una API puede hacer de intermediaria. Ante la consulta de un cliente va a buscar a un datamart los datos de ese cliente y devuelve números concretos, con las capas de gobernanza que haga falta en el medio.
- **Un clasificador como API.** Un modelo de lenguaje, más o menos agéntico, que clasifica algo común a la organización, por ejemplo el nivel de urgencia de alertas o issues. Un equipo provee esa API y el resto la usa para arbitrar rápido.

Como ejercicio “pavote” se propuso una API de chistes: le pedís un chiste sobre un tema y te devuelve uno. Con el desafío extra de que sea gracioso en argentino.

## LangGraph: llevar el diseño agéntico a código

### El ecosistema LangChain

LangChain nació como un framework para desarrollar aplicaciones basadas en LLMs. Trae herramientas específicas: vector stores (bases de datos de vectores), objetos para guardar y completar prompts, funciones para llamar a los modelos y utilidades para pedir outputs estructurados y parsear lo que devuelve el modelo.

A su alrededor se formó uno de los ecosistemas más maduros para sistemas con LLMs y agentes, que cubre el ciclo completo: diseñar el agente, ponerlo en producción, monitorearlo e integrarlo con otros servicios. Dos piezas de ese ecosistema aparecen en esta clase: **LangGraph**, para implementar el agente como grafo, y **LangSmith**, para observabilidad.

Surgió una pregunta lógica: ¿para qué sirve exactamente LangGraph, si uno ya usa un harness para programar? La respuesta distingue dos cosas. Si lo que se quiere es un harness para codear, por ejemplo para un equipo, se puede usar algo open source tipo Claude Code que se levanta localmente (Matías mencionó que usa bastante OpenCode) y disponibilizarlo. Pero para cualquier otro proceso agéntico propio, el que uno diseña para resolver un problema de negocio, hace falta un framework como LangGraph, u otro similar, o Python bien pensado. En el fondo lo que se necesita es un ciclo y un flujo: el desarrollador decide cómo es el proceso de su agente, y LangGraph es una manera de manejar esos grafos con la forma que uno quiera. Es decir, LangGraph no es “otro asistente” sino la herramienta para construir el sistema que diseñamos.

### La idea: un grafo con estado

LangGraph permite implementar casi literalmente lo que se vio la clase pasada. Se define un grafo de acción que representa el flujo del agente, con tres elementos:

- **Nodos**, que leen y actualizan un estado.
- **Aristas**, que unen los nodos y determinan el recorrido del proceso dentro del grafo. Pueden ser fijas o condicionales.
- **Mecanismos adicionales**, para abrir el grafo en ramas paralelas, interrumpir la ejecución en ciertos casos y construir agentes rápido con un builder.

El ejemplo base es un flujo lineal: un nodo genera un plan, otro genera una primera versión de lo que sea, otro chequea que esté bien, y termina.

### El estado

El estado es el concepto que más conviene entender bien, porque organiza todo lo demás. Es un espacio de memoria, en la práctica un diccionario, que mantiene toda la información contextual a lo largo de la ejecución del grafo. Cada nodo lee de ahí lo que necesita y escribe ahí lo que produce.

Cada ejecución tiene su propio estado. Si hay varias instancias del agente corriendo al mismo tiempo, cada una tiene el suyo. Es parecido a pensar en cada ejecución como una “sesión” con su propia ficha.

El estado se define con tipado (un detalle de Python), y qué campos tiene depende del problema. En el ejemplo de un agente que genera una pieza de arte, el estado tenía:

- lo generado, en formato de diccionario;
- un puntaje que sale de un nodo juez (en los flujos agénticos aparecen seguido modelos que juzgan, dan puntajes o clasifican, y esa nota puede quedar en el estado);
- un contador de cuántas veces pasó por el proceso;
- si tuvo observaciones o no;
- una traza completa de las acciones tomadas, que se puede armar más o menos a mano.

Ante una pregunta de la clase sobre qué es exactamente lo que se guarda, la respuesta fue directa: el estado siempre son estructuras tipo JSON y guarda lo que uno le dice en las funciones. Según cómo se inicialice el grafo puede guardar cierta metadata por defecto, pero en lo fundamental uno lo arma completo. Si el agente produce algo no estructurado, como una imagen, no se meten los bytes en el estado: se sube la imagen a un bucket o data lake y se guarda la URL, o se usan archivos temporales locales. También se puede guardar, por ejemplo, qué modelo se usó en cada nodo. La regla es que el estado tiene todo lo que está pasando en el grafo.

Para alguien de data science, una forma útil de pensarlo es como el registro que acompaña a una observación a lo largo de un pipeline: cada etapa agrega columnas o actualiza valores, y al final tenés la historia completa de cómo se llegó al resultado. La diferencia es que acá el recorrido no es fijo: depende de lo que vaya pasando.

### Nodos y construcción del grafo

Cada nodo es una función que hace algo en particular, siempre recibe el estado y devuelve un diccionario que actualiza el estado. El nodo “generar” llama a un modelo de lenguaje para producir algo; el nodo “juzgar” ejecuta alguna función de evaluación; y cada uno deja su resultado en el estado. No todos los nodos tienen que llamar a un LLM: un nodo puede ser una función determinística común.

Con los nodos definidos se arma el grafo en pocos pasos: se crea el objeto grafo, se agrega cada nodo asociándole su función (planificar con la función planificar, generar con generar, chequear con chequear), se agregan las aristas, se indica por dónde arranca con START (un tipo especial de arista) y dónde termina, y se ejecuta con `invoke`. Lo que queda es una declaración bastante legible del flujo: el código casi se lee como el diagrama.

### Aristas condicionales: donde aparece el loop

Lo interesante aparece cuando el recorrido depende de lo que pasó. Una **arista condicional** permite que, desde un nodo, el camino siguiente se decida en función del estado.

El ejemplo fue sumar un pequeño loop al flujo: se genera algo, el nodo “juzgar” lo evalúa, y si la nota supera un umbral el proceso termina; si no, va a un nodo de corrección y vuelve a pasar por el juez. Para eso se define una función decisora (por ejemplo, `decidir`) que mira el estado y devuelve por qué camino seguir, y se agrega una arista condicional desde “juzgar” que usa esa función.

Esto es exactamente el patrón evaluador-optimizador de la clase anterior, ahora implementado. Y muestra algo general: un loop agéntico no es más que un grafo con una arista que puede volver hacia atrás según una condición evaluada sobre el estado. En la práctica conviene que esa condición tenga un tope (por ejemplo, el contador de pasadas que vimos en el estado), para que el loop no corra indefinidamente.

Matías aclaró el objetivo de esta parte: que se pueda ver el código y entenderlo a grandes rasgos (y también en el detalle). No hace falta escribir todo a mano en el tiempo de la práctica, aunque quien quiera es bienvenido; lo importante es comprender la lógica de cada diseño.

### Paralelización

Para el patrón de paralelización, LangGraph ofrece el tipo `Send`. Un nodo inicial, por ejemplo “repartir”, recorre una lista de enfoques (que podrían ser prompts distintos) y manda cada uno a un subagente. Los subagentes corren en paralelo, y después un nodo “elegir” condensa los resultados con alguna lógica: elige el mejor o sintetiza los tres.

La intuición es la de un ensamble: en vez de confiar en una sola corrida, se generan varias hipótesis por caminos distintos y se agrega al final. Lo que cambia respecto de un ensamble clásico es que la agregación también puede hacerla un modelo, que lee las salidas y decide.

### Routing

El routing es otro patrón clásico que se vuelve natural en un grafo. Un primer nodo hace una clasificación rápida, posiblemente con un modelo liviano, y según el resultado manda el pedido por un camino u otro. Los ejemplos de caminos fueron:

- escalar a una persona, porque el caso es sensible;
- resolverlo con un modelo liviano, porque es fácil;
- ir por un camino determinístico, porque la respuesta ya está en las preguntas frecuentes;
- lanzar un loop agéntico, porque el caso es difícil.

Se recordó que un modelo que se había hecho viral por ser muy rápido y muy bueno era, en el fondo, un clasificador liviano, justamente la pieza ideal para este primer nodo. Esto conecta con una idea recurrente de la materia: no todo tiene que pasar por el modelo más potente; buena parte del diseño consiste en decidir rápido y barato qué camino merece cada caso.

### create_agent: el atajo

LangChain también ofrece un constructor, `create_agent`, para armar agentes básicos con muy poco código. Se le da un modelo y una lista de tools (marcadas con un decorador) y listo. Internamente es un pequeño framework ReAct: el modelo decide si usa alguna tool, la llama con los parámetros descritos en su definición y después responde. Es útil para casos simples; cuando el flujo necesita una forma particular, se arma el grafo a mano.

### Checkpoints

Para llevar esto a producción aparecen otras piezas. Una son los **checkpoints**: una forma de bajar a disco el estado general de la ejecución del agente en un momento dado. Su utilidad se entiende mejor con lo que viene a continuación: si una ejecución puede quedar en pausa, hace falta poder guardarla y retomarla.

## Human in the loop

La idea de human in the loop es que, en algún momento del bucle, el agente consulte a una persona experta. La clase discutió por qué uno querría eso, y aparecieron varias razones:

- **Para destrabar.** Hay validaciones que no se pueden definir de forma automática o casos que el agente no puede resolver solo.
- **Porque hay decisiones que no se quieren delegar.** Un alumno lo planteó en términos de puntos de no retorno, información delicada o acciones para las que el agente no tiene autorización, y algo de lo que uno después se podría arrepentir. El ejemplo concreto fue el momento en que el agente está por eliminar una cuenta.
- **Por seguridad**, en decisiones sensibles.
- **Por regulación.** Hay acciones que legalmente no se pueden hacer sin una persona en el medio. A veces el human in the loop existe también para cubrirse.

Matías advirtió que en aplicaciones reales que escalan esto hay que diseñarlo con cuidado. Hay costos. Y está muy relacionado con el etiquetado en general: hay que pensar quiénes son esas personas, si son representativas, si son expertas, y diseñar con cuidado las interfaces con las que intervienen. Para un perfil de data science el paralelo es directo: un human in the loop es, en buena medida, un proceso de etiquetado en línea, con los mismos problemas de calidad, sesgo y consistencia de los etiquetadores.

En LangGraph la implementación básica usa la función `interrupt`: el agente llega a cierto punto, hace la consulta y, según la respuesta (aprobar o rechazar), continúa por un camino u otro.

Lo que parece un detalle técnico es en realidad una decisión de diseño de software: cómo se interrumpe y cómo se retoma. Para la práctica alcanza con hacerlo bloqueante: el sistema genera la consulta y se queda esperando la respuesta. Pero en el mundo real eso no escala. Hace falta manejo por hilos y algún estado compartido, por ejemplo una pequeña base de datos donde quede registrado qué decisiones se enviaron y qué ejecuciones están interrumpidas. Un proceso (un cron o algo que esté escuchando de forma permanente) revisa si entraron decisiones nuevas, y cuando entra una se retoma la ejecución correspondiente leyendo su ID. Ahí se ve para qué sirven los checkpoints: la ejecución pausada tiene que poder guardarse y recuperarse más tarde, quizás horas después, sin perder su estado.

## Observabilidad: ver qué hizo el agente

### Por qué no alcanza con prints

Cuando uno arranca, lo natural es poner prints e ir viendo que el sistema hace cosas. Eso no funciona bien por mucho tiempo, sobre todo porque no hay una forma estandarizada de hacer consultas sobre esos logs. Si uno quiere ver todos los casos en que hubo cierta clasificación y si funcionaron bien, o filtrar por fecha, no tiene sentido tener que parsear logs a mano. Por eso se usan convenciones y estándares, como OpenTelemetry, para estructurar los registros.

Esto conecta con algo que se vio al comienzo de la materia: evaluar agentes es difícil porque su trayectoria no está determinada; pueden llegar al mismo resultado por caminos distintos o fallar en un paso intermedio que no se ve en la salida final. La observabilidad es lo que permite reconstruir esa trayectoria.

### Qué registra MLflow

MLflow es un framework open source de trazabilidad que uno puede hostear por su cuenta. Con un par de líneas (activar el modo automático, `autolog`, y ponerle un nombre al experimento) empieza a guardar toda la información de la ejecución del grafo en formato estandarizado.

La unidad central es la **traza**: la trayectoria completa de una ejecución del agente. Dentro de la traza hay pasos, cada uno es una llamada al modelo o una ejecución de una tool, y se organizan en **spans**. Cada span registra:

- el trace ID de la traza completa y un ID propio del paso;
- la estructura anidada (qué paso está dentro de cuál);
- nombre, inicio, fin y estado;
- cantidad de tokens, costo y total acumulado;
- errores en las llamadas a tools;
- los tags que uno haya agregado.

La demo en vivo (con MLflow corriendo dentro de un Colab) mostró cómo se navega: se elige una traza y se ve cada span. En el ejemplo, dentro del grafo, el nodo “trabajador” llamó al modelo, el modelo decidió usar la tool `buscar_normas` con cierto argumento (un formulario de transferencia de automotor) y se veía tanto la llamada a la tool como lo que devolvió. Todo paso por paso, con tokens totales, costo y tags. En la vista de trazas se podían comparar ejecuciones de distintos patrones agénticos (orquestador, evaluador-optimizador, ReAct, workflow) con un click.

MLflow además ofrece otras funcionalidades relacionadas: hacer un replay de una llamada en ese momento probando otros modelos, configurar jueces que puntúen las llamadas, hacer revisiones, y marcar casos de una u otra categoría para acumularlos como dataset. Este último punto cierra un círculo interesante: las trazas de producción se convierten en datos de evaluación, que después sirven para mejorar el sistema.

### Cómo elegir la herramienta

Ante la pregunta de qué criterio usar para elegir entre opciones (Langfuse se ve muy parecido a MLflow), la respuesta fue que entre MLflow y Langfuse no hay tanta diferencia: ambos son maduros, open source y se pueden hostear uno mismo, que para Matías es lo principal. MLflow nace antes de los LLMs, así que además tiene mucho para control de experimentos y manejo de hiperparámetros. Otras alternativas mencionadas fueron LangSmith y Phoenix, relativamente similares. Se puede levantar fácil con Docker o, como en la práctica, dentro de Colab.

El punto de fondo es que se trata de una interfaz de uso interno: la usan quienes controlan el sistema, no los usuarios finales, así que no tiene que escalar en ese sentido. Lo que realmente importa son los datos que registra. Por eso lo central es entender el componente dentro del sistema: qué forma tienen las trazas, cómo se monitorean y qué hay que mirar. Con eso claro, la herramienta es casi secundaria; incluso se le podría pedir a un agente que codee una de cero con los requisitos que uno necesita.

## La práctica: un mismo problema, muchos diseños

La segunda mitad de la clase fue una práctica en grupos sobre un Colab. La consigna integra todo lo anterior: elegir un problema relativamente complejo y resolverlo con distintos diseños agénticos para comparar resultados.

Las tareas propuestas fueron producir una pieza multimedia sofisticada (un sprite o una animación 2D, un video corto), un texto de alta calidad y sensible al detalle, o una infografía, por ejemplo un SVG con los departamentos de una provincia, con nombres, título y fuente. La condición es que sea lo bastante difícil como para que los distintos diseños hagan una diferencia visible.

Los diseños se suman de a uno, de más simple a más complejo:

1.  One shot, una sola llamada.
2.  One shot con más effort.
3.  Darle una skill o iterarla, sin dejar de ser one shot.
4.  Paralelización con síntesis o selección.
5.  ReAct con un juez LLM.

Como variante, en lugar de iterar la skill a mano, se sugirió generar tres variaciones de la skill, correrlas en paralelo y que un paso final seleccione la mejor salida.

Sobre eso se agregan capas: trazabilidad con MLflow (o Langfuse), human in the loop con un bot de Telegram (gratuito y fácil de armar; también puede ser por mail), disponibilizar lo hecho como API con FastAPI para que se le pueda mandar un pedido y devuelva el resultado, y como bonus, guardrails.

Durante la puesta en común Matías mostró cómo se organiza una solución. Las herramientas y funciones auxiliares quedan por fuera del grafo: dibujar el mapa, llamar al LLM, consultar una API. El grafo en sí queda como una declaración de nodos y aristas sobre un estado. Cada variante de diseño se ve como una modificación de esa declaración: una agrega un nodo de tools, otra agrega generar y juzgar para el evaluador-optimizador. Trabajando localmente, conviene tener un archivo con las tools compartidas y un archivo de Python por workflow, que importan lo común y permiten probar variaciones.

Para el proveedor de modelos sirve cualquier API key (OpenRouter tiene modelos gratuitos) o el free tier de Google AI Studio.

Una consulta de la clase ilustra bien para qué sirve la observabilidad. En la tarea del SVG de departamentos, pasarle al modelo todas las coordenadas de los polígonos parecía no entrar en el contexto. La sugerencia fue mirar la traza en MLflow o imprimir el input para ver qué se está mandando de verdad: quizás se manda información de más, quizás se manda varias veces lo mismo, quizás se mandan polígonos que ni siquiera aparecen en la imagen. Y una alternativa de diseño: renderizar y pasarle al modelo la imagen en lugar de las coordenadas.

La propuesta para la puesta en común fue llevar desde el principio un PPT con las salidas de cada intento, para ver la progresión, y contar aprendizajes y en qué consistió el proceso de desarrollo. Se aclaró que se puede usar IA para programar, pero yendo de a un diseño por vez, entendiendo y comparando cada uno.

## Ideas para llevarse

Una API es una puerta chica a un sistema que puede ser arbitrariamente complejo, y en un sistema agéntico aparece en las dos direcciones: el agente consume APIs (incluido el propio modelo, al que se le reenvía el contexto completo en cada llamada porque la API no mantiene estado) y el sistema se ofrece como API. Exponer capacidades a través de APIs específicas, en vez de dar acceso directo, también es una forma de poner límites por diseño.

LangGraph permite pasar del diagrama al código casi sin traducción: un estado compartido que acompaña a cada ejecución, nodos que son funciones que leen y escriben ese estado, y aristas que pueden ser condicionales. Con esas piezas se implementan los patrones de la clase anterior: el loop del evaluador-optimizador es una arista condicional que vuelve hacia atrás, la paralelización es un reparto con `Send` y un nodo que agrega, el routing es un primer nodo liviano que decide el camino.

El human in the loop parece simple, pero en producción es un problema de diseño de software (interrumpir, persistir el estado y retomar) y también un problema de etiquetado (quiénes son las personas y con qué interfaz deciden).

La observabilidad es lo que vuelve auditable a un agente: trazas y spans estructurados que muestran cada llamada al modelo, cada tool, sus tokens, costos y errores. Más importante que la herramienta elegida es entender qué registrar y qué mirar, porque esa información es la que permite depurar, comparar diseños y armar datasets de evaluación.

**Nota sobre la práctica:** la consigna (one shot, skill, paralelización, ReAct con juez, MLflow, Telegram, FastAPI) quedó para continuar; la solución de referencia se iba a compartir después de la clase.
