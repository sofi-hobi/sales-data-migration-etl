"""
src/extract/sqlserver_connector.py
Proyecto: Migración heterogénea SQL Server -> PostgreSQL

Responsabilidad (Integrante 2 - Extract): 
Conectarse a SQL Server, leer las tablas de origen de forma segura y 
extraer los registros crudos sin aplicar ninguna modificación o limpieza.
"""

import pyodbc
from typing import List, Dict, Any
from src.config.settings import get_settings

class SQLServerExtractor:
    def __init__(self):
        """Inicializa el extractor obteniendo la configuración centralizada."""
        self.settings = get_settings().sqlserver
        self._connection_string = self.settings.get_pyodbc_connection_string()

    def _ejecutar_consulta(self, query: str) -> List[Dict[str, Any]]:
        """
        Método privado auxiliar para manejar la apertura/cierre de conexiones 
        y mapear las filas del cursor a diccionarios de Python (clave: valor).
        """
        try:
            with pyodbc.connect(self._connection_string) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    columnas = [col[0] for col in cursor.description]
                    return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
        except pyodbc.Error as e:
            raise RuntimeError(f"Error crítico al extraer datos de SQL Server: {e}")

    def extraer_clientes(self) -> List[Dict[str, Any]]:
        """Lee la tabla completa ClienteOrigen con la data cruda.

        IMPORTANTE: trae TODAS las columnas que necesita la etapa de
        Transform (src/transform/cleansing.py::limpiar_cliente), no solo
        Nombre/Apellido/Correo. Ver src/extract/extract_queries.sql.
        """
        query = """
        SELECT IdClienteOrigen, Documento, Nombre, Apellido, Correo, Telefono,
               Direccion, Ciudad, FechaNacimientoTexto, FechaRegistroTexto,
               EstadoTexto, FechaCreacionSistema, FechaActualizacion
        FROM dbo.ClienteOrigen
        ORDER BY IdClienteOrigen;
        """
        return self._ejecutar_consulta(query)

    def extraer_productos(self) -> List[Dict[str, Any]]:
        """Lee la tabla completa ProductoOrigen con sus columnas reales."""
        query = """
        SELECT IdProductoOrigen, CodigoProducto, NombreProducto, 
               CategoriaTexto, Precio, EstadoTexto, 
               FechaCreacionSistema, FechaActualizacion 
        FROM dbo.ProductoOrigen
        ORDER BY IdProductoOrigen;
        """
        return self._ejecutar_consulta(query)

    def extraer_facturas(self) -> List[Dict[str, Any]]:
        """Lee la tabla completa FacturaOrigen mapeando sus columnas reales."""
        query = """
        SELECT IdFacturaOrigen, NumeroFactura, IdClienteOrigen, 
               FechaEmisionTexto, EstadoTexto, Subtotal, IVA, Total, 
               FechaCreacionSistema, FechaActualizacion 
        FROM dbo.FacturaOrigen
        ORDER BY IdFacturaOrigen;
        """
        return self._ejecutar_consulta(query)

    def extraer_detalles_factura(self) -> List[Dict[str, Any]]:
        """Lee la tabla completa FacturaDetalleOrigen mapeando sus columnas reales."""
        query = """
        SELECT IdDetalleOrigen, IdFacturaOrigen, IdProductoOrigen, 
               Cantidad, PrecioUnitario, Descuento, TotalLinea, 
               FechaCreacionSistema, FechaActualizacion 
        FROM dbo.FacturaDetalleOrigen
        ORDER BY IdDetalleOrigen;
        """
        return self._ejecutar_consulta(query)

    def extraer_todo(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Orquesta la extracción completa de todas las tablas origen del ETL.
        Devuelve un diccionario unificado listo para la fase de Transformación.
        """
        print("🚀 Iniciando extracción masiva de datos desde SQL Server...")
        
        data_cruda = {
            "clientes": self.extraer_clientes(),
            "productos": self.extraer_productos(),
            "facturas": self.extraer_facturas(),
            "detalles": self.extraer_detalles_factura()
        }
        
        print("✨ Extracción masiva completada con éxito.")
        return data_cruda


if __name__ == "__main__":
    # Prueba del pipeline de extracción completo (Health Check Integrante 2)
    try:
        extractor = SQLServerExtractor()
        resultado = extractor.extraer_todo()
        
        print("\n📊 RESUMEN DE LA DATA CRUDA EXTRAÍDA:")
        for tabla, registros in resultado.items():
            print(f"🔹 Tabla '{tabla}': {len(registros)} registros extraídos.")
            
    except Exception as exc:
        print(f"❌ Falló la prueba de extracción: {exc}")