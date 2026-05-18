# Correo de Facultad de Ingeniería del Ejército - Proyecto Agentes IA

> Fuente PDF: `Correo de Facultad de Ingeniería del Ejército - Proyecto Agentes IA.pdf`
>
> Markdown operativo generado para busqueda y lectura agentica.
> Metodo: `pdftotext -layout`.
> Paginas: 3.
> Palabras extraidas por `pdftotext`: 933.
> Palabras finales en este Markdown: 933.
> Nota de calidad: Transcripcion operativa generada desde PDF con texto embebido; revisar el PDF fuente para encabezados, tablas o formato original.

---

4/25/26, 9:20 AM                                                             Correo de Facultad de Ingeniería del Ejército - Proyecto Agentes IA

                                                                                                                                                     Becerra Mas Roca Ignacio <ibecerra@fie.undef.edu.ar>



  Proyecto Agentes IA
  CR (R) Ing César Daniel Cicerchia <cdcicerchia@fie.undef.edu.ar>                                                                                                      20 de marzo de 2
  Para: Goñe Juan Ignacio <jgone@fie.undef.edu.ar>, Becerra Mas Roca Ignacio <ibecerra@fie.undef.edu.ar>
  Cc: "CR(R) López Gabriel Vicente" <glopez@fie.undef.edu.ar>, Tozzi Adrián <atozzi@fie.undef.edu.ar>, Calvache Daniel <dcalvache@fie.undef.edu.ar>, Vegega Cinthia <cvegega@fie.undef.e
  Daniel <dbritez@fie.undef.edu.ar>, Sebastián Ernesto Moreira <moreira@fie.undef.edu.ar>, TP SCD Vera Batista Fernando <verabatista@fie.undef.edu.ar>

   Juan / Ignacio:

   Vamos a iniciar el trabajo del proyecto centenario (P100) para la Secr Ext.

   Ignacio: vas iniciar con Juan la definición de una arquitectura multiagente, segura, fiable e interoperable, apta para los 5 agentes.
   Juan: vas a trabajar con el Agente 1.

   Uno de los primeros desafíos es determinar las tecnologías factibles (open source, seguras y fiables).
   También, el repositorio seguro de código y resto de los artefactos de software.

   No se preocupen por toda la información que les voy a mandar, porque van a tener una gran experiencia de cómo se trabaja en el mundo real. El análisis de la información y sele
   que es de su interés es parte del aprendizaje.

   Los docentes del proyecto están en copia, además del profesor Proy Prom y Sint, para que asuman su rol desde las asignaturas respectivas, para guía, resolución de problemas
   evaluar el trabajo técnico, acorde a la siguiente previsión:




   Quiénes son (por favor, los docentes citar a los alumnos para orientarlos y dar su orientación técnica):

          Primario: Ing Cinthia Vegega - Lic Britez
          Secundario: Ing Carlos Maceira García Coni.
          Apoyo: Mg Adrián Tozzi - Lic Daniel Calvache.

   Ignacio: El Agente 2 todavía no se ha definido en cuanto a prioridad. Cuando lo determine con la Secr Ext, te pasaré información.
   Juan: relacionado con el Agente 1. Te paso la actividad en base al plan de proyecto, que se extenderá todo el año.




   Para empezar a entender el alcance, te paso la historia de usuario ID 1, que relevé en la Secr Ext (faltan definir los Criterios de Aceptación que quedarán):
          ID         Fecha         Historia de Usuario                                        Criterios de Aceptación ( a definir con el usuario)                                                           Prioridad     E
                                                                   • Dado que...
                                  Como [rol], quiero [acción]
            0                                                      • Cuando...                                                                                                                              Alta/Media
                                  para [beneficio].
                                                                   • Entonces...
                                                                   Conectividad y Origen:
                                                                   El sistema debe conectarse exitosamente a las APIs oficiales (o herramientas de scraping autorizadas) de Instagram, Facebook y
                                                                   LinkedIn.
                                                                   La extracción debe incluir publicaciones de los últimos [X] días o meses (definir el periodo temporal).
                                                                   Integridad del "Copy" y Metadatos:
                                 Como Coordinadora de              Para cada publicación, el sistema debe extraer el texto completo (Copy) sin truncar.
                                 Extensión, quiero que un          Se deben capturar obligatoriamente los siguientes metadatos asociados: Fecha de publicación, Red Social de origen, URL del post y
                                 usuario designado pueda           Tipo de contenido (imagen, video, carrusel).
                                 extraer de manera automática      Formato de Salida (Similitud con ANEXO 2):
                                 datos de diferentes redes         Los datos deben volcarse automáticamente en una planilla (Excel o Google Sheets) que respete exactamente el orden de columnas del
                                                                                                                                                                                                                         3m
                      17/03/2026 sociales
                                          (Instagram, Facebook,    ANEXO 2.
            1                                                                                                                                                                                                  Alta
                                 LinkedIn) y almacenarlos en       La columna "Copy" debe estar limpia de caracteres especiales extraños que rompan el formato de la celda.
                                 una planilla similar al ANEXO 2   Automatización y Frecuencia:
                                 (columna Copy con metadatos)      La extracción debe ejecutarse mediante un solo clic o de forma programada (ej. cada lunes a las 8:00 AM) sin intervención manual en la
                                 para reducir los tiempos          recolección.
                                 recolección de RRSS para su       El sistema debe notificar si alguna de las cuentas de red social perdió la conexión o requiere re-autenticación.
                                 análisis posterior de impacto.    Rendimiento (Criterio de Tiempo - T):
                                                                   El proceso de extracción total para las tres redes no debe superar los [X] minutos para garantizar la reducción de tiempos prometida.




   A fin de formular tu proyecto, tenés que tener en cuenta la estrategia de desarrollo planteada en el proyecto, que transcribo a continuación (tenés el documento completo):




https://mail.google.com/mail/u/1/?ik=d850e3f622&view=pt&search=all&permmsgid=msg-f:1860229529797803553&simpl=msg-f:1860229529797803553                                                                                   1/3
4/25/26, 9:20 AM                                                      Correo de Facultad de Ingeniería del Ejército - Proyecto Agentes IA




   El TP Vera Batista les dará apoyo de infraestructura.

   Seguimos en contacto (también en los pasillos).




   CR(R) César Daniel Cicerchia
   Oficial Ingeniero Militar - Ingeniero Informático
   Director de Carrera - Ingeniería en Informática
   Secretaría Académica


   Tel: (011) 4779-3355                Cel: +54 9 11 4870-8130
   Av. Cabildo 15 – CABA
   www.fie.undef.edu.ar



   El lun, 9 mar 2026 a las 16:23, CR (R) Ing César Daniel Cicerchia (<cdcicerchia@fie.undef.edu.ar>) escribió:
     Juan, te mando el proyecto para que veas el alcance y objetivos.

     A modo preparatorio, podés ir viendo las tecnologías open source para desarrollar agentes inteligentes.

     Vamos conversando.




     CR(R) César Daniel Cicerchia
     Oficial Ingeniero Militar - Ingeniero Informático
     Director de Carrera - Ingeniería en Informática
     Secretaría Académica


     Tel: (011) 4779-3355                Cel: +54 9 11 4870-8130
     Av. Cabildo 15 – CABA
     www.fie.undef.edu.ar

https://mail.google.com/mail/u/1/?ik=d850e3f622&view=pt&search=all&permmsgid=msg-f:1860229529797803553&simpl=msg-f:1860229529797803553      2/3
4/25/26, 9:20 AM                                     Correo de Facultad de Ingeniería del Ejército - Proyecto Agentes IA

     [El texto citado está oculto]




https://mail.google.com/mail/u/1/?ik=d850e3f622&view=pt&search=all&permmsgid=msg-f:1860229529797803553&simpl=msg-f:1860229529797803553   3/3
