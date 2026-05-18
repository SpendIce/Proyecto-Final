# kleer-scrum-estimation-planning-es

> Fuente PDF: `Lecturas y Herramientas/kleer-scrum-estimation-planning-es.pdf`
>
> Markdown operativo generado para busqueda y lectura agentica.
> Metodo: `pdftotext -layout`.
> Paginas: 61.
> Palabras extraidas por `pdftotext`: 12223.
> Palabras finales en este Markdown: 12223.
> Nota de calidad: Texto extraible util para busqueda; revisar el PDF fuente para tablas, figuras o maquetacion.

---

Análisis, Estimación y
                                   Planificación Ágil




                                               v




Web | www.kleer.la
Facebook | facebook.com/kleer.la
Twitter | twitter.com/kleer.la
Análisis, Estimación y Planificación Ágil con Scrum


Índice
Análisis, Estimación y Planificación Ágil.................................................................................................................................................................................... 1
   Desarrollo Evolutivo.....................................................................................................................................................................................................................4
        Minimum Marketable Features.......................................................................................................................................................................................5
        Visual Story Mapping........................................................................................................................................................................................................... 6
   Proceso de Análisis Ágil..............................................................................................................................................................................................................8
        Roles de Usuario.....................................................................................................................................................................................................................8
            Brainstorming de un conjunto inicial de roles.................................................................................................................................................8
            Organización del conjunto inicial de roles...................................................................................................................................................... 11
            Consolidación de roles.............................................................................................................................................................................................. 12
            Refinamiento de roles............................................................................................................................................................................................... 13
   Visual Story Mapping en la Práctica...................................................................................................................................................................................17
        Identificación de los Procesos de Negocio.............................................................................................................................................................. 17
        Identificación de Funcionalidades del Software (Herramientas)................................................................................................................19
        Identificación de MMF y posteriores releases.......................................................................................................................................................27
            MMF (o Release 1) – Objetivo: Comercializar Eventos............................................................................................................................. 27
            Release 2 – Objetivo: Toma de evaluaciones on-line................................................................................................................................. 28
            Release 3 – Objetivo: Pre-Inscripción Individual y Corrección de Exámenes a Desarrollar...................................................29
            Release 4 – Objetivo: Pre-Inscripción Corporativa y Seguimiento de Pagos..................................................................................29
            Release 5 – Objetivo: Logística de Eventos..................................................................................................................................................... 30
            Release 6 – Objetivo: Eventos Tentativos.......................................................................................................................................................30
            Release 7 – Objetivo: Integración con sistemas externos........................................................................................................................ 31
   Historias de Usuario.................................................................................................................................................................................................................. 32
        Componentes de una Historia de Usuario...............................................................................................................................................................33
        Redacción de una Historia de Usuario...................................................................................................................................................................... 33
            Primera Persona.......................................................................................................................................................................................................... 34
            Priorización....................................................................................................................................................................................................................34
            Propósito......................................................................................................................................................................................................................... 34
        INVEST - Características de una Historia de Usuario........................................................................................................................................ 34
            Independientes (I)...................................................................................................................................................................................................... 34
            Negociable (N).............................................................................................................................................................................................................. 34
            Valorable (V)..................................................................................................................................................................................................................35
            Estimable (E)................................................................................................................................................................................................................. 35
            Pequeña (Small)...........................................................................................................................................................................................................35
            Verificable (Testable)................................................................................................................................................................................................ 35
        Criterio de Listo................................................................................................................................................................................................................... 36
        Criterio de Terminado...................................................................................................................................................................................................... 36
   Las Historias de Usuario de Nuestro Sistema................................................................................................................................................................36
   Estimaciones Ágiles................................................................................................................................................................................................................... 46
        Cono de la Incertidumbre................................................................................................................................................................................................46
        Estimaciones en contextos inciertos..........................................................................................................................................................................48
        Escalas de PBIs y Estimaciones.................................................................................................................................................................................... 48
        Métodos Delphi de Predicción y Estimación..........................................................................................................................................................50
        Planning Poker..................................................................................................................................................................................................................... 51
        La Sabiduría de las Multitudes (Wisdom of Crowds)........................................................................................................................................ 51
        Conclusiones sobre estimaciones Ágiles..................................................................................................................................................................52
   Release Plan ..................................................................................................................................................................................................................................53
   Sprint 0.............................................................................................................................................................................................................................................58
   Duración del Proyecto.............................................................................................................................................................................................................. 58
   Release y BackLog Burn Down Chart................................................................................................................................................................................ 60
        Release Burn Down Chart............................................................................................................................................................................................... 60
        BackLog Burn Down Chart............................................................................................................................................................................................. 61
   Costo del Proyecto...................................................................................................................................................................................................................... 62




    Esta obra fue realizada por Martín Alaimo para KLEER, con aportes de Pablo Tortorella y Daniela Casquero y se encuentra
                    bajo una Licencia Creative Commons Atribución-NoComercial-SinDerivadas 3.0 Unported.




                                                                                                                  Página 2
Análisis, Estimación y Planificación Ágil con Scrum


Desarrollo Evolutivo
Supongamos que nos han contratado de una empresa de transporte para construir autobuses
para el traslado de niños desde su casa a la escuela y desde la escuela a su casa.




Luego de analizar las características o funcionalidades que el autobús debe tener, hemos
dividido la problemática en:




Una alternativa para construir el autobús sería dedicar la primera entrega al chasis y los
frenos, la segunda al motor y la carrocería, la tercera a la transmisión, etc., tal como se
muestra a continuación.




                                           Página 3
Análisis, Estimación y Planificación Ágil con Scrum




Sin embargo, si nosotros decidimos construir el vehículo de forma evolutiva e incremental
deberíamos tener una unidad funcionando al final de cada iteración, lo que significa
segmentar el desarrollo de forma transversal a dichas funcionalidades con el fin de proveer
una pequeña porción de cada una en cada entrega, formando un producto utilizable:




                                           Página 4
Análisis, Estimación y Planificación Ágil con Scrum




Partiendo de esta base, vamos a introducir dos conceptos complementarios entre sí:
Minimum Marketable Feature y Visual Story Mapping.

Minimum Marketable Features
Todas las metodologías ágiles coinciden en que un producto debe construirse de forma
evolutiva en pequeñas entregas. De todas formas no es suficiente, como vimos anteriormente,
dividir el producto en tres o cuatro entregas sucesivas, sino que debemos hacerlo de forma
criteriosa para que cada entrega pueda aportar valor suficiente a los usuarios finales. Esos
grupos de características se denominan MMF: Minimum Marketable Features, y pueden
definirse como “el conjunto más pequeño posible de funcionalidad que, por si misma, tiene valor
en el mercado”1



1 “Phased Releases” , James Shore, 2004

                                           Página 5
Análisis, Estimación y Planificación Ágil con Scrum

Visual Story Mapping
Conjugando el Desarrollo Evolutivo, la Priorización del Backlog y el concepto de Minimum
Marketable Feature, Jeff Patton plantea una técnica de Análisis Ágil llamada Mapeo Visual de
Historias o Visual Story Mapping2.
La teoría del Visual Story Mapping comienza en un nivel “humano” identificando los
Objetivos que toda persona persigue y dividiéndolos en Actividades para las cuales deben
utilizarse Herramientas, resultando entonces en una jerarquía de Objetivos → Actividades →
Herramientas, como muestra la siguiente figura:




                             Fig. X: Jerarquía Objetivo → Actividad → Herramienta


El último nivel denominado “herramientas”, puede desagregarse a su vez en diferentes
niveles de confort. Por este mismo principio una persona puede viajar de una ciudad a otra en
un automóvil del año 1965 o en un último modelo siendo que la actividad “llegar de una
ciudad a otra” seguirá cumpliéndose.
Este nivel de confort está dado por 1) la necesidad de negocio (necesito que el viaje se haga en
menos de 30 minutos) y 2) cuánto estemos dispuestos a invertir (precio del auto).
Haciendo una analogía con las organizaciones, esta jerarquía de Objetivo → Actividad →
Herramienta puede traducirse en Proceso de Negocio → Actividad → Software, como se
muestra a continuación:




2 Visual Story Mapping, Jeff Patton, 2009

                                                  Página 6
Análisis, Estimación y Planificación Ágil con Scrum




                        Fig. X: Jerarquía Proceso → Actividad → Software

El Software como herramienta también puede otorgarnos diferentes niveles de confort.
Uniendo entonces el concepto de MMF y de nivel de confort, deberíamos pensar la
construcción del software de forma evolutiva, naciendo desde lo mínimo posible (MMF) e ir
escalando en los niveles de confort de las funcionalidades iteración tras iteración, tratando de
abarcar tanta funcionalidad como sea posible en la extensión del proceso de negocio y no
tanto en profundidad.
Teniendo en cuenta entonces que el software será construido evolutivamente, incrementando
la funcionalidad entrega tras entrega y sumando elementos visuales, surge entonces una
herramienta colaborativa para analizar el alcance del software a ser construido y para
dividirlo en diferentes entregas. Esta técnica visual utiliza elementos físicos como marcadores,
notas autoadhesivas y papel afiche con el propósito de fomentar la colaboración entre las
personas.


Proceso de Análisis Ágil
Para el desarrollo de esta técnica en forma práctica, nos basaremos en el análisis para la
construcción de un sistema de gestión de cursos de capacitación.

Roles de Usuario
Previo al análisis del sistema, es necesario identificar los posibles usuarios que tendrá. Para
esto utilizaremos una técnica colaborativa descripta por Mike Cohn 3 basada en el trabajo de
Constantine & Lockwood4. Esta técnica se realiza en equipo, durante un taller donde el cliente
y tantos desarrolladores como sea posible colaboran en la identificación de los roles. El taller
se compone de cuatro actividades:
    •   Brainstorming de un conjunto inicial de roles
3 Agile Estimating and Planning, Mike Cohn, 2005
4 Software for Use, Constantine & Lockwood, 1999

                                                   Página 7
Análisis, Estimación y Planificación Ágil con Scrum

   •   Organización del conjunto inicial de roles
   •   Consolidación de roles
   •   Refinamiento de roles

Brainstorming de un conjunto inicial de roles
Como se ha mencionado anteriormente, la intención de esta actividad es que sea lo más
colaborativa posible. Tanto el cliente como el Equipo completo deberían participar, aunque
muchas veces será suficiente con la participación de un conjunto representativo del Equipo de
desarrollo.
La reunión se lleva a cabo sobre una mesa lo suficientemente grande para todos los
participantes. Cada uno toma varias fichas de una pila dispuesta en el centro de la mesa y
escribe un rol en la misma. Siendo que esta actividad es un Brainstorming no debe haber
discusión ni censura para cada rol que alguien escribe.
Una opción que suele funcionar muy bien es que los participantes anoten tantos roles como
sea posible en sus fichas, en silencio y sin compartirlos con el resto de las personas.
En nuestro caso, los involucrados identificaron varios roles cada uno, como se muestra en las
fotografías.




                                           Página 8
Análisis, Estimación y Planificación Ágil con Scrum




                                           Página 9
Análisis, Estimación y Planificación Ágil con Scrum


Organización del conjunto inicial de roles
Una vez que el grupo haya terminado de identificar los roles, el próximo paso es organizarlos.
Para esto, los dispondrá sobre la mesa de forma tal que las similitudes queden representadas
de forma visual. Esto se logra solapando levemente aquellos roles que tienen pocas
similitudes, solapando por completo aquellos que son iguales y separando los que no tienen
relación.
Para poder llegar a ese resultado, los participantes deben compartir los roles con el resto del
equipo y describir cada uno de ellos, discutiendo e indagando para poder entender las
similitudes y diferencias. Esto a su vez ayudará a diseminar el conocimiento entre los
integrantes del Equipo. Para nuestro sistema bajo análisis, el resultado de este ejercicio fue
como se muestra en las siguientes fotografías:




                                          Página 10
Análisis, Estimación y Planificación Ágil con Scrum




Consolidación de roles
Luego de haber agrupado los roles, el siguiente paso será consolidar y condensar. Para esto se
comienza por aquellas fichas que tienen el mayor solapamiento, se discuten para entender si
podrían condensarse en un único rol y, en el caso de que sea posible hacerlo, se buscará un
único nombre para que las represente. En nuestro ejemplo, luego de esta dinámica se llegó al
siguiente resultado:




                                          Página 11
Análisis, Estimación y Planificación Ágil con Scrum




Luego de discutir los diferentes roles, se agruparon de forma tal de representar los roles
principales en los niveles superiores, y los sub-roles o especializaciones en los niveles
inferiores, trasladados a su vez, hacia la derecha:




Refinamiento de roles

El cuarto y último paso de la identificación de roles consiste en lograr su refinamiento
mediante la descripción de las siguientes características:



                                           Página 12
Análisis, Estimación y Planificación Ágil con Scrum

   1. Frecuencia de uso del sistema por parte del usuario

   2. Nivel de experiencia del usuario en el dominio del problema

   3. El nivel general de experiencia del usuario con el uso de computadoras

   4. El nivel general de experiencia del usuario con el sistema

   5. Objetivo del usuario con la utilización del sistema

Descripción refinada de los roles:

   •   Comercial
       Uso intensivo del sistema con gran conocimiento del dominio del problema. Posee un
       nivel intermedio de experiencia en la utilización de computadoras y alto nivel de
       experiencia con el uso del sistema en particular. Su responsabilidad será la de proveer
       información sobre los diferentes cursos frente a las consultas de los interesados. Esto
       incluye programa, contenidos, fechas, precios y cantidad de vacantes. También debe
       conocer el estado de completitud de cada curso en el calendario y tener la posibilidad
       de crear nuevos eventos.

          •   Partner Comercial
              Ídem Comercial, con la particularidad que los eventos creados por un Partner
              Comercial se registran como “tentativos” hasta que un Comercial los confirma.

   •   Marketer
       Uso frecuente del sistema con conocimiento limitado del dominio del problema. Posee
       un nivel avanzado de experiencia en la utilización de computadoras y nivel intermedio
       de experiencia con el uso del sistema en particular y alto nivel de experiencia en el uso
       de redes sociales como Twitter y Facebook. Su responsabilidad será la de promover y
       difundir los eventos en internet.

          •   Media Partner
              Uso eventual del sistema con bajo conocimiento del dominio del problema.
              Posee un nivel avanzado de experiencia en la utilización de computadoras y
              nivel bajo de experiencia con el uso del sistema en particular y alto nivel de
              experiencia en su sitio web. Su responsabilidad será la de difundir los eventos
              entre los usuarios de sus sitios web, realizar sorteos y proveer códigos de
              descuento. También debe conocer el estado de su cuenta en el caso de obtener
              beneficios económicos en base a referidos.

   •   Interesado
       Uso infrecuente del sistema sin conocimiento del dominio del problema. Se asumirá un
       nivel avanzado de experiencia en la utilización de computadoras y bajo nivel de

                                           Página 13
Análisis, Estimación y Planificación Ágil con Scrum

       experiencia con el uso del sistema en particular. Su interés será consultar el calendario
       y contenidos de los eventos.

          •   Interesado E-mail
              Ídem interesado, pero su interés es recibir información vía e-mail.

          •   Interesado Redes Sociales
              Ídem interesado, pero su interés es recibir información vía redes sociales.

          •   Interesado en Futuros Eventos
              Un tipo particular de Interesado, cuyo foco está en futuros eventos en una
              ciudad o país en particular.

   •   Persona a Inscribirse
       Uso infrecuente del sistema sin conocimiento del dominio del problema. Se asumirá un
       nivel avanzado de experiencia en la utilización de computadoras y bajo nivel de
       experiencia con el uso del sistema en particular. Su interés es inscribirse a un
       determinado evento.

          •   Empresa con Personas a Inscribir
              Uso infrecuente del sistema sin conocimiento del dominio del problema. Se
              asumirá un nivel intermedio de experiencia en la utilización de computadoras y
              bajo nivel de experiencia con el uso del sistema en particular. Su interés es
              inscribirse a un determinado grupo de personas, todas de una misma empresa a
              un evento en particular.

          •   Beneficiario de Empresa
              Uso infrecuente del sistema sin conocimiento del dominio del problema. Se
              asumirá un nivel avanzado de experiencia en la utilización de computadoras y
              bajo nivel de experiencia con el uso del sistema en particular. Su interés es
              recibir información sobre los eventos a los que fue inscripto por una tercera
              persona.

   •   Deudor
       Uso infrecuente del sistema sin conocimiento del dominio del problema. Se asumirá un
       nivel avanzado de experiencia en la utilización de computadoras y bajo nivel de
       experiencia con el uso del sistema en particular. Su interés es la realización de los
       pagos pendientes para poder asistir al evento al cual está inscripto.

   •   Gestor de Cobranzas
       Uso intensivo del sistema con gran conocimiento del dominio del problema. Posee un
       nivel intermedio de experiencia en la utilización de computadoras y alto nivel de
       experiencia con el uso del sistema en particular. Su responsabilidad será el
       seguimiento de los pagos de los diferentes eventos.

                                           Página 14
Análisis, Estimación y Planificación Ágil con Scrum

   •   Facturador
       Uso intensivo del sistema con gran conocimiento del dominio del problema. Posee un
       nivel intermedio de experiencia en la utilización de computadoras y alto nivel de
       experiencia con el uso del sistema en particular. Su responsabilidad será la realización
       de las facturas a individuos u organizaciones.

   •   Gestor de Logística
       Uso periódico del sistema con gran conocimiento del dominio del problema. Posee un
       nivel intermedio de experiencia en la utilización de computadoras y alto nivel de
       experiencia con el uso del sistema en particular. Su responsabilidad será el
       seguimiento de todo lo que hace a la logística de un determinado evento.

          •   Gestor de Compras
              Uso periódico del sistema con gran conocimiento del dominio del problema.
              Posee un nivel intermedio de experiencia en la utilización de computadoras y
              alto nivel de experiencia con el uso del sistema en particular. Su responsabilidad
              será la realización de todas las compras necesarias para los eventos.

          •   Gestor de Materiales
              Uso periódico del sistema con gran conocimiento del dominio del problema.
              Posee un nivel intermedio de experiencia en la utilización de computadoras y
              alto nivel de experiencia con el uso del sistema en particular. Su responsabilidad
              será la determinación y administración de los materiales y cantidades para cada
              tipo de evento.

   •   Recepcionista
       Uso frecuente del sistema con gran conocimiento del dominio del problema. Posee un
       nivel intermedio de experiencia en la utilización de computadoras y alto nivel de
       experiencia con el uso del sistema en particular. Su responsabilidad será la recepción
       de los asistentes, la toma de asistencia y la autorización de participación a los mismos.

   •   Instructor
       Uso frecuente del sistema con gran conocimiento del dominio del problema. Posee un
       nivel intermedio a avanzado de experiencia en la utilización de computadoras y alto
       nivel de experiencia con el uso del sistema en particular. Su objetivo será la creación de
       tipos de eventos y la provisión de los contenidos, programas, lecturas y material
       asociado a cada uno de ellos. También será su responsabilidad la evaluación de los
       exámenes rendidos por los alumnos.

   •   Alumno
       Uso infrecuente del sistema sin conocimiento del dominio del problema. Se asumirá un
       nivel avanzado de experiencia en la utilización de computadoras y bajo nivel de
       experiencia con el uso del sistema en particular. Está interesado en acceder a los
       contenidos de los diferentes cursos o eventos a los cuales asiste, como así también en
       poder rendir los exámenes que cada curso requiera y obtener los correspondientes

                                           Página 15
Análisis, Estimación y Planificación Ágil con Scrum

       certificados de examen y asistencia.

          •   Alumno Certificable
              Ídem Alumno. Su interés consiste en poder recibir las instrucciones necesarias
              para solicitar la certificación correspondiente. Las certificaciones generalmente
              están relacionadas a la completitud de una serie determinada de cursos o un
              curso en particular.

   •   Ex-Alumno
       Ídem Alumno. Su interés es recibir información sobre nuevos eventos o cursos
       relacionados o correlativos a los cursos o eventos a los que ha aistido.

   •   Responsable de Finanzas
       Uso intensivo del sistema con gran conocimiento del dominio del problema. Posee un
       nivel intermedio de experiencia en la utilización de computadoras y alto nivel de
       experiencia con el uso del sistema en particular. Su responsabilidad será la
       planificación y elaboración de presupuestos para cursos y eventos y el conocimiento de
       los resultados económicos de los mismos.

   •   Responsable de REPs
       Uso intensivo del sistema con gran conocimiento del dominio del problema. Posee un
       nivel intermedio de experiencia en la utilización de computadoras y alto nivel de
       experiencia con el uso del sistema en particular. Su responsabilidad será la publicación
       de los alumnos en los cursos declarados en los sistemas de las organizaciones de las
       cuales la empresa es REP (Registered Education Provider).


Visual Story Mapping en la Práctica
Identificación de los Procesos de Negocio

A continuación se realizará una identificación de procesos de negocio que el sistema deberá
resolver, independientemente de los roles encontrados en el ejercicio anterior.




                                           Página 16
Análisis, Estimación y Planificación Ágil con Scrum




Los procesos de negocio identificados como parte de este taller fueron:

   1. Venta de Evento

   2. Registración a Evento

   3. Cobranza de Evento

   4. Facturación de Evento

   5. Evaluación de Evento

   6. Logística de Evento




                                          Página 17
Análisis, Estimación y Planificación Ágil con Scrum




Identificación de Funcionalidades del Software (Herramientas)
Continuando con la práctica de Visual Story Mapping, el próximo paso consiste en la
identificación de las funcionalidades con las que el sistema deberá contar. Esta actividad la
realizamos teniendo en cuenta todos los roles identificados, efectuando sucesivas “pasadas”
por todos los procesos de negocio y evaluando que cada uno de los roles involucrados en ellos
cuenten con las funcionalidades requeridas para la realización de sus objetivos. Al igual que la
identificación de roles, esta actividad se realiza en forma colaborativa junto al Product Owner
y la mayor cantidad de miembros del equipo posible. En las fotografías siguientes se podrán
identificar los procesos de negocio en color rosa, las actividades en color naranja y las
funcionalidades en color amarillo:




                                           Página 18
Análisis, Estimación y Planificación Ágil con Scrum




                                          Página 19
Análisis, Estimación y Planificación Ágil con Scrum




                                          Página 20
Análisis, Estimación y Planificación Ágil con Scrum




                                          Página 21
Análisis, Estimación y Planificación Ágil con Scrum




Para el sistema en cuestión hemos identificado las siguientes funcionalidades por cada uno de
los procesos de negocio:

   •   Venta de Evento

       ◦ Sugerir Evento

          ▪ Crear evento tentativo

          ▪ Notificar a comercial

          ▪ Consultar agenda de eventos

          ▪ Consultar agenda de instructores

          ▪ Modificar evento tentativo

          ▪ Cancelar evento tentativo

          ▪ Registrar evento tentativo en Google Calendar

       ◦ Crear Evento

          ▪ Ver listado de eventos tentativos

          ▪ Confirmar evento tentativo

          ▪ Crear un evento confirmado

          ▪ Ver listado de eventos confirmados


                                          Página 22
Análisis, Estimación y Planificación Ágil con Scrum

          ▪ Registrar evento confirmado en Google Calendar

          ▪ Notificar a Instructor sobre la confirmación de evento

          ▪ Notificar a Comercial o Partner Comercial sobre la confirmación de evento

          ▪ Crear balance contable del evento en Google Docs

          ▪ Ver listado de eventos tentativos agrupados por Partner Comercial y/o Región

          ▪ Modificar evento confirmado

          ▪ Cancelar evento confirmado

       ◦ Difundir Evento

          ▪ Publicar Evento en

              •   Twitter

              •   Facebook

              •   LinkedIn

          ▪ Listar evento en sitio web

          ▪ Difundir vía Mailchimp

          ▪ Difundir en forma masiva

          ▪ Difundir a leads comerciales

       ◦ Responder Consultas

          ▪ Publicar detalles de evento

          ▪ Generar texto con fechas y valores para “Copy & Paste” en e-mail de respuesta

          ▪ Generar brochure del evento

       ◦ Visualizar Estado de Inscripciones

          ▪ Dashboard de inscripciones a cursos

   •   Registración a Evento

       ◦ Pre-Inscripción a Evento

          ▪ Pre-Inscripción individual

          ▪ Pre-Inscripción de grupo

                                           Página 23
Análisis, Estimación y Planificación Ágil con Scrum

          ▪ Pre-Inscripción corporativa

          ▪ Notificación de Pre-Inscripción y pasos siguientes

       ◦ Confirmación de Inscripción

          ▪ Notificar Inscripción

          ▪ Recordatorio de Evento

          ▪ Notificación al responsable logístico sobre cupo alcanzado

          ▪ Confirmar inscripción sin pago (pago a cuenta)

   •   Cobranza de Evento

       ◦ Seguimiento de Cobros Pendientes

          ▪ Recordatorio de pago pendiente

          ▪ Listado de Pagos Pendientes por evento

       ◦ Pago de Pre-inscripción

          ▪ Obtención de información de facturación

          ▪ Elección de forma de pago

          ▪ Pagar en/por

              •   Efectivo

              •   Cheque

              •   Transferencia Bancaria

              •   PayPal

              •   Mercado Pago

       ◦ Procesar Cobro

          ▪ Registro de Pago

          ▪ Notificación de cobro a Gestor de Finanzas

          ▪ Generación de asiento contable

   •   Facturación de Evento

       ◦ Facturar Evento

                                           Página 24
Análisis, Estimación y Planificación Ágil con Scrum

          ▪ Generar Factura

          ▪ Imprimir Factura

          ▪ Ver listado de Facturas

          ▪ Entregar Factura

          ▪ Asentar Factura en Contabilidad

   •   Evaluación de Evento

       ◦ Responder Preguntas

          ▪ Responder Preguntas Multiple-Choice

          ▪ Responder Preguntas a Desarrollar

          ▪ Finalización de Evaluación (Pantalla)

          ▪ Notificación de Finalización de Evaluación (E-mail)

       ◦ Corregir Evaluación

          ▪ Corrección automática de preguntas multiple-choice

          ▪ Listado de evaluaciones a corregir

          ▪ Corrección manual de preguntas a desarrollar

          ▪ Feedback de corrección

       ◦ Notificar Resultado

          ▪ Notificación del resultado por e-mail

          ▪ Generación de certificado de evaluación aprobada

       ◦ Recuperar Evaluación

          ▪ Listado de recuperatorios pendientes

          ▪ Listado de preguntas erradas

          ▪ Responder preguntas erradas

          ▪ Recálculo automático de resultado basado en preguntas multiple-choice

          ▪ Corrección manual de preguntas a desarrollar

          ▪ Feedback de corrección

                                          Página 25
Análisis, Estimación y Planificación Ágil con Scrum

   •   Logística de Evento

       ◦ Gestionar Maestros de Logística

          ▪ ABM Tipos de Eventos

          ▪ ABM Checklist Template

          ▪ ABM Materiales

       ◦ Generar Checklist

          ▪ Instanciación de Checklist de Evento

       ◦ Actualizar Checklist

          ▪ Actualización de datos de Checklist

          ▪ Notificar a responsable de logística

       ◦ Operar Checklist

          ▪ Listado de eventos con progreso de checklist

          ▪ Detalle de checklist de evento

Identificación de MMF y posteriores releases
Como hemos indicado anteriormente5, la construcción del sistema se realizará en forma
orgánica o evolutiva, naciendo desde el MMP (producto mínimo necesario) y produciendo
incrementos funcionales potencialmente entregables en cada iteración.

MMF (o Release 1) – Objetivo: Comercializar Eventos

   •   Venta de Evento

       ◦ Crear Evento

          ▪ Crear un evento confirmado

          ▪ Ver listado de eventos confirmados

          ▪ Modificar evento confirmado

          ▪ Cancelar evento confirmado

       ◦ Difundir Evento

          ▪ Listar evento en sitio web
5Ver MMP y Visual Story Mapping

                                          Página 26
Análisis, Estimación y Planificación Ágil con Scrum

       ◦ Responder Consultas

          ▪ Publicar detalles de evento

          ▪ Generar texto con fechas y valores para “Copy & Paste” en e-mail de respuesta

       ◦ Visualizar Estado de Inscripciones

          ▪ Dashboard de inscripciones a cursos

   •   Registración a Evento

       ◦ Pre-Inscripción a Evento

          ▪ Pre-Inscripción individual

       ◦ Confirmación de Inscripción

          ▪ Notificar Inscripción

          ▪ Confirmar inscripción sin pago (pago a cuenta)

   •   Cobranza de Evento

       ◦ Seguimiento de Cobros Pendientes

          ▪ Listado de Pagos Pendientes por evento

       ◦ Pago de Pre-inscripción

          ▪ Pagar en/por

              •   Efectivo

              •   Cheque

              •   Transferencia Bancaria

       ◦ Procesar Cobro

          ▪ Registro de Pago

          ▪ Notificación de cobro a Gestor de Finanzas

Release 2 – Objetivo: Toma de evaluaciones on-line

   •   Evaluación de Evento

       ◦ Responder Preguntas

          ▪ Responder Preguntas Multiple-Choice

                                           Página 27
Análisis, Estimación y Planificación Ágil con Scrum

          ▪ Finalización de Evaluación (Pantalla)

          ▪ Notificación de Finalización de Evaluación (E-mail)

       ◦ Corregir Evaluación

          ▪ Corrección automática de preguntas multiple-choice

       ◦ Notificar Resultado

          ▪ Notificación del resultado por e-mail

          ▪ Generación de certificado de evaluación aprobada

       ◦ Recuperar Evaluación

          ▪ Listado de recuperatorios pendientes

          ▪ Listado de preguntas erradas

          ▪ Responder preguntas erradas

          ▪ Recálculo automático de resultado basado en preguntas multiple-choice

Release 3 – Objetivo: Pre-Inscripción Individual y Corrección de Exámenes a Desarrollar

   •   Registración a Evento

       ◦ Pre-Inscripción a Evento

          ▪ Notificación de Pre-Inscripción y pasos siguientes

   •   Evaluación de Evento

       ◦ Responder Preguntas

          ▪ Responder Preguntas a Desarrollar

       ◦ Corregir Evaluación

          ▪ Listado de evaluaciones a corregir

          ▪ Corrección manual de preguntas a desarrollar

          ▪ Feedback de corrección

Release 4 – Objetivo: Pre-Inscripción Corporativa y Seguimiento de Pagos

   •   Registración a Evento

       ◦ Pre-Inscripción a Evento
                                          Página 28
Análisis, Estimación y Planificación Ágil con Scrum

          ▪ Pre-Inscripción corporativa

       ◦ Confirmación de Inscripción

          ▪ Recordatorio de Evento

          ▪ Notificación al responsable logístico sobre cupo alcanzado

   •   Cobranza de Evento

       ◦ Seguimiento de Cobros Pendientes

          ▪ Recordatorio de pago pendiente

       ◦ Pago de Pre-inscripción

          ▪ Obtención de información de facturación

          ▪ Elección de forma de pago

          ▪ Pagar en/por

              •   PayPal

              •   Mercado Pago

Release 5 – Objetivo: Logística de Eventos

   •   Logística de Evento

       ◦ Gestionar Maestros de Logística

          ▪ ABM Tipos de Eventos

          ▪ ABM Checklist Template

          ▪ ABM Materiales

       ◦ Generar Checklist

          ▪ Instanciación de Checklist de Evento

       ◦ Actualizar Checklist

          ▪ Actualización de datos de Checklist

          ▪ Notificar a responsable de logística

       ◦ Operar Checklist

          ▪ Listado de eventos con progreso de checklist

                                          Página 29
Análisis, Estimación y Planificación Ágil con Scrum

          ▪ Detalle de checklist de evento

Release 6 – Objetivo: Eventos Tentativos

   •   Venta de Evento

       ◦ Sugerir Evento

          ▪ Crear evento tentativo

          ▪ Notificar a comercial

          ▪ Consultar agenda de eventos

          ▪ Modificar evento tentativo

          ▪ Cancelar evento tentativo

       ◦ Crear Evento

          ▪ Ver listado de eventos tentativos

          ▪ Confirmar evento tentativo

          ▪ Notificar a Comercial o Partner Comercial sobre la confirmación de evento

          ▪ Notificar a Instructor sobre la confirmación de evento

          ▪ Ver listado de eventos tentativos agrupados por Partner Comercial y/o Región

       ◦ Responder Consultas

          ▪ Generar brochure del evento

   •   Registración a Evento

       ◦ Pre-Inscripción a Evento

          ▪ Pre-Inscripción de grupo

Release 7 – Objetivo: Integración con sistemas externos

   •   Venta de Evento

       ◦ Sugerir Evento


                                           Página 30
Análisis, Estimación y Planificación Ágil con Scrum

          ▪ Consultar agenda de instructores

          ▪ Registrar evento tentativo en Google Calendar

       ◦ Crear Evento

          ▪ Registrar evento confirmado en Google Calendar

          ▪ Crear balance contable del evento en Google Docs

       ◦ Difundir Evento

          ▪ Publicar Evento en

              •   Twitter

              •   Facebook

              •   LinkedIn

          ▪ Difundir vía Mailchimp

          ▪ Difundir en forma masiva

          ▪ Difundir a leads comerciales

   •   Cobranza de Evento

       ◦ Procesar Cobro

          ▪ Generación de asiento contable

   •   Facturación de Evento

       ◦ Facturar Evento

          ▪ Generar Factura

          ▪ Imprimir Factura

          ▪ Ver listado de Facturas

          ▪ Entregar Factura

          ▪ Asentar Factura en Contabilidad

Historias de Usuario
                              Valor: Software funcionando por sobre la documentación extensiva
                             Principio: El método más eficiente y eficaz de transmitir información


                                             Página 31
Análisis, Estimación y Planificación Ágil con Scrum

                                                                hacia y dentro de un equipo de desarrollo
                                                                es mediante la comunicación cara a cara.
                                                                                     Agile Manifesto – 2001


Las Historias de Usuario surgieron en eXtremme Programming (XP) como una respuesta a
una situación habitual en los proyectos de desarrollo do software: los clientes o especialistas
de negocio se comunican con los equipos de desarrollo a través de extensos documentos
conocidos como especificaciones funcionales. A su vez, las especificaciones funcionales son la
documentación de supuestos y están sujetas a interpretaciones, lo que causa malos
entendidos y que finalmente el software construido no se corresponda con la realidad
esperada.
Una de las principales razones por las cuales la utilización de especificaciones detalladas
como medio de comunicación no conduce a resultados satisfactorios es porque solo cubre una
porción mínima (7%) del espectro de la comunicación humana: el contenido. Según Albert
Mehrabian, la comunicación humana se compone de tres partes6:
    •   En un 7%: El contenido (las palabras, lo dicho)
    •   En un 38%: El tono de la voz
    •   En un 55%: Las expresiones faciales
Por esto se concluye que para tener una comunicación sólida, completa, es necesario el
contacto cara-a-cara entre los interlocutores. En un esfuerzo orientado a que esas
conversaciones existan, podemos decir que las Historias de Usuario son especificaciones
funcionales que invitan a la conversación para que el detalle sea consecuencia de esta última y
no un remplazo.

Componentes de una Historia de Usuario

Una Historia de Usuario se compone de 3 elementos, también conocidos como “las tres Cs”7 de
las Historias de Usuario:

    1. Card (Ficha) – Toda historia de usuario debe poder describirse en una ficha de papel
       pequeña. Si una Historia de Usuario no puede describirse en ese tamaño, es una señal
       de que estamos traspasando las fronteras y comunicando demasiada información que
       debería compartirse cara a cara.

    2. Conversación – Toda historia de usuario debe tener una conversación con el Product
       Owner. Una comunicación cara a cara que intercambia no solo información sino
       también pensamientos, opiniones y sentimientos.

    3. Confirmación – Toda historia de usuario debe estar lo suficientemente explicada para
       que el equipo de desarrollo sepa qué es lo que debe construir y qué es lo que el Product
6 “Silent messages: Implicit communication of emotions and attitudes.”, Albert Mehrabian, 1981
7 “Essential XP: Card, Conversation, Confirmation”, Ron Jeffries, 2001

                                                   Página 32
Análisis, Estimación y Planificación Ágil con Scrum

        Owner espera. Esto se conoce también como Criterios de Aceptación.

Redacción de una Historia de Usuario
Mike Cohn sugiere una determinada forma de redactar Historias de Usuario bajo el siguiente
formato:
                         Como (rol) Necesito (funcionalidad) Para (beneficio)8
Ejemplo: Como estudiante necesito comprar un pase de estacionamiento para poder
estacionar mi vehículo en la universidad.
Los beneficios de este tipo e redacción son, principalmente:

Primera Persona
La redacción en primera persona de la Historia de Usuario invita a quien la lee a ponerse en el
lugar del usuario.

Priorización
Tener esta estructura para redactar la Historia de Usuario ayuda al Product Owner a priorizar.
Si el Product Backlog es un conjunto de ítems como “Permitir crear un evento tentativo”,
“Confirmar un evento tentativo”, “Notificar al responsable de logística”, “Ver el estado de
inscripciones”, etc. el Product Owner debe trabajar más para comprender cuál es la
funcionalidad, quien se beneficia y cuál es el valor de la misma.

Propósito
Conocer el propósito de una funcionalidad permite al equipo de desarrollo plantear
alternativas que cumplan con el mismo propósito en el caso de que el costo de la
funcionalidad solicitada sea alto o su construcción no sea viable.

INVEST - Características de una Historia de Usuario

Se recomienda que toda Historia de Usuario cumpla con 6 características que podemos
recordar bajo la regla mnemotécnica “INVEST”9:

Independientes (I)
Las Historias de Usuario deben ser independientes de forma tal que no se superpongan en
funcionalidades y que puedan planificarse y desarrollarse en cualquier orden.
Muchas veces esta característica no puede cumplirse para el 100% de las Historias. El objetivo
que debemos perseguir es preguntarnos y cuestionarnos en cada Historia de Usuario si hemos
hecho todo lo posible para que ésta sea independiente del resto.



8 “Advantages of the “As a user, I want” user story template”, Mike Cohn, 2008
9 “INVEST in Good Stories, and SMART Tasks”, Bill Wake, 2003

                                                   Página 33
Análisis, Estimación y Planificación Ágil con Scrum

Negociable (N)
Una buena Historia de Usuario es Negociable. No es un contrato explícito por el cual se debe
entregar todo-o-nada. Por el contrario, el alcance de las Historias (sus criterios de aceptación)
podrían ser variables: pueden incrementarse o eliminarse con el correr del desarrollo y en
función del feedback del usuario y/o la performance del Equipo. En el caso de que uno o
varios criterios de aceptación se eliminen de una Historia de Usuario, estos se transformarán
en una o varias Historias de Usuario nuevas.
Esta es la herramienta que el Product Owner y el Equipo tienen para negociar el alcance de
cada Sprint.

Valorable (V)
Una Historia de Usuario debe ser Valorable por el Product Owner. Los Desarrolladores
pueden tener actividades técnicas como parte del BackLog, pero para que puedan ser
consideradas una Historia de Usuario, deben ser enmarcadas de forma tal que el Product
Owner las considere importantes, caso contrario, no deberían formar parte del BackLog.
En general, esta característica representa un desafío a la hora de dividir Historias de Usuario.
Bill Wake propone pensar en una Historia de Usuario como si fuese una torta de múltiples
capas, por ejemplo: una capa de persistencia, una capa de negocio, una capa de presentación,
etc. Cuando dividamos esa Historia de Usuario, lo que vamos a estar sirviendo es una parte de
esa “torta” y el objetivo debería ser darle al Product Owner la esencia de la “torta” completa, y
la mejor manera de hacerlo es cortando una rodaja vertical de esta “torta” a través de todas
las capas. Los Desarrolladores tenemos una inclinación especial de trabajar en una capa a la
vez hasta completarla, pero una capa de persistencia de datos completa y terminada tiene
muy poco o ningún valor para el Product Owner si no hay una capa de negocio y de
presentación.

Estimable (E)
Una Historia de Usuario debería ser estimable. Mike Cohn 10, identifica tres razones principales por
las cuales una Historia de Usuario no podría estimarse:
    • La Historia de Usuario es demasiado grande. En este caso la solución sería dividir la
        Historia de Usuario en historias más pequeñas que sean estimables.
    • Falta de conocimiento funcional. En este caso la Historia de Usuario vuelve al Product
        Owner para bajar en detalle la Historia o inclusive (y recomendable) tener una conversación
        con el Equipo de Desarrollo.
    • Falta de conocimiento técnico. Muchas veces el Equipo de Desarrollo no tiene el
        conocimiento técnico suficiente para realizar la estimación. En estos casos el Equipo de
        Desarrollo puede dividir la historia en 1) un time-box conocido como “spike” que le permita
        investigar la solución y proveer una estimación más certera y 2) la funcionalidad a
        desarrollar como parte de la Historia en si misma.

Pequeña (Small)
Toda Historia de Usuario debe ser lo suficientemente pequeña de forma tal que permita ser estimada
por el Equipo de Desarrollo. Algunos Equipos fijan el tamaño de una Historia de usuario como no
10 “User Stories Applied”, Mike Cohn, 2003

                                             Página 34
Análisis, Estimación y Planificación Ágil con Scrum

más de dos semanas de una persona. Si bien no es una medida explícita, tener entre 4 y 6 Historias
de Usuario por Sprint es una buena señal de tamaño.
Las descripciones de las Historias de Usuario también deberían ser pequeñas, y escribirlas en fichas
pequeñas ayuda a que eso suceda.

Verificable (Testable)
Una buena Historia de Usuario es Verificable. Se espera que el Product Owner no solo pueda
describir la funcionalidad que necesita, sino que también logre verificarla (probarla). Algunos
Equipos acostumbran solicitar los criterios de aceptación antes de desarrollar la Historia de Usuario.
Si el Product Owner no sabe cómo verificar una Historia de Usuario o no puede enumerar los
criterios de aceptación, esto podría ser una señal de que la Historia en cuestión no está siendo lo
suficientemente clara.

Criterio de Listo

También conocido como “READY Criteria”, es el conjunto de características que una Historia
de Usuario debe cumplir para que el Equipo de Desarrollo pueda comprometerse a su entrega,
es decir, incluirla en un Sprint Backlog. Un típico criterio de “Listo” podría ser:

   •   La Historia de Usuario debe ser INVEST

   •   Todos sus pre-requisitos están resueltos (ej: dependencias con otros Equipos)

Criterio de Terminado

También conocido como “DONE Criteria”, es el conjunto de características que una Historia de
Usuario debe cumplir para que el equipo de desarrollo pueda determinar si ha terminado de
trabajar en ella. Un típico criterio de “Terminado” podría ser:

   •   Todos los criterios de aceptación funcionan correctamente

   •   Todos los archivos fuentes están en el repositorio de código fuente y el build se ejecutó
       exitosamente

   •   En el caso de Product Owners muy exigentes: El Product Owner dio su visto bueno de
       la funcionalidad construida antes de llegar a la Review Meeting.


Las Historias de Usuario de Nuestro Sistema
A continuación redactamos las Historias de Usuario que comprenden el Product Backlog de
nuestro producto. Dada la naturaleza evolutiva del alcance de un proyecto ágil, las Historias
de Usuario de mayor prioridad estarán más detalladas que las Historias de Usuario de menor
prioridad, las cuales inclusive podrían considerarse EPICS (agrupaciones de varias Historias
de usuario):

                                              Página 35
Análisis, Estimación y Planificación Ágil con Scrum

Release 1 - Comercializar Eventos
Prioridad Como ...        Necesito ...           Para ...       Criterios de Aceptación
1           Comercial     Crear un evento        Hacer el       - Debe tener Nombre, Fecha,
                          confirmado             seguimiento    Descripción, Destinatarios,
                                                 del mismo      Programa, Instructor, Lugar,
                                                                Ciudad, País, Capacidad,
                                                                Precios y Promociones: SEB
                                                                (Super Early Bird), EB (Early
                                                                Bird), dto. en % para 2
                                                                personas y dto. en % para 3 o
                                                                más personas.
                                                                - Las promociones son
                                                                opcionales.
                                                                - Las fechas de SEB y EB
                                                                deben ser anteriores a la
                                                                fecha del evento
                                                                - Por defecto SEB=30 días
                                                                antes, EB=10 días antes,
                                                                2personas=-10%, 3+
                                                                personas=-15%.
                                                                - Un evento puede ser público
                                                                o privado
2           Comercial     Ver listado de         No             - Mostrar Nombre, Ciudad y
                          eventos                superponer     País
                          confirmados            eventos        - Muestra solo los futuros
                                                                - Ordenado por fecha
                                                                ascendente
3           Comercial     Modificar evento       Corregir       - Permite modificar todos los
                          confirmado             cualquier      campos.
                                                 error o re
                                                 programarlo
4           Comercial     Cancelar evento        Dejar de       - Desaparece del listado de
                          confirmado             seguirlo       eventos confirmados.
5           Comercial     Listar los eventos     Que los       - Solo se listan los eventos
                          en un sitio web        interesados   públicos
                                                 puedan verlos - Listado por fechas (a futuro)
                                                               - Agrupados por Ciudad
6           Comercial     Publicar los detalles Que los       - Accesible desde el listado de
                          de cada evento        interesados   eventos
                                                puedan verlos - Muestra los detalles de cada
                                                              evento: Nombre, Fecha,
                                                              Descripción, Destinatarios,
                                                              Programa, Instructor, Lugar,
                                                              Ciudad, País, Precios y


                                            Página 36
Análisis, Estimación y Planificación Ágil con Scrum

                                                                 Promociones
7           Comercial     Generar un texto     Pegarlo en los - Debe generarlo agrupando
                          con fechas y valores e-mail de      por ciudad, cursos, fechas y
                                               respuesta      precios de cada uno.
8           Comercial     Dashboard de           Conocer el      - Muestra los eventos con
                          inscripciones a        estado de       colores: Rojo, Naranja,
                          cursos                 completitud     Amarillo y Verde. Los
                                                 de cada curso   criterios son:
                                                                 → Un evento debe estar al
                                                                 50% al menos 15 días antes
                                                                 → Un evento debe estar al
                                                                 75% al menos una semana
                                                                 antes
                                                                 → Un evento debe estar al
                                                                 100% dos días antes
                                                                 - La varianza sobre esos
                                                                 números alteran los colores:
                                                                 → Menos del 50% (Rojo)
                                                                 → Del 50% al 75% (Naranja)
                                                                 → Del 75% al 90% (Amarillo)
                                                                 → Del 90% al 100% (Verde)
9           Interesado    Pre-Inscribirme        Iniciar la    Debe solicitar Nombre*,
                                                 reserva de mi Apellido*, Teléfono de
                                                 vacante       Contacto*, Email*,
                                                               Empresa/Carrera, Rol y
                                                               Solicitar confirmación de que
                                                               el asistente llevará notebook*
                                                               si el curso lo requiere.
                                                               * = obligatorio, el resto,
                                                               opcional.
10          Comercial     Ser notificado de      Poder           El email debe ser enviado a
                          cada inscripción       reaccionar en   una dirección de correo
                                                 tiempo real     configurable indicando los
                                                 frente a cada   datos de contacto de la
                                                 una             persona que realizó la
                                                                 inscripción.
11          Comercial     Confirmar la         Financiar         Un pre-inscripto puede
                          inscripción sin pago ciertas           conviertirse en inscripto sin
                          (pago a cuenta)      vacantes          haber realizado el pago.
12          Comercial     Conocer los Pagos      Realizar el     Listar los eventos con pagos
                          Pendientes por         seguimiento     pendientes y un detalle de las
                          evento                 de los pagos    pre-inscripciones pendientes
                                                                 de pago por cada evento.
13          Interesado    Pagar en efectivo      Confirmar mi Una vez que un interesado se


                                            Página 37
Análisis, Estimación y Planificación Ágil con Scrum

                                                 vacante       pre-inscribe debe
                                                               proporcionarle los tados para
                                                               poder pagar en efectivo.
14          Interesado    Pagar con Cheque       Confirmar mi Una vez que un interesado se
                                                 vacante      pre-inscribe debe
                                                              proporcionarle los tados para
                                                              poder pagar con cheque.
15          Interesado    Pagar por              Confirmar mi Una vez que un interesado se
                          Transferencia          vacante      pre-inscribe debe
                          Bancaria                            proporcionarle los tados para
                                                              poder pagar por transferencia
                                                              bancaria.
16          Comercial     Registrar los Pagos Realizar el      Una pre-inscripción puede
                                              seguimiento      convertirse en inscripción
                                              de los pagos     registrando el pago realizado
                                                               (fecha, monto y forma de
                                                               pago).
17          Gestor de     Ser notificado del Realizar el       Cada vez que una pre-
            Cobranzas     cobro de un evento seguimiento       inscripción se convierte en
                                             de los pagos      inscripción, se debe enviar un
                                                               e-mail a una casilla
                                                               configurable.
Release 2 - Toma de evaluaciones on-line
Prioridad Como ...        Necesito ...           Para ...      Criterios de Aceptación
18          Alumno        Responder           Rendir el        - Si el evento requiere un
                          Preguntas Multiple- examen final     examen final, el alumno
                          Choice                               debería poder responder las
                                                               preguntas on-line (solo
                                                               multiple-choice)
                                                               - Se deben poder administrar
                                                               exámenes, preguntas y sus
                                                               posibles respuestas.
                                                               - Se asigna un tipo de examen
                                                               a los alumnos seleccionados
                                                               de un determinado evento.
19          Alumno        Un aviso de            Para saber    Se avisará en pantalla
                          Finalización de        que he
                          Evaluación             finalizado
20          Instructor    Que se realice la   Reducir mi       - Todo examen debe tener un
                          corrección          carga de         puntaje mínimo requerido
                          automática de       trabajo post-    (expresado en porcentaje)
                          preguntas multiple- evento           - Siendo preguntas multiple-
                          choice                               choice, las correctas suman


                                            Página 38
Análisis, Estimación y Planificación Ágil con Scrum

                                                                  un punto, las incorrectas no
                                                                  suman ni restan.
21          Alumno        Recibir una             Para conocer - Se notifica por e-mail al
                          notificación del        el resultado alumno tan pronto finalice el
                          resultado por e-        de mi examen examen.
                          mail
22          Alumno        Generar mi              Presentarlo     - El alumno podrá bajar un
                          certificado de          donde sea       PDF son la constancia de su
                          evaluación              necesario       aprobación de examen
                          aprobada
23          Instructor    Conocer los             Hacer           - Para un determinado evento,
                          recuperatorios          seguimiento     se listarán los exámenes y
                          pendientes              con los         recuperatorios pendientes.
                                                  alumnos
24          Alumno        Conocer las             Con el fin de   - Se listarán las preguntas
                          preguntas erradas       saber dónde     correctas con su explicación y
                                                  he fallado mi   las preguntas erradas, sin
                                                  evaluación      explicación.
25          Alumno        Recuperar las           Con el fin de   - Solo se realizará la respuesta
                          preguntas erradas       aprobar el      de las preguntas erradas
                                                  examen          - Al finalizar el recuperatorio,
                                                                  aplican las mismas acciones
                                                                  que para un examen estándar:
                                                                  aviso de finalización,
                                                                  corrección automática y aviso
                                                                  de resultado
Release 3 - Pre-Inscripción Individual y Corrección de Exámenes a Desarrollar
Prioridad Como ...        Necesito ...            Para ...        Criterios de Aceptación
26          Interesado    Recibir un aviso de     Poder           - Al inscribirse, el alumno
                          Pre-Inscripción y       confirmar mi    recibe por e-mail un
                          pasos siguientes        pre-            instructivo sobre los pasos a
                                                  inscripción     seguir para efectivizar su
                                                                  inscripción.
27          Alumno        Responder               Poder rendir    - Ciertas preguntas deberán
                          Preguntas a             el examen       solicitar un texto libre como
                          Desarrollar                             respuesta.
28          Instructor    Listado de              Poder           - Se deberán listar las
                          evaluaciones a          corregir        evaluaciones con preguntas a
                          corregir                evaluaciones    desarrollar que estén
                                                                  pendientes de corrección
29          Instructor    Corrección manual       Poder calificar - Las respuestas de texto libre
                          de preguntas a          a los alumnos deberán ser corregidas
                          desarrollar                             manualmente por el

                                             Página 39
Análisis, Estimación y Planificación Ágil con Scrum

                                                                  instructor
30          Instructor    Feedback de            Poder            - Al finalizar la corrección, el
                          corrección             recomendar o     instructor podrá dar feedback
                                                 sugerir          de la evaluación por medio de
                                                 acciones a los   un campo de texto libre.
                                                 alumnos
Release 4 - Pre-Inscripción Corporativa y Seguimiento de Pagos
Prioridad Como ...        Necesito ...           Para ...         Criterios de Aceptación
31          Empresa       Realizar una Pre-      Inscribir        Al inscribir se deberá solicitar
                          Inscripción            varios           responsable (mismos campos
                          corporativa            empleados de     que pre-inscripción) y
                                                 una sola vez     cantidad de inscriptos (hasta
                                                                  10).
                                                                  - Luego, cada inscripto deberá
                                                                  tener Nombre, Apellido, E-
                                                                  mail y Número de Contacto.
32          Interesado    Recibir un             Alertarme        - Enviado por e-mail al e-mail
                          Recordatorio de        sobre la         de contacto de cada inscripto
                          Evento                 proximidad       (copiando a los responsables
                                                 del evento e     de inscripciones corporativas
                                                 informarme       una sola vez).
                                                 sobre los        - Recordar horario, lugar y
                                                 pormenores       requisitos. Solicitar aviso en
                                                                  el caso de que el evento tenga
                                                                  almuerzo y el interesado
                                                                  tenga restricciones
                                                                  alimenticias.
                                                                  - Se debe enviar dos días
                                                                  antes del evento.
33          Responsable Ser notificado sobre A definir            A definir
            Logístico   cupo alcanzado
34          Interesado    Ser notificado sobre Poder              - Se enviará un recordatorio
                          el pago pendiente    confirmar mi       de pago pendiente 48hs luego
                                               vacante a          de la pre-inscripción,
                                               tiempo             avisando que la misma vence
                                                                  en 24hs hábiles.
35          Administrati Obtener la              Poder emitir     - Con cada Pre-Inscripción se
            vo           información de          las facturas     solicitará información de
                         facturación             correctament     facturación: Razón Social,
                                                 e                Domicilio Fiscal, CUIT,
                                                                  Situación frente al IVA.
36          Interesado    Pagar por PayPal       Confirmar mi - El sistema deberá proveer
                                                 Vacante      un link de pago de PayPal.


                                            Página 40
Análisis, Estimación y Planificación Ágil con Scrum

37          Interesado    Pagar por              Confirmar mi - El sistema deberá proveer
                          MercadoPago            Vacante      un link de pago de
                                                              MercadoPago.
Release 5 - Logística de Eventos
Prioridad Como ...        Necesito ...           Para ...        Criterios de Aceptación
38          Responsable Gestionar            Crear               - ABM de Tipos de Evento.
            de Logística diferentes Tipos de checklists de       Solo Nombre y Descripción.
                         Eventos             cada tipo
39          Responsable Gestionar           Que cada      - Uno por cada tipo de evento
            de Logística diferentes modelos evento pueda
                         de Checklist       instancias su
                                            checklist en
                                            base a un
                                            modelo
                                            prearmado
40          Responsable Gestionar                Saber qué se - Un listado de materiales por
            de Logística diferentes listados     debe comprar cada tipo de evento.
                         de Materiales           por cada
                                                 evento
41          Responsable Hacer el                 Que el mismo    - Poder marcar como
            de Logística seguimiento de          se realice de   “cumplido” los hitos de un
                         cada Checklist de       forma           checklist y dejar anotaciones
                         Evento                  eficiente       (opcionales).
42          Responsable Modificar los datos Tener                - se podrán agregar o eliminar
            de Logística de un Checklist    flexibilidad a       hitos de un checklist de
                                            la hora de           evento particular.
                                            gesitonar un
                                            evento
43          Responsable Ser notificado al        Para estar al - Se enviará un e-mail al
            de Logística modificar un            tanto de las  responsable de logística con
                         checklist               modificacione vcada modificación de
                                                 s             checklist (no incluye al
                                                               avance del checklist de
                                                               evento).
44          Responsable Conocer los eventos Para asegurar - Listar los eventos y el
            de Logística y el progreso de   el correcto   porcentaje de avance de cada
                         checklist de cada  seguimiento checklist
                         uno                de los
                                            checklists
45          Responsable Detalle de checklist Para asegurar       - Detallar el estado de cada
            de Logística de evento           el correcto         checklist con hitos cumplidos
                                             seguimiento         y pendientes y fechas
                                             de los              esperadas por cada uno.


                                            Página 41
Análisis, Estimación y Planificación Ágil con Scrum

                                                 checklists
Release 6 - Eventos Tentativos
Prioridad Como ...        Necesito ...           Para ...        Criterios de Aceptación
46          Partner       Crear evento           Proponer la     A definir
            Comercial     tentativo              realización del
                                                 mismo
47          Comercial     Ser notificado de un Realizar las      A definir
                          nuevo evento         acciones
                          tentativo            necesarias
                                               para la
                                               confirmación
                                               del mismo
48          Partner       Consultar agenda       Conocer las    A definir
            Comercial     de eventos             fechas y
                                                 disponibilidad
                                                 para crear
                                                 eventos
                                                 tentativos
49          Partner       Modificar evento       Realizar       A definir
            Comercial     tentativo              correcciones o
                                                 reprogramar
                                                 eventos
                                                 tentativos
50          Partner       Cancelar evento        Dejar de        A definir
            Comercial     tentativo              seguirlo
51          Comercial     Ver listado de         Tener un        A definir
                          eventos tentativos     panorama de
                                                 la
                                                 planificación
                                                 futura de
                                                 eventos
52          Comercial     Confirmar evento       Transformarl A definir
                          tentativo              o en un
                                                 evento
                                                 agendado y
                                                 publicarlo.
53          Partner       Ser notificado         Comenzar a     A definir
            Comercial /   sobre la               comercializarl
            Comercial /   confirmación de        o
            Instructor    evento
54          Comercial     Ver listado de         Tener un        A definir
                          eventos tentativos     panorama de
                          agrupados por          la

                                            Página 42
Análisis, Estimación y Planificación Ágil con Scrum

                          Partner Comercial       planificación
                          y/o Región              futura de
                                                  eventos
55          Interesado    Obtener un              Evaluar la      A definir
                          brochure de cada        información
                          evento                  con mayor
                                                  detalle
56          Interesado    Pre-Inscribir un        Asistir varios A definir
                          grupo de personas       a un mismo
                                                  evento sin ser
                                                  una
                                                  organización
Release 7 – Integración con sistemas Externos
Prioridad Como ...        Necesito ...            Para ...        Criterios de Aceptación
57          Partner       Consultar agenda        Conocer su     A definir
            Comercial     de instructores         disponibilidad
58          Comercial     Registrar evento    Publicar su         A definir
                          tentativo en Google existencia a
                          Calendar            todos los
                                              suscriptos a
                                              dicho
                                              calendario
59          Comercial     Registrar evento        Publicar su     A definir
                          confirmado en           existencia a
                          Google Calendar         todos los
                                                  suscriptos a
                                                  dicho
                                                  calendario
60          Responsable Crear balance      Comenzar a             A definir
            Financiero contable del evento hacer el
                        en Google Docs     seguimiento
                                           financiero de
                                           un evento
61          Comercial     Publicar Evento en Dar a conocer A definir
                          Twitter, Facebook & su existencia
                          LinkedIn
62          Comercial     Difundir vía            Dar a conocer A definir
                          Mailchimp               su existencia
63          Comercial     Difundir en forma       Dar a conocer A definir
                          masiva                  su existencia
64          Comercial     Difundir a leads        Dar a conocer A definir
                          comerciales             su existencia


                                             Página 43
Análisis, Estimación y Planificación Ágil con Scrum

65          Administrati La generación de    Registrar el      A definir
            vo           asiento contable de cobro con
                         Cobro               menor
                                             esfuerzo
66          Administrati Generar e Imprimir Reducir mi         A definir
            vo           Factura            esfuerzo y
                                            probabilidad
                                            de error
67          Administrati Ver listado de         Conocer las    A definir
            vo           Facturas               facturas
                                                generadas
68          Administrati Entregar Factura       Realizar el    A definir
            vo                                  cobro de un
                                                evento
69          Administrati Asentar Factura en     Reducir mi     A definir
            vo           Contabilidad           esfuerzo y
                                                probabilidad
                                                de error




                                          Página 44
Análisis, Estimación y Planificación Ágil con Scrum


Estimaciones Ágiles
Cono de la Incertidumbre
En gestión de proyectos, el cono de la incertidumbre describe la evolución de la incertidumbre
durante la ejecución de un proyecto. Al comienzo, poco es conocido sobre el producto y el
resultado del trabajo, por tanto las estimaciones están sujetas a una gran incertidumbre. A
medida que avanzamos en el proyecto obtenemos mayor conocimiento sobre el entorno, la
necesidad de negocio, el producto y el proyecto mismo. Esto causa que la incertidumbre
tienda a reducirse progresivamente hasta desaparecer, esto ocurre generalmente hacia el
final del proyecto: no se alcanza una incertidumbre del 0% sino hasta haber finalizado.
Muchos ambientes cambian tan lentamente que la incertidumbre reinante puede ser
considerada constante (evolución estática) durante la duración de un proyecto típico. En estos
contextos la gestión tradicional de proyectos hace hincapié en lograr un entendimiento total
mediante el análisis y la planificación detallada antes de comenzar a trabajar. De esta manera
los riesgos son reducidos a un nivel en el que pueden ser gestionados cómodamente. En estas
situaciones, el nivel de incertidumbre decrece rápidamente al comienzo y se mantiene
prácticamente constante (y bajo) durante la ejecución del proyecto.




                                          Página 45
Análisis, Estimación y Planificación Ágil con Scrum




            Fig. 2: Cono de la Incertidumbre en un contexto estable.

El contexto del software, por el contrario, es un contexto altamente volátil donde hay muchas
fuerzas externas actuando para incrementar el nivel de incertidumbre, como lo son los
cambios producidos en el contexto de negocio, los cambios tecnológicos y aquellos surgidos
por la mera existencia del producto construido que acontecen durante la ejecución del
proyecto. Debido a esta razón, se requiere trabajar activa y continuamente en reducir el nivel
de incertidumbre.
Investigaciones han demostrado que en la industria del software, el nivel de incertidumbre al
comienzo de un proyecto es del +/- 400% 11, esta incertidumbre tiende a decrementarse
durante la evolución del proyecto, pero sin garantías de ello.




            Fig. 3: Cono de la Incertidumbre en desarrollo de software.


11 McConnell, S (2006) Software Estimation: Demystifying the Black Art, Microsoft Press.

                                                    Página 46
Análisis, Estimación y Planificación Ágil con Scrum

Estimaciones en contextos inciertos
Como es de esperar según los gráficos previos, proveer una estimación precisa en etapas
tempranas de un proyecto tiene como consecuencia un compromiso poco probable de ser
cumplido.
A medida que adquiramos conocimiento, nuestras estimaciones se harán cada vez más
precisas. El problema aparece a la hora de estimar cuando muchas de las decisiones se toman
en base a supuestos que probablemente no sucedan o no sean los correctos.
“La propia palabra “estimación” deja en claro que no calculamos un valor exacto,
determinístico. De hecho, toda estimación tiene supuestos, y estos supuestos suman
incertidumbres.”12
Como consecuencia, las metodologías ágiles proponen comenzar a trabajar en un proyecto sin
la necesidad de tener una estimación precisa basada en supuestos y siendo conscientes de que
la estimación inicial es de un orden de magnitud probable, para poder ganar experiencia
rápidamente y así estimar con mayor certeza prescindiendo de supuestos.
Para mitigar el riesgo de proveer estimaciones incorrectas, en metodologías ágiles se opta por
reducir la precisión de las estimaciones en función de cuánto conocimiento se tiene sobre el
esfuerzo que se requiere estimar. De esta manera, los “requerimientos” y sus “estimaciones”
se categorizan en diferentes niveles de precisión.

Escalas de PBIs y Estimaciones
Podemos enumerar la siguiente escala de PBIs y estimaciones:
    1. Alto Nivel: EPIC (bloque funcional) estimada en Tamaño (XS, S, M, L, XL)
    2. Nivel Medio: Historia de Usuario (funcionalidad) estimada en Puntos de Historia
       (Sucesión de Fibonacci13)
    3. Bajo Nivel: tareas o actividades estimadas en horas, preferiblemente menos de un día.
Al comenzar el proyecto, nuestro Product Backlog se compone de bloques funcionales que
podemos estimar según sus tamaños:
    •   XS – Muy Pequeño
    •   S – Pequeño
    •   M – Medio
    •   L – Grande
    •   XL – Muy Grande
Esto nos permitirá tener una primera aproximación a la problemática de negocio y a las
características del producto que se desea construir. Conociendo las prioridades de dichos
bloques funcionales, se toman los de mayor prioridad y se descomponen en funcionalidades
más específicas, logrando de esa manera PBIs de menor nivel, llamados Historias de Usuario
o User Stories. A las Historias de Usuario las estimaremos utilizando la sucesión Fibonacci:

12 Fontela, Carlos (2007) Estimaciones y Estadística, Blog CyS Ingeniería de Software
13 http://es.wikipedia.org/wiki/Sucesi%C3%B3n_de_Fibonacci

                                                    Página 47
Análisis, Estimación y Planificación Ágil con Scrum

    •   0, 1, 2, 3, 5, 8, 13, 21, 40, 100 14
Para estimar las Historias de Usuario utilizamos una técnica comparativa llamada Estimación
Relativa. Esto significa asignar uno de los números de la serie de Fibonacci a cada una de las
Historias de Usuario. De esta manera, aquellas historias que tengan el número 2 requerirán
aproximadamente el doble de esfuerzo que las que lleven el número 1, aquellas que lleven el
número 3 requerirán aproximadamente el triple de esfuerzo de las que lleven el número 1,
una vez y media el esfuerzo de las que lleven el número 2, etc.
Finalmente llegamos al nivel más bajo de estimación: la estimación en horas. Solo aplica a las
tareas o actividades de las Historias de Usuario que han sido seleccionadas para formar parte
de un determinado Sprint. En la reunión de planificación de dicho Sprint, estas Historias de
Usuario son divididas por el Equipo en tareas o actividades y a su vez, las tareas o actividades,
estimadas en horas. Lo importante es que la estimación en horas solo se realiza para un las
actividades de un determinado Sprint.
Autores como Jeff Sutherland 15 expresan no estar de acuerdo con estimar a este bajo nivel,
mientras otros como Mike Cohn 16 promueven su utilización. Esta situación da origen a dos
modelos de planificación de Sprint: la planificación basada en velocidad (velocity-based
planning) donde el Equipo se compromete a realizar tantos User Stories de modo que sumen
una estimación en Puntos de Historia igual a la velocidad del Equipo, por un lado, y la
planificación basada en compromisos (commitment-based planning) donde sin importar la
velocidad, el Equipo revalúa las Historias de Usuario y se compromete en función de la
estimación de cada una de ellas, por el otro. En este último caso, las Historias de Usuario
involucradas deberían sumar una cantidad de Puntos de Historia aproximada a la Velocidad
del Equipo. Dice Mike Cohn con respecto a la utilización de la Velocidad del Equipo como
herramienta de planificación:
“Supongamos que un equipo de básquetbol está en la mitad de su temporada. Han anotado un
promedio de 98 puntos por cada partido de los 41 partidos jugados hasta el momento. Sería
conveniente para ellos decir "Nosotros anotaremos un promedio de 98 puntos por partido por el
resto de la temporada." Pero no deberían nunca decir antes de cualquier partido "Nuestro
promedio es de 98 puntos, por lo que se anotarán 98 puntos esta noche." Es por eso que afirmo
que la velocidad es un predictor útil para el largo plazo, pero no lo es para el corto plazo. ”17

Métodos Delphi de Predicción y Estimación
El Método Delphi es una técnica creada por la Corporación RAND 18 hacia fines de la década
de los 40's para la elaboración de pronósticos y predicciones sobre el impacto de la tecnología
en la Guerra Fría.
Su objetivo es lograr un consenso basado en la discusión entre expertos. Este método se basa

14 Con una leve deformación ya que se interrumpe la sucesión en el número 21 y se agregan luego los números 40 y
   100.
15 Jeff Sutherland (2010),“Story Points: Why are they better than hours?”,
   http://scrum.jeffsutherland.com/2010/04/story-points-why-are-they-better-than.html
16 Mike Cohn (2007), “Why I Don't use Story Points for Sprint Planning”, http://blog.mountaingoatsoftware.com
17 Ibid.
18 La Corporación RAND (Research And Development) es un laboratorio de ideas (think tank) norteamericano
   formado, en un primer momento, para ofrecer investigación y análisis a las fuerzas armadas norteamericanas.
   (fuente: Wikipedia)

                                                    Página 48
Análisis, Estimación y Planificación Ágil con Scrum

en la elaboración de un cuestionario que ha de ser contestado por una serie de expertos. Una
vez recibida la información, se vuelve a realizar otro cuestionario basado en el anterior para
ser contestado nuevamente.
Al final, el responsable del estudio elaborará sus conclusiones a partir de la explotación
estadística de los datos obtenidos en las iteraciones anteriores.
El Método Delphi se basa en:
    •    El anonimato de los participantes
    •    La repetición y retroalimentación controlada
    •    La respuesta del grupo en forma estadística
Basados en el Método Delphi, Barry Boehm y John Farquhar elaboraron en 1970 la variante
conocida desde entonces como Wideband Delphi. Se trata de una técnica basada en la
obtención de consensos para la estimación de esfuerzos, llamada “wideband” porque a
diferencia del conocido método Delphi, esta técnica requiere de un mayor grado de
interacción y discusión entre los participantes. Wideband Delphi fue popularizado en 1981
por Boehm en su libro “Software Engineering Economics” donde presenta los siguientes pasos
para su ejecución:
    1. Un coordinador presenta a cada experto una especificación y un formulario de
       estimación.
    2. El coordinador convoca a una reunión de grupo en la que los expertos debaten temas
       de estimación.
    3. Los expertos llenan los formularios de forma anónima.
    4. El coordinador prepara y distribuye un resumen de las estimaciones.
    5. El coordinador convoca a una reunión de grupo, centrándose específicamente en
       aquellas estimaciones donde los expertos varían ampliamente.
    6. Los expertos completan los formularios una vez más de forma anónima, y los pasos 4 a
       6 son repetidos para tantas rondas como sea necesario.

Planning Poker
James Greening presentó en su paper en 2002 llamado “Planning Poker (o cómo evitar análisis
parálisis en la planificación de liberaciones)”19 donde se basa en el método Wideband Delphi
para realizar la estimación de requerimientos (o User Stories) de forma colaborativa en un
Equipo. La técnica consiste en que cada integrante del Equipo posee en sus manos una baraja
de cartas con los números correspondientes a la sucesión de Fibonacci20 y se siguen los
siguientes pasos:
    1. El responsable del negocio presenta una historia de usuario para ser estimada.
    2. Todos los participantes proceden a realizar su estimación en forma secreta, sin
       influenciar al resto del Equipo, poniendo su carta elegida boca abajo sobre la mesa.
    3. Una vez que todos los integrantes han estimado, se dan vuelta las cartas y se discuten
19 http://renaissancesoftware.net/files/articles/PlanningPoker-v1.1.pdf
20 Se puede repasar en la sección de Escalas de PBIs y Estimaciones

                                                      Página 49
Análisis, Estimación y Planificación Ágil con Scrum

        principalmente los extremos.
    4. Al finalizar la discusión se levantan las cartas y se vuelve a estimar, esta vez con mayor
       información que la que se tenía previamente.
    5. Las rondas siguen hasta que se logra consenso en el Equipo y luego se continúa desde
       el punto número uno con una nueva historia de usuario.
Este método fue popularizado en 2005 por Mike Cohn en su libro “Agile Estimating and
Planning”.

La Sabiduría de las Multitudes (Wisdom of Crowds)
James Surowieki explica en su libro “La Sabiduría de las Multitudes” (2004): “Normalmente
solemos favorecer la opinión de los expertos, pues consideramos que sólo una persona con
experiencia y conocimientos suficientes es capaz de emitir juicios correctos en un área o materia
en particular. Sin embargo, hay evidencias de que las decisiones tomadas colectivamente por un
grupo de personas suelen ser más atinadas que las decisiones tomadas sobre la base del
conocimiento de un experto”.
La tesis detrás de la Sabiduría de las Multitudes es simple: dadas las circunstancias
requeridas, un grupo de personas puede tomar una decisión más acertada que la mejor de las
decisiones de la mayoría (si no todos) los integrantes del grupo individualmente.
Para que esto pueda suceder, Surowieki recomienda en su tesis las siguientes condiciones:
    1. Diversidad de opiniones: cada persona debería tener información particular aún si es
       sólo una interpretación excéntrica de los hechos conocidos. El grupo debe tener
       diversidad de perfiles.
    2. Independencia: las opiniones de los participantes no deberían estar influenciadas por
       las opiniones de los que los rodean, con el objetivo de evitar el Pensamiento de
       Grupo21.
    3. Agregación: El grupo debería tener la capacidad de sumar las opiniones individuales y
       no simplemente votar por la mejor opción.

Conclusiones sobre estimaciones Ágiles
Muchas teorías y enfoques convergen en las siguientes características sobre estimaciones en
proyectos ágiles:
    1. No tiene sentido presentar estimaciones certeras al comienzo de un proyecto ya que su
       probabilidad de ocurrencia es extremadamente baja por el alto nivel de incertidumbre.
    2. Intentar bajar dicha incertidumbre mediante el análisis puede llevarnos al “Análisis
       Parálisis”22. Para evitar esto debemos estimar a alto nivel con un elevado grado de
       probabilidad, actuar rápidamente, aprender de nuestras acciones y refinar las
       estimaciones frecuentemente. Este enfoque se conoce también como “Rolling Wave
       Planning” o “Elaboración Progresiva”.
    3. La mejor estimación es la que provee el Equipo de trabajo. Esta estimación será mucho
21 http://es.wikipedia.org/wiki/Pensamiento_de_grupo
22 http://en.wikipedia.org/wiki/Analysis_paralysis

                                                  Página 50
Análisis, Estimación y Planificación Ágil con Scrum

       más realista que la estimación provista por un experto ajeno al Equipo.




                                          Página 51
Análisis, Estimación y Planificación Ágil con Scrum


Release Plan
A continuación se presentan las Historias de Usuario estimadas por el Equipo de Desarrollo,
utilizando Planning Poker con Fibonacci y estimando una velocidad de Iteración de 15 puntos
de historia con una duración de dos semanas:
Release 1 - Comercializar Eventos
Prioridad Como ...        Necesito ...                  Para ...                Estimación
Sprint 1 – Velocidad: 15 puntos
1           Comercial     Crear un evento               Hacer el seguimiento    3
                          confirmado                    del mismo
2           Comercial     Ver listado de eventos        No superponer eventos 2
                          confirmados
3           Comercial     Modificar evento              Corregir cualquier     2
                          confirmado                    error o re programarlo
4           Comercial     Cancelar evento               Dejar de seguirlo       1
                          confirmado
5           Comercial     Listar los eventos en un Que los interesados          2
                          sitio web                puedan verlos
6           Comercial     Publicar los detalles de      Que los interesados     5
                          cada evento                   puedan verlos
Sprint 2 – Velocidad: 15 puntos
7           Comercial     Generar un texto con          Pegarlo en los e-mail de 5
                          fechas y valores              respuesta
9           Interesado    Pre-Inscribirme               Iniciar la reserva de mi 2
                                                        vacante
8           Comercial     Dashboard de                  Conocer el estado de    8
                          inscripciones a cursos        completitud de cada
                                                        curso
Sprint 3 – Velocidad: 14 puntos
10          Comercial     Ser notificado de cada        Poder reaccionar en     2
                          inscripción                   tiempo real frente a
                                                        cada una
11          Comercial     Confirmar la inscripción Financiar ciertas            2
                          sin pago (pago a cuenta) vacantes
12          Comercial     Conocer los Pagos             Realizar el seguimiento 3
                          Pendientes por evento         de los pagos
13          Interesado    Pagar en efectivo             Confirmar mi vacante    1
14          Interesado    Pagar con Cheque              Confirmar mi vacante    1


                                            Página 52
Análisis, Estimación y Planificación Ágil con Scrum

15          Interesado    Pagar por Transferencia Confirmar mi vacante          1
                          Bancaria
16          Comercial     Registrar los Pagos          Realizar el seguimiento 2
                                                       de los pagos
17          Gestor de     Ser notificado del cobro Realizar el seguimiento 2
            Cobranzas     de un evento             de los pagos
Release 2 - Toma de evaluaciones on-line
Prioridad Como ...        Necesito ...                 Para ...                 Estimación
Sprint 4 – Velocidad: 15 puntos
18          Alumno        Responder Preguntas          Rendir el examen final   8
                          Multiple-Choice
19          Alumno        Un aviso de Finalización Para saber que he            2
                          de Evaluación            finalizado
20          Instructor    Que se realice la            Reducir mi carga de      5
                          corrección automática        trabajo post-evento
                          de preguntas multiple-
                          choice
Sprint 5 – Velocidad: 15 puntos
21          Alumno        Recibir una notificación Para conocer el              2
                          del resultado por e-mail resultado de mi
                                                   examen
22          Alumno        Generar mi certificado Presentarlo donde sea          5
                          de evaluación aprobada necesario
23          Instructor    Conocer los                  Hacer seguimiento con 3
                          recuperatorios               los alumnos
                          pendientes
25          Alumno        Recuperar las preguntas Con el fin de aprobar el 5
                          erradas                 examen
Sprint 6 – Velocidad: 15 puntos
24          Alumno        Conocer las preguntas        Con el fin de saber      5
                          erradas                      dónde he fallado mi
                                                       evaluación
Release 3 - Pre-Inscripción Individual y Corrección de Exámenes a Desarrollar
Prioridad Como ...        Necesito ...                 Para ...                 Estimación
26          Interesado    Recibir un aviso de Pre-     Poder confirmar mi       2
                          Inscripción y pasos          pre-inscripción
                          siguientes
27          Alumno        Responder Preguntas a        Poder rendir el examen 8
                          Desarrollar


                                           Página 53
Análisis, Estimación y Planificación Ágil con Scrum

Sprint 7 – Velocidad: 16 puntos
28          Instructor    Listado de evaluaciones     Poder corregir           3
                          a corregir                  evaluaciones
29          Instructor    Corrección manual de        Poder calificar a los    3
                          preguntas a desarrollar     alumnos
30          Instructor    Feedback de corrección      Poder recomendar o       2
                                                      sugerir acciones a los
                                                      alumnos
Release 4 - Pre-Inscripción Corporativa y Seguimiento de Pagos
Prioridad Como ...        Necesito ...                Para ...                 Estimación
31          Empresa       Realizar una Pre-           Inscribir varios      8
                          Inscripción corporativa     empleados de una sola
                                                      vez
Sprint 8 – Velocidad: 15 puntos
32          Interesado    Recibir un Recordatorio Alertarme sobre la     3
                          de Evento               proximidad del evento
                                                  e informarme sobre los
                                                  pormenores
33          Responsable Ser notificado sobre          A definir                2
            Logístico   cupo alcanzado
34          Interesado    Ser notificado sobre el     Poder confirmar mi       3
                          pago pendiente              vacante a tiempo
35          Administrati Obtener la información       Poder emitir las       2
            vo           de facturación               facturas correctamente
36          Interesado    Pagar por PayPal            Confirmar mi Vacante     2
37          Interesado    Pagar por MercadoPago       Confirmar mi Vacante     3
Release 5 - Logística de Eventos
Prioridad Como ...        Necesito ...                Para ...                 Estimación
Sprint 9 – Velocidad: 15 puntos
38          Responsable Gestionar diferentes          Crear checklists de      2
            de Logística Tipos de Eventos             cada tipo
39          Responsable Gestionar diferentes          Que cada evento pueda 8
            de Logística modelos de Checklist         instancias su checklist
                                                      en base a un modelo
                                                      prearmado
40          Responsable Gestionar diferentes          Saber qué se debe        5
            de Logística listados de Materiales       comprar por cada
                                                      evento
Sprint 10 – Velocidad: 15 puntos


                                          Página 54
Análisis, Estimación y Planificación Ágil con Scrum

41          Responsable Hacer el seguimiento de Que el mismo se                  5
            de Logística cada Checklist de Evento realice de forma
                                                  eficiente
42          Responsable Modificar los datos de un Tener flexibilidad a la        8
            de Logística Checklist                hora de gesitonar un
                                                  evento
43          Responsable Ser notificado al               Para estar al tanto de   2
            de Logística modificar un checklist         las modificaciones
Sprint 11 – Velocidad: 15 puntos
44          Responsable Conocer los eventos y el Para asegurar el                3
            de Logística progreso de checklist de correcto seguimiento
                         cada uno                 de los checklists
45          Responsable Detalle de checklist de         Para asegurar el         3
            de Logística evento                         correcto seguimiento
                                                        de los checklists
Release 6 - Eventos Tentativos
Prioridad Como ...        Necesito ...                  Para ...                 Estimación
46          Partner       Crear evento tentativo        Proponer la realización 3
            Comercial                                   del mismo
47          Comercial     Ser notificado de un          Realizar las acciones    2
                          nuevo evento tentativo        necesarias para la
                                                        confirmación del
                                                        mismo
48          Partner       Consultar agenda de           Conocer las fechas y     3
            Comercial     eventos                       disponibilidad para
                                                        crear eventos
                                                        tentativos
49          Partner       Modificar evento              Realizar correcciones o 1
            Comercial     tentativo                     reprogramar eventos
                                                        tentativos
Sprint 12 – Velocidad: 16 puntos
50          Partner       Cancelar evento               Dejar de seguirlo        2
            Comercial     tentativo
51          Comercial     Ver listado de eventos        Tener un panorama de 2
                          tentativos                    la planificación futura
                                                        de eventos
52          Comercial     Confirmar evento              Transformarlo en un      2
                          tentativo                     evento agendado y
                                                        publicarlo.
53          Partner     Ser notificado sobre la         Comenzar a               2
            Comercial / confirmación de evento          comercializarlo

                                            Página 55
Análisis, Estimación y Planificación Ágil con Scrum

            Comercial /
            Instructor
54          Comercial     Ver listado de eventos   Tener un panorama de 3
                          tentativos agrupados por la planificación futura
                          Partner Comercial y/o    de eventos
                          Región
55          Interesado    Obtener un brochure de         Evaluar la información 5
                          cada evento                    con mayor detalle
Sprint 13 – Velocidad: 16 puntos
56          Interesado    Pre-Inscribir un grupo de Asistir varios a un           8
                          personas                  mismo evento sin ser
                                                    una organización
Release 7 – Integración con sistemas Externos
Prioridad Como ...        Necesito ...                   Para ...                 Estimación
57          Partner       Consultar agenda de            Conocer su               3
            Comercial     instructores                   disponibilidad
58          Comercial     Registrar evento               Publicar su existencia a 5
                          tentativo en Google            todos los suscriptos a
                          Calendar                       dicho calendario
Sprint 14 – Velocidad: 15 puntos
59          Comercial     Registrar evento               Publicar su existencia a 5
                          confirmado en Google           todos los suscriptos a
                          Calendar                       dicho calendario
60          Responsable Crear balance contable           Comenzar a hacer el    5
            Financiero del evento en Google              seguimiento financiero
                        Docs                             de un evento
61          Comercial     Publicar Evento en             Dar a conocer su         5
                          Twitter, Facebook &            existencia
                          LinkedIn
Sprint 15 – Velocidad: 15 puntos
62          Comercial     Difundir vía Mailchimp         Dar a conocer su         5
                                                         existencia
63          Comercial     Difundir en forma masiva Dar a conocer su               5
                                                   existencia
64          Comercial     Difundir a leads               Dar a conocer su         5
                          comerciales                    existencia
Sprint 16 – Velocidad: 15 puntos
65          Administrati La gneración de asiento         Registrar el cobro con   8
            vo           contable de Cobro               menor esfuerzo



                                             Página 56
Análisis, Estimación y Planificación Ágil con Scrum

66          Administrati Generar e Imprimir             Reducir mi esfuerzo y    5
            vo           Factura                        probabilidad de error
67          Administrati Ver listado de Facturas        Conocer las facturas     3
            vo                                          generadas
Sprint 17 – Velocidad: 11 puntos
68          Administrati Entregar Factura               Realizar el cobro de un 3
            vo                                          evento
69          Administrati Asentar Factura en             Reducir mi esfuerzo y    8
            vo           Contabilidad                   probabilidad de error



Sprint 0
El Sprint 0 (cero) es una aproximación que muchos autores utilizan para realizar todas
aquellas tareas necesarias para hacer el setup de un proyecto de desarrollo. Esto incluye pero
no se limita únicamente a configurar los entornos de desarrollo, realizar el release plan,
diseñar la arquitectura de la aplicación a alto nivel, configurar el repositorio de código fuente,
etc. En nuestro caso, el Sprint 0 tendrá una duración de 2 semanas, aunque podría ser
diferente a los Sprints de desarrollo.



Duración del Proyecto
Duración Total: 18 Sprints = 36 Semanas = 9 meses
Etapa                                         Duración           Desde            Hasta
Sprint 0                                      2 semanas          3-Oct-2011       14-Oct-2011
Release 1 - Comercializar Eventos
Sprint 1                                      2 semanas          17-Oct-2011      28-Oct-2011
Sprint 2                                      2 semanas          31-Oct-2011      11-Nov-2011
Sprint 3                                      2 semanas          14-Nov-2011      25-Nov-2011
Release 2 - Toma de evaluaciones on-line
Sprint 4                                      2 semanas          28-Nov-2011      9-Dic-2011
Sprint 5                                      2 semanas          12-Dic-2011      23-Dic-2011
Sprint 6                                      2 semanas          26-Dic-2011      6-Ene-2012
Release 3 - Pre-Inscripción Individual y Corrección de Exámenes a Desarrollar
Sprint 7                                      2 semanas          9-Ene-2012       20-Ene-2012
Release 4 - Pre-Inscripción Corporativa y Seguimiento de Pagos
Sprint 8                                      2 semanas          23-Ene-2012      3-Feb-2012



                                            Página 57
Análisis, Estimación y Planificación Ágil con Scrum

Release 5 - Logística de Eventos
Sprint 9                                    2 semanas   6-Feb-2012    17-Feb-2012
Sprint 10                                   2 semanas   20-Feb-2012   2-Mar-2012
Sprint 11                                   2 semanas   5-Mar-2012    16-mar-2012
Release 6 - Eventos Tentativos
Sprint 12                                   2 semanas   19-Mar-2012   30-mar-2012
Sprint 13                                   2 semanas   2-Abr-2012    13-Abr-2012
Release 7 – Integración con sistemas Externos
Sprint 14                                   2 semanas   16-Abr-2012   27-Abr-2012
Sprint 15                                   2 semanas   30-Abr-2012   11-May-2012
Sprint 16                                   2 semanas   14-May-2012   25-May-2012
Sprint 17                                   2 semanas   28-May-2012   8-Jun-2012




                                          Página 58
Análisis, Estimación y Planificación Ágil con Scrum


Release y BackLog Burn Down Chart
Para poder realizar el seguimiento del proyecto sprint tras sprint utilizaremos el Release Burn
Down Chart, que representa el avance esperado vs. el avance real y el BackLog burndown
chart que representa la evolución del alcance a través del tiempo. Ambos gráficos representan
lo siguiente al inicio del proyecto:

Release Burn Down Chart




BackLog Burn Down Chart




                                          Página 59
Análisis, Estimación y Planificación Ágil con Scrum


Costo del Proyecto
Para la realización de este proyecto se ha conformado un equipo de trabajo con las siguientes
características:
Perfil                                                            Precio por Hora
Product Owner                                                     $250.-/hr.
ScrumMaster                                                       $200.-/hr.
Desarrolladores (3)                                               $170 c/u = $510.-/hr.
Total Equipo                                                      $960.-/hr.
Concepto                                                          Sub-Total Proyecto
9 meses = 1440 horas del equipo                                                  $1.382.400.-
5 notebooks 4GB RAM c/u                                                              $20.000.-
Servidor de Testing/UAT ($450.-/mes)                                                  $4.050.-
Servidor de Integración Continua ($450.-/mes)                                         $4.050.-
Servidor de Repositorio de Código Fuente ($450.-/mes)                                 $4.050.-
Alquiler de Oficina Mensual ($4000.-/mes)                                            $36.000.-
Conectividad (Internet) ($380.-/mes)                                                  $3.420.-
Comunicaciones (Celular) ($580.-/mes)                                                 $5.220.-
Fondo de Contingencia (10%)                                                         $145.919.-
                                            Total del Proyecto:                 $1.605.109.-




                                          Página 60
Análisis, Estimación y Planificación Ágil con Scrum



                                                                                   Acerca de Kleer
Somos una empresa de capacitación y coaching ágil donde creemos en una forma de trabajo
clara, centrada en las personas y orientada hacia las necesidades específicas de cada contexto.
Nuestras premisas son:
   •    Mantenerlo simple. Las metodologías y prácticas de trabajo en las que confiamos
        aportan claridad a los proyectos. Los proyectos claros se vuelven más previsibles y con
        menor incidencia de errores evitables.
   •    Las personas son todo. No acompañamos proyectos sino equipos y personas. Nuestro
        propósito es transmitirles nuestro conocimiento y experiencia para que logren
        resultados de los que se sientan orgullosos.
   •    Cada contexto es un mundo. Estudiamos las características de cada proyecto u
        organización para entender cuáles son las prácticas y metodologías que mejor
        responden a sus necesidades y objetivos de negocio.


Contacto: entrenamos@kleer.la | http://www.kleer.la


                                                                                 Acerca del Autor
Martín Alaimo
Certified Scrum Coach (CSC) y entrenador en Metodologías Ágiles, con más de 15 años de
experiencia en proyectos de desarrollo de software. Martín acompaña a diferentes empresas,
muchas de primera línea, en su camino de adopción de Scrum y Agilidad. También dicta
entrenamientos sobre Scrum, tanto desde una perspectiva de gestión y liderazgo como de un
punto de vista de ingeniería y desarrollo de software.
Comenzó su carrera en la industria de desarrollo de software hace más de 15 años como
desarrollador de software centrado siempre en implementaciones web, convirtiéndose con el
tiempo en gerente de proyecto de Java / .NET / RoR y tecnologías de SAP, con varios años de
experiencia liderando proyectos de software en organizaciones multinacionales.
Estudió Analista de Sistemas Informáticos y se especializó en Gestión de Proyectos,
principalmente Agiles, obteniendo certificaciones como PMP (PMI), PMI-ACP, Certified
ScrumMaster, Certified Scrum Professional y Certified Scrum Coach.
Blog:http://www.martinalaimo.com/es/blog/
Contacto: martin.alaimo@kleer.la




 Esta obra fue realizada por Martín Alaimo para KLEER, con aportes de Pablo Tortorella y Daniela Casquero y se encuentra
                 bajo una Licencia Creative Commons Atribución-NoComercial-SinDerivadas 3.0 Unported.



                                                      Página 61
