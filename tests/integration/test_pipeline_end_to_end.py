# test_pipeline_end_to_end.py
"""Prueba de extremo a extremo de la etapa de Transform (Integrante 3):
toma el fixture de datos crudos (con duplicados, espacios, correos y
telefonos invalidos, fechas inconsistentes) y verifica que
`ejecutar_transformacion` deje todo limpio, deduplicado y con la lista
de errores correspondiente.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from transform import ejecutar_transformacion

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "mock_customers.json"
)


class TestPipelineEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE_PATH, encoding="utf-8") as archivo:
            cls.datos_crudos = json.load(archivo)
        cls.resultado = ejecutar_transformacion(cls.datos_crudos)

    def test_deduplica_clientes_con_mismo_documento(self):
        # El fixture tiene 4 clientes crudos, pero 1 y 2 son duplicados (mismo documento)
        self.assertEqual(len(self.resultado["clientes"]), 3)

    def test_deduplica_productos_con_mismo_codigo(self):
        # El fixture tiene 2 productos con el mismo codigo -> deben fusionarse en 1
        self.assertEqual(len(self.resultado["productos"]), 1)
        producto_fusionado = self.resultado["productos"][0]
        # El nombre viene del registro 1, que si lo tenia (el 2 lo tenia en None)
        self.assertEqual(producto_fusionado["nombre_producto"], "Laptop HP 15")

    def test_nombres_normalizados(self):
        nombres = {c["nombre"] for c in self.resultado["clientes"]}
        self.assertIn("Juan", nombres)
        self.assertNotIn("juan", nombres)

    def test_facturas_reasignadas_al_cliente_sobreviviente(self):
        ids_clientes_finales = {c["id_cliente_origen_sobreviviente"] for c in self.resultado["clientes"]}
        for factura in self.resultado["facturas"]:
            self.assertIn(factura["id_cliente_origen"], ids_clientes_finales)

    def test_detecta_errores_de_formato_y_de_inconsistencia(self):
        errores = self.resultado["errores"]
        motivos = " | ".join(e["motivo"] for e in errores)
        campos = {e["campo"] for e in errores}
        # correo mal formado (cliente 4) y telefono muy corto (cliente 4)
        self.assertIn("correo", campos)
        self.assertIn("telefono", campos)
        # fecha de nacimiento en el futuro (cliente 3)
        self.assertIn("futuro", motivos)
        # factura con total que no cuadra (factura 2) y detalle con total_linea que no cuadra
        self.assertIn("total", campos)
        self.assertIn("total_linea", campos)


if __name__ == "__main__":
    unittest.main()
