-- Emisión durable del lote de certificados aprobado en la web (#168).
--
-- La decisión del lote sigue viviendo en `lotes_certificados`: ahí quedó el
-- snapshot que se mostró al aprobar (actividad, lista, línea descriptiva).
-- Esta cola sólo guarda el trabajo y el puntero a ese snapshot. No copia
-- DNI, correos, nombres ni PDFs: la descarga se compone al vuelo desde el
-- lote mientras la retención lo permita.
--
-- `origen_creacion` distingue el lote ficticio de la demo (`demo`) del lote
-- real (`google`, el origen de identidad de la sesión). Es opcional para no
-- romper a quien ya crea lotes: el default `NULL` es el lote legacy, salvo
-- que el predicado de demo del dominio lo reconozca por su semilla.
--
-- Estados del trabajo real:
--   PENDIENTE  -> esperando worker
--   RESERVADA  -> un worker lo tomó, todavía no empezó a enviar
--   ENVIANDO   -> el motor ya puede haber mandado correo
--   EMITIDA / EMITIDA_PARCIAL / FALLIDA / EXPIRADA
--   INDETERMINADA -> el worker cayó mientras enviaba: no se reintenta
-- Estados del trabajo demo:
--   PENDIENTE/RESERVADA -> el worker lo tomó para componer el render
--   GENERADA_DEMO -> el render salió y la descarga ZIP queda habilitada
--   FALLIDA / EXPIRADA
-- El trabajo demo nunca llega a ENVIANDO ni a INDETERMINADA: no envía
-- nada, así que una caída a mitad del render sólo lo devuelve a la cola.
--
-- El lock real es PostgreSQL: `FOR UPDATE SKIP LOCKED` para la reserva y el
-- token de reserva para que un worker vencido no cierre el trabajo de otro.
BEGIN;

ALTER TABLE lotes_certificados
    ADD COLUMN origen_creacion VARCHAR(16);

ALTER TABLE lotes_certificados
    ADD CONSTRAINT lotes_certificados_origen_creacion_check
    CHECK (origen_creacion IS NULL OR origen_creacion IN ('google', 'demo'));

CREATE TABLE emisiones_certificados (
    id_emision VARCHAR(128) PRIMARY KEY,
    id_lote VARCHAR(128) NOT NULL UNIQUE
        REFERENCES lotes_certificados (id_lote) ON DELETE RESTRICT,
    modo VARCHAR(16) NOT NULL,
    estado VARCHAR(24) NOT NULL,
    intentos INTEGER NOT NULL DEFAULT 0,
    reservada_por VARCHAR(128),
    token_reserva CHAR(64),
    reservada_hasta TIMESTAMPTZ,
    iniciada_en TIMESTAMPTZ,
    terminada_en TIMESTAMPTZ,
    expira_en TIMESTAMPTZ NOT NULL,
    retencion_hasta TIMESTAMPTZ,
    total INTEGER NOT NULL DEFAULT 0,
    enviadas INTEGER NOT NULL DEFAULT 0,
    fallidas INTEGER NOT NULL DEFAULT 0,
    error_codigo VARCHAR(64),
    modo_envio VARCHAR(16),
    plantillas_hash CHAR(64),
    creada_en TIMESTAMPTZ NOT NULL,
    actualizada_en TIMESTAMPTZ NOT NULL,
    CHECK (id_emision ~ '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$'),
    CHECK (modo IN ('real', 'demo')),
    CHECK (estado IN (
        'PENDIENTE', 'RESERVADA', 'ENVIANDO',
        'EMITIDA', 'EMITIDA_PARCIAL', 'FALLIDA', 'INDETERMINADA',
        'GENERADA_DEMO', 'EXPIRADA'
    )),
    CHECK (modo = 'demo' OR estado <> 'GENERADA_DEMO'),
    CHECK (modo <> 'demo' OR estado IN (
        'PENDIENTE', 'RESERVADA', 'GENERADA_DEMO', 'FALLIDA', 'EXPIRADA'
    )),
    CHECK (intentos >= 0),
    CHECK (total >= 0 AND enviadas >= 0 AND fallidas >= 0),
    CHECK (enviadas + fallidas <= total),
    CHECK (modo_envio IS NULL OR modo_envio IN ('prueba', 'produccion')),
    CHECK (plantillas_hash IS NULL OR plantillas_hash ~ '^[0-9a-f]{64}$'),
    CHECK (error_codigo IS NULL OR error_codigo ~ '^[A-Za-z0-9_.-]{1,64}$'),
    CHECK (
        (estado IN ('PENDIENTE', 'RESERVADA', 'ENVIANDO')
         AND terminada_en IS NULL)
        OR
        (estado IN ('EMITIDA', 'EMITIDA_PARCIAL', 'FALLIDA',
                    'INDETERMINADA', 'GENERADA_DEMO', 'EXPIRADA')
         AND terminada_en IS NOT NULL)
    ),
    CHECK ((reservada_por IS NULL) = (token_reserva IS NULL)),
    CHECK ((reservada_por IS NULL) = (reservada_hasta IS NULL)),
    CHECK (reservada_por IS NULL OR estado IN ('RESERVADA', 'ENVIANDO')),
    CHECK (expira_en >= creada_en),
    CHECK (retencion_hasta IS NULL OR retencion_hasta >= creada_en),
    CHECK (estado <> 'INDETERMINADA' OR retencion_hasta IS NULL)
);

CREATE INDEX idx_emisiones_certificados_estado
    ON emisiones_certificados (estado, creada_en);

CREATE INDEX idx_emisiones_certificados_reserva
    ON emisiones_certificados (reservada_hasta)
    WHERE estado IN ('RESERVADA', 'ENVIANDO');

-- La app encola, reclama y cierra; el mantenimiento sólo lee para no purgar
-- un lote con emisión viva. La cola no tiene texto de titulares, así que no
-- hay columna que el rol de la app deba tener vedada.
GRANT SELECT, INSERT ON emisiones_certificados TO agente1_app;
GRANT UPDATE (
    estado, intentos, reservada_por, token_reserva, reservada_hasta,
    iniciada_en, terminada_en, retencion_hasta, total, enviadas, fallidas,
    error_codigo, modo_envio, plantillas_hash, actualizada_en
) ON emisiones_certificados TO agente1_app;
GRANT SELECT ON emisiones_certificados TO agente1_mantenimiento;

COMMIT;
