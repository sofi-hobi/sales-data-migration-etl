-- ============================================================
-- load_queries.sql
-- Consultas SQL usadas por src/load/postgres_connector.py.
--
-- Formato: cada bloque empieza con un comentario "-- name: <nombre>"
-- y termina en el siguiente "-- name:" o en el fin del archivo.
-- postgres_connector.py lee este archivo y arma un diccionario
-- {nombre: sql}, así las consultas quedan en un solo lugar en vez
-- de estar "hardcodeadas" dentro del código Python.
--
-- Todas usan INSERT ... ON CONFLICT (...) DO UPDATE, que es la forma
-- estándar de Postgres de hacer "UPSERT":
--   - si la clave de negocio (documento, codigo_producto, etc.)
--     NO existe todavía          -> se hace un INSERT normal
--   - si la clave de negocio YA existe (duplicado)  -> se actualizan
--     sus columnas con los valores nuevos, en vez de crear una fila
--     repetida. Así se evitan los duplicados sin perder información.
--
-- El truco "(xmax = 0) AS fue_insertado" le permite al connector
-- distinguir, fila por fila, si el UPSERT terminó en un INSERT o en
-- un UPDATE, para poder generar las estadísticas de carga.
-- ============================================================

-- name: upsert_cliente
INSERT INTO clientes (
    id_cliente_origen, documento, nombre, apellido, correo, telefono,
    direccion, ciudad, fecha_nacimiento, fecha_registro, estado, ids_origen_grupo
) VALUES (
    %(id_cliente_origen)s, %(documento)s, %(nombre)s, %(apellido)s, %(correo)s,
    %(telefono)s, %(direccion)s, %(ciudad)s, %(fecha_nacimiento)s,
    %(fecha_registro)s, %(estado)s, %(ids_origen_grupo)s
)
ON CONFLICT (documento) DO UPDATE SET
    id_cliente_origen = EXCLUDED.id_cliente_origen,
    nombre            = EXCLUDED.nombre,
    apellido          = EXCLUDED.apellido,
    correo            = EXCLUDED.correo,
    telefono          = EXCLUDED.telefono,
    direccion         = EXCLUDED.direccion,
    ciudad            = EXCLUDED.ciudad,
    fecha_nacimiento  = EXCLUDED.fecha_nacimiento,
    fecha_registro    = EXCLUDED.fecha_registro,
    estado            = EXCLUDED.estado,
    ids_origen_grupo  = EXCLUDED.ids_origen_grupo
RETURNING id_cliente, (xmax = 0) AS fue_insertado;

-- name: upsert_producto
INSERT INTO productos (
    id_producto_origen, codigo_producto, nombre_producto, categoria, precio, estado, ids_origen_grupo
) VALUES (
    %(id_producto_origen)s, %(codigo_producto)s, %(nombre_producto)s,
    %(categoria)s, %(precio)s, %(estado)s, %(ids_origen_grupo)s
)
ON CONFLICT (codigo_producto) DO UPDATE SET
    id_producto_origen = EXCLUDED.id_producto_origen,
    nombre_producto    = EXCLUDED.nombre_producto,
    categoria          = EXCLUDED.categoria,
    precio             = EXCLUDED.precio,
    estado             = EXCLUDED.estado,
    ids_origen_grupo   = EXCLUDED.ids_origen_grupo
RETURNING id_producto, (xmax = 0) AS fue_insertado;

-- name: upsert_factura
INSERT INTO facturas (
    id_factura_origen, numero_factura, id_cliente_origen, id_cliente,
    fecha_emision, estado, subtotal, iva, total
) VALUES (
    %(id_factura_origen)s, %(numero_factura)s, %(id_cliente_origen)s,
    %(id_cliente)s, %(fecha_emision)s, %(estado)s,
    %(subtotal)s, %(iva)s, %(total)s
)
ON CONFLICT (numero_factura) DO UPDATE SET
    id_factura_origen = EXCLUDED.id_factura_origen,
    id_cliente_origen = EXCLUDED.id_cliente_origen,
    id_cliente        = EXCLUDED.id_cliente,
    fecha_emision     = EXCLUDED.fecha_emision,
    estado            = EXCLUDED.estado,
    subtotal          = EXCLUDED.subtotal,
    iva               = EXCLUDED.iva,
    total             = EXCLUDED.total
RETURNING id_factura, (xmax = 0) AS fue_insertado;

-- name: upsert_detalle
INSERT INTO detalles (
    id_detalle_origen, id_factura_origen, id_factura,
    id_producto_origen, id_producto,
    cantidad, precio_unitario, descuento, total_linea
) VALUES (
    %(id_detalle_origen)s, %(id_factura_origen)s, %(id_factura)s,
    %(id_producto_origen)s, %(id_producto)s,
    %(cantidad)s, %(precio_unitario)s, %(descuento)s, %(total_linea)s
)
ON CONFLICT (id_factura_origen, id_producto_origen) DO UPDATE SET
    id_factura      = EXCLUDED.id_factura,
    id_producto     = EXCLUDED.id_producto,
    cantidad        = EXCLUDED.cantidad,
    precio_unitario = EXCLUDED.precio_unitario,
    descuento       = EXCLUDED.descuento,
    total_linea     = EXCLUDED.total_linea
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
