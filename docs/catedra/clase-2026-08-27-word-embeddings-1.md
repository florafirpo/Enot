# Explicación – Similitud semántica y word embeddings (clase 1)

Inteligencia Artificial Agéntica · Clase del 27/08/2026 · Docente: no se identifica en la transcripción

Esta clase y la siguiente forman un bloque aparte dentro de la materia: son contenidos de procesamiento de lenguaje natural “clásico”, anteriores a la IA agéntica, que llegan más o menos hasta 2015. Esa época importa porque entre 2013 y 2015 explotaron los *word embeddings*, la tecnología que permitió por primera vez representar el texto de manera numérica y usarlo como capa de entrada de las redes neuronales. Todo lo que vino después, incluidos los modelos de lenguaje sobre los que se construyen los agentes, se apoya en esa idea.

El hilo de la clase va así: primero se plantea qué significa medir la similitud semántica entre palabras y de dónde sale esa similitud (la hipótesis distribucional). Después se construyen, paso a paso, las herramientas para medirla: la matriz término-contexto, la Pointwise Mutual Information y sus variantes. Con eso se introduce el concepto de word embedding y se recorre su historia: el *vector space model* con TF-IDF, la reducción de dimensionalidad con LSA y finalmente Word2Vec. La parte más interesante de la clase es mostrar que Word2Vec, que se presentó como algo totalmente nuevo, en el fondo hace lo mismo que LSA: factorizar la matriz de PMI. La clase cierra con cómo se evaluaban los embeddings, el debate “contar o predecir” y cómo se usaban en la práctica.

El docente aclaró varias veces que el objetivo no es que uno vaya a calcular embeddings a mano (hoy vienen precomputados o se entrenan dentro del propio modelo), sino entender conceptualmente qué son, porque son la primera capa de todo lo que vino después.

## Qué es la similitud semántica

Si a alguien le piden que ubique el número 25 entre 0 y 100, la respuesta es inmediata: un cuarto de la recta. Pero si le piden que ubique “felicidad” entre “amor” y “comida”, ya no hay una respuesta obvia. Y además la respuesta depende del contexto: no es lo mismo pensarlo al final de un día de trabajo sin haber almorzado que un sábado a la noche.

La similitud semántica apunta justamente a eso: ubicar la distancia entre palabras (o su inversa, la similitud) y poder decir qué tan cerca está cada palabra de cada una de las demás del vocabulario. La forma de computarla es partir de un corpus, que en NLP significa una colección de documentos o textos, y usar la estadística de cómo aparecen las palabras entre sí.

De ahí sale una consecuencia que el docente subrayó: la métrica que uno obtiene es totalmente dependiente del dataset del que parte. Si el corpus son libros de cocina, es perfectamente posible que “felicidad” quede más cerca de “comida” que de “amor”. “Depende del contexto” quiere decir, también, “depende de dónde sale lo que estoy computando”. No hay una similitud semántica universal; hay una similitud semántica *según un corpus*.

### La hipótesis distribucional

¿De dónde sale la posibilidad de computar significado a partir de estadística? El docente lo mostró con un juego. “Zabarabrán aparece de noche. Cuando hay peligro, aparece Zabarabrán. Zabarabrán puede ayudarte. Zabarabrán es un científico.” ¿Qué significa Zabarabrán? Los alumnos respondieron enseguida: un superhéroe, Batman. Nadie dijo nunca “Batman”, pero el significado de la palabra se pudo inferir mirando el contexto en el que aparece.

Esa es la idea que resume una frase de uno de los pioneros de este enfoque, de una época en la que el tema lo trabajaban sobre todo lingüistas: *“You shall know a word by the company it keeps”*, conocerás una palabra por la compañía que tiene. Semántica significa el significado de las palabras, y la apuesta es que ese significado se puede aproximar observando qué palabras aparecen alrededor de cuáles.

## La matriz término-contexto

Para convertir esa intuición en números se usa una *sliding window*, una ventana móvil. Una ventana de tamaño 5 tiene una palabra central y cinco palabras de contexto a cada lado. Uno la va desplazando por todo el corpus (por ejemplo, toda la Wikipedia) y, cada vez que una palabra aparece en el contexto de otra, suma un punto en una matriz. El resultado es la *term-context matrix*, la matriz término-contexto: en las filas las palabras centrales, en las columnas las palabras de contexto y en cada celda cuántas veces coocurrieron. En el ejemplo de la clase (con datos inventados para ilustrar), la palabra central “chacarera” tenía un 1 con el contexto “memorias” y un 2 con otra palabra, porque habían aparecido juntas dos veces.

Si la ventana es simétrica, la matriz también lo es. La razón es mecánica: si en una posición de la ventana “chacarera” es la central y “memorias” está en el contexto, unos pasos antes o después la situación se invierte. Además, la diagonal no tiene por qué ser cero, porque una misma palabra puede repetirse dentro de una ventana corta.

Esta matriz ya tiene “sabor” a significado: dice qué palabras aparecen al lado de cuáles y cuántas veces, que es exactamente lo que la hipótesis distribucional dice que hay que mirar.

## Pointwise Mutual Information: normalizar los conteos

El problema de los conteos crudos se vio con una pregunta: según la matriz, ¿qué está más asociado a “chacarera”, “vino” o “zapateo”? Ambas coocurren 10 veces con “chacarera”, y la primera reacción de la clase fue decir “da igual”. La respuesta correcta era “zapateo”, porque hay que mirar cuántas veces aparece cada palabra en total. “Zapateo” aparece 25 veces en el corpus y 10 de ellas están junto a “chacarera”; “vino” aparece 70 veces y solo 10 son con “chacarera”. El 10 de “zapateo” pesa mucho más que el 10 de “vino”. Hace falta, entonces, normalizar.

Esa normalización es la *Pointwise Mutual Information* (PMI):

PMI(w, c) = log \[ P(w, c) / ( P(w) · P(c) ) \]

El numerador es la probabilidad de que las dos palabras aparezcan juntas, una en el contexto de la otra; el denominador es lo que se esperaría si cada una estuviera repartida al azar, independientemente de la otra. La PMI mide cuánto más probable es que dos palabras coocurran respecto del azar. Si son independientes, la probabilidad conjunta es el producto de las individuales, el cociente vale 1 y el logaritmo da 0: no tienen relación. Las probabilidades se estiman con cocientes de frecuencias tomados de la propia matriz; por ejemplo, la probabilidad de “chacarera” dado “vino” es 10 sobre 70.

Para alguien de data science esto no es nuevo, y en clase salió enseguida: es la misma matemática que se usa para analizar canastas de compra. Si uno tiene un dataset de canastas con productos, puede medir qué tan probable es que dos ítems aparezcan en la misma canasta, normalizado por la probabilidad de cada ítem aislado, y en escala logarítmica porque ese tipo de datos tiene naturalmente una distribución logarítmica. Es una métrica de asociación que compara lo observado con lo esperado si no hubiera relación. El docente lo planteó como un patrón que aparece todo el tiempo en data science: una colección de “bolsas” de elementos (documentos, canastas, ventanas), normalizada por la frecuencia de cada elemento en todas las bolsas, en eje logarítmico. Las ventanas de texto son un caso más.

### PMI negativa y Positive PMI

La PMI puede dar negativa: eso pasa cuando dos palabras aparecen juntas *menos* de lo que se esperaría por azar. El problema es que, para que ese valor negativo sea significativo y no una fluctuación estadística, hace falta un corpus gigantesco. El docente hizo la cuenta: si cada palabra tiene una frecuencia de 1 en un millón, para observar de manera confiable que coocurren menos de lo esperado (por debajo de 1 en 10¹²) se necesitaría un corpus de más de 10¹² palabras.

Por eso el estándar es tratar los negativos como ruido y ponerlos en cero. Eso es la *Positive PMI* (PPMI). Un alumno preguntó si en un corpus muy grande los negativos sí podrían significar algo; la respuesta fue que sí, que podrían, y que uno podría calcular su significancia, pero que lo estándar y más simple es anularlos.

### Normalized PMI

El docente mostró otro problema de la PMI con un caso límite: dos palabras totalmente correlacionadas, que siempre aparecen juntas, como “hocus pocus” o “ping pong”. Si “hocus” siempre aparece al lado de “pocus” y viceversa, la probabilidad conjunta es igual a la probabilidad de cada una por separado. En la fórmula, eso se simplifica y la PMI queda en menos el logaritmo de esa probabilidad. La consecuencia es que la PMI da más alta cuanto más rara es la palabra.

O sea, la PMI no está del todo normalizada: si uno observa una PMI de 1,5, no sabe si es mucho o poco, porque depende del corpus y de la frecuencia de las palabras. Para corregirlo existe la *Normalized PMI* (NPMI), que divide por un factor de normalización y deja una métrica más interpretable.

### Una aplicación concreta: collocations

La aplicación histórica de la PMI fue encontrar *collocations*: secuencias de palabras que juntas forman un concepto distinto del de sus partes. “Buenos Aires” no es “buenos” más “aires”; “Villa Urquiza” no es “villa” más “Urquiza”; “Martín Fierro”, “salud mental”, “ping pong” son conceptos únicos. Si se separa el texto en palabras aisladas se pierde ese concepto, y lo que uno quiere es unir esas secuencias en un único token.

Había dos maneras. Una era tener una lista gigante de collocations ya armada. La otra era calcular la PMI con una ventana particular: de largo 1 y de un solo lado, es decir, mirando qué palabra sigue a cuál. Con esa ventana la matriz deja de ser simétrica, porque “Martín Fierro” no es lo mismo que “Fierro Martín”. Se calcula la PMI (o la NPMI) de todos los pares, se ordenan y los más altos son las collocations: secuencias que aparecen juntas mucho más de lo esperado por azar. Esto ya está implementado en paquetes, que se usan en la práctica de la clase siguiente.

El docente fue honesto con la relevancia: la probabilidad de que uno termine calculando collocations en su vida es baja (aunque no nula). Pero el concepto de PMI va a reaparecer en el corazón de Word2Vec.

## El concepto de word embedding

Un *word embedding* es una representación vectorial, con una colección de números, de cada palabra del vocabulario de un corpus. Se construye de manera que palabras semánticamente cercanas queden cerca en ese espacio, y a la inversa: puntos cercanos en el espacio tienden a tener significados relacionados.

El docente mostró un ejemplo propio: tomó listas de animales, frutas y partes del cuerpo, buscó sus vectores (de dimensión 300), los redujo a dos dimensiones para graficarlos y les puso colores según la lista. Sin haberle dicho nunca al método cuáles eran los grupos, las palabras aparecían naturalmente separadas por categoría. En ese espacio se puede calcular una distancia, y la pregunta de si “felicidad” está más cerca de “amor” o de “comida” se puede responder ahí, como alternativa a la PMI.

Hay que tener en cuenta dos cosas. Primero, es un embedding *de palabras*: cada palabra aislada es un vector, no cada documento. Segundo, la nomenclatura: el término “word embedding” se popularizó en 2013 con Word2Vec, pero la idea existe desde 1990 con otros nombres; durante un tiempo se consolidó como *vector space model*.

### Para qué se usaban (y se usan)

El uso principal, que según el docente explica el 99% de los casos, es representar texto matemáticamente para que pueda entrar a una red neuronal. Por ejemplo, para hacer análisis de sentimiento de un tweet, cada palabra se reemplazaba por su vector y esa secuencia de vectores era el input de la red.

Eso sigue vigente hoy. Cuando usamos un modelo tipo ChatGPT, hay una primera capa que toma cada token y lo representa vectorialmente: eso es un embedding. La diferencia con las técnicas viejas es que antes el embedding era fijo para cada palabra aislada (cada palabra tenía un único punto en el mapa), mientras que en las técnicas actuales el vector también depende del contexto (cada palabra *en su contexto* tiene un punto en el mapa). Un alumno preguntó si Word2Vec ya tenía en cuenta el contexto; la respuesta fue que no: cuando termina de correr, Word2Vec devuelve un diccionario en el que cada palabra aislada tiene un vector.

Además existe un uso menos frecuente: los embeddings como herramienta para investigar un corpus, algo así como hacer sociología o lingüística de un conjunto de textos. El docente contó dos trabajos propios. En uno estudiaron sesgos de género en subtítulos de películas de los últimos 50 años: para cada año tomaron las películas top, bajaron sus subtítulos y midieron la PMI entre palabras asociadas a la brillantez intelectual y los pronombres masculinos y femeninos. Hay un estereotipo estudiado según el cual la brillantez se asocia más a los hombres, y así pudieron cuantificarlo y ver cómo cambiaba en el tiempo. En el otro usaron un corpus de relatos de sueños para, sin llegar a testear, al menos apoyar o no apoyar algunas hipótesis de teoría de los sueños.

## La matriz término-documento y TF-IDF

Los primeros *vector space models* no usaban la matriz término-contexto sino la *term-document matrix*: para cada documento del corpus se cuenta qué palabras aparecen y cuántas veces. Cada palabra queda representada por el vector de los documentos en los que aparece, con la idea de que palabras que aparecen en documentos parecidos probablemente tienen significados similares.

Estas matrices son extremadamente esparsas. Si el vocabulario tiene 100.000 palabras distintas y un documento tiene 100 palabras, casi toda la columna de ese documento está en cero.

Sobre esa matriz se aplica una transformación muy conocida: TF-IDF. La frecuencia de cada palabra en el documento (TF) se multiplica por un peso que depende de en cuántos documentos aparece esa palabra (IDF), del tipo log(D / número de documentos donde aparece la palabra), siendo D el tamaño del corpus. El caso extremo es un token que aparece en todos los documentos, como el punto final: no dice nada sobre en qué documento estamos, el cociente da 1, el logaritmo da 0 y el token queda sin peso. En cambio, una palabra que aparece en 10 de 10.000 documentos recibe un peso alto (log 1.000). El efecto es levantar o bajar cada palabra según qué tan frecuente es en todo el corpus.

Una advertencia práctica: hay muchas definiciones de IDF (el docente bromeó con que hay ochenta). En algunas se suma 1, lo que levanta todos los pesos por igual; en otras no, lo que puede bajar algunos números. Si uno lo usa, tiene que chequear qué definición está aplicando.

Con esta matriz transformada cada palabra queda representada por un vector cuya dimensión es igual al número de documentos del corpus. Puede parecer absurdo, pero así se calculaban las similitudes semánticas entre palabras a fines de los 90.

### Por qué la similitud coseno

Para medir qué tan cerca están dos vectores, el estándar es la similitud coseno: el coseno del ángulo entre ellos, que va de −1 (direcciones opuestas) a 1 (misma dirección). Lo interesante que explicó el docente es *por qué* se eligió medir ángulos y no distancias. La razón es separar frecuencia de significado. Una palabra muy frecuente como “vino” tiene números grandes en todas sus coordenadas; una infrecuente como “chacarera”, números chicos. Si uno mide distancia euclídea, las palabras frecuentes nunca van a quedar cerca de las infrecuentes, simplemente porque sus vectores son más largos. El ángulo, en cambio, mira solo la dirección y le saca el efecto de la frecuencia.

Una alumna preguntó cómo se eligen los documentos. La respuesta fue que depende de la tarea: con Wikipedia, por ejemplo, un documento podía ser un artículo, una sección o un párrafo, y esa decisión no era la más importante. De nuevo, el docente aclaró que esto se cuenta como historia conceptual: hoy los embeddings se bajan ya calculados.

### La misma matriz, mirada al revés: documentos e information retrieval

La matriz término-documento no solo da una representación de cada palabra (sus filas); también da una representación de cada documento (sus columnas). Dos documentos con una distribución de palabras parecida son documentos parecidos.

Eso se usó para *information retrieval* en los años 90, por ejemplo en buscadores como AltaVista. Llegaba una consulta como “zapateo y zarandeo en el fútbol argentino”, se la trataba como un pseudo-documento (se contaban sus palabras y se ponderaban con TF-IDF) y se calculaba la similitud coseno con cada documento indexado. El resultado era el documento más cercano. Antes de Google, buscar era esto.

El docente marcó que esa representación vectorial de documentos está más emparentada con lo que hoy se llama “embeddings” (por ejemplo, los que se usan para recuperar información en un RAG) que con los word embeddings. Esto conecta con la clase de information retrieval de más adelante en la materia.

## Coocurrencia de primer y segundo orden

Hasta acá hay dos maneras de representar una palabra: por los documentos en los que aparece (matriz término-documento) o por las palabras que suele tener alrededor (matriz término-contexto). En ambos casos se puede calcular la similitud coseno entre dos palabras, pero el docente insistió en que miden cosas distintas, y que este es un concepto teórico importante.

Con la matriz término-documento, que dos palabras tengan alta similitud significa que aparecen en los mismos documentos: es una coocurrencia de **primer orden**. Con la matriz término-contexto, alta similitud significa que las dos palabras tienen los mismos vecinos: si “chacarera” aparece mucho con “vino” y “zapateo” también, sus vectores son paralelos. Es una coocurrencia de **segundo orden**: no importa si las dos palabras aparecen juntas, sino si aparecen *con las mismas* palabras.

La lingüística tiene nombres para estos dos tipos de asociación. La asociación **sintagmática** es la de primer orden: palabras que suelen aparecer juntas, como “mostaza” y “hamburguesa”. La asociación **paradigmática** es la de segundo orden: palabras que comparten vecinos y son, en algún sentido, intercambiables, como “mostaza” y “ketchup”.

El ejemplo que mejor muestra la diferencia es el de los sinónimos. “Can” y “perro” casi nunca aparecen en el mismo documento: el autor usa una u otra. Por eso su similitud de primer orden es muy baja, y en la matriz término-documento parecería que no tienen relación. Pero las palabras que rodean a “can” son muy parecidas a las que rodean a “perro”, así que en la matriz término-contexto su similitud de segundo orden es alta. Si lo que uno busca es capturar significado parecido (como sinónimos), la coocurrencia de segundo orden es la que importa. En la práctica, igual, la mayoría de las palabras con coocurrencia de segundo orden también tienen algo de la de primero: “mostaza” y “hamburguesa” aparecen en los mismos documentos y además suelen tener contextos parecidos.

## Latent Semantic Analysis: reducir la dimensionalidad

Representar cada palabra con un vector de dimensión igual al número de documentos era malísimo: vectores gigantes, esparsos, difíciles de computar y con mucha variabilidad. La idea que surgió fue reducir la dimensionalidad de esa matriz.

Para eso se usó la descomposición en valores singulares (SVD). La matriz de T términos por D documentos se descompone en el producto de tres matrices (T×M, una diagonal M×M y M×D) y después se trunca: en lugar de quedarse con las M dimensiones, uno elige quedarse con K (100, 300, 1.000). Como SVD ordena las dimensiones según cuánta variabilidad de los datos explican, las que se descartan son las de menor variabilidad, las más ruidosas, y la matriz que se reconstruye después de tirarlas no es muy distinta de la original. Como resumió el docente más tarde, la filosofía es separar el contenido del ruido: quedarse con las dimensiones “donde los datos se mueven”, donde está guardada la información.

Hubo un matiz que vale la pena retener. SVD se parece a PCA en que ordena dimensiones por variabilidad, pero PCA trabaja centrando los datos en su centro de masa, mientras que SVD queda anclado en el cero. En este problema eso es clave: como lo que se mide son ángulos, el origen tiene significado y no conviene moverlo.

Después del truncamiento, cada palabra queda representada por K números, con K elegido por uno. Ese vector es su word embedding. A esta técnica (SVD truncado aplicado a la matriz término-documento o, como alternativa, a la matriz término-contexto) se la llamó *Latent Semantic Analysis* (LSA). El LSA clásico es determinístico: no hay semilla, dada la matriz el resultado es siempre el mismo. Las semillas aparecen recién en las versiones probabilísticas que se crearon para poder computarlo en datasets grandes.

La historia tiene un dato curioso. LSA surgió en 1990 para búsqueda de información, pero en 1997 un psicólogo, Landauer, lo usó para representar palabras y planteó que esto podía ser un buen modelo de cómo aprendemos las palabras las personas. No afirmó que el cerebro funcionara así, pero lo propuso como hipótesis. Fue la primera vez que alguien representaba palabras en un espacio de dimensión reducida; en ese momento todavía se hablaba de *vector space models*.

### Las dimensiones como tópicos

Al mirar las dimensiones de LSA, se empezó a notar que a veces tenían sentido: las palabras que se “prendían” en una dimensión (que tenían valores altos en ella) compartían un significado. De ahí nació el concepto de tópicos y el *topic modeling*. La línea siguió evolucionando: de SVD se pasó a una versión probabilística, después a *Latent Dirichlet Allocation*, después los tópicos se empezaron a calcular con redes neuronales mediante *document embeddings*, y hoy directamente se le puede pasar una colección de documentos a un LLM y pedirle qué tópicos contiene. Es un ejemplo de cómo muchas técnicas estadísticas fueron reemplazadas por soluciones basadas en LLMs.

### ¿Cuántas dimensiones? La historia del 300

Landauer buscó la dimensionalidad óptima de LSA con un test de sinónimos (más adelante se explica cómo funcionaba) y le dio 300. Ese número se quedó: durante años se siguió usando 300 en técnicas totalmente distintas. La hipótesis del docente es más sociológica que técnica: si uno elige el mismo parámetro que un paper anterior, ningún revisor le pregunta por qué.

Pero en el fondo, K tiene que ver con cuántos temas distintos hay en el corpus. En experimentos del docente con un dataset de diarios, el K óptimo para cierta tarea se relacionaba con la cantidad de grandes secciones del diario (alrededor de 13). Es decir, depende de qué se está midiendo y de la estructura de tópicos del corpus. En esa época también circulaban recetas prácticas, como descartar las primeras dimensiones (las de mayor variabilidad) porque a veces no eran significativas.

### La similitud coseno no es un valor absoluto

Otro punto práctico: la similitud coseno es comparativa. Que dos palabras tengan un coseno de 0,5 no dice nada en sí mismo; solo dice algo comparado con las similitudes de otras palabras. Además, el valor depende de la dimensionalidad: con vectores muy largos los puntos se esparcen en el espacio y las similitudes tienden a dar más chicas. Por eso solo tiene sentido comparar similitudes dentro del mismo corpus y con el mismo modelo entrenado. Decir “en este corpus me da 0,4 y en este otro 0,6” no es una comparación válida.

## Word2Vec

En 2013 apareció Word2Vec, a partir de un paper de Mikolov y colegas en Google. Además de proponer la técnica, Google abrió todo: el código, un dataset de textos y los embeddings ya calculados. Es en esta época cuando empieza a usarse el término *word embedding*.

### El planteo original, como “red neuronal”

Word2Vec se presentó como una red neuronal. Hay una palabra central y palabras de contexto, y la red calcula qué tan probable es ver cada palabra de contexto dada la palabra central. Con una ventana de tamaño 1, por ejemplo, “chacarera” es la central y hay una palabra a cada lado.

La palabra central se representa como un *one-hot vector*: un vector con ceros en todas las posiciones y un 1 en el índice de esa palabra. Ese vector se multiplica por una matriz W, el resultado por una matriz C, y a la salida se aplica una softmax, que convierte el resultado en una distribución de probabilidad sobre el vocabulario. La función objetivo es maximizar la probabilidad de las palabras que efectivamente aparecieron alrededor: que P(palabra de la izquierda \| chacarera) y P(palabra de la derecha \| chacarera) sean lo más altas posible. Esto se optimiza en cada paso de la ventana a lo largo de todo el corpus: en cada posición, los pesos de W y de C se mueven un poco en la dirección que mejora esa probabilidad.

### Por qué no es realmente una red neuronal

El docente desarmó esa presentación. Como la entrada es un one-hot, multiplicarla por W equivale simplemente a tomar una fila de W: el vector de “chacarera”. Y de la salida de la multiplicación por C solo interesa la columna de la palabra de contexto. Entonces todo lo que parecía una red neuronal se reduce a un producto entre dos vectores: la fila de “chacarera” en W y la columna de la palabra de contexto en C. Ese producto se exponencia y se divide por la suma de los productos de “chacarera” con todas las demás columnas.

Acá aparece una conexión con lo anterior. La similitud coseno es un producto escalar normalizado; un producto escalar sin normalizar también guarda la idea de similitud. Entonces lo que Word2Vec calcula es qué tan cerca está el vector de la palabra central del vector de la palabra de contexto, en relación con qué tan cerca está de todas las demás palabras. Es una manera de medir similitud.

Cuando Word2Vec apareció se hablaba de redes neuronales e incluso de “hacer deep learning sobre las palabras”. Con el tiempo, investigadores más cautos señalaron que en realidad era una optimización sobre un producto matricial, y la comunidad dejó de describirlo como red neuronal. El docente lo ilustró con el libro de Jurafsky (Stanford), que para él es la referencia más importante de NLP clásico y la que recomienda para profundizar: en sus primeras versiones presentaba Word2Vec como red neuronal y después pasó a describirlo en términos de productos matriciales.

### Negative sampling

Calcular el denominador de la softmax, el producto de la palabra central con todo el vocabulario, era carísimo. La solución fue el *negative sampling*. No es una aproximación de la fórmula anterior, pero sigue su misma filosofía. En lugar de comparar con todo el vocabulario, se samplean K palabras al azar (por ejemplo “él”, “gorro” y “pomelo”) y se le pide al optimizador dos cosas: que la palabra central y la palabra de contexto real queden cerca, y que las palabras al azar queden lejos. La función de costo usa una sigmoide sobre los productos: si el producto entre central y contexto es grande, la sigmoide se acerca a 1, que es lo deseado; para los negativos se busca que el producto sea lo más chico posible. Se optimiza con descenso de gradiente, y K (cuántas palabras negativas se toman: tres, cinco, diez) es un hiperparámetro.

### Qué pasa geométricamente en cada paso

En 2016, tres años después de Word2Vec, se publicó un paper (“word2vec Parameter Learning Explained”) que se sentó a derivar la función de costo para entender por qué funcionaba. El docente lo usó para señalar un rasgo del área: las cosas se prueban, se ve empíricamente que funcionan, la gente las adopta y la teoría llega mucho después, con poca gente investigando por qué funciona lo que funciona.

Lo que muestran las derivadas es muy intuitivo. En cada paso del descenso de gradiente, la palabra de contexto (“cantadas”) se mueve en una dirección paralela al vector de la palabra central (“chacarera”), es decir, se le acerca. El tamaño del paso depende de qué tan lejos estén: si ya están muy cerca, la sigmoide ya está cerca de 1 y casi no hay paso; si están lejos, el paso es más grande. Con la misma lógica, las palabras sampleadas al azar se alejan de la central, y se alejan más cuanto más cerca estaban. Y la palabra central, a su vez, se acerca a su contexto real y se aleja de las palabras al azar. Un alumno observó que eso era justamente lo que definía la función objetivo, y el docente le dio la razón: la filosofía ya estaba en la definición; lo que agrega la derivada es ver que los pasos son literalmente paralelos a los vectores.

Visto así, Word2Vec es palabras moviéndose en el espacio: en cada ventana, las que realmente aparecen juntas se acercan y las sampleadas al azar se alejan. Y eso explica por qué palabras con contextos parecidos terminan cerca. Si dos palabras suelen tener las mismas palabras alrededor, en cada paso se acercan a los mismos vectores de contexto, es decir, dan aproximadamente los mismos pasos en las mismas direcciones (las palabras negativas, en cambio, se alejan en direcciones al azar). El caso límite son los sinónimos: como sus contextos son prácticamente iguales, se mueven igual y terminan juntas. Es la coocurrencia de segundo orden de antes, ahora obtenida por optimización.

### El resultado central: Word2Vec factoriza la PMI

El docente presentó después un trabajo de Levy y Goldberg, “la gente que de verdad se dedicó a investigar por qué funciona lo que funciona”. En lugar de pensar Word2Vec como una sucesión de pasos sobre ventanas, plantearon la optimización global. Si “perro” aparece 10 veces en el contexto de “árbol” en el corpus, esa pareja se va a optimizar 10 veces; entonces se puede escribir una gran sumatoria sobre todos los pares de palabras, cada uno pesado por cuántas veces coocurre, y ese número sale directamente de la matriz término-contexto.

Al buscar el mínimo de esa función, encontraron que el óptimo se da cuando el producto de las dos matrices de vectores (la de palabras centrales y la de contexto) es igual a la matriz de PMI desplazada en log K, donde K es el número de muestras negativas.

Lo que hay que llevarse es esto: LSA toma la matriz (de PMI o de conteos), la descompone en tres matrices, trunca y usa una de ellas como representación de las palabras. Word2Vec toma la matriz de PMI, le resta un número y también la descompone en un producto de matrices; solo que esa descomposición la hace mediante una función de optimización. En el fondo, las dos técnicas trabajan sobre la misma matriz de PMI. Todo el recorrido de la clase, desde contar coocurrencias en ventanas hasta la PMI, termina siendo el corazón teórico de Word2Vec.

### Skip-gram, CBOW y qué matriz usar

Todo lo descrito corresponde a uno de los dos algoritmos de Word2Vec: **Skip-gram**, que a partir de la palabra central predice las de contexto. El otro es **CBOW**, que hace lo inverso: toma las palabras de contexto como entrada y estima la palabra central. Word2Vec es, en realidad, el nombre de la colección de ambos. A la larga ganó Skip-gram, y hoy cuando se habla de Word2Vec normalmente se habla de él.

Como hay dos matrices, W y C, hay dos embeddings posibles para cada palabra: su fila en W o su columna en C. Por convención la comunidad usa los vectores de W. Algunos trabajos promedian ambos.

### Las dimensiones no significan nada por separado

A diferencia de lo que se insinuaba con los tópicos de LSA, en Word2Vec cada dimensión aislada no significa nada. Que “chacarera” tenga 0,064 en la dimensión 1 no dice nada, y ni siquiera hay un orden entre dimensiones: la 1 no es más importante que la 2. Son dimensiones en las que se comprime la información. El significado aparece cuando se miran todas a la vez: en el espacio completo, las palabras cercanas tienen asociaciones semánticas.

### Las analogías lineales

En los papers de 2013, Mikolov encontró algo que nunca se había visto: relaciones lineales en el significado de las palabras. Si al vector de “rey” se le resta el de “hombre” y se le suma el de “mujer”, el resultado cae cerca de “reina”. Dicho de otra forma, reina − mujer ≈ rey − hombre: la relación vectorial entre reina y mujer es parecida a la que hay entre rey y hombre. No pudieron explicarlo en su momento, pero encontraron el patrón. Aparecieron analogías de todo tipo: mujer es a hombre lo que tía es a tío; París es a Francia lo que Buenos Aires es a Argentina. Con eso se armó un dataset de analogías que pasó a usarse como tarea para evaluar qué tan bueno es un embedding.

## ¿Cómo se sabe si un embedding es mejor que otro?

Cuando salió Word2Vec, sus autores dijeron que funcionaba mejor que todo lo anterior. Para poder afirmar algo así hacían falta tests, y la clase repasó tres.

El primero fue el mismo que usó Landauer para LSA: preguntas de sinónimos tipo TOEFL. Se da una palabra (por ejemplo *hue*), su sinónimo (*color*) y tres palabras distractoras, y el embedding acierta si deja al sinónimo más cerca que a los distractores. Landauer armó un set de 80 preguntas, a partir de manuales escolares, y con el porcentaje de aciertos eligió el famoso 300. El problema es que ese dataset era muy ruidoso y además privativo.

El segundo tipo de test usa juicios humanos de similitud. Se le pide a un grupo de personas que puntúe qué tan parecidos les parecen pares de palabras (“tigre” con “tigre”, 10; “Maradona” con “fútbol”, algo alto; “profesor” con “pepino”, en promedio 0,3) y se promedian las respuestas. Después se calcula la similitud de esos mismos pares con el embedding y se mide la correlación entre ambas listas. El embedding cuyas similitudes correlacionan más con las humanas es el mejor.

El tercero es el de analogías: por ejemplo, Atenas es a Grecia lo que París es a ¿?; si la palabra más cercana al resultado de la operación es “Francia”, se suma un acierto; si no, cero. Se cuenta el porcentaje de aciertos sobre todo el dataset. En el paper original, Word2Vec ganaba en casi todo y en particular capturaba las analogías mucho mejor que LSA.

## ¿Contar o predecir? El debate LSA vs. Word2Vec

En 2014 salió un paper con un título que era un juego de palabras: “Don’t count, predict!”. LSA representaba el “contar” y Word2Vec el “predecir”, por su presentación como red neuronal que predice palabras de contexto. Comparaban Word2Vec con varios modelos (LSA lo probaron solo a medias) y Word2Vec ganaba en todo, así que la recomendación era usarlo. Lo que se mostró después es que la oposición era falsa: los dos “cuentan”, los dos son descomposiciones matriciales y solo difieren en la función que optimizan.

El docente señaló también un patrón de la investigación: cuando salió Word2Vec se cambiaron las palabras para que pareciera algo totalmente distinto, cuando en el fondo era una nueva técnica de embedding dentro de la misma familia.

El golpe de gracia vino otra vez de Levy y Goldberg, que encontraron la trampa: Word2Vec tenía hiperparámetros elegidos con muchísimo esfuerzo por un equipo de Google. Algunos de esos “truquitos” eran:

- en la ventana, las palabras más cercanas a la central pesan más que las lejanas;
- las palabras muy frecuentes, por encima de cierto umbral de probabilidad, se submuestrean;
- al samplear los negativos no se usa la distribución de frecuencias tal cual, sino una suavizada con un factor α = 3/4 (nadie sabe muy bien de dónde salió; probablemente probaron muchas opciones).

Lo que hicieron fue trasladar esos mismos trucos a LSA, construyendo sus equivalentes para PPMI + SVD. Con eso, LSA dejó de dar peor y pasó a ser comparable con Word2Vec. Es decir, Word2Vec era mejor que LSA solo por esos trucos. En la comparación también aparecía GloVe, otro embedding muy conocido creado en Stanford, que el docente describió como parecido a Word2Vec y sin evidencia fuerte de que sea mucho mejor.

El docente sumó su propia experiencia: en un trabajo de 2017 comparó LSA con Skip-gram en cierto dataset y tarea, y encontró que en corpus muy chicos, algo común cuando se trabaja con idiomas con pocos recursos, LSA le ganaba por mucho a Word2Vec. La interpretación es que Word2Vec no tiene suficientes ejemplos para dar sus pasitos de optimización, mientras que LSA captura mejor la variabilidad de los datos. En datasets grandes, en cambio, Word2Vec le ganaba un poco y además escala mejor: descomponer una matriz gigante es muy costoso, y para datasets muy grandes LSA requiere versiones probabilísticas, que rinden peor.

La conclusión fue que no existe una técnica mejor que otra en general; depende del uso. El objetivo final de un word embedding es que en el espacio vectorial las palabras de significado similar queden cerca y las no relacionadas lejos, porque eso es lo que se aprovecha cuando el embedding entra como capa de una red neuronal o de cualquier otro cómputo.

### ¿Sirven para algo las operaciones vectoriales?

Sobre las analogías, el docente fue escéptico: en toda su carrera profesional nunca se cruzó con un caso de uso real de sumar y restar vectores de palabras. Un alumno propuso una conexión con los modelos actuales: en un transformer, el ajuste por contexto (por ejemplo, distinguir “banco” de plaza de “banco” financiero) se parece a sumarle un vector al embedding de la palabra. El docente no lo descartó y lo vinculó con un cambio de época: al principio los embeddings se calculaban aparte y se usaban como input de una red (por ejemplo una LSTM); después pasaron a ser un parámetro más del modelo, que se entrena junto con todo lo demás. Y en el mundo de las redes neuronales lo que importa es que el embedding represente el mundo lo mejor posible, no el estudio de un dataset en particular. Para analizar un dataset acotado, LSA puede seguir siendo la mejor opción.

## Cierre: de calcularlos a bajarlos

En la práctica, con el tiempo nadie calculaba sus propios embeddings: se bajaban los de otros. Google corrió Word2Vec sobre un dataset de Google News de unos 100.000 millones de palabras y publicó los vectores. GloVe hizo lo mismo con versiones entrenadas sobre Wikipedia, Common Crawl y Twitter. Después Facebook contrató a Mikolov, que creó FastText, un algoritmo parecido a Word2Vec que además mira partes de las palabras, y publicó embeddings entrenados sobre Wikipedia en una enorme cantidad de idiomas, incluido el español. Si una tarea puntual necesita word embeddings, se bajan y se usan.

El uso típico hasta alrededor de 2016 era sencillo: para clasificar un documento, se tomaban los embeddings de todas sus palabras, se promediaban para obtener un “significado promedio” y ese vector se le pasaba a un clasificador, por ejemplo un random forest. Funcionaba bien. Después llegó la etapa en que los embeddings pasaron a ser parte del modelo.

## Ideas para llevarse

El significado de una palabra se puede aproximar por las palabras que la rodean, y toda la clase es un recorrido de cómo convertir esa intuición en vectores. La PMI es la pieza central: normaliza las coocurrencias contra lo esperado por azar (es la misma métrica de asociación que en el análisis de canastas), se recorta a PPMI porque los negativos son ruido en corpus de tamaño realista, y se puede normalizar más con NPMI. Hay que distinguir qué mide cada representación: la matriz término-documento captura coocurrencia de primer orden (asociación sintagmática), mientras que la término-contexto captura la de segundo orden (asociación paradigmática), que es la que acerca a los sinónimos. LSA reduce la dimensionalidad con SVD truncado para separar información de ruido; Word2Vec llega a algo equivalente mediante optimización con negative sampling, acercando palabras que coocurren y alejando las sampleadas al azar. El resultado teórico de Levy y Goldberg muestra que, en el fondo, ambos factorizan la matriz de PMI, y que la ventaja de Word2Vec venía en buena parte de sus hiperparámetros. No hay técnica universalmente mejor: LSA rinde mejor en corpus chicos y Word2Vec escala mejor en grandes. La similitud coseno solo se puede comparar dentro del mismo corpus y modelo. Y lo más importante para el resto de la materia: los word embeddings son la primera capa de todas las redes neuronales que vinieron después; la diferencia de los modelos actuales es que el vector de cada palabra pasó a depender de su contexto. La historia continúa en la clase siguiente.
