-- Lote de certificados en la web del Agente 1 (#168, ADR 0018).
--
-- El canal web reemplaza el correo al aprobador: el lote que hoy queda
-- `PENDIENTE_APROBACION` en la corrida de emisión se guarda acá para que
-- quien lo generó lo evalúe y lo decida en la web, sobre la lista de
-- cierre y un certificado de muestra marcado como borrador.
--
-- `objeto_lote` es el hash canónico de `objeto_lote_cierre` (actividad +
-- hash de la lista) y es único: el mismo lote no se duplica y cualquier
-- edición de la lista produce otro objeto. La decisión queda en la misma
-- fila porque es terminal y única: identidad, rol, origen y versión del
-- agente. `personas` es el único texto con datos personales; la purga
-- diaria del canal web lo deja en NULL cuando el lote ya se decidió y
-- conserva cantidad, hashes y decisión.
BEGIN;

CREATE TABLE lotes_certificados (
    id_lote VARCHAR(128) PRIMARY KEY,
    id_actividad VARCHAR(128) NOT NULL,
    objeto_lote CHAR(64) NOT NULL UNIQUE,
    hash_lista CHAR(64) NOT NULL,
    actividad JSONB NOT NULL,
    personas JSONB,
    cantidad_personas INTEGER NOT NULL,
    linea_descriptiva TEXT NOT NULL,
    plantilla_muestra VARCHAR(64) NOT NULL,
    estado VARCHAR(32) NOT NULL,
    generada_por_hash CHAR(64) NOT NULL,
    creada_en TIMESTAMPTZ NOT NULL,
    decidida_en TIMESTAMPTZ,
    decidida_por_hash CHAR(64),
    rol_decision VARCHAR(64),
    origen_identidad VARCHAR(16),
    version_agente VARCHAR(64),
    purgada_en TIMESTAMPTZ,
    CHECK (id_lote ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (id_actividad ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (objeto_lote ~ '^[0-9a-f]{64}$'),
    CHECK (hash_lista ~ '^[0-9a-f]{64}$'),
    CHECK (generada_por_hash ~ '^[0-9a-f]{64}$'),
    CHECK (decidida_por_hash IS NULL OR decidida_por_hash ~ '^[0-9a-f]{64}$'),
    CHECK (jsonb_typeof(actividad) = 'object'),
    CHECK (personas IS NULL OR jsonb_typeof(personas) = 'array'),
    CHECK (cantidad_personas >= 1),
    CHECK (estado IN ('PENDIENTE_APROBACION', 'APROBADA', 'DESCARTADA')),
    CHECK (
        rol_decision IS NULL
        OR rol_decision ~ '^[A-Za-z0-9_.-]{1,64}$'
    ),
    CHECK (
        origen_identidad IS NULL
        OR origen_identidad IN ('google', 'demo')
    ),
    CHECK (
        version_agente IS NULL
        OR version_agente ~ '^[0-9A-Za-z._-]{1,64}$'
    ),
    CHECK ((personas IS NULL) = (purgada_en IS NOT NULL)),
    CHECK (decidida_en IS NULL OR decidida_en >= creada_en),
    CHECK (purgada_en IS NULL OR purgada_en >= creada_en),
    CHECK (
        (
            estado = 'PENDIENTE_APROBACION'
            AND decidida_en IS NULL
            AND decidida_por_hash IS NULL
            AND rol_decision IS NULL
            AND origen_identidad IS NULL
            AND version_agente IS NULL
        )
        OR (
            estado IN ('APROBADA', 'DESCARTADA')
            AND decidida_en IS NOT NULL
            AND decidida_por_hash IS NOT NULL
            AND rol_decision IS NOT NULL
            AND origen_identidad IS NOT NULL
            AND version_agente IS NOT NULL
        )
    )
);

CREATE INDEX idx_lotes_certificados_estado
    ON lotes_certificados (estado, creada_en DESC);

-- La app lee, crea y decide (UPDATE del ciclo de vida del lote). La lista
-- de personas se retira con el mismo rol, como el resto del ciclo web; el
-- mantenimiento sólo la lee para el respaldo y la evidencia.
GRANT SELECT, INSERT, UPDATE ON lotes_certificados TO agente1_app;
GRANT SELECT ON lotes_certificados TO agente1_mantenimiento;

COMMIT;
