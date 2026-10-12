"""Puerto de lectura del buzón propio del agente (ADR 0004).

Las respuestas con comprobante de pago llegan a `cursoscomplementarios@` y el
Departamento las reenvía por filtro al buzón de la cuenta técnica. `BuzonPropio`
es el único contacto que el agente tiene con ese correo: **listar** los
mensajes recibidos con sus metadatos. No hay marcar-leído, mover ni borrar: el
agente no administra el buzón, lo relee entero en cada corrida (ADR 0003) y la
custodia de los correos queda en Workspace.

`MensajeBuzon` sólo expone metadatos — remitente, asunto, fecha, Message-ID y,
por cada adjunto, tipo de contenido y sha256 — porque el cuerpo y los adjuntos
son **entrada no confiable** (ADR 0001): la corrida de pagos los cuenta y los
discrimina por hash, nunca los interpreta, y nada de ese contenido puede llegar
a un prompt o a un modelo. Por eso el tipo no tiene campo `cuerpo` ni `datos`
del adjunto: que no exista el campo es el control, no un comentario.

Implementaciones:

- `BuzonPropioEml`: adapter sobre una carpeta de archivos `.eml`. Es la vía de
  las pruebas y de la demo controlada; los archivos se arman a mano (D16).
- `BuzonPropioMemoria`: fake en memoria para ejercitar la corrida sin disco,
  mismo patrón que los demás fakes del paquete.
- `buzon_gmail.GoogleGmailBuzonPropio`: adapter del buzón real por Gmail API
  con `gmail.readonly` sobre la propia cuenta (D11); implementa este mismo
  puerto y produce los mismos `MensajeBuzon`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
import hashlib
from pathlib import Path
from typing import Protocol, Sequence


class BuzonPropioError(ValueError):
    """Falla de lectura del buzón, identificada por un código estable."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class AdjuntoMensaje:
    """Metadatos de un adjunto: de qué tipo es y su huella, nunca su contenido.

    `sha256` se calcula sobre los bytes decodificados del adjunto en el momento
    de la lectura; no se persiste. `nombre` es el nombre de archivo declarado
    por el remitente: es un metadato más, útil para que una persona ubique la
    pieza en el buzón, y no se usa para asociar nada.
    """

    tipo: str
    sha256: str
    nombre: str | None = None


@dataclass(frozen=True)
class MensajeBuzon:
    """Metadatos de un mensaje del buzón propio.

    `remitente` ya viene normalizado (en minúsculas, sólo la dirección). La
    `fecha` puede ser `None` cuando el encabezado Date falta o no se puede
    interpretar: la asociación no la necesita y el orden cronológico la trata
    como la más antigua. El contenido del mensaje no forma parte del tipo por
    diseño (ver docstring del módulo).
    """

    remitente: str
    asunto: str
    fecha: datetime | None
    message_id: str
    adjuntos: tuple[AdjuntoMensaje, ...]


class BuzonPropio(Protocol):
    """Puerto: enumerar los mensajes del buzón propio del agente.

    `listar` devuelve todo lo recibido; quien corre decide qué hacer con cada
    mensaje. El puerto no filtra: filtrar en el adapter escondería mensajes que
    la corrida debe informar como «no asociadas».
    """

    def listar(self) -> list[MensajeBuzon]: ...


class BuzonPropioMemoria:
    """Fake en memoria del puerto, para pruebas sin disco ni transporte."""

    def __init__(self, mensajes: Sequence[MensajeBuzon] = ()) -> None:
        self._mensajes = list(mensajes)

    def agregar(self, mensaje: MensajeBuzon) -> None:
        self._mensajes.append(mensaje)

    def listar(self) -> list[MensajeBuzon]:
        return list(self._mensajes)


class BuzonPropioEml:
    """Adapter del puerto sobre una carpeta de archivos `.eml`.

    Cada archivo `.eml` del directorio es un mensaje. El orden de `listar` es
    determinista (por nombre de archivo) para que dos corridas sobre la misma
    carpeta vean lo mismo; el orden cronológico real lo aplica la corrida por
    el encabezado Date.
    """

    def __init__(self, directorio: Path) -> None:
        self._directorio = Path(directorio)

    def listar(self) -> list[MensajeBuzon]:
        if not self._directorio.is_dir():
            raise BuzonPropioError("buzon_no_encontrado")
        mensajes: list[MensajeBuzon] = []
        for ruta in sorted(self._directorio.iterdir()):
            if ruta.is_file() and ruta.suffix.lower() == ".eml":
                mensajes.append(_parsear_eml(ruta.read_bytes()))
        return mensajes


def _parsear_eml(contenido: bytes) -> MensajeBuzon:
    """Extrae los metadatos de un `.eml`. El cuerpo se descarta en el parser:

    sólo se materializan encabezados y los bytes de los adjuntos para hashear;
    ninguna cadena del cuerpo se conserva en el resultado.
    """

    mensaje = BytesParser(policy=policy.default).parsebytes(contenido)
    return MensajeBuzon(
        remitente=_extraer_remitente(mensaje),
        asunto=str(mensaje.get("Subject", "") or ""),
        fecha=_extraer_fecha(mensaje),
        message_id=_extraer_message_id(mensaje),
        adjuntos=tuple(_iterar_adjuntos(mensaje)),
    )


def _extraer_remitente(mensaje) -> str:
    """Dirección del primer From, normalizada. Vacía si no hay ninguna."""

    encabezado = mensaje.get("From")
    if encabezado is None:
        return ""
    direcciones = getaddresses([str(encabezado)])
    for _nombre, direccion in direcciones:
        if direccion:
            return direccion.strip().lower()
    return ""


def _extraer_fecha(mensaje) -> datetime | None:
    """Date interpretada; `None` si falta o no se puede leer.

    Una fecha sin zona horaria se asume UTC para que el orden cronológico sea
    siempre comparable entre mensajes.
    """

    encabezado = mensaje.get("Date")
    if encabezado is None:
        return None
    try:
        fecha = parsedate_to_datetime(str(encabezado))
    except (TypeError, ValueError):
        return None
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha


def _extraer_message_id(mensaje) -> str:
    encabezado = mensaje.get("Message-ID")
    if encabezado is None:
        return ""
    return str(encabezado).strip().strip("<>").strip()


def _iterar_adjuntos(mensaje):
    """Rinde `AdjuntoMensaje` por cada pieza adjunta del mensaje.

    Una pieza cuenta como adjunta si su disposición es `attachment` o si lleva
    nombre de archivo (una imagen en línea con `cid:` también es un archivo que
    el remitente mandó). Los contenedores multipart no son piezas.
    """

    for parte in mensaje.walk():
        if parte.get_content_maintype() == "multipart":
            continue
        nombre = parte.get_filename()
        if parte.get_content_disposition() != "attachment" and nombre is None:
            continue
        # `decode=True` materializa los bytes del adjunto sólo para hashearlos;
        # el contenido no se conserva ni se inspecciona.
        contenido = parte.get_payload(decode=True) or b""
        yield AdjuntoMensaje(
            tipo=parte.get_content_type().lower(),
            sha256=hashlib.sha256(contenido).hexdigest(),
            nombre=nombre,
        )
