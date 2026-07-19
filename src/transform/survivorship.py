# survivorship.py
"""Reglas de survivorship: elige y fusiona el registro sobreviviente de cada grupo."""
from __future__ import annotations

CAMPOS_CLIENTE = [
    "documento", "nombre", "apellido", "correo", "telefono",
    "direccion", "ciudad", "fecha_nacimiento", "fecha_registro", "estado",
]
CAMPOS_PRODUCTO = ["codigo_producto", "nombre_producto", "categoria", "precio", "estado"]


def _completitud(registro, campos):
    return sum(1 for campo in campos if registro.get(campo) not in (None, ""))


def _fusionar(base, resto, campos):
    fusionado = dict(base)
    for campo in campos:
        if fusionado.get(campo) in (None, ""):
            for candidato in resto:
                if candidato.get(campo) not in (None, ""):
                    fusionado[campo] = candidato[campo]
                    break
    return fusionado


def elegir_sobreviviente_cliente(grupo_ids, clientes_por_id):
    registros = sorted(
        (clientes_por_id[i] for i in grupo_ids),
        key=lambda r: (-_completitud(r, CAMPOS_CLIENTE), r["id_cliente_origen"]),
    )
    sobreviviente, resto = registros[0], registros[1:]
    fusionado = _fusionar(sobreviviente, resto, CAMPOS_CLIENTE)
    fusionado["id_cliente_origen_sobreviviente"] = sobreviviente["id_cliente_origen"]
    fusionado["ids_origen_grupo"] = [r["id_cliente_origen"] for r in registros]
    return fusionado


def elegir_sobreviviente_producto(grupo_ids, productos_por_id):
    registros = sorted(
        (productos_por_id[i] for i in grupo_ids),
        key=lambda r: (-_completitud(r, CAMPOS_PRODUCTO), r["id_producto_origen"]),
    )
    sobreviviente, resto = registros[0], registros[1:]
    fusionado = _fusionar(sobreviviente, resto, CAMPOS_PRODUCTO)
    fusionado["id_producto_origen_sobreviviente"] = sobreviviente["id_producto_origen"]
    fusionado["ids_origen_grupo"] = [r["id_producto_origen"] for r in registros]
    return fusionado
