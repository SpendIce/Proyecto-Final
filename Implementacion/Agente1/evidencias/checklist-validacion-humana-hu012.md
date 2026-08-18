# HU-012 — Checklist de validación humana

**Estado:** PENDIENTE  
**Artefacto:** plantilla provisional `confirmacion_inscripcion_provisional_v1`  
**Alcance:** evaluación de borradores; no autoriza ni registra correo real.

## Identificación de la sesión

- Persona validadora: PENDIENTE de designación por SEU.
- Rol institucional: PENDIENTE.
- Fecha: PENDIENTE.
- Versión de criterios SEU: PENDIENTE.
- Identificador de muestra: PENDIENTE.

## Criterios por borrador

Marcar **Sí / No / No aplica** y agregar observaciones.

1. ¿El nombre y el email corresponden a la inscripción seleccionada?
2. ¿Actividad, fecha, lugar, organización y contacto coinciden con la fuente?
3. ¿El asunto y el cuerpo son claros y adecuados al tono institucional?
4. ¿El borrador evita promesas, aprobación o publicación no respaldadas?
5. ¿El marcador `BORRADOR — NO ENVIAR` resulta inequívoco?
6. ¿La plantilla es utilizable cuando el lugar está pendiente?
7. ¿Se aprueba, rechaza o solicita corrección del borrador?

## Gate de envío

- [ ] Existe una decisión humana trazable con persona, rol y fecha.
- [ ] La plantilla fue aprobada por SEU.
- [ ] El destinatario fue verificado contra la fuente institucional.
- [ ] Existe autorización explícita para el mecanismo de envío.
- [ ] Se probó idempotencia en el entorno autorizado.

Mientras alguna condición permanezca pendiente, **no debe existir correo real**.
Este checklist no acredita Gate G2 ni TRL 3.
