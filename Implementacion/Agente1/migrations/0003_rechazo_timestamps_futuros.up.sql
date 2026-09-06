-- Cierra la brecha temporal remanente del spike: una escritura SQL directa no
-- puede crear una ejecución ni registrar una validación con timestamp futuro.
-- Se usa trigger y no CHECK con now(): PostgreSQL exige expresiones inmutables
-- en CHECK, mientras que el control debe evaluarse al momento de escribir.

BEGIN;

CREATE FUNCTION agente1_rechazar_timestamp_futuro()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    timestamp_controlado TIMESTAMPTZ;
BEGIN
    timestamp_controlado := (to_jsonb(NEW) ->> TG_ARGV[0])::TIMESTAMPTZ;
    IF timestamp_controlado > CURRENT_TIMESTAMP THEN
        RAISE EXCEPTION 'timestamp futuro no permitido para %', TG_ARGV[0]
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ejecuciones_rechazan_creada_en_futura
BEFORE INSERT OR UPDATE OF creada_en ON ejecuciones
FOR EACH ROW
EXECUTE FUNCTION agente1_rechazar_timestamp_futuro('creada_en');

CREATE TRIGGER validaciones_rechazan_registrada_en_futura
BEFORE INSERT OR UPDATE OF registrada_en ON validaciones
FOR EACH ROW
EXECUTE FUNCTION agente1_rechazar_timestamp_futuro('registrada_en');

COMMIT;
