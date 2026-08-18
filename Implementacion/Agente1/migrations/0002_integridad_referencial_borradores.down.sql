-- Rollback de 0002. Reabre las brechas estructurales que 0002 cerró, por lo que
-- sólo es defensible antes de almacenar evidencia institucional real.

BEGIN;

ALTER TABLE validaciones
    DROP CONSTRAINT validaciones_no_preceden_al_borrador;

ALTER TABLE validaciones
    DROP CONSTRAINT validaciones_borrador_creada_fk;

ALTER TABLE validaciones
    DROP COLUMN borrador_creada_en;

ALTER TABLE borradores
    DROP CONSTRAINT borradores_id_creada_key;

ALTER TABLE borradores
    DROP CONSTRAINT borradores_ejecucion_output_fk;

ALTER TABLE ejecuciones
    DROP CONSTRAINT ejecuciones_id_output_hash_key;

COMMIT;
