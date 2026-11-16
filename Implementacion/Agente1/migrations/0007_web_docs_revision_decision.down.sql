-- Revierte 0007: el esquema vuelve al estado de 0006.
--
-- El `down` aborta si hay revisiones importadas (prosa `importado` o
-- borradores con `id_ejecucion NULL`): el `SET NOT NULL` y el `UNIQUE`
-- que se recrean no las pueden representar. Las decisiones web, en
-- cambio, **sí se pierden**: se borran `rol`, `origen_identidad` y
-- `version_agente` sin chequear filas. Por eso el retiro de la
-- funcionalidad exige restaurar el respaldo previo (o exportar esas
-- columnas) antes de correr este `down`; el test lo clasifica como
-- `pierde_datos`.
BEGIN;

ALTER TABLE validaciones
    DROP CONSTRAINT validaciones_rol_check,
    DROP CONSTRAINT validaciones_origen_identidad_check,
    DROP CONSTRAINT validaciones_version_agente_check;
ALTER TABLE validaciones
    DROP COLUMN rol,
    DROP COLUMN origen_identidad,
    DROP COLUMN version_agente;

ALTER TABLE prosa_transitoria
    DROP CONSTRAINT prosa_transitoria_clase_check;
ALTER TABLE prosa_transitoria
    ADD CONSTRAINT prosa_transitoria_clase_check
        CHECK (clase IN ('descripcion', 'campos', 'ajuste', 'generado'));
ALTER TABLE prosa_transitoria
    DROP COLUMN id_borrador;

ALTER TABLE borradores
    ALTER COLUMN id_ejecucion SET NOT NULL;
ALTER TABLE borradores
    ADD CONSTRAINT borradores_id_ejecucion_key UNIQUE (id_ejecucion);
ALTER TABLE borradores
    DROP CONSTRAINT borradores_origen_check;
ALTER TABLE borradores
    DROP COLUMN origen;

ALTER TABLE solicitudes
    DROP CONSTRAINT solicitudes_doc_ref_check,
    DROP CONSTRAINT solicitudes_doc_url_check;
ALTER TABLE solicitudes
    DROP COLUMN doc_ref,
    DROP COLUMN doc_url;

COMMIT;
