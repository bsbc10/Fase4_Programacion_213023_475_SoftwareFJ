"""
``GestorSistema``: fachada que administra clientes, servicios y reservas
mediante **listas internas** (sin base de datos).

Cada operación pública pasa por ``_ejecutar``, que aplica el patrón
**try / except / else**: si la operación falla con un error controlado se
registra en el log como WARNING y se relanza al llamador; si tiene éxito
(bloque ``else``) se registra como INFO.
"""

from typing import Callable, TypeVar  # Tipado del método genérico _ejecutar.

from .cliente import Cliente
from .excepciones import (
    EntidadNoEncontradaError,
    OperacionNoPermitidaError,
    ParametroFaltanteError,
    SoftwareFJError,
    ValidacionError,
)
from .registro import obtener_logger
from .reserva import EstadoReserva, Reserva
from .servicios import IVA, AlquilerEquipo, Asesoria, ReservaSala, Servicio

log = obtener_logger("sistema")
T = TypeVar("T")  # Tipo genérico del resultado de cada operación.


class GestorSistema:
    """Administra las colecciones del sistema Software FJ."""

    # Fábrica de servicios: asocia un nombre corto con la clase concreta (extensible).
    TIPOS_SERVICIO: dict[str, type[Servicio]] = {
        "sala": ReservaSala,
        "equipo": AlquilerEquipo,
        "asesoria": Asesoria,
    }

    def __init__(self) -> None:
        # Listas internas privadas: única "fuente de datos" del sistema.
        self.__clientes: list[Cliente] = []
        self.__servicios: list[Servicio] = []
        self.__reservas: list[Reserva] = []

    # ------------------------------------------------- acceso de solo lectura
    @property
    def clientes(self) -> tuple[Cliente, ...]:
        """Copia inmutable: desde fuera no se puede agregar ni borrar sin validar."""
        return tuple(self.__clientes)

    @property
    def servicios(self) -> tuple[Servicio, ...]:
        return tuple(self.__servicios)

    @property
    def reservas(self) -> tuple[Reserva, ...]:
        return tuple(self.__reservas)

    # ------------------------------------------------------- ejecución común
    @staticmethod
    def _ejecutar(operacion: str, accion: Callable[[], T]) -> T:
        """Ejecuta ``accion`` registrando el resultado (try/except/else)."""
        try:
            resultado = accion()
        except SoftwareFJError as error:
            # Si el error fue encadenado, también se registra su causa original.
            causa = f" | causa: {type(error.__cause__).__name__}: {error.__cause__}" if error.__cause__ else ""
            log.warning("%s FALLÓ: %s%s", operacion, error, causa)
            raise  # Se relanza para que la capa superior decida cómo continuar.
        else:
            # Se registra el ID de la entidad afectada (o el valor devuelto, p. ej. un costo).
            log.info("%s OK -> %s", operacion, getattr(resultado, "id", resultado))
            return resultado

    # ----------------------------------------------------------- búsquedas
    def buscar_cliente(self, documento: str) -> Cliente:
        """Busca un cliente por documento en la lista interna."""
        for cliente in self.__clientes:
            if cliente.documento == str(documento).strip():
                return cliente
        raise EntidadNoEncontradaError(f"No existe un cliente con documento terminado en '{str(documento)[-4:]}'.")

    def buscar_servicio(self, id_servicio: str) -> Servicio:
        """Busca un servicio por su ID."""
        for servicio in self.__servicios:
            if servicio.id == id_servicio:
                return servicio
        raise EntidadNoEncontradaError(f"No existe el servicio '{id_servicio}'.")

    def buscar_reserva(self, id_reserva: str) -> Reserva:
        """Busca una reserva por su ID."""
        for reserva in self.__reservas:
            if reserva.id == id_reserva:
                return reserva
        raise EntidadNoEncontradaError(f"No existe la reserva '{id_reserva}'.")

    # ------------------------------------------------------------- clientes
    def registrar_cliente(self, nombre=None, documento=None, correo=None, telefono=None) -> Cliente:
        """Crea, valida y agrega un cliente. Los parámetros ausentes generan ``ParametroFaltanteError``."""

        def accion() -> Cliente:
            # La validación de cada dato ocurre dentro de los setters de Cliente.
            cliente = Cliente(nombre, documento, correo, telefono)
            # Regla de negocio: no se permiten documentos duplicados.
            if any(c.documento == cliente.documento for c in self.__clientes):
                raise OperacionNoPermitidaError(
                    f"Ya existe un cliente con el documento {cliente.documento_enmascarado}.")
            self.__clientes.append(cliente)
            return cliente

        return self._ejecutar("Registrar cliente", accion)

    # ------------------------------------------------------------ servicios
    def registrar_servicio(self, tipo: str, **datos) -> Servicio:
        """Crea un servicio del ``tipo`` indicado ('sala', 'equipo' o 'asesoria')."""

        def accion() -> Servicio:
            clase = self.TIPOS_SERVICIO.get(str(tipo).strip().lower())
            if clase is None:
                raise ValidacionError(f"Tipo de servicio desconocido: '{tipo}'.",
                                      detalle={"permitidos": sorted(self.TIPOS_SERVICIO)})
            try:
                servicio = clase(**datos)
            except TypeError as error:
                # Falta un argumento obligatorio o sobra uno desconocido: se encadena la causa.
                raise ParametroFaltanteError(
                    f"Parámetros incompletos o desconocidos para '{tipo}': {error}") from error
            self.__servicios.append(servicio)
            return servicio

        return self._ejecutar(f"Registrar servicio ({tipo})", accion)

    def cambiar_disponibilidad(self, id_servicio: str, disponible: bool) -> Servicio:
        """Activa o desactiva un servicio existente."""

        def accion() -> Servicio:
            servicio = self.buscar_servicio(id_servicio)
            if disponible:
                servicio.activar()
            else:
                servicio.desactivar()
            return servicio

        estado = "activar" if disponible else "desactivar"
        return self._ejecutar(f"{estado.capitalize()} servicio {id_servicio}", accion)

    # ------------------------------------------------------------- reservas
    def crear_reserva(self, documento_cliente: str, id_servicio: str, duracion, **opciones) -> Reserva:
        """Crea una reserva PENDIENTE para un cliente y un servicio existentes."""

        def accion() -> Reserva:
            cliente = self.buscar_cliente(documento_cliente)
            servicio = self.buscar_servicio(id_servicio)
            reserva = Reserva(cliente, servicio, duracion, **opciones)
            self.__reservas.append(reserva)
            return reserva

        return self._ejecutar(f"Crear reserva ({id_servicio})", accion)

    def confirmar_reserva(self, id_reserva: str) -> Reserva:
        def accion() -> Reserva:
            reserva = self.buscar_reserva(id_reserva)
            reserva.confirmar()
            return reserva

        return self._ejecutar(f"Confirmar reserva {id_reserva}", accion)

    def cancelar_reserva(self, id_reserva: str, motivo: str = "Solicitud del cliente") -> Reserva:
        def accion() -> Reserva:
            reserva = self.buscar_reserva(id_reserva)
            reserva.cancelar(motivo)
            return reserva

        return self._ejecutar(f"Cancelar reserva {id_reserva}", accion)

    def procesar_reserva(self, id_reserva: str, impuesto: float = IVA, descuento=None) -> float:
        def accion() -> float:
            return self.buscar_reserva(id_reserva).procesar(impuesto, descuento)

        return self._ejecutar(f"Procesar reserva {id_reserva}", accion)

    # --------------------------------------------------------------- reporte
    def resumen(self) -> dict:
        """Totales del sistema calculados a partir de las listas internas."""
        procesadas = [r for r in self.__reservas if r.estado is EstadoReserva.PROCESADA]
        return {
            "clientes": len(self.__clientes),
            "servicios": len(self.__servicios),
            "reservas": len(self.__reservas),
            "por_estado": {e.value: sum(r.estado is e for r in self.__reservas) for e in EstadoReserva},
            "ingresos": round(sum(r.costo_total for r in procesadas), 2),
        }
