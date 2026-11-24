# Software FJ – Sistema Integral de Gestión de Clientes, Servicios y Reservas

Proyecto de la **Fase 4 – Prácticas simuladas** del curso **Programación (213023)** de la UNAD.
Ejercicio 1 del *Anexo 3 – Problema a desarrollar Fase 4*.

* **Grupo de referencia:** 213023_475
* **Modalidad:** desarrollo individual, autorizado expresamente por la tutora del curso.
* **Lenguaje:** Python 3, solo biblioteca estándar; sin bases de datos ni dependencias externas.
* **Versiones probadas:** Python **3.12.14** y Python **3.10.11** en Windows 11 (pruebas, simulación y evidencia de error inesperado con resultados idénticos). No se probaron otras versiones.

---

## 1. Requisitos cubiertos

Aplicación orientada a objetos, sin base de datos, que gestiona clientes, servicios (salas, equipos, asesorías) y reservas, con manejo avanzado de excepciones y registro de eventos/errores en archivo. La matriz completa requisito → implementación → evidencia está en [`02_Planificacion/analisis_y_trazabilidad.md`](02_Planificacion/analisis_y_trazabilidad.md).

| Requisito del Anexo 3 | Dónde |
|-----------------------|-------|
| Clase abstracta de entidades generales | `software_fj/entidad.py` → `EntidadBase` |
| Cliente con validaciones y encapsulación | `software_fj/cliente.py` → `Cliente` |
| Clase abstracta Servicio + 3 servicios | `software_fj/servicios.py` → `Servicio`, `ReservaSala`, `AlquilerEquipo`, `Asesoria` |
| Reserva con confirmación, cancelación y procesamiento | `software_fj/reserva.py` → `Reserva`, `EstadoReserva` |
| Métodos sobrecargados (impuestos, descuentos, opcionales) | `Servicio.calcular_costo(...)`, `Servicio.resolver_descuento` |
| Listas internas | `software_fj/sistema.py` → `GestorSistema` |
| Excepciones personalizadas | `software_fj/excepciones.py` |
| try/except, try/except/else, try/except/finally, encadenamiento | `validaciones.py`, `sistema.py`, `reserva.py`, `main.py` |
| Archivo de logs | `software_fj/registro.py` → `03_Desarrollo/logs/software_fj.log` |
| ≥ 10 operaciones simuladas | `03_Desarrollo/main.py` (30 operaciones) |
| Continuidad ante errores no previstos | `03_Desarrollo/evidencia_error_inesperado.py` (`ZeroDivisionError`) |

## 2. Estructura del repositorio

```
├── .gitignore
├── README.md
├── 02_Planificacion/analisis_y_trazabilidad.md   # Requisitos, ambigüedades, UML, trazabilidad
├── 03_Desarrollo/                                # Código fuente
│   ├── main.py                                   # Simulación de 30 operaciones
│   ├── evidencia_error_inesperado.py             # Demostración de un error no previsto (ZeroDivisionError)
│   ├── software_fj/                              # Paquete del dominio
│   │   ├── __init__.py
│   │   ├── excepciones.py   registro.py   validaciones.py
│   │   ├── entidad.py       cliente.py    servicios.py
│   │   ├── reserva.py       sistema.py
│   └── tests/test_software_fj.py                 # 31 pruebas unitarias
├── 04_Pruebas/
│   ├── resultado_pruebas_unitarias.txt           # Salida de las pruebas con Python 3.12.14
│   └── resultado_pruebas_python310.txt           # Salida de las pruebas con Python 3.10.11
└── 05_Evidencias/
    ├── salida_simulacion.txt                     # Consola de main.py
    ├── software_fj.log                           # Log de main.py
    ├── salida_error_inesperado.txt               # Consola de evidencia_error_inesperado.py
    └── evidencia_error_inesperado.log            # Log con la línea ERROR y la traza
```

El informe en PDF se entrega por el campus virtual y no se incluye en el repositorio.

## 3. Arquitectura

```
main.py  (aplicación: guion de operaciones, captura final de errores)
   │
   ▼
GestorSistema  (fachada: listas internas, búsquedas, registro OK/FALLÓ en log)
   │
   ├── Cliente ─────────┐
   ├── Servicio (ABC) ──┼──► EntidadBase (ABC)
   │     ├─ ReservaSala │
   │     ├─ AlquilerEquipo
   │     └─ Asesoria    │
   └── Reserva ─────────┘   (máquina de estados)

Transversales: excepciones.py · validaciones.py · registro.py
```

### Decisiones técnicas

1. **Excepción raíz `SoftwareFJError`** con código (`SFJ-100`, `SFJ-300`…): la aplicación captura en un solo `except` todos los errores de negocio y deja un `except Exception` aparte como red de seguridad para fallos no previstos, que se registran con traza completa.
2. **Validación en el constructor y en los setters**: ningún objeto queda en estado inválido. El ID (`CLI-0001`, `SRV-0001`, `RES-0001`) se asigna solo después de validar, por lo que los intentos fallidos no generan huecos en la numeración.
3. **Sobrecarga en Python**: el lenguaje no admite varios métodos con el mismo nombre y distinta firma. Se usan los mecanismos idiomáticos:
   * parámetros opcionales: `calcular_costo(duracion)`, `calcular_costo(duracion, impuesto)`, `calcular_costo(duracion, impuesto, descuento)`, `calcular_costo(duracion, cantidad=2)`;
   * despacho por tipo con `functools.singledispatchmethod`: `resolver_descuento(None)`, `resolver_descuento(0.15)` / `(15)`, `resolver_descuento("UNAD20")`.
4. **Máquina de estados en `Reserva`**: `PENDIENTE → CONFIRMADA → PROCESADA`, y `PENDIENTE/CONFIRMADA → CANCELADA`. Cualquier otra transición lanza `OperacionNoPermitidaError`.
5. **`Reserva.procesar` usa try/except/else/finally**: si el cálculo falla, la reserva sigue `CONFIRMADA` (el `else` no se ejecuta) y puede reintentarse; el `finally` siempre registra el intento.
6. **Encadenamiento (`raise … from error`)**: los errores técnicos (`ValueError`, `TypeError`) y de validación se transforman en errores de negocio conservando la causa en `__cause__`, que también se escribe en el log.
7. **Protección de datos personales**: el documento del cliente se muestra enmascarado (`******6789`) en descripciones y logs.
8. **Supuestos de negocio** (no definidos en el Anexo, configurables como constantes): IVA 19 %, descuento máximo 50 %, códigos promocionales `BIENVENIDA10`, `EMPRESA15`, `UNAD20`; sala 1–12 h; equipos 1–72 h; asesorías 0,5–8 h en bloques de 30 min; factor por nivel de asesor (junior 1,0; senior 1,5; experto 2,0).

### Fórmulas de costo

| Servicio | Subtotal |
|----------|----------|
| `ReservaSala` | tarifa × horas × (1,15 si incluye audiovisual) |
| `AlquilerEquipo` | tarifa × horas × cantidad |
| `Asesoria` | tarifa × horas × factor de nivel |

Total = subtotal × (1 − descuento) × (1 + impuesto), redondeado a 2 decimales. Se valida que el impuesto esté entre 0 y 1, el descuento entre 0 y 50 % y que el total sea finito y positivo.

## 4. Instalación desde cero

1. Instalar Python desde <https://www.python.org/downloads/> (en Windows, marcar *Add python.exe to PATH*). Versiones verificadas: **3.12.14** y **3.10.11**. El código usa sintaxis disponible desde Python 3.10 (por ejemplo, `str | None`), por lo que no funciona en versiones anteriores.
2. Verificar la instalación:
   ```powershell
   python --version
   ```
3. Obtener el proyecto (clonar el repositorio o descomprimir la carpeta) y entrar a la carpeta de código:
   ```powershell
   cd 03_Desarrollo
   ```

No hay dependencias que instalar: todo pertenece a la biblioteca estándar.

## 5. Ejecución

```powershell
python main.py
```

Muestra las 30 operaciones con su resultado (`EXITO` / `FALLO` controlado), un resumen y la ruta del log. Termina con código 0 si cada operación se comportó como se esperaba. El log se acumula en `03_Desarrollo/logs/software_fj.log` (borrarlo para empezar desde cero).

Ejemplo de líneas del log:

```
INFO     | software_fj.sistema | Registrar cliente OK -> CLI-0001
WARNING  | software_fj.sistema | Registrar cliente FALLÓ: [SFJ-100] El correo electrónico no tiene un formato válido.
WARNING  | software_fj.sistema | Crear reserva (SRV-0001) FALLÓ: [SFJ-500] Parámetros de reserva inválidos ... | causa: ValidacionError: ...
INFO     | software_fj.reserva | Intento de procesamiento de RES-0002 finalizado (exito=False)
```

## 6. Operaciones simuladas

| # | Operación | Esperado | Excepción / resultado |
|---|-----------|----------|------------------------|
| 01–02 | Registrar dos clientes válidos | Éxito | `CLI-0001`, `CLI-0002` |
| 03 | Cliente con correo inválido | Fallo | `ValidacionError` |
| 04 | Cliente sin documento | Fallo | `ParametroFaltanteError` |
| 05 | Documento duplicado | Fallo | `OperacionNoPermitidaError` |
| 06–08 | Crear sala, equipos y asesoría | Éxito | `SRV-0001`…`SRV-0003` |
| 09 | Servicio con tarifa negativa | Fallo | `ValidacionError` |
| 10 | Servicio sin capacidad | Fallo | `ParametroFaltanteError` ← `TypeError` |
| 11 | Tipo de servicio inexistente | Fallo | `ValidacionError` |
| 12–14 | Reservar, confirmar y procesar sala (IVA + código promo) | Éxito | Total $295.596 |
| 15–16 | Reservar y confirmar 2 portátiles | Éxito | Inventario 3 → 1 |
| 17 | Pedir 2 portátiles más | Fallo | `ServicioNoDisponibleError` |
| 18 | Sala sobre su capacidad | Fallo | `ReservaInvalidaError` ← `ValidacionError` |
| 19 | Asesoría de 1,2 h | Fallo | `ReservaInvalidaError` ← `ValidacionError` |
| 20 | Duración "dos horas" | Fallo | `ReservaInvalidaError` ← `ValidacionError` ← `ValueError` |
| 21 | Cliente inexistente | Fallo | `EntidadNoEncontradaError` |
| 22–23 | Desactivar asesoría y reservarla | Éxito / Fallo | `ServicioNoDisponibleError` |
| 24 | Cancelar reserva procesada | Fallo | `OperacionNoPermitidaError` |
| 25 | Descuento del 80 % | Fallo | `ReservaInvalidaError` ← `CalculoInconsistenteError` |
| 26 | Impuesto 150 % | Fallo | `ReservaInvalidaError` ← `CalculoInconsistenteError` |
| 27 | Cancelar reserva de portátiles | Éxito | Inventario 1 → 3 |
| 28 | Procesar reserva cancelada | Fallo | `OperacionNoPermitidaError` |
| 29–30 | Reactivar asesoría, reservar, confirmar y procesar | Éxito | Total $306.000 |

Resultado de la última ejecución: **30/30 operaciones con el comportamiento esperado (14 éxitos, 16 fallos controlados)**; ver `05_Evidencias/salida_simulacion.txt` y `05_Evidencias/software_fj.log`.

### Evidencia de un error inesperado

Las 30 operaciones solo provocan errores **controlados** (subclases de `SoftwareFJError`), que se registran como WARNING. Para demostrar la red de seguridad `except Exception` de `main.ejecutar_operacion`, el script `evidencia_error_inesperado.py` inyecta a propósito una división por cero (`ZeroDivisionError`), que simula un defecto de programación, entre operaciones normales:

```powershell
cd 03_Desarrollo
python evidencia_error_inesperado.py
```

| # | Operación | Resultado real |
|---|-----------|----------------|
| 1 | Registrar cliente válido | Éxito |
| 2 | División por cero (error inesperado) | Fallo capturado: `ERROR INESPERADO ZeroDivisionError: division by zero` |
| 3 | Cliente con teléfono inválido (error controlado, para contrastar) | Fallo controlado: `ValidacionError` |
| 4–5 | Crear un servicio y reservarlo después del error | Éxito: la aplicación continuó |

El script verifica por sí mismo que el log contiene la línea `ERROR … Error inesperado en la operación 2` con la traza completa (*traceback*) y que las operaciones 4 y 5 terminaron con éxito; termina con código 0 solo si todo eso se cumple. Resultado: **5/5**. Ver `05_Evidencias/salida_error_inesperado.txt` y `05_Evidencias/evidencia_error_inesperado.log`. En esta copia del log, la ruta absoluta del equipo donde se ejecutó se reemplazó por `<repositorio>` para no publicar datos de la carpeta personal; el resto del contenido no se modificó.

## 7. Pruebas

```powershell
cd 03_Desarrollo
python -m unittest discover -s tests -v
```

31 pruebas unitarias con `unittest` (biblioteca estándar) que cubren: clases abstractas no instanciables, herencia, validaciones de cliente, encapsulación, polimorfismo de costos, variantes de cálculo (sobrecarga), descuentos/impuestos inconsistentes, encadenamiento (`__cause__`), máquina de estados, inventario de equipos, listas encapsuladas, registro en log, simulación completa y continuidad ante un error inesperado (`ZeroDivisionError`).
Última ejecución: **31 pruebas, OK** con Python 3.12.14 (`04_Pruebas/resultado_pruebas_unitarias.txt`) y **31 pruebas, OK** con Python 3.10.11 (`04_Pruebas/resultado_pruebas_python310.txt`).

## 8. Defectos corregidos

Los tres defectos se detectaron al **ejecutar la simulación** (`main.py`) y revisar su salida y el log, no mediante las pruebas unitarias. Después de corregir el primero se incorporó la prueba de regresión `test_servicio_invalido_no_consume_id`, para que no vuelva a aparecer sin ser detectado.

| Defecto | Cómo se detectó | Causa | Corrección |
|---------|-----------------|-------|------------|
| Los IDs saltaban (`SRV-0006` para el primer servicio) | Salida de la simulación | El ID se asignaba antes de validar y un contador global era compartido por todas las entidades | Contador por prefijo y llamada a `EntidadBase.__init__` al final de cada constructor, tras validar. Prueba de regresión añadida |
| Mensaje "tarifa debe ser mayor o igual a 0" ante tarifa negativa, aunque 0 tampoco era válido | Salida de la simulación (operación 09) | Límite mínimo mal expresado | Mínimo de tarifa = 1 |
| El log de éxito no indicaba qué entidad se afectó | Revisión del archivo de log | Mensaje genérico | Se agrega el ID o valor devuelto: `Registrar cliente OK -> CLI-0001` |

## 9. Documentación del código

La guía pide documentar el código de manera clara y precisa. Cada módulo, clase y método público tiene una descripción (*docstring*), y las instrucciones con lógica no evidente tienen un comentario técnico que explica **por qué** se hacen (reglas de negocio, orden de validación, encadenamiento, polimorfismo, cálculos de ejemplo), sin repetir lo que el código ya dice. Las líneas autoexplicativas (por ejemplo, un `return` o una asignación directa) no llevan comentario.

## 10. Autoría

Desarrollo individual de Brayan Santiago Benavides Campos, autorizado por la tutora, para el grupo de referencia 213023_475.

**Uso de herramientas de inteligencia artificial.** El código, las pruebas, la documentación y el informe se elaboraron con la asistencia de Claude Code (Anthropic), un asistente de programación con IA. El estudiante definió los requisitos a partir de la guía y el Anexo 3, tomó las decisiones del proyecto, revisó y ejecutó cada etapa, y es responsable del contenido entregado. Por esa asistencia, GitHub muestra a Claude como coautor de uno de los commits.
