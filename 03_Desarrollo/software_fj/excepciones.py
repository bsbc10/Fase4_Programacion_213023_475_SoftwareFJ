"""
Módulo de excepciones personalizadas del sistema Software FJ.

Todas las excepciones del dominio heredan de ``SoftwareFJError``. Esto
permite que la capa de aplicación capture con un solo ``except`` cualquier
error controlado del negocio, y que distinga esos errores de los fallos
inesperados de Python (``Exception`` genérica).

Jerarquía:

    SoftwareFJError
    ├── ValidacionError
    │   └── ParametroFaltanteError
    ├── EntidadNoEncontradaError
    ├── OperacionNoPermitidaError
    ├── ServicioNoDisponibleError
    ├── ReservaInvalidaError
    └── CalculoInconsistenteError
"""


class SoftwareFJError(Exception):
    """Excepción raíz de todos los errores controlados del sistema."""

    # Código corto por defecto; cada subclase lo redefine para identificar el error en los logs.
    codigo = "SFJ-000"

    def __init__(self, mensaje: str, *, detalle: dict | None = None) -> None:
        # Se inicializa la clase base Exception con el mensaje legible.
        super().__init__(mensaje)
        # Se guarda el mensaje como atributo para usarlo en logs y reportes.
        self.mensaje = mensaje
        # Diccionario opcional con datos de contexto (valor recibido, campo, etc.).
        self.detalle = detalle or {}

    def __str__(self) -> str:
        # Representación uniforme: "[CÓDIGO] mensaje".
        return f"[{self.codigo}] {self.mensaje}"


class ValidacionError(SoftwareFJError):
    """Datos inválidos: formato incorrecto, valores fuera de rango, tipos erróneos."""

    codigo = "SFJ-100"


class ParametroFaltanteError(ValidacionError):
    """Un parámetro obligatorio no fue suministrado o llegó vacío."""

    codigo = "SFJ-101"


class EntidadNoEncontradaError(SoftwareFJError):
    """Se buscó un cliente, servicio o reserva que no existe en las listas internas."""

    codigo = "SFJ-200"


class OperacionNoPermitidaError(SoftwareFJError):
    """La operación viola una regla de negocio (p. ej. cancelar una reserva ya procesada)."""

    codigo = "SFJ-300"


class ServicioNoDisponibleError(SoftwareFJError):
    """El servicio solicitado está inactivo o sin capacidad/unidades."""

    codigo = "SFJ-400"


class ReservaInvalidaError(SoftwareFJError):
    """La reserva no puede crearse o procesarse con los datos indicados."""

    codigo = "SFJ-500"


class CalculoInconsistenteError(SoftwareFJError):
    """El cálculo de costos produjo o recibió valores incoherentes."""

    codigo = "SFJ-600"
