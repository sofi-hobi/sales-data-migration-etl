"""Contrato del dataset final usado en Docker (sin necesitar bases de datos)."""
from __future__ import annotations

import json
from pathlib import Path

from src.transform.orchestrator import ejecutar_transformacion

ROOT = Path(__file__).resolve().parents[2]

MAPAS = {
    "clientes": {
        "idClienteOrigen": "IdClienteOrigen", "documento": "Documento",
        "nombre": "Nombre", "apellido": "Apellido", "correo": "Correo",
        "telefono": "Telefono", "direccion": "Direccion", "ciudad": "Ciudad",
        "fechaNacimiento": "FechaNacimientoTexto", "fechaRegistro": "FechaRegistroTexto",
        "estado": "EstadoTexto",
    },
    "productos": {
        "idProductoOrigen": "IdProductoOrigen", "codigo": "CodigoProducto",
        "nombre": "NombreProducto", "categoria": "CategoriaTexto",
        "precio": "Precio", "estado": "EstadoTexto",
    },
    "facturas": {
        "idFacturaOrigen": "IdFacturaOrigen", "numeroFactura": "NumeroFactura",
        "idClienteOrigen": "IdClienteOrigen", "fechaEmision": "FechaEmisionTexto",
        "estado": "EstadoTexto", "subtotal": "Subtotal", "iva": "IVA", "total": "Total",
    },
    "detalles": {
        "idDetalleOrigen": "IdDetalleOrigen", "idFacturaOrigen": "IdFacturaOrigen",
        "idProductoOrigen": "IdProductoOrigen", "cantidad": "Cantidad",
        "precioUnitario": "PrecioUnitario", "descuento": "Descuento",
        "totalLinea": "TotalLinea",
    },
}


def _cargar_crudos():
    payload = json.loads((ROOT / "data/source/datos_origen.json").read_text(encoding="ascii"))
    return {
        tabla: [{MAPAS[tabla][clave]: valor for clave, valor in fila.items()} for fila in filas]
        for tabla, filas in payload.items()
    }


def test_dataset_supera_mil_clientes_y_preserva_historial():
    crudos = _cargar_crudos()
    resultado = ejecutar_transformacion(crudos)

    assert len(crudos["clientes"]) == 1200
    assert len(resultado["clientes"]) == 1098
    assert len(resultado["productos"]) == 55
    assert len(resultado["facturas"]) == len(crudos["facturas"]) == 1206
    assert len(resultado["detalles"]) == len(crudos["detalles"]) == 2412

    total_origen = round(sum(float(f["Total"]) for f in crudos["facturas"]), 2)
    total_destino = round(sum(float(f["total"]) for f in resultado["facturas"]), 2)
    assert total_origen == total_destino == 120011.78

    juan = next(c for c in resultado["clientes"] if 1 in c["ids_origen_grupo"])
    assert juan["ids_origen_grupo"] == [1, 2, 3]
    assert sum(1 for f in resultado["facturas"] if f["id_cliente_origen"] == 1) == 9


def test_no_quedan_referencias_huerfanas_despues_de_transformar():
    resultado = ejecutar_transformacion(_cargar_crudos())
    clientes = {c["id_cliente_origen_sobreviviente"] for c in resultado["clientes"]}
    productos = {p["id_producto_origen_sobreviviente"] for p in resultado["productos"]}
    facturas = {f["id_factura_origen"] for f in resultado["facturas"]}

    assert all(f["id_cliente_origen"] in clientes for f in resultado["facturas"])
    assert all(d["id_factura_origen"] in facturas for d in resultado["detalles"])
    assert all(d["id_producto_origen"] in productos for d in resultado["detalles"])
