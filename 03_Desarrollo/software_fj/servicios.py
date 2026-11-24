"""
Jerarquía de servicios de Software FJ.

* ``Servicio`` (abstracta): datos y comportamiento común a todo servicio.
* ``ReservaSala``, ``AlquilerEquipo``, ``Asesoria``: servicios
  especializados que **sobrescriben** ``calcular_costo``, ``describir`` y
  ``validar_parametros`` (polimorfismo: el sistema los usa a todos a
  través de la misma interfaz sin preguntar de qué tipo son).

Sobrecarga en Python
--------------------
Python no permite declarar varios métodos con el mismo nombre y distinta
firma (el último reemplaza al anterior). Las variantes del cálculo de
costos se implementan con los dos mecanismos idiomáticos del lenguaje:

1. **Parámetros opcionales**: ``calcular_costo(duracion)``,
   ``calcular_costo(duracion, impuesto)``,
   ``calcular_costo(duracion, impuesto, descuento)``,
   ``calcular_costo(duracion, descuento=...)``.
2. **Despacho por tipo** con ``functools.singledispatchmethod``: el
   descuento puede ser un porcentaje (``float``/``int``), un código de
   promoción (``str``) o ``None``; se ejecuta una implementación distinta
   según el tipo del argumento.
"""

from abc import abstractmethod  # Decorador para métodos que las subclases deben implementar.
from functools import singledispatchmethod  # Sobrecarga por tipo del primer argumento.
import math  # Verificación de resultados finitos.

from .entidad import EntidadBase
from .excepciones import (
    CalculoInconsistenteError,
    ServicioNoDisponibleError,
    ValidacionError,
)
from .validaciones import validar_entero, validar_numero, validar_texto

# IVA general vigente en Colombia, usado como impuesto por defecto al procesar reservas.
IVA = 0.19
# Descuento máximo permitido por política comercial (50 %). Más que eso es un cálculo inconsistente.
DESCUENTO_MAXIMO = 0.50
# Códigos de promoción válidos y su porcentaje de descuento.
CODIGOS_PROMOCION = {"BIENVENIDA10": 0.10, "EMPRESA15": 0.15, "UNAD20": 0.20}


class Servicio(EntidadBase):
    """Servicio genérico ofrecido por Software FJ (clase abstracta)."""

    # IDs de servicio: SRV-0001...
    PREFIJO_ID = "SRV"
    # Nombre legible del tipo; cada subclase lo redefine.
    TIPO = "Servicio"

    def __init__(self, nombre: str, tarifa_hora: float) -> None:
        # Nombre comercial del servicio (validado).
        self.__nombre = validar_texto(nombre, "nombre del servicio", minimo=3, maximo=80)
        # Tarifa por hora: al menos 1 peso y máximo 10 millones COP/h.
        self.__tarifa_hora = validar_numero(tarifa_hora, "tarifa_hora", minimo=1, maximo=10_000_000)
        # Todo servicio nace disponible; puede desactivarse por mantenimiento.
        self.__disponible = True
        # ID y fecha de creación heredados (al final: solo servicios válidos reciben ID).
        super().__init__()

    # ---------------------------------------------------------- propiedades
    # Propiedades de solo lectura: nombre y tarifa no cambian tras la creación,
    # y la disponibilidad solo cambia mediante activar()/desactivar().
    @property
    def nombre(self) -> str:
        """Nombre comercial del servicio."""
        return self.__nombre

    @property
    def tarifa_hora(self) -> float:
        """Tarifa base por hora en pesos colombianos."""
        return self.__tarifa_hora

    @property
    def disponible(self) -> bool:
        """True si el servicio acepta nuevas reservas."""
        return self.__disponible

    # ------------------------------------------------- gestión de disponibilidad
    def activar(self) -> None:
        """Marca el servicio como disponible."""
        self.__disponible = True

    def desactivar(self) -> None:
        """Marca el servicio como no disponible (mantenimiento, fuera de servicio)."""
        self.__disponible = False

    def verificar_disponibilidad(self, **opciones) -> None:
        """Lanza ``ServicioNoDisponibleError`` si el servicio no puede reservarse."""
        # **opciones no se usa aquí, pero mantiene la misma firma que la versión
        # sobrescrita de AlquilerEquipo (que sí necesita la cantidad): polimorfismo.
        if not self.__disponible:
            raise ServicioNoDisponibleError(f"El servicio '{self.nombre}' ({self.id}) no está disponible.",
                                            detalle={"servicio": self.id})

    def ocupar(self, **opciones) -> None:
        """Gancho que se ejecuta al confirmar una reserva. Por defecto no hace nada."""

    def liberar(self, **opciones) -> None:
        """Gancho que se ejecuta al cancelar una reserva confirmada. Por defecto no hace nada."""

    # ---------------------------------------------- métodos a sobrescribir
    # @abstractmethod obliga a cada subclase a implementarlos; si falta alguno,
    # Python impide instanciar la subclase (TypeError al crear el objeto).
    @abstractmethod
    def validar_parametros(self, duracion: float, **opciones) -> float:
        """Valida la duración y opciones propias del servicio; devuelve la duración normalizada."""

    @abstractmethod
    def calcular_costo(self, duracion: float, impuesto: float = 0.0, descuento=None, **opciones) -> float:
        """Calcula el costo del servicio para ``duracion`` horas (variantes por parámetros opcionales)."""

    def validar(self) -> None:
        """Verifica la coherencia del propio servicio."""
        # Implementa el método abstracto de EntidadBase (verificación defensiva).
        if self.__tarifa_hora <= 0:
            raise ValidacionError("La tarifa del servicio debe ser positiva.", detalle={"servicio": self.id})

    # ------------------------------------------- sobrecarga por tipo: descuento
    @singledispatchmethod
    def resolver_descuento(self, descuento) -> float:
        """Convierte el argumento ``descuento`` en una fracción entre 0 y 1.

        Implementación por defecto: tipos no soportados.
        """
        # singledispatchmethod elige la implementación según el tipo del argumento
        # "descuento"; esta versión base solo se ejecuta si ningún tipo registrado coincide
        # (por ejemplo, una lista).
        raise CalculoInconsistenteError(
            f"Tipo de descuento no soportado: {type(descuento).__name__}.",
            detalle={"descuento": repr(descuento)},
        )

    # Cada variante se registra con el tipo que atiende; el nombre "_" indica que la
    # función no se llama directamente, sino a través de resolver_descuento.
    @resolver_descuento.register(type(None))
    def _(self, descuento) -> float:
        # Variante sin descuento.
        return 0.0

    @resolver_descuento.register(int)
    @resolver_descuento.register(float)
    def _(self, descuento: float) -> float:
        # Variante porcentaje: se acepta 0.15 (fracción) o 15 (porcentaje entero).
        if isinstance(descuento, bool):
            # True/False no son descuentos válidos aunque bool herede de int.
            raise CalculoInconsistenteError("El descuento no puede ser booleano.")
        # Un valor mayor que 1 se interpreta como porcentaje (15 -> 0.15). Los rangos
        # inválidos (negativos, > 50 %) se rechazan después, en _aplicar_ajustes.
        fraccion = descuento / 100 if descuento > 1 else float(descuento)
        return fraccion

    @resolver_descuento.register
    def _(self, descuento: str) -> float:
        # Variante código de promoción: se busca en la tabla de códigos.
        # Se normaliza para aceptar "unad20" o " UNAD20 " igual que "UNAD20".
        codigo = descuento.strip().upper()
        if codigo not in CODIGOS_PROMOCION:
            raise CalculoInconsistenteError(f"Código de promoción inválido: '{descuento}'.",
                                            detalle={"codigo": descuento})
        return CODIGOS_PROMOCION[codigo]

    # ------------------------------------------- lógica común de ajustes
    def _aplicar_ajustes(self, subtotal: float, impuesto: float, descuento) -> float:
        """Aplica descuento e impuesto a ``subtotal`` y verifica la coherencia del resultado."""
        try:
            # El impuesto debe ser una fracción entre 0 y 1 (0.19 = 19 %).
            tasa_impuesto = validar_numero(impuesto, "impuesto", minimo=0, maximo=1)
        except ValidacionError as error:
            # Encadenamiento: un impuesto inválido hace inconsistente el cálculo.
            raise CalculoInconsistenteError(f"Impuesto inválido: {impuesto!r}.") from error

        # Despacho por tipo (sobrecarga) para interpretar el descuento.
        tasa_descuento = self.resolver_descuento(descuento)
        # Regla de negocio: descuento entre 0 % y 50 %.
        if not 0 <= tasa_descuento <= DESCUENTO_MAXIMO:
            raise CalculoInconsistenteError(
                f"Descuento fuera de política ({tasa_descuento:.0%}); máximo {DESCUENTO_MAXIMO:.0%}.",
                detalle={"descuento": tasa_descuento},
            )

        # Fórmula: primero se descuenta y luego se aplica el impuesto sobre el valor neto.
        total = subtotal * (1 - tasa_descuento) * (1 + tasa_impuesto)
        # Verificación defensiva del resultado (no negativo, finito y no nulo).
        if not math.isfinite(total) or total <= 0:
            raise CalculoInconsistenteError(f"Resultado de costo inconsistente: {total}.",
                                            detalle={"subtotal": subtotal, "total": total})
        # Redondeo a 2 decimales (centavos).
        return round(total, 2)

    def __str__(self) -> str:
        # print(servicio) muestra la descripción polimórfica de la subclase concreta.
        return self.describir()


class ReservaSala(Servicio):
    """Reserva de salas de reuniones o capacitación."""

    # Redefine el atributo de clase TIPO heredado de Servicio.
    TIPO = "Reserva de sala"
    # Límites de duración en horas para una reserva de sala.
    DURACION_MIN, DURACION_MAX = 1, 12
    # Recargo porcentual si la sala incluye equipo audiovisual.
    RECARGO_AUDIOVISUAL = 0.15

    def __init__(self, nombre: str, tarifa_hora: float, capacidad: int, incluye_audiovisual: bool = False) -> None:
        # Capacidad máxima de personas en la sala (entero entre 1 y 500).
        self.__capacidad = validar_entero(capacidad, "capacidad", minimo=1, maximo=500)
        # Se exige un booleano real para evitar valores ambiguos como "si" o 1.
        if not isinstance(incluye_audiovisual, bool):
            raise ValidacionError("'incluye_audiovisual' debe ser True o False.")
        self.__incluye_audiovisual = incluye_audiovisual
        # Validación de los datos comunes (nombre, tarifa) y asignación de ID en la clase padre.
        super().__init__(nombre, tarifa_hora)

    @property
    def capacidad(self) -> int:
        """Número máximo de asistentes."""
        return self.__capacidad

    def validar_parametros(self, duracion: float, **opciones) -> float:
        """Sobrescrito: duración 1-12 h y asistentes dentro de la capacidad."""
        # Los límites se leen de la clase, así cada subclase define los suyos.
        horas = validar_numero(duracion, "duracion", minimo=self.DURACION_MIN, maximo=self.DURACION_MAX)
        # Número de asistentes (opcional, por defecto 1).
        asistentes = validar_entero(opciones.get("asistentes", 1), "asistentes", minimo=1)
        if asistentes > self.__capacidad:
            raise ValidacionError(
                f"La sala admite {self.__capacidad} personas; se solicitaron {asistentes}.",
                detalle={"capacidad": self.__capacidad, "asistentes": asistentes},
            )
        return horas

    def calcular_costo(self, duracion: float, impuesto: float = 0.0, descuento=None, **opciones) -> float:
        """Sobrescrito: tarifa × horas, con recargo si hay audiovisual."""
        # Se revalida aquí porque calcular_costo también puede llamarse directamente, sin Reserva.
        horas = self.validar_parametros(duracion, **opciones)
        subtotal = self.tarifa_hora * horas
        if self.__incluye_audiovisual:
            # Recargo del 15 %: el subtotal se multiplica por 1,15.
            subtotal *= 1 + self.RECARGO_AUDIOVISUAL
        # Impuesto y descuento se aplican con la lógica común heredada de Servicio.
        return self._aplicar_ajustes(subtotal, impuesto, descuento)

    def describir(self) -> str:
        """Sobrescrito: descripción propia de una sala."""
        # :,.0f muestra la tarifa con separador de miles y sin decimales.
        extra = "con audiovisual" if self.__incluye_audiovisual else "sin audiovisual"
        return (f"[{self.id}] {self.TIPO}: {self.nombre} - capacidad {self.__capacidad} personas, "
                f"{extra}, ${self.tarifa_hora:,.0f}/h")


class AlquilerEquipo(Servicio):
    """Alquiler de equipos tecnológicos (portátiles, proyectores, etc.)."""

    TIPO = "Alquiler de equipo"
    # De 1 hora hasta 3 días (72 h) por alquiler.
    DURACION_MIN, DURACION_MAX = 1, 72
    # Tipos de equipo que la empresa alquila.
    TIPOS_EQUIPO = {"portatil", "proyector", "camara", "impresora", "tablet"}

    def __init__(self, nombre: str, tarifa_hora: float, tipo_equipo: str, unidades: int) -> None:
        # El tipo de equipo se normaliza a minúsculas y debe estar en el catálogo.
        tipo = validar_texto(tipo_equipo, "tipo_equipo").lower()
        if tipo not in self.TIPOS_EQUIPO:
            raise ValidacionError(f"Tipo de equipo no ofrecido: '{tipo_equipo}'.",
                                  detalle={"permitidos": sorted(self.TIPOS_EQUIPO)})
        self.__tipo_equipo = tipo
        # Inventario: número de unidades disponibles para alquilar (0 a 1000).
        self.__unidades = validar_entero(unidades, "unidades", minimo=0, maximo=1000)
        # Validación de datos comunes y asignación de ID en la clase padre.
        super().__init__(nombre, tarifa_hora)

    @property
    def unidades(self) -> int:
        """Unidades disponibles en este momento (cambia al confirmar o cancelar)."""
        return self.__unidades

    @staticmethod
    def _cantidad(opciones: dict) -> int:
        """Obtiene y valida la cantidad de equipos solicitada (1 por defecto)."""
        # @staticmethod: no usa self; centraliza la regla para los cinco métodos que la necesitan.
        return validar_entero(opciones.get("cantidad", 1), "cantidad", minimo=1)

    def verificar_disponibilidad(self, **opciones) -> None:
        """Sobrescrito: además del estado activo, verifica que haya unidades suficientes."""
        # Primero la verificación común de la clase padre (servicio activo).
        super().verificar_disponibilidad()
        # Luego la regla propia: stock suficiente para la cantidad pedida.
        cantidad = self._cantidad(opciones)
        if cantidad > self.__unidades:
            raise ServicioNoDisponibleError(
                f"Solo hay {self.__unidades} unidad(es) de '{self.nombre}'; se pidieron {cantidad}.",
                detalle={"disponibles": self.__unidades, "solicitadas": cantidad},
            )

    def ocupar(self, **opciones) -> None:
        """Sobrescrito: descuenta del inventario las unidades reservadas."""
        # Se revalida el stock justo antes de descontar (otra reserva pudo ocuparlo).
        self.verificar_disponibilidad(**opciones)
        # Solo se descuenta si la verificación anterior no lanzó excepción.
        self.__unidades -= self._cantidad(opciones)

    def liberar(self, **opciones) -> None:
        """Sobrescrito: devuelve al inventario las unidades de una reserva cancelada."""
        # Reserva.cancelar solo llama a liberar() si la reserva estaba CONFIRMADA,
        # así que nunca se devuelven unidades que no se hayan descontado.
        self.__unidades += self._cantidad(opciones)

    def validar_parametros(self, duracion: float, **opciones) -> float:
        """Sobrescrito: duración 1-72 h y cantidad de equipos ≥ 1."""
        horas = validar_numero(duracion, "duracion", minimo=self.DURACION_MIN, maximo=self.DURACION_MAX)
        # Se invoca solo por su efecto: lanza ValidacionError si la cantidad es inválida.
        self._cantidad(opciones)
        return horas

    def calcular_costo(self, duracion: float, impuesto: float = 0.0, descuento=None, **opciones) -> float:
        """Sobrescrito: tarifa × horas × cantidad de equipos."""
        horas = self.validar_parametros(duracion, **opciones)
        # La tarifa es por unidad, por eso se multiplica por la cantidad alquilada.
        subtotal = self.tarifa_hora * horas * self._cantidad(opciones)
        return self._aplicar_ajustes(subtotal, impuesto, descuento)

    def describir(self) -> str:
        """Sobrescrito: incluye el tipo de equipo y el inventario actual."""
        return (f"[{self.id}] {self.TIPO}: {self.nombre} ({self.__tipo_equipo}) - "
                f"{self.__unidades} unidad(es) disponibles, ${self.tarifa_hora:,.0f}/h por unidad")


class Asesoria(Servicio):
    """Asesoría especializada prestada por un consultor."""

    TIPO = "Asesoría especializada"
    # De media hora a una jornada laboral (8 h).
    DURACION_MIN, DURACION_MAX = 0.5, 8
    # Especialidades ofrecidas por Software FJ.
    ESPECIALIDADES = {"desarrollo de software", "bases de datos", "ciberseguridad", "nube", "analitica de datos"}
    # Multiplicador de tarifa según el nivel del asesor.
    FACTOR_NIVEL = {"junior": 1.0, "senior": 1.5, "experto": 2.0}

    def __init__(self, nombre: str, tarifa_hora: float, especialidad: str, nivel: str = "senior") -> None:
        # La especialidad debe pertenecer al catálogo de la empresa.
        esp = validar_texto(especialidad, "especialidad").lower()
        if esp not in self.ESPECIALIDADES:
            raise ValidacionError(f"Especialidad no ofrecida: '{especialidad}'.",
                                  detalle={"permitidas": sorted(self.ESPECIALIDADES)})
        # El nivel determina el multiplicador de la tarifa.
        niv = validar_texto(nivel, "nivel").lower()
        if niv not in self.FACTOR_NIVEL:
            raise ValidacionError(f"Nivel de asesor inválido: '{nivel}'.",
                                  detalle={"permitidos": sorted(self.FACTOR_NIVEL)})
        # Se asignan solo después de validar ambos datos.
        self.__especialidad = esp
        self.__nivel = niv
        # Validación de datos comunes y asignación de ID en la clase padre.
        super().__init__(nombre, tarifa_hora)

    def validar_parametros(self, duracion: float, **opciones) -> float:
        """Sobrescrito: 0,5-8 h y en bloques de media hora."""
        horas = validar_numero(duracion, "duracion", minimo=self.DURACION_MIN, maximo=self.DURACION_MAX)
        # (horas * 2) debe ser entero: 1.5 es válido, 1.2 no.
        if not (horas * 2).is_integer():
            raise ValidacionError("Las asesorías se reservan en bloques de 30 minutos.",
                                  detalle={"duracion": horas})
        return horas

    def calcular_costo(self, duracion: float, impuesto: float = 0.0, descuento=None, **opciones) -> float:
        """Sobrescrito: tarifa × horas × factor del nivel del asesor."""
        horas = self.validar_parametros(duracion, **opciones)
        # El nivel ya se validó en el constructor, así que la clave siempre existe.
        subtotal = self.tarifa_hora * horas * self.FACTOR_NIVEL[self.__nivel]
        return self._aplicar_ajustes(subtotal, impuesto, descuento)

    def describir(self) -> str:
        """Sobrescrito: incluye especialidad y nivel del asesor."""
        return (f"[{self.id}] {self.TIPO}: {self.nombre} - {self.__especialidad}, nivel {self.__nivel}, "
                f"${self.tarifa_hora:,.0f}/h base")
