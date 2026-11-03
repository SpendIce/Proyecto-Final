---
status: proposed
---

# La web de A1 verifica identidad Google y el portal P100 queda para continuidad

## Acuerdos de la entrevista con Juani (03/11/2026)

- Primera entrega: recorrido completo de gacetillas/FIE INFORMA; el resto de las funciones vigentes de A1 conserva alcance y canal durante la transición.
- Pedido inicial guiado en formulario propio: tipo de gacetilla, actividad cuando corresponda, área emisora e indicaciones adicionales; datos disponibles precargados y sin exigir una actividad para los tipos que no la necesitan.
- Un ajuste por el agente parte de la última revisión recuperada, incluidas correcciones humanas, y produce otra revisión sin sobrescribir la anterior. Los hechos institucionales siguen teniendo su fuente autorizada; la prosa editada no la reemplaza.
- La corrección admite edición manual y pedidos de ajuste al agente, con revisiones identificadas. Juani eligió Google Docs abierto aparte como editor manual para la primera entrega; A1 actualiza la vista al volver y registra la decisión sobre la revisión efectivamente revisada. No se incorpora editor propio ni se depende de un Doc privado editable embebido. Los permisos del Doc se confirman por separado del login de A1.
- Bandeja compartida de la SEU, con acciones y acceso según permisos; las personas autorizadas pueden continuar el trabajo de otras. La asignación institucional de esos permisos sigue por confirmar.
- La revisión y la decisión sobre la pieza se realizan en la web, con su sesión de acceso. Esto es distinto de la prueba guiada con la SEU.
- La primera prueba guiada puede usar un prototipo para mejorar el recorrido. Acredita lo efectivamente observado de usabilidad y contenido, no autenticación real, permisos o recuperación si se simulan.
- Para las piezas de difusión, el recorrido de A1 termina con la aprobación del borrador (o su descarte). Juani descartó pedir un registro posterior de publicación porque agrega trabajo que el agente no necesita para producir la pieza. No se infiere que una pieza aprobada haya sido publicada. Esta decisión no elimina aprobaciones de lote ni registros de envío/emisión de otras historias.
- El aporte automático de estas piezas a Historia Viva queda diferido del primer recorrido web. Juani indicó que el personal puede registrarlas allí manualmente por ahora. Se conserva la consulta a Historia Viva cuando corresponda y no se transforma aprobación en publicación.
- Se capturan automáticamente aprobación, descarte y diferencias entre la salida generada y la revisión final, vinculados a pedido, revisiones y versión del agente; el comentario es opcional. No se agregan tareas obligatorias ni se conserva prosa adicional sin definir su retención. Una aprobación después de edición humana no se cuenta como aceptación sin cambios del texto original.

El ADR conserva estado `proposed` hasta la confirmación de entendimiento compartido al cerrar la entrevista. Las preguntas Q1–Q10 sobre el recorrido fueron respondidas. Permisos institucionales, configuración de acceso y detalle técnico de persistencia/retención tienen responsables o trabajo pendiente; los acuerdos de producto no acreditan implementación ni aceptación institucional.

El circuito Form → correo → borrador → nuevo Form obliga a cambiar de contexto para corregir una pieza. César respaldó simplificarlo cuidando seguridad y usabilidad; Juani pidió cerrar una propuesta para validarla con la SEU junto con el contenido. Se propone una web propia del Agente 1 con login Google, bandeja restringida y revisión de borradores. El primer recorrido completo será gacetillas/FIE INFORMA; las otras funciones vigentes se migrarán por etapas. El portal común de los cinco agentes queda como propuesta de continuidad a acordar con sus responsables.

La web verifica la identidad en el servidor y resuelve permisos por padrón y operación; el login no otorga acceso a Google Workspace personal ni sustituye la identidad técnica del ADR 0011. Un adapter web reutiliza el núcleo de generación y las reglas de decisión, con estado durable, idempotencia y auditoría. Se propone FastAPI para la capa HTTP porque aparece esa necesidad concreta; no se lo incorpora al runtime con este ADR.

Esta propuesta reemplaza el experimento de Forms embebidos como dirección preferida, pero no declara retirado el adapter Form del ADR 0005. El cambio de canal debe probar identidad, permisos, revisión de versiones, recuperación y uso con la SEU antes de activarse. Quedan pendientes configuración institucional de login/HTTPS, detalle de persistencia/retención y permisos por confirmar. No se deduce del login un rol de aprobación para Dirección.

Se consideraron Forms embebidos —menor cambio inicial, pero conservan restricciones del recorrido y no autentican la página contenedora— y un portal P100 completo —mayor coordinación y alcance antes de validar A1—. La opción acotada permite validar usabilidad y contenido manteniendo la frontera de A1 en P4.

Diseño, DoD y condiciones de salida: [Interfaz web del Agente 1](../../Documentos/Arquitectura/Interfaz-Web-Agente-1-PPS-Juan-Ignacio-Gone.md).
