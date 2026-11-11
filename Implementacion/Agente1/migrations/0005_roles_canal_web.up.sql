-- Roles del canal web (ADR 0016): `agente1_app` corre la web y el worker
-- con mínimo privilegio (escribe estado, inserta auditoría, nunca la toca);
-- `agente1_mantenimiento` corre la purga diaria y el VACUUM de la prosa
-- transitoria. Las claves no viajan en la migración: las asigna quien
-- despliega, por variables de entorno o secrets del stack.
BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agente1_app') THEN
        CREATE ROLE agente1_app LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agente1_mantenimiento') THEN
        CREATE ROLE agente1_mantenimiento LOGIN;
    END IF;
END
$$;

-- La aplicación lee y escribe el estado operativo de las tablas del
-- agente. Sobre la auditoría sólo puede insertar: no UPDATE ni DELETE,
-- para que una aplicación comprometida no pueda retocar la trazabilidad.
GRANT SELECT, INSERT, UPDATE, DELETE
    ON solicitudes, ejecuciones, borradores, defectos
    TO agente1_app;
GRANT SELECT, INSERT ON validaciones TO agente1_app;
GRANT SELECT, INSERT ON eventos_ejecucion TO agente1_app;
GRANT SELECT, INSERT, UPDATE ON prosa_transitoria TO agente1_app;
GRANT USAGE ON SEQUENCE
    eventos_ejecucion_secuencia_seq,
    prosa_transitoria_secuencia_seq
    TO agente1_app;

-- El mantenimiento lee todo el estado, vacía la prosa transitoria y la
-- mantiene como dueño de tabla para que el VACUUM diario corra con su rol
-- (PostgreSQL exige ser dueño o superusuario para aspirar una tabla).
GRANT SELECT
    ON solicitudes, ejecuciones, borradores, validaciones, defectos,
       eventos_ejecucion
    TO agente1_mantenimiento;
ALTER TABLE prosa_transitoria OWNER TO agente1_mantenimiento;

COMMIT;
