# DSI1 Unidad V I - Diseno de software, arquitectura, componentes, acoplamiento y cohesion

Fuente PDF: `DSI1/Unidad_V_I.pdf`.

Markdown operativo: `DSI1/_md/unidad-v-i.md`.

Paginas PDF: 49. Palabras extraidas: 3757.

Nota: extraccion automatica con `pdftotext -layout` para busqueda y recuperacion por agentes. Para tablas, figuras o formato exacto, consultar el PDF fuente.

---

1


---

2


---

El diseño de SW es un proceso iterativo a través del cual se traducen los
requisitos en un representación del SW.


                                                                            3


---

El diseño de SW es un proceso iterativo a través del cual se traducen los
requisitos en un representación del SW.


                                                                            4


---

El proceso de desarrollo de software es aquel en el que las necesidades del
usuario son traducidas en requisitos de software, estos transformados en
diseño y el diseño implementado en código.


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

10


---

•En ocasiones, los clientes están muy preparados y pueden entender el qué y
el cómo en forma conjunta, y en esos casos, los diseños conceptual y técnico
pueden combinarse en un único documento de diseño.
•Es importante vincular los diseños conceptual y técnico, de modo que los
cambios en uno de ellos se reflejen como cambios en el otro.
•Un sistema queda definido por sus límites, atributos, entidades y relaciones.


                                                                                 11


---

El proceso de diseño avanza de una visión general de software a una visión
    más estrecha que define el detalle requerido para implementar un sistema.
    Los pasos de dicho proceso se pueden enumerar de la siguiente manera:
1. El proceso comienza con un enfoque en la arquitectura.
2. Se definen los subsistemas.
3. Se establecen los mecanismos de comunicación entre los subsistemas.
4. Se identifican los componentes.
5. Se desarrolla una descripción detallada de cada componente.


Además, se diseñan las interfaces internas, externa y del usuario.


                                                                                12


---

13


---

Luego M sería el número de módulos que resultaría en un costo de desarrollo
mínimo, pero, no se tiene la sofisticación necesaria para predecir M con
seguridad.


Además, la modularidad permite aislar aquellas partes del problema que son
difíciles de tratar, y los niveles de abstracción permiten comprender el
problema en niveles crecientes de detalle.


                                                                              14


---

15


---

Dan como resultado productos de calidad. Por calidad se entiende a la
  adecuación del software a los requisitos exigidos.


Extensibilidad. Facilidad para adaptarse a los cambios en las
   especificaciones. Se logra haciendo simples los diseños de los módulos
   autónomos.
Funcionalidad. Conjunto de posibilidades ofrecido por un sistema.
Solidez o robustez. Habilidad para funcionar aún en condiciones anormales,
   es decir, con aquellos casos no explicitados en las especificaciones. Si se
   presentan el sistema termina “limpiamente”.
Facilidad de uso. Facilidad con la que personas con diferentes niveles de
   experiencia pueden aprender a usar los productos software.
Eficiencia. Facilidad de utilizar el mínimo de recursos de cómputo para
   conseguir mayor rapidez y menor necesidad de almacenamiento.
Reutilización. Habilidad para utilizar de nuevo productos de software
  completos o partes de ellos en nuevas aplicaciones.
Compatibilidad. Facilidad con la que un producto software puede combinarse
  con otros. Se logra homogeneidad en el diseño y estandarización en la
  comunicación entre programas.


                                                                                 16


---

Portabilidad. Facilidad de transferir productos a diferentes plataformas.


                                                                            16


---

La independencia funcional se adquiere desarrollando módulos con una
clara función, evitando una excesiva interacción con otros módulos.


                                                                       17


---

El acoplamiento es la medida de la interconexión entre módulos de un
    programa.


El acoplamiento depende de varios aspectos:
      •   Las referencias hechas de un componente a otro.
      •   La cantidad de datos pasados de un componente a otro.
      •   El grado de control que un componente tiene sobre el otro.
      •   El grado de complejidad de la interfaz entre los componentes


El rango de medidas de Acoplamiento es:
             •   Acoplamiento de contenido: Un componente modifica a otro.
                 El componente modificado es completamente dependiente
                 del que lo modifica.
             •   Acoplamiento común: Por que ambos componentes utilizan
                 un área común para almacenar datos.
             •   Acoplamiento por control: Un componente pasa parámetros
                 para controlar la actividad del otro componente.
             •   Acoplamiento por estampado: Se usa una estructura de


                                                                             18


---

    datos para pasar información de un componente a otro.
•   Acoplamiento por datos: Solo se pasan datos de un
    componente a otro.
•   No Acoplados.


                                                            18


---

Un módulo cohesivo ejecuta una tarea sencilla de un procedimiento de SW y
   requiere poca interacción con procedimientos que ejecutan otras partes de
   un programa.


Los grados de Cohesión son:
             •   Cohesión coincidental: Ocurre cuando las partes de un
                 componente no tienen relación alguna entre sí y se
                 encuentran en un mismo componente por razones de
                 conveniencia o simplemente porque sí.
             •   Cohesión lógica: Algunas funciones o elementos de datos
                 relacionados lógicamente están puestos en el mismo
                 componente. Estos elementos no están relacionados
                 funcionalmente.
             •   Cohesión temporal: Las funciones en sí sólo están
                 relacionadas por el momento en que ocurren.
             •   Cohesión procedimental: Las funciones se agrupan en un
                 mismo componente para asegurar el orden.
             •   Cohesión comunicativa: Las funciones operan, o producen, el
                 mismo conjunto de datos.


                                                                               19


---

•   Cohesión secuencial: La salida proporcionada por una parte
    del componente actúa como entrada para la parte que le
    sigue.
•   Cohesión funcional: Cada elemento de proceso es esencial
    para la realización de una única función y todos los
    elementos esenciales están contenidos en un único
    componente. El componente no sólo realiza la función para la
    cual ha sido diseñado, sino que realiza esa función y nada
    más.


                                                                   19


---

La independencia funcional se adquiere desarrollando módulos con una
clara función, evitando una excesiva interacción con otros módulos.


                                                                       20


---

Ante una falla (desvío del sistema respecto de su comportamiento requerido)
   las posibles soluciones son:
Eliminarlo
prevenir las condiciones de entrada
agregar comportamiento para la recuperación del daño provocado por la falla


                                                                              21


---

Ante una falla (desvío del sistema respecto de su comportamiento requerido)
   las posibles soluciones son:
Eliminarlo
prevenir las condiciones de entrada
agregar comportamiento para la recuperación del daño provocado por la falla


                                                                              22


---

Debe tenerse en cuenta que no todos los parámetros tienen el mismo peso.


                                                                           23


---

Diseño a nivel de componentes: Define las estructuras de datos, los
   algoritmos, las características de la interfaz y los mecanismos de
   comunicación asignados a cada componente de software. Como
   resultado se obtiene el diseño de cada componente, representado
   en una notación gráfica, tabular o textual.
      •   Componente: Es una parte modular, desplegable y
          reemplazable de un sistema que encapsula implementación y
          expone un conjunto de interfaces. Es un bloque de
          construcción modular para el software de cómputo.
Concepto orientado a objetos.
      •   Componente: Es un conjunto de clases que colaboran entre
          sí. Cada clase un componente se ha elaborado
          completamente para incluir todos los atributos y las
          operaciones relevantes para su implementación. Como parte
          de la elaboración del diseño, también deben definirse todas
          las interfaces (mensajes) que permiten que las clases se
          comuniquen con otras clases de diseño.
Concepto convencional.
      •   Componente: Es un elemento funcional de un programa que
          incorpora la lógica del procesamiento, las estructuras interna


                                                                           24


---

de los datos necesarios para implementar dicha lógica, y una
interfaz que permita la invocación del componente y el paso
de los datos. También llamado módulo.


                                                               24


---

Diseño a nivel de componentes: Define las estructuras de datos, los
   algoritmos, las características de la interfaz y los mecanismos de
   comunicación asignados a cada componente de software. Como
   resultado se obtiene el diseño de cada componente, representado
   en una notación gráfica, tabular o textual.
      •   Componente: Es una parte modular, desplegable y
          reemplazable de un sistema que encapsula implementación y
          expone un conjunto de interfaces. Es un bloque de
          construcción modular para el software de cómputo.
Concepto orientado a objetos.
      •   Componente: Es un conjunto de clases que colaboran entre
          sí. Cada clase un componente se ha elaborado
          completamente para incluir todos los atributos y las
          operaciones relevantes para su implementación. Como parte
          de la elaboración del diseño, también deben definirse todas
          las interfaces (mensajes) que permiten que las clases se
          comuniquen con otras clases de diseño.
Concepto convencional.
      •   Componente: Es un elemento funcional de un programa que
          incorpora la lógica del procesamiento, las estructuras interna


                                                                           25


---

de los datos necesarios para implementar dicha lógica, y una
interfaz que permita la invocación del componente y el paso
de los datos. También llamado módulo.


                                                               25


---

Diseño a nivel de componentes: Define las estructuras de datos, los
   algoritmos, las características de la interfaz y los mecanismos de
   comunicación asignados a cada componente de software. Como
   resultado se obtiene el diseño de cada componente, representado
   en una notación gráfica, tabular o textual.
      •   Componente: Es una parte modular, desplegable y
          reemplazable de un sistema que encapsula implementación y
          expone un conjunto de interfaces. Es un bloque de
          construcción modular para el software de cómputo.
Concepto orientado a objetos.
      •   Componente: Es un conjunto de clases que colaboran entre
          sí. Cada clase un componente se ha elaborado
          completamente para incluir todos los atributos y las
          operaciones relevantes para su implementación. Como parte
          de la elaboración del diseño, también deben definirse todas
          las interfaces (mensajes) que permiten que las clases se
          comuniquen con otras clases de diseño.
Concepto convencional.
      •   Componente: Es un elemento funcional de un programa que
          incorpora la lógica del procesamiento, las estructuras interna


                                                                           26


---

de los datos necesarios para implementar dicha lógica, y una
interfaz que permita la invocación del componente y el paso
de los datos. También llamado módulo.


                                                               26


---

27


---

El universo computacional está poblado por objetos, cada uno responsable de
sí mismo, y comunicándose con los demás por medio de mensajes. Cada
objeto representa una instancia de alguna clase, y estas clases son miembros
de una jerarquía de clase unidas vía relaciones de herencia.


La diferencia entre un objeto y una clases que un objeto es una entidad
concreta que existe en tiempo y espacio, mientras que una clase representa
una abstracción, la esencia de un objeto.


Robustez. La robustez de un sistema debe ser uno de los objetivos
principales del diseño. El sistema debe ser protegidos contra errores y ofrecer
diagnósticos que permitan identificar fallas, en particular aquellas que son
fatales. Durante el desarrollo, a veces es bueno insertar instrucciones internas
en el código para descubrir fallas, aunque luego se eliminen durante la
producción. En general, se debe escoger lenguajes de programación que
apoyen estos aspectos, como son el manejo de excepciones. El
encapsulamiento es fundamental para la robustez del sistema. Ocultar la
información interna, atributos e implementación de métodos de una clase,
permite cambiarla sin afectar al resto del sistema. Únicamente la interfaz de
los métodos afecta a las demás clases.


                                                                                   28


---

Reuso. El reuso es un aspecto fundamental del diseño. Cuanto más se pueda
reutilizar el código será mejor la robustez del sistema. El encapsulamiento es
muy efectivo para lograr el reuso, se aplica tanto al nivel de los objetos como
de componentes desarrollados en otras aplicaciones. Estos componentes se
reutilizan como se diseñaron, agregándolos a nuevas interfaces.


Extensibilidad. La mayor parte de los sistemas son extendidos de manera
imprevista. Se debe encapsular otra vez las clases, ocultando su estructura
interna a las otras clases. Sólo los métodos de las clases deben acceder sus
atributos.


                                                                                  28


---

El universo computacional está poblado por objetos, cada uno responsable de
sí mismo, y comunicándose con los demás por medio de mensajes. Cada
objeto representa una instancia de alguna clase, y estas clases son miembros
de una jerarquía de clase unidas vía relaciones de herencia.


La diferencia entre un objeto y una clases que un objeto es una entidad
concreta que existe en tiempo y espacio, mientras que una clase representa
una abstracción, la esencia de un objeto.


Robustez. La robustez de un sistema debe ser uno de los objetivos
principales del diseño. El sistema debe ser protegidos contra errores y ofrecer
diagnósticos que permitan identificar fallas, en particular aquellas que son
fatales. Durante el desarrollo, a veces es bueno insertar instrucciones internas
en el código para descubrir fallas, aunque luego se eliminen durante la
producción. En general, se debe escoger lenguajes de programación que
apoyen estos aspectos, como son el manejo de excepciones. El
encapsulamiento es fundamental para la robustez del sistema. Ocultar la
información interna, atributos e implementación de métodos de una clase,
permite cambiarla sin afectar al resto del sistema. Únicamente la interfaz de
los métodos afecta a las demás clases.


                                                                                   29


---

Reuso. El reuso es un aspecto fundamental del diseño. Cuanto más se pueda
reutilizar el código será mejor la robustez del sistema. El encapsulamiento es
muy efectivo para lograr el reuso, se aplica tanto al nivel de los objetos como
de componentes desarrollados en otras aplicaciones. Estos componentes se
reutilizan como se diseñaron, agregándolos a nuevas interfaces.


Extensibilidad. La mayor parte de los sistemas son extendidos de manera
imprevista. Se debe encapsular otra vez las clases, ocultando su estructura
interna a las otras clases. Sólo los métodos de las clases deben acceder sus
atributos.


                                                                                  29


---

Los patrones de diseño son la base para la búsqueda de soluciones a
    problemas comunes en el desarrollo de software y otros ámbitos
    referentes al diseño de interacción o interfaces.
Un patrón de diseño resulta ser una solución a un problema de diseño.
    Para que una solución sea considerada un patrón debe poseer
    ciertas características. Una de ellas es que debe haber
    comprobado su efectividad resolviendo problemas similares en
    ocasiones anteriores. Otra es que debe ser reutilizable, lo que
    significa que es aplicable a diferentes problemas de diseño en
    distintas circunstancias.


"Cada patrón describe un problema que ocurre infinidad de veces en
   nuestro entorno, así como la solución al mismo, de tal modo que
   podemos utilizar esta solución un millón de veces más adelante sin
   tener que volver a pensarla otra vez."


                                                                        30


---

Los patrones de diseño pretenden:
      • Proporcionar catálogos de elementos reusables en el diseño
          de sistemas software.
      • Evitar la reiteración en la búsqueda de soluciones a
          problemas ya conocidos y solucionados anteriormente.
      • Formalizar un vocabulario común entre diseñadores.
      • Estandarizar el modo en que se realiza el diseño.
      • Facilitar el aprendizaje de las nuevas generaciones de
          diseñadores condensando conocimiento ya existente.

Asimismo, no pretenden:
      • Imponer ciertas alternativas de diseño frente a otras.
      • Eliminar la creatividad inherente al proceso de diseño.

No es obligatorio utilizar los patrones, solo es aconsejable en el caso
    de tener el mismo problema o similar que soluciona el patrón,
    siempre teniendo en cuenta que en un caso particular puede no ser
    aplicable. "Abusar o forzar el uso de los patrones puede ser un
    error".


                                                                          31


---

Los patrones de diseño pretenden:
      • Proporcionar catálogos de elementos reusables en el diseño
          de sistemas software.
      • Evitar la reiteración en la búsqueda de soluciones a
          problemas ya conocidos y solucionados anteriormente.
      • Formalizar un vocabulario común entre diseñadores.
      • Estandarizar el modo en que se realiza el diseño.
      • Facilitar el aprendizaje de las nuevas generaciones de
          diseñadores condensando conocimiento ya existente.

Asimismo, no pretenden:
      • Imponer ciertas alternativas de diseño frente a otras.
      • Eliminar la creatividad inherente al proceso de diseño.

No es obligatorio utilizar los patrones, solo es aconsejable en el caso
    de tener el mismo problema o similar que soluciona el patrón,
    siempre teniendo en cuenta que en un caso particular puede no ser
    aplicable. "Abusar o forzar el uso de los patrones puede ser un
    error".


                                                                          32


---

Patrones de creación
        •    Object Pool: se obtienen objetos nuevos a través de la clonación. Utilizado
             cuando el costo de crear una clase es mayor que el de clonarla. Especialmente
             con objetos muy complejos. Se especifica un tipo de objeto a crear y se utiliza
             una interfaz del prototipo para crear un nuevo objeto por clonación. El proceso de
             clonación se inicia instanciando un tipo de objeto de la clase que queremos
             clonar.
        •    Abstract Factory (fábrica abstracta): permite trabajar con objetos de distintas
             familias de manera que las familias no se mezclen entre sí y haciendo
             transparente el tipo de familia concreta que se esté usando.
        •    Builder (constructor virtual): abstrae el proceso de creación de un objeto
             complejo, centralizando dicho proceso en un único punto.
        •    Factory Method (método de fabricación): centraliza en una clase constructora la
             creación de objetos de un subtipo de un tipo determinado, ocultando al usuario la
             casuística, es decir, la diversidad de casos particulares que se pueden prever,
             para elegir el subtipo que crear.
        •    Prototype (prototipo): crea nuevos objetos clonándolos de una instancia ya
             existente.
        •    Singleton (instancia única): garantiza la existencia de una única instancia para
             una clase y la creación de un mecanismo de acceso global a dicha instancia.


[http://patronesdediseno.net16.net/creacion.html]


                                                                                                  33


---

Patrones estructurales
            • Adapter (Adaptador): Adapta una interfaz para que pueda ser
               utilizada por una clase que de otro modo no podría utilizarla.
            • Bridge (Puente): Desacopla una abstracción de su
               implementación.
            • Composite (Objeto compuesto): Permite tratar objetos
               compuestos como si de uno simple se tratase.
            • Decorator (Envoltorio): Añade funcionalidad a una clase
               dinámicamente.
            • Facade (Fachada): Provee de una interfaz unificada simple
               para acceder a una interfaz o grupo de interfaces de un
               subsistema.
            • Flyweight (Peso ligero): Reduce la redundancia cuando gran
               cantidad de objetos poseen idéntica información.
            • Proxy: Mantiene un representante de un objeto.
            • Módulo: Agrupa varios elementos relacionados, como clases,
               singletons, y métodos, utilizados globalmente, en una entidad
               única.

[http://patronesdediseno.net16.net/estructurales.html]


                                                                                34


---

Patrones de comportamiento
               •   Chain of Responsibility (Cadena de responsabilidad): Permite establecer la línea
                   que deben llevar los mensajes para que los objetos realicen la tarea indicada.
               •   Command (Orden): Encapsula una operación en un objeto, permitiendo ejecutar
                   dicha operación sin necesidad de conocer el contenido de la misma.
               •   Interpreter (Intérprete): Dado un lenguaje, define una gramática para dicho
                   lenguaje, así como las herramientas necesarias para interpretarlo.
               •   Iterator (Iterador): Permite realizar recorridos sobre objetos compuestos
                   independientemente de la implementación de estos.
               •   Mediator (Mediador): Define un objeto que coordine la comunicación entre objetos
                   de distintas clases, pero que funcionan como un conjunto.
               •   Memento (Recuerdo): Permite volver a estados anteriores del sistema.
               •   Observer (Observador): Define una dependencia de uno-a-muchos entre objetos,
                   de forma que cuando un objeto cambie de estado se notifique y actualicen
                   automáticamente todos los objetos que dependen de él.
               •   State (Estado): Permite que un objeto modifique su comportamiento cada vez que
                   cambie su estado interno.
               •   Strategy (Estrategia): Permite disponer de varios métodos para resolver un
                   problema y elegir cuál utilizar en tiempo de ejecución.
               •   Template Method (Método plantilla): Define en una operación el esqueleto de un
                   algoritmo, delegando en las subclases algunos de sus pasos, esto permite que
                   las subclases redefinan ciertos pasos de un algoritmo sin cambiar su estructura.
               •   Visitor (Visitante): Permite definir nuevas operaciones sobre una jerarquía de
                   clases sin modificar las clases sobre las que opera.

[http://patronesdediseno.net16.net/comportamiento.html]


                                                                                                      35


---

Patrones de comportamiento
               •   Chain of Responsibility (Cadena de responsabilidad): Permite establecer la línea
                   que deben llevar los mensajes para que los objetos realicen la tarea indicada.
               •   Command (Orden): Encapsula una operación en un objeto, permitiendo ejecutar
                   dicha operación sin necesidad de conocer el contenido de la misma.
               •   Interpreter (Intérprete): Dado un lenguaje, define una gramática para dicho
                   lenguaje, así como las herramientas necesarias para interpretarlo.
               •   Iterator (Iterador): Permite realizar recorridos sobre objetos compuestos
                   independientemente de la implementación de estos.
               •   Mediator (Mediador): Define un objeto que coordine la comunicación entre objetos
                   de distintas clases, pero que funcionan como un conjunto.
               •   Memento (Recuerdo): Permite volver a estados anteriores del sistema.
               •   Observer (Observador): Define una dependencia de uno-a-muchos entre objetos,
                   de forma que cuando un objeto cambie de estado se notifique y actualicen
                   automáticamente todos los objetos que dependen de él.
               •   State (Estado): Permite que un objeto modifique su comportamiento cada vez que
                   cambie su estado interno.
               •   Strategy (Estrategia): Permite disponer de varios métodos para resolver un
                   problema y elegir cuál utilizar en tiempo de ejecución.
               •   Template Method (Método plantilla): Define en una operación el esqueleto de un
                   algoritmo, delegando en las subclases algunos de sus pasos, esto permite que
                   las subclases redefinan ciertos pasos de un algoritmo sin cambiar su estructura.
               •   Visitor (Visitante): Permite definir nuevas operaciones sobre una jerarquía de
                   clases sin modificar las clases sobre las que opera.

[http://patronesdediseno.net16.net/comportamiento.html]


                                                                                                      36


---

Los patrones arquitectónicos, o patrones de arquitectura, son patrones de
diseño de software que ofrecen soluciones a problemas de arquitectura de
software en ingeniería de software. Dan una descripción de los elementos y el
tipo de relación que tienen junto con un conjunto de restricciones sobre cómo
pueden ser usados. Un patrón arquitectónico expresa un esquema de
organización estructural esencial para un sistema de software, que consta de
subsistemas, sus responsabilidades e interrelaciones. En comparación con los
patrones de diseño, los patrones arquitectónicos tienen una nivel de
abstracción mayor.


                                                                                37


---

Aunque un patrón arquitectónico comunica una imagen de un sistema, no es
una arquitectura como tal. Un patrón arquitectónico es más un concepto que
captura elementos esenciales de una arquitectura de software. Muchas
arquitecturas diferentes pueden implementar el mismo patrón y por lo tanto
compartir las mismas características. Además, los patrones son a menudo
definidos como una cosa "estrictamente descrita y comúnmente disponible".
Por ejemplo, la arquitectura en capas es un estilo de llamamiento-y-regreso,
cuando define uno un estilo general para interaccionar. Cuando esto es
descrito estrictamente y comúnmente disponible, es un patrón.


Uno de los aspectos más importantes de los patrones arquitectónicos es que
encarnan diferentes atributos de calidad. Por ejemplo, algunos patrones
representan soluciones a problemas de rendimiento y otros pueden ser
utilizados con éxito en sistemas de alta disponibilidad. En las primeras fases
del diseño, un arquitecto de software escoge qué patrones arquitectónicos
mejor ofrecen las calidades deseadas para el sistema.


Algunos de esos aspectos no funcionales son:


• Control de acceso: Hay muchas situaciones en las cuales el acceso a


                                                                                 38


---

  datos, características y funcionalidad son limitadas a la definición de los
  usuarios. Desde un punto de vista arquitectónico, acceder a determinadas
  partes del software debe tener un riguroso control.
• Concurrencia: Muchas aplicaciones deben manejar múltiples tareas de
  forma que simule el paralelismo. Hay muchas formas de manejar esta
  concurrencia, y cada una puede ser presentada por un patrón
  arquitectónico diferente.
• Distribución: El problema de distribución dirige el problema de forma en que
  los sistemas o componentes se comunican con otros en un entorno
  distribuido. El patrón más común para afrontar el problema es "the broker".
  Actuando como un "middleman" entre el componente cliente y el servidor.
  El cliente envía un mensaje al "broker" y éste se encarga de completar la
  conexión.
Persistencia:


Los datos persistentes son almacenados en bases de datos o archivos y
pueden ser leídos o modificados por otros procesos más adelante. En los
entornos orientados a objetos esto va más allá, y lo que puede ser accedido o
modificable son las propiedades de los objetos.


                                                                                 38


---

Ejemplos de patrones arquitectónicos:
• Programación por capas
• Tres niveles
• Pipeline
• Invocación implícita
• Arquitectura en pizarra
• Arquitectura dirigida por eventos
• Peer-to-peer
• Arquitectura orientada a servicios
• Modelo-Vista-Controlador


                                        39


---

40


---
