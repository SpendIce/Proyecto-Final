# DSI2 Gestion de Calidad del Software

Fuente PDF: `DSI2/09 Calidad/7. Calidad.pdf`.

Markdown operativo: `DSI2/_md/09-calidad.md`.

Paginas PDF: 25. Palabras OCR extraidas: 943.

Nota: OCR automatico local con `pdftoppm` + `tesseract -l spa+eng` para busqueda y recuperacion por agentes. Puede contener errores propios de OCR; para tablas, figuras o formato exacto, consultar el PDF fuente.

---



---

## Pagina 1

Administración de la Calidad en
Proyectos de Software.
Escuela Superior Técnica
1


---

## Pagina 2

Subconjunto de la Administración de
Proyectos que incluye las actividades
necesarias para asegurar que el Proyecto
dejará satisfechos los requerimientos porslos
cuales fue encarado.
Incluye actividades de:

Planificación de la Calidad

Aseguramiento de la Calidad

Control de la Calidad

2


---

## Pagina 3

Lo que distingue a las organizaciones que se
anticipan a los problemas, es su esfuerzo
por mantener su proceso VISIBLE.
Administrando el proceso, estas
organizaciones exitosas garantizan la
calidad de todos sus productos.
3


---

## Pagina 4

Las técnicas actuales de Administración de
la Calidad reconocen la importancia de:
— La satisfacción del cliente.
La responsabilidad de la gerencia en la calidady
— La prevención en lugar del control posteriot.
4


---

## Pagina 5

Planeamiento de la Calidad
Aseguramiento de la Calidad
Control de la Calidad
5


---

## Pagina 6

f   C     | @      r    [
Identificación de los estándares de calidad
relevantes al proyecto y cómo satisfacerlos.
Genera el Plan de Calidad, donde se indica
cómo el proyecto implementará su política
de calidad
6


---

## Pagina 7

]

Evaluación regular a nivel del proyecto del
cumplimiento de los estándares de calidad.
Actividades tendientes a verificar quedos

procedimientos establecidos se aplicaron

correcta y efectivamente al proyecto.

Genera Mejoras de Calidad: Acciones que
mejoran la performance del proyecto.

,


---

## Pagina 8

Control de resultados específicos para
determinar Calidad y eliminar las causas de
no conformidad.
Actividades tendientes a encontrar defectos
existentes en el producto de software,
incluyendo todas las formas de prueba e
inspección.
8


---

## Pagina 9

Técnicas y herramientas:

Inspecciones, revisiones
— Pruebas
— Análisis estadístico
Resultados:

Resultados de conformidad / No conformidad
— Re-trabajo

Mejoras de calidad
— Ajustes al Proceso

9


---

## Pagina 10

Costos de Conformidad:
— Verificación, validación y prueba
Retrabajo, mantenimiento
— Entrenamiento y capacitación
Auditoría
10


---

## Pagina 11

Costo de No Conformidad:
— Rechazo de trabajos completos
Fallas de diseño
— Servicios y reparaciones en garantía
Exceso de gastos que no contribuyen al
producto
Quejas y mala imagen ante el cliente
11


---

## Pagina 12

Tratar de ahorrar bajando los costos de
conformidad es desastroso.
Sin un plan de calidad, el mayor costoes el
retrabajo por fallas.
Con un plan de calidad el mayor costo es en
la prevención.
12


---

## Pagina 13

                                        AHORRO
|
!    SIN PLAN DE CALIDAD     CON PLAN DE CALIDAD
13


---

## Pagina 14

Ubicación temprana de defectos
Revisiones: Se revisa el producto en forma
personal. El objetivo es encontrar defectos
antes de la compilación y prueba
Inspecciones: Hechas por pares para encontrar
problemas.
Walkthroughs: El desarrollador presenta el
producto a la audiencia. El objetivo es
comunicar y obtener aprobación. Utiles en
requerimientos y diseño

14


---

## Pagina 15

[    1
Testing:
El objetivo valido del testing es encontrar y
corregir defectos en el software.
Un objetivo adicional es mostrar que
funciona en un ambiente operativo.
15


---

## Pagina 16

La especificación de requerimientos es
esencial para la prueba.
La prueba es un esfuerzo para mostrar que,el
producto no cumple con la especificación.
El testing efectivo detecta defectos
provenientes de diferentes etapas del
proyecto (Análisis, Diseño, Desarrollo,
Implementación)
16


---

## Pagina 17

Prueba Planificada: Ejecución de los casos
de prueba planificados
Prueba de regresión: Re-prueba de los
defectos corregidos y de las áreas del
producto impactadas por la corrección.
Prueba libre: El tester utiliza libremente el
producto, intentando encontrar fallas.
17


---

## Pagina 18

ebe estar en condiciones de responder:
Debe estar en condiciones de responder
“uando va a estar el producto listo para ser

¿Cuándo va a estar el producto listo para ser

liberado?

¿Qué defectos deben ser corregidos?

¿Cuáles son las áreas de riesgo en el

(¢                      S

producto?

18


---

## Pagina 19

¿Cuándo va a estar el producto en
condiciones de ser liberado?
Cuando no haya más defectos críticos:
Debo conocer el ritmo al que se corrigen los
defectos
— Y el ritmo al que se detectan nuevos defectos,
19


---

## Pagina 20

¿Qué defectos deben ser corregidos?
Se debe comparar el costo de corregir un defeeto, con el
costo de liberar el producto con ese defecto.
Si el segundo es mayor, el defecto es crítico y debe ser
corregido.
Cualquier manipulación del código puede generar
nuevos defectos. Llegado un punto en la evolución del
proyecto, se debe suspender la corrección de todos los
defectos no críticos, aunque su costo sea casi nulo.
20


---

## Pagina 21

¿Qué áreas del producto están en riesgo?
Se reportan defectos sobre el producto, ño,sobre
las personas.
Las áreas con mayor concentración de defectos,
requieren especial atención.
21


---

## Pagina 22

Una metodología de prueba de software.
El objetivo es desarrollar y probar.en
simultáneo.
De esta forma, se detectan antes los
defectos y pueden ser corregidos
rápidamente.
22


---

## Pagina 23

Claves para el éxito:
— Crear un ejecutable diario
Probar el ejecutable generado
— Corregir los defectos encontrados y agregar
nuevas funcionalidades en el siguiente
ejecutable.
No abandonar el proceso bajo presión.
23


---

## Pagina 24

Beneficios:
— Minimiza el riesgo de Integración
Reduce el riesgo de baja calidad
— Provee una medida del progreso del desarrollo:
Alimenta la moral del equipo al tener objetivos
de corto plazo continuamente.
Mejora la relación con el cliente, porque ve
evolucionar el producto.
24


---

## Pagina 25

Para cada defecto, se debe registrar:
— Descripción
Forma de reproducirlo
— Componente en que se encuentra
Fecha de detección
— Severidad
Prioridad
Estado actual (Abierto, Corregido, Suspendido,
cerrado)
25
