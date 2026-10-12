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

## Qué no demuestra

- No hay adapter Gmail, SMTP ni otro transporte de correo real: el envío asíncrono sólo difiere la entrega simulada, no la hace real.
- La cola es archivo o memoria inyectada; no hay broker externo (Celery/Redis diferidos) ni persistencia operativa en base: PostgreSQL sigue siendo spike.
- No se probó autenticación, permisos, cuotas, rebotes ni entrega real.
- La plantilla y los criterios no fueron aprobados por SEU.
- La plantilla de `recordatorio_pago` es provisional y sus aprobaciones en tests y matriz son simuladas; las anticipaciones `[7, 2]` son `SUPUESTO_TECNICO` pendiente de confirmación con la SEU (D15).
- Las aprobaciones utilizadas en tests y matriz son simuladas y no institucionales.
- No existe lista institucional de destinatarios ni fuente live conectada.
- No acredita Gate G2 ni TRL 3.

## Fronteras de seguridad

El asunto es fijo y provisional. El destinatario rechaza CR/LF y formatos inválidos. El cuerpo se renderiza sin LLM: cualquier texto con apariencia de prompt injection permanece como dato literal y no puede activar un envío. El flag de envío falla cerrado sin las dos aprobaciones registradas y sin un fake explícito; un rol fuera del circuito invalida la decisión. En el circuito por lote, el encolado falla cerrado sin plantilla `APROBADA` y sin la lista exacta de ítems en la aprobación utilitaria; los medios de pago (links, datos bancarios) viajan en el cuerpo del borrador y nunca en la auditoría.

Agregar un transporte real requiere una decisión separada, autorización institucional, gestión de secretos, pruebas de revocación y un nuevo gate de revisión.
