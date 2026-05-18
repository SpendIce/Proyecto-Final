# DSI2 Ingenieria del Software y Organizacion de Proyectos Informaticos

Fuente PDF: `DSI2/02 Ing de Sw y Org de Proy Inf/Ingenieria del software.pdf`.

Markdown operativo: `DSI2/_md/02-ingenieria-del-software.md`.

Paginas PDF: 23. Palabras OCR extraidas: 1197.

Nota: OCR automatico local con `pdftoppm` + `tesseract -l spa+eng` para busqueda y recuperacion por agentes. Puede contener errores propios de OCR; para tablas, figuras o formato exacto, consultar el PDF fuente.

---



---

## Pagina 1

DISENO DE SISTEMAS
INFORMÁTICOS I
1


---

## Pagina 2

¿QUE ES EL SOFTWARE?
* “El software son sólo los programas”.
* Este tipo de pensamiento genera problemas:

* Medir productividad por líneas de código generadas.

* Montañas de código que no se pueden integrar.

* Sistemas que funcionan “correctamente” pero no resuelven los

requerimientos del usuario.
2


---

## Pagina 3

¿QUE ES EL SOFTWARE?
* No se debe perder de vista el objetivo:
* Es un sistema, que incluye:
* Conocimiento del área de aplicación.
* Colección de programas y datos.
* Información generada en el proceso.
..para convertir una computadora de propósito general en
una máquina de propósito específico.
3


---

## Pagina 4

Ó                                   "      -
Del conocimiento especifico, se ocuparán los especialistas en el área.
Las representaciones de software (el código), lo realizarán los programadores.
De la información inherente al proceso de construcción del software, se ocupa
la ingeniería de SW
4


---

## Pagina 5

INGENIERIA DE SOFTWARE
* |EEE
* “El uso de métodos sistemáticos, disciplinados y cuantificables
para el desarrollo, operación y mantenimiento de software, y el
estudio de técnicas relacionadas con dichos métodos.”
IEEE: Institute of Electrical and Electronic Engineers.
5


---

## Pagina 6

* Fairley:
* “La disciplina tecnológica y de administración que se ocupa de
la producción y evolución sistemática de productos de software
que son desarrollados y modificados dentro de los costos y
tiempos estimados.”
6


---

## Pagina 7

INGENIERIA DE SOFTWARE
* Ghezzi:
* “Es el campo de la ciencia de la computación que trata de la
construcción de sistemas de software que son tan grandes o
complejos que son construidos por un equipo o equipos de
ingenieros.”
7


---

## Pagina 8

INGENIERIA DE SOFTWARE
* Reúne el conocimiento específico del proceso de
desarrollo de software.
* Informaciénrelativa al proyecto
* Información sobre la tecnología de software (métodos,
conceptos, técnicas)
* Conocimiento de sistemas similares
* Información sobre identificación y solución de problemas técnicos
del sistema en desarrollo.
8


---

## Pagina 9

“:x:'.¿,…  S y SU:               ,
1                   HERRAMIENTAS
               METODOLOGIAS
METODOS Y TECNICAS
PRINCIPIOS
Método: Lineamiento general que gobierna la ejecución de alguna actividad,
deben ser enfoques disciplinados, sistemáticos y rigurosos.
Técnica: Lineamiento más técnico y mecánico con una aplicabilidad más
restringida.
Metodología: Promueve un enfoque de solución de problemas,
preseleccionando un paquete de métodos y técnicas a ser usadas.
Herramienta: Elemento (software) desarrollado para soportar la aplicación de
técnicas, métodos y metodología
9


---

## Pagina 10

PRINCIPIOS DE INGENIERIA DE
SOFWARE
* Los principios son cualidades deseables de los procesos y
productos de software descriptas en forma general y
abstracta
* Para aplicarlos, son necesarios métodos y técnicas
específicas que permitan incorporar esas propiedades al
software.
10


---

## Pagina 11

PRINCIPIOS DE INGENIERIA DE
SOFTWARE
* Rigor y Formalidad
* El diseño y desarrollo de software es una actividad creativa y
por lo tanto tiende a ser inexacto e impreciso.
* El rigor es un complemento necesario en cualquier actividad
ingenieril, que debe saberse aplicar adecuadamente.
11


---

## Pagina 12

1       * El proce         e\                            encia de pasos
claramente definidos; e           o se sigue algún método o se
J               aplica alguna técnica.
O              * La unión de estos factores se traduce en un enfoque riguroso y
sistemático que puede ser explicado y aplicado una y otra vez.
T               (Melcdo] agl
A partir de una visión rigurosa del proceso, se definen los diferentes modelos
de proceso; cada uno con su metodología propia.
Estos procesos son desarrollados y controlados mediante técnicas de
ADMINISTRACION DE PROYECTOS (UD! y UD2).
Este rigor a menudo debe ser verificado por personas externas al proceso:
Auditorías (UD5)
12


---

## Pagina 13

PRINCIPIOS DE INGENIERIA DE
SOFTWARE
* Separación de aspectos
* Permite manejar la complejidad tratando los diferentes aspectos
individuales de un problema y concentrándonos por separado
en cada uno.
* Las bases de separación pueden ser el tiempo, cualidades,
vistas, partes.
13


---

## Pagina 14

PRINCIPIOS DE INGENIERIA DE
SOFTWARE
* Modularidad (Cohesión y acoplamiento)
* Un sistema puede ser descompuesto en piezas llamadas
módulos.
* Esta división tiene tres objetivos:
* Capacidad de descomponer un sistema complejo
* Componer un sistema con módulos preexistentes
* Comprender cada parte del sistema separadamente
En el principio de Modularidad, se basan los métodos de reutilización de
software y reingeniería de software (UD3).
14


---

## Pagina 15

PRINCIPIOS DE INGENIERIA DE
SOFTWARE
* Abstracción

* Proceso por el cual identificamos los aspectos importantes del

fenómeno e ignoramos los detalles.
* Utilizada para manejar la complejidad
Se deben tener en cuenta las limitaciones impuestas por la tecnología: (UD4)
15


---

## Pagina 16

PRINCIPIOS DE INGENIERIA DE
SOFTWARE
* Anticipación del cambio
* La habilidad de evolucionar requiere que anticipemos cómo y
dónde pueden ocurrir cambios de tal manera de preparar al
software para incorporar el cambio con facilidad.
* Puede utilizarse como criterio separar en porciones específicas
de software los elementos susceptibles de cambio.
16


---

## Pagina 17

PRINCIPIOS DE INGENIERIA DE
SOFTWARE
* Generalización
* Cada vez que se nos pide resolver un problema, enfocarse en
descubrir un problema más general que se esconda detrás del
problema original.
* Puede ser que la generalización no sea más compleja de
resolver que el problema original, y es más fácil de reusar.
17


---

## Pagina 18

PRINCIPIOS DE INGENIERIA DE
SOFTWARE
* Incrementabilidad
* Caracteriza un proceso que se desarrolla por pasos que se
vayan aproximando sucesivamente al objetivo deseado.
* Este principio hace posible la idea de prototipos y el
paralelismo entre las diferentes etapas del proceso.
18


---

## Pagina 19

ADMINISTRACIÓN DE PROYECTOS
* Proyecto: Emprendimiento temporario, llevado a cabo
para crear un producto o servicio único.
* TEMPORARIO: Tiene un principio y un fin definido.
* ÚNICO: Distinguible de todos los demás productos y
servicios.
19


---

## Pagina 20

ADMINISTRACIÓN DE PROYECTOS
* Es la aplicación de conocimiento, habilidades, técnicas y
herramientas a las actividades del proyecto para cumplir
con los requerimientos del mismo.
20


---

## Pagina 21

(
K

R             Riesgos      Adm. Calidad E Comunicaciones

(                           ;       o

í     Integración           Alcance         Adm. Tiempos      Adm. Costos

‘       T
INTEGRACIÓN: Asegura que los componentes del proyecto estén
debidamente coordinados.
ALCANCE: Asegura que el proyecto incluye todo el trabajo requerido para
completarse y no más.
ADM DE TIEMPOS: Asegura que el proyecto se completará en el tiempo
comprometido.
ADM DE COSTOS: Asegura que el proyecto se completará en el presupuesto
aprobado.
ADM DE CALIDAD: Asegura que el proyecto cumplirá con las pautas de
Calidad acordadas.
RECURSOS HUMANOS: Asegura que el proyecto utilizará eficientemente
los recursos humanos que le fueron asignados.
COMUNICACIONES: Asegura la generación, diseminación y archivo de la
información del proyecto en tiempo y forma.
RIESGOS: Asegura que el proyecto hará un esfuerzo constante para
identificar, analizar y responder a los riesgos.
ADQUISICION: Incluye el proceso requerido para adquirir bienes y servicios
necesarios para el proyecto.

21


---

## Pagina 22

21


---

## Pagina 23

»
p
O
Ó
lo]
\                                  CONTROL
Los límites entre una y otra fase suelen ser difusos; siempre hay un
solapamiento doble o hasta triple.
22
