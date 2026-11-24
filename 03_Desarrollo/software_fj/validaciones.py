"""
Funciones de validación reutilizables por Cliente, Servicio y Reserva.

Cada función recibe el valor y el nombre del campo, y devuelve el valor ya
normalizado (sin espacios, convertido a número, etc.) o lanza una
excepción personalizada. Así las reglas no se repiten en cada clase.
"""

import math  # Para detectar valores no finitos (NaN, infinito).

from .excepciones import ParametroFaltanteError, ValidacionError


def validar_texto(valor, campo: str, *, minimo: int = 1, maximo: int = 100) -> str:
    """Valida un texto obligatorio y devuelve el texto sin espacios laterales."""
    # None o cadena vacía/solo espacios se consideran parámetro faltante.
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        raise ParametroFaltanteError(f"El campo '{campo}' es obligatorio.", detalle={"campo": campo})
    # Si llega otro tipo (número, lista...), es un dato inválido.
    if not isinstance(valor, str):
        raise ValidacionError(
            f"El campo '{campo}' debe ser texto; se recibió {type(valor).__name__}.",
            detalle={"campo": campo, "valor": repr(valor)},
        )
    # Se eliminan espacios al inicio y al final.
    texto = valor.strip()
    # Se verifica la longitud permitida.
    if not minimo <= len(texto) <= maximo:
        raise ValidacionError(
            f"El campo '{campo}' debe tener entre {minimo} y {maximo} caracteres.",
            detalle={"campo": campo, "longitud": len(texto)},
        )
    return texto


def validar_numero(valor, campo: str, *, minimo: float | None = None, maximo: float | None = None,
                   permitir_cero: bool = True) -> float:
    """Convierte ``valor`` a float y verifica que sea finito y esté en rango.

    Demuestra **encadenamiento de excepciones**: si ``float()`` falla con
    ``TypeError``/``ValueError``, se lanza ``ValidacionError`` con
    ``from error`` para conservar la causa original en ``__cause__``.
    """
    # Un valor ausente es un parámetro faltante.
    if valor is None:
        raise ParametroFaltanteError(f"El campo '{campo}' es obligatorio.", detalle={"campo": campo})
    # bool es subclase de int en Python; se rechaza explícitamente (True no es una duración).
    if isinstance(valor, bool):
        raise ValidacionError(f"El campo '{campo}' no admite valores booleanos.", detalle={"campo": campo})
    try:
        # Intento de conversión: acepta int, float o texto numérico como "2.5".
        numero = float(valor)
    except (TypeError, ValueError) as error:
        # Encadenamiento explícito: la causa técnica queda disponible en error.__cause__.
        raise ValidacionError(
            f"El campo '{campo}' debe ser numérico; se recibió {valor!r}.",
            detalle={"campo": campo, "valor": repr(valor)},
        ) from error
    # NaN e infinito no son cantidades válidas.
    if not math.isfinite(numero):
        raise ValidacionError(f"El campo '{campo}' debe ser un número finito.", detalle={"campo": campo})
    # Regla opcional: impedir el cero (p. ej. tarifas o duraciones).
    if not permitir_cero and numero == 0:
        raise ValidacionError(f"El campo '{campo}' no puede ser cero.", detalle={"campo": campo})
    # Límite inferior.
    if minimo is not None and numero < minimo:
        raise ValidacionError(
            f"El campo '{campo}' debe ser mayor o igual a {minimo}; se recibió {numero}.",
            detalle={"campo": campo, "valor": numero},
        )
    # Límite superior.
    if maximo is not None and numero > maximo:
        raise ValidacionError(
            f"El campo '{campo}' debe ser menor o igual a {maximo}; se recibió {numero}.",
            detalle={"campo": campo, "valor": numero},
        )
    return numero


def validar_entero(valor, campo: str, *, minimo: int | None = None, maximo: int | None = None) -> int:
    """Valida un número entero (capacidades, unidades)."""
    # Se reutiliza la validación numérica general (rango, finitud, encadenamiento).
    numero = validar_numero(valor, campo, minimo=minimo, maximo=maximo)
    # Se exige que no tenga parte decimal (3.0 es válido, 3.5 no).
    if not numero.is_integer():
        raise ValidacionError(f"El campo '{campo}' debe ser un número entero.", detalle={"campo": campo})
    return int(numero)
