# UN MODELO DE ESTIMACION DE PROYECTOS DE SOFTWARE

> Fuente PDF: `Lecturas y Herramientas/UN_MODELO_DE_ESTIMACION_DE_PROYECTOS_DE_SOFTWARE.pdf`
>
> Markdown operativo generado para busqueda y lectura agentica.
> Metodo: `pdftotext -layout`.
> Paginas: 49.
> Palabras extraidas por `pdftotext`: 13842.
> Palabras finales en este Markdown: 13842.
> Nota de calidad: Texto extraible util para busqueda; revisar el PDF fuente para tablas, figuras o maquetacion.

---

- COCOMO -


          UN MODELO DE ESTIMACION DE PROYECTOS DE SOFTWARE




                                 Adriana Gómez, María del C.López,
                                   Silvina Migani, Alejandra Otazú



                                            RESUMEN


       Como se conoce, una de las tareas de mayor importancia en la planificación de proyectos de
software es la estimación, la cual consiste en determinar, con cierto grado de certeza, los recursos
de hardware y software, costo, tiempo y esfuerzo necesarios para el desarrollo de los mismos.
       Este trabajo describe un modelo de estimación, propuesto por Barry Boehm, llamado
COCOMO II. Este modelo permite realizar estimaciones en función del tamaño del software, y de
un conjunto de factores de costo y de escala. Los factores de costo describen aspectos relacionados
con la naturaleza del producto, hardware utilizado, personal involucrado, y características propias
del proyecto. El conjunto de factores de escala explica las economías y deseconomías de escala
producidas a medida que un proyecto de software incrementa su tamaño.
       COCOMO II posee tres modelos denominados Composición de Aplicación, Diseño
Temprano y Post-Arquitectura. Cada uno de ellos orientados a sectores específicos del mercado de
desarrollo de software y a las distintas etapas del desarrollo de software.
1      Introducción ................................................................................................................................4
2      Breve Historia..............................................................................................................................5
3      COCOMO 81 ...............................................................................................................................6
    3.1 Modos de Desarrollo........................................................................................................................... 7
    3.2 Modelo Básico ..................................................................................................................................... 9
    3.3 Modelo Intermedio ........................................................................................................................... 12
    3.4 Modelo Detallado .............................................................................................................................. 14
       3.4.1       Procedimiento de estimación de esfuerzo .................................................................................................14
       3.4.2       Procedimiento de estimación del cronograma...........................................................................................25
4      COCOMO II ..............................................................................................................................26
    4.1 Definición del modelo ....................................................................................................................... 26
    4.2 Estimación del Esfuerzo ................................................................................................................... 28
       4.2.1       Modelo Composición de Aplicación .........................................................................................................28
       4.2.2       Modelo Diseño Temprano.........................................................................................................................28
       4.2.3       Modelo Post-Arquitectura .........................................................................................................................30
    4.3 Estimación del Cronograma ............................................................................................................ 30
    4.4 Métricas de Software ........................................................................................................................ 31
       4.4.1       Puntos Objeto ............................................................................................................................................31
       4.4.2       Puntos Función..........................................................................................................................................32
       4.4.3       Líneas de Código Fuente...........................................................................................................................35
       4.4.4       Conversión de Puntos Función a Líneas de Código Fuente (SLOC).........................................................36
       4.4.5       Desperdicio de Código (Breakage). ..........................................................................................................37
       4.4.6       Modelo de Reuso.......................................................................................................................................37
       4.4.7       Reingeniería y Conversión ........................................................................................................................40
    4.5 Factor Exponencial de Escala.......................................................................................................... 42
       4.5.1       Precedencia y Flexibilidad en el Desarrollo (PREC Y FLEX ).................................................................43
       4.5.2       Arquitectura y Determinación del Riesgo (RESL)....................................................................................44
       4.5.3       Cohesión del Equipo (TEAM) .................................................................................................................45
       4.5.4       Madurez del Proceso (PMAT) ..................................................................................................................45
    4.6 Factores Multiplicadores de Esfuerzo ( Effort Multipliers EM ). ................................................ 46
       4.6.1       Factores del producto ................................................................................................................................48
       4.6.2       Factores de la plataforma ..........................................................................................................................50
       4.6.3       Factores del personal.................................................................................................................................51
       4.6.4       Factores del proyecto ...............................................................................................................................52
    4.7 Consideraciones destacables del modelo......................................................................................... 53
5      Un Ejemplo Práctico .................................................................................................................54


                                                                                                                                                                             2
6   Conclusiones..............................................................................................................................59
7   Anexo I.......................................................................................................................................60
8   Acrónimos y Abreviaturas.........................................................................................................63
9   Referencias ................................................................................................................................66




                                                                                                                                                  3
1 Introducción
      Una de las tareas de mayor importancia en la administración de proyectos de software es la
estimación de costos. Si bien es una de las primeras actividades, inmediatamente posterior al
establecimiento de los requerimientos, se ejecuta regularmente a medida que el proyecto progresa
con el fin de ajustar la precisión en la estimación.
      La estimación de costos de software tiene dos usos en la administración de proyectos:
      !   Durante la etapa de planeamiento: Permite decidir cuantas personas son necesarias para
          llevar a cabo el proyecto y establecer el cronograma adecuado.
      !   Para controlar el progreso del proyecto: Es esencial evaluar si el proyecto está
          evolucionando de acuerdo al cronograma y tomar las acciones correctivas si fuera
          necesario. Para esto se requiere contar con métricas que permitan medir el nivel de
          cumplimiento del desarrollo del software.
      En el ámbito de la ingeniería de software, la estimación de costos radica básicamente en
estimar la cantidad de personas necesarias para desarrollar el producto. A diferencia de otras
disciplinas de la ingeniería, en las cuales, el costo de los materiales es el principal componente a ser
estimado.
      La estimación de costos de software posibilita relacionar conceptos generales y técnicas del
análisis económico en el mundo particular de la ingeniería de software. Aunque no es una ciencia
exacta no podemos prescindir de ella puesto que hoy en día un error en las predicciones puede
conducir a resultados adversos.
      Es importante reconocer la fuerte relación entre costo, cronograma y calidad. Estos tres
aspectos están íntimamente relacionados y confrontados entre sí. De esta manera, se hace difícil
incrementar la calidad sin aumentar el costo y/o el cronograma del software a desarrollar.
Similarmente, el cronograma de desarrollo no puede reducirse dramáticamente sin deteriorar la
calidad del producto de software y/o incrementar el costo de desarrollo. Los modelos de estimación
juegan un papel importante ya que permiten equilibrar estos tres factores.
      Se han propuesto numerosos métodos de estimación. Entre ellos se pueden contar:
      !   Juicio de Expertos: Este método implica la consulta a expertos, quienes usan su
          experiencia y conocimiento del proyecto propuesto para lograr una estimación de sus
          costos.
      !   Analogía: Este método implica una estimación por analogía con proyectos similares, que
          ya han finalizado, de manera de relacionar los costos reales con la estimación del costo
          del nuevo proyecto. La principal virtud de la estimación por analogía es que está basada
          en la experiencia real de un proyecto. Esta experiencia puede ser estudiada para
          determinar las diferencias específicas con un proyecto nuevo y el impacto de los cambios
          en los costos. Por otra parte, la principal desventaja es que no está claro hasta que punto es
          realmente representativo el proyecto previo, en lo que se refiere a restricciones, técnicas,
          personal y funcionalidad requerida.
      !   Parkinson: Este método intenta adaptar la estimación del costo a los recursos disponibles.
          En general, es extremadamente inadecuado.
      !   Tasar para ganar: Estima los costos en función del presupuesto adecuado para ganar el
          trabajo, o el cronograma necesario para estar primero en el mercado con el nuevo
          producto.



                                                                                                      4
     !   Estimación top-down: A partir de las propiedades globales del producto de software se
         deriva el costo de todo el proyecto. Después, el costo total es dividido entre las diversas
         componentes.
     !   Estimación bottom-up: El costo de cada componente de software es estimado por
         separado, generalmente por la persona responsable del desarrollo de la misma, y luego
         sumados para obtener el costo total del proyecto. Las técnicas de estimación bottom-up y
         top-down pueden ser usadas en conjunción con cualquiera de los métodos discutidos en
         esta sección.
     !   Modelos Algorítmicos: Estos métodos proveen uno o más algoritmos que estiman el costo
         del software en función de un número de variables que se consideran los principales
         factores de costo. Los valores de los factores se establecen a partir del análisis de
         regresión de datos confiables recopilados en proyectos anteriores. Comparados con otros
         métodos una de sus ventajas es la objetividad, ya que están calibrados a partir de
         experiencias anteriores. Esto mismo constituye la principal desventaja, por no poder
         asegurar que estas experiencias sean realmente representativas de proyectos futuros, en
         especial si se desarrollan en nuevas áreas de aplicación, con nuevas técnicas y
         arquitecturas. Como sucede en cualquier modelo de estimación, no hay forma de
         compensar la falta o calidad de los datos de entrada y/o precisión de los valores de los
         factores de costo. El modelo COCOMO es un ejemplo de modelo algorítmico.


2 Breve Historia
      El modelo COCOMO ha evolucionado debido a los constantes avances en el mercado de
desarrollo de software.
      En el año 1981 Barry Boehm publica el modelo COCOMO, acorde a las prácticas de
desarrollo de software de aquel momento [Boehm 1981]. Durante la década de los 80, el modelo se
continuó perfeccionando y consolidando, siendo el modelo de estimación de costos más
ampliamente utilizado en el mundo.
     Al aparecer las computadoras personales y generalizarse su uso, surgieron algunas
implementaciones. Varias empresas comenzaron a comercializar herramientas de estimación
computarizadas.
       En el año 1983 se introduce el lenguaje de programación Ada (American National Standard
Institute) para reducir los costos de desarrollo de grandes sistemas. Algunos aspectos de Ada
provocaron un gran impacto en los costos de desarrollo y mantenimiento, así Barry Boehm y
Walker Royce definieron un modelo revisado, llamado Ada COCOMO [Boehm 1989].
      En los 90, las técnicas de desarrollo de software cambiaron dramáticamente, surgieron la
necesidad de reusar software existente, la construcción de sistemas usando librerías, etc. Estos
cambios comenzaron a generar problemas en la aplicación del modelo COCOMO. La solución fue
reinventar el modelo. Después de algunos años y de un esfuerzo combinado de USC-CSE (
University of Southern California- Center For Software Engineering), IRUS at UC Irvine y
organizaciones privadas, aparece COCOMO II. Las incorporaciones a este modelo lo reforzaron e
hicieron apto para ser aplicado en proyectos vinculados a tecnologías como orientación a objetos,
desarrollo incremental, composición de aplicación, y reingeniería. COCOMO II consta de tres
modelos, cada uno de los cuales ofrece una precisión acorde a cada etapa de desarrollo del
proyecto. Enunciados en orden creciente de fidelidad son, modelo de Composición de Aplicación,
Diseño Temprano y Post Arquitectura.



                                                                                                  5
     El USC- CSE implementó los dos últimos modelos en una herramienta de software. Esta
herramienta le permite al planificador hacer rápidamente una exploración de las posibilidades de un
proyecto, analizando qué efectos provoca el ajuste de requerimientos, recursos y staff sobre la
estimación de costos y tiempos.
      Para evitar confusión el modelo COCOMO original fue redesignado con el nombre
COCOMO’ 81. Así todas las referencias de COCOMO encontradas en la literatura antes de 1995 se
refieren a lo que ahora llamamos COCOMO’81. La mayoría de las referencias publicadas a partir
de 1995 se refieren a COCOMO II.
      Existe una nomenclatura para distinguir el modelo teórico, de la implementación, esto es, se
denomina COCOMO II al modelo y USC COCOMOII a la herramienta de software. La designación
del primer release de la implementación fue USC COCOMO II.1997.0. El componente del año
calendario identifica la calibración. Dentro de cualquier año calendario sólo una versión oficial es
liberada por USC. Sin embargo, en un mismo año pueden existir más de un release del software, así
por ejemplo USC COCOMO II.1997.0 y USC COCOMO II.1997.1 tienen los mismos valores de
parámetros sólo los diferencia mejoras incorporadas en la interfase.


3 COCOMO 81
      COCOMO’ 81 está compuesto por tres modelos que corresponden a distintos niveles de
detalle y precisión. Mencionados en orden creciente son: Modelo Básico, Intermedio y Detallado.
La estimación es más precisa a medida que se toman en cuenta mayor cantidad de factores que
influyen en el desarrollo de un producto de software.
      COCOMO’81 permite estimar cómo se distribuye el esfuerzo y el tiempo en las distintas fases
del desarrollo de un proyecto y dentro de cada fase, en las actividades principales. Las fases
consideradas por COCOMO’81 son:
       !   Diseño del Producto       (PD)
               Se define la arquitectura del hardware, software y las estructuras de datos y control.
           También se desarrolla un bosquejo del manual del usuario y los planes de aceptación y
           testeo.
       !   Diseño Detallado          (DD)
       !   Codificación y Testeo de Unidades        (CT)
              En estas dos fases el diseño global de la fase anterior es implementado, creando las
           componentes de software, que son testeadas y evaluadas individualmente.
       !   Integración y Testeo                     (IT)
              Se fusionan todas las componentes de software desarrolladas con el fin de lograr que
           el producto de software funcione correctamente. Los requerimientos definidos son
           usados para controlar las aptitudes del producto liberado.
       Los costos y tiempos de las fases excluídas (Requerimientos y Mantenimiento) deben ser
estimados en forma separada empleando otros modelos.
       Se distinguen las siguientes actividades principales:
       !   Análisis de Requerimientos
               Determinación, especificación, revisión y actualización de la funcionalidad,
           performance e interfase del software


                                                                                                   6
4 COCOMO II

4.1       Definición del modelo
      Los objetivos principales que se tuvieron en cuenta para construir el modelo COCOMO II
fueron:
           !   Desarrollar un modelo de estimación de costo y cronograma de proyectos de software
               que se adaptara tanto a las prácticas de desarrollo de la década del 90 como a las futuras.
           !   Construir una base de datos de proyectos de software que permitiera la calibración
               continua del modelo, y así incrementar la precisión en la estimación.
           !   Implementar una herramienta de software que soportara el modelo.
           !   Proveer un marco analítico cuantitativo y un conjunto de herramientas y técnicas que
               evaluaran el impacto de las mejoras tecnológicas de software sobre los costos y tiempos
               en las diferentes etapas del ciclo de vida de desarrollo.
     COCOMO II está compuesto por tres modelos denominados: Composición de Aplicación,
Diseño Temprano y Post-Arquitectura.
     Éstos surgen en respuesta a la diversidad del mercado actual y futuro de desarrollo de
software. Esta diversidad podría representarse con el siguiente esquema (Figura 3).


                                  Aplicaciones desarrolladas por usuarios finales


                            Generadores           Aplicaciones          Sistemas
                           de Aplicaciones     con Componentes         Integrados

                                                Infraestructura

                 Figura 3: Distribución del Mercado de Software Actual y Futuro. [Boehm 1995/1]

      !    Aplicaciones desarrolladas por Usuarios Finales:    En este sector se encuentran las
           aplicaciones de procesamiento de información generadas directamente por usuarios finales,
           mediante la utilización de generadores de aplicaciones tales como planillas de cálculo,
           sistemas de consultas, etc. Estas aplicaciones surgen debido al uso masivo de estas
           herramientas, conjuntamente con la presión actual para obtener soluciones rápidas y
           flexibles.
      !    Generadores de Aplicaciones: En este sector operan firmas como Lotus, Microsoft, Novell,
           Borland con el objetivo de crear módulos pre-empaquetados que serán usados por usuarios
           finales y programadores.
      !    Aplicaciones con Componentes: Sector en el que se encuentran aquellas aplicaciones que
           son específicas para ser resueltas por soluciones pre-empaquetadas, pero son lo
           suficientemente simples para ser construidas a partir de componentes interoperables.
           Componentes típicas son constructores de interfases gráficas, administradores de bases de
           datos, buscadores inteligentes de datos, componentes de dominio-específico (medicina,
           finanzas, procesos industriales, etc.). Estas aplicaciones son generadas por un equipo
           reducido de personas, en pocas semanas o meses.
      !    Sistemas Integrados: Sistemas de gran escala, con un alto grado de integración entre sus
           componentes, sin antecedentes en el mercado que se puedan tomar como base. Porciones de

                                                                                                       26
               estos sistemas pueden ser desarrolladas a través de la composición de aplicaciones. Entre las
               empresas que desarrollan software representativo de este sector, se encuentran grandes
               firmas que desarrollan software de telecomunicaciones, sistemas de información
               corporativos, sistemas de control de fabricación, etc.
       !       Infraestructura: Área que comprende el desarrollo de sistemas operativos, protocolos de
               redes, sistemas administradores de bases de datos, etc. Incrementalmente este sector
               direccionará sus soluciones, hacia problemas genéricos de procesamiento distribuido y
               procesamiento de transacciones, a soluciones middleware. Firmas representativas son
               Microsoft, Oracle, SyBase, Novell y NeXT.
      Los tres modelos de COCOMO II se adaptan tanto a las necesidades de los diferentes
sectores descriptos, como al tipo y cantidad de información disponible en cada etapa del ciclo de
vida de desarrollo, lo que se conoce por granularidad de la información.
       Se puede afirmar que para las aplicaciones desarrolladas por usuarios finales no se justifica la
utilización de un modelo de estimación de costos. Estas aplicaciones normalmente se construyen en
poco tiempo, por lo tanto requieren solamente una estimación basada en actividades.
      El modelo Composición de Aplicación, es el modelo de estimación utilizado en los proyectos
de software que se construyen a partir de componentes pre-empaquetadas. En este caso, se emplean
Puntos Objeto5 para estimar el tamaño del software, lo cual está acorde al nivel de información que
generalmente se tiene en la etapa de planificación, y el nivel de precisión requerido en la estimación
de proyectos de esta naturaleza.
    Para los demás sectores del mercado se aplica un modelo mixto, combinación de los tres
modelos.
      El modelo Composición de Aplicación se emplea en desarrollos de software durante la etapa
de prototipación.
      El modelo Diseño Temprano se utiliza en las primeras etapas del desarrollo en las cuales se
evalúan las alternativas de hardware y software de un proyecto. En estas etapas se tiene poca
información, lo que concuerda con el uso de Puntos Función6, para estimar tamaño y el uso de un
número reducido de factores de costo.
      El modelo Post-Arquitectura se aplica en la etapa de desarrollo propiamente dicho, después
que se define la arquitectura del sistema, y en la etapa de mantenimiento. Este modelo utiliza:
           !     Puntos Función y/o Líneas de Código Fuente7 para estimar tamaño, con modificadores
                 que contemplan el reuso, con y sin traducción automática, y el "desperdicio" (breakage)8.
           !     Un conjunto de 17 atributos, denominados factores de costo9, que permiten considerar
                 características del proyecto referentes al personal, plataforma de desarrollo, etc., que
                 tienen injerencia en los costos.
           !     Cinco factores que determinan un exponente, que incorpora al modelo el concepto de
                 deseconomía y economía de escala10. Estos factores reemplazan los modos Orgánico,
                 Semiacoplado y Empotrado del modelo COCOMO '81.


5
    Técnica de estimación de tamaño de software, tratada en la sección 4.4.1,página 31.
6
    Técnica de estimación de tamaño de software, tratada en la sección 4.4.2, página 32.
7
    Técnica de estimación de tamaño de software, tratada en la sección 4.4.3, página 35.
8
    Concepto tratado en la sección 4.4.5, página 37.
9
    Conceptos tratados en la sección 4.6, página 46.

                                                                                                         27
4.2      Estimación del Esfuerzo
     El esfuerzo necesario para concretar un proyecto de desarrollo de software, cualquiera sea el
modelo empleado, se expresa en meses/persona (PM) y representa los meses de trabajo de una
persona fulltime, requeridos para desarrollar el proyecto.

4.2.1      Modelo Composición de Aplicación

         La fórmula propuesta en este modelo es la siguiente:


                           PM = NOP / PROD
         Donde:
                  NOP (Nuevos Puntos Objeto): Tamaño del nuevo software a desarrollar expresado en
                                             Puntos Objeto y se calcula de la siguiente manera:
                                     NOP = OP x (100 - %reuso)/100
                  OP      (Puntos Objeto): Tamaño del software a desarrollar expresado en Puntos Objeto
                  %reuso: Porcentaje de reuso que se espera lograr en el proyecto
                  PROD: Es la productividad promedio determinada a partir del análisis de datos de
                        proyectos en [Banker 1994], mostrada en Tabla 6.


             Experiencia y
            capacidad de los           Muy Bajo         Bajo    Normal          Alto        Muy Alto
            desarrolladores
         Madurez y Capacidad
                                       Muy Bajo         Bajo     Normal         Alto        Muy Alto
             del ICASE
                  PROD                      4            7         13            25               50
                Tabla 6: Productividad para el modelo Composición de Aplicación. [Boehm 1995/2]


4.2.2      Modelo Diseño Temprano

      Este modelo se usa en las etapas tempranas de un proyecto de software, cuando se conoce
muy poco del tamaño del producto a ser desarrollado, de la naturaleza de la plataforma, del
personal a ser incorporado al proyecto o detalles específicos del proceso a utilizar. Este modelo
podría emplearse tanto en productos desarrollados en sectores de Generadores de Aplicación,
Sistemas Integrados o Infraestructura.

     El modelo de Diseño Temprano ajusta el esfuerzo nominal usando siete factores de costo. La
fórmula para el cálculo del esfuerzo es la siguiente:



                                             7
          PM estimado = PM nominal × ∏ EM i
                                            i =1




10
     Conceptos tratados en la sección 4.5, página 42.

                                                                                                       28
PM nominal = A × ( KSLOC ) B
                        5
B = 1.01 + 0.01 × ∑ Wj
                     j =1

Donde:
 !   PMEstimado es el esfuerzo Nominal ajustado por 7 factores, que reflejan otros aspectos
     propios del proyecto que afectan al esfuerzo necesario para la ejecución del mismo.
 !   KSLOC es el tamaño del software a desarrollar expresado en miles de líneas de código
     fuente.
 !   A es una constante que captura los efectos lineales sobre el esfuerzo de acuerdo a la
     variación del tamaño, (A=2.94).
 !   B es el factor exponencial de escala, toma en cuenta las características relacionadas con
     las economías y deseconomías de escala producidas cuando un proyecto de software
     incrementa su tamaño. Ver sección 4.5, página 42.
 !   EMi corresponde a los factores de costo que tienen un efecto multiplicativo sobre el
     esfuerzo, llamados Multiplicadores de Esfuerzo (Effort Multipliers). Cada factor se
     puede clasificar en seis niveles diferentes que expresan el impacto del multiplicador
     sobre el esfuerzo de desarrollo. Esta escala varía desde un nivel Extra Bajo hasta un
     nivel Extra Alto. Cada nivel tiene un peso asociado. El peso promedio o nominal es 1.0.
     Si el factor provoca un efecto nocivo en el esfuerzo de un proyecto, el valor del
     multiplicador correspondiente será mayor que 1.0, caso contrario el multiplicador será
     inferior a 1.0. La Figura 4 muestra una pantalla del software COCOMO II.1999.0, donde
     se aprecian los valores de los factores de acuerdo a cada nivel, según la calibración
     efectuada para el año 1999.
     Clasificados en categorías, los 7 Multiplicadores de Esfuerzo son:
         Del Producto
              RCPX: Confiabilidad y Complejidad del producto
              RUSE: Reusabilidad Requerida
         De la Plataforma
              PDIF: Dificultad de la Plataforma
         Del Personal
              PERS: Aptitud del Personal
              PREX: Experiencia del Personal
         Del Proyecto
              FCIL: Facilidades
              SCED: Cronograma de Desarrollo Requerido




                                                                                           29
                                                                                                      11
                Figura 4: Multiplicadores de Esfuerzo del Modelo de Diseño Temprano. [COCOMO II.0]


4.2.3    Modelo Post-Arquitectura

     Es el modelo de estimación más detallado y se aplica cuando la arquitectura del proyecto está
completamente definida. Este modelo se aplica durante el desarrollo y mantenimiento de productos
de software incluidos en las áreas de Sistemas Integrados, Infraestructura y Generadores de
Aplicaciones.
      El esfuerzo nominal se ajusta usando 17 factores multiplicadores de esfuerzo. El mayor
número de multiplicadores permite analizar con más exactitud el conocimiento disponible en las
últimas etapas de desarrollo, ajustando el modelo de tal forma que refleje fielmente el producto de
software bajo desarrollo. La fórmula para el cálculo del esfuerzo es la siguiente:
                                      17
        PM estimado = PM nominal × ∏ EM i
                                      i =1

       Los 17 factores de costo correspondientes a este modelo se explicarán en detalle en la sección
4.6., página 46.

4.3     Estimación del Cronograma
       La versión inicial de COCOMO II provee un modelo de estimación del cronograma similar
al presentado en COCOMO' 81 y ADA COCOMO. La ecuación inicial para los tres modelos de
COCOMO II es:




11
  El Software COCOMO II.1999.0 permite el uso de dos factores del usuario (USR1, USR2) para poder contemplar
particularidades de cada proyecto.

                                                                                                           30
                     [
        TDEV = 3.0 × PM *( 0.33+ 0.2×(B −1.01)) × ] SCED
                                                      100
                                                          %



        Donde:
                 TDEV es el tiempo calendario en meses que transcurre desde la determinación de los
                       requerimientos a la culminación de una actividad que certifique que el
                       producto cumple con las especificaciones.
                 PM*     es el esfuerzo expresado en meses personas, calculado sin tener en cuenta el
                          multiplicador de esfuerzo SCED. Ver Tabla 21.
                 B       es el Factor de Escala
                 SCED% es el porcentaje de compresión/expansión del cronograma.
       Las futuras versiones de COCOMO II ofrecerán un modelo de estimación de cronograma
más completo que refleje los diferentes modelos de procesos que se puede usar en el desarrollo de
un proyecto, los efectos del reuso de software y la composición de aplicaciones.

4.4     Métricas de Software
       En la estimación del tamaño de software COCOMO II utiliza tres técnicas: Puntos Objeto,
Puntos Función No Ajustados y Líneas de Código Fuente. Además se emplean otros parámetros
relativos al tamaño que contemplan aspectos tales como: reuso, reingeniería, conversión, y
mantenimiento.
      Es necesario unificar criterios de medición de tamaño, tanto para poder planificar y controlar
proyectos, como para realizar estudios y análisis entre proyectos en pro de la mejora de procesos
[Park 1992].

4.4.1       Puntos Objeto

      A pesar de que la estimación a través de Puntos Objeto es un enfoque de medición de tamaño
de software relativamente nuevo, es apropiado para las aplicaciones con componentes y para
estimar esfuerzos en las etapas de prototipación. En estas circunstancias, se lo ha comparado con la
estimación de Puntos Función. Un experimento, diseñado por Kaufman y Kumar en 1993, involucró
a 4 administradores de proyecto experimentados usando Puntos Objeto y Puntos Función, para
estimar el esfuerzo requerido de dos proyectos terminados en 3.5 y 6 meses-persona
respectivamente. Como base, se emplearon las descripciones disponibles al comienzo de tales
proyectos. El experimento permitió determinar que:
        !    Los Puntos Objeto y los Puntos Función produjeron resultados igualmente precisos
             (ligeramente más exacto con Puntos Objetos, pero no estadísticamente significativo).
        !    El tiempo promedio para producir una estimación con Puntos Objeto fue alrededor del
             47% del tiempo promedio necesario para las estimaciones con Puntos Función. Además,
             los administradores consideraron que el método de Puntos Objeto era más fácil de usar.
      De esta manera, aunque estos resultados no están respaldados estadísticamente, parecen
suficientemente prometedores como para justificar el uso de Puntos Objeto como punto de partida
en el modelo de estimación de Composición de Aplicación de COCOMO II.
     A continuación se describe el procedimiento para determinar Puntos Objeto en un proyecto de
software:


                                                                                                  31
Primero: Determinar Cantidad de Objetos: Estimar la cantidad de pantallas, reportes, componentes
de 3GL que contendrá la aplicación.
Segundo: Clasificar cada instancia de un objeto según sus niveles de complejidad (simple, media o
difícil) de acuerdo a la Tabla 7.
Tercero: Dar el peso a cada objeto según el nivel de complejidad. Los pesos reflejan el esfuerzo
relativo requerido para implementar una instancia de ese nivel de complejidad. Tabla 8.
Cuarto: Determinar la cantidad de Puntos Objeto, sumando todos los pesos de las instancias de los
tipos de objetos especificados.



                                                         Para Pantallas
                                                  Cantidad y fuente de las tablas de datos
        Cantidad de                 Total < 4                       Total < 8                  Total 8 +
          Vistas                  ( < 2 servidor                ( < 2 - 3 servidor          ( > 3 servidor
        Contenidas                 < 3 cliente)                  < 3 - 5 cliente)            < 5 cliente)
            <3                       Simple                          Simple                     Media
           3-7                       Simple                          Media                      Difícil
            >8                       Media                           Difícil                    Difícil
                                                    Para Reportes
                                                  Cantidad y fuente de las tablas de datos
        Cantidad de
                                    Total < 4                       Total < 8                  Total 8 +
          Vistas
                                  ( < 2 servidor                ( < 2- 3 servidor           ( > 3 servidor
        Contenidas
                                   < 3 cliente)                  < 3-5 cliente)              < 5 cliente)
           0o1                       Simple                          Simple                     Media
           2o3                       Simple                          Media                      Difícil
            4+                       Media                           Difícil                    Difícil
                    Tabla 7: Esquema de Clasificación de Puntos Objetos. [Boehm 1995/2]



                                                              Complejidad - Peso
                    Tipo de Objeto                Simple              Media          Difícil
                       Pantalla                      1                    2            3
                       Reporte                       2                    5            8
                   Componente 3GL                                                      10
                             Tabla 8: Peso de un Punto Objeto. [Boehm 1995/2]


4.4.2    Puntos Función

      El modelo COCOMO II usa Puntos Función y/o Líneas de Código Fuente (SLOC) como base
para medir tamaño en los modelos de estimación de Diseño Temprano y Post-Arquitectura




                                                                                                             32
      Las métricas para puntos función están basadas en las guías proporcionadas por el
"International Function Point User Group"-IFPUG [IFPUG 1994][Behrens 1983][Kunkler 1985].
      Los Puntos Función procuran cuantificar la funcionalidad de un sistema de software. La meta
es obtener un número que caracterice completamente al sistema. Son útiles estimadores ya que
están basados en información que está disponible en las etapas tempranas del ciclo de vida del
desarrollo de software. COCOMO II considera solamente UFP (Puntos Función no ajustados).
     La fórmula de Albretch [Albretch 1979] para calcular los puntos función, es la siguiente:
            FP = UFP x TCF
     Donde UFP: Puntos Función no Ajustados
              TCF: Factor de Complejidad Técnica
     Para calcular los UFP, se deben identificar los siguientes tipos de ítems:
     !  Entradas Externas (Inputs): Entrada de datos del usuario o de control que ingresan desde
        el exterior del sistema para agregar y/o cambiar datos a un archivo lógico interno.
     !   Salidas Externas (Outputs): Salida de datos de usuario o de control que deja el límite del
         sistema de software.
     !   Archivo Lógicos Internos (Archivos): Incluye cada archivo lógico, es decir cada grupo
         lógico de datos que es generado, usado, o mantenido por el sistema de software.
     !   Archivos Externos de Interfase (Interfases): Archivos transferidos o compartidos entre
         sistemas de software.
     !   Solicitudes Externas (Queries): Combinación única de entrada-salida, donde una entrada
         causa y genera una salida inmediata, como un tipo de solicitud externa.

       Una vez identificados los ítems se clasifican de acuerdo al grado de complejidad en: bajo,
promedio o alto. Se asigna un peso a cada ítem según el tipo y el grado de complejidad
correspondiente. Finalmente los UFP son calculados mediante la sumatoria de los pesos de todos
los ítems identificados.
                       15
              UFP =    ∑ (Cantidad _ Items _ Tipo ) × ( Peso )
                       i =1
                                                     i           i




      La Tabla 9 muestra como se determinan los niveles de complejidad de cada tipo de ítem en
función del número y tipo de elementos de datos y archivos involucrados.


 Para archivos lógicos internos
                                      Para salidas y consultas externas          Para entradas externas
y archivos externos de interfase
Elementos   Elementos de datos                    Elementos de datos                     Elementos de datos
    de                                Tipos de                               Tipos de
             1-19    20-50    51+     archivos    1-5     6-19       20+     archivos    1-4    5-15      16+
 Registro
    1        Bajo    Bajo     Prom.     0ó1       Bajo    Bajo       Prom.    0ó1       Bajo    Bajo    Prom.
   2-5       Bajo   Prom.     Alto       2-3      Bajo   Prom.       Alto      2-3      Bajo    Prom.     Alto
    6+      Prom.    Alto     Alto       4+      Prom.    Alto       Alto      3+       Prom.   Alto      Alto
                    Tabla 9: Puntos Función. Determinación del Peso. [Boehm 1995/2]



                                                                                                        33
     La Tabla 10 muestra las ponderaciones asociadas a cada tipo de ítem. Estas ponderaciones
han sido derivadas y validadas empíricamente mediante la observación de una gran variedad de
proyectos.


               Tipo de función                          Peso del Factor de Complejidad
                                                  Bajo             Promedio              Alto
         Entradas Externas (Inputs)                 3                  4                  6
         Salidas Externas (Outputs)                 4                  5                  7
          Archivo Lógicos Internos
                                                    7                 10                 15
                 (Archivos)
       Archivos Externos de Interfase
                                                    5                  7                 10
                (Interfases)
        Consultas Externas (Queries)                3                  4                  6
                         Tabla 10: Peso del Factor de Complejidad. [Boehm 1995/2]



     Para el cálculo del Factor de Complejidad Técnica, TCF, se considera la siguiente fórmula:


                                 14
     TCF = 0.65 + 0.01 × ∑ Fi
                                 i =1

     Donde los F i corresponden a los pesos asignados a los siguientes factores:
           F1: Mecanismos de recuperación y back-up confiables
           F2: Comunicación de Datos
           F3: Funciones de Procesamiento Distribuido
           F4: Performance
           F5: Configuración usada rigurosamente
           F6: Entrada de datos on-line
           F7: Factibilidad Operativa
           F8: Actualización de archivos on-line
           F9: Interfases Complejas
           F10: Procesamiento Interno Complejo
           F11: Reusabilidad
           F12: Fácil Instalación
           F13: Soporte de múltiples instalaciones
           F14: Facilidad de cambios y amigabilidad
      Los pesos se consideran dentro de una escala de 0 a 5, descripta a continuación:
     0: Sin influencia
     1: Incidental


                                                                                                  34
        2: Moderado
        3: Medio
        4: Significativo
        5: Esencial
      Estas 14 características consideran aspectos como reusabilidad, performance, complejidad,
confiabilidad, etc., contemplados por COCOMO II a través de los factores de costo. Es por ello que
este modelo utiliza los UFP como métrica de determinación de tamaño.

4.4.3    Líneas de Código Fuente

      COCOMO II considera a la sentencia fuente lógica como línea standard de código. Ahora
bien, definir una línea de código es difícil debido a que existen diferencias conceptuales cuando se
cuentan sentencias ejecutables y de declaraciones de datos en lenguajes diferentes. El objetivo es
medir la cantidad de trabajo intelectual puesto en el desarrollo de un programa.
      Para minimizar esos problemas, se usa el checklist de definición desarrollado por el SEI, que
permite unificar criterios en la definición de una línea de código fuente [Park 1992], [Goethert et al.
1992]. Ver Figura 5. A los efectos de COCOMO II, se han efectuado cambios que consisten en
eliminar las categorías de software que insumen poco esfuerzo. Así no están incluidas librerías de
soporte de lenguajes, sistemas operativos, librerías comerciales, etc., ni tampoco el código generado
con generadores de código fuente.
      Existen herramientas automatizadas para medir la cantidad de líneas de código fuente, como
por ejemplo Amadeus [Amadeus 1994] [Selby et al. 1991]. Para realizar un análisis de mayor
especificidad, Amadeus automáticamente recolecta medidas adicionales como total de líneas fuente,
de comentarios, declaraciones, interfases, anidamientos, sentencias ejecutables y otras. Esta
herramienta provee varias medidas de tamaño, incluyendo métricas aplicables a tecnologías de
objetos de [Chidamber and Kemerer 1994].




                                                                                                    35
             Figura 5: Checklist para la definición de una línea de código fuente. [COCOMO II.0]


4.4.4   Conversión de Puntos Función a Líneas de Código Fuente (SLOC)

        Para determinar el esfuerzo nominal en el modelo COCOMO II los puntos función no
ajustados tienen que ser convertidos a líneas de código fuente considerando el lenguaje de
implementación (assembler, lenguajes de alto nivel, lenguajes de cuarta generación, etc.). Esto se
realiza para los modelos Diseño Temprano y Post Arquitectura teniendo en cuenta la Tabla 11
propuesta por Jones.




                                                                                                   36
                                                               SLOC/
                                        Lenguaje
                                                            Pto. Función
                           Ada                                          71
                           AI Shell                                     49
                           APL                                          32
                           Assembler                                   320
                           Assembler (macro).                          213
                           ANSI/Quick/Turbo Basic.                      64
                           Basic - Compilado                           91
                           Basic – Interpretado                        128
                           C                                           128
                           C++                                          29
                           ANSI Cobol 85                                91
                           Fortran 77                                  105
                           Forth                                        64
                           Jovial                                      105
                           Lisp                                         64
                           Modula 2                                     80
                           Pascal                                       91
                           Prolog                                       64
                           Generador de Reportes                       80
                           Planilla de Cálculo                          6
                        Tabla 11: Conversión de UFP a SLOC. [COCOMO II.0]


4.4.5   Desperdicio de Código (Breakage)

        Se considera como Desperdicio al porcentaje de código que se debe eliminar debido a la
volatilidad de los requerimientos. Por ejemplo, un proyecto con 100.000 instrucciones liberadas que
descartó el equivalente de 20.000 instrucciones tiene un valor de Desperdicio (BRAK) del 20%.
Éste se usa para ajustar el tamaño efectivo del software a ser desarrollado a los efectos del proceso
de estimación. De este modo la ecuación del esfuerzo nominal modificada, para contemplar este
aspecto, es la siguiente:


                                                                              B
                                              BRAK             
                            PM nominal = A ×  1 +      × KSLOC 
                                                  100          
4.4.6   Modelo de Reuso

    COCOMO II usa un modelo no lineal para estimar el tamaño del software cuando éste incluye
componentes reusables. El análisis de 3.000 casos de reuso de módulos realizado en el Laboratorio



                                                                                                  37
de Ingeniería de Software de la NASA indica que el costo asociado al reuso es una función no lineal
debido a dos razones [Selby 1988]:
     !   Existe un costo base, de alrededor de un 5%, que contempla la evaluación, selección, y
         asimilación del componente reusable.
     !   Pequeñas modificaciones generan desproporcionadamente grandes costos. Esto se debe al
         esfuerzo por comprender el software a ser modificado, testear y chequear las interfases.




                                Figura 6: Efectos no lineales del reuso



     En [Parikh and Zvegintzov 1983] se indica que el 47% del esfuerzo en el mantenimiento de
software está relacionado con la tarea que implica entender el software que va a ser modificado.
Además, en [Gerlich and Denskat 1994] se muestra que existe un efecto no lineal en el costo del
reuso debido al chequeo de interfases que debe realizarse durante el desarrollo del software
modificado. Estos inconvenientes pueden reducirse si el software está apropiadamente estructurado.
      El modelo COCOMO II permite tener en cuenta si un proyecto de software va a ser
construído a partir de componentes existentes. Para ello, reemplaza en la ecuación de estimación de
esfuerzo el parámetro KSLOC por el KESLOC, que representa la cantidad equivalente de nuevas
líneas de código a desarrollar.
     ESLOC se calcula de la siguiente forma:




     Donde:
     ASLOC           Cantidad de líneas de código fuente del software existente usadas para
                     desarrollar el nuevo producto
     DM              Porcentaje del diseño del software que requiere modificación para alcanzar
                     los objetivos del nuevo software a desarrollar


                                                                                                38
          CM                     Porcentaje del código del software que requiere modificación para lograr los
                                 objetivos del nuevo software a desarrollar
          IM                     Porcentaje del esfuerzo requerido para integrar y testear el software adaptado
                                 al producto global
          SU                     Porcentaje de comprensibilidad del software existente. Se determina en
                                 función a tres características: estructura, claridad y descriptividad. Ver Tabla
                                 12.
          AA                     Grado de Evaluación y Asimilación. Porcentaje de esfuerzo necesario para
                                 determinar si un módulo de software a adaptar es apropiado a la aplicación,
                                 como así también para integrar su descripción a la descripción total del
                                 producto. Ver Tabla 13.
          UNFM                   Nivel de familiaridad del programador con el software. Ver Tabla 14.


                        Muy Bajo               Bajo               Nominal               Alto              Muy Alto
                      Cohesión muy           Cohesión        Razonablemente                                 Fuerte
                                                                                    Alta cohesión,
                         baja, alto       moderadamente      bien estructurado,                          modularidad
 Estructura                                                                       bajo acoplamiento
                      acoplamiento,         Baja, alto         Algunas áreas                          Ocultamiento de la
                     código espagueti      acoplamiento            débiles                             implementación
                         Ninguna               Alguna           Moderada               Buena                Clara
                     correspondencia      correspondencia    correspondencia      correspondencia      correspondencia
 Claridad en          con el dominio       con el dominio     con el dominio       con el dominio       con el dominio
la aplicación          de aplicación

                                                                                                           Código
                                                                                 Buen nivel de
                      Código oscuro,       Algunas líneas                                              autodescriptivo,
                                                            Nivel moderado de líneas comentario,
                      documentación        comentario, y                                              documentación al
Descriptividad                                              líneas comentario, y documentación
                     faltante, oscura,         alguna                                                     día, bien
                                                             y documentación    útil; debilidad en
                         u obsoleta      documentación útil                                            organizada con
                                                                                 algunas áreas
                                                                                                       racional diseño
     SU                     50                  40                  30                   20                  10
                Tabla 12: Niveles del Incremento por Entendimiento del Software (SU). [COCOMO II.0]



          Incremento
                                                        Nivel de esfuerzo de AA
              AA
                 0         Ninguno
                 2         Búsqueda del módulo básico y documentación
                 4         Algunos módulos de testeo y evaluación, documentación
                 6         Considerable cantidad de módulos de testeo y evaluación, documentación
                 8         Gran cantidad de módulos de testeo y evaluación, documentación
                 Tabla 13: Niveles del Incremento por Asimilación y Evaluación (AA). [COCOMO II.0]




                                                                                                                  39
                             UNFM Incremento                     Nivel de Desconocimiento
                                      0.0                Completamente familiar
                                      0.2                Familiar en su mayor parte
                                      0.4                Algo familiar
                                      0.6                Considerablemente familiar
                                      0.8                Desconocido en su mayor parte
                                      1.0                Completamente Desconocido
                Tabla 14: Niveles del Incremento por Desconocimiento (UNFM). [COCOMO II.0]


4.4.7    Reingeniería y Conversión

       El modelo de Reuso de COCOMO II necesita un refinamiento adicional para estimar el costo
de reingeniería y de conversión. La principal diferencia entre reingeniería y conversión está dada
por la eficiencia de las herramientas automatizadas utilizadas para reestructurar el software. Pueden
producirse situaciones en las que a un muy alto nivel de porcentaje de código a modificar (CM) le
corresponda un bajo nivel de esfuerzo. En un caso de estudio de reingeniería analizado en [Ruhl
and Gunn 1991], el 80% del código (13.131 sentencias fuentes COBOL) fue reutilizado por medio
de la traducción automática con un esfuerzo real de 35 meses/personas, casi cuatro veces menos de
lo que se estimó usando el modelo de COCOMO II (152 meses/persona).
      El enfoque de reingeniería y conversión involucra la estimación de un nuevo parámetro AT,
que representa el porcentaje de código que sufre un proceso de reingeniería mediante el uso de una
herramienta de traducción automática. Del análisis de los datos del proyecto anterior surge que la
productividad de la traducción automática es de 2400 líneas de código fuente por mes-persona, este
valor podrá variar con las diferentes tecnologías y es designado en el modelo COCOMO II como
ATPROD.
      La ecuación siguiente muestra como afecta el reuso y la traducción automática a la estimación
del esfuerzo nominal:
                                                             AT
                                                     ASLOC ×
                             = A × ( KSLOC )   B
                                                   +        100
        PM       no min al                            ATPROD
                                                     $!!# ! !"
                                                           1


                                                                                                       
                                                    100 − AT  ( AA + AAF × (1 + 0 . 02 × SU × UNFM ) 
        KSLOC    = KNSLOC         +  KASLOC       ×          ×                                        , AAF ≤ 0 . 5
                                                   $ ! 100
                                                        !# !! "
                                                                                  100                   
                                                        2                                             


                                                    100 − AT  ( AA + AAF + SU × UNFM ) 
        KSLOC    = KNSLOC         +  KASLOC       ×          ×                          , AAF > 0 . 5
                                                       100               100           




        Donde:
                PMNominal              Esfuerzo expresado en meses personas
                B                      Factor de Escala
                A                      Constante que captura los efectos lineales sobre el esfuerzo de acuerdo
                                       a la variación del tamaño, (A=2.94)


                                                                                                                          40
           KSLOC          Tamaño del software a desarrollar
           KASLOC         Tamaño del software a adaptar
           KNSLOC         Tamaño del software a desarrollar desde cero
           AT             Porcentaje de código que sufre un proceso de reingeniería mediante el
                          uso de una herramienta de traducción automática.
           ATPROD         Productividad de la herramienta utilizada en la traducción automática
           SU             Porcentaje de comprensibilidad del software existente. Se determina en
                          función a tres características: estructura, claridad y descriptividad. Ver
                          Tabla 12
           AA             Grado de Evaluación y Asimilación. Porcentaje de esfuerzo necesario
                          para determinar si un módulo de software a adaptar es apropiado a la
                          aplicación, como así también para integrar su descripción en la
                          descripción total del producto. Ver Tabla 13
           UNFM            Nivel de familiaridad del programador con el software. Ver Tabla 14
           1               Término que representa el esfuerzo asociado a la traducción
                           automática
           2              Porcentaje de código que se adapta sin el uso de una herramienta
                          automatizada
       Considerando un módulo original de 5000 SLOC, y teniendo en cuenta los valores de los
parámetros de la Figura 7, la ecuación anterior determina que el tamaño del nuevo módulo a
considerar en la estimación de esfuerzo, es de 1731 SLOC.




                    Figura 7: Cómputo de un módulo adaptado. [COCOMO II.0]




                                                                                                 41
       como AAF=0.34, se aplica la primera ecuación:
                                  100 − 25  (4 + 34 × (1 + 0.02 × 30 × 0.4) 
              KSLOC = 0 + 5000 ×           ×                                 = 1731
                                  100                     100               


4.5   Factor Exponencial de Escala
      Los modelos de estimación de costos analizan dos aspectos antagónicos que influyen
notablemente en los procesos de estimación, la economía y deseconomía de escala. La economía de
escala abarca factores que hacen más eficiente la producción de software en gran escala. Es
frecuente lograr economía en proyectos de gran envergadura, gracias a la inversión en software de
propósitos específicos que mejoran la productividad, tales como herramientas de testeo, librerías de
programas, preprocesadores, postprocesadores. Ahora bien, estamos frente a una deseconomía de
escala cuando al incrementarse el tamaño del producto se produce una considerable disminución de
la productividad. El aumento de la cantidad de personas que conforman el equipo de desarrollo
generalmente provoca problemas de integración, que sumados a los conflictos personales, las
diferencias en la filosofía y hábitos de trabajos producen deseconomía de escala.
      Los modelos de estimación de costos frecuentemente tienen un factor exponencial para
considerar las economías y deseconomías de escala. En particular, COCOMO II captura esos
efectos en el exponente B:
                                                             5
                                       B = 1.01 + 0.01 × ∑ Wj
                                                            j =1

     Si B < 1.0, el proyecto exhibe economía de escala. Es decir si un producto aumenta el doble
su tamaño el esfuerzo del proyecto es menos del doble. Esto significa que la productividad del
proceso de desarrollo de software incrementa a medida que aumenta el tamaño del proyecto.
      Si el B = 1.0 las economías y deseconomías de escala están en equilibrio. Este modelo lineal
se usa siempre en la estimación de costos de proyectos pequeños.
      Si el B > 1.0 el proyecto muestra deseconomía de escala. Esto generalmente se debe a dos
factores principales: el crecimiento de las comunicaciones interpersonales y el de la integración de
sistemas. Integrar un producto pequeño como parte de otro requiere no sólo el esfuerzo de
desarrollar el producto sino también el esfuerzo de diseñar, mantener, integrar y testear interfases
con el resto del software. La productividad del proceso de desarrollo de software disminuye a
medida que aumenta el tamaño del proyecto.
      El cálculo del Factor Exponencial de Escala B está basado en factores que influyen
exponencialmente en la productividad y esfuerzo de un proyecto de software. Estos factores toman
valores dentro de un rango que va desde un nivel Muy Bajo hasta uno Extra Alto, tal como muestra
la Tabla 15. Cada nivel tiene un peso asociado Wj, y ese valor específico es el que se denomina
factor de escala. En la Figura 8 se observan los pesos de cada factor según el nivel, considerados
por el software COCOMO II.1999.0.




                                                                                                 42
  Factor de
                  Muy Bajo             Bajo           Normal            Alto           Muy Alto           Extra
  Escala Wj

Precedencia                         Ampliamente        Algún        Generalmente     Ampliamente      Completamente
                Completamente
                                        sin
    PREC        sin precedentes                      precedente        Familiar         Familiar         Familiar
                                    precedentes
 Flexibilidad
    en el                            Relajación       Alguna        Conformidad en     Alguna             Metas
  desarrollo       Rigurosa
                                     Ocasional       Relajación        general       Conformidad        generales
    FLEX
Arquitectura/
 Resolución          Poca              Alguna         Siempre       Generalmente     Principalmente     Completo
  de riesgo
                    (20%)              (40%)           (60%)            75%)             (90%)           (100%)
    RESL
Cohesión de                         Interacciones   Interacciones
                 Interacciones                                       Ampliamente       Altamente       Interacciones
  equipo                             con alguna     básicamente
                   difíciles           dificultad   cooperativas     Cooperativas    Cooperativas       Sin Fisuras
    TEAM
Madurez del
 proceso                                                 Desarrollado más adelante
    PMAT
                                 Tabla 15: Factores de Escala. [Boehm 1995/2]




                                 Figura 8: Factores de Escala. [COCOMO II.0]


4.5.1   Precedencia y Flexibilidad en el Desarrollo (PREC Y FLEX )

       El factor de precedencia (PREC) toma en cuenta el grado de experiencia previa en relación
al producto a desarrollar, tanto en aspectos organizacionales como en el conocimiento del software
y hardware a utilizar.
       El factor de flexibilidad (FLEX) considera el nivel de exigencia en el cumplimiento de los
requerimientos preestablecidos, plazos de tiempos y especificaciones de interfase.
       El modelo COCOMO II presenta la Tabla 16, en la cual se detallan las siete características a
analizar para encontrar el peso de los factores PREC y FLEX.




                                                                                                              43
                        Características                                 Muy Bajo             Nominal       Extra Alto
                                                                            Bajo               Alto        Muy Alto
                                                    Precedencia
   Entendimiento organizacional de los objetivos del
                                                                           General         Considerable      Total
   producto
   Experiencia en el trabajo con software relacionado                   Moderada           Considerable     Amplia
   Desarrollo concurrente de          nuevo       hardware     y
                                                                       Abundante            Moderado        Escaso
   procedimientos operacionales
   Necesidad de innovación en el procesamiento de
                                                                      Considerable            Alguna        Mínima
   datos, arquitectura y algoritmos
                                        Flexibilidad en el desarrollo
   Necesidad    de     conformar      requerimientos         pre-
                                                                            Total          Considerable     Básica
   establecidos
   Necesidad de conformar especificaciones externas de
                                                                            Total          Considerable     Básica
   interfase
   Estímulo por terminación temprana                                       Elevado            Medio          Bajo
         Tabla 16: Factores de Escala relacionados al modo de desarrollo de COCOMO. [COCOMO II.0]


 4.5.2    Arquitectura y Determinación del Riesgo (RESL)

       Este factor involucra aspectos relacionados al conocimiento de los ítems de riesgo crítico y
 al modo de abordarlos dentro del proyecto.
         El nivel del factor RESL es el resultado de un promedio de los niveles de las características
 listadas en la Tabla 17.


          Características              Muy Bajo         Bajo        Normal           Alto       Muy Alto       Extra
Planificación de la administración
de riesgo, identificando todos los
ítems de riesgo y estableciendo                                                                  En gran
                                        Ninguna       Pequeña        Algo           General                  Completa
hitos de control para su solución                                                                medida
por medio de la revisión del diseño
del producto (PDR)
Cronograma, presupuesto e hitos
internos especificados en el PDR,                                                                En gran
                                        Ninguno       Pequeño        Algo           General                  Completo
compatibles con el plan de                                                                       medida
administración de riesgo
Porcentaje     del      cronograma
dedicado a la definición de la
                                              5          10           17              25              33         40
arquitectura de acuerdo a los
objetivos generales del producto
Porcentaje de arquitecturas     de
software disponibles para        el        20            40           60              80           100          120
proyecto
Herramientas disponibles para
resolver    ítems   de     riesgo,                                                                Muy
                                        Ninguna        Pocas        Algunas         Buenas                   Completas
desarrollando y verificando las                                                                  Buenas
especulaciones de arquitecturas



                                                                                                                      44
Nivel de incertidumbre en factores
claves de la arquitectura: interfase                  Significati- Conside-
                                          Extremo                                Medio       Poco         Muy Poco
de usuario, hardware, tecnología,                         vo        rable
performance
Cantidad y grado de criticidad de           > 10          5 - 10      2-4          1         > 5 No
                                                                                                       < 5 No Crítico
ítems de riesgo                            Crítico        Crítico    Crítico     Crítico     Crítico
               Tabla 17: Componentes para calcular el factor de escala RESL. [COCOMO II.0]


 4.5.3   Cohesión del Equipo (TEAM)

         El factor de escala denominado Cohesión del Equipo tiene en cuenta las dificultades de
 sincronización entre los participantes del proyecto: usuarios, clientes, desarrolladores, encargados
 de mantenimiento, etc. Estas dificultades pueden surgir por diferencias culturales, dificultad en la
 conciliación de objetivos, falta de experiencia y familiaridad con el trabajo en equipo. El valor del
 factor TEAM se calcula como un promedio ponderado de las características listadas en Tabla 18.


             Características                   Muy Bajo Bajo Nominal              Alto      Muy Alto      Extra Alto
 Compatibilidad entre los objetivos y              Poca     Alguna Básica Considerable        Fuerte        Total
 culturas de los integrantes del equipo
 Habilidad y predisposición            para        Poca     Alguna Básica Considerable        Fuerte        Total
 conciliar objetivos
 Experiencia en el trabajo en equipo            Ninguna      Poca     Poca       Básica    Considerable     Vasto
 Visión compartida de objetivos           y     Ninguna      Poca     Poca       Básica    Considerable    Amplia
 compromisos compartidos
                           Tabla 18: Componentes del factor TEAM. [COCOMO II.0]


 4.5.4   Madurez del Proceso (PMAT)

         El procedimiento para determinar el factor PMAT se basa en el Modelo de CMM propuesto
 por el Software Engineering Institute. Existen dos formas de calcularlo:
         !   La primera captura el nivel de madurez de la organización, resultado de la evaluación
             según CMM y asignándole el valor correspondiente según Tabla 19:


                                        Nivel de CMM                 PMAT
                                       1 – Mitad inferior           Muy Bajo
                                    1 – Mitad superior                Bajo
                                               2                    Nominal
                                               3                      Alto
                                               4                    Muy Alto
                                               5                    Extra Alto
                     Tabla 19: Factor PMAT de acuerdo al nivel de CMM. [COCOMO II.0]

         !   La segunda está basada en las dieciocho Áreas de Procesos Claves (KPAs) del modelo
             del SEI. El procedimiento para determinar el PMAT es establecer el porcentaje de
             cumplimiento de cada una de las Áreas evaluando el grado de cumplimiento de las metas
             correspondientes. Para este procedimiento se emplea la Tabla 20.

                                                                                                                45
                                                         La mitad
                                       Casi      A                Ocasion     Casi
                                                           de las                     No se     No se
 Áreas de Procesos Claves            Siempre menudo                almente   nunca
                                                           veces                      aplica   conoce
                                      (90%)  (60-90%)             (10-40%)   (<10%)
                                                         (40-60%)
Administración    de      Requeri-
mientos
Planificación del Proyecto de
Software
Seguimiento y supervisión del
Proyecto de Software
Administración de Subcontratos
Aseguramiento de la Calidad
Administración de la Configura-
ción
Objetivo   del    Proceso      de
Organización
Definición del       Proceso   de
Organización
Programa de Entrenamiento
Administración   Integrada     de
Software
Ingeniería del Producto
Coordinación entre Grupos
Revisión por Pares
Administración Cuantitativa
Administración de la Calidad
Prevención de Defectos
Administración de las Tecno-
logías de Cambio
Administración de los Procesos
de Cambio
              Tabla 20: Nivel de cumplimiento de los objetivos de cada KPA. [COCOMO II.0]

       Despúes de determinar el nivel de cumplimiento de cada KPA el factor PMAT es calculado
según la fórmula:
                                                    18  KPA% i  5 
                                                    ∑
                                        PMAT = 5 −             × 
                                                    i =1  100  18 

4.6   Factores Multiplicadores de Esfuerzo ( Effort Multipliers EM )
      El esfuerzo nominal de desarrollo de un proyecto de software se ajusta para una mejor
estimación mediante factores que se clasifican en cuatro áreas: Producto, Plataforma, Personal y
Proyecto. La Tabla 21 muestra los niveles correspondientes a cada factor según las características
inherentes al área. Los valores asignados a cada factor según el nivel se pueden apreciar en la
Figura 9, Figura 10, Figura 11 y Figura 12 (COCOMO II.1999.0).


                                                                                                  46
              Factor        Muy Bajo                   Bajo                      Normal                     Alto             Muy Alto           Extra

                         Inconvenientes
                                                                                                     Pérdida financiera
                         insignificantes,      Mínimas pérdidas al        Pérdidas moderadas al
                                                                                                         elevada o        Vida humana en
              RELY         que afectan         usuario, fácilmente       usuario recuperables sin
                                                                                                       inconveniente           riesgo
                         solamente a los          recuperables           grandes inconvenientes
                                                                                                      humano masivo
                         desarrolladores
                                               DB bytes/Pgm SLOC
              DATA                                                            10<=D/P<100             100<=D/P<1000         D/P >0 1000


Producto
                                                       <10

              CPLX                                                                  Ver Tabla 22

                                                                                                                                              Reusable
                                                                                                                          Reusable dentro
                                                                                                     Reusable dentro de                       dentro de
                                               Ningún componente        Reusable dentro del mismo                          de una misma
              RUSE                                                                                       un mismo                             múltiples
                                                    reusable                    proyecto                                      línea de
                                                                                                         programa                             líneas de
                                                                                                                             productos
                                                                                                                                              producto
                            Muchas                                                                    Necesidades del     Necesidades del
                                               Algunas necesidades      Necesidades del ciclo de
                          necesidades                                                                  ciclo de vida       ciclo de vida
              DOCU                             del ciclo de vida sin    vida cubiertas en su justa
                           del ciclo de                                                                  cubiertas           cubiertas
                                                       cubrir                    medida
                         vida sin cubrir                                                               ampliamente        excesivamente
                                                                        Uso de <= 50% del tiempo
               TIME                                                                                        70%                 85%              95%
                                                                         de ejecución disponible



Plataforma
                                                                           Uso de <= 50% del
              STOR                                                         porcentaje total de             70%                 85%              95%
                                                                            almacenamiento

                                                Un cambio principal                                   Cambio principal    Cambio principal
                                                                         Cambio principal cada 6
                                                cada 12 meses. Un                                      cada 2 meses       cada 2 semanas.
              PVOL                                                        meses. Cambio menor
                                              cambio menor todos los                                 Cambio menor uno      Cambio menor
                                                                            cada 2 semanas
                                                     meses                                              por semana           cada 2 días

              ACAP         15 percentil            35 percentil                55 percentil             75 percentil        90 percentil
              PCAP         15 percentil            35 percentil                55 percentil             75 percentil        90 percentil


Personal
              PCON        48 % por año            24 % por año                12 % por año              6% por año          3 % por año
              AEXP         <= 2 meses              <= 6 meses                     1 año                   3 años              6 años
              PEXP         <= 2 meses              <= 6 meses                     1 año                   3 años              6 años
               LTEX        <= 2 meses              <= 6 meses                     1 año                   3 años              6 años
                                                                                                       Herramientas         Herramientas
                          Herramientas         Herramientas simples
                                                                                                        robustas y           altamente
                          que permiten        con escasa integración       Herramientas básicas,
              TOOL                                                                                       maduras,         integradas a los
                         editar, codificar,        al proceso de        integradas moderadamente
                                                                                                        integradas            procesos,
                             depurar                 desarrollo
                                                                                                      moderadamente       métodos y reuso

               SITE                                                                                                                           Completa-

Proyecto
                                               Multi-ciudad y multi-       Multi-ciudad o multi-      Misma ciudad o      Mismo Edificio o
             Ubicación    Internacional                                                                                                        mente
                                                    compañía                     compañía            área metropolitana      complejo
             Espacial                                                                                                                        Centralizado

                                                                                                                          Comunicaciones
               SITE                                                                                   Comunicaciones       electrónicas de
                         Algún teléfono,      Teléfonos individuales,                                                                        Multimedia
             Comuni-                                                     Email de banda angosta       electrónicas de       banda ancha,
                              mail                    FAX                                                                                    Interactiva
              cación                                                                                   banda ancha         ocasionalmente
                                                                                                                          videoconferencia


                             75% del                 85% del                    100% del                 130% del            160% del
              SCED
                             nominal                 nominal                     nominal                  nominal             nominal


                         Tabla 21: Factores de costo Modelo Post-Arquitectura. [Boehm 1995/1] [Boehm 1995/2]




                                                                                                                                               47
           4.6.1    Factores del producto

                    Se refieren a las restricciones y requerimientos sobre el producto a desarrollar.
                   RELY: Confiabilidad requerida
                  Este factor mide la confiabilidad del producto de software a ser desarrollado, esto es, que el
           producto cumpla satisfactoriamente con la función que debe realizar y respete el tiempo de
           ejecución que se fijó para el mismo.
                 Los niveles de escala para este factor son Muy Bajo, Bajo, Nominal, Alto y Muy Alto. Si el
           efecto de la falla del software produce inconvenientes solamente al desarrollador, quien debe
           solucionarla, el valor de RELY es Bajo. Si por el contrario, la falla atenta contra la vida humana el
           valor que adopta es Muy Alto.
                   DATA: Tamaño de la base de datos
                 El esfuerzo requerido para desarrollar un producto de software está relacionado con el tamaño
           de la base de datos asociada. Un ejemplo que marca la importancia de esta influencia es el esfuerzo
           que insume la preparación de los lotes de prueba que se usan en el testeo del producto.
                El valor de DATA se determina calculando la relación entre el tamaño de la base de datos y el
           tamaño del programa.
                                                      D Tamaño _ BasedeDatos ( Bytes)
                                                        =
                                                      P   Tamaño _ Pr ograma( SLOC )



                   CPLX: Complejidad del producto
                 CPLX analiza la complejidad de las operaciones empleadas en el producto, clasificadas en
           operaciones: de control, computacionales, dependientes de los dispositivos, de administración de
           datos y de administración de interfaz de usuario. El nivel que adopta este factor es el promedio del
           nivel de cada una de las cinco áreas o tipo de operaciones involucradas, ver Tabla 22 .


                                                                                                         Operaciones de
                                                              Operaciones          Operaciones de
              Operaciones de          Operaciones                                                       administración de
                                                            dependientes de       administración de
                 Control            computacionales                                                       interfases de
                                                            los dispositivos           datos
                                                                                                             usuario
              Pocas estructuras
            sin anidamiento: DO,

Muy Bajo
                    CASE,           Evaluación de una                             Arreglos simples en
                                                              Sentencias de        memoria principal.    Generadores de
              IF_THEN_ELSE.          expresión simple
                                                            lectura / escritura                              reportes,
                Composición                                                           Consultas,
                                       Por ejemplo:           con formatos                                Formularios de
             modular simple por                                                    actualizaciones a
                                                                 simples                                 entrada simples.
            medio de llamadas a       A=B+C*(D-E)                                     COTS-DB
              procedimientos o
                simples script




                                                                                                                    48
                                                                                         Archivo que subsiste
                                                                                            sin cambios de
                                            Evaluación de
                                                                                         estructuras de datos,
                                            expresiones de
                                                                  Ninguna necesidad          ni ediciones ni
      Bajo
                                             complejidad                                                       Uso de generadores
                                                                    de dispositivos              archivos
                   Estructuras anidadas       moderada                                                           de interfases de
                                                                   especiales para            intermedios.
                         sencillas                                                                               usuario gráficas
                                              Por ejemplo:        procesamiento de            Consultas y
                                                                                                                     simples
                                                                          I/O              actualizaciones a
                                            D=SQRT(B**2-
                                                                                                COTS-DB
                                               4.*A*C)
                                                                                           moderadamente
                                                                                                complejas
                    Uso mayoritario de
                      anidamientos                                                        Varios archivos de
                        sencillos .          Uso de rutinas        Procesamiento de
                                                                                          entrada y solo un

Nominal
                                             estándares de         Entradas/Salidas
                    Algunos controles                                                      archivo de salida.
                                             matemática y              que incluye
                     entre módulos.                                                            Cambios
                                              estadística             selección de                                Uso simple de
                   Tablas de decisión.                                                       estructurales
                                                                       dispositivo,                            algunos dispositivos
                   Pasaje de mensajes Operaciones básicas                                sencillos y ediciones
                                                                   procesamiento de
                      o llamadas a      con matrices y                                   simples. Consultas y
                                                                   errores y chequeo
                   subrutinas. Soporte     vectores                                        actualizaciones a
                                                                        de estado
                   para procesamiento                                                    COTS-DB complejas
                        distribuido
                                                                    Operaciones de
                       Programación                                 Entrada/salida a
                   estructurada con alto                               nivel físico
                                           Análisis numérico
                          grado de                                  (traducciones a
                                                  básico:                                 Triggers simples      Uso de un conjunto
                     anidamiento con                                 direcciones de
      Alto               predicados
                                             Interpolación,
                                                                    almacenamiento       activados por flujos    de dispositivo de
                                               ecuaciones                                     de datos.            Multimedia,
                   compuestos. Control                            físico, seeks, read,
                                              diferenciales                                                     Entrada/Salida de
                       de cola y pila.                                    etc. )           Reestructuración
                                                ordinarias,                                                     Procesamiento de
                      Procesamiento                                                       compleja de datos
                                               redondeos,          Optimización de                                     voz
                    distribuido. Control
                                            truncamientos           superposición
                    en tiempo real con
                                                                   Entradas/Salidas
                      un procesador

                        Codificación
                   recursiva. Manejo de
                    interrupciones con
                        prioridad fija.                             Rutinas para el        Coordinación de
                                           Análisis numérico

      Muy Alto
                     Sincronización de                                 control de           base de datos
                                             estructurado:                                                      Multimedia, Gráficos
                     tareas, complejas                              interrupciones,          distribuidas
                                              Matrices de                                                       dinámicos, Gráficos
                         llamadas a          ecuaciones.          enmascaramiento.          Disparadores             2D y 3D de
                         subrutinas           Ecuaciones          Manejo de líneas de        complejos.              moderadad
                       Procesamiento         diferenciales           comunicación                                   complejidad
                          distribuido                                                      Optimización de
                                               parciales
                   heterogéneo. Control                                                      búsqueda
                    en tiempo real con
                       un procesador

                                                                    Codificación de         Alto grado de
                   Planificación múltiple
                                                                                           acoplamiento,

      Extra Alto
                     de recursos con      Análisis numérico no       dispositivos
                                                                   dependientes del           relaciones
                   cambio dinámico de estructurado: Datos
                                                                        tiempo               dinámicas,
                   prioridades. Control      estocásticos.                                                      Multimedia compleja
                                                                                           estructuras de
                         al nivel de      Análisis de ruido con      Operaciones                                  Realidad virtual
                                                                                                objeto,
                   microcódigo. Control      alto grado de        microprogramadas.       administración de
                      en tiempo real            precisión         Performance crítica     datos en lenguaje
                         distribuido                               con relación a I/O           natural
                                Tabla 22. Factor Multiplicador CPLX. Complejidad del Producto. [COCOMO II.0]

                                                                                                                             49
        RUSE: Requerimientos de reusabilidad
       Este factor considera el esfuerzo adicional necesario para construir componentes que
puedan ser reusadas dentro de un mismo proyecto o en futuros desarrollos. El incremento del
esfuerzo se debe a que se incorporan tareas inherentes al reuso, tales como: creación de diseños
genéricos de software, elaboración de mayor cantidad de documentación, testeo intensivo para
asegurar que las componentes estén debidamente depuradas, etc.
        DOCU: Documentación acorde a las diferentas etapas del ciclo de vida
      Varios modelos de costo de software tienen un factor de costo para representar el nivel de
documentación requerida. En COCOMO II este factor se evalúa en función de la adecuación de la
documentación del proyecto a las necesidades particulares en cada etapa del ciclo de vida.
      Los posibles valores de DOCU van desde Muy Bajo (documentación que no cubre varias
necesidades) hasta Muy Alto (documentación excesiva de acuerdo a las necesidades).




                  Figura 9: Factores del producto. Modelo Post-Arquitectura.[COCOMO II.0]




4.6.2    Factores de la plataforma

        Estos factores analizan la complejidad de la plataforma subyacente.
     La plataforma es la infraestructura base de hardware y software, lo que también recibe el
nombre de máquina virtual. Si el software a desarrollar es un sistema operativo la plataforma es el
hardware, si en cambio se trata del desarrollo de un administrador de base de datos se considerará
como plataforma el hardware y el sistema operativo. Por ejemplo, la plataforma puede incluir
cualquier compilador o ensamblador empleado en el desarrollo del software.
        PVOL: Volatilidad de la plataforma
        Este factor se usa para representar la frecuencia de los cambios en la plataforma subyacente.
        STOR: Restricción del almacenamiento principal
      Este factor es una función que representa el grado de restricción del almacenamiento
principal impuesto sobre un sistema de software. Cuando se habla de almacenamiento principal se
hace una referencia al almacenamiento de acceso directo, tales como circuitos integrados, memoria
de núcleos magnéticos, excluyendo discos, cintas, etc.
     EL valor de STOR está expresado en términos de porcentaje del almacenamiento principal
que usará el sistema. El rango posible de valores va desde Nominal hasta Extra Alto.


                                                                                                    50
         TIME: Restricción del tiempo de ejecución
       Este factor representa el grado de restricción de tiempo de ejecución impuesta sobre el
sistema de software.
     EL valor de TIME está expresado en términos de porcentaje de tiempo de ejecución
disponible que usará el sistema. El rango posible de valores va desde Nominal hasta Extra Alto.




               Figura 10: Factores de la plataforma. Modelo Post-Arquitectura.[COCOMO II.0]




4.6.3    Factores del personal

        Estos factores están referidos al nivel de habilidad que posee el equipo de desarrollo.
        ACAP: Capacidad del analista
      Se entiende por analista a la persona que trabaja con los requerimientos, en el diseño global y
en el diseño detallado. Los principales atributos que deberían considerarse en un analista son la
habilidad para el diseño, el análisis, la correcta comunicación y cooperación entre sus pares. En este
análisis no se tiene en cuenta el nivel de experiencia.
        PCAP: Capacidad del programador
        Las tendencias actuales siguen enfatizando la importancia de la capacidad de los analistas.
Sin embargo, debido a que la productividad se ve afectada notablemente por la habilidad del
programador en el uso de las herramientas actuales, existe una tendencia a darle mayor importancia
a la capacidad del programador. También se evalúa la capacidad de los programadores para el
trabajo en equipo más que para el trabajo individual, resaltando las aptitudes para comunicarse y
cooperar mutuamente.
        PCON: Continuidad del personal
       Este factor mide el grado de permanencia anual del personal afectado a un proyecto de
software. Los posibles valores que puede adoptar PCON van desde 48% (muy bajo) al 3% (muy
alto).
        AEXP: Experiencia en la aplicación
       Este factor mide el nivel de experiencia del equipo de desarrollo en aplicaciones similares.
El rango de valores posibles de AEXP va desde Muy Bajo, representando una experiencia menor a
2 meses, hasta Muy Alto, experiencia de 6 o más años.
        PEXP: Experiencia en la plataforma
       COCOMO afirma que existe gran influencia de este factor en la productividad.
Reconociendo así la importancia del conocimiento de nuevas y potentes plataformas, interfases
gráficas, base de datos, redes, etc.


                                                                                                   51
    El rango de valores posibles de PEXP va desde Muy Bajo, representando una experiencia
menor a 2 meses, hasta Muy Alto, experiencia de 6 o más años.
        LTEX: Experiencia en el lenguaje y las herramientas
        Este factor mide el nivel de experiencia del equipo en el uso del lenguaje y herramientas a
emplear. El desarrollo de software, hoy en día, incluye el uso de herramientas que soportan tareas
tales como representación de análisis y diseño, administración de la configuración, extracción de
documentación, administración de librerías, y chequeos de consistencia. Es por ello que, no sólo es
importante la experiencia en el manejo del lenguaje de programación sino también en el uso de
estas herramientas, ya que influye notablemente en el tiempo de desarrollo.
      El rango de valores de posibles de LTEX va desde Bajo, representando una experiencia
menor a 2 meses hasta Muy Alto representando una experiencia de 6 o más años.




                 Figura 11: Factores del personal. Modelo Post-Arquitectura.[COCOMO II.0]




4.6.4    Factores del proyecto

     Estos factores se refieren a las condiciones y restricciones bajos las cuales se lleva a cabo el
proyecto.
        TOOL: Uso de herramientas de software
      Las herramientas de software se han incrementado significativamente desde la década del 70.
El tipo de herramientas abarca desde las que permiten editar y codificar hasta las que posibilitan una
administración integral del desarrollo en todas sus etapas.
     El rango de valores posibles de TOOL va desde Muy Bajo, que corresponde al uso de
herramientas sólo para codificación, edición y depuración, hasta Muy Alto, que incluye potentes
herramientas integradas al proceso de desarrollo.
        SITE: Desarrollo multisitio
     La determinación de este factor de costo involucra la evaluación y promedio de dos factores,
ubicación espacial (disposición del equipo de trabajo) y comunicación (soporte de comunicación).
        SCED: Cronograma requerido para el desarrollo
       Este factor mide la restricción en los plazos de tiempo impuesta al equipo de trabajo. Los
valores se definen como un porcentaje de extensión o aceleración de plazos con respecto al valor
nominal. Acelerar los plazos produce más esfuerzo en las últimas etapas del desarrollo, en las que


                                                                                                   52
se acumulan más temas a determinar por la escacez de tiempo para resolverlos tempranamente. Por
el contrario una relajación de los plazos produce mayor esfuerzo en las etapas tempranas donde se
destina más tiempo para las tareas de planificación, especificación, validación cuidadosa y
profunda. El rango de valores posibles de SCED va desde 75% al 160%.




               Figura 12: Factores del proyecto. Modelo Post-Arquitectura.[COCOMO II.0]




4.7   Consideraciones destacables del modelo
      En el modelo COCOMO se pueden distinguir los siguientes aspectos relevantes:
       1. Los factores de costo del modelo son, en orden de importancia:
          !   Tamaño: Cantidad de líneas de código fuente.
          !   Factor Exponencial de Escala: Representa el impacto de la economía y deseconomía
              de escala.
          !   Factores Multiplicadores de Esfuerzo: Simbolizan características que influyen en el
              desarrollo del producto, clasificadas en 4 categorías: plataforma, personal, proyecto y
              producto.
       2. COCOMO asume que la especificación de requerimientos no sufrirá cambios
          fundamentales después de que culmine la fase de planificación de requerimientos.
          Algunos refinamientos y reinterpretaciones pueden ser inevitables, por lo tanto,
          cualquier modificación importante implicará una revisión en la estimación de los costos.
       3. El período de desarrollo cubierto por este modelo comienza después de la fase de
          revisión de requerimientos y finaliza con la aprobación de la fase de testeo.
       4. El análisis de distribución de esfuerzo y tiempo de desarrollo por fase y actividad se
          hereda del modelo COCOMO' 81, donde se asume el uso de un modelo de desarrollo
          secuencial denominado comunmente "Cascada" (Waterfall). Si el proyecto bajo estudio
          se ejecuta usando otro modelo, los porcentajes de distribución deben reinterpretarse o
          directamente no deben ser tenidos en cuenta.
       5. La estimación de COCOMO abarca todas las tareas en relación directa a las actividades
          del proyecto, quedando de esta manera excluidas las actividades ejecutadas por
          operadores, secretarias, administradores de alto nivel, etc.
       6. COCOMO evita estimar costos en una unidad monetaria determinada puesto que la
          unidad mes-persona es más estable, al ser inmune a las fluctuaciones monetarias del
          mercado. Para convertir mes-persona a dólares se aplica un promedio del valor mes-
          persona diferente para cada fase del proyecto, lo que permite tener en cuenta los distintos
          niveles salariales.


                                                                                                  53
5 Un Ejemplo Práctico
    Se propone ilustrar la aplicación del modelo COCOMO II tomando como ejemplo el mismo
proyecto de la Sección 3.4.1, el sistema STUJOB, Sistema de Administración de Trabajo para
Estudiantes.
     En el ejemplo presentado a continuación se usará un formulario similar a los introducidos en la
Sección 3.4.1 denominado CLEF12, este formulario es de gran ayuda para la estimación manual. A
efectos de clarificar el proceso, también se presentarán algunas pantallas de una herramienta
automatizada que implementa el modelo, COCOMO II.1999.0. Vale la pena aclarar que este
software está calibrado para módulos de más de 2000 SLOC, por lo tanto los resultados pueden ser
no muy precisos.
       Los pasos del proceso de estimación de esfuerzo y tiempo de desarrollo son:
1. Identificar los módulos que conforman el sistema, asignarles un número y un nombre e
   ingresarlos en las columnas 1 y 2, respectivamente. Ej: Módulo 2: Search.
2. Determinar el tamaño de cada módulo expresado en SLOC, líneas de código fuentes liberadas,
   y registrarlo en la columna 3.
       Se debe tener en cuenta que el tamaño puede verse afectado por dos aspectos: el reuso y la
       traducción automática, como se analizó en las secciones 4.4.6 y 4.4.7.
       Ej: Para el Módulo Utilities, adaptado a partir de un módulo de 5000 SLOC, se considera un valor
       igual a 1731 SLOC.
3. Determinar el tamaño en SLOC del Sistema, sumando el tamaño de los módulos que lo
   componen. Anotarlo en la celda 28.
       Ej: Tamaño del Sistema: 1800+700+1200+1700+900+1731 = 8031 SLOC
4. Calcular el Factor Exponencial de Escala (B), considerando los 5 factores Wj (PREC, FLEX,
   RESL, TEAM y MAT) en un nivel nominal. Ver Figura 8.

                                                                 5
                                            B = 1.01 + 0.01 ×   ∑Wj
                                                                 j =1




          B = 1.01 + 0.01 x (3.72 + 3.04 + 4.24 +3.29 + 4.68) = 1.1997 ≅ 1.20


5. Calcular el Esfuerzo Nominal requerido para desarrollar el sistema, PMNominal, en la celda 29 y la
   Productividad del Proyecto en la celda 30.

                      PMNominal = (KSLOC/PM) Nominal = 2.94 × (8.031)                     = 35.81
                                                                                   1.20




                                                                              8031
                      Productivi dad Nominal = (KSLOC/PM Nominal ) =                = 224.27
                                                                              35.81



12
     Component Level Estimating Form. Formulario de Estimación al nivel de componente.



                                                                                                    54
6. Calcular y registrar en la columna 22 el Esfuerzo Nominal por Módulo(PMNominal,Módulo), que se
   obtiene como el cociente entre el tamaño del módulo (columna 3) y la Productividad del
   Proyecto (celda 30).
   Ej: Para el módulo Modify PMNominal,Módulo = 900 / 224.27 = 4.0130 ≅ 4.0
7. Analizar las características de cada módulo y determinar, con la ayuda de la Tabla 21, en que
   nivelse encuentra cada uno de los factores de costo. Según el nivel determinado (Muy Bajo,
   Bajo, Nominal, Alto, Muy Alto) asignar los valores de los multiplicadores de esfuerzo
   correspondientes, obteniéndolos de la Figura 9 a la Figura 12 y completar las columnas 4 a 20.
8. Multiplicar los multiplicadores de esfuerzo de la columna 4 a la 20 para cada fila y así obtener
   el Factor de Ajuste del Esfuerzo EAF para cada módulo. Ingresar los resultados en la columna
   21.
   Ej: Para el Módulo Modify, el cálculo es:
                EAFM= 0.87 x 0.87 x 0.85 x 1.15 x 0.81 x 1.09 x 1.09 x 0.90 = 0.64
9. Calcular el Esfuerzo Estimado por Módulo, PMEstimado,Módulo, en la columna 23, multiplicando el
   valor de PMNominal,Módulo, columna 22, por el correspondiente Factor de Ajuste EAFM de la
   columna 21.
   Ej: Para el Módulo Modify, el cálculo es:
                PMEstimado,Módulo = PMNominal,Módulo x EAFM= 4.0 x 0.64 =2.56 ≅ 2.6
10. Sumar los valores calculados en el ítem anterior para determinar el Esfuerzo Estimado del
    Sistema Total PMEstimado, registrar este valor en la celda 31.
   Ej: PMEstimado = 4.3 + 1.2 + 3.4 + 4.1 + 2.6 +6.4 = 22
11. Determinar el Tiempo de Desarrollo Estimado del proyecto TDEV y anotarlo en la celda 34.

                                     [                           ] SCED
                           TDEV = 3.0 × 22 ( 0.33+ 0.2×(1.2−1.01)) ×
                                                                     100
                                                                         %
                                                                           = 9.36


12. Anotar en la columna 24 el Costo del Mes-Persona para cada módulo, expresado en miles de
    dólares. Posteriormente multiplicar estos costos por los PMEstimado,Módulo correspondientes
    (columna 23), encontrando así el Costo Estimado de cada módulo y registrarlo en la columna
    25.
   Ej: Para el Módulo Utils, se asume un costo más bajo debido a la participación de un grupo de
   analistas y programadores novatos:
             Costo Mes-Persona = 5250
             Costo Estimado,Módulo= Costo Mes-Persona x PMEstimado,Módulo = 5250 x 6.4 = 33600
13. Calcular el Costo Total del Sistema sumando los valores obtenidos en el ítem anterior y
    registrarlo en la celda 32.
   Ej: Costo Estimado= 23091+6444+18258+22071+13962 = 117490
14. Para cada módulo determinar y registrar en la columna 26 el Costo por instrucción en US$, el
    cual se calcula como el cociente entre el Costo de Desarrollo (columna 25) y el Tamaño del
    Módulo (columna 3).
   Ej: Para el Módulo Modify
         Costo por instrucción en miles de US$ = 13962/900 = 15.51 dólares



                                                                                                 55
15. Para cada módulo determinar y registrar en la columna 27 la Productividad, calculada como el
    cociente entre el Tamaño del Módulo (columna 3) y el Esfuerzo Estimado por módulo
    PMNominal,Módulo (columna 23).
    Ej: Para el Módulo Modify
       Productividad = 900/2.6 = 346.15 SLOC / mes-persona


        El software COCOMO II.1999.0 además de las estimaciones presentadas brinda otras
posibilidades que vale la pena mencionar:
•   Tanto el esfuerzo como el tiempo de desarrollo del proyecto completo se pueden distribuir por
    fase. Según se observa en la Figura 13, los porcentajes de distribución son similares a los usados
    en el modelo COCOMO’ 81 correspondientes al Modo Semiacoplado y a un tamaño de 8
    KSLOC, ver Tabla 2. La diferencia surge debido a que los porcentajes se han interpolado para
    considerar el tamaño real de software de 8031 SLOC.




           Figura 13: Distribución del esfuerzo y tiempo de desarrollo del sistema total por fase

•   Existe la posibilidad de analizar la distribución de esfuerzo y de tiempo de desarrollo de cada
    módulo en las distintas fases de desarrollo. La Figura 14 muestra los valores correspondientes al
    módulo Qedit.




         Figura 14: Distribución del esfuerzo y tiempo de desarrollo de un modulo (Qedit) por fase




                                                                                                     56
•      Al igual que COCOMO'81 el software también permite estudiar como se distribuye el esfuerzo
       y tiempo de desarrollo para cada actividad en cada fase. La Figura 15 muestra los valores
       considerando la fase de Integración y Testeo. La Figura 17 considera la misma fase sólo para el
       módulo Qedit.




                                                                                                           13
Figura 15: Distribución del esfuerzo y tiempo de desarrollo de la fase Integración y Testeo por subfases




Figura 16: Distribución del esfuerzo y tiempo de desarrollo de la fase Integración y Testeo por subfases,
considerando el módulo Qedit, solamente




13
     Se llaman subfases, a lo que COCOMO' 81 denomina actividades.




                                                                                                                57
Número Módulo       Nombre Módulo                                                                                                                                                                             PM Nominal              PM Estimado              Costo Mes-Pers                       Costo x Instrucc                              SLOC/Mes-Pers
                                                              Producto                           Plataforma                           Personal                                    Proyecto



                                                                                                                                                                                                                                                                                                                                  Productividad
                                      SLOC                                                                                                                                                                                 Mes-Pers                 Mes-Pers                    Dólares     Costo                      Dólares
                                                                                                                                                                                                        EAF
                                               RELY    DATA      CPLX     RUSE    DOCU    TIME       STOR     PVOL    ACAP    PCAP     PCON     AEXP     PEXP     LTEX     TOOL       SITE     SCED



1                  2                 3        4        5         6        7       8       9         10        11     12      13      14       15       16       17       18         19        20      21          22                      23                         24                    25             26                           27


1                Qedit              1800     1.00     1.00     1.00      1.00    1.00    1.00      1.00     0.87     0.85    1.00    1.00     0.81     1.00     1.00     0.90       1.00     1.00     0.54           8                  4.3                    5370                       23091     12.8                          418.6


2               Search              700      1.00     1.00     1.00      1.00    1.00    1.00      1.00     0.87     0.85    0.88    1.00     0.81     0.91     0.91     0.90       1.00     1.00     0.39      3.1                     1.2                    5370                       6444          9.2                       583.3


3               Output              1200     1.00     1.00     0.87      1.00    1.00    1.00      1.00     0.87     0.85    1.15    1.00     0.81     1.09     1.09     0.90       1.00     1.00     0.64      5.3                     3.4                    5370                       18258     15.2                          352.9


4               UpEdit              1700     1.00     1.00     1.00      1.00    1.00    1.00      1.00     0.87     0.85    1.00    1.00     0.81     1.00     1.00     0.90       1.00     1.00     0.54      7.6                     4.1                    5370                       22071     12.9                          414.6


5               Modify              900      1.00     1.00     0.87      1.00    1.00    1.00      1.00     0.87     0.85    1.15    1.00     0.81     1.09     1.09     0.90       1.00     1.00     0.64           4                  2.6                    5370                       13962     15.51                         346.1


6               Utils               1731*    1.00     1.00     0.73      1.00    1.00    1.00      1.00     0.87     1.00    1.15    1.00     1.00     1.09     1.09     0.90       1.00     1.00     0.78      8.2                     6.4                    5250                       33600     19.4                          270.4

                             28              Total SLOC                                                                                                                                                                    31                                                   32                                     33
                                    8031                                                                                                                                                       Esfuerzo Estimado                      22.0                                                117426                                   365
                                                                                                                                                                                                            PMEst
                                             Esfuerzo PMNominal                                                                                                                                                            34         9.36                                      Costo Total                        Productividad
                             29     35.81                                                                                                                                                                                                                                             Estimado                               Estimada
                                                                                                                                                                                             Tiempo de Desarrollo
                                                                                                                                                                                                          TDEV
                                             Productividad
                             30 224.27
                                             (KSLOC/PM)Nomlnal

                                                                        Figura 17: Formulario para la estimación de esfuerzo y tiempo de desarrollo utilizando COCOMO II.


                   *
                        Tamaño del módulo, considerando que es adaptado a partir de un módulo de 5000 SLOC. Ver Tema 4.4.6, pag. 37.




                                                                                                                                                                                                                                                                                                                                 58
6 Conclusiones
      Durante la última década, la evolución de las tecnologías de desarrollo de software impulsó
un nuevo enfoque en la estimación de costos, que considerara conceptos tales como orientación a
objetos, reingeniería, reusabilidad, utilización de paquetes comerciales, composición de
aplicaciones. Además, surgió la necesidad de que estos nuevos modelos se adaptaran a la
granularidad de la información disponible en las diferentes etapas de desarrollo.
      La familia de modelos de COCOMO II, constituída por los modelos Composición de
Aplicación, Diseño Temprano y Post-Arquitectura, conforma estas premisas ya que son parte de
sus objetivos principales.
      COCOMO II, al igual que el modelo original preserva su estado de dominio público en
relación a los algoritmos, la herramienta de software, estructuras de datos, relaciones e interfases.
      Para contar con información fidedigna y favorecer el continuo refinamiento y calibración del
modelo, la USC implementó un Programa de Recolección de Datos14. Se espera que en el
transcurso del año 2001 se libere una nueva versión de la herramienta calibrada y actualizada.
      Otra de las ventajas de este modelo es que puede ser adaptado (calibrado) a un organismo en
particular, si se cuenta con la experiencia de un número importante de proyectos ya culminados que
puedan aportar los datos necesarios para la recalibración
      Sin lugar a dudas, en la actualidad siguen existiendo inconvenientes y limitaciones para las
estimaciones, pero más allá de esto COCOMO II ha recorrido un importante camino, logrando la
madurez necesaria del modelo para conseguir estimaciones de gran precisión.




14
  Es importante destacar que cualquier entidad u organización que trabaje en proyectos de desarrollo de software puede
participar en este esfuerzo de recolección de datos mediante la contestación de un cuestionario provisto por el USC o
enviando los archivos generados por el software USC COCOMO II.1999.0.

                                                                                                                   59
7 Anexo I.
  Formularios para la Estimación Jerárquica de Software. Modelo COCOMO Detallado.




                                                                                    60
Proyecto: ……………….                                            Analista: …………………..                                    Fecha: …………………

 1       2                     Producto        Atributos de la Computadora     Personal             Proyecto         32    20     33      34       35   36
                    8
Nro Subsistema                 21         22   23      24      25     26      27      28      29       30      31   EAF    PM     PM                    TOT
                  KSLOC
SS SS                      RELY       DATA     TIME   STOR    VIRT   TURN ACAP AEXP          MODP    TOOL SCED       SS   MOD     EST
                          PD
                          DD
                          CUT
                          IT




                                                                                                                          PD
Modo:        9            Total KSLOC                                                                                     DD
                                                                                                                          CUT
                                                                                                                          IT

             10           Esfuerzo Nominal                              12    Fracción por                                Total
                          PMNominal                                              Fase
                                                                             PD
             11           Productividad                                      DD                                                   PM    Schedule   K
                          (KSLOC/PM)Nominal                                  CUT
                                                                             IT
Proyecto: ……………..                            Analista: ……………….                 Fecha: …………………
                                                                                  18       13        19       37
   3         4          5        6      7       14        15      16     17
                                                                               EAF      PM        PM       PM
Nro. SS Nro. Módulo   Módulo   KSLOC   AAF     CPLX      PCAP    VEXP   LEXP
                                                                               Módulo   Nominal   Módulo   Estimado




                                                                                                              62
8 Acrónimos y Abreviaturas
            Third Generation Language
    3GL
            Lenguaje de 3era. Generación
            Percentage of reuse effort due to assessment and assimilation
    AA
            Porcentaje de esfuerzo de reuso debido a la evaluación y asimilación
            Analyst Capability
   ACAP
            Aptitud del Analista
            Annual Change Traffic
    ACT
             Tráfico Anual de Cambios
            Adapted Source Lines of Code
   ASLOC
            Líneas de Código Fuente Adaptadas
            Applications Experience
   AEXP
            Experiencia en las Aplicaciones
            Automated Translation
    AT
            Traducción automática
            Breakage
   BRAK
            Desperdicio de Código
            Computer Aided Software Engineering
   CASE
            Ingeniería de Software Asistida por Computadora
   CLNT     Cantidad de tablas de datos en clientes usadas en SCREEN o REPORT
            Percentage of code modified during reuse
    CM
            Porcentaje de Código modificado durante el reuso
            Capability Maturity Model
   CMM
            Modelo de Madurez de Capacidades
            Constructive Cost Model
  COCOMO
            Modelo Constructivo de Costo
            Commercial Off The Shelf Packages
   COTS
            Paquetes, módulos, clases, librerías comerciales
            Product Complexity
   CPLX
            Complejidad del Producto
            Database Size
   DATA
            Tamaño de la Base de Datos
            Database Management System
   DBMS
            Sistema de Administración de Base de Datos
        Degree of Influence
 DI
        Grado de Influencia
        Percentage of design modified during reuse
 DM
        Porcentaje de Diseño modificado durante el reuso
        Documentation to match lifecycle needs
DOCU
        Documentación acorde a las necesidades del ciclo de vida
        Electronic Data Systems
 EDS
        Sistemas Electrónicos de Datos
        Equivalent Source Lines of Code
ESLOC
        Líneas de Código Fuente Equivalentes
        Facilities
FCIL
        Facilidades
        Function Points
 FP
        Puntos Función
        Government Furnished Software
 GFS
        Software Provisto por el Gobierno
        Graphical User Interfase
 GUI
        Interfaz de Usuario Gráfica
        Integrated Computer Aided Software Environment
ICASE
        Ambiente Integrado Asistido de Software
        Percentage of integration redone during reuse
 IM
        Porcentaje de Integración durante el reuso
        Thousands of Source Lines of Code
KSLOC
        Miles de Líneas de Código Fuente
        Programming Language Experience
LEXP
        Experiencia en el Lenguaje de Programación
        Language and Tool Experience
LTEX
        Experiencia en lenguajes y Herramientas
        Modern Programming Practices
MODP
        Prácticas Modernas de Programación
        National Institute of Standards and Technology
NIST
        Instituto Nacional de Estándares y Tecnología
        New Object Points
NOP
        Nuevos Puntos Objetos
 OS     Operating Systems

                                                                   64
       Sistemas Operativos
       Programmer Capability
PCAP
       Aptitud del Programador
       Personnel Continuity
PCON
       Continuidad del Personal
       Platform Difficulty
PDIF
       Dificultad de la Plataforma
       Personnel Capability
PERS
       Aptitud del Personal
       Platform Experience
PEXP
       Experiencia en la Plataforma
       Product Line
 PL
       Línea de Productos
       Person Month
PM
       Mes-Persona
       Personnel Experience
PREX
       Experiencia del Personal
       Productivity rate
PROD
       Tasa de Productividad
       Platform Volatility
PVOL
       Volatilidad de la Plataforma
       Product Reliability and Complexity
RCPX
       Confiabilidad y Complejidad del producto
       Required Software Reliability
RELY
       Confiabilidad Requerida
       Required Reusability
RUSE
       Reusabilidad Requerida
       Requirements Volatility
RVOL
       Volatilidad de los Requerimientos
       Required Development Cronograma
SCED
       Cronograma de Desarrollo Requerido
       Classified Security Application
SECU
       Aplicación de Seguridad Clasificada
       Software Engineering Institute
SEI
       Instituto de Ingeniería de Software

                                                  65
                Multi-site operation
    SITE
                Operación Multi-Sitio
                Source Lines of Code
    SLOC
                Líneas de Código Fuente
                Main Storage Constraint
    STOR
                Restricción de Almacenamiento Principal
                Cantidad tablas de datos en servidores (mainframe o equivalente) usadas en
   SRVR
                SCREEN o REPORT
                Computer Turnaround Time
   TURN
                Tiempo de Respuesta de la computadora expresado en horas
                Test and Evaluation
    T&E
                Test y Evaluación
                Percentage of reuse effort due to software understanding
     SU
                Porcentaje de esfuerzo de reuso debido al entendimiento del software
                Execution Time Constraint
    TIME
                Restricción del Tiempo de Ejecución
                Use of Software Tools
   TOOL
                Uso de Herramientas de Software
                Air Force Electronic Systems Division
USAF/ESD U.S.
                División de Sistemas Electrónicos de la Fuerza Area
                Virtual Machine Experience
   VEXP
                Experiencia en la Máquina Virtual
                Virtual Machine Volatility
    VIRT
                Volatilidad de la Máquina Virtual
                Virtual Machine Volatility: Host
   VMVH
                Volatilidad de la Máquina Virtual: Principal
                Virtual Machine Volatility: Target
   VMVT
                Volatilidad de la Máquina Virtual
   %reuse       El porcentaje de pantallas, reportes, y módulos de 3GL reusados de aplicaciones
                previas, clasificadas en grados de reuso



9 Referencias
   [Albretch 1979] Albretch, A.J , “Measuring Application Development Productivity”, Proc.
                   IBM Application Development Symposium, Monterrey, CA, Octubre 1979,
                   Págs. 83-92.


                                                                                         66
[Amadeus 1994] Amadeus, Amadeus Measurement System User’s Guide, Version 2.3a,
               Amadeus Software Research, Inc., Irvine, California, July 1994.
[Banker 1994]   Banker, R., R. Kauffman and R. Kumar (1994), “An Empirical Test of
                Object-Based Output Measurement Metrics in a Computer Aided Software
                Engineering (CASE) Environment” Journal of Management Information
                Systems.
[Behrens 1983] Behrens, C. (1983), “Measuring the Productivity of Computer Systems
               Development Activities with Function Points”, IEEET Transactions on
               Software Engineering.
[Boehm 1981]    Barry W Boehm, Software Engineering Economics, Ed. Prentice Hall.
[Boehm 1989] Boehm, B. and W. Royce, Ada COCOMO and the Ada Process Model,
              Proceedings, Fifth COCOMO Users’ Group Meeting, Software Engineering
              Institute, Pittsburgh, PA, November 1989.
[Boehm 1995/1] Boehm B.W.,Clark B., Horowizt E., Westland C., Madachy R., Selby R.,
               Cost Models for Future Software Life Cycle Processes: COCOMO II ,
               Annals of Software Engineering Special Volume on Software Process and
               Product Measurement, 1995, Vol 1, pp. 45-60. Primer paper que trata
               COCOMO II.
                http://sunset.usc.edu/COCOMOII/cocomo.html
[Boehm 1995/2] Boehm B.W.,Clark B., Horowizt E., Westland C., Madachy R., Selby R.,
               The COCOMO 2.0 Software Cost Estimation Model,
                http://sunset.usc.edu/COCOMOII/cocomo.html.
[Chidamber and Kemerer 1994] Chidamber, S. and C. Kemerer , A Metrics Suite for Object
               Oriented Design, IEEE Transactions on Software Engineering, 1994.
[COCOMO II.0] Documentos de la ayuda del software COCOMO II.0.


[Fenton 1997]   Fenton, N.E. Pfleeger, Software Metrics. A Rigorous & Practical Approach,
                PWS Publishing Company, Boston, 1997, S.L. Capitulo 7.
[Ghezzi 1991]   Carlo Ghezzi, Mehdi Jazayeri, Dino Mandrioli, “Fundamentals of Software
                Engineering”.
[Gerlich and Denskat 1994] Gerlich, R. and Denskat U., “A Cost Estimation Model for
               Maintenance and High Reuse”, Proceedings, ESCOM 1994, Ivrea, Italy.
[Goethert et al. 1992] Goethert, W., E. Bailey, M. Busby, Software Effort and Cronograma
                   Measurement: A Framework for Counting Staff Hours and Reporting
                   Cronograma Information, CMU/SEI-92-TR-21, Software Engineering
                   Institute, Pittsburgh, PA.
[Madachy 1997] Madachy, J. Raymond, Heuristic Risk Assessment Using Cost Factors,
               IEEE Software, May/June 1997, pp. 51-59.
[Parikh and Zvegintzov 1983]
[Park 1992]     Park R., Software Size Measurement: A Framework for Counting Source
                Statements, CMU/SEI-92-TR-20, Software Engineering Institute,
                Pittsburgh, PA.



                                                                                      67
[IFPUG 1994]     IEPUG, IFPUG Function Point Counting Practices: Manual Release 4.0,
                 International Function Point Users’ Group, Westerville, OH.
[Kunkler 1985] Kunkler,  J.,   A    Cooperative    Industry    Study    on   Software
               Development/Maintenance Productivity, Xerox Corporation, Xerox Square -
               -- XRX2 52A, Rochester, NY 14644, Third Report, March 1985.
[Pressman 1997] Pressman Roger, “Ingeniería de Software, Un Enfoque Práctico”.
[Ruhl and Gunn 1991] Ruhl, M., and Gunn, M., “Software Reengineering: A Case Study and
                Lessons Learned” NIST Special Publication 500-193, Washington, DC,
                September 1991.
[Selby 1988]     Selby R., “Empirical Analyzing Software Reuse in a Production
                 Environment”, In Software Reuse: Emerging Technology, W. Tracz (Ed.),
                 IEEE Computer Society Press, 1988, pp. 176-189.
[Selby et al. 1991] Selby R., A. Porter, D. Schimidt and J. Berney , Metric-Driven Analysis
                  and Feedback systems for Enabling Empirically Guided Software
                  Development, Proceedings of the Thirteenth International Conference on
                  Software Engineering (ICSE 13), Austin, TX, May 13-16, 1991, pp. 288-
                  298.
[USC 1989]       Center for Software Engineering, Modeling Software Defect Introduction.
                 Los Angeles, California 1989.
                http://sunset.usc.edu/COCOMOII/cocomo.html.




                                                                                        68
