# test_fk_reassignment.py
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from transform.fk_reassignment import (
    construir_mapa_sobrevivientes,
    reasignar_detalles,
    reasignar_facturas,
)


class TestConstruirMapaSobrevivientes(unittest.TestCase):
    def test_mapea_cada_id_origen_al_sobreviviente(self):
        sobrevivientes = [
            {"id_cliente_origen_sobreviviente": 2, "ids_origen_grupo": [1, 2]},
            {"id_cliente_origen_sobreviviente": 3, "ids_origen_grupo": [3]},
        ]
        mapa = construir_mapa_sobrevivientes(sobrevivientes, "id_cliente_origen_sobreviviente")
        self.assertEqual(mapa, {1: 2, 2: 2, 3: 3})


class TestReasignarFacturas(unittest.TestCase):
    def test_reasigna_cliente_al_sobreviviente(self):
        facturas = [
            {"id_factura_origen": 10, "id_cliente_origen": 1},
            {"id_factura_origen": 11, "id_cliente_origen": 5},
        ]
        mapa_cliente = {1: 2}
        resultado = reasignar_facturas(facturas, mapa_cliente)
        self.assertEqual(resultado[0]["id_cliente_origen"], 2)
        # Si no esta en el mapa, se deja igual (no era parte de ningun grupo de duplicados)
        self.assertEqual(resultado[1]["id_cliente_origen"], 5)

    def test_no_modifica_la_lista_original(self):
        facturas = [{"id_factura_origen": 10, "id_cliente_origen": 1}]
        reasignar_facturas(facturas, {1: 2})
        self.assertEqual(facturas[0]["id_cliente_origen"], 1)


class TestReasignarDetalles(unittest.TestCase):
    def test_reasigna_producto_al_sobreviviente(self):
        detalles = [
            {"id_detalle_origen": 100, "id_producto_origen": 1},
            {"id_detalle_origen": 101, "id_producto_origen": 9},
        ]
        mapa_producto = {1: 2}
        resultado = reasignar_detalles(detalles, mapa_producto)
        self.assertEqual(resultado[0]["id_producto_origen"], 2)
        self.assertEqual(resultado[1]["id_producto_origen"], 9)


if __name__ == "__main__":
    unittest.main()
