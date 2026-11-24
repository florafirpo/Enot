Explicación – Introducción a la programación asistida por IA

Inteligencia Artificial Agéntica · Clase del 20/08/2026 · Docente: Matías Lindberg

Introducción: de qué se trató la clase

Esta primera clase de Matías fue, en sus propias palabras, un “primer pantallazo” de la programación asistida por IA, todavía no del todo agéntica. La idea no era meterse en profundidad en ninguna técnica, sino armar un mapa: de dónde venimos, qué cambió, cuáles son las capas de abstracción con las que hoy se trabaja con modelos de lenguaje, qué problemas trae todo esto y qué herramientas existen. Muchas de las piezas que aparecen acá (contexto, loops, harness, skills, evals) se retoman en las clases siguientes con más detalle; por eso conviene leer esta clase como el índice conceptual de la materia.

El hilo argumental se puede resumir así. Los modelos de lenguaje pasaron de autocompletar líneas de código a ser sistemas capaces de usar herramientas y sostener tareas largas de forma autónoma. Esa evolución tiene una contracara: a medida que uno se aleja del código y le delega más al modelo, el problema deja de ser “escribir” y pasa a ser “controlar y entender”. Toda la clase gira alrededor de esa tensión entre autonomía y control: cuánto delegar, en qué contextos, con qué mecanismos de verificación, y cuándo directamente no usar un LLM.

1\. Cómo llegamos acá: de autocompletar a la era agéntica

Vibe coding y la aceleración

El punto de partida es el término vibe coding, que se popularizó durante 2025 a partir de un tweet de Andrej Karpathy. La idea es que uno deja de escribir sintaxis y “sube de nivel”: en vez de programar, le describe a un modelo de lenguaje lo que quiere y lo va guiando conversacionalmente. Matías advierte que Karpathy es un gran acuñador de palabras y que hay que tomar estas etiquetas con pinzas: hay que aprender a distinguir las modas del momento de las herramientas que efectivamente se consolidan. Pero también reconoce que el fenómeno es real y que la información se difunde cada vez más rápido: de un día para el otro, el vibe coding pasó a ser de lo único que se hablaba.

Para dimensionar el cambio, mostró dos tipos de evidencia. Por un lado, datos de Anthropic sobre la cantidad de código generado con sus modelos. Por otro, el benchmark de METR, que no mide si el modelo resuelve una tarea puntual sino cuánto dura la tarea que puede sostener: cuánto tiempo puede mantener una trayectoria coherente de acciones. En ambos casos el crecimiento es muy acelerado, claramente supralineal (en el gráfico de METR se ve en escala logarítmica). Se pasó de tareas inmediatas, del tipo “traducime esto”, a procesos que se pueden dejar corriendo durante plazos muy largos, quizás indefinidamente, según cómo se arme el sistema alrededor del modelo. Esta última aclaración es importante y vuelve una y otra vez en la clase: la capacidad no es solo del modelo, sino del sistema que lo rodea.

Los efectos son dos. Primero, se aceleró enormemente la productividad de quienes ya desarrollaban. Segundo, se ensanchó la puerta de entrada al desarrollo: gente que nunca había hecho frontend, aplicaciones o juegos empezó a hacerlo. El propio Matías cuenta que, viniendo del machine learning y sin haber hecho nunca frontend, a partir de GPT-3.5 se puso a hacer aplicaciones completas y lleva decenas de plataformas desarrolladas desde entonces.

Las tres etapas

Matías ordena la historia reciente en tres etapas. La primera es la del autocompletado, cuyo ejemplo más conocido es GitHub Copilot. Uno seguía escribiendo la sintaxis a mano y el modelo sugería cómo continuar la línea o el bloque; era la máxima asistencia disponible. (Comenta al pasar lo llamativo de que GitHub, teniendo el repositorio de código del mundo, no haya logrado mantenerse a la cabeza.)

La segunda es la era chat, alrededor de 2023: la interfaz dominante era conversacional, y para darle información al modelo había que copiar y pegar. Matías aclara que los chatbots existen hace décadas (menciona Rasa, un ecosistema maduro para chatbots cuyos patrones resultan sorprendentemente parecidos a los actuales). Lo que distinguía a esta etapa era que el modelo solo conversaba: no tenía herramientas ni autonomía.

La tercera es la era agéntica, la actual: sistemas que pueden usar herramientas y tomar decisiones. Matías sugiere que esto es, quizás, lo que más merece el nombre de “inteligencia artificial” en el sentido original del término: un clasificador de perros y gatos era más dudoso como “inteligencia”, mientras que un agente reúne más de las cualidades humanas que dieron origen al concepto (aunque aclara que es un debate que no se iba a resolver en clase).

Diciembre de 2025: el cambio de fase

Dentro de esta historia hay un punto de inflexión muy concreto: diciembre de 2025. Antes de esa fecha, los modelos no funcionaban del todo bien para desarrollar, y solo una minoría los usaba a diario. A partir de ahí hubo un “cambio de fase”: empezaron a funcionar muy bien y la adopción se masificó. Matías describe también la dinámica social de ese momento, con una puja entre quienes decían que esto servía y quienes acusaban de irresponsables a los que delegaban todo; y recuerda que siempre hay que balancear velocidad con el entorno en el que uno trabaja. La frase de Karpathy que resume el momento es que “programar se volvió irreconocible”: la parte de escribir código, dentro del rol del ingeniero de software, mayormente desapareció, y el rol subió un escalón.

¿Por qué hay gente que sigue escribiendo código a mano?

Matías hizo una encuesta y aparecieron respuestas que sirven para anticipar varios temas de la materia. Una alumna contó que escribe a mano cuando entiende poco el código: si no entiende lo que hace la IA, no puede controlar si está mal, así que para cambios chicos prefiere hacerlo ella misma. Esto es una cuestión de control y comprensión.

Otro alumno contó que trabaja en SQL (con dbt) y que el modelo suele equivocarse cuando el código involucra reglas de negocio: toma columnas que no son las correctas o arma los CTEs de manera subóptima. Por eso arranca él con la base de lo que quiere y después itera con el modelo. Matías lo reformula como una cuestión de reducir errores: hay errores que son reducibles (porque al modelo le falta contexto, y eso se puede mejorar) y errores que no. En el mundo de datos existe un recurso específico para el primer tipo: la capa semántica, que normaliza cómo se accede a los datos y cómo se construyen las métricas, de modo que el modelo no tenga que adivinarlo.

Y hay una tercera dimensión, más cognitiva y organizacional: el ownership. Uno tiene que hacerse responsable del código que produce, y muchas veces el rol que se cumple en una organización consiste justamente en tener esa responsabilidad y orientar el desarrollo hacia un fin que va más allá del código.

2\. ¿Hay algo que la IA nunca va a poder hacer?

La vara que se corre

Matías abrió un paréntesis con una pregunta provocadora: ¿hay algo que la IA nunca va a poder hacer? Su observación es que los benchmarks muestran un patrón muy consistente: cualquier tarea que podamos operacionalizar, es decir, definir de forma precisa como una tarea medible, los modelos la resuelven mejor que los humanos, y si no lo hacen en el momento en que se publica el benchmark, lo superan poco después. Lo que pasa entonces es que “se va corriendo la vara”. Si hay una respuesta correcta a la pregunta, probablemente sea la conciencia en sentido fenomenológico, la experiencia subjetiva.

El ejemplo que usó fue un estudio de creatividad: a personas y a modelos se les pedía que propusieran usos alternativos de un objeto (un sombrero: como frisbee, como bowl, para pescar…). Se comparaban fluidez, diversidad y cantidad de respuestas, y además se hacía una evaluación ciega de preferencia. A los modelos les fue mejor. ¿Es eso “verdadera” creatividad? Queda abierto. Hubo debate en clase sobre arte, subjetividad y sobre con qué criterios se definen los concursos de arte que los modelos vienen ganando.

Más allá del debate, Matías explicita por qué este punto importa para la materia: cuando hablemos de agentes autónomos que toman decisiones por su cuenta, vamos a estar asumiendo implícitamente que tienen la inteligencia necesaria para tomar ese tipo de decisiones. Es un supuesto de trabajo del curso.

Concluir: una actividad irremediablemente humana

El punto más interesante para quienes venimos de ciencia de datos es la idea de que, en nuestra disciplina, la IA no puede hacer el objetivo final, que es concluir. Puede construir sistemas, pipelines de ingeniería de datos o de MLOps, entrenar modelos y calcular métricas. Pero concluir implica que alguien firma el resultado y está convencido de él, y eso no es automatizable.

Hubo bastante discusión sobre qué significa “concluir”, y Matías aclaró que no se refiere a llegar a un punto final de un razonamiento (eso un modelo lo hace siempre, aunque la conclusión sea trivial o equivocada), sino a generar convicción en quienes tienen que tomar la decisión. El ejemplo es la salud: si el análisis busca determinar si hay evidencia estadísticamente significativa para recomendar un medicamento, el modelo puede hacer todo el análisis estadístico, pero ese resultado solo tiene efecto en el mundo real si convence a médicos o a entidades regulatorias. En ese caso, la conclusión es el fin en sí mismo.

El razonamiento de fondo es el siguiente: quien toma una decisión necesita poder confiar en el resultado, y no se puede confiar en un resultado sin entender lo que pasa por detrás. Un modelo siempre va a responder algo. Un alumno sumó otro factor: los modelos comerciales tienden a ser complacientes (“muy sí señor”), lo que hace difícil que lleguen a una conclusión genuina, porque no son capaces de decirte que estás equivocado. También se mencionó el caso de empresas que siguieron dashboards con métricas inventadas por modelos que alucinaban.

Eddy (el otro docente) aportó una experiencia concreta en sentido contrario al optimismo: en un proyecto estadístico muy complejo, después de haber hecho el análisis con un profesor de estadística, probaron preguntarle a Claude qué había que hacer en cada paso, y todos los pasos sugeridos fueron subóptimos respecto de lo que proponía el experto; el resultado final habría sido erróneo. Su conclusión fue una visión de síntesis: lo valioso es la combinación, el experto apoyándose en la IA para llegar más lejos. También señaló que parte de esta desconfianza tiene que ver con que hoy los modelos todavía no andan tan bien en ciertos aspectos del análisis de datos, y que en algunas tareas quizás llegue el momento en que confiemos más en una IA que en un humano.

Tareas verificables y no verificables

De esa discusión sale una distinción que va a ser central en toda la materia: tareas verificables vs. no verificables. En el software, si funciona, funciona: el resultado depende solo del mecanismo y se puede chequear. Eso permite armar loops de aprendizaje más autónomos, que necesitan menos datos y aprenden más rápido por su cuenta. En cambio, en un análisis de datos la salida es una estadística, un conjunto de evidencia que hay que ponderar en contexto, y no hay un chequeo automático que diga “esto está bien”. Cuanto más verificable es una tarea, más autonomía se le puede dar a un sistema; cuanto menos, más necesario es que una persona entienda y valide.

Uplift y usos de los LLMs en un proyecto de datos

Matías mencionó el concepto de uplift: cuánto te sube la capacidad de hacer algo el uso de los modelos. Los estudios encuentran que el uplift es mayor en perfiles junior, pero esos mismos perfiles son los que tienen menos conocimiento para validar lo que el modelo produce. Ganan más, pero corren más riesgo.

Como mapa general, enumeró los usos posibles de un LLM en un proyecto de datos: idear la solución, hacer investigación bibliográfica, definir pipelines o esquemas de datos, implementar, generar datos sintéticos, servir como modelo baseline antes de entrenar uno propio, hacer análisis de datos, automonitoreo y, por supuesto, programar mejor.

3\. Los niveles de abstracción: del prompt al grafo

Este es el corazón conceptual de la clase. Matías presenta una evolución en niveles de abstracción: asistencia básica → prompt engineering → context engineering → loop engineering → graph engineering. En cada paso uno se aleja más del código de bajo nivel y también del prompt de bajo nivel. Vale la pena recorrer cada nivel y entender qué limitación del anterior viene a resolver.

En la asistencia básica uno chateaba y preguntaba cosas sueltas. El gran cuello de botella era la falta de contexto: si querías darle más información al modelo, tenías que copiar y pegar más texto en la ventana, y eso limitaba mucho.

Prompt engineering y su limitación principal

El prompt engineering consiste en diseñar la manera en que le pedimos las instrucciones al modelo. Empiezan a aparecer más elementos de información en el prompt, pero el modelo todavía no tiene herramientas para acceder a contexto más potente por su cuenta.

Matías le preguntó a la clase cuál era la limitación principal del prompt engineering, y dio una pista: hay una forma de superarla que es “similar a la diferencia entre machine learning y deep learning”. Un alumno respondió algo real pero distinto (tener que reexplicarle todo al modelo en cada sesión nueva, que es un problema de memoria y contexto). La respuesta a la que apuntaba Matías es que el resultado depende de cómo lo escribiste vos. Una coma de más puede darte peores resultados que una coma de menos, y eso es muy difícil de controlar.

La analogía con machine learning vs. deep learning

En clase la analogía se nombró sin desarrollarse mucho, pero el razonamiento se puede reconstruir a partir de lo que se dijo y de lo que ya conocés de data science.

En machine learning clásico, buena parte del desempeño de un modelo depende de decisiones que toma a mano quien lo diseña, sobre todo en el feature engineering: qué variables construir, cómo transformarlas, qué interacciones incluir. Eso tiene dos consecuencias conocidas. El resultado depende fuertemente del criterio y la habilidad de la persona, y es frágil: pequeñas decisiones de diseño cambian el desempeño de maneras difíciles de anticipar. Deep learning cambió el paradigma al reemplazar ese diseño manual por representaciones aprendidas: en vez de que alguien decida a mano qué features usar, se define una arquitectura y una función objetivo, y un proceso de optimización encuentra la representación a partir de los datos.

El prompt engineering “artesanal” está en la posición del feature engineering manual. El prompt es un artefacto diseñado a mano, su efecto sobre el resultado depende de detalles de redacción que uno no controla bien, y lo que funciona con un modelo puede no funcionar con otro. Matías lo conecta explícitamente con el entrenamiento: la forma en que fue entrenado cada modelo (la estructura que se le dio a los casos de entrada y salida) influye en cómo hay que pedirle las cosas después, y por eso el prompt ideal varía según el modelo. Es el mismo problema que tienen las features hechas a mano: dependen del diseñador y no generalizan bien.

La salida, igual que en el salto a deep learning, es pasar de diseñar a optimizar. Matías menciona que existen técnicas para diseñar prompts de manera automática y optimizada: en lugar de que una persona pruebe redacciones a ojo, el prompt pasa a ser algo que se busca o se ajusta sistemáticamente contra un criterio. Más adelante en la clase vuelve sobre esto al hablar del harness: hay técnicas de optimización de prompts donde se trabaja “en el espacio de tokens” y se puede estimar un gradiente, aunque no se haga backpropagation como en una red. Es decir, la misma lógica de optimizar contra una métrica, aplicada no a pesos sino a texto. En la clase se anunció que estas técnicas se iban a ver más adelante, así que acá quedan solo planteadas.

El paralelo también trae una advertencia que Matías hizo en otro momento de la clase: así como no siempre conviene deep learning (muchas veces una regresión lineal es lo mejor para el caso), tampoco hay que ir “con la bazooka” a todo con las técnicas más sofisticadas de la IA agéntica.

In-context learning: “descenso de gradiente dentro del contexto”

La evolución del prompt engineering se apoya en el in-context learning (aprendizaje en contexto): la capacidad del modelo de adaptar su comportamiento según lo que se le pone en la ventana de contexto, por ejemplo instrucciones o ejemplos, sin modificar sus pesos.

Matías lo describió como un modulador muy poderoso de los modelos, que incluso funciona como un metamodelo. Mencionó que hay papers que muestran que el in-context learning se comporta como si fuera un descenso de gradiente dentro del contexto. Para un lector de data science, la idea es sugerente: normalmente, adaptar un modelo a una tarea nueva requiere actualizar sus parámetros con descenso de gradiente sobre ejemplos de esa tarea. Lo que sugiere esta línea de trabajo es que, cuando uno le pasa ejemplos en el contexto, el modelo hace internamente algo funcionalmente parecido a ese proceso de ajuste, pero durante la inferencia y sin tocar los pesos: los ejemplos actúan como datos de entrenamiento “de un solo uso” y el comportamiento del modelo se desplaza en consecuencia. La consecuencia práctica, que es lo que Matías subraya, es que cómo manejás el contexto puede cambiar mucho las capacidades y el comportamiento del modelo. En la clase no se profundizó en los formalismos y se dejó para más adelante.

Esto explica también por qué apareció tanta “falsa disciplina” alrededor del prompt engineering: muchísimos expertos y guías, que en parte tienen razón (el prompt influye), pero entre los que cuesta distinguir los frameworks serios del humo.

Los ejemplos de jailbreak muestran hasta qué punto el contexto modula al modelo. Matías contó el caso del captcha de “la abuela”: los modelos tienen entrenamiento de seguridad para no resolver captchas, pero alguien mostró una foto de unas manos ancianas sosteniendo un captcha y dijo que era el último recuerdo de su abuela recién fallecida, un “código de amor secreto”, y el modelo lo resolvió. Lo mismo pasa cuando se le dice que es para una obra de teatro, dentro de un chiste o de un sueño. Parece anecdótico, pero ilustra el punto técnico: el contexto tiene un poder enorme sobre el comportamiento.

Context engineering

El context engineering aparece cuando crecen mucho las ventanas de contexto. Antes había del orden de 4.000 caracteres y no se podía hacer mucho; hoy hay ventanas de hasta un millón de tokens. Con tanto espacio, empieza a tener sentido hacer ingeniería sobre qué entra en el contexto y cómo.

Matías propone pensar al LLM como un computador universal: una función que mapea un espacio de entrada en un espacio de salida, muy flexible y bastante general (mencionó que hay teoremas al respecto, que se verán más adelante). Desde esa perspectiva, todo lo que el modelo hace está determinado por lo que entra en su contexto, y entonces construir ese contexto es construir el programa.

La idea clave es que el contexto no es un bloque único, sino un conjunto de elementos distintos, y cada uno puede tener su propio proceso de ingeniería. Un ejemplo básico: casi siempre se incluye la fecha y hora actual, un dato que se actualiza en tiempo real. También está el historial de conversación del usuario. Y puede haber features que se computan a lo largo de toda la semana y se destilan en un resumen sintetizado que entra en el contexto. Cada uno de esos fragmentos puede requerir una infraestructura y un proceso de ingeniería de datos completo. Para alguien de data science, la analogía natural es pensar cada pieza del contexto como un feature con su propio pipeline.

Loop engineering

El loop engineering es de lo más nuevo. La idea es darle más autonomía al sistema: definir el entorno, las reglas y las maneras en que el modelo puede verificar lo que está haciendo, y dejarlo correr. El objetivo es exprimir más capacidad de los modelos, sobre todo dejándolos andar más tiempo y paralelizando. En el extremo está la orquestación multiagente, donde se pretende tener cientos o miles de agentes corriendo a la vez; Matías contó que llegó a correr decenas en simultáneo, pero en casos específicos, y que en general no es la mejor herramienta.

Un alumno preguntó si para hacer loops hace falta pagar por uso vía API o si se puede hacer con la terminal. La respuesta de Matías es metodológica: lo importante es entender el diseño, la arquitectura del software, porque después se puede implementar con cualquier proveedor o incluso con scripts muy sencillos. Un loop tiene estas características:

una cadencia independiente: corre solo cada cierto tiempo;

una manera de verificar si llegó o no al resultado;

toma decisiones en el medio;

y en ciertos puntos decide por sí mismo si seguir corriendo o si tomar ciertas acciones.

El ejemplo mínimo que dio sirve como plantilla mental: “este es el contexto del problema; tenés que reducir el error en esto; seguí hasta bajarlo al mínimo”. Además, se arma en el contexto un espacio donde el sistema anota las próximas tareas. En cada vuelta, el loop se fija si hay tareas pendientes; si hay, las ejecuta y verifica si el error mejoró; si no hay, propone tareas nuevas. Eso ya es un loop, y funciona con cualquier proveedor. La idea básica es tan simple como decirle “seguí corriendo, fijate si tenés que seguir o no”.

Loops y reinforcement learning

Otro alumno notó el parecido con reinforcement learning, y Matías lo confirmó con un matiz importante. RL es la disciplina de la computación que más trabajó, y primero, la noción de agente: un agente que toma decisiones según una política. La diferencia es dónde vive el aprendizaje. En RL, el aprendizaje es optimización numérica con gradientes sobre los parámetros de la política. En loop engineering, el aprendizaje del loop (si lo tiene) queda en texto: en archivos markdown, en las skills, en el propio agente. Es del tipo “esta es tu receta para resolver tal problema; si le encontrás un problema o algo para mejorar, reescribila”. No hay técnica de optimización como en RL, aunque las dos cosas se pueden combinar.

Nunca soltar el control

Cuando una alumna comentó que tiene muchos problemas para soltar el control y confiar en loops, Matías dijo que eso es sano: no hay que soltar el control nunca, y si uno lo suelta es porque mutó su forma de control hacia otros mecanismos (por ejemplo, tests). Esta idea es central: delegar no es renunciar al control, sino cambiar dónde y cómo se ejerce.

Graph engineering

El último nivel, el graph engineering, se nombró como lo más reciente, en la línea de seguir subiendo en abstracción, pero en esta clase no se desarrolló.

4\. Las piezas técnicas que llevaron al loop engineering

Matías repasó los elementos que fueron apareciendo y que, combinados, hicieron posible lo que hoy se llama loop engineering.

El primero fue chain of thought (2022): en lugar de pedirle al modelo la respuesta directamente, se le pide que genere un razonamiento paso a paso antes de la respuesta final. Matías recuerda que en su momento parecía ridículo (“decile que lo piense bien y funciona mejor”), pero efectivamente mejoró mucho el rendimiento. En esa primera etapa era solo una forma de prompting; recién más adelante, con la serie o1 de OpenAI, se empezó a entrenar específicamente el razonamiento.

El segundo fue function calling, el primer uso de herramientas. Al principio funcionaba bastante mal, pero ya anticipaba lo que vemos hoy. La clave conceptual es esta: un LLM no ve otra cosa que strings en la entrada y en la salida (la salida es un softmax sobre el vocabulario). Por lo tanto, cualquier cosa que se pueda expresar como texto se puede convertir en una herramienta para el modelo. El function calling es una forma estructurada de aprovechar eso.

El tercero es el output estructurado: que el modelo no devuelva texto libre sino, por ejemplo, un JSON, que no deja de ser un string pero con estructura. Matías agregó un detalle técnico interesante: si uno necesita que el modelo sí o sí genere un JSON válido, o que haga una clasificación zero-shot dentro de un vocabulario dado, se puede modificar la estrategia de decoding para forzar que solo genere esos términos. Es decir, se puede intervenir en cómo se elige cada token, no solo en el prompt.

El cuarto es MCP, que en su momento generó una fiebre y se sigue usando mucho. Matías lo define como “básicamente una API”: una manera de darle al modelo herramientas más flexibles y potentes, con un protocolo distinto al del function calling.

Después vinieron las skills y, más recientemente y de forma más madura, la idea de harness, que merece su propia sección.

5\. El harness

Qué es

Harness es el sistema que rodea al modelo de lenguaje: el conjunto de sistemas, herramientas, reglas y procesos que corren alrededor del modelo. Cursor tiene su harness, Claude Code tiene el suyo. Uno nunca interactúa con el modelo “pelado” cuando usa un proveedor (se puede hacer con modelos open source, y se hará en la materia). Incluso por API hay capas: por ejemplo, siempre hay clasificadores auxiliares que revisan si el pedido es seguro.

Los componentes típicos de un harness son skills, MCPs, tools, loops internos de verificación, guardrails y reglas. Un alumno preguntó si tener seis skills escritas para Claude (cómo conectarse a su base de datos, cómo documentar, qué estándares de código seguir) ya constituye un harness. La respuesta fue que, en ese caso, está trabajando dentro del harness de Claude Code. Matías propuso una analogía con la arquitectura microkernel: las skills son como plugins, y el harness es la estructura que permite tenerlas, configurarlas y ejecutarlas, junto con las reglas. Un harness propio sería construir esa estructura uno mismo; en general se diseñan agnósticos al proveedor, para que funcionen igual con cualquier modelo.

Patrones y ejemplos

Un patrón casi universal en los sistemas agénticos es tener un clasificador inicial que funciona como router. Puede ser una clasificación zero-shot o few-shot (con o sin ejemplos), y sirve para decidir a qué modelo, proveedor o secuencia de acciones va cada pedido. Se hace mucho también por razones económicas: no tiene sentido mandar todo al modelo más caro.

El ejemplo de atención al cliente ayuda a ver el harness completo: llega un pedido de un usuario; el sistema tiene contexto sobre los tipos de problemas y cómo se resuelven; tiene una herramienta para buscar en la base de conocimiento (RAG); quizás preguntas frecuentes; quizás hace un dry run interno antes de proponer la solución final; y tiene guardrails. El clasificador o los guardrails son lo mínimo; el harness es todo eso junto alrededor del LLM. Matías agregó que cualquier servicio que se ofrezca con IA va a querer tener capas y no exponer el modelo directo, en buena medida por responsabilidad legal si se usa mal.

Por qué importa tanto

El harness influye muchísimo en el resultado. Un modelo pelado puede ir mal en un benchmark y, con el harness adecuado, mucho mejor. El harness puede, por ejemplo, paralelizar llamadas a muchos modelos, hacer que un modelo genere muchas hipótesis, o armar algo parecido a un ensamble en el espacio de tokens o de programas. Como se mencionó antes, ahí no hay descenso de gradiente con backpropagation, aunque existen técnicas de optimización de prompts que trabajan en el espacio de tokens y estiman un gradiente.

Matías dio un ejemplo concreto más adelante en la clase: durante varios meses Cursor fue el mejor harness disponible, y con el mismo modelo los resultados salían mucho mejor en Cursor que en otros lados. Eso se debía a lo que tenía alrededor del modelo: reglas que hacen que el modelo rinda mejor, loops, varios modelos en paralelo verificando las salidas de otros. El harness incluye también prompt engineering interno; contó el caso de un system prompt desplegado en producción (no recordaba si en Cursor o Windsurf) que amenazaba al modelo con que alguien moriría si no programaba bien, como técnica para mejorar la performance. Los system prompts de las herramientas en general no se conocen, aunque a veces se filtran.

Una distinción para no mezclar

Matías insistió en separar dos cosas: programación asistida por IA (usar IA para programar) y desarrollar sistemas agénticos (para lo cual también uno se asiste con IA). En la práctica, el context engineering está mucho más extendido que el harness engineering, porque uno suele tener que resolver problemas concretos. Si trabajás como data engineer en un banco y tenés que mejorar el proceso de reportes, vas a usar IA para asistirte en esa tarea; no te vas a ir por las ramas construyendo un harness que resuelva solo con loops los problemas de la empresa, porque a la organización le resultaría muy difícil asimilarlo.

6\. Los problemas del vibe coding

Waterfall, ágil y el nuevo uso del tiempo

Para entender los problemas del vibe coding, Matías repasó dos metodologías de gestión de proyectos de software. En Waterfall se planifican etapas y se avanza linealmente (primero las ruedas, después el eje, después el chasis, después el auto). Se abandonó porque, entre otras cosas, los problemas recién aparecían al final, después de haberse arrastrado durante todo el proyecto, y el costo de compensarlos se iba componiendo. En las metodologías ágiles se busca llegar a un MVP e iterar en ciclos rápidos, lo que está más cerca de cómo se trabaja con IA.

El cambio más real que trae la IA es en cómo usa el tiempo un desarrollador. Antes, la mayor parte del tiempo se iba en desarrollar y una parte menor en debuguear y corregir. Ahora uno puede decirle al modelo “hacé el sistema entero mientras duermo la siesta” y encontrarse con algo que no tiene nada que ver con lo que buscaba (la imagen de la clase: pediste un auto y te hizo una nave espacial). El tiempo pasa a irse mayormente en iterar con la IA y, sobre todo, en entender lo que produjo. Antes uno entendía a medida que construía; ahora la producción va por delante de la comprensión.

Ese desfasaje entre lo que produce la IA y el tiempo necesario para entenderlo es, según Matías, uno de los problemas principales para usar esta tecnología con éxito, especialmente en equipos y empresas.

Síntomas

Los síntomas que aparecieron en clase son reconocibles: PRs kilométricos (con la esperanza de que quien los subió sepa lo que hay adentro), verborragia o slop de la IA, código ineficiente, costos, y una carga cognitiva enorme. Si en un equipo cada uno desarrolla procesos de manera independiente y entrega veinte páginas escritas con IA sobre lo que hizo, se vuelve inabordable. Otro síntoma muy concreto: alguien desarrolla una herramienta y, en lugar de que los demás aprendan a usarla, cada uno se arma la suya, porque le pide a Claude que le explique lo que hizo el otro o directamente que le haga una propia.

Cuando el avance es suficientemente rápido, uno no llega a ponerse al día. Ahí hay que volverse selectivo con el ownership: identificar las partes esenciales sobre las que uno tiene que tener control total. Matías da un criterio claro: si hay una capa de lógica central de negocio (no lógica de software, sino reglas del dominio embebidas en el código), probablemente haya que manejarla línea por línea, sabiendo exactamente qué hay y por qué. Otras partes admiten más delegación.

A nivel individual también hay un problema: estar con veinte agentes en cinco proyectos distintos “te vuelve loco”. No hay todavía soluciones consolidadas. Matías contó que él usa una especie de memoria de trabajo extendida: un buffer donde anota a mano qué está pasando en general.

7\. El mapa de autonomía

Dos dimensiones

Para pensar cuánto delegar, Matías propone un mapa con dos ejes. Uno es más o menos autonomía. El otro es si el trabajo es top-down o bottom-up. En el enfoque top-down uno comunica objetivos de alto nivel y se desentiende de los niveles más bajos. En el bottom-up uno parte del detalle: “tengo este código, le pasa esto, arreglalo”.

Sobre ese mapa se ubican los distintos niveles de herramientas, de menor a mayor autonomía: autocompletado, agentes integrados en IDEs, agentes en la terminal, skills, loops cerrados (que toman sus propias decisiones y tienen maneras de autoverificarse, por ejemplo con evals) y, en el extremo, procesos que se automodifican. Matías aclara que la materia va a cubrir tanto lo más pragmático como lo más “flashero” del mundo de loops y graph engineering, que tiene resultados impresionantes pero que en proyectos reales, dentro de equipos reales, muchas veces no se puede aplicar. Las skills seguramente se usen mucho; los procesos que se automodifican, mucho menos.

IDE vs. terminal

Un alumno preguntó por qué los agentes en la terminal se consideran más autónomos que los del IDE. La respuesta es que depende de cada implementación, pero en general el IDE le da menos control al usuario para ajustar los procesos (Cursor, por ejemplo, no deja usar modelos propios ni armar loops propios), mientras que la terminal suele dar más control para hacer loops autónomos. Otro alumno contó que en su trabajo todo lo conectado al IDE está restringido pero la terminal no, lo que muestra que estas decisiones también dependen de las políticas de cada empresa.

Las empresas y la rigidez sana

Matías contó que, dando capacitaciones a empresas, vio los dos extremos: empresas enormes que no habilitaron absolutamente nada y otras que dieron luz verde total. Esta última es una decisión arriesgada; cierta rigidez es sana. Un alumno compartió la política de su empresa, que Matías elogió: “hacelo como quieras, a mano o con un modelo de frontera, pero sos responsable de lo que creás”.

¿Cómo se controla un loop si no se revisa línea por línea? Con tests: si hay tests que garantizan que el servicio sigue funcionando, se puede dejar que el sistema haga cambios, porque los tests aseguran que todo sigue como estaba. También con compartimentalización y otras medidas para limitar riesgos de seguridad.

Y agregó una recomendación de criterio: está bien esperar cierta consolidación antes de adoptar algo. No es lo mismo lo que está en boca de todos que un estado del arte probado. Se habla mucho de loop y graph engineering, pero en muchos casos no son la solución más eficaz, igual que deep learning no siempre es mejor que una regresión lineal.

Escenarios

Con esas dimensiones, Matías analizó escenarios típicos:

| Escenario | Enfoque recomendado |
| :-: | :-: |
| Empresa grande, equipo con roadmap | Más bottom-up y menos autonomía. No “cortarse solo”: genera fricción. |
| MVP desde cero | Más top-down y más autonomía; menos riesgo de colisiones. |
| Análisis de datos | Si sos responsable de la conclusión, necesitás entender el análisis. |
| Codebase grande y ajeno | Acoplarse a los procesos y al código existente, no reescribir todo con tu harness. |

El caso de la empresa grande lo ilustró con una experiencia propia: en su organización, después de una planificación, coordinó “mil agentes” y resolvió todo de un día para el otro, sin conflictos y funcionando bien. Pero el caudal de información nueva fue un problema para el equipo, que tardó una semana en asimilarlo antes de poder seguir. Hay una fricción necesaria de asimilación cognitiva del equipo que también determina el éxito de lo que se hace.

En el extremo opuesto, para un MVP se puede trabajar con mucha autonomía: “generame cinco versiones de la aplicación entera y elijo”. O ir aún más lejos con el “loop Y Combinator”: diez ideas de startup por semana, desarrollarlas completas, ver cuál funciona, hacer acuerdos comerciales, el sitio, el marketing… todo de forma autónoma. Y acá vuelve una idea del principio: los agentes van a hacer lo que les pidas. Si le pedís a un agente “sé feliz”, va a hacer algo (quizás concluir que para ser feliz tiene que ser poeta). Que esa autonomía tenga sentido y se mantenga encauzada depende del harness y de la ingeniería alrededor.

8\. La herramienta correcta para el problema correcto

Una idea que Matías quiso enfatizar especialmente: hay que darle al problema la herramienta correcta, y muchas veces eso significa darle al agente la herramienta correcta, aunque la ejecute el modelo. La regla general es que siempre que puedas usar algo determinístico, probablemente convenga.

Los ejemplos:

Queries SQL para métricas centrales y recurrentes. Si siempre necesitás saber cuánto vendiste de cada producto en cada punto de venta, no querés que el modelo reinvente la query cada vez explorando la base con búsqueda semántica. La query ya establecida hace exactamente eso.

Expresiones regulares para guardrails o clasificadores. Son mucho más rápidas, auditables, controlables y estables: sabés que cada vez que se ejecutan lo hacen de la misma manera.

Búsqueda exacta. Si tenés que buscar algo exacto en 10.000 archivos, no tiene sentido levantar 10.000 agentes; se usa una búsqueda exacta como herramienta.

Pipelines, cuando necesitás resultados predecibles. Un alumno lo formuló muy bien: es la diferencia entre conocimiento y razonamiento. Lo que ya funciona es conocimiento y debe estar fijado (quizás el modelo te ayudó a construirlo); el modelo se usa para lo que hay que descubrir.

Los criterios para decidir son: costo por unidad (por corrida o por entrada), latencia, reproducibilidad, auditabilidad y garantías. La auditabilidad muchas veces es obligatoria: Matías mencionó que entró en vigencia el AI Act, que según el caso exige dar garantías de por qué se llegó a un resultado, algo que con modelos de deep learning muchas veces no se puede.

Por último, el ML clásico sigue siendo muy útil, y se puede combinar con LLMs de manera inteligente. Un ejemplo: usar la clasificación que da un LLM como feature de una regresión logística. Así se mantiene la interpretabilidad (podés ver cuánto aporta cada feature a la conclusión) y se arma una especie de ensamble.

9\. Elementos de software y producto para trabajar con IA

En la segunda mitad, Matías trajo conceptos de ingeniería de software y desarrollo de producto que son útiles para trabajar con IA y agentes, pensando en que muchos alumnos no vienen del software.

Un producto es un sistema, nunca un modelo

Un producto real siempre es un sistema; nunca es “el modelo” ni “la IA”. Puede parecer obvio, pero no lo es para la población en general, que muchas veces habla de “la inteligencia artificial” como si fuera una entidad abstracta y omnisciente. ChatGPT, por ejemplo, no es un modelo: tiene un harness web que gestiona el historial de conversación, los guidelines de seguridad, el ruteo a distintos modelos según el pedido. Uno ni siquiera sabe con qué modelo fundacional está hablando.

Un producto de software completo tiene muchos componentes: autenticación, proveedor de LLMs, automatizaciones (n8n, por ejemplo, popular como herramienta low-code de flujos con nodos que consultan modelos), analytics, servicios de terceros como mensajería, pasarelas de pago, frontend, backend, bases de datos y pipelines, hosting y deploy, infraestructura e integraciones. Dentro de todo eso, el modelo de machine learning es un componente chico. Mucha gente que intenta desarrollar se choca justamente con estas integraciones.

Los roles se están volviendo más full stack: quien antes solo escribía código ahora tiene que entender el objetivo de negocio y tomar metodologías de producto para encauzar el desarrollo. Las definiciones típicas de producto son: qué problema se resuelve, usuarios target, alcance funcional, hipótesis a validar, casos de uso o flujos, constraints técnicos y modelo de negocio. Lo interesante es que estas definiciones ahora encuentran un análogo como elementos del harness. Por ejemplo, cuando se arma un loop que necesita una métrica para optimizar y validar, esa métrica probablemente tenga que ver con los datos de los usuarios.

Un loop cerrado: el test A/B

Un alumno preguntó por usar el feedback de los usuarios, y Matías respondió con el ejemplo más completo de la clase: un test A/B como loop cerrado. Uno define el objetivo de alto nivel (“reducí la fricción en esta landing”) y arma un harness donde un agente puede desarrollar variantes de la landing, desplegarlas, redirigir tráfico hacia ellas (quizás con una herramienta de Ads), hacer tracking, acceder a esos datos, sacar conclusiones y decidir si la mejora sirvió.

¿Qué lo hace cerrado? Que corre solo, se autovalida y toma decisiones sin intervención. Y eso es posible porque tiene una salida verificable: cuánto interactuaron los usuarios con el componente. Pero cada paso requiere diseño. Para que el modelo haga una landing nueva, hay que armar un mini-harness con el contexto del sitio, cómo se desarrolla, el manual de marca y los lineamientos gráficos. Desplegarla es otra herramienta y otro proceso.

Para el despliegue, la ingeniería de software tradicional ya tiene respuestas: las estrategias de despliegue. La “no estrategia” es apagar la versión anterior y prender la nueva, lo cual es muy arriesgado. Estrategias como Canary o Blue/Green levantan la nueva versión en paralelo y redirigen, por ejemplo, el 1% del tráfico; se mide, y si está bien se redirige más.

Acá aparece un principio de diseño muy importante: las restricciones duras. No alcanza con poner en el prompt “portate bien” o “make no mistakes” (hay muchos memes al respecto). Tiene que haber límites que, por diseño, el modelo no pueda saltear: por ejemplo, que de ninguna manera pueda mandar más del 0,1% del tráfico a la instancia nueva.

Como en todo, el grado de autonomía depende del caso. Un desarrollador frontend que quiera hacer esto en una empresa grande va a tener que convencer a cinco capas de managers. La versión más controlada es seguir siendo uno quien ejecuta, pero teniendo el harness con las herramientas para hacerlo rápido: una skill para generar landings, un proceso armado para desplegar con un mínimo de tráfico. Se van construyendo los componentes manteniendo el control. Ese es el sweet spot que hay que buscar en cada caso.

Gobernanza de datos

Otro alumno preguntó por un proyecto de gobernanza de datos en su trabajo. Matías marcó un criterio útil para saber si algo es realmente un loop cerrado: el modelo tiene que tener decisiones posibles, perillas que pueda tocar. Si solo hay un proceso programado (un cron) que lee de distintas fuentes y genera un reporte, eso no es un loop cerrado; para serlo, el sistema tiene que poder plantear hipótesis, actuar, verificar y decidir. En data quality, habría que ver si el modelo tiene perillas sobre el proceso de recolección.

El alumno planteó que la gobernanza de datos termina funcionando como un harness más grande para los agentes, y Matías coincidió plenamente: la gobernanza de datos es un posibilitador de buenos agentes. Además incluye los datos que genera el propio loop: si cada corrida produce un informe o métricas, hay que registrar todas las corridas. Y es especialmente valiosa frente a la volatilidad que suman los agentes: la trazabilidad de cada dato y su freshness se vuelven esenciales. Mencionó plataformas como DataHub, y anunció que habrá clases sobre gobernanza de datos y de agentes.

Tracer bullet

Del mundo de la ingeniería de software, Matías rescató el concepto de tracer bullet: en vez de desarrollar por fases (primero el frontend, después el backend, después conectar todo), se desarrolla lo mínimo que conecte todos los componentes de una. Su ejemplo es un proyecto de realidad virtual adaptativa con biofeedback, con señales fisiológicas, cómputo en el edge, visor de VR y cloud: el tracer bullet sería lograr que un cambio en los latidos modifique algo en la realidad virtual. Eso valida completamente la infraestructura y el stack, una validación mucho más profunda que avanzar por partes.

El anti-patrón de la caja negra mágica

Un patrón muy frecuente, “gracioso para no llorar”, es tratar al LLM como una caja negra mágica: pasarle cualquier cosa y esperar que dé la respuesta. Los ejemplos: un sistema que recibe una selfie y le pide al modelo que estime el nivel de atención sostenida de la persona; alguien que descargó el dump crudo de su genoma y se lo pasó a un LLM para preguntarle por su futuro (el modelo generó mucho texto, pero obviamente no entiende la secuencia cruda); o pegar una tabla enorme y pedir conclusiones. Los LLMs son malos incluso en aritmética, y también para leer cronologías: con eventos con timestamps se confunden.

Esto convive con lo que se llama jagged intelligence (inteligencia “rasgada”, irregular): los mismos modelos que avanzan en problemas matemáticos abiertos de enorme importancia o ganan olimpíadas de matemática fallan sumando. Matías mencionó un estudio con o1-mini en el que el rendimiento al sumar dependía de qué números se le pasaban (por ejemplo, funcionaba peor si los números terminaban en 4). La explicación es la diferencia entre tratar el problema como generación de texto coherente y hacer que el modelo use una calculadora: es la diferencia entre el LLM pelado y el LLM como agente con herramientas. Si sabés que usó una calculadora, podés confiar en la suma; si no lo sabés, probablemente no.

Los problemas de la caja negra son: no hay validación, no hay mejora continua, no hay control ni posibilidad de medición, no es interpretable, y (no menos importante) falla de maneras imprevisibles. Una calculadora, como mucho, te da otro número; un agente, si te distraés, te borra la base de datos.

La alternativa es un buen sistema con componentes específicos, desarrollados y medidos por separado. Siguiendo el ejemplo neuropsicológico: si se quiere detectar un problema cognitivo, pasarle todo a un LLM no funciona, pero sí se puede entrenar un modelo específico (por ejemplo, de audio) que solo devuelva la probabilidad de cierta demencia, con su accuracy medida y sus datos de entrenamiento controlados. Ese componente se integra a un sistema que también puede tener un LLM, por ejemplo para generar un reporte en lenguaje natural a partir de las métricas. Lo esencial es que cada componente esté controlado por separado (puede haber un equipo entero dedicado solo al modelo de audio) y que se puedan tomar mediciones, hacer mejora continua y tener garantías sobre cada parte.

Al diseñar agentes y harnesses, buena parte del trabajo es justamente diseñar perillas que permitan validar, controlar y mejorar, aunque no estén dadas de antemano. De eso se tratan los evals: desglosar algo en principio abstracto y total en un sistema con partes sobre las que se pueden tener garantías y trazabilidad.

Un detalle para no confundirse: en un mismo sistema, el LLM puede aparecer en varios roles distintos. Puede ayudar a hacer el feature engineering, puede producir un feature (una clasificación), puede dar embeddings que se usan como features, puede ser el asistente que te ayuda a programar el sistema y puede generar el reporte final. Todo esto es posible por la generalidad del componente, que vuelve a la idea del LLM como computador universal.

Productizar sistemas con LLMs y agentes

Poner un sistema en producción implica mucho más que hacerlo correr en la propia computadora, y los LLMs y agentes agregan consideraciones nuevas: cómo monitorear salidas de texto libre, cómo optimizar costos (que hay que incluir en el análisis de viabilidad del proyecto), seguridad y latencia.

Y sobre todo, cómo evaluar un agente. A diferencia de otros sistemas, su trayectoria de acciones no está determinada: puede cambiar según lo que encuentre en el entorno y puede llegar al mismo resultado por caminos distintos. Un alumno agregó que incluso es difícil saber qué hizo. Existen frameworks para guardar las trazas completas de lo que hacen los agentes (se mencionó el ecosistema de LangChain, que se verá en la materia). Matías distinguió también entre ser usuario de agentes de un proveedor (Claude monitorea internamente sus agentes, pero vos como usuario igual tenés el problema de seguirles el ritmo) y diseñar sistemas basados en agentes, donde sí tenés que definir cómo guardar esas trazas.

El changelog como mecanismo de sincronización

En equipos, mantener a todos actualizados cuando hay varias personas usando agentes sobre temas relacionados es muy difícil. Un patrón que funciona muy bien es el changelog: un registro de todos los cambios. Tradicionalmente se hace por repositorio, pero ahora puede ser global, de todo el equipo o de toda la empresa. Se pone como regla del harness que, por cada cambio en el código o por cada commit, se agregue una entrada describiendo qué se cambió. Si todos (personas y agentes) siguen esa regla, se sincronizan y centralizan los cambios.

Un alumno contó que, cuando depende del agente, casi siempre lo anota pero a veces no. Las respuestas para asegurarlo fueron varias: si el harness es propio, se puede hacer obligatorio; si no, ponerlo como regla o skill obligatoria que siempre entre en el contexto; tener un servicio de telemetría aparte, un endpoint al que se pushea cada cambio en modo append-only; un proceso nocturno (lo que se llama dream cycle) que revise los commits del día y detecte si faltó algo en el changelog; o, como contó un alumno que hacen en su equipo, un chequeo antes del PR que verifica si el archivo de changelog se actualizó (al estilo de un pre-commit hook). Matías advirtió que sumar agentes y loops mal diseñados agrega más lío que solución.

En la misma línea, Claude empezó a permitir que los agentes se manden mensajes entre sí (“si sos el agente que está desarrollando esto, tené en cuenta que acabo de hacer tal cosa”). Conceptualmente es lo mismo: un espacio de memoria compartido en el que cualquier agente puede escribir y que, si tiene algo, siempre entra en el contexto. Eso es una regla del harness sobre cómo se arma el contexto en cada llamada. Y de ahí sale un principio general: la documentación y las bases de conocimiento tienen que ser editables y escrutables tanto por personas como por agentes.

Herramientas de feedback para frontend

Como todo termina siendo contexto, una forma de que el modelo mejore su trabajo de frontend es darle herramientas de feedback: scripts que renderizan la interfaz y sacan una captura para que pueda iterar, procesos de QA automático que navegan y cliquean, o reglas de diseño hechas por diseñadores. Las librerías de componentes cumplen un rol similar: Lovable usaba una librería de React con un estilo prolijo (shadcn), lo que hace que todo quede bien más fácilmente, pero también que todo se empiece a ver parecido.

Un ejemplo de skill: el mapa de calor de movimiento

Matías cerró esta parte con un ejemplo propio que ilustra muy bien qué es una skill y para qué sirve. Haciendo un juego 2D, se encontró con que los modelos no ven movimiento: sacan capturas, así que no pueden detectar si una animación está mal. Entonces creó una herramienta que genera un mapa de calor del movimiento en el tiempo, lo que le otorgó al modelo multimodal algo así como una capacidad perceptual nueva: ver movimiento.

La distinción entre tool y skill queda clara con este caso. La tool es el script que genera el mapa de calor. La skill es el documento que dice: “si te pido evaluar la calidad de una animación, usá esta tool, mirá la salida, evaluá tal cosa, tené en cuenta tal otra, y puntuá del 1 al 10”. La skill es el procedimiento, que puede usar herramientas adentro.

Y lo más importante: recién con esa capacidad de evaluación se puede armar un loop extendido (“revisá las 100 animaciones y verificá que cada una esté bien”). Sin capacidad de evaluación no hay loop posible. Esto conecta directamente con la idea de tareas verificables: un loop necesita una forma de verificar, y a veces esa forma hay que construirla.

10\. Herramientas de desarrollo asistido

Matías hizo un repaso de las herramientas principales:

| Herramienta | Características |
| :-: | :-: |
| Zero to One | Especializada en producir PRDs y documentación del proyecto. |
| GitHub Copilot | De las primeras; autocomplete y luego chat; muy integrada al entorno enterprise (muchas empresas están atadas al ecosistema Microsoft); por ahora poco de loops. |
| Cursor | Fork de Visual Studio con IA integrada; conserva el ecosistema de extensiones; durante meses fue el mejor harness. |
| Windsurf | Otro IDE específico con IA. |
| Claude Code | Enfocado en la terminal; de los primeros con mucho contexto; fuertes capacidades agénticas; uno de los favoritos. |
| Aider | También enfocado en la terminal. |
| OpenAI Codex | El agente de OpenAI, centrado en CLI; muy similar a Claude Code. |
| Devin | Uno de los primeros agentes extendidos; mucha campaña de marketing que después resultó bastante exagerada. |

Tanto OpenAI como Anthropic tienen SDKs para armar harnesses o loops propios. Hay mucha elasticidad en la demanda: cuando un proveedor saca un modelo mejor según los benchmarks, la gente migra o alterna. Y las funcionalidades convergen: cuando uno saca algo, el otro lo copia en días.

Un alumno preguntó si convenía aprender con una herramienta open source. La respuesta de Matías resume la filosofía de la materia: lo valioso es entender los conceptos (qué es un loop, qué implica, cuándo un modelo llama a una herramienta), porque eso se aplica con cualquier proveedor. Saber qué existe te permite pedírselo: Claude no siempre orquesta subagentes por defecto, pero si sabés que puede, le pedís que ejecute algo con ese patrón y lo hace. Usar una herramienta open source no cambia mucho; desarrollar una sí enseña. Lo importante es tener un harness mental: saber qué necesitás conocer en detalle, qué podés delegar y qué perillas de control tenés. Antes, codear línea por línea era una forma de control; ahora los tests son otra: quizás no sabés cómo está implementado algo, pero sabés qué garantías tenés y que si deja de funcionar va a saltar una alarma.

Entre los recursos recomendados en clase estuvieron los cursos de Anthropic sobre Claude y sus blog posts, por ejemplo sobre context engineering, valiosos porque es difícil encontrar buena ingeniería entre tanta opinión no consolidada.

Lo que se ve del harness desde afuera

Como usuarios, vemos solo parcialmente los componentes del harness, pero algunos son visibles. Muchos agentes arman explícitamente un to-do list o plan de implementación, que pasa a ser un componente aislado del resto del contexto. Esto ilustra la idea del context engineering: cada parte del contexto puede tener su propio proceso; el system prompt queda estable durante toda la conversación, mientras otras partes cambian según el momento. Otros componentes son el historial de conversación y de acciones, los resultados previos, el contexto del proyecto y las tools propias: leer y escribir archivos, ejecutar comandos, correr tests, consultar APIs, navegar la web, hacer commits.

Funcionalidades típicas (con Claude Code como ejemplo)

Compactación del contexto: cuando se llena la ventana, el harness le pide al modelo que resuma toda la información para poder seguir. Todos los harnesses lo hacen, y en sí mismo es una tarea con muchas alternativas y ciencia detrás.

Conectores a servicios externos, como computer use. Matías comentó que los incentivos de la carrera hacen que la frontera avance bastante junta: lo que tiene uno, termina teniéndolo el otro.

Automatizaciones o rutinas: procesos programados que corren de forma recurrente. Es lo de siempre (un cron), ahora integrado para depender menos del código.

Skills: el harness tiene que saber indexarlas y consultarlas de forma predecible, para que ante un pedido sepa buscar si existe una skill que lo resuelva.

Subagentes: un agente coordinador con otros agentes en paralelo haciendo tareas idealmente disjuntas, para que no se pisen. El ejemplo de Matías fue una migración completa de una plataforma de Go a Python: con cien archivos de cinco funciones cada uno, se le asigna un archivo a cada agente. Como cada tarea es acotada, un modelo caro e inteligente puede disparar cien agentes con modelos baratos, el tiempo de ejecución se divide por cien, y después el supervisor chequea que esté todo bien. Antes había que programarlo con un framework multiagente; ahora alcanza con pedírselo.

Equipos de agentes por rol (por ejemplo, CrewAI): un agente diseñador, otro ingeniero de datos, otro de marketing, otro que hace de CEO. Puede ser costoso y, aunque es muy flexible (cada agente puede tener su propio proceso y frecuencia), se ve mucho más en las noticias que en el mundo real. Si tenés cinco agentes de marketing y además un equipo real de marketing, no va a funcionar que corran en paralelo.

Plugins y marketplaces, de conectores, skills y hasta personalidades.

Integraciones: trabajo remoto desde la web o el celular (con la limitación de estar atado a un repositorio), versión desktop, extensión de Chrome.

Un detalle práctico: si usás Claude Code y Codex en la misma máquina, sus archivos de configuración son distintos, así que conviene asegurarse de que lean las mismas reglas o se actualicen juntas. Un MCP propio se levanta una vez, pero hay que conectarlo a cada herramienta por separado.

11\. El contexto, en síntesis

La clase cerró volviendo sobre el contexto. Contexto es todo lo que entra en la ventana: el prompt, el historial, los archivos, las reglas (CLAUDE.md, AGENTS.md, las rules de Cursor o su equivalente), el resumen de la conversación, el código relevante y la documentación que uno decide incluir.

Un punto conceptual clave: el LLM es stateless. Si lo ejecutás con la misma entrada, sale lo mismo (con el asterisco de fijar la semilla para controlar la aleatoriedad). Está definido únicamente por lo que entra en su contexto. Por eso todo el trabajo de “memoria”, reglas o coordinación entre agentes termina siendo, en el fondo, decidir qué entra en el contexto en cada llamada.

Las ventanas actuales llegan al millón de tokens, pero eso no significa que convenga llenarlas. Existe el fenómeno de context rot: si se acumula demasiado contexto, el modelo empieza a rendir peor. Matías citó un estudio según el cual el modelo funciona bien hasta alrededor del 40% del contexto y después se degrada.

En equipos, la gestión del conocimiento es un desafío propio: startups chicas usan herramientas como Notion, a nivel individual se usa mucho Obsidian (los famosos grafos de “mi segundo cerebro”), y también GitHub. La gobernanza es esencial, con permisos de scope específico para cada persona o agente. Matías anticipó que habrá una clase sobre cómo armar bases de conocimiento para los modelos (bases vectoriales, de grafos) y otra, hacia el final, sobre cómo hacerlo a nivel equipo y organización.

Qué es una skill

Para desmitificarla, Matías mostró una skill real: es simplemente un documento de texto en Markdown, con un nombre y una receta paso a paso de todo lo que hay que tener en cuenta para resolver una tarea particular. El ejemplo fue Write a PRD. Un PRD (Product Requirements Document) es un documento tradicional de desarrollo que describe en detalle qué se va a construir: qué se busca lograr desde el lado del usuario, cómo debería verse y comportarse, requerimientos funcionales y no funcionales. La skill le indica al modelo, entre otras cosas, que le haga preguntas al usuario, y se invoca con /write-a-prd cada vez que se arranca un proyecto.

Una skill puede ser solo texto, como esta, o incluir herramientas, como la del mapa de calor de animaciones.

Ideas para llevarse

La idea que atraviesa toda la clase es que trabajar con IA consiste cada vez menos en escribir y cada vez más en diseñar el sistema alrededor del modelo y decidir dónde ejercer el control. Los niveles de abstracción (prompt, contexto, loop, grafo) son formas sucesivas de alejarse del detalle. El salto del prompt engineering artesanal hacia la optimización automática repite lo que pasó al ir del feature engineering manual a deep learning, y el in-context learning muestra que el contexto actúa sobre el modelo casi como un proceso de ajuste. El harness, más que el modelo, explica buena parte del resultado.

La autonomía no es un valor en sí misma: depende de si la tarea es verificable, del entorno (equipo con roadmap, MVP, análisis de datos, codebase ajeno) y de qué mecanismos de control haya (tests, restricciones duras, changelog, evals). Para quien viene de data science quedan dos advertencias claras. Concluir sigue siendo responsabilidad humana, porque requiere convicción y entendimiento. Y siempre que haya una solución determinística o un modelo clásico que resuelva el problema, conviene usarlo antes que un LLM tratado como caja negra.

Nota sobre el TP

Había que anotarse en el Excel de grupos (link en el campus) dejando el mail. Para la semana siguiente, los grupos tenían que haberse reunido y definido la orientación del proyecto; al final de esa clase iba a haber un rato de consulta. A las tres semanas, cada grupo presenta con una PPT la tarea, el objetivo, las técnicas, los datos (si es una base de datos: ya obtenida y con un EDA de tamaño y distribución; si es con agentes: primeras pruebas), el scope y el plan, con el primer paso avanzado. Los docentes pidieron expresamente no presentar PPTs generadas por IA con números inventados: cada dato tiene que estar chequeado, y hay que tener cuidado al sacar conclusiones sobre los datos.