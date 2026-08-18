"""Slice offline de HU-012: borradores de confirmación, nunca correo real."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
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
    """Genera y opcionalmente entrega sólo a un fake, bajo aprobación explícita."""

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
