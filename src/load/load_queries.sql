-- ============================================================
-- load_queries.sql
-- Consultas SQL usadas por src/load/postgres_connector.py.
--
-- Formato: cada bloque empieza con un comentario "-- name: <nombre>"
-- y termina en el siguiente "-- name:" o en el fin del archivo.
-- postgres_connector.py lee este archivo y arma un diccionario
-- {nombre: sql}, asi las consultas quedan en un solo lugar en vez
-- de estar "hardcodeadas" dentro del codigo Python.
--
-- Todas usan INSERT ... ON CONFLICT (...) DO UPDATE, que es la forma
-- estandar de Postgres de hacer "UPSERT":
--   - si la clave de negocio (documento, codigo, numero_factura, etc.)
--     NO existe todavia          -> se hace un INSERT normal
--   - si la clave de negocio YA existe (duplicado)  -> se actualizan
--     sus columnas con los valores nuevos, en vez de crear una fila
--     repetida. Asi se evitan los duplicados sin perder informacion.
--
-- El truco "(xmax = 0) AS fue_insertado" le permite al connector
-- distinguir, fila por fila, si el UPSERT termino en un INSERT o en
-- un UPDATE, para poder generar las estadisticas de carga.
-- ============================================================

-- name: upsert_cliente
INSERT INTO clientes (
    id_cliente_origen, documento, nombre, email, telefono, direccion, ids_origen_grupo
) VALUES (
    %(id_cliente_origen)s, %(documento)s, %(nombre)s, %(email)s, %(telefono)s, %(direccion)s, %(ids_origen_grupo)s
)
ON CONFLICT (documento) DO UPDATE SET
    id_cliente_origen = EXCLUDED.id_cliente_origen,
    nombre            = EXCLUDED.nombre,
    email             = EXCLUDED.email,
    telefono          = EXCLUDED.telefono,
    direccion         = EXCLUDED.direccion,
    ids_origen_grupo  = EXCLUDED.ids_origen_grupo
RETURNING id_cliente, (xmax = 0) AS fue_insertado;

-- name: upsert_producto
INSERT INTO productos (
    id_producto_origen, codigo, nombre, categoria, precio, ids_origen_grupo
) VALUES (
    %(id_producto_origen)s, %(codigo)s, %(nombre)s, %(categoria)s, %(precio)s, %(ids_origen_grupo)s
)
ON CONFLICT (codigo) DO UPDATE SET
    id_producto_origen = EXCLUDED.id_producto_origen,
    nombre             = EXCLUDED.nombre,
    categoria          = EXCLUDED.categoria,
    precio             = EXCLUDED.precio,
    ids_origen_grupo   = EXCLUDED.ids_origen_grupo
RETURNING id_producto, (xmax = 0) AS fue_insertado;

-- name: upsert_factura
INSERT INTO facturas (
    numero_factura, id_cliente_origen, id_cliente, fecha_factura, total
) VALUES (
    %(numero_factura)s, %(id_cliente_origen)s, %(id_cliente)s, %(fecha_factura)s, %(total)s
)
ON CONFLICT (numero_factura) DO UPDATE SET
    id_cliente_origen = EXCLUDED.id_cliente_origen,
    id_cliente        = EXCLUDED.id_cliente,
    fecha_factura     = EXCLUDED.fecha_factura,
    total             = EXCLUDED.total
RETURNING id_factura, (xmax = 0) AS fue_insertado;

-- name: upsert_detalle
INSERT INTO detalles (
    numero_factura, id_factura, id_producto_origen, id_producto, cantidad, precio_unitario
) VALUES (
    %(numero_factura)s, %(id_factura)s, %(id_producto_origen)s, %(id_producto)s, %(cantidad)s, %(precio_unitario)s
)
ON CONFLICT (numero_factura, id_producto_origen) DO UPDATE SET
    id_factura      = EXCLUDED.id_factura,
    id_producto     = EXCLUDED.id_producto,
    cantidad        = EXCLUDED.cantidad,
    precio_unitario = EXCLUDED.precio_unitario
RETURNING id_detalle, (xmax = 0) AS fue_insertado;

-- name: insertar_auditoria_carga
INSERT INTO etl_carga_auditoria (
    tabla, registros_leidos, registros_insertados, registros_actualizados,
    registros_con_error, duracion_segundos
) VALUES (
    %(tabla)s, %(registros_leidos)s, %(registros_insertados)s, %(registros_actualizados)s,
    %(registros_con_error)s, %(duracion_segundos)s
);

-- name: insertar_error_carga
INSERT INTO etl_carga_errores (
    tabla, identificador_registro, mensaje_error, registro_json
) VALUES (
    %(tabla)s, %(identificador_registro)s, %(mensaje_error)s, %(registro_json)s
);
