"""Genera un conjunto reproducible de datos sucios para SmartCleanOrigen.

Resultado esperado:
- 1,200 clientes de origen.
- 1,098 clientes maestros después de consolidar 101 grupos duplicados.
- 60 productos de origen (55 productos maestros).
- 1,206 facturas.
- 2,412 detalles.

El archivo se escribe con escapes Unicode para que SQL Server Linux pueda
leerlo mediante OPENROWSET(..., SINGLE_CLOB) sin usar CODEPAGE.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent / "source" / "datos_origen.json"

NOMBRES = [
    "María", "Carlos", "Ana", "Luis", "Sofía", "Jorge", "Valentina", "Diego",
    "Camila", "Andrés", "Daniela", "Mateo", "Fernanda", "Sebastián", "Paula",
]
APELLIDOS = [
    "García", "Rodríguez", "López", "Martínez", "Sánchez", "Pérez", "Gómez",
    "Torres", "Vásquez", "Mendoza", "Castro", "Romero", "Cevallos", "Espinosa",
]
CIUDADES = ["Quito", "Guayaquil", "Cuenca", "Ambato", "Loja", "Manta", "Riobamba"]
CATEGORIAS = ["Limpieza general", "Desinfección", "Accesorios", "Hogar", "Industrial"]


def dinero(valor: Decimal) -> float:
    return float(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def persona_canonica(id_cliente: int) -> dict:
    nombre = NOMBRES[id_cliente % len(NOMBRES)]
    apellido = APELLIDOS[(id_cliente * 3) % len(APELLIDOS)]
    ciudad = CIUDADES[id_cliente % len(CIUDADES)]
    documento = f"17{id_cliente:08d}"[-10:]
    correo_base = f"cliente{id_cliente}.{apellido.lower()}@correo.ec"
    telefono = f"09{id_cliente:08d}"[-10:]

    nacimiento = date(1960, 1, 1) + timedelta(days=(id_cliente * 37) % 15000)
    registro = date(2022, 1, 1) + timedelta(days=(id_cliente * 11) % 1200)

    # Errores intencionales que siguen siendo procesables por el ETL.
    correo = correo_base
    if id_cliente % 37 == 0:
        correo = correo_base.replace("@", "")  # inválido -> se limpia a NULL
    elif id_cliente % 17 == 0:
        correo = f"  {correo_base.upper()}  "

    telefono_sucio = telefono
    if id_cliente % 29 == 0:
        telefono_sucio = telefono[:6]  # inválido, pero auditable
    elif id_cliente % 13 == 0:
        telefono_sucio = f"({telefono[:3]}) {telefono[3:6]}-{telefono[6:]}"

    documento_sucio = documento
    if id_cliente % 200 == 0:
        documento_sucio = None  # demuestra clientes sin documento sin perderlos
    elif id_cliente % 19 == 0:
        documento_sucio = f" {documento[:3]}-{documento[3:6]}-{documento[6:]} "

    fecha_nacimiento = nacimiento.isoformat()
    if id_cliente % 41 == 0:
        fecha_nacimiento = "31/02/1990"
    elif id_cliente % 9 == 0:
        fecha_nacimiento = nacimiento.strftime("%d/%m/%Y")

    fecha_registro = registro.isoformat()
    if id_cliente % 47 == 0:
        fecha_registro = "sin fecha"

    nombre_sucio = nombre
    apellido_sucio = apellido
    if id_cliente % 10 == 0:
        nombre_sucio = f"  {nombre.upper()}  "
        apellido_sucio = f" {apellido.upper()} "

    return {
        "idClienteOrigen": id_cliente,
        "documento": documento_sucio,
        "nombre": nombre_sucio,
        "apellido": apellido_sucio,
        "correo": correo,
        "telefono": telefono_sucio,
        "direccion": f" Calle {id_cliente} y Avenida Principal ",
        "ciudad": f" {ciudad.upper()} " if id_cliente % 12 == 0 else ciudad,
        "fechaNacimiento": fecha_nacimiento,
        "fechaRegistro": fecha_registro,
        "estado": "activo" if id_cliente % 7 else "A",
    }


def generar_clientes() -> list[dict]:
    clientes = []

    # Grupo emblemático para la exposición: tres variantes de Juan Pérez.
    clientes.extend([
        {
            "idClienteOrigen": 1, "documento": " 1712345678 ", "nombre": " Juan ",
            "apellido": "Pérez", "correo": "JUAN.PEREZ@GMAIL.COM ",
            "telefono": "099-123-4567", "direccion": " Av. Amazonas N34-120 ",
            "ciudad": "Quito", "fechaNacimiento": "1995-04-12",
            "fechaRegistro": "2024-01-15", "estado": "ACTIVO",
        },
        {
            "idClienteOrigen": 2, "documento": "1712345678", "nombre": "JUAN",
            "apellido": "PEREZ IDROVO", "correo": "juan.perez@gmail.com",
            "telefono": "(099) 123 4567", "direccion": "Av Amazonas N34 120",
            "ciudad": " QUITO ", "fechaNacimiento": "12/04/1995",
            "fechaRegistro": "15/01/2024", "estado": "activo",
        },
        {
            "idClienteOrigen": 3, "documento": None, "nombre": "Jn",
            "apellido": "Perez", "correo": "juan.perez @gmail.com",
            "telefono": "0991234567", "direccion": None, "ciudad": "quito",
            "fechaNacimiento": "1995/04/12", "fechaRegistro": "sin fecha", "estado": "A",
        },
    ])

    # 1,097 clientes canónicos adicionales.
    for id_cliente in range(4, 1101):
        clientes.append(persona_canonica(id_cliente))

    # 100 duplicados intencionales de los clientes 4..103.
    for offset, id_base in enumerate(range(4, 104), start=1101):
        base = persona_canonica(id_base)
        documento = "".join(ch for ch in str(base["documento"] or "") if ch.isdigit()) or None
        correo = f"cliente{id_base}.{APELLIDOS[(id_base * 3) % len(APELLIDOS)].lower()}@correo.ec"
        telefono = f"09{id_base:08d}"[-10:]
        clientes.append({
            "idClienteOrigen": offset,
            "documento": f" {documento[:3]}-{documento[3:6]}-{documento[6:]} " if documento else None,
            "nombre": f" {str(base['nombre']).strip().upper()} ",
            "apellido": f" {str(base['apellido']).strip().upper()} ",
            "correo": f" {correo.upper()} ",
            "telefono": f"{telefono[:3]} {telefono[3:6]} {telefono[6:]}",
            "direccion": str(base["direccion"]).strip(),
            "ciudad": str(base["ciudad"]).strip().lower(),
            "fechaNacimiento": base["fechaNacimiento"],
            "fechaRegistro": base["fechaRegistro"],
            "estado": "1",
        })

    assert len(clientes) == 1200
    return clientes


def generar_productos() -> list[dict]:
    productos = []
    for i in range(1, 56):
        precio = Decimal("1.25") + Decimal(i) * Decimal("0.73")
        productos.append({
            "idProductoOrigen": i,
            "codigo": f"SC-{i:03d}",
            "nombre": f"Producto de limpieza {i}",
            "categoria": CATEGORIAS[i % len(CATEGORIAS)],
            "precio": dinero(precio),
            "estado": "ACTIVO" if i % 11 else "inactivo",
        })
    # Cinco duplicados de producto con código en otro formato/caso.
    for i in range(56, 61):
        base = i - 55
        productos.append({
            "idProductoOrigen": i,
            "codigo": f" sc-{base:03d} ",
            "nombre": f"PRODUCTO DE LIMPIEZA {base}",
            "categoria": CATEGORIAS[base % len(CATEGORIAS)],
            "precio": productos[base - 1]["precio"],
            "estado": "A",
        })
    assert len(productos) == 60
    return productos


def generar_ventas(clientes: list[dict], productos: list[dict]) -> tuple[list[dict], list[dict]]:
    precio_por_id = {p["idProductoOrigen"]: Decimal(str(p["precio"])) for p in productos}
    facturas: list[dict] = []
    detalles: list[dict] = []
    id_factura = 1001
    id_detalle = 5001

    def agregar_factura(id_cliente: int, indice: int) -> None:
        nonlocal id_factura, id_detalle
        p1 = ((id_cliente + indice * 3) % 55) + 1
        p2 = ((id_cliente + indice * 7 + 11) % 55) + 1
        if p2 == p1:
            p2 = (p2 % 55) + 1
        lineas = []
        for pos, producto_id in enumerate((p1, p2), start=1):
            cantidad = ((id_cliente + indice + pos) % 3) + 1
            precio = precio_por_id[producto_id]
            descuento = Decimal("0.00") if (id_factura + pos) % 17 else Decimal("0.50")
            total_linea = Decimal(cantidad) * precio - descuento
            lineas.append((producto_id, cantidad, precio, descuento, total_linea))

        subtotal = sum((linea[4] for linea in lineas), Decimal("0.00"))
        iva = (subtotal * Decimal("0.15")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total = subtotal + iva
        fecha = date(2025, 1, 1) + timedelta(days=(id_factura * 7) % 540)
        fecha_texto = fecha.isoformat()
        if id_factura % 211 == 0:
            fecha_texto = "2025-15-40"  # inconsistencia intencional

        facturas.append({
            "idFacturaOrigen": id_factura,
            "numeroFactura": f"FAC-{id_factura:07d}",
            "idClienteOrigen": id_cliente,
            "fechaEmision": fecha_texto,
            "estado": ("PAGADA", "PENDIENTE", "ANULADA")[id_factura % 3],
            "subtotal": dinero(subtotal),
            "iva": dinero(iva),
            "total": dinero(total),
        })
        for producto_id, cantidad, precio, descuento, total_linea in lineas:
            detalles.append({
                "idDetalleOrigen": id_detalle,
                "idFacturaOrigen": id_factura,
                "idProductoOrigen": producto_id,
                "cantidad": cantidad,
                "precioUnitario": dinero(precio),
                "descuento": dinero(descuento),
                "totalLinea": dinero(total_linea),
            })
            id_detalle += 1
        id_factura += 1

    # Nueve facturas repartidas entre las tres variantes de Juan Pérez.
    for id_cliente in (1, 2, 3):
        for indice in range(3):
            agregar_factura(id_cliente, indice)

    # Una factura para cada uno de los demás clientes de origen.
    for cliente in clientes:
        id_cliente = cliente["idClienteOrigen"]
        if id_cliente > 3:
            agregar_factura(id_cliente, 0)

    assert len(facturas) == 1206
    assert len(detalles) == 2412
    return facturas, detalles


def main() -> None:
    clientes = generar_clientes()
    productos = generar_productos()
    facturas, detalles = generar_ventas(clientes, productos)
    payload = {
        "clientes": clientes,
        "productos": productos,
        "facturas": facturas,
        "detalles": detalles,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=False),
        encoding="ascii",
    )
    total = sum(Decimal(str(f["total"])) for f in facturas)
    print(f"Archivo generado: {OUTPUT}")
    print(f"Clientes: {len(clientes)}")
    print(f"Productos: {len(productos)}")
    print(f"Facturas: {len(facturas)}")
    print(f"Detalles: {len(detalles)}")
    print(f"Total facturado: {total.quantize(Decimal('0.01'))}")


if __name__ == "__main__":
    main()
