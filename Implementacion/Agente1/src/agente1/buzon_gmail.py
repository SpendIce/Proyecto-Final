"""Adapter del puerto `BuzonPropio` sobre Gmail API, sólo lectura (ADR 0004).

Implementa `BuzonPropio` contra el buzón de la cuenta técnica del agente, con
el scope `gmail.readonly` que D11 habilitó sobre esa cuenta, sin delegación.
La corrida de control de pagos funciona igual con este adapter, con la carpeta
`.eml` o con el fake en memoria: todas las vías hablan `listar()` y devuelven
los mismos `MensajeBuzon` — sólo metadatos, nunca contenido (ADR 0001).

Son exactamente tres los endpoints que este módulo puede tocar, todos de
lectura y todos sobre el usuario `me`, que va literal en la ruta:

- `GET /gmail/v1/users/me/messages?q=<consulta>` — lista los mensajes del
  buzón que entran en la consulta acotada (el criterio del filtro del
  Departamento: asunto de preinscripción con adjunto).
- `GET /gmail/v1/users/me/messages/{id}?format=full` — encabezados y la
  estructura de partes MIME de cada mensaje listado.
- `GET /gmail/v1/users/me/messages/{id}/attachments/{attId}` — los bytes de
  cada adjunto, que se decodifican y se hashean **en memoria**: nada se
  descarga a disco, el sha256 no se persiste y el contenido no puede llegar
  a un modelo porque `AdjuntoMensaje` no tiene campo para él.

Decisiones que no se ven en el código:

- **`me` literal, nunca parametrizado.** El usuario forma parte de la ruta
  fija: no existe una configuración que pueda apuntar el adapter al buzón de
  otra cuenta. Recibir correos reenviados no otorga los permisos del buzón
  que los recibió primero.
- **La consulta se fija en el constructor.** `consulta` replica el criterio
  del filtro de reenvío del Departamento (ADR 0004: ese criterio es un
  contrato que no se puede cambiar sólo de un lado). Va URL-encoded en `q`;
  no hay forma de ampliarla en tiempo de ejecución.
- **Paginación con tope explícito y fail-closed.** `tope_mensajes` corta el
  listado: si Gmail devuelve un `nextPageToken` cuando ya se llegó al tope,
  la corrida falla con `gmail_paginacion_excedida` en vez de trabajar sobre
  un buzón truncado — un comprobante invisible derivaría un `PENDIENTE`
  falso y un recordatorio indebido.
- **Un solo deadline para toda la lectura.** Listar páginas, leer cada
  mensaje y traer cada adjunto comparten el mismo deadline absoluto y el
  mismo tope de respuesta `MAX_WORKSPACE_RESPONSE_BYTES`, con la misma
  disciplina que los demás adapters de Workspace: una respuesta anómala no
  puede estirar la corrida ni agotar memoria.
- **Un 404 al leer un mensaje listado lo omite.** El diseño acepta que un
  correo desaparezca del buzón — la cuota vuelve a figurar pendiente — así
  que un borrado entre el listado y la lectura no tumba la corrida (§6.3).
  Un 404 al leer un adjunto sí falla: contarlo sin hashearlo sería mentir
  sobre el comprobante.
- **Las etiquetas y el estado de los mensajes no se tocan.** No hay
  `modify`, `trash`, `send` ni `labels` en ninguna ruta que este módulo
  construye: el agente no administra el buzón, lo relee.
"""

from __future__ import annotations

import base64
import binascii
from datetime import timezone
from email.utils import getaddresses, parsedate_to_datetime
import hashlib
import json
import math
import time
from urllib.parse import quote

from .buzon import AdjuntoMensaje, BuzonPropioError, MensajeBuzon
from .google_workspace import (
    GMAIL_HOST,
    ID_RE,
    MAX_WORKSPACE_RESPONSE_BYTES,
    MAX_WORKSPACE_TIMEOUT_S,
    AccessTokenProvider,
    HttpsWorkspaceTransport,
    TransporteHttp,
    _RespuestaDemasiadoGrande,
)


# La ruta de mensajes lleva el usuario `me` literal: leer el buzón propio es
# el único caso previsto (ADR 0004) y la auditoría admite justo estas rutas.
_GMAIL_MESSAGES = "/gmail/v1/users/me/messages"
_MAX_CONSULTA_CARACTERES = 512
_MAX_TOKEN_PAGINA_CARACTERES = 2048
_TOPE_MENSAJES_MAXIMO = 5_000
_TAMANO_PAGINA_MAXIMO = 500  # tope que la propia API de Gmail acepta

# Id de adjunto devuelto por la API: misma forma segura que un id de Workspace.
_ATT_ID_RE = ID_RE


class GoogleGmailBuzonPropio:
    """Lee el buzón propio por Gmail API y devuelve `MensajeBuzon`.

    `listar()` pide el listado paginado con la consulta fijada al construir,
    lee cada mensaje con `format=full` — de donde salen los encabezados y la
    declaración de partes — y trae cada adjunto por `attachments.get` sólo
    para hashear sus bytes decodificados en memoria. Es la implementación del
    puerto para la cuenta técnica real; en pruebas se inyecta un transporte
    fake y el resultado es equivalente al de `BuzonPropioEml` sobre el mismo
    conjunto de mensajes.
    """

    def __init__(
        self,
        *,
        consulta: str,
        token_provider: AccessTokenProvider,
        transport: TransporteHttp | None = None,
        timeout_s: float = 10.0,
        tope_mensajes: int = 500,
        tamano_pagina: int = 100,
    ) -> None:
        # Toda la validación de la configuración ocurre acá: un despliegue mal
        # configurado falla al arrancar, no a mitad de una corrida.
        if (
            not isinstance(consulta, str)
            or not 1 <= len(consulta) <= _MAX_CONSULTA_CARACTERES
            or any(
                ord(caracter) < 32 or ord(caracter) == 127
                for caracter in consulta
            )
            or isinstance(tope_mensajes, bool)
            or not isinstance(tope_mensajes, int)
            or not 1 <= tope_mensajes <= _TOPE_MENSAJES_MAXIMO
            or isinstance(tamano_pagina, bool)
            or not isinstance(tamano_pagina, int)
            or not 1 <= tamano_pagina <= _TAMANO_PAGINA_MAXIMO
            or isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s)
            or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
        ):
            raise ValueError("configuración de Gmail inválida")
        self._consulta = consulta
        self._tope_mensajes = tope_mensajes
        self._tamano_pagina = tamano_pagina
        self._token_provider = token_provider
        self._transport = transport or HttpsWorkspaceTransport()
        self._timeout_s = float(timeout_s)

    def listar(self) -> list[MensajeBuzon]:
        """Relee el buzón completo dentro de la consulta, como pide el puerto.

        El orden es el del listado de Gmail (más reciente primero); el orden
        cronológico real lo aplica la corrida por el encabezado Date.
        """
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._obtener_token()}",
        }
        deadline = time.monotonic() + self._timeout_s
        mensajes: list[MensajeBuzon] = []
        for message_id in self._listar_ids(headers, deadline):
            mensaje = self._leer_mensaje(headers, deadline, message_id)
            if mensaje is not None:
                mensajes.append(mensaje)
        return mensajes

    def _listar_ids(self, headers: dict[str, str], deadline: float) -> list[str]:
        """Recorre las páginas del listado y devuelve los ids, con tope.

        Un `nextPageToken` que queda pendiente al llegar al tope es un error,
        no un corte silencioso: trabajar sobre una porción del buzón esconde
        comprobantes.
        """
        ids: list[str] = []
        token_pagina: str | None = None
        while True:
            target = (
                f"{_GMAIL_MESSAGES}"
                f"?maxResults={min(self._tamano_pagina, self._tope_mensajes)}"
                "&fields=messages(id),nextPageToken"
                f"&q={quote(self._consulta, safe='')}"
            )
            if token_pagina is not None:
                target += f"&pageToken={quote(token_pagina, safe='')}"
            documento = self._get_json(headers, deadline, target)
            mensajes = documento.get("messages", [])
            if not isinstance(mensajes, list):
                raise BuzonPropioError("gmail_response_invalid")
            for entrada in mensajes:
                if (
                    not isinstance(entrada, dict)
                    or not isinstance(entrada.get("id"), str)
                    or ID_RE.fullmatch(entrada["id"]) is None
                ):
                    raise BuzonPropioError("gmail_response_invalid")
                ids.append(entrada["id"])
            if len(ids) > self._tope_mensajes:
                raise BuzonPropioError("gmail_paginacion_excedida")
            token_pagina = documento.get("nextPageToken")
            if token_pagina is None:
                return ids
            if (
                not isinstance(token_pagina, str)
                or not token_pagina
                or len(token_pagina) > _MAX_TOKEN_PAGINA_CARACTERES
            ):
                raise BuzonPropioError("gmail_response_invalid")
            if len(ids) >= self._tope_mensajes:
                raise BuzonPropioError("gmail_paginacion_excedida")

    def _leer_mensaje(
        self, headers: dict[str, str], deadline: float, message_id: str
    ) -> MensajeBuzon | None:
        """Lee un mensaje con `format=full`. `None` si desapareció del buzón
        entre el listado y la lectura: el diseño lo trata como correo borrado
        (§6.3), no como falla de la corrida."""
        try:
            documento = self._get_json(
                headers,
                deadline,
                f"{_GMAIL_MESSAGES}/{message_id}"
                "?format=full&fields=id,payload",
            )
        except BuzonPropioError as exc:
            if exc.code == "gmail_source_not_found":
                return None
            raise
        payload = documento.get("payload")
        if not isinstance(payload, dict):
            raise BuzonPropioError("gmail_response_invalid")
        encabezados = _mapa_encabezados(payload)
        return MensajeBuzon(
            remitente=_remitente(encabezados.get("from")),
            asunto=encabezados.get("subject") or "",
            fecha=_fecha(encabezados.get("date")),
            message_id=_message_id(encabezados.get("message-id")),
            adjuntos=tuple(
                self._iterar_adjuntos(headers, deadline, message_id, payload)
            ),
        )

    def _iterar_adjuntos(
        self,
        headers: dict[str, str],
        deadline: float,
        message_id: str,
        payload: dict[str, object],
    ):
        """Rinde `AdjuntoMensaje` por cada parte adjunta del payload.

        El criterio es el mismo que el del adapter `.eml`: una parte cuenta si
        lleva nombre de archivo o si su disposición es `attachment`; los
        contenedores multipart no son partes. Así el mismo correo produce los
        mismos adjuntos por cualquiera de los dos adapters.
        """
        pila = [payload]
        while pila:
            parte = pila.pop()
            if not isinstance(parte, dict):
                raise BuzonPropioError("gmail_response_invalid")
            mime = parte.get("mimeType")
            if not isinstance(mime, str):
                raise BuzonPropioError("gmail_response_invalid")
            if mime.lower().startswith("multipart/"):
                subpartes = parte.get("parts", [])
                if not isinstance(subpartes, list):
                    raise BuzonPropioError("gmail_response_invalid")
                pila.extend(subpartes)
                continue
            nombre = parte.get("filename")
            # La API puede omitir `filename` en piezas que no son adjunto:
            # ausente o nulo cuenta como sin nombre, cualquier otro tipo es
            # una respuesta fuera de contrato.
            if nombre is None:
                nombre = ""
            if not isinstance(nombre, str):
                raise BuzonPropioError("gmail_response_invalid")
            disposicion = _encabezado_parte(parte, "content-disposition")
            if not nombre and not disposicion.lower().startswith("attachment"):
                continue
            yield AdjuntoMensaje(
                tipo=mime.lower(),
                sha256=self._sha256_adjunto(
                    headers, deadline, message_id, parte
                ),
                nombre=nombre or None,
            )

    def _sha256_adjunto(
        self,
        headers: dict[str, str],
        deadline: float,
        message_id: str,
        parte: dict[str, object],
    ) -> str:
        """El sha256 de los bytes decodificados del adjunto, en memoria.

        Con `format=full` el cuerpo de un adjunto llega como `attachmentId` y
        hay que pedirlo a `attachments.get`; una pieza chica puede venir en
        línea en `body.data` y no necesita request extra. En ambos casos el
        contenido se descarta apenas calculado el hash.
        """
        cuerpo = parte.get("body")
        if not isinstance(cuerpo, dict):
            raise BuzonPropioError("gmail_response_invalid")
        datos = cuerpo.get("data")
        if isinstance(datos, str) and datos:
            return _sha256_b64url(datos)
        att_id = cuerpo.get("attachmentId")
        if att_id in (None, ""):
            # Pieza declarada adjunta sin cuerpo: cuenta como contenido vacío,
            # igual que un `.eml` cuyo adjunto viene sin bytes.
            return hashlib.sha256(b"").hexdigest()
        if not isinstance(att_id, str) or _ATT_ID_RE.fullmatch(att_id) is None:
            raise BuzonPropioError("gmail_response_invalid")
        documento = self._get_json(
            headers,
            deadline,
            f"{_GMAIL_MESSAGES}/{message_id}/attachments/{att_id}?fields=data",
        )
        datos = documento.get("data")
        if not isinstance(datos, str):
            raise BuzonPropioError("gmail_response_invalid")
        return _sha256_b64url(datos)

    def _get_json(
        self, headers: dict[str, str], deadline: float, target: str
    ) -> dict[str, object]:
        """GET al host fijo de Gmail con la disciplina común de Workspace.

        Los errores se traducen a códigos por servicio (`gmail_*`), con el
        mismo criterio que los otros adapters: el cuerpo remoto no se refleja
        y un 401/403 nunca se reintenta.
        """
        try:
            respuesta = self._transport.request(
                method="GET",
                host=GMAIL_HOST,
                target=target,
                headers=headers,
                body=None,
                deadline=deadline,
                max_response_bytes=MAX_WORKSPACE_RESPONSE_BYTES,
            )
        except _RespuestaDemasiadoGrande:
            raise BuzonPropioError("gmail_response_too_large") from None
        except Exception:
            # `from None`: el traceback original puede llevar la URL o el
            # token, y estos errores terminan en logs y reportes.
            raise BuzonPropioError("gmail_unavailable") from None
        if len(respuesta.body) > MAX_WORKSPACE_RESPONSE_BYTES:
            raise BuzonPropioError("gmail_response_too_large")
        if respuesta.status in {401, 403}:
            raise BuzonPropioError("gmail_auth_denied")
        if respuesta.status == 404:
            raise BuzonPropioError("gmail_source_not_found")
        if respuesta.status == 429:
            raise BuzonPropioError("gmail_rate_limited")
        if not 200 <= respuesta.status < 300:
            raise BuzonPropioError("gmail_unavailable")
        try:
            documento = json.loads(respuesta.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise BuzonPropioError("gmail_response_invalid") from None
        if not isinstance(documento, dict):
            raise BuzonPropioError("gmail_response_invalid")
        return documento

    def _obtener_token(self) -> str:
        try:
            token = self._token_provider.obtener_access_token()
        except Exception:
            raise BuzonPropioError("gmail_auth_unavailable") from None
        if (
            not isinstance(token, str)
            or not token.strip()
            or token != token.strip()
            or "\r" in token
            or "\n" in token
        ):
            raise BuzonPropioError("gmail_auth_unavailable")
        return token


def _mapa_encabezados(payload: dict[str, object]) -> dict[str, str]:
    """Encabezados del mensaje indexados por nombre en minúsculas; el primero
    gana, como en el parser de `.eml`. Son estructura, no contenido."""
    encabezados = payload.get("headers")
    if not isinstance(encabezados, list):
        raise BuzonPropioError("gmail_response_invalid")
    mapa: dict[str, str] = {}
    for encabezado in encabezados:
        if (
            not isinstance(encabezado, dict)
            or not isinstance(encabezado.get("name"), str)
            or not isinstance(encabezado.get("value"), str)
        ):
            raise BuzonPropioError("gmail_response_invalid")
        mapa.setdefault(encabezado["name"].lower(), encabezado["value"])
    return mapa


def _encabezado_parte(parte: dict[str, object], nombre: str) -> str:
    """Primer encabezado `nombre` declarado en una parte MIME; vacío si no hay
    lista de encabezados en la parte (la API la puede omitir)."""
    encabezados = parte.get("headers")
    if encabezados is None:
        return ""
    if not isinstance(encabezados, list):
        raise BuzonPropioError("gmail_response_invalid")
    buscado = nombre.lower()
    for encabezado in encabezados:
        if (
            not isinstance(encabezado, dict)
            or not isinstance(encabezado.get("name"), str)
            or not isinstance(encabezado.get("value"), str)
        ):
            raise BuzonPropioError("gmail_response_invalid")
        if encabezado["name"].lower() == buscado:
            return encabezado["value"]
    return ""


def _remitente(valor: str | None) -> str:
    """Dirección del primer From, normalizada. Vacía si no hay ninguna."""
    if not valor:
        return ""
    for _nombre, direccion in getaddresses([valor]):
        if direccion:
            return direccion.strip().lower()
    return ""


def _fecha(valor: str | None):
    """Date interpretada; `None` si falta o no se puede leer. Una fecha sin
    zona se asume UTC, igual que en el adapter `.eml`."""
    if not valor:
        return None
    try:
        fecha = parsedate_to_datetime(valor)
    except (TypeError, ValueError):
        return None
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha


def _message_id(valor: str | None) -> str:
    if not valor:
        return ""
    return valor.strip().strip("<>").strip()


def _sha256_b64url(datos: str) -> str:
    """Decodifica base64url y devuelve el sha256 de los bytes; la entrada
    malformada es una respuesta inválida, nunca un hash de basura."""
    try:
        contenido = base64.urlsafe_b64decode(
            datos.encode("ascii") + b"=" * (-len(datos) % 4)
        )
    except (UnicodeEncodeError, binascii.Error, ValueError):
        raise BuzonPropioError("gmail_response_invalid") from None
    return hashlib.sha256(contenido).hexdigest()
