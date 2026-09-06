"""Runner de punta a punta: planilla → generación → documento, con manifest.

Envuelve los pipelines de HU-010/HU-011 y agrega lo que hace falta para
ejecutarlos contra servicios reales sin riesgo de duplicar una comunicación:
control de idempotencia y un manifest sanitizado por ejecución.

**Idempotencia fail-closed.** La clave se deriva de tipo, canal, solicitud,
ambiente y versiones de pipeline/contrato/renderer. Antes de escribir se
*reserva* la clave creando un archivo con `O_EXCL` —operación atómica del
sistema de archivos, sin condición de carrera— y recién después se llama al
destino. Si la reserva ya existe, no se genera nada.

**No hay takeover automático.** Si una ejecución quedó `IN_PROGRESS` (se cortó
la luz, se mató el proceso), ninguna corrida posterior la retoma por más viejo
que sea el registro: queda `BLOQUEADA_RECONCILIACION` hasta que una persona
mire qué pasó. Un reintento automático podría dejar dos documentos para la
misma solicitud, y en comunicación institucional un duplicado es peor que una
demora. Esa es la política declarada en `RECOVERY_POLICY = "manual_only"`.

**Modo live con doble opt-in.** Salir a Workspace real exige dos banderas
explícitas (`habilitar_live` y `confirmar_escritura`), ambiente D2/D3 y
configuración completa y válida. El default es offline con fakes.

**El manifest no copia nada.** Guarda hashes, códigos y versiones: ni el
identificador de la solicitud, ni el del documento, ni el contenido. Está
pensado para ser adjuntable como evidencia sin volverse un canal de fuga.
"""

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
# Estados que un registro de idempotencia puede tener en disco. `IN_PROGRESS`
# está incluido a propósito: una reserva sin cerrar es un estado válido y
# bloqueante, no un archivo corrupto que se pueda descartar.
_ESTADOS_TERMINALES = frozenset({"COMPLETE", "UNCERTAIN", "IN_PROGRESS"})
# Política de recuperación declarada en cada manifest: toda reconciliación es
# manual. Ver el docstring del módulo.
RECOVERY_POLICY = "manual_only"
# Las versiones entran en la clave de idempotencia: cambiar el prompt, el
# contrato o el renderer habilita legítimamente una nueva ejecución de la misma
# solicitud, porque el resultado esperado ya no es el mismo.
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
    """Resultado del runner.

    `estado` puede ser el del pipeline (`PENDIENTE_VALIDACION`, `INCOMPLETA`,
    …) o uno propio del runner: `DUPLICADA` (ya existía un borrador para esta
    clave) y `BLOQUEADA_RECONCILIACION` (hay una ejecución previa sin cerrar y
    hace falta que una persona la revise).
    """

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
    """Puerto del registro de idempotencia.

    `reservar` debe ser atómico y devolver `False` —no levantar— cuando la
    clave ya existe: es lo que convierte a este puerto en un candado. `liberar`
    existe sólo para pruebas y limpieza manual; el runner nunca libera una
    reserva por su cuenta.
    """

    def consultar(self, key_hash: str) -> dict[str, object] | None: ...
    def reservar(self, key_hash: str) -> bool: ...
    def guardar(self, key_hash: str, registro: dict[str, object]) -> None: ...
    def liberar(self, key_hash: str) -> None: ...


class RegistroIdempotenciaMemoria:
    """Registro por proceso, para pruebas y corridas offline."""

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
    """Registro fail-closed con reserva atómica y archivos privados.

    Usa el sistema de archivos como candado: `O_EXCL` garantiza que sólo un
    proceso cree la reserva, sin necesitar una base de datos. Los archivos se
    crean con permisos 0600 y el directorio con 0700 porque, aunque sólo
    contengan hashes, revelan qué solicitudes se procesaron y cuándo.
    """

    def __init__(self, directorio: Path) -> None:
        self._directorio = directorio.resolve()

    def _path(self, key_hash: str) -> Path:
        # La clave es un hash y se valida como tal antes de usarse como nombre
        # de archivo: nunca puede contener separadores de ruta.
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
            # Un registro ilegible se trata como UNCERTAIN, no como inexistente:
            # puede corresponder a una ejecución que sí escribió en el destino.
            # Ante la duda, bloquear y que lo revise una persona.
            return {"status": "UNCERTAIN", "error_code": "idempotency_record_invalid"}
        if not _registro_persistido_valido(payload):
            return _registro_idempotencia(
                "UNCERTAIN", error_code="idempotency_record_invalid"
            )
        return payload

    def reservar(self, key_hash: str) -> bool:
        self._directorio.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            # `mkdir(mode=...)` no aplica si el directorio ya existía, así que
            # se fuerzan los permisos igual en cada reserva.
            os.chmod(self._directorio, 0o700)
            # O_CREAT|O_EXCL: crear o fallar. Es la operación atómica que hace
            # de candado entre procesos concurrentes.
            descriptor = os.open(
                self._path(key_hash),
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            # Alguien más ya reservó esta clave: no es un error, es el candado
            # funcionando. El llamador consulta el registro para saber si aquella
            # ejecución terminó o quedó a medias.
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
        # Escritura atómica: se escribe en un temporal, se fuerza a disco con
        # fsync y se reemplaza con `os.replace` (atómico en POSIX). Así un corte
        # de energía deja el registro anterior intacto o el nuevo completo,
        # nunca un JSON truncado.
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
    """Envuelve el destino real y le pone el candado alrededor.

    La reserva se toma en el último instante posible —dentro de `guardar`, justo
    antes de escribir— y no al empezar la ejecución: si el pipeline falla antes
    (datos incompletos, salida no conforme), la clave queda libre para reintentar
    sin intervención humana. Se bloquea sólo cuando pudo haber escritura remota.
    """

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
            # Falla inesperada del destino: se marca UNCERTAIN, no se libera la
            # reserva. No se sabe si llegó a escribir, y liberar habilitaría un
            # reintento que podría duplicar el documento.
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
    """Ejecuta una solicitud de punta a punta y deja su manifest.

    Siempre escribe un manifest, incluso cuando no genera nada: una ejecución
    bloqueada o duplicada también es evidencia y tiene que quedar registrada.

    `ambiente` y `live` son independientes a propósito: se puede correr con
    ambiente D2 y fakes (ensayo de configuración) pero no al revés, porque
    `live` exige D2/D3.
    """

    _validar_solicitud_runner(tipo=tipo, canal=canal, ambiente=ambiente, live=live)
    versiones = _PIPELINE_VERSIONS[tipo]
    key_hash = _idempotency_key(
        tipo=tipo,
        canal=canal,
        id_solicitud=id_solicitud,
        ambiente=ambiente,
        versiones=versiones,
    )
    # Consulta previa: si ya hay un registro para esta clave, la ejecución no
    # arranca. `COMPLETE` es una duplicada legítima (el borrador ya existe);
    # cualquier otro estado quedó a medias y requiere reconciliación manual.
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
    """Construye los adapters reales. Único punto donde el agente sale a la red.

    Las comprobaciones son a propósito `is not True` y no `if not ...`: sólo el
    booleano `True` habilita, de modo que un valor "verdadero por casualidad"
    —un string no vacío, un 1— no active el modo live.

    Se pide y valida el token acá, antes de devolver los adapters, para que un
    problema de credenciales aparezca al preparar la corrida y no a mitad de
    camino, con parte del trabajo ya hecho.
    """

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
    """Deriva la clave de idempotencia de todo lo que define "la misma pieza".

    El id de la solicitud entra ya hasheado (`request_ref_hash`) para que el
    nombre del archivo de reserva no revele qué solicitudes se procesaron.
    `ambiente` forma parte de la clave: una prueba en D2 no debe bloquear la
    ejecución equivalente en D3.
    """

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
    # Un manifest por correlation_id, creado con O_EXCL: una evidencia nunca se
    # sobrescribe. Si el nombre ya existiera sería un bug de correlación y es
    # preferible que falle ruidosamente a que pise la evidencia anterior.
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
    """Deja pasar al manifest sólo lo que ya *es* un hash.

    El registro de idempotencia puede haber sido alterado en disco. Antes de
    copiar cualquiera de sus valores al manifest se verifica la forma: si no es
    un sha256 hexadecimal, se descarta. Así el manifest no puede terminar
    conteniendo un id real que alguien haya inyectado en ese campo.
    """

    if isinstance(valor, str) and len(valor) == 64 and all(c in "0123456789abcdef" for c in valor):
        return valor
    return None


def _etiqueta_segura(valor: object) -> str | None:
    """Igual que `_hash_opcional`, pero para etiquetas cortas (`google_docs`)."""

    if isinstance(valor, str) and re.fullmatch(r"[a-z0-9][a-z0-9_]{0,63}", valor):
        return valor
    return None


def _registro_persistido_valido(payload: object) -> bool:
    """Valida un registro leído de disco antes de confiar en él.

    Un registro que no cumpla la forma esperada se degrada a UNCERTAIN, que
    bloquea; nunca se interpreta como "no existe". Un `COMPLETE` sin hash de
    destino sería una afirmación de éxito sin evidencia, y por eso también se
    rechaza.
    """

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
