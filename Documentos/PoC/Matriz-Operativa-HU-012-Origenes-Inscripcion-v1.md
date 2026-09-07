# Matriz operativa HU-012 por origen de inscripción

- **Fecha:** 2026-08-26
- **Proceso BPM:** P5 con apoyo de P4
- **HU:** HU-012
- **Estado:** `CANDIDATO_PENDIENTE_CONFIRMACION_SEU`
- **Artefacto:** `Implementacion/Agente1/src/agente1/contracts/matriz_origenes_inscripcion_v1.json`
- **Módulo:** `Implementacion/Agente1/src/agente1/origenes_inscripcion.py`
- **Regresión:** `Implementacion/Agente1/tests/test_matriz_origenes_inscripcion.py`
- **Antecedente:** `Diseno-HU-012-Origenes-Inscripcion-v2.md`
- **Clasificación:** diseño técnico candidato, sin credenciales, URLs privadas ni datos personales reales; requiere confirmación escrita de la SEU.

## 1. Propósito y límite

La SEU comunicó **dónde** se inscribe cada tipo de actividad. No comunicó
identificadores, estados de preinscripción, responsables del dato ni regla de
autorización de envío. Esta matriz separa una cosa de la otra por cada origen,
de modo que el adapter futuro pueda especificarse sin conectar SIU Guaraní,
Google Forms ni correo, y de modo que lo que falta se pueda pedir por punto en
lugar de pedirlo en general.

La matriz **no habilita envío en ningún caso**. Está declarado en el artefacto
(`x-habilita-envio: false`) y verificado por regresión: cada origen devuelve una
decisión negativa con sus motivos enumerados.

## 2. Procedencia del dato

Cada afirmación de la matriz lleva su procedencia, porque la diferencia importa
para el gate:

| Procedencia | Significado |
|---|---|
| `CONFIRMADO_SEU` | Comunicado por escrito por la Secretaría |
| `SUPUESTO_TECNICO` | Propuesto por el equipo técnico; requiere confirmación |
| `DESCONOCIDO` | Ni comunicado ni supuesto con fundamento suficiente |

Hoy **ningún campo contractual necesario para emitir una confirmación está en
`CONFIRMADO_SEU`**. Sí hay metadatos de contexto confirmados en el cuarto
registro —por ejemplo, el área que emite el correo posterior y la existencia
del PDF—, pero no alcanzan para habilitar una confirmación ni un envío.

## 3. Matriz por origen

### 3.1 `SIU_GUARANI` — cursos y diplomaturas

| Aspecto | Estado |
|---|---|
| Hecho comunicado | La inscripción a cursos y diplomaturas se realiza en SIU Guaraní (`CONFIRMADO_SEU`) |
| Tipos de actividad | `CURSO`, `DIPLOMATURA` (`CONFIRMADO_SEU`) |
| Responsable del dato | Departamento de Cursos Complementarios (`SUPUESTO_TECNICO`: fue descripto como puerta de entrada de la solicitud, no como administrador del padrón) |
| Campos disponibles | `id_inscripcion`, `lugar`, `contacto` y `estado_preinscripcion`: `DESCONOCIDO`. Nombre, correo, actividad, fecha y organiza: `SUPUESTO_TECNICO` |
| Estado de preinscripción | Sin lista validada ni criterio de qué estado habilita confirmar |
| PDF informativo | `DESCONOCIDO` en este origen: el PDF se comunicó asociado al correo posterior |
| Adapter | `NO_DEFINIDO` |
| Regla de envío | `PROHIBIDO` |

### 3.2 `SIU_GUARANI_EXTENSION` — talleres

| Aspecto | Estado |
|---|---|
| Hecho comunicado | Los talleres se inscriben en un SIU Guaraní de Extensión, con dominio diferente al inscribirse; luego se accede desde la misma web (`CONFIRMADO_SEU`) |
| Tipos de actividad | `TALLER` (`CONFIRMADO_SEU`) |
| Responsable del dato | SEU (`SUPUESTO_TECNICO`: no se comunicó administrador ni referente técnico del entorno) |
| Campos disponibles | Igual perfil que 3.1 |
| Estado de preinscripción | Sin definir |
| PDF informativo | `DESCONOCIDO` |
| Adapter | `NO_DEFINIDO`: sin endpoint, permisos ni contrato de extracción |
| Regla de envío | `PROHIBIDO` |

### 3.3 `GOOGLE_FORMS` — webinar e Ingeniería Por Un Día

| Aspecto | Estado |
|---|---|
| Hecho comunicado | Se usa habitualmente para eventos gratuitos y de mayor asistencia (`CONFIRMADO_SEU`) |
| Tipos de actividad | `WEBINAR`, `INGENIERIA_POR_UN_DIA` (`CONFIRMADO_SEU`) |
| Responsable del dato | SEU (`SUPUESTO_TECNICO`). **Dato crítico faltante:** quién es dueño del formulario y de la planilla de respuestas, necesario tanto para permisos como para responsabilidad sobre datos personales |
| Campos disponibles | Igual perfil que 3.1 |
| Estado de preinscripción | Sin definir. Un formulario no expone estados por sí mismo |
| PDF informativo | `DESCONOCIDO`: al ser gratuitos no habría enlace de pago, pero no se confirmó si igual se envía material |
| Adapter | `NO_DEFINIDO` |
| Regla de envío | `PROHIBIDO` |

### 3.4 `CORREO_CURSOS_COMPLEMENTARIOS` — canal posterior, no origen

| Aspecto | Estado |
|---|---|
| Hecho comunicado | Tras la preinscripción se comunica información adicional del curso y un PDF con información y enlace de pago (`CONFIRMADO_SEU`) |
| Clasificación | `CANAL_POSTERIOR`. No es un origen de preinscripción y por eso **no** integra el enum del contrato |
| Responsable del dato | Departamento de Cursos Complementarios (`CONFIRMADO_SEU`) |
| PDF informativo | `CONFIRMADO_SEU`, producido por ese departamento |
| Regla de envío | `PROHIBIDO`, con el motivo adicional `canal_no_es_origen_de_inscripcion` |

Este cuarto elemento se modela explícitamente para evitar el error de diseño de
tratar «hay un correo que se manda después» como «existe un circuito de envío
que A1 puede ocupar». Son cosas distintas: la primera está confirmada, la
segunda no.

**Consecuencia sobre el contrato:** el PDF trae enlace de pago. El contrato
`confirmacion_inscripcion_v2` admite una referencia controlada al material
informativo y no tiene ningún campo de pago; la regresión verifica que siga sin
tenerlo.

## 4. Motivos de bloqueo y a qué pregunta corresponde cada uno

| Motivo | Definición institucional que lo levanta |
|---|---|
| `origen_sin_adapter` | Endpoint, permisos y contrato de extracción por origen |
| `combinacion_origen_tipo_no_confirmada` | Confirmación de qué tipos se inscriben por cada origen, con sus excepciones |
| `estado_preinscripcion_no_confirmado` | Lista de estados y cuál habilita emitir una confirmación |
| `regla_de_aprobacion_no_definida` | Aprobación individual por confirmación o plantilla preaprobada con regla de habilitación |
| `politica_datos_personales_no_definida` | Tratamiento, consentimiento, retención, borrado y canal autorizado |
| `canal_no_es_origen_de_inscripcion` | No corresponde levantarlo: es una clasificación, no una brecha |

Los estados de preinscripción candidatos —`PREINSCRIPTO`, `INSCRIPTO`,
`PAGO_PENDIENTE`, `CONFIRMADO`, `BAJA`— están marcados `SUPUESTO_TECNICO` y
sirven sólo para que la SEU corrija sobre una lista concreta en vez de responder
en abstracto.

## 5. Qué destraba esto y qué no

**Destraba:** la especificación del adapter puede escribirse ahora, porque cada
origen tiene declarados sus campos, su responsable presunto, su clasificación y
sus bloqueos. También permite que la conversación con la SEU sea por campo y por
origen.

**No destraba:** la implementación del adapter, que requiere las seis
definiciones de la sección 4 más el acceso. Mientras tanto HU-012 conserva su
baseline offline con contrato v1, destino fake y aprobación humana explícita.

## 6. Criterio de actualización

Un campo pasa a `CONFIRMADO_SEU` únicamente con una respuesta escrita
recuperable, no con una conversación informal. Al cambiar la procedencia de un
campo, la regresión correspondiente debe actualizarse en el mismo incremento,
para que la matriz no pueda envejecer en silencio.
