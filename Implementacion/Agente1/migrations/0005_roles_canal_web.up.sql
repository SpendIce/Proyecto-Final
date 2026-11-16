-- Roles del canal web (ADR 0016): `agente1_app` corre la web, el worker
-- y el vencimiento de solicitudes con mínimo privilegio (escribe estado,
-- inserta auditoría, nunca la toca ni vacía prosa); `agente1_mantenimiento`
-- corre la purga diaria de la prosa y su VACUUM. Las claves no viajan en
-- la migración: las asigna quien despliega, por variables de entorno o
-- secrets del stack.
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
-- Sobre la prosa transitoria lee e inserta (crear la solicitud la siembra,
-- completar el trabajo guarda el generado): el UPDATE que la vacía es de
-- la purga, no suyo.
GRANT SELECT, INSERT, UPDATE, DELETE
    ON solicitudes, ejecuciones, borradores, defectos
    TO agente1_app;
GRANT SELECT, INSERT ON validaciones TO agente1_app;
GRANT SELECT, INSERT ON eventos_ejecucion TO agente1_app;
GRANT SELECT, INSERT ON prosa_transitoria TO agente1_app;
GRANT USAGE ON SEQUENCE
    eventos_ejecucion_secuencia_seq,
    prosa_transitoria_secuencia_seq
    TO agente1_app;

-- El respaldo diario corre `pg_dump` con el DSN de la app y el volcado
-- lee `last_value` de cada secuencia del esquema — USAGE no alcanza.
-- El esquema lo decide el despliegue (la migración corre adentro de él),
-- así que el grant va por `current_schema`.
DO $$
BEGIN
    EXECUTE format(
        'GRANT SELECT ON ALL SEQUENCES IN SCHEMA %I TO agente1_app',
        current_schema()
    );
END
$$;

-- El mantenimiento lee todo el estado, vacía la prosa transitoria como
-- dueño de la tabla (PostgreSQL exige ser dueño o superusuario para
-- aspirarla) y asienta el evento `prosa_purgada` por solicitud en la
-- auditoría de ejecuciones —sólo inserta, no toca lo asentado—. Nunca
-- escribe el ciclo de vida de la solicitud.
GRANT SELECT
    ON solicitudes, ejecuciones, borradores, validaciones, defectos
    TO agente1_mantenimiento;
GRANT SELECT, INSERT ON eventos_ejecucion TO agente1_mantenimiento;
GRANT USAGE ON SEQUENCE eventos_ejecucion_secuencia_seq
    TO agente1_mantenimiento;
ALTER TABLE prosa_transitoria OWNER TO agente1_mantenimiento;

COMMIT;
