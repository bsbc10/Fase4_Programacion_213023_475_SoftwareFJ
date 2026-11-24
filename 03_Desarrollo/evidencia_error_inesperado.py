"""
Evidencia del manejo de un error **inesperado** (no previsto por el negocio).

Ejecutar desde la carpeta ``03_Desarrollo``::

    python evidencia_error_inesperado.py

La simulación principal (``main.py``) solo produce errores controlados
(subclases de ``SoftwareFJError``). Para demostrar la red de seguridad
``except Exception`` de ``main.ejecutar_operacion``, este script inyecta a
propósito una división por cero (``ZeroDivisionError``), que simula un
defecto de programación, entre operaciones normales. Se comprueba que:

1. el error se captura y se clasifica como FALLO (no detiene el programa);
2. se registra en el log con nivel ERROR y la traza completa (traceback);
3. las operaciones posteriores se ejecutan con normalidad.

El log de esta evidencia se escribe en ``logs/evidencia_error_inesperado.log``
para no mezclarse con el de la simulación principal.
"""

import sys  # Código de salida del script.
from pathlib import Path  # Rutas independientes del sistema operativo.

# Se reutiliza exactamente la misma función que usa la simulación principal.
from main import Operacion, ejecutar_operacion
from software_fj import GestorSistema, configurar_registro
from software_fj.registro import obtener_logger

# Archivo de log propio de esta evidencia, dentro de 03_Desarrollo/logs/.
RUTA_LOG = Path(__file__).resolve().parent / "logs" / "evidencia_error_inesperado.log"


def calcular_ocupacion_promedio(total_horas: float, numero_reservas: int) -> float:
    """Cálculo auxiliar SIN validación previa: falla si ``numero_reservas`` es 0.

    Representa un defecto de programación (no una regla de negocio): por eso
    produce un ``ZeroDivisionError`` nativo de Python y no una excepción
    personalizada del sistema.
    """
    return total_horas / numero_reservas


def main() -> int:
    """Ejecuta la secuencia de evidencia y devuelve 0 si se comportó como se esperaba."""
    # Se borra el log anterior para que el archivo contenga solo esta ejecución.
    RUTA_LOG.unlink(missing_ok=True)
    configurar_registro(RUTA_LOG)
    log = obtener_logger("evidencia")
    log.info("===== Inicio de la evidencia de error inesperado =====")

    gestor = GestorSistema()
    operaciones = [
        # 1: operación normal antes del error.
        Operacion("Registrar cliente válido", lambda: gestor.registrar_cliente(
            nombre="Laura Torres", documento="52123456", correo="laura.torres@correo.com",
            telefono="3201234567"), "EXITO"),
        # 2: error INESPERADO inyectado a propósito (división por cero).
        Operacion("Calcular ocupación promedio con 0 reservas (ZeroDivisionError)",
                  lambda: calcular_ocupacion_promedio(10, len(gestor.reservas)), "FALLO"),
        # 3: error CONTROLADO, para contrastar su registro (WARNING) con el inesperado (ERROR).
        Operacion("Registrar cliente con teléfono inválido (error controlado)", lambda: gestor.registrar_cliente(
            nombre="Pedro Rojas", documento="80123456", correo="pedro@correo.com", telefono="12"), "FALLO"),
        # 4 y 5: operaciones normales DESPUÉS del error: demuestran la continuidad.
        Operacion("Crear servicio de sala después del error", lambda: gestor.registrar_servicio(
            "sala", nombre="Sala Norte", tarifa_hora=60000, capacidad=8), "EXITO"),
        Operacion("Reservar la sala 2 h después del error", lambda: gestor.crear_reserva(
            "52123456", gestor.servicios[0].id, 2, asistentes=5), "EXITO"),
    ]

    # Misma lógica de main.py: cada operación aislada en try/except/else/finally.
    resultados = [ejecutar_operacion(n, op, log) for n, op in enumerate(operaciones, start=1)]

    print("=" * 100)
    print("EVIDENCIA - MANEJO DE ERROR INESPERADO (ZeroDivisionError)")
    print("=" * 100)
    for r in resultados:
        marca = "OK " if r.coincide else "!! "
        print(f"{marca}{r.numero:02d}. [{r.obtenido:5}] {r.descripcion}")
        print(f"        -> {r.detalle}")

    # Comprobaciones explícitas sobre el archivo de log generado.
    for manejador in log.parent.handlers:
        manejador.flush()  # Asegura que todo esté escrito en disco antes de leerlo.
    contenido = RUTA_LOG.read_text(encoding="utf-8")
    hay_error = "ERROR    | software_fj.evidencia | Error inesperado en la operación 2" in contenido
    hay_traza = "Traceback (most recent call last)" in contenido and "ZeroDivisionError" in contenido
    continuo = resultados[3].obtenido == "EXITO" and resultados[4].obtenido == "EXITO"
    coinciden = sum(r.coincide for r in resultados)

    print("-" * 100)
    print(f"Resultados que coinciden con lo esperado: {coinciden}/{len(resultados)}")
    print(f"Log contiene línea ERROR de la operación 2: {'SI' if hay_error else 'NO'}")
    print(f"Log contiene la traza (traceback) del ZeroDivisionError: {'SI' if hay_traza else 'NO'}")
    print(f"Operaciones 4 y 5 ejecutadas con éxito después del error: {'SI' if continuo else 'NO'}")
    print("Log de esta evidencia: logs/evidencia_error_inesperado.log")
    print("La aplicación terminó sin interrupciones.")
    log.info("===== Fin de la evidencia (%d/%d coinciden) =====", coinciden, len(resultados))

    # Código 0 solo si todas las comprobaciones se cumplen.
    return 0 if (coinciden == len(resultados) and hay_error and hay_traza and continuo) else 1


# Solo se ejecuta al lanzar el script directamente.
if __name__ == "__main__":
    sys.exit(main())
