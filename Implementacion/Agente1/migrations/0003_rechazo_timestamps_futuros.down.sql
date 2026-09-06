-- Rollback de 0003. Sólo es admisible antes de que una política institucional
-- reemplace este control; no borra evidencia ni datos.

BEGIN;

DROP TRIGGER validaciones_rechazan_registrada_en_futura ON validaciones;
DROP TRIGGER ejecuciones_rechazan_creada_en_futura ON ejecuciones;
DROP FUNCTION agente1_rechazar_timestamp_futuro();

COMMIT;
