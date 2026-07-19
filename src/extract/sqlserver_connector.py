# sqlserver_connector.py
"""Extraccion de datos crudos desde SmartCleanOrigen (SQL Server).

Lee las cuatro tablas de origen tal cual estan (con duplicados, nulos y
fechas en texto sin convertir) y las devuelve como listas de diccionarios
para que src/transform se encargue del saneo.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import pyodbc

from src.config.logging_config import get_logger
from src.config.settings import SqlServerConfig, get_sqlserver_config

logger = get_logger(__name__)

QUERIES: dict[str, str] = {
    "clientes": "SELECT * FROM dbo.ClienteOrigen;",
    "productos": "SELECT * FROM dbo.ProductoOrigen;",
    "facturas": "SELECT * FROM dbo.FacturaOrigen;",
    "detalles": "SELECT * FROM dbo.FacturaDetalleOrigen;",
}


@contextmanager
def sqlserver_connection(config: SqlServerConfig | None = None) -> Iterator[pyodbc.Connection]:
    """Abre una conexion a SQL Server y la cierra automaticamente al salir del bloque."""
    config = config or get_sqlserver_config()
    conn = pyodbc.connect(config.odbc_connection_string, timeout=10)
    try:
        yield conn
    finally:
        conn.close()


def _fetch_as_dicts(cursor: pyodbc.Cursor) -> list[dict]:
    columnas = [columna[0] for columna in cursor.description]
    return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def extract_all(config: SqlServerConfig | None = None) -> dict[str, list[dict]]:
    """Extrae clientes, productos, facturas y detalles desde SQL Server."""
    resultado: dict[str, list[dict]] = {}
    with sqlserver_connection(config) as conn:
        cursor = conn.cursor()
        for nombre, query in QUERIES.items():
            logger.info("Extrayendo '%s' desde SQL Server...", nombre)
            cursor.execute(query)
            filas = _fetch_as_dicts(cursor)
            logger.info("  -> %d filas leidas de %s", len(filas), nombre)
            resultado[nombre] = filas
    return resultado
