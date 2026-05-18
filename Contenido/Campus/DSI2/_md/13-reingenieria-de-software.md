# DSI2 Reingenieria de Software

Fuente PDF: `DSI2/13 Reingenieria de software/12. Reingenieria de Software.pdf`.

Markdown operativo: `DSI2/_md/13-reingenieria-de-software.md`.

Paginas PDF: 36. Palabras OCR extraidas: 1543.

Nota: OCR automatico local con `pdftoppm` + `tesseract -l spa+eng` para busqueda y recuperacion por agentes. Puede contener errores propios de OCR; para tablas, figuras o formato exacto, consultar el PDF fuente.

---



---

## Pagina 1

DISEÑO DE SISTEMAS
INFORMÁTICOS 1I
1


---

## Pagina 2

COSTOS DEL SOFTWARE
Distribución del costo a lo largo del ciclo de vida del software:
Pruebas — Pruebas
modulares _ de integración
Código      8% 7%
7%
Diseño  m
Análisis        6%
de requisitos |
Mantenimiento
2


---

## Pagina 3

MANTENIMIENTO DEL SOFTWARE
* Corrección de defectos que surgen en el software e

impiden su correcta utilización.
* Creación de nuevas funcionalidades en el software para

adaptarlo a nuevos requerimientos.
* Mejora del rendimiento y la usabilidad en la

funcionalidad existente.

3


---

## Pagina 4

* Mantenimiento correctivo: actividades dedicadas a corregir
defectos en el sistema detectados por el usuario durante la
operación.
* Mantenimiento adaptativo: actividades dedicadas a
modificar el sistema para adaptarlo a los cambios en su
ambiente (tecnológico o del negocio).
* Mantenimiento perfectivo: actividades dedicadas a mejorar
los servicios ofrecidos por el sistema.
4


---

## Pagina 5

MANTENIMIENTO DEL SOFTWARE
* Distribución del costo de tareas de mantenimiento:
Implementar
cambio
Actualizar                                    Estudio del
documentación          19%                  código
"             6 %                23%
Estudiar
documentación m
18 %        28 %
Estudiar
peticiones                              Prudbas:
5


---

## Pagina 6

MANTENIMIENTO DEL SOFTWARE
* Factores que inciden:

* Inexistencia de métodos, técnicas y herramientas que
solucionen el mantenimiento.

* La complejidad se incrementa con las sucesivas
modificaciones.

* La documentación del sistema es defectuosa, inexistente
Ú obsoleta.

* Se considera al mantenimiento una actividad poco
creativa o de menor nivel.

* Las actividades de mantenimiento suelen realizarse bajo
presión.

6


---

## Pagina 7

REINGENIERIA DE SOFTWARE
* Proceso de modificación y reorganización de Sistemas de

Software para hacerlos más sencillos y mantenibles.
* Examen y modificación de un sistema para reconstruirlo

de una nueva forma (sin alterar la funcionalidad).
* Mantenimiento preventivo: actividades dedicadas a

mejorar la mantenibilidad del sistema.

7


---

## Pagina 8

REINGENIERIA
* Sommerville: Los principales factores que afectan a
los costes de re ingeniería son:
1. La calidad del software sobre el que se va a hacer
reingeniería. Cuanto más baja sea la calidad del
software y su documentación asociada (si la hay), más
altos serán los costes de reingeniería.
2. Las herramientas de soporte disponibles para la
reingeniería. Normalmente no es rentable hacer
reingeniería sobre un sistema software a menos que
puedan utilizarse herramientas CASE para
automatizar la mayor parte de los cambios en los
programas.
8


---

## Pagina 9

REINGENIERIA
3. La amplitud de la conversión de datos requerida. Si
el sistema sobre el que se va a hacer reingeniería
requiere que se conviertan grandes volúmenes de
datos. el coste del proceso se incrementa de forma
significativa.
4. La disponibilidad de personal experto. Si el
personal responsable de mantener el sistema no
puede implicarse en el proceso de re ingeniería, los
costes se incrementarán debido a que los ingenieros
encargados de la reingeniería tienen que invertir una
gran cantidad de tiempo en comprender el sistema.

9


---

## Pagina 10

REINGENIERIA

Los candidatos a la reingenieria aparecen

usualmente si cumplen estas condiciones:

* Frecuentes fallas de producción (fiabilidad

cuestionable).

* Problemas de rendimiento.

* Tecnología obsoleta.

* Problemas de integración del sistema.

10


---

## Pagina 11

REINGENIERIA
Los candidatos a la reingenieria aparecen
usualmente si cumplen estas condiciones:
* Código de calidad pobre.
* Dificultad (peligroso) al cambio.
* Dificultad para probar.
* Mantenimiento caro.
* Incremento de problemas del sistema.
11


---

## Pagina 12

REINGENIERIA PRESSMAN
12


---

## Pagina 13

REINGENIERIA SOMMERVILLE
   ==
13


---

## Pagina 14

REINGENIERIA PRESSMAN — SOMMERVILLE
Roger Pressman                                                     lan Sommervielle
Andlisis de inventario                                        Traduccion del código fuente
Reestructuracion de documentos                          Ingenieria inversa
Ingenieria inversa                                                  Mejora de la estructura del programa
Reestructuración de código                               Modularizacion de los programas
Reestructuracion de datos                                 Reingenieria de datos
Ingenieriería directa.
14


---

## Pagina 15

REINGENIERIA DE SOFTWARE
* Ingeniería directa: Proceso tradicional del desarrollo de
software.
* Reestructuración: Transformación de una forma de
representación a otra en el mismo nivel de abstracción,
mientras se mantenga el comportamiento externo del
sistema.
15


---

## Pagina 16

* Ingeniería inversa: Proceso de análisis de un sistema para
identificar sus componentes e interrelaciones y crear
representaciones del mismo en un mayor nivel de
abstracción.
* Reingeniería de software: Examen y modificación de un
sistema para reconstruirlo de una nueva forma.
16


---

## Pagina 17

REINGENIERIA DE SOFTWARE
* Procesos involucrados:
ANALISIS               _DISENO                _CODIGO
Ingenieria — |           Ingenieria
Directa     |           Directa
Ingeniería              Ingenieria
Inversa               Inversa
Z — — ——
- |        — Reingeniería
[ Reingemiería |
Recstricturación             Reestructuración            Reestructuración
17


---

## Pagina 18

* Los sistemas heredados son utilizados por la organización
para sus negocios. Deben mantenerse.
* Sus costos de mantenimiento tienden a incrementarse.
* Pueden tener millones de líneas de código, escritas en
lenguajes obsoletos.
18


---

## Pagina 19

SISTEMAS HEREDADOS
* Desarrollados antes de que el uso de técnicas de
ingeniería de software estuviera difundido. No están
estructurados ni documentados.
* Incrustados de conocimiento crítico del negocio que
puede no estar documentado en otro lado. No hay
especificaciones.
* El riesgo de reimplementar estos sistemas es muy alto.
19


---

## Pagina 20

CUÁNDO APLICAR REINGENIERÍA
* Los cambios son necesarios sólo en una parte del sistema.
* El soporte de hardware o software se vuelven obsoletos.
* El costo de mantenimiento del software se vuelve cada
vez más elevado.
20


---

## Pagina 21

PROCESOS DE REINGENIERIA
* Análisis de código.
* Reestructuración de procesos.
* Reestructuración de datos.
* Ingeniería inversa.
* Traducción de código.
21


---

## Pagina 22

* Análisis estático: Evaluación que estudia la estructura del
código sin ejecutarlo.
* Se evalúa su simplicidad, facilidad de comprensión,
seguimiento de estándares y comentarios, más que los
errores de programación.
* Se obtienen métricas que dan idea de la complejidad
del software analizado.
22


---

## Pagina 23

ANÁLISIS DE CÓDIGO
* Algunas métricas que se pueden obtener son:
* Número de caminos
* Accesibilidad del módulo
* Complejidad jerárquica
* Complejidad de flujos de información
* Número de niveles anidados
* Número ciclomático
* Frecuencia de comentarios
* Longitud del código
23


---

## Pagina 24

REESTRUCTURACIÓN DE PROCESOS
* Evitar construcciones no estructuradas.
* Evitar ramificaciones innecesarias.
* Revisar la complejidad en las condiciones.
* Priorizar la ejecución del camino principal sobre las
excepciones.
24


---

## Pagina 25

REESTRUCTURACIÓN DE PROCESOS
SECUENCIA   O—0
"    case
SELECCION <í>0 @Q
REPETICION CE % ? while
… repeat
25


---

## Pagina 26

REESTRUCTURACIÓN DE PROCESOS
Uh programa es estructurado si su complejidad ciclomática es
reductible a 1
e
Q                O
5       => + —
(@‘)     @
Q    [     Ol      O
. 09    O  @
-
26


---

## Pagina 27

REESTRUCTURACIÓN DE PROCESOS
* Construcciones no permitidas en un código estructurado
27


---

## Pagina 28

REESTRUCTURACIÓN DE PROCESOS
* Simplificación de condiciones:
* Eliminar operadores NOT. Invertir las condiciones
negadas.
* Realizar primero las comparaciones que más
frecuentemente definirán el valor de verdad de la
condición.
* Invertir condiciones sin sentencia THEN.
* Revisar condiciones redundantes.
28


---

## Pagina 29

REESTRUCTURACIÓN DE PROCESOS
\\ Idénticos en:
| - Funcionalidad
L         | - Interfaces
b             f - Comportamiento
29


---

## Pagina 30

REESTRUCTURACIÓN DE DATOS
* El mismo dato puede estar nombrado de diferentes
formas (sinonimia).
* El mismo nombre puede representar datos diferentes.
* El mismo dato puede tener diferentes representaciones
(estructuras, longitudes)
30


---

## Pagina 31

REESTRUCTURACIÓN DE DATOS
* Inconsistencias de datos:
* Inconsistencia en los valores de default.
* Inconsistencia en las reglas de validación.
* Inconsistencia en las unidades.
* Inconsistencia en la representación semántica.
* Inconsistencia en el manejo de valores negativos.
* Información “basura” almacenada.
31


---

## Pagina 32

REESTRUCTURACIÓN DE DATOS
* La reestructuración de datos es un proceso crítico y
costoso.
* A menudo, puede ser un proyecto independiente.
* Debe realizarse en paralelo a la reestructuración de
código.
32


---

## Pagina 33

INGENIERIA INVERSA
* A partir del código fuente, generar modelos de diseño y
análisis.
* Es un proceso complejo y caro, pero me permite conocer
el funcionamiento del módulo.
* Es necesario si el módulo debe ser mantenido.
33


---

## Pagina 34

INGENIERÍA INVERSA
* Aplicable a procesos o a datos.
* Si se conoce el diseño del módulo es más factible de ser

reutilizado.
* Mediante aplicaciones específicas es posible obtener el

código fuente a partir de código objeto.
* No es recomendable, se pierde la visibilidad de

variables y comentarios.
* Sólo es útil como auditoría o aprendizaje.

34


---

## Pagina 35

TRADUCCIÓN DE CÓDIGO
* Implica convertir el código de un lenguaje (o de una
versión de lenguaje) a otro. Por ejemplo de FORTRAN a
E
* Puede ser necesario debido a:
* Actualización de la plataforma de hardware.
* Falta de conocimiento del personal.
* Cambio en las políticas de la empresa.
* Solo se puede hacer si hay un traductor automático
disponible.
35


---

## Pagina 36

OTROS PROCESOS
* Redocumentación: Generación o actualización de la
documentación indispensable para el mantenimiento de
un sistema existente.
* Remodularización: Redefinición de los límites entre
módulos de un sistema para mejorar su cohesión. Por
afectar a las interfaces entre módulos es un proceso
arduo y complejo.
36
