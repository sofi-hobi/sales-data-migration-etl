# fk_reassignment.py
"""Reasignacion de FKs hacia el registro sobreviviente de cada grupo."""
from __future__ import annotations


def construir_mapa_sobrevivientes(sobrevivientes, campo_id_sobreviviente):
    mapa = {}
    for sobreviviente in sobrevivientes:
        id_sobreviviente = sobreviviente[campo_id_sobreviviente]
        for id_origen in sobreviviente["ids_origen_grupo"]:
            mapa[id_origen] = id_sobreviviente
    return mapa


def reasignar_facturas(facturas_limpias, mapa_cliente):
    reasignadas = []
    for factura in facturas_limpias:
        nueva = dict(factura)
        nueva["id_cliente_origen"] = mapa_cliente.get(
            factura["id_cliente_origen"], factura["id_cliente_origen"]
        )
        reasignadas.append(nueva)
    return reasignadas


def reasignar_detalles(detalles_limpios, mapa_producto):
    reasignados = []
    for detalle in detalles_limpios:
        nuevo = dict(detalle)
        nuevo["id_producto_origen"] = mapa_producto.get(
            detalle["id_producto_origen"], detalle["id_producto_origen"]
        )
        reasignados.append(nuevo)
    return reasignados
