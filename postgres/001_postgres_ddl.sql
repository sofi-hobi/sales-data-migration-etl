-- ============================================================
-- 001_postgres_ddl.sql
-- DDL del esquema destino (base "etl_destino") para el pipeline ETL.
--
-- Se ejecuta AUTOMATICAMENTE la primera vez que arranca el contenedor
-- "postgres" (ver docker-compose.yml -> build: ./postgres -> Dockerfile
-- -> COPY *.sql /docker-entrypoint-initdb.d/). Postgres corre los
-- scripts de esa carpeta en orden alfabetico, por eso este archivo
-- lleva el prefijo "001_" y debe ejecutarse ANTES que
-- "002_audit_tables.sql".
-- ============================================================

BEGIN;

-- ---------------------------------------------------------------
-- Clientes
-- Ya llegan deduplicados y fusionados desde Transform (Integrante 3):
-- una fila por cliente "sobreviviente".
-- La unicidad se controla por "documento" (clave de negocio real).
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clientes (
    id_cliente          SERIAL PRIMARY KEY,
    id_cliente_origen   INTEGER NOT NULL,
    documento           VARCHAR(50)  NOT NULL,
    nombre              VARCHAR(200),
    apellido            VARCHAR(200),
    correo              VARCHAR(200),
    telefono            VARCHAR(50),
    direccion           VARCHAR(300),
    ciudad              VARCHAR(100),
    fecha_nacimiento    DATE,
    fecha_registro      DATE,
    estado              VARCHAR(20) DEFAULT 'ACTIVO',
    ids_origen_grupo    TEXT,
    fecha_carga         TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_clientes_documento UNIQUE (documento)
);

-- ---------------------------------------------------------------
-- Productos
-- Unicidad por "codigo_producto".
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS productos (
    id_producto         SERIAL PRIMARY KEY,
    id_producto_origen  INTEGER NOT NULL,
    codigo_producto     VARCHAR(50) NOT NULL,
    nombre_producto     VARCHAR(200),
    categoria           VARCHAR(100),
    precio              NUMERIC(12,2),
    estado              VARCHAR(20) DEFAULT 'ACTIVO',
    ids_origen_grupo    TEXT,
    fecha_carga         TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_productos_codigo UNIQUE (codigo_producto)
);

-- ---------------------------------------------------------------
-- Facturas
-- id_cliente_origen ya viene REASIGNADO al cliente sobreviviente
-- (etapa fk_reassignment.py de Transform). id_cliente es la FK real
-- hacia la tabla clientes de este esquema, resuelta durante el Load.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS facturas (
    id_factura          SERIAL PRIMARY KEY,
    id_factura_origen   INTEGER NOT NULL,
    numero_factura      VARCHAR(50) NOT NULL,
    id_cliente_origen   INTEGER NOT NULL,
    id_cliente          INTEGER REFERENCES clientes(id_cliente),
    fecha_emision       DATE,
    estado              VARCHAR(20) DEFAULT 'ACTIVO',
    subtotal            NUMERIC(14,2),
    iva                 NUMERIC(14,2),
    total               NUMERIC(14,2),
    fecha_carga         TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_facturas_numero UNIQUE (numero_factura)
);

-- ---------------------------------------------------------------
-- Detalles de factura
-- id_producto_origen ya viene reasignado al producto sobreviviente.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS detalles (
    id_detalle           SERIAL PRIMARY KEY,
    id_detalle_origen    INTEGER NOT NULL,
    id_factura_origen    INTEGER NOT NULL,
    id_factura           INTEGER REFERENCES facturas(id_factura),
    id_producto_origen   INTEGER NOT NULL,
    id_producto          INTEGER REFERENCES productos(id_producto),
    cantidad             NUMERIC(12,2),
    precio_unitario      NUMERIC(12,2),
    descuento            NUMERIC(12,2) DEFAULT 0,
    total_linea          NUMERIC(14,2),
    fecha_carga          TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_detalles_factura_producto UNIQUE (id_factura_origen, id_producto_origen)
);

CREATE INDEX IF NOT EXISTS idx_facturas_cliente  ON facturas(id_cliente);
CREATE INDEX IF NOT EXISTS idx_detalles_factura  ON detalles(id_factura);
CREATE INDEX IF NOT EXISTS idx_detalles_producto ON detalles(id_producto);

COMMIT;
