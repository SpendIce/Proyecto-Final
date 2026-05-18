# DSI1 Unidad III I - Proceso de desarrollo y transformacion de requisitos en diseno

Fuente PDF: `DSI1/Unidad_III_I.pdf`.

Markdown operativo: `DSI1/_md/unidad-iii-i.md`.

Paginas PDF: 24. Palabras OCR extraidas: 1725.

Nota: OCR automatico local con `pdftoppm` + `tesseract -l spa+eng` para busqueda y recuperacion por agentes. Puede contener errores propios de OCR; para tablas, figuras o formato exacto, consultar el PDF fuente.

---



---

## Pagina 1

Unidad Il
El Modelado de Análisis ***
de
1


---

## Pagina 2

Unidad Il - Modelado de Análisis

Considerar algunas aspectos:

1. Supuestos: reducen el número de permutaciones y
variaciones posibles, permitiendo así al modelo reflejar
el problema de manera razonable. (Limitarse el
proceso y el rango de entradas.

2. Simplificaciones: que permiten crear el modelo a
tiempo.

3. Limitaciones: que ayudan a delimitar el sistema.

4. Restricciones: que guían la manera de crear el modelo
y el enfoque que se toma al implementar el modelo.

5. Preferencias: que indican la arquitectura preferida para
todos los datos, funciones y tecnología. La solución
preferida entra a veces en conflicto con otros factores
restrictivos.

2


---

## Pagina 3

Unidad Il - Modelado de Análisis

e Al terminar el análisis de requerimientos, el paso
siguiente es la transformación de aquellos deseos
en una solución: un diseño que satisfaga las
necesidades de los clientes.

e Basado en este análisis, se generan las
especificaciones de las características del SW, se
indican las interfaces del SW con otros elementos
del Sistema y se establecen restricciones que se
debe tener el Sistema.

e Proporciona Información para el desarrollador y el
diseñador

3


---

## Pagina 4

Unidad Il - Modelado de Análisis
al 4F'r'oibrlérfr;a?   2         —
— —l QA    an 2- 1
(Factibilidad)——— m EL                        —
P—       C Análisis ",_.“/ím — y
—'g?—…[]    7       :\!rfr;::ﬂyﬁ,r‘\       3";‘]
m f   —                         y— Disefiod -
- au              ==
".          PRy               Módulos
C
————;.—];—]]— ——o—]—FI$ - UNI
El proceso de desarrollo de software es aquel en el que las necesidades del
usuario son traducidas en requisitos de software, estos transformados en
diseño y el diseño implementado en código.
4


---

## Pagina 5

Unidad Il - Modelado de Análisis
* Combinación de texto y diagramas para representar
requisitos de datos, las funciones y el
comportamiento, de manera fácil de entender.
* Conduce a lograr la corrección, la integridad y la
consistencia.
Cumplir 3 objetivos primarios:
1. Describir lo que requiere el cliente
2. Establecer una base para la creación de un
diseño SW.
3. Definir Conjunto de Requisitos que puedan
validarse una vez construido el SW.
5


---

## Pagina 6

Unidad Il - Modelado de Análisis

Reglas practicas del análisis

* Modelo centrado en requisitos visibles dentro del
problema o dominio del negocio. Grado de
abstracción alto (sin detalles)

* Cada elemento del modelo de análisis debe
agregarse de acuerdo a los requisitos del SW y
deben proporcionar una visión interna del dominio
de la información, función y comportamiento del
sistema.

* Debe retrasarse la consideración de la
Infraestructura y otros modelos no funcionales
hasta el diseño (Ej: BD sin clases, funciones o
comportamientos)

6


---

## Pagina 7

Unidad Il - Modelado de Análisis
Reglas practicas del análisis
* Minimizar el acoplamiento de todo el sistema en

relación entre funciones y clases.
* Debe proporcionar valor a todos los interesados.

(validar requisitos, base del diseño)
* Modelo lo mas simple que sea posible.

7


---

## Pagina 8

Unidad Il - Modelado de Análisis

Análisis del dominio:

* Utilizar patrones definidos y clasificados, estos
aceleran la creación.

* Patrones de diseño reutilizables y componentes
ejecutables.

* ldentificar, analizar y especificar las capacidades
comunes reutilizables dentro de un dominio
específico de aplicación (objetos, — clases,
subsistemas)

Enfoque del Modelado:

Estructurado: los datos y los procesos que los transforman son

entidades separadas

00: definición de clases y como estas colaboran entre si para

efectuar requisitos del cliente

8


---

## Pagina 9

Unidad Il - Modelado de Análisis
Modelado de datos
* Objeto de datos:
Representación de cualquier  información
compuesta que el SW debe entender: entidad
externa, cosa, papel, evento o estructura.
e Atributos: definen propiedades puede:
1. Nombrar una ocurrencia Obj Datos.
2. Describir la ocurrencia.
3. Hacer referencia a otra ocurrencia .
9


---

## Pagina 10

Unidad Il - Modelado de Análisis
Modelado de datos
e Relaciones:
Conexión de datos entre si.
Cardinalidad cuantas ocurrencias.
Modalidad:
- Relación 0, no hay necesidad u obligatoria
explicita.
- Relación 1, ocurrencia relación obligatoria
(diagrama entidad relación)
10


---

## Pagina 11

Unidad Il - Modelado de Análisis
* Análisis orientado a objetos definir todas las clases
(Relaciones y Comportamiento) relevantes para el
problema y que deben resolverse.
* Tareas:
* Comunicar Requisitos Básicos entre cliente e
Ingeniero SW.
* — Identificar clases.
* — Definir jerarquía.
* Representar relaciones Obj a Obj.
* Modelar comportamiento Obj
* — terativo.
11


---

## Pagina 12

Unidad Il - Modelado de Análisis

* Modelado basado en casos de escenario:
(CU texto — Diagrama Actividad, Diagrama Carril)
Escritura de casos de uso.
Desarrollo Diagrama de actividad complementan CU
representación grafica del flujo de interacción dentro
de un escenario, agrega detalles adicionales
Diagrama de carril variación Diagrama de actividad
además indica que actor o clases análisis tiene la
responsabilidad de la acción

12


---

## Pagina 13

Unidad Il - Modelado de Análisis
* Modelado Orientado al Flujo: (Diagrama Flujo
Datos, Diagrama Flujo Control, Narrativas del
procesamiento)
Visión del Sistema tipo E — P — S , representación
jerárquica.
* Se van refinando posteriormente proporcionando
mayor detalle.
* Se crea el modelo de flujo de datos: permite
modelo domino Información y dominio funcional
* Nivel 0: representar SW o Sistema como una sola
burbuja, E/S primaria establecerse con cuidado,
refinar aislando procesos, Objetos de datos,
almacenamiento datos.
13


---

## Pagina 14

Unidad Il - Modelado de Análisis

* Crear modelo de control de flujo: Aplicaciones que
están guiadas por eventos y no datos, que
producen información de control. En lugar de
reportes o despliegues y que procesan información
por tiempo y rendimiento

* Especificación     del     control:     representa
comportamiento Sistema de 2 maneras diferentes
Diagrama de Estado: que es una especificación
secuencial del comportamiento.

Tabla de activación de programa: especificacion
combinatoria del comportamiento , falta descripción
del comportamiento.

* Especificación del proceso: describe todos los
procesos del modelo de flujos que aparecen en el
nivel final de la refinación.

14


---

## Pagina 15

Unidad Il - Modelado de Análisis
* Modelado basado en clases: (Diagrama Clases,
Paquete Análisis, Modelo CRC (clase -
responsabilidad   -   colaborador),   Diagrama
Colaboración)
* — Identificación clases de análisis:
o Entidades externas (otros sistemas, dispositivos)
que producen o consumen información
o Cosas que son parte del domino de la
información
o Sucesos o eventos que ocurren dentro del
contexto de la operación sistema — Papeles que
desempeñan personas que interactúan con el
sistema
o Unidades organizacionales.
15


---

## Pagina 16

Unidad Il - Modelado de Análisis
o Sitios que establecen el contexto del problema y

la función global del sistema.

o Estructuras (sensor, vehículo, etc) que definen
una clase de objeto o clases de objeto
relacionadas.

* Características de selección: Información referida.
La información debe recordarse para que el sistema
funcione — Servicios requeridos: Conjunto
operaciones identificables que puedan cambiar el
valor de sus atributos de alguna manera — Atributos
múltiples — Atributos comunes — Operaciones
comunes — Requisitos esenciales.

* Especificación de atributos: describen a la clase, la
definen

16


---

## Pagina 17

Unidad Il - Modelado de Análisis
* Definición    de    operaciones:    Definen    el
comportamiento de los objetos.
o Varios tipos de operaciones que manipulan los
datos de alguna manera
o Operaciones que realizan un cómputo
o Operaciones que preguntan por el estado de un
objeto
o Operaciones que monitorean un objeto para la
ocurrencia de un evento de control, pueden
operar sobre los atributos o asociaciones
17


---

## Pagina 18

Unidad Il - Modelado de Análisis
* Modelado: Clase - Responsabilidad — Colaborador
Proporciona un medio simple para identificar y
organizar las clases relevantes para los requisitos
del sistema o Producto,
3 tipos Clases
= Clases de Entidad o del modelo del negocio: se
extraen directamente del problema.
= Clases de Frontera: sirven para crear la interfaz.
= Clases de Controlador: manejan una unidad de
trabajo del principio al final.
Pueden manejar: Creación o actualización de un Obj
Entidad — Inmediatez de Obj frontera conformen
obtienen Info Obj entidad — Comunicación compleja
entre Conj Obj — Validación de datos comunicados
entre Obj o entre el usuario y la aplicación.
18


---

## Pagina 19

Unidad Il - Modelado de Análisis
* Responsabilidades
5 directrices para determinar responsabilidad:
> La inteligencia del sistema se debe distribuir
entre las clases para abordar de mejor manera la
necesidad de los problemas.
> Cada responsabilidad debe establecerse tan
general como sea posible.
> La información y el comportamiento relacionado
con ella debe estar dentro de la misma clase.
> La información relativa a una cosa debe
localizarse como una sola clase, no distribuirse
entre muchas.
> Las responsabilidades pueden compartirse entre
clases relacionadas cuando sea posible.
19


---

## Pagina 20

Unidad Il - Modelado de Análisis
* Colaboraciones: Utilizar sus propias operaciones
para manipular sus propios atributos y cumplir una
responsabilidad particular.
* Unaclase puede colaborar con otras.
20


---

## Pagina 21

Unidad II - Modelado de Análisis
* Asociaciones y dependencias: las clases de análisis
se relacionan entre si — multiplicidad.
* Paquetes de análisis: clasificación como una
agrupación
21


---

## Pagina 22

Unidad Il - Modelado de Análisis
* Creación modelo de comportamiento: (Diagrama de
Estado, Diagrama de Secuencia) representación
dinámica del sistema o producto.
* Pasos para crear:
1.Evaluar todos los CU para entender por completo
la secuencia de interacción dentro del Sistema.
2.Identificar los eventos que conducen a la
secuencia de interacción y entender la forma en
que estos se relacionan con clases específicas
3.Crear una secuencia para cada CU.
4.Construir un diagrama de estado para cada
sistema.
5.Revisar el modelo de comportamiento para
verificar su exactitud y consistencia .
22


---

## Pagina 23

Unidad Il - Modelado de Análisis

* Identificación de eventos de caso de uso: Cada CU
representa secuencia de actividades que implica
actores y el sistema.

* Representaciones de estado: 2 tipos: El estado que
tiene cada clase conforme el sistema realiza su
función — El estado del sistema como se observa del
exterior conforme realiza su función.

* Diagramas de estado para clases de analisis:
representa los estados activos para cada clase y los
eventos que ocasionan cambios de estos estados
activos

* Diagrama de secuencias Indican como los eventos
causan transiciones de un objero a otro.

23


---

## Pagina 24

FIN
