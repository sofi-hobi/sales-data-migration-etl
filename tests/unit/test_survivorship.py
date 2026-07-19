# test_survivorship.py
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from transform.survivorship import elegir_sobreviviente_cliente, elegir_sobreviviente_producto


class TestElegirSobrevivienteCliente(unittest.TestCase):
    def test_elige_el_mas_completo_y_rellena_huecos_con_el_resto(self):
        clientes_por_id = {
            1: {
                "id_cliente_origen": 1, "documento": "111", "nombre": "Juan",
                "apellido": "Perez", "correo": None, "telefono": "0991234567",
                "direccion": None, "ciudad": "Quito", "fecha_nacimiento": None,
                "fecha_registro": None, "estado": "ACTIVO",
            },
            2: {
                "id_cliente_origen": 2, "documento": "111", "nombre": "Juan",
                "apellido": "Perez", "correo": "juan@x.com", "telefono": None,
                "direccion": "Av. Amazonas", "ciudad": None, "fecha_nacimiento": None,
                "fecha_registro": "2024-01-15", "estado": "ACTIVO",
            },
        }
        resultado = elegir_sobreviviente_cliente([1, 2], clientes_por_id)
        # El 2 tiene mas campos completos (correo, direccion y fecha_registro) -> deberia ganar
        self.assertEqual(resultado["id_cliente_origen_sobreviviente"], 2)
        # Pero el telefono, que le faltaba al 2, se rellena desde el 1
        self.assertEqual(resultado["telefono"], "0991234567")
        self.assertEqual(resultado["ciudad"], "Quito")
        self.assertEqual(sorted(resultado["ids_origen_grupo"]), [1, 2])

    def test_grupo_de_un_solo_elemento_se_devuelve_igual(self):
        clientes_por_id = {
            1: {
                "id_cliente_origen": 1, "documento": "111", "nombre": "Juan",
                "apellido": "Perez", "correo": "juan@x.com", "telefono": "0991234567",
                "direccion": "Av. Amazonas", "ciudad": "Quito", "fecha_nacimiento": None,
                "fecha_registro": None, "estado": "ACTIVO",
            }
        }
        resultado = elegir_sobreviviente_cliente([1], clientes_por_id)
        self.assertEqual(resultado["id_cliente_origen_sobreviviente"], 1)
        self.assertEqual(resultado["ids_origen_grupo"], [1])


class TestElegirSobrevivienteProducto(unittest.TestCase):
    def test_elige_el_mas_completo(self):
        productos_por_id = {
            1: {
                "id_producto_origen": 1, "codigo_producto": "ABC-100",
                "nombre_producto": None, "categoria": None, "precio": 750.5,
                "estado": "ACTIVO",
            },
            2: {
                "id_producto_origen": 2, "codigo_producto": "ABC-100",
                "nombre_producto": "Laptop HP 15", "categoria": "Tecnologia",
                "precio": 750.5, "estado": "ACTIVO",
            },
        }
        resultado = elegir_sobreviviente_producto([1, 2], productos_por_id)
        self.assertEqual(resultado["id_producto_origen_sobreviviente"], 2)
        self.assertEqual(resultado["nombre_producto"], "Laptop HP 15")


if __name__ == "__main__":
    unittest.main()
