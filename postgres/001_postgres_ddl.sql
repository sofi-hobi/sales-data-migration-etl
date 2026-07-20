-- ============================================================
-- 001_postgres_ddl.sql
-- Esquema normalizado de destino para PostgreSQL.
-- Se ejecuta automáticamente al crear por primera vez el volumen.
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS clientes (
    id_cliente          SERIAL PRIMARY KEY,
    id_cliente_origen   INTEGER NOT NULL,
    documento           VARCHAR(50),
    nombre              VARCHAR(200),
    apellido            VARCHAR(200),
    correo              VARCHAR(200),
    telefono            VARCHAR(50),
    direccion           VARCHAR(300),
    ciudad              VARCHAR(100),
    fecha_nacimiento    DATE,
    fecha_registro      DATE,
    estado              VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    ids_origen_grupo    JSONB NOT NULL DEFAULT '[]'::jsonb,
    fecha_carga         TIMESTAMP NOT NULL DEFAULT now(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_clientes_id_origen UNIQUE (id_cliente_origen),
    CONSTRAINT ck_clientes_estado CHECK (estado IN ('ACTIVO', 'INACTIVO'))
);

-- Los clientes sin documento/correo también deben migrarse. La unicidad se
-- aplica únicamente cuando el valor limpio no es NULL.
CREATE UNIQUE INDEX IF NOT EXISTS uq_clientes_documento_no_nulo
    ON clientes(documento) WHERE documento IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_clientes_correo_no_nulo
    ON clientes(correo) WHERE correo IS NOT NULL;

CREATE TABLE IF NOT EXISTS productos (
    id_producto         SERIAL PRIMARY KEY,
    id_producto_origen  INTEGER NOT NULL,
    codigo_producto     VARCHAR(50) NOT NULL,
    nombre_producto     VARCHAR(200),
    categoria           VARCHAR(100),
    precio              NUMERIC(12,2),
    estado              VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    ids_origen_grupo    JSONB NOT NULL DEFAULT '[]'::jsonb,
    fecha_carga         TIMESTAMP NOT NULL DEFAULT now(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_productos_id_origen UNIQUE (id_producto_origen),
    CONSTRAINT uq_productos_codigo UNIQUE (codigo_producto),
    CONSTRAINT ck_productos_precio CHECK (precio IS NULL OR precio >= 0),
    CONSTRAINT ck_productos_estado CHECK (estado IN ('ACTIVO', 'INACTIVO'))
);

CREATE TABLE IF NOT EXISTS facturas (
    id_factura          SERIAL PRIMARY KEY,
    id_factura_origen   INTEGER NOT NULL,
    numero_factura      VARCHAR(50) NOT NULL,
    id_cliente_origen   INTEGER NOT NULL,
    id_cliente          INTEGER NOT NULL REFERENCES clientes(id_cliente),
    fecha_emision       DATE,
    estado              VARCHAR(20) NOT NULL DEFAULT 'EMITIDA',
    subtotal            NUMERIC(14,2) NOT NULL,
    iva                 NUMERIC(14,2) NOT NULL,
    total               NUMERIC(14,2) NOT NULL,
    fecha_carga         TIMESTAMP NOT NULL DEFAULT now(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_facturas_id_origen UNIQUE (id_factura_origen),
    CONSTRAINT uq_facturas_numero UNIQUE (numero_factura),
    CONSTRAINT ck_facturas_montos CHECK (subtotal >= 0 AND iva >= 0 AND total >= 0),
    CONSTRAINT ck_facturas_estado CHECK (estado IN ('PAGADA', 'PENDIENTE', 'ANULADA', 'EMITIDA', 'VENCIDA'))
);

CREATE TABLE IF NOT EXISTS detalles (
    id_detalle           SERIAL PRIMARY KEY,
    id_detalle_origen    INTEGER NOT NULL,
    id_factura_origen    INTEGER NOT NULL,
    id_factura           INTEGER NOT NULL REFERENCES facturas(id_factura),
    id_producto_origen   INTEGER NOT NULL,
    id_producto          INTEGER NOT NULL REFERENCES productos(id_producto),
    cantidad             NUMERIC(12,2) NOT NULL,
    precio_unitario      NUMERIC(12,2) NOT NULL,
    descuento            NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_linea          NUMERIC(14,2) NOT NULL,
    fecha_carga          TIMESTAMP NOT NULL DEFAULT now(),
    fecha_actualizacion  TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_detalles_id_origen UNIQUE (id_detalle_origen),
    CONSTRAINT ck_detalles_valores CHECK (
        cantidad > 0 AND precio_unitario >= 0 AND descuento >= 0 AND total_linea >= 0
    )
);

CREATE INDEX IF NOT EXISTS idx_facturas_cliente  ON facturas(id_cliente);
CREATE INDEX IF NOT EXISTS idx_detalles_factura  ON detalles(id_factura);
CREATE INDEX IF NOT EXISTS idx_detalles_producto ON detalles(id_producto);

COMMIT;
