-- Doc por solicitud, revisiones importadas y decisión del canal web
-- (ADR 0016, issue #153). Ninguna tabla nueva: el Doc vive en
-- `solicitudes`, cada revisión en `borradores`, su texto en
-- `prosa_transitoria` (se purga igual que el resto) y la decisión en
-- `validaciones` con los metadatos que pide la trazabilidad.
--
-- Grants: no hace falta tocar los de 0005 — las columnas nuevas heredan
-- los permisos de tabla ya concedidos a `agente1_app` (INSERT en
-- auditoría, SELECT/INSERT en prosa, ciclo de vida completo en el resto)
-- y la lectura de `agente1_mantenimiento`.
BEGIN;

-- El Doc de la solicitud: `doc_ref` es el id opaco que usa el exportador
-- para reimportar; `doc_url` es el enlace «Editar en Google Docs». Ambos
-- NULL cuando el destino no es Google (el fake de desarrollo no produce
-- un enlace real y la interfaz no inventa uno).
ALTER TABLE solicitudes
    ADD COLUMN doc_ref VARCHAR(255),
    ADD COLUMN doc_url VARCHAR(512);

ALTER TABLE solicitudes
    ADD CONSTRAINT solicitudes_doc_ref_check
        CHECK (doc_ref IS NULL OR doc_ref ~ '^[A-Za-z0-9_/-]{1,255}$'),
    ADD CONSTRAINT solicitudes_doc_url_check
        CHECK (
            doc_url IS NULL
            OR doc_url ~ '^https://docs\.google\.com/document/d/[A-Za-z0-9_-]{1,255}/edit$'
        );

-- Origen de la revisión: la primera la escribe el agente (`generada`);
-- las siguientes entran por «Traer cambios del Doc» (`editada_docs`).
-- Queda NULL en los borradores de los otros canales, que no son
-- revisiones de una solicitud web.
ALTER TABLE borradores
    ADD COLUMN origen VARCHAR(32);

ALTER TABLE borradores
    ADD CONSTRAINT borradores_origen_check
        CHECK (origen IS NULL OR origen IN ('generada', 'editada_docs'));

-- Una revisión importada no es una ejecución del pipeline: el vínculo
-- con `ejecuciones` queda opcional (sigue siendo FK) y deja de ser
-- único. Los eventos de revisión y decisión se asientan sobre la
-- ejecución original de la solicitud, que es su ciclo de vida.
ALTER TABLE borradores
    DROP CONSTRAINT borradores_id_ejecucion_key;
ALTER TABLE borradores
    ALTER COLUMN id_ejecucion DROP NOT NULL;

-- El texto de cada revisión importada vive acá, enlazado a su borrador,
-- como exige ADR 0016 (hash fuera de la prosa, texto que se purga).
ALTER TABLE prosa_transitoria
    ADD COLUMN id_borrador VARCHAR(128) REFERENCES borradores (id_borrador);

ALTER TABLE prosa_transitoria
    DROP CONSTRAINT prosa_transitoria_clase_check;
ALTER TABLE prosa_transitoria
    ADD CONSTRAINT prosa_transitoria_clase_check
        CHECK (
            clase IN (
                'descripcion', 'campos', 'ajuste', 'generado', 'importado'
            )
        );

-- La decisión del canal web guarda quién decidió (hash del correo, ya en
-- `validador_ref_hash`), con qué rol del padrón, desde qué origen de
-- identidad (`google` verificada o `demo` del modo demostración, ADR
-- 0019) y con qué versión del agente corrió el servidor.
ALTER TABLE validaciones
    ADD COLUMN rol VARCHAR(64),
    ADD COLUMN origen_identidad VARCHAR(16),
    ADD COLUMN version_agente VARCHAR(64);

ALTER TABLE validaciones
    ADD CONSTRAINT validaciones_rol_check
        CHECK (rol IS NULL OR rol ~ '^[A-Za-z0-9_.-]{1,64}$'),
    ADD CONSTRAINT validaciones_origen_identidad_check
        CHECK (
            origen_identidad IS NULL
            OR origen_identidad IN ('google', 'demo')
        ),
    ADD CONSTRAINT validaciones_version_agente_check
        CHECK (
            version_agente IS NULL
            OR version_agente ~ '^[0-9A-Za-z._-]{1,64}$'
        );

COMMIT;
