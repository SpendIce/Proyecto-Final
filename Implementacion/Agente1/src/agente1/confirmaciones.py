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

Estados: `PENDIENTE_VALIDACION` → `APROBADA` | `RECHAZADA`, y de `APROBADA` →
`ENVIO_RESERVADO` → `ENVIADA_SIMULADA` | `FALLIDA`. El paso intermedio
`ENVIO_RESERVADO` existe para que una caída durante la entrega no deje el
registro en un estado que habilite reintentar y mandar dos veces.

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
    """Decisión humana registrada. Sin esto no hay envío posible.

    Exige quién decidió (`validador`), con qué rol y cuándo, con zona horaria
    obligatoria: una aprobación sin responsable identificable no sirve como
    evidencia. Sólo se guarda su hash en el log, no los datos de la persona.
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
    """Escribe por reemplazo para que nadie lea un registro a medio escribir."""

    temporal = ruta.with_suffix(".json.tmp")
    descriptor = os.open(temporal, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
        archivo.write(_serializar_registro(registro))
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
    if enviar and aprobacion is None:
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="INVALIDA",
            error="approval_required",
        )
    # Control central de la HU: sólo se entrega a un fake. Se compara el tipo
    # exacto y no con isinstance, para que una subclase que sí mande correo no
    # pueda pasar por acá. Es el candado que permite tener el ciclo de vida
    # completo implementado sin capacidad real de envío.
    if (
        enviar
        and aprobacion is not None
        and aprobacion.aprobada
        and type(destino) is not DestinoConfirmacionesFake
    ):
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="INVALIDA",
            error="offline_destination_required",
        )

    existente = registro.obtener(idempotency_key)
    creado = existente is None
    if existente is None:
        asunto_nuevo, cuerpo_nuevo = _renderizar(solicitud)
        if registro.crear(idempotency_key, asunto_nuevo, cuerpo_nuevo):
            existente = BorradorRegistrado(
                estado="PENDIENTE_VALIDACION",
                asunto=asunto_nuevo,
                cuerpo=cuerpo_nuevo,
            )
        else:
            creado = False
            existente = registro.obtener(idempotency_key)
    if existente is None:
        raise RuntimeError("registro de idempotencia inconsistente")
    asunto, cuerpo = existente.asunto, existente.cuerpo

    if aprobacion is None:
        if not creado:
            return _duplicada(
                log_path, solicitud, correlation_id, idempotency_key
            )
        return _finalizar(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="PENDIENTE_VALIDACION",
            asunto=asunto,
            cuerpo=cuerpo,
        )

    if not aprobacion.aprobada:
        if not registro.transicionar(
            idempotency_key, frozenset({"PENDIENTE_VALIDACION"}), "RECHAZADA"
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

    if existente.estado == "PENDIENTE_VALIDACION":
        if not registro.transicionar(
            idempotency_key, frozenset({"PENDIENTE_VALIDACION"}), "APROBADA"
        ):
            return _duplicada(log_path, solicitud, correlation_id, idempotency_key)
    elif existente.estado != "APROBADA":
        return _duplicada(log_path, solicitud, correlation_id, idempotency_key)

    if not enviar:
        return _finalizar(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="APROBADA",
            asunto=asunto,
            cuerpo=cuerpo,
            aprobacion=aprobacion,
        )

    # Reserva del envío antes de intentarlo: si el proceso muere en la entrega,
    # el registro queda en ENVIO_RESERVADO y un reintento no vuelve a entregar,
    # porque ya no está en APROBADA. Se prefiere una confirmación no enviada a
    # una enviada dos veces.
    if not registro.transicionar(
        idempotency_key,
        frozenset({"APROBADA"}),
        "ENVIO_RESERVADO",
    ):
        return _duplicada(log_path, solicitud, correlation_id, idempotency_key)
    if enviar:
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
        or not aprobacion.rol.strip()
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
    entrada = json.dumps(
        asdict(solicitud),
        ensure_ascii=False,
        sort_keys=True,
        default=lambda valor: f"<invalid:{type(valor).__name__}>",
    )
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
        "input_hash": _hash(entrada),
        "recipient_hash": _hash(solicitud.email_destinatario),
        "output_hash": _hash((asunto or "") + "\n" + (cuerpo or "")),
        "human_decision_present": aprobacion is not None,
        "human_decision_hash": _hash(
            json.dumps(asdict(aprobacion), ensure_ascii=False, sort_keys=True)
        )
        if aprobacion is not None
        else None,
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
