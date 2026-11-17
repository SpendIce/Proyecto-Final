BEGIN;

DROP TABLE IF EXISTS emisiones_certificados;

ALTER TABLE lotes_certificados
    DROP CONSTRAINT IF EXISTS lotes_certificados_origen_creacion_check;

ALTER TABLE lotes_certificados
    DROP COLUMN IF EXISTS origen_creacion;

COMMIT;
