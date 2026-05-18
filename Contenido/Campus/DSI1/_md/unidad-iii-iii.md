# DSI1 Unidad III III - Proceso Unificado de Desarrollo de Software

Fuente PDF: `DSI1/Unidad_III_III.pdf`.

Markdown operativo: `DSI1/_md/unidad-iii-iii.md`.

Paginas PDF: 31. Palabras extraidas: 1896.

Nota: extraccion automatica con `pdftotext -layout` para busqueda y recuperacion por agentes. Para tablas, figuras o formato exacto, consultar el PDF fuente.

---

DISEÑO DE SISTEMAS
    INFORMÁTICOS I


                     1


                         1


---

          Unidad III
      El Proceso de
Desarrollo Unificado


                       2


                           2


---

         PDU
         TEMARIO
         • Características del producto de software.
         • El paradigma de desarrollo iterativo e
           incremental.
         • Ciclo de Vida del Proceso Unificado.
         • Fases e iteraciones.
         • Disciplinas-
           Flujos de trabajos fundamentales y de
           soporte.
         • Fases del UDP.
                                                                    3


El paradigma de desarrollo iterativo e incremental. Presentación del
concepto de Proceso Unificado de Desarrollo de Software.
•   Disciplinas
    Flujos de trabajos fundamentales (Captura de Requisitos; Análisis; Diseño;
    Implementación; Prueba) y de soporte (Gestión de Configuración;
    Administración del Ambiente; Gestión de Proyecto).
•   Fases del UDP:
    Inicial, Elaboración, Construcción y Transición.


                                                                                 3


---

        PDU
                      Proceso de desarrollo de SW.

           • Como transformar requisitos de usuario en sistema.
           • Se basa en componentes unidos por interfases.
           • Utiliza UML como forma gráfica.

                        Principales características:

        •Dirigido por CU.

           • Sigue un hilo conductor, que son los flujos.
           • Son requerimientos funcionales (es la definición).
           • Resultado: Modelo de CU. (Que debe hacer el sistema
             para cada usuario).
           • CU Guían: Diseño, Implementación y Pruebas.
                                                                  4


El Proceso Unificado es un proceso de desarrollo de software: “conjunto de
actividades necesarias para transformar los requisitos del usuario en un
sistema software”.


                                                                             4


---

PDU
•Centrado arquitectura.

   • Diferentes vistas del sistema.
   • Aspectos estáticos y dinámicos.
   • Vista del diseño completo dejando de lado los detalles
     (Tener en cuenta que factores influyen).
   • Función y Forma: ambas deben ser tenidas en cuenta.

•Iterativo e incremental.

   •   Dividir como si fueran pequeños proyectos.
   •   Cada CU es un incremento.
   •   Iteraciones → paso de flujo del trabajo.
   •   Incremento → crecimiento del Producto.

                                                       5


                                                              5


---

        PDU
         La Iteración: Trata Grupo CU = una funcionalidad.
                       Manejan los riesgos.

         La Iteración: Es CU, análisis, diseño, implementación y
                      pruebas llegando a un estado.

         No tienen que ser aditivos.

         Por cada iteración se agregan CU relevantes.
         Nuevamente diseño, implementación y pruebas.


                                                                  6


Cada miniproyecto es una iteración que resulta en un incremento. Las
iteraciones deben estar controladas (debe existir una planificación)
Secuenciar las iteraciones en un orden lógico.
No tienen que ser aditivos: a veces deben ser reemplazados diseños
superficial por uno mas detallado o sofisticado.


                                                                       6


---

PDU
•Ventajas:

   • Reduce riesgos de costo y de esfuerzo.

   • Reduce riesgo de no entregar un producto en el
     calendario previsto. (tiempo que se emplea en resolver
     problemas, es empleado en realizar una buena
     definición)

   • Acelera ritmo de esfuerzo de desarrollo.

   • Requisitos    no    pueden    definirse    inicialmente.
     (refinamiento)


                                                           7


                                                                7


---

         PDU
                          Fases dentro de un ciclo:
           • Inicio
           • Elaboración
           • Construcción
           • Transición.
             Cada fase tiene su iteración. La fase terminada se
             identifica con los hitos.
                                 El producto.
         Cada ciclo entrega una nueva versión del sistema →
         PRODUCTO ES TODO (Completo - es + que el código).
         Modelo CU → Especificado por Modelo Análisis → Realizado por
         Modelo Diseño → Distribuido por Modelo Despliegue →
         Implementado por Modelo Implementación → Verificado por
         Modelo Prueba
                                                                     8


El PDU se repite a lo largo de una serie de ciclos que constituyen la vida de
un sistema.
Producto terminado incluye requisitos, CU, especificaciones NF , casos de
pruebas, modelo de arquitectura y modelo visual.
Modelo CU: con todas sus relaciones con los usuarios
Modelo Análisis: refinar los CU y establecer la asignación inicial de
funcionalidades del sistema a un conjunto de objetos que proporcionan el
comportamiento.
Modelo Diseño: define 1. la estructura estática del sistema como
subsistemas, clases e interfaces y 2. Los CU reflejados como colaboraciones
entre los subsistemas, clases e interfaces.
Modelo de implementación: que incluye los componentes y la correspondencia
entre los componentes y las clases
Modelo Implementación: que incluye los componentes (código fuente) y la
correspondencia entre los componentes y las clases.
Modelo Despliegue; que define los nodos físicos y la correspondencia entre
los componentes y los nodos
Modelo Prueba: describe los casos de prueba que verifican los CU.


                                                                                8


---

PDU
• Fase Inicio:

   Se desarrolla la descripción del producto final y se presenta
   el análisis del negocio.
   CU mas simplificados que contiene a los CU mas críticos.
   Arquitectura provisional.
   Identificar y priorizar los riesgos mas importantes.

• Fase Elaboración:

   Especificación de la mayoría de los CU y se diseña la
   arquitectura del sistema. ( se representa en formas de
   vistas)
   Modelo CU / Modelo Análisis / Modelo Diseño / Despliegue
   / Modelo Implementación
                                                            9


                                                                   9


---

PDU
•Fase Construcción:

   Se crea el producto. Debe estar preparado para su entrega
   al usuario. La arquitectura puede no ser la final.

•Fase Transición:

   El producto se convierte en versión Beta.
   Se corrigen problemas y se incorporan mejoras.
   Incluye otras acciones


                                                       10


                                                               10


---

PDU


      11


           11


---

PDU


      12


           12


---

PDU
Las 4 Ps

•Personal.

   Arquitectos, desarrolladores, Ing. Pruebas, y soporte
   además de usuarios, clientes y stakeholders.

•Los procesos de desarrollo afectan a las personas:
   o Viabilidad del proyecto
   o Gestión del riesgo
   o Estructura de equipos
   o Planificación del proyecto
   o Facilidad de comprensión del proyecto
   o Sensación de cumplimiento
                                                      13


                                                           13


---

PDU
• Producto.

   Artefactos que se crean.
   Artefactos: cualquier tipo de      información creada,
   producida, cambiada o utilizada por los desarrolladores
   para crear el sistema.
   Colección de modelos: los mencionados. Abstracción del
   sistema.
   Relación entre modelos: los mencionados.
• Proyecto.

   Única manera de gestionar la complejidad.
   Comprender los factores del éxito críticos y enfoque de
   sentido común para planificar, supervisar y controlar el
   proyecto.
                                                       14


                                                              14


---

PDU
• Proceso.
    Proporciona marco de trabajo establecer un detallado plan
    para el desarrollo del software.
   Número de tareas se puede aplicar a todos los proyectos
   de software, sin tener en cuenta su tamaño o complejidad.
   (Tareas, hitos, productos del trabajo y puntos de control de
   calidad) permiten tareas adaptarse a las características del
   proyecto de Software y a los requisitos del equipo del
   proyecto
Diferenciación de los procesos.
(No todos los procesos son iguales)
   • Factores organizativos.
   • Factores del dominio.
   • Factores del ciclo de vida.
   • Factores técnicos.
                                                          15


                                                                  15


---

        PDU
         • Herramientas.

            Son esenciales para el proceso. Dan soporte al ciclo de
            vida.

            Influyen en el proceso: automatizar procesos repetitivos,
            gestionar grandes volúmenes de datos, etc.

            El proceso dirige a las herramientas: deben ser fáciles
            de usar, deben poder probar otras alternativas.

            Guiar a los desarrolladores en la implementación para
            lograr que se ajusten a las necesidades del cliente.


                                                                  16


Las necesidades del cliente no son fáciles de entender.
Captura de Req: 1. Encontrar los mas importantes, 2. Representarlo de modo
adecuado.


                                                                             16


---

        PDU
         Dirigido por los CU

         La eficiencia se mide en Coste / Calidad / Tiempo de
         desarrollo.
            •Requerimiento → Modelo CU
            •Análisis → Modelo Análisis
            •Diseño → Modelo Diseño / Modelo Despliegue
            •Implementación → Modelo Implementación
            •Prueba → Modelo Pruebas
         Posee características:

            •Es jerárquico. Contiene relaciones
            •Son estereotipos de colaboraciones.
            •Es un esquema de la implementación.
                                                             17


Relaciones: asociaciones, generalizaciones y dependencias.


                                                                  17


---

       PDU


                 18


Captura de CU.


                      18


---

PDU


      19


           19


---

PDU


      20


           20


---

         PDU
         Proceso iterativo e incremental.

         Cada fase tiene sus iteraciones.
           Desarrollar pequeños pasos.
           Planeamiento.
           Especificar, diseño, implementación.
           Integrar, probar, ejecutar c/iteración. C/ iteración no es una
           identidad, está fuertemente influenciada por el Proyecto.

                Que no es iteración.
                  Desarrollo aleatorio.
                  No solo afecta desarrolladores.
                  No es rediseñar infinitamente.
                  No es impredecible.

                                                                     21


Las iteraciones en las primeras fases tratan en su mayor parte con la
determinación del ámbito del proyecto, la eliminación de los riesgos críticos,
y la creación de la línea base de la arquitectura


                                                                                 21


---

        PDU
        Porque iterativo e incremental

            Manejar riesgos críticos
            Identificar la arquitectura que guía el desarrollo.
            Proporciona un marco de trabajo, gestión de cambios
            de Requisitos
            Poder construir un Sistema a lo largo del tiempo.

            Proporcionar un proceso
               Gestión de Requisitos cambiantes
               Permitir cambio táctico
               Conseguir iteración continua
               Conseguir aprendizaje temprano


                                                                  22


Una iteración es un mini proyecto, un recorrido más o menos completo a lo
largo de todos los flujos de trabajo fundamentales, que obtiene como
resultado una versión interna del sistema.


                                                                            22


---

PDU
La aproximación iterativa está dirigida por los riesgos.

Riesgo variable que pone en peligro al proyecto.

Experimentar sucesos no deseables como retraso fecha, costo
o cancelación.

Las iteraciones alivian riesgos técnicos.

   Riesgos relacionados con las nuevas tecnologías.
   Riesgos relacionados con la arquitectura.
   Riesgos relacionados con construir el sistema adecuado.
   Riesgos relacionados con el rendimiento.

La dirección es responsable de los riesgos no técnicos.
                                                           23


                                                                23


---

PDU
El resultado de la iteración es un incremento.
Las iteraciones sobre el ciclo de vida

      • Inicio: Objetivo del ciclo de vida.
      • Elaboración: Arquitectura del ciclo de vida.
      • Construcción: Funcionalidad operativa inicial.
      • Transición: versión del producto

   Los modelos evolucionan con las iteraciones.

   Las iteraciones desafían a la organización.


                                                         24


                                                              24


---

       PDU


                 25


Captura de CU.


                      25


---

PDU


      26


           26


---

        PDU
         Entender el Modelo de Dominio

            Objetos del negocio que representan cosas que manipulan
            como cuentas pedidos, contratos.
            Objeto del mundo real.
            Sucesos que han ocurrido u ocurrirán.
         Desarrollo de un modelo de Dominio.
         Comprensión del contexto del sistema mediante un modelo
         Negocio
         Como desarrollar un modelo de Negocio
           Confeccionar modelo CU del Negocio
           Desarrollar un modelo de Objetos del negocio compuestos
           por trabajadores, entidades y unidades de trabajo

                                                                   27


Modelo del Dominio
Un modelo del dominio captura los tipos más importantes de objetos en el
contexto del sistema. Los objetos del dominio representan las “cosas” que
existen o los eventos que suceden en el entorno en el que trabaja el sistema.
Las clases del dominio aparecen entres formas típicas: - Objetos del negocio
que representan cosas que se manipulan en el negocio, como pedidos,
cuentas, contratos, etc.
- Objetos del mundo real y conceptos de los que el sistema debe hacer
seguimiento como aviación enemiga, misiles, trayectorias, etc.
- Sucesos que ocurrirán o han ocurrido, como llegada de un avión, su
salida, hora de la comida, etc.
El modelo de dominio se representa fundamentalmente por diagramas
de clases en UML.
El objetivo del modelado del dominio es comprender y describir las
clases más importantes dentro del contexto del sistema.


Modelo del Negocio
El modelado del negocio es una técnica para comprender los procesos de
negocio de la organización.


                                                                                27


---

El modelado del negocio está soportado por dos tipos de modelos de UML:
el modelado de casos de uso, y modelos de objetos.
Un Modelo de Casos de Uso del Negocio describe los proceso de negocio
de una empresa en términos de casos de uso del negocio y actores del
negocio que se corresponden con los procesos del negocio y los clientes
respectivamente.
Al igual que el modelo de casos de uso para un sistema software, el
modelo de casos de uso del negocio presenta un sistema (en este caso, el
negocio) desde la perspectiva de su uso, y esquematiza como proporciona
valor a sus usuarios.
El modelo de casos de uso del negocio se describe mediante diagramas de
casos de uso.
Un modelo de objetos del negocio describe como cada caso de uso del
negocio es llevado a cabo por parte de un conjunto de trabajadores
que utilizan un conjunto de entidades del negocio y de unidades de trabajo.
Cada realización de un caso de uso del negocio puede mostrarse en
diagramas de interacción y diagramas de actividad.
Una entidad del negocio representa algo que los trabajadores toman,
manipulan, inspeccionan, producen o utilizan en un negocio.
Una unidad de trabajo es un conjunto de esas entidades que conforma
un todo reconocible para el usuario final.


                                                                              27


---

PDU


      28


           28


---

PDU


      29


           29


---

FIN

      30


           30


---
