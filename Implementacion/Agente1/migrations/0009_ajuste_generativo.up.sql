-- Ajuste generativo sobre la revisión vigente del canal web.
--
-- Un ajuste no sobrescribe la revisión anterior: crea una ejecución
-- propia (`ejecuciones.clase = 'ajuste'`), registra el pedido en `ajustes`
-- (quién, rol, origen de identidad, hash de la revisión base y versión del
-- agente) y deja la indicación en `prosa_transitoria` con clase `ajuste`.
-- El worker escribe el texto nuevo en el mismo Doc y `completar_trabajo`
-- crea la revisión con origen `ajuste_generativo` y su `id_borrador_base`.
-- La solicitud pasa por `AJUSTANDO` mientras el worker trabaja.
--
-- Grants: `ajustes` es una tabla operativa más del canal; la app escribe y
-- el mantenimiento sólo lee, igual que el resto del ciclo de vida.
BEGIN;

ALTER TABLE solicitudes
    DROP CONSTRAINT solicitudes_estado_web_check;

ALTER TABLE solicitudes
    ADD CONSTRAINT solicitudes_estado_web_check
        CHECK (
            estado_web IS NULL
            OR estado_web IN (
                'EN_COLA', 'GENERANDO', 'AJUSTANDO', 'LISTA', 'ERROR',
                'APROBADA', 'DESCARTADA', 'VENCIDA'
            )
        );

-- La ejecución de un ajuste comparte solicitud con la generación original:
-- es una unidad de trabajo nueva, reservable igual que aquélla, pero su
-- despacho no vuelve a generar desde cero.
ALTER TABLE ejecuciones
    ADD COLUMN clase VARCHAR(16) NOT NULL DEFAULT 'generacion';

ALTER TABLE ejecuciones
    ADD CONSTRAINT ejecuciones_clase_check
        CHECK (clase IN ('generacion', 'ajuste'));

-- Cada revisión de ajuste declara de qué revisión partió. Las revisiones
-- generadas e importadas quedan con NULL.
ALTER TABLE borradores
    ADD COLUMN id_borrador_base VARCHAR(128) REFERENCES borradores (id_borrador);

ALTER TABLE borradores
    DROP CONSTRAINT borradores_origen_check;

ALTER TABLE borradores
    ADD CONSTRAINT borradores_origen_check
        CHECK (
            origen IS NULL
            OR origen IN ('generada', 'editada_docs', 'ajuste_generativo')
        );

CREATE TABLE ajustes (
    id_ajuste VARCHAR(128) PRIMARY KEY,
    id_solicitud VARCHAR(128) NOT NULL REFERENCES solicitudes (id_solicitud),
    id_ejecucion VARCHAR(128) NOT NULL UNIQUE REFERENCES ejecuciones (id_ejecucion),
    id_borrador_base VARCHAR(128) NOT NULL REFERENCES borradores (id_borrador),
    base_output_hash CHAR(64) NOT NULL,
    indicacion_hash CHAR(64) NOT NULL,
    solicitante_hash CHAR(64) NOT NULL,
    rol VARCHAR(64) NOT NULL,
    origen_identidad VARCHAR(16) NOT NULL,
    version_agente VARCHAR(64) NOT NULL,
    creada_en TIMESTAMPTZ NOT NULL,
    CHECK (id_ajuste ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (base_output_hash ~ '^[0-9a-f]{64}$'),
    CHECK (indicacion_hash ~ '^[0-9a-f]{64}$'),
    CHECK (solicitante_hash ~ '^[0-9a-f]{64}$'),
    CHECK (rol ~ '^[A-Za-z0-9_.-]{1,64}$'),
    CHECK (origen_identidad IN ('google', 'demo')),
    CHECK (version_agente ~ '^[0-9A-Za-z._-]{1,64}$')
);

CREATE INDEX idx_ajustes_solicitud ON ajustes (id_solicitud);

GRANT SELECT, INSERT ON ajustes TO agente1_app;
GRANT SELECT ON ajustes TO agente1_mantenimiento;

COMMIT;
