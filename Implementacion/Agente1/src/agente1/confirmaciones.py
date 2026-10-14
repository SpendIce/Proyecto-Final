"""Slice de HU-012: borradores de confirmación y entrega acotada por destino.

Prepara el texto de una confirmación de inscripción y gobierna su ciclo de
vida completo —incluida la aprobación humana y la entrega— con una salida
posible por tipo exacto: `DestinoConfirmacionesFake`, o
`GmailDestinoConfirmaciones` de `gmail_envio.py`, el adapter de `gmail.send`
que sólo puede construirse con una lista de direcciones de prueba activa
(D12). El control se verifica en tiempo de ejecución comparando el tipo
exacto —nunca `isinstance`— así que ni una subclase ni un envoltorio del
fake o del Gmail se cuelan como destino. El candado anterior era más chico:
«sólo el fake». La ampliación actual quedó documentada en el registro de
defectos (DEF-A1-020) con las decisiones D11/D12 que la habilitan.

Por qué el ciclo de vida es el mismo que cuando no había envío real: el
punto de la HU es demostrar que la secuencia de autorización es correcta
—sin aprobación no hay envío, sin destinatario válido no hay borrador, un
reintento no duplica— y eso no depende de qué destino ejecuta la entrega.
La capacidad nueva es un adapter detrás del mismo puerto, no lógica de
control nueva. `ENVIADA_SIMULADA` sigue siendo el nombre del estado
terminal de entrega —el sufijo es histórico— y lo que distingue al destino
que entregó es el `delivery_mode` de la línea de auditoría: `fake` o
`gmail_test_list`.

Estados: `PENDIENTE_VALIDACION` → `APROBADA_SEMANTICA` | `APROBADA_UTILITARIA`
según cuál de las dos aprobaciones llega primero, y de ahí → `APROBADA` cuando
llega la complementaria; cualquier decisión negativa lleva a `RECHAZADA`.
Sólo desde `APROBADA` —las dos aprobaciones registradas— se puede pasar a
`ENVIO_RESERVADO` → `ENVIADA_SIMULADA` | `FALLIDA`. El paso intermedio
`ENVIO_RESERVADO` existe para que una caída durante la entrega no deje el
registro en un estado que habilite reintentar y mandar dos veces.

Desde `APROBADA` también se puede encolar la entrega con `asincrono=True` y
una `ColaEnvios` inyectada (s4d): el registro pasa a `ENVIO_ENCOLADO` y un
worker separado, `drenar_envios`, reserva y entrega después con reintentos
acotados. La cola es una pista de trabajo, no la autoridad: el estado que
habilita o descarta una entrega vive siempre en el registro, así que un ítem
encolado cuyo registro ya no está pendiente se descarta sin re-entregar. No
hay broker externo (Celery y Redis quedaron diferidos por decisión
documentada) y la entrega exige el mismo destino habilitado que la vía
síncrona: el encolado cambia cuándo se entrega, no qué se entrega ni quién
puede recibirlo.

Qué falta para que esto sea utilizable, y por qué no está: los orígenes de
inscripción reales no están definidos por la SEU. `origenes_inscripcion.py`
enumera exactamente qué falta por cada origen y bloquea el envío en todos.

Tipos de notificación (bible 22/09 y diseño de control de pagos): HU-012
cubre seis tipos —`inscripcion`, `participacion`, `situacion_pagos`,
`aprobacion`, `recordatorio_pago` e `instrucciones_pago`— declarados en el
catálogo cerrado `contracts/tipos_notificacion_v2.json` que expone
`tipos_notificacion.py`. El tipo viaja en la solicitud (con default
`inscripcion`, el único que existía), entra a la clave de idempotencia —una
notificación de participación sobre la misma inscripción es otra
comunicación, no un duplicado— y elige la frase del evento en el cuerpo.
Todo lo demás del pipeline es idéntico para todos los tipos por envío:
misma doble aprobación, misma cola, mismo destino habilitado. El control
por tipo es fail-closed y se evalúa antes de tocar el registro: un tipo
fuera del catálogo es `INVALIDA`, un tipo con datos `DESCONOCIDO` es
`notification_type_blocked`, y un tipo habilitado cuyo `modo_circuito`
declarado no es el de solicitud individual —`recordatorio_pago`, que
tramita por lote (D3)— es `notification_mode_mismatch`: ninguno produce
borrador ni envío por esta vía.

`instrucciones_pago` (D8) es el único tipo por envío que exige un dato
estructurado además de los campos del contrato: la solicitud lo porta en
`datos_pago`, un `DatosInstruccionesPago` con el asunto de preinscripción,
las cuotas, los medios y las bonificaciones del plan. Su render no usa la
plantilla genérica —el correo lista el plan de pago— y su asunto es el
`asunto_preinscripcion` del plan sin la marca de borrador, porque la
respuesta del preinscripto se asocia por ese asunto normalizado (§4.2 del
diseño de pagos): la marca sigue yendo en el cuerpo, que es donde el
destino la exige.

Retención acotada (issue #87, ADR 0009 y término del glosario): el texto
del borrador y los datos de la persona viven en el registro sólo mientras
dura el ciclo de envío más su ventana de reconciliación. Una vez que la
confirmación llega a un estado terminal y la ventana vence,
`purgar_terminadas` reescribe el archivo dejando `asunto` y `cuerpo`
vacíos y conservando clave, estado, fechas y el hash del contenido: la
idempotencia sigue intacta porque la clave no se toca nunca, y la traza
sigue siendo auditable contra el log. Los indeterminados y todo estado
no terminal quedan a la vista: la purga no decide por una persona.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from importlib.resources import files
from pathlib import Path
from threading import Lock
from typing import Callable, Protocol

from .registro_auditoria import escribir_registro
from .tipos_notificacion import (
    MODO_CIRCUITO_POR_ENVIO,
    TIPO_NOTIFICACION_PREDETERMINADO,
    TIPOS_NOTIFICACION,
    campos_requeridos,
    descripcion_tipo,
    evaluar_tipo,
    modo_circuito,
)

HU = "HU-012"
CONTRACT_VERSION = "confirmacion_inscripcion_v1"
TEMPLATE_VERSION = "confirmacion_inscripcion_provisional_v1"
POLICY_STATUS = "PROVISIONAL_NO_INSTITUCIONAL"
MARCADOR_BORRADOR = "BORRADOR — NO ENVIAR"

# El tipo del correo de preinscripción con las instrucciones de pago (D8):
# se declara en el catálogo v2 y tramita por este circuito con `datos_pago`.
TIPO_INSTRUCCIONES_PAGO = "instrucciones_pago"
TEMPLATE_VERSION_INSTRUCCIONES = "instrucciones_pago_provisional_v1"

# El documento de plantilla del correo de instrucciones: la sección central
# (entre el encabezado de versión y `LÍMITES:`) es el cuerpo que se
# renderiza; los límites documentan restricciones y no viajan.
TEXTO_PLANTILLA_INSTRUCCIONES = (
    files("agente1")
    .joinpath("prompts", "instrucciones_pago_provisional_v1.txt")
    .read_text(encoding="utf-8")
)
EMAIL_LOCAL_RE = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}\Z")
EMAIL_DOMAIN_LABEL_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
# Las claves del registro durable son sha256 en hexadecimal. Se validan igual
# antes de construir un path: una clave no debe poder elegir dónde se escribe.
CLAVE_REGISTRO_RE = re.compile(r"[0-9a-f]{64}\Z")
# Conjunto base de campos exigidos, el que siempre tuvo `inscripcion` —que
# era el único tipo. La fuente vigente por tipo es el catálogo
# (`campos_requeridos(tipo)`); esta constante queda como baseline fijado por
# fuera del catálogo para que cualquier cambio de los campos de `inscripcion`
# sea una decisión visible en el diff, no un arrastre silencioso.
REQUIRED_FIELDS = (
    "id_inscripcion",
    "nombre_destinatario",
    "actividad",
    "fecha",
    "organiza",
    "contacto",
)

# La bible exige dos aprobaciones independientes antes de habilitar un envío:
# la semántica, a cargo del Responsable de Gestión del Conocimiento, y la
# utilitaria, del Coordinador de Extensión (CU10 "Aprobar Borrador", bloque
# "Human in the Loop"; CP18/CP19 del Plan de Pruebas Unitarias). El conjunto
# de roles es cerrado: una decisión con otro rol no es una aprobación. Es un
# catálogo provisional —la identidad real de quien decide sigue pendiente de
# la identidad institucional (DEF-A1-001, issue #15)— pero la exigencia de
# dos decisiones distintas ya aplica.
ROL_APROBACION_SEMANTICA = "RESPONSABLE_GESTION_CONOCIMIENTO"
ROL_APROBACION_UTILITARIA = "COORDINADOR_EXTENSION"
ROLES_APROBACION = frozenset(
    {ROL_APROBACION_SEMANTICA, ROL_APROBACION_UTILITARIA}
)

# Estados parciales de aprobación: el nombre declara la aprobación que ya
# quedó registrada, así que la que falta para habilitar el envío es la otra.
ESTADO_APROBADA_SEMANTICA = "APROBADA_SEMANTICA"
ESTADO_APROBADA_UTILITARIA = "APROBADA_UTILITARIA"
ESTADOS_PARCIALES_APROBACION = frozenset(
    {ESTADO_APROBADA_SEMANTICA, ESTADO_APROBADA_UTILITARIA}
)

# Camino asíncrono (s4d): la confirmación ya aprobada por las dos decisiones
# espera en cola hasta que `drenar_envios` la tome. `ENVIO_ENCOLADO` es un
# estado propio, no se reusa `APROBADA`, para que el registro refleje que el
# envío ya tiene una intención registrada: un segundo pedido, síncrono o
# encolado, es duplicado y no puede producir otra entrega.
ESTADO_ENVIO_ENCOLADO = "ENVIO_ENCOLADO"

# Presupuesto fijo de intentos por ítem: una falla transitoria del destino
# reintenta en el próximo drenaje, pero un ítem no puede reintentar para
# siempre. Tres intentos alcanzan para distinguir transitorio de definitivo
# sin convertir la cola en un bucle.
REINTENTOS_ENVIO_MAX = 3

# Ventana de reconciliación de la retención acotada (ADR 0009, glosario):
# los 30 días que una persona tiene para cruzar el registro contra Gmail
# Enviados antes de que el texto del borrador se purgue.
VENTANA_RECONCILIACION_DIAS = 30

# Estados desde los que ninguna transición sale y que no esperan la
# decisión de una persona: la entrega terminó, falló o el borrador fue
# rechazado. Es el único conjunto que la purga puede tocar. Quedan fuera
# a propósito `ENVIO_INDETERMINADO` y `EMISION_INDETERMINADA` (siguen a la
# vista hasta que una persona reconcilie), todo estado no terminal y
# cualquier estado desconocido: lo que el conjunto no nombra no se purga.
# Se incluyen los estados terminales de HU-014 porque el registro es el
# mismo (`RegistroCertificadosArchivo` es un alias de esta clase).
ESTADOS_PURGABLES = frozenset(
    {"ENVIADA_SIMULADA", "EMITIDA_SIMULADA", "FALLIDA", "RECHAZADA"}
)

# Por rol: el estado en que queda un borrador pendiente cuando ese rol
# aprueba, y el estado parcial del que parte para completar el par.
_PARCIAL_POR_ROL = {
    ROL_APROBACION_SEMANTICA: (
        ESTADO_APROBADA_SEMANTICA,
        ESTADO_APROBADA_UTILITARIA,
    ),
    ROL_APROBACION_UTILITARIA: (
        ESTADO_APROBADA_UTILITARIA,
        ESTADO_APROBADA_SEMANTICA,
    ),
}


@dataclass(frozen=True)
class CuotaInstrucciones:
    """Una cuota del plan en la forma que viaja por la solicitud.

    `vencimiento` es texto ISO (AAAA-MM-DD) o `None`: el dato viaja
    serializable para que la clave de idempotencia y el hash de la entrada
    lo cubran íntegro, como a cualquier otro campo de la solicitud.
    """

    nro: int
    monto: int
    vencimiento: str | None = None


@dataclass(frozen=True)
class DatosInstruccionesPago:
    """Los datos del plan de pago que el tipo `instrucciones_pago` consume.

    Es el «dato específico» del tipo según el catálogo (`plan_pago`,
    SUPUESTO_TECNICO): no viene del SIU ni del pedido humano sino del plan
    de pagos de la actividad, que la corrida de `pagos.py` ya carga con su
    procedencia. Viaja dentro de la solicitud — no en un archivo aparte —
    porque es parte de lo que se aprueba: dos borradores de instrucciones
    con planes distintos son comunicaciones distintas y el hash de la
    solicitud los separa.

    `asunto_preinscripcion` es el dato crítico: el asunto del borrador sale
    de ahí, exacto, porque la respuesta del preinscripto con el comprobante
    se asocia a la actividad por ese asunto normalizado (§4.2 del diseño).
    """

    asunto_preinscripcion: str
    cuotas: tuple[CuotaInstrucciones, ...]
    medios_pago: tuple[str, ...]
    bonificaciones: tuple[str, ...]
    fecha_inicio: str | None = None
    fecha_limite_inscripcion: str | None = None


@dataclass(frozen=True)
class SolicitudConfirmacion:
    """Entrada del pipeline de HU-012.

    `tipo_notificacion` pertenece al catálogo cerrado de
    `tipos_notificacion.py` y por omisión es `inscripcion`, el único tipo que
    existía antes de la ampliación de la bible del 22/09 —así las entradas
    anteriores conservan su significado sin declararlo. El tipo forma parte
    de la identidad de la comunicación: entra al hash de idempotencia, así
    que dos tipos distintos sobre la misma inscripción no colisionan.

    `datos_pago` es el dato específico que sólo `instrucciones_pago`
    consume: los demás tipos lo ignoran (el catálogo no lo exige para
    ellos) y para `instrucciones_pago` es obligatorio — un `None` deja la
    solicitud `INCOMPLETA`.
    """

    id_inscripcion: str
    nombre_destinatario: str
    email_destinatario: str
    actividad: str
    fecha: str
    lugar: str
    organiza: str
    contacto: str
    tipo_notificacion: str = TIPO_NOTIFICACION_PREDETERMINADO
    datos_pago: DatosInstruccionesPago | None = None


@dataclass(frozen=True)
class AprobacionHumana:
    """Decisión humana registrada. Sin las dos del circuito no hay envío.

    Exige quién decidió (`validador`), con qué rol y cuándo, con zona horaria
    obligatoria: una aprobación sin responsable identificable no sirve como
    evidencia. `rol` pertenece a `ROLES_APROBACION`: la semántica y la
    utilitaria son decisiones de roles distintos y hacen falta las dos.
    Sólo se guarda su hash en el log, no los datos de la persona.
    """

    aprobada: bool
    validador: str
    rol: str
    fecha_iso: str


@dataclass(frozen=True)
class EntregaSimulada:
    idempotency_key: str
    destinatario: str
    asunto: str
    cuerpo: str


class DestinoConfirmaciones(Protocol):
    """Puerto de entrega de HU-012.

    Implementaciones habilitadas por el circuito, siempre por tipo exacto:
    `DestinoConfirmacionesFake` (doble de pruebas, sin red) y
    `GmailDestinoConfirmaciones` de `gmail_envio.py` (`gmail.send` cercado
    por la lista de direcciones de prueba de D12).
    """

    def entregar(
        self,
        *,
        idempotency_key: str,
        destinatario: str,
        asunto: str,
        cuerpo: str,
    ) -> None: ...


class DestinoConfirmacionesFake:
    """Test double explícito: registra entregas en memoria y no usa red."""

    def __init__(self, *, error: str | None = None) -> None:
        self.entregas: list[EntregaSimulada] = []
        self._error = error

    def entregar(
        self,
        *,
        idempotency_key: str,
        destinatario: str,
        asunto: str,
        cuerpo: str,
    ) -> None:
        if self._error:
            raise RuntimeError(self._error)
        self.entregas.append(
            EntregaSimulada(idempotency_key, destinatario, asunto, cuerpo)
        )


class EntregaRechazadaError(RuntimeError):
    """Rechazo de política de una entrega, antes de cualquier llamada de red.

    Lo levanta un destino cuando la entrega está prohibida en sí —un
    destinatario fuera de la lista de prueba, un cuerpo sin la marca de
    borrador— a diferencia de una falla del medio, que podría resolverse en
    un reintento. `code` es el identificador auditable del motivo y termina
    como `resultado` en la línea de auditoría. El circuito la lleva a
    `FALLIDA` de una vez: reintentar un rechazo de política no tiene sentido
    y gastaría el presupuesto de intentos contra una decisión que no cambia.
    """

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _destino_habilitado_para_entrega(destino: object) -> bool:
    """«Fake exacto, o Gmail con lista de prueba», siempre por tipo exacto.

    Es el control vigente del circuito (D12): la entrega existe contra
    `DestinoConfirmacionesFake` o contra `GmailDestinoConfirmaciones`, que
    no puede construirse sin una lista de direcciones de prueba cargada.
    Una subclase, un envoltorio o cualquier otro destino se rechaza, porque
    se compara `type(...) is` y no `isinstance`. El import diferido rompe el
    ciclo: `gmail_envio` implementa el puerto definido en este módulo.
    """

    if type(destino) is DestinoConfirmacionesFake:
        return True
    from .gmail_envio import GmailDestinoConfirmaciones

    return type(destino) is GmailDestinoConfirmaciones


def _modo_entrega(destino: object) -> str:
    """Identificador del destino que entregó, para la línea de auditoría.

    `ENVIADA_SIMULADA` es el nombre histórico del estado terminal; el modo
    es lo que distingue si la entrega fue en memoria (`fake`) o un envío
    real por `gmail.send` cercado por la lista (`gmail_test_list`).
    """

    if type(destino) is DestinoConfirmacionesFake:
        return "fake"
    from .gmail_envio import GmailDestinoConfirmaciones

    if type(destino) is GmailDestinoConfirmaciones:
        return "gmail_test_list"
    return "desconocido"


@dataclass(frozen=True)
class BorradorRegistrado:
    """Un registro del almacén durable: estado más el texto del borrador.

    Los cuatro campos opcionales completan la traza que la retención
    acotada necesita: `creado_en` y `actualizado_en` (ISO-8601 con zona
    horaria) fechan el alta y la última transición, `output_hash` es el
    `sha256` de `asunto + "\\n" + cuerpo` (el mismo cómputo de la línea de
    auditoría) y `purgado_en` fecha la purga. Un registro anterior a la
    fecha que los introduce puede venir sin ellos: para decidir la purga
    el reloj de último recurso es el `mtime` del archivo, y la purga misma
    deja asentada la fecha que usó. Después de purgar, `asunto` y `cuerpo`
    quedan vacíos y el resto se conserva.
    """

    estado: str
    asunto: str
    cuerpo: str
    creado_en: str | None = None
    actualizado_en: str | None = None
    output_hash: str | None = None
    purgado_en: str | None = None


class RegistroConfirmaciones(Protocol):
    """Puerto del registro de estado.

    `transicionar` recibe el conjunto de estados de origen aceptables y devuelve
    `False` si el actual no está entre ellos: es un compare-and-set. Así el
    llamador no puede leer el estado, decidir y escribir en tres pasos, que es
    donde aparecería la carrera que permite enviar dos veces.
    """

    def obtener(self, idempotency_key: str) -> BorradorRegistrado | None: ...

    def crear(self, idempotency_key: str, asunto: str, cuerpo: str) -> bool: ...

    def transicionar(
        self, idempotency_key: str, desde: frozenset[str], hacia: str
    ) -> bool: ...


class RegistroConfirmacionesMemoria:
    """Unique semantics de proceso para pruebas y matrices offline.

    Estampa los mismos campos de traza que el registro durable
    (`creado_en`, `actualizado_en`, `output_hash`) con un reloj inyectable:
    las pruebas que intercambian ambos puertos ven la misma forma.
    """

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._borradores: dict[str, BorradorRegistrado] = {}
        self._lock = Lock()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def obtener(self, idempotency_key: str) -> BorradorRegistrado | None:
        with self._lock:
            return self._borradores.get(idempotency_key)

    def crear(self, idempotency_key: str, asunto: str, cuerpo: str) -> bool:
        ahora = _iso(self._clock())
        with self._lock:
            if idempotency_key in self._borradores:
                return False
            self._borradores[idempotency_key] = BorradorRegistrado(
                estado="PENDIENTE_VALIDACION",
                asunto=asunto,
                cuerpo=cuerpo,
                creado_en=ahora,
                actualizado_en=ahora,
                output_hash=_hash(asunto + "\n" + cuerpo),
            )
            return True

    def transicionar(
        self, idempotency_key: str, desde: frozenset[str], hacia: str
    ) -> bool:
        with self._lock:
            actual = self._borradores.get(idempotency_key)
            if actual is None or actual.estado not in desde:
                return False
            self._borradores[idempotency_key] = BorradorRegistrado(
                estado=hacia,
                asunto=actual.asunto,
                cuerpo=actual.cuerpo,
                creado_en=actual.creado_en,
                actualizado_en=_iso(self._clock()),
                output_hash=actual.output_hash,
                purgado_en=actual.purgado_en,
            )
            return True


@dataclass(frozen=True)
class ItemEnvio:
    """Unidad de trabajo de la cola de envíos.

    El ítem porta lo que la entrega necesita y el registro no guarda: el
    destinatario (el registro conserva asunto y cuerpo, no el correo) y el
    hash de la solicitud para que cada intento del worker quede correlacionado
    con la auditoría del encolado. `intentos` cuenta los intentos ya
    consumidos; el asunto y el cuerpo NO viajan en el ítem porque el registro
    es la fuente de verdad y el worker los lee de ahí al drenar.
    """

    idempotency_key: str
    destinatario: str
    input_hash: str
    intentos: int = 0


class ColaEnvios(Protocol):
    """Puerto de la cola de envío asíncrono.

    La cola es una pista de trabajo, no la autoridad: la decisión de entregar
    la toma el registro con el compare-and-set `ENVIO_ENCOLADO` →
    `ENVIO_RESERVADO`. Por eso el puerto no necesita semántica transaccional:
    `encolar` es idempotente por clave, `pendientes` respeta el orden de
    llegada, `reemplazar` actualiza el ítem conservando su lugar y `descartar`
    lo quita. Ninguna operación de la cola entrega nada por sí sola.
    """

    def encolar(self, item: ItemEnvio) -> bool:
        """Agrega el ítem; `False` si la clave ya tenía uno."""
        ...

    def pendientes(self) -> tuple[ItemEnvio, ...]:
        """Ítems vigentes en orden de llegada."""
        ...

    def reemplazar(self, item: ItemEnvio) -> bool:
        """Actualiza el ítem de esa clave conservando su lugar; `False` si no existe."""
        ...

    def descartar(self, idempotency_key: str) -> bool:
        """Quita el ítem de esa clave; `False` si no existía."""
        ...


class ColaEnviosMemoria:
    """Cola en proceso para pruebas y corridas locales."""

    def __init__(self) -> None:
        # El dict preserva el orden de inserción y `reemplazar` reasigna sobre
        # la misma clave, así que un reintento conserva su lugar en la fila.
        self._items: dict[str, ItemEnvio] = {}
        self._lock = Lock()

    def encolar(self, item: ItemEnvio) -> bool:
        _validar_clave_cola(item.idempotency_key)
        with self._lock:
            if item.idempotency_key in self._items:
                return False
            self._items[item.idempotency_key] = item
            return True

    def pendientes(self) -> tuple[ItemEnvio, ...]:
        with self._lock:
            return tuple(self._items.values())

    def reemplazar(self, item: ItemEnvio) -> bool:
        _validar_clave_cola(item.idempotency_key)
        with self._lock:
            if item.idempotency_key not in self._items:
                return False
            self._items[item.idempotency_key] = item
            return True

    def descartar(self, idempotency_key: str) -> bool:
        with self._lock:
            return self._items.pop(idempotency_key, None) is not None


class RegistroConfirmacionesArchivo:
    """Registro durable: la idempotencia sobrevive al reinicio del proceso.

    El registro en memoria alcanza para una corrida, pero la idempotencia que
    importa es la que aguanta una caída: si el proceso muere después de
    reservar el envío y al reiniciar no queda rastro, un reintento vuelve a
    entregar. Por eso el estado vive en disco.

    Decisiones que no se ven en el código:

    - **Un archivo por clave, publicado con `os.link`.** `crear` no consulta y
      después escribe: escribe el contenido en un temporal y lo enlaza al
      nombre definitivo. `link` falla si el destino existe, así que da la
      semántica de "crear una vez" entre procesos, y además publica el archivo
      ya completo. Con `O_EXCL` alcanzaba para la exclusión pero no para eso:
      el archivo quedaba visible y vacío entre la creación y la escritura, y
      otro proceso que perdía la carrera lo leía justo ahí y encontraba un
      registro ilegible.
    - **`transicionar` toma un lock sobre un archivo aparte.** Un
      compare-and-set hecho con leer, decidir y escribir tiene una ventana
      donde dos procesos ven `APROBADA` y los dos reservan. `flock` la cierra,
      pero el lock tiene que vivir en un archivo cuyo inodo no cambie: como el
      registro se escribe con `os.replace`, un lock tomado sobre el `.json`
      quedaría sobre el inodo viejo y dejaría entrar a un segundo proceso. Por
      eso cada clave tiene su `.lock` estable, y el `.json` se reemplaza entero
      para que ningún lector vea un registro a medio escribir.
    - **Permisos restrictivos.** El registro guarda el texto del borrador, que
      es una comunicación institucional sin publicar y puede llevar el nombre
      de una persona. El directorio queda `0700` y cada archivo `0600`. La
      línea de auditoría, en cambio, sigue sin llevar texto: sólo hashes.
    - **La clave es un sha256.** Se valida igual antes de construir el path:
      una clave con `..` o con separadores no debe poder elegir dónde escribe
      el registro, aunque hoy la produzca el propio módulo.
    - **El registro lleva sus propias fechas.** `crear` y `transicionar`
      estampan `creado_en` y `actualizado_en` dentro del archivo, no fuera:
      la ventana de retención sobrevive a un respaldo que no preserve el
      `mtime`, porque la fecha viaja con el registro.
    """

    def __init__(
        self,
        directorio: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._directorio = Path(directorio)
        self._directorio.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _ruta(self, idempotency_key: str) -> Path:
        if not CLAVE_REGISTRO_RE.fullmatch(idempotency_key):
            raise ValueError("clave de idempotencia inválida")
        return self._directorio / f"{idempotency_key}.json"

    def obtener(self, idempotency_key: str) -> BorradorRegistrado | None:
        ruta = self._ruta(idempotency_key)
        try:
            contenido = ruta.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        return _leer_registro(contenido)

    def crear(self, idempotency_key: str, asunto: str, cuerpo: str) -> bool:
        ruta = self._ruta(idempotency_key)
        ahora = _iso(self._clock())
        registro = BorradorRegistrado(
            estado="PENDIENTE_VALIDACION",
            asunto=asunto,
            cuerpo=cuerpo,
            creado_en=ahora,
            actualizado_en=ahora,
            output_hash=_hash(asunto + "\n" + cuerpo),
        )
        temporal = ruta.with_name(f"{ruta.stem}.{uuid.uuid4().hex}.tmp")
        descriptor = os.open(temporal, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
                archivo.write(_serializar_registro(registro))
                archivo.flush()
                os.fsync(archivo.fileno())
            try:
                os.link(temporal, ruta)
            except FileExistsError:
                return False
            return True
        finally:
            temporal.unlink(missing_ok=True)

    def transicionar(
        self, idempotency_key: str, desde: frozenset[str], hacia: str
    ) -> bool:
        ruta = self._ruta(idempotency_key)
        candado = ruta.with_suffix(".lock")
        descriptor = os.open(candado, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            with os.fdopen(descriptor, "r+", encoding="utf-8") as archivo:
                fcntl.flock(archivo.fileno(), fcntl.LOCK_EX)
                actual = self.obtener(idempotency_key)
                if actual is None or actual.estado not in desde:
                    return False
                _escribir_atomico(
                    ruta,
                    BorradorRegistrado(
                        estado=hacia,
                        asunto=actual.asunto,
                        cuerpo=actual.cuerpo,
                        creado_en=actual.creado_en,
                        actualizado_en=_iso(self._clock()),
                        output_hash=actual.output_hash,
                        purgado_en=actual.purgado_en,
                    ),
                )
                return True
        except OSError:
            return False

    def listar_por_estado(self, estado: str) -> tuple[str, ...]:
        """Claves en un estado dado, para reconciliar. No cambia nada."""

        encontradas = []
        for ruta in sorted(self._directorio.glob("*.json")):
            registro = _leer_registro(ruta.read_text(encoding="utf-8"))
            if registro is not None and registro.estado == estado:
                encontradas.append(ruta.stem)
        return tuple(encontradas)

    def purgar_terminadas(
        self,
        *,
        ahora: datetime | None = None,
        ventana_dias: int = VENTANA_RECONCILIACION_DIAS,
    ) -> tuple[str, ...]:
        """Purga el texto de los registros terminales cuya ventana venció.

        La retención acotada (ADR 0009, issue #87): una confirmación en un
        estado de `ESTADOS_PURGABLES` cuya última transición quedó más
        atrás que `ahora - ventana_dias` pierde `asunto` y `cuerpo`, que es
        donde viven el texto del borrador y los datos de la persona. El
        archivo se reescribe con la misma atomicidad de siempre (temporal +
        `os.replace`, bajo el `.lock` por clave) y conserva la clave —el
        nombre del archivo no cambia, así que `crear` sigue fallando en la
        misma clave—, el estado, las fechas y el hash del contenido
        borrado. Por eso purgar nunca habilita un reenvío.

        La fecha que mide la ventana es `actualizado_en`: en un registro
        terminal es la fecha en que llegó a ese estado. Un registro
        anterior a los campos se mide por el `mtime` del archivo, que para
        un registro terminal es la última escritura, y la purga deja esa
        fecha asentada en `actualizado_en`. `ENVIO_INDETERMINADO`,
        `EMISION_INDETERMINADA` y todo estado no terminal no se tocan:
        siguen a la vista hasta que una persona decida. Un archivo
        ilegible o cuyo nombre no es una clave sha256 tampoco se toca:
        queda como evidencia.

        Devuelve las claves purgadas, ordenadas. La corrida es idempotente:
        `purgado_en` distingue lo ya purgado.
        """

        momento = ahora if ahora is not None else self._clock()
        _validar_momento(momento)
        if (
            not isinstance(ventana_dias, int)
            or isinstance(ventana_dias, bool)
            or not 1 <= ventana_dias <= 3650
        ):
            raise ValueError("ventana de retención inválida")
        corte = momento - timedelta(days=ventana_dias)
        purgadas = []
        for ruta in sorted(self._directorio.glob("*.json")):
            # El nombre también es la guarda: la purga sólo puede tocar
            # archivos cuyo nombre es una clave del registro.
            if CLAVE_REGISTRO_RE.fullmatch(ruta.stem) is None:
                continue
            registro = _leer_registro(ruta.read_text(encoding="utf-8"))
            if registro is None or not _es_purgable(registro):
                continue
            # "más de N días": en el instante exacto del corte la ventana
            # recién se cumple, así que el texto todavía queda.
            if _fecha_terminal(registro, ruta) >= corte:
                continue
            if self._purgar_si_vencida(ruta.stem, ruta, corte, momento):
                purgadas.append(ruta.stem)
        return tuple(purgadas)

    def _purgar_si_vencida(
        self, clave: str, ruta: Path, corte: datetime, ahora: datetime
    ) -> bool:
        """Reescribe el registro sin texto, bajo el lock por clave.

        Vuelve a leer y a verificar dentro del `flock`: el filtro previo de
        `purgar_terminadas` es sólo una optimización, la decisión se toma
        acá con la misma disciplina que `transicionar`. Si una corrida
        concurrente ya purgó la clave, `purgado_en` la descarta.
        """

        candado = ruta.with_suffix(".lock")
        descriptor = os.open(candado, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            with os.fdopen(descriptor, "r+", encoding="utf-8") as archivo:
                fcntl.flock(archivo.fileno(), fcntl.LOCK_EX)
                actual = self.obtener(clave)
                if actual is None or not _es_purgable(actual):
                    return False
                desde = _fecha_terminal(actual, ruta)
                if desde >= corte:
                    return False
                _escribir_atomico(
                    ruta,
                    BorradorRegistrado(
                        estado=actual.estado,
                        asunto="",
                        cuerpo="",
                        creado_en=actual.creado_en,
                        actualizado_en=actual.actualizado_en or _iso(desde),
                        output_hash=actual.output_hash
                        or _hash(actual.asunto + "\n" + actual.cuerpo),
                        purgado_en=_iso(ahora),
                    ),
                )
                return True
        except OSError:
            return False


class ColaEnviosArchivo:
    """Cola durable: los envíos encolados sobreviven al reinicio del proceso.

    Sigue el mismo patrón que el registro porque vale el mismo argumento: si
    la cola viviera sólo en memoria, una caída con trabajo encolado perdería
    los ítems y las confirmaciones quedarían en `ENVIO_ENCOLADO` sin que
    nadie las drene.

    Decisiones que no se ven en el código:

    - **Un archivo por ítem, publicado con `os.link`.** El nombre se deriva
      sólo de la clave (`{clave}.json`), así que `link` da el create-once:
      dos encolados de la misma clave, incluso entre procesos, producen un
      solo ítem. El orden de llegada NO está en el nombre: va en el campo
      `secuencia`, asignado bajo `flock` sobre `secuencia.lock`. Si el nombre
      llevara la secuencia, dos encolados de la misma clave tendrían nombres
      distintos y la idempotencia se perdería.
    - **La secuencia puede tener huecos.** Dos procesos que compiten por la
      misma clave consumen dos números y sólo uno gana el `link`; el hueco no
      rompe el orden porque `pendientes` ordena por `secuencia`.
    - **Sin lock por escritura en `reemplazar`/`descartar`.** La cola es una
      pista de trabajo: el compare-and-set que protege la entrega vive en el
      registro (`ENVIO_ENCOLADO` → `ENVIO_RESERVADO`). Dos workers que pisan
      un ítem no duplican la entrega porque sólo uno gana la reserva.
    - **Un ítem ilegible queda en disco.** `pendientes` lo omite y ninguna
      operación de la API lo toca: borrar un archivo que no se pudo
      interpretar sería destruir evidencia. Queda para revisión humana.
    - **Permisos restrictivos.** El ítem lleva el correo del destinatario en
      claro (el registro no lo guarda y la entrega lo necesita). El directorio
      queda `0700` y cada archivo `0600`, como el registro.
    """

    def __init__(self, directorio: Path) -> None:
        self._directorio = Path(directorio)
        self._directorio.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _ruta(self, idempotency_key: str) -> Path:
        _validar_clave_cola(idempotency_key)
        return self._directorio / f"{idempotency_key}.json"

    def _proxima_secuencia(self) -> int:
        """Número siguiente bajo lock; los huecos son aceptables, no hay reuse."""

        candado = self._directorio / "secuencia.lock"
        descriptor = os.open(candado, os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(descriptor, "r+", encoding="utf-8") as archivo:
            fcntl.flock(archivo.fileno(), fcntl.LOCK_EX)
            ruta = self._directorio / "secuencia"
            try:
                secuencia = int(ruta.read_text(encoding="utf-8").strip())
            except FileNotFoundError:
                secuencia = 0
            except ValueError:
                raise ValueError("cola de envíos corrupta: secuencia ilegible")
            secuencia += 1
            ruta.write_text(str(secuencia), encoding="utf-8")
            return secuencia

    def encolar(self, item: ItemEnvio) -> bool:
        ruta = self._ruta(item.idempotency_key)
        secuencia = self._proxima_secuencia()
        temporal = ruta.with_name(f"{ruta.stem}.{uuid.uuid4().hex}.tmp")
        descriptor = os.open(temporal, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
                archivo.write(_serializar_item(item, secuencia))
                archivo.flush()
                os.fsync(archivo.fileno())
            try:
                os.link(temporal, ruta)
            except FileExistsError:
                return False
            return True
        finally:
            temporal.unlink(missing_ok=True)

    def pendientes(self) -> tuple[ItemEnvio, ...]:
        items = []
        for ruta in sorted(self._directorio.glob("*.json")):
            leido = _leer_item(ruta.read_text(encoding="utf-8"))
            if leido is not None:
                items.append(leido)
        items.sort(key=lambda par: par[0])
        return tuple(item for _, item in items)

    def reemplazar(self, item: ItemEnvio) -> bool:
        ruta = self._ruta(item.idempotency_key)
        try:
            leido = _leer_item(ruta.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return False
        # Un ítem corrupto se trata como ausente, igual que en el registro:
        # reemplazarlo sería tapar evidencia y encima adjudicarle una
        # secuencia que no sabemos cuál era.
        if leido is None:
            return False
        _escribir_texto_atomico(ruta, _serializar_item(item, leido[0]))
        return True

    def descartar(self, idempotency_key: str) -> bool:
        # Una clave que no es un hash no construye path: devolver `False` es
        # fail-closed, la API nunca borra un archivo fuera del patrón.
        if CLAVE_REGISTRO_RE.fullmatch(idempotency_key) is None:
            return False
        try:
            self._ruta(idempotency_key).unlink()
            return True
        except FileNotFoundError:
            return False


def _validar_clave_cola(idempotency_key: str) -> None:
    if not CLAVE_REGISTRO_RE.fullmatch(idempotency_key):
        raise ValueError("clave de idempotencia inválida")


def _serializar_item(item: ItemEnvio, secuencia: int) -> str:
    return json.dumps(
        {**asdict(item), "secuencia": secuencia},
        ensure_ascii=False,
        sort_keys=True,
    )


def _leer_item(contenido: str) -> tuple[int, ItemEnvio] | None:
    """Un ítem ilegible se trata como ausente y queda en disco como evidencia.

    Se exige la clave con formato de hash por la misma razón que en el
    registro: una clave arbitraria no debe poder dirigir escrituras ni
    borrados. El destinatario no se valida acá porque el worker es quien
    decide qué hacer con un ítem semánticamente inválido (lo descarta sin
    entregar y lo audita).
    """

    try:
        datos = json.loads(contenido)
    except json.JSONDecodeError:
        return None
    if not isinstance(datos, dict):
        return None
    clave, destinatario, input_hash = (
        datos.get("idempotency_key"),
        datos.get("destinatario"),
        datos.get("input_hash"),
    )
    intentos, secuencia = datos.get("intentos"), datos.get("secuencia")
    if not all(
        isinstance(valor, str) for valor in (clave, destinatario, input_hash)
    ):
        return None
    if CLAVE_REGISTRO_RE.fullmatch(clave) is None:
        return None
    if any(
        not isinstance(valor, int) or isinstance(valor, bool) or valor < 0
        for valor in (intentos, secuencia)
    ):
        return None
    return secuencia, ItemEnvio(
        idempotency_key=clave,
        destinatario=destinatario,
        input_hash=input_hash,
        intentos=intentos,
    )


def _serializar_registro(registro: BorradorRegistrado) -> str:
    # Los campos de traza ausentes (registros anteriores a su introducción)
    # no se serializan: `null` no aporta y la ausencia es más honesta.
    return json.dumps(
        {
            clave: valor
            for clave, valor in asdict(registro).items()
            if valor is not None
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _leer_registro(contenido: str) -> BorradorRegistrado | None:
    """Un registro ilegible se trata como ausente, no como vacío.

    Devolver un `BorradorRegistrado` con campos por defecto convertiría un
    archivo corrupto en un estado válido, y desde ahí se podría transicionar a
    entrega. Ausente es fail-closed: `crear` va a fallar por `O_EXCL` y la
    inconsistencia sale a la luz en vez de habilitar un envío.

    Los campos de traza se validan con la misma dureza que los obligatorios:
    una fecha que no es ISO con zona o un hash que no es sha256 hacen el
    registro ilegible, porque aceptarlos degradaría en silencio la
    evidencia. Las claves desconocidas se ignoran, para que un archivo
    escrito por una versión posterior siga leyéndose.
    """

    try:
        datos = json.loads(contenido)
    except json.JSONDecodeError:
        return None
    if not isinstance(datos, dict):
        return None
    estado, asunto, cuerpo = (
        datos.get("estado"),
        datos.get("asunto"),
        datos.get("cuerpo"),
    )
    if not all(isinstance(valor, str) for valor in (estado, asunto, cuerpo)):
        return None
    creado_en, actualizado_en, purgado_en = (
        datos.get("creado_en"),
        datos.get("actualizado_en"),
        datos.get("purgado_en"),
    )
    output_hash = datos.get("output_hash")
    for fecha in (creado_en, actualizado_en, purgado_en):
        if fecha is not None and not _es_timestamp_iso(fecha):
            return None
    if output_hash is not None and CLAVE_REGISTRO_RE.fullmatch(output_hash) is None:
        return None
    return BorradorRegistrado(
        estado=estado,
        asunto=asunto,
        cuerpo=cuerpo,
        creado_en=creado_en,
        actualizado_en=actualizado_en,
        output_hash=output_hash,
        purgado_en=purgado_en,
    )


def _es_timestamp_iso(valor: object) -> bool:
    """ISO-8601 con zona horaria: un timestamp ingenuo no es comparable."""

    if not isinstance(valor, str):
        return False
    try:
        fecha = datetime.fromisoformat(valor)
    except ValueError:
        return False
    return fecha.tzinfo is not None and fecha.utcoffset() is not None


def _iso(momento: datetime) -> str:
    _validar_momento(momento)
    return momento.astimezone(timezone.utc).isoformat()


def _validar_momento(momento: datetime) -> None:
    # Misma regla que el resto de la trazabilidad: un timestamp sin zona no
    # es comparable entre máquinas ni contra la ventana de retención.
    if (
        not isinstance(momento, datetime)
        or momento.tzinfo is None
        or momento.utcoffset() is None
    ):
        raise ValueError("el timestamp debe incluir zona horaria")


def _es_purgable(registro: BorradorRegistrado) -> bool:
    return registro.estado in ESTADOS_PURGABLES and registro.purgado_en is None


def _fecha_terminal(registro: BorradorRegistrado, ruta: Path) -> datetime:
    """Cuándo entró al estado actual: `actualizado_en` o, en un registro
    anterior a los campos, el `mtime` del archivo —que para un registro
    terminal es su última escritura."""

    if registro.actualizado_en is not None:
        return datetime.fromisoformat(registro.actualizado_en)
    return datetime.fromtimestamp(ruta.stat().st_mtime, timezone.utc)


@dataclass(frozen=True)
class ResultadoPurga:
    """Qué dejó una corrida de purga: claves afectadas y dónde se auditó.

    `purgadas` son claves sha256, nunca contenido: el registro ya no tiene
    el texto y la auditoría nunca lo tuvo.
    """

    purgadas: tuple[str, ...]
    ventana_dias: int
    ejecutado_en: str
    correlation_id: str
    log_path: Path


def correr_purga_registro(
    *,
    registro: RegistroConfirmacionesArchivo,
    directorio_salida: Path,
    ahora: datetime | None = None,
    ventana_dias: int = VENTANA_RECONCILIACION_DIAS,
) -> ResultadoPurga:
    """Corre la purga del registro y deja una línea en la auditoría.

    Es la operación de la retención acotada: el scheduler local (#84) la
    dispara una vez por día vía `scripts/purgar_registro.py`, antes del
    respaldo diario (#86) para que ningún respaldo conserve texto que la
    política ya venció. La línea de auditoría lleva cuántos registros se
    purgaron y un hash del conjunto de claves: cantidad y verificabilidad,
    nunca contenido.
    """

    momento = ahora if ahora is not None else datetime.now(timezone.utc)
    purgadas = registro.purgar_terminadas(ahora=momento, ventana_dias=ventana_dias)
    correlation_id = str(uuid.uuid4())
    log_path = Path(directorio_salida) / "logs" / "confirmaciones-hu012.jsonl"
    auditoria = {
        "hu": HU,
        "contract_version": CONTRACT_VERSION,
        "template_version": TEMPLATE_VERSION,
        "policy_status": POLICY_STATUS,
        "correlation_id": correlation_id,
        "evento": "purga_retencion",
        "ventana_dias": ventana_dias,
        "ejecutado_en": _iso(momento),
        "purgados": len(purgadas),
        "claves_hash": _hash("\n".join(purgadas)),
    }
    escribir_registro(log_path, auditoria)
    return ResultadoPurga(
        purgadas=purgadas,
        ventana_dias=ventana_dias,
        ejecutado_en=_iso(momento),
        correlation_id=correlation_id,
        log_path=log_path,
    )


def _escribir_atomico(ruta: Path, registro: BorradorRegistrado) -> None:
    _escribir_texto_atomico(ruta, _serializar_registro(registro))


def _escribir_texto_atomico(ruta: Path, contenido: str) -> None:
    """Escribe por reemplazo para que nadie lea un archivo a medio escribir."""

    temporal = ruta.with_suffix(".json.tmp")
    descriptor = os.open(temporal, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
        archivo.flush()
        os.fsync(archivo.fileno())
    os.replace(temporal, ruta)


@dataclass(frozen=True)
class ReservaReconciliada:
    """Una entrega que quedó en duda, y por qué no se reintenta."""

    idempotency_key: str
    estado_anterior: str = "ENVIO_RESERVADO"
    estado: str = "ENVIO_INDETERMINADO"


def reconciliar_envios_reservados(
    registro: RegistroConfirmacionesArchivo,
) -> tuple[ReservaReconciliada, ...]:
    """Cierra las reservas que quedaron colgadas, sin volver a entregar.

    Una reserva interrumpida es, por definición, indeterminada: el proceso
    murió entre reservar y saber el resultado, así que nadie puede afirmar si
    la entrega ocurrió. Reintentar sería apostar a que no, y el costo de
    equivocarse es una confirmación duplicada a una persona real.

    Por eso la reconciliación no entrega ni marca como enviada: mueve el
    registro a `ENVIO_INDETERMINADO`, un estado terminal para el pipeline —
    `procesar_confirmacion` no transiciona desde ahí— que existe para que una
    persona decida con el registro a la vista.
    """

    reconciliadas = []
    for clave in registro.listar_por_estado("ENVIO_RESERVADO"):
        if registro.transicionar(
            clave, frozenset({"ENVIO_RESERVADO"}), "ENVIO_INDETERMINADO"
        ):
            reconciliadas.append(ReservaReconciliada(idempotency_key=clave))
    return tuple(reconciliadas)


@dataclass(frozen=True)
class ResultadoEnvioEncolado:
    """Qué pasó con un ítem de la cola durante un drenaje.

    `intento` es el número de intento de entrega realizado en este drenaje
    (0 si el ítem se resolvió sin llamar al destino). `estado_registro` es el
    estado del registro al terminar, o el estado encontrado cuando el ítem
    se descartó. `resolucion` es el código cerrado: `entregada`,
    `reintento_pendiente`, `fallida`, `descartada_sin_entrega` o `pendiente`
    (la reserva no se pudo tomar en esta corrida y el ítem sigue en cola).
    """

    idempotency_key: str
    intento: int
    estado_registro: str
    resolucion: str


def drenar_envios(
    *,
    registro: RegistroConfirmaciones,
    cola: ColaEnvios,
    destino: DestinoConfirmaciones,
    directorio_salida: Path,
    max_intentos: int = REINTENTOS_ENVIO_MAX,
) -> tuple[ResultadoEnvioEncolado, ...]:
    """Worker del envío asíncrono: procesa los ítems debidos de la cola.

    Cada ítem se intenta una vez por drenaje. El ciclo respeta el mismo
    lifecycle que la entrega síncrona (`ENVIO_ENCOLADO` → `ENVIO_RESERVADO` →
    `ENVIADA_SIMULADA` | `FALLIDA`) porque la reserva sigue siendo lo que
    protege contra una doble entrega si el proceso muere a mitad de camino:
    una reserva colgada la cierra `reconciliar_envios_reservados` hacia
    `ENVIO_INDETERMINADO`, y el ítem que le corresponde se descarta en el
    próximo drenaje porque el registro ya no está pendiente.

    Reintentos: una falla del destino devuelve el registro a `ENVIO_ENCOLADO`
    y deja el ítem en cola con `intentos` incrementado, así el próximo
    drenaje lo reintenta. Al agotar `max_intentos` el registro queda
    `FALLIDA` y el ítem sale de la cola. Cada intento (y cada descarte) deja
    una línea de auditoría en el mismo log que `procesar_confirmacion`.

    Fail-closed en ambas puntas: sin un destino habilitado el worker no
    procesa nada (devuelve vacío y la cola queda intacta), y un ítem cuyo
    registro ya no está en `ENVIO_ENCOLADO` (entregada, fallida, rechazada,
    indeterminada o ausente) se descarta sin re-entregar.
    """

    if (
        not isinstance(max_intentos, int)
        or isinstance(max_intentos, bool)
        or max_intentos < 1
    ):
        raise ValueError("presupuesto de reintentos inválido")
    # El mismo candado que `procesar_confirmacion`: la entrega sólo existe
    # contra el fake explícito o el Gmail con lista de prueba. Acá no hay
    # Invalida que devolver porque el worker no procesa solicitudes:
    # simplemente no trabaja.
    if not _destino_habilitado_para_entrega(destino):
        return ()
    modo_entrega = _modo_entrega(destino)
    log_path = Path(directorio_salida) / "logs" / "confirmaciones-hu012.jsonl"

    resultados = []
    for item in cola.pendientes():
        clave = item.idempotency_key
        correlation_id = str(uuid.uuid4())
        # Un ítem mal formado (clave que no es hash, destinatario inválido o
        # contador negativo) no llega ni al registro ni al destino: se
        # descarta y el registro queda intacto para revisión humana.
        if (
            CLAVE_REGISTRO_RE.fullmatch(clave) is None
            or not email_valido(item.destinatario)
            or item.intentos < 0
        ):
            cola.descartar(clave)
            _auditar_drenaje(
                log_path,
                correlation_id=correlation_id,
                item=item,
                delivery_mode=modo_entrega,
                intento=0,
                estado="ITEM_INVALIDO",
                resultado="queue_item_invalid",
                asunto="",
                cuerpo="",
            )
            resultados.append(
                ResultadoEnvioEncolado(
                    idempotency_key=clave,
                    intento=0,
                    estado_registro="DESCONOCIDO",
                    resolucion="descartada_sin_entrega",
                )
            )
            continue

        actual = registro.obtener(clave)
        if actual is None or actual.estado != ESTADO_ENVIO_ENCOLADO:
            cola.descartar(clave)
            encontrado = actual.estado if actual is not None else "AUSENTE"
            _auditar_drenaje(
                log_path,
                correlation_id=correlation_id,
                item=item,
                delivery_mode=modo_entrega,
                intento=0,
                estado=encontrado,
                resultado="queue_item_discarded",
                asunto=actual.asunto if actual is not None else "",
                cuerpo=actual.cuerpo if actual is not None else "",
            )
            resultados.append(
                ResultadoEnvioEncolado(
                    idempotency_key=clave,
                    intento=0,
                    estado_registro=encontrado,
                    resolucion="descartada_sin_entrega",
                )
            )
            continue

        # Presupuesto ya consumido en corridas anteriores: no se intenta de
        # nuevo, la confirmación queda FALLIDA y el ítem sale de la cola.
        if item.intentos >= max_intentos:
            registro.transicionar(
                clave, frozenset({ESTADO_ENVIO_ENCOLADO}), "FALLIDA"
            )
            cola.descartar(clave)
            _auditar_drenaje(
                log_path,
                correlation_id=correlation_id,
                item=item,
                delivery_mode=modo_entrega,
                intento=item.intentos,
                estado="FALLIDA",
                resultado="delivery_budget_exhausted",
                asunto=actual.asunto,
                cuerpo=actual.cuerpo,
            )
            resultados.append(
                ResultadoEnvioEncolado(
                    idempotency_key=clave,
                    intento=item.intentos,
                    estado_registro="FALLIDA",
                    resolucion="fallida",
                )
            )
            continue

        # La reserva es el compare-and-set que impide la doble entrega entre
        # workers. Si no se toma (otro proceso ganó o el registro falló) el
        # ítem queda en cola: el próximo drenaje lo reintenta si sigue
        # encolado o lo descarta si el estado ya cambió.
        if not registro.transicionar(
            clave, frozenset({ESTADO_ENVIO_ENCOLADO}), "ENVIO_RESERVADO"
        ):
            _auditar_drenaje(
                log_path,
                correlation_id=correlation_id,
                item=item,
                delivery_mode=modo_entrega,
                intento=0,
                estado=ESTADO_ENVIO_ENCOLADO,
                resultado="reservation_lost",
                asunto=actual.asunto,
                cuerpo=actual.cuerpo,
            )
            resultados.append(
                ResultadoEnvioEncolado(
                    idempotency_key=clave,
                    intento=0,
                    estado_registro=ESTADO_ENVIO_ENCOLADO,
                    resolucion="pendiente",
                )
            )
            continue

        intento = item.intentos + 1
        try:
            destino.entregar(
                idempotency_key=clave,
                destinatario=item.destinatario,
                asunto=actual.asunto,
                cuerpo=actual.cuerpo,
            )
        except EntregaRechazadaError as exc:
            # Rechazo de política —destinatario fuera de la lista de prueba,
            # cuerpo sin marca de borrador—: no hay transitorio que esperar.
            # El registro queda FALLIDA de una vez y el ítem sale de la cola,
            # sin gastar intentos contra una decisión que no cambia.
            registro.transicionar(
                clave, frozenset({"ENVIO_RESERVADO"}), "FALLIDA"
            )
            cola.descartar(clave)
            _auditar_drenaje(
                log_path,
                correlation_id=correlation_id,
                item=item,
                delivery_mode=modo_entrega,
                intento=intento,
                estado="FALLIDA",
                resultado=exc.code,
                asunto=actual.asunto,
                cuerpo=actual.cuerpo,
            )
            resultados.append(
                ResultadoEnvioEncolado(
                    idempotency_key=clave,
                    intento=intento,
                    estado_registro="FALLIDA",
                    resolucion="fallida",
                )
            )
            continue
        except Exception:
            if intento >= max_intentos:
                registro.transicionar(
                    clave, frozenset({"ENVIO_RESERVADO"}), "FALLIDA"
                )
                cola.descartar(clave)
                _auditar_drenaje(
                    log_path,
                    correlation_id=correlation_id,
                    item=item,
                    delivery_mode=modo_entrega,
                    intento=intento,
                    estado="FALLIDA",
                    resultado="delivery_failed_budget_exhausted",
                    asunto=actual.asunto,
                    cuerpo=actual.cuerpo,
                )
                resultados.append(
                    ResultadoEnvioEncolado(
                        idempotency_key=clave,
                        intento=intento,
                        estado_registro="FALLIDA",
                        resolucion="fallida",
                    )
                )
            else:
                # Vuelve a la cola con el presupuesto descontado: el registro
                # regresa a ENVIO_ENCOLADO, nunca a APROBADA, para que un
                # pedido síncrono concurrente no pueda re-entregar.
                registro.transicionar(
                    clave,
                    frozenset({"ENVIO_RESERVADO"}),
                    ESTADO_ENVIO_ENCOLADO,
                )
                cola.reemplazar(
                    ItemEnvio(
                        idempotency_key=clave,
                        destinatario=item.destinatario,
                        input_hash=item.input_hash,
                        intentos=intento,
                    )
                )
                _auditar_drenaje(
                    log_path,
                    correlation_id=correlation_id,
                    item=item,
                    delivery_mode=modo_entrega,
                    intento=intento,
                    estado=ESTADO_ENVIO_ENCOLADO,
                    resultado="delivery_failed_retry_pending",
                    asunto=actual.asunto,
                    cuerpo=actual.cuerpo,
                )
                resultados.append(
                    ResultadoEnvioEncolado(
                        idempotency_key=clave,
                        intento=intento,
                        estado_registro=ESTADO_ENVIO_ENCOLADO,
                        resolucion="reintento_pendiente",
                    )
                )
            continue

        registro.transicionar(
            clave, frozenset({"ENVIO_RESERVADO"}), "ENVIADA_SIMULADA"
        )
        cola.descartar(clave)
        _auditar_drenaje(
            log_path,
            correlation_id=correlation_id,
            item=item,
            delivery_mode=modo_entrega,
            intento=intento,
            estado="ENVIADA_SIMULADA",
            resultado="ok",
            asunto=actual.asunto,
            cuerpo=actual.cuerpo,
        )
        resultados.append(
            ResultadoEnvioEncolado(
                idempotency_key=clave,
                intento=intento,
                estado_registro="ENVIADA_SIMULADA",
                resolucion="entregada",
            )
        )
    return tuple(resultados)


def _auditar_drenaje(
    log_path: Path,
    *,
    correlation_id: str,
    item: ItemEnvio,
    delivery_mode: str,
    intento: int,
    estado: str,
    resultado: str,
    asunto: str,
    cuerpo: str,
) -> None:
    """Constancia por intento del worker, con el mismo formato que el pipeline.

    La línea no lleva destinatario ni texto en claro: `recipient_hash` e
    `input_hash` permiten correlacionarla con la línea del encolado, y
    `evento`/`intento` distinguen cada pasada del worker.
    """

    auditoria = {
        "hu": HU,
        "contract_version": CONTRACT_VERSION,
        "template_version": TEMPLATE_VERSION,
        "policy_status": POLICY_STATUS,
        "correlation_id": correlation_id,
        "idempotency_key": item.idempotency_key,
        "evento": "drenaje_cola_envios",
        "intento": intento,
        "estado": estado,
        "resultado": resultado,
        "input_hash": item.input_hash,
        "recipient_hash": _hash(item.destinatario),
        "output_hash": _hash(asunto + "\n" + cuerpo),
        "human_decision_present": False,
        "human_decision_hash": None,
        "approval_role": None,
        "delivery_mode": delivery_mode if estado == "ENVIADA_SIMULADA" else "none",
        "origen_envio": "asincrono",
    }
    escribir_registro(log_path, auditoria)


@dataclass(frozen=True)
class ResultadoConfirmacion:
    estado: str
    idempotency_key: str
    log_path: Path
    correlation_id: str
    asunto: str | None = None
    cuerpo: str | None = None
    error: str | None = None


def procesar_confirmacion(
    *,
    solicitud: SolicitudConfirmacion,
    directorio_salida: Path,
    registro: RegistroConfirmaciones,
    aprobacion: AprobacionHumana | None = None,
    destino: DestinoConfirmaciones | None = None,
    enviar: bool = False,
    asincrono: bool = False,
    cola: ColaEnvios | None = None,
) -> ResultadoConfirmacion:
    """Genera y opcionalmente entrega a un destino habilitado, bajo aprobación.

    El destino habilitado es el fake explícito o el Gmail con lista de prueba
    (D12), siempre por tipo exacto: el control vive en
    `_destino_habilitado_para_entrega` y se aplica igual en la vía síncrona y
    en el worker `drenar_envios`.

    El orden de los controles no es casual: primero los que descalifican la
    solicitud en sí (tipos, destinatario, campos completos), después los de
    autorización (aprobación válida, aprobación presente si se pide enviar,
    destino obligatoriamente fake). Recién ahí se toca el registro. Así una
    solicitud mal formada no crea ni reserva nada.

    Sin `aprobacion` el resultado máximo es `PENDIENTE_VALIDACION`: generar el
    texto no es aprobarlo. Con `aprobacion.aprobada = False` la confirmación
    queda `RECHAZADA` y el borrador ya no puede aprobarse después.

    `asincrono=True` (s4d) es en sí mismo un pedido de envío: en lugar de
    entregar, la confirmación `APROBADA` pasa a `ENVIO_ENCOLADO` y queda un
    ítem en `cola`, que es obligatoria en esta vía. `destino` no se usa
    porque la entrega la hace `drenar_envios` con el suyo. Sin las dos
    aprobaciones nada entra a la cola: una aprobación parcial deja el estado
    parcial como siempre y un pedido sobre un registro no aprobado es
    `INVALIDA`.
    """


    correlation_id = str(uuid.uuid4())
    log_path = directorio_salida / "logs" / "confirmaciones-hu012.jsonl"
    idempotency_key = _idempotency_key(solicitud)

    if not _tipos_solicitud_validos(solicitud):
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="INVALIDA",
            error="input_contract_invalid",
        )
    # El catálogo de tipos es cerrado: un tipo que no está en él es un pedido
    # mal formado, igual que un campo que no es string. Va acá, entre los
    # controles de la solicitud en sí, porque evaluar un tipo desconocido
    # haría cualquier decisión posterior ilegible.
    if solicitud.tipo_notificacion not in TIPOS_NOTIFICACION:
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="INVALIDA",
            error="notification_type_invalid",
        )
    if not email_valido(solicitud.email_destinatario):
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="INVALIDA",
            error="recipient_invalid",
        )
    if not _campos_completos(solicitud):
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="INCOMPLETA",
            error="required_fields_missing",
        )
    # Segundo control por tipo, ya con la solicitud bien formada: un tipo
    # declarado pero sin origen confirmado para sus datos no produce ni
    # borrador ni envío, tenga o no aprobación humana. Los motivos quedan en
    # la línea de auditoría para que el pedido pendiente a la SEU sea
    # puntual.
    decision_tipo = evaluar_tipo(solicitud.tipo_notificacion)
    if not decision_tipo.habilitado:
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="INVALIDA",
            error="notification_type_blocked",
            auditoria_extra={
                "motivos_bloqueo_tipo": sorted(decision_tipo.motivos)
            },
        )
    # Tercer control por tipo: el modo de circuito declarado en el catálogo.
    # Un tipo habilitado puede tramitar por un circuito distinto del por
    # envío — `recordatorio_pago` declara `lote` (D3): no hay solicitud
    # individual que aprobar porque sus ítems nacen de la planificación de la
    # corrida y los encola `recordatorios.py` con sus propias autorizaciones.
    # Rechazarlo acá es fail-closed: una vía que el catálogo no declara para
    # el tipo no puede producir borrador ni envío.
    modo = modo_circuito(solicitud.tipo_notificacion)
    if modo != MODO_CIRCUITO_POR_ENVIO:
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="INVALIDA",
            error="notification_mode_mismatch",
            auditoria_extra={"modo_circuito": modo},
        )
    if aprobacion is not None and not _aprobacion_valida(aprobacion):
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="INVALIDA",
            error="approval_invalid",
        )
    # Control central de la HU: todo pedido de envío que pueda terminar en una
    # entrega exige un destino habilitado —el fake explícito o el Gmail con
    # lista de prueba— por tipo exacto y no con isinstance, para que una
    # subclase o un envoltorio no pueda pasar por acá. La lista del Gmail se
    # exige al construir el adapter: si el objeto existe, la lista existe.
    # Una decisión de rechazo no entrega nunca, así que no exige destino.
    # En la vía encolada el candado equivalente es `drenar_envios`, que exige
    # el mismo tipo exacto recién al entregar; lo que se exige acá es la cola
    # inyectada, porque encolar sin cola no tiene adónde ir.
    pide_envio = enviar or asincrono
    if pide_envio and (aprobacion is None or aprobacion.aprobada):
        if asincrono and cola is None:
            return _resultado(
                log_path=log_path,
                solicitud=solicitud,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
                estado="INVALIDA",
                error="queue_required",
            )
        if not asincrono and not _destino_habilitado_para_entrega(destino):
            return _resultado(
                log_path=log_path,
                solicitud=solicitud,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
                estado="INVALIDA",
                error="offline_destination_required",
            )

    existente = registro.obtener(idempotency_key)

    if aprobacion is None:
        if pide_envio:
            # Entrega sin decisión nueva: la autoriza el estado APROBADA, que
            # sólo se alcanza con las dos aprobaciones registradas. Un pedido
            # de envío sin registro o sobre uno todavía en validación es
            # inválido y no crea ni mueve nada; sobre un registro que ya pasó
            # de ese punto —entregada, fallida, rechazada, indeterminada— es
            # un reintento y se responde como duplicado.
            if existente is None or existente.estado in (
                {"PENDIENTE_VALIDACION"} | ESTADOS_PARCIALES_APROBACION
            ):
                return _resultado(
                    log_path=log_path,
                    solicitud=solicitud,
                    correlation_id=correlation_id,
                    idempotency_key=idempotency_key,
                    estado="INVALIDA",
                    error="approval_required",
                )
            if existente.estado != "APROBADA":
                return _duplicada(
                    log_path, solicitud, correlation_id, idempotency_key
                )
            if asincrono:
                return _encolar(
                    registro=registro,
                    cola=cola,
                    log_path=log_path,
                    solicitud=solicitud,
                    correlation_id=correlation_id,
                    idempotency_key=idempotency_key,
                    asunto=existente.asunto,
                    cuerpo=existente.cuerpo,
                )
            return _entregar(
                registro=registro,
                log_path=log_path,
                solicitud=solicitud,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
                destino=destino,
                asunto=existente.asunto,
                cuerpo=existente.cuerpo,
            )
        if existente is not None:
            return _duplicada(
                log_path, solicitud, correlation_id, idempotency_key
            )
        asunto_nuevo, cuerpo_nuevo = _renderizar(solicitud)
        if not registro.crear(idempotency_key, asunto_nuevo, cuerpo_nuevo):
            return _duplicada(
                log_path, solicitud, correlation_id, idempotency_key
            )
        return _finalizar(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="PENDIENTE_VALIDACION",
            asunto=asunto_nuevo,
            cuerpo=cuerpo_nuevo,
        )

    # A partir de acá hay una decisión humana que registrar. Si el borrador
    # todavía no existe, la decisión lo materializa primero; la lectura se
    # repite para conservar el registro tal como quedó en disco, con sus
    # fechas y su hash, y no una copia a mano que ya diverge.
    if existente is None:
        asunto_nuevo, cuerpo_nuevo = _renderizar(solicitud)
        registro.crear(idempotency_key, asunto_nuevo, cuerpo_nuevo)
        existente = registro.obtener(idempotency_key)
    if existente is None:
        raise RuntimeError("registro de idempotencia inconsistente")
    asunto, cuerpo = existente.asunto, existente.cuerpo

    if not aprobacion.aprobada:
        if not registro.transicionar(
            idempotency_key,
            frozenset({"PENDIENTE_VALIDACION"} | ESTADOS_PARCIALES_APROBACION),
            "RECHAZADA",
        ):
            return _duplicada(
                log_path, solicitud, correlation_id, idempotency_key
            )
        return _finalizar(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="RECHAZADA",
            asunto=asunto,
            cuerpo=cuerpo,
            aprobacion=aprobacion,
        )

    # Cada rol deja su propio estado parcial; la aprobación del otro rol es la
    # única que completa el circuito. Dos compare-and-set en cadena cierran la
    # carrera entre aprobaciones simultáneas de roles distintos.
    parcial_propia, parcial_ajena = _PARCIAL_POR_ROL[aprobacion.rol]
    if registro.transicionar(
        idempotency_key, frozenset({"PENDIENTE_VALIDACION"}), parcial_propia
    ):
        estado_actual = parcial_propia
    elif registro.transicionar(
        idempotency_key, frozenset({parcial_ajena}), "APROBADA"
    ):
        estado_actual = "APROBADA"
    else:
        return _duplicada(log_path, solicitud, correlation_id, idempotency_key)

    if not pide_envio or estado_actual != "APROBADA":
        # Si se pidió enviar pero falta la otra aprobación, el estado devuelto
        # lo dice explícitamente: la decisión quedó registrada y no se entregó.
        return _finalizar(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado=estado_actual,
            asunto=asunto,
            cuerpo=cuerpo,
            aprobacion=aprobacion,
        )

    if asincrono:
        return _encolar(
            registro=registro,
            cola=cola,
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            asunto=asunto,
            cuerpo=cuerpo,
            aprobacion=aprobacion,
        )
    return _entregar(
        registro=registro,
        log_path=log_path,
        solicitud=solicitud,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        destino=destino,
        asunto=asunto,
        cuerpo=cuerpo,
        aprobacion=aprobacion,
    )


def _encolar(
    *,
    registro: RegistroConfirmaciones,
    cola: ColaEnvios,
    log_path: Path,
    solicitud: SolicitudConfirmacion,
    correlation_id: str,
    idempotency_key: str,
    asunto: str,
    cuerpo: str,
    aprobacion: AprobacionHumana | None = None,
) -> ResultadoConfirmacion:
    """Deja la entrega encolada sin entregar: `APROBADA` → `ENVIO_ENCOLADO`.

    El compare-and-set garantiza que el encolado ocurre una sola vez por
    confirmación: un segundo pedido, síncrono o encolado, ya no encuentra el
    registro en `APROBADA` y es duplicado. Si el proceso muere entre la
    transición y `cola.encolar`, el registro queda `ENVIO_ENCOLADO` sin ítem:
    no entrega nunca y queda visible para revisión humana, la misma
    preferencia de siempre (una confirmación no enviada antes que una
    enviada dos veces).
    """

    if not registro.transicionar(
        idempotency_key,
        frozenset({"APROBADA"}),
        ESTADO_ENVIO_ENCOLADO,
    ):
        return _duplicada(log_path, solicitud, correlation_id, idempotency_key)
    # El ítem lleva el destinatario porque el registro no lo guarda, y el hash
    # de la solicitud para correlacionar los intentos del worker con esta
    # línea de auditoría. Si ya existía un ítem con la clave (sólo posible con
    # una cola precargada por fuera del pipeline) se respeta el existente.
    cola.encolar(
        ItemEnvio(
            idempotency_key=idempotency_key,
            destinatario=solicitud.email_destinatario,
            input_hash=_hash_solicitud(solicitud),
        )
    )
    return _finalizar(
        log_path=log_path,
        solicitud=solicitud,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        estado=ESTADO_ENVIO_ENCOLADO,
        asunto=asunto,
        cuerpo=cuerpo,
        aprobacion=aprobacion,
    )


def _entregar(
    *,
    registro: RegistroConfirmaciones,
    log_path: Path,
    solicitud: SolicitudConfirmacion,
    correlation_id: str,
    idempotency_key: str,
    destino: DestinoConfirmaciones,
    asunto: str,
    cuerpo: str,
    aprobacion: AprobacionHumana | None = None,
) -> ResultadoConfirmacion:
    """Reserva el envío antes de intentarlo, desde `APROBADA` solamente.

    Si el proceso muere en la entrega, el registro queda en ENVIO_RESERVADO y
    un reintento no vuelve a entregar, porque ya no está en APROBADA. Se
    prefiere una confirmación no enviada a una enviada dos veces.
    """

    if not registro.transicionar(
        idempotency_key,
        frozenset({"APROBADA"}),
        "ENVIO_RESERVADO",
    ):
        return _duplicada(log_path, solicitud, correlation_id, idempotency_key)
    assert _destino_habilitado_para_entrega(destino)
    try:
        destino.entregar(
            idempotency_key=idempotency_key,
            destinatario=solicitud.email_destinatario,
            asunto=asunto,
            cuerpo=cuerpo,
        )
    except EntregaRechazadaError as exc:
        # El destino rechazó la entrega por política antes de la red (un
        # destinatario fuera de la lista de prueba, un cuerpo sin marca):
        # FALLIDA es terminal —no hay reintento de una prohibición.
        registro.transicionar(
            idempotency_key, frozenset({"ENVIO_RESERVADO"}), "FALLIDA"
        )
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="FALLIDA",
            error=exc.code,
            asunto=asunto,
            cuerpo=cuerpo,
            aprobacion=aprobacion,
        )
    except Exception:
        registro.transicionar(
            idempotency_key, frozenset({"ENVIO_RESERVADO"}), "FALLIDA"
        )
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="FALLIDA",
            error="fake_delivery_failed"
            if type(destino) is DestinoConfirmacionesFake
            else "delivery_failed",
            asunto=asunto,
            cuerpo=cuerpo,
            aprobacion=aprobacion,
        )
    registro.transicionar(
        idempotency_key, frozenset({"ENVIO_RESERVADO"}), "ENVIADA_SIMULADA"
    )
    return _resultado(
        log_path=log_path,
        solicitud=solicitud,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        estado="ENVIADA_SIMULADA",
        error=None,
        asunto=asunto,
        cuerpo=cuerpo,
        aprobacion=aprobacion,
        auditoria_extra={"delivery_mode": _modo_entrega(destino)},
    )


def _duplicada(
    log_path: Path,
    solicitud: SolicitudConfirmacion,
    correlation_id: str,
    idempotency_key: str,
) -> ResultadoConfirmacion:
    return _resultado(
        log_path=log_path,
        solicitud=solicitud,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        estado="DUPLICADA",
        error="idempotency_duplicate",
    )


def _finalizar(
    *,
    log_path: Path,
    solicitud: SolicitudConfirmacion,
    correlation_id: str,
    idempotency_key: str,
    estado: str,
    asunto: str,
    cuerpo: str,
    aprobacion: AprobacionHumana | None = None,
    auditoria_extra: dict[str, object] | None = None,
) -> ResultadoConfirmacion:
    return _resultado(
        log_path=log_path,
        solicitud=solicitud,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        estado=estado,
        error=None,
        asunto=asunto,
        cuerpo=cuerpo,
        aprobacion=aprobacion,
        auditoria_extra=auditoria_extra,
    )


def _renderizar(solicitud: SolicitudConfirmacion) -> tuple[str, str]:
    """Arma asunto y cuerpo desde una plantilla fija. No interviene el modelo.

    La notificación es un texto administrativo: no hay nada que redactar y sí
    un riesgo concreto si un modelo altera un dato. Por eso HU-012 es
    puramente determinista. La SEU confirmó una única plantilla preaprobada
    para todos los tipos; lo único que varía por tipo es el asunto base y la
    frase del evento, declaradas en el catálogo `tipos_notificacion_v2`. Para
    `inscripcion` el resultado es idéntico al de siempre: su `asunto_base`
    reproduce el asunto que el módulo tenía fijado antes del catálogo.

    `instrucciones_pago` es la excepción: su cuerpo sale de
    `prompts/instrucciones_pago_provisional_v1.txt` con los datos del plan y
    su asunto es el `asunto_preinscripcion` del plan — sin la marca de
    borrador — porque la respuesta del preinscripto se asocia por ese
    asunto normalizado.
    """

    if solicitud.tipo_notificacion == TIPO_INSTRUCCIONES_PAGO:
        return _renderizar_instrucciones_pago(solicitud)

    plantilla = descripcion_tipo(solicitud.tipo_notificacion)["plantilla"]
    # Un lugar vacío se completa con una frase explícita en vez de dejarse en
    # blanco: el destinatario tiene que ver que el dato falta, no un renglón
    # cortado que parezca un error de sistema.
    lugar = solicitud.lugar.strip() or "A confirmar por la Secretaría de Extensión"
    cuerpo = (
        f"{MARCADOR_BORRADOR}\n\n"
        f"Hola {solicitud.nombre_destinatario.strip()},\n\n"
        f"Registramos {plantilla['frase_evento']}: {solicitud.actividad.strip()}.\n"
        f"Fecha: {solicitud.fecha.strip()}\n"
        f"Lugar: {lugar}\n"
        f"Organiza: {solicitud.organiza.strip()}\n\n"
        "Este texto es una plantilla provisional y requiere validación humana antes de cualquier envío.\n"
        f"Contacto: {solicitud.contacto.strip()}\n"
    )
    return f"[{MARCADOR_BORRADOR}] {plantilla['asunto_base']}", cuerpo


_PLACEHOLDER_RE = re.compile(r"\{\{[^}]+\}\}")


def _renderizar_instrucciones_pago(
    solicitud: SolicitudConfirmacion,
) -> tuple[str, str]:
    """El correo de preinscripción con las instrucciones de pago (D8).

    El asunto es `asunto_preinscripcion` del plan, exacto y sin la marca de
    borrador: la asociación de respuestas de `pagos.py` compara el asunto
    normalizado de cada respuesta contra ese valor, así que un prefijo
    «BORRADOR» en el asunto haría que ningún comprobante se asocie. La
    marca no falta: va en la primera línea del cuerpo, que es el lugar que
    el destino habilitado exige (`draft_marker_missing` en Gmail).

    El cuerpo es la sección central del documento de plantilla, con cada
    `{{...}}` reemplazado por el dato del plan. Un placeholder sin valor es
    un error de programación — como en `recordatorios.py` — y se rechaza
    antes de entregar una llave suelta al destinatario. Los medios de pago
    llegan sólo acá, al cuerpo: la auditoría conserva hashes.
    """

    datos = solicitud.datos_pago
    # `datos_pago` ya pasó `_datos_pago_validos` en el control de campos:
    # llegar acá con `None` sería un bug del pipeline, no un pedido malo.
    assert isinstance(datos, DatosInstruccionesPago)

    detalle_cuotas = "\n".join(
        f"- Cuota {cuota.nro}: ${_monto_texto(cuota.monto)}"
        + (
            f", vencimiento {cuota.vencimiento}."
            if cuota.vencimiento
            else "."
        )
        for cuota in datos.cuotas
    )
    medios = ", ".join(medio.strip() for medio in datos.medios_pago)
    bonificaciones = ", ".join(
        bonificacion.strip() for bonificacion in datos.bonificaciones
    )
    valores = {
        "nombre_destinatario": solicitud.nombre_destinatario.strip(),
        "actividad": solicitud.actividad.strip(),
        "linea_fecha_limite": (
            f"Inscripción abierta hasta: {datos.fecha_limite_inscripcion.strip()}.\n"
            if datos.fecha_limite_inscripcion
            else ""
        ),
        "fecha_inicio": (
            datos.fecha_inicio.strip()
            if datos.fecha_inicio
            else "A confirmar por la Secretaría de Extensión"
        ),
        "detalle_cuotas": detalle_cuotas,
        "medios_pago": medios or "A confirmar por la Secretaría de Extensión",
        "linea_bonificaciones": (
            f"Bonificaciones: {bonificaciones}.\n"
            if bonificaciones
            else "Sin bonificaciones declaradas.\n"
        ),
        "contacto": solicitud.contacto.strip(),
    }
    cuerpo = _seccion_cuerpo(TEXTO_PLANTILLA_INSTRUCCIONES)
    for clave, valor in valores.items():
        cuerpo = cuerpo.replace("{{" + clave + "}}", valor)
    if _PLACEHOLDER_RE.search(cuerpo):
        raise ValueError("plantilla con placeholders sin renderizar")
    return datos.asunto_preinscripcion.strip(), cuerpo


def _seccion_cuerpo(texto_plantilla: str) -> str:
    """La parte aprobable del documento de plantilla: entre el encabezado
    de versión/estado y la sección `LÍMITES`, que documenta restricciones
    y no viaja al destinatario."""

    sin_limites = texto_plantilla.split("LÍMITES:", 1)[0]
    lineas = sin_limites.splitlines()
    # Las dos primeras líneas son TEMPLATE_VERSION y POLICY_STATUS.
    return "\n".join(lineas[2:]).strip("\n") + "\n"


def _monto_texto(monto: int) -> str:
    """El importe con separador de miles rioplatense («20.000»)."""

    return f"{monto:,}".replace(",", ".")


def _campos_completos(solicitud: SolicitudConfirmacion) -> bool:
    """Los campos que exige el tipo, según el catálogo, presentes y con texto.

    `getattr` con default cierra el caso de un campo declarado en el catálogo
    que la solicitud no tenga: se cuenta como faltante en vez de explotar.
    `datos_pago` es el único campo estructurado: no alcanza con que exista,
    tiene que traer el plan completo que el render consume
    (`_datos_pago_validos`).
    """
    if not isinstance(solicitud.id_inscripcion, str) or ID_RE.fullmatch(
        solicitud.id_inscripcion
    ) is None:
        return False
    for campo in campos_requeridos(solicitud.tipo_notificacion):
        valor = getattr(solicitud, campo, None)
        if campo == "datos_pago":
            if not _datos_pago_validos(valor):
                return False
            continue
        if not isinstance(valor, str) or not valor.strip():
            return False
    return True


def _datos_pago_validos(datos: object) -> bool:
    """La estructura del dato específico de `instrucciones_pago`.

    Un `datos_pago` sin asunto de preinscripción o sin cuotas no puede
    renderizar el correo: el asunto es la llave que asocia las respuestas
    con el comprobante y las cuotas son la instrucción misma. Medios y
    bonificaciones sí pueden venir vacíos — un plan puede no declararlos —
    y el cuerpo lo dice explícito en vez de dejar un renglón cortado.
    """

    if not isinstance(datos, DatosInstruccionesPago):
        return False
    if not datos.asunto_preinscripcion.strip():
        return False
    if not datos.cuotas:
        return False
    for cuota in datos.cuotas:
        if (
            not isinstance(cuota.nro, int)
            or isinstance(cuota.nro, bool)
            or cuota.nro < 1
            or not isinstance(cuota.monto, int)
            or isinstance(cuota.monto, bool)
            or cuota.monto < 1
            or (
                cuota.vencimiento is not None
                and (
                    not isinstance(cuota.vencimiento, str)
                    or not _es_fecha_iso(cuota.vencimiento)
                )
            )
        ):
            return False
    for fecha in (datos.fecha_inicio, datos.fecha_limite_inscripcion):
        if fecha is not None and (
            not isinstance(fecha, str) or not _es_fecha_iso(fecha)
        ):
            return False
    return all(
        isinstance(texto, str) and bool(texto.strip())
        for texto in (*datos.medios_pago, *datos.bonificaciones)
    )


def _es_fecha_iso(valor: str) -> bool:
    try:
        date.fromisoformat(valor)
    except ValueError:
        return False
    return True


def _tipos_solicitud_validos(solicitud: SolicitudConfirmacion) -> bool:
    """Cada campo con su tipo: `str` para todo el contrato y la estructura
    cerrada — o `None` — para `datos_pago`."""

    if solicitud.datos_pago is not None and not isinstance(
        solicitud.datos_pago, DatosInstruccionesPago
    ):
        return False
    return all(
        isinstance(valor, str)
        for nombre, valor in asdict(solicitud).items()
        if nombre != "datos_pago"
    )


def email_valido(email: object) -> bool:
    """Validación cerrada de una dirección de correo.

    Es pública porque la reutiliza `gmail_envio.py` para validar la lista de
    direcciones de prueba: la misma regla que exige el pipeline al dato de
    entrada es la que exige el adapter a la configuración.
    """

    if (
        not isinstance(email, str)
        or len(email) > 254
        or "\r" in email
        or "\n" in email
        or email.count("@") != 1
    ):
        return False
    local, dominio = email.rsplit("@", 1)
    if (
        EMAIL_LOCAL_RE.fullmatch(local) is None
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
    ):
        return False
    etiquetas = dominio.split(".")
    return len(etiquetas) >= 2 and all(
        EMAIL_DOMAIN_LABEL_RE.fullmatch(etiqueta) is not None
        for etiqueta in etiquetas
    )


def _aprobacion_valida(aprobacion: AprobacionHumana) -> bool:
    if not isinstance(aprobacion.aprobada, bool):
        return False
    if (
        not isinstance(aprobacion.validador, str)
        or not isinstance(aprobacion.rol, str)
        or not aprobacion.validador.strip()
        or aprobacion.rol not in ROLES_APROBACION
    ):
        return False
    try:
        fecha = datetime.fromisoformat(aprobacion.fecha_iso)
    except (TypeError, ValueError):
        return False
    return fecha.tzinfo is not None


def _idempotency_key(solicitud: SolicitudConfirmacion) -> str:
    """Deriva la clave del contenido completo de la solicitud.

    Al incluir todos los campos, cambiar cualquier dato —la fecha, el
    destinatario— produce una clave distinta y por lo tanto una confirmación
    nueva, que es lo correcto: es otra comunicación. Reenviar exactamente la
    misma solicitud, en cambio, choca contra la clave existente.
    """

    canonico = json.dumps(
        {"contract": CONTRACT_VERSION, **asdict(solicitud)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda valor: f"<invalid:{type(valor).__name__}>",
    )
    return _hash(canonico)


def _hash_solicitud(solicitud: SolicitudConfirmacion) -> str:
    return _hash(
        json.dumps(
            asdict(solicitud),
            ensure_ascii=False,
            sort_keys=True,
            default=lambda valor: f"<invalid:{type(valor).__name__}>",
        )
    )


def _resultado(
    *,
    log_path: Path,
    solicitud: SolicitudConfirmacion,
    correlation_id: str,
    idempotency_key: str,
    estado: str,
    error: str | None,
    asunto: str | None = None,
    cuerpo: str | None = None,
    aprobacion: AprobacionHumana | None = None,
    auditoria_extra: dict[str, object] | None = None,
) -> ResultadoConfirmacion:
    # La línea de auditoría no lleva ni el correo del destinatario ni el texto:
    # sólo hashes. `recipient_hash` permite verificar después que se confirmó a
    # la persona correcta, sin guardar el dato personal en un segundo lugar.
    # `tipo_notificacion` no es dato personal y queda en claro porque la
    # evidencia tiene que distinguir qué clase de notificación se procesó; si
    # llegara con un tipo no string (pedido mal formado) se serializa con la
    # misma marca defensiva que `_hash` para que la auditoría no explote.
    auditoria = {
        "hu": HU,
        "contract_version": CONTRACT_VERSION,
        "template_version": TEMPLATE_VERSION,
        "policy_status": POLICY_STATUS,
        "correlation_id": correlation_id,
        "idempotency_key": idempotency_key,
        "tipo_notificacion": solicitud.tipo_notificacion
        if isinstance(solicitud.tipo_notificacion, str)
        else f"<invalid:{type(solicitud.tipo_notificacion).__name__}>",
        "estado": estado,
        "resultado": error or "ok",
        "input_hash": _hash_solicitud(solicitud),
        "recipient_hash": _hash(solicitud.email_destinatario),
        "output_hash": _hash((asunto or "") + "\n" + (cuerpo or "")),
        "human_decision_present": aprobacion is not None,
        "human_decision_hash": _hash(
            json.dumps(asdict(aprobacion), ensure_ascii=False, sort_keys=True)
        )
        if aprobacion is not None
        else None,
        # El rol queda en claro para poder evidenciar que las dos aprobaciones
        # vinieron de roles distintos; no es un dato personal.
        "approval_role": aprobacion.rol if aprobacion is not None else None,
        "delivery_mode": "fake" if estado == "ENVIADA_SIMULADA" else "none",
    }
    # Motivos de bloqueo por tipo u otra evidencia puntual del control que
    # produjo el resultado; nunca datos personales ni texto en claro.
    if auditoria_extra:
        auditoria.update(auditoria_extra)
    escribir_registro(log_path, auditoria)
    return ResultadoConfirmacion(
        estado=estado,
        idempotency_key=idempotency_key,
        log_path=log_path,
        correlation_id=correlation_id,
        asunto=asunto,
        cuerpo=cuerpo,
        error=error,
    )


def _hash(valor: object) -> str:
    serializado = (
        valor
        if isinstance(valor, str)
        else json.dumps(
            valor,
            ensure_ascii=False,
            sort_keys=True,
            default=lambda item: f"<invalid:{type(item).__name__}>",
        )
    )
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()
