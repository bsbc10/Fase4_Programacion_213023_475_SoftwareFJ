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

# Logger "software_fj.sistema": sus líneas se distinguen en el archivo de log por este nombre.
log = obtener_logger("sistema")
T = TypeVar("T")  # Tipo genérico del resultado de cada operación.


class GestorSistema:
    """Administra las colecciones del sistema Software FJ."""

    # Fábrica de servicios: asocia un nombre corto con la clase concreta (extensible).
    # Para añadir un servicio nuevo basta con crear la subclase y registrarla aquí.
    TIPOS_SERVICIO: dict[str, type[Servicio]] = {
        "sala": ReservaSala,
        "equipo": AlquilerEquipo,
        "asesoria": Asesoria,
    }

    def __init__(self) -> None:
        # Listas internas privadas: única "fuente de datos" del sistema.
        # El doble guion bajo activa el "name mangling" de Python (_GestorSistema__clientes),
        # lo que impide modificarlas por accidente desde fuera de la clase.
        self.__clientes: list[Cliente] = []
        self.__servicios: list[Servicio] = []
        self.__reservas: list[Reserva] = []

    # ------------------------------------------------- acceso de solo lectura
    @property
    def clientes(self) -> tuple[Cliente, ...]:
        """Copia inmutable: desde fuera no se puede agregar ni borrar sin validar."""
        # tuple() crea una copia: un .append() externo fallaría (las tuplas no lo tienen).
        return tuple(self.__clientes)

    @property
    def servicios(self) -> tuple[Servicio, ...]:
        """Copia inmutable de la lista de servicios."""
        return tuple(self.__servicios)

    @property
    def reservas(self) -> tuple[Reserva, ...]:
        """Copia inmutable de la lista de reservas."""
        return tuple(self.__reservas)

    # ------------------------------------------------------- ejecución común
    @staticmethod
    def _ejecutar(operacion: str, accion: Callable[[], T]) -> T:
        """Ejecuta ``accion`` registrando el resultado (try/except/else)."""
        try:
            # La acción concreta (registrar, reservar...) se recibe como función sin argumentos.
            resultado = accion()
        except SoftwareFJError as error:
            # Si el error fue encadenado (raise ... from), también se registra su causa original.
            causa = f" | causa: {type(error.__cause__).__name__}: {error.__cause__}" if error.__cause__ else ""
            log.warning("%s FALLÓ: %s%s", operacion, error, causa)
            raise  # Se relanza para que la capa superior decida cómo continuar.
        else:
            # Solo se llega aquí si accion() no lanzó ninguna excepción.
            # Se registra el ID de la entidad afectada (o el valor devuelto, p. ej. un costo).
            log.info("%s OK -> %s", operacion, getattr(resultado, "id", resultado))
            return resultado

    # ----------------------------------------------------------- búsquedas
    def buscar_cliente(self, documento: str) -> Cliente:
        """Busca un cliente por documento en la lista interna."""
        # Búsqueda lineal: suficiente para el volumen de una simulación en memoria.
        for cliente in self.__clientes:
            # str() y strip() permiten buscar con número o texto con espacios.
            if cliente.documento == str(documento).strip():
                return cliente
        # El mensaje solo muestra los 4 últimos dígitos para no exponer el documento en el log.
        raise EntidadNoEncontradaError(f"No existe un cliente con documento terminado en '{str(documento)[-4:]}'.")

    def buscar_servicio(self, id_servicio: str) -> Servicio:
        """Busca un servicio por su ID."""
        for servicio in self.__servicios:
            if servicio.id == id_servicio:
                return servicio
        # Si el bucle termina sin retornar, el ID no existe en la lista.
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
        # Los valores por defecto None hacen que un dato omitido llegue a la validación
        # (ParametroFaltanteError) en lugar de provocar un TypeError de Python.

        def accion() -> Cliente:
            # La validación de cada dato ocurre dentro de los setters de Cliente.
            cliente = Cliente(nombre, documento, correo, telefono)
            # Regla de negocio: no se permiten documentos duplicados.
            if any(c.documento == cliente.documento for c in self.__clientes):
                raise OperacionNoPermitidaError(
                    f"Ya existe un cliente con el documento {cliente.documento_enmascarado}.")
            # Solo un cliente válido y no duplicado entra a la lista interna.
            self.__clientes.append(cliente)
            return cliente

        # Toda operación pública se delega en _ejecutar para registrar éxito o fallo en el log.
        return self._ejecutar("Registrar cliente", accion)

    # ------------------------------------------------------------ servicios
    def registrar_servicio(self, tipo: str, **datos) -> Servicio:
        """Crea un servicio del ``tipo`` indicado ('sala', 'equipo' o 'asesoria')."""

        def accion() -> Servicio:
            # Se normaliza el tipo (sin espacios, minúsculas) y se busca su clase en la fábrica.
            clase = self.TIPOS_SERVICIO.get(str(tipo).strip().lower())
            if clase is None:
                raise ValidacionError(f"Tipo de servicio desconocido: '{tipo}'.",
                                      detalle={"permitidos": sorted(self.TIPOS_SERVICIO)})
            try:
                # **datos pasa el diccionario como argumentos con nombre al constructor.
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
                # Un servicio desactivado rechaza nuevas reservas (ServicioNoDisponibleError).
                servicio.desactivar()
            return servicio

        # El texto de la operación ("Activar"/"Desactivar") se usa solo para el log.
        estado = "activar" if disponible else "desactivar"
        return self._ejecutar(f"{estado.capitalize()} servicio {id_servicio}", accion)

    # ------------------------------------------------------------- reservas
    def crear_reserva(self, documento_cliente: str, id_servicio: str, duracion, **opciones) -> Reserva:
        """Crea una reserva PENDIENTE para un cliente y un servicio existentes."""

        def accion() -> Reserva:
            # Ambas búsquedas lanzan EntidadNoEncontradaError si el dato no existe.
            cliente = self.buscar_cliente(documento_cliente)
            servicio = self.buscar_servicio(id_servicio)
            # El constructor de Reserva valida duración, opciones y disponibilidad.
            reserva = Reserva(cliente, servicio, duracion, **opciones)
            self.__reservas.append(reserva)
            return reserva

        return self._ejecutar(f"Crear reserva ({id_servicio})", accion)

    def confirmar_reserva(self, id_reserva: str) -> Reserva:
        """Confirma una reserva PENDIENTE (ver ``Reserva.confirmar``)."""

        def accion() -> Reserva:
            reserva = self.buscar_reserva(id_reserva)
            reserva.confirmar()
            return reserva

        return self._ejecutar(f"Confirmar reserva {id_reserva}", accion)

    def cancelar_reserva(self, id_reserva: str, motivo: str = "Solicitud del cliente") -> Reserva:
        """Cancela una reserva PENDIENTE o CONFIRMADA (ver ``Reserva.cancelar``)."""

        def accion() -> Reserva:
            reserva = self.buscar_reserva(id_reserva)
            reserva.cancelar(motivo)
            return reserva

        return self._ejecutar(f"Cancelar reserva {id_reserva}", accion)

    def procesar_reserva(self, id_reserva: str, impuesto: float = IVA, descuento=None) -> float:
        """Procesa una reserva CONFIRMADA y devuelve su costo total (ver ``Reserva.procesar``)."""

        def accion() -> float:
            return self.buscar_reserva(id_reserva).procesar(impuesto, descuento)

        return self._ejecutar(f"Procesar reserva {id_reserva}", accion)

    # --------------------------------------------------------------- reporte
    def resumen(self) -> dict:
        """Totales del sistema calculados a partir de las listas internas."""
        # Solo las reservas procesadas tienen costo_total; las demás valen None.
        procesadas = [r for r in self.__reservas if r.estado is EstadoReserva.PROCESADA]
        return {
            "clientes": len(self.__clientes),
            "servicios": len(self.__servicios),
            "reservas": len(self.__reservas),
            # sum() de booleanos cuenta los True: número de reservas en cada estado.
            "por_estado": {e.value: sum(r.estado is e for r in self.__reservas) for e in EstadoReserva},
            "ingresos": round(sum(r.costo_total for r in procesadas), 2),
        }
