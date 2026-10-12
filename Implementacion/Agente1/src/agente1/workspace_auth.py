"""Proveedores de credencial para Workspace: del token pegado al minteo OAuth.

`TokenEntornoProvider` resolvió el camino D2 con un access token efímero
pegado en el entorno (~1h de vida, consentimiento manual por corrida). Este
módulo agrega el mecanismo durable de la Alternativa A del paquete del issue
#15: `OAuthRefreshTokenProvider` intercambia un refresh token por un access
token nuevo en cada operación, sin humano en el medio.

Decisiones que no se ven en el código:

- **El host de token es el único host nuevo que se habilita.** El plano de
  datos sigue limitado a Sheets/Docs/Drive; `oauth2.googleapis.com` existe
  sólo para el intercambio de credencial y se declara acá, separado de la
  lista que la auditoría contrasta contra los adapters.
- **Los tres secretos entran juntos o no entran.** Un trío incompleto
  (`workspace_auth_config_incomplete`) es peor que ninguno: deja una
  credencial a medio configurar que nadie audita.
- **Los secretos no pasan por la configuración.** Igual que el token de
  `TokenEntornoProvider`, client id/secret/refresh token los lee el provider
  directo del entorno: `ConfiguracionWorkspace` y `resumen_seguro()` no los
  ven ni los hashean.
- **El intercambio es una operación con deadline y tope**, igual que las
  llamadas del plano de datos. Un endpoint de token que cuelga no puede
  estirar la ejecución.
- **Nunca se reintenta el intercambio.** Si el refresh token fue revocado
  (`400 invalid_grant`, `401`, `403`), el agente se detiene con
  `workspace_token_exchange_denied`: esa es la señal de la prueba de
  revocación.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from collections.abc import Mapping
from urllib.parse import urlencode

from .google_workspace import (
    MAX_WORKSPACE_RESPONSE_BYTES,
    MAX_WORKSPACE_TIMEOUT_S,
    HttpsWorkspaceTransport,
    RespuestaHttp,
    TransporteHttp,
    _RespuestaDemasiadoGrande,
)
from .workspace_config import ConfiguracionWorkspaceError, TokenEntornoProvider

# Host exclusivo del intercambio OAuth. No forma parte del plano de datos:
# ningún adapter lo toca, sólo este provider.
OAUTH_TOKEN_HOST = "oauth2.googleapis.com"
OAUTH_TOKEN_TARGET = "/token"

CLIENT_ID_ENV = "AGENTE1_WORKSPACE_OAUTH_CLIENT_ID"
CLIENT_SECRET_ENV = "AGENTE1_WORKSPACE_OAUTH_CLIENT_SECRET"
REFRESH_TOKEN_ENV = "AGENTE1_WORKSPACE_OAUTH_REFRESH_TOKEN"
_OAUTH_ENVS = frozenset({CLIENT_ID_ENV, CLIENT_SECRET_ENV, REFRESH_TOKEN_ENV})

# Credenciales OAuth: ASCII imprimible sin espacios ni controles. Un client id
# o refresh token legítimo nunca lleva whitespace; admitirlo sólo serviría
# para meter valores malformados en un request firmado.
_SECRETO_RE = re.compile(r"[!-~]{1,8192}\Z")


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


def construir_token_provider(
    environ: Mapping[str, str] | None = None,
    *,
    timeout_s: float = 10.0,
) -> object:
    """Elige la credencial disponible: refresh token si está completo, si no
    el token efímero del entorno.

    Un trío OAuth a medio configurar no cae en silencio al token efímero —
    falla explícito: si alguien cargó dos de las tres variables, lo que
    quiere es OAuth y hay que arreglar la carga, no esconderla.
    """

    env = os.environ if environ is None else environ
    if _OAUTH_ENVS & env.keys():
        return OAuthRefreshTokenProvider.desde_entorno(env, timeout_s=timeout_s)
    return TokenEntornoProvider()


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
