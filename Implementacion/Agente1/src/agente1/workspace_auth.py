"""Proveedores de credencial para Workspace: de la cuenta de servicio al token pegado.

`TokenEntornoProvider` resolvió el camino D2 con un access token efímero
pegado en el entorno (~1h de vida, consentimiento manual por corrida). Este
módulo agrega dos mecanismos durables:

- `CuentaServicioDelegadaProvider` es el **mecanismo vigente** (ADR 0011): una
  cuenta de servicio de DSI con *domain-wide delegation* firma un assertion
  JWT RS256 con `sub` = la cuenta por la que el agente se hace pasar y lo
  intercambia por un access token. Sólo puede hacerse pasar por las cuentas de
  la **lista cerrada** de `contracts/cuentas_suplantables_v1.json`.
- `OAuthRefreshTokenProvider` es la Alternativa A del paquete del issue #15:
  intercambia un refresh token por un access token nuevo en cada operación,
  sin humano en el medio. Queda como **respaldo explícito** —no silencioso—
  hasta que se cierre el issue #99 (dar de baja la OAuth al instalar la cuenta
  de servicio en el host).

Decisiones que no se ven en el código:

- **El host de token es el único host nuevo que se habilita.** El plano de
  datos sigue limitado a Sheets/Docs/Drive; `oauth2.googleapis.com` existe
  sólo para el intercambio de credencial y se declara acá, separado de la
  lista que la auditoría contrasta contra los adapters.
- **La clave de la cuenta de servicio nunca pasa por la configuración, los
  logs ni las excepciones.** El provider lee su ruta del entorno y la lee él
  mismo, igual que los secretos OAuth y el token de `TokenEntornoProvider`:
  `ConfiguracionWorkspace` y `resumen_seguro()` no la ven ni la hashean. Un
  error de lectura o de parseo es un código estable (`workspace_key_*`), sin
  el contenido adentro —el repo es público y el traceback termina en logs.
- **El agente sólo se hace pasar por una cuenta de la lista cerrada.** El
  archivo la tiene como sha256 de la dirección normalizada (sin la dirección
  en claro) y entra en el manifest de la versión (ADR 0010). El entorno indica
  por quién hacerse pasar; si esa cuenta no está en la lista, el provider no
  se construye y el modo operación no arranca
  (`workspace_impersonation_not_allowed`).
- **Se firma con `openssl`, sin dependencias de runtime.** El proyecto tiene
  hoy cero dependencias de runtime y eso es una fortaleza de seguridad ya
  relevada (superficie de *supply chain* nula). El assertion JWT se firma con
  el binario `openssl` del host, con la clave privada pasada por un `pipe`
  —nunca por `argv`, el entorno ni un archivo temporal—; si el binario falta o
  la firma falla, el agente se detiene con `workspace_auth_signing_unavailable`
  (fail-closed). *Alternativa abierta para Juani:* sumar una dependencia de
  criptografía (p. ej. `cryptography`) y fijarla en `uv.lock`; cambiaría la
  superficie de supply chain y por eso no se implementa acá.
- **El JWT se firma cada vez que se pide un token.** No se cachea el access
  token: cada operación mintea el suyo, con deadline y tope de respuesta, y
  sin reintentos. Si Google deniega (`400 invalid_grant`, `401`, `403`), el
  agente se detiene con `workspace_token_exchange_denied`: es la señal de la
  prueba de clave inválida (reemplaza la prueba de revocación conjunta que DSI
  no hace).
- **Cada token deja asentado por quién se pidió.** Si el provider se construye
  con un directorio de salida, cada emisión agrega una línea a
  `logs/cuenta-suplantada.jsonl` con el sha256 de la cuenta suplantada y la
  versión del agente. Se escribe antes de devolver el token: si la auditoría no
  se puede escribir, la emisión falla cerrada (`workspace_cuenta_audit_unavailable`).
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlencode

from .google_workspace import (
    MAX_WORKSPACE_RESPONSE_BYTES,
    MAX_WORKSPACE_TIMEOUT_S,
    HttpsWorkspaceTransport,
    RespuestaHttp,
    TransporteHttp,
    _RespuestaDemasiadoGrande,
)
from .manifest_version import raiz_agente, version_desde_pyproject
from .workspace_config import ConfiguracionWorkspaceError, TokenEntornoProvider

# Host exclusivo del intercambio OAuth. No forma parte del plano de datos:
# ningún adapter lo toca, sólo este módulo.
OAUTH_TOKEN_HOST = "oauth2.googleapis.com"
OAUTH_TOKEN_TARGET = "/token"
# `aud` del assertion: el mismo endpoint contra el que se intercambia.
OAUTH_TOKEN_AUDIENCE = f"https://{OAUTH_TOKEN_HOST}{OAUTH_TOKEN_TARGET}"

CLIENT_ID_ENV = "AGENTE1_WORKSPACE_OAUTH_CLIENT_ID"
CLIENT_SECRET_ENV = "AGENTE1_WORKSPACE_OAUTH_CLIENT_SECRET"
REFRESH_TOKEN_ENV = "AGENTE1_WORKSPACE_OAUTH_REFRESH_TOKEN"
_OAUTH_ENVS = frozenset({CLIENT_ID_ENV, CLIENT_SECRET_ENV, REFRESH_TOKEN_ENV})

# Cuenta de servicio (ADR 0011). La ruta de la clave y la cuenta por la que el
# agente se hace pasar vienen del entorno; la clave nunca entra a la
# configuración. El par es todo o nada: una identidad a medias deja una
# credencial que nadie audita.
SERVICE_ACCOUNT_KEY_ENV = "AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY"
IMPERSONATED_ACCOUNT_ENV = "AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT"
_SERVICE_ACCOUNT_ENVS = frozenset({SERVICE_ACCOUNT_KEY_ENV, IMPERSONATED_ACCOUNT_ENV})

# Scopes autorizados en la delegación (ADR 0011, §3 del modelo de seguridad).
# Se piden juntos: son los que DSI dejó habilitados para el client ID.
SCOPES_CUENTA_SERVICIO = (
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
)
SCOPE_STRING_CUENTA_SERVICIO = " ".join(SCOPES_CUENTA_SERVICIO)

# Lista cerrada de cuentas suplantables (ADR 0011). Archivo controlado del repo
# con el sha256 de cada dirección normalizada, sin la dirección en claro.
CUENTAS_SUPLANTABLES_CONTRATO = "cuentas_suplantables_v1.json"
CUENTAS_SUPLANTABLES_SCHEMA = "agente1_cuentas_suplantables_v1"

# Auditoría de cada token: por quién se pidió y con qué versión del agente.
CUENTA_AUDITORIA_RECORD = "agente1_cuenta_suplantada_v1"
CUENTA_AUDITORIA_NOMBRE = "cuenta-suplantada.jsonl"

# Vigencia del assertion JWT en segundos. Google acepta hasta 3600.
JWT_VIGENCIA_S = 3600

# Credenciales OAuth/assertion: ASCII imprimible sin espacios ni controles. Un
# client id, refresh token o assertion legítimo nunca lleva whitespace;
# admitirlo sólo serviría para meter valores malformados en un request firmado.
_SECRETO_RE = re.compile(r"[!-~]{1,8192}\Z")
# Dirección de cuenta: forma mínima de correo, sin espacios ni controles. Es la
# que se normaliza y se busca en la lista cerrada, y la que viaja como `sub`.
_CUENTA_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class CuentaServicioDelegadaProvider:
    """Mintea un access token con una cuenta de servicio y delegación.

    El assertion JWT se firma con la clave privada de la cuenta de servicio y
    lleva `sub` = la cuenta por la que el agente se hace pasar. Esa cuenta se
    valida contra la lista cerrada al construir el provider y no puede cambiar
    después: no hay forma de pedir un token por una cuenta que no esté en la
    lista. La clave se lee en cada emisión --no se guarda-- y nunca sale hacia
    la configuración ni hacia un mensaje de error.
    """

    __slots__ = (
        "_key_path",
        "_cuenta",
        "_cuenta_hash",
        "_transport",
        "_timeout_s",
        "_auditoria",
    )

    def __init__(
        self,
        *,
        key_path: str,
        cuenta: str,
        cuentas_suplantables: frozenset[str],
        transport: TransporteHttp | None = None,
        timeout_s: float = 10.0,
        directorio_auditoria: Path | None = None,
    ) -> None:
        if (
            not isinstance(key_path, str)
            or not key_path
            or key_path != key_path.strip()
            or any(ord(caracter) < 32 or ord(caracter) == 127 for caracter in key_path)
            or not isinstance(cuenta, str)
            or _CUENTA_RE.fullmatch(cuenta.strip()) is None
            or isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s)
            or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
            or not isinstance(cuentas_suplantables, (frozenset, set, tuple, list))
        ):
            raise ConfiguracionWorkspaceError("workspace_auth_config_invalid")
        cuenta_normalizada = normalizar_cuenta(cuenta)
        cuenta_hash = sha256_cuenta(cuenta_normalizada)
        if cuenta_hash not in cuentas_suplantables:
            raise ConfiguracionWorkspaceError("workspace_impersonation_not_allowed")
        self._key_path = key_path
        self._cuenta = cuenta_normalizada
        self._cuenta_hash = cuenta_hash
        self._transport = transport or HttpsWorkspaceTransport()
        self._timeout_s = float(timeout_s)
        self._auditoria = (
            AuditoriaCuentaSuplantada(directorio_auditoria)
            if directorio_auditoria is not None
            else None
        )

    @property
    def cuenta_suplantada_sha256(self) -> str:
        """El sha256 de la cuenta por la que este provider se hace pasar."""

        return self._cuenta_hash

    @classmethod
    def desde_entorno(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        cuentas_suplantables: frozenset[str] | None = None,
        timeout_s: float = 10.0,
        directorio_auditoria: Path | None = None,
    ) -> "CuentaServicioDelegadaProvider":
        """Construye el provider desde el entorno. Ruta y cuenta son todo o nada."""

        env = os.environ if environ is None else environ
        presentes = _SERVICE_ACCOUNT_ENVS & env.keys()
        if not presentes:
            raise ConfiguracionWorkspaceError("workspace_auth_config_missing")
        if presentes != _SERVICE_ACCOUNT_ENVS:
            raise ConfiguracionWorkspaceError("workspace_auth_config_incomplete")
        if cuentas_suplantables is None:
            cuentas_suplantables = cargar_cuentas_suplantables()
        return cls(
            key_path=env[SERVICE_ACCOUNT_KEY_ENV],
            cuenta=env[IMPERSONATED_ACCOUNT_ENV],
            cuentas_suplantables=cuentas_suplantables,
            timeout_s=timeout_s,
            directorio_auditoria=directorio_auditoria,
        )

    def obtener_access_token(self) -> str:
        client_email, private_key = self._leer_clave()
        assertion = _firmar_assertion(
            client_email=client_email,
            cuenta=self._cuenta,
            private_key_pem=private_key,
        )
        # El assertion viaja en el cuerpo del POST, codificado como formulario,
        # que es el contrato del intercambio con cuenta de servicio.
        cuerpo = urlencode(
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            }
        ).encode("utf-8")
        try:
            respuesta = self._transport.request(
                method="POST",
                host=OAUTH_TOKEN_HOST,
                target=OAUTH_TOKEN_TARGET,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body=cuerpo,
                deadline=time.monotonic() + self._timeout_s,
                max_response_bytes=MAX_WORKSPACE_RESPONSE_BYTES,
            )
        except _RespuestaDemasiadoGrande:
            raise ConfiguracionWorkspaceError(
                "workspace_token_exchange_response_too_large"
            ) from None
        except Exception:
            raise ConfiguracionWorkspaceError(
                "workspace_token_exchange_unavailable"
            ) from None
        token = _validar_respuesta_token(respuesta)
        if self._auditoria is not None:
            try:
                self._auditoria.anexar(
                    cuenta_suplantada_sha256=self._cuenta_hash,
                    version=_version_agente(),
                    resultado="emitido",
                )
            except OSError:
                raise ConfiguracionWorkspaceError(
                    "workspace_cuenta_audit_unavailable"
                ) from None
        return token

    def _leer_clave(self) -> tuple[str, str]:
        """Lee la clave de la cuenta de servicio. Falla con código, sin contenido.

        Ausente o ilegible es `workspace_key_unreadable`; JSON malformado o sin
        `client_email`/`private_key` es `workspace_key_invalid`. Nunca se
        incluye el contenido de la clave ni la ruta en el error.
        """

        try:
            crudo = Path(self._key_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raise ConfiguracionWorkspaceError("workspace_key_unreadable") from None
        try:
            documento = json.loads(crudo)
        except json.JSONDecodeError:
            raise ConfiguracionWorkspaceError("workspace_key_invalid") from None
        if not isinstance(documento, dict):
            raise ConfiguracionWorkspaceError("workspace_key_invalid")
        client_email = documento.get("client_email")
        private_key = documento.get("private_key")
        if (
            not isinstance(client_email, str)
            or _CUENTA_RE.fullmatch(client_email.strip()) is None
            or not isinstance(private_key, str)
            or "PRIVATE KEY" not in private_key
        ):
            raise ConfiguracionWorkspaceError("workspace_key_invalid")
        return client_email.strip(), private_key

    def __repr__(self) -> str:
        return "CuentaServicioDelegadaProvider(<redacted>)"


class OAuthRefreshTokenProvider:
    """Mintea un access token por operación a partir de un refresh token.

    El refresh token es la credencial durable: la obtiene una persona una
    sola vez con la cuenta técnica dedicada, vive en el gestor de secretos
    del ambiente y de acá sólo sale hacia el endpoint de Google dentro del
    cuerpo del POST —nunca a logs ni a excepciones.
    """

    __slots__ = ("_client_id", "_client_secret", "_refresh_token", "_transport", "_timeout_s")

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        transport: TransporteHttp | None = None,
        timeout_s: float = 10.0,
    ) -> None:
        if (
            not isinstance(client_id, str)
            or _SECRETO_RE.fullmatch(client_id) is None
            or not isinstance(client_secret, str)
            or _SECRETO_RE.fullmatch(client_secret) is None
            or not isinstance(refresh_token, str)
            or _SECRETO_RE.fullmatch(refresh_token) is None
            or isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s)
            or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
        ):
            raise ConfiguracionWorkspaceError("workspace_auth_config_invalid")
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._transport = transport or HttpsWorkspaceTransport()
        self._timeout_s = float(timeout_s)

    @classmethod
    def desde_entorno(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        timeout_s: float = 10.0,
    ) -> "OAuthRefreshTokenProvider":
        """Construye el provider desde el entorno. El trío es todo o nada."""
        env = os.environ if environ is None else environ
        presentes = _OAUTH_ENVS & env.keys()
        if not presentes:
            raise ConfiguracionWorkspaceError("workspace_auth_config_missing")
        if presentes != _OAUTH_ENVS:
            raise ConfiguracionWorkspaceError("workspace_auth_config_incomplete")
        return cls(
            client_id=env[CLIENT_ID_ENV],
            client_secret=env[CLIENT_SECRET_ENV],
            refresh_token=env[REFRESH_TOKEN_ENV],
            timeout_s=timeout_s,
        )

    def obtener_access_token(self) -> str:
        # El cuerpo lleva los secretos codificados como formulario, que es el
        # contrato del endpoint de Google. `urlencode` se encarga de que
        # caracteres especiales del refresh token no rompan el cuerpo.
        cuerpo = urlencode(
            {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        try:
            respuesta = self._transport.request(
                method="POST",
                host=OAUTH_TOKEN_HOST,
                target=OAUTH_TOKEN_TARGET,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body=cuerpo,
                deadline=time.monotonic() + self._timeout_s,
                max_response_bytes=MAX_WORKSPACE_RESPONSE_BYTES,
            )
        except _RespuestaDemasiadoGrande:
            raise ConfiguracionWorkspaceError(
                "workspace_token_exchange_response_too_large"
            ) from None
        except Exception:
            raise ConfiguracionWorkspaceError(
                "workspace_token_exchange_unavailable"
            ) from None
        return _validar_respuesta_token(respuesta)

    def __repr__(self) -> str:
        return "OAuthRefreshTokenProvider(<redacted>)"


class AuditoriaCuentaSuplantada:
    """El registro de por quién se pidió cada token, una línea JSONL por emisión.

    Vive en `logs/cuenta-suplantada.jsonl` bajo el directorio de salida, junto
    al log del scheduler y al de integridad, así que viaja dentro del respaldo
    del día siguiente. Lleva el sha256 de la cuenta suplantada y la versión del
    agente: nunca la dirección en claro ni la credencial.
    """

    def __init__(self, directorio: Path) -> None:
        self._path = Path(directorio) / "logs" / CUENTA_AUDITORIA_NOMBRE

    @property
    def path(self) -> Path:
        return self._path

    def anexar(
        self,
        *,
        cuenta_suplantada_sha256: str,
        version: str | None,
        resultado: str,
    ) -> dict[str, object]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        entrada = {
            "record": CUENTA_AUDITORIA_RECORD,
            "cuenta_suplantada_sha256": cuenta_suplantada_sha256,
            "version": version,
            "resultado": resultado,
            "ejecutado_en": datetime.now(timezone.utc).isoformat(),
        }
        with self._path.open("a", encoding="utf-8", newline="") as archivo:
            archivo.write(json.dumps(entrada, ensure_ascii=False, sort_keys=True))
            archivo.write("\n")
        return entrada


def construir_token_provider(
    environ: Mapping[str, str] | None = None,
    *,
    timeout_s: float = 10.0,
    directorio_auditoria: Path | None = None,
) -> object:
    """Elige la credencial disponible, en orden de preferencia.

    1. **Cuenta de servicio** (ADR 0011): el mecanismo vigente. Si el entorno
       trae su par de variables, se usa; un par a medias falla explícito en vez
       de caer al respaldo.
    2. **Refresh token OAuth**: respaldo explícito hasta el issue #99. Si el
       trío está completo, se usa; a medias falla explícito.
    3. **Token efímero del entorno**: el camino de desarrollo, sólo cuando no
       hay ninguna de las dos credenciales durables configurada.
    """

    env = os.environ if environ is None else environ
    if _SERVICE_ACCOUNT_ENVS & env.keys():
        return CuentaServicioDelegadaProvider.desde_entorno(
            env, timeout_s=timeout_s, directorio_auditoria=directorio_auditoria
        )
    if _OAUTH_ENVS & env.keys():
        return OAuthRefreshTokenProvider.desde_entorno(env, timeout_s=timeout_s)
    return TokenEntornoProvider()


def cargar_cuentas_suplantables() -> frozenset[str]:
    """La lista cerrada de cuentas suplantables, validada y como conjunto.

    Es un archivo controlado del repo (entra en el manifest de la versión,
    ADR 0010) con el sha256 de cada dirección normalizada, sin direcciones en
    claro. Una forma abierta o vacía falla cerrado: la lista es la única
    compensación del riesgo aceptado por la delegación de todo el dominio.
    """

    try:
        documento = json.loads(
            files("agente1")
            .joinpath("contracts", CUENTAS_SUPLANTABLES_CONTRATO)
            .read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise ConfiguracionWorkspaceError(
            "workspace_cuentas_suplantables_invalid"
        ) from None
    return _validar_cuentas_suplantables(documento)


def _validar_cuentas_suplantables(documento: object) -> frozenset[str]:
    if (
        not isinstance(documento, dict)
        or documento.get("schema_version") != CUENTAS_SUPLANTABLES_SCHEMA
    ):
        raise ConfiguracionWorkspaceError("workspace_cuentas_suplantables_invalid")
    cuentas = documento.get("cuentas_sha256")
    if not isinstance(cuentas, list) or not cuentas:
        raise ConfiguracionWorkspaceError("workspace_cuentas_suplantables_invalid")
    for entrada in cuentas:
        if not isinstance(entrada, str) or _SHA256_RE.fullmatch(entrada) is None:
            raise ConfiguracionWorkspaceError("workspace_cuentas_suplantables_invalid")
    return frozenset(cuentas)


def normalizar_cuenta(cuenta: str) -> str:
    """La forma canónica de una dirección: sin espacios y en minúscula.

    Google trata las direcciones de Workspace como insensibles a mayúsculas,
    así que la lista y la búsqueda comparten esta normalización; si no, una
    `Bot_IA1@FIE...` legítima quedaría afuera de la lista por la caja.
    """

    return cuenta.strip().lower()


def sha256_cuenta(cuenta: str) -> str:
    """El sha256 de la dirección normalizada: lo que guarda la lista cerrada.

    Es la única forma de la cuenta que sale del provider hacia la lista o la
    auditoría; la dirección en claro no se persiste en ningún lado.
    """

    return hashlib.sha256(normalizar_cuenta(cuenta).encode("utf-8")).hexdigest()


def _firmar_assertion(*, client_email: str, cuenta: str, private_key_pem: str) -> str:
    ahora = int(time.time())
    encabezado = {"alg": "RS256", "typ": "JWT"}
    reclamos = {
        "iss": client_email,
        "sub": cuenta,
        "scope": SCOPE_STRING_CUENTA_SERVICIO,
        "aud": OAUTH_TOKEN_AUDIENCE,
        "iat": ahora,
        "exp": ahora + JWT_VIGENCIA_S,
    }
    mensaje = f"{_b64url_json(encabezado)}.{_b64url_json(reclamos)}".encode("ascii")
    firma = _firmar_rs256(mensaje, private_key_pem)
    return f"{mensaje.decode('ascii')}.{_b64url(firma)}"


def _b64url_json(documento: object) -> str:
    serializado = json.dumps(
        documento, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return _b64url(serializado.encode("utf-8"))


def _b64url(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode("ascii")


def _firmar_rs256(mensaje: bytes, private_key_pem: str) -> bytes:
    """Firma RS256 con `openssl`, sin dependencias de runtime.

    La clave privada se pasa al proceso por un `pipe` (`/dev/fd/N`), no por
    `argv` --que es visible en `ps`--, ni por el entorno --visible en
    `/proc/<pid>/environ`--, ni por un archivo en disco. Si `openssl` falta o
    la firma no sale, se detiene con `workspace_auth_signing_unavailable`: la
    alternativa (sumar una dependencia de criptografía) es una decisión
    abierta, no un camino oculto.
    """

    openssl = _resolver_openssl()
    if openssl is None:
        raise ConfiguracionWorkspaceError("workspace_auth_signing_unavailable")
    lectura, escritura = os.pipe()
    try:
        _escribir_todo(escritura, private_key_pem.encode("utf-8"))
    finally:
        os.close(escritura)
    try:
        resultado = subprocess.run(
            [openssl, "dgst", "-sha256", "-sign", f"/dev/fd/{lectura}", "-binary"],
            input=mensaje,
            capture_output=True,
            pass_fds=(lectura,),
            check=False,
        )
    except OSError:
        raise ConfiguracionWorkspaceError("workspace_auth_signing_unavailable") from None
    finally:
        os.close(lectura)
    if resultado.returncode != 0 or not resultado.stdout:
        raise ConfiguracionWorkspaceError("workspace_auth_signing_unavailable")
    return resultado.stdout


def _escribir_todo(fd: int, datos: bytes) -> None:
    visto = 0
    while visto < len(datos):
        visto += os.write(fd, datos[visto:])


def _resolver_openssl() -> str | None:
    """La ruta del binario `openssl`, o `None` si el host no lo tiene."""

    return shutil.which("openssl")


def _version_agente() -> str | None:
    """La versión del agente para la auditoría; `None` si no se puede leer."""

    try:
        return version_desde_pyproject(raiz_agente())
    except Exception:
        return None


def _validar_respuesta_token(respuesta: RespuestaHttp) -> str:
    if len(respuesta.body) > MAX_WORKSPACE_RESPONSE_BYTES:
        raise ConfiguracionWorkspaceError(
            "workspace_token_exchange_response_too_large"
        )
    if not 200 <= respuesta.status < 300:
        if respuesta.status in {400, 401, 403}:
            codigo = "workspace_token_exchange_denied"
        elif respuesta.status == 429:
            codigo = "workspace_token_exchange_rate_limited"
        else:
            codigo = "workspace_token_exchange_unavailable"
        raise ConfiguracionWorkspaceError(codigo)
    try:
        documento = json.loads(respuesta.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ConfiguracionWorkspaceError(
            "workspace_token_exchange_response_invalid"
        ) from None
    access_token = documento.get("access_token") if isinstance(documento, dict) else None
    # El token sale tal cual al header Authorization de los adapters: se le
    # exige la misma higiene que a cualquier provider (sin whitespace ni
    # controles) para que un endpoint comprometido no pueda inyectar nada.
    if (
        not isinstance(access_token, str)
        or _SECRETO_RE.fullmatch(access_token) is None
    ):
        raise ConfiguracionWorkspaceError(
            "workspace_token_exchange_response_invalid"
        )
    return access_token
