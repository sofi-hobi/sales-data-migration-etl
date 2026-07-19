# __init__.py
"""Paquete de transformacion - Integrante 3 (ETL - Transform).

Punto de entrada recomendado para el resto del pipeline: `ejecutar_transformacion`.
Todas las demas funciones tambien se exponen aqui por si se necesitan por separado
(por ejemplo, para pruebas unitarias o para depurar un caso puntual).
"""
from .cleansing import (
    limpiar_cliente,
    limpiar_correo,
    limpiar_detalle,
    limpiar_documento,
    limpiar_estado,
    limpiar_factura,
    limpiar_producto,
    limpiar_telefono,
    limpiar_texto,
    normalizar_nombre,
    parsear_fecha,
)
from .deduplication import agrupar_duplicados_clientes, agrupar_duplicados_productos
from .fk_reassignment import (
    construir_mapa_sobrevivientes,
    reasignar_detalles,
    reasignar_facturas,
)
from .orchestrator import ejecutar_transformacion
from .survivorship import elegir_sobreviviente_cliente, elegir_sobreviviente_producto
from .validation import (
    detectar_inconsistencias_cliente,
    detectar_inconsistencias_detalle,
    detectar_inconsistencias_factura,
    generar_lista_errores,
    validar_codigo_producto,
    validar_correo,
    validar_documento,
    validar_precio_producto,
    validar_telefono,
)

__all__ = [
    "limpiar_cliente",
    "limpiar_correo",
    "limpiar_detalle",
    "limpiar_documento",
    "limpiar_estado",
    "limpiar_factura",
    "limpiar_producto",
    "limpiar_telefono",
    "limpiar_texto",
    "normalizar_nombre",
    "parsear_fecha",
    "agrupar_duplicados_clientes",
    "agrupar_duplicados_productos",
    "construir_mapa_sobrevivientes",
    "reasignar_detalles",
    "reasignar_facturas",
    "elegir_sobreviviente_cliente",
    "elegir_sobreviviente_producto",
    "detectar_inconsistencias_cliente",
    "detectar_inconsistencias_detalle",
    "detectar_inconsistencias_factura",
    "generar_lista_errores",
    "validar_codigo_producto",
    "validar_correo",
    "validar_documento",
    "validar_precio_producto",
    "validar_telefono",
    "ejecutar_transformacion",
]
