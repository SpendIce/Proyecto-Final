# HU-012 — Límites del slice offline

**Estado institucional:** PENDIENTE  
**Estado técnico:** prototipo contractual offline, provisional.

## Qué demuestra

- Validación sintáctica del destinatario.
- Render determinista de asunto y cuerpo con marcador de borrador.
- Estados `PENDIENTE_VALIDACION`, `APROBADA_SEMANTICA`, `APROBADA_UTILITARIA`, `APROBADA`, `RECHAZADA`, `ENVIO_ENCOLADO`, `ENVIO_RESERVADO`, `ENVIADA_SIMULADA`, `FALLIDA` y `ENVIO_INDETERMINADO`.
- Circuito de doble aprobación (CU10 del bible): la semántica del Responsable de Gestión del Conocimiento y la utilitaria del Coordinador de Extensión, ambas obligatorias y en cualquier orden.
- Envío diferido (s4d): `ENVIO_ENCOLADO` con puerto `ColaEnvios` en memoria o durable en archivo, encolado idempotente por clave y worker `drenar_envios` con presupuesto fijo de 3 intentos, constancia auditable por intento y descarte de ítems cuyo registro ya no está pendiente.
- Idempotency key determinista y rechazo de duplicados.
- Auditoría con hashes, sin email, nombre, asunto ni cuerpo en claro.
- Entrega exclusivamente en memoria mediante `DestinoConfirmacionesFake`.
- Circuito por lote del tipo `recordatorio_pago` (catálogo `tipos_notificacion_v2`): la corrida de control de pagos planifica los recordatorios debidos del día desde el estado derivado —sin registro propio de pagos—, la plantilla provisional se aprueba una sola vez con la doble decisión, cada lote diario exige una aprobación utilitaria con la lista exacta de ítems y el drenaje va por la misma cola y el mismo fake.
- Circuito por envío del tipo `instrucciones_pago` (sexto del catálogo, D8): el correo de preinscripción con el plan de pago se genera como borrador con el `asunto_preinscripcion` del plan —exacto, sin la marca de borrador en el asunto—, la misma llave con la que la respuesta con el comprobante se asocia (§4.2); el cuerpo sale de la plantilla provisional con cuotas, medios, bonificaciones y fechas, y la validación cerrada del `datos_pago` impide borradores recortados.
- Candidatos a confirmación de inscripción (D9): la corrida enumera los preinscriptos cuya cuota 1 quedó `PAGO_CONFIRMADO` o `BONIFICADA` —un `COMPROBANTE_PRESENTADO` no alcanza (D1)— y el builder traduce el candidato a una solicitud del tipo `inscripcion`, que tramita con la doble aprobación y la entrega simulada de siempre; la repetición de la corrida es absorbida por la idempotencia del registro.

## Qué no demuestra

- No hay adapter Gmail, SMTP ni otro transporte de correo real: el envío asíncrono sólo difiere la entrega simulada, no la hace real.
- La cola es archivo o memoria inyectada; no hay broker externo (Celery/Redis diferidos) ni persistencia operativa en base: PostgreSQL sigue siendo spike.
- No se probó autenticación, permisos, cuotas, rebotes ni entrega real.
- La plantilla y los criterios no fueron aprobados por SEU.
- La plantilla de `recordatorio_pago` es provisional y sus aprobaciones en tests y matriz son simuladas; las anticipaciones `[7, 2]` son `SUPUESTO_TECNICO` pendiente de confirmación con la SEU (D15).
- La plantilla de `instrucciones_pago` es provisional y sus aprobaciones en tests y matriz son simuladas; quién dispara la generación del correo de preinscripción en la operación —la SEU o el Departamento— queda pendiente de confirmación, y el plan de pago que consume `datos_pago` es `SUPUESTO_TECNICO` del catálogo.
- La enumeración de candidatos a confirmación no envía ni registra nada por sí sola: el borrador de confirmación nace de una solicitud del circuito por envío y de la doble aprobación humana, igual que cualquier `inscripcion`.
- Las aprobaciones utilizadas en tests y matriz son simuladas y no institucionales.
- No existe lista institucional de destinatarios ni fuente live conectada.
- No acredita Gate G2 ni TRL 3.

## Fronteras de seguridad

El asunto es fijo y provisional. El destinatario rechaza CR/LF y formatos inválidos. El cuerpo se renderiza sin LLM: cualquier texto con apariencia de prompt injection permanece como dato literal y no puede activar un envío. El flag de envío falla cerrado sin las dos aprobaciones registradas y sin un fake explícito; un rol fuera del circuito invalida la decisión. En el circuito por lote, el encolado falla cerrado sin plantilla `APROBADA` y sin la lista exacta de ítems en la aprobación utilitaria; los medios de pago (links, datos bancarios) viajan en el cuerpo del borrador y nunca en la auditoría. El asunto del borrador de `instrucciones_pago` sale del plan y no lleva la marca —la marca va en el cuerpo, que es donde el destino la exige—, así que una respuesta con otro asunto o de un remitente ajeno al padrón no se asocia a la actividad.

Agregar un transporte real requiere una decisión separada, autorización institucional, gestión de secretos, pruebas de revocación y un nuevo gate de revisión.
