"""Verificación del ID token de Google en el servidor (ADR 0014 §3).

El navegador sólo traslada el `credential` que emite Google Identity
Services; toda la verificación ocurre acá, con `google-auth`: firma contra
los JWKS, `iss`, `aud` (el client ID), `exp` y `hd` (el dominio institucional
cuando está configurado). El correo verificado es la entrada del padrón de
roles; nunca se acepta un rol ni un correo enviado por el cliente.

El verificador es inyectable: producción apunta a los JWKS reales de
Google; las pruebas firman tokens con claves propias y sirven el JWKS con
un transporte fake, por el mismo camino de verificación.

Decisiones que no se ven en el código:

- **`hd` se verifica siempre que está configurado**, no sólo cuando el
  token lo trae: un token sin `hd` contra un canal con dominio declarado
  rechaza igual, porque la política es «esta cuenta institucional», no
  «cualquier Google» (diseño §3).
- **El `sub` nunca sale de la sesión**: lo que se conserva para el
  padrón y la auditoría es el correo verificado — y de él sólo el hash
  (ADR 0016). El identificador opaco de Google no le dice nada al resto
  del sistema, que ya auditaba por hash de correo.
- **El verificador es un puerto, no una conveniencia de test**: el mismo
  código de verificación corre contra los JWKS de Google en producción y
  contra claves de prueba en la suite, así que lo que se prueba es el
  camino real, no un doble.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})


class VerificacionIdentidadError(ValueError):
    """Token inválido o reclamos que no cumplen la política del canal."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class IdentidadVerificada:
    """Lo que Google afirmó, ya verificado: `sub`, correo y dominio."""

    sub: str
    correo: str
    hd: str | None


class VerificadorIdToken(Protocol):
    """Puerto de verificación de identidad del canal web."""

    def verificar(self, token: str) -> IdentidadVerificada: ...


class VerificadorGoogle:
    """Verificación real con `google-auth`.

    `client_id` y `dominio` llegan por entorno (los valores reales los
    entrega DSI, #62): ninguno vive en el repositorio. `request` es el
    transporte de `google.auth.transport` que descarga los JWKS; en pruebas
    se inyecta un fake que devuelve un JWKS de claves de prueba, y
    `certs_url` lo apunta a cualquier origen.
    """

    def __init__(
        self,
        *,
        client_id: str,
        dominio: str | None,
        request=None,
        certs_url: str | None = None,
    ) -> None:
        self._client_id = client_id
        self._dominio = dominio
        if request is None:
            from google.auth.transport import requests as transporte_requests

            request = transporte_requests.Request()
        self._request = request
        self._certs_url = certs_url

    def verificar(self, token: str) -> IdentidadVerificada:
        from google.auth import exceptions as auth_exceptions
        from google.oauth2 import id_token
        from jwt.exceptions import PyJWTError

        kwargs: dict[str, object] = {"audience": self._client_id}
        if self._certs_url is not None:
            kwargs["certs_url"] = self._certs_url
        try:
            payload = id_token.verify_token(token, self._request, **kwargs)
        except (ValueError, auth_exceptions.GoogleAuthError, PyJWTError):
            raise VerificacionIdentidadError("id_token_invalid") from None

        if payload.get("iss") not in _ISSUERS:
            raise VerificacionIdentidadError("iss_invalid")
        hd = payload.get("hd")
        if self._dominio is not None and hd != self._dominio:
            raise VerificacionIdentidadError("dominio_invalid")
        if payload.get("email_verified") is not True:
            raise VerificacionIdentidadError("email_no_verificado")
        correo = payload.get("email")
        sub = payload.get("sub")
        if not isinstance(correo, str) or not correo or not isinstance(sub, str):
            raise VerificacionIdentidadError("claims_incompletos")
        return IdentidadVerificada(sub=sub, correo=correo, hd=hd)


class VerificadorFake:
    """Verificador inyectable para desarrollo y evidencia sin Google.

    Acepta un mapa `token -> IdentidadVerificada`; un token desconocido o la
    cadena `"invalid"` devuelven el mismo error estable que un token real
    inválido. Nunca se usa en producción: el script del servidor lo exige
    explícito.
    """

    def __init__(self, identidades: dict[str, IdentidadVerificada]) -> None:
        self._identidades = dict(identidades)

    def verificar(self, token: str) -> IdentidadVerificada:
        identidad = self._identidades.get(token)
        if identidad is None:
            raise VerificacionIdentidadError("id_token_invalid")
        return identidad
