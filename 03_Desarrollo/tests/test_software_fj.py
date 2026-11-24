"""
Pruebas unitarias del sistema Software FJ (módulo estándar ``unittest``).

Ejecutar desde ``03_Desarrollo``::

    python -m unittest discover -s tests -v

Los logs de las pruebas se escriben en un archivo temporal para no mezclar
su contenido con el log de la simulación.
"""

import io
import logging
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from software_fj import (
    AlquilerEquipo, Asesoria, CalculoInconsistenteError, Cliente, EntidadBase, EntidadNoEncontradaError,
    EstadoReserva, GestorSistema, OperacionNoPermitidaError, ParametroFaltanteError, Reserva,
    ReservaInvalidaError, ReservaSala, Servicio, ServicioNoDisponibleError, SoftwareFJError, ValidacionError,
    configurar_registro,
)
from software_fj.validaciones import validar_numero

# Directorio temporal compartido por todas las pruebas para el archivo de log.
_TMP = tempfile.TemporaryDirectory()
RUTA_LOG = Path(_TMP.name) / "pruebas.log"


def setUpModule():
    configurar_registro(RUTA_LOG)


def tearDownModule():
    # Se cierran los manejadores antes de borrar la carpeta temporal (necesario en Windows).
    for manejador in list(logging.getLogger("software_fj").handlers):
        manejador.close()
        logging.getLogger("software_fj").removeHandler(manejador)
    _TMP.cleanup()


def nuevo_cliente(documento="1032456789"):
    return Cliente("Ana Gómez", documento, "ana@correo.com", "3104567890")


class PruebasAbstraccion(unittest.TestCase):
    def test_clases_abstractas_no_instanciables(self):
        with self.assertRaises(TypeError):
            EntidadBase()
        with self.assertRaises(TypeError):
            Servicio("Genérico", 1000)

    def test_herencia(self):
        self.assertTrue(issubclass(Cliente, EntidadBase))
        for clase in (ReservaSala, AlquilerEquipo, Asesoria):
            self.assertTrue(issubclass(clase, Servicio))
            self.assertTrue(issubclass(clase, EntidadBase))
        self.assertTrue(issubclass(Reserva, EntidadBase))

    def test_jerarquia_de_excepciones(self):
        self.assertTrue(issubclass(ParametroFaltanteError, ValidacionError))
        for exc in (ValidacionError, EntidadNoEncontradaError, OperacionNoPermitidaError,
                    ServicioNoDisponibleError, ReservaInvalidaError, CalculoInconsistenteError):
            self.assertTrue(issubclass(exc, SoftwareFJError))


class PruebasCliente(unittest.TestCase):
    def test_cliente_valido_y_normalizado(self):
        c = Cliente("  Ana   María Gómez ", "1032456789", "ANA@Correo.com", "310-456 7890")
        self.assertEqual(c.nombre, "Ana María Gómez")
        self.assertEqual(c.correo, "ana@correo.com")
        self.assertEqual(c.telefono, "3104567890")
        self.assertTrue(c.id.startswith("CLI-"))

    def test_documento_enmascarado_en_descripcion(self):
        c = nuevo_cliente()
        self.assertEqual(c.documento_enmascarado, "******6789")
        self.assertNotIn("1032456789", c.describir())

    def test_datos_invalidos(self):
        casos = [
            ("Ana123", "1032456789", "ana@correo.com", "3104567890"),   # nombre con dígitos
            ("Ana Gómez", "12AB56", "ana@correo.com", "3104567890"),     # documento no numérico
            ("Ana Gómez", "12345", "ana@correo.com", "3104567890"),      # documento corto
            ("Ana Gómez", "1032456789", "ana@correo", "3104567890"),     # correo sin dominio
            ("Ana Gómez", "1032456789", "ana@correo.com", "31045"),      # teléfono corto
        ]
        for datos in casos:
            with self.subTest(datos=datos), self.assertRaises(ValidacionError):
                Cliente(*datos)

    def test_parametro_faltante(self):
        with self.assertRaises(ParametroFaltanteError):
            Cliente("Ana Gómez", None, "ana@correo.com", "3104567890")
        with self.assertRaises(ParametroFaltanteError):
            Cliente("   ", "1032456789", "ana@correo.com", "3104567890")

    def test_encapsulacion_setter_valida_modificaciones(self):
        c = nuevo_cliente()
        with self.assertRaises(ValidacionError):
            c.correo = "no-es-correo"
        self.assertEqual(c.correo, "ana@correo.com")  # el valor anterior se conserva
        with self.assertRaises(AttributeError):
            c.id = "CLI-9999"  # propiedad de solo lectura


class PruebasServicios(unittest.TestCase):
    def setUp(self):
        self.sala = ReservaSala("Sala A", 80000, capacidad=10, incluye_audiovisual=True)
        self.equipo = AlquilerEquipo("Portátiles", 15000, "portatil", unidades=3)
        self.asesoria = Asesoria("Consultoría", 100000, "nube", "experto")

    def test_polimorfismo_calcular_costo(self):
        # Misma llamada, fórmula distinta según la clase concreta.
        esperados = {self.sala: 80000 * 2 * 1.15, self.equipo: 15000 * 2, self.asesoria: 100000 * 2 * 2.0}
        for servicio, esperado in esperados.items():
            with self.subTest(servicio=type(servicio).__name__):
                self.assertAlmostEqual(servicio.calcular_costo(2), esperado)
                self.assertIn(servicio.TIPO, servicio.describir())

    def test_variantes_de_calculo_sobrecarga(self):
        base = self.equipo.calcular_costo(10)                                 # solo duración
        self.assertEqual(base, 150000)
        self.assertEqual(self.equipo.calcular_costo(10, 0.19), 178500)        # con impuesto
        self.assertEqual(self.equipo.calcular_costo(10, 0.19, 0.10), 160650)  # impuesto + descuento
        self.assertEqual(self.equipo.calcular_costo(10, descuento=10), 135000)  # descuento como entero %
        self.assertEqual(self.equipo.calcular_costo(10, descuento="unad20"), 120000)  # código promo
        self.assertEqual(self.equipo.calcular_costo(10, cantidad=2), 300000)  # parámetro opcional propio

    def test_descuentos_inconsistentes(self):
        for descuento in (0.8, -0.1, "CODIGO_FALSO", [0.1], True):
            with self.subTest(descuento=descuento), self.assertRaises(CalculoInconsistenteError):
                self.sala.calcular_costo(2, 0.19, descuento)

    def test_impuesto_invalido_encadena_causa(self):
        with self.assertRaises(CalculoInconsistenteError) as ctx:
            self.sala.calcular_costo(2, impuesto="diecinueve")
        self.assertIsInstance(ctx.exception.__cause__, ValidacionError)

    def test_validar_parametros_sobrescrito(self):
        with self.assertRaises(ValidacionError):
            self.sala.validar_parametros(13)              # sala: máx 12 h
        with self.assertRaises(ValidacionError):
            self.sala.validar_parametros(2, asistentes=11)  # capacidad 10
        with self.assertRaises(ValidacionError):
            self.asesoria.validar_parametros(1.2)          # bloques de 30 min
        self.assertEqual(self.asesoria.validar_parametros("1.5"), 1.5)
        with self.assertRaises(ValidacionError):
            self.equipo.validar_parametros(2, cantidad=0)

    def test_creacion_incorrecta_de_servicios(self):
        with self.assertRaises(ValidacionError):
            ReservaSala("Sala", -1, capacidad=5)
        with self.assertRaises(ValidacionError):
            ReservaSala("Sala", 1000, capacidad=0)
        with self.assertRaises(ValidacionError):
            AlquilerEquipo("Dron", 1000, "dron", 2)
        with self.assertRaises(ValidacionError):
            Asesoria("Asesoría", 1000, "astrología")
        with self.assertRaises(ValidacionError):
            Asesoria("Asesoría", 1000, "nube", "maestro")

    def test_servicio_invalido_no_consume_id(self):
        primero = ReservaSala("Sala X", 1000, 5)
        with self.assertRaises(ValidacionError):
            ReservaSala("Sala Y", 1000, 0)
        segundo = ReservaSala("Sala Z", 1000, 5)
        n1, n2 = int(primero.id.split("-")[1]), int(segundo.id.split("-")[1])
        self.assertEqual(n2, n1 + 1)


class PruebasValidaciones(unittest.TestCase):
    def test_encadenamiento_desde_error_nativo(self):
        with self.assertRaises(ValidacionError) as ctx:
            validar_numero("abc", "duracion")
        self.assertIsInstance(ctx.exception.__cause__, ValueError)

    def test_rechaza_no_finitos_y_booleanos(self):
        for valor in (float("nan"), float("inf"), True):
            with self.subTest(valor=valor), self.assertRaises(ValidacionError):
                validar_numero(valor, "x")


class PruebasReserva(unittest.TestCase):
    def setUp(self):
        self.cliente = nuevo_cliente()
        self.equipo = AlquilerEquipo("Proyectores", 20000, "proyector", unidades=2)

    def test_flujo_completo(self):
        r = Reserva(self.cliente, self.equipo, 5, cantidad=2)
        self.assertIs(r.estado, EstadoReserva.PENDIENTE)
        r.confirmar()
        self.assertEqual(self.equipo.unidades, 0)  # inventario ocupado
        total = r.procesar()                         # IVA por defecto
        self.assertEqual(total, round(20000 * 5 * 2 * 1.19, 2))
        self.assertIs(r.estado, EstadoReserva.PROCESADA)
        self.assertEqual([e for _, e, _ in r.historial],
                         [EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA, EstadoReserva.PROCESADA])
        r.validar()

    def test_cancelacion_libera_inventario(self):
        r = Reserva(self.cliente, self.equipo, 5, cantidad=2)
        r.confirmar()
        r.cancelar("Evento aplazado")
        self.assertEqual(self.equipo.unidades, 2)
        self.assertIs(r.estado, EstadoReserva.CANCELADA)

    def test_transiciones_no_permitidas(self):
        r = Reserva(self.cliente, self.equipo, 5)
        with self.assertRaises(OperacionNoPermitidaError):
            r.procesar()          # sin confirmar
        r.confirmar()
        with self.assertRaises(OperacionNoPermitidaError):
            r.confirmar()         # doble confirmación
        r.procesar()
        with self.assertRaises(OperacionNoPermitidaError):
            r.cancelar()          # ya procesada

    def test_procesamiento_fallido_conserva_estado(self):
        r = Reserva(self.cliente, self.equipo, 5)
        r.confirmar()
        with self.assertRaises(ReservaInvalidaError) as ctx:
            r.procesar(0.19, 0.9)
        self.assertIsInstance(ctx.exception.__cause__, CalculoInconsistenteError)
        self.assertIs(r.estado, EstadoReserva.CONFIRMADA)  # el bloque else no se ejecutó
        self.assertIsNone(r.costo_total)
        self.assertIsNotNone(r.procesar())                 # se puede reintentar con datos válidos

    def test_reservas_incorrectas(self):
        with self.assertRaises(ReservaInvalidaError):
            Reserva("no es cliente", self.equipo, 2)
        with self.assertRaises(ReservaInvalidaError) as ctx:
            Reserva(self.cliente, self.equipo, 100)
        self.assertIsInstance(ctx.exception.__cause__, ValidacionError)
        with self.assertRaises(ServicioNoDisponibleError):
            Reserva(self.cliente, self.equipo, 2, cantidad=3)
        self.equipo.desactivar()
        with self.assertRaises(ServicioNoDisponibleError):
            Reserva(self.cliente, self.equipo, 2)

    def test_confirmar_revalida_disponibilidad(self):
        r = Reserva(self.cliente, self.equipo, 2)
        self.equipo.desactivar()
        with self.assertRaises(ServicioNoDisponibleError):
            r.confirmar()
        self.assertIs(r.estado, EstadoReserva.PENDIENTE)


class PruebasGestor(unittest.TestCase):
    def setUp(self):
        self.g = GestorSistema()
        self.g.registrar_cliente("Carlos Ruiz", "79856123", "cruiz@empresa.co", "6015551234")
        self.sala = self.g.registrar_servicio("sala", nombre="Sala B", tarifa_hora=50000, capacidad=6)

    def test_listas_internas_encapsuladas(self):
        self.assertIsInstance(self.g.clientes, tuple)
        with self.assertRaises(AttributeError):
            self.g.clientes.append("intruso")
        self.assertEqual(len(self.g.clientes), 1)

    def test_cliente_duplicado(self):
        with self.assertRaises(OperacionNoPermitidaError):
            self.g.registrar_cliente("Otro Nombre", "79856123", "otro@empresa.co", "6015550000")
        self.assertEqual(len(self.g.clientes), 1)

    def test_servicio_tipo_desconocido_y_parametro_faltante(self):
        with self.assertRaises(ValidacionError):
            self.g.registrar_servicio("transporte", nombre="Van", tarifa_hora=1000)
        with self.assertRaises(ParametroFaltanteError) as ctx:
            self.g.registrar_servicio("equipo", nombre="Cámaras", tarifa_hora=1000)
        self.assertIsInstance(ctx.exception.__cause__, TypeError)
        self.assertEqual(len(self.g.servicios), 1)

    def test_busquedas_inexistentes(self):
        for buscar, valor in ((self.g.buscar_cliente, "00000000"), (self.g.buscar_servicio, "SRV-X"),
                              (self.g.buscar_reserva, "RES-X")):
            with self.subTest(buscar=buscar.__name__), self.assertRaises(EntidadNoEncontradaError):
                buscar(valor)

    def test_flujo_y_resumen(self):
        r = self.g.crear_reserva("79856123", self.sala.id, 2, asistentes=4)
        self.g.confirmar_reserva(r.id)
        total = self.g.procesar_reserva(r.id, 0, None)
        self.assertEqual(total, 100000)
        resumen = self.g.resumen()
        self.assertEqual(resumen["ingresos"], 100000)
        self.assertEqual(resumen["por_estado"]["procesada"], 1)

    def test_errores_quedan_registrados_en_log(self):
        with self.assertRaises(SoftwareFJError):
            self.g.crear_reserva("79856123", self.sala.id, "abc")
        for manejador in logging.getLogger("software_fj").handlers:
            manejador.flush()
        contenido = RUTA_LOG.read_text(encoding="utf-8")
        self.assertIn("WARNING", contenido)
        self.assertIn("causa: ValidacionError", contenido)


class PruebasContinuidad(unittest.TestCase):
    def test_simulacion_completa_sin_interrupciones(self):
        import main
        # Se redirige el log de la simulación al archivo temporal de pruebas.
        original = main.configurar_registro
        main.configurar_registro = lambda: configurar_registro(RUTA_LOG)
        try:
            with redirect_stdout(io.StringIO()) as salida:
                codigo = main.main()
        finally:
            main.configurar_registro = original
        self.assertEqual(codigo, 0, salida.getvalue())
        self.assertIn("terminó sin interrupciones", salida.getvalue())

    def test_error_inesperado_no_detiene_la_aplicacion(self):
        import main
        log = logging.getLogger("software_fj.main")
        malo = main.Operacion("División por cero", lambda: 1 / 0, "FALLO")
        bueno = main.Operacion("Operación válida", lambda: 42, "EXITO")
        r1 = main.ejecutar_operacion(1, malo, log)
        r2 = main.ejecutar_operacion(2, bueno, log)
        self.assertEqual(r1.obtenido, "FALLO")
        self.assertIn("ERROR INESPERADO ZeroDivisionError", r1.detalle)
        self.assertEqual(r2.obtenido, "EXITO")


if __name__ == "__main__":
    unittest.main()
