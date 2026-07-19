# orchestrator.py
"""Punto de entrada unico de la etapa de Transform (Integrante 3).

Conecta, en orden, todas las reglas de esta etapa:
  1. Limpieza / normalizacion de cada tabla       (cleansing.py)
  2. Deteccion de duplicados                      (deduplication.py)
  3. Eleccion y fusion del registro sobreviviente  (survivorship.py)
  4. Reasignacion de FKs hacia el sobreviviente    (fk_reassignment.py)
  5. Validaciones + deteccion de inconsistencias   (validation.py)

Quien construya el pipeline completo (extract -> transform -> load) solo
necesita llamar a `ejecutar_transformacion(datos_crudos)` con lo que haya
devuelto el extractor (ver src/extract/extract_queries.sql para el formato
de columnas esperado: PascalCase).
"""
from __future__ import annotations

from .cleansing import limpiar_cliente, limpiar_detalle, limpiar_factura, limpiar_producto
from .deduplication import agrupar_duplicados_clientes, agrupar_duplicados_productos
from .fk_reassignment import (
    construir_mapa_sobrevivientes,
    reasignar_detalles,
    reasignar_facturas,
)
from .survivorship import elegir_sobreviviente_cliente, elegir_sobreviviente_producto
from .validation import generar_lista_errores


def ejecutar_transformacion(datos_crudos):
    """Ejecuta toda la etapa de Transform sobre los datos extraidos.

    Parametros
    ----------
    datos_crudos: dict con llaves 'clientes', 'productos', 'facturas',
    'detalles' -> cada una una lista de dicts tal como los entrega el
    extractor (PascalCase: IdClienteOrigen, Documento, Nombre, ...).

    Retorna
    -------
    dict con:
      - clientes, productos: listas ya limpias, deduplicadas y fusionadas
        (un registro por grupo de duplicados, con 'ids_origen_grupo')
      - facturas, detalles: listas limpias con las FKs ya reasignadas
        al registro sobreviviente correspondiente
      - errores: lista de errores de validacion / inconsistencias
        detectados durante todo el proceso
    """
    clientes_crudos = datos_crudos.get("clientes", [])
    productos_crudos = datos_crudos.get("productos", [])
    facturas_crudas = datos_crudos.get("facturas", [])
    detalles_crudos = datos_crudos.get("detalles", [])

    # 1. Limpieza / normalizacion
    clientes_limpios = [limpiar_cliente(c) for c in clientes_crudos]
    productos_limpios = [limpiar_producto(p) for p in productos_crudos]
    facturas_limpias = [limpiar_factura(f) for f in facturas_crudas]
    detalles_limpios = [limpiar_detalle(d) for d in detalles_crudos]

    # 2. Deteccion de duplicados
    grupos_clientes = agrupar_duplicados_clientes(clientes_limpios)
    grupos_productos = agrupar_duplicados_productos(productos_limpios)

    # 3. Survivorship: se elige y fusiona un sobreviviente por grupo
    clientes_por_id = {c["id_cliente_origen"]: c for c in clientes_limpios}
    productos_por_id = {p["id_producto_origen"]: p for p in productos_limpios}

    sobrevivientes_clientes = [
        elegir_sobreviviente_cliente(grupo, clientes_por_id) for grupo in grupos_clientes
    ]
    sobrevivientes_productos = [
        elegir_sobreviviente_producto(grupo, productos_por_id) for grupo in grupos_productos
    ]

    # 4. Reasignacion de FKs hacia los sobrevivientes
    mapa_clientes = construir_mapa_sobrevivientes(
        sobrevivientes_clientes, "id_cliente_origen_sobreviviente"
    )
    mapa_productos = construir_mapa_sobrevivientes(
        sobrevivientes_productos, "id_producto_origen_sobreviviente"
    )

    facturas_finales = reasignar_facturas(facturas_limpias, mapa_clientes)
    detalles_finales = reasignar_detalles(detalles_limpios, mapa_productos)

    # 5. Validaciones de formato (sobre datos crudos) + inconsistencias
    #    de negocio (sobre datos ya limpios/fusionados)
    errores = generar_lista_errores(
        clientes_crudos=clientes_crudos,
        clientes_limpios=sobrevivientes_clientes,
        facturas_limpias=facturas_finales,
        detalles_limpios=detalles_finales,
    )

    return {
        "clientes": sobrevivientes_clientes,
        "productos": sobrevivientes_productos,
        "facturas": facturas_finales,
        "detalles": detalles_finales,
        "errores": errores,
    }
