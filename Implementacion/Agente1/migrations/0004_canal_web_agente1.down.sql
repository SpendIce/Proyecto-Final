-- Revierte 0004: el esquema vuelve al estado del spike (0003).
BEGIN;

DROP INDEX idx_prosa_transitoria_solicitud;
DROP TABLE prosa_transitoria;

ALTER TABLE validaciones
    DROP CONSTRAINT validaciones_doc_hash_check,
    DROP CONSTRAINT validaciones_senal_check,
    DROP CONSTRAINT validaciones_proporcion_check,
    DROP CONSTRAINT validaciones_ajustes_check;
ALTER TABLE validaciones
    DROP COLUMN head_revision_id,
    DROP COLUMN doc_hash,
    DROP COLUMN senal,
    DROP COLUMN proporcion_cambiado,
    DROP COLUMN cantidad_ajustes;

ALTER TABLE borradores
    DROP CONSTRAINT borradores_numero_revision_check,
    DROP CONSTRAINT borradores_revision_unica_por_solicitud;
ALTER TABLE borradores
    DROP COLUMN id_solicitud,
    DROP COLUMN numero_revision,
    DROP COLUMN doc_ref,
    DROP COLUMN head_revision_id;

DROP INDEX idx_ejecuciones_trabajo;
ALTER TABLE ejecuciones
    DROP CONSTRAINT ejecuciones_reservada_por_check;
ALTER TABLE ejecuciones
    DROP COLUMN reservada_hasta,
    DROP COLUMN reservada_por;

ALTER TABLE solicitudes DROP CONSTRAINT solicitudes_fuente_tipo_check;
ALTER TABLE solicitudes
    ADD CONSTRAINT solicitudes_fuente_tipo_check
    CHECK (fuente_tipo IN ('csv', 'fixture', 'google_sheets', 'jsonl_replay'));

ALTER TABLE solicitudes
    DROP CONSTRAINT solicitudes_canal_check,
    DROP CONSTRAINT solicitudes_solicitante_hash_check,
    DROP CONSTRAINT solicitudes_rol_check,
    DROP CONSTRAINT solicitudes_tipo_pieza_check,
    DROP CONSTRAINT solicitudes_estado_web_check,
    DROP CONSTRAINT solicitudes_revision_vigente_fk,
    DROP CONSTRAINT solicitudes_ultima_actividad_check,
    DROP CONSTRAINT solicitudes_web_campos_check;
ALTER TABLE solicitudes
    DROP COLUMN canal,
    DROP COLUMN solicitante_hash,
    DROP COLUMN rol,
    DROP COLUMN tipo_pieza,
    DROP COLUMN actividad_ref,
    DROP COLUMN estado_web,
    DROP COLUMN revision_vigente,
    DROP COLUMN ultima_actividad_en;

COMMIT;
