-- Revierte 0005 en su parte de esquema: la propiedad de la tabla vuelve
-- al rol que corrió la migración y se retiran los permisos del canal web
-- sobre estas tablas.
--
-- Los roles NO se eliminan: son objetos del clúster (como los crea quien
-- despliega con su clave) y pueden tener permisos concedidos desde otros
-- esquemas o bases; un `DROP ROLE` condicionado a que ninguna otra
-- concesión exista haría el down no determinista. Quedan sin permisos
-- sobre este esquema y sin clave, que es lo que el down puede garantizar.
BEGIN;

ALTER TABLE prosa_transitoria OWNER TO CURRENT_USER;

REVOKE SELECT, INSERT, UPDATE, DELETE
    ON solicitudes, ejecuciones, borradores, defectos
    FROM agente1_app;
REVOKE SELECT, INSERT ON validaciones FROM agente1_app;
REVOKE SELECT, INSERT ON eventos_ejecucion FROM agente1_app;
REVOKE SELECT, INSERT, UPDATE ON prosa_transitoria FROM agente1_app;
REVOKE USAGE ON SEQUENCE
    eventos_ejecucion_secuencia_seq,
    prosa_transitoria_secuencia_seq
    FROM agente1_app;
REVOKE SELECT
    ON solicitudes, ejecuciones, borradores, validaciones, defectos,
       eventos_ejecucion
    FROM agente1_mantenimiento;

COMMIT;
