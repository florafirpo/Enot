# Explicación – Agentic coding, Spec-Driven Development e Information Retrieval

Inteligencia Artificial Agéntica · Clase del 01/10/2026 · Docentes: Carlos “Charlie” (profesor invitado) y Eddy

La clase tuvo dos partes con un hilo en común. En la primera, Charlie, que es desarrollador y trabaja en productos basados en agentes, abrió la caja de lo que pasa cuando un agente programa por nosotros. No lo planteó desde la pregunta de si el agente puede hacerlo, que da por resuelta, sino desde otra: cómo hacer para confiar en lo que hace. Para responderla recorrió cómo lee el agente un repositorio, cómo sabe qué tiene que hacer, cómo verifica su propio trabajo y qué límites conviene ponerle. En la segunda parte, Eddy presentó las bases de Information Retrieval: cómo se encuentran documentos relevantes frente a una consulta, que es la pieza de búsqueda que hay debajo de cualquier RAG.

El puente entre las dos partes es justamente la búsqueda. Una idea fuerte de la primera mitad es que un agente que programa no usa RAG para entender un repositorio, sino búsqueda exacta. La segunda mitad explica cómo funciona la búsqueda “clásica” y semántica que sí tiene sentido en otros escenarios. Entender ambas cosas permite elegir bien cuándo usar cada una.

## 1. Del “haceme un script” a confiar en un agente

El término *agentic coding* tiene bastante humo alrededor, pero la idea de fondo es simple: entender a los agentes y cómo programan para nosotros. Abarca un espectro amplio. En un extremo está el uso cotidiano de una herramienta como Claude Code, a la que uno le pide, le ordena y le corrige cosas sobre su propio código. En el otro están los agentes que operan sistemas grandes por medio de *loops*: un agente toma una tarea (que puede darle una persona o no) y se pone a trabajar solo, de manera sostenida. Los loops se ven en profundidad más adelante en la materia. Esta clase se queda en los cimientos, en lo que tiene que estar en su lugar para que cualquiera de esos niveles funcione.

Para dimensionar el cambio, Charlie trajo un caso: un producto interno de OpenAI, la empresa detrás de Codex, se construyó con tres ingenieros, sin escribir ninguna línea de código a mano y con unos 1.500 pull requests en cinco meses. Un PR es una propuesta de cambio sobre el código. En la práctica, cada uno suele traer una funcionalidad nueva, un arreglo o una mejora no trivial, así que conviene pensar el número como 1.500 funcionalidades o arreglos y no como 1.500 cambios cosméticos. Es un volumen que antes requería muchos desarrolladores trabajando sin parar durante meses. Matías aportó un dato de su propio equipo: pasaron de unos 20 PRs por persona por mes a casi 80.

Lo interesante del ejemplo no es el número sino el *cómo*. Lograr ese ritmo y poder confiar en el resultado depende de tener especificaciones, reglas, tests unitarios y de integración, y de que el agente sepa usar todo eso. El agentic coding, en este sentido, es mucho más que pedirle un script a un modelo. Es la capacidad del agente de adaptarse a uno o varios repositorios, trabajar según una política específica y ser sostenible para un equipo entero.

De ahí viene el cambio de rol que Charlie describió con la imagen del copiloto y el piloto. Incluso en el primer nivel de contacto, el agente en tu propia computadora para tu propio trabajo, el agente ya no ayuda: maneja. La persona pasa a ser piloto y orquestador. Su responsabilidad ya no es escribir el código sino asegurarse de que el agente tenga todo lo que necesita, que trabaje de manera segura y que exista un sistema en el que se pueda confiar en él. Charlie contó que trabaja con sistemas en los que, respecto de lo que hacía antes, ya “no hace nada”: se ocupa de verificar que todo esté bien.

Hay dos advertencias que acompañan todo esto. La primera es que cuando algo sale mal con un agente, no siempre se nota como una rotura. Puede aparecer como un commit vacío, o un commit que solo agregó un comentario, mientras el agente informa muy tranquilo que terminó su trabajo. Las fallas pueden ser silenciosas. La segunda es que muchos de estos problemas se mitigan con mejores modelos, pero no siempre se va a tener acceso al mejor modelo, ya sea por costos o por la política de la empresa. Por eso lo que se ve en la clase no depende de tener el modelo más potente.

De ahí el disclaimer central: los agentes automatizan mucho, pero no hay que perder la costumbre de leer lo que hacen. No se trata de revisar cien archivos modificados, sino de tener el criterio para saber si lo que hicieron es veraz. Buena parte de la clase apunta a construir ese criterio.

## 2. Cómo lee un agente un repositorio

La primera pregunta es cómo se entera un agente de lo que hay en un repositorio. La respuesta es menos sofisticada de lo que uno esperaría: lo hace principalmente con **grep**, la herramienta de terminal que busca texto y devuelve las coincidencias exactas. Matías acotó en el chat que grep existe desde noviembre de 1974. Es una herramienta antiquísima y funciona muy bien para lo que el agente necesita.

No hay un índice previamente construido, ni un RAG con búsqueda semántica, ni ningún sistema de búsqueda complejo. El agente decide qué buscar y va tirando comandos. Si le preguntás por la función que emite facturas, primero lista archivos y busca los que tengan “factura” en el nombre. Después, dentro de esos archivos, usa grep para encontrar “emitir” y lee solamente las líneas que le interesan. Va ampliando su contexto paso a paso, con búsquedas dirigidas.

Que la búsqueda sea exacta es una virtud y no una limitación. Cuando el agente busca la función de emitir una factura, no le sirve nada que sea “semánticamente parecido”, como un texto sobre emitir un programa de televisión. Quiere ir directo a lo que necesita. Su tarea típica es leer el estado actual del repositorio, encontrar exactamente lo relevante para una pregunta concreta y después hacer el trabajo de razonamiento y edición. Para eso, la coincidencia literal es justamente lo que conviene.

Detrás de esto hay un principio que atraviesa toda la materia: **un agente es tan bueno como el contexto que tiene a disposición**. Parte de nuestro rol como operadores es verificar que use la mejor forma de ampliar su contexto para cada caso de uso. Charlie mencionó que hay gente que cree que RAG resuelve todos los problemas de contexto de un agente, y la clase muestra por qué eso no es así.

### Buscador, búsqueda agéntica y RAG

Para entender la diferencia conviene contrastar tres formas de buscar. Un **buscador** clásico recibe una query y tiene un índice con algún mecanismo, sea semántico o un indexado tipo base de datos, que devuelve primero los resultados más relevantes. Un **RAG** es un caso de esto en el que lo recuperado se usa para ampliar el contexto de un modelo. La **búsqueda agéntica**, en cambio, no tiene índice: el agente decide en el momento qué buscar, con las herramientas que tiene a mano.

El argumento decisivo contra usar RAG sobre un repositorio es la **frescura**. Un índice hay que mantenerlo: reindexar y, en el caso de un RAG, tener todos los embeddings vectorizados y actualizados. En un repositorio en desarrollo activo el corpus cambia todo el tiempo, porque cada edición del propio agente lo modifica. Mantener un índice al día sobre algo que se reescribe a cada rato no tiene sentido, y la búsqueda con grep sobre el estado actual ya alcanza de sobra. Por eso montar un RAG o un motor como Elasticsearch sobre una base de código para hacer agentic coding no es un buen caso de uso.

Eso no quiere decir que RAG no sirva. Sirve, y mucho, cuando el agente no programa sino que forma parte de un producto: responde preguntas, asesora y necesita ampliar su contexto con un corpus estable. El ejemplo de manual son las preguntas frecuentes de un banco o un agente de atención al cliente. Ahí el corpus cambia poco y la búsqueda semántica aporta.

Existe además una tercera vía intermedia, que Charlie llamó **base fija más exploración**. Hay cosas que conviene dejar definidas de antemano para que el agente no tenga que descubrirlas, y a partir de ahí el agente explora sobre la marcha. Esa “base fija” son los archivos de reglas como CLAUDE.md o AGENTS.md, de los que se habla más abajo.

| Enfoque                  | Cuándo conviene                                                                                                       |
|--------------------------|-----------------------------------------------------------------------------------------------------------------------|
| RAG                      | Agente dentro de un producto que responde sobre un corpus estable (FAQ de un banco, atención al cliente)              |
| Búsqueda agéntica (grep) | Tareas de código en varios pasos sobre un corpus que cambia constantemente (arreglar un bug en un repo en desarrollo) |
| Base fija + exploración  | Hay información conocida de antemano (reglas, convenciones) y el resto se descubre al andar                           |

## 3. El harness: el sistema sobre el que se monta el modelo

La razón por la que el agente tiene grep “a mano” no es casual: viene de lo que se llama **harness**. La palabra significa arnés, como el que se le pone a un caballo para montarlo. La imagen es que el modelo es el jinete y el harness es todo el sistema más grande sobre el que se monta.

Esto importa porque el modelo, por sí solo, no tiene acceso a ninguna herramienta. Es el harness el que le dice qué tiene disponible (por ejemplo, grep, que está en cualquier máquina donde corra) y en qué formato le llega el contexto. Puede presentarle la información de una manera más legible para el modelo o más eficiente en tokens. Por eso **el mismo modelo, en distintos harness, se comporta y rinde distinto**. Cuando sale un modelo nuevo que mejora en algo, una parte de la mejora suele venir también del harness en el que corre, y no solo del modelo.

Charlie dio ejemplos de harness que usa. Cursor es un fork de Visual Studio Code con agentes integrados. Claude Code se puede usar como plugin dentro del editor, como aplicación de escritorio o como herramienta de línea de comandos. Codex es el equivalente de OpenAI. Cada uno tiene su manera de mostrarle las cosas al modelo y de “sacarle el jugo”. La tendencia que señaló es que cada vez más gente deja de lado el editor de texto y trabaja directamente con la aplicación o la CLI.

En esta clase no se construye un harness, pero todo lo que sigue (los archivos de reglas, las skills, los hooks, los permisos) son piezas del harness. Entenderlas por separado es la base para después armar uno propio.

## 4. Cómo sabe el agente qué tiene que hacer: los archivos de reglas

Más allá del prompt que le damos, ¿de dónde saca el agente la información sobre cómo trabajar en un proyecto? Una parte importante viene de los archivos de reglas: **CLAUDE.md** en el caso de Anthropic y **AGENTS.md** en herramientas como Gemini, Codex y otras que siguen ese estándar. En el fondo son lo mismo.

Este archivo se carga en las primeras etapas de cada sesión nueva. No es lo primero que lee el modelo: primero viene el system prompt y después el CLAUDE.md o AGENTS.md. Eso pasa cuando uno abre una sesión, pero también cada vez que un programa o un agente dispara a otro agente, que arranca cargando esa misma información.

Su función no es indexar el repositorio ni reemplazar la búsqueda. Es darle al modelo información valiosa para que vaya directo adonde tiene que ir, o para que evite lo que no debe tocar, que muchas veces vale lo mismo. El contenido típico incluye cómo correr los tests, dónde están ciertos archivos, una especie de índice de los archivos importantes, y convenciones, incluidas las metodologías de trabajo del equipo. Por eso es el lugar donde se optimiza el trabajo colaborativo: cuando varias personas trabajan sobre el mismo repo con agentes, este archivo hace que todos los agentes sepan “dónde están parados”.

### Leer una regla no garantiza cumplirla

La pregunta que planteó Charlie es si el hecho de que el agente lea siempre estas reglas significa que las cumpla siempre. La respuesta es no, y la explicación la dio un alumno. Un LLM no tiene un comportamiento determinista: genera prediciendo la próxima palabra según probabilidades condicionadas por todo el contexto, y otras cosas en ese contexto pueden llevarlo a no respetar una regla. No es un código que ejecuta un `if`. Los modelos muy buenos lo hacen mejor, pero nunca lo garantizan.

El ejemplo que surgió en la clase es muy concreto. Aunque le digas al agente que nunca mire las variables de entorno, en algún momento puede leerlas, y en ese caso los secretos quedan en el prompt que se manda al proveedor del modelo, o sea, salieron de tu máquina. A veces el propio agente te avisa después que tenés que rotar esas claves.

Ante eso hay dos lecturas, y las dos son válidas. Por un lado, si una regla es dura y no cumplirla es un problema serio, el archivo de texto no alcanza y hay que encontrar otra forma de imponerla (eso son los hooks, que vienen más adelante). Si en cambio es una convención de estilo, que el agente no la siga es menos grave. Por otro lado, si un archivo de reglas falla de forma recurrente, probablemente el problema es el archivo y hay que mejorarlo.

El primer síntoma de un mal archivo de reglas, según Charlie, es que es **demasiado largo**. Pasa mucho al principio: uno le pide al modelo que vaya “puliendo” el archivo y de pronto tiene 100 o 200 líneas, muchas de ellas basura. La recomendación es curarlo cada tanto con un test muy simple aplicado línea por línea: *si borro esta regla, ¿mi agente puede equivocarse?* Si su ausencia no causa errores, la regla sobra.

Matías sumó un matiz importante: cada archivo de reglas se interpreta distinto según el modelo, y cada modelo tiene su “personalidad”. Contó que en su trabajo, cuando salió un modelo nuevo, notaron que “corregía” lo que se le pedía: le pedías un botón rojo, hacía el cambio y después avisaba que había encontrado que el botón debía ser verde. Siguieron usando el modelo anterior para conversar y le pedían que lanzara un agente del modelo nuevo solo para escribir el código, que hacía muy bien. De ahí sacaron una regla de equipo: antes de adoptar un modelo nuevo, una semana de pruebas contra todo el harness que tienen armado. Charlie agregó que los modelos son cada vez más cajas negras. El marketing muestra benchmarks, pero en el uso se nota que razonan distinto y que pueden pasar por encima de lo que dice el AGENTS.md.

### Qué dice la evidencia sobre estos archivos

Charlie mostró un estudio que evaluó agentes de distintos proveedores (un modelo Sonnet de Anthropic, modelos de Codex de OpenAI y un modelo Qwen) midiendo la tasa de éxito en tareas bajo tres condiciones: sin archivo de contexto, con un archivo generado por el propio LLM y con un archivo escrito por los desarrolladores, que solo contenía lo que veían que funcionaba y era importante. En promedio, el archivo escrito por los desarrolladores tuvo la mayor tasa de éxito.

La conclusión de los autores es que se pueden omitir los archivos autogenerados y concentrarse en escribir el contenido de valor que el agente no puede deducir por su cuenta: reglas específicas del equipo, del producto, del negocio, o qué archivos no visitar. Un archivo corto, limpio y con lo que solo un humano sabe rinde más que uno largo producido por el modelo.

De todo esto se desprende una idea que vale la pena retener: cuando un modelo no hace lo que queremos, no siempre “alucinó”. Muchas veces le dimos un mal harness o una regla confusa, y el modelo hizo lo que pudo con lo que tenía.

## 5. Spec-Driven Development

El SDD (*Spec-Driven Development*) es una metodología: una serie de pasos para trabajar con agentes. El primero, y el que le da nombre, es escribir una **especificación** o *spec*. La spec detalla qué va a hacer el agente y qué no, qué tiene que revisar y qué no, y, lo más importante, **cómo va a verificar su trabajo**. Muchos piensan que el agente “se va a dar cuenta solo” de si lo hizo bien, pero no se le puede dejar esa tarea a la ligera. Una parte central de la spec existe para responder esa pregunta.

Como metodología, se implementa de distintas formas y con más o menos pasos. Lo más común es hacerlo con *skills*. Una alumna contó que usa OpenSpec, que básicamente carga una serie de skills y trabaja siguiendo sus reglas. Charlie mencionó Superpowers, que combina una especie de SDD con TDD (*Test-Driven Development*, del que derivan todos los “DD” posteriores).

Vale la pena precisar qué es una **skill** en este contexto. Es un documento de texto más que se le presenta al agente. No se carga entero en el contexto, sino que el agente lo conoce a través de las herramientas que se le cargan al iniciar la sesión, y decide cuándo usarlo según su propio razonamiento y lo que dice la skill. Es, literalmente, una “habilidad”: una receta para hacer algo sin tener que razonarlo todo de cero.

¿El SDD funciona siempre? No, depende de qué se evalúe. Lo que sí da es un marco de trabajo para operar siempre de la misma manera cuando se hace agentic coding. Y la consistencia es valiosa en sí misma, porque permite saber qué esperar.

### Las fases y la fase de entrevista

En una versión global, el SDD tiene un modo de **exploración**, un paso de **escritura de la spec** y, según la variante, un paso de **escritura del plan**. La spec puede escribirse junto con el plan o quedar a la espera de que la persona la revise antes de seguir.

Ahí aparece la pregunta de cuánto leer. Una alumna contó que siempre lee la spec al menos por arriba, para verificar que el agente no haya decidido nada por fuera de lo que ella quería. En muchos aspectos el modelo toma mejores decisiones que ella, y cuando se desvía suele ser evidente. Charlie lo tomó como ejemplo de algo que solo se aprende con exposición a las herramientas: reconocer cuándo el agente está tomando una buena decisión y cuándo no. Esa intuición se forma usándolas.

Charlie recomendó especialmente una fase que suele quedar implícita: la **entrevista**. Es la instancia previa a la implementación en la que el agente pregunta para completar contexto o para resolver una decisión que le falta. Muchas veces pregunta solo, pero la recomendación es no esperar a que lo haga y convertirla en una fase real: “preguntame hasta que esto quede claro”. Eso mejora mucho la experiencia y además obliga a uno mismo a entender lo que está haciendo. Lo contrario, que todos hacemos alguna vez, es tirar un ticket y decir “resolvelo” sin leer nada. Además del riesgo de un mal resultado, ese prompt podría traer algo envenenado o malintencionado sin que nadie lo note (aunque eso se previene con los límites y permisos que se ven después).

La entrevista no siempre es útil. En sistemas multiagénticos el flujo puede ser más directo: un agente planifica, otro revisa y se avanza. Lo que se termina revisando es la métrica final.

### Cuándo vale la pena una spec

No todo cambio necesita SDD. Para un cambio muy chico, que sabés que se termina en menos de dos minutos y que no altera nada, alcanza con verificar los riesgos y confiar en el razonamiento del modelo. Cuando el cambio es más grande y empieza a importar entender qué se está cambiando, ahí conviene la especificación. El flujo general queda así: explorar, planificar y, si la tarea lo amerita, escribir una spec.

Charlie contó su propia trayectoria: antes de la IA usaba TDD, aunque implicaba escribir el doble de código; después pasó por la etapa de “tirar prompts y ver qué pasa”; después usó el modo de planificación, y seguía teniendo problemas. Uno de ellos era que la ventana de contexto se acababa rápido en bases de código grandes. El SDD trajo, además de la spec, una serie de **archivos que persisten entre sesiones**, como el changelog y los ADRs. Eso le permite al agente retomar el trabajo sin depender de lo que quedó en una conversación.

### Cómo se ve una spec

La spec es un archivo Markdown. El ejemplo de la clase, muy simplificado, era la tarea “validar emails en el alta”:

- **Archivos a tocar:** solo el de validación y el de sus tests.
- **Interfaz:** la función recibe solo texto y se usa una sola función.
- **Fuera de alcance:** verificar que el dominio del email exista. También se pueden declarar archivos fuera de alcance, por ejemplo porque son privados.

Lo valioso de este formato es que obliga a hacer explícito lo que normalmente queda implícito. Un ejercicio que sugirió Charlie es leer specs reales y detectar qué se especifica de manera explícita y qué queda implícito.

### ADR: registrar por qué se decidió algo

Uno de los archivos persistentes es el **ADR** (*Architectural Decision Record*, registro de decisión de arquitectura). Antes de desarrollar un sistema, incluso antes de pensar en qué programar, se piensa su arquitectura. Eso implica responder preguntas como quién va a usar la funcionalidad, con qué sistemas se va a comunicar o qué latencia se busca. Las decisiones que salen de ahí son críticas porque determinan que el producto sea mantenible y escalable. Escalable en dos sentidos: que el código pueda crecer y sumar funcionalidades, y que la aplicación soporte a muchos usuarios. El ADR deja asentadas esas decisiones y sus razones.

## 6. Verificar: el problema de confiar en lo que el agente dice

Charlie le preguntó a la clase cómo hacen para confiar en que el agente hizo lo que dice que hizo. Matías respondió con su propio flujo. Todo lo que produce el agente pasa por Git y por un PR que él revisa. Como trabaja con datos, cuando el agente hace análisis le pide una notebook de Python ejecutada en la que vaya anotando por qué hizo cada cosa. Y cuando tiene que escribir código, empieza diseñando los tests y le pide al agente que los cumpla.

Charlie dijo que son estrategias muy sólidas, pero señaló hacia dónde se quiere ir: sacarse de ese lugar siempre que se pueda. No porque haya que hacerlo así por dogma, sino porque muchas veces no hace falta que una persona verifique: se puede lograr que el agente verifique por nosotros. Siempre queda algún intervalo de *human in the loop*, pero el objetivo es reducirlo para tener un agente con cierta autonomía real. El horizonte ideal es un agente lo bastante bueno como para no tener que meter mano en el repositorio ni leer nada, y confiar solo en la métrica final que se mide. La pregunta pasa a ser cuál es esa métrica.

La respuesta principal son los **tests**: una de las únicas maneras de comprobar que un código efectivamente funciona. Pero ahí empieza lo interesante: ¿cómo sabés que tus tests funcionan? Podés tener todos los tests pasando y un 100% de *coverage* (cuánto de tu código está cubierto por tests) y aun así no poder confiar del todo.

El concepto clave es el de **test significativo**: un test vale si realmente prueba la funcionalidad que tiene que probar, y no si solo confirma que “la función funciona por funcionar”. Esto vale para desarrollo, para datos y para cualquier cosa. Un test que pasa no es necesariamente un buen test. Charlie mencionó la técnica de **mutantes** (*mutation testing*), que consiste en introducir variaciones para ver si el test tenía la calidad que uno creía. La pregunta que responde no es si el test pasa, sino si detectaría un error.

Para un perfil de datos el razonamiento es familiar: es la diferencia entre que una métrica dé bien y que la métrica mida lo que importa. Si sabés que los tests pasan y que tienen un mínimo de calidad, podés confiar en el trabajo aunque no leas el código. Y la conclusión inversa también vale: sin tests, o sin alguna manera dura de medir lo que se produjo, vos terminás siendo el verificador.

## 7. Guías, hooks y sensores

Hasta acá aparecieron varios artefactos: la spec, el CLAUDE.md, el AGENTS.md, las skills. Charlie remarcó que todos son archivos de texto y que, por lo tanto, son **guías**: orientan al agente pero no siempre se cumplen. Para que algo se cumpla sí o sí hay otra herramienta: los **hooks**.

### Hooks: lo que tiene que pasar siempre

El concepto de hook es el mismo que en Git, donde se usa alrededor del commit: algo que sucede en un momento determinado con respecto a otra cosa. En agentes, un hook puede ejecutarse, por ejemplo, antes de que se ejecute una acción o antes de que se mande información al proveedor del modelo. Concretamente es un pequeño script que chequea si el agente está por hacer algo indebido, como leer un archivo sensible, y en ese caso lo bloquea y devuelve un error: “por acá no podés ir”.

Lo esencial es que **un hook es determinístico**. A diferencia de la regla escrita en el CLAUDE.md, que el modelo puede saltearse, el hook no depende de lo que el modelo decida. En Claude se configuran en un archivo de hooks dentro de la carpeta de configuración `.claude`.

Esto lleva a distinguir entre **regla** y **política**. Una regla es una guía. Una política es algo que tiene que acatarse sí o sí, por ejemplo “el modelo nunca puede recibir los tokens o credenciales”, y se implementa con hooks. En entornos empresariales esto se ve de forma muy clara: las empresas imponen hooks a nivel organización que el usuario no puede modificar, para que ciertos archivos jamás entren a la inferencia, por ejemplo por acuerdos de confidencialidad.

### Sensores y el ciclo de trabajo del agente

Con estas piezas se puede describir el ciclo completo de un agente que programa. Primero lee y amplía su contexto (con el archivo de reglas, la spec, grep). Después actúa, y antes, durante y después de cada acción puede haber hooks. La acción cambia el código. Y finalmente se mide qué tan bien estuvo el cambio, según lo que dice la última sección de la spec, la que define cómo verificar.

Lo que mide se llama genéricamente **sensores**. Pueden ser tests, *linters*, una revisión hecha por otro modelo o un LLM como juez, entre otras opciones. Lo importante es que siempre hay algo que le indica al agente cuánto tiempo tiene que seguir dando vueltas en el ciclo.

Ese ciclo es un *loop*, aunque no exactamente el loop que se ve en las próximas clases. Hay varios niveles de loop. Este es el que permite completar una tarea. Para que un agente sea autosuficiente no solo para hacer una tarea sino para **mantener un sistema**, lo que exige programar y decidir constantemente, hace falta un loop de otro nivel: algo parecido a un `while` o a un cron que corre todo el tiempo y chequea cuándo tiene que intervenir un agente. Ambos se apoyan sobre el harness.

### Ejercicio: ¿guía, hook o sensor?

La clase cerró este bloque con cuatro casos, que sirven para fijar los criterios.

**“En este repo se usa pnpm y no npm.”** Va en una guía, en el CLAUDE.md. Es un dato que el agente no puede adivinar y que no hay que dejarle librado al azar. Charlie contó que, trabajando con otro gestor de paquetes de Python, el agente usó el que estaba instalado en la máquina en lugar del que correspondía al proyecto. No rompió nada, pero podría haberlo hecho.

**“Nunca escribir en la carpeta migrations.”** Va en un hook. Es algo que hay que impedir siempre, en cualquier momento. Además no se verifica con tests: no es habitual escribir tests para comprobar si se escribió o no en cierta carpeta. Es una cuestión de seguridad del código y de su infraestructura, no de funcionalidad.

**“El endpoint de alta tiene que rechazar tal usuario.”** Va en un sensor, es decir, un test. Es una regla de negocio que depende de que la aplicación funcione de cierta manera, y eso es justamente lo que mide un test. Se ejecuta en el CI (*Continuous Integration*, cuando los tests corren de forma automática) o cuando se le pide al agente que corra los tests al final. Implementarlo como hook sería un sobreuso, porque no es algo que tenga que chequearse cada vez que se usa el modelo.

**“¿El módulo nuevo quedó bien separado del resto?”** Va a revisión humana. Es una decisión de arquitectura y no se expresa como una condición cuantificable en un test. Se le puede preguntar al agente, pero eso nunca reemplaza ir a ver que efectivamente quedó separado. No todo es automatizable.

## 8. Límites: permisos, aprobaciones y sandbox

El último bloque conceptual de Charlie trata de qué puede hacer el agente sin preguntar y dónde lo dejamos correr.

### Modos de permisos

Las herramientas ofrecen distintos modos. El **manual o default** pregunta antes de actuar, lo que obliga a leer lo que pide. El **auto** no es que pregunte menos por sí mismo, sino que clasifica qué acciones realmente requieren preguntar. El **Bypass Permissions** (en Codex y en Cursor se lo llamó “YOLO”) prácticamente no pregunta ni bloquea nada y le da libertad total al agente.

El bypass solo tiene sentido cuando confiás plenamente en el agente y además lo tenés viviendo en un lugar bien limitado. Charlie contó que lo usa en algunos proyectos porque los tiene muy bien armados y sabe que el agente no tiene acceso a nada con lo que pueda causar daño. El riesgo aparece cuando no se trabaja de forma ordenada. Si abriste la sesión en una carpeta con permisos sobre muchas otras cosas, cualquier orden mal interpretada puede hacer daño. Si no tenés la costumbre de pensar dónde abrís cada sesión, la recomendación es usar el modo manual o default y leer.

Hay una sutileza: apretar “aceptar, aceptar, aceptar” sin leer es igual de riesgoso que el bypass, porque en los hechos es lo mismo. Por eso a veces el modo auto termina siendo mejor que el manual: al clasificar, te hace mirar con atención justamente las cosas que importan.

Los permisos además se pueden configurar: qué acciones se deniegan, cuáles se piden siempre y cuáles se permiten siempre. Esto es clave en agentes muy autónomos. Eso sí, en modo bypass esa configuración se saltea, así que hay que usarlo con cuidado.

### Sandbox

Un **sandbox** es un espacio aislado que provee el sistema operativo (macOS, Linux) del que el agente no puede salir: no se comunica con la red local, no lanza procesos fuera, no accede a archivos de otros dominios de la computadora. Hay varias formas de lograr ese aislamiento: Docker y contenedores, reglas de red, máquinas virtuales.

La aplicación de escritorio de Claude Code ya ejecuta cada sesión dentro de su propio sandbox, así que aun con bypass los permisos aplican dentro de ese lugar. Lo importante es aislar bien el agente o confiar en que el harness que usás lo aísla de verdad. El riesgo concreto, si no lo hacés, es que haya órdenes escondidas en un prompt, en una skill o en un MCP bajado de un repositorio desconocido (*prompt poisoning* o *prompt injection*) y terminen rompiendo la computadora o robando credenciales.

### Ejercicio: qué modo y qué límite según la situación

- **Un refactor en tu propio repositorio, con tests y Git.** Modo plan o auto, local. Es tu código, tenés control y una red de seguridad.
- **Revisar un PR o probar una skill o un MCP de un repositorio desconocido.** Dentro de un sandbox, para que una inyección no llegue a tu máquina.
- **Dejar al agente corriendo solo toda la noche.** Bypass, para que no se trabe esperando aprobaciones (o auto, si la tarea es muy clara), avisándole que te vas y que debe decidir con autonomía. Y, sobre todo, dentro de un sandbox. Lo más simple es usar la aplicación de escritorio. Si se hace por terminal, hay que averiguar si la herramienta realmente aísla bien.

## 9. MCP y la demo

El cuarto bloque previsto era MCP, que quedó para clases siguientes. Solo se adelantó la idea: un MCP permite conectar al agente con sistemas y componentes externos, desde una base de datos hasta las plataformas de nube donde se despliega una aplicación (GCP, AWS, Azure), para facilitar el desarrollo y ampliar el contexto del agente. No es la única manera de darle más capacidades al agente.

### La demo: ver el flujo de un agente paso a paso

Charlie mostró una demo pensada para ver qué pasa por detrás en una sesión. El repositorio tenía un corpus (el código penal), tests y requerimientos. La spec pedía partir el código penal en artículos, y el archivo que hace esa partición tenía un error, por lo que al correr los tests dos fallaban.

Abrió una sesión de Claude con una configuración mínima: solo un MCP definido en un archivo de configuración oculto del proyecto. Al levantar la sesión se ve que el MCP está disponible con sus 14 herramientas. Todo eso se suma al contexto, y conviene tener presente que **hay muchas cosas que suman al contexto además del prompt**.

El prompt pedía leer la spec, hacer pasar los tests modificando solo el archivo de artículos, explicar en tres líneas qué iba a cambiar, usar una herramienta específica del MCP y al final informar el resultado de los tests. En modo manual se ve el flujo completo. El agente lista archivos con herramientas de terminal, llama al MCP, lee las líneas que le interesan con grep, pide permiso para leer y después para editar, y antes de aplicar muestra el *diff*. La idea central de la demo es poder parar, leer y decidir: decirle “no edites todavía, mostrame los cambios antes”.

La práctica propuesta es repetir ese flujo atómico haciendo pequeños cambios en el AGENTS.md o CLAUDE.md y, si uno se anima, en los hooks, mirando qué herramientas llama el agente y qué hace. El objetivo es familiarizarse con el flujo, porque eso es lo que después permite entender cómo va a funcionar un agente que uno mismo construya.

### Changelog y ADRs entre sesiones

La parte práctica que Charlie destacó como más importante son el changelog y los ADRs, dos maneras de registrar lo que pasa entre sesiones. El **ADR** explica *por qué* se decidió algo. El **changelog** explica *qué* fue cambiando y *cuándo*. Si quedan en el repositorio, el agente siempre está al tanto del historial sin que haya que explicárselo, aunque el cambio haya sido hace meses. El ejercicio es escribir en el AGENTS.md o CLAUDE.md la regla de mantenerlos y pedirle al agente un cambio para comprobar que efectivamente la aplica.

## 10. Information Retrieval

La segunda parte de la clase, a cargo de Eddy, cambia de escala: de cómo busca un agente dentro de un repositorio a cómo se construye un sistema de búsqueda sobre una colección de documentos.

**Information Retrieval** es la tarea de encontrar los documentos relevantes frente a una *query*, que puede ser una pregunta o simplemente un texto. Es la base de cualquier buscador, desde AltaVista y Google en adelante. Si la consulta es “cómo se transportan los kiwis importados”, el objetivo es traer los documentos más relevantes para ese texto. Lo que se busca normalmente es un **ranking**: un orden de los documentos del dataset según su relevancia respecto de la búsqueda. Puede ser el top mil o el dataset entero ordenado.

### BM25

El algoritmo estándar y clásico para esto es **BM25**, que rankea documentos según la aparición de las palabras exactas de la query.

El punto de partida es la representación que ya conocés: la query como un vector sobre el vocabulario, con un 1 en cada término que aparece (cómo, se, transportan, los, kiwis, importados) y 0 en el resto, igual que en la matriz término-documento. Una idea ingenua sería puntuar cada documento por el porcentaje de términos de la query que contiene: 3 de 6 da 0,5. El problema inmediato es que no todas las palabras valen lo mismo: un documento con “se”, “cómo” y “los” no interesa, uno con “transportan”, “kiwis” e “importados” sí. De ahí el primer peso, el **IDF**, que pondera cada término por su rareza, y el TF-IDF, que combina frecuencia en el documento y rareza.

El score de BM25 para un par (documento, query) es una suma sobre las palabras de la query del IDF de cada palabra multiplicado por un factor que depende de su frecuencia en el documento. Se calcula ese score para todos los documentos y se los ordena. Lo que distingue a BM25 del TF-IDF a secas son dos ajustes sobre ese factor de frecuencia.

El primero es la **normalización por longitud**. Un documento gigante que contiene casi todo el vocabulario tendría siempre un score alto, simplemente porque aparecen muchas palabras. El IDF normaliza por rareza de la palabra, pero hace falta normalizar también por tamaño del documento. Para eso, la frecuencia se ajusta según el largo del documento respecto del promedio del corpus: si un documento tiene 1.000 palabras y el promedio es 100, ese cociente da 10 y la frecuencia se divide aproximadamente por 10. El parámetro **b** regula cuánto peso tiene este ajuste. Con b = 1 se ajusta por completo, con b = 0 se anula y los valores intermedios ponderan.

El segundo es la **saturación**, controlada por **k1**. Si “kiwi” aparece diez veces, queda más claro que el documento habla de kiwis, así que debería aportar más que si aparece una vez, pero no diez veces más. La función de BM25 hace que el factor valga 0 cuando la frecuencia es 0 y crezca con la frecuencia hasta una cota máxima de k1 + 1: para frecuencias muy grandes, k1 se vuelve despreciable frente a la frecuencia ajustada y el cociente tiende a esa cota. Es la misma lógica de rendimientos decrecientes que conocés de otras transformaciones de features.

En síntesis, BM25 puntúa cada documento según cuántas veces aparecen las palabras de la query, con menos peso para los documentos largos y más peso para las palabras raras, según el IDF. Su limitación es obvia: busca **palabras exactas**. Eso le trae dos problemas. Por un lado la polisemia: buscar “United States Capital” puede traer documentos sobre *capital punishment*, y “States” no significa lo mismo que “Estados Unidos”. Por otro, los sinónimos: no trae documentos que dicen lo mismo con otras palabras.

### Embeddings de documentos

La solución a esas limitaciones son los embeddings, ahora a nivel de documento: representaciones vectoriales de un documento entero, construidas de manera que documentos similares queden cerca en el espacio. Se representan todos los documentos del corpus y la query en el mismo espacio, se calcula la similitud coseno (o el *dot product*) entre la query y cada documento, y esa similitud es el score con el que se ordena. Eddy remarcó que es una técnica clásica a la que se le fue cambiando el nombre: antes se hablaba de *bi-encoders*, hoy de *vector databases*, pero es lo mismo.

### Búsqueda híbrida y fusión de rankings

BM25 y los embeddings capturan cosas distintas. BM25 captura palabras exactas, lo que importa por ejemplo en el ámbito legal o cuando se busca un nombre propio y se quiere a esa persona exactamente. Los embeddings capturan el concepto. A veces interesan las dos cosas a la vez, y ahí aparecen las **técnicas híbridas**. Una situación típica es usar solo embeddings y notar que no están capturando una palabra exacta que hace falta.

El problema práctico es combinar dos métodos que funcionan en espacios y escalas totalmente distintos. La salida es combinar los **rankings** en lugar de los scores. Una técnica es **Reciprocal Rank Fusion**: para cada documento se suma, por cada método, 1 / (c + posición en el ranking de ese método). Si un documento no aparece en el top que se mira de un método, ese método aporta 0.

El ejemplo de la clase usa c = 60 y mira solo el top 2 de cada método, con tres documentos. BM25 rankea A primero y B segundo, y C queda afuera. Los embeddings rankean C primero y B segundo, y A queda afuera. Entonces A suma 1/61, C suma 1/61 y B suma 1/62 + 1/62. B queda primero en el ranking fusionado porque está bien posicionado en los dos métodos, aunque no haya sido primero en ninguno.

El parámetro **c** suaviza: hace que la diferencia entre posiciones cercanas importe poco (estar primero o segundo cambia el aporte de 1/61 a 1/62). El efecto es que lo que más pesa es aparecer entre los primeros en ambos rankings.

### Cross-encoders y re-rankers

Con embeddings se calcula un vector para la query, otro para cada documento, y se los compara con coseno. La pregunta natural es por qué la métrica de similitud tendría que ser el coseno, y si no habría una mejor. La hay: se puede entrenar una red neuronal que reciba la query y el documento juntos y diga si son parecidos. Eso es un **cross-encoder**. Funciona mejor, pero requiere un dataset anotado de pares query-documento relevantes y no relevantes para entrenarlo, y sobre todo es lento. Con un millón de documentos habría que correr la red un millón de veces por cada query, lo que no termina más.

Por eso el cross-encoder se usa como **re-ranker**. Un primer *retriever* barato (BM25, un bi-encoder o un híbrido) trae el top 100 del millón de documentos, y sobre esos 100 el re-ranker elige los mejores 10. Es una arquitectura en dos etapas: recuperación amplia y barata, y después refinamiento caro sobre pocos candidatos.

Eddy señaló que hoy, como todo en NLP, eso cambió: **el re-ranker es un LLM**. Se le pasan la pregunta y los 100 documentos y se le pide que los ordene por relevancia, y además se le pueden dar criterios explícitos de ordenamiento. Es otra capa de inteligencia sobre el buscador.

Un alumno que trabaja en el ámbito legal preguntó por el costo frente a un cross-encoder. Eddy contestó que nunca vio un cross-encoder en producción en esta época. En los usos normales de una empresa, que suelen ser internos y sin volúmenes enormes de consultas, el cómputo del LLM no es tan caro, y nunca le tocó un caso en que no valiera la pena. Usar un cross-encoder preentrenado probablemente no funcionaría tan bien sin un esfuerzo grande de fine-tuning. La ecuación podría cambiar en una empresa gigante con una cantidad inmensa de queries por minuto.

### Cómo evaluar un sistema de IR

Para evaluar un buscador hace falta un dataset con muchas queries y, para cada una, anotados los documentos relevantes del corpus. Con eso se comparan los resultados del sistema contra la anotación. Supongamos que para una query hay 5 documentos relevantes y el sistema trae 10, de los cuales 4 son relevantes: la *precision* es 4/10 y el *recall* es 4/5, y se puede combinar en un F-score. Son métricas que ya conocés. El punto que remarcó Eddy es que son **métricas sin orden**: les da lo mismo si los relevantes aparecen arriba o abajo de la lista, y en un buscador eso importa mucho, porque importa cuánto de lo relevante ve el usuario primero. Por eso se usan métricas que sí consideran el orden, entre las que destacó **NDCG**. En el ámbito legal además pesa especialmente el recall: lo que más importa es asegurarse de haber traído todos los documentos relevantes.

Eddy contó una experiencia que conecta con todo lo anterior. Apenas salió GPT-4, su equipo armó un RAG legal en un trabajo científico para ver cómo funcionaba, y no funcionaba bien. Al evaluar, descubrieron que el problema no era la IA sino el buscador. Eso los llevó a trabajar en mejorar el retrieval y, como parte de eso, a construir un dataset de evaluación de Information Retrieval en castellano rioplatense, publicado en un paper llamado “Me sirve”. La lección es que en un RAG la calidad de la recuperación muchas veces es el cuello de botella.

### Cómo anotar sin revisar todo el corpus

Queda un problema práctico: para medir el recall hay que saber cuántos relevantes hay en total, y con un millón de documentos no se puede anotar todo. La técnica es el **pooling**. Se toman varios métodos de búsqueda, se trae el top 50 de cada uno y se juntan: con cinco métodos son unos 250 candidatos por query para anotar. La hipótesis es que los relevantes van a estar dentro de ese pool.

Para estimar lo que se escapa del pool se usa muestreo. Por ejemplo, entre las posiciones 100 y 2.000 de los rankings hay unos 5.000 documentos. Se anotan al azar 200, y si alrededor del 1% resulta relevante, se estima que en esa franja hay unos 50 relevantes que no se están mirando. Del resto del corpus se anota otra muestra, por ejemplo 300 documentos, y si ninguno es relevante se aproxima ese aporte a cero. Sumando el pool y las estimaciones se obtiene cuántos relevantes hay en total para cada query, que es lo que hace falta para el recall.

Anotar es caro, sobre todo si requiere expertos. Una salida es combinar anotación de expertos (en el caso legal, abogados) con anotación hecha por un LLM.

## Ideas para llevarse

La pregunta que organiza el agentic coding no es si el agente puede hacer el trabajo, sino cómo construir un sistema en el que se pueda confiar en lo que hace. Ese sistema tiene capas. El harness define qué herramientas y qué contexto tiene el modelo, y explica por qué un mismo modelo rinde distinto en distintos entornos. Para leer un repositorio, la búsqueda exacta con grep le gana a RAG, porque el código cambia todo el tiempo y la frescura importa más que la semántica; RAG queda para corpus estables dentro de productos.

Los archivos de reglas, las specs y las skills son guías: mejoran mucho el trabajo si son cortos y contienen lo que el agente no puede deducir, pero no garantizan nada, porque el modelo no es determinista. Lo que tiene que cumplirse siempre se implementa con hooks, que son determinísticos. Lo que hay que medir se implementa con sensores, sobre todo tests, que además tienen que ser significativos. Lo que no se puede cuantificar, como una decisión de arquitectura, sigue requiriendo revisión humana. Alrededor de todo eso, los permisos y el sandbox definen cuánto daño puede hacer un error o una inyección.

En la parte de Information Retrieval, el recorrido va de BM25 (palabras exactas, con IDF, normalización por longitud y saturación) a los embeddings (conceptos), su combinación híbrida por fusión de rankings y el re-ranking, que hoy se hace con un LLM. Y queda una advertencia que conecta las dos mitades: cuando un sistema con IA anda mal, muchas veces el problema no es el modelo, sino el contexto que le damos, sea un archivo de reglas sucio o un buscador que trae los documentos equivocados.

**Sobre la práctica:** el material que mandó Charlie propone repetir el flujo atómico de la demo, en modo manual, modificando el CLAUDE.md o AGENTS.md (y opcionalmente los hooks) para observar qué herramientas llama el agente, y agregar al archivo de reglas la instrucción de mantener un changelog y ADRs para verificar que el agente la aplica.
