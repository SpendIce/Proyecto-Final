# HU-012 — Límites del slice offline

**Estado institucional:** PENDIENTE  
**Estado técnico:** prototipo contractual offline, provisional.

## Qué demuestra

- Validación sintáctica del destinatario.
- Render determinista de asunto y cuerpo con marcador de borrador.
- Estados `PENDIENTE_VALIDACION`, `APROBADA_SEMANTICA`, `APROBADA_UTILITARIA`, `APROBADA`, `RECHAZADA`, `ENVIO_RESERVADO`, `ENVIADA_SIMULADA`, `FALLIDA` y `ENVIO_INDETERMINADO`.
- Circuito de doble aprobación (CU10 del bible): la semántica del Responsable de Gestión del Conocimiento y la utilitaria del Coordinador de Extensión, ambas obligatorias y en cualquier orden.
- Idempotency key determinista y rechazo de duplicados.
- Auditoría con hashes, sin email, nombre, asunto ni cuerpo en claro.
- Entrega exclusivamente en memoria mediante `DestinoConfirmacionesFake`.

## Qué no demuestra

- No hay adapter Gmail, SMTP ni otro transporte de correo real.
- No se probó autenticación, permisos, cuotas, rebotes ni entrega real.
- La plantilla y los criterios no fueron aprobados por SEU.
- Las aprobaciones utilizadas en tests y matriz son simuladas y no institucionales.
- No existe lista institucional de destinatarios ni fuente live conectada.
- No acredita Gate G2 ni TRL 3.

## Fronteras de seguridad

El asunto es fijo y provisional. El destinatario rechaza CR/LF y formatos inválidos. El cuerpo se renderiza sin LLM: cualquier texto con apariencia de prompt injection permanece como dato literal y no puede activar un envío. El flag de envío falla cerrado sin las dos aprobaciones registradas y sin un fake explícito; un rol fuera del circuito invalida la decisión.

Agregar un transporte real requiere una decisión separada, autorización institucional, gestión de secretos, pruebas de revocación y un nuevo gate de revisión.
