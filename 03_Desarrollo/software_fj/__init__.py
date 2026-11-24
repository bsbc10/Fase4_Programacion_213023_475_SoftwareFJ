"""
Paquete ``software_fj``: Sistema Integral de Gestión de Clientes, Servicios
y Reservas (Fase 4 - Programación 213023, UNAD).

Se exponen aquí las clases principales para importarlas de forma corta:
``from software_fj import GestorSistema``.
"""

# Importaciones relativas (con punto): se refieren a módulos de este mismo paquete.
# Este archivo se ejecuta al importar "software_fj"; por eso reexporta las clases públicas.
from .cliente import Cliente  # Cliente con datos personales validados.
from .entidad import EntidadBase  # Clase abstracta raíz de las entidades.
# Jerarquía completa de excepciones personalizadas.
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
from .registro import configurar_registro  # Configuración del archivo de logs.
from .reserva import EstadoReserva, Reserva  # Reserva y su máquina de estados.
from .servicios import AlquilerEquipo, Asesoria, ReservaSala, Servicio  # Servicio abstracto y sus 3 subclases.
from .sistema import GestorSistema  # Fachada con las listas internas.

# __all__ define qué nombres exporta "from software_fj import *" (la API pública del paquete).
__all__ = [
    "AlquilerEquipo", "Asesoria", "CalculoInconsistenteError", "Cliente", "EntidadBase",
    "EntidadNoEncontradaError", "EstadoReserva", "GestorSistema", "OperacionNoPermitidaError",
    "ParametroFaltanteError", "Reserva", "ReservaInvalidaError", "ReservaSala", "Servicio",
    "ServicioNoDisponibleError", "SoftwareFJError", "ValidacionError", "configurar_registro",
]
