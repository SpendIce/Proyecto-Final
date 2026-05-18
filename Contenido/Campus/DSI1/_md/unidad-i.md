# DSI1 Unidad I - Requisitos, comportamiento del sistema y casos de uso

Fuente PDF: `DSI1/Unidad_I.pdf`.

Markdown operativo: `DSI1/_md/unidad-i.md`.

Paginas PDF: 50. Palabras extraidas: 1680.

Nota: extraccion automatica con `pdftotext -layout` para busqueda y recuperacion por agentes. Para tablas, figuras o formato exacto, consultar el PDF fuente.

---

1


---

2


---

SW que debe residir en un Sistema, antes de construirlo se debe comprender el
Sistema.


                                                                                3


---

4


---

5


---

6


---

7


---

8


---

9


---

A diferencia de las actividades de transacción, las relacionadas con decisiones
no siguen un procedimiento específico.
Las rutinas no son muy claras y es posible que los controles sean vagos. (Ej.:
Sistema para decidir el precio de una mercancía).
En algunos casos, se procesan los datos de la transacción para generar
nueva información para la toma de decisiones


                                                                                  10


---

11


---

oLa determinación de requerimientos da como resultado una evaluación de la
forma cómo trabajan los métodos empleados y si es necesario o posible
realizar ajustes.


DIFICULTADES DE REQUERIMIENTOS:
• Los usuarios no tiene claro lo que desean
• Los usuarios no entienden el proceso desarrollo


Para tener en cuenta:
• Requerimiento: son todas las necesidades y deseos pedidos por el cliente y
  las personas involucradas en el software
• Requisito: todas las funcionalidades, características y restricciones que
  debería tener el software


• “Requerimientos del cliente”: Necesidades del cliente, siempre cambiantes
  y por eso no obligatorias del todo.
• “Requisitos del sistema”: Capacidades que debe tener el sistema para
  satisfacer las necesidades de los usuarios del sistema.


                                                                               12


---

Un requerimiento funcional define una función del sistema de software o sus
componentes. Una función es descrita como un conjunto de entradas,
comportamientos y salidas. Los requerimientos funcionales pueden ser:
cálculos, detalles técnicos, manipulación de datos y otras funcionalidades
específicas que se supone, un sistema debe cumplir. Los requerimientos de
comportamiento para cada requerimiento funcional se muestran en los casos
de uso. Son complementados por los requerimientos no funcionales, que se
enfocan en cambio en el diseño o la implementación.
Típicamente, un analista de requerimientos genera requerimientos funcionales
después de realizar los casos de uso. Sin embargo, esto puede tener
excepciones, ya que el desarrollo de software es un proceso iterativo y
algunos requerimientos son previos al diseño de los casos de uso. Ambos
elementos (casos de uso y requerimientos) se complementan en un proceso
bidireccional.
Un requerimiento funcional típico contiene un nombre y un número de serie
único y un resumen. Esta información se utiliza para ayudar al lector a
entender por qué el requerimiento es necesario, y para seguir al mismo
durante el desarrollo del producto.
El núcleo del requerimiento es la descripción del comportamiento requerido,
que debe ser clara y concisa. Este comportamiento puede provenir de reglas
organizacionales o del negocio, o ser descubiertas por interacción con


                                                                               13


---

usuarios, inversores y otros expertos en la organización.


                                                            13


---

14


---

15


---

16


---

17


---

18


---

19


---

20


---

21


---

22


---

23


---

24


---

25


---

26


---

27


---

28


---

29


---

30


---

31


---

32


---

33


---

oInformación valiosa puede perderse si los sistemas de transacciones no
capturan y guardan los datos necesarios para las decisiones.
oCuando los analistas estudian sistemas para un departamento también
deben evaluar las implicaciones para los demás departamentos con lo que
interactúa el sistema bajo investigación.
oLa determinación de requerimientos es el proceso por el cual los analistas
obtienen conocimiento relacionado con la organización y lo aplican para
seleccionar la tecnología correcta para una aplicación en particular. En
muchos casos, el objetivo más importante de este proceso es aprender cómo
se manejan las excepciones. Las excepciones desafían los procedimientos
estándares de operación.


                                                                              34


---

35


---

•Entrevistas estructuradas: Utilizan preguntas estándar en un formato de
respuesta abierta o cerrada. El primero permite que el entrevistado dé
respuesta a las preguntas con sus propias palabras; el segundo utiliza un
conjunto anticipado de respuestas.
•Entrevistas no estructuradas: Utilizan un formato pregunta-respuesta y son
apropiadas cuando el analista desea adquirir información general acerca de
un sistema


Es importante contar con la adecuada verificación de los datos por medio de
otros métodos para recopilarlos


                                                                              36


---

37


---

38


---

39


---

•Condiciones y variables de decisión. Cuando se observa un sistema y se
pregunta ¿cuáles son las posibilidades? o ¿qué puede suceder?, en realidad
se está preguntando por las condiciones (ej: bueno y malo), que son los
posibles estados de una entidad (persona, objeto o evento).
Las condiciones cambian y es por esto que el analista se refiere a ellas como
variables de decisión. (En una empresa, el manejo de una factura está basado
en una condición que constituye una variable de decisión).
Al documentar la decisión sobre un procedimiento, el investigador debe
identificar tanto las condiciones permisibles como las relevantes que pueden
presentarse en determinada situación. Sólo deben incluirse en el estudio
aquellas condiciones que son relevantes (el hecho de que la factura esté o no
firmada es una variable relevante. Sin embargo, el tamaño de la hoja del papel
sobre la que está impresa probablemente no lo sea).

•Acciones. Cuando se conocen todas las posibles condiciones, el siguiente
paso del analista es determinar qué hacer cuando se presentan algunas de
éstas. Las acciones son las opciones, que comprenden pasos, actividades o
procedimientos, que puede elegir una persona cuando se enfrenta ante un
conjunto de condiciones. En algunos casos las acciones pueden ser bastante
sencillas, mientras que en otros muy extensas.
Las acciones pueden estar relacionadas con condiciones cuantitativas.


                                                                                 40


---

En muchos procedimientos el analista debe considerar combinaciones de
condiciones y acciones.


                                                                        40


---

Las decisiones y procedimientos son de importancia para el analista cuando
éste conduce una investigación de sistemas dentro de la empresa. Las
herramientas ayudan al analista a integrar los datos recopilados por los
diversos                          métodos                          estudiados.
Tener diferentes formas de decir la misma cosa puede crear dificultades de
comunicación durante los estudios de sistemas. Por consiguiente el analista
busca evitar las malas interpretaciones. Asimismo, el analista necesita
organizar la información recopilada con respecto a la toma de decisiones


                                                                                 41


---

La raíz del árbol, aparece en la parte izquierda, es el punto donde comienza la
secuencia de decisión. La rama a seguir depende de las condiciones
existentes y de la decisión que debe tomarse. Al avanzar de izquierda a
derecha por una rama en particular, se obtiene una serie de toma de
decisiones. Después de cada punto de decisión, se encuentra el siguiente
conjunto de decisiones a considerar. De esta forma, los nodos del árbol
representan condiciones y señalan la necesidad de tomar una determinación
relacionada con la existencia de alguna de éstas, antes de seleccionar la
siguiente trayectoria. La parte que se encuentra a la derecha del árbol indica
las acciones que deben realizarse, las que a su vez dependen de la secuencia
                    de condiciones que las preceden.
También son útiles para identificar los requerimientos de datos críticos que
rodean al proceso de decisión; es decir, los árboles indican conjuntos de datos
que la gerencia requiere para formular decisiones o tomar acciones.

El gran número de ramas que pertenecen a varias trayectorias
constituye más un problema que una ayuda para el análisis. En estos
casos los analistas corren el riesgo de no determinar qué políticas o
estrategias de la empresa son guía para la toma de decisiones específicas.
Cuando aparecen estos problemas, entonces es momento de considerar
las tablas de decisión.


                                                                                  42


---

Secciones:
             •Identificación de condiciones: señala aquellas que son
             relevantes.
             •Entradas de condiciones: indican qué valor, si es que los hay,
             se debe asociar para una determinada condición.
             •Identificación de acciones: enlista el conjunto de todos los
             pasos que se deben seguir cuando se presenta cierta condición.
             •Entradas de acciones: muestran las acciones específicas del
             conjunto que deben emprenderse cuando ciertas condiciones o
             combinaciones de éstas son verdaderas.
Las columnas del lado derecho de la tabla enlazan condiciones y acciones,
forman reglas de decisión que establecen las condiciones que deben
satisfacer para emprender un determinado conjunto de acciones.
Cabe destacar que se omite el orden de la secuencia (en que las condiciones
son examinadas) cosa que no sucede con los árboles de decisión. La regla de
decisión incorpora todas las acciones que deben ser cierta y no sólo una a la
vez.


Eliminación de la redundancia: La redundancia se presenta cuando las


                                                                                43


---

siguientes condiciones son verdaderas al mismo tiempo:
             •Dos reglas de decisión son idénticas salvo por una condición
             del renglón.
             •Las acciones para las dos reglas son idénticas.
Las reglas de decisión son redundantes y pueden combinarse en una sola
regla. La condición sobre el renglón donde ellas difieren se puede reemplazar
por un espacio en blanco o un guion para indicar que esa condición no es
importante.


Supresión de contradicciones: Las reglas de decisión son contradictorias
entre sí cuando dos o más reglas tienen el mismo conjunto de condiciones
pero sus acciones son diferentes (si son las mismas, entonces las reglas de
decisión son redundantes).
Las contradicciones indican que la información que tiene el analista es
incorrecta o bien que existe un error en la construcción de la tabla. Sin
embargo, muchas veces la contradicción es resultado de las discrepancias en
la información que recibe el analista de diferentes personas con respecto a la
forma en que éstas toman decisiones.
Para eliminar la contradicción se debe verificar la acción apropiada y proceder
a eliminar la inconsistencia.


Forma ELSE


                                                                                  43


---

▪Estructuras de secuencia: Es un solo paso o acción incluido en un proceso.
Éste no depende de la existencia de ninguna condición y, cuando se
encuentra, siempre se lleva a cabo. En general, se emplean varias
instrucciones en secuencia para describir un proceso.
▪Estructuras de decisión: Aparecen cuando se pueden emprender dos o más
acciones, lo que depende del valor de una condición específica. Para esto,
primero se evalúa la condición y después se toma la decisión de emprender
     las acciones o el grupo de acciones asociado con esta condición.
No están limitadas a pares de combinaciones condición-acción, sino que
pueden       existir     muchas       condiciones     (IF/THEN/ELSE      o
IF/THEN/OTHERWISE).
▪Estructuras de iteración: En las actividades rutinarias de operación, es
común encontrar que algunas de ellas se repiten mientras existen ciertas
condiciones o hasta que éstas se presentan. Las instrucciones de iteración
permiten al analista describir estos casos.


Después de describir las actividades en forma estructurada, los analistas
pueden pedir a otras personas que revisen la descripción y determinen con
rapidez los errores u omisiones cometidos al establecer los procesos de
decisión.


                                                                              44


---

También es un método eficaz para el diseño de sistemas.


                                                          44


---

45


---

46


---
