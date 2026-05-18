# DSI2 Ingenieria de Sistemas

Fuente PDF: `DSI2/16 Ingenieria de Sistemas/1. Ingenieria de Sistemas.pdf`.

Markdown operativo: `DSI2/_md/16-ingenieria-de-sistemas.md`.

Paginas PDF: 35. Palabras OCR extraidas: 1893.

Nota: OCR automatico local con `pdftoppm` + `tesseract -l spa+eng` para busqueda y recuperacion por agentes. Puede contener errores propios de OCR; para tablas, figuras o formato exacto, consultar el PDF fuente.

---



---

## Pagina 1

DISEÑO DE SISTEMAS
INFORMÁTICOS I
1


---

## Pagina 2

SISTEMAS CLIENTE SERVIDOR

* Consiste en el procesamiento cooperativo de la
información por medio de un conjunto de
procesadores, en el cual múltiples clientes,
distribuidos geográficamente, solicitan
requerimientos a uno o más servidores centrales.

* Es una arquitectura distribuida que permite a los
usuarios finales obtener acceso a la información
en forma transparente, aún en entornos
multiplataforma.

2


---

## Pagina 3

SISTEMAS CLIENTE SERVIDOR
* En este modelo, el cliente envía un mensaje solicitando un
determinado servicio a un servidor, y éste envía uno o
varios mensajes con la respuesta.
Solicitud , f
« Respuesta
3


---

## Pagina 4

SISTEMAS CLIENTE SERVIDOR
* Características:

* Se establece una relación entre procesos distintos, los
cuales pueden ser ejecutados en la misma o diferentes
computadoras.

* La relación establecida puede ser de uno a muchos, en
la que un servidor puede dar servicio a muchos clientes,
regulando su acceso a recursos compartidos.

* Los clientes corresponden a procesos activos, ya que son
éstos los que hacen peticiones a los servidores. Estos
Últimos tienen una función pasiva

4


---

## Pagina 5

SISTEMAS CLIENTE SERVIDOR
* Características:
* No existe otra relación entre el cliente y el servidor más
que el intercambio de mensajes.
* Las plataformas de hardware y software entre cliente y
servidor son independientes. Precisamente, esta es una de
sus principales ventajas.
* El concepto de escalabilidad, tanto horizontal como
vertical es aplicable a cualquier sistema cliente-servidor.
5


---

## Pagina 6

SISTEMAS CLIENTE SERVIDOR
* Componentes:
* Proceso cliente: Es quien inicia el diálogo, solicitando un servicio
al servidor.
* Proceso servidor: Espera a que lleguen peticiones de servicio.
* Middleware: Interfaz que permite la conectividad entre ambos.
6


---

## Pagina 7

SISTEMAS CLIENTE SERVIDOR
* Cliente:

* Administra la interfaz de usuario (front-end).

* Interactúa con el usuario.

* Procesa la lógica de la aplicación y hace validaciones

locales.

* Genera requerimientos de acceso a datos.

* Recibe resultados del servidor.

* Formatea esos resultados.

7


---

## Pagina 8

SISTEMAS CLIENTE SERVIDOR
* Servidor:

* Acepta los requerimientos de acceso a datos.

* Procesa dichos requerimientos.

* Procesa la lógica de la aplicación y realiza validaciones a nivel

de base de datos.
* Formatea datos para transmitirlos a los clientes.
8


---

## Pagina 9

SISTEMAS CLIENTE SERVIDOR
* Middleware:

* Provee conectividad entre aplicaciones clientes,
aplicaciones servidores y bases de datos (Un tipo
particular de servidor).

* Protege a los desarrolladores de tener que manejar
detalles de bajo nivel de distintos protocolos de
comunicacién, sistemas operativos y arquitecturas.

* Incluye API's, PRC, pipes, mensajerías de red y accesos a
bases de datos.

9


---

## Pagina 10

* Clasificación:

* Las relaciones entre cliente, middleware y servidor definirán el
modelo de sistema que mejor se aplica a cada situación.

* Se debe tener en cuenta tiempo de respuesta, tamaño de
registros, tamaño de bases de datos, estimaciones de tráfico de
red, distribución geográfica de datos y procesos, entre otros
factores.


---

## Pagina 11

SISTEMAS CLIENTE SERVIDOR
* Fat client (Thin server)
==  u
| Clente                   ==
Servidor            —
| Nivel de
1


---

## Pagina 12

SISTEMAS CLIENTE SERVIDOR
* Fat server (Thin client)
ivel de Presentación | [ Nivel de Aplicación
—         then
=2  ‘
else_
Cliente            )|       Senvidor
Servidor                      —
de Base               Nivel de
’  de Datos             | Base de
_ Datos     J
12


---

## Pagina 13

* Clasificación por planos (Tiers):
* Se define en base a como se distribuyen los tres procesos
clásicos de un sistema cliente servidor: Interfaz de usuario, lógica
del negocio y base de datos.
* Estos niveles pueden ser de software o hardware.
* Puede ser de dos planos, tres planos o multiplanos.
13


---

## Pagina 14

* Dos planos (software) con SQL remoto:
m. Nl de        El cliente envia mensajes con
Presentación      =
_  I el e        solicitudes SQL al servidor y
tano Uro)      yea deNegocs
=       AE       el resultado de cada consulta
               es enviado a través de la red,
-     sin importar su tamaño.
Adecuado para sistemas de
              apoyo y gestión, pero no para
ey n   PR sistomas oriticos
Es mas sencillo su desarrollo,
pero genera mayor tráfico de
red
14


---

## Pagina 15

SISTEMAS CLIENTE SERVIDOR
* Dos planos (software) con procedimientos almacenados
cherte ;am-          Presenta las mismas ventajas del
bt                               modelo anterior, pero mejora su
                performance.

— e        Su principal desventaja radica en
que el grueso de la aplicación se
basa en SQL extendido (stored

               procedures, triggers y constrains)
hi I PE         propios del proveedor de la base
00 —              de datos.
v de Bese
15


---

## Pagina 16

SISTEMAS CLIENTE SERVIDOR
* Tres planos (software)
Reduce el tráfico de
E EN oo
     d          Brinda mayor flexibilidad
- Combn rcscón     (puede resultar más
(Plano Dos)       Negocos         Aec          Es escalable.
                            ,
Reduce el impacto del
Nirel de Base de    mantenimiento.

Servidor de Base   Datos       D    :    —
de Datos                      isminuye la cantidad de
(Plano Tres)

“                clientes (licencias) de la
base de datos.
16


---

## Pagina 17

SISTEMAS CLIENTE SERVIDOR
* Dos planos (hardware)
Mútiples Clentes     Los clientes se
conectan vía LAN a
           =          un servidor central,
\           quien además
=           administra los datos.
(a         AM
17


---

## Pagina 18

SISTEMAS CLIENTE SERVIDOR
* Tres planos (hardware)
Los clientes se
Múltiples Clientes                   conectan a un
                    servidor local, el
                         =            cual a su vez se
—               —           ==             conecta con un
l           %              servidor central de
…m]              base de datos.
m         El Servidor local
[ m           ridor Local - Servidor Central        tiene un
=i,                                       comportamiento
dual, ya que es
cliente del servidor
central
18


---

## Pagina 19

SISTEMAS CLIENTE SERVIDOR
* Múltiples planos (hardware)
— Y
%    \      —  E         En este modelo,
a         \       los clientes
NE          M          d
N           E  Servidores Locales     —
'        >                 conectarse
a   \        m               directamente
‘                        con el servidor
‘                      central de Base
a                       de datos.
19


---

## Pagina 20

SISTEMAS DE TIEMPO REAL
* Se denominan Sistemas de Tiempo Real a aquellos en
donde el instante en el que se produce el resultado es
significativo.
* Reaccionan ante estímulos del ambiente.
* La corrección del resultado devuelto depende tanto de su
valor como del instante de su entrega.
20


---

## Pagina 21

SISTEMAS DE TIEMPO REAL
21


---

## Pagina 22

SISTEMAS DE TIEMPO REAL
* No significa Gnicamente que el Sistema deba ser rápido:
* Ej: Brazo robot

* Cada respuesta del sistema tiene una ventana de tiempo

en la que es válida.
* Cuanto más pequeña sea esta ventana o “jitter”, más

complejo será el sistema.

22


---

## Pagina 23

SISTEMAS DE TIEMPO REAL
* Sistemas hard RT: El jitter es muy pequeño, El costo
de las fallas es mucho mayor al costo del Sistema.
* Sistemas soft RT: Se permiten algunas fallas. El
tamaño del jitter es mayor.
* Sistemas firm RT: Se puede retrasar y perder alguna
información, siempre y cuando esto no ocurra muy
frecuentemente.
23


---

## Pagina 24

* Tarea (task): Es un proceso que desempeña una actividad
específica.
* Sus atributos principales son:
* Deadline: Es el momento en que debe terminar la ejecución de
la tarea. No sirve que termine antes o empiece después.
* Release time: Momento a partir del cual puede empezar a
ejecutarse la tarea.
* Duración: Tiempo que tarda en ejecutarse.
24


---

## Pagina 25

SISTEMAS DE TIEMPO REAL
* Control de tareas:
* Por tiempos: El proceso se ejecuta y actualiza su estado
periódicamente, generalmente en forma frecuente.
* Por eventos: El proceso se ejecuta y actualiza al ser
invocado por un estímulo externo. Es un proceso reactivo.
25


---

## Pagina 26

SISTEMAS DE TIEMPO REAL
Características de los STR:
* Determinismo: Es la capacidad de determinar con
precisión, cuanto es el tiempo que toma una tarea en
iniciarse.
Se refiere al tiempo que tarda el sistema en
responder a una interrupción. Esto es importante, ya
que casi todas las peticiones de servicios al sistema
son generadas por eventos externos.
26


---

## Pagina 27

SISTEMAS DE TIEMPO REAL
* Responsividad:
* Es el tiempo que tarda la tarea en ejecutarse
una vez que la interrupción ha sido atendida.
Una vez realizado el cálculo de determinismo y
responsividad del Sistema, se convierte en una
característica del sistema y un requerimiento
para las aplicaciones que correrán en él.
27


---

## Pagina 28

SISTEMAS DE TIEMPO REAL

* Usuarios Controladores:
En estos sistemas, los usuarios (los procesos que
correrán sobre el Sistema Operativo) tienen un
control mucho más amplio:

* El proceso es capaz de especificar su prioridad.

* El proceso es capaz de especificar el manejo de memoria
que requiere. (Usar o no caché o memoria virtual, por
ejemplo)

* El proceso especifica qué derechos tiene sobre el sistema.

28


---

## Pagina 29

SISTEMAS DE TIEMPO REAL
* Confiabilidad: La calidad del servicio que presta el
sistema no debe degradarse más allá de un límite
determinado. El Sistema debe seguir funcionando
más allá de catástrofes o fallas mecánicas.
* Estabilidad: Si es imposible cumplir todas las tareas
sin exceder sus restricciones de tiempos, entonces
cumplir las más críticas y de mayor prioridad.
29


---

## Pagina 30

SISTEMAS PARA INTERNET
30


---

## Pagina 31

SISTEMAS PARA INTERNET
* Son un ejemplo clásico de Sistemas cliente servidor.
* La aplicación cliente (Browser) solicita un servicio (visualizar
una página) a un servidor.
* El middleware (DNS) provee la comunicación entre ambos a
través de un protocolo propio (TCP/IP).
31


---

## Pagina 32

SISTEMAS PARA INTERNET

* En los Sistemas que van a estar en Internet, es
crucial el aspecto de la seguridad, ya que son
potencialmente accesibles para millones de
usuarios.

* Se debe considerar que no hay forma de
garantizar su disponibilidad o velocidad de
respuesta a través de Internet.

* Tampoco se puede controlar la aplicación cliente (si
el sistema está destinado al público en general),
por lo que se deben garantizar su accesibilidad a
la mayor cantidad posible de clientes.

32


---

## Pagina 33

SISTEMAS PARA INTERNET
* Pensar ejemplos en Internet de aplicaciones:
* 2 niveles de software con SQL remoto.
* 2 niveles de software con procedimientos almacenados.
* 3 niveles de software.
* 2 niveles de hardware.
* 3 niveles de hardware.
* Múltiples niveles de hardware.
33


---

## Pagina 34

SISTEMAS PARA INTERNET
* “Lenguajes” de programación:

* HTML: Código estático que entiende el browser. El
código está en el servidor, y al ser solicitado viaja hasta
el cliente.

* Javascript, Vbscript, Applet: Código ejecutable, que se
ejecuta en el browser al ser disparado por un evento.
No todos los browsers entienden todos los lenguajes.

* ASP / PHP: Código que al ser solicitado por un cliente,
se ejecuta en el servidor (por eso puede acceder a
Bases de datos), genera el código HTML y éste se
transmite al browser.

* Flash: Lenguaje “cerrado” que se visualiza en el clientd
con una aplicación específica.

34


---

## Pagina 35

SISTEMAS PARA INTERNET
* Con esta misma tecnología, se pueden generar:
* Intranet: una red local interna, pero con la misma tecnología de
Internet.
* Extranet: cuando esa misma red puede ser accedida a través de
Internet.
35
