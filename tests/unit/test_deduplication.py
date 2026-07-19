# test_deduplication.py
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from transform.deduplication import agrupar_duplicados_clientes, agrupar_duplicados_productos


def _cliente(id_origen, documento=None, correo=None):
    return {"id_cliente_origen": id_origen, "documento": documento, "correo": correo}


def _producto(id_origen, codigo=None):
    return {"id_producto_origen": id_origen, "codigo_producto": codigo}


class TestAgruparDuplicadosClientes(unittest.TestCase):
    def test_agrupa_por_documento_igual(self):
        clientes = [
            _cliente(1, documento="1712345678", correo="a@x.com"),
            _cliente(2, documento="1712345678", correo="b@x.com"),
            _cliente(3, documento="0999999999", correo="c@x.com"),
        ]
        grupos = agrupar_duplicados_clientes(clientes)
        grupos_ordenados = sorted(sorted(g) for g in grupos)
        self.assertIn([1, 2], grupos_ordenados)
        self.assertIn([3], grupos_ordenados)

    def test_agrupa_por_correo_igual_aunque_documento_distinto(self):
        clientes = [
            _cliente(1, documento="111", correo="mismo@x.com"),
            _cliente(2, documento="222", correo="mismo@x.com"),
        ]
        grupos = agrupar_duplicados_clientes(clientes)
        self.assertEqual(sorted(grupos[0]), [1, 2])

    def test_transitividad_documento_y_correo_encadenan_grupo(self):
        # 1 y 2 comparten documento; 2 y 3 comparten correo -> deben quedar en el mismo grupo
        clientes = [
            _cliente(1, documento="111", correo="uno@x.com"),
            _cliente(2, documento="111", correo="dos@x.com"),
            _cliente(3, documento="333", correo="dos@x.com"),
        ]
        grupos = agrupar_duplicados_clientes(clientes)
        self.assertEqual(len(grupos), 1)
        self.assertEqual(sorted(grupos[0]), [1, 2, 3])

    def test_sin_documento_ni_correo_no_se_agrupan_entre_si(self):
        clientes = [_cliente(1), _cliente(2)]
        grupos = agrupar_duplicados_clientes(clientes)
        grupos_ordenados = sorted(sorted(g) for g in grupos)
        self.assertEqual(grupos_ordenados, [[1], [2]])


class TestAgruparDuplicadosProductos(unittest.TestCase):
    def test_agrupa_por_codigo_sin_importar_mayusculas_minusculas(self):
        productos = [
            _producto(1, codigo="abc-100"),
            _producto(2, codigo="ABC-100"),
            _producto(3, codigo="XYZ-1"),
        ]
        grupos = agrupar_duplicados_productos(productos)
        grupos_ordenados = sorted(sorted(g) for g in grupos)
        self.assertIn([1, 2], grupos_ordenados)
        self.assertIn([3], grupos_ordenados)


if __name__ == "__main__":
    unittest.main()
