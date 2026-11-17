-- Revierte 0011: `agente1_app` vuelve a tener sólo SELECT e INSERT sobre
-- `prosa_transitoria`, como antes de este permiso (0005). No toca datos
-- ni la propiedad de la tabla, que sigue en `agente1_mantenimiento`.
BEGIN;

REVOKE UPDATE (id_borrador) ON prosa_transitoria FROM agente1_app;

COMMIT;
