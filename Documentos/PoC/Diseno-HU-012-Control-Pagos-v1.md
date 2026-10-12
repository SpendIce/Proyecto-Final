# Diseño candidato HU-012 — control de pagos v1

- **HU:** HU-012 (notificaciones de inscripción, participación, **situación de pagos** y aprobación)
- **Proceso BPM:** P5 con apoyo de P4
- **Estado del diseño técnico:** `CANDIDATO_PENDIENTE_CONFIRMACION_SEU`
- **Origen del requisito:** el Director lo incorporó a HU-012 en una entrevista con la SEU. En la bible figura como «hu que dispare mensajes a los deudores (se modificó la HU-012)». La mecánica (respuesta con comprobante, cuotas, recordatorios y verificación por la Fundación Savio) la comunicó Juani el 2026-10-07. Que el requisito exista no está en discusión; lo que falta confirmar son los detalles operativos de §9.
- **Evidencia del proceso actual:** correo real de preinscripción a una actividad arancelada enviado por el Departamento Cursos Complementarios (SEU) el 2026-10-05, con el adjunto «Datos para transferencias Fundación Savio». El original queda fuera del repo porque tiene datos personales del destinatario.
- **Reemplaza:** el bloqueo genérico `situacion_deuda_o_saldo: DESCONOCIDO` de `tipos_notificacion_v1` por un modelo de cuotas que se deriva de fuentes explícitas.

## 1. Proceso actual observado

El correo de preinscripción a una actividad arancelada trae, en este orden:

| Elemento | Valor en el ejemplo | Dato que necesita el control de pagos |
|---|---|---|
| Actividad | Curso «IA Aplicada a la Educación y Gestión: NotebookLM — Nivel 2» | `actividad` |
| Inicio | 05/10/2026 | `fecha_inicio` |
| Fecha límite de inscripción | 29/09/2026 | `fecha_limite_inscripcion` |
| Plan de pago | Cuota única de $20.000, sin matrícula | `cantidad_cuotas`, `monto_cuota`, `vencimiento` por cuota |
| Bonificación | 100 % para alumnos, personal y egresados FIE | `categorias_bonificadas` |
| Medios | Link de Mercado Pago por cuota; transferencia a la Fundación Savio (alias/CBU) | `medios_pago` (dato institucional de la actividad, no del inscripto) |
| Cierre | «Respondé a este correo adjuntando el comprobante… en el que figure número de operación» | evento que dispara el registro |

Circuito actual, según Juani:

```
SEU envía preinscripción ─▶ inscripto responde con comprobante (a cursoscomplementarios@)
   ─▶ el Departamento reenvía el comprobante a la Fundación Savio ─▶ la Fundación verifica el ingreso
```

La conciliación es manual y la acreditación la verifica la **Fundación Savio**, no la FIE.

## 2. Alcance de la modificación

`situacion_pagos` deja de ser un aviso aislado y pasa a ser un ciclo por inscripto y por cuota:

1. **Instrucciones de pago:** la notificación de preinscripción a una actividad arancelada incluye el plan de cuotas y los medios de pago, como el correo de ejemplo.
2. **Detección de comprobante:** una respuesta del inscripto con un adjunto cuenta como comprobante presentado para una cuota.
3. **Cuotas pagadas:** se informa `k de N` por inscripto.
4. **Recordatorio:** si se acerca el vencimiento de una cuota o el inicio del curso y la cuota no tiene comprobante, se prepara un recordatorio.

Fuera de alcance: cobrar, generar links de pago, consultar la cuenta bancaria o Mercado Pago, verificar acreditaciones (lo hace la Fundación), reenviar comprobantes a la Fundación (circuito del Departamento, ver §4.4), decidir bajas por falta de pago y hacer analítica de morosidad.

## 3. Modelo de dominio

### 3.1 Plan de pago (por actividad)

**Complemento documental del 2026-10-07:** Juani aportó la propuesta y el informe del curso NotebookLM Nivel 2 y confirmó que **el informe es la referencia vigente para difusión**. Ambos documentos informan cuota única de $20.000; el informe agrega transferencia y Mercado Pago. El [registro documental candidato](Registro-Actividades-Fuentes-Documentales-v1.md) conserva los antecedentes y selecciona los datos del informe. Estos archivos describen las condiciones de la actividad; no informan pagos individuales ni quién mantiene el plan en Sheets.

| Campo | Procedencia hoy |
|---|---|
| `actividad_id` | `SUPUESTO_TECNICO`: el mismo identificador de actividad del origen SIU |
| `cantidad_cuotas` (N ≥ 1) | `OBSERVADO_DOCUMENTO`: cuota única en informe p. 3 y propuesta §11 del ejemplo. Responsable de carga y origen operativo por confirmar |
| `cuotas[i].monto`, `cuotas[i].vencimiento` | Monto observado: $20.000 en ambas fuentes. Vencimiento exacto no informado. No generalizar el monto a otras actividades |
| `fecha_inicio` | El contrato actual trae una `fecha` genérica. El informe p. 2 aporta «05 de octubre», sin año explícito; el correo del ejemplo de §1 aporta 05/10/2026. Conservar cada procedencia y completar el campo específico antes de planificar |
| `categorias_bonificadas` | Informe vigente para difusión: alumnos, personal y egresados FIE; porcentaje no informado. Acreditación de la condición del inscripto sigue `DESCONOCIDO` |
| `medios_pago` | `OBSERVADO_DOCUMENTO`: transferencia y Mercado Pago en informe p. 3; sin URL de pago ni datos bancarios en ese archivo. Carga estructurada pendiente |
| `asunto_preinscripcion` | `SUPUESTO_TECNICO`: el asunto del correo de preinscripción, que sirve para asociar las respuestas a la actividad |

Propuesta: una pestaña «Plan de pagos» en la planilla del camino Workspace D2, que ya está provisionada y tiene permisos de Sheets.

### 3.2 Estado de cada cuota: derivado, no guardado

A1 **no guarda el estado de pago por inscripto**. En cada corrida lo recalcula desde las fuentes (§6):

| Estado derivado | Condición |
|---|---|
| `BONIFICADA` | El inscripto pertenece a una categoría bonificada del plan |
| `PAGO_CONFIRMADO` | La Fundación confirmó el ingreso y esa confirmación es observable (pregunta 4 de §9) |
| `COMPROBANTE_PRESENTADO` | Hay una respuesta del inscripto con un adjunto distinto, asignada a esa cuota |
| `PENDIENTE` | Ninguna de las anteriores |

- `cuotas_pagadas` = cantidad de cuotas en `COMPROBANTE_PRESENTADO`, `PAGO_CONFIRMADO` o `BONIFICADA`. En los informes se muestra desglosado («2 de 3: 1 confirmada por la Fundación, 1 con comprobante presentado»). Un comprobante no prueba el pago: solo prueba que el inscripto dice haber pagado.
- Mientras la confirmación de la Fundación no sea observable, `PAGO_CONFIRMADO` no se produce y lo máximo que A1 informa es `COMPROBANTE_PRESENTADO`. Para el recordatorio alcanza: lo que importa es no reclamarle a quien ya mandó su comprobante.
- `VENCIDA` no es un estado. Se deriva de `PENDIENTE` + `hoy > vencimiento`.

## 4. Recepción de comprobantes: reenvío automático al buzón del agente

### 4.1 Mecanismo recomendado

Las respuestas llegan a `cursoscomplementarios@`. En lugar de darle a A1 acceso a ese buzón, el Departamento configura un **filtro de Gmail con reenvío automático** hacia el buzón de la cuenta técnica de A1:

```
cursoscomplementarios@  ── filtro: subject:("Pre-Inscripción") has:attachment ──▶ reenvío a la cuenta técnica de A1
```

- El Departamento conserva su circuito actual: sigue recibiendo las respuestas y las reenvía a la Fundación como hasta ahora.
- A1 solo lee **su propio buzón**. No hay delegación ni acceso a buzones de terceros, y el principio del glosario se mantiene: recibir por un buzón no otorga los permisos de ese buzón.
- El reenvío por filtro conserva el remitente original. Hay que verificarlo en la prueba controlada, porque la asociación (§4.2) depende de eso.

Requisitos:

| Requisito | Quién |
|---|---|
| El dominio permite el reenvío automático a direcciones internas (opción de la consola de administración) | DSI |
| El Departamento agrega la cuenta técnica de A1 como dirección de reenvío. Google manda un código de confirmación a la cuenta destino, y el operador técnico de A1 lo lee | Departamento + Juani |
| Se crea el filtro con el criterio acordado | Departamento |
| A1 obtiene `gmail.readonly` **sobre su propia cuenta**, sin domain-wide delegation | DSI (enmienda al issue #15) |

**Enmienda al pedido DSI.** El paquete del issue #15 declara «Gmail API fuera de este alcance». Esa exclusión la escribimos nosotros en el pedido; DSI no la decidió. Hay que cambiarla a «Gmail API de solo lectura sobre el buzón propio de la cuenta técnica, sin delegación». El proyecto GCP está dentro de la organización y tiene la consent screen en Internal, así que un scope restringido no requiere verificación de Google. Existe una alternativa más chica, `gmail.metadata`, que solo da encabezados. Con ella no se pueden distinguir comprobantes duplicados por contenido, así que no se recomienda.

### 4.2 Asociación respuesta → inscripto y actividad

En orden y sin aproximaciones:

1. **Actividad:** el asunto de la respuesta («Re: Pre-Inscripción …») tiene que coincidir con el `asunto_preinscripcion` del plan, después de normalizar `Re:`/`RV:` y espacios.
2. **Inscripto:** el remitente tiene que coincidir con el `email_destinatario` de **una sola** inscripción de esa actividad, según el padrón del origen SIU.
3. Si la coincidencia falla o no es única, la respuesta queda en **no asociadas**. Se lista en el informe de la corrida para que una persona la resuelva. Nunca se asocia por nombre ni por similitud.

Si alguien responde desde otra dirección (por ejemplo, desde su correo personal en vez del que figura en SIU), el Departamento puede cargar la correspondencia en la pestaña «Novedades de pago» (§6.2).

### 4.3 Contenido de la respuesta

- El cuerpo y los adjuntos son **entrada no confiable** (ADR 0001): no llegan como instrucción a ningún modelo.
- La señal es que haya al menos un adjunto PDF o imagen. Extraer el número de operación, el monto o la fecha por OCR puede ayudar a quien revisa, pero nunca cambia un estado por sí solo.
- Los comprobantes distintos de un inscripto se cuentan por el `sha256` del adjunto, que se calcula en cada corrida y no se guarda. Mandar dos veces la misma captura no cuenta como dos cuotas.
- Asignación a cuotas: los comprobantes distintos se asignan en orden cronológico a las cuotas no bonificadas, de la 1 a la N. Si un solo comprobante cubre dos cuotas, se corrige en «Novedades de pago».

### 4.4 Reenvío a la Fundación Savio

Hoy lo hace el Departamento a mano. Se podría automatizar con un segundo filtro en `cursoscomplementarios@`, pero esa configuración es del Departamento y de la Fundación, no de A1. A1 no envía comprobantes a terceros.

## 5. Recordatorios

### 5.1 Regla de disparo

Para cada cuota derivada como `PENDIENTE`:

```
fecha_referencia = cuota.vencimiento  (si no está definido: fecha_inicio de la actividad)
debe_recordar    = hoy ∈ {fecha_referencia − d : d ∈ anticipaciones}
```

- `anticipaciones`: `SUPUESTO_TECNICO` [7, 2] días, configurable por actividad.
- No hay recordatorios después del vencimiento, porque eso ya sería gestión de deuda (D4).
- Zona horaria: `America/Argentina/Buenos_Aires`.
- Antes de armar el lote, la corrida vuelve a leer el buzón. Si alguien mandó su comprobante a la mañana, no recibe el recordatorio esa tarde.

### 5.2 Idempotencia

La clave `sha256(actividad_id, id_inscripcion, nro_cuota, anticipacion_d)` identifica cada recordatorio en el registro durable que HU-012 ya tiene. Si el proceso corre dos veces el mismo día, no sale un recordatorio duplicado. El recordatorio persiste lo mismo que cualquier notificación de HU-012: el registro guarda asunto y cuerpo del borrador bajo la clave hash, y la cola guarda el destinatario mientras el envío está pendiente. No hay un registro de pagos.

### 5.3 Validación humana

Hoy cada envío de HU-012 exige aprobación semántica y aprobación utilitaria. Si se aprueba recordatorio por recordatorio, la automatización no ahorra trabajo. Propuesta (D3): **plantilla de recordatorio preaprobada una vez** con doble aprobación, más una **aprobación utilitaria del lote del día** (destinatarios, cuota y fecha). La aprobación del lote también actúa como red de seguridad: si un correo se borró del buzón y una cuota volvió a figurar como pendiente, la persona que aprueba lo puede notar.

### 5.4 Contenido

El recordatorio repite los medios de pago del plan y la instrucción «respondé con el comprobante». Los links y los datos bancarios salen del plan al renderizar y no se persisten en la auditoría.

## 6. Datos personales: recálculo en lugar de estado

### 6.1 Fuentes de cada corrida

```
plan de pagos (planilla D2)  ┐
padrón de la actividad (SIU) ├─▶ derivar_estados(hoy) ─▶ cuotas por inscripto ─▶ planificar_recordatorios(hoy)
buzón propio de A1 (Gmail)   │                                                  └─▶ informe: k de N, no asociadas
novedades de pago (planilla) ┘
```

Nada de lo derivado se guarda en A1. La fuente de verdad del pago queda donde ya estaba: los correos, bajo custodia institucional en Workspace. Esto respeta la minimización que la SEU confirmó el 22/09: A1 procesa datos personales durante la corrida y no los retiene.

### 6.2 Correcciones humanas: pestaña «Novedades de pago»

Lo que no se puede deducir de los correos lo carga el Departamento en una pestaña de la planilla D2. Es su propio registro y no un estado de A1:

| Columna | Uso |
|---|---|
| `id_inscripcion` | Inscripto afectado |
| `tipo` | `CONFIRMADO_FUNDACION` · `COMPROBANTE_RECHAZADO` · `COMPROBANTE_CUBRE_N_CUOTAS` · `EMAIL_ALTERNATIVO` · `BONIFICADO` |
| `valor` | Cuota, cantidad o dirección, según el tipo |
| `fecha`, `responsable` | Trazabilidad |

Las novedades se aplican después de lo derivado del buzón y tienen precedencia sobre esa derivación.

### 6.3 Límites del recálculo

| Riesgo | Mitigación |
|---|---|
| Se borra un correo y una cuota vuelve a quedar `PENDIENTE` | El reenvío deja una copia en el buzón de A1, independiente de la del Departamento; además está la aprobación del lote (§5.3) |
| El inscripto responde desde otra dirección | Queda en «no asociadas» y se resuelve con `EMAIL_ALTERNATIVO` |
| El asunto de la respuesta cambia | Queda en «no asociadas»; no se adivina |
| Costo de releer el buzón | Bajo: el filtro limita los mensajes a preinscripciones con adjunto, y el volumen de la SEU es chico |

## 7. Impacto técnico

- `tipos_notificacion_v1` → v2: `situacion_pagos` pasa a tener subtipos `instrucciones_pago` y `recordatorio_vencimiento`. El dato específico deja de ser `situacion_deuda_o_saldo` y pasa a ser `plan_pago` + estado derivado de la cuota.
- Contrato nuevo `plan_pagos_actividad_v1.schema.json`.
- `pagos.py`: `derivar_estados(plan, padron, mensajes, novedades) → estados por cuota` y `planificar_recordatorios(plan, estados, hoy) → lote`. Son funciones puras que se prueban sin red ni reloj.
- Puerto `BuzonPropio` (listar mensajes reenviados, encabezados y hashes de adjuntos) con `BuzonPropioFake`. El adapter Gmail de solo lectura depende de la enmienda a #15.
- Se reutilizan: registro durable de claves, cola de envío (s4d), doble aprobación y destino fake.
- No cambia: fail-closed, `BORRADOR — NO PUBLICAR`, ningún correo real sin el adapter autorizado.

El núcleo (derivación, planificación, contrato y fakes) se puede implementar ya, sin esperar a DSI. El buzón live y el filtro dependen de DSI y del Departamento.

## 8. Decisiones (grilling del 2026-10-07)

| ID | Decisión | Estado |
|---|---|---|
| D1 | ¿Un comprobante es un pago? | **Resuelta:** no. La Fundación Savio verifica el ingreso. A1 informa `COMPROBANTE_PRESENTADO`, y `PAGO_CONFIRMADO` solo sale de una novedad `CONFIRMADO_FUNDACION` |
| D2 | ¿Cómo llega el comprobante a A1? | **Resuelta:** filtro de reenvío del Departamento hacia el buzón propio de A1 + `gmail.readonly` sobre esa cuenta (ADR 0004) |
| D3 | ¿Cómo se aprueban los recordatorios? | `SUPUESTO_TECNICO`: plantilla preaprobada con doble aprobación + aprobación utilitaria de cada lote diario. Se consulta a la SEU |
| D4 | ¿Hay recordatorios después del vencimiento? | `SUPUESTO_TECNICO`: no. Se consulta a la SEU |
| D5 | ¿Se persiste estado por inscripto? | **Resuelta:** no. Se recalcula en cada corrida (ADR 0003) |
| D6 | ¿Cabe en el cierre 2026-11? | El núcleo sin conexiones, sí. Los adapters de Gmail entran con la prueba en vivo restringida de D12 |
| D7 | ¿A quién se le recuerda? | **Resuelta:** a preinscriptos con la cuota 1 sin pagar y a inscriptos con cuotas posteriores pendientes. El primer corte cubre solo a los preinscriptos |
| D8 | ¿Quién envía la preinscripción con las instrucciones de pago? | **Resuelta:** en el primer corte, el Departamento, como hoy. **El objetivo es que la envíe A1** como borrador de HU-012 con doble aprobación, porque HU-012 busca que las notificaciones salgan por correo directamente |
| D9 | ¿Qué convierte a un preinscripto en inscripto? | `SUPUESTO_TECNICO`: el pago confirmado de la cuota 1 (novedad `CONFIRMADO_FUNDACION`) o la bonificación. Es lo que dispara la confirmación de inscripción. Se consulta a la SEU; si el SIU lleva ese estado, la fuente pasa a ser el SIU |
| D10 | ¿De dónde sale el padrón? | **Resuelta:** CSV en las pruebas y pestaña de la planilla D2 en la demo. La exportación periódica y la conexión con el SIU se definen con el conector |
| D11 | ¿Se usa Gmail sin esperar a DSI? | **Resuelta (Juani):** sí. Se habilita Gmail API, se agregan `gmail.send` y `gmail.readonly` y se vuelve a autorizar la cuenta técnica. Después se informa a DSI cómo queda funcionando |
| D12 | ¿A quién puede escribir A1? | **Resuelta:** solo a una lista de direcciones de prueba, hasta que la SEU apruebe la plantilla de cada tipo. Un destinatario fuera de la lista se rechaza antes de enviar, aunque el envío tenga las dos aprobaciones. Pasar a destinatarios reales es un cambio de configuración |
| D13 | ¿Qué cuenta como comprobante? | **Resuelta:** cualquier adjunto PDF o imagen en una respuesta asociable. Sin OCR en el primer corte |
| D14 | ¿Qué pasa con un bonificado que el padrón no identifica? | **Resuelta:** columna opcional `bonificado` en el padrón. Si falta y el plan tiene bonificaciones, el recordatorio se arma igual y aparece en el lote marcado «bonificación no verificable» |
| D15 | ¿Con cuánta anticipación se recuerda? | `SUPUESTO_TECNICO`: 7 y 2 días antes. Para la cuota 1 del preinscripto se cuenta desde la fecha límite de inscripción, y si no existe, desde el inicio |
| D16 | ¿Cómo se prueba en vivo? | **Resuelta:** respuestas armadas a mano enviadas desde la cuenta de Juani al bot, para las pruebas repetibles, y una prueba del filtro de reenvío en el buzón propio de Juani para verificar que se conserva el remitente. Nunca se le mandan comprobantes falsos al Departamento |

### Orden de trabajo

| Corte | Contenido | Depende de |
|---|---|---|
| 1 | Contrato del plan de pago y lectura desde CSV y desde una pestaña de la planilla, con el caso NotebookLM cargado | — |
| 2 | Puerto `BuzonPropio` + fake, asociación y «no asociadas», pestaña de novedades, derivación pura de `k de N` | — |
| 3 | Planificador puro de recordatorios, clave de idempotencia, lote con aprobación utilitaria, entrega fake | 1, 2 |
| 4 | `tipos_notificacion_v2`: `recordatorio_pago` habilitado sin conexión; `instrucciones_pago` y la confirmación de inscripción por pago confirmado como borradores | 3 |
| 5 | Adapters de Gmail de lectura y envío por detrás de los puertos, con transporte fake y lista de direcciones de prueba (D12). Cubre la tarea del Gantt «Adapter de correo real HU-012» (12–23/10) | — (la prueba en vivo depende de D11) |

## 9. Preguntas para la SEU (las lleva Juani en persona; se suman al issue #14)

**Plan de pago y actividad**

1. Con el informe como referencia vigente para difusión, ¿quién carga el plan de pago de cada actividad (cuotas, montos, vencimientos, bonificaciones) y dónde? ¿Sirve una pestaña «Plan de pago» en la planilla?
2. En una cuota única, ¿qué fecha manda para el recordatorio: la fecha límite de inscripción o el inicio del curso? Si hay varias cuotas, ¿cada una tiene su propio vencimiento?
3. ¿El asunto del correo de preinscripción es estable por actividad? ¿Se puede fijar un formato («Pre-Inscripción <actividad>»)?

**Pago y verificación**

4. ¿El Departamento registra los pagos en SIU Guaraní Extensión? ¿El SIU tiene un estado como «pago pendiente» o «confirmado» que alguien actualice?
5. ¿Cómo y por dónde informa la Fundación Savio que verificó un ingreso: por correo, con un listado, o no lo informa?
6. ¿Qué convierte a un preinscripto en inscripto: el comprobante, la verificación de la Fundación o un cambio en el SIU? (Supuesto actual: la verificación de la Fundación.)
7. ¿Cómo se acredita que alguien es alumno, personal o egresado FIE para la bonificación? ¿Lo declara en la preinscripción o se valida contra el SIU?
8. ¿Qué pasa con quien no pagó al inicio del curso? (Solo para saber dónde termina el aviso; A1 no decide bajas.)

**Recordatorios**

9. ¿Alcanza con aprobar la plantilla del recordatorio una vez y después aprobar cada lote diario, o hay que aprobar uno por uno?
10. ¿Se mandan recordatorios después del vencimiento? (Supuesto actual: no.)
11. ¿Les parece bien avisar 7 y 2 días antes?
12. ¿La respuesta con comprobante tiene que recibir un acuse automático?

**Circuito de correo**

13. ¿El Departamento puede configurar en `cursoscomplementarios@` un filtro que reenvíe al buzón del agente las respuestas con adjunto a la preinscripción?
14. ¿Cuánto tiempo pueden quedar esas respuestas en el buzón del agente? ¿Hasta el cierre administrativo de la actividad?
15. Objetivo de HU-012: ¿aceptan que el correo de preinscripción con las instrucciones de pago lo genere el agente, con las dos aprobaciones, en lugar de redactarlo a mano?

**Padrón y SIU**

16. ¿El SIU puede exportar periódicamente y de forma automática los preinscriptos de una actividad (planilla o CSV)? ¿Quién lo administraría?
