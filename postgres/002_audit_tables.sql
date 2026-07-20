-- ============================================================
-- 002_audit_tables.sql
-- Auditoría, trazabilidad, consolidación y errores del ETL.
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS etl_carga_auditoria (
    id_carga                 SERIAL PRIMARY KEY,
    tabla                    VARCHAR(80) NOT NULL,
    registros_leidos         INTEGER NOT NULL DEFAULT 0,
    registros_insertados     INTEGER NOT NULL DEFAULT 0,
    registros_actualizados   INTEGER NOT NULL DEFAULT 0,
    registros_con_error      INTEGER NOT NULL DEFAULT 0,
    duracion_segundos        NUMERIC(12,3),
    fecha_ejecucion          TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS etl_carga_errores (
    id_error                 SERIAL PRIMARY KEY,
    tabla                    VARCHAR(80) NOT NULL,
    identificador_registro   VARCHAR(200),
    mensaje_error            TEXT NOT NULL,
    registro_json            JSONB,
    fecha_error              TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cliente_origen_mapeo (
    id_cliente_origen        INTEGER PRIMARY KEY,
    id_cliente_sobreviviente INTEGER NOT NULL,
    id_cliente               INTEGER NOT NULL REFERENCES clientes(id_cliente),
    es_sobreviviente         BOOLEAN NOT NULL,
    fecha_actualizacion      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS auditoria_consolidacion (
    id_auditoria             SERIAL PRIMARY KEY,
    id_cliente_sobreviviente INTEGER NOT NULL UNIQUE,
    id_cliente               INTEGER NOT NULL REFERENCES clientes(id_cliente),
    ids_origen_grupo         JSONB NOT NULL,
    cantidad_registros       INTEGER NOT NULL,
    datos_maestro            JSONB NOT NULL,
    fecha_actualizacion      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS etl_transformacion_errores (
    id_error                 SERIAL PRIMARY KEY,
    entidad                  VARCHAR(50) NOT NULL,
    id_origen                INTEGER,
    campo                    VARCHAR(100) NOT NULL,
    valor_original           TEXT,
    motivo                   TEXT NOT NULL,
    fecha_actualizacion      TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_error_transformacion UNIQUE (entidad, id_origen, campo, motivo)
);

CREATE TABLE IF NOT EXISTS etl_validacion_resultado (
    id_validacion            SERIAL PRIMARY KEY,
    nombre_validacion        VARCHAR(120) NOT NULL,
    valor_origen             NUMERIC(18,2),
    valor_destino            NUMERIC(18,2),
    es_correcto              BOOLEAN NOT NULL,
    detalle                  TEXT,
    fecha_ejecucion          TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_carga_errores_tabla ON etl_carga_errores(tabla);
CREATE INDEX IF NOT EXISTS idx_carga_auditoria_tabla ON etl_carga_auditoria(tabla);
CREATE INDEX IF NOT EXISTS idx_mapeo_sobreviviente ON cliente_origen_mapeo(id_cliente_sobreviviente);
CREATE INDEX IF NOT EXISTS idx_transformacion_error_entidad ON etl_transformacion_errores(entidad);

COMMIT;
