# Definiciones operativas comunicadas por la SEU — Agente 1

- **Fecha de registro:** 2026-08-26
- **Fuente:** respuesta escrita de la Secretaría de Extensión Universitaria (SEU), aportada al proyecto.
- **Alcance:** precisiones operativas para P4 y HU-010/HU-011; insumos para el diseño candidato de HU-012.
- **Estado:** `INSUMO_OPERATIVO_RECIBIDO`; no reemplaza un acta de validación ni habilita publicación, envío o integraciones live.

## 1. Gobierno de contenido y aprobación

| Etapa | Rol comunicado | Responsable designado | Evidencia requerida para usarla | Estado |
|---|---|---|---|---|
| Revisión de primeros borradores y criterios de redes | Revisor editorial y referente de redes | A/c Juan Manuel Gonzalez Chipont | Acta de sesión con identidad, fecha, nueve decisiones y observaciones | `PENDIENTE_DE_SESION` |
| Suplencia de revisión | Revisor editorial suplente | VS “ec” Tomás de Vergara | Acta que documente la suplencia efectiva | `PENDIENTE` |
| Diseño de gacetillas/publicaciones | Departamento de Comunicación | Departamento de Comunicación | Pieza y trazabilidad de su elaboración | `OPERATIVO_DESCRIPTO` |
| Aprobación y corrección institucional | Oficial de Comunicación Institucional | TC Sebastián Ernesto Moreira | Decisión registrada para cada pieza que se considere oficial | `PENDIENTE_DE_IMPLEMENTACION` |
| Escalamiento superior, si corresponde | Decanato | CR David Fiorito | Decisión de escalamiento y aprobación resultante | `CONDICIONAL` |

La revisión editorial no se confunde con la aprobación institucional. A1 mantiene cada salida como `BORRADOR — NO PUBLICAR` hasta que exista la decisión humana registrada que corresponda.

## 2. Gacetillas

SEU informó que no existe una plantilla oficial de gacetilla. Para una publicación oficial elevada a DGE/SGE se prepara una **nota institucional** con logos institucionales en la parte superior, texto e imágenes correspondientes, respetando las características de la gacetilla.

Esto habilita una especificación candidata, no una plantilla institucional. Antes de automatizar el formato faltan los activos aprobados, sus reglas de uso y ejemplos sanitizados o un instructivo de referencia.

## 3. HU-012: orígenes conocidos de inscripción

| Tipo de actividad | Origen comunicado | Hecho operativo conocido | Límite actual de A1 |
|---|---|---|---|
| Cursos y diplomaturas | SIU Guaraní | La inscripción se realiza en SIU Guaraní | Sin acceso ni adapter definido |
| Talleres | SIU Guaraní de Extensión | Al inscribirse usa un dominio diferente; luego puede accederse desde la misma web | Sin endpoint, permisos ni contrato de extracción definidos |
| Webinar e Ingeniería Por Un Día | Google Forms | Usado habitualmente para eventos gratuitos y de mayor asistencia | Sin ownership, trigger ni consentimiento documentados |
| Información posterior a preinscripción | Correo de Cursos Complementarios | Se comunica información adicional del curso y un PDF con información y enlace de pago | No se infiere que aplique a toda actividad ni se habilita envío automático |

El contrato `confirmacion_inscripcion_v2` clasifica estos orígenes para trazabilidad. Es candidato y no reemplaza el contrato offline activo v1 hasta validar combinaciones, estados de preinscripción, datos mínimos y regla de autorización de envío.

## 4. Fuente y habilitación de actividades

El flujo comunicado es: solicitante → Departamento de Cursos Complementarios (formulario y documentación) → Departamento de Planes y Programas y, cuando corresponda, UNDEF → aprobación → PDF final de difusión web y pieza para canales de comunicación.

Para A1, la consecuencia de diseño es fail-closed: una pieza o confirmación no debe tratar una actividad como difundible sin una referencia recuperable a su aprobación y al material final. La obligatoriedad exacta de ese campo por tipo de actividad queda pendiente de validación SEU.

## 5. Volumen de referencia para pruebas y capacidad

SEU informó como mínimo un reel mensual y dos publicaciones semanales; el promedio aproximado es de 12 publicaciones mensuales, condicionado por los eventos previstos. Se usa sólo como referencia para planificar una prueba de capacidad: no es un SLA ni una promesa de producción.

## 6. Pendientes concretos

Cada pendiente tiene ahora un artefacto que lo hace pedible por punto en lugar
de en general. El artefacto no reemplaza la definición institucional: la
prepara.

| # | Pendiente | Artefacto que lo instrumenta |
|---|---|---|
| 1 | Sesión de revisión de las nueve muestras y acta | `Validacion-SEU/` (paquete listo, sin acta) |
| 2 | Criterios por canal: tono, longitud, hashtags, CTA, reels | [`Politica-Redes-Reglas-Verificables-v1.md`](Politica-Redes-Reglas-Verificables-v1.md) |
| 3 | Activos y reglas de la nota institucional de gacetilla | [`Solicitud-Activos-Gacetilla-Agente-1.md`](Solicitud-Activos-Gacetilla-Agente-1.md) |
| 4 | Matriz tipo de actividad → origen → estado → dato → responsable | [`Matriz-Operativa-HU-012-Origenes-Inscripcion-v1.md`](Matriz-Operativa-HU-012-Origenes-Inscripcion-v1.md) |
| 5 | Aprobación individual o preaprobación de plantilla para envío | Motivo `regla_de_aprobacion_no_definida` de la matriz de orígenes |
| 6 | Datos personales, consentimiento, retención y canal autorizado | Motivo `politica_datos_personales_no_definida` de la matriz de orígenes |

El volumen de referencia del punto 5 ya fue usado para la prueba de capacidad:
`Implementacion/Agente1/evidencias/benchmark-capacidad-a1-2026-08-26.md`.

### Enunciado original de los pendientes

1. Realizar la sesión de revisión de las nueve muestras con el revisor designado o su suplente y registrar el acta.
2. Obtener los criterios por canal: tono, longitud, hashtags, CTA, uso de reels y ejemplos aprobados.
3. Recibir activos y reglas aprobadas para logos, imágenes y nota institucional de gacetilla.
4. Confirmar por escrito la matriz tipo de actividad → origen de inscripción → estado de preinscripción → dato disponible → responsable.
5. Definir si cada confirmación requiere aprobación individual o si existe una plantilla y una regla de preaprobación que habilite un envío controlado; hasta entonces, A1 no envía.
6. Definir tratamiento de datos personales, consentimiento, retención y canal autorizado antes de conectar SIU, Google Forms o correo.
