from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from typing import Protocol
import uuid

from .destinos import DestinoBorradores, DestinoBorradoresError, ReferenciaBorrador
from .fuentes import FuenteSolicitudes
from .google_workspace import (
    AccessTokenProvider,
    GoogleDrivePlantillaDestinoBorradores,
    GoogleSheetsFuenteSolicitudes,
    MAX_WORKSPACE_RESPONSE_BYTES,
    TransporteHttp,
)
from .posts import (
    STRUCTURED_OUTPUT_CONTRACT_VERSION,
    STRUCTURED_RENDERER_VERSION,
    procesar_post_estructurado,
)
from .procesamiento import Generator, ResultadoProceso, procesar_solicitud
from .workspace_config import ConfiguracionWorkspace


MANIFEST_VERSION = "workspace_e2e_manifest_v1"
IDEMPOTENCY_VERSION = "workspace_e2e_idempotency_v1"
_ESTADOS_TERMINALES = frozenset({"COMPLETE", "UNCERTAIN", "IN_PROGRESS"})
RECOVERY_POLICY = "manual_only"
_PIPELINE_VERSIONS = {
    "gacetilla": {
        "pipeline_version": "workspace_hu010_gacetilla_v1",
        "contract_version": "gacetilla_input_v1",
        "renderer_version": "gacetilla_generator_render_v2",
    },
    "post": {
        "pipeline_version": "workspace_hu011_structured_v2",
        "contract_version": f"post_input_v1+{STRUCTURED_OUTPUT_CONTRACT_VERSION}",
        "renderer_version": STRUCTURED_RENDERER_VERSION,
    },
}


class RunnerWorkspaceError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ResultadoWorkspaceE2E:
    estado: str
    correlation_id: str
    manifest_path: Path
    duplicada: bool = False
    reconciliation_ref_hash: str | None = None


class FuenteMemoria(FuenteSolicitudes):
    """Fake offline explícito; conserva la fila sólo durante el proceso."""

    def __init__(self, fila: dict[str, str]) -> None:
        self._fila = dict(fila)
        self.invocaciones = 0

    def obtener(self, id_solicitud: str) -> dict[str, str]:
        self.invocaciones += 1
        return dict(self._fila)


class DestinoMemoria(DestinoBorradores):
    """Fake offline: nunca escribe ni contacta servicios externos."""

    def __init__(self) -> None:
        self.invocaciones = 0
        self.output_hash: str | None = None

    def guardar(self, id_solicitud: str, contenido: str) -> ReferenciaBorrador:
        self.invocaciones += 1
        self.output_hash = _hash(contenido)
        return ReferenciaBorrador(
            tipo="memory_fake",
            referencia=f"mem-{self.output_hash[:24]}",
        )


class RegistroIdempotencia(Protocol):
    def consultar(self, key_hash: str) -> dict[str, object] | None: ...
    def reservar(self, key_hash: str) -> bool: ...
    def guardar(self, key_hash: str, registro: dict[str, object]) -> None: ...
    def liberar(self, key_hash: str) -> None: ...


class RegistroIdempotenciaMemoria:
    def __init__(self) -> None:
        self._registros: dict[str, dict[str, object]] = {}

    def consultar(self, key_hash: str) -> dict[str, object] | None:
        registro = self._registros.get(key_hash)
        return dict(registro) if registro is not None else None

    def reservar(self, key_hash: str) -> bool:
        if key_hash in self._registros:
            return False
        self._registros[key_hash] = _registro_idempotencia("IN_PROGRESS")
        return True

    def guardar(self, key_hash: str, registro: dict[str, object]) -> None:
        self._registros[key_hash] = dict(registro)

    def liberar(self, key_hash: str) -> None:
        self._registros.pop(key_hash, None)


class RegistroIdempotenciaArchivo:
    """Registro fail-closed con reserva atómica y archivos privados."""

    def __init__(self, directorio: Path) -> None:
        self._directorio = directorio.resolve()

    def _path(self, key_hash: str) -> Path:
        if len(key_hash) != 64 or any(c not in "0123456789abcdef" for c in key_hash):
            raise RunnerWorkspaceError("runner_idempotency_key_invalid")
        return self._directorio / f"{key_hash}.json"

    def consultar(self, key_hash: str) -> dict[str, object] | None:
        path = self._path(key_hash)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {"status": "UNCERTAIN", "error_code": "idempotency_record_invalid"}
        if not _registro_persistido_valido(payload):
            return _registro_idempotencia(
                "UNCERTAIN", error_code="idempotency_record_invalid"
            )
        return payload

    def reservar(self, key_hash: str) -> bool:
        self._directorio.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self._directorio, 0o700)
            descriptor = os.open(
                self._path(key_hash),
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            return False
        except OSError as exc:
            raise RunnerWorkspaceError("runner_idempotency_unavailable") from exc
        try:
            contenido = json.dumps(
                _registro_idempotencia("IN_PROGRESS"),
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
            os.write(descriptor, contenido)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return True

    def guardar(self, key_hash: str, registro: dict[str, object]) -> None:
        path = self._path(key_hash)
        temporal = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            descriptor = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                os.write(
                    descriptor,
                    json.dumps(registro, ensure_ascii=False, sort_keys=True).encode("utf-8"),
                )
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.replace(temporal, path)
            os.chmod(path, 0o600)
        except OSError as exc:
            try:
                temporal.unlink(missing_ok=True)
            except OSError:
                pass
            raise RunnerWorkspaceError("runner_idempotency_unavailable") from exc

    def liberar(self, key_hash: str) -> None:
        try:
            self._path(key_hash).unlink(missing_ok=True)
        except OSError as exc:
            raise RunnerWorkspaceError("runner_idempotency_unavailable") from exc


class _DestinoIdempotente:
    def __init__(self, destino: DestinoBorradores, registro: RegistroIdempotencia, key_hash: str) -> None:
        self._destino = destino
        self._registro = registro
        self._key_hash = key_hash
        self.duplicada = False
        self.conflicto: dict[str, object] | None = None

    def guardar(self, id_solicitud: str, contenido: str) -> ReferenciaBorrador:
        if not self._registro.reservar(self._key_hash):
            self.conflicto = self._registro.consultar(self._key_hash) or _registro_idempotencia(
                "UNCERTAIN", error_code="idempotency_record_unavailable"
            )
            self.duplicada = self.conflicto.get("status") == "COMPLETE"
            raise DestinoBorradoresError("destination_unavailable")
        try:
            referencia = self._destino.guardar(id_solicitud, contenido)
        except DestinoBorradoresError as exc:
            self._registro.guardar(
                self._key_hash,
                _registro_idempotencia(
                    "UNCERTAIN",
                    reconciliation_ref_hash=exc.reconciliation_ref_hash,
                    error_code=exc.code,
                ),
            )
            raise
        except Exception:
            self._registro.guardar(
                self._key_hash,
                _registro_idempotencia("UNCERTAIN", error_code="destination_unavailable"),
            )
            raise
        self._registro.guardar(
            self._key_hash,
            _registro_idempotencia(
                "COMPLETE",
                destination_type=referencia.tipo,
                destination_ref_hash=_hash(referencia.referencia),
            ),
        )
        return referencia


def ejecutar_workspace_e2e(
    *,
    tipo: str,
    canal: str | None,
    id_solicitud: str,
    fuente: FuenteSolicitudes,
    generator: Generator,
    destino: DestinoBorradores,
    directorio_salida: Path,
    registro: RegistroIdempotencia,
    ambiente: str = "OFFLINE",
    live: bool = False,
) -> ResultadoWorkspaceE2E:
    _validar_solicitud_runner(tipo=tipo, canal=canal, ambiente=ambiente, live=live)
    versiones = _PIPELINE_VERSIONS[tipo]
    key_hash = _idempotency_key(
        tipo=tipo,
        canal=canal,
        id_solicitud=id_solicitud,
        ambiente=ambiente,
        versiones=versiones,
    )
    previo = registro.consultar(key_hash)
    if previo is not None:
        correlation_id = str(uuid.uuid4())
        reconciliation_ref_hash = _hash_opcional(previo.get("reconciliation_ref_hash"))
        completa = previo.get("status") == "COMPLETE"
        estado_previo = "DUPLICADA" if completa else "BLOQUEADA_RECONCILIACION"
        manifest_path = _guardar_manifest(
            directorio_salida=directorio_salida,
            correlation_id=correlation_id,
            key_hash=key_hash,
            id_solicitud=id_solicitud,
            ambiente=ambiente,
            live=live,
            tipo=tipo,
            canal=canal,
            estado=estado_previo,
            destination=previo,
            duplicada=completa,
            versiones=versiones,
        )
        return ResultadoWorkspaceE2E(
            estado=estado_previo,
            correlation_id=correlation_id,
            manifest_path=manifest_path,
            duplicada=completa,
            reconciliation_ref_hash=reconciliation_ref_hash,
        )

    destino_idempotente = _DestinoIdempotente(destino, registro, key_hash)
    if tipo == "gacetilla":
        resultado_core = procesar_solicitud(
            fuente=fuente,
            id_solicitud=id_solicitud,
            directorio_salida=directorio_salida,
            generator=generator,
            destino=destino_idempotente,
        )
        hu = "HU-010"
    else:
        resultado_core = procesar_post_estructurado(
            fuente=fuente,
            id_solicitud=id_solicitud,
            canal=canal or "",
            directorio_salida=directorio_salida,
            generator=generator,
            destino=destino_idempotente,
        )
        hu = "HU-011"

    registro_destino = destino_idempotente.conflicto or registro.consultar(key_hash)
    duplicada = destino_idempotente.duplicada
    if destino_idempotente.conflicto is not None and not duplicada:
        estado = "BLOQUEADA_RECONCILIACION"
    elif duplicada:
        estado = "DUPLICADA"
    else:
        estado = resultado_core.estado
    reconciliation_ref_hash = _hash_opcional(
        (registro_destino or {}).get("reconciliation_ref_hash")
    )
    manifest_path = _guardar_manifest(
        directorio_salida=directorio_salida,
        correlation_id=resultado_core.correlation_id,
        key_hash=key_hash,
        id_solicitud=id_solicitud,
        ambiente=ambiente,
        live=live,
        tipo=tipo,
        canal=canal,
        estado=estado,
        destination=registro_destino,
        duplicada=duplicada,
        hu=hu,
        core_error=resultado_core.error is not None,
        versiones=versiones,
    )
    return ResultadoWorkspaceE2E(
        estado=estado,
        correlation_id=resultado_core.correlation_id,
        manifest_path=manifest_path,
        duplicada=duplicada,
        reconciliation_ref_hash=reconciliation_ref_hash,
    )


def crear_dependencias_workspace_live(
    *,
    habilitar_live: bool,
    confirmar_escritura: bool,
    config: ConfiguracionWorkspace,
    token_provider: AccessTokenProvider,
    transport: TransporteHttp | None = None,
) -> tuple[GoogleSheetsFuenteSolicitudes, GoogleDrivePlantillaDestinoBorradores]:
    if habilitar_live is not True:
        raise RunnerWorkspaceError("runner_live_not_enabled")
    if confirmar_escritura is not True:
        raise RunnerWorkspaceError("runner_live_write_not_confirmed")
    if (
        not isinstance(config, ConfiguracionWorkspace)
        or config.ambiente not in {"D2", "D3"}
        or config.max_response_bytes != MAX_WORKSPACE_RESPONSE_BYTES
    ):
        raise RunnerWorkspaceError("runner_live_config_invalid")
    try:
        token = token_provider.obtener_access_token()
    except Exception:
        raise RunnerWorkspaceError("runner_live_auth_unavailable") from None
    if not isinstance(token, str) or not token.strip() or token != token.strip() or "\n" in token or "\r" in token:
        raise RunnerWorkspaceError("runner_live_auth_unavailable")
    try:
        return (
            GoogleSheetsFuenteSolicitudes(
                spreadsheet_id=config.spreadsheet_id,
                rango_a1=config.rango_a1,
                token_provider=token_provider,
                transport=transport,
                timeout_s=config.timeout_s,
            ),
            GoogleDrivePlantillaDestinoBorradores(
                plantilla_id=config.template_id,
                carpeta_id=config.folder_id,
                token_provider=token_provider,
                transport=transport,
                timeout_s=config.timeout_s,
            ),
        )
    except ValueError:
        raise RunnerWorkspaceError("runner_live_config_invalid") from None


def _validar_solicitud_runner(*, tipo: str, canal: str | None, ambiente: str, live: bool) -> None:
    if tipo not in {"gacetilla", "post"}:
        raise RunnerWorkspaceError("runner_type_invalid")
    if tipo == "post" and canal not in {"instagram", "linkedin"}:
        raise RunnerWorkspaceError("runner_channel_required")
    if tipo == "gacetilla" and canal is not None:
        raise RunnerWorkspaceError("runner_channel_not_allowed")
    if not isinstance(ambiente, str) or not ambiente or len(ambiente) > 32:
        raise RunnerWorkspaceError("runner_environment_invalid")
    if not isinstance(live, bool):
        raise RunnerWorkspaceError("runner_mode_invalid")
    if live and ambiente not in {"D2", "D3"}:
        raise RunnerWorkspaceError("runner_live_environment_invalid")


def _idempotency_key(
    *,
    tipo: str,
    canal: str | None,
    id_solicitud: str,
    ambiente: str,
    versiones: dict[str, str],
) -> str:
    return _hash(
        json.dumps(
            {
                "version": IDEMPOTENCY_VERSION,
                "tipo": tipo,
                "canal": canal,
                "request_ref_hash": _hash(id_solicitud) if isinstance(id_solicitud, str) else None,
                "ambiente": ambiente,
                "pipeline_version": versiones["pipeline_version"],
                "contract_version": versiones["contract_version"],
                "renderer_version": versiones["renderer_version"],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def _registro_idempotencia(
    status: str,
    *,
    destination_type: str | None = None,
    destination_ref_hash: str | None = None,
    reconciliation_ref_hash: str | None = None,
    error_code: str | None = None,
) -> dict[str, object]:
    return {
        "version": IDEMPOTENCY_VERSION,
        "status": status,
        "destination_type": destination_type,
        "destination_ref_hash": destination_ref_hash,
        "reconciliation_ref_hash": reconciliation_ref_hash,
        "error_code": error_code,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "recovery_policy": RECOVERY_POLICY,
    }


def _guardar_manifest(
    *,
    directorio_salida: Path,
    correlation_id: str,
    key_hash: str,
    id_solicitud: str,
    ambiente: str,
    live: bool,
    tipo: str,
    canal: str | None,
    estado: str,
    destination: dict[str, object] | None,
    duplicada: bool,
    hu: str | None = None,
    core_error: bool = False,
    versiones: dict[str, str],
) -> Path:
    destination = destination or {}
    payload = {
        "schema_version": MANIFEST_VERSION,
        "execution_ref": correlation_id,
        "core_correlation_id": correlation_id,
        "idempotency_key_hash": key_hash,
        "request_ref_hash": _hash(id_solicitud),
        "ambiente": ambiente,
        "modo": "live_write_opt_in" if live else "offline_fake",
        "tipo": tipo,
        "canal": canal,
        "pipeline_version": versiones["pipeline_version"],
        "contract_version": versiones["contract_version"],
        "renderer_version": versiones["renderer_version"],
        "recovery_policy": RECOVERY_POLICY,
        "HU": hu or ("HU-010" if tipo == "gacetilla" else "HU-011"),
        "estado": estado,
        "duplicada": duplicada,
        "core_error": core_error,
        "destination": {
            "status": destination.get("status", "NOT_INVOKED"),
            "type": _etiqueta_segura(destination.get("destination_type")),
            "ref_hash": _hash_opcional(destination.get("destination_ref_hash")),
            "reconciliation_ref_hash": _hash_opcional(destination.get("reconciliation_ref_hash")),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    manifests = (directorio_salida / "manifests").resolve()
    manifests.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(manifests, 0o700)
    path = manifests / f"{correlation_id}.json"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(
            descriptor,
            (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"),
        )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return path


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


def _hash_opcional(valor: object) -> str | None:
    if isinstance(valor, str) and len(valor) == 64 and all(c in "0123456789abcdef" for c in valor):
        return valor
    return None


def _etiqueta_segura(valor: object) -> str | None:
    if isinstance(valor, str) and re.fullmatch(r"[a-z0-9][a-z0-9_]{0,63}", valor):
        return valor
    return None


def _registro_persistido_valido(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("version") != IDEMPOTENCY_VERSION:
        return False
    if payload.get("status") not in _ESTADOS_TERMINALES:
        return False
    if payload.get("recovery_policy") != RECOVERY_POLICY:
        return False
    actualizado = payload.get("updated_at")
    if not isinstance(actualizado, str):
        return False
    try:
        instante = datetime.fromisoformat(actualizado)
    except ValueError:
        return False
    if instante.tzinfo is None:
        return False
    # No hay takeover automático: incluso un lease antiguo requiere
    # reconciliación manual. Sólo rechazamos relojes futuros/corruptos.
    if instante > datetime.now(timezone.utc) + timedelta(seconds=5):
        return False
    if payload["status"] == "COMPLETE":
        if _hash_opcional(payload.get("destination_ref_hash")) is None:
            return False
        if _etiqueta_segura(payload.get("destination_type")) is None:
            return False
    reconciliation = payload.get("reconciliation_ref_hash")
    if reconciliation is not None and _hash_opcional(reconciliation) is None:
        return False
    return True
