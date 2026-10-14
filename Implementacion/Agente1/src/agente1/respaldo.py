"""Respaldo diario del estado local en Drive y su restauración (#86, ADR 0009).

Una vez por día hábil, en el slot diario del scheduler (#84) y después de la
purga (#87), el estado local del agente viaja a una carpeta de Drive de la
cuenta técnica que no se comparte con nadie: registro durable de
confirmaciones, los JSONL bajo `logs/`, `insumos-procesados.jsonl`, el estado
del canal Form (`estado-canal-form/`), el registro de decisiones
(`estado-decisiones/`), la cola de envíos (`cola-envios/`) y los manifests.
Así el RPO queda en un día hábil y el registro que protege contra envíos
duplicados sobrevive a la pérdida del host.

El artefacto es un `.tar.gz` con un `manifest.json` adentro: nombre único por
fecha (`agente1-respaldo-AAAA-MM-DD.tar.gz`), un sha256 por miembro y la
marca `creado_en` que la restauración usa para decidir qué quedó indeterminado.
Se sube siempre con `files.create`: no existe en el módulo ninguna operación
que modifique un archivo remoto, así que un respaldo nunca se sobrescribe.
Una segunda corrida del mismo día que encuentre el archivo ya subido lo omite
en vez de subir otro.

Decisiones que no se ven en el código:

- **La excepción a "el agente nunca borra" está cercada tres veces.** El
  borrado por antigüedad (más de 30 días, la ventana de reconciliación)
  actúa sólo sobre la carpeta fijada al construir el adapter, sólo sobre
  archivos que el propio respaldo creó —convención de nombre
  `agente1-respaldo-*.tar.gz` más el `appProperties` `agente1_respaldo=v1`—
  y con `drive.file` Drive además sólo devuelve archivos creados por la
  aplicación. Cada borrado queda en la auditoría con hash y fecha, sin
  contenido. Es un `files.delete` permanente, no `trashed`: la papelera
  retendría el dato 30 días más y rompería la retención acotada.
- **El respaldo no espera a la purga pero corre detrás de ella.** El
  scheduler lo invoca como subproceso, igual que `purgar_registro.py`: una
  falla se asienta `falla`, se reintenta en el tick siguiente y la corrida
  sigue con lo suyo. La composición en `cli_scheduler` encadena además el
  resultado de la purga del día: si la purga falló, el respaldo también
  falla a propósito, para que ningún artefacto conserve texto que la
  retención ya venció.
- **El aviso al operador es un puerto.** Offline queda el fake declarado
  `AvisoOperadorJsonl` (una línea JSONL con el aviso que se habría mandado);
  en live, `GmailAvisoOperador` reusa `GmailDestinoConfirmaciones`, el
  `gmail.send` cercado por la lista de prueba de D12: el aviso sale sólo a
  una dirección de esa lista y el cuerpo lleva la marca de borrador.
- **La restauración es un procedimiento manual con marca.** El operador
  descarga el artefacto y corre `scripts/restaurar_respaldo.py`: verifica
  hashes, repone archivos sin pisar nada existente (un archivo distinto ya
  presente es un conflicto reportado, nunca una sobreescritura) y después
  marca `ENVIO_INDETERMINADO` toda reserva —que por definición quedó
  interrumpida— y toda aprobación posterior a la marca del respaldo. Lo
  indeterminado no se reenvía: una persona lo cruza contra Gmail Enviados.
- **El artefacto es localmente efímero.** Se construye en memoria y sólo
  existe el archivo subido: conservar copias locales del tar dejaría el
  texto purgado vivo fuera del registro.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import tarfile
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Protocol
from urllib.parse import urlencode

from .certificados import reconciliar_emisiones_reservadas
from .confirmaciones import (
    CLAVE_REGISTRO_RE,
    ESTADOS_PARCIALES_APROBACION,
    MARCADOR_BORRADOR,
    BorradorRegistrado,
    RegistroConfirmacionesArchivo,
    email_valido,
    reconciliar_envios_reservados,
)
from .gmail_envio import GmailDestinoConfirmaciones
from .google_workspace import (
    DRIVE_HOST,
    ID_RE,
    MAX_WORKSPACE_RESPONSE_BYTES,
    MAX_WORKSPACE_TIMEOUT_S,
    AccessTokenProvider,
    HttpsWorkspaceTransport,
    RespuestaHttp,
    TransporteHttp,
    _RespuestaDemasiadoGrande,
)
from .registro_auditoria import escribir_registro

MANIFEST_RECORD = "agente1_respaldo_v1"
AUDITORIA_RECORD = "agente1_respaldo_diario_v1"
AUDITORIA_NOMBRE = "respaldo-diario.jsonl"
AVISOS_OFFLINE_NOMBRE = "avisos-operador-offline.jsonl"
NOMBRE_MANIFIESTO = "manifest.json"
MIME_ARTEFACTO = "application/gzip"

# Días que un respaldo vive en la carpeta antes del borrado por antigüedad:
# la misma ventana de reconciliación que gobierna la purga del registro.
RETENCION_RESPALDOS_DIAS = 30

# El upload es `multipart` de una sola llamada, así que el artefacto entero
# viaja en el cuerpo del request. El tope coincide con el límite de la API
# para `uploadType=multipart` (5 MB): un estado que lo supere es una falla
# cerrada del paso, no una subida a medias.
MAX_ARTEFACTO_BYTES = 5 * 1024 * 1024

# Marker de procedencia declarado en `appProperties`: la carpeta sólo
# recibe archivos que el respaldo creó y el borrado exige la pareja
# convención de nombre + marker, además del filtro del lado de Drive.
APPPROPERTIES_CLAVE = "agente1_respaldo"
APPPROPERTIES_RESPALDO = {APPPROPERTIES_CLAVE: "v1"}

# Convención de nombre propia: la fecha del respaldo viaja en el nombre, así
# la antigüedad se decide contra un dato que el agente escribió y no contra
# `createdTime`, que un restore o una recarga podría mover.
NOMBRE_RE = re.compile(
    r"agente1-respaldo-(?P<fecha>[0-9]{4}-[0-9]{2}-[0-9]{2})\.tar\.gz\Z"
)
# Un miembro del artefacto: segmentos de nombre seguros, sin `..` ni raíz.
_RUTA_MIEMBRO_RE = re.compile(
    r"(?:salida|registro-confirmaciones)"
    r"(?:/[A-Za-z0-9._-]{1,128}){1,6}\Z"
)

# Conjunto declarado del estado bajo el directorio de salida que viaja en el
# artefacto: subdirectorios con su patrón y archivos sueltos de la raíz.
# Los borradores generados (*.md, PDFs) no son estado: quedan fuera a
# propósito, igual que el lock del scheduler y el staging de artefactos.
_DIRS_SALIDA = (
    ("logs", "*.jsonl"),
    ("manifests", "*.json"),
    ("estado-canal-form", "*.jsonl"),
    ("estado-decisiones", "*.jsonl"),
    ("cola-envios", "*"),
)
_ARCHIVOS_SALIDA = ("insumos-procesados.jsonl",)

# Estados desde los que una entrega puede seguir sin otra decisión humana:
# las dos aprobaciones parciales, la aprobación completa y la espera en
# cola. Si la última transición es posterior a la marca del respaldo, la
# restauración los declara `ENVIO_INDETERMINADO` (ver docstring del módulo).
_ESTADOS_APROBACION_POSTERIORES = (
    *sorted(ESTADOS_PARCIALES_APROBACION),
    "APROBADA",
    "ENVIO_ENCOLADO",
)

_PREFIX = "AGENTE1_RESPALDO_"
ENV_CARPETA_ID = "AGENTE1_RESPALDO_CARPETA_ID"
ENV_CARPETA_FAKE = "AGENTE1_RESPALDO_CARPETA_FAKE"
ENV_AVISO_DESTINATARIO = "AGENTE1_RESPALDO_AVISO_DESTINATARIO"
ENV_CONFIRMAR_ESCRITURA = "AGENTE1_RESPALDO_CONFIRMAR_ESCRITURA"
ENV_TIMEOUT_S = "AGENTE1_RESPALDO_TIMEOUT_S"
_ALLOWED_KEYS = frozenset(
    {
        ENV_CARPETA_ID,
        ENV_CARPETA_FAKE,
        ENV_AVISO_DESTINATARIO,
        ENV_CONFIRMAR_ESCRITURA,
        ENV_TIMEOUT_S,
    }
)
DEFAULT_TIMEOUT_S = 30.0


class RespaldoDiarioError(RuntimeError):
    """Falla del respaldo o de la restauración, con código cerrado.

    `etapa` dice en qué tramo cayó (`artefacto`, `listado`, `subida`,
    `borrado`, `aviso`, `restauracion`): la auditoría lo publica.
    """

    def __init__(self, code: str, *, etapa: str = "") -> None:
        self.code = code
        self.etapa = etapa
        super().__init__(code)


class ConfiguracionRespaldoError(ValueError):
    """Falla de la configuración del respaldo, con código estable."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, repr=False)
class ConfiguracionRespaldo:
    """Destino del respaldo y canal del aviso, validados de una sola vez.

    Exactamente uno de `carpeta_id` (carpeta real de Drive, modo live) o
    `carpeta_fake` (directorio local declarado, modo offline) define el
    destino. En live, `aviso_destinatario` es obligatorio y
    `CONFIRMAR_ESCRITURA` debe venir en `SI`: son las dos señales humanas
    del opt-in de escritura real, en el espíritu de `--live` +
    `--confirm-write-workspace`.
    """

    carpeta_id: str | None
    carpeta_fake: Path | None
    aviso_destinatario: str | None
    timeout_s: float

    @property
    def modo(self) -> str:
        return "live" if self.carpeta_id is not None else "fake_local"

    def resumen_seguro(self) -> dict[str, object]:
        return {
            "modo": self.modo,
            "carpeta_ref_hash": _hash(self.carpeta_id or str(self.carpeta_fake)),
            "aviso_declarado": self.aviso_destinatario is not None,
            "timeout_s": self.timeout_s,
        }


def cargar_configuracion_respaldo(
    environ: Mapping[str, str] | None = None,
) -> ConfiguracionRespaldo | None:
    """Lee `AGENTE1_RESPALDO_*`; `None` cuando el paso no está configurado.

    Mismo contrato que los otros loaders: una clave propia desconocida se
    rechaza, un valor vacío es configuración rota y los errores son códigos
    sin datos adentro. `None` es "no declarado", no "default": sin carpeta
    el paso queda `pendiente` en el slot diario.
    """

    env = os.environ if environ is None else environ
    desconocidas = {
        clave for clave in env if clave.startswith(_PREFIX) and clave not in _ALLOWED_KEYS
    }
    if desconocidas:
        raise ConfiguracionRespaldoError("respaldo_config_unknown_key")
    if not any(clave in env for clave in _ALLOWED_KEYS):
        return None

    carpeta_id = _valor_env(env, ENV_CARPETA_ID)
    carpeta_fake = _valor_env(env, ENV_CARPETA_FAKE)
    aviso = _valor_env(env, ENV_AVISO_DESTINATARIO)
    confirmar = _valor_env(env, ENV_CONFIRMAR_ESCRITURA)
    timeout_texto = _valor_env(env, ENV_TIMEOUT_S)

    if (carpeta_id is None) == (carpeta_fake is None):
        # Las dos o ninguna: el destino tiene que ser inequívoco.
        raise ConfiguracionRespaldoError("respaldo_config_incomplete")
    try:
        timeout_s = float(timeout_texto) if timeout_texto else DEFAULT_TIMEOUT_S
    except ValueError:
        raise ConfiguracionRespaldoError("respaldo_config_invalid") from None
    if (
        not math.isfinite(timeout_s)
        or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
    ):
        raise ConfiguracionRespaldoError("respaldo_config_invalid")

    if carpeta_id is not None:
        if ID_RE.fullmatch(carpeta_id) is None:
            raise ConfiguracionRespaldoError("respaldo_config_invalid")
        if aviso is None or not email_valido(aviso):
            raise ConfiguracionRespaldoError("respaldo_config_incomplete")
        if confirmar != "SI":
            # Segunda señal del opt-in live, igual que --confirm-write-workspace.
            raise ConfiguracionRespaldoError("respaldo_config_write_not_confirmed")
        return ConfiguracionRespaldo(
            carpeta_id=carpeta_id,
            carpeta_fake=None,
            aviso_destinatario=aviso,
            timeout_s=timeout_s,
        )

    # Modo fake declarado: el destinatario no aplica porque el aviso queda
    # en el JSONL offline; declararlo igual sería una trampa silenciosa.
    if aviso is not None or confirmar is not None:
        raise ConfiguracionRespaldoError("respaldo_config_invalid")
    assert carpeta_fake is not None
    return ConfiguracionRespaldo(
        carpeta_id=None,
        carpeta_fake=Path(carpeta_fake),
        aviso_destinatario=None,
        timeout_s=timeout_s,
    )


def _valor_env(env: Mapping[str, str], clave: str) -> str | None:
    if clave not in env:
        return None
    valor = env[clave].strip()
    if not valor:
        raise ConfiguracionRespaldoError("respaldo_config_invalid")
    return valor


@dataclass(frozen=True)
class EntradaArtefacto:
    """Un archivo del estado local empaquetado: ruta dentro del tar y bytes."""

    ruta: str
    contenido: bytes
    sha256: str


@dataclass(frozen=True)
class ArtefactoRespaldo:
    """El `.tar.gz` listo para subir, con su manifiesto ya adentro."""

    contenido: bytes
    sha256: str
    archivos: int
    manifiesto_sha256: str
    marca: str


def nombre_respaldo(fecha_operativa: date) -> str:
    """El nombre único por fecha del archivo remoto."""

    return f"agente1-respaldo-{fecha_operativa.isoformat()}.tar.gz"


def construir_artefacto(
    *,
    directorio_salida: Path,
    registro_confirmaciones: Path | None,
    marca: datetime,
) -> ArtefactoRespaldo:
    """Empaqueta el estado declarado en un `.tar.gz` con manifiesto de hashes.

    La `marca` es el instante en que empezó el empaquetado: viaja en el
    manifiesto como `creado_en` y la restauración la usa como corte — toda
    aprobación posterior queda indeterminada, así que lo que el snapshot
    pudo haber capturado a mitad de una transición no habilita un reenvío.

    El conjunto es cerrado y declarado (`_DIRS_SALIDA`, `_ARCHIVOS_SALIDA`
    y el directorio del registro): ni los borradores generados ni archivos
    ajenos entran al respaldo. Un nombre que no se puede representar como
    miembro seguro falla el artefacto entero, porque un respaldo a medias
    es peor que ninguno.
    """

    if marca.tzinfo is None or marca.utcoffset() is None:
        raise RespaldoDiarioError("respaldo_marca_invalid", etapa="artefacto")
    marca_iso = marca.astimezone(timezone.utc).isoformat()
    base = Path(directorio_salida)
    entradas: list[EntradaArtefacto] = []

    def recolectar(origen: Path, ruta_miembro: str) -> None:
        if _RUTA_MIEMBRO_RE.fullmatch(ruta_miembro) is None or ".." in ruta_miembro:
            raise RespaldoDiarioError("respaldo_artefacto_invalid", etapa="artefacto")
        try:
            contenido = origen.read_bytes()
        except OSError:
            raise RespaldoDiarioError(
                "respaldo_entrada_inaccesible", etapa="artefacto"
            ) from None
        entradas.append(
            EntradaArtefacto(
                ruta=ruta_miembro,
                contenido=contenido,
                sha256=hashlib.sha256(contenido).hexdigest(),
            )
        )

    for subdir, patron in _DIRS_SALIDA:
        directorio = base / subdir
        if not directorio.is_dir():
            continue
        for ruta in sorted(directorio.glob(patron)):
            if ruta.is_file() and ruta.suffix != ".tmp":
                recolectar(ruta, f"salida/{subdir}/{ruta.name}")
    for nombre in _ARCHIVOS_SALIDA:
        ruta = base / nombre
        if ruta.is_file():
            recolectar(ruta, f"salida/{nombre}")

    if registro_confirmaciones is not None:
        registro_dir = Path(registro_confirmaciones)
        if not registro_dir.is_dir():
            raise RespaldoDiarioError(
                "respaldo_entrada_inaccesible", etapa="artefacto"
            )
        for ruta in sorted(registro_dir.iterdir()):
            # El directorio es dedicado del registro: todo archivo regular
            # que viva ahí es estado (los `.lock` viajan igual, vacíos).
            if ruta.is_file() and ruta.suffix != ".tmp":
                recolectar(ruta, f"registro-confirmaciones/{ruta.name}")

    entradas.sort(key=lambda entrada: entrada.ruta)
    manifiesto = {
        "record": MANIFEST_RECORD,
        "creado_en": marca_iso,
        "archivos": [
            {"ruta": e.ruta, "sha256": e.sha256, "bytes": len(e.contenido)}
            for e in entradas
        ],
    }
    manifiesto_bytes = json.dumps(
        manifiesto, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz", format=tarfile.PAX_FORMAT) as tar:
        info = tarfile.TarInfo(NOMBRE_MANIFIESTO)
        info.size = len(manifiesto_bytes)
        _normalizar_miembro(info)
        tar.addfile(info, io.BytesIO(manifiesto_bytes))
        for entrada in entradas:
            info = tarfile.TarInfo(entrada.ruta)
            info.size = len(entrada.contenido)
            _normalizar_miembro(info)
            tar.addfile(info, io.BytesIO(entrada.contenido))
    contenido = buffer.getvalue()
    if len(contenido) > MAX_ARTEFACTO_BYTES:
        raise RespaldoDiarioError("respaldo_artefacto_too_large", etapa="artefacto")
    return ArtefactoRespaldo(
        contenido=contenido,
        sha256=hashlib.sha256(contenido).hexdigest(),
        archivos=len(entradas),
        manifiesto_sha256=hashlib.sha256(manifiesto_bytes).hexdigest(),
        marca=marca_iso,
    )


def _normalizar_miembro(info: tarfile.TarInfo) -> None:
    """Metadatos fijos: el artefacto es reproducible y sin dueños locales."""

    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mode = 0o600


@dataclass(frozen=True)
class RespaldoRemoto:
    """Un archivo de la carpeta de respaldo, identificado por id y nombre."""

    archivo_id: str
    nombre: str


class DestinoRespaldos(Protocol):
    """Puerto de la carpeta de respaldo: crear, listar y borrar los propios.

    `subir` crea siempre un archivo nuevo y devuelve su identificador; no
    existe operación de actualización. `borrar` sólo se invoca sobre ids
    que `listar` devolvió y que pasaron la verificación de procedencia.
    """

    def subir(self, *, nombre: str, contenido: bytes) -> str: ...

    def listar(self) -> tuple[RespaldoRemoto, ...]: ...

    def borrar(self, *, archivo_id: str) -> None: ...


class CarpetaRespaldoLocal:
    """Destino fake declarado: una carpeta local que ocupa el lugar de Drive.

    Mismo contrato que el adapter real —crear nuevo, listar los propios,
    borrar por id— para que el slot diario y las pruebas ejerciten el
    mecanismo completo sin red. `subir` usa `O_EXCL`: un nombre repetido
    es anomalía, no sobreescritura. El id devuelto deriva del nombre, así
    `archivo_id_hash` en la auditoría tiene el mismo sentido que en live.
    """

    def __init__(self, directorio: Path) -> None:
        self._directorio = Path(directorio)
        self._directorio.mkdir(parents=True, exist_ok=True, mode=0o700)

    def subir(self, *, nombre: str, contenido: bytes) -> str:
        if NOMBRE_RE.fullmatch(nombre) is None:
            raise RespaldoDiarioError("respaldo_nombre_invalid", etapa="subida")
        try:
            descriptor = os.open(
                self._directorio / nombre, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
            )
        except FileExistsError:
            raise RespaldoDiarioError(
                "respaldo_destino_duplicate", etapa="subida"
            ) from None
        except OSError:
            raise RespaldoDiarioError(
                "respaldo_destino_unavailable", etapa="subida"
            ) from None
        with os.fdopen(descriptor, "wb") as archivo:
            archivo.write(contenido)
            archivo.flush()
            os.fsync(archivo.fileno())
        return f"local-{hashlib.sha256(nombre.encode('utf-8')).hexdigest()[:24]}"

    def listar(self) -> tuple[RespaldoRemoto, ...]:
        try:
            nombres = sorted(
                ruta.name
                for ruta in self._directorio.iterdir()
                if ruta.is_file() and NOMBRE_RE.fullmatch(ruta.name) is not None
            )
        except OSError:
            raise RespaldoDiarioError(
                "respaldo_destino_unavailable", etapa="listado"
            ) from None
        return tuple(
            RespaldoRemoto(
                archivo_id=f"local-{hashlib.sha256(n.encode('utf-8')).hexdigest()[:24]}",
                nombre=n,
            )
            for n in nombres
        )

    def borrar(self, *, archivo_id: str) -> None:
        # El id fake deriva del nombre; se reconstruye y se vuelve a exigir
        # la convención antes de borrar, como en el adapter real.
        encontrado = next(
            (r for r in self.listar() if r.archivo_id == archivo_id), None
        )
        if encontrado is None:
            raise RespaldoDiarioError(
                "drive_resource_not_found", etapa="borrado"
            )
        try:
            (self._directorio / encontrado.nombre).unlink()
        except OSError:
            raise RespaldoDiarioError(
                "respaldo_destino_unavailable", etapa="borrado"
            ) from None


class GoogleDriveRespaldoDiario:
    """Carpeta de respaldo real sobre Drive v3, por HTTP a mano.

    Las tres operaciones que el paso necesita y ninguna más:

    - `subir`: `POST /upload/drive/v3/files?uploadType=multipart` — un
      `files.create` con metadata y contenido en el mismo request. Es la
      única forma de escribir que existe acá: crear nuevo siempre, nunca
      `files.update`, así que un respaldo no puede sobrescribir otro.
    - `listar`: `GET /drive/v3/files` con la carpeta fijada al construir
      en la query —el borrado no puede tocar otra carpeta— y el marker
      `appProperties` exigido también del lado de Google.
    - `borrar`: `DELETE /drive/v3/files/{id}` permanente, la única
      excepción a "nunca borra" (ADR 0009). Sólo la alcanzan ids que
      `listar` devolvió con la convención de nombre propia.

    Con el scope `drive.file`, Drive además sólo muestra los archivos que
    la aplicación creó: la procedencia queda verificada por Google y por
    la convención local. No pide ningún scope nuevo.
    """

    def __init__(
        self,
        *,
        carpeta_id: str,
        token_provider: AccessTokenProvider,
        transport: TransporteHttp | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        if (
            not isinstance(carpeta_id, str)
            or ID_RE.fullmatch(carpeta_id) is None
            or isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s)
            or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
        ):
            raise ValueError("configuración de Drive para respaldo inválida")
        self._carpeta_id = carpeta_id
        self._token_provider = token_provider
        self._transport = transport or HttpsWorkspaceTransport()
        self._timeout_s = float(timeout_s)

    def subir(self, *, nombre: str, contenido: bytes) -> str:
        if NOMBRE_RE.fullmatch(nombre) is None or not contenido:
            raise RespaldoDiarioError("respaldo_nombre_invalid", etapa="subida")
        if len(contenido) > MAX_ARTEFACTO_BYTES:
            raise RespaldoDiarioError("respaldo_artefacto_too_large", etapa="subida")
        token = self._obtener_token()
        # Boundary derivado del contenido: deterministico y sin azar en el
        # cuerpo; el `fields=id` reduce la respuesta a lo único que se usa.
        boundary = "a1r" + hashlib.sha256(contenido).hexdigest()[:48]
        metadata = json.dumps(
            {
                "name": nombre,
                "parents": [self._carpeta_id],
                "appProperties": APPPROPERTIES_RESPALDO,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        cuerpo = b"".join(
            (
                b"--" + boundary.encode("ascii") + b"\r\n",
                b"Content-Type: application/json; charset=UTF-8\r\n\r\n",
                metadata + b"\r\n",
                b"--" + boundary.encode("ascii") + b"\r\n",
                b"Content-Type: " + MIME_ARTEFACTO.encode("ascii") + b"\r\n\r\n",
                contenido + b"\r\n",
                b"--" + boundary.encode("ascii") + b"--\r\n",
            )
        )
        respuesta = self._request(
            method="POST",
            target=(
                "/upload/drive/v3/files"
                "?uploadType=multipart&fields=id&supportsAllDrives=true"
            ),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            body=cuerpo,
            etapa="subida",
        )
        if respuesta.status not in {200, 201}:
            raise RespaldoDiarioError(_codigo_drive(respuesta.status), etapa="subida")
        documento = _json_documento(respuesta, etapa="subida")
        if (
            not isinstance(documento.get("id"), str)
            or ID_RE.fullmatch(documento["id"]) is None
        ):
            raise RespaldoDiarioError("drive_response_invalid", etapa="subida")
        return documento["id"]

    def listar(self) -> tuple[RespaldoRemoto, ...]:
        token = self._obtener_token()
        # La carpeta va en la query y además está fijada al construir: el
        # conjunto devuelto no puede incluir archivos de otro lugar.
        consulta = (
            f"'{self._carpeta_id}' in parents and trashed = false "
            f"and appProperties has {{key='{APPPROPERTIES_CLAVE}' and value='v1'}}"
        )
        remotos: list[RespaldoRemoto] = []
        page_token: str | None = None
        # El volumen de la carpeta es un respaldo por día: diez páginas de
        # cien quedan muy por encima de cualquier horizonte razonable.
        for _ in range(10):
            params = {
                "q": consulta,
                "fields": "files(id,name,appProperties),nextPageToken",
                "pageSize": "100",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
            if page_token is not None:
                params["pageToken"] = page_token
            respuesta = self._request(
                method="GET",
                target=f"/drive/v3/files?{urlencode(params)}",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                body=None,
                etapa="listado",
            )
            if respuesta.status != 200:
                raise RespaldoDiarioError(
                    _codigo_drive(respuesta.status), etapa="listado"
                )
            documento = _json_documento(respuesta, etapa="listado")
            archivos = documento.get("files")
            if not isinstance(archivos, list):
                raise RespaldoDiarioError("drive_response_invalid", etapa="listado")
            for archivo in archivos:
                if not isinstance(archivo, dict):
                    raise RespaldoDiarioError(
                        "drive_response_invalid", etapa="listado"
                    )
                archivo_id, nombre = archivo.get("id"), archivo.get("name")
                if (
                    not isinstance(archivo_id, str)
                    or ID_RE.fullmatch(archivo_id) is None
                    or not isinstance(nombre, str)
                    or len(nombre) > 256
                    or NOMBRE_RE.fullmatch(nombre) is None
                ):
                    raise RespaldoDiarioError(
                        "drive_response_invalid", etapa="listado"
                    )
                # Verificación local del marker además de la query: si el
                # scope alguna vez se amplía, la procedencia sigue exigida.
                props = archivo.get("appProperties")
                if not isinstance(props, dict) or props.get(APPPROPERTIES_CLAVE) != "v1":
                    raise RespaldoDiarioError(
                        "drive_response_invalid", etapa="listado"
                    )
                remotos.append(RespaldoRemoto(archivo_id=archivo_id, nombre=nombre))
            siguiente = documento.get("nextPageToken")
            if siguiente is None:
                return tuple(remotos)
            if not isinstance(siguiente, str) or len(siguiente) > 1024:
                raise RespaldoDiarioError("drive_response_invalid", etapa="listado")
            page_token = siguiente
        raise RespaldoDiarioError("drive_response_invalid", etapa="listado")

    def borrar(self, *, archivo_id: str) -> None:
        if not isinstance(archivo_id, str) or ID_RE.fullmatch(archivo_id) is None:
            raise RespaldoDiarioError("respaldo_borrado_invalid", etapa="borrado")
        token = self._obtener_token()
        respuesta = self._request(
            method="DELETE",
            target=(
                f"/drive/v3/files/{archivo_id}?supportsAllDrives=true"
            ),
            headers={"Authorization": f"Bearer {token}"},
            body=None,
            etapa="borrado",
        )
        if 200 <= respuesta.status < 300 or respuesta.status == 404:
            # Un 404 significa que el archivo ya no está: el estado buscado
            # (que no exista) ya vale; el borrado queda auditado igual.
            return
        raise RespaldoDiarioError(_codigo_drive(respuesta.status), etapa="borrado")

    def _request(
        self,
        *,
        method: str,
        target: str,
        headers: dict[str, str],
        body: bytes | None,
        etapa: str,
    ) -> RespuestaHttp:
        try:
            return self._transport.request(
                method=method,
                host=DRIVE_HOST,
                target=target,
                headers=headers,
                body=body,
                deadline=time.monotonic() + self._timeout_s,
                max_response_bytes=MAX_WORKSPACE_RESPONSE_BYTES,
            )
        except _RespuestaDemasiadoGrande:
            raise RespaldoDiarioError(
                "drive_response_too_large", etapa=etapa
            ) from None
        except RespaldoDiarioError:
            raise
        except Exception:
            raise RespaldoDiarioError("drive_unavailable", etapa=etapa) from None

    def _obtener_token(self) -> str:
        try:
            token = self._token_provider.obtener_access_token()
        except Exception:
            raise RespaldoDiarioError(
                "workspace_auth_unavailable", etapa="token"
            ) from None
        if (
            not isinstance(token, str)
            or not token.strip()
            or token != token.strip()
            or "\r" in token
            or "\n" in token
        ):
            raise RespaldoDiarioError("workspace_auth_unavailable", etapa="token")
        return token


def _json_documento(respuesta: object, *, etapa: str) -> dict[str, object]:
    if len(respuesta.body) > MAX_WORKSPACE_RESPONSE_BYTES:
        raise RespaldoDiarioError("drive_response_too_large", etapa=etapa)
    try:
        documento = json.loads(respuesta.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RespaldoDiarioError("drive_response_invalid", etapa=etapa) from None
    if not isinstance(documento, dict):
        raise RespaldoDiarioError("drive_response_invalid", etapa=etapa)
    return documento


def _codigo_drive(status: int) -> str:
    # Mismo vocabulario que los otros adapters de Drive: 401/403 es la
    # señal de revocación y nunca se reintenta en el mismo intento.
    if status in {401, 403}:
        return "drive_auth_denied"
    if status == 404:
        return "drive_resource_not_found"
    if status == 429:
        return "drive_rate_limited"
    return "drive_unavailable"


class AvisoOperador(Protocol):
    """Puerto del aviso al operador cuando el respaldo falla.

    `avisar` devuelve el modo en que quedó registrado el aviso: `enviado`
    (el correo salió por `gmail.send`) o `registrado_offline` (el fake
    declarado dejó la línea). El destinatario nunca sale en el retorno ni
    en la auditoría.
    """

    def avisar(self, *, asunto: str, cuerpo: str) -> str: ...


class AvisoOperadorJsonl:
    """Fake declarado del aviso: lo deja en un JSONL, sin red ni correo."""

    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._path = Path(path)
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def avisar(self, *, asunto: str, cuerpo: str) -> str:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        entrada = {
            "record": "agente1_aviso_operador_v1",
            "creado_en": self._clock().astimezone(timezone.utc).isoformat(),
            "asunto": asunto,
            "cuerpo": cuerpo,
            "modo": "offline_fake",
        }
        escribir_registro(self._path, entrada)
        return "registrado_offline"


class GmailAvisoOperador:
    """Aviso real por `gmail.send`, cercado por la lista de prueba (D12).

    Reusa `GmailDestinoConfirmaciones`, el único destino de correo
    habilitado: el destinatario tiene que estar en la lista de direcciones
    de prueba o la entrega se rechaza antes de la red, y el cuerpo sale
    con la marca de borrador como cualquier correo del agente. La clave de
    idempotencia es un hash del aviso — es lo que el contrato del destino
    exige, no un dato.
    """

    def __init__(
        self, *, destinatario: str, destino: GmailDestinoConfirmaciones
    ) -> None:
        if not email_valido(destinatario):
            raise ValueError("destinatario del aviso inválido")
        self._destinatario = destinatario
        self._destino = destino

    def avisar(self, *, asunto: str, cuerpo: str) -> str:
        self._destino.entregar(
            idempotency_key=hashlib.sha256(
                f"aviso-respaldo|{asunto}|{cuerpo}".encode("utf-8")
            ).hexdigest(),
            destinatario=self._destinatario,
            asunto=asunto,
            cuerpo=MARCADOR_BORRADOR + "\n" + cuerpo,
        )
        return "enviado"


class AuditoriaRespaldo:
    """El log del respaldo: una línea JSONL append-only por evento.

    Vive en `logs/respaldo-diario.jsonl` bajo el directorio de salida, así
    que viaja dentro del artefacto del día siguiente. Lleva hashes, nombres
    de archivo (que sólo contienen la fecha) y códigos cerrados: nunca
    contenido ni identificadores de Drive en claro.
    """

    def __init__(self, directorio_salida: Path) -> None:
        self._path = Path(directorio_salida) / "logs" / AUDITORIA_NOMBRE

    @property
    def path(self) -> Path:
        return self._path

    def anexar(
        self, *, evento: str, correlation_id: str, campos: Mapping[str, object]
    ) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        entrada = {
            "record": AUDITORIA_RECORD,
            "evento": evento,
            "correlation_id": correlation_id,
            "ejecutado_en": datetime.now(timezone.utc).isoformat(),
            **campos,
        }
        escribir_registro(self._path, entrada)


@dataclass(frozen=True)
class ResultadoRespaldo:
    """Qué dejó el paso diario: el archivo remoto y los borrados propios."""

    nombre: str
    subido: bool
    omitido_existente: bool
    artefacto_sha256: str
    archivos: int
    eliminados: tuple[str, ...]
    correlation_id: str
    audit_path: Path


def correr_respaldo_diario(
    *,
    directorio_salida: Path,
    destino: DestinoRespaldos,
    registro_confirmaciones: Path | None = None,
    aviso: AvisoOperador | None = None,
    ahora: datetime | None = None,
    fecha_operativa: date | None = None,
    retencion_dias: int = RETENCION_RESPALDOS_DIAS,
) -> ResultadoRespaldo:
    """El paso diario completo: empaquetar, subir nuevo, borrar los vencidos.

    `fecha_operativa` decide el nombre y el corte de antigüedad; default la
    fecha UTC de `ahora`, que dentro de la ventana de operación coincide
    con la fecha local. Idempotente por día: si ya existe un archivo con
    el nombre de hoy lo omite en vez de subir otro (la subida real nunca
    es `update` de todos modos). Cualquier `RespaldoDiarioError` audita la
    falla, dispara el aviso al operador cuando hay destino de aviso y se
    propaga para que el scheduler asiente `falla` y reintente en el tick
    siguiente — la corrida nunca se entera de que el paso falló.
    """

    momento = ahora if ahora is not None else datetime.now(timezone.utc)
    if momento.tzinfo is None or momento.utcoffset() is None:
        raise RespaldoDiarioError("respaldo_marca_invalid", etapa="artefacto")
    if (
        not isinstance(retencion_dias, int)
        or isinstance(retencion_dias, bool)
        or not 1 <= retencion_dias <= 3650
    ):
        raise RespaldoDiarioError("respaldo_retencion_invalid", etapa="borrado")
    fecha = fecha_operativa or momento.astimezone(timezone.utc).date()
    nombre = nombre_respaldo(fecha)
    correlation_id = str(uuid.uuid4())
    auditoria = AuditoriaRespaldo(directorio_salida)

    try:
        artefacto = construir_artefacto(
            directorio_salida=directorio_salida,
            registro_confirmaciones=registro_confirmaciones,
            marca=momento,
        )
        remotos = {r.nombre: r for r in destino.listar()}
        if nombre in remotos:
            auditoria.anexar(
                evento="respaldo_omitido_existente",
                correlation_id=correlation_id,
                campos={
                    "nombre": nombre,
                    "archivo_id_hash": _hash(remotos[nombre].archivo_id),
                    "artefacto_sha256": artefacto.sha256,
                },
            )
            archivo_id = remotos[nombre].archivo_id
            subido = False
        else:
            archivo_id = destino.subir(nombre=nombre, contenido=artefacto.contenido)
            auditoria.anexar(
                evento="respaldo_subido",
                correlation_id=correlation_id,
                campos={
                    "nombre": nombre,
                    "archivo_id_hash": _hash(archivo_id),
                    "artefacto_sha256": artefacto.sha256,
                    "artefacto_bytes": len(artefacto.contenido),
                    "archivos": artefacto.archivos,
                    "manifiesto_sha256": artefacto.manifiesto_sha256,
                },
            )
            subido = True

        eliminados: list[str] = []
        corte = fecha - timedelta(days=retencion_dias)
        errores_borrado = 0
        for remoto in sorted(remotos.values(), key=lambda r: r.nombre):
            match = NOMBRE_RE.fullmatch(remoto.nombre)
            # Sin convención de nombre no hay borrado: puede no ser nuestro.
            if match is None:
                continue
            fecha_remoto = date.fromisoformat(match["fecha"])
            if fecha_remoto >= corte:
                continue
            try:
                destino.borrar(archivo_id=remoto.archivo_id)
            except RespaldoDiarioError as exc:
                errores_borrado += 1
                auditoria.anexar(
                    evento="respaldo_eliminar_fallido",
                    correlation_id=correlation_id,
                    campos={
                        "nombre": remoto.nombre,
                        "archivo_id_hash": _hash(remoto.archivo_id),
                        "error": exc.code,
                    },
                )
                continue
            eliminados.append(remoto.nombre)
            auditoria.anexar(
                evento="respaldo_eliminado",
                correlation_id=correlation_id,
                campos={
                    "nombre": remoto.nombre,
                    "archivo_id_hash": _hash(remoto.archivo_id),
                    "fecha_respaldo": fecha_remoto.isoformat(),
                },
            )
        if errores_borrado:
            raise RespaldoDiarioError("respaldo_borrado_error", etapa="borrado")
    except RespaldoDiarioError as exc:
        auditoria.anexar(
            evento="respaldo_fallido",
            correlation_id=correlation_id,
            campos={"etapa": exc.etapa or "desconocida", "error": exc.code},
        )
        _avisar_operador(auditoria, aviso, exc, correlation_id)
        raise

    return ResultadoRespaldo(
        nombre=nombre,
        subido=subido,
        omitido_existente=not subido,
        artefacto_sha256=artefacto.sha256,
        archivos=artefacto.archivos,
        eliminados=tuple(eliminados),
        correlation_id=correlation_id,
        audit_path=auditoria.path,
    )


def _avisar_operador(
    auditoria: AuditoriaRespaldo,
    aviso: AvisoOperador | None,
    exc: RespaldoDiarioError,
    correlation_id: str,
) -> None:
    """El aviso de la falla: si él mismo falla, queda auditado y listo."""

    if aviso is None:
        auditoria.anexar(
            evento="aviso_operador",
            correlation_id=correlation_id,
            campos={"resultado": "sin_destino"},
        )
        return
    try:
        modo = aviso.avisar(
            asunto="Agente 1: el respaldo diario falló",
            cuerpo=(
                f"El respaldo diario del estado local falló en la etapa "
                f"{exc.etapa or 'desconocida'} con el código {exc.code}. "
                f"Revisar logs/{AUDITORIA_NOMBRE} y el runbook del scheduler."
            ),
        )
    except Exception:
        auditoria.anexar(
            evento="aviso_operador",
            correlation_id=correlation_id,
            campos={"resultado": "fallido"},
        )
        return
    auditoria.anexar(
        evento="aviso_operador",
        correlation_id=correlation_id,
        campos={"resultado": modo},
    )


@dataclass(frozen=True)
class ResultadoRestauracion:
    """Qué dejó la restauración: archivos repuestos y marcas de revisión."""

    marca: str
    artefacto_sha256: str
    archivos_restaurados: int
    archivos_omitidos: int
    conflictos: tuple[str, ...]
    indeterminados: tuple[str, ...]
    correlation_id: str
    audit_path: Path


def restaurar_estado_respaldo(
    *,
    artefacto_path: Path,
    directorio_salida: Path,
    registro_confirmaciones: Path | None,
) -> ResultadoRestauracion:
    """El procedimiento de restauración: verificar, reponer, marcar.

    Tres fases, todas fail-closed:

    1. **Verificación.** El manifiesto del artefacto tiene que cerrar:
       record, `creado_en` con zona y un sha256 por miembro que coincida
       byte a byte. Un artefacto que no verifica no toca nada.
    2. **Reposición sin sobreescritura.** Cada miembro se escribe sólo si
       el destino no existe; un archivo idéntico ya presente se omite y un
       archivo distinto es un `conflicto` reportado, nunca una pérdida
       silenciosa de estado posterior.
    3. **Marca.** En el registro repuesto, toda reserva (`ENVIO_RESERVADO`
       → `ENVIO_INDETERMINADO`, `EMISION_RESERVADA` → `EMISION_INDETERMINADA`)
       pasa a indeterminada porque una reserva restaurada es por definición
       interrumpida, y toda entrada en estado de aprobación cuya última
       transición es posterior a la marca del respaldo pasa a
       `ENVIO_INDETERMINADO`: lo que el snapshot no pudo afirmar no se
       reenvía hasta que una persona lo cruce contra Gmail Enviados.

    Devuelve el informe y deja la línea `restauracion_respaldo` en la
    auditoría del respaldo. No descarga nada de Drive: el operador provee
    el artefacto local (runbook del scheduler).
    """

    correlation_id = str(uuid.uuid4())
    auditoria = AuditoriaRespaldo(directorio_salida)
    contenido, marca_iso, miembros = _verificar_artefacto(artefacto_path)
    marca_dt = datetime.fromisoformat(marca_iso)

    salida_base = Path(directorio_salida)
    registro_base = (
        Path(registro_confirmaciones) if registro_confirmaciones is not None else None
    )
    restaurados = 0
    omitidos = 0
    conflictos: list[str] = []
    for ruta_miembro, datos in sorted(miembros.items()):
        if ruta_miembro.startswith("salida/"):
            destino = salida_base / ruta_miembro[len("salida/"):]
        else:
            if registro_base is None:
                raise RespaldoDiarioError(
                    "respaldo_registro_destino_ausente", etapa="restauracion"
                )
            destino = registro_base / ruta_miembro[len("registro-confirmaciones/"):]
        if destino.exists():
            try:
                existente = destino.read_bytes()
            except OSError:
                raise RespaldoDiarioError(
                    "respaldo_entrada_inaccesible", etapa="restauracion"
                ) from None
            if existente == datos:
                omitidos += 1
            else:
                conflictos.append(ruta_miembro)
            continue
        destino.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporal = destino.with_name(f"{destino.name}.{uuid.uuid4().hex}.tmp")
        try:
            descriptor = os.open(
                temporal, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
            )
            with os.fdopen(descriptor, "wb") as archivo:
                archivo.write(datos)
                archivo.flush()
                os.fsync(archivo.fileno())
            os.replace(temporal, destino)
        except OSError:
            temporal.unlink(missing_ok=True)
            raise RespaldoDiarioError(
                "respaldo_entrada_inaccesible", etapa="restauracion"
            ) from None
        restaurados += 1

    indeterminados = (
        _marcar_posteriores_indeterminados(registro_base, marca_dt)
        if registro_base is not None and registro_base.is_dir()
        else ()
    )
    auditoria.anexar(
        evento="restauracion_respaldo",
        correlation_id=correlation_id,
        campos={
            "artefacto_sha256": hashlib.sha256(contenido).hexdigest(),
            "marca": marca_iso,
            "archivos_restaurados": restaurados,
            "archivos_omitidos": omitidos,
            "conflictos": len(conflictos),
            "conflictos_hash": _hash("\n".join(conflictos)),
            "indeterminados": len(indeterminados),
            "claves_hash": _hash("\n".join(indeterminados)),
        },
    )
    return ResultadoRestauracion(
        marca=marca_iso,
        artefacto_sha256=hashlib.sha256(contenido).hexdigest(),
        archivos_restaurados=restaurados,
        archivos_omitidos=omitidos,
        conflictos=tuple(conflictos),
        indeterminados=indeterminados,
        correlation_id=correlation_id,
        audit_path=auditoria.path,
    )


def _verificar_artefacto(
    artefacto_path: Path,
) -> tuple[bytes, str, dict[str, bytes]]:
    """Abre el artefacto y exige el manifiesto íntegro, byte verificado.

    Falla cerrada con `respaldo_artefacto_invalid` ante cualquier cosa que
    no sea exactamente un `.tar.gz` del respaldo: miembros que no son
    archivo regular, rutas fuera de las dos raíces declaradas, hashes que
    no coinciden, miembros sin manifestar o manifestados ausentes.
    """

    ruta = Path(artefacto_path)
    try:
        if ruta.stat().st_size > MAX_ARTEFACTO_BYTES:
            raise RespaldoDiarioError(
                "respaldo_artefacto_too_large", etapa="restauracion"
            )
        contenido = ruta.read_bytes()
    except RespaldoDiarioError:
        raise
    except OSError:
        raise RespaldoDiarioError(
            "respaldo_entrada_inaccesible", etapa="restauracion"
        ) from None

    invalido = RespaldoDiarioError("respaldo_artefacto_invalid", etapa="restauracion")
    try:
        with tarfile.open(fileobj=io.BytesIO(contenido), mode="r:gz") as tar:
            miembros: dict[str, bytes] = {}
            manifiesto_crudo: bytes | None = None
            for miembro in tar:
                if not miembro.isfile():
                    raise invalido
                # Tope por miembro además del tope del artefacto: un tar
                # chico puede descomprimirse en algo enorme.
                if miembro.size > MAX_ARTEFACTO_BYTES:
                    raise invalido
                nombre = miembro.name
                if nombre == NOMBRE_MANIFIESTO:
                    extraido = tar.extractfile(miembro)
                    manifiesto_crudo = (
                        extraido.read() if extraido is not None else None
                    )
                    continue
                if _RUTA_MIEMBRO_RE.fullmatch(nombre) is None:
                    raise invalido
                extraido = tar.extractfile(miembro)
                if extraido is None:
                    raise invalido
                miembros[nombre] = extraido.read()
    except RespaldoDiarioError:
        raise
    except (tarfile.TarError, EOFError, OSError):
        raise invalido from None

    if manifiesto_crudo is None or len(manifiesto_crudo) > MAX_WORKSPACE_RESPONSE_BYTES:
        raise invalido
    try:
        manifiesto = json.loads(manifiesto_crudo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise invalido from None
    if (
        not isinstance(manifiesto, dict)
        or manifiesto.get("record") != MANIFEST_RECORD
        or not isinstance(manifiesto.get("creado_en"), str)
    ):
        raise invalido
    try:
        marca_dt = datetime.fromisoformat(manifiesto["creado_en"])
    except ValueError:
        raise invalido from None
    if marca_dt.tzinfo is None or marca_dt.utcoffset() is None:
        raise invalido
    archivos = manifiesto.get("archivos")
    if not isinstance(archivos, list):
        raise invalido
    declaradas: set[str] = set()
    for entrada in archivos:
        if (
            not isinstance(entrada, dict)
            or not isinstance(entrada.get("ruta"), str)
            or not isinstance(entrada.get("sha256"), str)
            or not isinstance(entrada.get("bytes"), int)
        ):
            raise invalido
        ruta_miembro = entrada["ruta"]
        datos = miembros.get(ruta_miembro)
        if datos is None or ruta_miembro in declaradas:
            raise invalido
        if (
            len(datos) != entrada["bytes"]
            or hashlib.sha256(datos).hexdigest() != entrada["sha256"]
        ):
            raise invalido
        declaradas.add(ruta_miembro)
    if set(miembros) != declaradas:
        raise invalido
    return contenido, manifiesto["creado_en"], miembros


def _marcar_posteriores_indeterminados(
    registro_base: Path, marca_dt: datetime
) -> tuple[str, ...]:
    """La marca del respaldo hecha estado: reservas y aprobaciones dudosas.

    Las reservas se reconcilian siempre —una restaurada es una reserva
    interrumpida, igual que una colgada por una caída— cada una hacia el
    indeterminado de su propio pipeline. Las aprobaciones posteriores a la
    marca pasan a `ENVIO_INDETERMINADO`: como el registro no distingue el
    pipeline de una `APROBADA` compartida, lo importante es que el estado
    queda terminal-sospechoso para las dos vías (ninguna puede entregar ni
    emitir desde ahí).
    """

    registro = RegistroConfirmacionesArchivo(registro_base)
    marcadas: list[str] = []
    for reconciliada in reconciliar_envios_reservados(registro):
        marcadas.append(reconciliada.idempotency_key)
    for reconciliada in reconciliar_emisiones_reservadas(registro):
        marcadas.append(reconciliada.idempotency_key)

    for estado in _ESTADOS_APROBACION_POSTERIORES:
        for clave in registro.listar_por_estado(estado):
            if CLAVE_REGISTRO_RE.fullmatch(clave) is None:
                continue
            entrada = registro.obtener(clave)
            if entrada is None:
                continue
            if _ultima_transicion(entrada, registro_base, clave) <= marca_dt:
                continue
            if registro.transicionar(
                clave, frozenset({estado}), "ENVIO_INDETERMINADO"
            ):
                marcadas.append(clave)
    return tuple(marcadas)


def _ultima_transicion(
    entrada: BorradorRegistrado, registro_base: Path, clave: str
) -> datetime:
    """La fecha de la última transición, con los mismos fallbacks de la purga."""

    if entrada.actualizado_en is not None:
        return datetime.fromisoformat(entrada.actualizado_en)
    if entrada.creado_en is not None:
        return datetime.fromisoformat(entrada.creado_en)
    try:
        mtime = (registro_base / f"{clave}.json").stat().st_mtime
    except OSError:
        return datetime.min.replace(tzinfo=timezone.utc)
    return datetime.fromtimestamp(mtime, timezone.utc)


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()
