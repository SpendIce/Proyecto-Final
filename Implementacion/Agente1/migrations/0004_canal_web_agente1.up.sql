-- Canal web del Agente 1 (ADR 0016, issue #149): la solicitud web queda
-- durable desde que nace, la ejecución reservable es la unidad de trabajo
-- del worker y la prosa transitoria vive en su propia tabla, único lugar
-- con texto, para que la purga diaria la vacíe sin tocar la trazabilidad.
BEGIN;

-- Canal de origen, identidad opaca y ciclo de vida de la solicitud web.
ALTER TABLE solicitudes
    ADD COLUMN canal VARCHAR(32) NOT NULL DEFAULT 'planilla',
    ADD COLUMN solicitante_hash CHAR(64),
    ADD COLUMN rol VARCHAR(64),
    ADD COLUMN tipo_pieza VARCHAR(64),
    ADD COLUMN actividad_ref VARCHAR(128),
    ADD COLUMN estado_web VARCHAR(32),
    ADD COLUMN revision_vigente VARCHAR(128),
    ADD COLUMN ultima_actividad_en TIMESTAMPTZ;

ALTER TABLE solicitudes
    ADD CONSTRAINT solicitudes_canal_check
        CHECK (canal IN ('planilla', 'form', 'web')),
    ADD CONSTRAINT solicitudes_solicitante_hash_check
        CHECK (solicitante_hash IS NULL OR solicitante_hash ~ '^[0-9a-f]{64}$'),
    ADD CONSTRAINT solicitudes_rol_check
        CHECK (rol IS NULL OR rol ~ '^[A-Za-z0-9_.-]{1,64}$'),
    ADD CONSTRAINT solicitudes_tipo_pieza_check
        CHECK (tipo_pieza IS NULL OR tipo_pieza ~ '^[a-z][a-z0-9_]{0,63}$'),
    ADD CONSTRAINT solicitudes_estado_web_check
        CHECK (
            estado_web IS NULL
            OR estado_web IN (
                'EN_COLA', 'GENERANDO', 'LISTA', 'ERROR',
                'APROBADA', 'DESCARTADA', 'VENCIDA'
            )
        ),
    ADD CONSTRAINT solicitudes_revision_vigente_fk
        FOREIGN KEY (revision_vigente) REFERENCES borradores (id_borrador),
    ADD CONSTRAINT solicitudes_ultima_actividad_check
        CHECK (ultima_actividad_en IS NULL OR ultima_actividad_en >= creada_en),
    ADD CONSTRAINT solicitudes_web_campos_check
        CHECK (
            canal <> 'web'
            OR (
                solicitante_hash IS NOT NULL
                AND rol IS NOT NULL
                AND tipo_pieza IS NOT NULL
                AND estado_web IS NOT NULL
                AND ultima_actividad_en IS NOT NULL
            )
        );

-- La fuente `web` se suma al vocabulario cerrado de 0001.
ALTER TABLE solicitudes DROP CONSTRAINT solicitudes_fuente_tipo_check;
ALTER TABLE solicitudes
    ADD CONSTRAINT solicitudes_fuente_tipo_check
    CHECK (fuente_tipo IN ('csv', 'fixture', 'google_sheets', 'jsonl_replay', 'web'));

-- Reserva del worker sobre la ejecución: la unidad de trabajo que se toma
-- con SELECT ... FOR UPDATE SKIP LOCKED y que vence por plazo (ADR 0016).
ALTER TABLE ejecuciones
    ADD COLUMN reservada_hasta TIMESTAMPTZ,
    ADD COLUMN reservada_por VARCHAR(64);
ALTER TABLE ejecuciones
    ADD CONSTRAINT ejecuciones_reservada_por_check
        CHECK (reservada_por IS NULL OR reservada_por ~ '^[A-Za-z0-9_.-]{1,64}$');
CREATE INDEX idx_ejecuciones_trabajo
    ON ejecuciones (estado, reservada_hasta);

-- Revisión de pieza: número dentro de la solicitud, referencia opaca al
-- Doc y headRevisionId de Drive (ADR 0016).
ALTER TABLE borradores
    ADD COLUMN id_solicitud VARCHAR(128) REFERENCES solicitudes (id_solicitud),
    ADD COLUMN numero_revision INT,
    ADD COLUMN doc_ref VARCHAR(255),
    ADD COLUMN head_revision_id VARCHAR(255);
ALTER TABLE borradores
    ADD CONSTRAINT borradores_numero_revision_check
        CHECK (numero_revision IS NULL OR numero_revision >= 1),
    ADD CONSTRAINT borradores_revision_unica_por_solicitud
        UNIQUE (id_solicitud, numero_revision);

-- Decisión de revisión (la opera #153; acá sólo queda el esquema):
-- hash del Doc reimportado, señal de edición y métricas, nunca prosa.
ALTER TABLE validaciones
    ADD COLUMN head_revision_id VARCHAR(255),
    ADD COLUMN doc_hash CHAR(64),
    ADD COLUMN senal VARCHAR(32),
    ADD COLUMN proporcion_cambiado REAL,
    ADD COLUMN cantidad_ajustes INT;
ALTER TABLE validaciones
    ADD CONSTRAINT validaciones_doc_hash_check
        CHECK (doc_hash IS NULL OR doc_hash ~ '^[0-9a-f]{64}$'),
    ADD CONSTRAINT validaciones_senal_check
        CHECK (senal IS NULL OR senal IN ('sin_cambios', 'con_cambios')),
    ADD CONSTRAINT validaciones_proporcion_check
        CHECK (
            proporcion_cambiado IS NULL
            OR (proporcion_cambiado >= 0 AND proporcion_cambiado <= 1)
        ),
    ADD CONSTRAINT validaciones_ajustes_check
        CHECK (cantidad_ajustes IS NULL OR cantidad_ajustes >= 0);

-- Única tabla con texto del canal web (ADR 0016): la descripción del
-- pedido, los campos confirmados, cada pedido de ajuste y el texto
-- generado para la revisión vigente. Se pone en NULL en la primera purga
-- diaria posterior al cierre de la solicitud; quedan hash, clase y marcas.
CREATE TABLE prosa_transitoria (
    secuencia BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_solicitud VARCHAR(128) NOT NULL REFERENCES solicitudes (id_solicitud),
    id_ejecucion VARCHAR(128) REFERENCES ejecuciones (id_ejecucion),
    clase VARCHAR(32) NOT NULL
        CHECK (clase IN ('descripcion', 'campos', 'ajuste', 'generado')),
    texto TEXT,
    texto_hash CHAR(64) NOT NULL CHECK (texto_hash ~ '^[0-9a-f]{64}$'),
    creada_en TIMESTAMPTZ NOT NULL,
    purgada_en TIMESTAMPTZ,
    CHECK ((texto IS NULL) = (purgada_en IS NOT NULL))
);
CREATE INDEX idx_prosa_transitoria_solicitud
    ON prosa_transitoria (id_solicitud);

COMMIT;
