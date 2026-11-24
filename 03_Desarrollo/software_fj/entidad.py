"""
Clase abstracta ``EntidadBase``: representa cualquier entidad general del sistema.

Cliente, Servicio y Reserva heredan de ella. Centraliza lo común a todas
las entidades (identificador único, fecha de creación) y obliga, mediante
métodos abstractos, a que cada subclase sepa describirse y validarse.
"""

from abc import ABC, abstractmethod  # Herramientas para definir clases abstractas.
from datetime import datetime  # Fecha y hora de creación de la entidad.
from itertools import count  # Generador de números consecutivos para los IDs.


class EntidadBase(ABC):
    """Entidad general del sistema (no instanciable directamente)."""

    # Un contador por prefijo (CLI, SRV, RES): cada tipo de entidad numera de forma independiente.
    _contadores: dict[str, count] = {}
    # Prefijo del identificador; cada subclase lo redefine (CLI, SRV, RES).
    PREFIJO_ID = "ENT"

    def __init__(self) -> None:
        # Las subclases llaman a este constructor DESPUÉS de validar sus datos, de modo que
        # un objeto inválido nunca consume un número de la secuencia.
        contador = EntidadBase._contadores.setdefault(self.PREFIJO_ID, count(1))
        # Se toma el siguiente número del contador y se forma un ID legible, p. ej. "CLI-0001".
        self.__id = f"{self.PREFIJO_ID}-{next(contador):04d}"
        # Momento exacto en que se creó el objeto.
        self.__fecha_creacion = datetime.now()

    @property
    def id(self) -> str:
        """Identificador único de solo lectura (no tiene setter)."""
        return self.__id

    @property
    def fecha_creacion(self) -> datetime:
        """Fecha de creación de solo lectura."""
        return self.__fecha_creacion

    @abstractmethod
    def describir(self) -> str:
        """Devuelve una descripción legible de la entidad (polimórfico)."""

    @abstractmethod
    def validar(self) -> None:
        """Verifica la coherencia interna del objeto; lanza excepción si no es válido."""

    def __repr__(self) -> str:
        # Representación técnica común para depuración: "<Cliente CLI-0001>".
        return f"<{type(self).__name__} {self.id}>"
