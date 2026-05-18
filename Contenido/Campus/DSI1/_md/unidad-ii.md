# DSI1 Unidad II - Modelado del contexto e ingenieria de sistemas

Fuente PDF: `DSI1/Unidad_II.pdf`.

Markdown operativo: `DSI1/_md/unidad-ii.md`.

Paginas PDF: 24. Palabras extraidas: 1877.

Nota: extraccion automatica con `pdftotext -layout` para busqueda y recuperacion por agentes. Para tablas, figuras o formato exacto, consultar el PDF fuente.

---

                                      19/3/2021


    DISEÑO DE SISTEMAS
        INFORMÁTICOS I
               Cnl Gabriel López
                  glopez@iue.edu.ar


1


                                             1


---

                        19/3/2021


            Unidad II

    Modelado del
     Contexto


2


                               2


---

                                                   19/3/2021


        Modelado del Contexto
    El enfoque sistémico y la ingeniería de sistemas.
    Ingeniería de Sistemas Enfoque de Proceso

    •    Diseño Conceptual.
    •    Diseño Preliminar.
    •    Diseño de Detalle y Desarrollo.
    •    Producción, Construcción.
    •    Operación y Soporte.
    •    Retiro y Desecho.


3


                                                          3


---

                                                19/3/2021


    Modelado del Contexto
    Diseño Conceptual:

     • Identificación de la necesidad,
     • Formulación de requerimientos,
     • Análisis de requerimientos,
     • Concepto de mantenimiento y soporte,
     • Evaluación de tecnologías disponibles,
     • Selección de enfoque técnico,
     • Definición funcional del sistema.


4


                                                       4


---

                                                19/3/2021


    Modelado del Contexto
    Diseño Preliminar:

     • Análisis funcional.
     • Asignación de requerimientos.
     • Estudios de compromisos (trade offs)
     • Síntesis, diseño preliminar.
     • Pruebas y evaluación del diseño conceptual
       (prototipos iniciales)
     • Plan de adquisición.
     • Contratos.
     • Programa de implementación.
     • Proveedores mayores y actividades de
       proveedores.

5


                                                       5


---

                                                     19/3/2021


    Modelado del Contexto
    Diseño de detalle y desarrollo:

     • Diseño de subsistema y componentes.
     • Estudio de compromisos y evaluación de
       alternativas.
     • Desarrollo de ingeniería (especificaciones
       técnicas) y prototipos.
     • Verificación de procesos de manufactura y
       producción.
     • Pruebas y evaluación del desarrollo.
     • Planificación de la producción y actividades de
       proveedores.


6


                                                            6


---

                                                19/3/2021


    Modelado del Contexto
    Producción / Construcción:

     • Producción y/o construcción de componentes
       del sistema.
     • Actividades de producción de proveedores.
     • Integración y pruebas de aceptación.
     • Distribución y operación del sistema.
     • Pruebas y evaluación del desarrollo.


7


                                                       7


---

                                                       19/3/2021


    Modelado del Contexto
    Uso operacional y Soporte del Sistema:

     • Operación del sistema en el ambiente del
       usuario.
     • Apoyo logístico y mantenimiento.
     • Pruebas operacionales.
     • Modificaciones para mejoramiento del sistema
     • Apoyo a contratistas.
     • Valoración del sistema (recolección y análisis de
       datos).


8


                                                              8


---

                                                      19/3/2021


    Modelado del Contexto
    Retiro y Desecho:

     • Retiro parcial o total del Sistema del servicio.
       Corresponde ejecutar lo planificado para las
       distintas alternativas consideradas.

        (Deshuase,       transformación,   enajenación,
        desecho controlado, reutilización con otro rol,
        fines históricos en museos, otras)


9


                                                             9


---

                                                    19/3/2021


     Modelado del Contexto
     Modelos de Desarrollo de Sistemas

     Existen diferentes Modelos para el desarrollo de
     Sistemas, que en general abarcan las siguientes
     actividades generales:

      • Aclaración del Problema (el Porqué)
      • Definición del sistema (el Qué)
      • Construcción del sistema (el Cómo)
      • Verificación y Validación del Sistema


10


                                                          10


---

                                                                         19/3/2021


      Modelado del Contexto
                            Lineal o Cascada
     Hacer adaptaciones o mejoras
     Necesita de requerimientos bien definidos y estables.
     Comunicación / Planeacion / Modelado / Construcción / Despliegue /
     Mantenimiento.
     Problemas:
     1. Proyectos reales raras veces siguen el modelo secuencial que
        propone el modelo. Modelo lineal puede acoplar interacción,
        indirectamente, los cambios pueden causar confusión Eq
        Trabajo.
     2. Dificil que el cliente exponga explícitamente todos los requisitos.
        Este modelo lo requiere y tiene dificultades de acomodar la
        incertidumbre natural al comienzo de muchos proyectos.
     3. El Cliente debe tener paciencia. La versión no estará disponible
        hasta que el proyecto esté muy avanzado. Un error puede ser
        desastroso si no se detecta hasta que se revisa el programa.
     Estado de bloqueo (un proceso debe terminar para que comience el
        otro).
11


                                                                               11


---

                                                                      19/3/2021


      Modelado del Contexto
           Modelos de procesos Incrementales.
     Incremental.
     Combina elementos del modelo cascada en forma interactiva.
     Aplica secuencias lineales de forma escalonada mientras progresa
     el tiempo en el calendario.
     Cada secuencia lineal produce un «incremento» del Sw Ej, SW
     tratamiento de textos
     1er incremento producto esencial (Req básicos, suplementarios
     no) El cliente evalúa luego nuevo incremento. Afronta modificación
     del producto central para cumplir mejor necesidades del cliente,
     entrega de funciones y características adicionales.
     Proceso se repite siguiendo la entrega de cada incremento.
     Diferencia construcción prototipos, modelo incremental se centra
     en la entrega de un producto operacional con cada incremento.
     Particularmente es útil cuando la dotación del personal necesario
     no este disponible para una implementación completa en la fecha
     límite.
12


                                                                            12


---

                                                                      19/3/2021


      Modelado del Contexto
             Modelos de procesos Incrementales.
     DRA.
     Es incremental y enfatiza el ciclo de desarrollo extremadamente
     corto.
     Adaptación «alta velocidad» modelo cascada logra desarrollo
     rápido utilizando construcción basada en componentes.
     Comprender bien requisitos y limitar el ámbito del proyecto,
     permite al equipo de desarrollo crear «sistema completamente
     funcional» dentro de períodos cortos de tiempo.
     • Comunicación: comprender el problema negocios y características
        de la Información que se debe incluir.
     • Planeación: coordinar varios equipos en paralelo diferentes para
        distintas funciones.
     • Modelado incluye 3 grandes fases: Modelado Negocios, Modelado
        de datos, Modelado del proceso.
     • Construcción empleo de componentes y generación automática de
        código
     • Despliegue base para iteraciones sucesivas.
13


                                                                            13


---

                                                                      19/3/2021


      Modelado del Contexto
     Problemas
     1. Para proyectos grandes pero escalables, requiere recursos
        humanos suficientes como para crear el número correcto de
        equipos DRA.
     2. Requiere clientes y desarrolladores comprometidos en
        actividades rápidas necesarias para completar el sistema con
        tiempos abreviado. Sin compromiso de ninguna de las partes
        constituyentes, fracasarán
     3. Si un sistema no se puede modularizar adecuadamente, la
        construcción de los componentes necesarios será problemático
     4. Alto rendimiento, se va a conseguir el rendimiento convirtiendo
        interfaces en componentes de sistemas, el enfoque DRA
        puede que no funcione.
     5. No es adecuado cuando los riesgos técnicos son altos.


14


                                                                            14


---

                                                                         19/3/2021


      Modelado del Contexto
              Modelos de procesos Evolutivos
     Prototipado.
     Este Paradigma ofrece el mejor enfoque cuando:
     • El cliente, define un conjunto de objetivos generales para el sw, pero
       no identifica los requisitos detallados de entrada, proceso o salida.
     • Responsable del desarrollo SW puede no estar seguro de la eficacia
       de un algoritmo, capacidad de adaptación de un SO, forma que
       debería tomarse la interacción hombre-máquina.
     • Comunicación: Identifican requisitos conocidos y áreas del esquema
       donde es obligatoria más definición.
     • La iteración: Construcción de un prototipo. Se representa el modelado
       en forma de un diseño rápido.
     • Diseño rápido aquellos aspectos que serán visibles para el cliente.
     • El Prototipo es evaluado por el cliente / usuario y se utiliza para
       refinar los requisitos de SW desarrollar.
     • Iteración el prototipo se pone a punto para satisfacer las necesidades
       del, permitiendo al mismo tiempo que el desarrollador comprenda
       mejor lo que se necesita hacer.
15


                                                                                15


---

                                                                        19/3/2021


      Modelado del Contexto
     Problemática
     1. El Cliente ve una versión de funcionamiento SW, sin tener
        conocimiento que el prototipo es prueba, hay funciones que no se
        han tenido en cuenta, la calidad del software global o la facilidad
        de mantenimiento a largo plazo. Cuando se informa de que el
        producto se debe construir otra vez para que se puedan
        mantener los niveles altos de calidad, el cliente no lo entiende y
        pide que se apliquen pequeños ajustes para que se pueda hacer
        del prototipo un producto final.
     2. El desarrollador, toma compromisos de implementación para
        hacer que prototipo funcione rápidamente. Utilizar SO o lenguaje
        de programación inadecuados porque esta disponible o es
        conocido. La construcción de prototipos puede ser un paradigma
        efectivo para la Ing SW. Clave definir reglas del juego al
        comienzo; cliente y desarrollador deben poner de acuerdo en que
        el prototipo se construya para servir como un mecanismo de
        definición de requisitos. Y después desarrollar con enfoque de
        calidad.
16


                                                                              16


---

                                                                     19/3/2021


      Modelado del Contexto
     Espiral
     Conjuga naturaleza iterativa construcción de prototipos con
     aspectos controlados y sistemáticos del modelo lineal secuencial.

     Proporciona potencial para el desarrollo rápido de versiones
     incrementales de SW.,

     Durante las primeras iteraciones, la versión incremental es un
     modelo papel o un prototipo.

     Durante las últimas iteraciones se producen versiones cada vez
     más completas del sistema desarrollado.

     Apto para :
     Proy Mant Prod / Proy mejora Prod / Proy Des nuevos productos. /
     Proy Des de conceptos.

17


                                                                           17


---

                                                                  19/3/2021


      Modelado del Contexto
     Se divide en un número de actividades de marco de trabajo,
     llamadas regiones de tareas6.E existen entre 3 y 6 regiones de
     tareas.
     • Comunicación con el cliente tareas requeridas para establecer
        comunicación entre el desarrollador y el cliente.
     • Planeación- estimación – itinerario – análisis de riesgos.
     • Modelado- análisis y diseño.
     • Construcción – código y prueba
     • Despliegue - entrega retroalimentación.


18


                                                                        18


---

                                                                      19/3/2021


      Modelado del Contexto
     Cada una de las regiones está compuestas por 1 conjunto tareas
     del trabajo, se adaptan a las características del proyecto a
     emprenderse
     Importante Gestión del riesgo, Puntos de fijación: combinación de
     productos de trabajo y condiciones del espiral consideradas para
     cada paso evolutivo.
     Primer paso especificación del producto
     Posterior se construye un prototipo luego mas elaborado, ajustes
     del plan de proyecto.
     Se puede iniciar como proyecto de desarrollo de concepto, luego
     proyecto de mejoramiento de producto
     Mantiene el enfoque sistemático de los pasos sugeridos por el ciclo
     de vida clásico, pero incorpora al marco de trabajo iterativo que
     refleja de forma mas realista el mundo real.
     Difícil de convencer al cliente de que el enfoque evolutivo es
     controlable.


19


                                                                            19


---

                                                                   19/3/2021


      Modelado del Contexto
     Modelo de desarrollo concurrente
     llamado también ingeniería concurrente.
     Se puede representar en forma de esquema como una serie de
     actividades del marco de trabajo, acciones y tareas Ing SW y
     estados asociados.

     Todas las actividades existen concurrentemente, pero residen en
     estados diferentes.

     El modelo de proceso concurrente define una serie de
     acontecimientos que dispararán transiciones de estado a estado
     para cada una de las actividades, acciones o tareas de las
     actividades de la ingeniería del software


20


                                                                         20


---

                                                                        19/3/2021


      Modelado del Contexto
     Por ejemplo, al principio del proyecto la actividad de comunicación
     con el cliente ha finalizado su primera iteración y la actividad de
     cambios está en estado de espera.

     La actividad de análisis (que estaba en el estado sin inicio,
     mientras que se iniciaba la comunicación inicial con el cliente)
     ahora hace una transición al estado de desarrollo.

     Sin embargo, si el cliente indica que se deben hacer cambios en
     requisitos, la actividad análisis cambia del estado de desarrollo al
     estado espera de cambios.


21


                                                                              21


---

                                                                          19/3/2021


      Modelado del Contexto
     Modelos especializados de procesos
     Desarrollo basado en componentes
     Incorpora mucho del espiral, es evolutivo por naturaleza y exige u
     enfoque interactivo para la creación del SW,
     Técnica de Objetos, Clases, encapsulación, son reutilizables por
     distintas aplicaciones y arquitectura SIBC
     Centrado: 1er paso identificación de los componentes candidatos
     Como módulos, como clases o paquetes.
     • Productos basados en componentes disponibles se investigan
        y evalúan para el dominio de aplicación en cuestión.
     • Considerar aspectos de integración de componentes
     • Diseñar Arquitectura de Sw para adaptar componentes.
     • Los componentes se integran a las arquitecturas.
     • Se realizan pruebas detalladas para asegurar funcionalidad
        apropiada.

22


                                                                                22


---

                                                                                                           19/3/2021


                                                         Desarrollo
       Modelo           Modelo          Modelo DRA
                                                         basado en         Prototipo      Modelo Espiral
       Factor         Incremental
                                                        componentes
                    Necesita          Comprender bien Identificar las   Sirve para       Necesita
                    Requisitos        los requisitos    clases          identificar      Requisitos
      Requisitos    básicos para el   limitar el ámbito candidatas      No identifica    básicos para el
                    inicio            del proyecto                      requisitos E/S/P inicio

                    No se pueden      Riesgos técnicos Mal ensamblaje Creer que es un construcción de
       Riesgos      cumplir con       altos            de los         producto final  prototipos para
                    fecha limite                       componentes                    evitarlos
                    Entrega partes    Crear             Reutilización   Mejor descartar   Construcción de
     Construcción   pequeñas pero     componentes       del SW          el prototipo      prototipos en
      basada en     reutilizables     reutilizables                                       cualquier etapa
     componentes

                    Entrega un      Tiempo         Empleo de            Incrementos        Incrementos a
                    producto                       UML                                    lo largo de la
     Centrado en
                    operacional en                                                        vida
                    cada incremento
                    Indistinto      Extremadamente Indistinto           Relativamente     Indistinto
       Ciclo de                     cortos                              cotos             proyectos
      desarrollo                                                                          menores o
                                                                                          mayores


23


                                                                                                                 23


---

           19/3/2021


     FIN
24


                 24


---
