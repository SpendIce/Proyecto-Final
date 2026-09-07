# Diseño candidato HU-012 — orígenes de inscripción v2

- **Proceso BPM:** P5 con apoyo de P4
- **Estado:** `CANDIDATO_PENDIENTE_CONFIRMACION_SEU`
- **Contrato asociado:** `Implementacion/Agente1/src/agente1/contracts/confirmacion_inscripcion_v2.schema.json`
- **Fuente de alto nivel:** comunicación escrita de la SEU registrada el 2026-08-26; no es un acta de aprobación ni habilita operación.

## Decisión de diseño

HU-012 separa la trazabilidad por `origen_inscripcion` en lugar de asumir una única fuente. Los tres valores candidatos son `SIU_GUARANI`, `SIU_GUARANI_EXTENSION` y `GOOGLE_FORMS`.

| Origen | Actividades informadas | Adapter | Acción de A1 por ahora |
|---|---|---|---|
| `SIU_GUARANI` | Cursos, diplomaturas | No definido | Recibir sólo datos normalizados y autorizados |
| `SIU_GUARANI_EXTENSION` | Talleres | No definido | Recibir sólo datos normalizados y autorizados |
| `GOOGLE_FORMS` | Webinar, Ingeniería Por Un Día | No definido | Recibir sólo datos normalizados y autorizados |

No se codifica una restricción rígida origen/tipo hasta confirmar excepciones operativas con SEU.

## Estados y seguridad

El v2 no agrega un trigger ni un destino real. Conserva el recorrido controlado actual: `RECIBIDA` → `BORRADOR` → `PENDIENTE_VALIDACION` → `APROBADA` o `RECHAZADA`; los estados posteriores `ENVIO_RESERVADO` y `ENVIADA_SIMULADA` sólo pertenecen al fake y no representan un envío real. La clave de idempotencia debe incluir el origen además del ID institucional cuando se implemente el adapter.

No deben persistirse en el contrato de trazabilidad enlaces de pago, credenciales, secretos ni más datos personales que los estrictamente necesarios para la confirmación aprobada.

## Criterios para activar v2

1. Matriz SEU validada de origen, tipo de actividad, estado y campos disponibles.
2. Regla escrita de aprobación individual o preaprobación de plantilla para cada envío.
3. Responsable del canal, permisos mínimos y prueba negativa de bypass HITL.
4. Política de datos personales, consentimiento, retención y borrado.
5. Prueba controlada por cada origen con evidencia recuperable y sin correo real hasta la autorización correspondiente.
