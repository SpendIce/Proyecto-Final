"""Puerto de persistencia auditable para las ejecuciones del Agente 1.

El módulo guarda sólo referencias opacas y hashes. El contenido de solicitudes,
borradores y prompts permanece en los sistemas que ya son responsables por él.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import re
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from types import MappingProxyType
from typing import Callable, Mapping, Protocol, runtime_checkable


class PersistenciaError(RuntimeError):
    """Error controlado del puerto de persistencia."""


class ConflictoIdempotencia(PersistenciaError):
    """La clave o correlación ya identifica otra operación."""


class EstadoInvalido(PersistenciaError):
    """La transición solicitada viola el ciclo de vida."""


class RegistroNoEncontrado(PersistenciaError):
    """No existe el agregado requerido para la operación."""


class EstadoEjecucion(str, Enum):
    INICIADA = "INICIADA"
    INCOMPLETA = "INCOMPLETA"
    PENDIENTE_VALIDACION = "PENDIENTE_VALIDACION"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"
    FALLIDA = "FALLIDA"


ESTADOS_TERMINALES = frozenset(
    {
        EstadoEjecucion.INCOMPLETA,
        EstadoEjecucion.APROBADA,
        EstadoEjecucion.RECHAZADA,
        EstadoEjecucion.FALLIDA,
    }
)
DECISIONES_VALIDACION = frozenset({"APROBADA", "RECHAZADA"})
SEVERIDADES = frozenset({"BAJA", "MEDIA", "ALTA", "CRITICA"})
FUENTES_TIPO = frozenset({"csv", "fixture", "google_sheets", "jsonl_replay"})
CANALES = frozenset({"gacetilla", "instagram", "linkedin"})
RESULTADOS_POR_ESTADO = {
    EstadoEjecucion.INCOMPLETA: frozenset({"datos_incompletos"}),
    EstadoEjecucion.PENDIENTE_VALIDACION: frozenset({"borrador_generado"}),
    EstadoEjecucion.FALLIDA: frozenset(
        {
            "channel_invalid",
            "destination_failure",
            "error_generacion",
            "policy_incompatible",
            "salida_no_conforme",
            "salida_vacia",
            "source_failure",
            "source_invalid",
            "source_not_renderable",
        }
    ),
}
ERROR_CODES = frozenset(
    {
        "destination_contract_invalid",
        "destination_unavailable",
        "docs_auth_denied",
        "docs_rate_limited",
        "docs_response_invalid",
        "docs_response_too_large",
        "docs_unavailable",
        "docs_update_failed_orphaned",
        "drive_auth_denied",
        "drive_rate_limited",
        "drive_request_too_large",
        "drive_resource_not_found",
        "drive_response_invalid",
        "drive_response_too_large",
        "drive_unavailable",
        "generator_unavailable",
        "sheets_headers_invalid",
        "sheets_row_invalid",
        "source_contract_invalid",
        "source_duplicate_id",
        "source_fact_in_creative_field",
        "source_id_mismatch",
        "source_request_invalid",
        "source_request_not_found",
        "source_status_claim_not_allowed",
        "source_unavailable",
        "workspace_auth_denied",
        "workspace_auth_unavailable",
        "workspace_rate_limited",
        "workspace_response_invalid",
        "workspace_response_too_large",
        "workspace_source_not_found",
        "workspace_unavailable",
    }
)
EVENTO_RESULTADO_POR_ESTADO = {
    EstadoEjecucion.INCOMPLETA: "ejecucion_incompleta",
    EstadoEjecucion.PENDIENTE_VALIDACION: "borrador_generado",
    EstadoEjecucion.FALLIDA: "ejecucion_fallida",
}
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
IDEMPOTENCY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,254}\Z")
HU_RE = re.compile(r"HU-[0-9]{3}\Z")
CODIGO_RE = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")


@dataclass(frozen=True)
class EjecucionNueva:
    id_solicitud: str
    id_ejecucion: str
    idempotency_key: str
    correlation_id: str
    hu: str
    input_hash: str
    fuente_tipo: str
    creada_en: datetime


@dataclass(frozen=True)
class BorradorNuevo:
    id_borrador: str
    referencia_hash: str
    output_hash: str
    canal: str
    creada_en: datetime


@dataclass(frozen=True)
class ResultadoEjecucion:
    id_ejecucion: str
    estado: EstadoEjecucion
    resultado: str
    finalizada_en: datetime
    output_hash: str | None = None
    error_code: str | None = None
    borrador: BorradorNuevo | None = None


@dataclass(frozen=True)
class ValidacionNueva:
    id_validacion: str
    id_borrador: str
    decision: str
    validador_ref_hash: str
    checklist_version: str
    registrada_en: datetime


@dataclass(frozen=True)
class DefectoNuevo:
    id_defecto: str
    id_ejecucion: str
    codigo: str
    severidad: str
    evidencia_hash: str
    creado_en: datetime


@dataclass(frozen=True)
class SolicitudPersistida:
    id_solicitud: str
    input_hash: str
    fuente_tipo: str
    creada_en: datetime
    eliminado_en: datetime | None = None


@dataclass(frozen=True)
class EjecucionPersistida:
    id_ejecucion: str
    id_solicitud: str
    idempotency_key: str
    correlation_id: str
    hu: str
    input_hash: str
    fuente_tipo: str
    estado: EstadoEjecucion
    resultado: str | None
    output_hash: str | None
    error_code: str | None
    creada_en: datetime
    finalizada_en: datetime | None = None
    eliminado_en: datetime | None = None


@dataclass(frozen=True)
class BorradorPersistido:
    id_borrador: str
    id_ejecucion: str
    referencia_hash: str
    output_hash: str
    canal: str
    estado: str
    creada_en: datetime
    eliminado_en: datetime | None = None


@dataclass(frozen=True)
class ValidacionPersistida:
    id_validacion: str
    id_borrador: str
    decision: str
    validador_ref_hash: str
    checklist_version: str
    registrada_en: datetime
    eliminado_en: datetime | None = None


@dataclass(frozen=True)
class DefectoPersistido:
    id_defecto: str
    id_ejecucion: str
    codigo: str
    severidad: str
    evidencia_hash: str
    estado: str
    creado_en: datetime
    cerrado_en: datetime | None = None
    eliminado_en: datetime | None = None


@dataclass(frozen=True)
class EventoPersistido:
    secuencia: int
    id_ejecucion: str
    tipo: str
    ocurrido_en: datetime
    evidencia_hash: str | None = None


@dataclass(frozen=True)
class SnapshotPersistencia:
    solicitudes: Mapping[str, SolicitudPersistida]
    ejecuciones: Mapping[str, EjecucionPersistida]
    borradores: Mapping[str, BorradorPersistido]
    validaciones: Mapping[str, ValidacionPersistida]
    defectos: Mapping[str, DefectoPersistido]
    eventos: tuple[EventoPersistido, ...]


@runtime_checkable
class RepositorioEjecuciones(Protocol):
    """Puerto transaccional centrado en el ciclo de vida de una ejecución."""

    def iniciar(self, nueva: EjecucionNueva) -> EjecucionPersistida: ...

    def completar(self, resultado: ResultadoEjecucion) -> None: ...

    def registrar_validacion(self, validacion: ValidacionNueva) -> None: ...

    def registrar_defecto(self, defecto: DefectoNuevo) -> None: ...

    def obtener_por_idempotencia(self, clave: str) -> EjecucionPersistida | None: ...

    def eliminar_logicamente_anteriores(
        self, *, antes_de: datetime, eliminado_en: datetime
    ) -> int: ...


class InMemoryRepositorioEjecuciones:
    """Adapter determinista para tests, con atomicidad por operación y lock local."""

    def __init__(
        self, *, clock: Callable[[], datetime] | None = None
    ) -> None:
        self._solicitudes: dict[str, SolicitudPersistida] = {}
        self._ejecuciones: dict[str, EjecucionPersistida] = {}
        self._borradores: dict[str, BorradorPersistido] = {}
        self._validaciones: dict[str, ValidacionPersistida] = {}
        self._defectos: dict[str, DefectoPersistido] = {}
        self._eventos: list[EventoPersistido] = []
        self._por_idempotencia: dict[str, str] = {}
        self._por_correlation: dict[str, str] = {}
        self._lock = RLock()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def iniciar(self, nueva: EjecucionNueva) -> EjecucionPersistida:
        _validar_ejecucion_nueva(nueva)
        with self._lock:
            self._validar_no_futuro(nueva.creada_en)
            existente_id = self._por_idempotencia.get(nueva.idempotency_key)
            if existente_id is not None:
                existente = self._ejecuciones[existente_id]
                if _firma_idempotente(existente) != _firma_nueva(nueva):
                    raise ConflictoIdempotencia("idempotency_key reutilizada")
                return existente
            if nueva.id_ejecucion in self._ejecuciones:
                raise ConflictoIdempotencia("id_ejecucion duplicado")
            if nueva.correlation_id in self._por_correlation:
                raise ConflictoIdempotencia("correlation_id duplicado")
            solicitud = self._solicitudes.get(nueva.id_solicitud)
            if solicitud is not None and solicitud.input_hash != nueva.input_hash:
                raise ConflictoIdempotencia("la solicitud cambió su input_hash")
            if solicitud is not None and solicitud.fuente_tipo != nueva.fuente_tipo:
                raise ConflictoIdempotencia("la solicitud cambió su fuente_tipo")
            if solicitud is not None and nueva.creada_en < solicitud.creada_en:
                raise EstadoInvalido(
                    "la ejecución no puede ser anterior a la solicitud existente"
                )

            solicitud_nueva = solicitud or SolicitudPersistida(
                id_solicitud=nueva.id_solicitud,
                input_hash=nueva.input_hash,
                fuente_tipo=nueva.fuente_tipo,
                creada_en=nueva.creada_en,
            )
            ejecucion = EjecucionPersistida(
                id_ejecucion=nueva.id_ejecucion,
                id_solicitud=nueva.id_solicitud,
                idempotency_key=nueva.idempotency_key,
                correlation_id=nueva.correlation_id,
                hu=nueva.hu,
                input_hash=nueva.input_hash,
                fuente_tipo=nueva.fuente_tipo,
                estado=EstadoEjecucion.INICIADA,
                resultado=None,
                output_hash=None,
                error_code=None,
                creada_en=nueva.creada_en,
            )
            self._solicitudes[nueva.id_solicitud] = solicitud_nueva
            self._ejecuciones[nueva.id_ejecucion] = ejecucion
            self._por_idempotencia[nueva.idempotency_key] = nueva.id_ejecucion
            self._por_correlation[nueva.correlation_id] = nueva.id_ejecucion
            self._agregar_evento(nueva.id_ejecucion, "ejecucion_iniciada", nueva.creada_en)
            return ejecucion

    def completar(self, resultado: ResultadoEjecucion) -> None:
        _validar_resultado(resultado)
        with self._lock:
            ejecucion = self._obtener_ejecucion(resultado.id_ejecucion)
            self._validar_no_futuro(resultado.finalizada_en)
            if resultado.borrador is not None:
                self._validar_no_futuro(resultado.borrador.creada_en)
            if ejecucion.estado is not EstadoEjecucion.INICIADA:
                raise EstadoInvalido("sólo una ejecución INICIADA puede completarse")
            if resultado.finalizada_en < ejecucion.creada_en:
                raise EstadoInvalido("la finalización no puede ser anterior al inicio")
            borrador = resultado.borrador
            if borrador is not None and borrador.creada_en < ejecucion.creada_en:
                raise EstadoInvalido("el borrador no puede ser anterior al inicio")
            if borrador is not None and borrador.id_borrador in self._borradores:
                raise ConflictoIdempotencia("id_borrador duplicado")

            ejecucion_actualizada = replace(
                ejecucion,
                estado=resultado.estado,
                resultado=resultado.resultado,
                output_hash=resultado.output_hash,
                error_code=resultado.error_code,
                finalizada_en=resultado.finalizada_en,
            )
            borrador_persistido = None
            if borrador is not None:
                borrador_persistido = BorradorPersistido(
                    id_borrador=borrador.id_borrador,
                    id_ejecucion=resultado.id_ejecucion,
                    referencia_hash=borrador.referencia_hash,
                    output_hash=borrador.output_hash,
                    canal=borrador.canal,
                    estado="PENDIENTE_VALIDACION",
                    creada_en=borrador.creada_en,
                )

            self._ejecuciones[resultado.id_ejecucion] = ejecucion_actualizada
            if borrador_persistido is not None:
                self._borradores[borrador_persistido.id_borrador] = borrador_persistido
            self._agregar_evento(
                resultado.id_ejecucion,
                EVENTO_RESULTADO_POR_ESTADO[resultado.estado],
                resultado.finalizada_en,
                resultado.output_hash,
            )

    def registrar_validacion(self, validacion: ValidacionNueva) -> None:
        _validar_validacion(validacion)
        with self._lock:
            if validacion.id_validacion in self._validaciones:
                raise ConflictoIdempotencia("id_validacion duplicado")
            borrador = self._borradores.get(validacion.id_borrador)
            if borrador is None:
                raise RegistroNoEncontrado("borrador inexistente")
            ejecucion = self._obtener_ejecucion(borrador.id_ejecucion)
            self._validar_no_futuro(validacion.registrada_en)
            instante_minimo = max(
                borrador.creada_en,
                ejecucion.finalizada_en or ejecucion.creada_en,
            )
            if validacion.registrada_en < instante_minimo:
                raise EstadoInvalido("la validación no puede ser anterior al borrador")
            if (
                borrador.estado != "PENDIENTE_VALIDACION"
                or ejecucion.estado is not EstadoEjecucion.PENDIENTE_VALIDACION
            ):
                raise EstadoInvalido("el borrador ya no admite validación")
            estado_borrador = "APROBADO" if validacion.decision == "APROBADA" else "RECHAZADO"
            estado_ejecucion = EstadoEjecucion(validacion.decision)
            persistida = ValidacionPersistida(**vars(validacion))

            self._validaciones[validacion.id_validacion] = persistida
            self._borradores[borrador.id_borrador] = replace(
                borrador, estado=estado_borrador
            )
            self._ejecuciones[ejecucion.id_ejecucion] = replace(
                ejecucion, estado=estado_ejecucion
            )
            self._agregar_evento(
                ejecucion.id_ejecucion,
                f"validacion_{validacion.decision.lower()}",
                validacion.registrada_en,
                validacion.validador_ref_hash,
            )

    def registrar_defecto(self, defecto: DefectoNuevo) -> None:
        _validar_defecto(defecto)
        with self._lock:
            ejecucion = self._obtener_ejecucion(defecto.id_ejecucion)
            self._validar_no_futuro(defecto.creado_en)
            if defecto.creado_en < ejecucion.creada_en:
                raise EstadoInvalido("el defecto no puede ser anterior a la ejecución")
            if defecto.id_defecto in self._defectos:
                raise ConflictoIdempotencia("id_defecto duplicado")
            self._defectos[defecto.id_defecto] = DefectoPersistido(
                **vars(defecto), estado="ABIERTO"
            )
            self._agregar_evento(
                defecto.id_ejecucion,
                "defecto_registrado",
                defecto.creado_en,
                defecto.evidencia_hash,
            )

    def obtener_por_idempotencia(self, clave: str) -> EjecucionPersistida | None:
        with self._lock:
            identificador = self._por_idempotencia.get(clave)
            return self._ejecuciones.get(identificador) if identificador else None

    def eliminar_logicamente_anteriores(
        self, *, antes_de: datetime, eliminado_en: datetime
    ) -> int:
        _validar_timestamp(antes_de)
        _validar_timestamp(eliminado_en)
        with self._lock:
            if eliminado_en < antes_de:
                raise ValueError("la eliminación no puede ser anterior al corte")
            self._validar_no_futuro(antes_de)
            self._validar_no_futuro(eliminado_en)
            candidatas = [
                ejecucion
                for ejecucion in self._ejecuciones.values()
                if ejecucion.finalizada_en is not None
                and ejecucion.estado in ESTADOS_TERMINALES
                and ejecucion.finalizada_en < antes_de
                and ejecucion.eliminado_en is None
            ]
            for ejecucion in candidatas:
                self._ejecuciones[ejecucion.id_ejecucion] = replace(
                    ejecucion, eliminado_en=eliminado_en
                )
                for identificador, borrador in tuple(self._borradores.items()):
                    if borrador.id_ejecucion == ejecucion.id_ejecucion:
                        self._borradores[identificador] = replace(
                            borrador, eliminado_en=eliminado_en
                        )
                        for validacion_id, validacion in tuple(
                            self._validaciones.items()
                        ):
                            if validacion.id_borrador == identificador:
                                self._validaciones[validacion_id] = replace(
                                    validacion, eliminado_en=eliminado_en
                                )
                for identificador, defecto in tuple(self._defectos.items()):
                    if defecto.id_ejecucion == ejecucion.id_ejecucion:
                        self._defectos[identificador] = replace(
                            defecto, eliminado_en=eliminado_en
                        )
                self._agregar_evento(
                    ejecucion.id_ejecucion,
                    "retencion_eliminacion_logica",
                    eliminado_en,
                )
            for solicitud_id, solicitud in tuple(self._solicitudes.items()):
                relacionadas = [
                    ejecucion
                    for ejecucion in self._ejecuciones.values()
                    if ejecucion.id_solicitud == solicitud_id
                ]
                if relacionadas and all(e.eliminado_en is not None for e in relacionadas):
                    self._solicitudes[solicitud_id] = replace(
                        solicitud, eliminado_en=eliminado_en
                    )
            return len(candidatas)

    def snapshot(self) -> SnapshotPersistencia:
        with self._lock:
            return SnapshotPersistencia(
                solicitudes=MappingProxyType(dict(self._solicitudes)),
                ejecuciones=MappingProxyType(dict(self._ejecuciones)),
                borradores=MappingProxyType(dict(self._borradores)),
                validaciones=MappingProxyType(dict(self._validaciones)),
                defectos=MappingProxyType(dict(self._defectos)),
                eventos=tuple(self._eventos),
            )

    def _obtener_ejecucion(self, identificador: str) -> EjecucionPersistida:
        try:
            return self._ejecuciones[identificador]
        except KeyError as error:
            raise RegistroNoEncontrado("ejecución inexistente") from error

    def _agregar_evento(
        self,
        id_ejecucion: str,
        tipo: str,
        ocurrido_en: datetime,
        evidencia_hash: str | None = None,
    ) -> None:
        self._eventos.append(
            EventoPersistido(
                secuencia=len(self._eventos) + 1,
                id_ejecucion=id_ejecucion,
                tipo=tipo,
                ocurrido_en=ocurrido_en,
                evidencia_hash=evidencia_hash,
            )
        )

    def _validar_no_futuro(self, valor: datetime) -> None:
        ahora = self._clock()
        _validar_timestamp(ahora)
        if valor > ahora:
            raise ValueError("el timestamp no puede estar en el futuro")


def _validar_ejecucion_nueva(nueva: EjecucionNueva) -> None:
    for valor in (nueva.id_solicitud, nueva.id_ejecucion, nueva.correlation_id):
        _validar_patron(valor, ID_RE, "identificador")
    _validar_patron(nueva.idempotency_key, IDEMPOTENCY_RE, "idempotency_key")
    _validar_patron(nueva.hu, HU_RE, "HU")
    if nueva.fuente_tipo not in FUENTES_TIPO:
        raise ValueError("fuente_tipo inválida")
    _validar_hash(nueva.input_hash)
    _validar_timestamp(nueva.creada_en)


def _validar_resultado(resultado: ResultadoEjecucion) -> None:
    _validar_patron(resultado.id_ejecucion, ID_RE, "id_ejecucion")
    _validar_timestamp(resultado.finalizada_en)
    if not isinstance(resultado.estado, EstadoEjecucion):
        raise ValueError("estado de ejecución inválido")
    if resultado.estado is EstadoEjecucion.INICIADA:
        raise EstadoInvalido("INICIADA no es un resultado")
    permitidos = RESULTADOS_POR_ESTADO.get(resultado.estado, frozenset())
    if resultado.resultado not in permitidos:
        raise ValueError("resultado no permitido para el estado")
    if resultado.error_code is not None and resultado.error_code not in ERROR_CODES:
        raise ValueError("error_code no permitido")
    if resultado.estado is EstadoEjecucion.PENDIENTE_VALIDACION:
        if resultado.borrador is None or resultado.output_hash is None:
            raise EstadoInvalido("el estado pendiente requiere borrador y output_hash")
        if resultado.error_code is not None:
            raise EstadoInvalido("un borrador pendiente no puede registrar error_code")
    elif resultado.borrador is not None:
        raise EstadoInvalido("un estado no publicable no puede crear borrador")
    elif resultado.output_hash is not None:
        raise EstadoInvalido("un estado sin borrador no puede registrar output_hash")
    if resultado.estado is EstadoEjecucion.INCOMPLETA and resultado.error_code is not None:
        raise EstadoInvalido("una solicitud incompleta no puede registrar error_code")
    if resultado.output_hash is not None:
        _validar_hash(resultado.output_hash)
    if resultado.borrador is not None:
        borrador = resultado.borrador
        _validar_patron(borrador.id_borrador, ID_RE, "id_borrador")
        if borrador.canal not in CANALES:
            raise ValueError("canal inválido")
        _validar_hash(borrador.referencia_hash)
        _validar_hash(borrador.output_hash)
        _validar_timestamp(borrador.creada_en)
        if borrador.output_hash != resultado.output_hash:
            raise EstadoInvalido("los output_hash no coinciden")


def _validar_validacion(validacion: ValidacionNueva) -> None:
    for valor in (validacion.id_validacion, validacion.id_borrador):
        _validar_patron(valor, ID_RE, "identificador de validación")
    _validar_patron(validacion.checklist_version, CODIGO_RE, "checklist_version")
    if validacion.decision not in DECISIONES_VALIDACION:
        raise ValueError("decisión de validación inválida")
    _validar_hash(validacion.validador_ref_hash)
    _validar_timestamp(validacion.registrada_en)


def _validar_defecto(defecto: DefectoNuevo) -> None:
    for valor in (defecto.id_defecto, defecto.id_ejecucion):
        _validar_patron(valor, ID_RE, "identificador de defecto")
    _validar_patron(defecto.codigo, CODIGO_RE, "código de defecto")
    if defecto.severidad not in SEVERIDADES:
        raise ValueError("severidad inválida")
    _validar_hash(defecto.evidencia_hash)
    _validar_timestamp(defecto.creado_en)


def _validar_patron(valor: str, patron: re.Pattern[str], nombre: str) -> None:
    if not isinstance(valor, str) or patron.fullmatch(valor) is None:
        raise ValueError(f"{nombre} inválido")


def _validar_hash(valor: str) -> None:
    if len(valor) != 64 or any(caracter not in "0123456789abcdef" for caracter in valor):
        raise ValueError("se requiere hash SHA-256 hexadecimal")


def _validar_timestamp(valor: datetime) -> None:
    if not isinstance(valor, datetime) or valor.tzinfo is None or valor.utcoffset() is None:
        raise ValueError("el timestamp debe incluir zona horaria")


def _firma_nueva(nueva: EjecucionNueva) -> tuple[str, ...]:
    return (
        nueva.id_solicitud,
        nueva.idempotency_key,
        nueva.correlation_id,
        nueva.hu,
        nueva.input_hash,
        nueva.fuente_tipo,
    )


def _firma_idempotente(ejecucion: EjecucionPersistida) -> tuple[str, ...]:
    return (
        ejecucion.id_solicitud,
        ejecucion.idempotency_key,
        ejecucion.correlation_id,
        ejecucion.hu,
        ejecucion.input_hash,
        ejecucion.fuente_tipo,
    )
