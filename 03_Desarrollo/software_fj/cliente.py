"""
Clase ``Cliente``: datos personales encapsulados y validados.

Encapsulación: los atributos son privados (doble guion bajo) y solo se
accede a ellos mediante propiedades. Los *setters* validan cada dato, de
modo que es imposible dejar un cliente en estado inválido, ni al crearlo
ni al modificarlo después.
"""

import re  # Expresiones regulares para validar formatos.

from .entidad import EntidadBase
from .excepciones import ValidacionError
from .validaciones import validar_texto

# Nombre: letras (incluye tildes y ñ), espacios, apóstrofo y guion.
PATRON_NOMBRE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' -]+$")
# Documento de identidad: solo dígitos, entre 6 y 10 caracteres.
PATRON_DOCUMENTO = re.compile(r"^\d{6,10}$")
# Correo electrónico con estructura usuario@dominio.ext (validación básica, sin envío).
PATRON_CORREO = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
# Teléfono: 7 a 10 dígitos (fijo o celular en Colombia).
PATRON_TELEFONO = re.compile(r"^\d{7,10}$")


class Cliente(EntidadBase):
    """Cliente de Software FJ."""

    # Prefijo de los IDs de cliente: CLI-0001, CLI-0002...
    PREFIJO_ID = "CLI"

    def __init__(self, nombre: str, documento: str, correo: str, telefono: str) -> None:
        # Cada asignación pasa por el setter correspondiente, que valida el dato.
        self.nombre = nombre
        self.documento = documento
        self.correo = correo
        self.telefono = telefono
        # Solo con todos los datos válidos se inicializa la parte común (ID y fecha).
        super().__init__()

    # ------------------------------------------------------------------ nombre
    @property
    def nombre(self) -> str:
        """Nombre completo del cliente."""
        return self.__nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        # Texto obligatorio de 3 a 80 caracteres.
        texto = validar_texto(valor, "nombre", minimo=3, maximo=80)
        # Solo letras y separadores permitidos.
        if not PATRON_NOMBRE.match(texto):
            raise ValidacionError("El nombre solo puede contener letras y espacios.", detalle={"valor": texto})
        # Se normalizan espacios múltiples internos a uno solo.
        self.__nombre = " ".join(texto.split())

    # --------------------------------------------------------------- documento
    @property
    def documento(self) -> str:
        """Documento completo (uso interno del sistema)."""
        return self.__documento

    @documento.setter
    def documento(self, valor: str) -> None:
        # Se acepta número o texto, pero se valida como texto de dígitos.
        texto = validar_texto(str(valor) if isinstance(valor, int) else valor, "documento", minimo=6, maximo=10)
        if not PATRON_DOCUMENTO.match(texto):
            raise ValidacionError("El documento debe tener entre 6 y 10 dígitos.", detalle={"valor": texto})
        self.__documento = texto

    @property
    def documento_enmascarado(self) -> str:
        """Documento con los primeros dígitos ocultos para mostrar en pantalla o logs."""
        # Protección de datos personales: solo se exponen los últimos 4 dígitos.
        return "*" * (len(self.__documento) - 4) + self.__documento[-4:]

    # ------------------------------------------------------------------ correo
    @property
    def correo(self) -> str:
        """Correo electrónico en minúsculas."""
        return self.__correo

    @correo.setter
    def correo(self, valor: str) -> None:
        texto = validar_texto(valor, "correo", minimo=6, maximo=120).lower()
        if not PATRON_CORREO.match(texto):
            raise ValidacionError("El correo electrónico no tiene un formato válido.", detalle={"valor": texto})
        self.__correo = texto

    # ---------------------------------------------------------------- teléfono
    @property
    def telefono(self) -> str:
        """Teléfono de contacto."""
        return self.__telefono

    @telefono.setter
    def telefono(self, valor: str) -> None:
        # Se permiten espacios o guiones al escribirlo; se eliminan antes de validar.
        texto = validar_texto(valor, "telefono", minimo=7, maximo=15).replace(" ", "").replace("-", "")
        if not PATRON_TELEFONO.match(texto):
            raise ValidacionError("El teléfono debe tener entre 7 y 10 dígitos.", detalle={"valor": texto})
        self.__telefono = texto

    # ---------------------------------------------------- métodos abstractos
    def validar(self) -> None:
        """Revalida todos los datos (útil si se alteraran por fuera del flujo normal)."""
        # Reasignar ejecuta de nuevo cada setter con sus reglas.
        self.nombre, self.documento = self.__nombre, self.__documento
        self.correo, self.telefono = self.__correo, self.__telefono

    def describir(self) -> str:
        """Descripción segura: no expone el documento completo."""
        return f"Cliente {self.id}: {self.nombre} (doc. {self.documento_enmascarado}, {self.correo})"
