# cleansing.py
"""Funciones de limpieza (cleansing) para los datos crudos del origen."""
from __future__ import annotations

import re
from datetime import date, datetime

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_FECHA_FORMATOS = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d")
_ESTADOS_ACTIVOS = {"ACTIVO", "A", "1", "TRUE", "SI"}
_ESTADOS_INACTIVOS = {"INACTIVO", "I", "0", "FALSE", "NO"}


def limpiar_texto(valor):
    if valor is None:
        return None
    texto = " ".join(valor.strip().split())
    return texto or None


def limpiar_documento(valor):
    if valor is None:
        return None
    solo_digitos = re.sub(r"\D", "", valor)
    return solo_digitos or None


def limpiar_telefono(valor):
    if valor is None:
        return None
    solo_digitos = re.sub(r"\D", "", valor)
    return solo_digitos or None


def limpiar_correo(valor):
    if valor is None:
        return None
    correo = valor.strip().lower().replace(" ", "")
    return correo if EMAIL_REGEX.match(correo) else None


def limpiar_estado(valor):
    if valor is None:
        return "ACTIVO"
    normalizado = valor.strip().upper()
    if normalizado in _ESTADOS_ACTIVOS:
        return "ACTIVO"
    if normalizado in _ESTADOS_INACTIVOS:
        return "INACTIVO"
    return "ACTIVO"


def parsear_fecha(valor):
    if valor is None:
        return None
    texto = valor.strip()
    if not texto or texto.lower() in {"sin fecha", "n/a", "null"}:
        return None
    for formato in _FECHA_FORMATOS:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def limpiar_cliente(crudo):
    return {
        "id_cliente_origen": crudo["IdClienteOrigen"],
        "documento": limpiar_documento(crudo.get("Documento")),
        "nombre": limpiar_texto(crudo.get("Nombre")),
        "apellido": limpiar_texto(crudo.get("Apellido")),
        "correo": limpiar_correo(crudo.get("Correo")),
        "telefono": limpiar_telefono(crudo.get("Telefono")),
        "direccion": limpiar_texto(crudo.get("Direccion")),
        "ciudad": limpiar_texto(crudo.get("Ciudad")),
        "fecha_nacimiento": parsear_fecha(crudo.get("FechaNacimientoTexto")),
        "fecha_registro": parsear_fecha(crudo.get("FechaRegistroTexto")),
        "estado": limpiar_estado(crudo.get("EstadoTexto")),
    }


def limpiar_producto(crudo):
    return {
        "id_producto_origen": crudo["IdProductoOrigen"],
        "codigo_producto": limpiar_texto(crudo.get("CodigoProducto")),
        "nombre_producto": limpiar_texto(crudo.get("NombreProducto")),
        "categoria": limpiar_texto(crudo.get("CategoriaTexto")),
        "precio": crudo.get("Precio"),
        "estado": limpiar_estado(crudo.get("EstadoTexto")),
    }


def limpiar_factura(crudo):
    return {
        "id_factura_origen": crudo["IdFacturaOrigen"],
        "numero_factura": limpiar_texto(crudo.get("NumeroFactura")),
        "id_cliente_origen": crudo["IdClienteOrigen"],
        "fecha_emision": parsear_fecha(crudo.get("FechaEmisionTexto")),
        "estado": limpiar_estado(crudo.get("EstadoTexto")),
        "subtotal": crudo.get("Subtotal"),
        "iva": crudo.get("IVA"),
        "total": crudo.get("Total"),
    }


def limpiar_detalle(crudo):
    return {
        "id_detalle_origen": crudo["IdDetalleOrigen"],
        "id_factura_origen": crudo["IdFacturaOrigen"],
        "id_producto_origen": crudo["IdProductoOrigen"],
        "cantidad": crudo.get("Cantidad"),
        "precio_unitario": crudo.get("PrecioUnitario"),
        "descuento": crudo.get("Descuento", 0),
        "total_linea": crudo.get("TotalLinea"),
    }
