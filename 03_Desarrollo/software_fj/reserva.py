"""
Clase ``Reserva``: integra cliente, servicio, duración y estado.

Ciclo de vida (máquina de estados):

    PENDIENTE ──confirmar()──► CONFIRMADA ──procesar()──► PROCESADA
        │                          │
        └────────cancelar()────────┴──────► CANCELADA

Cualquier transición distinta a las del diagrama lanza
``OperacionNoPermitidaError``.
"""

from datetime import datetime  # Marca de tiempo del historial de estados.
from enum import Enum  # Enumeración de estados posibles.

from .cliente import Cliente
from .entidad import EntidadBase
from .excepciones import (
    CalculoInconsistenteError,
    OperacionNoPermitidaError,
    ReservaInvalidaError,
    ValidacionError,
)
from .registro import obtener_logger
from .servicios import IVA, Servicio
from .validaciones import validar_texto

# Logger de este módulo: escribe en el mismo archivo con el nombre "software_fj.reserva".
log = obtener_logger("reserva")


class EstadoReserva(Enum):
    """Estados posibles de una reserva."""

    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    PROCESADA = "procesada"
    CANCELADA = "cancelada"


class Reserva(EntidadBase):
    """Reserva de un servicio por parte de un cliente."""

    PREFIJO_ID = "RES"

    def __init__(self, cliente: Cliente, servicio: Servicio, duracion: float, **opciones) -> None:
        # Validación de tipos: una reserva solo puede vincular objetos del dominio.
        if not isinstance(cliente, Cliente):
            raise ReservaInvalidaError("La reserva requiere un objeto Cliente válido.",
                                       detalle={"recibido": type(cliente).__name__})
        if not isinstance(servicio, Servicio):
            raise ReservaInvalidaError("La reserva requiere un objeto Servicio válido.",
                                       detalle={"recibido": type(servicio).__name__})
        try:
            # Polimorfismo: cada servicio valida la duración y opciones con sus propias reglas.
            horas = servicio.validar_parametros(duracion, **opciones)
        except ValidacionError as error:
            # Encadenamiento: el motivo técnico (ValidacionError) queda como __cause__.
            raise ReservaInvalidaError(
                f"Parámetros de reserva inválidos para '{servicio.nombre}': {error.mensaje}",
                detalle={"servicio": servicio.id},
            ) from error

        # Disponibilidad (lanza ServicioNoDisponibleError si el servicio está inactivo o sin stock).
        servicio.verificar_disponibilidad(**opciones)

        # Solo si todo es válido se crea la entidad (y se consume un ID).
        super().__init__()
        self.__cliente = cliente
        self.__servicio = servicio
        self.__duracion = horas
        # Copia de las opciones para que cambios externos al diccionario no afecten la reserva.
        self.__opciones = dict(opciones)
        self.__estado = EstadoReserva.PENDIENTE
        self.__costo_total: float | None = None
        # Lista interna con el historial de cambios de estado: (fecha, estado, nota).
        self.__historial: list[tuple[datetime, EstadoReserva, str]] = []
        self.__registrar_estado("Reserva creada")

    # ------------------------------------------------------------- propiedades
    @property
    def cliente(self) -> Cliente:
        return self.__cliente

    @property
    def servicio(self) -> Servicio:
        return self.__servicio

    @property
    def duracion(self) -> float:
        return self.__duracion

    @property
    def estado(self) -> EstadoReserva:
        return self.__estado

    @property
    def costo_total(self) -> float | None:
        """Costo final; ``None`` hasta que la reserva se procese."""
        return self.__costo_total

    @property
    def historial(self) -> tuple:
        """Copia inmutable del historial (encapsulación de la lista interna)."""
        return tuple(self.__historial)

    # ---------------------------------------------------------- utilitarios
    def __registrar_estado(self, nota: str) -> None:
        """Agrega una entrada al historial y la escribe en el log."""
        self.__historial.append((datetime.now(), self.__estado, nota))
        log.info("%s -> %s: %s", self.id, self.__estado.value.upper(), nota)

    def __exigir_estado(self, operacion: str, *permitidos: EstadoReserva) -> None:
        """Lanza ``OperacionNoPermitidaError`` si el estado actual no está entre ``permitidos``."""
        if self.__estado not in permitidos:
            raise OperacionNoPermitidaError(
                f"No se puede {operacion} la reserva {self.id} en estado '{self.__estado.value}'.",
                detalle={"reserva": self.id, "estado": self.__estado.value},
            )

    # -------------------------------------------------------------- operaciones
    def confirmar(self) -> None:
        """PENDIENTE → CONFIRMADA. Ocupa el recurso del servicio (p. ej. unidades de equipo)."""
        self.__exigir_estado("confirmar", EstadoReserva.PENDIENTE)
        # Se revalida la disponibilidad: el servicio pudo desactivarse después de crear la reserva.
        self.__servicio.verificar_disponibilidad(**self.__opciones)
        # Gancho polimórfico: solo AlquilerEquipo descuenta inventario.
        self.__servicio.ocupar(**self.__opciones)
        self.__estado = EstadoReserva.CONFIRMADA
        self.__registrar_estado("Reserva confirmada")

    def cancelar(self, motivo: str = "Sin motivo") -> None:
        """PENDIENTE/CONFIRMADA → CANCELADA. Libera el recurso si estaba confirmada."""
        self.__exigir_estado("cancelar", EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA)
        motivo = validar_texto(motivo, "motivo", maximo=200)
        # Solo una reserva confirmada había ocupado recursos.
        if self.__estado is EstadoReserva.CONFIRMADA:
            self.__servicio.liberar(**self.__opciones)
        self.__estado = EstadoReserva.CANCELADA
        self.__registrar_estado(f"Reserva cancelada. Motivo: {motivo}")

    def procesar(self, impuesto: float = IVA, descuento=None) -> float:
        """CONFIRMADA → PROCESADA. Calcula y fija el costo total.

        Usa **try / except / else / finally**:

        * ``try``: cálculo polimórfico del costo.
        * ``except``: un cálculo inconsistente se transforma (encadenado) en
          ``ReservaInvalidaError``; la reserva conserva su estado CONFIRMADA.
        * ``else``: solo si no hubo error se cambia el estado y se guarda el costo.
        * ``finally``: siempre se registra que hubo un intento de procesamiento.
        """
        self.__exigir_estado("procesar", EstadoReserva.CONFIRMADA)
        exito = False
        try:
            total = self.__servicio.calcular_costo(self.__duracion, impuesto, descuento, **self.__opciones)
        except CalculoInconsistenteError as error:
            raise ReservaInvalidaError(
                f"No se pudo procesar la reserva {self.id}: {error.mensaje}",
                detalle={"reserva": self.id},
            ) from error
        else:
            self.__costo_total = total
            self.__estado = EstadoReserva.PROCESADA
            self.__registrar_estado(f"Reserva procesada. Total ${total:,.2f}")
            exito = True
            return total
        finally:
            # Se ejecuta tanto si hubo éxito como si se lanzó la excepción.
            log.info("Intento de procesamiento de %s finalizado (exito=%s)", self.id, exito)

    # ------------------------------------------------------ métodos abstractos
    def validar(self) -> None:
        """Comprueba la coherencia interna de la reserva."""
        if self.__duracion <= 0:
            raise ReservaInvalidaError("La duración de la reserva debe ser positiva.")
        # Una reserva procesada debe tener costo; una no procesada no debe tenerlo.
        procesada = self.__estado is EstadoReserva.PROCESADA
        if procesada != (self.__costo_total is not None):
            raise ReservaInvalidaError(f"Estado y costo incoherentes en {self.id}.")

    def describir(self) -> str:
        costo = f"${self.__costo_total:,.2f}" if self.__costo_total is not None else "por calcular"
        return (f"Reserva {self.id}: {self.__cliente.nombre} | {self.__servicio.TIPO} '{self.__servicio.nombre}' | "
                f"{self.__duracion:g} h | estado {self.__estado.value} | costo {costo}")
