"""
Configuración del registro (logging) de eventos y errores en archivo.

Se usa el módulo estándar ``logging``: no requiere dependencias externas y
permite separar niveles (INFO para eventos, WARNING para errores
controlados, ERROR/CRITICAL para fallos inesperados).
"""

import logging  # Módulo estándar de registro de eventos.
from pathlib import Path  # Manejo de rutas independiente del sistema operativo.

# Nombre del logger raíz del proyecto; los módulos usan hijos como "software_fj.cliente".
NOMBRE_LOGGER = "software_fj"

# Ruta por defecto del archivo de logs: <carpeta 03_Desarrollo>/logs/software_fj.log
RUTA_LOG_POR_DEFECTO = Path(__file__).resolve().parent.parent / "logs" / "software_fj.log"

# Formato de cada línea: fecha, nivel, módulo y mensaje.
FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configurar_registro(ruta_log: Path | str | None = None, *, nivel: int = logging.INFO) -> logging.Logger:
    """Configura y devuelve el logger del proyecto escribiendo en ``ruta_log``.

    Es idempotente: si se llama varias veces, reemplaza el manejador de
    archivo anterior en lugar de duplicar líneas en el log.
    """
    # Si no se indica ruta, se usa la ruta por defecto del proyecto.
    ruta = Path(ruta_log) if ruta_log else RUTA_LOG_POR_DEFECTO
    # Se crea la carpeta de logs si no existe (parents=True crea toda la ruta).
    ruta.parent.mkdir(parents=True, exist_ok=True)

    # Se obtiene el logger raíz del proyecto.
    logger = logging.getLogger(NOMBRE_LOGGER)
    # Nivel mínimo de mensajes que se registrarán.
    logger.setLevel(nivel)
    # Evita que los mensajes se propaguen al logger raíz de Python (sin duplicados en consola).
    logger.propagate = False

    # Se cierran y eliminan manejadores previos para que la configuración sea idempotente.
    for manejador in list(logger.handlers):
        manejador.close()
        logger.removeHandler(manejador)

    # Manejador que escribe en el archivo, en UTF-8 para conservar tildes y eñes.
    manejador_archivo = logging.FileHandler(ruta, mode="a", encoding="utf-8")
    # Se aplica el formato definido arriba.
    manejador_archivo.setFormatter(logging.Formatter(FORMATO))
    # Se asocia el manejador al logger.
    logger.addHandler(manejador_archivo)
    return logger


def obtener_logger(nombre_modulo: str) -> logging.Logger:
    """Devuelve un logger hijo, p. ej. ``software_fj.reserva``."""
    # Los loggers hijos heredan los manejadores del logger "software_fj".
    return logging.getLogger(f"{NOMBRE_LOGGER}.{nombre_modulo}")
