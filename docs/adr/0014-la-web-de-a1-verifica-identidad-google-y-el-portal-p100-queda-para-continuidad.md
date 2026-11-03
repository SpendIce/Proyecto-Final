---
status: proposed
---

# La web de A1 verifica identidad Google y el portal P100 queda para continuidad

El circuito Form → correo → borrador → nuevo Form obliga a cambiar de contexto para corregir una pieza. César respaldó simplificarlo cuidando seguridad y usabilidad; Juani pidió cerrar una propuesta para validarla con la SEU junto con el contenido. Se propone una web propia del Agente 1 con login Google, bandeja restringida y revisión de borradores. El primer recorrido completo será gacetillas/FIE INFORMA; las otras funciones vigentes se migrarán por etapas. El portal común de los cinco agentes queda como propuesta de continuidad a acordar con sus responsables.

La web verifica la identidad en el servidor y resuelve permisos por padrón y operación; el login no otorga acceso a Google Workspace personal ni sustituye la identidad técnica del ADR 0011. Un adapter web reutiliza el núcleo de generación y las reglas de decisión, con estado durable, idempotencia y auditoría. Se propone FastAPI para la capa HTTP porque aparece esa necesidad concreta; no se lo incorpora al runtime con este ADR.

Esta propuesta reemplaza el experimento de Forms embebidos como dirección preferida, pero no declara retirado el adapter Form del ADR 0005. El cambio de canal debe probar identidad, permisos, revisión de versiones, recuperación y uso con la SEU antes de activarse. Quedan pendientes configuración institucional de login/HTTPS, detalle de persistencia/retención y permisos por confirmar. No se deduce del login un rol de aprobación para Dirección.

Se consideraron Forms embebidos —menor cambio inicial, pero conservan restricciones del recorrido y no autentican la página contenedora— y un portal P100 completo —mayor coordinación y alcance antes de validar A1—. La opción acotada permite validar usabilidad y contenido manteniendo la frontera de A1 en P4.

Diseño, DoD y condiciones de salida: [Interfaz web del Agente 1](../../Documentos/Arquitectura/Interfaz-Web-Agente-1-PPS-Juan-Ignacio-Gone.md).
