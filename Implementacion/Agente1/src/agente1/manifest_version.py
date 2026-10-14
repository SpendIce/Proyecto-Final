"""Manifest de versión del Agente 1 y verificación de integridad al arrancar (#92).

Una versión del agente se instala en un host que opera Informática y la
dispara un scheduler sin nadie mirando. Un prompt, una política de redes o un
contrato editados a mano en ese host cambian lo que el agente redacta o lo que
deja pasar el gate, sin PR y sin que la auditoría registre de dónde salió la
pieza (ADR 0010). Este módulo construye el **manifest de versión** —el sha256
de todo lo controlado que vive en el repo— y lo usa para **verificar la
integridad del host al arrancar en modo operación**.

Decisiones que no se ven en el código:

- **Qué es «lo controlado» y qué queda afuera.** El manifest cubre el código,
  los prompts, las políticas y los contratos bajo `src/`, las `migrations/`,
  el `uv.lock`, el `pyproject.toml`, los `scripts/` operativos y las unidades
  `systemd/` (ADR 0010). La **configuración por entorno** —IDs de planillas y
  Forms, scopes— queda fuera a propósito: Informática la rota sin pasar por el
  repo y frenar el arranque por eso sería fricción, no control. El conjunto es
  cerrado y declarado en `RUTAS_CONTROLADAS`.
- **La exclusión espeja `.gitignore`.** `__pycache__`, `*.py[cod]` y
  `*.egg-info` son basura de build que el host genera solo: si entraran al
  manifest, un `import` cualquiera los volvería «sobrantes» y el agente no
  arrancaría nunca. Lo controlado es lo versionado.
- **El manifest no se controla a sí mismo.** Vive en la raíz del Agente 1
  (`manifest-version.json`), fuera de las rutas que recorre, así que no hay
  autorreferencia: el hash del manifest lo calcula quien lo referencia (el
  manifest de corte) hasheando el archivo.
- **Sin timestamps volátiles.** El manifest es determinista: el mismo árbol
  produce el mismo archivo byte a byte. El `ejecutado_en` de la auditoría no
  entra al manifest.
- **Fail-closed al arrancar.** En modo operación, un archivo faltante,
  modificado o sobrante —o un manifest ausente o inválido— impide arrancar y
  deja en `logs/integridad-arranque.jsonl` el archivo, el hash esperado y el
  encontrado. El modo operación es la corrida con `--live` (el único camino
  por el que el agente toca sistemas reales, y el que usan las unidades
  `systemd/`): las corridas offline (`--tabla`), la CLI local y la suite no
  verifican, para que el desarrollo no dependa de regenerar el manifest en
  cada cambio (ADR 0010).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MANIFEST_VERSION_SCHEMA = "agente1_manifest_version_v1"
MANIFEST_VERSION_NOMBRE = "manifest-version.json"

AUDITORIA_RECORD = "agente1_integridad_arranque_v1"
AUDITORIA_NOMBRE = "integridad-arranque.jsonl"

# Lo controlado que vive en el repo, declarado de una vez (ADR 0010). Un
# cambio acá es un cambio de alcance del control: no se descubre solo.
RUTAS_CONTROLADAS: tuple[str, ...] = (
    "src",
    "migrations",
    "scripts",
    "systemd",
    "uv.lock",
    "pyproject.toml",
)

# Misma exclusión que `.gitignore`: lo controlado es lo versionado, y la
# basura de build que el host genera sola no puede volver «sobrante» al árbol.
_DIRECTORIOS_EXCLUIDOS = frozenset({"__pycache__"})
_SUFIJOS_EXCLUIDOS = (".pyc", ".pyo")
_SUFIJO_EGG_INFO = ".egg-info"

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class IntegridadError(RuntimeError):
    """Falla cerrada de la integridad del agente, con código estable.

    `discrepancias` viaja sólo en el caso de archivos que no coinciden: es la
    lista de `{archivo, motivo, hash_esperado, hash_encontrado}` que la
    auditoría ya dejó asentada.
    """

    def __init__(
        self, code: str, *, discrepancias: Sequence[Mapping[str, object]] = ()
    ) -> None:
        self.code = code
        self.discrepancias = tuple(dict(item) for item in discrepancias)
        super().__init__(code)


def raiz_agente() -> Path:
    """La raíz del Agente 1 (donde vive `manifest-version.json`).

    Derivada de la ubicación del paquete: sirve para un checkout editable, que
    es como corre el agente. En una instalación empaquetada sin el checkout,
    la verificación falla cerrada porque el manifest no está en su lugar.
    """

    return Path(__file__).resolve().parents[2]


def listar_controlados(raiz: Path) -> tuple[str, ...]:
    """Todo lo controlado bajo `raiz`, en rutas POSIX relativas y ordenadas.

    Mismo barrido para generar y para verificar: así no hay dos definiciones
    de «lo controlado» que puedan divergir. Determinista por construcción
    (recorrido ordenado más orden final), no por depender del orden del
    sistema de archivos.
    """

    raiz = Path(raiz)
    encontrados: set[str] = set()
    for controlada in RUTAS_CONTROLADAS:
        base = raiz / controlada
        if base.is_file():
            encontrados.add(controlada)
            continue
        if not base.is_dir():
            continue
        for directorio, subdirectorios, archivos in os.walk(base):
            subdirectorios[:] = sorted(
                nombre
                for nombre in subdirectorios
                if not _directorio_excluido(nombre)
            )
            for nombre in archivos:
                if _archivo_excluido(nombre):
                    continue
                completo = Path(directorio) / nombre
                encontrados.add(completo.relative_to(raiz).as_posix())
    return tuple(sorted(encontrados))


def _directorio_excluido(nombre: str) -> bool:
    return nombre in _DIRECTORIOS_EXCLUIDOS or nombre.endswith(_SUFIJO_EGG_INFO)


def _archivo_excluido(nombre: str) -> bool:
    return nombre.endswith(_SUFIJOS_EXCLUIDOS)


def sha256_archivo(ruta: Path) -> str:
    """El sha256 de un archivo, en hex minúscula."""

    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def sha256_bytes(contenido: bytes) -> str:
    """El sha256 de un bloque de bytes (el manifest como artefacto)."""

    return hashlib.sha256(contenido).hexdigest()


def version_desde_pyproject(raiz: Path) -> str:
    """La versión declarada en `pyproject.toml`, validada.

    Es la unidad que se instala, se revierte y se cita (#93 le da tag y
    changelog): mientras tanto, el `version` del proyecto es la fuente única
    para que el manifest y el `pyproject` no puedan divergir.
    """

    try:
        documento = tomllib.loads(
            (Path(raiz) / "pyproject.toml").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        raise IntegridadError("manifest_version_invalido") from None
    proyecto = documento.get("project")
    version = proyecto.get("version") if isinstance(proyecto, Mapping) else None
    if not isinstance(version, str) or not version.strip():
        raise IntegridadError("manifest_version_invalido")
    return version.strip()


def identidad_version_agente(raiz: Path | None = None) -> dict[str, object]:
    """La identidad de la versión instalada para los registros de auditoría (#93).

    Devuelve las dos claves que #93 agrega a cada registro: `version_agente`
    —la de `pyproject.toml`, fuente única, para que la versión no se repita a
    mano— y `manifest_version_sha256` —el sha256 del manifest de versión que
    viaja con lo instalado (`manifest-version.json`), el mismo hash que ata el
    manifest de corte—. Con eso una pieza se rastrea hasta la versión exacta y
    la huella de lo controlado que la produjo, no sólo hasta el prompt o la
    política.

    Es tolerante a propósito: si faltan el `pyproject.toml` o el manifest, el
    campo correspondiente queda en `None` en vez de impedir que el registro se
    escriba. El fail-closed del arranque (ADR 0010) es el que exige el manifest
    en modo operación; la auditoría no puede dejar de asentar por eso.
    """

    raiz = Path(raiz) if raiz is not None else raiz_agente()
    try:
        version: str | None = version_desde_pyproject(raiz)
    except IntegridadError:
        version = None
    try:
        hash_manifest: str | None = sha256_archivo(raiz / MANIFEST_VERSION_NOMBRE)
    except OSError:
        hash_manifest = None
    return {
        "version_agente": version,
        "manifest_version_sha256": hash_manifest,
    }


def construir_manifest(raiz: Path, *, version: str | None = None) -> dict[str, Any]:
    """El manifest de versión: `schema_version`, `version` y los hashes.

    Sin `version` explícita toma la de `pyproject.toml`. Si no hay archivos
    controlados, falla: un manifest vacío verificaría cualquier host.
    """

    raiz = Path(raiz)
    if version is None:
        version = version_desde_pyproject(raiz)
    elif not version.strip():
        raise IntegridadError("manifest_version_invalido")

    archivos = {
        relativo: sha256_archivo(raiz / relativo)
        for relativo in listar_controlados(raiz)
    }
    if not archivos:
        raise IntegridadError("manifest_sin_archivos")
    return {
        "schema_version": MANIFEST_VERSION_SCHEMA,
        "version": version,
        "archivos_sha256": archivos,
    }


def serializar_manifest(manifest: Mapping[str, object]) -> str:
    """Serializa el manifest de forma determinista y estable en Git."""

    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def leer_manifest(ruta: Path) -> dict[str, Any]:
    """Lee y valida el manifest; ausente e inválido son fallas distintas."""

    try:
        contenido = Path(ruta).read_bytes()
    except OSError:
        raise IntegridadError("manifest_version_ausente") from None
    try:
        documento = json.loads(contenido)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise IntegridadError("manifest_version_invalido") from None
    validar_manifest(documento)
    assert isinstance(documento, dict)
    return documento


def validar_manifest(manifest: object) -> None:
    """El contrato cerrado del manifest, sin efectos: o vale o falla con código."""

    if not isinstance(manifest, dict):
        raise IntegridadError("manifest_version_invalido")
    if manifest.get("schema_version") != MANIFEST_VERSION_SCHEMA:
        raise IntegridadError("manifest_version_invalido")
    version = manifest.get("version")
    if not isinstance(version, str) or not version.strip():
        raise IntegridadError("manifest_version_invalido")
    archivos = manifest.get("archivos_sha256")
    if not isinstance(archivos, dict) or not archivos:
        raise IntegridadError("manifest_version_invalido")
    for relativo, hash_esperado in archivos.items():
        if (
            not isinstance(relativo, str)
            or not _ruta_controlada(relativo)
            or not isinstance(hash_esperado, str)
            or _SHA256_RE.fullmatch(hash_esperado) is None
        ):
            raise IntegridadError("manifest_version_invalido")


def _ruta_controlada(relativo: str) -> bool:
    """Una ruta del manifest tiene que caer bajo alguna raíz controlada."""

    if not relativo or relativo.startswith("/") or "\\" in relativo:
        return False
    if ".." in Path(relativo).parts:
        return False
    return any(
        relativo == raiz or relativo.startswith(f"{raiz}/")
        for raiz in RUTAS_CONTROLADAS
    )


def comparar_archivos(
    raiz: Path, esperados: Mapping[str, str]
) -> list[dict[str, object]]:
    """Las discrepancias entre el manifest y el árbol del host.

    Tres motivos cerrados: `faltante` (está en el manifest y no en el host),
    `modificado` (los hashes difieren) y `sobrante` (está en el host y no en
    el manifest). Cada discrepancia lleva el hash esperado y el encontrado
    —`None` cuando no existe— para que la auditoría muestre los dos.
    """

    raiz = Path(raiz)
    encontrados = {
        relativo: sha256_archivo(raiz / relativo)
        for relativo in listar_controlados(raiz)
    }
    discrepancias: list[dict[str, object]] = []
    for relativo in sorted(esperados):
        esperado = esperados[relativo]
        if relativo not in encontrados:
            discrepancias.append(
                {
                    "archivo": relativo,
                    "motivo": "faltante",
                    "hash_esperado": esperado,
                    "hash_encontrado": None,
                }
            )
        elif encontrados[relativo] != esperado:
            discrepancias.append(
                {
                    "archivo": relativo,
                    "motivo": "modificado",
                    "hash_esperado": esperado,
                    "hash_encontrado": encontrados[relativo],
                }
            )
    for relativo in sorted(set(encontrados) - set(esperados)):
        discrepancias.append(
            {
                "archivo": relativo,
                "motivo": "sobrante",
                "hash_esperado": None,
                "hash_encontrado": encontrados[relativo],
            }
        )
    return discrepancias


class AuditoriaIntegridad:
    """El log de la verificación: una línea JSONL append-only por arranque.

    Vive en `logs/integridad-arranque.jsonl` bajo el directorio de salida,
    junto al log del scheduler y al del respaldo, así que viaja dentro del
    respaldo del día siguiente. Lleva hashes, la versión y rutas relativas del
    repo: nunca contenido de archivos ni credenciales.
    """

    def __init__(self, directorio_salida: Path) -> None:
        self._path = Path(directorio_salida) / "logs" / AUDITORIA_NOMBRE

    @property
    def path(self) -> Path:
        return self._path

    def anexar(
        self,
        *,
        resultado: str,
        motivo: str | None,
        version: str | None,
        manifest_version_sha256: str | None,
        archivos_esperados: int,
        discrepancias: Iterable[Mapping[str, object]],
    ) -> dict[str, Any]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        entrada = {
            "record": AUDITORIA_RECORD,
            "resultado": resultado,
            "motivo": motivo,
            "version": version,
            "manifest_version_sha256": manifest_version_sha256,
            "archivos_esperados": archivos_esperados,
            "discrepancias": [dict(item) for item in discrepancias],
            "ejecutado_en": datetime.now(timezone.utc).isoformat(),
        }
        with self._path.open("a", encoding="utf-8", newline="") as archivo:
            archivo.write(json.dumps(entrada, ensure_ascii=False, sort_keys=True))
            archivo.write("\n")
        return entrada


def verificar_integridad_al_arrancar(
    *,
    directorio_salida: Path,
    raiz: Path | None = None,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Verifica el árbol del host contra el manifest de versión, fail-closed.

    Escribe siempre una línea de auditoría y levanta `IntegridadError` si algo
    no coincide, si el manifest falta o si es inválido. La auditoría se anexa
    antes de levantar: el motivo del rechazo queda registrado aunque el
    arranque no siga.
    """

    raiz = Path(raiz) if raiz is not None else raiz_agente()
    manifiesto = (
        Path(manifest_path)
        if manifest_path is not None
        else raiz / MANIFEST_VERSION_NOMBRE
    )
    auditoria = AuditoriaIntegridad(directorio_salida)

    try:
        contenido = manifiesto.read_bytes()
    except OSError:
        auditoria.anexar(
            resultado="FAIL",
            motivo="manifest_version_ausente",
            version=None,
            manifest_version_sha256=None,
            archivos_esperados=0,
            discrepancias=(),
        )
        raise IntegridadError("manifest_version_ausente") from None

    manifest_version_sha256 = sha256_bytes(contenido)
    try:
        documento = json.loads(contenido)
        validar_manifest(documento)
    except (UnicodeDecodeError, json.JSONDecodeError, IntegridadError):
        auditoria.anexar(
            resultado="FAIL",
            motivo="manifest_version_invalido",
            version=None,
            manifest_version_sha256=manifest_version_sha256,
            archivos_esperados=0,
            discrepancias=(),
        )
        raise IntegridadError("manifest_version_invalido") from None

    assert isinstance(documento, dict)
    esperados = documento["archivos_sha256"]
    assert isinstance(esperados, dict)
    discrepancias = comparar_archivos(raiz, esperados)
    if discrepancias:
        auditoria.anexar(
            resultado="FAIL",
            motivo="integridad_archivos_no_coinciden",
            version=documento["version"],
            manifest_version_sha256=manifest_version_sha256,
            archivos_esperados=len(esperados),
            discrepancias=discrepancias,
        )
        raise IntegridadError(
            "integridad_archivos_no_coinciden", discrepancias=discrepancias
        )

    return auditoria.anexar(
        resultado="PASS",
        motivo=None,
        version=documento["version"],
        manifest_version_sha256=manifest_version_sha256,
        archivos_esperados=len(esperados),
        discrepancias=(),
    )
