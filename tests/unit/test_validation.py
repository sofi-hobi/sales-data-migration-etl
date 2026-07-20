# test_validation.py
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from transform.validation import (
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


class TestValidarCorreo(unittest.TestCase):
    def test_correo_valido_no_genera_error(self):
        self.assertIsNone(validar_correo(1, "juan@x.com"))

    def test_correo_invalido_genera_error(self):
        error = validar_correo(1, "juanx.com")
        self.assertIsNotNone(error)
        self.assertEqual(error["campo"], "correo")

    def test_correo_vacio_genera_error(self):
        error = validar_correo(1, "")
        self.assertIsNotNone(error)
        self.assertIn("vacio", error["motivo"])


class TestValidarTelefono(unittest.TestCase):
    def test_telefono_valido_no_genera_error(self):
        self.assertIsNone(validar_telefono(1, "0991234567"))

    def test_telefono_muy_corto_genera_error(self):
        error = validar_telefono(1, "093-12")
        self.assertIsNotNone(error)
        self.assertEqual(error["campo"], "telefono")


class TestValidarDocumento(unittest.TestCase):
    def test_documento_valido_no_genera_error(self):
        self.assertIsNone(validar_documento(1, "1712345678"))

    def test_documento_nulo_genera_error(self):
        self.assertIsNotNone(validar_documento(1, None))


class TestValidarCodigoProducto(unittest.TestCase):
    def test_codigo_valido_no_genera_error(self):
        self.assertIsNone(validar_codigo_producto(1, "SKU-001"))

    def test_codigo_nulo_genera_error(self):
        error = validar_codigo_producto(1, None)
        self.assertIsNotNone(error)
        self.assertEqual(error["entidad"], "producto")
        self.assertEqual(error["campo"], "codigo_producto")

    def test_codigo_vacio_genera_error(self):
        error = validar_codigo_producto(1, "   ")
        self.assertIsNotNone(error)
        self.assertIn("vacio", error["motivo"])


class TestValidarPrecioProducto(unittest.TestCase):
    def test_precio_valido_no_genera_error(self):
        self.assertIsNone(validar_precio_producto(1, 25.5))

    def test_precio_nulo_genera_error(self):
        error = validar_precio_producto(1, None)
        self.assertIsNotNone(error)
        self.assertIn("vacio", error["motivo"])

    def test_precio_negativo_genera_error(self):
        error = validar_precio_producto(1, -10)
        self.assertIsNotNone(error)
        self.assertIn("negativo", error["motivo"])

    def test_precio_cero_genera_error(self):
        error = validar_precio_producto(1, 0)
        self.assertIsNotNone(error)
        self.assertIn("cero", error["motivo"])

    def test_precio_no_numerico_genera_error(self):
        error = validar_precio_producto(1, "no-es-numero")
        self.assertIsNotNone(error)
        self.assertIn("no es un numero", error["motivo"])


class TestDetectarInconsistenciasCliente(unittest.TestCase):
    def test_fecha_nacimiento_futura(self):
        cliente = {
            "id_cliente_origen": 1,
            "fecha_nacimiento": date(2999, 1, 1),
            "fecha_registro": None,
        }
        errores = detectar_inconsistencias_cliente(cliente, hoy=date(2026, 7, 18))
        motivos = [e["motivo"] for e in errores]
        self.assertTrue(any("futuro" in m for m in motivos))

    def test_registro_anterior_a_nacimiento(self):
        cliente = {
            "id_cliente_origen": 1,
            "fecha_nacimiento": date(2000, 1, 1),
            "fecha_registro": date(1999, 1, 1),
        }
        errores = detectar_inconsistencias_cliente(cliente, hoy=date(2026, 7, 18))
        motivos = [e["motivo"] for e in errores]
        self.assertTrue(any("anterior a la fecha de nacimiento" in m for m in motivos))

    def test_registro_consistente_no_genera_errores(self):
        cliente = {
            "id_cliente_origen": 1,
            "fecha_nacimiento": date(1995, 4, 12),
            "fecha_registro": date(2024, 1, 15),
        }
        errores = detectar_inconsistencias_cliente(cliente, hoy=date(2026, 7, 18))
        self.assertEqual(errores, [])


class TestDetectarInconsistenciasFactura(unittest.TestCase):
    def test_total_no_coincide_con_subtotal_mas_iva(self):
        factura = {"id_factura_origen": 1, "subtotal": 100.0, "iva": 12.0, "total": 999.0}
        errores = detectar_inconsistencias_factura(factura)
        self.assertEqual(len(errores), 1)
        self.assertEqual(errores[0]["campo"], "total")

    def test_total_correcto_no_genera_error(self):
        factura = {"id_factura_origen": 1, "subtotal": 100.0, "iva": 12.0, "total": 112.0}
        self.assertEqual(detectar_inconsistencias_factura(factura), [])


class TestDetectarInconsistenciasDetalle(unittest.TestCase):
    def test_total_linea_no_coincide(self):
        detalle = {
            "id_detalle_origen": 1, "cantidad": 3, "precio_unitario": 50.0,
            "descuento": 0, "total_linea": 500.0,
        }
        errores = detectar_inconsistencias_detalle(detalle)
        self.assertEqual(len(errores), 1)
        self.assertEqual(errores[0]["campo"], "total_linea")

    def test_total_linea_correcto_no_genera_error(self):
        detalle = {
            "id_detalle_origen": 1, "cantidad": 2, "precio_unitario": 50.0,
            "descuento": 0, "total_linea": 100.0,
        }
        self.assertEqual(detectar_inconsistencias_detalle(detalle), [])


class TestGenerarListaErrores(unittest.TestCase):
    def test_combina_validaciones_e_inconsistencias(self):
        clientes_crudos = [
            {"IdClienteOrigen": 1, "Correo": "malformato.com", "Telefono": "0991234567", "Documento": "1712345678"},
        ]
        clientes_limpios = [
            {"id_cliente_origen": 1, "fecha_nacimiento": date(2999, 1, 1), "fecha_registro": None},
        ]
        errores = generar_lista_errores(clientes_crudos, clientes_limpios)
        campos = {e["campo"] for e in errores}
        self.assertIn("correo", campos)
        self.assertIn("fecha_nacimiento", campos)

    def test_incluye_validaciones_de_producto(self):
        clientes_crudos = [
            {"IdClienteOrigen": 1, "Correo": "juan@x.com", "Telefono": "0991234567", "Documento": "1712345678"},
        ]
        clientes_limpios = [{"id_cliente_origen": 1, "fecha_nacimiento": None, "fecha_registro": None}]
        productos_crudos = [
            {"IdProductoOrigen": 1, "CodigoProducto": "", "Precio": -5},
        ]
        errores = generar_lista_errores(
            clientes_crudos, clientes_limpios, productos_crudos=productos_crudos,
        )
        errores_producto = [e for e in errores if e["entidad"] == "producto"]
        campos = {e["campo"] for e in errores_producto}
        self.assertIn("codigo_producto", campos)
        self.assertIn("precio", campos)


if __name__ == "__main__":
    unittest.main()
