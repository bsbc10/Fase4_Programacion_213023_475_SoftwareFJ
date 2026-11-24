"""
Punto de entrada: simulación de operaciones completas del sistema Software FJ.

Ejecutar desde la carpeta ``03_Desarrollo``::

    python main.py

Cada operación se ejecuta dentro de ``ejecutar_operacion``, que usa
**try / except / else / finally** para que ningún error (controlado o
inesperado) detenga la aplicación. Al final se muestra un resumen y se
indica la ruta del archivo de logs.
"""

import sys  # Código de salida del programa.
from dataclasses import dataclass  # Estructura simple para describir cada operación.
from pathlib import Path  # Para mostrar la ruta del log de forma relativa.
from typing import Any, Callable  # Anotaciones: "cualquier valor" y "función invocable".

from software_fj import GestorSistema, SoftwareFJError, configurar_registro
from software_fj.registro import RUTA_LOG_POR_DEFECTO, obtener_logger


# @dataclass genera automáticamente __init__ y __repr__ a partir de los atributos declarados.
@dataclass
class Operacion:
    """Describe una operación simulada y el resultado esperado."""

    descripcion: str  # Texto que se imprime en el reporte.
    accion: Callable[[], Any]  # Función sin argumentos que ejecuta la operación.
    esperado: str  # "EXITO" o "FALLO"


@dataclass
class Resultado:
    """Resultado real de ejecutar una operación."""

    numero: int  # Posición de la operación en el guion (01, 02...).
    descripcion: str
    esperado: str  # Lo que debía ocurrir según el guion.
    obtenido: str  # Lo que realmente ocurrió al ejecutar.
    detalle: str  # Descripción del objeto creado o de la excepción capturada.

    @property
    def coincide(self) -> bool:
        """True si el comportamiento real fue el esperado (éxito o fallo controlado)."""
        return self.esperado == self.obtenido


def ejecutar_operacion(numero: int, operacion: Operacion, log) -> Resultado:
    """Ejecuta una operación sin permitir que un error detenga el programa."""
    # Valores por defecto: si ocurre una excepción, la operación cuenta como FALLO.
    obtenido, detalle = "FALLO", ""
    try:
        valor = operacion.accion()
    except SoftwareFJError as error:
        # Error controlado del negocio: ya quedó registrado por el gestor; se informa y se continúa.
        detalle = f"{type(error).__name__}: {error}"
        # __cause__ existe cuando el error se lanzó con "raise ... from": se muestra la causa original.
        if error.__cause__ is not None:
            detalle += f" (causa: {type(error.__cause__).__name__})"
    except Exception as error:  # noqa: BLE001 - red de seguridad deliberada
        # Error NO previsto: se registra con traza completa (nivel ERROR) y la aplicación sigue.
        # Este except va después del anterior porque Python usa el primer except que coincide.
        log.exception("Error inesperado en la operación %d", numero)
        detalle = f"ERROR INESPERADO {type(error).__name__}: {error}"
    else:
        # Solo se ejecuta si no hubo excepción.
        obtenido = "EXITO"
        # Las entidades se describen a sí mismas (polimorfismo); otros valores (p. ej. un costo) se muestran tal cual.
        detalle = valor.describir() if hasattr(valor, "describir") else f"Resultado: {valor!r}"
    finally:
        # Siempre se ejecuta: deja constancia de que la operación terminó.
        log.info("Operación %02d finalizada", numero)
    return Resultado(numero, operacion.descripcion, operacion.esperado, obtenido, detalle)


def construir_operaciones(gestor: GestorSistema) -> list[Operacion]:
    """Define el guion de la simulación.

    Las operaciones dependen de objetos creados antes (por eso se usan
    funciones ``lambda`` que buscan los IDs en el momento de ejecutarse).
    """
    # Atajos para obtener IDs de servicios/reservas creados en pasos anteriores.
    def srv(indice: int) -> str:
        """ID del servicio en la posición ``indice`` de la lista del gestor."""
        return gestor.servicios[indice].id

    def res(indice: int) -> str:
        """ID de la reserva en la posición ``indice`` de la lista del gestor."""
        return gestor.reservas[indice].id

    # Cada comentario indica la regla o excepción que la operación pone a prueba.
    return [
        # --- Clientes -----------------------------------------------------
        # 01-02: datos válidos; el teléfono "601 555 1234" demuestra la normalización de espacios.
        Operacion("Registrar cliente válido (Ana Gómez)", lambda: gestor.registrar_cliente(
            nombre="Ana María Gómez", documento="1032456789", correo="ana.gomez@correo.com",
            telefono="3104567890"), "EXITO"),
        Operacion("Registrar cliente válido (Carlos Ruiz)", lambda: gestor.registrar_cliente(
            nombre="Carlos Ruiz", documento="79856123", correo="cruiz@empresa.co", telefono="601 555 1234"),
            "EXITO"),
        # 03: correo sin dominio -> ValidacionError (setter de Cliente.correo).
        Operacion("Registrar cliente con correo inválido", lambda: gestor.registrar_cliente(
            nombre="Luis Pérez", documento="11223344", correo="luis.perez@", telefono="3001112233"), "FALLO"),
        # 04: se omite "documento" -> llega None -> ParametroFaltanteError.
        Operacion("Registrar cliente sin documento (parámetro faltante)", lambda: gestor.registrar_cliente(
            nombre="Marta Díaz", correo="marta@correo.com", telefono="3157778899"), "FALLO"),
        # 05: mismo documento que la operación 01 -> OperacionNoPermitidaError.
        Operacion("Registrar cliente con documento duplicado", lambda: gestor.registrar_cliente(
            nombre="Ana Duplicada", documento="1032456789", correo="otra@correo.com", telefono="3100000000"),
            "FALLO"),
        # --- Servicios ----------------------------------------------------
        # 06-08: un servicio de cada subclase (SRV-0001 sala, SRV-0002 equipos, SRV-0003 asesoría).
        Operacion("Crear servicio: sala de juntas", lambda: gestor.registrar_servicio(
            "sala", nombre="Sala Innovación", tarifa_hora=80000, capacidad=12, incluye_audiovisual=True),
            "EXITO"),
        Operacion("Crear servicio: alquiler de portátiles", lambda: gestor.registrar_servicio(
            "equipo", nombre="Portátiles Dell", tarifa_hora=15000, tipo_equipo="portatil", unidades=3), "EXITO"),
        Operacion("Crear servicio: asesoría en ciberseguridad", lambda: gestor.registrar_servicio(
            "asesoria", nombre="Auditoría de seguridad", tarifa_hora=120000, especialidad="ciberseguridad",
            nivel="experto"), "EXITO"),
        # 09: tarifa por debajo del mínimo (1) -> ValidacionError.
        Operacion("Crear servicio con tarifa negativa", lambda: gestor.registrar_servicio(
            "sala", nombre="Sala Barata", tarifa_hora=-5000, capacidad=4), "FALLO"),
        # 10: falta "capacidad" -> TypeError de Python encadenado a ParametroFaltanteError.
        Operacion("Crear servicio con parámetro faltante (sin capacidad)", lambda: gestor.registrar_servicio(
            "sala", nombre="Sala Sin Capacidad", tarifa_hora=50000), "FALLO"),
        # 11: "transporte" no está en la fábrica TIPOS_SERVICIO -> ValidacionError.
        Operacion("Crear servicio de tipo inexistente", lambda: gestor.registrar_servicio(
            "transporte", nombre="Van ejecutiva", tarifa_hora=90000), "FALLO"),
        # --- Reservas exitosas -------------------------------------------
        # 12-14: ciclo completo PENDIENTE -> CONFIRMADA -> PROCESADA.
        # Costo: 80.000 x 3 h x 1,15 (audiovisual) x 0,90 (BIENVENIDA10) x 1,19 (IVA) = 295.596.
        Operacion("Reservar sala 3 h para 8 asistentes", lambda: gestor.crear_reserva(
            "1032456789", srv(0), 3, asistentes=8), "EXITO"),
        Operacion("Confirmar reserva de sala", lambda: gestor.confirmar_reserva(res(0)), "EXITO"),
        Operacion("Procesar reserva de sala (IVA 19 % + código BIENVENIDA10)", lambda: gestor.procesar_reserva(
            res(0), 0.19, "BIENVENIDA10"), "EXITO"),
        # 15-16: al confirmar, el inventario de portátiles baja de 3 a 1.
        Operacion("Reservar 2 portátiles por 24 h", lambda: gestor.crear_reserva(
            "79856123", srv(1), 24, cantidad=2), "EXITO"),
        Operacion("Confirmar reserva de portátiles (descuenta inventario)",
                  lambda: gestor.confirmar_reserva(res(1)), "EXITO"),
        # --- Reservas fallidas -------------------------------------------
        # 17: inventario insuficiente -> ServicioNoDisponibleError.
        Operacion("Reservar 2 portátiles más (solo queda 1)", lambda: gestor.crear_reserva(
            "1032456789", srv(1), 5, cantidad=2), "FALLO"),
        # 18: supera la capacidad -> ValidacionError encadenado a ReservaInvalidaError.
        Operacion("Reservar sala para 20 personas (capacidad 12)", lambda: gestor.crear_reserva(
            "79856123", srv(0), 2, asistentes=20), "FALLO"),
        # 19: regla propia de Asesoria (bloques de 30 min) -> ReservaInvalidaError.
        Operacion("Reservar asesoría de 1,2 h (no es bloque de 30 min)", lambda: gestor.crear_reserva(
            "1032456789", srv(2), 1.2), "FALLO"),
        # 20: cadena doble: ValueError (float) -> ValidacionError -> ReservaInvalidaError.
        Operacion("Reservar con duración no numérica", lambda: gestor.crear_reserva(
            "1032456789", srv(2), "dos horas"), "FALLO"),
        # 21: documento no registrado -> EntidadNoEncontradaError.
        Operacion("Reservar con cliente inexistente", lambda: gestor.crear_reserva(
            "99999999", srv(0), 2), "FALLO"),
        # 22-23: servicio desactivado -> ServicioNoDisponibleError al reservar.
        Operacion("Desactivar asesoría por mantenimiento", lambda: gestor.cambiar_disponibilidad(
            srv(2), False), "EXITO"),
        Operacion("Reservar asesoría no disponible", lambda: gestor.crear_reserva(
            "79856123", srv(2), 2), "FALLO"),
        # --- Operaciones no permitidas y cálculos inconsistentes ----------
        # 24: transición PROCESADA -> CANCELADA no permitida -> OperacionNoPermitidaError.
        Operacion("Cancelar reserva ya procesada", lambda: gestor.cancelar_reserva(res(0)), "FALLO"),
        # 25-26: CalculoInconsistenteError encadenado a ReservaInvalidaError; la reserva sigue CONFIRMADA.
        Operacion("Procesar reserva de portátiles con descuento 80 % (inconsistente)",
                  lambda: gestor.procesar_reserva(res(1), 0.19, 0.80), "FALLO"),
        Operacion("Procesar reserva de portátiles con impuesto inválido", lambda: gestor.procesar_reserva(
            res(1), 1.5), "FALLO"),
        # 27: cancelar una reserva confirmada devuelve las 2 unidades al inventario.
        Operacion("Cancelar reserva de portátiles (libera inventario)", lambda: gestor.cancelar_reserva(
            res(1), "Cambio de fecha del evento"), "EXITO"),
        # 28: CANCELADA -> PROCESADA no permitida -> OperacionNoPermitidaError.
        Operacion("Procesar reserva cancelada", lambda: gestor.procesar_reserva(res(1)), "FALLO"),
        # 29-30: cada lambda ejecuta dos pasos en una tupla y devuelve el segundo ([1]).
        # Costo 30: 120.000 x 1,5 h x 2,0 (experto) x 0,85 (descuento 15) sin IVA = 306.000.
        Operacion("Reactivar asesoría y reservar 1,5 h", lambda: (
            gestor.cambiar_disponibilidad(srv(2), True), gestor.crear_reserva("79856123", srv(2), 1.5))[1],
            "EXITO"),
        Operacion("Confirmar y procesar asesoría (descuento 15 %, sin IVA)", lambda: (
            gestor.confirmar_reserva(res(2)), gestor.procesar_reserva(res(2), 0, 15))[1], "EXITO"),
    ]


def main() -> int:
    """Ejecuta la simulación completa y devuelve el código de salida."""
    # Se configura el archivo de logs antes de cualquier operación.
    configurar_registro()
    app_log = obtener_logger("main")
    app_log.info("===== Inicio de la simulación Software FJ =====")

    # Un gestor nuevo por ejecución: los datos viven solo en memoria durante la simulación.
    gestor = GestorSistema()
    # enumerate(..., start=1) numera las operaciones desde 1; ninguna puede detener el bucle.
    resultados = [ejecutar_operacion(n, op, app_log)
                  for n, op in enumerate(construir_operaciones(gestor), start=1)]

    # --- Reporte en consola ---------------------------------------------
    print("=" * 100)
    print("SIMULACIÓN SOFTWARE FJ - Sistema de Gestión de Clientes, Servicios y Reservas")
    print("=" * 100)
    for r in resultados:
        # "OK" = el resultado coincidió con lo esperado (incluye fallos esperados); "!!" = discrepancia.
        marca = "OK " if r.coincide else "!! "
        print(f"{marca}{r.numero:02d}. [{r.obtenido:5}] {r.descripcion}")
        print(f"        -> {r.detalle}")

    resumen = gestor.resumen()
    # sum() sobre booleanos cuenta cuántos son True.
    exitos = sum(r.obtenido == "EXITO" for r in resultados)
    coincidencias = sum(r.coincide for r in resultados)
    print("-" * 100)
    print(f"Operaciones ejecutadas: {len(resultados)} | exitosas: {exitos} | "
          f"fallidas controladas: {len(resultados) - exitos}")
    print(f"Resultados que coinciden con lo esperado: {coincidencias}/{len(resultados)}")
    print(f"Estado final: {resumen}")
    # Ruta relativa a 03_Desarrollo: no expone la carpeta personal del usuario.
    ruta_relativa = RUTA_LOG_POR_DEFECTO.relative_to(Path(__file__).resolve().parent)
    print(f"Log de eventos y errores: {ruta_relativa.as_posix()}")
    print("La aplicación terminó sin interrupciones.")

    app_log.info("Resumen final: %s", resumen)
    app_log.info("===== Fin de la simulación (%d/%d coinciden) =====", coincidencias, len(resultados))
    # Código 0 si todas las operaciones se comportaron como se esperaba; 1 en caso contrario.
    return 0 if coincidencias == len(resultados) else 1


# Este bloque solo se ejecuta al lanzar "python main.py", no al importar el módulo (p. ej. en las pruebas).
if __name__ == "__main__":
    sys.exit(main())
