# HU-014 — Límites del slice offline

**Estado institucional:** PENDIENTE
**Estado técnico:** prototipo contractual offline, provisional.

## Qué demuestra

- Render determinista del texto canónico del certificado, para los tipos cerrados `ASISTENCIA` y `APROBACION`.
- Generación de PDF mínimo con stdlib solamente, determinista byte a byte (sin timestamps ni IDs aleatorios), con marca `BORRADOR — NO EMITIR` en toda salida previa a la aprobación completa.
- Estados `PENDIENTE_VALIDACION`, `APROBADA_SEMANTICA`, `APROBADA_UTILITARIA`, `APROBADA`, `RECHAZADA`, `EMISION_RESERVADA`, `EMITIDA_SIMULADA`, `FALLIDA` y `EMISION_INDETERMINADA`.
- Circuito de doble aprobación (CU10 del bible, mismo catálogo de roles provisional que HU-012): la semántica del Responsable de Gestión del Conocimiento y la utilitaria del Coordinador de Extensión, ambas obligatorias y en cualquier orden.
- Idempotency key determinista, rechazo de duplicados y registro durable por archivo que sobrevive al reinicio, con reconciliación de reservas colgadas hacia `EMISION_INDETERMINADA` sin reemitir.
- Auditoría con hashes, sin nombre, documento, título ni texto del certificado en claro; `pdf_hash` registra el artefacto emitido.
- Emisión exclusivamente en memoria mediante `DestinoCertificadosFake`.
- Desde `certificado_emision_v2` (#74), la línea descriptiva por actividad redactada por el modelo con gates deterministas, su aprobación una vez por actividad por el Form de decisiones (`linea_descriptiva-<id_actividad>-<hash>`, `apruebo_semantica` + `apruebo_utilitaria` por rol) y la precondición del lote de cierre (`apruebo_lote`) antes de cualquier emisión con línea. Las variables `id_actividad`, `modalidad` y `carga_horaria` son datos del registro interpolados por la plantilla, nunca texto del modelo.

## Qué no demuestra

- No hay adapter de emisión real: ni carpeta de Drive, ni registro institucional, ni transporte alguno.
- No hay firma digital: el enunciado la menciona, pero el DoD no la exige y no existe infraestructura de firma; el PDF lo declara en su propio texto.
- La plantilla es provisional: la plantilla institucional de certificados queda `PENDIENTE_SEU` (diseño, logo, firmantes y formato finales son definiciones de la SEU).
- No se probó validez del PDF contra un lector institucional ni accesibilidad; es un artefacto de texto mínimo para verificar el pipeline.
- Las aprobaciones utilizadas en tests y matriz son simuladas y no institucionales.
- No existe lista institucional de titulares ni fuente live conectada (el trigger por estado "Aprobado" es HU-015/HU-016, fuera de este slice).
- La emisión en vivo del certificado y la lista de participantes del lote de cierre son alcance de #75: este slice sólo deja verificable la precondición de autorización en el `RegistroDecisiones`. El recorrido live con el Form real queda para la ejecución del operador en D2, como en #72.
- La línea descriptiva se ensayó offline con generador fake y decisiones simuladas en la auditoría del registro; no hay línea generada por un modelo en producción ni aprobación institucional real.
- No acredita Gate G2 ni TRL 3.

## Fronteras de seguridad

El tipo de certificado es un catálogo cerrado: un valor fuera de él invalida la solicitud antes de generar. El texto se renderiza sin LLM: cualquier texto con apariencia de prompt injection permanece como dato literal y no puede activar una emisión. El flag de emisión falla cerrado sin las dos aprobaciones registradas y sin un fake explícito; un rol fuera del circuito invalida la decisión. El registro durable guarda el texto del borrador con permisos `0700`/`0600`, mientras que la auditoría sigue llevando sólo hashes.

Agregar un destino de emisión real, una plantilla institucional o firma digital requiere una decisión separada, autorización institucional, gestión de secretos, pruebas de revocación y un nuevo gate de revisión.
