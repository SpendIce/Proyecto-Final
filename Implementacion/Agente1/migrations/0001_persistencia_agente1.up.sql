BEGIN;

CREATE TABLE solicitudes (
    id_solicitud VARCHAR(128) PRIMARY KEY,
    input_hash CHAR(64) NOT NULL CHECK (input_hash ~ '^[0-9a-f]{64}$'),
    fuente_tipo VARCHAR(64) NOT NULL,
    creada_en TIMESTAMPTZ NOT NULL,
    eliminado_en TIMESTAMPTZ,
    CHECK (eliminado_en IS NULL OR eliminado_en >= creada_en),
    CHECK (id_solicitud ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (fuente_tipo IN ('csv', 'fixture', 'google_sheets', 'jsonl_replay'))
);

CREATE TABLE ejecuciones (
    id_ejecucion VARCHAR(128) PRIMARY KEY,
    id_solicitud VARCHAR(128) NOT NULL REFERENCES solicitudes(id_solicitud),
    idempotency_key VARCHAR(255) NOT NULL,
    correlation_id VARCHAR(128) NOT NULL,
    hu VARCHAR(16) NOT NULL,
    input_hash CHAR(64) NOT NULL CHECK (input_hash ~ '^[0-9a-f]{64}$'),
    estado VARCHAR(32) NOT NULL,
    resultado VARCHAR(64),
    output_hash CHAR(64) CHECK (output_hash ~ '^[0-9a-f]{64}$'),
    error_code VARCHAR(64),
    creada_en TIMESTAMPTZ NOT NULL,
    finalizada_en TIMESTAMPTZ,
    eliminado_en TIMESTAMPTZ,
    UNIQUE (idempotency_key),
    UNIQUE (correlation_id),
    CHECK (id_ejecucion ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (id_solicitud ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (idempotency_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,254}$'),
    CHECK (correlation_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (hu ~ '^HU-[0-9]{3}$'),
    CHECK (estado IN (
        'INICIADA', 'INCOMPLETA', 'PENDIENTE_VALIDACION',
        'APROBADA', 'RECHAZADA', 'FALLIDA'
    )),
    CHECK (finalizada_en IS NULL OR finalizada_en >= creada_en),
    CHECK (eliminado_en IS NULL OR eliminado_en >= creada_en),
    CHECK (resultado IS NULL OR resultado IN (
        'borrador_generado', 'channel_invalid', 'datos_incompletos',
        'destination_failure', 'error_generacion', 'policy_incompatible',
        'salida_no_conforme', 'salida_vacia', 'source_failure',
        'source_invalid', 'source_not_renderable'
    )),
    CHECK (error_code IS NULL OR error_code ~ '^[a-z][a-z0-9_]{0,63}$'),
    CHECK (error_code IS NULL OR error_code IN (
        'destination_contract_invalid', 'destination_unavailable',
        'docs_auth_denied', 'docs_rate_limited', 'docs_response_invalid',
        'docs_response_too_large', 'docs_unavailable',
        'docs_update_failed_orphaned', 'drive_auth_denied',
        'drive_rate_limited', 'drive_request_too_large',
        'drive_resource_not_found', 'drive_response_invalid',
        'drive_response_too_large', 'drive_unavailable',
        'generator_unavailable', 'sheets_headers_invalid',
        'sheets_row_invalid', 'source_contract_invalid',
        'source_duplicate_id', 'source_fact_in_creative_field',
        'source_id_mismatch', 'source_request_invalid',
        'source_request_not_found', 'source_status_claim_not_allowed',
        'source_unavailable', 'workspace_auth_denied',
        'workspace_auth_unavailable', 'workspace_rate_limited',
        'workspace_response_invalid', 'workspace_response_too_large',
        'workspace_source_not_found', 'workspace_unavailable'
    )),
    CHECK (
        (estado = 'INICIADA' AND resultado IS NULL
            AND output_hash IS NULL AND error_code IS NULL)
        OR (estado = 'INCOMPLETA' AND resultado = 'datos_incompletos'
            AND output_hash IS NULL AND error_code IS NULL)
        OR (estado IN ('PENDIENTE_VALIDACION', 'APROBADA', 'RECHAZADA')
            AND resultado = 'borrador_generado'
            AND output_hash IS NOT NULL AND error_code IS NULL)
        OR (estado = 'FALLIDA' AND resultado IN (
            'channel_invalid', 'destination_failure', 'error_generacion',
            'policy_incompatible', 'salida_no_conforme', 'salida_vacia',
            'source_failure', 'source_invalid', 'source_not_renderable'
        ) AND output_hash IS NULL)
    ),
    CHECK (
        (estado = 'INICIADA' AND finalizada_en IS NULL)
        OR (estado <> 'INICIADA' AND finalizada_en IS NOT NULL)
    )
);

CREATE TABLE borradores (
    id_borrador VARCHAR(128) PRIMARY KEY,
    id_ejecucion VARCHAR(128) NOT NULL UNIQUE REFERENCES ejecuciones(id_ejecucion),
    referencia_hash CHAR(64) NOT NULL CHECK (referencia_hash ~ '^[0-9a-f]{64}$'),
    output_hash CHAR(64) NOT NULL CHECK (output_hash ~ '^[0-9a-f]{64}$'),
    canal VARCHAR(32) NOT NULL,
    estado VARCHAR(32) NOT NULL,
    creada_en TIMESTAMPTZ NOT NULL,
    eliminado_en TIMESTAMPTZ,
    CHECK (estado IN ('PENDIENTE_VALIDACION', 'APROBADO', 'RECHAZADO')),
    CHECK (eliminado_en IS NULL OR eliminado_en >= creada_en),
    CHECK (id_borrador ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (id_ejecucion ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (canal IN ('gacetilla', 'instagram', 'linkedin'))
);

CREATE TABLE validaciones (
    id_validacion VARCHAR(128) PRIMARY KEY,
    id_borrador VARCHAR(128) NOT NULL UNIQUE REFERENCES borradores(id_borrador),
    decision VARCHAR(16) NOT NULL,
    validador_ref_hash CHAR(64) NOT NULL CHECK (validador_ref_hash ~ '^[0-9a-f]{64}$'),
    checklist_version VARCHAR(64) NOT NULL,
    registrada_en TIMESTAMPTZ NOT NULL,
    eliminado_en TIMESTAMPTZ,
    CHECK (decision IN ('APROBADA', 'RECHAZADA')),
    CHECK (eliminado_en IS NULL OR eliminado_en >= registrada_en),
    CHECK (id_validacion ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (id_borrador ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (checklist_version ~ '^[a-z][a-z0-9_]{0,63}$')
);

CREATE TABLE defectos (
    id_defecto VARCHAR(128) PRIMARY KEY,
    id_ejecucion VARCHAR(128) NOT NULL REFERENCES ejecuciones(id_ejecucion),
    codigo VARCHAR(64) NOT NULL,
    severidad VARCHAR(16) NOT NULL,
    evidencia_hash CHAR(64) NOT NULL CHECK (evidencia_hash ~ '^[0-9a-f]{64}$'),
    estado VARCHAR(16) NOT NULL DEFAULT 'ABIERTO',
    creado_en TIMESTAMPTZ NOT NULL,
    cerrado_en TIMESTAMPTZ,
    eliminado_en TIMESTAMPTZ,
    CHECK (severidad IN ('BAJA', 'MEDIA', 'ALTA', 'CRITICA')),
    CHECK (estado IN ('ABIERTO', 'CERRADO')),
    CHECK ((estado = 'ABIERTO' AND cerrado_en IS NULL)
        OR (estado = 'CERRADO' AND cerrado_en IS NOT NULL)),
    CHECK (cerrado_en IS NULL OR cerrado_en >= creado_en),
    CHECK (eliminado_en IS NULL OR eliminado_en >= creado_en),
    CHECK (id_defecto ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (id_ejecucion ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (codigo ~ '^[a-z][a-z0-9_]{0,63}$')
);

CREATE TABLE eventos_ejecucion (
    secuencia BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_ejecucion VARCHAR(128) NOT NULL REFERENCES ejecuciones(id_ejecucion),
    tipo VARCHAR(64) NOT NULL,
    ocurrido_en TIMESTAMPTZ NOT NULL,
    evidencia_hash CHAR(64) CHECK (evidencia_hash ~ '^[0-9a-f]{64}$'),
    CHECK (id_ejecucion ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (tipo ~ '^[a-z][a-z0-9_]{0,63}$')
);

CREATE INDEX idx_ejecuciones_solicitud ON ejecuciones(id_solicitud);
CREATE INDEX idx_ejecuciones_estado_creada ON ejecuciones(estado, creada_en);
CREATE INDEX idx_defectos_ejecucion ON defectos(id_ejecucion);
CREATE INDEX idx_eventos_ejecucion_secuencia
    ON eventos_ejecucion(id_ejecucion, secuencia);

COMMIT;
