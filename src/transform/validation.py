# validation.py
"""Validacion de campos y deteccion de inconsistencias de negocio.

Este modulo completa lo que cleansing.py no hace: en vez de solo limpiar/
normalizar valores y descartar en silencio lo invalido (devolviendo None),
aqui se registra CADA problema encontrado como un error estructurado, y se
detectan inconsistencias que cruzan varios campos o varias tablas.
"""
from __future__ import annotations

from datetime import date, timedelta

from .cleansing import EMAIL_REGEX

TELEFONO_MIN_DIGITOS = 7
TELEFONO_MAX_DIGITOS = 15
DOCUMENTO_MIN_DIGITOS = 5
EDAD_MAXIMA_ANIOS = 120
TOLERANCIA_MONTOS = 0.01


def _error(entidad, id_origen, campo, valor_original, motivo):
    """Estructura estandar de un error para poder exportarlo/auditarlo despues."""
    return {
        "entidad": entidad,
        "id_origen": id_origen,
        "campo": campo,
        "valor_original": valor_original,
        "motivo": motivo,
    }


# ---------------------------------------------------------------------------
# Validaciones de formato sobre el valor CRUDO (antes de limpiar), para poder
# reportar el motivo exacto por el que un dato fue rechazado.
# ---------------------------------------------------------------------------

def validar_correo(id_origen, correo_original):
    if correo_original is None or not str(correo_original).strip():
        return _error("cliente", id_origen, "correo", correo_original, "correo vacio o nulo")
    normalizado = str(correo_original).strip().lower().replace(" ", "")
    if not EMAIL_REGEX.match(normalizado):
        return _error("cliente", id_origen, "correo", correo_original, "formato de correo invalido")
    return None


def validar_telefono(id_origen, telefono_original):
    if telefono_original is None or not str(telefono_original).strip():
        return _error("cliente", id_origen, "telefono", telefono_original, "telefono vacio o nulo")
    solo_digitos = "".join(ch for ch in str(telefono_original) if ch.isdigit())
    if not (TELEFONO_MIN_DIGITOS <= len(solo_digitos) <= TELEFONO_MAX_DIGITOS):
        return _error(
            "cliente", id_origen, "telefono", telefono_original,
            f"cantidad de digitos fuera de rango ({len(solo_digitos)})",
        )
    return None


def validar_documento(id_origen, documento_original):
    if documento_original is None or not str(documento_original).strip():
        return _error("cliente", id_origen, "documento", documento_original, "documento vacio o nulo")
    solo_digitos = "".join(ch for ch in str(documento_original) if ch.isdigit())
    if len(solo_digitos) < DOCUMENTO_MIN_DIGITOS:
        return _error(
            "cliente", id_origen, "documento", documento_original,
            f"documento con muy pocos digitos ({len(solo_digitos)})",
        )
    return None


def validar_codigo_producto(id_origen, codigo_original):
    if codigo_original is None or not str(codigo_original).strip():
        return _error("producto", id_origen, "codigo_producto", codigo_original, "codigo de producto vacio o nulo")
    return None


def validar_precio_producto(id_origen, precio_original):
    if precio_original is None or not str(precio_original).strip():
        return _error("producto", id_origen, "precio", precio_original, "precio vacio o nulo")
    try:
        precio = float(precio_original)
    except (TypeError, ValueError):
        return _error("producto", id_origen, "precio", precio_original, "precio no es un numero valido")
    if precio < 0:
        return _error("producto", id_origen, "precio", precio_original, "precio negativo")
    if precio == 0:
        return _error("producto", id_origen, "precio", precio_original, "precio en cero")
    return None


# ---------------------------------------------------------------------------
# Deteccion de inconsistencias de negocio sobre el registro ya limpio
# (cruces entre campos, no solo formato).
# ---------------------------------------------------------------------------

def detectar_inconsistencias_cliente(cliente_limpio, hoy=None):
    hoy = hoy or date.today()
    errores = []
    id_origen = cliente_limpio["id_cliente_origen"]
    fecha_nac = cliente_limpio.get("fecha_nacimiento")
    fecha_reg = cliente_limpio.get("fecha_registro")

    if fecha_nac and fecha_nac > hoy:
        errores.append(_error(
            "cliente", id_origen, "fecha_nacimiento", fecha_nac,
            "fecha de nacimiento en el futuro",
        ))

    if fecha_nac and fecha_nac < hoy - timedelta(days=365 * EDAD_MAXIMA_ANIOS):
        errores.append(_error(
            "cliente", id_origen, "fecha_nacimiento", fecha_nac,
            f"edad implicita mayor a {EDAD_MAXIMA_ANIOS} anios",
        ))

    if fecha_reg and fecha_reg > hoy:
        errores.append(_error(
            "cliente", id_origen, "fecha_registro", fecha_reg,
            "fecha de registro en el futuro",
        ))

    if fecha_nac and fecha_reg and fecha_reg < fecha_nac:
        errores.append(_error(
            "cliente", id_origen, "fecha_registro", fecha_reg,
            "fecha de registro anterior a la fecha de nacimiento",
        ))

    return errores


def detectar_inconsistencias_factura(factura_limpia):
    errores = []
    id_origen = factura_limpia["id_factura_origen"]
    subtotal = factura_limpia.get("subtotal")
    iva = factura_limpia.get("iva")
    total = factura_limpia.get("total")

    if subtotal is not None and iva is not None and total is not None:
        calculado = round(float(subtotal) + float(iva), 2)
        if abs(calculado - round(float(total), 2)) > TOLERANCIA_MONTOS:
            errores.append(_error(
                "factura", id_origen, "total", total,
                f"total ({total}) no coincide con subtotal + iva ({calculado})",
            ))

    if subtotal is not None and float(subtotal) < 0:
        errores.append(_error("factura", id_origen, "subtotal", subtotal, "subtotal negativo"))

    if iva is not None and float(iva) < 0:
        errores.append(_error("factura", id_origen, "iva", iva, "iva negativo"))

    return errores


def detectar_inconsistencias_detalle(detalle_limpio):
    errores = []
    id_origen = detalle_limpio["id_detalle_origen"]
    cantidad = detalle_limpio.get("cantidad")
    precio_unitario = detalle_limpio.get("precio_unitario")
    descuento = detalle_limpio.get("descuento") or 0
    total_linea = detalle_limpio.get("total_linea")

    if cantidad is not None and cantidad <= 0:
        errores.append(_error("detalle", id_origen, "cantidad", cantidad, "cantidad debe ser mayor a cero"))

    if precio_unitario is not None and float(precio_unitario) < 0:
        errores.append(_error("detalle", id_origen, "precio_unitario", precio_unitario, "precio unitario negativo"))

    if cantidad is not None and precio_unitario is not None and total_linea is not None:
        calculado = round(float(cantidad) * float(precio_unitario) - float(descuento), 2)
        if abs(calculado - round(float(total_linea), 2)) > TOLERANCIA_MONTOS:
            errores.append(_error(
                "detalle", id_origen, "total_linea", total_linea,
                f"total_linea ({total_linea}) no coincide con cantidad*precio-descuento ({calculado})",
            ))

    return errores


# ---------------------------------------------------------------------------
# Orquestador: recorre todo lo transformado y arma la lista de errores final.
# Esto es lo que llamaria pipeline.py despues de limpiar/deduplicar.
# ---------------------------------------------------------------------------

def generar_lista_errores(
    clientes_crudos,
    clientes_limpios,
    facturas_limpias=None,
    detalles_limpios=None,
    productos_crudos=None,
):
    errores = []

    for crudo in clientes_crudos:
        id_origen = crudo["IdClienteOrigen"]
        for validador, campo_crudo in (
            (validar_correo, "Correo"),
            (validar_telefono, "Telefono"),
            (validar_documento, "Documento"),
        ):
            error = validador(id_origen, crudo.get(campo_crudo))
            if error:
                errores.append(error)

    for crudo in productos_crudos or []:
        id_origen = crudo["IdProductoOrigen"]
        for validador, campo_crudo in (
            (validar_codigo_producto, "CodigoProducto"),
            (validar_precio_producto, "Precio"),
        ):
            error = validador(id_origen, crudo.get(campo_crudo))
            if error:
                errores.append(error)

    for cliente_limpio in clientes_limpios:
        errores.extend(detectar_inconsistencias_cliente(cliente_limpio))

    for factura in facturas_limpias or []:
        errores.extend(detectar_inconsistencias_factura(factura))

    for detalle in detalles_limpios or []:
        errores.extend(detectar_inconsistencias_detalle(detalle))

    return errores
