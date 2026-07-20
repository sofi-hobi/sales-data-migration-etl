import os
import pyodbc
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

def get_sqlserver_data():
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={os.getenv('SQLSERVER_HOST', 'sqlserver')},{os.getenv('SQLSERVER_PORT', '1433')};"
        f"DATABASE={os.getenv('SQLSERVER_DATABASE', 'SmartCleanOrigen')};"
        f"UID={os.getenv('SQLSERVER_USER', 'sa')};"
        f"PWD={os.getenv('SQLSERVER_PASSWORD', 'Grupo1@BDD!')};"
        "TrustServerCertificate=yes;"
    )
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Clientes
        cursor.execute("SELECT TOP 20 idClienteOrigen, documento, nombre, apellido, correo, telefono, estadoTexto as estado FROM ClienteOrigen ORDER BY idClienteOrigen")
        cols = [column[0] for column in cursor.description]
        clientes = [dict(zip(cols, row)) for row in cursor.fetchall()]
        
        # Productos
        cursor.execute("SELECT TOP 20 idProductoOrigen, codigoProducto, nombreProducto, precio, estadoTexto as estado FROM ProductoOrigen ORDER BY idProductoOrigen")
        cols = [column[0] for column in cursor.description]
        productos = [dict(zip(cols, row)) for row in cursor.fetchall()]
        
        # Facturas
        cursor.execute("SELECT TOP 20 idFacturaOrigen, numeroFactura, idClienteOrigen, subtotal, total FROM FacturaOrigen ORDER BY idFacturaOrigen")
        cols = [column[0] for column in cursor.description]
        facturas = [dict(zip(cols, row)) for row in cursor.fetchall()]
        
        # Detalles
        cursor.execute("SELECT TOP 20 idDetalleOrigen, idFacturaOrigen, idProductoOrigen, cantidad, totalLinea FROM FacturaDetalleOrigen ORDER BY idDetalleOrigen")
        cols = [column[0] for column in cursor.description]
        detalles = [dict(zip(cols, row)) for row in cursor.fetchall()]

        conn.close()
        return {"clientes": clientes, "productos": productos, "facturas": facturas, "detalles": detalles}
    except Exception as e:
        print(f"Error SQL Server: {e}")
        return {"clientes": [], "productos": [], "facturas": [], "detalles": []}

def get_postgres_data():
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            dbname=os.getenv("POSTGRES_DB", "etl_destino"),
            user=os.getenv("POSTGRES_USER", "etl_user"),
            password=os.getenv("POSTGRES_PASSWORD", "Grupo1_PG!")
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Clientes
        cursor.execute("SELECT id_cliente_origen, documento, nombre, apellido, correo, telefono, estado FROM clientes ORDER BY id_cliente_origen")
        clientes = cursor.fetchall()
        
        # Productos
        cursor.execute("SELECT id_producto_origen, codigo_producto, nombre_producto, precio, estado FROM productos ORDER BY id_producto_origen")
        productos = cursor.fetchall()
        
        # Facturas
        cursor.execute("SELECT id_factura_origen, numero_factura, id_cliente_origen, subtotal, total FROM facturas ORDER BY id_factura_origen")
        facturas = cursor.fetchall()
        
        # Detalles
        cursor.execute("SELECT id_detalle_origen, id_factura_origen, id_producto_origen, cantidad, total_linea FROM detalles ORDER BY id_detalle_origen")
        detalles = cursor.fetchall()

        conn.close()
        return {"clientes": clientes, "productos": productos, "facturas": facturas, "detalles": detalles}
    except Exception as e:
        print(f"Error Postgres: {e}")
        return {"clientes": [], "productos": [], "facturas": [], "detalles": []}

@app.get("/api/data")
def read_data():
    return {
        "sqlserver": get_sqlserver_data(),
        "postgres": get_postgres_data()
    }

app.mount("/", StaticFiles(directory="static", html=True), name="static")
