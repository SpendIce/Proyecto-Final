---
status: accepted
confirmed_by: Juan Ignacio Goñe
confirmed_on: 2026-11-11
---

# El canal web de A1 persiste en PostgreSQL con retención mínima

La web del Agente 1 ([ADR 0014](https://github.com/SpendIce/Proyecto-Final/blob/planning/validacion-seu-a1-2026-11-04/docs/adr/0014-la-web-de-a1-verifica-identidad-google-y-el-portal-p100-queda-para-continuidad.md), todavía en la rama `planning/validacion-seu-a1-2026-11-04`) necesita guardar algo que hoy A1 no guarda: en el canal del Form la prosa de la solicitud queda en la hoja de respuestas de Google; en la web no hay hoja, así que A1 tiene que conservarla mientras la procesa. Además, la decisión debe quedar atada a la revisión vigente y sobrevivir a una caída. Juani fijó el 11/11/2026 una **retención mínima**: guardar sólo lo indispensable para operar, recuperar y dejar trazabilidad, por el menor plazo posible ([issue #151](https://github.com/SpendIce/Proyecto-Final/issues/151)).

Decidimos que **el estado del canal web vive en PostgreSQL**, en un contenedor propio del stack de A1, partiendo del esquema del spike (`persistencia.py`, migraciones 0001–0003), y que **la única tabla con texto es la de prosa transitoria**, que se purga.

## Qué se guarda y por cuánto

- **Solicitud y revisiones.** Cada solicitud web tiene **un único Google Doc**; A1 escribe ahí cada revisión nueva. En la base quedan el número de revisión, el hash del contenido y el `headRevisionId` de Drive; las revisiones anteriores quedan en el historial de Drive. Mapeo sobre el spike: solicitud = solicitud web; ejecución + borrador = revisión; validación = decisión (descartada = `RECHAZADA`, una por revisión); eventos = auditoría. Lo que falta (canal y fuente `web`, `headRevisionId`, revisión vigente, estado vencido) entra por migraciones 0004 en adelante.
- **Prosa transitoria.** La descripción de la solicitud, el texto de cada pedido de ajuste y el texto que A1 generó para la revisión vigente van a una tabla aparte. Se conservan sólo mientras la solicitud está abierta y se ponen en `NULL` en la primera purga diaria después de que queda aprobada, descartada o vencida. Una solicitud sin actividad durante **30 días** pasa a **vencida** (el mismo plazo que la ventana de reconciliación).
- **Señales de edición.** Al aprobar, A1 compara el texto generado con el Doc reimportado y guarda sólo métricas: aceptada sin cambios o con cambios, proporción de texto cambiado y cantidad de ajustes. Después el texto se purga con el resto de la prosa transitoria.
- **Auditoría sin plazo y sin texto.** Identificador de solicitud y revisión, hash del contenido aprobado, hash del correo, rol, decisión, fecha y versión del agente. Se conserva sin purga: es la trazabilidad (CU06). No contiene prosa ni identidad en claro.
- **Sesión web sólo en memoria.** Guarda el `sub` de Google y el rol resuelto, nunca el token. Vence a los 30 minutos sin actividad o a las 8 horas. Un reinicio obliga a volver a entrar.
- **Los Docs quedan fuera de la retención de A1.** A1 no borra Docs, ni aprobados ni descartados: son el repositorio de borradores de la SEU. Su plazo es una consulta institucional asignada a la SEU (seguimiento de [#14](https://github.com/SpendIce/Proyecto-Final/issues/14)).

## Decisión, concurrencia y recuperación

- **La aprobación queda atada al contenido.** Al decidir, el servidor reimporta el Doc y compara su hash con el de la revisión que la persona tenía en pantalla. Si difieren, registra una revisión nueva, rechaza la decisión y muestra la vigente. Pedido, revisión y evento se escriben en una sola transacción.
- **Generación fuera del HTTP.** Un worker separado, de a una solicitud por vez porque Ollama comparte el host, toma el trabajo con `SELECT … FOR UPDATE SKIP LOCKED` y un plazo de reserva. Si el proceso cae, al vencer la reserva la solicitud vuelve a la cola y se regenera. Antes de crear el Doc, A1 lo busca por una marca de la solicitud en sus propiedades, para no duplicarlo. Generar no tiene efectos externos, así que no se marca indeterminado: lo indeterminado sigue siendo exclusivo de la cola de envíos.
- **Purga, respaldo y restauración siguen la cadena del [ADR 0009](0009-el-agente-respalda-su-estado-en-drive-y-borra-sus-propios-respaldos.md).** Primero la purga (`NULL` + `VACUUM`), después el respaldo, que incluye un `pg_dump` dentro del mismo `.tar.gz` que va a Drive y se borra a los 30 días. Al restaurar, las solicitudes vuelven al último estado respaldado. Una decisión de difusión posterior al respaldo se pierde y se vuelve a tomar; no tiene efectos externos, así que no se marca indeterminada. RPO: un día hábil.
- **Dos roles con mínimo privilegio.** `agente1_app` (web y worker) lee y escribe solicitudes y revisiones, pero en la auditoría sólo inserta. `agente1_mantenimiento` corre la purga y el `VACUUM`. Las migraciones las corre el dueño de la base. Las credenciales son secretos del stack de Portainer.

**Alcance.** Sólo el canal web usa PostgreSQL. La cola de envíos, el registro de confirmaciones, las decisiones del Form y los demás JSONL siguen en archivos hasta su propia migración: no se duplica la cola ni se tienen dos fuentes de verdad para lo mismo.

## Considered Options

- **Archivos en el volumen**, con el patrón de la cola de envíos (un archivo por clave, `os.link`, `flock`). Entraba solo en el respaldo, la purga y la restauración, y no sumaba servicios. Se descartó porque la decisión toca solicitud, revisión y evento a la vez, y con archivos esa atomicidad y el rechazo de la revisión obsoleta se arman a mano. Además, la bandeja obliga a leer y parsear todas las solicitudes en cada consulta.
- **SQLite en el volumen.** Da casi las mismas garantías transaccionales sin un servicio nuevo. Se descartó porque la bible pide PostgreSQL para el log de auditoría (CU06) y como precondición de ExtensiónBot (EP01), y lista SQLite sólo para desarrollo. También porque deja sin usar el spike, que ya estaba escrito para PostgreSQL y sigue `PREPARADO_NO_EJECUTADO`, y porque no da concurrencia de escritura real ni `SKIP LOCKED`/`LISTEN`.
- **Un Doc por revisión.** Se descartó porque deja más Docs con prosa y cambia el link en cada ajuste.
- **Que A1 borre los Docs de solicitudes descartadas o vencidas.** Se descartó porque amplía la excepción de borrado del ADR 0009 y borrar en Drive es irreversible.

## Consequences

- El stack de A1 suma un contenedor de PostgreSQL sin puertos expuestos fuera de su red. Lo despliega el autor por Portainer; se avisa a DSI en [#62](https://github.com/SpendIce/Proyecto-Final/issues/62).
- La CI necesita un PostgreSQL de servicio. El adapter web ([#149](https://github.com/SpendIce/Proyecto-Final/issues/149)) se acepta cuando pasa estas pruebas contra una base real:
  1. **Caída durante la generación:** al vencer la reserva, la solicitud se regenera sin un segundo Doc.
  2. **Caída mientras se registra una decisión:** no queda nada a medias y la persona vuelve a decidir.
  3. **Doble clic o reenvío:** una sola solicitud y una sola decisión, por clave de idempotencia.
  4. **Decisión obsoleta:** si la revisión no es la vigente o el Doc cambió, se rechaza, se registra la revisión nueva y se muestra la vigente.
  5. **Purga:** prosa y texto generado en `NULL`, `VACUUM` ejecutado, hashes y eventos intactos. El respaldo del día no contiene la prosa purgada.
  6. **Restauración:** estados al último respaldo, sin indeterminados nuevos. Los envíos siguen con su regla.
  7. **Auditoría protegida:** `agente1_app` recibe «permiso denegado» si intenta modificar o borrar la auditoría.
  8. **Sesión:** con la sesión vencida o después de reiniciar, toda acción se rechaza. Ningún token queda en disco ni en logs.
  9. **Sin prosa en la trazabilidad:** después de la purga, el texto de prueba no aparece ni en la base ni en los logs.
- El respaldo y la restauración (`respaldo.py`, `scripts/restaurar_respaldo.py`) suman el volcado de la base. La purga diaria suma el paso de la base antes del respaldo.
- En el peor caso, la prosa transitoria vive en un respaldo hasta 30 días después de purgada, igual que hoy el texto del registro de confirmaciones.
