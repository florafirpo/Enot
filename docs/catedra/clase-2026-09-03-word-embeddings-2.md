# Explicación – Word embeddings (clase 2): comparación de corpus y práctica con Word2Vec

Inteligencia Artificial Agéntica · Clase del 03/09/2026 · Docente: no se identifica en la transcripción

La clase tiene dos mitades bien distintas, y conviene leerlas con esa división en la cabeza. La primera termina un tema que quedó abierto: cómo comparar dos colecciones de textos para encontrar las palabras que de verdad las diferencian. Esta parte es conceptual y tiene bastante de estadística, pero el foco no está en las fórmulas. Lo que importa es entender por qué la manera más intuitiva de hacerlo está mal y qué hay que corregir. La segunda mitad vuelve a los word embeddings con una práctica demostrativa: entrenar Word2Vec sobre un corpus de reviews de películas, explorarlo, compararlo con LSA y con un embedding preentrenado de Google, y jugar con analogías y similitudes para ganar intuición sobre qué computa realmente un embedding.

El hilo que une las dos mitades es la misma idea de fondo: todo lo que estas técnicas devuelven son asociaciones estadísticas que salen de cómo co-ocurren las palabras en un corpus particular. En la comparación de corpus esa idea aparece como “hay que normalizar bien y mirar la significancia”. En los embeddings aparece como “la similitud no mide una propiedad del mundo, sino cuánto aparece una palabra en el contexto de otra en estos textos”. Si te llevás eso, te llevás la clase.

## 1. Comparar corpus: dos preguntas que suelen confundirse

Cuando tenés dos datasets de texto y querés saber en qué se diferencian, en realidad podés estar haciendo dos preguntas distintas.

La primera es temática: cuáles son los grandes temas de cada colección y cómo cambia su peso de una a otra. Esa pregunta se responde con topic modeling. Dada una colección de documentos, encontrás los temas que se tratan en total y después mirás cuáles aparecen más en un dataset que en el otro.

La segunda pregunta es más fina y es la que ocupa esta parte de la clase: cuáles son las palabras cuya frecuencia de uso más se diferencia entre los dos corpus. El ejemplo típico es el de los diarios o los blogs que muestran “las palabras que diferencian los discursos del político A y del político B”, normalmente en forma de nube o de lista de nueve palabras.

El docente lo presenta explícitamente como un ejemplo de cómo se hace mal. Lo habitual es tomar las palabras más frecuentes de cada corpus. Si hacés eso con todos los discursos de dos políticos, arriba no aparecen “pueblo” ni “gobierno”: aparecen “el”, “a”, “y”. Son stop words, palabras de función que se usan muchísimo pero no dicen nada sobre el contenido. Entonces quien arma la nube empieza a tirar palabras de arriba hacia abajo, a criterio propio, hasta quedarse con las que le “gustan”.

El problema de fondo no es solo lo arbitrario de ese filtrado. Lo que resulta es una lista de palabras frecuentes, no de palabras diferenciales, y esas son dos cosas distintas. Palabras como “política”, “economía” o “dólar” probablemente estén muy arriba en los dos discursos. Aparecen en las dos nubes, pero no diferencian nada. Lo que se busca en realidad son palabras que aparezcan mucho en uno y poco en el otro y, además, que esa diferencia sea significativa y no producto del azar. Esa doble exigencia, diferencia grande y diferencia confiable, es la que ordena todo lo que sigue.

## 2. Normalizar bien: el ejemplo de IMDB

Para construir la intuición, la clase usa un ejemplo del libro de Jurafsky y Martin. Jurafsky es profesor de NLP en Stanford y su libro es la referencia para toda la parte de NLP de la materia (no para la parte agéntica). El dataset es IMDB: reviews de películas, cada una con la cantidad de estrellas que puso el usuario, de 1 a 10. La pregunta es qué palabras diferencian las reviews de una estrella de las de diez.

### Primera trampa: no normalizar por el tamaño de cada grupo

El primer gráfico cuenta cuántas veces aparece “bad” en cada categoría de estrellas. Da unas 122.000 apariciones en las reviews de una estrella, que es esperable, y unas 51.000 en las de diez. Eso es raro: ¿por qué “bad” aparecería tanto en reviews entusiastas, y bastante más que en las de nueve estrellas?

Un alumno propuso la hipótesis de la interacción con otras palabras (“not bad”, por ejemplo). Es un efecto posible, pero en este caso no es el principal. La explicación es más básica: no se está normalizando por el tamaño de cada categoría. Hay muchísimas más palabras en reviews de diez estrellas que en las de nueve, y también hay un pico de volumen en las de una estrella. Contar apariciones crudas mezcla dos cosas: cuánto se usa la palabra y cuánto texto hay en cada grupo.

La corrección es la que aplicarías en cualquier análisis: para cada categoría, dividir las apariciones de “bad” por el total de palabras de esa categoría. Eso da una frecuencia relativa, del orden de cuatro “bad” cada mil palabras en la categoría de una estrella. En esa escala el patrón se acomoda: “bad” aparece proporcionalmente más en las categorías bajas que en las altas.

### Segunda trampa: comparar palabras de frecuencias muy distintas

Con la frecuencia relativa resuelta aparece un segundo problema cuando querés comparar dos palabras entre sí. “Bad” está en el orden de cuatro cada mil palabras; “horrible”, en el orden de cinco cada diez mil. Si ponés las dos distribuciones lado a lado, la de “horrible” está en otra escala y no podés ver bien cuál está más asociada a las reviews negativas. Peor todavía, una comparación ingenua puede sugerir que “horrible” está menos concentrada en una estrella que “bad”, cuando cualquiera esperaría lo contrario.

La razón es que “horrible” es una palabra mucho más infrecuente. El hecho de que sea rara en general la hace parecer débilmente asociada a cualquier categoría. Para separar la forma de la distribución de su nivel general, se hace una segunda normalización: cada frecuencia relativa por categoría se divide por la suma de las frecuencias relativas de esa palabra en todas las categorías. Así cada palabra queda expresada como una distribución sobre las diez categorías que suma uno, y ahí sí se comparan formas. Con esta vista, la distribución de “horrible” resulta más puntiaguda en una estrella que la de “bad”. Es decir, está más concentrada en las reviews negativas, que es lo que la intuición pedía.

Este indicador lo propuso otro profesor (en la transcripción el nombre del score figura como “post-score”; el docente comentó que es algo bastante obvio a lo que su autor le puso nombre propio). Con él se ven patrones lindos: “good” se centra alrededor de seis o siete estrellas, mientras que “amazing” y “great” se centran en diez, con “great” menos dispersa.

### Un paréntesis sobre las negaciones

El ejemplo de “bad” en reviews positivas sirvió para comentar cómo se trataban las negaciones antes de las redes neuronales, más o menos hasta 2015. Cuando se trabajaba con palabras aisladas y aparecía un negador (“not”), se reescribía lo que venía después como un token nuevo. “This is not good” pasaba a tener un token “not_good”, distinto de “good”. Era una forma artesanal de que el modelo distinguiera “good” de “not good”, porque un enfoque de bolsa de palabras no tiene ninguna noción del orden.

### Del score a una lista de palabras diferenciales, y su límite

Con ese score ya podés atacar la tarea original. Para cada palabra del vocabulario calculás la probabilidad de la palabra en el corpus A, normalizada por su probabilidad en el total. Ordenás y te quedás con las palabras de score más alto para A y, simétricamente, para B. Esa es una lista de palabras mucho más probables en A que en B, o que en el corpus total.

El límite de mirar solo probabilidades es serio y es el que motiva la técnica siguiente. Una palabra que aparece una sola vez en A y nunca en B tiene probabilidad condicional uno de estar en A, y entonces score máximo. Termina arriba del ranking, cuando lo más probable es que sea una fluctuación estadística: una palabra rarísima que cayó de un lado por azar. El docente marcó que esto también pasa, en menor medida, con PMI. En términos que ya conocés, es el problema clásico de estimar proporciones con muestras chicas: el estimador puntual es extremo justo donde tiene más varianza.

## 3. Otras técnicas, y por qué quedó la de Monroe et al.

El docente contó que la tarea de comparar corpus existe por lo menos desde los años 80, con papers aislados que proponen métricas distintas. Nadie hizo nunca una comparación sistemática de todas, un proyecto que él tenía pendiente de cuando trabajaba como científico. Mencionó, por ejemplo, el enfoque de entrenar una regresión lineal que clasifique entre A y B y mirar los pesos de cada palabra, que considera una buena técnica.

La técnica que terminó instalada en la cultura de NLP es la de Monroe et al. (2009), y el docente fue honesto sobre el porqué: según su interpretación, no se impuso por ser mejor que las otras. Jurafsky la usó en un paper, la explicó en su libro, y como ese libro es el central del área, la comunidad se volcó a ella. Es un buen recordatorio de que en ciencia la adopción de un método a veces tiene más que ver con dónde quedó escrito que con una comparación rigurosa.

### El log odds ratio

El paper de Monroe et al. analiza discursos del Congreso de Estados Unidos para comparar de qué hablan distintas facciones. El punto de partida es el log odds ratio, una técnica estadística conocida para testear si una palabra se diferencia entre dos grupos.

Para una palabra W (el ejemplo de clase es “perro”) armás una tabla de dos por dos: en el corpus A, cuántas veces aparece “perro” y cuántas palabras de A no son “perro”; lo mismo en B. Si A tiene un millón de palabras y “perro” aparece tres veces, tenés tres contra 999.997. El log odds ratio es el logaritmo de “apariciones de perro sobre resto de A” menos el logaritmo de “apariciones de perro sobre resto de B”.

Hay una simplificación que ayuda a leerlo. Como la probabilidad de una palabra concreta es bajísima, “el resto del corpus” es prácticamente el tamaño del corpus, y p/(1−p) es prácticamente p. Lo que queda es la diferencia entre el logaritmo de la probabilidad de “perro” en A y en B, es decir, el logaritmo del cociente de probabilidades. Leído así, el log odds ratio dice cuántas veces más probable es que la palabra aparezca de un lado que del otro, en escala logarítmica. Es una medida de tamaño de efecto: cuán grande es la diferencia.

### Los dos cambios que proponen Monroe et al.

El aporte del paper son dos modificaciones al log odds ratio directo, y cada una ataca uno de los dos requisitos del principio: que la diferencia sea robusta y que sea significativa.

El primer cambio es sumar un corpus de background. Tomás un corpus general del área, con su propia distribución de palabras, y a la frecuencia de “perro” en A le sumás la frecuencia de “perro” en el background; lo mismo para B, normalizando de forma consistente. Es como agregarle a A y a B el mismo colchón de texto general. Esto tiene dos efectos. El primero es un suavizado: si “perro” aparece una vez en A y cero en B, ya no comparás uno contra cero (que da un cociente infinito o un score máximo), sino “uno más background” contra “cero más background”, y la diferencia se vuelve razonable. Ese es exactamente el antídoto contra el problema de las palabras raras del score anterior. El segundo efecto es que se pesan más las palabras específicas de A y B que aparecen poco en el background: como el colchón las levanta poco, su diferencia entre A y B se destaca más en la comparación.

El segundo cambio es no quedarse con el tamaño de efecto y pasar al espacio de la significancia con un z-score: cuántos sigmas se aleja la métrica de cero. Cero significa que la palabra es igual de probable en A que en B; con más de dos sigmas ya se puede empezar a decir que la diferencia es significativa. Lo valioso de este paso es que combina en un solo número las dos cosas que se buscaban: que la palabra aparezca suficientes veces como para que la estimación sea confiable y que la diferencia entre corpus sea grande. Una palabra con un cociente enorme pero apoyada en dos apariciones queda con pocos sigmas. Una palabra frecuente con una diferencia moderada pero sostenida puede quedar con muchos.

El ejemplo del paper es la discusión sobre aborto en el Congreso estadounidense. Se separaron las intervenciones de demócratas y republicanos sobre el tema y se usó como background el resto de las discusiones del Congreso que no tenían que ver con aborto. Esa elección de background levanta todavía más las palabras específicas del tema. Con el z-score como medida, aparecen claramente las palabras que separan a cada grupo: unos se diferencian por términos como “woman” o “right”, y otros por términos centrados en “kill” y “baby”.

### Sobre el corpus de background: lo que se sabe y lo que no

Un alumno preguntó si el corpus de background tiene que ser completamente ajeno al tema. La respuesta del docente fue explícitamente personal: es su intuición estadística, no algo estudiado ni escrito en ningún lado. Su lectura es que el background resalta un poco las palabras que más diferencian a A y B del propio background, pero no espera que cambie mucho el resultado. El paper lo prueba un poco y tampoco muestra grandes cambios. Para él, con un log odds ratio llevado a z-score alcanza para que la técnica funcione.

Como alternativa al background mencionó el smoothing estándar, que podés pensar como un background donde cada palabra aparece una vez: le sumás uno a cada conteo. En la jerga del paper eso es un “non-informative Dirichlet prior”, y el método con un corpus de background real se llama “informative Dirichlet prior”. El docente advirtió que los nombres suenan bayesianos, pero la técnica es totalmente frecuentista. Agregó que mucha gente de computación que trabaja en el área no sabe tanta estadística y mezcla conceptos. Como data scientist es un buen momento para notar que estás viendo un estimador suavizado con pseudoconteos, no una inferencia bayesiana en sentido estricto.

Al final de la práctica volvió sobre el tema con una anécdota que refuerza el punto: parte de la explicación de esta técnica en el libro de Jurafsky estaba mal escrita, él le escribió, Jurafsky le dio la razón y la corrigió. Lo usó para ilustrar algo que ve mucho en el área: la gente encuentra que algo funciona y no se detiene a estudiar por qué. Eso está cambiando un poco ahora que el impacto de los LLMs despertó interés en entender sus mecanismos.

### Qué se espera para el examen

Una alumna preguntó qué se espera en el examen teórico, y la respuesta sirve como guía para toda la parte de NLP. No hay que memorizar fórmulas ni saber explicar una ecuación concreta. Si te preguntan cómo armarías la nube de palabras que diferencia los discursos sobre aborto, la respuesta no puede ser “agarro las palabras más frecuentes de cada uno”. Tenés que saber que existen técnicas que tienen en cuenta las diferencias estadísticas, y entender conceptos simples pero importantes como que hay que normalizar bien. Lo mismo vale para la clase anterior de word embeddings, que fue muy matemática a propósito: lo que se evalúa es entender qué es un word embedding y la esencia de cómo funciona, no el detalle de sus ecuaciones.

## 4. Práctica: Word2Vec sobre IMDB

La segunda mitad es demostrativa. El docente aclaró que el código no es lo importante: el objetivo es ganar intuición sobre qué son los word embeddings y cómo se comportan.

Para eso usa Gensim, un paquete clásico e histórico para embeddings de palabras. Hay un énfasis que conviene no perder: acá cada vector representa una palabra. Hoy, cuando se habla de embeddings, casi siempre se trata de embeddings de documentos u oraciones, lo que se usa en las bases vectoriales. Lo de esta clase es el antecedente de eso, una palabra por vector.

El corpus es otra vez IMDB. Ese dataset nació como tarea clásica para trabajos prácticos de materias: viene separado en train y test, y la tarea estándar era predecir las estrellas, o sea el sentimiento, a partir del texto. Acá eso no importa. Se toman todos los textos como una única colección y se entrena Word2Vec sobre ellos, sin otra utilidad que la de jugar con el resultado.

### Preprocesamiento: limpieza y collocations

El preprocesamiento es el que ya conocés para cualquier pipeline de texto clásico. Se tokeniza con el word tokenizer de NLTK (de un string a una lista de palabras), se pasa todo a minúsculas, se limpian espacios, se separa cada review en oraciones y cada oración en palabras, y se dejan solo las palabras alfabéticas, sin números ni puntuación. La estructura resultante, que es la que espera Gensim, es una lista de listas: una lista de palabras por oración. El corpus queda en unas 600.000 oraciones y 11 millones de palabras, que para estos estándares es chico.

El paso interesante es el de collocations, que conecta con la clase anterior. La idea es detectar secuencias de palabras que funcionan como una unidad y fusionarlas en un solo token, por ejemplo que “Buenos Aires” pase a ser “buenos_aires”. El detector se queda con pares que aparecen al menos diez veces (por debajo de eso es probablemente ruido) y cuya normalized PMI supera un umbral de 0,4. Recordá que PMI mide cuánto más probable es que dos palabras aparezcan juntas que lo esperado por azar, y la versión normalizada la acota. “Amores perros” tiene NPMI de uno: cada vez que aparece “amores”, aparece al lado “perros”, algo esperable en un corpus en inglés donde esas palabras casi solo pueden ser el título de una película. Aparecen así unas ocho mil collocations, como “Mardi Gras”, “sci-fi” o nombres propios.

La importancia de este paso se ve más adelante: sin él no podrías preguntarle nada al modelo sobre “Jim Carrey”. Tendrías un vector para “jim”, que puede ser cualquier Jim, y otro para “carrey”. Detectar collocations es lo que convierte a los nombres propios y a los conceptos compuestos en unidades con un embedding propio.

Un alumno preguntó si todo esto es preprocesamiento, y la respuesta fue que sí, con una observación histórica relevante para la materia: este tipo de limpieza se hacía antes y hoy normalmente no se hace. Si hoy trabajás con texto, se lo das a la IA generativa tal como viene, sin sacarle stop words ni normalizarlo, porque esos modelos ya saben entender texto.

### La ley de Zipf

Antes de entrenar, el docente se desvió hacia una regularidad que llamó una ley natural de la distribución de palabras: la ley de Zipf. Se cuenta la frecuencia de cada palabra y se las ordena por ranking. En IMDB, “the” ocupa el primer lugar con unas 600.000 apariciones, “and” el segundo con unas 300.000, después “a”, y así. Las primeras son todas stop words.

Si se grafica frecuencia contra ranking en escala log-log, lo que aparece es una recta: una ley de potencia. Aproximadamente, cuando avanzás diez veces en el ranking la frecuencia se divide por diez. La consecuencia es la cola larga que ya conocés de otras distribuciones: muy pocas palabras concentran la mayor parte del volumen y la enorme mayoría aparece muy pocas veces. El docente dio una cifra orientativa, del orden de un 5% de las palabras explicando un 80% del volumen. También lo ilustró con el vocabulario de un niño, que es chico pero alcanza para decir un montón de cosas. Es una propiedad que aparece en todos los idiomas, y probablemente también en los lenguajes de programación.

Zipf no es solo una curiosidad: explica por qué tienen sentido los hiperparámetros de filtrado que vienen a continuación.

### Las decisiones de Word2Vec

Al entrenar se fijan varios hiperparámetros, y cada uno es una decisión sobre qué señal de co-ocurrencia usar.

El tamaño del vector, `vector_size`, se fijó en 20 dimensiones solo para que corriera rápido; se podrían usar más, y más adelante se ve que esto tiene consecuencias. `min_count` descarta las palabras que aparecen menos de diez veces, y por Zipf eso es muchísimo vocabulario, del orden de la mitad del corpus según el docente. `window` es el tamaño de la ventana de contexto: la palabra central se representa a partir de las palabras que tiene alrededor, y valores usuales son 5, 10 o 15. `sample` filtra las palabras demasiado frecuentes, las que aparecen en una fracción del corpus mayor que el umbral y que probablemente son stop words. `negative` es la cantidad de ejemplos negativos que se samplean, acá 5, retomando el negative sampling de la clase anterior. Y `sg` elige el modelo, porque Word2Vec no es un modelo sino una colección de dos, CBOW y Skip-gram; acá se usa Skip-gram.

Una alumna preguntó si descartar las palabras con menos de diez apariciones no influye muchísimo en el resultado, por ejemplo en textos donde una palabra poco frecuente es central y se la menciona de forma indirecta. La respuesta retoma la intuición dinámica de Word2Vec que se dio en la clase anterior: cada vez que aparece una palabra, su vector da un pasito en la dirección de las palabras que la rodean. Una palabra con muy pocas apariciones dio muy pocos pasos y queda mal representada. Además, las palabras raras que aparecen alrededor de otras están distribuidas de forma bastante aleatoria, así que los pasos que generarían probablemente se cancelarían entre sí. Sacarlas mejora la representación del resto y además acelera el entrenamiento. Es una práctica estándar.

Otro alumno preguntó qué pasa con el idioma: si hay que procurar que todo el corpus esté en una sola lengua. La respuesta es conceptual: el idioma es una noción que está por fuera del conteo de palabras. Word2Vec solo cuenta qué token aparece cerca de cuál y computa los vectores a partir de eso. Los tokens pueden ser palabras, hashtags o cualquier cosa; para el modelo no significan nada en sí mismos. En este caso el corpus es casi todo en inglés.

### Similitud coseno y qué está midiendo realmente

Una vez entrenado, el embedding de una palabra como “awesome” es una colección de veinte números que individualmente no significan nada. Lo que sí tiene sentido es la geometría relativa, y la herramienta para explorarla es la similitud coseno: el coseno del ángulo entre dos vectores.

La exploración arranca con ejemplos de cine. “Jim Carrey” y “silly” dan 0,52. Las palabras más cercanas a “Jim Carrey” son Eddie Murphy, Robin Williams, “comedian”, “stand up”: el vecindario de un actor de comedia. Entre “Jim Carrey” y “Adam Sandler” la similitud es altísima, 0,80; Ben Stiller queda bastante más lejos. A la pregunta de si Dios está más relacionado con Morgan Freeman o con Jim Carrey (que actuaron en la misma película, en la que Freeman hace de Dios), gana Morgan Freeman. Como control, contra “silly” gana Jim Carrey.

Después viene el ejercicio de “quién es más gracioso”: calcular la similitud entre “funny” y una lista de actores. Arriba quedan Chris Rock, Jim Carrey, Ben Stiller y Eddie Murphy; abajo, DiCaprio, Harrison Ford y Stallone. El docente subrayó que se está tomando una licencia poética. El modelo no mide qué tan gracioso es nadie: mide cuánto se asocia el concepto “funny” a cada uno de esos nombres en este corpus de reviews, que es lo que la gente opina de lo que vio en películas.

Esa aclaración se volvió central cuando apareció un resultado raro: Van Damme quedó por encima de Adam Sandler como “gracioso”. La discusión que siguió es un buen modelo de cómo razonar sobre un embedding. Primero, no es que Van Damme sea más gracioso: en este corpus “funny” probablemente aparece más en el contexto de Van Damme, sea por co-ocurrencia de primer orden (aparecen juntas) o de segundo orden (aparecen con las mismas palabras). Segundo, un alumno preguntó si el modelo tiene en cuenta la negación (“no es gracioso”), y la respuesta es que no: mira palabras aisladas y qué palabras tienen alrededor, sin estructura. El docente igual señaló que es raro que alguien escriba específicamente “Van Damme no es gracioso”. Otra hipótesis posible es que haya un puñado de películas de Van Damme donde la gente comenta escenas graciosas.

Lo más útil es cómo dijo que lo investigaría si fuera un trabajo en serio. Leería cien documentos donde aparece cada nombre para ver qué palabras los rodean, computaría el grado de co-ocurrencia y la PMI entre los términos, y se preguntaría si es una asociación real, de segundo orden o una fluctuación estadística. También variaría hiperparámetros de Word2Vec para ver si el resultado se sostiene, y no descartaría que falten dimensiones o que haya un problema en la limpieza. Es decir, un embedding se audita volviendo a los datos que lo generaron.

### Visualizar el espacio: MDS y t-SNE

Para ver el espacio en conjunto, se arman categorías de palabras: géneros de película, actores de acción, actores de comedia, superhéroes, colores y palabras al azar. Se calcula la matriz de distancias de todas contra todas y se proyecta a dos dimensiones con multidimensional scaling y con t-SNE. Las dos técnicas las conocés, así que lo que importa es lo que la clase remarcó sobre su lectura. MDS intenta que las distancias en 2D sean lo más fieles posible a las distancias originales de todos contra todos, y es más robusto a los hiperparámetros. t-SNE intenta preservar la estructura local: lo que estaba cerca queda cerca, pero lo que estaba lejos queda lejos sin que importe dónde. Por eso puede separar grupos más de lo que deberían estar, y no conviene leer las distancias entre clusters. Su perplexity regula el grado de localidad: valores bajos juntan mucho más las cosas, y en la demo un valor de 12 resultó excesivo para pocas palabras. El docente lo resumió en que t-SNE suele funcionar mejor cuando se lo ajusta.

El resultado, en las dos proyecciones, es que las palabras se agrupan de forma razonable por categoría: superhéroes por un lado, colores por otro, actores de acción y de humor en sus zonas. La clave es que nadie le dijo al modelo cuáles eran las categorías; los colores del gráfico se pintan después. La estructura semántica emergió solo de las co-ocurrencias.

### LSA como contraste

Para comparar, se computa LSA, que recordarás de la clase anterior como el enfoque de factorizar la matriz término-documento. En Gensim el flujo es distinto al de Word2Vec. Primero se arma un diccionario que asigna un ID a cada palabra, cada documento se expresa como una colección de IDs, se aplica una transformación TF-IDF sobre esa matriz término-documento y, sobre eso, LSA hace la reducción de dimensionalidad, acá a 40 “tópicos” o dimensiones. Cada palabra queda representada por un número en cada dimensión, y se pueden listar las palabras más presentes en una dimensión para intentar interpretarla. El docente fue claro en que muchas veces esas dimensiones no significan nada y de vez en cuando aparece una que sí.

En la demo, la visualización de LSA salió mucho peor que la de Word2Vec. El docente lo atribuyó a la elección de hiperparámetros: probablemente 40 dimensiones eran demasiadas, porque en otras pruebas con 20 le había dado bien. Más que un veredicto sobre LSA, el punto es que estos métodos son sensibles a esas decisiones.

### El embedding preentrenado de Google

Finalmente se baja el Word2Vec que entrenó Google en 2013 sobre Google News, una colección gigante de noticias, con 300 dimensiones. Con las mismas categorías de palabras y la misma visualización, las palabras se agrupan naturalmente por categoría, otra vez sin que nadie les indique nada. Este modelo es el que se usa para el resto de la clase.

## 5. Analogías vectoriales

La operación más famosa de los word embeddings es la aritmética de vectores. Con `most_similar` le pasás palabras positivas y negativas: tomás el vector de “king”, le restás “man”, le sumás “woman”, y buscás la palabra cuyo vector es más cercano, por similitud coseno, a ese nuevo punto del espacio. Sale “queen”.

Lo interesante es que funciona con relaciones que nadie definió. “Dólar” menos “USA” más “Argentina” da la moneda argentina; “peanut butter” menos “USA” más “Argentina” da “dulce de leche”. Los alumnos propusieron sus propias pruebas. Con “Maradona” menos “Argentina” más “USA” salió un nombre que nadie supo identificar, y hubo resultados ruidosos con “dinosaur”, que dependían de detalles como el plural o la mayúscula. Con “soccer” apareció también “fútbol”, que tiene sentido porque la palabra se usa en inglés.

Un alumno preguntó si los valores de similitud son comparables en términos absolutos. Dentro de un mismo espacio, sí: dos similitudes calculadas en el mismo embedding se pueden comparar. Pero el docente hizo una distinción importante: comparable no quiere decir significativo. Una palabra que aparece diez veces quedó en algún lugar del espacio, y ese lugar puede deberse en parte a una fluctuación estadística. El embedding no te da ningún índice de cuánto creerle a esa posición; hay un grado de ruido que la métrica no muestra. Es el mismo problema que en la primera mitad de la clase, cuando el log odds ratio solo no alcanzaba y había que pasar a significancia, pero acá no hay un z-score a mano.

Si preguntás por la similitud de palabras que no están en el corpus, simplemente no se puede computar: no tienen vector.

## 6. Sesgos en los embeddings

Un uso muy importante de los word embeddings es investigar sesgos. Un sesgo que se vuelve indeseable también se llama estereotipo. Lo que se observó es que la similitud semántica entre palabras refleja los sesgos presentes en el corpus del que nace el embedding, en este caso un corpus de noticias.

En el modelo de Google, “mujer” aparece más asociada a “cocina” que “hombre”. “Woman” está más asociada a “wife” que “man” a “husband”, cuando lo razonable sería que las dos relaciones fueran equivalentes. Y “woman” está más asociada a “children” que “man”. También aparecen sesgos étnicos y nacionales: los latinos más asociados a drogas que los europeos, y México más asociado a drogas que Estados Unidos. Un alumno señaló que Estados Unidos es el principal consumidor, y el docente rescató el punto: es un corpus de Estados Unidos, que muestra a México como el proveedor. Ahí está justamente lo interesante: estas asociaciones permiten preguntarte cómo te muestran los datos ciertas relaciones.

La aritmética de analogías también los deja ver. Hay un paper cuyo título es justamente “Man is to Computer Programmer as Woman is to…”: si a “computer programmer” le restás “man” y le sumás “woman”, terminás en “homemaker” o “housewife”. Hay muchísimos estudios mostrando que los sesgos de los word embeddings reflejan los sesgos del corpus y de la realidad, y el docente mencionó trabajos propios que usan embeddings como métrica de asociación para estudiar, por ejemplo, el sesgo de género.

## 7. Intuiciones sobre similitud: el ejercicio participativo

La última parte fue un juego de predicción con el modelo de Google, pensado para calibrar la intuición sobre qué computa un embedding.

La primera pregunta: ¿“bank” queda más cerca de “money” o de “park”? (En inglés, “bank” es banco financiero, pero también orilla o terraplén). La mayoría dijo “money” y es correcto. La explicación vuelve a lo que se repite toda la clase: el embedding computa asociación, cuánto más frecuentemente aparece una palabra en el contexto de otra, que es la intuición de PMI. La mayoría de los contextos donde aparece “bank” no tienen nada que ver con parques, y la mayoría de los parques no se mencionan junto a bancos. Por eso, aunque “bank” tenga dos sentidos, su vector queda más cerca del financiero. Los vecinos más cercanos lo confirman: “banks”, “banking”, “lender”, “banker”, “depositors”, “mortgage”.

Esto llevó a una idea importante sobre la polisemia en embeddings estáticos. En estos modelos “bank” es siempre el mismo vector, sea cual sea el contexto. El docente citó un paper con Word2Vec que muestra qué pasa geométricamente: si entrenás solo con los textos de un sentido, la palabra cae en un punto; si entrenás solo con los del otro, cae en otro. Al variar la proporción de cada uso, el embedding se mueve sobre la recta entre esos dos puntos. Es decir, el vector final es una combinación lineal de los embeddings que tendría con cada significado por separado, ponderada por la frecuencia de cada uso. Esa limitación (un solo vector para todos los sentidos) es la que motiva las representaciones que dependen del contexto, que la materia ve en la clase de modelos de lenguaje.

Después vino un ejercicio para calibrar la escala. Palabras elegidas medio al azar, como “money” y “run” o “wizard” y “happy”, dan valores del orden de 0,05 a 0,09: ese es el piso de “no relacionadas” en este espacio. “Money” y “wealthy” da 0,32, bastante más alto. Para “money” y “bankrupt”, un alumno argumentó que debería dar menos que “wealthy” porque hay una sola manera de estar en bancarrota y muchas de ser rico; el valor dio parecido, pero el docente rescató el razonamiento. “Good” y “happy” da 0,5, muy alto.

La pregunta más contraintuitiva fue “good” contra “bad”. La respuesta correcta es que deberían estar entre los valores más altos, y es una de las intuiciones más importantes de la clase: los antónimos quedan muy cerca en el espacio de embeddings. Son palabras reemplazables entre sí, que aparecen exactamente en los mismos contextos (“la película fue \_\_\_“). Para un modelo que solo ve co-ocurrencias, el significado opuesto es casi invisible frente a la enorme similitud de uso.”Black” y “white” dan alrededor de 0,8.

El cierre volvió al modelo chico de IMDB con una pregunta trampa: ¿qué similitud tienen “boat” y “red”? Dio alrededor de 0,6, altísimo para dos palabras sin relación aparente. Los alumnos propusieron hipótesis creativas (alguna película con un bote rojo, errores de tipeo), y para testear se probaron otras palabras al azar, que también dieron valores altos (0,5, 0,6, 0,8). La explicación, que había anticipado un alumno, es que los números de un espacio no son comparables con los de otro. La distribución de similitudes depende del corpus y, sobre todo, de la dimensionalidad. El Word2Vec de Google tiene 300 dimensiones y el de IMDB tiene 20. Con muchas dimensiones los puntos se dispersan muchísimo más y es mucho más improbable que dos vectores apunten en la misma dirección por azar; con 20 dimensiones, los vectores están más amontonados. Entonces un 0,6 es una cercanía enorme en el espacio de Google y bastante poco en el de IMDB. El máximo sigue siendo uno, pero el centro de la distribución se corre. Se podría normalizar mirando la distribución de similitudes de todas contra todas, pero no se suele hacer. La moraleja que dejó el docente es que los números que da un embedding dependen de los contextos: no son algo absoluto.

## 8. Por qué importan hoy los word embeddings

El docente fue franco sobre el lugar de esta técnica: los word embeddings como tal están prácticamente en desuso porque el área avanzó muy rápido. Pero insistió en dos cosas. La primera es que algo parecido es lo que está detrás de los vectores de oraciones y documentos que hoy se usan en las bases de datos vectoriales: la intuición de que la cercanía en el espacio refleja similitud de uso, y todas sus limitaciones, se trasladan directamente. La segunda es que son fundamentals del mundo de la IA y están subestudiados. Contó, por ejemplo, una tesis de licenciatura que dirigió en la que observaron cómo se mueven los puntos durante el entrenamiento de un embedding, y en algún momento el espacio entero empieza a rotar. Ese tipo de propiedades geométricas no está estudiado.

Siguen teniendo interés en otras áreas: en lingüística, para estudiar cómo cambia el uso de las palabras en el tiempo; en neurociencia, para entender cómo representamos las palabras en la mente; y en el estudio de sesgos. A una alumna que estaba enfocando su tesis en word embeddings le sugirió que el valor de un tema muchas veces está en el impacto que tiene en un área de aplicación.

## Ideas para llevarse

Para comparar dos corpus, las palabras más frecuentes de cada uno no sirven: hay que buscar palabras que aparezcan mucho en uno y poco en el otro, con una diferencia significativa. Eso exige normalizar bien. Primero, por el tamaño de cada grupo. Después, si comparás palabras de frecuencias distintas, por la frecuencia general de cada palabra. Los scores basados solo en probabilidades premian las palabras raras que cayeron de un lado por azar. El log odds ratio con background de Monroe et al. lo corrige con dos movimientos: suaviza con un corpus de referencia y lleva la diferencia a un z-score, que combina tamaño de efecto y frecuencia en una medida de significancia. Para el examen alcanza con entender esa lógica.

Del lado de los embeddings, la idea central es que un word embedding codifica asociación por co-ocurrencia en un corpus particular. Por eso refleja los temas y los sesgos de ese corpus, pone a los antónimos muy cerca, le da un único vector a una palabra polisémica (una mezcla de sus usos según su frecuencia) y produce números que solo se pueden comparar dentro del mismo espacio, sin ninguna medida de confianza. Las decisiones de preprocesamiento y de entrenamiento no son detalles: detectar collocations, filtrar por frecuencia en función de Zipf y elegir la dimensionalidad cambian lo que el modelo puede representar y la escala de sus similitudes. Y cuando un resultado sorprende, la forma de entenderlo es volver a los textos.
