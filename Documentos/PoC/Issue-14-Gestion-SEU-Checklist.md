# Issue #14 — Paquete de gestión con la SEU

- **Issue:** `SpendIce/Proyecto-Final#14`
- **Título:** Obtener definiciones operativas y validación de la SEU
- **Agente:** Agente 1 — Extensión Bot
- **Proceso BPM:** P4 — Comunicación y Difusión Institucional, con apoyo de P5 para HU-012
- **Estado del paquete:** `READY_FOR_HUMAN`
- **Estado de cierre:** `PENDIENTE_EXTERNO`
- **Aprobación institucional:** no consta; este paquete sólo prepara la gestión de Juan.

## Propósito

Este documento consolida qué puede gestionar Juan Ignacio y qué evidencia falta
para satisfacer el issue. Es un instrumento de solicitud y seguimiento; no es
una respuesta de la Secretaría de Extensión Universitaria (SEU), no asigna
puntajes y no autoriza publicar, enviar o elevar una pieza.

La regla operativa es conservadora: una definición pasa a
`CONFIRMADO_SEU` únicamente cuando existe una respuesta escrita recuperable.
Una conversación informal, una prueba técnica en local o la conformidad del
modelo no sustituyen esa evidencia.

## Base existente

El paquete se apoya en estos artefactos ya preparados:

| Necesidad | Artefacto | Qué permite hacer ahora | Qué sigue faltando |
|---|---|---|---|
| Revisión HU-010/HU-011 | [`Validacion-SEU/`](Validacion-SEU/) | Entregar nueve muestras sintéticas, protocolo, checklist, acta vacía y manifest | Sesión real, puntajes, observaciones, identidad verificable y decisión |
| Pedido de revisión | [`Validacion-SEU/Correo-Solicitud-Revision-SEU-2026-08-26.md`](Validacion-SEU/Correo-Solicitud-Revision-SEU-2026-08-26.md) | Copiar y adaptar un correo para Juan Ignacio | Envío y respuesta a cargo de Juan; no se envía desde el repositorio |
| Criterios de redes | [`Politica-Redes-Reglas-Verificables-v1.md`](Politica-Redes-Reglas-Verificables-v1.md) | Mostrar qué controles son provisionales y qué dimensiones requieren decisión editorial | Criterios institucionales por canal y ejemplos aprobados |
| Nota institucional/gacetilla | [`Solicitud-Activos-Gacetilla-Agente-1.md`](Solicitud-Activos-Gacetilla-Agente-1.md) y [`Especificacion-Gacetilla-Nota-Institucional-v1.md`](Especificacion-Gacetilla-Nota-Institucional-v1.md) | Pedir activos, reglas y ejemplos sin inventar una plantilla oficial | Activos autorizados, reglas de uso, destino y prueba institucional |
| Orígenes HU-012 | [`Matriz-Operativa-HU-012-Origenes-Inscripcion-v1.md`](Matriz-Operativa-HU-012-Origenes-Inscripcion-v1.md) | Separar hechos comunicados de campos, estados y permisos desconocidos; mantener `fail-closed` | Matriz confirmada por origen, política de datos, aprobación y acceso autorizado |
| Definiciones recibidas | [`Definiciones-SEU-Operacion-Agente-1-2026-08-26.md`](Definiciones-SEU-Operacion-Agente-1-2026-08-26.md) | Conservar el alcance de la comunicación escrita ya aportada | No confundirla con acta de validación ni con autorización de operación |

## Matriz de aceptación del issue

| Criterio del issue | Estado legítimo al corte | Evidencia de cierre que debe obtener Juan |
|---|---|---|
| Validadores titulares y suplentes por rol | `PARCIAL`: existe una comunicación escrita sobre referentes; la participación efectiva y el acta siguen pendientes | Acta o respuesta institucional con titular, suplente, rol/área, fecha y alcance de la revisión |
| Tono, longitud, CTA, hashtags y uso de canales | `PENDIENTE_EXTERNO`: los valores del código son provisionales del equipo técnico | Guía o respuesta escrita por canal, incluidos valores “no definido” cuando corresponda |
| Activos, reglas y destino autorizado de la nota institucional/gacetilla | `PARCIAL`: SEU comunicó que no hay plantilla oficial y describió una nota institucional candidata; faltan activos y reglas | Respuesta del área competente con logos, orden, variantes, reglas, ejemplos o instructivo, destino y permisos |
| Revisión de muestra HU-010/HU-011 | `PENDIENTE_EXTERNO`: el acta y los nueve registros están vacíos | Checklist completo por muestra, fecha, puntaje, observaciones, decisión y referencia al manifest |
| Orígenes, campos, estados, responsable, aprobación y política de datos de HU-012 | `PARCIAL`: se conocen orígenes de alto nivel; el contrato permanece candidato y ningún origen habilita envío | Matriz escrita origen por origen con campos, estados habilitantes, responsable, regla de aprobación, consentimiento, retención y canal autorizado |
| Evidencia durable versionada y sanitizada | `PREPARADO`: el paquete registra hashes/IDs y evita copiar borradores o secretos | Incorporar sólo acta y respuesta sanitizadas; mantener identidades o datos sensibles fuera del issue público y de los manifests públicos |

Mientras exista una fila `PENDIENTE_EXTERNO` o `PARCIAL`, el issue no tiene
evidencia suficiente para cerrarse. En particular, `APROBADO_COMO_BORRADOR` no
significa autorización de publicación ni de envío.

## Checklist de gestión para Juan

### Antes de contactar

- [ ] Revisar [`Correo-Solicitud-Revision-SEU-2026-08-26.md`](Validacion-SEU/Correo-Solicitud-Revision-SEU-2026-08-26.md) y completar sólo datos que Juan pueda verificar.
- [ ] Adjuntar únicamente el paquete PDF de revisión y, si la contraparte lo pide, los artefactos técnicos de respaldo.
- [ ] Confirmar que las nueve piezas usan datos sintéticos y conservan `BORRADOR — NO PUBLICAR`.
- [ ] No incluir credenciales, tokens, IDs de Workspace, padrones ni datos personales reales.
- [ ] No presentar los parámetros de [`politica_redes_provisional_v1.json`](../../Implementacion/Agente1/src/agente1/politicas/politica_redes_provisional_v1.json) como política institucional.

### Solicitud mínima en una respuesta escrita

Se puede pedir una respuesta parcial. Para cada punto, la contraparte puede
responder un valor, `no definido`, `no aplica` o indicar quién debe decidirlo.

#### A. Gobierno y revisión

| Campo | Respuesta de la SEU |
|---|---|
| Titular de revisión editorial y criterios de redes (rol/área) | |
| Suplente (rol/área) | |
| Responsable de corrección/diseño de la nota institucional | |
| Responsable de aprobación institucional, si corresponde | |
| Alcance de cada rol | |

La identidad de quien efectivamente revise las muestras, la fecha y la
referencia de evidencia se completan en el acta privada de la sesión, no se
infieren de esta tabla.

#### B. Criterios de comunicación

| Canal | Registro lingüístico | Tono | Longitud | Hashtags autorizados | CTA | Emojis | ¿Reel u otro apoyo textual? |
|---|---|---|---|---|---|---|---|
| Instagram | | | | | | | |
| LinkedIn | | | | | | | |
| Otro canal (indicar) | | | | | | | |

Si un criterio todavía no existe, debe registrarse como pendiente y mantenerse
provisional en el código. La respuesta no habilita por sí sola la publicación.

#### C. Nota institucional/gacetilla

- [ ] Logos autorizados y fuente institucional de cada archivo.
- [ ] Orden, combinaciones y variantes permitidas.
- [ ] Área de resguardo, tamaño mínimo y usos prohibidos.
- [ ] Tipografía, márgenes, encabezado, pie y orden de campos.
- [ ] Imágenes: proveedor, cantidad, ubicación y derechos de uso.
- [ ] Firma, cargo, contacto y vía de elevación a DGE/SGE.
- [ ] Destino autorizado, permisos y responsable de mantener los activos.
- [ ] Uno o dos ejemplos sanitizados, o instructivo equivalente.

#### D. Sesión HU-010/HU-011

- [ ] Confirmar modalidad y fecha con la persona revisora o su suplente.
- [ ] Verificar hashes del manifest antes de revisar.
- [ ] Completar seis puntajes por cada una de las nueve muestras.
- [ ] Registrar observación concreta para todo puntaje 1 o 2.
- [ ] Marcar controles obligatorios y decisión por muestra.
- [ ] Completar decisión global, fundamento y referencia de evidencia.
- [ ] Registrar defectos reproducibles sin copiar contenido sensible.
- [ ] Si una pieza se considera oficial, registrar por separado la aprobación/corrección institucional.

#### E. HU-012

Para cada origen, solicitar explícitamente:

| Origen | Tipos de actividad | Identificador estable | Campos disponibles | Estado que habilita | Responsable del dato | Regla de aprobación | Consentimiento/retención | Canal autorizado |
|---|---|---|---|---|---|---|---|---|
| SIU Guaraní | | | | | | | | |
| SIU Guaraní de Extensión | | | | | | | | |
| Google Forms | | | | | | | | |

El correo posterior de Cursos Complementarios debe clasificarse como canal
posterior o confirmarse como otra cosa; no se lo debe tratar automáticamente
como origen de inscripción. Hasta completar esta tabla y obtener los permisos
correspondientes, HU-012 mantiene envío prohibido y sólo puede ejecutar el
slice offline con destino fake.

## Registro posterior a la gestión

Cuando Juan reciba material, debe conservar la trazabilidad sin exponer datos:

1. Guardar la respuesta institucional y el acta en un recurso autorizado, con
   acceso restringido cuando contengan identidad o información sensible.
2. Incorporar al repositorio una versión sanitizada: decisión, rol, fecha,
   alcance, IDs opacos, hashes y estado; no el contenido de correos, padrones,
   credenciales ni datos personales innecesarios.
3. Actualizar la matriz o política correspondiente y su regresión en el mismo
   incremento. Un campo no pasa a `CONFIRMADO_SEU` sólo porque el código fue
   modificado.
4. Regenerar el manifest de referencias y conservar el acta vacía original
   como antecedente sólo si la trazabilidad lo requiere.
5. Actualizar `Registro-Defectos-Agente-1.md` y la matriz de evidencia con la
   referencia recuperable, sin cerrar `DEF-A1-005`, `DEF-A1-007` o
   `DEF-A1-015` hasta satisfacer sus criterios completos.

## Límite y decisión de cierre

El equipo técnico puede dejar listo el pedido, el instrumento, la matriz
candidata y los controles `fail-closed`. No puede fabricar una respuesta de la
SEU, seleccionar validadores en nombre de la institución, puntuar muestras ni
habilitar un envío real.

Por lo tanto, al estado actual la salida correcta para el issue es:

```text
READY_FOR_HUMAN / PENDIENTE_EXTERNO
Artefactos de gestión preparados; no cerrar el issue.
```

Si no llega respuesta, Juan debe registrar el intento y mantener los estados
pendientes. No se deben sustituir los criterios faltantes por valores del
equipo técnico ni convertir una prueba local en evidencia institucional.
