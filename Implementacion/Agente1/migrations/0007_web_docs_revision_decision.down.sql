-- Revierte 0007: el esquema vuelve al estado de 0006.
--
-- Si ya hay revisiones importadas (prosa `importado` o borradores sin
-- ejecución) o decisiones web registradas, los `ADD CONSTRAINT` y el
-- `SET NOT NULL` abortan la transacción en voz alta: el `down` nunca
-- reclasifica ni pierde una revisión o una decisión en silencio. El
-- retiro de la funcionalidad define qué se hace con esas filas antes de
-- revertir.
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
