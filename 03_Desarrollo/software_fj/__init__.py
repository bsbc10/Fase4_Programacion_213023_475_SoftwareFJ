"""
Paquete ``software_fj``: Sistema Integral de Gestión de Clientes, Servicios
y Reservas (Fase 4 - Programación 213023, UNAD).

Se exponen aquí las clases principales para importarlas de forma corta:
``from software_fj import GestorSistema``.
"""

from .cliente import Cliente
from .entidad import EntidadBase
from .excepciones import (
    CalculoInconsistenteError,
    EntidadNoEncontradaError,
    OperacionNoPermitidaError,
    ParametroFaltanteError,
    ReservaInvalidaError,
    ServicioNoDisponibleError,
    SoftwareFJError,
    ValidacionError,
)
from .registro import configurar_registro
from .reserva import EstadoReserva, Reserva
from .servicios import AlquilerEquipo, Asesoria, ReservaSala, Servicio
from .sistema import GestorSistema

__all__ = [
    "AlquilerEquipo", "Asesoria", "CalculoInconsistenteError", "Cliente", "EntidadBase",
    "EntidadNoEncontradaError", "EstadoReserva", "GestorSistema", "OperacionNoPermitidaError",
    "ParametroFaltanteError", "Reserva", "ReservaInvalidaError", "ReservaSala", "Servicio",
    "ServicioNoDisponibleError", "SoftwareFJError", "ValidacionError", "configurar_registro",
]
