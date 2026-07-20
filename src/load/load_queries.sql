-- name: upsert_cliente
INSERT INTO clientes (
    id_cliente_origen, documento, nombre, apellido, correo, telefono,
    direccion, ciudad, fecha_nacimiento, fecha_registro, estado, ids_origen_grupo
) VALUES (
    %(id_cliente_origen)s, %(documento)s, %(nombre)s, %(apellido)s, %(correo)s,
    %(telefono)s, %(direccion)s, %(ciudad)s, %(fecha_nacimiento)s,
    %(fecha_registro)s, %(estado)s, %(ids_origen_grupo)s::jsonb
)
ON CONFLICT (id_cliente_origen) DO UPDATE SET
    documento           = EXCLUDED.documento,
    nombre              = EXCLUDED.nombre,
    apellido            = EXCLUDED.apellido,
    correo              = EXCLUDED.correo,
    telefono            = EXCLUDED.telefono,
    direccion           = EXCLUDED.direccion,
    ciudad              = EXCLUDED.ciudad,
    fecha_nacimiento    = EXCLUDED.fecha_nacimiento,
    fecha_registro      = EXCLUDED.fecha_registro,
    estado              = EXCLUDED.estado,
    ids_origen_grupo    = EXCLUDED.ids_origen_grupo,
    fecha_actualizacion = now()
RETURNING id_cliente, (xmax = 0) AS fue_insertado;

-- name: upsert_producto
INSERT INTO productos (
    id_producto_origen, codigo_producto, nombre_producto, categoria, precio, estado, ids_origen_grupo
) VALUES (
    %(id_producto_origen)s, %(codigo_producto)s, %(nombre_producto)s,
    %(categoria)s, %(precio)s, %(estado)s, %(ids_origen_grupo)s::jsonb
)
ON CONFLICT (id_producto_origen) DO UPDATE SET
    codigo_producto     = EXCLUDED.codigo_producto,
    nombre_producto    = EXCLUDED.nombre_producto,
    categoria          = EXCLUDED.categoria,
    precio             = EXCLUDED.precio,
    estado             = EXCLUDED.estado,
    ids_origen_grupo   = EXCLUDED.ids_origen_grupo,
    fecha_actualizacion = now()
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
ON CONFLICT (id_factura_origen) DO UPDATE SET
    numero_factura      = EXCLUDED.numero_factura,
    id_cliente_origen   = EXCLUDED.id_cliente_origen,
    id_cliente          = EXCLUDED.id_cliente,
    fecha_emision       = EXCLUDED.fecha_emision,
    estado              = EXCLUDED.estado,
    subtotal            = EXCLUDED.subtotal,
    iva                 = EXCLUDED.iva,
    total               = EXCLUDED.total,
    fecha_actualizacion = now()
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
ON CONFLICT (id_detalle_origen) DO UPDATE SET
    id_factura_origen   = EXCLUDED.id_factura_origen,
    id_factura          = EXCLUDED.id_factura,
    id_producto_origen  = EXCLUDED.id_producto_origen,
    id_producto         = EXCLUDED.id_producto,
    cantidad            = EXCLUDED.cantidad,
    precio_unitario     = EXCLUDED.precio_unitario,
    descuento           = EXCLUDED.descuento,
    total_linea         = EXCLUDED.total_linea,
    fecha_actualizacion = now()
RETURNING id_detalle, (xmax = 0) AS fue_insertado;

-- name: upsert_cliente_mapeo
INSERT INTO cliente_origen_mapeo (
    id_cliente_origen, id_cliente_sobreviviente, id_cliente, es_sobreviviente
) VALUES (
    %(id_cliente_origen)s, %(id_cliente_sobreviviente)s, %(id_cliente)s, %(es_sobreviviente)s
)
ON CONFLICT (id_cliente_origen) DO UPDATE SET
    id_cliente_sobreviviente = EXCLUDED.id_cliente_sobreviviente,
    id_cliente               = EXCLUDED.id_cliente,
    es_sobreviviente         = EXCLUDED.es_sobreviviente,
    fecha_actualizacion      = now();

-- name: upsert_auditoria_consolidacion
INSERT INTO auditoria_consolidacion (
    id_cliente_sobreviviente, id_cliente, ids_origen_grupo,
    cantidad_registros, datos_maestro
) VALUES (
    %(id_cliente_sobreviviente)s, %(id_cliente)s, %(ids_origen_grupo)s::jsonb,
    %(cantidad_registros)s, %(datos_maestro)s::jsonb
)
ON CONFLICT (id_cliente_sobreviviente) DO UPDATE SET
    id_cliente          = EXCLUDED.id_cliente,
    ids_origen_grupo    = EXCLUDED.ids_origen_grupo,
    cantidad_registros  = EXCLUDED.cantidad_registros,
    datos_maestro       = EXCLUDED.datos_maestro,
    fecha_actualizacion = now();

-- name: upsert_error_transformacion
INSERT INTO etl_transformacion_errores (
    entidad, id_origen, campo, valor_original, motivo
) VALUES (
    %(entidad)s, %(id_origen)s, %(campo)s, %(valor_original)s, %(motivo)s
)
ON CONFLICT (entidad, id_origen, campo, motivo) DO UPDATE SET
    valor_original      = EXCLUDED.valor_original,
    fecha_actualizacion = now();

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
    %(tabla)s, %(identificador_registro)s, %(mensaje_error)s, %(registro_json)s::jsonb
);

-- name: insertar_validacion
INSERT INTO etl_validacion_resultado (
    nombre_validacion, valor_origen, valor_destino, es_correcto, detalle
) VALUES (
    %(nombre_validacion)s, %(valor_origen)s, %(valor_destino)s,
    %(es_correcto)s, %(detalle)s
);
