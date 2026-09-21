"""Slice offline de HU-012: borradores de confirmación, nunca correo real.

Prepara el texto de una confirmación de inscripción y modela su ciclo de vida
completo —incluida la aprobación humana y el "envío"— pero **no existe ningún
adapter que mande correo**. La única entrega posible es contra
`DestinoConfirmacionesFake`, y eso se verifica en tiempo de ejecución
comparando el tipo exacto (`type(destino) is not DestinoConfirmacionesFake`, no
`isinstance`): ni siquiera una subclase puede colarse como destino.

Por qué modelar un envío que no se hace: el punto de la HU es demostrar que la
secuencia de autorización es correcta —sin aprobación no hay envío, sin
destinatario válido no hay borrador, un reintento no duplica— antes de que
exista la capacidad técnica de enviar. Cuando la SEU habilite el correo, lo que
se agrega es un adapter, no la lógica de control.

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
documentada) y la entrega sigue siendo exclusivamente contra el fake: el
encolado cambia cuándo se entrega, no qué se entrega.

Qué falta para que esto sea utilizable, y por qué no está: los orígenes de
inscripción reales no están definidos por la SEU. `origenes_inscripcion.py`
enumera exactamente qué falta por cada origen y bloquea el envío en todos.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
from threading import Lock
from typing import Protocol
import uuid


HU = "HU-012"
CONTRACT_VERSION = "confirmacion_inscripcion_v1"
TEMPLATE_VERSION = "confirmacion_inscripcion_provisional_v1"
POLICY_STATUS = "PROVISIONAL_NO_INSTITUCIONAL"
ASUNTO_BORRADOR = "[BORRADOR — NO ENVIAR] Confirmación de inscripción"
MARCADOR_BORRADOR = "BORRADOR — NO ENVIAR"
EMAIL_LOCAL_RE = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}\Z")
EMAIL_DOMAIN_LABEL_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
# Las claves del registro durable son sha256 en hexadecimal. Se validan igual
# antes de construir un path: una clave no debe poder elegir dónde se escribe.
CLAVE_REGISTRO_RE = re.compile(r"[0-9a-f]{64}\Z")
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
class SolicitudConfirmacion:
    id_inscripcion: str
    nombre_destinatario: str
    email_destinatario: str
    actividad: str
    fecha: str
    lugar: str
    organiza: str
    contacto: str


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
    """Puerto sin implementación productiva en HU-012 offline."""

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


@dataclass(frozen=True)
class BorradorRegistrado:
    estado: str
    asunto: str
    cuerpo: str


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
    """Unique semantics de proceso para pruebas y matrices offline."""

    def __init__(self) -> None:
        self._borradores: dict[str, BorradorRegistrado] = {}
        self._lock = Lock()

    def obtener(self, idempotency_key: str) -> BorradorRegistrado | None:
        with self._lock:
            return self._borradores.get(idempotency_key)

    def crear(self, idempotency_key: str, asunto: str, cuerpo: str) -> bool:
        with self._lock:
            if idempotency_key in self._borradores:
                return False
            self._borradores[idempotency_key] = BorradorRegistrado(
                estado="PENDIENTE_VALIDACION", asunto=asunto, cuerpo=cuerpo
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
                estado=hacia, asunto=actual.asunto, cuerpo=actual.cuerpo
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
    """

    def __init__(self, directorio: Path) -> None:
        self._directorio = Path(directorio)
        self._directorio.mkdir(parents=True, exist_ok=True, mode=0o700)

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
        registro = BorradorRegistrado(
            estado="PENDIENTE_VALIDACION", asunto=asunto, cuerpo=cuerpo
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
                        estado=hacia, asunto=actual.asunto, cuerpo=actual.cuerpo
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
    return json.dumps(asdict(registro), ensure_ascii=False, sort_keys=True)


def _leer_registro(contenido: str) -> BorradorRegistrado | None:
    """Un registro ilegible se trata como ausente, no como vacío.

    Devolver un `BorradorRegistrado` con campos por defecto convertiría un
    archivo corrupto en un estado válido, y desde ahí se podría transicionar a
    entrega. Ausente es fail-closed: `crear` va a fallar por `O_EXCL` y la
    inconsistencia sale a la luz en vez de habilitar un envío.
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
    return BorradorRegistrado(estado=estado, asunto=asunto, cuerpo=cuerpo)


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

    Fail-closed en ambas puntas: sin el fake explícito el worker no procesa
    nada (devuelve vacío y la cola queda intacta), y un ítem cuyo registro ya
    no está en `ENVIO_ENCOLADO` (entregada, fallida, rechazada, indeterminada
    o ausente) se descarta sin re-entregar.
    """

    if (
        not isinstance(max_intentos, int)
        or isinstance(max_intentos, bool)
        or max_intentos < 1
    ):
        raise ValueError("presupuesto de reintentos inválido")
    # El mismo candado que `procesar_confirmacion`: la entrega sólo existe
    # contra el fake explícito. Acá no hay Invalida que devolver porque el
    # worker no procesa solicitudes: simplemente no trabaja.
    if type(destino) is not DestinoConfirmacionesFake:
        return ()
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
            or not _email_valido(item.destinatario)
            or item.intentos < 0
        ):
            cola.descartar(clave)
            _auditar_drenaje(
                log_path,
                correlation_id=correlation_id,
                item=item,
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
        "delivery_mode": "fake" if estado == "ENVIADA_SIMULADA" else "none",
        "origen_envio": "asincrono",
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(auditoria, ensure_ascii=False, sort_keys=True) + "\n")


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
    """Genera y opcionalmente entrega sólo a un fake, bajo aprobación explícita.

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
    if not _email_valido(solicitud.email_destinatario):
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
    # entrega exige el fake explícito. Se compara el tipo exacto y no con
    # isinstance, para que una subclase que sí mande correo no pueda pasar por
    # acá. Es el candado que permite tener el ciclo de vida completo
    # implementado sin capacidad real de envío. Una decisión de rechazo no
    # entrega nunca, así que no exige destino.
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
        if not asincrono and type(destino) is not DestinoConfirmacionesFake:
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
    # todavía no existe, la decisión lo materializa primero.
    if existente is None:
        asunto_nuevo, cuerpo_nuevo = _renderizar(solicitud)
        if registro.crear(idempotency_key, asunto_nuevo, cuerpo_nuevo):
            existente = BorradorRegistrado(
                estado="PENDIENTE_VALIDACION",
                asunto=asunto_nuevo,
                cuerpo=cuerpo_nuevo,
            )
        else:
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
    assert type(destino) is DestinoConfirmacionesFake
    try:
        destino.entregar(
            idempotency_key=idempotency_key,
            destinatario=solicitud.email_destinatario,
            asunto=asunto,
            cuerpo=cuerpo,
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
            error="fake_delivery_failed",
            asunto=asunto,
            cuerpo=cuerpo,
            aprobacion=aprobacion,
        )
    registro.transicionar(
        idempotency_key, frozenset({"ENVIO_RESERVADO"}), "ENVIADA_SIMULADA"
    )
    return _finalizar(
        log_path=log_path,
        solicitud=solicitud,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        estado="ENVIADA_SIMULADA",
        asunto=asunto,
        cuerpo=cuerpo,
        aprobacion=aprobacion,
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
    )


def _renderizar(solicitud: SolicitudConfirmacion) -> tuple[str, str]:
    """Arma asunto y cuerpo desde una plantilla fija. No interviene el modelo.

    La confirmación de una inscripción es un texto administrativo: no hay nada
    que redactar y sí un riesgo concreto si un modelo altera un dato. Por eso
    HU-012 es puramente determinista.
    """

    # Un lugar vacío se completa con una frase explícita en vez de dejarse en
    # blanco: el destinatario tiene que ver que el dato falta, no un renglón
    # cortado que parezca un error de sistema.
    lugar = solicitud.lugar.strip() or "A confirmar por la Secretaría de Extensión"
    cuerpo = (
        f"{MARCADOR_BORRADOR}\n\n"
        f"Hola {solicitud.nombre_destinatario.strip()},\n\n"
        f"Registramos tu inscripción a: {solicitud.actividad.strip()}.\n"
        f"Fecha: {solicitud.fecha.strip()}\n"
        f"Lugar: {lugar}\n"
        f"Organiza: {solicitud.organiza.strip()}\n\n"
        "Este texto es una plantilla provisional y requiere validación humana antes de cualquier envío.\n"
        f"Contacto: {solicitud.contacto.strip()}\n"
    )
    return ASUNTO_BORRADOR, cuerpo


def _campos_completos(solicitud: SolicitudConfirmacion) -> bool:
    if ID_RE.fullmatch(solicitud.id_inscripcion) is None:
        return False
    return all(
        isinstance(getattr(solicitud, campo), str)
        and bool(getattr(solicitud, campo).strip())
        for campo in REQUIRED_FIELDS
    )


def _tipos_solicitud_validos(solicitud: SolicitudConfirmacion) -> bool:
    return all(isinstance(valor, str) for valor in asdict(solicitud).values())


def _email_valido(email: object) -> bool:
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
) -> ResultadoConfirmacion:
    # La línea de auditoría no lleva ni el correo del destinatario ni el texto:
    # sólo hashes. `recipient_hash` permite verificar después que se confirmó a
    # la persona correcta, sin guardar el dato personal en un segundo lugar.
    auditoria = {
        "hu": HU,
        "contract_version": CONTRACT_VERSION,
        "template_version": TEMPLATE_VERSION,
        "policy_status": POLICY_STATUS,
        "correlation_id": correlation_id,
        "idempotency_key": idempotency_key,
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
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(auditoria, ensure_ascii=False, sort_keys=True) + "\n")
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
