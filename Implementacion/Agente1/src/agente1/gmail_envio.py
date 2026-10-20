"""Adapter Gmail de envío: `gmail.send` en modo prueba o en modo producción.

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
  tenga las dos aprobaciones. Pasar a destinatarios reales exige el modo
  producción y una lista aprobada, los dos por configuración (ticket #141);
  el código es el mismo.

Los dos modos y por qué el default no cambia:

- **Prueba** (`AGENTE1_GMAIL_MODO` ausente, o `prueba`): la lista sale de
  `AGENTE1_GMAIL_DESTINATARIOS_PRUEBA` y todo cuerpo lleva las dos marcas de
  borrador. Es el comportamiento de siempre y el único que se usa mientras la
  SEU no apruebe la plantilla de cada tipo.
- **Producción** (`AGENTE1_GMAIL_MODO=produccion`): la lista sale de
  `AGENTE1_GMAIL_DESTINATARIOS_APROBADOS` y el cuerpo viaja tal como llega,
  sin prefijo de borrador. Un valor desconocido del modo, la ausencia de la
  lista aprobada o una lista vacía o inválida impiden construir el destino:
  el modo producción no se puede activar a medias.

Decisiones que no se ven en el código:

- **La lista se valida dos veces.** Al construir el destino (sin lista no hay
  objeto, y una lista vacía o con direcciones inválidas falla igual) y otra
  vez en cada `entregar`, antes del token y del transporte. Que el objeto
  exista no prueba que un destinatario concreto esté permitido. Cada modo
  tiene su lista y su techo: la de producción es más grande porque puede
  nombrar una cohorte entera.
- **Las listas salen de configuración fuera del repo.** Viven en el mismo
  archivo de entorno que el resto de la configuración de Workspace
  (`workspace_config.py`), separadas por coma. Nunca se versionan ni se
  hardcodean: este módulo no declara ni una sola dirección. Cuál lista se
  aprueba y con qué plantilla por tipo lo decide la SEU; este ticket no
  inventa ninguna de las dos.
- **Las marcas de borrador son del modo prueba.** Ahí todo cuerpo tiene que
  empezar con `MARCADOR_BORRADOR` («BORRADOR — NO ENVIAR», la marca que
  escribe `_renderizar` en `confirmaciones.py`) y además se le antepone
  `BORRADOR_MARKER` («BORRADOR — NO PUBLICAR», la marca de `destinos.py`)
  antes de armar el MIME: el correo se declara no publicable en los dos
  dialectos del repo. En producción no se exige ni se antepone ninguna, y un
  cuerpo que todavía traiga una marca se rechaza: un texto que dice «NO
  ENVIAR» no puede salir a un destinatario institucional.
- **Una sola operación existe: `users/me/messages/send`.** No hay lectura de
  mensajes, ni labels, ni envío «en nombre de» otro buzón: la cuenta técnica
  manda como ella misma (`me`). La auditoría D2 admite exactamente este
  endpoint como servicio de distribución, con la lista de prueba activa o con
  el modo producción declarado, nunca con los dos a la vez.
- **El rechazo no reintenta.** Un destinatario fuera de la lista o un cuerpo
  con la marca equivocada para el modo levanta `EntregaRechazadaError`, que
  el circuito distingue de una falla del medio: el registro queda `FALLIDA`
  de una vez, sin gastar intentos contra una decisión que no cambia.
- **Un correo puede llevar a lo sumo un adjunto acotado (#75).** La emisión
  de certificados de HU-014 adjunta el PDF al titular y el PDF de muestra al
  correo de aprobación del lote. El adjunto viaja como `AdjuntoCorreo` y se
  valida por completo antes de tocar el token o la red: nombre seguro para
  cabecera, contenido no vacío dentro de un tope fijo y tipo MIME del
  allowlist (hoy sólo `application/pdf`). Un adjunto inválido es un rechazo
  de política, no una falla del medio: `EntregaRechazadaError`, sin
  reintento. El endpoint declarado no cambia: el adjunto va dentro del
  mismo `raw` del `messages/send`, así que la auditoría D2 sigue viendo la
  misma ruta y el mismo método.
"""

from __future__ import annotations

import base64
import json
import math
import os
import re
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from email import policy
from email.message import EmailMessage

from .confirmaciones import (
    MARCADOR_BORRADOR,
    EntregaRechazadaError,
    email_valido,
)
from .destinos import BORRADOR_MARKER
from .google_workspace import (
    GMAIL_HOST,
    MAX_WORKSPACE_RESPONSE_BYTES,
    MAX_WORKSPACE_TIMEOUT_S,
    AccessTokenProvider,
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

# Modo de envío (ticket #141). Ausente equivale a `prueba`: el default no
# cambia. `produccion` es un opt-in explícito que además exige su propia lista.
MODO_ENVIO_ENV = "AGENTE1_GMAIL_MODO"
MODO_ENVIO_PRUEBA = "prueba"
MODO_ENVIO_PRODUCCION = "produccion"
MODOS_ENVIO = frozenset({MODO_ENVIO_PRUEBA, MODO_ENVIO_PRODUCCION})

# Lista aprobada para el modo producción. La aprueba la SEU y vive fuera del
# repo; el ticket #141 no fija direcciones ni plantillas. El techo es más alto
# que el de prueba porque puede nombrar el padrón completo de una cohorte.
DESTINATARIOS_APROBADOS_ENV = "AGENTE1_GMAIL_DESTINATARIOS_APROBADOS"
MAX_DESTINATARIOS_APROBADOS = 1000

_CLAVE_IDEMPOTENCIA_RE = re.compile(r"[0-9a-f]{64}\Z")
_GMAIL_MESSAGE_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,256}\Z")

# Contrato del adjunto (#75): nombre seguro para cabecera `filename` (sin
# separadores de ruta ni bytes de control, así un nombre armado con datos de
# una planilla no puede inyectar cabeceras), tope de tamaño y allowlist de
# tipo MIME. El tope queda muy por debajo del límite de `messages/send` y
# alcanza de sobra para un PDF de una página.
NOMBRE_ADJUNTO_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,198}\Z")
MAX_ADJUNTO_BYTES = 5 * 1024 * 1024
MIME_TYPES_ADJUNTO = frozenset({"application/pdf"})


@dataclass(frozen=True)
class AdjuntoCorreo:
    """Un adjunto de un correo, ya validado en forma pero sin enviar.

    `nombre` es el `filename` del MIME: tiene que ser seguro para cabecera.
    `contenido` son los bytes crudos y `tipo_mime` pertenece al allowlist.
    La validación completa la hace `entregar` antes de cualquier llamada de
    red, igual que la lista de prueba: el dataclass existe para que el
    adjunto sea un dato explícito del contrato, no un tuple suelto.
    """

    nombre: str
    contenido: bytes
    tipo_mime: str = "application/pdf"


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
    efecto sin ejecutarlo—. El mismo objeto sirve a los dos modos; lo que
    cambia es la lista que lo cerca y si el cuerpo lleva marcas de borrador.

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
        modo: str = MODO_ENVIO_PRUEBA,
    ) -> None:
        if modo not in MODOS_ENVIO:
            raise ConfiguracionWorkspaceError("gmail_mode_invalid")
        try:
            lista = _validar_destinatarios(
                destinatarios_permitidos,
                maximo=(
                    MAX_DESTINATARIOS_APROBADOS
                    if modo == MODO_ENVIO_PRODUCCION
                    else MAX_DESTINATARIOS_PRUEBA
                ),
            )
        except ValueError:
            codigo = (
                "gmail_production_list_invalid"
                if modo == MODO_ENVIO_PRODUCCION
                else "gmail_test_list_invalid"
            )
            raise ConfiguracionWorkspaceError(codigo) from None
        if (
            isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s)
            or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
        ):
            raise ValueError("configuración de Gmail inválida")
        self._modo = modo
        self._destinatarios_permitidos = lista
        self._token_provider = token_provider
        self._transport = transport or HttpsWorkspaceTransport()
        self._timeout_s = float(timeout_s)

    @property
    def modo(self) -> str:
        """Modo con el que se construyó el destino: `prueba` o `produccion`.

        Lo lee la auditoría de `confirmaciones.py` para distinguir
        `gmail_test_list` de `gmail_production` en `delivery_mode`.
        """

        return self._modo

    @classmethod
    def desde_entorno(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        token_provider: AccessTokenProvider,
        transport: TransporteHttp | None = None,
        timeout_s: float = 10.0,
    ) -> "GmailDestinoConfirmaciones":
        """Construye el destino con el modo y la lista leídos del entorno.

        Es el camino productivo: sin `AGENTE1_GMAIL_MODO` el modo es `prueba`
        y la lista sale de `AGENTE1_GMAIL_DESTINATARIOS_PRUEBA`, como siempre.
        Con `produccion`, la lista sale de
        `AGENTE1_GMAIL_DESTINATARIOS_APROBADOS`. Un modo desconocido o una
        lista ausente, vacía o inválida impiden que el destino exista.
        """

        modo = cargar_modo_envio(environ)
        destinatarios = (
            cargar_destinatarios_aprobados(environ)
            if modo == MODO_ENVIO_PRODUCCION
            else cargar_destinatarios_prueba(environ)
        )
        return cls(
            destinatarios_permitidos=destinatarios,
            token_provider=token_provider,
            transport=transport,
            timeout_s=timeout_s,
            modo=modo,
        )

    def entregar(
        self,
        *,
        idempotency_key: str,
        destinatario: str,
        asunto: str,
        cuerpo: str,
        adjunto: AdjuntoCorreo | None = None,
    ) -> None:
        """Envía el correo. Rechaza antes de tocar el token o la red.

        Cuatro controles, todos anteriores a cualquier llamada: el
        destinatario tiene que estar en la lista del modo, los campos que
        viajan en cabeceras no pueden llevar saltos de línea, el cuerpo tiene
        que cumplir el contrato de marcas de su modo y el adjunto, cuando
        viene, tiene que cumplir el contrato de `AdjuntoCorreo` (nombre
        seguro, contenido dentro del tope, MIME del allowlist). Cada rechazo
        es `EntregaRechazadaError`: una prohibición de política, no una falla
        del medio, así que el circuito la deja `FALLIDA` sin reintentos.
        """

        en_produccion = self._modo == MODO_ENVIO_PRODUCCION
        if (
            not isinstance(destinatario, str)
            or destinatario.strip().lower() not in self._destinatarios_permitidos
        ):
            raise EntregaRechazadaError(
                "recipient_off_approved_list"
                if en_produccion
                else "recipient_off_test_list"
            )
        if (
            not isinstance(idempotency_key, str)
            or _CLAVE_IDEMPOTENCIA_RE.fullmatch(idempotency_key) is None
            or not isinstance(asunto, str)
            or not asunto
            or "\r" in asunto
            or "\n" in asunto
            or not isinstance(cuerpo, str)
            or not cuerpo.strip()
        ):
            raise EntregaRechazadaError("message_contract_invalid")
        if en_produccion:
            # El cuerpo de producción es el de la plantilla aprobada. Si
            # todavía trae una marca de borrador, el pipeline que lo armó no
            # está listo para producción: se rechaza antes de la red.
            if cuerpo.startswith(MARCADOR_BORRADOR) or cuerpo.startswith(
                BORRADOR_MARKER
            ):
                raise EntregaRechazadaError("draft_marker_in_production")
        elif not cuerpo.startswith(MARCADOR_BORRADOR):
            raise EntregaRechazadaError("draft_marker_missing")
        if adjunto is not None and not _adjunto_valido(adjunto):
            raise EntregaRechazadaError("attachment_contract_invalid")

        token = self._obtener_token()
        raw = _codificar_mensaje(
            idempotency_key=idempotency_key,
            destinatario=destinatario.strip().lower(),
            asunto=asunto,
            cuerpo=cuerpo,
            adjunto=adjunto,
            marcar_borrador=not en_produccion,
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
            f"modo={self._modo}, "
            f"lista={len(self._destinatarios_permitidos)} direcciones)"
        )


def cargar_modo_envio(environ: Mapping[str, str] | None = None) -> str:
    """Lee el modo de envío; ausente es `prueba`, un valor raro es error.

    Una variable ausente conserva el comportamiento de siempre. Una variable
    presente pero vacía o con un valor fuera de `MODOS_ENVIO` no se interpreta
    como default: es una configuración ambigua y falla cerrado con
    `gmail_mode_invalid`, para que nadie active producción «casi».
    """

    env = os.environ if environ is None else environ
    crudo = env.get(MODO_ENVIO_ENV)
    if crudo is None:
        return MODO_ENVIO_PRUEBA
    modo = crudo.strip().lower()
    if modo not in MODOS_ENVIO:
        raise ConfiguracionWorkspaceError("gmail_mode_invalid")
    return modo


def cargar_destinatarios_prueba(
    environ: Mapping[str, str] | None = None,
) -> frozenset[str]:
    """Lee la lista de direcciones de prueba desde el entorno.

    `environ` inyectable para probar sin tocar el entorno real del proceso.
    Los mensajes de error son códigos (`gmail_test_list_missing`,
    `gmail_test_list_invalid`) y no dicen qué dirección falló: ese detalle
    terminaría en logs de CI.
    """

    return _cargar_lista(
        environ,
        variable=DESTINATARIOS_PRUEBA_ENV,
        maximo=MAX_DESTINATARIOS_PRUEBA,
        codigo_ausente="gmail_test_list_missing",
        codigo_invalido="gmail_test_list_invalid",
    )


def cargar_destinatarios_aprobados(
    environ: Mapping[str, str] | None = None,
) -> frozenset[str]:
    """Lee la lista aprobada del modo producción desde el entorno.

    Mismo contrato que la lista de prueba, con sus propios códigos:
    `gmail_production_list_missing` y `gmail_production_list_invalid`. La
    lista la aprueba la SEU y no se versiona.
    """

    return _cargar_lista(
        environ,
        variable=DESTINATARIOS_APROBADOS_ENV,
        maximo=MAX_DESTINATARIOS_APROBADOS,
        codigo_ausente="gmail_production_list_missing",
        codigo_invalido="gmail_production_list_invalid",
    )


def _cargar_lista(
    environ: Mapping[str, str] | None,
    *,
    variable: str,
    maximo: int,
    codigo_ausente: str,
    codigo_invalido: str,
) -> frozenset[str]:
    env = os.environ if environ is None else environ
    crudo = env.get(variable)
    if crudo is None or not crudo.strip():
        raise ConfiguracionWorkspaceError(codigo_ausente)
    try:
        return _validar_destinatarios(crudo.split(","), maximo=maximo)
    except ValueError:
        raise ConfiguracionWorkspaceError(codigo_invalido) from None


def _validar_destinatarios(
    direcciones: Iterable[object], *, maximo: int
) -> frozenset[str]:
    """Normaliza y valida la lista; vacía o inválida no produce destino.

    Las direcciones se normalizan a minúsculas sin espacios: la comparación
    por entrega es sobre direcciones canónicas, así una variante de
    mayúsculas no esquiva ni falsifica la lista.
    """

    if isinstance(direcciones, (str, bytes)):
        raise ValueError("lista de destinatarios inválida")
    normalizadas: set[str] = set()
    try:
        for direccion in direcciones:
            if not isinstance(direccion, str):
                raise ValueError("lista de destinatarios inválida")
            normalizada = direccion.strip().lower()
            if not email_valido(normalizada):
                raise ValueError("lista de destinatarios inválida")
            normalizadas.add(normalizada)
    except TypeError:
        raise ValueError("lista de destinatarios inválida") from None
    if not normalizadas or len(normalizadas) > maximo:
        raise ValueError("lista de destinatarios inválida")
    return frozenset(normalizadas)


def _adjunto_valido(adjunto: object) -> bool:
    """El adjunto cumple el contrato: nombre seguro, contenido acotado, MIME
    del allowlist. Se corre entero antes de cualquier llamada de red."""

    return (
        isinstance(adjunto, AdjuntoCorreo)
        and isinstance(adjunto.nombre, str)
        and NOMBRE_ADJUNTO_RE.fullmatch(adjunto.nombre) is not None
        and isinstance(adjunto.contenido, bytes)
        and 0 < len(adjunto.contenido) <= MAX_ADJUNTO_BYTES
        and adjunto.tipo_mime in MIME_TYPES_ADJUNTO
    )


def _codificar_mensaje(
    *,
    idempotency_key: str,
    destinatario: str,
    asunto: str,
    cuerpo: str,
    adjunto: AdjuntoCorreo | None = None,
    marcar_borrador: bool = True,
) -> str:
    """Arma el RFC 822 y lo devuelve en base64url, el formato de `gmail.send`.

    `EmailMessage` con `policy.SMTP` se encarga de la codificación del asunto
    (puede llevar acentos y el em dash del marcador) y del cuerpo en utf-8.
    La clave de idempotencia viaja en una cabecera `X-`: es un hash, no un
    dato personal, y permite cruzar el correo enviado con el registro sin
    exponer la clave en el texto que lee el destinatario.

    En modo prueba, al cuerpo se le antepone `BORRADOR_MARKER` si no lo
    llevara: el mensaje se declara «NO PUBLICAR» además de «NO ENVIAR». Si el
    texto ya viniera con la marca (un pipeline que la escribe antes) no se
    duplica. En modo producción `marcar_borrador` es `False` y el cuerpo
    viaja exactamente como llegó: es el de la plantilla aprobada.

    El adjunto, cuando viene, se agrega como una parte MIME más del mismo
    mensaje: el endpoint y el método del envío no cambian.
    """

    cuerpo_marcado = cuerpo
    if marcar_borrador and not cuerpo.startswith(BORRADOR_MARKER):
        cuerpo_marcado = BORRADOR_MARKER + cuerpo
    mensaje = EmailMessage(policy=policy.SMTP)
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje["X-Agente1-Idempotency-Key"] = idempotency_key
    mensaje.set_content(cuerpo_marcado, charset="utf-8")
    if adjunto is not None:
        maintype, _, subtype = adjunto.tipo_mime.partition("/")
        mensaje.add_attachment(
            adjunto.contenido,
            maintype=maintype,
            subtype=subtype,
            filename=adjunto.nombre,
        )
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
