-- ============================================================
-- 002_audit_tables.sql
-- Tablas de auditoria de la etapa de Load.
-- Corre DESPUES de 001_postgres_ddl.sql (orden alfabetico dentro de
-- /docker-entrypoint-initdb.d/), ya que no depende de las tablas de
-- negocio pero conceptualmente documenta lo que paso al cargarlas.
--
-- Integrante 4 - Etapa de Load
-- ============================================================

BEGIN;

-- Una fila por cada tabla cargada en cada corrida del pipeline.
-- Aqui se guardan las ESTADISTICAS agregadas que pide la tarea
-- ("Generar estadisticas de carga").
CREATE TABLE IF NOT EXISTS etl_carga_auditoria (
    id_carga                 SERIAL PRIMARY KEY,
    tabla                    VARCHAR(50) NOT NULL,
    registros_leidos         INTEGER NOT NULL DEFAULT 0,
    registros_insertados     INTEGER NOT NULL DEFAULT 0,
    registros_actualizados   INTEGER NOT NULL DEFAULT 0,
    registros_con_error      INTEGER NOT NULL DEFAULT 0,
    duracion_segundos        NUMERIC(10,3),
    fecha_ejecucion          TIMESTAMP NOT NULL DEFAULT now()
);

-- Detalle fila por fila de los errores de insercion, para poder
-- diagnosticar que registro fallo, por que, y reprocesarlo si hace falta.
CREATE TABLE IF NOT EXISTS etl_carga_errores (
    id_error               SERIAL PRIMARY KEY,
    tabla                  VARCHAR(50) NOT NULL,
    identificador_registro VARCHAR(200),   -- clave natural del registro que fallo
    mensaje_error          TEXT NOT NULL,
    registro_json          JSONB,          -- payload completo, para poder reintentar
    fecha_error            TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_carga_errores_tabla ON etl_carga_errores(tabla);
CREATE INDEX IF NOT EXISTS idx_carga_auditoria_tabla ON etl_carga_auditoria(tabla);

COMMIT;
