# Procesos y Agentes SEU - FIE con Backlog tecnico (Jira)

Fuente original vigente: `Contenido/bible/Procesos y Agentes SEU - FIE con Backlog técnico (Jira).pdf`.

Nota operativa: este Markdown fue resincronizado desde la version vigente del PDF de 16 paginas. La fuente actual se concentra en el Agente 1, Extension Bot: problema, usuarios, modelo de negocio, requisitos, interacciones, metodologia, cronograma y diagramas/casos de uso. El PDF queda como evidencia original; este archivo queda como working source textual para busqueda, diff y actualizacion documental.

---

## Indice

- Proyecto
- Problema
- Descripcion de los Usuarios
- Modelo de Negocio
- Requisitos del sistema
  - Funcionales
  - No Funcionales
- Interaccion con Demas Agentes
- Metodologia de desarrollo de software
- Cronograma
- Diagrama de Gantt
- Diagrama de Clases
- Diagrama de Casos de Uso
  - Bloque 1: Generacion de Contenido
  - Bloque 2: Human in the Loop
  - Bloque 3: Difusion de Contenido
  - Bloque 4: Soporte
  - Lista de Actores para los Casos de Uso
- Diagrama de Componentes
- Diagrama de Despliegue
- Diagrama de Estados
- Diagrama de Actividades
- Diagrama de Secuencia

## Proyecto

Proyecto CENTENARIO: Sistema de Agentes Inteligentes para Extension Universitaria.
Particularmente el agente "Extension Bot".

## Problema

La Secretaria de Extension Universitaria se encuentra con problemas de comunicacion y coordinacion con otras areas que se suman a la existencia de tareas repetitivas y tediosas que podrian ser automatizadas, como el envio de certificados de inscripcion, asistencia y aprobacion, difusion de anuncios, etc.

Es por esto que surgio la necesidad de un sistema que automatice estas tareas y con el cual se pueda comunicar el personal de esta area.

## Descripcion de los Usuarios

- Pertenecen al area de extension de la facultad, como auxiliares, coordinadores y el Secretario de Extension.
- Salvo el Secretario de Extension, todos tienen mas de 5 anos de antiguedad.
- Todos manejan software de ofimatica y aplicaciones de mensajeria/correo electronico ademas de organizacion, sean calendarios o herramientas administrativas, pero solo la mitad utiliza regularmente herramientas de IA y de manera ocasional.
- El uso de la IA actualmente se enfoca principalmente en la redaccion de textos y la busqueda y resumen de informacion, mostrando que son las tareas que mas se desean automatizar.
- Los usuarios afirman tener una familiarizacion de media a alta con la tecnologia y consideran que hay multiples tareas que automatizar.
- Las principales dificultades que encuentran en su trabajo son problemas de comunicacion y coordinacion con otras areas, problemas con la gestion administrativa y existencia de tareas repetitivas y tediosas que podrian ser automatizadas.

## Modelo de Negocio

### Socios Clave

- Equipo academico e investigadores.
- Facultad de Ingenieria del Ejercito (FIE).
- Proveedores tecnologicos.

### Actividades Clave

- Relevamiento de necesidades y soporte a los usuarios.
- Diseno y desarrollo de agentes inteligentes.
- Automatizacion de procesos.
- Validacion de avances.

### Recursos Clave

- Recursos humanos: alumnos de 4. y 5. ano, profesores.
- Informacion acerca de las necesidades de la Secretaria de Extension Universitaria.
- Bibliografia.
- Memorias RAM de hasta 64 GB para servidores destinados a desarrollo, pruebas y preproduccion del software.
- Microprocesador IA para servidor de implementacion y despliegue de agentes inteligentes funcionales.

### Propuestas de Valor

- Automatizar tareas repetitivas relacionadas con la creacion y extraccion de informacion sin descartar la intervencion humana.
- Acelerar busqueda y analisis de informacion.
- Garantizar la trazabilidad mediante generacion automatica de logs.
- Ofrecer una herramienta que proteja la soberania de los datos de la FIE.

### Relacion con los Clientes

- Relacion colaborativa y comunicacion/feedback constante.
- Capacitacion y acompanamiento.
- Soporte tecnico.

### Canales de Comunicacion

- Implementacion directa del sistema dentro de la institucion.
- Feedback a traves de encuestas, correos y reuniones presenciales.

### Segmento de Clientes

- Personal del area de Secretaria de Extension Universitaria de la Facultad de Ingenieria del Ejercito.
- Entidades como CONEAU y SIU.
- Docentes y estudiantes.

### Estructuras de Costo

- Infraestructura tecnologica mencionada en los recursos.
- Mantenimiento del sistema.
- Documentacion.

### Fuentes de Ingresos

- Inversion que realizara la FIE de acuerdo al presupuesto.

## Requisitos del sistema

### Funcionales

1. Generar gacetillas en base a plantillas institucionales o solicitudes de los usuarios.
2. Generar post para redes sociales de formato adaptable.
3. Generar newsletters en base a la informacion recibida.
4. Generar certificados en formato PDF.
5. Ingreso mediante credenciales de usuarios con permisos particulares dependientes de su rol.
6. Solicitar validacion humana antes de la publicacion de cualquier contenido generado.
7. Permitir a los usuarios correspondientes validar contenidos pendientes de aprobacion.
8. Programar el envio de anuncios de actividades a medida que se crean estas.
9. Recibir e interpretar distintos tipos de archivos (PDF, DOCX, XLSX, etc.), con el objetivo de generar contenido.
10. Almacenar resultados mediante hojas de Google Sheets.
11. Disparar la generacion de contenido a partir de peticiones humanas, alertas de cambios en una fuente de informacion sobre propuestas academicas o solicitudes de otros agentes.

### No Funcionales

1. Generar contenido en menos de 30 segundos.
2. Operar la informacion de forma segura.
3. Tener una interfaz amigable.
4. Ser facil de utilizar, realizando las tareas principales de forma directa.
5. Funcionar en un servidor local.
6. Resultar mantenible.
7. Ser tolerante a fallos.
8. Tener una disponibilidad del 99%.

## Interaccion con Demas Agentes

### Agente 2

- Entrada: datos historicos y efemerides.
- Proceso objetivo: Proceso 7 - Memoria Institucional.

### Agente 3

- Entrada: informacion sobre eventos y oportunidades externas.
- Proceso objetivo: Proceso 2 y Proceso 6 - Eventos y Vinculacion.

### Agente 4

- Entrada: consultas sobre propuestas institucionales y solicitudes de materiales de orientacion.
- ExtensionBot le envia material para resolver dichas consultas.
- Proceso objetivo: Proceso 5 y Proceso 9 - Cursos y Atencion.

### Agente 5

- Entrada: analiticas de contenidos publicados para considerar durante la generacion.
- Proceso objetivo: Proceso 8 - Mejora Continua.

## Metodologia de desarrollo de software

Se propuso para el proyecto la metodologia de desarrollo iterativa Scrum.

Esto se debe a que el proyecto esta conformado por varios grupos que deben coordinarse para disenar y desarrollar funciones comunes, por lo que las reuniones frecuentes, caracteristica de Scrum, facilitaran la comunicacion y colaboracion entre equipos.

## Cronograma

| Actividad / Entregable | Semestre 1 (Meses 1-6) | Semestre 2 (Meses 7-12) | Semestre 3 (Meses 13-18) | Semestre 4 (Meses 19-24) |
|---|---:|---:|---:|---:|
| Relevamiento de necesidades de la Secretaria de Extension | * |  |  |  |
| Definicion funcional y tecnica del sistema de agentes | * |  |  |  |
| Preparacion de infraestructura minima | * |  |  |  |
| Pilotos de automatizacion comunicacional | * | * |  |  |
| Integracion con redes sociales y web institucional | * | * |  |  |
| Repositorio historico institucional | * | * |  |  |
| Evaluacion de impacto institucional |  |  |  | * |
| Manual operativo y capacitacion |  |  |  | * |
| Plan de escalabilidad hacia el Centenario |  |  |  | * |

## Diagrama de Gantt

En el link adjunto anterior se puede acceder al diagrama y observar las tareas del desarrollo, ya sea cumplidas, en ejecucion o planificadas a futuro.

Vista previa: incluida en el PDF original.

## Diagrama de Clases

En el link adjunto anterior se puede acceder al diagrama de clases propuesto para ExtensionBot particularmente.

Tengase en cuenta que dicho diagrama se encuentra sujeto a modificaciones constantes y por lo tanto no deberia considerarse para el desarrollo hasta que se encuentre validado oficialmente.

Vista previa: pendiente de agregar en la fuente original.

## Diagrama de Casos de Uso

En el link adjunto anterior se puede acceder al diagrama de casos de uso del ExtensionBot.

Dichos casos de uso se encuentran clasificados en bloques y listados a continuacion junto con su flujo principal.

### Bloque 1: Generacion de Contenido

#### CU01: Recibir Entradas

Actor: Apps Script.

1. El Apps Script envia las entradas al ExtensionBot.
2. Esto puede ocurrir por modificaciones en Google Workspace o en momentos previamente programados: efemerides, eventos, etc.
3. Las entradas son validadas por ExtensionBot.
4. En caso de que la validacion resulte exitosa se pasa al CU03 Generar Contenido (include).
5. En caso de que la validacion falle se pasa al CU02 Notificar Error (extend).

#### CU02: Notificar Error

Actor: Apps Script.

1. ExtensionBot detecta un error en la informacion de las entradas recibidas.
2. Se genera un registro detallando el error.
3. Se envia al Apps Script la informacion del error para que gestione la solicitud de reenvio de datos con la fuente original: operario de extension, otro agente, etc.

#### CU03: Generar Contenido

1. El bot toma una entrada validada de la cola de Redis.
2. Mediante el modelo de IA ejecuta el prompt adecuado al tipo de solicitud recibida, como redaccion de gacetilla o generacion de certificado, y dispara el CU04 Consultar Repositorio para obtener las referencias necesarias (include).
3. Una vez terminado el procesamiento del prompt dispara el CU05 Persistir Borrador (include).
4. Dispara el CU06 Registrar Log de Auditoria (include).

#### CU04: Consultar repositorio

Actor: Repositorio Institucional.

1. El agente consulta al repositorio de informacion para generar contenido en base a los resultados.

#### CU05: Persistir Borrador

Actor: Google Workspace.

1. Se persiste el contenido generado como borrador pendiente de validacion en Google Drive o Gmail segun corresponda.

#### CU06: Registrar Log de Auditoria

Actor: Base de Datos.

1. ExtensionBot luego del CU03 Generar Contenido genera una entrada en un log detallando que tipo de contenido se genero, el origen de la peticion y la fecha y hora.
2. El log es almacenado en una base de datos de PostgreSQL.

### Bloque 2: Human in the Loop

#### CU07: Iniciar sesion

Actores: Responsable de Gestion del Conocimiento, Coordinador de Extension.

1. Ingresar credenciales.
2. Corroborar credenciales ingresadas con la base de datos.
3. Si las credenciales se encuentran en la base de datos, otorgar acceso.
4. Si faltan credenciales o fueron ingresadas erroneamente, negar acceso.
5. Registrar ingreso en el log.
6. Disparar el CU08 Consultar Borradores (include).

#### CU08: Consultar borradores

Actores: Responsable de Gestion del Contenido, Coordinador de Extension.

1. Los actores, una vez autenticados correctamente, acceden al listado de borradores pendientes de validacion almacenados en Google Drive.
2. Los actores eligen uno de los borradores.
3. Se puede disparar el CU09 Corregir Borrador (extend) o el CU10 Aprobar Borrador (extend).

#### CU09: Corregir Borrador

Actores: Responsable de Gestion del Contenido, Coordinador de Extension.

1. Los actores marcan observaciones y correcciones al borrador.
2. Las correcciones son enviadas al bot.
3. Se vuelve a generar el borrador mediante el CU03 Generar Contenido (include).

#### CU10: Aprobar Borrador

Actores: Responsable de Gestion del Contenido, Coordinador de Extension.

1. Los actores marcan al borrador como aprobado segun su rol: aprobacion semantica o utilitaria.
2. Si el bot detecta que el borrador recibio ambas aprobaciones dispara el CU11 Planificar Fecha de Publicacion (extend).

### Bloque 3: Difusion de Contenido

#### CU11: Planificar Fecha de Publicacion

Actor: Coordinador de Extension.

1. Una vez el contenido es aprobado se le asigna una fecha y hora de publicacion.
2. Cuando se alcance dicha fecha y hora se disparara el CU12 Publicar Contenido Programado (include).

#### CU12: Publicar Contenido Programado

Actores: Canales de Publicacion, Scheduler.

1. El Scheduler detecta que se alcanzo la fecha de publicacion programada para un borrador aprobado.
2. Se envia el contenido del borrador a las APIs de los canales de publicacion correspondientes.

### Bloque 4: Soporte

#### CU13: Mantener el sistema

Actor: Responsable Tecnico.

El flujo de este caso de uso depende exclusivamente del responsable tecnico y queda fuera del alcance del proyecto.

### Lista de Actores para los Casos de Uso

- Apps Script: esta pendiente de nuevas entradas de contenido y dispara la generacion de contenido por parte del Extension Bot.
- Scheduler: actor de sistema encargado de ejecutar tareas programadas.
- Repositorio Institucional: encargado de contener las referencias para la generacion de contenido.
- Base de Datos: encargada de almacenar y gestionar los registros del sistema.
- Google Workspace: almacena los borradores que genere el bot y gestiona el envio de correos electronicos.
- Responsable de Gestion del Conocimiento (RGC): encargado de la validacion semantica.
- Coordinador de Extension: encargado de la validacion utilitaria.
- Canales de Publicacion: encargados de recibir y publicar los contenidos aprobados que genere el bot.
- Responsable Tecnico: encargado del mantenimiento del sistema.

## Diagrama de Componentes

En el link adjunto anterior se puede acceder al diagrama de componentes propuesto para ExtensionBot.

Al momento de la redaccion de este documento la implementacion tecnica del proyecto sigue siendo evaluada, por lo que dicho diagrama se encuentra sometido a modificaciones constantes.

Vista previa: incluida en el PDF original.

## Diagrama de Despliegue

Vista previa: incluida en el PDF original.

## Diagrama de Estados

En el link adjunto anterior se puede acceder al diagrama de maquina de estados para el contenido generado por ExtensionBot.

Vista previa: incluida en el PDF original.

## Diagrama de Actividades

En el link adjunto anterior se puede acceder al diagrama de actividades propuesto para ExtensionBot, en el que se describe su flujo de trabajo a nivel general.

Vista previa: incluida en el PDF original.

## Diagrama de Secuencia

En el link adjunto anterior es posible acceder a los diagramas de secuencia realizados para ExtensionBot.

Con el fin de facilitar su comprension y acelerar la lectura, se separo la secuencia de ExtensionBot en un diagrama para su flujo principal y un subdiagrama para las validaciones del contenido.

Vistas previas: incluidas en el PDF original.
