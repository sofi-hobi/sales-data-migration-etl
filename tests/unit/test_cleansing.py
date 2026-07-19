# test_cleansing.py
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from transform.cleansing import (
    limpiar_correo,
    limpiar_cliente,
    limpiar_documento,
    limpiar_estado,
    limpiar_telefono,
    limpiar_texto,
    normalizar_nombre,
    parsear_fecha,
)


class TestLimpiarTexto(unittest.TestCase):
    def test_quita_espacios_extra_y_bordes(self):
        self.assertEqual(limpiar_texto("  Av.   Amazonas   N34-120  "), "Av. Amazonas N34-120")

    def test_none_devuelve_none(self):
        self.assertIsNone(limpiar_texto(None))

    def test_cadena_vacia_devuelve_none(self):
        self.assertIsNone(limpiar_texto("   "))


class TestNormalizarNombre(unittest.TestCase):
    def test_capitaliza_y_quita_espacios(self):
        self.assertEqual(normalizar_nombre("  juan   perez  "), "Juan Perez")

    def test_todo_mayusculas(self):
        self.assertEqual(normalizar_nombre("MARIA JOSE"), "Maria Jose")

    def test_respeta_conectores_no_iniciales(self):
        self.assertEqual(normalizar_nombre("maria de los angeles"), "Maria de los Angeles")

    def test_none_devuelve_none(self):
        self.assertIsNone(normalizar_nombre(None))


class TestLimpiarDocumentoYTelefono(unittest.TestCase):
    def test_documento_solo_digitos(self):
        self.assertEqual(limpiar_documento(" 171-234-5678 "), "1712345678")

    def test_telefono_solo_digitos(self):
        self.assertEqual(limpiar_telefono("099-123-4567"), "0991234567")

    def test_none_devuelve_none(self):
        self.assertIsNone(limpiar_documento(None))
        self.assertIsNone(limpiar_telefono(None))


class TestLimpiarCorreo(unittest.TestCase):
    def test_normaliza_a_minusculas_y_quita_espacios(self):
        self.assertEqual(limpiar_correo("JUAN.PEREZ@GMAIL.COM "), "juan.perez@gmail.com")

    def test_formato_invalido_devuelve_none(self):
        self.assertIsNone(limpiar_correo("pedro.ramirezcorreo.com"))

    def test_none_devuelve_none(self):
        self.assertIsNone(limpiar_correo(None))


class TestLimpiarEstado(unittest.TestCase):
    def test_variantes_activo(self):
        for valor in ("activo", "A", "1", "true", "si"):
            self.assertEqual(limpiar_estado(valor), "ACTIVO")

    def test_variantes_inactivo(self):
        for valor in ("inactivo", "I", "0", "false", "no"):
            self.assertEqual(limpiar_estado(valor), "INACTIVO")

    def test_none_por_defecto_activo(self):
        self.assertEqual(limpiar_estado(None), "ACTIVO")


class TestParsearFecha(unittest.TestCase):
    def test_formato_iso(self):
        self.assertEqual(parsear_fecha("1995-04-12"), date(1995, 4, 12))

    def test_formato_dia_mes_anio(self):
        self.assertEqual(parsear_fecha("12/04/1995"), date(1995, 4, 12))

    def test_valores_sin_fecha(self):
        for valor in ("sin fecha", "N/A", "null", None, ""):
            self.assertIsNone(parsear_fecha(valor))

    def test_formato_no_reconocido(self):
        self.assertIsNone(parsear_fecha("12-Abr-1995"))


class TestLimpiarCliente(unittest.TestCase):
    def test_registro_completo(self):
        crudo = {
            "IdClienteOrigen": 1,
            "Documento": " 171-234-5678 ",
            "Nombre": "  juan  ",
            "Apellido": "PEREZ",
            "Correo": "JUAN.PEREZ@GMAIL.COM ",
            "Telefono": "099-123-4567",
            "Direccion": "  Av. Amazonas  ",
            "Ciudad": "quito",
            "FechaNacimientoTexto": "1995-04-12",
            "FechaRegistroTexto": "2024-01-15",
            "EstadoTexto": "ACTIVO",
        }
        limpio = limpiar_cliente(crudo)
        self.assertEqual(limpio["nombre"], "Juan")
        self.assertEqual(limpio["apellido"], "Perez")
        self.assertEqual(limpio["correo"], "juan.perez@gmail.com")
        self.assertEqual(limpio["telefono"], "0991234567")
        self.assertEqual(limpio["fecha_nacimiento"], date(1995, 4, 12))
        self.assertEqual(limpio["estado"], "ACTIVO")


if __name__ == "__main__":
    unittest.main()
