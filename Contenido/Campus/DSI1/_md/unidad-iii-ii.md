# DSI1 Unidad III II - UML y modelos visuales de software

Fuente PDF: `DSI1/Unidad_III_II.pdf`.

Markdown operativo: `DSI1/_md/unidad-iii-ii.md`.

Paginas PDF: 56. Palabras extraidas: 6258.

Nota: extraccion automatica con `pdftotext -layout` para busqueda y recuperacion por agentes. Para tablas, figuras o formato exacto, consultar el PDF fuente.

---

         Unidad III
    El Lenguaje de
Modelado Unificado
            (UML)


                      1


---

El Lenguaje de Modelado Unificado
⚫ El Lenguaje Unificado de Modelado (UML) es
 un lenguaje de modelado visual que se usa
 para especificar, construir y documentar
 artefactos de un sistema de software.

⚫ Captura decisiones y conocimiento sobre los
 sistemas que se deben construir.


                                                2


---

El Lenguaje de Modelado Unificado
⚫ El modelo capta los aspectos importantes de
  lo que estamos modelando, desde cierto punto
  de vista, y simplifica u omite el resto.

⚫ El modelo de un sistema de software está
  construido en un lenguaje de modelado, como
  UML.


                                                 3


---

         El Lenguaje de Modelado Unificado
         ⚫ Los  modelos se usan para muchos
           propósitos:
           ⚫ Para   captar y enumerar exhaustivamente
              los requisitos y el dominio de conocimiento,
              de forma que todos los implicados puedan
              entenderlos y estar de acuerdo con ellos.
           ⚫ Para   pensar del diseño de un sistema.
              Ayuda a los desarrolladores a explorar
              varias arquitecturas y soluciones de diseño
              fácilmente, antes de escribir el código.
           ⚫ Para capturar decisiones del diseño en una
              forma mutable a partir de los requisitos.


•Para captar y enumerar exhaustivamente los requisitos y el dominio de
conocimiento, de forma que todos los implicados puedan entenderlos y
estar de acuerdo con ellos.
•Para pensar del diseño de un sistema. La simplicidad de crear y modificar
modelos pequeños permite pensamiento creativo e innovación con poco
coste.


Un modelo de un sistema de software ayuda a los desarrolladores a explorar
varias arquitecturas y soluciones de diseño fácilmente, antes de escribir el
código.
•Para capturar decisiones del diseño en una forma mutable a partir de
los requisitos.
•Para generar productos aprovechables para el trabajo.
•Para organizar, encontrar, filtrar, recuperar, examinar, y corregir la
información en grandes sistemas.
•Para explorar económicamente múltiples soluciones. Los modelos de un
sistema de software grande permiten que se propongan y comparen varios
diseños. Los modelos no se construyen al detalle, por supuesto, pero incluso
un modelo rudimentario puede exponer muchas cuestiones que el diseño final


                                                                               4


---

debe tener en cuenta. Modelar permite considerar varios diseños, con un
coste pequeño al implementar cualquiera de ellos.


                                                                          4


---

El Lenguaje de Modelado Unificado
⚫ Los  modelos se usan para          muchos
  propósitos:
 ⚫ Para generar productos aprovechables para
   el trabajo.
 ⚫ Para organizar, encontrar,
                           filtrar, recuperar,
   examinar, y corregir la información en
   grandes sistemas.
 ⚫ Para   explorar económicamente múltiples
   soluciones.


                                                 5


---

El Lenguaje de Modelado Unificado
•   UML fue desarrollado en un esfuerzo para
    simplificar y consolidar el gran número de
    métodos de desarrollo orientado a objetos que
    habían surgido.

•   Está pensado para usarse con todos los
    métodos de desarrollo. La especificación de
    UML no define un proceso estándar pero está
    pensado para ser útil en un proceso de
    desarrollo iterativo. Pretende dar apoyo a la
    mayoría de los procesos de desarrollo
    orientados a objetos.


                                                    6


---

         El Lenguaje de Modelado Unificado
         ⚫ La   palabra unificado tiene los siguientes
           significados relevantes para UML:

           ⚫ A   través de los métodos históricos y
             notaciones.
           ⚫ A través del ciclo de vida de desarrollo.
           ⚫ A través de los dominios de aplicación.
           ⚫ A través de los lenguajes de implementación
             y plataformas.


•A través de los métodos históricos y notaciones. UML combina conceptos
comúnmente aceptados por muchos métodos orientados a objetos,
seleccionando una definición clara para cada concepto, así como una
notación y una terminología.
•A través del ciclo de vida de desarrollo. UML no tiene saltos ni
discontinuidades desde los requisitos a la implantación. Se puede utilizar el
mismo conjunto de conceptos y notación en las diferentes etapas del
desarrollo, incluso mezcladas en un solo modelo. No es necesario traducir de
una etapa a otra. Esta continuidad es crítica para un desarrollo iterativo e
incremental.
•A través de los dominios de aplicación. UML está pensado para modelar la
mayoría de los dominios de aplicación, incluyendo aquellos que implican
sistemas grandes, complejos, de tiempo real, distribuidos, con tratamiento
intensivo de datos o con cálculo intensivo, entre otras propiedades.
•A través de los lenguajes de implementación y plataformas. UML está
pensado para ser usado en sistemas desarrollados en varios lenguajes de
implementación y plataformas.

Es importante darse cuenta de que UML y el proceso para usar UML son dos
cosas independientes. UML pretende trabajar correctamente con todos, o al
menos con la mayoría de los procesos de desarrollo existentes.


                                                                                7


---

         El Lenguaje de Modelado Unificado
         •   Tiene partes estáticas, dinámicas, de entorno
             y organizativas.

         •   Se debe tener en cuenta que para dominios
             especializados, tales como la composición de
             IGU o inteligencia artificial basada en reglas,
             podría ser más apropiado una herramienta
             especializada con un lenguaje especial.


•UML capta la información sobre la estructura estática y el comportamiento
dinámico de un sistema. Un sistema se modela como una colección de
objetos discretos que interactúan para realizar un trabajo que finalmente
beneficia a un usuario externo. La estructura estática define los tipos de
objetos importantes para un sistema y para su implementación, así como las
relaciones entre los objetos. El comportamiento dinámico define la historia de
los objetos en el tiempo y la comunicación entre objetos para cumplir sus
objetivos.


•UML también contiene construcciones organizativas para agrupar los
modelos en paquetes, lo que permite a los equipos de software dividir grandes
sistemas en piezas de trabajo, para entender y controlar las dependencias
entre paquetes, y para gestionar las versiones de las unidades del modelo, en
un entorno de desarrollo complejo.


                                                                                 8


---

        El Lenguaje de Modelado Unificado
        ⚫ Los  conceptos y modelos de UML pueden
           agruparse    en  las  siguientes áreas
           conceptuales:

           ⚫ Estructura estática.
           ⚫ Comportamiento dinámico.
           ⚫ Construcciones de implementación.
           ⚫ Organización del modelo.


Los conceptos y modelos de UML pueden agruparse en las siguientes áreas
conceptuales:


      •Estructura estática. Cualquier modelo preciso debe primero definir el
      universo del discurso, esto es, los conceptos clave de la aplicación, sus
      propiedades internas, y las relaciones entre cada una. Este conjunto de
      construcciones es la vista estática. Los conceptos de la aplicación son
      modelados como clases, cada una de las cuales describe un conjunto
      de objetos discretos que almacenan información y se comunican para
      implementar un comportamiento. La información que almacenan es
      modelada como atributos; el comportamiento que realizan es modelado
      como operaciones. La vista estática se expresa en diagramas de
      clases.


      •Comportamiento dinámico. Hay dos formas de modelar el
      comportamiento. Una es la historia de la vida de un objeto, que
      muestra la forma que interactúa con el resto del mundo; la otra son los
      patrones de comunicación de un conjunto de objetos conectados, que
      muestra cómo interactúan para implementar su comportamiento.
      La visión de un objeto aislado es una máquina de estados –una vista


                                                                                  9


---

de un objeto que muestra la forma en que responde a los eventos en
función de su estado actual, realiza acciones como parte de su
respuesta y transiciones a un nuevo estado-. Las máquinas de estados
se representan en un diagrama de estados.
La visión de la interacción de los objetos de un sistema es una
colaboración. Las colaboraciones e interacciones se muestran
mediante los diagramas de secuencia y los diagramas de colaboración.
Guiando todas las vistas de comportamiento se encuentra un conjunto
de casos de uso. Cada uno es una descripción de una porción de la
funcionalidad del sistema como la percibe un actor, un usuario externo
del sistema.


•Construcciones de implementación. Un componente es una parte
física reemplazable de un sistema y es capaz de responder a las
peticiones descritas por un conjunto de interfaces. Se pretende que sea
fácilmente sustituible por otro componente que cumpla la misma
especificación. Un nodo es un recurso computacional que define una
localización durante la ejecución del sistema. Pueden contener
componentes y objetos. La vista de despliegue describe la
configuración de los nodos de un sistema en ejecución y la
organización de los componentes y objetos en él, incluyendo posibles
migraciones de contenido entre nodos.


•Organización del modelo. En un sistema grande, la información del
modelo debe ser dividida en piezas coherentes, para que los equipos
puedan trabajar en las diferentes partes de forma concurrente. Los
paquetes son unidades organizativas, jerárquicas, y de propósito
general de los modelos de UML. Pueden usarse para almacenamiento,
control de acceso, gestión de la configuración, y construcción de
bibliotecas que contengan fragmentos de código reutilizable. Una
dependencia entre paquetes puede ser impuesta por la arquitectura
global del sistema. Por lo tanto, los contenidos de los paquetes deben
adaptarse a las dependencias del paquete y a las impuestas por la
arquitectura del sistema.


                                                                          9


---

El Lenguaje de Modelado Unificado
   Área            Vista         Diagramas               Conceptos principales

              Estática         De Clase         Clases, asociación, generalización,
                                                dependencia, realización, interfaz
              De casos de      De caso de uso   Caso de uso, actor, asociación, extensión,
              uso                               inclusión, generalización de caso de uso
Estructural
              De             De                 Componente, interfaz, dependencia,
              implementación componentes        realización
              De despliegue    De despliegue    Nodo, Componente, dependencia,
                                                localización
              Máquina de       De estados       Estado, evento, transición acción
              estados
              De actividad     De actividad     Estado, actividad, transición de
Dinámica                                        terminación, división, unión
              De interacción   De secuencia     Interacción, objeto, mensaje, activación
                               De               Colaboración, interacción, rol de
                               colaboración     colaboración, mensaje
Gestión       De gestión del   De clases        Paquete, subsistema, modelo
del modelo    modelo
Extensión     Todas            Todos            Restricción, estereotipo, valores
de UML                                          etiquetados


                                                                                             10


---

         El Lenguaje de Modelado Unificado
                             Vista estática.

           ⚫ La vista estática modela los conceptos del
                 dominio de la aplicación, así como los
                 conceptos internos inventados como parte
                 de la implementación de la aplicación.

           ⚫ La       visión estática se        exhibe     en    los
                 diagramas de clases.


Vista estática


La vista estática modela los conceptos del dominio de la aplicación, así como
los conceptos internos inventados como parte de la implementación de la
aplicación. Esta visión es estática porque no describe el comportamiento del
sistema dependiente en el tiempo, que se describe en otras vistas. Los
componentes principales de la vista estática son las claves y sus relaciones:
asociación, generalización, realización y uso. La visión estática se exhibe en
los diagramas de clases.


                                                                                 11


---

         El Lenguaje de Modelado Unificado
         Diagrama de clases


La figura muestra un diagrama de clases de la aplicación de la taquilla. Este
diagrama contiene parte del modelo del dominio “venta de entradas”. Muestra
varias clases importantes, tales como Cliente, Reserva, Entrada y
Presentación. Los clientes pueden tener muchas reservas, pero cada reserva
es hecha por un cliente.


Las reservas son de dos clases: suscripción y reservas individuales. Ambos
reservan entradas: en un caso, solamente una entrada; en el otro caso, varias
entradas.


Cada entrada es parte de una suscripción o de una reserva individual, pero no
de ambas. Cada representación tiene muchas entradas disponibles, cada una
con un número de asiento único. Una representación se puede identificar por
una obra, una fecha y una hora.


Las clases se pueden escribir con varios niveles de precisión y concreción. Al
empezar el diseño, el modelo captura los aspectos más lógicos del problema.
En las fases posteriores, el modelo también capta decisiones de diseño y
detalles de la implementación. La mayoría de las vistas tienen un
comportamiento evolutivo similar.


                                                                                 12


---

         El Lenguaje de Modelado Unificado
         Asociación.

            ⚫ Representa una relación entre clases, pero
              además aporta la semántica y la estructura
              de las conexiones y relaciones entre objetos,
              por lo que podría decirse que las
              asociaciones son los mecanismos que
              permiten a los objetos comunicarse entre sí.
            ⚫ Además, pueden especificar el propósito de
              la asociación, pudiendo ser unidireccionales
              o bidireccionales. En cada extremo de la
              asociación se incluye un valor de
              multiplicidad, que indica cuántos objetos de
              ese lado de la asociación están relacionados
              con un objeto del extremo contrario.


Asociaciones:


Una asociación representa una relación entre clases, pero además aporta la
semántica y la estructura de las conexiones y relaciones entre objetos, por lo
que podría decirse que las asociaciones son los mecanismos que permiten a
los objetos comunicarse entre sí. Además, pueden especificar el propósito de
la asociación, pudiendo ser unidireccionales o bidireccionales.


En cada extremo de la asociación se incluye un valor de multiplicidad, que
indica cuántos objetos de ese lado de la asociación están relacionados con un
objeto del extremo contrario.


En UML, las asociaciones se representan por medio de líneas que conectan
las clases participantes en la relación, y también pueden mostrar el papel y la
multiplicidad de cada uno de los participantes. La multiplicidad se muestra
como un rango [mín...máx] de valores no negativos, con un asterisco (*)
representando el infinito en el lado máximo.


                                                                                  13


---

         El Lenguaje de Modelado Unificado
         Asociación.
            ⚫ Los diferentes tipos de asociaciones son:
              ⚫ Herencia
              ⚫ Agregación
              ⚫ Composición
              ⚫ Asociación
              ⚫ Dependencia o Instanciación


Los diferentes tipos de asociaciones son:
•Herencia (Especialización/Generalización): Esta relación indica que una
subclase hereda los métodos y atributos especificados por una superclase, la
subclase además de contar con sus propios métodos y atributos, tendrá los
atributos y métodos visibles de la superclase. Se representa por una línea
terminada en un triángulo en el lado de la superclase.
•Agregación: Usada cuando se requiere componer objetos cuyo tipo sea la
unión de otros tipos definidos por el desarrollador. Se representa por una línea
terminada en un rombo blanco en el lado del agregador.
•Composición: Es un caso de agregación, pero con una relación más potente,
de forma que el agregador no tiene sentido sin el agregado. Se representa por
una línea terminada en un rombo negro en el lado del agregador.
•Asociación: Representada por una linea que une las clases, permite asociar
objetos que colaboran entre si. No es una relación fuerte, por lo que el tiempo
de vida de un objeto no depende del otro.
•Dependencia o Instanciación: Se denota por una flecha punteada y su uso
más habitual es denotar la dependencia que tiene una clase de otra.


                                                                                   14


---

         El Lenguaje de Modelado Unificado
         Agregación.

            ⚫ Forma    de asociación que especifica una
              relación todo-parte entre un agregado (el
              todo) y las partes que lo componen.

            ⚫ La  relación de agregación es transitiva y
              antisimétrica a través de los enlaces de
              agregación.


Agregación.


Forma de asociación que especifica una relación todo-parte entre un
agregado (el todo) y las partes que lo componen. Un extremo de la asociación
se designa como agregado mientras que el otro no se marca de forma
especial. Se debe tener en cuenta, que no pueden ser agregados (o
compuestos) ambos extremos. Además la relación de agregación es transitiva
y antisimétrica a través de los enlaces de agregación. (La antisimetría obliga a
que no existan bucles en las rutas dirigidas de los enlaces de agregación.
Esto es, no es posible que ningún objeto sea parte de sí mismo directa o
indirectamente).


Existe una relación más fuerte de agregación llamada composición. Un
compuesto es un agregado con las restricciones adicionales de que un objeto
puede ser parte sólo de un compuesto, y de que el objeto compuesto tiene la
responsabilidad de la disponibilidad de sus partes a la hora de crearlas y
destruirlas.


En la agregación simple, una parte puede pertenecer a más de un agregado, y
lo que es más, puede existir independientemente del agregado. A menudo el


                                                                                   15


---

agregado “necesita” las partes, en el sentido de que puede ser considerado
como una colección de partes, pero las partes pueden existir por sí mismas,
sin tener que ser vistas como partes únicamente.


                                                                              15


---

El Lenguaje de Modelado Unificado
Agregación.

 ⚫ Una  parte puede pertenecer a más de un
   agregado, y lo que es más, puede existir
   independientemente del agregado. A
   menudo el agregado “necesita” las partes,
   en el sentido de que puede ser considerado
   como una colección de partes, pero las
   partes pueden existir por sí mismas, sin
   tener que ser vistas como partes
   únicamente.


                                                16


---

         El Lenguaje de Modelado Unificado
         Agregación.


Por ejemplo, una ruta es poco más que un conjunto de segmentos, pero un
segmento puede existir independientemente de si pertenece o no a una ruta, y
además el mismo segmento puede pertenecer a más de una ruta.


                                                                               17


---

         El Lenguaje de Modelado Unificado
         Agregación.


Por ejemplo, una ruta es poco más que un conjunto de segmentos, pero un
segmento puede existir independientemente de si pertenece o no a una ruta, y
además el mismo segmento puede pertenecer a más de una ruta.


                                                                               18


---

         El Lenguaje de Modelado Unificado
         Composición.
            ⚫ Una forma de asociación de agregación con
               fuerte sentido de posesión y tiempo de vida
               coincidente de las partes con el conjunto.
            ⚫ Una   pieza puede pertenecer solamente a
               una composición.
            ⚫ Las    partes con multiplicidad no fija, se
               pueden crear después del elemento
               compuesto. Pero una vez creadas, viven y
               mueren con él (es decir, comparten tiempo
               de vida). Tales piezas se pueden también
               quitar explícitamente antes de la muerte del
               elemento compuesto.


Composición.


Una forma de asociación de agregación con fuerte sentido de posesión y
tiempo de vida coincidente de las partes con el conjunto. Una pieza puede
pertenecer a solamente una composición. Las partes con multiplicidad no fija,
se pueden crear después del elemento compuesto. Pero una vez creadas,
viven y mueren con él (es decir, comparten tiempo de vida). Tales piezas se
pueden también quitar explícitamente antes de la muerte del elemento
compuesto. La composición puede ser recurrente.


Durante su instanciación, un elemento compuesto debe asegurarse de que
hayan sido instanciadas y unidas correctamente a él todas sus partes. Debe
tenerse en cuenta que un objeto puede ser parte solamente de un objeto
compuesto a la vez, donde esto no imposibilita a una clase para ser una parte
compuesta de más de una clase en diferentes momentos o en diferentes
instancias, pero solamente puede existir un enlace de composición al mismo
tiempo para un objeto.


Al igual que la agregación, la composición es transitiva.


                                                                                19


---

El Lenguaje de Modelado Unificado
Composición.
 ⚫ Un objeto puede ser parte solamente de un
   objeto compuesto a la vez, donde esto no
   imposibilita a una clase para ser una parte
   compuesta de más de una clase en
   diferentes momentos o en diferentes
   instancias, pero solamente puede existir un
   enlace de composición al mismo tiempo para
   un objeto.
 ⚫ Al igual que la agregación, la composición es
   transitiva.


                                                   20


---

El Lenguaje de Modelado Unificado


                                    21


---

El Lenguaje de Modelado Unificado
Composición.


                                    22


---

El Lenguaje de Modelado Unificado
Composición.


                                    23


---

El Lenguaje de Modelado Unificado


                                    24


---

         El Lenguaje de Modelado Unificado
                       Vista de los casos de uso.

            ⚫ Modela la funcionalidad del sistema según lo
              perciben los usuarios externos, llamados
              actores.
            ⚫ Su propósito es enumerar a los actores y los
              casos de uso, y demostrar qué actores
              participan en cada caso de uso.

           Caso de uso
              es una unidad coherente de funcionalidad,
              expresada como transacción entre los
              actores y el sistema.


Vista de los casos de uso.


La vista de los casos de uso modela la funcionalidad del sistema según lo
perciben los usuarios externos, llamados actores. Un caso de uso es una
unidad coherente de funcionalidad, expresada como transacción entre los
actores y el sistema. El propósito de la vista de los casos de uso es enumerar
a los actores y los casos de uso, y demostrar qué actores participan en cada
caso de uso.


Los casos de uso describen las relaciones y las dependencias entre un grupo
de acciones que se pueden realizar en el sistema y los actores participantes
en dicho proceso. Cabe destacar que los diagramas de casos de uso no están
pensados para representar el diseño en sí del sistema, por lo que no puede
describir sus elementos internos.


Por lo tanto, sirven para facilitar la comunicación con los futuros usuarios del
sistema, y con el cliente, siendo muy útiles para determinar las características
necesarias que tendrá el sistema: describen qué es lo que debe hacer el
sistema, pero no la forma en que lo hace


                                                                                   25


---

         El Lenguaje de Modelado Unificado
         Diagrama de casos de uso


La figura muestra un diagrama de casos de uso para el ejemplo de la taquilla.
Los actores son el vendedor, el supervisor y el quiosco. El quiosco es otro
sistema que acepta pedidos de un cliente. El cliente no es actor en la
aplicación de la taquilla, porque no está conectado directamente con la
aplicación. Los casos de uso incluyen el comprar entradas, a través del
quiosco o del vendedor, comprar suscripciones (solamente a través del
vendedor), y examinar las ventas totales (a petición del supervisor).

El comprar entradas y el comprar las suscripciones incluyen un fragmento
común –que es hacer cargos al servicio de la tarjeta de crédito-. (La
descripción completa de la taquilla implicaría muchos otros casos de uso,
tales como cambio de entradas y comprobación de disponibilidad).


Los casos de uso se pueden también describir en varios niveles de detalle. Se
pueden sacar partes como factor común y ser descritos en términos de otros
casos de uso más simple.

La interacción sólo incluye las comunicaciones habidas entre el sistema y los
actores. El comportamiento o implementación internos se ocultan.
Se debe tener en cuenta que entre los actores (usuarios) se cuentan las


                                                                                26


---

personas así como los computadores y otros objetos (otro HW y/o SW).


Los casos de uso incluyen el comportamiento normal y habitual que se tiene
como respuesta a una solicitud del usuario, así como posibles variantes de la
secuencia normal, tales como secuencias alternativas, comportamiento frente
a excepciones y manejo de errores. El objetivo es describir un trozo de
funcionalidad coherente en todas sus variaciones, incluyendo las condiciones
de error. Para ello el caso de uso se puede describir mediante una descripción
informal en forma de texto.


                                                                                 26


---

         El Lenguaje de Modelado Unificado
          Diagrama de casos de uso


Sus componentes principales serían:
       •Caso de Uso: Describe un grupo de actividades del sistema que
       produce un resultado concreto y tangible, siempre desde el punto de
       vista de los actores. Podrían verse como descriptores de las
       interacciones típicas entre los usuarios y el sistema, representando el
       interfaz externo del mismo y especificando qué requisitos de
       funcionamiento debe tener.


       A la hora de diseñar un diagrama de casos de uso hay que tener en
       cuenta las siguientes reglas:
                    • Cada caso de uso está relacionado como mínimo con un
                    actor.
                    • Cada caso de uso es un iniciador de una secuencia más
                    amplia de acciones del sistema.
                    • Por lo tanto, cada caso de uso lleva al desarrollo de un
                    resultado relevante con valor intrínseco.


       Además, los casos de uso pueden tener relación con otros casos de
uso:


                                                                                 27


---

                  •Include: Especifica una situación en la que un caso
                  ocurre dentro de otro.
                  •Extends: Señala que un caso de uso será extendido por
                  otro en algún momento de la ejecución.
                  •Generalización: Un caso de uso hereda las
                  características del "Super Caso", de forma similar a la
                  herencia de clases.


      • Actor: Un actor es una entidad externa al sistema que interacciona
      con él mediante un caso de uso. Los actores pueden ser gente real,
      otros               ordenadores o algún evento externo. Hay que
      tener claro que los actores representan los diferentes roles de los
      posibles usuarios del sistema   y no a personas o máquinas en
      concreto.


Especificación de CU: http://www.seas.es/blog/wp-
content/uploads/2013/11/tabla-casos-de-uso.jpg         y
http://www.juntadeandalucia.es/servicios/madeja/sites/default/files/imag
ecache/wysiwyg_imageupload_lightbox_preset/wysiwyg_imageupload/1
0/MadejaIR-EjemploCdU_0.png


                                                                             27


---

         El Lenguaje de Modelado Unificado
                   Vista de implementación

         •   La vista de implementación modela los
             componentes de un sistema así como las
             dependencias entre los componentes, para
             poder determinar el impacto de un cambio
             propuesto.

         •   También modela la asignación de clases y de
             otros elementos del modelo a los
             componentes.

         •   La vista de implementación se representa en
             diagramas componentes.


La vista de implementación


Modela los componentes de un sistema –a partir de los cuales se construye la
aplicación– así como las dependencias entre los componentes, para poder
determinar el impacto de un cambio propuesto. También modela la asignación
de clases y de otros elementos del modelo a los componentes.


La vista de implementación se representa en diagramas componentes.


                                                                               28


---

         El Lenguaje de Modelado Unificado
         Diagrama de implementación


La figura muestra un diagrama de componentes para el sistema de taquilla.


Hay tres interfaces de usuario:
la de los clientes que usan un quiosco,
la de los vendedores que usan el sistema de reserva autorizado,
y la de los supervisores que hacen consultas sobre las ventas de entradas.


Hay un componente vendedor de entradas que ordena las peticiones de los
quioscos y de los vendedores;
un componente que procesa los cargos a la tarjeta de crédito; y la base de
datos que contiene la información de la entrada.
El diagrama de componentes muestra los tipos de componentes del sistema;
una configuración particular de la aplicación puede tener más de una copia de
un componente.


Un círculo pequeño con un nombre es una interfaz –un conjunto coherente de
servicios–. Una línea sólida que va desde un componente a una interfaz,
indica que el componente proporciona los servicios de la interfaz.


                                                                                29


---

Una flecha de guiones de un componente a una interfaz indica que el
componente requiere los servicios proporcionados por interfaz. Por ejemplo,
las ventas de suscripciones y las ventas de grupos de entradas, son
proporcionadas por el componente “vendedor de entradas”; las ventas de
suscripciones son accesibles tanto para los quioscos como para los
vendedores, pero las ventas de grupos sólo son accesibles para un vendedor


                                                                              29


---

         El Lenguaje de Modelado Unificado
                         Vista de despliegue.
         •   Esta vista proporciona una oportunidad de
             establecer correspondencias entre las clases
             y los componentes de implementación y
             nodos.

         •   Representa la disposición de las instancias
             de componentes de ejecución en instancias
             de nodos.


La vista de despliegue


Representa la disposición de las instancias de componentes de ejecución en
instancias de nodos. Un nodo es un recurso de ejecución, tal como una
computadora, un dispositivo o memoria.
Esta vista permite determinar las consecuencias de la distribución y de la
asignación de recursos.


La vista de despliegue se representa en diagramas de despliegue.
La figura muestra un diagrama de despliegue del nivel de descriptor para el
sistema de taquilla.
Este diagrama muestra los tipos de nodos del sistema y los tipos de
componentes que contienen. Un nodo se representa como un cubo.


                                                                              30


---

El Lenguaje de Modelado Unificado
            Vista de despliegue.
• Un nodo es un recurso de ejecución, tal como
  una computadora, un dispositivo o memoria.
  Esta    vista    permite   determinar     las
  consecuencias de la distribución y de la
  asignación de recursos.

• La vista de despliegue se representa en
  diagramas de despliegue.


                                                  31


---

PDU
Diagrama de despliegue


                         32


                              32


---

         El Lenguaje de Modelado Unificado
         Diagrama de despliegue


La figura muestra un diagrama de despliegue del nivel de descriptor para el
sistema de taquilla.

Este diagrama muestra los tipos de nodos del sistema y los tipos de
componentes que contienen. Un nodo se representa como un cubo.


                                                                              33


---

         El Lenguaje de Modelado Unificado
         Diagrama de despliegue


La figura muestra un diagrama de despliegue del nivel de instancias, para el
sistema de taquilla.

El diagrama muestra los nodos individuales y sus enlaces, en una versión
particular del sistema. La información de este modelo es consistente con la
información del nivel del descriptor de la figura anterior.


                                                                               34


---

El Lenguaje de Modelado Unificado
              Vista dinámicas
          Vista de la máquina de estados.
 • Una máquina de estados modela las posibles
   historias de vida de un objeto de una clase.
 • Una máquina de estados contiene los estados
   conectados por transiciones.
 • Cada estado modela un período de tiempo,
   durante la vida de un objeto, en el que satisface
   ciertas condiciones.
 • Cuando      ocurre    un evento, se puede
   desencadenar una transición que lleve el objeto a
   un nuevo estado.
 • Cuando se dispara una transición se puede
   ejecutar una acción unida a la transición.


                                                       35


---

El Lenguaje de Modelado Unificado
•   Las máquinas de estados se pueden utilizar
    para describir:

    • interfaces de usuario
    • controladores de dispositivo
    • otros subsistemas reactivos.
    • describir los objetos pasivos que pasan por
      varias fases cualitativas distintas, durante
      su tiempo de vida, cada una de las cuales
      tiene su propio comportamiento especial


                                                     36


---

         El Lenguaje de Modelado Unificado
         Diagrama de estados


La figura muestra un diagrama de estados de la historia de una entrada para
un representación. El estado inicial de una entrada (representado por un punto
negro) es el estado “disponible”.


Antes del comienzo de la temporada, se asignan los asientos para los
suscriptores de la temporada. Las entradas individuales compradas
interactivamente primero se bloquean mientras el cliente hace una selección.
Después de esto, se venden o se liberan si no se eligen.
Si el cliente tarda demasiado en hacer una selección, finaliza el tiempo de la
transacción y se libera el asiento.
Los asientos vendidos para suscriptores de temporada, se pueden cambiar
para otras representaciones, en cuyo caso, vuelven a estar disponibles otra
vez.


                                                                                 37


---

         El Lenguaje de Modelado Unificado
                          Vista de actividades.

            •   Un grafo de actividades es una variante de
                una máquina de estados, que muestra las
                actividades de computación implicadas en la
                ejecución de un cálculo.

            •   Un estado de actividad representa una
                actividad: un paso en el flujo de trabajo o la
                ejecución de una operación.

            •   Un grafo de actividades describe grupos
                secuenciales y concurrentes de actividades.


Vista de actividades.


Un grafo de actividades es una variante de una máquina de estados, que
muestra las actividades de computación implicadas en la ejecución de un
cálculo.


Un estado de actividad representa una actividad: un paso en el flujo de trabajo
o la ejecución de una operación.


Un grafo de actividades describe grupos secuenciales y concurrentes de
actividades.


                                                                                  38


---

         El Lenguaje de Modelado Unificado
         Diagrama de actividades


La figura muestra un diagrama de actividades para la taquilla. Este diagrama
muestra las actividades implicadas en montar una obra. Las flechas muestran
dependencias secuenciales, por ejemplo, las representaciones deben ser
seleccionadas antes de poder planificarlas.
Las barras horizontales representan bifurcaciones o uniones de control. Por
ejemplo, después de planificar la obra, el teatro puede comenzar a darle
publicidad, a comprar guiones, a contratar artistas, a construir decorados, a
diseñar la iluminación, y a hacer los trajes, todo concurrentemente.


El propósito del diagrama de actividades es el de modelar los procesos reales
de una organización humana, pero además se pueden utilizar para modelar
actividades software.
Un diagrama de actividades es provechoso para entender el comportamiento
de alto nivel de la ejecución de un sistema, sin profundizar en los detalles
internos de los mensajes.


Se debe tener en cuenta que un diagrama de actividades puede contener
calles, las cuales son partición de los grafos de actividades que se emplean
para organizar las responsabilidades de las actividades.


                                                                                39


---

Las calles no tienen un significado fijo, pero suelen corresponder a las
unidades organizativas en los modelos de negocios.


                                                                           39


---

         El Lenguaje de Modelado Unificado
                          Vista de interacción.

           •   Describe secuencias de intercambios de
               mensajes entre los roles que implementan el
               comportamiento de un sistema. Un rol es la
               descripción de un objeto, que desempeña
               un determinado papel dentro de una
               interacción, distinto de los otros objetos de
               la misma clase.
               • Diagrama de secuencia
               • Diagrama de colaboración


Vista de interacción.


La vista de interacción describe secuencias de intercambios de mensajes
entre los roles que implementan el comportamiento de un sistema. Un rol es la
descripción de un objeto, que desempeña un determinado papel dentro de
una interacción, distinto de los otros objetos de la misma clase.


Esta visión proporciona una vista integral del comportamiento de un sistema –
es decir, muestra el flujo de control a través de muchos objetos-. La vista de
interacción se exhibe en dos diagramas centrados en distintos aspectos:
diagramas de secuencia y diagramas de colaboración.


                                                                                 40


---

         El Lenguaje de Modelado Unificado
         Diagrama de secuencia.

            •   Muestra un conjunto de mensajes,
                dispuestos en una secuencia temporal.
                Cada rol en la secuencia se muestra como
                una línea de vida, es decir, una línea
                vertical que representa el rol durante cierto
                plazo de tiempo. Los mensajes se muestran
                como flechas entre las líneas de vida.


El diagrama de secuencia.


Un diagrama de secuencia muestra un conjunto de mensajes, dispuestos en
una secuencia temporal. Cada rol en la secuencia se muestra como una línea
de vida, es decir, una línea vertical que representa el rol durante cierto plazo
de tiempo, con la interacción completa. Los mensajes se muestran como
flechas entre las líneas de vida.


Los diagramas de secuencia muestran la forma o secuencia en que se
invocan las acciones, métodos o paso de mensajes entre ciertos
componentes del sistema en un momento dado, poniendo especial énfasis en
el orden y el momento en que se envían los mensajes a los objetos,
representándose visualmente la creación de objetos en el tiempo. En los
diagramas de secuencia, los objetos están representados por líneas
intermitentes verticales (emulando al eje temporal), con el nombre del objeto
en la parte más alta.


Los mensajes son enviados de un objeto a otro en forma de flechas con los
nombres de la operación (o método) y los parámetros.


                                                                                   41


---

         El Lenguaje de Modelado Unificado
         Diagrama de secuencia


Un uso de un diagrama de secuencia es mostrar la secuencia del
comportamiento de un caso de uso.
La figura muestra un diagrama de secuencia para el caso de uso “comprar
entrada”. Este caso de uso lo inicia el cliente en el quiosco, comunicándose
con la taquilla.

Este diagrama de secuencia está en una primera etapa de desarrollo y no
muestra los detalles completos de la interfaz de usuario. Por ejemplo, la forma
exacta de la lista de asientos y el mecanismo de especificar asientos, no se
han definidos aún, pero la comunicación esencial de la interacción ha sido
especificada por el caso de uso.

Ver para fragmentos: http://msdn.microsoft.com/es-es/library/dd465153.aspx


                                                                                  42


---

         El Lenguaje de Modelado Unificado
         Diagrama de colaboración.

           •   Una colaboración modela los objetos y los
               enlaces     significativos dentro  de   una
               interacción.
               Un rol describe un objeto, y un rol en la
               asociación describe un enlace dentro de una
               colaboración.
               Los mensajes se muestran como flechas,
               ligadas a las líneas de la relación, que
               conectan a los roles.
               La secuencia de mensajes, se indica con los
               números secuenciales que preceden a las
               descripciones del mensaje.


El diagrama de colaboración.


Una colaboración modela los objetos y los enlaces significativos dentro de una
interacción. Un rol describe un objeto, y un rol en la asociación describe un
enlace dentro de una colaboración.


Los mensajes se muestran como flechas, ligadas a las líneas de la relación,
que conectan a los roles. La secuencia de mensajes, se indica con los
números secuenciales que preceden a las descripciones del mensaje.


Un uso de un diagrama de colaboración es mostrar la implementación de una
operación. La colaboración muestra los parámetros y las variables locales de
la operación, así como asociaciones permanentes.


                                                                                 43


---

         El Lenguaje de Modelado Unificado
         Diagrama de colaboración


La figura muestra un diagrama de colaboración para la interacción de la
reserva de entradas en una fase ulterior del desarrollo. La colaboración
muestra la interacción entre objetos internos en la aplicación para reservar
entradas. La petición llega del quiosco y se utiliza para encontrar en la base
de datos de la representación deseada en el conjunto de todas las
representaciones.

El puntero “db” que es devuelto al objeto “vendedor de entradas” representa
un enlace local transitorio a una base de datos de representaciones, que
persiste durante la interacción y después se desecha.

El vendedor de entradas solicita un número de asientos para la
representación, se bloquea temporalmente, y se devuelve al quiosco para la
selección de los clientes. Cuando el cliente hace una selección de la lista de
asientos, se obtienen los asientos seleccionados y el resto son liberados.


                                                                                 44


---

El Lenguaje de Modelado Unificado
•   Tanto los diagramas de secuencia como los de
    colaboración muestran interacciones, pero
    acentúan aspectos diferentes.

    •   Un diagrama de secuencia muestra secuencia
        en el tiempo como dimensión geométrica, pero
        las relaciones entre los roles son implícitas.

    •   Un diagrama de colaboración muestra las
        relaciones entre roles geométricamente, y
        relaciona los mensajes con las relaciones, pero
        las secuencias temporales están menos claras,
        porque vienen dadas por los números de
        secuencia.


                                                          45


---

         El Lenguaje de Modelado Unificado
                    Vista de gestión del modelo.

           •   Modela la organización del modelo en sí
               mismo.

           •   Un modelo abarca un conjunto de paquetes
               que contienen los elementos del modelo,
               tales como clases, máquinas de estados, y
               casos de uso.

           •   Los paquetes         pueden       contener      otros
               paquetes


Vista de gestión del modelo.


La vista de gestión del modelo modela la organización del modelo en sí
mismo.


Un modelo abarca un conjunto de paquetes que contienen los elementos del
modelo, tales como clases, máquinas de estados, y casos de uso. Los
paquetes pueden contener otros paquetes: por lo tanto, un modelo señala un
paquete raíz, que contiene indirectamente todo el contenido del modelo. Los
paquetes son unidades para manipular el contenido de un modelo, así como
unidades para el control de acceso y el control de configuración.


Cada elemento del modelo pertenece a un paquete o a otro elemento.


Un modelo es una descripción completa de un sistema, con una determinada
precisión, desde un punto de vista. Puede haber varios modelos de un
sistema desde distintos puntos de vista; por ejemplo, un modelo de análisis y
un modelo de diseño. Un modelo se representa como una clase especial de
p          a          q         u           e          t         e          .


                                                                                46


---

Un subsistema es otro paquete especial. Representa una porción de un
sistema, con una interfaz perfectamente determinada, que puede ser
implementado como un componente distinto.


                                                                       46


---

         El Lenguaje de Modelado Unificado
         Diagrama de paquetes


La figura muestra la descomposición de la totalidad del sistema de teatro en
paquetes y sus relaciones de dependencia.

El subsistema de taquilla incluye los ejemplos anteriores de este capítulo; el
sistema completo también incluye operaciones del teatro y subsistemas de
planificación.

Cada subsistema consta de varios paquetes.


                                                                                 47


---

FIN


      48


---
