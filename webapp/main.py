from __future__ import annotations

import os
from contextlib import closing
from decimal import Decimal

import psycopg2
import pyodbc
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from psycopg2.extras import RealDictCursor

app = FastAPI(title="Validación del Pipeline ETL")
ROW_LIMIT = max(10, min(int(os.getenv("WEBAPP_ROW_LIMIT", "100")), 500))


def _sqlserver_connection_string() -> str:
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={os.getenv('SQLSERVER_HOST', 'sqlserver')},{os.getenv('SQLSERVER_PORT', '1433')};"
        f"DATABASE={os.getenv('SQLSERVER_DATABASE', 'SmartCleanOrigen')};"
        f"UID={os.getenv('SQLSERVER_USER', 'sa')};"
        f"PWD={os.getenv('SQLSERVER_PASSWORD', 'Grupo1@BDD!')};"
        "TrustServerCertificate=yes;Connection Timeout=15;"
    )


def _rows_as_dicts(cursor):
    columnas = [col[0] for col in cursor.description]
    return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def get_sqlserver_data() -> dict:
    with closing(pyodbc.connect(_sqlserver_connection_string())) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                (SELECT COUNT_BIG(*) FROM dbo.ClienteOrigen) AS clientes,
                (SELECT COUNT_BIG(*) FROM dbo.ProductoOrigen) AS productos,
                (SELECT COUNT_BIG(*) FROM dbo.FacturaOrigen) AS facturas,
                (SELECT COUNT_BIG(*) FROM dbo.FacturaDetalleOrigen) AS detalles,
                (SELECT COALESCE(SUM(Total), 0) FROM dbo.FacturaOrigen) AS total_facturado
        """)
        resumen = _rows_as_dicts(cursor)[0]

        cursor.execute(f"""SELECT TOP ({ROW_LIMIT})
            IdClienteOrigen AS idClienteOrigen, Documento AS documento,
            Nombre AS nombre, Apellido AS apellido, Correo AS correo,
            Telefono AS telefono, EstadoTexto AS estado
            FROM dbo.ClienteOrigen ORDER BY IdClienteOrigen""")
        clientes = _rows_as_dicts(cursor)

        cursor.execute(f"""SELECT TOP ({ROW_LIMIT})
            IdProductoOrigen AS idProductoOrigen, CodigoProducto AS codigoProducto,
            NombreProducto AS nombreProducto, Precio AS precio, EstadoTexto AS estado
            FROM dbo.ProductoOrigen ORDER BY IdProductoOrigen""")
        productos = _rows_as_dicts(cursor)

        cursor.execute(f"""SELECT TOP ({ROW_LIMIT})
            IdFacturaOrigen AS idFacturaOrigen, NumeroFactura AS numeroFactura,
            IdClienteOrigen AS idClienteOrigen, Subtotal AS subtotal, Total AS total
            FROM dbo.FacturaOrigen ORDER BY IdFacturaOrigen""")
        facturas = _rows_as_dicts(cursor)

        cursor.execute(f"""SELECT TOP ({ROW_LIMIT})
            IdDetalleOrigen AS idDetalleOrigen, IdFacturaOrigen AS idFacturaOrigen,
            IdProductoOrigen AS idProductoOrigen, Cantidad AS cantidad, TotalLinea AS totalLinea
            FROM dbo.FacturaDetalleOrigen ORDER BY IdDetalleOrigen""")
        detalles = _rows_as_dicts(cursor)

        return {
            "ok": True,
            "error": None,
            "resumen": resumen,
            "limite_muestra": ROW_LIMIT,
            "clientes": clientes,
            "productos": productos,
            "facturas": facturas,
            "detalles": detalles,
        }


def _postgres_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "etl_destino"),
        user=os.getenv("POSTGRES_USER", "etl_user"),
        password=os.getenv("POSTGRES_PASSWORD", "Grupo1_PG!"),
        connect_timeout=15,
    )


def get_postgres_data() -> dict:
    with closing(_postgres_connection()) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT
                    (SELECT COUNT(*) FROM clientes) AS clientes,
                    (SELECT COUNT(*) FROM productos) AS productos,
                    (SELECT COUNT(*) FROM facturas) AS facturas,
                    (SELECT COUNT(*) FROM detalles) AS detalles,
                    (SELECT COALESCE(SUM(total), 0) FROM facturas) AS total_facturado,
                    (SELECT COUNT(*) FROM auditoria_consolidacion) AS grupos_consolidados,
                    (SELECT COUNT(*) FROM etl_transformacion_errores) AS errores_calidad
            """)
            resumen = dict(cursor.fetchone())

            cursor.execute("""SELECT id_cliente_origen, documento, nombre, apellido, correo, telefono, estado
                FROM clientes ORDER BY id_cliente_origen LIMIT %s""", (ROW_LIMIT,))
            clientes = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""SELECT id_producto_origen, codigo_producto, nombre_producto, precio, estado
                FROM productos ORDER BY id_producto_origen LIMIT %s""", (ROW_LIMIT,))
            productos = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""SELECT id_factura_origen, numero_factura, id_cliente_origen, subtotal, total
                FROM facturas ORDER BY id_factura_origen LIMIT %s""", (ROW_LIMIT,))
            facturas = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""SELECT id_detalle_origen, id_factura_origen, id_producto_origen, cantidad, total_linea
                FROM detalles ORDER BY id_detalle_origen LIMIT %s""", (ROW_LIMIT,))
            detalles = [dict(r) for r in cursor.fetchall()]

            return {
                "ok": True,
                "error": None,
                "resumen": resumen,
                "limite_muestra": ROW_LIMIT,
                "clientes": clientes,
                "productos": productos,
                "facturas": facturas,
                "detalles": detalles,
            }


def _seguro(funcion) -> dict:
    try:
        return funcion()
    except Exception as exc:  # La UI debe mostrar el problema, no quedarse cargando.
        return {
            "ok": False,
            "error": str(exc),
            "resumen": {},
            "limite_muestra": ROW_LIMIT,
            "clientes": [], "productos": [], "facturas": [], "detalles": [],
        }


def _sqlserver_is_ready() -> bool:
    with closing(pyodbc.connect(_sqlserver_connection_string())) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return cursor.fetchone()[0] == 1


def _postgres_is_ready() -> bool:
    with closing(_postgres_connection()) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone()[0] == 1


@app.get("/api/health")
def health():
    # El healthcheck debe ser liviano: no vuelve a leer las ocho muestras de datos.
    sql_ok = False
    pg_ok = False
    try:
        sql_ok = _sqlserver_is_ready()
    except Exception:
        sql_ok = False
    try:
        pg_ok = _postgres_is_ready()
    except Exception:
        pg_ok = False
    return {"ok": sql_ok and pg_ok, "sqlserver": sql_ok, "postgres": pg_ok}


@app.get("/api/data")
def read_data():
    return {
        "sqlserver": _seguro(get_sqlserver_data),
        "postgres": _seguro(get_postgres_data),
    }


app.mount("/", StaticFiles(directory="static", html=True), name="static")
