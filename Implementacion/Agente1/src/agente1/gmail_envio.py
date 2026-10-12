"""Adapter Gmail de envío: `gmail.send` detrás de una lista de prueba.

Implementa el puerto `DestinoConfirmaciones` de `confirmaciones.py` contra la
API de Gmail, usando el mismo transporte HTTP a mano que los adapters de
Workspace (`TransporteHttp`, con deadline absoluto y tope de tamaño). Es el
primer destino que manda correo de verdad, y entra cercado por dos decisiones
del diseño de control de pagos (grilling del 2026-10-07):

- **D11**: se habilita Gmail API en la cuenta técnica sin esperar a DSI; los
  scopes quedan `gmail.send` y `gmail.readonly`, y después se informa a DSI
  cómo quedó funcionando.
- **D12**: A1 sólo puede escribir a una **lista de direcciones de prueba**,
  hasta que la SEU apruebe la plantilla de cada tipo. Un destinatario fuera
  de la lista se rechaza *antes* de cualquier llamada de red, aunque el envío
  tenga las dos aprobaciones. Pasar a destinatarios reales es un cambio de
  configuración: se reemplaza la lista, no el código.

Decisiones que no se ven en el código:

- **La lista se valida dos veces.** Al construir el destino —sin lista no hay
  objeto, y una lista vacía o con direcciones inválidas falla igual— y otra
  vez en cada `entregar`, antes del token y del transporte. Que el objeto
  exista no prueba que un destinatario concreto esté permitido.
- **La lista sale de configuración fuera del repo.** Vive en el mismo archivo
  de entorno que el resto de la configuración de Workspace
  (`workspace_config.py`): `AGENTE1_GMAIL_DESTINATARIOS_PRUEBA`, direcciones
  separadas por coma. Nunca se versiona ni se hardcodea: este módulo no
  declara ni una sola dirección.
- **Las dos marcas de borrador viajan en el cuerpo.** Todo cuerpo que sale
  por este destino tiene que empezar con `MARCADOR_BORRADOR` («BORRADOR —
  NO ENVIAR», la marca que escribe `_renderizar` en `confirmaciones.py`), y
  además se le antepone `BORRADOR_MARKER` («BORRADOR — NO PUBLICAR», la
  marca de `destinos.py`) antes de armar el MIME. Mientras la entrega la
  rija la lista de prueba —y este destino sólo existe con lista—, el correo
  se declara no publicable en los dos dialectos del repo. Un cuerpo sin
  marca se rechaza antes de la red.
- **Una sola operación existe: `users/me/messages/send`.** No hay lectura de
  mensajes, ni labels, ni envío «en nombre de» otro buzón: la cuenta técnica
  manda como ella misma (`me`). La auditoría D2 admite exactamente este
  endpoint como servicio de distribución, y sólo con la lista activa.
- **El rechazo no reintenta.** Un destinatario fuera de la lista o un cuerpo
  sin marca levanta `EntregaRechazadaError`, que el circuito distingue de una
  falla del medio: el registro queda `FALLIDA` de una vez, sin gastar
  intentos contra una decisión que no cambia.
"""

from __future__ import annotations

import base64
from collections.abc import Iterable, Mapping
from email.message import EmailMessage
from email import policy
import json
import math
import os
import re
import time

from .confirmaciones import (
    EntregaRechazadaError,
    MARCADOR_BORRADOR,
    email_valido,
)
from .destinos import BORRADOR_MARKER
from .google_workspace import (
    AccessTokenProvider,
    GMAIL_HOST,
    MAX_WORKSPACE_RESPONSE_BYTES,
    MAX_WORKSPACE_TIMEOUT_S,
    HttpsWorkspaceTransport,
    RespuestaHttp,
    TransporteHttp,
    _RespuestaDemasiadoGrande,
)
from .workspace_config import ConfiguracionWorkspaceError


# El único endpoint de distribución que el agente puede llamar: la cuenta
# técnica enviando como ella misma. `auditoria_d2` lo contrasta contra las
# llamadas registradas; cualquier otra ruta de Gmail —lectura, labels, otro
# usuario— sigue siendo un endpoint de distribución prohibido.
GMAIL_SEND_TARGET = "/gmail/v1/users/me/messages/send"
GMAIL_SEND_METHOD = "POST"

# Variable de entorno con la lista de direcciones de prueba, separadas por
# coma. Usa prefijo propio `AGENTE1_GMAIL_`, no `AGENTE1_WORKSPACE_`: no es
# configuración de los adapters de Sheets/Drive/Docs y el loader de Workspace
# la ignora por desconocida si se la escribiera mal.
DESTINATARIOS_PRUEBA_ENV = "AGENTE1_GMAIL_DESTINATARIOS_PRUEBA"
# Techo arbitrario de la lista: una lista de prueba no necesita más que unas
# pocas direcciones, y un límite corta una configuración desbocada.
MAX_DESTINATARIOS_PRUEBA = 100

_CLAVE_IDEMPOTENCIA_RE = re.compile(r"[0-9a-f]{64}\Z")
_GMAIL_MESSAGE_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,256}\Z")


class GmailEnvioError(RuntimeError):
    """Falla del envío Gmail con código auditable, nunca con datos adentro."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class GmailDestinoConfirmaciones:
    """Destino real de confirmaciones por `gmail.send`, cercado por la lista.

    Es el «destino de prueba» del glosario: un buzón real con alcance
    restringido y declarado, que el mecanismo productivo alcanza igual que
    alcanzaría al destino definitivo —se distingue del fake, que finge el
    efecto sin ejecutarlo.

    `destinatarios_permitidos` es la lista efectiva: se normaliza a
    minúsculas y se congela en un `frozenset` al construir. El circuito de
    `confirmaciones.py` habilita este destino comparando el tipo exacto: una
    subclase no hereda el permiso de escribir.
    """

    def __init__(
        self,
        *,
        destinatarios_permitidos: Iterable[str],
        token_provider: AccessTokenProvider,
        transport: TransporteHttp | None = None,
        timeout_s: float = 10.0,
    ) -> None:
        try:
            lista = _validar_lista_prueba(destinatarios_permitidos)
        except ValueError:
            raise ConfiguracionWorkspaceError("gmail_test_list_invalid") from None
        if (
            isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s)
            or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
        ):
            raise ValueError("configuración de Gmail inválida")
        self._destinatarios_permitidos = lista
        self._token_provider = token_provider
        self._transport = transport or HttpsWorkspaceTransport()
        self._timeout_s = float(timeout_s)

    @classmethod
    def desde_entorno(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        token_provider: AccessTokenProvider,
        transport: TransporteHttp | None = None,
        timeout_s: float = 10.0,
    ) -> "GmailDestinoConfirmaciones":
        """Construye el destino con la lista leída del entorno.

        Es el camino productivo: la lista sale de
        `AGENTE1_GMAIL_DESTINATARIOS_PRUEBA`, nunca del código. Ausente,
        vacía o inválida impide que el destino exista.
        """

        return cls(
            destinatarios_permitidos=cargar_destinatarios_prueba(environ),
            token_provider=token_provider,
            transport=transport,
            timeout_s=timeout_s,
        )

    def entregar(
        self,
        *,
        idempotency_key: str,
        destinatario: str,
        asunto: str,
        cuerpo: str,
    ) -> None:
        """Envía el correo. Rechaza antes de tocar el token o la red.

        Tres controles, todos anteriores a cualquier llamada: el destinatario
        tiene que estar en la lista de prueba, los campos que viajan en
        cabeceras no pueden llevar saltos de línea y el cuerpo tiene que
        conservar la marca de borrador. Cada rechazo es
        `EntregaRechazadaError`: una prohibición de política, no una falla
        del medio, así que el circuito la deja `FALLIDA` sin reintentos.
        """

        if (
            not isinstance(destinatario, str)
            or destinatario.strip().lower() not in self._destinatarios_permitidos
        ):
            raise EntregaRechazadaError("recipient_off_test_list")
        if (
            not isinstance(idempotency_key, str)
            or _CLAVE_IDEMPOTENCIA_RE.fullmatch(idempotency_key) is None
            or not isinstance(asunto, str)
            or not asunto
            or "\r" in asunto
            or "\n" in asunto
            or not isinstance(cuerpo, str)
        ):
            raise EntregaRechazadaError("message_contract_invalid")
        if not cuerpo.startswith(MARCADOR_BORRADOR):
            raise EntregaRechazadaError("draft_marker_missing")

        token = self._obtener_token()
        raw = _codificar_mensaje(
            idempotency_key=idempotency_key,
            destinatario=destinatario.strip().lower(),
            asunto=asunto,
            cuerpo=cuerpo,
        )
        body = json.dumps(
            {"raw": raw}, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        try:
            respuesta = self._transport.request(
                method=GMAIL_SEND_METHOD,
                host=GMAIL_HOST,
                target=GMAIL_SEND_TARGET,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                body=body,
                deadline=time.monotonic() + self._timeout_s,
                max_response_bytes=MAX_WORKSPACE_RESPONSE_BYTES,
            )
        except _RespuestaDemasiadoGrande:
            raise GmailEnvioError("gmail_response_too_large") from None
        except Exception:
            # `from None` corta la cadena a propósito: el transporte puede
            # llevar la URL o el token en el mensaje original.
            raise GmailEnvioError("gmail_unavailable") from None
        _validar_respuesta_envio(respuesta)

    def _obtener_token(self) -> str:
        try:
            token = self._token_provider.obtener_access_token()
        except Exception:
            raise GmailEnvioError("gmail_auth_unavailable") from None
        if (
            not isinstance(token, str)
            or not token.strip()
            or token != token.strip()
            or "\r" in token
            or "\n" in token
        ):
            raise GmailEnvioError("gmail_auth_unavailable")
        return token

    def __repr__(self) -> str:
        # La lista no se imprime: un repr con direcciones terminaría en logs.
        return (
            "GmailDestinoConfirmaciones("
            f"lista={len(self._destinatarios_permitidos)} direcciones)"
        )


def cargar_destinatarios_prueba(
    environ: Mapping[str, str] | None = None,
) -> frozenset[str]:
    """Lee la lista de direcciones de prueba desde el entorno.

    `environ` inyectable para probar sin tocar el entorno real del proceso.
    Los mensajes de error son códigos (`gmail_test_list_missing`,
    `gmail_test_list_invalid`) y no dicen qué dirección falló: ese detalle
    terminaría en logs de CI.
    """

    env = os.environ if environ is None else environ
    crudo = env.get(DESTINATARIOS_PRUEBA_ENV)
    if crudo is None or not crudo.strip():
        raise ConfiguracionWorkspaceError("gmail_test_list_missing")
    try:
        return _validar_lista_prueba(crudo.split(","))
    except ValueError:
        raise ConfiguracionWorkspaceError("gmail_test_list_invalid") from None


def _validar_lista_prueba(direcciones: Iterable[object]) -> frozenset[str]:
    """Normaliza y valida la lista; vacía o inválida no produce destino.

    Las direcciones se normalizan a minúsculas sin espacios: la comparación
    por entrega es sobre direcciones canónicas, así una variante de
    mayúsculas no esquiva ni falsifica la lista.
    """

    if isinstance(direcciones, (str, bytes)):
        raise ValueError("lista de prueba inválida")
    normalizadas: set[str] = set()
    try:
        for direccion in direcciones:
            if not isinstance(direccion, str):
                raise ValueError("lista de prueba inválida")
            normalizada = direccion.strip().lower()
            if not email_valido(normalizada):
                raise ValueError("lista de prueba inválida")
            normalizadas.add(normalizada)
    except TypeError:
        raise ValueError("lista de prueba inválida") from None
    if not normalizadas or len(normalizadas) > MAX_DESTINATARIOS_PRUEBA:
        raise ValueError("lista de prueba inválida")
    return frozenset(normalizadas)


def _codificar_mensaje(
    *,
    idempotency_key: str,
    destinatario: str,
    asunto: str,
    cuerpo: str,
) -> str:
    """Arma el RFC 822 y lo devuelve en base64url, el formato de `gmail.send`.

    `EmailMessage` con `policy.SMTP` se encarga de la codificación del asunto
    (puede llevar acentos y el em dash del marcador) y del cuerpo en utf-8.
    La clave de idempotencia viaja en una cabecera `X-`: es un hash, no un
    dato personal, y permite cruzar el correo enviado con el registro sin
    exponer la clave en el texto que lee el destinatario.

    Al cuerpo se le antepone `BORRADOR_MARKER` si no lo llevara: mientras la
    lista de prueba rija la entrega, el mensaje se declara «NO PUBLICAR»
    además de «NO ENVIAR». Si el texto ya viniera con la marca (un pipeline
    que la escribe antes) no se duplica.
    """

    cuerpo_marcado = (
        cuerpo
        if cuerpo.startswith(BORRADOR_MARKER)
        else BORRADOR_MARKER + cuerpo
    )
    mensaje = EmailMessage(policy=policy.SMTP)
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje["X-Agente1-Idempotency-Key"] = idempotency_key
    mensaje.set_content(cuerpo_marcado, charset="utf-8")
    return base64.urlsafe_b64encode(mensaje.as_bytes()).decode("ascii")


def _validar_respuesta_envio(respuesta: RespuestaHttp) -> None:
    """Acepta un 2xx con `id` de mensaje; todo lo demás es error con código."""

    if len(respuesta.body) > MAX_WORKSPACE_RESPONSE_BYTES:
        raise GmailEnvioError("gmail_response_too_large")
    if not 200 <= respuesta.status < 300:
        raise GmailEnvioError(_codigo_gmail(respuesta.status))
    try:
        documento = json.loads(respuesta.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise GmailEnvioError("gmail_response_invalid") from None
    if (
        not isinstance(documento, dict)
        or not isinstance(documento.get("id"), str)
        or _GMAIL_MESSAGE_ID_RE.fullmatch(documento["id"]) is None
    ):
        raise GmailEnvioError("gmail_response_invalid")


def _codigo_gmail(status: int) -> str:
    # 400 se distingue porque significa que nuestro request rompió el
    # contrato de la API —un bug, no un problema del medio. 401/403 es la
    # señal de revocación y nunca se reintenta en el mismo intento.
    if status in {401, 403}:
        return "gmail_auth_denied"
    if status == 400:
        return "gmail_request_invalid"
    if status == 429:
        return "gmail_rate_limited"
    return "gmail_unavailable"
