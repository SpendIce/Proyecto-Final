#!/usr/bin/env python3
"""Corrida única del Agente 1 en el servidor de la facultad (#132).

La mañana del miércoles 21/10/2026 hay una sola ventana para probar el
sistema en `labredesfie`: correr y mirar, no depurar. Este runner encadena
los pasos en el orden de la demo y corta en la primera falla con un código
de salida propio, para que el operador sepa qué mirar sin leer un
traceback.

Pasos:

1. **Preflight** (offline): raíz del repo, commit, host, Python, variables
   de Workspace, credencial durable (cuenta de servicio o, como
   contingencia, el trío OAuth anterior) y los datos sintéticos de HU-014/HU-012.
2. **Ollama** (live): `GET /api/version` contra el loopback y comparación
   con la versión congelada de la medición (#50), más `GET /api/tags` para
   confirmar que el modelo está descargado.
3. **Smoke de Workspace** (live): `workspace_smoke.py --live`, una lectura
   de sólo lectura de la planilla autorizada.
4. **Gacetilla E2E** (live): `workspace_e2e.py --live` con el doble opt-in
   de escritura; deja un borrador pendiente de validación humana.
5. **HU-014** (offline): emisión de certificados con la lista sintética,
   las dos aprobaciones de línea y la aprobación del lote.
6. **HU-012** (offline): el pedido de plantilla por el canal del Form y el
   circuito completo de la plantilla con los CSV sintéticos.

El modo por defecto es **dry-run**: valida la configuración local, imprime
el plan y no abre red ni toca Workspace. `--live` ejecuta de verdad.

Decisiones que no se ven en el código:

- **Los secretos nunca pasan por argv.** Los pasos heredan el entorno; el
  comando que se muestra y se guarda no lleva valores de credenciales.
- **La evidencia se sanitiza al escribirla.** El log y el JSON de la
  corrida reemplazan el contenido de las variables sensibles y la ruta de
  la clave; no se guarda el contenido de ningún `.env`.
- **El presupuesto se controla antes de cada paso, no dentro.** Un paso que
  ya arrancó termina (o agota su propio timeout); el corte de 45 minutos se
  aplica al siguiente. Así el corte nunca deja un proceso a medio escribir.
- **El registro de idempotencia del E2E es estable** (`tmp/workspace-e2e`),
  no la carpeta de evidencia: una repetición devuelve `DUPLICADA` en vez de
  crear otro borrador en Drive. Los manifiestos nuevos se copian a la
  evidencia de la corrida.
- **El modelo no se decide acá.** Se toma por parámetro (`--modelo`), con
  El modelo entra por parámetro; para la demo del 21/10 es `gemma4:e4b` (#51).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TextIO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.workspace_auth import (  # noqa: E402
    CLIENT_ID_ENV,
    CLIENT_SECRET_ENV,
    IMPERSONATED_ACCOUNT_ENV,
    REFRESH_TOKEN_ENV,
    SERVICE_ACCOUNT_KEY_ENV,
)

OLLAMA_BASE = "http://127.0.0.1:11434"
OLLAMA_VERSION_DEFAULT = "0.40.6"
MODELO_DEFAULT = "llama3.2:3b"
ID_SOLICITUD_DEFAULT = "SYN-001"
ACTIVIDAD_HU014 = "SYN-001"
PRESUPUESTO_DEFAULT_MIN = 45.0
SALIDA_E2E = ROOT / "tmp" / "workspace-e2e"

EXIT_OK = 0
EXIT_PREFLIGHT = 1
EXIT_OLLAMA = 2
EXIT_SMOKE = 3
EXIT_GACETILLA = 4
EXIT_HU014 = 5
EXIT_HU012 = 6
EXIT_PRESUPUESTO = 7
EXIT_USO = 64

_VARS_WORKSPACE = (
    "AGENTE1_WORKSPACE_AMBIENTE",
    "AGENTE1_WORKSPACE_SPREADSHEET_ID",
    "AGENTE1_WORKSPACE_RANGO_A1",
    "AGENTE1_WORKSPACE_FOLDER_ID",
    "AGENTE1_WORKSPACE_TEMPLATE_ID",
    "AGENTE1_WORKSPACE_TIMEOUT_S",
    "AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES",
)
_SCRIPTS = (
    "workspace_smoke.py",
    "workspace_e2e.py",
    "emitir_certificados.py",
    "registrar_form_decisiones.py",
    "atender_canal_form.py",
    "plantilla_actividad_lote_demo.py",
)
_DATOS = (
    "data/actividades_sinteticas.csv",
    "data/actividades_notebooklm_n2_sinteticas.csv",
    "data/plan_pagos_notebooklm_n2.csv",
    "data/padron_pagos_sintetico.csv",
    "data/padron_roles_sintetico.csv",
)
_CUENTA_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\Z")
_COMMIT_RE = re.compile(r"[0-9a-f]{7,40}\Z")
_SECRETO_NOMBRE_RE = re.compile(
    r"(TOKEN|SECRET|PASSWORD|CREDENTIAL|PRIVATE|SERVICE_ACCOUNT_KEY)"
)

_PADRON = """correo,rol
aux@example.invalid,auxiliar_seu
rgc@example.invalid,RESPONSABLE_GESTION_CONOCIMIENTO
coord@example.invalid,COORDINADOR_EXTENSION
"""
_LISTA = """nombre,apellido,dni,mail,tratamiento,condicion
Ana,Prueba Uno,30111222,ana.prueba@example.invalid,Dra.,asistencia
Bruno,Prueba Dos,30222333,bruno.prueba@example.invalid,Lic.,aprobacion
"""
_LINEA = (
    "En el marco de la política de extensión universitaria, la actividad aporta\n"
    "a la vinculación tecnológica educativa.\n"
)
_PEDIDO_HU012 = """Marca temporal,Correo,Pedido
2026-10-10 09:00:00,solicitante@example.invalid,generá la plantilla de correos para INTELIGENCIA ARTIFICIAL APLICADA A LA EDUCACIÓN Y GESTIÓN: NOTEBOOKLM - NIVEL 2
"""


@dataclass(frozen=True)
class Opciones:
    live: bool
    modelo: str
    ollama_version: str
    id_solicitud: str
    presupuesto_min: float
    evidencia_dir: Path
    root: Path = ROOT
    salida_e2e: Path = SALIDA_E2E
    timeout_modelo: float = 300.0


@dataclass(frozen=True)
class ResultadoComando:
    codigo: int
    salida: str
    duracion_s: float = 0.0


@dataclass
class Contexto:
    environ: Mapping[str, str]
    host: str
    commit: str
    python: str
    plataforma: str
    ahora: Callable[[], datetime]
    monotonic: Callable[[], float]
    ejecutar: Callable[
        [Sequence[str], Path, Mapping[str, str], float], ResultadoComando
    ]
    consultar: Callable[[str, float], object]
    salida: TextIO
    root: Path = ROOT


@dataclass(frozen=True)
class Chequeo:
    nombre: str
    ok: bool
    detalle: str


@dataclass
class ResultadoPaso:
    ok: bool
    detalle: str
    exit_code: int | None = None
    comandos: list[dict[str, object]] = field(default_factory=list)
    datos: dict[str, object] = field(default_factory=dict)


@dataclass
class Paso:
    id: str
    nombre: str
    modo: str
    codigo_fallo: int
    funcion: Callable[
        [Opciones, Contexto, "Registro"], ResultadoPaso
    ]
    estado: str = "pendiente"
    inicio: str | None = None
    duracion_s: float = 0.0
    exit_code: int | None = None
    detalle: str = ""
    comandos: list[dict[str, object]] = field(default_factory=list)
    datos: dict[str, object] = field(default_factory=dict)


class Sanitizador:
    """Reemplaza valores sensibles antes de imprimir o persistir.

    La lista de valores sale del propio entorno: toda variable con nombre de
    token, clave o credencial, más la ruta de la clave de la cuenta de
    servicio. Los patrones cubren las formas habituales de un token OAuth y
    de una clave PEM escapada en JSON. No se toca ningún hash: los hashes
    son evidencia, no secretos.
    """

    def __init__(self, environ: Mapping[str, str], ruta_clave: str | None) -> None:
        self._valores: dict[str, str] = {}
        for nombre, valor in environ.items():
            if _SECRETO_NOMBRE_RE.search(nombre.upper()) and len(valor) >= 8:
                self._valores[valor] = "<redactado>"
        if ruta_clave:
            self._valores[ruta_clave] = "<ruta-clave>"
        cuenta = environ.get(IMPERSONATED_ACCOUNT_ENV, "").strip()
        if cuenta:
            self._valores[cuenta] = "<cuenta>"
        self._patrones = (
            (re.compile(r"ya29\.[A-Za-z0-9._-]+"), "<token>"),
            (
                re.compile(r"(?i)(authorization:\s*bearer\s+)\S+"),
                r"\1<token>",
            ),
            (
                re.compile(
                    r'(?i)("?(?:access_token|id_token|refresh_token|'
                    r'client_secret|private_key)"?\s*[:=]\s*)'
                    r'("[^"]*"|[^,\s}]+)'
                ),
                r'\1"<redactado>"',
            ),
            (
                re.compile(
                    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?"
                    r"-----END [A-Z ]*PRIVATE KEY-----",
                    re.DOTALL,
                ),
                "<clave-privada>",
            ),
        )

    def __call__(self, texto: str) -> str:
        for valor in sorted(self._valores, key=len, reverse=True):
            texto = texto.replace(valor, self._valores[valor])
        for patron, reemplazo in self._patrones:
            texto = patron.sub(reemplazo, texto)
        return texto


class Registro:
    """Salida por pantalla y transcripción, siempre sanitizada."""

    def __init__(self, salida: TextIO, sanitizar: Callable[[str], str]) -> None:
        self._salida = salida
        self._sanitizar = sanitizar
        self._lineas: list[str] = []

    def linea(self, texto: str = "") -> None:
        limpio = self._sanitizar(texto)
        print(limpio, file=self._salida)
        self._lineas.append(limpio)

    def texto(self) -> str:
        return "\n".join(self._lineas) + "\n"

    def sanitizar(self, texto: str) -> str:
        return self._sanitizar(texto)


class _ParserSeguro(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # No repetir argv: podría contener un secreto pegado por error.
        self.exit(EXIT_USO, "error: argumentos inválidos\n")


def _ahora() -> datetime:
    return datetime.now().astimezone()


def _ejecutar_comando(
    comando: Sequence[str],
    cwd: Path,
    environ: Mapping[str, str],
    timeout_s: float,
) -> ResultadoComando:
    entorno = dict(environ)
    previo = entorno.get("PYTHONPATH", "")
    entorno["PYTHONPATH"] = (
        f"{cwd / 'src'}{os.pathsep}{previo}" if previo else str(cwd / "src")
    )
    inicio = time.monotonic()
    try:
        proceso = subprocess.run(
            list(comando),
            cwd=str(cwd),
            env=entorno,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ResultadoComando(
            124,
            f"tiempo agotado tras {timeout_s:.0f} s",
            time.monotonic() - inicio,
        )
    except OSError as exc:
        return ResultadoComando(
            127,
            f"no se pudo ejecutar el comando ({type(exc).__name__})",
            time.monotonic() - inicio,
        )
    salida = (proceso.stdout or "") + (proceso.stderr or "")
    return ResultadoComando(
        proceso.returncode, salida, time.monotonic() - inicio
    )


def _consultar_json(url: str, timeout_s: float) -> object:
    with urllib.request.urlopen(url, timeout=timeout_s) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def _mostrar_comando(comando: Sequence[str]) -> str:
    partes = ["python" if parte == sys.executable else parte for parte in comando]
    return " ".join(partes)


def _correr(
    contexto: Contexto,
    registro: Registro,
    comando: Sequence[str],
    *,
    timeout_s: float,
) -> tuple[ResultadoComando, dict[str, object]]:
    registro.linea(f"$ {_mostrar_comando(comando)}")
    resultado = contexto.ejecutar(
        list(comando), contexto.root, contexto.environ, timeout_s
    )
    for linea in resultado.salida.splitlines():
        registro.linea(linea)
    entrada = {
        "comando": _mostrar_comando(comando),
        "exit_code": resultado.codigo,
        "duracion_s": round(resultado.duracion_s, 3),
    }
    return resultado, entrada


def _ultimo_json(texto: str) -> dict[str, object] | None:
    for linea in reversed(texto.splitlines()):
        limpia = linea.strip()
        if not limpia.startswith("{"):
            continue
        try:
            valor = json.loads(limpia)
        except json.JSONDecodeError:
            continue
        if isinstance(valor, dict):
            return valor
    return None


def _json_por_linea(texto: str) -> list[dict[str, object]]:
    objetos: list[dict[str, object]] = []
    for linea in texto.splitlines():
        limpia = linea.strip()
        if not limpia.startswith("{"):
            continue
        try:
            valor = json.loads(limpia)
        except json.JSONDecodeError:
            continue
        if isinstance(valor, dict):
            objetos.append(valor)
    return objetos


def _leer_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    objetos: list[dict[str, object]] = []
    for linea in path.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        try:
            valor = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if isinstance(valor, dict):
            objetos.append(valor)
    return objetos


def _preflight(
    opciones: Opciones, contexto: Contexto
) -> tuple[list[Chequeo], str | None]:
    chequeos: list[Chequeo] = []
    fallo: str | None = None

    def agregar(nombre: str, ok: bool, detalle: str, accion: str = "") -> None:
        nonlocal fallo
        chequeos.append(Chequeo(nombre, ok, detalle))
        if not ok and fallo is None:
            fallo = accion or detalle

    raiz_ok = (
        (opciones.root / "pyproject.toml").is_file()
        and (opciones.root / "src" / "agente1").is_dir()
        and (opciones.root / "scripts").is_dir()
    )
    agregar(
        "raiz",
        raiz_ok,
        f"raíz del Agente 1: {opciones.root}",
        "No encuentro la raíz del Agente 1 (falta pyproject.toml o src/agente1). "
        "Corré el script desde el checkout de ~/p100/Agente1.",
    )

    commit_ok = bool(_COMMIT_RE.fullmatch(contexto.commit))
    agregar(
        "commit",
        commit_ok,
        f"commit {contexto.commit or 'no disponible'}",
        "No pude leer `git rev-parse HEAD` en la raíz del repo. "
        "¿El checkout está completo? Corré `git -C ~/p100/Agente1 rev-parse HEAD`.",
    )

    agregar(
        "host",
        bool(contexto.host.strip()),
        f"host {contexto.host or 'no disponible'}",
        "No pude resolver el nombre del host. Revisá `hostname` antes de seguir.",
    )

    try:
        mayor, menor = (int(p) for p in contexto.python.split(".")[:2])
        python_ok = (mayor, menor) >= (3, 11)
    except (ValueError, TypeError):
        python_ok = False
    agregar(
        "python",
        python_ok,
        f"Python {contexto.python}",
        f"Python {contexto.python} no sirve: el Agente 1 pide 3.11 o más. "
        "Entrá al venv con `uv sync` y corré `uv run python scripts/corrida_unica.py`.",
    )

    clave = contexto.environ.get(SERVICE_ACCOUNT_KEY_ENV, "").strip()
    cuenta = contexto.environ.get(IMPERSONATED_ACCOUNT_ENV, "").strip()
    oauth = {
        CLIENT_ID_ENV: contexto.environ.get(CLIENT_ID_ENV, "").strip(),
        CLIENT_SECRET_ENV: contexto.environ.get(CLIENT_SECRET_ENV, "").strip(),
        REFRESH_TOKEN_ENV: contexto.environ.get(REFRESH_TOKEN_ENV, "").strip(),
    }
    presentes = [
        nombre
        for nombre, valor in (
            (SERVICE_ACCOUNT_KEY_ENV, clave),
            (IMPERSONATED_ACCOUNT_ENV, cuenta),
        )
        if valor
    ]
    oauth_presentes = [nombre for nombre, valor in oauth.items() if valor]
    usa_cuenta_servicio = len(presentes) == 2
    usa_oauth = len(oauth_presentes) == 3

    if len(presentes) == 1:
        falta = (
            IMPERSONATED_ACCOUNT_ENV
            if presentes[0] == SERVICE_ACCOUNT_KEY_ENV
            else SERVICE_ACCOUNT_KEY_ENV
        )
        agregar(
            "credencial",
            False,
            "el par de la cuenta de servicio está a medias",
            f"El par de credenciales está a medias: {presentes[0]} está "
            f"definida y falta {falta}. El par es todo o nada; no hay "
            "respaldo silencioso. Exportá las dos variables o ninguna.",
        )
    elif usa_cuenta_servicio:
        agregar("credencial", True, "par de la cuenta de servicio completo")
    elif oauth_presentes and not usa_oauth:
        faltan_oauth = [nombre for nombre in oauth if not oauth[nombre]]
        agregar(
            "credencial",
            False,
            "el trío OAuth está a medias",
            "El trío OAuth anterior está incompleto: falta "
            + ", ".join(faltan_oauth)
            + ". Es todo o nada; exportá el trío completo o ninguna.",
        )
    elif usa_oauth:
        agregar(
            "credencial",
            True,
            "trío OAuth anterior completo (Plan B)",
            "Se usará el refresh token OAuth anterior como contingencia. "
            "La identidad objetivo sigue siendo la cuenta de servicio (#99).",
        )
    else:
        agregar(
            "credencial",
            False,
            "no hay credencial durable configurada",
            "Configurá el par de la cuenta de servicio o, como contingencia, "
            "el trío OAuth anterior. Nunca por argv.",
        )

    faltantes = [
        nombre
        for nombre in _VARS_WORKSPACE
        if not contexto.environ.get(nombre, "").strip()
    ]
    agregar(
        "variables_workspace",
        not faltantes,
        "variables de Workspace completas"
        if not faltantes
        else "faltan: " + ", ".join(faltantes),
        "Faltan variables de Workspace: "
        + ", ".join(faltantes)
        + ". Cargá el entorno de ~/.config/agente1/ (fuera del repo) y volvé "
        "a correr el dry-run.",
    )

    ambiente = contexto.environ.get("AGENTE1_WORKSPACE_AMBIENTE", "").strip()
    if ambiente:
        agregar(
            "ambiente",
            ambiente in {"D2", "D3"},
            f"ambiente {ambiente}",
            f"AGENTE1_WORKSPACE_AMBIENTE vale {ambiente}; los ambientes "
            "válidos son D2 y D3. Para la demo, D2.",
        )

    if clave:
        ruta = Path(clave).expanduser()
        if not ruta.exists():
            agregar(
                "clave_archivo",
                False,
                "la ruta de la clave no existe",
                "La variable AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY apunta a "
                "un archivo que no existe. Copiá el JSON con scp a una ruta "
                "fuera del repo y volvé a exportar la variable.",
            )
        elif not ruta.is_file():
            agregar(
                "clave_archivo",
                False,
                "la ruta de la clave no es un archivo",
                "La ruta de la clave es un directorio, no un archivo. "
                "Pasá la ruta del JSON de la cuenta de servicio.",
            )
        else:
            agregar("clave_archivo", True, "la clave es un archivo existente")
            modo = stat.S_IMODE(ruta.stat().st_mode)
            agregar(
                "clave_permisos",
                modo == 0o600,
                f"permisos {modo:o}",
                f"La clave tiene permisos {modo:o}; tienen que ser 600. "
                "Corré `chmod 600` sobre el archivo al que apunta "
                "AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY.",
            )
            try:
                documento = json.loads(ruta.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                agregar(
                    "clave_json",
                    False,
                    "la clave no se puede leer como JSON",
                    "El archivo de la clave no es JSON válido. Volvé a "
                    "copiarlo con scp, sin editarlo ni recomprimirlo.",
                )
            else:
                cliente = (
                    documento.get("client_email")
                    if isinstance(documento, dict)
                    else None
                )
                privada = (
                    documento.get("private_key")
                    if isinstance(documento, dict)
                    else None
                )
                valida = (
                    isinstance(cliente, str)
                    and bool(cliente.strip())
                    and isinstance(privada, str)
                    and "PRIVATE KEY" in privada
                )
                agregar(
                    "clave_json",
                    valida,
                    "JSON parseable con client_email y private_key"
                    if valida
                    else "JSON sin client_email o private_key",
                    "El JSON de la clave no tiene `client_email` y "
                    "`private_key`. No es el JSON de la cuenta de servicio: "
                    "volvé a descargarlo de la consola de Google.",
                )
    elif usa_oauth:
        # La credencial OAuth ya se validó arriba; no hay archivo de clave.
        pass
    else:
        agregar(
            "clave_archivo",
            False,
            "clave no configurada",
            "No hay ruta de clave configurada. Ver la variable "
            "AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY.",
        )

    if cuenta:
        agregar(
            "cuenta_suplantada",
            bool(_CUENTA_RE.fullmatch(cuenta)),
            "cuenta a la que se hace pasar con forma de correo"
            if _CUENTA_RE.fullmatch(cuenta)
            else "la cuenta a la que se hace pasar no tiene forma de correo",
            "AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT no tiene forma de "
            "correo. Tiene que ser la cuenta de Workspace por la que se "
            "hace pasar la cuenta de servicio.",
        )

    faltan_scripts = [
        nombre for nombre in _SCRIPTS
        if not (opciones.root / "scripts" / nombre).is_file()
    ]
    agregar(
        "scripts",
        not faltan_scripts,
        "los seis runners existen"
        if not faltan_scripts
        else "faltan: " + ", ".join(faltan_scripts),
        "Faltan runners en scripts/: "
        + ", ".join(faltan_scripts)
        + ". El checkout está incompleto o el ticket no está mergeado.",
    )

    faltan_datos = [
        nombre for nombre in _DATOS
        if not (opciones.root / nombre).is_file()
    ]
    agregar(
        "datos_sinteticos",
        not faltan_datos,
        "los CSV sintéticos existen"
        if not faltan_datos
        else "faltan: " + ", ".join(faltan_datos),
        "Faltan datos sintéticos: "
        + ", ".join(faltan_datos)
        + ". No sigas: HU-014 y HU-012 no se pueden correr.",
    )

    evidencia = opciones.evidencia_dir
    evidencia_ok = not evidencia.is_file() and not (
        (evidencia / "corrida.json").is_file()
    )
    agregar(
        "evidencia",
        evidencia_ok,
        f"evidencia en {evidencia}",
        "El directorio de evidencia ya tiene una corrida. Elegí otro "
        "`--evidencia-dir` para no pisar la anterior.",
    )

    agregar(
        "parametros",
        bool(opciones.modelo.strip())
        and bool(opciones.ollama_version.strip())
        and bool(opciones.id_solicitud.strip())
        and opciones.presupuesto_min > 0,
        f"modelo {opciones.modelo}; Ollama esperado "
        f"{opciones.ollama_version}; presupuesto "
        f"{opciones.presupuesto_min:g} min",
        "Revisá --id-solicitud, --modelo, --ollama-version y "
        "--presupuesto-min: alguno está vacío o no es positivo.",
    )

    return chequeos, fallo


def _paso_ollama(
    opciones: Opciones, contexto: Contexto, registro: Registro
) -> ResultadoPaso:
    registro.linea(
        f"Consulta a {OLLAMA_BASE}/api/version (esperado "
        f"{opciones.ollama_version})..."
    )
    try:
        version_doc = contexto.consultar(f"{OLLAMA_BASE}/api/version", 5.0)
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        return ResultadoPaso(
            False,
            f"No pude consultar Ollama en {OLLAMA_BASE}/api/version "
            f"({type(exc).__name__}). Levantá Ollama 0.40.6 en espacio de "
            "usuario (sin sudo), en loopback :11434, y volvé a intentar.",
        )
    version = (
        version_doc.get("version") if isinstance(version_doc, dict) else None
    )
    if not isinstance(version, str) or not version.strip():
        return ResultadoPaso(
            False,
            "Ollama respondió algo que no tiene `version`. Revisá que el "
            "puerto 11434 sea el Ollama de 0.40.6 y no otro servicio.",
        )
    if version != opciones.ollama_version:
        return ResultadoPaso(
            False,
            f"Ollama responde {version}, se esperaba "
            f"{opciones.ollama_version}. La versión se congela con el modelo "
            "(medición #50): no actualices ni reinicies el servicio del "
            "sistema; levantá el binario de 0.40.6 de ~/ollama y repetí.",
            datos={"ollama_version": version},
        )
    registro.linea(f"Ollama {version}: versión correcta.")

    try:
        tags = contexto.consultar(f"{OLLAMA_BASE}/api/tags", 5.0)
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        return ResultadoPaso(
            False,
            f"Ollama {version} responde la versión pero falló /api/tags "
            f"({type(exc).__name__}). Revisá `ollama ps` y volvé a intentar.",
            datos={"ollama_version": version},
        )
    nombres: set[str] = set()
    if isinstance(tags, dict) and isinstance(tags.get("models"), list):
        for entrada in tags["models"]:
            if not isinstance(entrada, dict):
                continue
            for clave in ("name", "model"):
                valor = entrada.get(clave)
                if isinstance(valor, str):
                    nombres.add(valor)
    if opciones.modelo not in nombres and f"{opciones.modelo}:latest" not in nombres:
        return ResultadoPaso(
            False,
            f"El modelo {opciones.modelo} no está descargado en este Ollama. "
            f"Descargalo sin sudo con `ollama pull {opciones.modelo}` y "
            "volvé a correr el paso.",
            datos={"ollama_version": version},
        )
    registro.linea(
        f"Modelo {opciones.modelo}: descargado. "
        "Ollama queda listo para la gacetilla."
    )
    return ResultadoPaso(
        True,
        f"Ollama {version}; modelo {opciones.modelo} disponible",
        datos={"ollama_version": version, "modelo": opciones.modelo},
    )


def _paso_smoke(
    opciones: Opciones, contexto: Contexto, registro: Registro
) -> ResultadoPaso:
    comando = [
        sys.executable,
        str(opciones.root / "scripts" / "workspace_smoke.py"),
        "--live",
        "--id-solicitud",
        opciones.id_solicitud,
    ]
    resultado, entrada = _correr(contexto, registro, comando, timeout_s=180.0)
    payload = _ultimo_json(resultado.salida) or {}
    if resultado.codigo != 0:
        return ResultadoPaso(
            False,
            "El smoke de Workspace falló "
            f"(exit {resultado.codigo}, resultado "
            f"{payload.get('resultado', 'sin JSON')}). Revisá el par de la "
            "cuenta de servicio, la delegación y la lista cerrada de cuentas; "
            "no hay fallback silencioso.",
            exit_code=resultado.codigo,
            comandos=[entrada],
        )
    if payload.get("resultado") != "lectura_confirmada":
        return ResultadoPaso(
            False,
            "El smoke terminó sin error de proceso pero no confirmó la "
            f"lectura (resultado {payload.get('resultado', 'desconocido')}). "
            "Mirá la planilla, el rango A1 y el id de solicitud.",
            exit_code=resultado.codigo,
            comandos=[entrada],
        )
    return ResultadoPaso(
        True,
        f"Lectura de la planilla confirmada con el id {opciones.id_solicitud}",
        exit_code=resultado.codigo,
        comandos=[entrada],
    )


def _paso_gacetilla(
    opciones: Opciones, contexto: Contexto, registro: Registro
) -> ResultadoPaso:
    manifests = opciones.salida_e2e / "manifests"
    antes = (
        {p.name for p in manifests.glob("*.json")} if manifests.is_dir() else set()
    )
    comando = [
        sys.executable,
        str(opciones.root / "scripts" / "workspace_e2e.py"),
        "--live",
        "--confirm-write-workspace",
        "--tipo",
        "gacetilla",
        "--id-solicitud",
        opciones.id_solicitud,
        "--salida",
        str(opciones.salida_e2e),
        "--modelo",
        opciones.modelo,
        "--timeout-modelo",
        f"{opciones.timeout_modelo:g}",
    ]
    resultado, entrada = _correr(contexto, registro, comando, timeout_s=900.0)
    payload = _ultimo_json(resultado.salida) or {}
    estado = payload.get("estado")
    duplicada = estado == "DUPLICADA"
    if resultado.codigo != 0 or estado not in {"PENDIENTE_VALIDACION", "DUPLICADA"}:
        detalle = (
            f"El E2E de gacetilla no terminó bien (exit "
            f"{resultado.codigo}, estado {estado or 'sin JSON'})."
        )
        if estado == "BLOQUEADA_RECONCILIACION":
            detalle += (
                " Hay una escritura previa en curso o incierta: no repitas "
                "el paso; reconciliá con DSI/SEU antes de cualquier reintento."
            )
        else:
            detalle += (
                " Mirá el resultado del runner y el manifiesto en "
                f"{opciones.salida_e2e}/manifests/. Si falló la generación, "
                "no cambies de modelo en vivo: mirá el rechazo y mostrá la evidencia de la mañana."
            )
        return ResultadoPaso(
            False, detalle, exit_code=resultado.codigo, comandos=[entrada]
        )

    despues = (
        {p.name for p in manifests.glob("*.json")} if manifests.is_dir() else set()
    )
    nuevos = sorted(despues - antes)
    if nuevos:
        destino = opciones.evidencia_dir / "workspace-e2e" / "manifests"
        try:
            destino.mkdir(parents=True, exist_ok=True)
            for nombre in nuevos:
                shutil.copy2(manifests / nombre, destino / nombre)
        except OSError as exc:
            return ResultadoPaso(
                False,
                "El E2E terminó, pero no pude copiar el manifiesto a la "
                f"evidencia ({type(exc).__name__}). Queda en "
                f"{opciones.salida_e2e}/manifests/; revisá permisos y "
                "copialo a mano antes de seguir.",
                exit_code=resultado.codigo,
                comandos=[entrada],
                datos={"estado": estado},
            )
        registro.linea(
            f"Manifiesto(s) copiado(s) a la evidencia: {', '.join(nuevos)}"
        )
    else:
        return ResultadoPaso(
            False,
            "El E2E terminó con estado válido pero no dejó un manifiesto "
            "nuevo en tmp/workspace-e2e/manifests/. No puedo acreditar la "
            "corrida; revisá el directorio antes de seguir.",
            exit_code=resultado.codigo,
            comandos=[entrada],
        )

    if duplicada:
        detalle = (
            "La gacetilla ya estaba registrada (DUPLICADA): no se creó otro "
            "documento. Es evidencia válida; no borres el registro de "
            "idempotencia."
        )
    else:
        detalle = (
            "Borrador de gacetilla creado y pendiente de validación humana. "
            "No se publicó ni se compartió."
        )
    return ResultadoPaso(
        True,
        detalle,
        exit_code=resultado.codigo,
        comandos=[entrada],
        datos={"estado": estado, "manifiestos": nuevos},
    )


def _paso_hu014(
    opciones: Opciones, contexto: Contexto, registro: Registro
) -> ResultadoPaso:
    base = opciones.evidencia_dir / "hu014"
    run = base / "run"
    base.mkdir(parents=True, exist_ok=True)
    (base / "padron.csv").write_text(_PADRON, encoding="utf-8")
    (base / "lista.csv").write_text(_LISTA, encoding="utf-8")
    (base / "linea.txt").write_text(_LINEA, encoding="utf-8")
    (base / "decisiones-linea.csv").unlink(missing_ok=True)
    (base / "decisiones-lote.csv").unlink(missing_ok=True)
    comandos_hu014: list[dict[str, object]] = []

    def emitir() -> tuple[ResultadoComando, dict[str, object], dict[str, object]]:
        comando = [
            sys.executable,
            str(opciones.root / "scripts" / "emitir_certificados.py"),
            "--actividad",
            ACTIVIDAD_HU014,
            "--lista-csv",
            str(base / "lista.csv"),
            "--linea",
            str(base / "linea.txt"),
            "--aprobador",
            "coord@example.invalid",
            "--solicitante",
            "aux@example.invalid",
            "--directorio",
            str(run),
        ]
        resultado, entrada = _correr(contexto, registro, comando, timeout_s=180.0)
        comandos_hu014.append(entrada)
        return resultado, _ultimo_json(resultado.salida) or {}, entrada

    def registrar(csv: Path, declarar: str | None) -> ResultadoPaso | None:
        comando = [
            sys.executable,
            str(opciones.root / "scripts" / "registrar_form_decisiones.py"),
            "--directorio",
            str(run),
            "--respuestas-csv",
            str(csv),
            "--padron",
            str(base / "padron.csv"),
        ]
        if declarar:
            comando += ["--declarar", declarar]
        resultado, entrada = _correr(contexto, registro, comando, timeout_s=120.0)
        comandos_hu014.append(entrada)
        if resultado.codigo != 0:
            return ResultadoPaso(
                False,
                "No pude registrar las decisiones de HU-014 "
                f"(exit {resultado.codigo}). Mirá el padrón y los roles del "
                "circuito; la decisión se rechaza si el rol no corresponde.",
                exit_code=resultado.codigo,
                comandos=list(comandos_hu014),
            )
        procesadas = [
            item for item in _json_por_linea(resultado.salida)
            if "resultado" in item
        ]
        if not procesadas or any(
            item.get("resultado") != "registrada" for item in procesadas
        ):
            rechazos = [
                str(item.get("rechazo_codigo"))
                for item in procesadas
                if item.get("resultado") != "registrada"
            ]
            return ResultadoPaso(
                False,
                "Las decisiones de HU-014 no quedaron registradas "
                f"({', '.join(rechazos) or 'sin resultados'}). Revisá el rol "
                "y el catálogo del Form de decisiones.",
                exit_code=resultado.codigo,
                comandos=list(comandos_hu014),
            )
        return None

    primero, payload, _entrada1 = emitir()
    if primero.codigo != 0 or payload.get("error") != "linea_descriptiva_no_aprobada":
        return ResultadoPaso(
            False,
            "La primera corrida de HU-014 no quedó pendiente por la línea "
            f"descriptiva (exit {primero.codigo}, estado "
            f"{payload.get('estado', 'sin JSON')}, error "
            f"{payload.get('error', 'ninguno')}). Revisá la lista y la línea "
            "antes de seguir.",
            exit_code=primero.codigo,
            comandos=list(comandos_hu014),
        )
    objetos = [
        item for item in _leer_jsonl(run / "emisiones-certificados-hu014.jsonl")
        if isinstance(item.get("objeto_linea"), str)
    ]
    if not objetos:
        return ResultadoPaso(
            False,
            "La corrida quedó pendiente pero el log no tiene `objeto_linea`. "
            "No puedo armar la decisión de línea; mirá "
            "hu014/run/emisiones-certificados-hu014.jsonl.",
            comandos=list(comandos_hu014),
        )
    objeto_linea = str(objetos[-1]["objeto_linea"])

    (base / "decisiones-linea.csv").write_text(
        "Marca temporal,Correo,Tipo,Objeto,Decisión\n"
        "2026-10-01 10:00:00,rgc@example.invalid,linea_descriptiva,"
        f"{objeto_linea},apruebo_semantica\n"
        "2026-10-01 10:05:00,coord@example.invalid,linea_descriptiva,"
        f"{objeto_linea},apruebo_utilitaria\n",
        encoding="utf-8",
    )
    fallo = registrar(
        base / "decisiones-linea.csv", f"linea_descriptiva:{objeto_linea}"
    )
    if fallo is not None:
        return fallo

    segundo, payload2, _entrada2 = emitir()
    if segundo.codigo != 0 or payload2.get("error") != "lote_no_aprobado":
        return ResultadoPaso(
            False,
            "La segunda corrida de HU-014 no quedó pendiente por el lote "
            f"(exit {segundo.codigo}, estado "
            f"{payload2.get('estado', 'sin JSON')}, error "
            f"{payload2.get('error', 'ninguno')}). Revisá que las dos "
            "aprobaciones de línea hayan quedado registradas.",
            exit_code=segundo.codigo,
            comandos=list(comandos_hu014),
        )
    pendientes = [
        item for item in _leer_jsonl(run / "estado-decisiones" / "decisiones-pendientes.jsonl")
        if item.get("tipo") == "lote"
    ]
    if not pendientes:
        return ResultadoPaso(
            False,
            "La corrida quedó pendiente del lote pero no hay objeto de lote "
            "declarado. Mirá hu014/run/estado-decisiones/decisiones-pendientes.jsonl.",
            comandos=list(comandos_hu014),
        )
    objeto_lote = str(pendientes[-1].get("objeto_id", ""))
    (base / "decisiones-lote.csv").write_text(
        "Marca temporal,Correo,Tipo,Objeto,Decisión\n"
        "2026-10-01 11:00:00,coord@example.invalid,lote,"
        f"{objeto_lote},apruebo_lote\n",
        encoding="utf-8",
    )
    fallo = registrar(base / "decisiones-lote.csv", None)
    if fallo is not None:
        return fallo

    tercero, payload3, _entrada3 = emitir()
    if (
        tercero.codigo != 0
        or payload3.get("estado") != "EMITIDA"
        or payload3.get("emitidas") != 2
    ):
        return ResultadoPaso(
            False,
            "La tercera corrida de HU-014 no emitió los dos certificados "
            f"(exit {tercero.codigo}, estado "
            f"{payload3.get('estado', 'sin JSON')}, emitidas "
            f"{payload3.get('emitidas', 'sin dato')}). Es el gate de "
            "aprobación: no hay emisión parcial.",
            exit_code=tercero.codigo,
            comandos=list(comandos_hu014),
        )
    cierre = [
        item for item in _leer_jsonl(run / "emisiones-certificados-hu014.jsonl")
        if item.get("evento") == "cierre"
    ]
    if not cierre or cierre[-1].get("emitidas") != 2:
        return ResultadoPaso(
            False,
            "La corrida dijo EMITIDA pero el log de cierre no acredita dos "
            "entregas. Mirá hu014/run/emisiones-certificados-hu014.jsonl.",
            comandos=list(comandos_hu014),
        )
    return ResultadoPaso(
        True,
        "HU-014 completo: línea aprobada por los dos roles, lote aprobado y "
        "2 certificados entregados en modo offline.",
        comandos=list(comandos_hu014),
        datos={"emitidas": 2, "objeto_linea": objeto_linea, "objeto_lote": objeto_lote},
    )


def _paso_hu012(
    opciones: Opciones, contexto: Contexto, registro: Registro
) -> ResultadoPaso:
    base = opciones.evidencia_dir / "hu012"
    canal = base / "canal"
    lote = base / "lote"
    base.mkdir(parents=True, exist_ok=True)
    (base / "pedidos.csv").write_text(_PEDIDO_HU012, encoding="utf-8")

    comando_canal = [
        sys.executable,
        str(opciones.root / "scripts" / "atender_canal_form.py"),
        "--directorio",
        str(canal),
        "--respuestas-csv",
        str(base / "pedidos.csv"),
        "--csv",
        str(opciones.root / "data" / "actividades_notebooklm_n2_sinteticas.csv"),
        "--padron",
        str(opciones.root / "data" / "padron_roles_sintetico.csv"),
        "--plan-csv",
        str(opciones.root / "data" / "plan_pagos_notebooklm_n2.csv"),
    ]
    resultado_canal, entrada_canal = _correr(
        contexto, registro, comando_canal, timeout_s=180.0
    )
    lineas_canal = _json_por_linea(resultado_canal.salida)
    despacho = [
        item for item in lineas_canal
        if item.get("intencion") == "generar_plantilla_actividad"
    ]
    resumen = next(
        (item for item in reversed(lineas_canal) if "atendidos" in item), {}
    )
    if resultado_canal.codigo != 0 or not despacho or resumen.get("atendidos") != 1:
        return ResultadoPaso(
            False,
            "El canal de pedidos de HU-012 no clasificó el pedido de "
            f"plantilla (exit {resultado_canal.codigo}, atendidos "
            f"{resumen.get('atendidos', 'sin dato')}). Revisá el CSV de "
            "pedidos y el padrón sintético; el borrador queda en "
            "hu012/canal/borradores/.",
            exit_code=resultado_canal.codigo,
            comandos=[entrada_canal],
        )

    comando_lote = [
        sys.executable,
        str(opciones.root / "scripts" / "plantilla_actividad_lote_demo.py"),
        "--directorio",
        str(lote),
        "--csv",
        str(opciones.root / "data" / "actividades_notebooklm_n2_sinteticas.csv"),
        "--actividad",
        "EJEMPLO-NOTEBOOKLM-N2",
        "--plan-csv",
        str(opciones.root / "data" / "plan_pagos_notebooklm_n2.csv"),
        "--padron-csv",
        str(opciones.root / "data" / "padron_pagos_sintetico.csv"),
        "--padron-roles",
        str(opciones.root / "data" / "padron_roles_sintetico.csv"),
    ]
    resultado_lote, entrada_lote = _correr(
        contexto, registro, comando_lote, timeout_s=300.0
    )
    fases = _json_por_linea(resultado_lote.salida)
    cierre = next(
        (item for item in reversed(fases) if item.get("fase") == "lote"), {}
    )
    estado = cierre.get("estado")
    duplicada = estado == "DUPLICADA"
    if (
        (resultado_lote.codigo != 0 and not duplicada)
        or estado not in {"ENVIO_ENCOLADO", "DUPLICADA"}
        or cierre.get("items") != 3
    ):
        return ResultadoPaso(
            False,
            "El circuito completo de HU-012 no encoló los tres correos "
            f"(exit {resultado_lote.codigo}, estado "
            f"{estado or 'sin JSON'}, items {cierre.get('items', 'sin dato')}). "
            "Mirá hu012/lote/logs/ y el borrador de la plantilla.",
            exit_code=resultado_lote.codigo,
            comandos=[entrada_canal, entrada_lote],
        )
    detalle = (
        "HU-012 completo: el canal clasificó el pedido y el lote encoló y "
        "entregó 3 correos simulados (BORRADOR — NO ENVIAR)."
    )
    if duplicada:
        detalle = (
            "HU-012 ya estaba encolado (DUPLICADA): no se reenvió. Es "
            "evidencia válida; no borres el registro de idempotencia."
        )
    return ResultadoPaso(
        True,
        detalle,
        comandos=[entrada_canal, entrada_lote],
        datos={"estado_lote": estado, "items": 3},
    )


_PASOS: tuple[tuple[str, str, str, int, Callable[..., ResultadoPaso]], ...] = (
    ("ollama", "Ollama y modelo", "live", EXIT_OLLAMA, _paso_ollama),
    ("smoke", "Smoke de Workspace (lectura)", "live", EXIT_SMOKE, _paso_smoke),
    ("gacetilla", "E2E de gacetilla", "live", EXIT_GACETILLA, _paso_gacetilla),
    ("hu014", "HU-014 certificados", "offline", EXIT_HU014, _paso_hu014),
    ("hu012", "HU-012 plantilla y lote", "offline", EXIT_HU012, _paso_hu012),
)


def _plan(opciones: Opciones) -> list[str]:
    salida = [
        "[2] Ollama (live)",
        f"    GET {OLLAMA_BASE}/api/version (esperado {opciones.ollama_version})",
        f"    GET {OLLAMA_BASE}/api/tags (modelo {opciones.modelo})",
        "[3] Smoke de Workspace (live)",
        f"    python scripts/workspace_smoke.py --live --id-solicitud {opciones.id_solicitud}",
        "[4] E2E de gacetilla (live)",
        "    python scripts/workspace_e2e.py --live --confirm-write-workspace "
        f"--tipo gacetilla --id-solicitud {opciones.id_solicitud} "
        f"--salida tmp/workspace-e2e --modelo {opciones.modelo} "
        f"--timeout-modelo {opciones.timeout_modelo:g}",
        "[5] HU-014 certificados (offline)",
        "    python scripts/emitir_certificados.py --actividad SYN-001 "
        "--lista-csv <evidencia>/hu014/lista.csv --linea "
        "<evidencia>/hu014/linea.txt --aprobador coord@example.invalid "
        "--solicitante aux@example.invalid --directorio <evidencia>/hu014/run",
        "    python scripts/registrar_form_decisiones.py --directorio "
        "<evidencia>/hu014/run --respuestas-csv "
        "<evidencia>/hu014/decisiones-linea.csv --padron "
        "<evidencia>/hu014/padron.csv --declarar linea_descriptiva:<objeto>",
        "    (segunda corrida, aprobación del lote y tercera corrida)",
        "[6] HU-012 plantilla y lote (offline)",
        "    python scripts/atender_canal_form.py --directorio "
        "<evidencia>/hu012/canal --respuestas-csv "
        "<evidencia>/hu012/pedidos.csv --csv "
        "data/actividades_notebooklm_n2_sinteticas.csv --padron "
        "data/padron_roles_sintetico.csv --plan-csv "
        "data/plan_pagos_notebooklm_n2.csv",
        "    python scripts/plantilla_actividad_lote_demo.py --directorio "
        "<evidencia>/hu012/lote --csv "
        "data/actividades_notebooklm_n2_sinteticas.csv --actividad "
        "EJEMPLO-NOTEBOOKLM-N2 --plan-csv data/plan_pagos_notebooklm_n2.csv "
        "--padron-csv data/padron_pagos_sintetico.csv --padron-roles "
        "data/padron_roles_sintetico.csv",
    ]
    return salida


def _escribir_evidencia(
    opciones: Opciones,
    contexto: Contexto,
    registro: Registro,
    chequeos: list[Chequeo],
    pasos: list[Paso],
    *,
    inicio: datetime,
    fin: datetime,
    codigo: int,
    mensaje: str,
) -> bool:
    evidencia = opciones.evidencia_dir
    try:
        evidencia.mkdir(parents=True, exist_ok=True)
        resultado = "OK" if codigo == EXIT_OK else (
            "CORTE_PRESUPUESTO" if codigo == EXIT_PRESUPUESTO else "FALLO"
        )
        lineas_host = [
            f"host: {contexto.host}",
            f"plataforma: {contexto.plataforma}",
            f"python: {contexto.python}",
            f"commit: {contexto.commit}",
            f"raiz: {opciones.root}",
            f"inicio: {inicio.isoformat()}",
            f"fin: {fin.isoformat()}",
            f"modo: {'live' if opciones.live else 'dry-run'}",
            f"modelo: {opciones.modelo}",
            f"ollama_esperado: {opciones.ollama_version}",
            f"resultado: {resultado}",
            f"codigo_salida: {codigo}",
            "",
        ]
        (evidencia / "host.txt").write_text(
            registro.sanitizar("\n".join(lineas_host)), encoding="utf-8"
        )
        ollama = next(
            (
                paso.datos.get("ollama_version")
                for paso in pasos
                if paso.id == "ollama" and paso.datos.get("ollama_version")
            ),
            None,
        )
        corrida = {
            "schema": "agente1_corrida_unica_v1",
            "host": contexto.host,
            "plataforma": contexto.plataforma,
            "python": contexto.python,
            "commit": contexto.commit,
            "raiz": str(opciones.root),
            "modo": "live" if opciones.live else "dry-run",
            "modelo": opciones.modelo,
            "ollama_esperado": opciones.ollama_version,
            "ollama_version": ollama,
            "id_solicitud": opciones.id_solicitud,
            "presupuesto_min": opciones.presupuesto_min,
            "inicio": inicio.isoformat(),
            "fin": fin.isoformat(),
            "duracion_s": round((fin - inicio).total_seconds(), 3),
            "resultado": resultado,
            "codigo_salida": codigo,
            "mensaje": mensaje,
            "preflight": [
                {
                    "chequeo": chequeo.nombre,
                    "ok": chequeo.ok,
                    "detalle": chequeo.detalle,
                }
                for chequeo in chequeos
            ],
            "pasos": [
                {
                    "id": paso.id,
                    "nombre": paso.nombre,
                    "modo": paso.modo,
                    "estado": paso.estado,
                    "inicio": paso.inicio,
                    "duracion_s": round(paso.duracion_s, 3),
                    "exit_code": paso.exit_code,
                    "detalle": paso.detalle,
                    "comandos": paso.comandos,
                    "datos": paso.datos,
                }
                for paso in pasos
            ],
        }
        texto_corrida = (
            json.dumps(corrida, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        )
        (evidencia / "corrida.json").write_text(
            registro.sanitizar(texto_corrida), encoding="utf-8"
        )
        (evidencia / "transcripcion.log").write_text(
            registro.texto(), encoding="utf-8"
        )
    except OSError as exc:
        print(
            "No pude escribir la evidencia en "
            f"{evidencia} ({type(exc).__name__}). La corrida sigue en "
            "pantalla, pero no queda respaldo en disco.",
            file=contexto.salida,
        )
        return False
    return True


def ejecutar(opciones: Opciones, contexto: Contexto) -> int:
    inicio_dt = contexto.ahora()
    inicio = contexto.monotonic()
    ruta_clave = contexto.environ.get(SERVICE_ACCOUNT_KEY_ENV, "").strip() or None
    sanitizador = Sanitizador(contexto.environ, ruta_clave)
    registro = Registro(contexto.salida, sanitizador)
    registro.linea("Corrida única del Agente 1 (#132)")
    registro.linea(
        f"Host: {contexto.host} · Commit: {contexto.commit} · "
        f"Python: {contexto.python}"
    )
    registro.linea(
        "Modo: "
        + (
            "LIVE (lee la planilla y crea un borrador en Drive; no publica)"
            if opciones.live
            else "dry-run (valida configuración local; no toca red ni Workspace)"
        )
    )
    registro.linea(f"Evidencia: {opciones.evidencia_dir}")
    registro.linea("")

    chequeos, fallo = _preflight(opciones, contexto)
    registro.linea("[1/6] Preflight (offline)")
    for chequeo in chequeos:
        marca = "OK" if chequeo.ok else "FALLA"
        registro.linea(f"  {marca}  {chequeo.nombre}: {chequeo.detalle}")
    pasos = [
        Paso(id_, nombre, modo, codigo, funcion)
        for id_, nombre, modo, codigo, funcion in _PASOS
    ]
    if fallo is not None:
        mensaje = f"PREFLIGHT: {fallo}"
        registro.linea("")
        registro.linea(mensaje)
        fin_dt = contexto.ahora()
        _escribir_evidencia(
            opciones,
            contexto,
            registro,
            chequeos,
            pasos,
            inicio=inicio_dt,
            fin=fin_dt,
            codigo=EXIT_PREFLIGHT,
            mensaje=mensaje,
        )
        return EXIT_PREFLIGHT

    if not opciones.live:
        registro.linea("")
        registro.linea("Plan de la corrida live (no se ejecuta en dry-run):")
        for linea in _plan(opciones):
            registro.linea(linea)
        for paso in pasos:
            paso.estado = "omitido"
            paso.detalle = "dry-run: no se ejecutó"
        mensaje = (
            "Dry-run OK: la configuración local está completa. No se tocó "
            "red ni Workspace. Volvé a correr con --live."
        )
        registro.linea("")
        registro.linea(mensaje)
        fin_dt = contexto.ahora()
        _escribir_evidencia(
            opciones,
            contexto,
            registro,
            chequeos,
            pasos,
            inicio=inicio_dt,
            fin=fin_dt,
            codigo=EXIT_OK,
            mensaje=mensaje,
        )
        return EXIT_OK

    for indice, paso in enumerate(pasos, start=2):
        transcurrido = (contexto.monotonic() - inicio) / 60.0
        if transcurrido >= opciones.presupuesto_min:
            pendientes = [p.nombre for p in pasos if p.estado == "pendiente"]
            paso.estado = "corte_presupuesto"
            for restante in pasos:
                if restante.estado == "pendiente":
                    restante.estado = "no_ejecutado"
                    restante.detalle = "corte de presupuesto"
            mensaje = (
                f"CORTE_PRESUPUESTO: pasaron {transcurrido:.1f} min de "
                f"{opciones.presupuesto_min:g}. Quedaron sin correr: "
                + ", ".join(pendientes)
                + ". La evidencia parcial quedó en "
                f"{opciones.evidencia_dir}."
            )
            registro.linea("")
            registro.linea(mensaje)
            fin_dt = contexto.ahora()
            _escribir_evidencia(
                opciones,
                contexto,
                registro,
                chequeos,
                pasos,
                inicio=inicio_dt,
                fin=fin_dt,
                codigo=EXIT_PRESUPUESTO,
                mensaje=mensaje,
            )
            return EXIT_PRESUPUESTO

        registro.linea("")
        registro.linea(f"[{indice}/6] {paso.nombre} ({paso.modo})")
        paso.inicio = contexto.ahora().isoformat()
        t0 = contexto.monotonic()
        try:
            resultado = paso.funcion(opciones, contexto, registro)
        except Exception as exc:
            # Un fallo inesperado no debe terminar en un traceback en la
            # mañana de la demo: se informa el tipo y se conserva la
            # transcripción, que ya tiene los comandos ejecutados.
            resultado = ResultadoPaso(
                False,
                "Falla inesperada del paso "
                f"({type(exc).__name__}). No sigas: mirá la transcripción y "
                "la evidencia parcial; si el paso tocó Workspace, no lo "
                "repitas sin reconciliar.",
            )
        paso.duracion_s = contexto.monotonic() - t0
        paso.exit_code = (
            resultado.exit_code if resultado.ok else paso.codigo_fallo
        )
        if resultado.ok and paso.exit_code is None:
            paso.exit_code = 0
        paso.comandos = resultado.comandos
        paso.datos = resultado.datos
        paso.detalle = resultado.detalle
        if not resultado.ok:
            paso.estado = "fallo"
            for restante in pasos:
                if restante.estado == "pendiente":
                    restante.estado = "no_ejecutado"
                    restante.detalle = "no se ejecutó por la falla anterior"
            mensaje = f"{paso.nombre.upper()}: {resultado.detalle}"
            registro.linea("")
            registro.linea(mensaje)
            fin_dt = contexto.ahora()
            _escribir_evidencia(
                opciones,
                contexto,
                registro,
                chequeos,
                pasos,
                inicio=inicio_dt,
                fin=fin_dt,
                codigo=paso.codigo_fallo,
                mensaje=mensaje,
            )
            return paso.codigo_fallo
        paso.estado = "ok"
        registro.linea(f"OK: {resultado.detalle}")

    mensaje = (
        "Corrida completa: gacetilla, HU-014 y HU-012 terminaron. Revisá la "
        "evidencia y no borres tmp/workspace-e2e."
    )
    registro.linea("")
    registro.linea(mensaje)
    fin_dt = contexto.ahora()
    _escribir_evidencia(
        opciones,
        contexto,
        registro,
        chequeos,
        pasos,
        inicio=inicio_dt,
        fin=fin_dt,
        codigo=EXIT_OK,
        mensaje=mensaje,
    )
    return EXIT_OK


def _directorio_evidencia(root: Path) -> Path:
    base = root / "evidencias"
    sello = datetime.now().strftime("%Y-%m-%d-%H%M")
    candidato = base / f"corrida-{sello}"
    sufijo = 2
    while candidato.exists():
        candidato = base / f"corrida-{sello}-{sufijo:02d}"
        sufijo += 1
    return candidato


def _leer_commit(root: Path) -> str:
    try:
        proceso = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return proceso.stdout.strip() if proceso.returncode == 0 else ""


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    ejecutar_comando: Callable[
        [Sequence[str], Path, Mapping[str, str], float], ResultadoComando
    ]
    | None = None,
    consultar: Callable[[str, float], object] | None = None,
    host: str | None = None,
    commit: str | None = None,
    ahora: Callable[[], datetime] | None = None,
    monotonic: Callable[[], float] | None = None,
    salida: TextIO | None = None,
) -> int:
    parser = _ParserSeguro(
        description=(
            "Corrida única del Agente 1 en el servidor: preflight, Ollama, "
            "smoke de Workspace, gacetilla, HU-014 y HU-012. Dry-run por "
            "defecto; --live ejecuta."
        )
    )
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--modelo", default=MODELO_DEFAULT)
    parser.add_argument("--ollama-version", default=OLLAMA_VERSION_DEFAULT)
    parser.add_argument("--id-solicitud", default=ID_SOLICITUD_DEFAULT)
    parser.add_argument("--presupuesto-min", type=float, default=PRESUPUESTO_DEFAULT_MIN)
    parser.add_argument("--timeout-modelo", type=float, default=300.0)
    parser.add_argument("--evidencia-dir", type=Path)
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)

    raiz = ROOT
    evidencia = args.evidencia_dir or _directorio_evidencia(raiz)
    opciones = Opciones(
        live=bool(args.live),
        modelo=args.modelo,
        ollama_version=args.ollama_version,
        id_solicitud=args.id_solicitud,
        presupuesto_min=args.presupuesto_min,
        evidencia_dir=evidencia,
        root=raiz,
        timeout_modelo=args.timeout_modelo,
    )
    entorno = dict(os.environ if environ is None else environ)
    contexto = Contexto(
        environ=entorno,
        host=host if host is not None else socket.gethostname(),
        commit=commit if commit is not None else _leer_commit(raiz),
        python=platform.python_version(),
        plataforma=platform.platform(),
        ahora=ahora or _ahora,
        monotonic=monotonic or time.monotonic,
        ejecutar=ejecutar_comando or _ejecutar_comando,
        consultar=consultar or _consultar_json,
        salida=salida or sys.stdout,
    )
    return ejecutar(opciones, contexto)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
