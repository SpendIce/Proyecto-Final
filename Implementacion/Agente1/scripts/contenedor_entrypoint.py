"""Entrypoint de los contenedores del Agente 1 (#143, ADR 0013).

Hace cuatro cosas, en este orden, antes de lanzar el comando pedido:

1. **Carga el env file en tiempo de ejecución.** Lee `AGENTE1_ENV_FILE` (montado
   en sólo lectura desde el host) y lo agrega al entorno del proceso hijo. Así
   la configuración y la ruta de la clave nunca quedan en la imagen, en los
   build args ni en `docker inspect`.
2. **Verifica la integridad de la versión** contra `manifest-version.json`
   (ADR 0010). El contenedor es el modo operación: si un archivo controlado no
   coincide, no arranca y deja el motivo en `logs/integridad-arranque.jsonl`
   bajo `AGENTE1_ESTADO`.
3. **Levanta el relay de loopback hacia Ollama.** El adaptador sólo acepta un
   Ollama en loopback (`ollama.py`). Ollama corre en su propio contenedor, en
   una red interna sin salida a internet, así que este proceso escucha en
   `127.0.0.1:11434` y reenvía a `AGENTE1_OLLAMA_UPSTREAM` (`ollama:11434`).
   El control del adaptador no se toca.
4. **Lanza el comando** como proceso hijo y le reenvía `SIGTERM`/`SIGINT`.

Comandos:

- `consola`: la consola visual de la demo, escuchando en `0.0.0.0:8080` dentro
  del contenedor (el compose la publica sólo en `127.0.0.1` del host).
- `scheduler ...`: `python -m agente1 scheduler ...` con los flags que siguen.
- `verificar`: sólo la verificación de integridad; sale 0 si coincide.
- `smoke ...` / `e2e ...`: `scripts/workspace_smoke.py` / `scripts/workspace_e2e.py`.
- Cualquier otra cosa se ejecuta tal cual (por ejemplo `python -m agente1 ...`).

Variables:

- `AGENTE1_ENV_FILE`: env file del host. Si está definida, tiene que existir.
- `AGENTE1_OLLAMA_UPSTREAM`: `host:puerto` de Ollama; vacía desactiva el relay.
- `AGENTE1_ESTADO`: directorio de estado y auditoría (por defecto `/state`).

Usa sólo la biblioteca estándar: la imagen de runtime no tiene dependencias.
"""

from __future__ import annotations

import asyncio
import os
import signal
import socket
import subprocess
import sys
import threading
from collections.abc import Mapping, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.manifest_version import (  # noqa: E402
    IntegridadError,
    verificar_integridad_al_arrancar,
)

RELAY_HOST = "127.0.0.1"
RELAY_PUERTO = 11434
UPSTREAM_POR_DEFECTO = "ollama:11434"
ESTADO_POR_DEFECTO = "/state"

SALIDA_CONFIG_INVALIDA = 64
SALIDA_INTEGRIDAD = 2


class ConfigError(Exception):
    """Configuración del contenedor inválida: el entrypoint no arranca."""


def leer_env_file(ruta: Path) -> dict[str, str]:
    """Lee un env file `CLAVE=valor` como los de `~/.config/agente1/`.

    Ignora líneas vacías y comentarios, acepta `export` adelante y saca un par
    de comillas simples o dobles que envuelvan el valor. No expande variables.
    """

    valores: dict[str, str] = {}
    for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if linea.startswith("export "):
            linea = linea[len("export ") :].lstrip()
        clave, separador, valor = linea.partition("=")
        clave = clave.strip()
        if not separador or not clave.isidentifier():
            raise ConfigError(f"env file inválido en la línea {numero}")
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "'\"":
            valor = valor[1:-1]
        valores[clave] = valor
    return valores


def entorno_hijo(environ: Mapping[str, str]) -> dict[str, str]:
    """El entorno del comando: el del contenedor más el env file, si hay."""

    entorno = dict(environ)
    ruta = environ.get("AGENTE1_ENV_FILE", "").strip()
    if ruta:
        archivo = Path(ruta)
        if not archivo.is_file():
            raise ConfigError("AGENTE1_ENV_FILE no existe o no es un archivo")
        entorno.update(leer_env_file(archivo))
    return entorno


def parsear_upstream(valor: str) -> tuple[str, int] | None:
    """`host:puerto` → tupla; vacío → `None` (relay desactivado)."""

    valor = valor.strip()
    if not valor:
        return None
    host, separador, puerto = valor.rpartition(":")
    if not separador or not host or not puerto.isdigit():
        raise ConfigError("AGENTE1_OLLAMA_UPSTREAM debe ser host:puerto")
    numero = int(puerto)
    if not 0 < numero < 65536:
        raise ConfigError("AGENTE1_OLLAMA_UPSTREAM con puerto fuera de rango")
    return host, numero


async def _copiar(origen: asyncio.StreamReader, destino: asyncio.StreamWriter) -> None:
    try:
        while True:
            datos = await origen.read(65536)
            if not datos:
                break
            destino.write(datos)
            await destino.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        try:
            destino.close()
        except Exception:
            pass


async def _atender(
    upstream: tuple[str, int],
    cliente_r: asyncio.StreamReader,
    cliente_w: asyncio.StreamWriter,
) -> None:
    try:
        remoto_r, remoto_w = await asyncio.open_connection(*upstream)
    except OSError:
        cliente_w.close()
        return
    await asyncio.gather(_copiar(cliente_r, remoto_w), _copiar(remoto_r, cliente_w))


class Relay:
    """Reenvío TCP de `127.0.0.1:<puerto>` a Ollama, en un hilo propio."""

    def __init__(self, upstream: tuple[str, int], *, puerto: int = RELAY_PUERTO) -> None:
        self.upstream = upstream
        self.puerto = puerto
        self._loop = asyncio.new_event_loop()
        self._listo = threading.Event()
        self._error: BaseException | None = None
        self._servidor: asyncio.AbstractServer | None = None
        self._hilo = threading.Thread(target=self._correr, name="relay-ollama", daemon=True)

    def _correr(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._servidor = self._loop.run_until_complete(
                asyncio.start_server(
                    lambda r, w: _atender(self.upstream, r, w),
                    host=RELAY_HOST,
                    port=self.puerto,
                    family=socket.AF_INET,
                )
            )
            self.puerto = self._servidor.sockets[0].getsockname()[1]
        except BaseException as exc:  # el hilo principal decide qué hacer
            self._error = exc
            self._listo.set()
            return
        self._listo.set()
        self._loop.run_forever()

    def iniciar(self) -> int:
        self._hilo.start()
        self._listo.wait(timeout=10)
        if self._error is not None:
            raise ConfigError(f"no se pudo abrir el relay: {self._error}")
        return self.puerto

    def detener(self) -> None:
        if self._servidor is not None:
            self._loop.call_soon_threadsafe(self._servidor.close)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._hilo.join(timeout=5)


def comando_para(argv: Sequence[str]) -> list[str] | None:
    """Traduce el comando del contenedor; `None` para `verificar`."""

    if not argv:
        argv = ["consola"]
    nombre, resto = argv[0], list(argv[1:])
    python = sys.executable
    if nombre == "verificar":
        return None
    if nombre == "consola":
        return [python, str(ROOT / "scripts" / "demo_visual_plan_b.py"), "--host", "0.0.0.0", "--port", "8080", *resto]
    if nombre == "scheduler":
        return [python, "-m", "agente1", "scheduler", *resto]
    if nombre == "smoke":
        return [python, str(ROOT / "scripts" / "workspace_smoke.py"), *resto]
    if nombre == "e2e":
        return [python, str(ROOT / "scripts" / "workspace_e2e.py"), *resto]
    return [nombre, *resto]


def verificar(estado: Path) -> None:
    verificar_integridad_al_arrancar(directorio_salida=estado, raiz=ROOT)


def main(argv: Sequence[str] | None = None, environ: Mapping[str, str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    environ = os.environ if environ is None else environ
    estado = Path(environ.get("AGENTE1_ESTADO", ESTADO_POR_DEFECTO) or ESTADO_POR_DEFECTO)

    try:
        entorno = entorno_hijo(environ)
        upstream = parsear_upstream(environ.get("AGENTE1_OLLAMA_UPSTREAM", UPSTREAM_POR_DEFECTO))
    except ConfigError as exc:
        print(f"entrypoint: {exc}", file=sys.stderr)
        return SALIDA_CONFIG_INVALIDA

    try:
        verificar(estado)
    except IntegridadError as exc:
        print(f"entrypoint: integridad de la versión: {exc.code}", file=sys.stderr)
        return SALIDA_INTEGRIDAD

    comando = comando_para(argv)
    if comando is None:
        print("entrypoint: integridad de la versión verificada", file=sys.stderr)
        return 0

    relay = None
    if upstream is not None:
        relay = Relay(upstream)
        try:
            relay.iniciar()
        except ConfigError as exc:
            print(f"entrypoint: {exc}", file=sys.stderr)
            return SALIDA_CONFIG_INVALIDA

    hijo = subprocess.Popen(comando, env=entorno, cwd=ROOT)

    def reenviar(numero: int, _frame: object) -> None:
        if hijo.poll() is None:
            hijo.send_signal(numero)

    signal.signal(signal.SIGTERM, reenviar)
    signal.signal(signal.SIGINT, reenviar)
    try:
        return hijo.wait()
    finally:
        if relay is not None:
            relay.detener()


if __name__ == "__main__":
    raise SystemExit(main())
