# Explicación – Qué es entrenar: funciones, programas y el espacio de programas

Inteligencia Artificial Agéntica · Clase del 05/11/2026 · Docente: no se identifica en la transcripción (participan también Fran y Eddy con aportes)

Esta clase es distinta de las demás. El docente aclara desde el principio que no busca darnos información, que hoy se consigue preguntándole a cualquier modelo, sino transmitir intuiciones: qué estamos haciendo realmente cuando “hacemos IA” y, en particular, cuando entrenamos. El hilo de la clase es una sola idea, que se va mirando desde distintos ángulos hasta que se vuelve natural: todo problema se puede expresar como un programa, existe un espacio enorme de programas posibles y entrenar no es otra cosa que buscar dentro de ese espacio uno que funcione suficientemente bien. A partir de ahí se reinterpretan cosas que ya conocemos, como el prompting, los workflows, los agentes, el fine-tuning y los benchmarks, como distintas formas de moverse por ese espacio. La clase cierra con una práctica (un clasificador de facturas) y con una novedad reciente, Weight Space Programming, que agrega una tercera manera de buscar programas.

El propio docente lo presenta como compartir su *world model*. Un world model es una representación de cómo funciona algo (el concepto está de moda, sobre todo en robótica), y la clase es un intento de transmitir la representación que él se armó de qué es la IA.

## 1. Dejar de llamarla “IA”: funciones y aproximaciones

La propuesta inicial es provocadora: si queremos entender qué es la inteligencia artificial, conviene dejar de llamarla así y pensarla en términos de funciones, programas y aproximaciones. Para justificarlo, el docente vuelve sobre una pregunta histórica: ¿por qué un grupo de investigadores (los “padres” de la IA moderna, y después una segunda generación en la que se menciona a Andrej Karpathy) estuvo tan convencido durante décadas de que el deep learning era el camino, cuando casi nadie lo veía? La respuesta que da es un resultado teórico: el paper que demostró que una red neuronal es un **aproximador universal de funciones**. Esa semilla, combinada con una segunda idea, explica toda la convicción.

La segunda idea es que **todo puede ser una función**. Una función mapea valores de un espacio X (el dominio, lo que entra) en un espacio Y (lo que sale). La clase recorre ejemplos cada vez menos obvios: los tweets de una persona mapeados a un sentimiento; la señal de Wi-Fi de una sala mapeada a la posición de las personas que están adentro (un alumno duda porque el resultado son varios puntos, pero sigue siendo una función: el output puede ser un objeto con varios puntos); las señales de sensores cerebrales, como en los experimentos tipo Neuralink, mapeadas a movimientos en una partida de ajedrez o a la posición de un cursor. La conclusión es que prácticamente cualquier cosa del mundo se puede representar como un input que entra y un output que sale.

El problema real nunca es si algo es una función, sino **cuál es** esa función. El ejemplo que vuelve una y otra vez en la clase es el piloto automático. Desde afuera es fácil de definir: entran los píxeles de las cámaras y los datos del radar o el lidar, salen el ángulo del volante y la posición de los pedales. Pero nadie en el mundo sabe escribir esa función. Es fácil especificar *qué* hace y es imposible escribir *cómo* lo hace.

Ahí entra el segundo concepto: la **aproximación**. Si no conocemos la forma de una función, podemos aproximarla, estar cerca de ella. Y eso es exactamente lo que hace un optimizador cuando entrenamos. Para quitarle peso a la idea de que una aproximación es una solución “de segunda”, el docente usa el modelo ptolemaico del sistema solar: planetas moviéndose en órbitas dentro de órbitas. Era una representación completamente equivocada de la realidad, pero se usó durante siglos porque predecía muy bien. Un ingeniero lo habría adoptado encantado. La lección es que una aproximación suficientemente buena es casi equivalente a la solución correcta, y en algunos escenarios hasta es preferible. A quien trabaja como ingeniero de IA le interesa predecir, mapear espacios o resolver problemas, no descubrir la verdad última de cómo funciona algo.

Juntando las dos piezas se entiende la convicción de aquellos investigadores: si una red neuronal puede aproximar cualquier función y todo es una función, entonces, al menos en teoría, se puede aprender la solución a cualquier problema.

## 2. Programas, funciones y el *program space*

El paso siguiente es igualar dos palabras que solemos usar por separado: **una función y un programa son lo mismo**. La clase lo muestra con dos objetos de apariencia muy distinta: la ley de gravitación universal de Newton (una función matemática que describe un sistema físico) y el *Fast Inverse Square Root*, un fragmento de código famoso que hizo posibles los gráficos del videojuego Quake. Uno es una ecuación y el otro es código, pero ambos toman algo y devuelven algo.

La diferencia que sí importa es otra: **descripción explícita versus implícita**. La ecuación de Newton, el código del Quake o un `.py` que escribimos nosotros describen explícitamente el procedimiento. Una red neuronal también puede aprender a calcular la fuerza gravitatoria entre dos cuerpos, pero lo hace de forma implícita: el “procedimiento” queda distribuido en sus parámetros y no lo podemos leer.

Con esto aparece la intuición central de toda la clase. Existe un universo de todos los programas posibles, al que el docente llama **program space** o **solution space** (en matemática se habla de *function space*, que es lo mismo). Podemos imaginarlo como un cubo en el que cada punto es un programa distinto. Lo que un humano puede alcanzar escribiendo código a mano es solo un **subconjunto** de ese espacio. El piloto automático, la decodificación de señales cerebrales o la clasificación confiable de un PDF son programas que existen en algún lugar del espacio, pero que nadie sabe escribir.

De ahí sale una regla práctica muy sana: **si podés escribir el programa a mano, o pedírselo a un asistente de código, hacelo**. No tiene sentido entrenar un modelo para algo que se resuelve con un `.py` conocido. La IA es la herramienta extra para el subconjunto enorme de problemas que nadie sabe resolver explícitamente: clasificar un documento, extraer un JSON de una conversación, decidir qué ambulancia mandar.

### Software 2.0: explorar en lugar de escribir

Acá se conecta el concepto de **Software 2.0** de Karpathy (que la clase ilustra con un tweet suyo, bastante polémico, sobre que una red puede escribir mejor código que nosotros). En el software tradicional, el programador elige un punto del espacio escribiendo línea por línea. En Software 2.0, en lugar de ir a un punto escribiendo, **se explora el espacio lanzando un optimizador**. Cada combinación de parámetros de una red neuronal es un programa distinto, así que entrenar es moverse de un programa a otro buscando uno mejor.

Como data scientist, esta forma de verlo tiene una consecuencia interesante: el espacio de hipótesis que conocemos de ML se reinterpreta como un espacio de programas, y entrenar es buscar dentro de él. Por eso aparece la frase “el data scientist es el nuevo programador”. El programador tradicional explora el espacio por su cuenta, pensando y escribiendo. El data scientist o ingeniero de IA busca qué modelo contiene el programa que necesita y explora ese espacio hasta encontrarlo.

### Cada foundation model es un program space

Fran pregunta en clase cómo se define la frontera del program space, es decir, hasta dónde llega lo que hoy se puede hacer. La respuesta reinterpreta la evolución de los modelos: la diferencia entre GPT-3, GPT-4 y GPT-5 es que **el program space se expandió**. Con cada generación aparecen tareas que antes no tenían solución y ahora sí, porque el modelo contiene más programas buenos. Los modelos especializados (por ejemplo, uno de biología) no solo tienen espacios más grandes o más chicos: representan **espacios distintos**, con otros programas adentro. Cuando sale un modelo nuevo, la pregunta útil es qué programas contiene que antes no estaban disponibles.

Y si cada foundation model es un espacio de programas, **promptear es elegir un punto dentro de ese espacio**. Cuando le decimos a un modelo “tu input son imágenes, sos un clasificador y tu único output posible es una lista de tres valores”, estamos seleccionando un programa concreto entre todos los que el modelo puede ser. Revisar un mail es un programa; clasificar un documento es otro; cada uno es un punto distinto del mismo cubo.

### Del problema de negocio al programa

La clase agrega una capa más, pensando en el trabajo real. Un problema concreto, como cuánto debería durar el rojo de un semáforo o cuál es la mejor ruta para un auto, abre un **espacio de soluciones**: un timer, una cámara que detecta el tránsito, un modelo de lenguaje que decide cuándo cambiar a verde. Cada solución se implementa con un programa. En la industria el foco está en el problema de negocio, no en el modelo: nadie quiere “un modelo entrenado” en abstracto. La secuencia correcta es entender el problema, pensar soluciones y, si no hay forma de escribir la solución a mano, ir a buscar el programa a un foundation model.

## 3. Cómo se define un programa: input, output y types

Un alumno plantea una inquietud muy concreta: muchas veces el modelo le propone “soluciones” que no lo son (como sugerirle que no conecte el dispositivo viejo que quería conectar, o que abra él mismo los 3.000 archivos que le pidió procesar). ¿Cómo se define entonces qué es una solución dentro de este espacio?

La respuesta lleva a la definición operativa de programa: **una caja en la que entra un input, pasa algo en el medio y sale un output**. Lo que pasa en el medio (el `.py` que escribimos o el prompt que redactamos) es el algoritmo, el conjunto de pasos. Pero el programa que buscamos **se define únicamente por lo que entra, lo que sale y sus *types***: si es un vector, un string, un integer, un boolean o un enum. Esta es la única definición que tenemos de programa y, por lo tanto, de solución.

Los ejemplos de clase lo muestran:

- Un analista financiero necesita detectar documentos riesgosos: input, un documento; output, un boolean (peligroso o no peligroso).
- Una persona llama pidiendo una ambulancia y describe síntomas: input, la transcripción o la lista de síntomas; output, un enum con tres categorías (ambulancia de alta, media o baja complejidad). Antes había que escribir a mano reglas del tipo “si dice dolor de pecho, entonces…”; hoy se puede tomar la transcripción entera, pasársela a un modelo y restringir su respuesta a esas tres opciones.

Todo lo que viene después (armar un benchmark, entrenar, juntar datos, hacer RAG o context engineering) existe para **mejorar la performance de ese programa**. Pero lo primero siempre es decidir cuál es el programa. Esto da una herramienta para el problema del alumno: si el output está bien tipado y acotado, una “solución” que no responde a lo pedido queda fuera de la especificación.

## 4. Sentirse cómodo con una caja negra

Otro alumno observa que todo esto parece reducir la complejidad metiéndola en una caja negra. El docente responde que precisamente eso es lo que hay que aprender a hacer, y lo explica con la distinción entre dos formas de conocer un sistema:

- **Bottom-up**: conozco cómo funciona cada parte (cada engranaje, cada arandela) y puedo inferir el comportamiento del conjunto. Es la forma típica de la ingeniería y de buena parte de la física.
- **Top-down**: no sé cómo funciona por dentro, pero conozco cómo se comporta en distintos escenarios. Es la forma de las ciencias naturales: no sé exactamente qué pasa adentro de una célula, pero sé que si le agrego cloro hace una cosa y si la caliento hace otra.

Al trabajar con modelos de IA pasamos del software bottom-up al **software top-down**. No sabemos qué hay adentro; sabemos qué hace en cada escenario, y entrenar o hacer benchmarks sirve para mejorar ese comportamiento sin abrir nunca la caja. El docente comenta que a muchos ingenieros esto les cuesta, porque están acostumbrados a razonar desde las partes, mientras que quienes vienen de las ciencias naturales lo viven con naturalidad: en los sistemas complejos aparecen **propiedades emergentes** al combinar partes, y no hay forma de entenderlo todo pieza por pieza. Un programa puede ser un modelo, muchos modelos o un agente; lo que importa es que, con estos inputs, da estos outputs y eso sirve para el trabajo.

## 5. Determinismo, distribuciones y la confianza del modelo

Una objeción natural: una función es determinística (mismo input, mismo output), pero los modelos no lo son. ¿Eso no rompe todo el planteo?

La respuesta corta es que no. Un foundation model tiene, al final, un proceso estocástico de **sampling**, y por eso no responde igual dos veces ante el mismo input. Pero esa aleatoriedad se puede controlar: ajustando la temperatura se elimina el sampling y el modelo queda determinístico “entre comillas”. La estocasticidad, entonces, no es lo que distingue a una red neuronal.

Eddy suma una mirada desde el modelado físico: hay muchísimos procesos físicos estocásticos, y en sistemas complejos lo que se modela es el comportamiento estadístico (como en termodinámica). Una función puede ir de un input a una **distribución de probabilidad** y sigue siendo una función. La red neuronal, de hecho, estima una distribución, y después se samplea. De ahí una recomendación: en lugar de forzar todo a ser determinístico, conviene asumir que **el output de nuestros sistemas son distribuciones de probabilidad**, como ocurre en el mundo y en la biología.

Entonces, ¿qué es lo que realmente distingue a una red neuronal de, por ejemplo, una ecuación física? Que **no sabemos cómo se comporta por dentro** y, por lo tanto, no podemos predecir su comportamiento en escenarios que no probamos. Con una ecuación de estado se puede calcular si un asteroide va a impactar dentro de 50 años; con una red, no hay forma de deducir qué va a hacer ante un caso nuevo. Esto explica por qué hay que mirar trazas y monitorear una y otra vez: no porque el modelo sea aleatorio, sino porque su comportamiento futuro es desconocido.

### Las únicas perillas: prompt y parámetros de inferencia

Cuando trabajamos con un foundation model que no entrenamos, **el prompt y los parámetros de inferencia son las únicas perillas** que tenemos para modificar su comportamiento y llegar a la performance que nos piden (además de componer modelos, que se ve más adelante). Un alumno cuenta que en su trabajo un modelo de Anthropic, a partir de cierta versión, ya no permite fijar la temperatura. El docente lo confirma como una tendencia de algunos proveedores a controlar cómo se comportan sus modelos, y señala que con modelos open source, o servidos por uno mismo, ese control vuelve a estar en nuestras manos.

### Para qué sirve tener la distribución

Tener la distribución de probabilidad es muy útil en producción. El caso de clase es la ingesta de documentos escritos a mano: un modelo extrae los datos a un JSON y una persona (human in the loop) valida y corrige. Si tenemos la distribución, podemos indicarle a esa persona qué campos revisar con más cuidado porque son los que tienen más probabilidad de estar mal. De paso, esas correcciones generan datos para entrenar después.

La forma de acceder a esa certeza son los **logprobs**: el logaritmo de la probabilidad de cada output, que representa cuán seguro está el modelo. Algunos proveedores los exponen y otros no (en la clase se menciona que Amazon Bedrock no los da para algunos modelos). Un alumno pregunta si, corriendo un modelo localmente, se podría restringir el vocabulario a las palabras de las clases y leer las probabilidades de la última capa. El docente le da la razón: eso es exactamente lo que ocurre por debajo. Hoy está estandarizado como output estructurado (un JSON con una key de tipo enum), que es la forma práctica de hacer lo mismo.

### El error de pedirle la confianza en el prompt

Un error muy común es pedirle al modelo que diga su nivel de confianza. El docente cuenta que alguien le aseguró que su prueba de concepto tenía un 5% de error “porque se lo había dicho el modelo”. El problema es que pedir eso en el prompt es pedir **inferencia**: el modelo genera tokens, inventa un número plausible. Generar tokens no te dice cuál es la certeza real sobre cada token. La confianza que el modelo “dice” es distinta de la que aparece en los logprobs o la que se mide con un benchmark. Para tener incertidumbre en serio hay dos caminos: leer la distribución en el momento o medir después cuán seguido falla.

### Cuándo querés estocasticidad y cuándo no

Esto no lo decide el modelo, lo decidimos nosotros según el programa:

- **Extracción a JSON**: queremos que dé siempre el mismo valor, así que conviene eliminar la aleatoriedad.
- **Agentes con un while loop**: si el clasificador es determinístico, repetirlo no sirve para nada; si clasifica mal, va a clasificar mal siempre. Con algo de estocasticidad, ante el mismo documento a veces dirá “factura” y a veces “no factura”, y río abajo otro modelo puede agregar: “salió 95 veces factura y 5 no factura, decidí”.
- **Escritura de prosa**: con temperatura cero el modelo elige siempre el token más probable y escribe de forma mecánica, sin sorpresa ni variabilidad.

## 6. Software 3.0 y “¿es esto un programa?”

Con todo lo anterior se define **Software 3.0**: es lo mismo que Software 2.0, explorar el program space, pero en lugar de tocar los pesos de la red nos movemos por el **espacio de prompts y de parámetros de inferencia**. Cuando alguien sugiere “poné la temperatura en 0,2”, no está haciendo otra cosa que tocar una de las perillas disponibles para pararse en otro punto del espacio.

Para fijar la idea, la clase propone un juego: ¿es esto un programa? La respuesta es siempre sí:

- Un modelo solo es un programa.
- Un modelo con un prompt (a esto algunos le dicen *nodo*) es un programa.
- Un **workflow**, que según la distinción propuesta por Anthropic es una composición de modelos (uno llama a otro, se rutea entre varios, se encadenan), es un programa.
- Un **agente**, que es un modelo con acceso a código tradicional (tools) y a un while loop para intentar una y otra vez hasta lograr el resultado, también es un programa.

La consecuencia clave es que **componer programas da otro programa**. Por eso, a quien trabaja como ingeniero no le interesa la composición en sí, sino el programa: que con el input definido produzca el output esperado con la performance suficiente.

### La escalera práctica

De acá sale una forma muy concreta de encarar un problema, usando como ejemplo la ingesta de documentos escritos a mano, que según el docente es de lo que más se hace hoy en la industria (antes, trabajo manual de data entry):

1.  **¿Lo resuelve un modelo así nomás?** Le pedís que extraiga los datos a un JSON. Si funciona lo suficiente, salís a producción con eso.
2.  **Prompting.** Si la performance no alcanza, mejorás el programa con instrucciones: por ejemplo, “la fecha va en formato día/mes/año, no en el formato estadounidense”. También podés eliminar la temperatura para que se comporte siempre igual.
3.  **Workflow.** Si aun así no alcanza, componés programas. Un patrón típico: un modelo de segmentación divide la imagen en partes, cada parte se extrae por separado y río abajo otro modelo recibe todos los resultados junto con la imagen original, los verifica y arma el JSON final.
4.  **Agente.** Si tampoco alcanza, sumás código discreto (por ejemplo, un script de Python que elimina los píxeles por debajo de cierto nivel de gris antes de pasarle la imagen al modelo) y un while loop: “este fue tu resultado anterior, esta fue su performance, probá de otra forma”.

En cada escalón seguís trabajando con una caja negra, como si fuera una API de la que no sabés qué hay detrás: probás escenarios y verificás si se comporta como querés.

## 7. Inteligencia como compresión

La última intuición teórica antes de la práctica es la de **inteligencia como compresión**. La clase arranca con el Hutter Prize, una competencia con un premio grande para quien logre comprimir mejor un archivo de texto. Comprimir una secuencia repetitiva es trivial: si el texto es “1, 2, 3” repetido cien veces, basta con decir “repetí 1, 2, 3 cien veces”. Pero ¿qué significa comprimir el Quijote? No es obvio.

Para entenderlo, la clase vuelve a Newton. Imaginate que recorrés el universo midiendo masas, distancias y fuerzas, y guardás todo en una lista. Esa lista es tu dataset, y pesa lo que pesan todas las observaciones. Con ella podés hacer tres cosas:

- **Guardar la lista tal cual.** No comprimiste nada.
- **Entrenar una red neuronal** que ajuste la curva de fuerza contra distancia. Es una compresión, pero las redes tienden a overfitear: funcionan bien con los datos que vieron y hacen cualquier cosa fuera de ellos, lo cual es un problema serio en producción, donde siempre aparecen escenarios que no estaban en el dataset.
- **Encontrar la ecuación de Newton**, una compresión muchísimo mejor: con dos masas y una distancia te da la fuerza en cualquier escenario.

Ecuación, programa y red neuronal son, entonces, **compresiones de las observaciones**. Y hacer inferencia es lo inverso: “descomprimir” esa representación para un escenario particular.

La analogía de la abogada lo vuelve muy tangible. Toda la normativa está publicada (el boletín oficial, los códigos, los libros de derecho), pero si te despiden del trabajo, encontrar ahí qué te corresponde es dificilísimo. Una abogada comprimió toda esa información en un modelo de cómo funcionan las cosas y puede decirte “lo que te cubre es esta ley, tenés que hacer esto”. ChatGPT y los demás modelos son una gran compresión de la información del mundo, que formó un world model aproximado y que, cada vez que preguntamos, descomprime para nuestro caso.

De ahí la definición de inteligencia que el docente considera más objetiva: **compresión sin pérdida**. Es fácil comprimir el Quijote recortándolo; lo difícil es comprimirlo entendiendo lo que pasa y pudiendo explicarlo. Es fácil guardar video; lo difícil es comprimirlo de manera tal que puedas predecir el próximo frame. La robótica, que según el docente va a crecer mucho, necesita justamente un world model de física: haber comprimido una enorme cantidad de observaciones del mundo real. Cuando alguien dice “¿para qué una red neuronal, si hay una ecuación?”, es porque alguien ya encontró esa compresión explícita. En la mayoría de los problemas nadie la encontró y no queda otra que comprimir en un modelo. **Entrenar es un proceso de compresión.**

## 8. Tamaño del modelo y program space

Un alumno pregunta por qué los modelos son tan grandes, si en principio uno querría la compresión más chica posible. El docente usa como referencia Kimi K3, con alrededor de 2,8 billones (*trillions*) de parámetros, que para correr necesita entrar entero en la memoria de las GPUs, no en la RAM: teras de memoria de GPU, carísimas.

La explicación vuelve al program space: **la dimensionalidad del program space es igual a la cantidad de parámetros**. Con dos o tres parámetros el espacio es chico; con billones, crece exponencialmente. Las redes neuronales fueron las que resolvieron el problema de conseguir un espacio útil y suficientemente grande: si el espacio crece exponencialmente, aumentan las chances de que el programa que buscamos esté adentro. Por eso los problemas más complejos (por ejemplo, predecir la estructura 3D de una proteína a partir de una secuencia de ARN, o encontrar la molécula para tratar un tipo de cáncer) requieren modelos más grandes.

Pero el tamaño tiene un costo, y eso explica por qué hoy son útiles los **modelos especializados chicos**. Pasar de un modelo de 2,8 billones de parámetros a uno de 9.000 millones achica muchísimo el espacio. La pregunta que se responde al entrenar el modelo chico es: dado que el modelo gigante tiene un espacio enorme y puede hacer de todo, ¿cómo comprimo eso y me quedo solo con los programas que me interesan? Si el modelo grande extrae JSON espectacularmente bien, puedo intentar llevar esa capacidad a un modelo de 9B que extraiga muy bien… y que tal vez clasifique muy mal. Es un trade-off asumido: el modelo grande es muy bueno en todo, pero no perfecto en nada, y es pesado.

El caso extremo que se menciona es un modelo de decisión de unos 500 millones de parámetros: no puede hacer casi nada de lo que hace un modelo de frontera, pero toma decisiones muy bien (por ejemplo, un triage: elegir el mejor vehículo para enviar según la situación). Su program space solo contiene programas de decisión. La clase comenta que en paralelo aparecieron las *Decision APIs* de OpenAI y Anthropic, y un alumno cuenta que, usándolas esa semana, obtuvo la probabilidad de cada decisión y los tokens gastados, con buenos resultados siempre que defina con precisión cada label. La pregunta que tenemos que hacernos al entrenar es: **¿qué programas quiero y por qué me quiero quedar con un modelo más chico?**

## 9. Entrenar en Software 2.0, visto desde el program space

La parte de entrenamiento clásico la conocés desde data science, así que vale la pena quedarse con la relectura que propone la clase más que con los detalles. Para entrenar en Software 2.0 hacen falta tres cosas: **arquitectura, datos y optimizador**.

- **Arquitectura como “aprendedor de programas”.** Las convolucionales eran muy buenas para programas cuyo input son imágenes; las secuenciales y las LSTM, para series temporales; el transformer nació para traducción y hoy le gana a casi todo. La intuición es que cada arquitectura aprende mejor ciertos programas, y elegirla es pensar qué programas querés aprender. El modelo de decisión chico y el modelo gigante tienen arquitecturas muy distintas precisamente porque buscan subconjuntos de programas distintos. Hoy la elección pasa por opciones como BERT (decisión), Mixture of Experts (bueno para muchas cosas) o encoder-decoder (transcripción). Un alumno pregunta si con los foundation models la arquitectura queda implícita, y efectivamente es así: elegir un modelo es elegir una arquitectura, entre los más de tres millones de modelos que hay en Hugging Face.
- **Datos.** En producción lo más probable es el aprendizaje supervisado: le mostramos al modelo cómo debe comportarse el programa (“esta imagen es una factura, esta es un pie”). El aprendizaje por refuerzo (RLHF, por ejemplo) es el estado del arte y busca, a prueba y error y sin datos etiquetados, el programa que mejor funciona. Para conseguir datasets: Hugging Face (organizado por tipo de modelo, no por tarea), Kaggle, Papers with Code y arXiv. El ejemplo es fine-tunear un modelo de transcripción para el castellano rioplatense: input, audio; output, texto; buscás un dataset de ese dialecto y entrenás.
- **Optimizador.** La función de pérdida dice si un programa es mejor que otro y el optimizador decide hacia dónde moverse. Lo interesante es la lectura geométrica: algunos optimizadores exploran mejor espacios con cierta geometría; algunos llegan rápido a un buen programa pero, si se sigue entrenando, lo pierden (lo que la gente describe como “el modelo se volvió tonto”); otros tardan más pero, cuando llegan, encuentran zonas con muchos programas buenos cerca.

El monitoreo de la loss se reinterpreta igual: el eje Y indica cuán bueno es cada programa encontrado, y la forma de la curva (suave o con *spikes*) dice qué está pasando en la búsqueda. Medir la performance final no es trivial y queda para la clase de benchmarks.

## 10. La práctica: un clasificador de facturas

La parte práctica baja todo esto a un caso concreto de Software 3.0. El problema es casi canónico: si en producción te piden extraer los datos de facturas, lo primero es asegurarte de que el documento **sea** una factura. Un extractor solo, si le llega la foto de un pie, va a extraer algo igual, cualquier cosa. Entonces el primer programa es un clasificador: **input, imagen; output, enum {factura, no factura}**.

El código tiene dos elementos esenciales. El primero es elegir proveedor y modelo (en el ejemplo, un modelo de Anthropic servido en Amazon Bedrock). Esta elección ya es una pregunta de program space: ¿el espacio de este modelo contiene un buen clasificador de facturas o hay otro mejor? Si no lo sabés, la alternativa es un loop que pruebe todos los modelos que puedas. El segundo es definir el **schema**: el formato del input y del output. Como el modelo es multimodal, el input casi no importa; lo que hay que controlar es el output: un JSON con una única key, “categoría”, de tipo enum, con dos valores posibles.

Con eso, dice el docente, tomaste el modelo más inteligente que tengas y lo “lobotomizaste”: lo único que puede hacer ahora es responder “factura” o “no factura”. Acabás de crear un clasificador. Al correrlo con un contrato, una factura, un reclamo y un gráfico de ventas, clasifica bien todos.

Para mejorar el programa se trabaja el prompt. Si notás que confunde remitos con facturas, escribís “ojo, un remito no es una factura, tiene tal forma”; si entran muchas fotos de pies, aclarás que no son facturas. Esto es programar en esta generación: en software tradicional cambiabas líneas de código, en Software 2.0 entrenabas con datos, con foundation models trabajás el prompt. Cada cambio de prompt o de parámetros de inferencia es **pararse en otro punto del espacio**, y un clasificador que clasifica mejor que otro es, literalmente, otro programa.

Cambiar el output también crea un programa nuevo. Si decidís que te conviene una tercera categoría, “remito”, le pedís a un agente de código que modifique el enum, y ahora tenés un programa distinto. Un alumno pregunta cómo obtener una probabilidad de la clasificación. Se puede agregar al schema un campo “confianza” de tipo float, y va a funcionar en el sentido de que devuelve un número, pero por lo visto antes ese número es inventado: si después hacés un benchmark o mirás los logprobs, no coincide.

El contraste histórico hace notar la magnitud de algo que parece trivial. Entre 2005 y 2010, hacer un clasificador de facturas significaba escribir un `.py` que analizara píxeles, colores y líneas, y no funcionaba. No existían clasificadores ni extractores de facturas porque nadie en el mundo sabía escribir ese programa, y no por falta de buenos programadores. Ese era el enfoque bottom-up. Hoy el enfoque es top-down: no te importa cómo funciona por dentro, definís cómo se tiene que comportar y verificás si lo hace. Un clasificador de este tipo se arma en un minuto pidiéndoselo a un asistente; lo difícil, y donde está el trabajo de ingeniería, es que alcance la performance que exige producción.

Sobre el entorno de trabajo, el docente aclara que terminal o IDE es cuestión de gusto. Él prefiere la terminal porque facilita el paralelismo: tener muchas terminales con loops corriendo durante horas mientras uno solo monitorea, que es la forma de trabajar que hoy defienden quienes hablan de loop engineering.

## 11. Optimizar en el espacio de prompts

Probar prompts a mano tiene un problema: la combinatoria explota. Cada prompt puede funcionar distinto según la temperatura y los demás parámetros de inferencia, y todo eso se multiplica por la cantidad de modelos disponibles. Probar prompt tras prompt, como se hacía con el prompt engineering manual, nunca llega a cubrir el espacio.

La salida es trasladar a Software 3.0 la misma estructura de Software 2.0, y acá está la analogía que conviene entender bien:

- La **arquitectura** pasa a ser **los modelos que elegís**.
- Los **datos** pasan a ser **un conjunto de casos anotados** donde sabés cuál es la respuesta correcta (esta imagen es factura, esta no).
- El **optimizador** pasa a moverse **en el espacio de prompts y parámetros de inferencia**, en lugar del espacio de pesos. DSPy es un ejemplo de optimizador de este tipo.

Esta es la conexión con la analogía de la clase introductoria entre prompt engineering y ML versus deep learning. En ML clásico, el humano diseñaba a mano las features; en deep learning se dejó de diseñar y se lanzó un optimizador que encontrara la representación. Con los prompts pasa lo mismo: el prompt engineering manual es el equivalente al diseño manual de features, y lanzar un optimizador sobre el espacio de prompts es el equivalente al salto a deep learning. La lección del deep learning, dice el docente, es “no intentes hacer el programa a mano: lanzá un optimizador y que encuentre el mejor”. Para vos, que conocés la búsqueda de hiperparámetros, la intuición es cercana: el prompt pasa a ser un eje más de búsqueda, junto con la temperatura y la elección del modelo.

Hay una diferencia técnica importante: **el espacio de prompts no es diferenciable**. No hay gradiente que te diga cómo cambiar el texto para mejorar. Por eso el optimizador tiene que ser **otro modelo**: le mostrás qué prompts probaste y cómo funcionaron, y le pedís que proponga el siguiente. Lo mismo se puede hacer con otras dimensiones, por ejemplo pidiéndole que proponga qué combinación de inputs darle al modelo.

### The Bitter Lesson y el lugar del ingenio

Esto se apoya en *The Bitter Lesson* de Rich Sutton: todo el ingenio que pongamos en diseñar a mano una solución va a perder contra un método basado en cómputo que explore las combinaciones, porque el cómputo se duplica aproximadamente cada dos años. De ahí la consigna de dejar el prompt engineering artesanal (cambiar el prompt, probar, volver a cambiarlo) y hacer lo que hace cualquiera que trabaja con IA: lanzar un optimizador. Según el docente, eso es hoy el estado del arte en producción: primero probar un prompt con distintos modelos y, después, lanzar un optimizador sobre el espacio de prompts y quedarse con el mejor.

Pero el docente agrega una lectura propia que es clave: el texto de Sutton no dice que el ingenio no sirva. **El ingenio sirve para decidir cuando el cómputo te restringe.** Nunca tenés cómputo infinito, y ahí entra elegir bien: si es un problema de clasificación de imágenes, un modelo chico basado en convolucionales, barato de correr y fácil de fine-tunear, es una buena decisión; agarrar un modelo gigante open source y entrenarlo es una mala decisión. Elegir el modelo, la arquitectura, el tipo de aprendizaje y el benchmark es donde se juega tu criterio.

### Complementos: código discreto, loops y ensambles

Cuando ningún prompt llega a la performance necesaria, hay otras herramientas. Podés escribir **código discreto** que ayude (por ejemplo, un detector de QR hecho a mano comparando píxeles) y unificar río abajo con un foundation model: “mi clasificador dijo que es factura, mi script detectó un QR; decidí”. Eso es un workflow. Si lo metés en un **while loop**, evaluás el mismo documento cien veces y agregás: 98 contra 2 es factura; 50 y 50 es duda. Un alumno suma la idea de los **ensambles**: usar cien modelos distintos, ninguno excelente, y combinar sus respuestas, como en un random forest. Todo eso también entra como ejes del espacio de búsqueda.

### Descomponer el problema

Otro alumno plantea un caso real más complejo: un grafo que conecta comercios, clientes y medios de pago, donde los modelos funcionaban bien en cada parte pero metían mucho ruido al querer conectarlo todo. La respuesta vuelve a la definición de programa. Lo que describió no es un programa: es una composición de muchos programas chicos (uno que da un score crediticio, otro que describe la forma del grafo, otro que dice si algo es óptimo), y meter todo en uno solo probablemente funcione mal. El trabajo de ingeniería empieza por decidir **en qué programas vas a romper el problema**. Después se puede probar el enfoque de una sola vez (todos los inputs, todos los outputs) y optimizar en el espacio de prompts, incluyendo cómo se le dan los inputs (la base entera, valores derivados, vectores), siempre con un optimizador que, por lo dicho antes, tiene que ser otro modelo.

### Costo y “tortugas hasta abajo”

El costo de todo esto es enorme, y eso explica las inversiones gigantes en GPUs de las que se habla: explorar estos espacios, tanto en parámetros como en Software 3.0, es computacionalmente carísimo, porque la dimensionalidad del espacio es inmensa. Por eso también existe todo un campo de optimizadores: dado que no hay cómputo infinito, cómo explorar el espacio de la forma más eficiente. Hay optimizadores que dan grandes saltos, espacios continuos y espacios discretos (donde algunos optimizadores no funcionan) y métodos como Monte Carlo, que encontró una forma eficiente de explorar espacios de búsqueda gigantes. Sobre si quedarse con un máximo local o el global, la respuesta práctica es que **te quedás con lo mejor que puedas encontrar**; probar que algo es el óptimo global es otra pregunta, mucho más teórica.

El docente cuenta que su trabajo de ese mes es justamente armar un optimizador de prompts mejor: un modelo que sugiera qué modelos probar, cien prompts por modelo elegidos para mapear bien el espacio y luego los parámetros de inferencia. Y usa la imagen de las **tortugas hasta abajo** (la del mito de la Tierra sostenida por una tortuga, que a su vez está sostenida por otra tortuga): optimizás el prompt, después el optimizador que propone prompts, después el que genera los datos, después la elección de modelos… nunca termina.

## 12. Geometría del espacio: dimensionalidad y densidad

Para cerrar la parte conceptual, el docente vuelve a lo que considera más importante de la clase: entender la forma del espacio en el que buscamos.

La **dimensionalidad** crece rapidísimo. Un parámetro de inferencia con diez valores posibles da diez programas; dos parámetros dan cien; tres forman un cubo de mil. Una red de 49 millones de parámetros (pocos para los estándares actuales), donde cada parámetro es continuo y puede tomar muchísimos valores, genera un espacio de búsqueda absurdamente grande. Esa es la **maldición de la dimensionalidad**.

A eso se suma el **sparsity problem**: los buenos programas pueden estar aislados, con un buen programa en una esquina del cubo rodeado de programas malos y otro en la esquina opuesta. Un optimizador que llega a uno de esos puntos puede quedar atascado, porque todo lo que tiene alrededor es peor. No solo el espacio es enorme: los buenos programas son pocos y están dispersos.

La situación ideal es encontrar **regiones con alta densidad de buenos programas**, donde el optimizador se mueva y siga encontrando soluciones que sirven. Y esto explica por qué los foundation models fueron tan revolucionarios: son **una compresión de un buen program space**, una región ya densa en programas útiles, que se explora mucho más eficientemente con prompts. Moverse entre distintos foundation models, cada uno con buenas regiones, es usar el ingenio para encontrar buenos programas.

## 13. Qué funciona hoy en producción y cómo pensar los costos

Un alumno pregunta para qué usa el docente los prompts optimizados, y la respuesta lleva a qué tiene valor económico en 2026. Según su experiencia en una startup que desarrolla productos para empresas, los casos que funcionan son:

- **Ingesta de documentos.** Hay empresas con decenas de personas cargando a mano documentos escritos. Un clasificador y un extractor a JSON, con un human in the loop que corrige, reemplazan buena parte de ese trabajo; y las correcciones sirven luego para entrenar (en 3.0, cambiando prompts; en 2.0, tocando parámetros).
- **Auditoría de procesos.** Un programa recibe un conjunto de políticas y responde si se cumplen o no; otro recomienda aprobar o rechazar.
- **Triage o decisión.** Un programa con output enum que, dado el contexto, elige la mejor opción (por ejemplo, qué proveedor asignar). Muchas veces funciona desde el primer intento con un buen prompt; si no, se recorre el camino de probar modelos, optimizar prompts y eventualmente entrenar.

El valor, insiste, hoy está menos en lo conversacional y más en clasificar, segmentar, extraer, decidir y auditar. Usar un modelo para ser más productivo (pedirle un resumen o un informe) es otro dominio; hacer un agente conversacional tiene valor, pero no deja de ser buscar un programa.

### Software 2.0 vs. 3.0 en la práctica

Software 3.0 es mucho más **eficiente en capital** que Software 2.0. Entrenar modelos grandes es carísimo, y la clase lo pone en números: una H100 cuesta del orden de 40.000 dólares, para arrancar se necesitan varias y para estar al nivel de un laboratorio de frontera, cientos de miles. En Latinoamérica el cómputo es escaso. Con restricciones económicas o de cómputo, lo más razonable es trabajar en Software 3.0 con modelos grandes, o en Software 2.0 con modelos chiquitos.

Además, entrenar tu propio modelo trae el problema de la **infraestructura**: un modelo que te sirve un proveedor se paga por request, pero el que fine-tuneaste no te lo sirve nadie. Tenés que levantar una máquina con GPU y servirlo vos, y eso es muy complejo; trabajar en 3.0 te lo ahorra. El docente comparte una restricción concreta: en producción, lo que tiene sentido entrenar en 2.0 es lo que entra en una función serverless tipo Lambda, con unos 250 MB en total, de los cuales queda alrededor de 100 MB útiles para el modelo. Por eso se comprimen modelos con **cuantización** o **pruning**, que también se pueden leer como formas de comprimir el program space hasta quedarse con los programas que interesan en un tamaño que entre. En clasificación lo que más se usa es YOLO, chico y muy bueno; para triage hay modelos de decisión que hay que achicar; y siguen vigentes los clasificadores basados en árboles del ML tradicional.

El flujo típico es salir a producción con el modelo más potente disponible, con un prompt cualquiera, y después, para mejorar y abaratar, entrenar un modelo chico propio. El modelo grande funciona para todo, pero no llega al estado del arte en tu tarea y es caro justamente porque su espacio es enorme.

Sobre si esto se puede hacer sin presupuesto (un alumno pregunta cómo armar portfolio), la respuesta es que hay mucho que se puede hacer localmente con modelos chicos: el docente cuenta que están entrenando un modelo de transcripción para rioplatense que pesa 42 MB. La clave es el ingenio para armar el dataset correcto, elegir la arquitectura adecuada y lanzar los optimizadores correctos dentro de tus límites. La mejor medida de un buen ingeniero es si puede encontrar el programa con los recursos que tiene.

### Optimización prematura y unit economics

Otro alumno cuenta que en un trabajo le impusieron usar solo modelos de OpenAI. La respuesta: tu espacio de búsqueda pasa a ser todos los modelos de ese proveedor y los programas que contienen, y lo primero es **definir qué significa “suficientemente bueno”**. Nadie te da un premio por usar un agente; el premio es encontrar el programa que resuelve el problema de negocio con performance suficiente y que pueda salir a producción.

Y aparece una advertencia importante: cuidado con la **optimización prematura**. Primero se busca el programa que resuelve el problema, y conviene estimar cuánto vale ese problema (por ejemplo, cuánta plata se pierde cada vez que un proceso se audita mal). Los costos se optimizan después, y hay varias formas de hacerlo: un modelo más chico con más exploración de prompts, un workflow de modelos chicos que iguale al grande o un fine-tuning de un modelo que entre en tu infraestructura. Finalmente está el **unit economics**: comparar lo que cuesta el sistema, infraestructura incluida, con lo que vale la tarea. Si clasificar un documento vale un dólar y tu sistema cuesta más, no es viable.

## 14. Benchmarks: ¿qué es un buen programa?

Un alumno señala algo que el docente considera central: es muy difícil medir si un programa es bueno y, también, saber si estás buscando el programa correcto. **Un programa es bueno o malo solo respecto de un benchmark.** El mismo punto del espacio puede ser excelente según un benchmark y malo según otro. Y como el benchmark se convierte en aquello hacia lo que el optimizador empuja, definirlo mal arruina toda la búsqueda.

En el estado del arte se optimiza contra muchos benchmarks a la vez, y mejorar en una dirección empeora en otra. El ejemplo del docente es que un modelo optimizado intensamente para programar termina escribiendo peor prosa. Correr benchmarks que hicieron otros es fácil (hay frameworks tipo *evaluation harness*), y cuando sale un modelo nuevo y “es muy bueno en estos benchmarks”, lo que pasó es que se lo evaluó contra benchmarks públicos asumiendo que eso se traduce en ser bueno para tus problemas. Pero crear un benchmark nuevo para tu caso, como un agente que corrija exámenes de antropología, es muy difícil, tanto conceptualmente (hay que definir criterios con especialistas) como computacionalmente. Es un problema abierto en el que el docente trabaja con una herramienta llamada Benchy, que se ve en la clase siguiente.

Otro alumno observa que quizás estás explorando un espacio entero cuando existe otro, mucho más simple, donde casi todo funciona mejor, y simplemente no se te ocurrió. Eso lleva de vuelta al **teorema de aproximación universal**: una red feedforward densa, la más simple de todas, puede encontrar cualquier función si tenés cómputo infinito y datos infinitos. Como no los tenés, en la práctica una feedforward no sirve frente a una convolucional en imágenes o un transformer en lenguaje. Según el docente, ese es el problema de los últimos treinta años: sabemos que cualquier programa es alcanzable en teoría, y todas las arquitecturas, optimizadores y formas de entrenar nuevas intentan responder cómo encontrarlo con recursos finitos.

## 15. Una nueva forma de encontrar programas: Weight Space Programming

El cierre es una novedad muy reciente que el docente describe como posiblemente el descubrimiento más grande de los últimos años, aunque habrá que ver hasta dónde llega. Toda la clase partió de una premisa: la única forma de moverse por el program space es con un optimizador que prueba cosas a ciegas, porque no sabemos qué parámetro tocar para que el programa funcione. El paper de **Weight Space Programming** muestra que los modelos de frontera son muy buenos entendiendo una red neuronal y sabiendo qué parámetros tocar para que se comporte como queremos.

Con esto hay tres maneras de buscar programas:

1.  **Hasta 2023**: entrenar una red neuronal tocando parámetros con datos y un optimizador. Costoso y difícil.
2.  **Con los foundation models**: explorar una compresión de un buen program space probando prompts. Muchísimo más eficiente.
3.  **Ahora**: pedirle a un foundation model, en un loop de miles de iteraciones, que proponga él mismo los cambios en los pesos (“este parámetro está en 8, lo paso a 17 porque sé que funciona mejor por este otro”).

La diferencia con pedirle a un asistente que escriba un `.py` es fundamental: un `.py` solo puede representar el subconjunto del espacio que alcanzan los programas explícitos; acá el modelo explora el otro espacio, el de los pesos, que es donde viven los programas que nadie sabe escribir. Las preguntas abiertas son las de siempre: cuánto cuesta que el modelo proponga miles de modificaciones, cómo evaluar si lo que hizo está bien y cómo optimizar contra varios benchmarks a la vez. Un alumno sugiere que un laboratorio podría comparar, con la misma cantidad de intentos, la búsqueda tradicional contra la del modelo y ver cuál gana más seguido, y el docente lo toma como el tipo de experimento que construye intuición sobre qué conviene en cada momento.

## Ideas para llevarse

La idea que el docente quiere dejar es una sola. Todo problema se puede expresar como un programa, definido únicamente por su input, su output y sus types; existe un espacio de programas mucho más grande que el que los humanos pueden escribir a mano; y **entrenar es explorar ese espacio** buscando un programa que funcione suficientemente bien con los recursos que tenés. Desde esa óptica, el prompting, los workflows, los agentes, el fine-tuning, la compresión de modelos y Weight Space Programming son distintas formas de moverse por el mismo espacio. Software 2.0 se mueve tocando pesos; Software 3.0, tocando prompts, parámetros de inferencia y la elección del modelo. En ambos casos, el prompt engineering manual debería ceder lugar a optimizadores, y el ingenio se usa para decidir dónde buscar cuando el cómputo es limitado.

Hay tres problemas abiertos que atraviesan todo: definir qué es un buen programa (los benchmarks), explorar eficientemente un espacio casi infinito (los optimizadores) y elegir dónde buscar (arquitecturas y modelos). El docente cierra diciendo que arquitecturas, optimizadores y benchmarks van a cambiar, pero que estos conceptos se van a sostener durante años: no hay mérito en entrenar un modelo por sí mismo, solo en encontrar el programa que resuelve el problema. La clase siguiente se dedica justamente a benchmarks e inferencia local.
