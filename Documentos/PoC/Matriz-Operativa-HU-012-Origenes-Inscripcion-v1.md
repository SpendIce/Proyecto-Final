# Matriz operativa HU-012 por origen de inscripción

- **Fecha:** 2026-08-26
- **Proceso BPM:** P5 con apoyo de P4
- **HU:** HU-012
- **Estado:** `CANDIDATO_PENDIENTE_CONFIRMACION_SEU`
- **Artefacto:** `Implementacion/Agente1/src/agente1/contracts/matriz_origenes_inscripcion_v1.json`
- **Módulo:** `Implementacion/Agente1/src/agente1/origenes_inscripcion.py`
- **Regresión:** `Implementacion/Agente1/tests/test_matriz_origenes_inscripcion.py`
- **Artefacto adicional (tipos, 22/09):** `Implementacion/Agente1/src/agente1/contracts/tipos_notificacion_v1.json`
- **Módulo adicional (tipos):** `Implementacion/Agente1/src/agente1/tipos_notificacion.py`
- **Regresión adicional (tipos):** `Implementacion/Agente1/tests/test_tipos_notificacion.py`
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
| `CONFIRMADO_SEU` | Comunicado por escrito por la Secretaría, **o confirmado por su referente designado en una reunión registrada en acta recuperable** —el acta del 22/09 es el export del instrumento ([`Respuestas-SEU-Reunion-2026-09-22.md`](Respuestas-SEU-Reunion-2026-09-22.md)) |
| `SUPUESTO_TECNICO` | Propuesto por el equipo técnico; requiere confirmación |
| `DESCONOCIDO` | Ni comunicado ni supuesto con fundamento suficiente |

Al corte del 22/09 quedan confirmados los tipos de actividad, los campos
disponibles de ambos SIU, la regla de aprobación (plantilla preaprobada), el
canal (correo), el tratamiento (personal), el estado habilitante («inscripto
confirmado», nombre interno SIU por confirmar), el consentimiento tomado en la
inscripción y la no retención de datos por el sistema. Google Forms quedó
descartado como origen: sus tipos pasan a Guaraní Extensión. Siguen sin
confirmarse el identificador estable (`id_inscripcion`), el nombre interno del
estado en SIU, el administrador del padrón de cada entorno y el canal correo
como medio autorizado por la institución.

## 3. Matriz por origen

### 3.1 `SIU_GUARANI` — cursos y diplomaturas

| Aspecto | Estado |
|---|---|
| Hecho comunicado | La inscripción a cursos y diplomaturas se realiza en SIU Guaraní (`CONFIRMADO_SEU`) |
| Tipos de actividad | `CURSO`, `DIPLOMATURA` (`CONFIRMADO_SEU`); el 22/09 se registró que también cubre **carreras** y que la partición entre orígenes va por carga horaria (>90 h → Guaraní) (`CONFIRMADO_SEU`, acta de reunión 22/09) |
| Responsable del dato | La lista de inscriptos sale del propio SIU (`SUPUESTO_TECNICO` de diseño, registrado 22/09: la extracción se pide al administrador del entorno —quien administra el padrón sigue `DESCONOCIDO`) |
| Campos disponibles | Registrado 22/09 (`CONFIRMADO_SEU`, acta de reunión 22/09): nombre, apellido, DNI, mail, teléfono, título y —en carreras— colegio de origen. `id_inscripcion`, `lugar` y `estado_preinscripcion`: `DESCONOCIDO` |
| Estado de preinscripción | Habilita confirmar el estado «inscripto confirmado» (`CONFIRMADO_SEU`, precisión posterior al acta 22/09); el nombre interno del estado en SIU sigue `DESCONOCIDO` |
| PDF informativo | `DESCONOCIDO` en este origen: el PDF se comunicó asociado al correo posterior |
| Adapter | `NO_DEFINIDO` |
| Regla de envío | `PROHIBIDO` |

### 3.2 `SIU_GUARANI_EXTENSION` — talleres

| Aspecto | Estado |
|---|---|
| Hecho comunicado | Los talleres se inscriben en un SIU Guaraní de Extensión, con dominio diferente al inscribirse; luego se accede desde la misma web (`CONFIRMADO_SEU`) |
| Tipos de actividad | `TALLER` (`CONFIRMADO_SEU`); el 22/09 se registró además seminarios, actividades culturales y de extensión en general (`CONFIRMADO_SEU`, acta de reunión 22/09). En precisión posterior del mismo día: **también recibe lo que antes entraba por Forms: webinars, cursos e Ingeniería Por Un Día** (`CONFIRMADO_SEU`) |
| Responsable del dato | SEU (`SUPUESTO_TECNICO`: no se comunicó administrador ni referente técnico del entorno) |
| Campos disponibles | Registrado 22/09 (`CONFIRMADO_SEU`, acta de reunión 22/09): nombre, apellido, DNI, mail —subconjunto de los de 3.1, sin teléfono ni datos académicos— |
| Estado de preinscripción | Habilita confirmar el estado «inscripto confirmado» (`CONFIRMADO_SEU`, precisión posterior al acta 22/09); el nombre interno del estado en SIU sigue `DESCONOCIDO` |
| PDF informativo | `DESCONOCIDO` |
| Adapter | `NO_DEFINIDO`: sin endpoint, permisos ni contrato de extracción |
| Regla de envío | `PROHIBIDO` |

### 3.3 `GOOGLE_FORMS` — webinar e Ingeniería Por Un Día

| Aspecto | Estado |
|---|---|
| Hecho comunicado | Se usaba habitualmente para eventos gratuitos y de mayor asistencia (`CONFIRMADO_SEU`). El 22/09 la SEU comunicó que Forms se deprecaba y las inscripciones pasaban a SIU Guaraní; en precisión posterior del mismo día quedó en que **Forms ya no opera como origen: sus tipos pasan a Guaraní Extensión** (`CONFIRMADO_SEU`) |
| Trayectoria | `DEPRECADO`: el origen deja de existir para A1; webinars, cursos e Ingeniería Por Un Día se inscriben en `SIU_GUARANI_EXTENSION` (§3.2) |
| Tipos de actividad | `WEBINAR`, `INGENIERIA_POR_UN_DIA` (`CONFIRMADO_SEU`); reasignados a `SIU_GUARANI_EXTENSION` |
| Responsable del dato | `NO_APLICA`: el origen dejó de operar; el padrón es el de Guaraní Extensión (§3.2) |
| Campos disponibles | Igual perfil que 3.1 |
| Estado de preinscripción | Sin definir. Un formulario no expone estados por sí mismo |
| PDF informativo | `DESCONOCIDO`: al ser gratuitos no habría enlace de pago, pero no se confirmó si igual se envía material |
| Adapter | `NO_DEFINIDO` —y ya no corresponde especificarlo: el esfuerzo va al adapter SIU destino |
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
| `estado_preinscripcion_no_confirmado` | Habilita el estado «inscripto confirmado» (`CONFIRMADO_SEU`, precisión posterior al acta 22/09); queda confirmar el nombre interno del estado en cada SIU |
| `regla_de_aprobacion_no_definida` | El 22/09 se registró **plantilla preaprobada** igual para todos, canal **correo** y tratamiento personal preferido (`CONFIRMADO_SEU`, acta de reunión 22/09); resta confirmar quién aprueba la plantilla |
| `politica_datos_personales_no_definida` | Resuelta en lo principal el 22/09: el consentimiento para enviar correos **ya se toma en la inscripción** y **el sistema no retiene los datos** (minimización: los datos llegan con el envío y no se persisten en registros durables) (`CONFIRMADO_SEU`, precisión posterior al acta). Queda confirmar que el canal correo sea el medio autorizado por la institución |
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

## 6. Tipos de notificación (ampliación de la bible del 22/09)

La bible sincronizada el 22/09 amplió HU-012: de «confirmaciones de
inscripción» a «notificaciones automáticas de **inscripción, participación,
situación de pagos y aprobación**» para cada curso, absorbiendo la HU previa
de mensajes a deudores. La matriz por origen (secciones 1–5) responde *de
dónde sale el inscripto*; el catálogo
`contracts/tipos_notificacion_v1.json` —expuesto por
`tipos_notificacion.py`— responde el eje nuevo: *qué clase de notificación
es*, qué campos exige, de qué orígenes puede provenir el destinatario y qué
dato específico necesita el evento.

| Tipo | Evento gatillo | Dato específico | Procedencia | ¿Entra al pipeline? |
|---|---|---|---|---|
| `inscripcion` | Alta en estado «inscripto confirmado» (nombre interno SIU pendiente) | — | — | Sí (es el default; comportamiento intacto) |
| `participacion` | Participación del inscripto en la actividad (evento concreto sin definir) | `constancia_participacion` | `SUPUESTO_TECNICO` (se supone el mismo SIU) | Sí |
| `situacion_pagos` | Aviso sobre deuda/saldo (ex-HU de mensajes a deudores; evento sin definir) | `situacion_deuda_o_saldo` | **`DESCONOCIDO`** | **No** — fail-closed |
| `aprobacion` | Aprobación del inscripto en la actividad (fuente sin definir) | `condicion_aprobada` | `SUPUESTO_TECNICO` (se supone el mismo SIU) | Sí |

Reglas que fija el catálogo y verifica la regresión:

- **El catálogo es cerrado.** Un tipo fuera de él vuelve `INVALIDA` con
  `notification_type_invalid`; no hay modo de colar una clase de aviso no
  declarada.
- **`situacion_pagos` existe pero no produce nada.** El contacto del
  inscripto tiene origen confirmado; lo que no tiene origen es el dato que
  distingue al tipo (la deuda). Una solicitud de ese tipo —con o sin
  aprobación humana, por la vía síncrona o encolada— vuelve `INVALIDA` con
  `notification_type_blocked`, sin crear borrador ni registro, y la línea de
  auditoría declara el motivo (`dato_especifico_sin_origen_confirmado`).
- **Habilitado ≠ autorizado.** Que un tipo entre al pipeline sólo significa
  que puede generar borrador y seguir el circuito: la doble aprobación
  semántica + utilitaria aplica a todos los tipos, la entrega sigue siendo
  exclusivamente contra el fake, y los bloqueos de la matriz de orígenes
  (sección 4) no se levantan —son dos controles distintos.
- **`SUPUESTO_TECNICO` no bloquea el tipo, `DESCONOCIDO` sí.** El supuesto es
  una hipótesis declarada para que la SEU la corrija sobre algo concreto
  (mismo criterio que los campos de la matriz); `DESCONOCIDO` no admite ni
  siquiera modelado honesto.
- **La plantilla es una sola, como confirmó la SEU.** El render sigue siendo
  determinista y provisional; lo único que varía por tipo es el asunto base y
  la frase del evento («tu inscripción a», «tu participación en», «tu
  aprobación de»), declaradas en el catálogo. Para `inscripcion` el borrador
  resulta byte a byte idéntico al golden versionado.
- **El tipo es parte de la identidad de la comunicación:** entra al hash de
  idempotencia, así una notificación de participación sobre la misma
  inscripción no colisiona con la confirmación —es otra comunicación.

Para habilitar `situacion_pagos` la SEU tiene que responder, como mínimo: de
qué fuente sale la situación de pagos de un inscripto (SIU Guaraní, planilla
de cobranzas, otro sistema) y quién la administra; qué campos expone
(concepto, monto, vencimiento, estado) y cuáles puede usar la notificación
sin persistir datos de pago; y qué evento la dispara (deuda detectada,
vencimiento próximo, pago acreditado). Quedan en `preguntas_abiertas` del
contrato, junto con cómo se acredita participación y aprobación y si la
plantilla única alcanza para los cuatro tipos.

## 7. Criterio de actualización

Un campo pasa a `CONFIRMADO_SEU` únicamente con una respuesta escrita
recuperable, no con una conversación informal. Al cambiar la procedencia de un
campo, la regresión correspondiente debe actualizarse en el mismo incremento,
para que la matriz no pueda envejecer en silencio.
