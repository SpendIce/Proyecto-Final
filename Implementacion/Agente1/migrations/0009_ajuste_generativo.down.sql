-- Revierte 0009. Aborta si quedó cualquier rastro de un ajuste: recrear el
-- esquema anterior no puede representar la ejecución `ajuste`, la revisión
-- `ajuste_generativo`, la indicación ni la solicitud `AJUSTANDO` sin
-- mentir la proveniencia. Sin esos datos, el `down` es estructural.
BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM ajustes)
        OR EXISTS (SELECT 1 FROM ejecuciones WHERE clase = 'ajuste')
        OR EXISTS (SELECT 1 FROM solicitudes WHERE estado_web = 'AJUSTANDO')
        OR EXISTS (
            SELECT 1 FROM borradores WHERE origen = 'ajuste_generativo'
        )
    THEN
        RAISE EXCEPTION
            '0009_down_con_ajustes: exportar o restaurar el respaldo antes';
    END IF;
END
$$;

DROP TABLE ajustes;

ALTER TABLE borradores
    DROP CONSTRAINT borradores_origen_check;

ALTER TABLE borradores
    ADD CONSTRAINT borradores_origen_check
        CHECK (origen IS NULL OR origen IN ('generada', 'editada_docs'));

ALTER TABLE borradores
    DROP COLUMN id_borrador_base;

ALTER TABLE ejecuciones
    DROP CONSTRAINT ejecuciones_clase_check;

ALTER TABLE ejecuciones
    DROP COLUMN clase;

ALTER TABLE solicitudes
    DROP CONSTRAINT solicitudes_estado_web_check;

ALTER TABLE solicitudes
    ADD CONSTRAINT solicitudes_estado_web_check
        CHECK (
            estado_web IS NULL
            OR estado_web IN (
                'EN_COLA', 'GENERANDO', 'LISTA', 'ERROR',
                'APROBADA', 'DESCARTADA', 'VENCIDA'
            )
        );

COMMIT;
