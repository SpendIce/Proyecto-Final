-- Permiso puntual para completar un ajuste (0009, ADR 0016).
--
-- `completar_trabajo` enlaza la indicación de un ajuste con la revisión
-- que produjo: `UPDATE prosa_transitoria SET id_borrador = ...`. 0005
-- concedió a `agente1_app` sólo SELECT e INSERT sobre esa tabla, así que
-- el worker fallaba al cerrar el ajuste con `permission denied` y la
-- solicitud quedaba en `AJUSTANDO`. 0009 agregó el flujo de ajuste pero no
-- el permiso.
--
-- El grant es sólo de la columna `id_borrador`. El texto, `texto_hash` y
-- las demás columnas siguen vedados a la app; borrar o vaciar la prosa y
-- su VACUUM siguen siendo de `agente1_mantenimiento`, dueño de la tabla.
-- Como todo permiso por columna, no acota filas: el repositorio sólo
-- actualiza la fila de la ejecución del ajuste, y aun comprometida la app
-- no puede alterar el texto ni la auditoría ya asentada.
-- No hay cambio de estructura: el `down` sólo revoca el permiso y la
-- imagen 0.8.1, que no corre `down`, lo conserva al revertir.
BEGIN;

GRANT UPDATE (id_borrador) ON prosa_transitoria TO agente1_app;

COMMIT;
