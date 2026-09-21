"""Slice offline de HU-014: certificados en PDF, nunca emisión real.

Genera el texto y el PDF de un certificado de asistencia o de aprobación y
modela su ciclo de vida completo, incluida la doble aprobación humana y la
"emisión", pero **no existe ningún adapter que emita de verdad**. La única
emisión posible es contra `DestinoCertificadosFake`, y se verifica en tiempo
de ejecución comparando el tipo exacto (`type(destino) is not
DestinoCertificadosFake`, no `isinstance`): ni siquiera una subclase puede
colarse como destino.

Por qué modelar una emisión que no se hace: el punto de la HU es demostrar
que la secuencia de autorización es correcta (sin aprobación no hay emisión,
un reintento no duplica, una reserva interrumpida no se reemite a ciegas)
antes de que exista la capacidad técnica de emitir. Cuando la SEU defina la
plantilla institucional, el destino de entrega y la firma digital, lo que se
agrega es un adapter, no la lógica de control.

Estados: `PENDIENTE_VALIDACION` → `APROBADA_SEMANTICA` | `APROBADA_UTILITARIA`
según cuál de las dos aprobaciones llega primero, y de ahí → `APROBADA`
cuando llega la complementaria; cualquier decisión negativa lleva a
`RECHAZADA`. Sólo desde `APROBADA` —las dos aprobaciones registradas— se
puede pasar a `EMISION_RESERVADA` → `EMITIDA_SIMULADA` | `FALLIDA`. El paso
intermedio existe para que una caída durante la emisión no deje el registro
en un estado que habilite reintentar y emitir dos veces; al reinicio se
reconcilia hacia `EMISION_INDETERMINADA`, sin reemitir.

El PDF se genera sólo con stdlib: un documento mínimo de una página,
determinista byte a byte (sin timestamps ni identificadores aleatorios, que
son los que suelen hacer irreproducible un PDF). La plantilla es provisional
y lleva la marca `BORRADOR — NO EMITIR` en toda salida previa a la aprobación
completa; la plantilla institucional queda `PENDIENTE_SEU`, igual que la
firma digital que menciona el enunciado de la HU.

El circuito de decisión es el de HU-012 sin modificaciones: se reusan
`AprobacionHumana`, `ROLES_APROBACION`, los estados parciales y el registro
durable archivo-por-clave (`os.link` + `flock`). Los helpers privados que se
importan mantienen un único contrato de decisión y de hash entre las dos HU;
los alias de registro sólo ponen el nombre del dominio en las firmas.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Protocol
import uuid

from agente1.confirmaciones import (
    ESTADO_APROBADA_SEMANTICA,
    ESTADO_APROBADA_UTILITARIA,
    ESTADOS_PARCIALES_APROBACION,
    ID_RE,
    AprobacionHumana,
    BorradorRegistrado,
    RegistroConfirmaciones,
    RegistroConfirmacionesArchivo,
    RegistroConfirmacionesMemoria,
    _aprobacion_valida,
    _hash,
    _PARCIAL_POR_ROL,
)


HU = "HU-014"
CONTRACT_VERSION = "certificado_emision_v1"
TEMPLATE_VERSION = "certificado_provisional_v1"
POLICY_STATUS = "PROVISIONAL_NO_INSTITUCIONAL"
MARCADOR_BORRADOR = "BORRADOR — NO EMITIR"
TIPOS_CERTIFICADO = frozenset({"ASISTENCIA", "APROBACION"})
REQUIRED_FIELDS = (
    "id_certificado",
    "nombre_titular",
    "documento_titular",
    "actividad",
    "fecha",
    "organiza",
    "firmante",
)

# Encabezado del documento y verbo de la línea de certificación, por tipo.
_TEXTO_POR_TIPO = {
    "ASISTENCIA": ("CERTIFICADO DE ASISTENCIA", "asistió a"),
    "APROBACION": ("CERTIFICADO DE APROBACIÓN", "aprobó"),
}

# El puerto de registro es genérico: guarda (estado, asunto, cuerpo) por
# clave, donde `asunto` es el título del certificado y `cuerpo` el texto
# canónico del que se deriva el PDF. `RegistroConfirmacionesArchivo` ya
# implementa crear-una-vez con `os.link`, lock por clave con `flock`,
# permisos restrictivos y listado por estado para reconciliar.
RegistroCertificados = RegistroConfirmaciones
RegistroCertificadosMemoria = RegistroConfirmacionesMemoria
RegistroCertificadosArchivo = RegistroConfirmacionesArchivo


@dataclass(frozen=True)
class SolicitudCertificado:
    id_certificado: str
    nombre_titular: str
    documento_titular: str
    tipo_certificado: str
    actividad: str
    fecha: str
    organiza: str
    firmante: str


@dataclass(frozen=True)
class EmisionSimulada:
    idempotency_key: str
    titulo: str
    pdf: bytes


class DestinoCertificados(Protocol):
    """Puerto sin implementación productiva en HU-014 offline."""

    def emitir(
        self, *, idempotency_key: str, titulo: str, pdf: bytes
    ) -> None: ...


class DestinoCertificadosFake:
    """Test double explícito: registra emisiones en memoria y no usa red."""

    def __init__(self, *, error: str | None = None) -> None:
        self.emisiones: list[EmisionSimulada] = []
        self._error = error

    def emitir(
        self, *, idempotency_key: str, titulo: str, pdf: bytes
    ) -> None:
        if self._error:
            raise RuntimeError(self._error)
        self.emisiones.append(EmisionSimulada(idempotency_key, titulo, pdf))


@dataclass(frozen=True)
class EmisionReconciliada:
    """Una emisión que quedó en duda, y por qué no se reintenta."""

    idempotency_key: str
    estado_anterior: str = "EMISION_RESERVADA"
    estado: str = "EMISION_INDETERMINADA"


def reconciliar_emisiones_reservadas(
    registro: RegistroCertificadosArchivo,
) -> tuple[EmisionReconciliada, ...]:
    """Cierra las reservas que quedaron colgadas, sin volver a emitir.

    Una reserva interrumpida es, por definición, indeterminada: el proceso
    murió entre reservar y saber el resultado, así que nadie puede afirmar si
    la emisión ocurrió. Reintentar sería apostar a que no, y el costo de
    equivocarse es un certificado duplicado a nombre de una persona real.

    Por eso la reconciliación no emite ni marca como emitida: mueve el
    registro a `EMISION_INDETERMINADA`, un estado terminal para el pipeline
    —`procesar_certificado` no transiciona desde ahí— que existe para que una
    persona decida con el registro a la vista.
    """

    reconciliadas = []
    for clave in registro.listar_por_estado("EMISION_RESERVADA"):
        if registro.transicionar(
            clave, frozenset({"EMISION_RESERVADA"}), "EMISION_INDETERMINADA"
        ):
            reconciliadas.append(EmisionReconciliada(idempotency_key=clave))
    return tuple(reconciliadas)


@dataclass(frozen=True)
class ResultadoCertificado:
    estado: str
    idempotency_key: str
    log_path: Path
    correlation_id: str
    titulo: str | None = None
    cuerpo: str | None = None
    pdf: bytes | None = None
    error: str | None = None


def procesar_certificado(
    *,
    solicitud: SolicitudCertificado,
    directorio_salida: Path,
    registro: RegistroCertificados,
    aprobacion: AprobacionHumana | None = None,
    destino: DestinoCertificados | None = None,
    emitir: bool = False,
) -> ResultadoCertificado:
    """Genera y opcionalmente emite sólo a un fake, bajo doble aprobación.

    El orden de los controles no es casual: primero los que descalifican la
    solicitud en sí (tipos, tipo de certificado del catálogo, campos
    completos), después los de autorización (aprobación válida, aprobación
    presente si se pide emitir, destino obligatoriamente fake). Recién ahí se
    toca el registro. Así una solicitud mal formada no crea ni reserva nada.

    Sin `aprobacion` el resultado máximo es `PENDIENTE_VALIDACION`: generar el
    PDF no es aprobarlo. Con `aprobacion.aprobada = False` el certificado
    queda `RECHAZADA` y ya no puede aprobarse después.
    """

    correlation_id = str(uuid.uuid4())
    log_path = directorio_salida / "logs" / "certificados-hu014.jsonl"
    idempotency_key = _idempotency_key(solicitud)

    if not _tipos_solicitud_validos(solicitud):
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="INVALIDA",
            error="input_contract_invalid",
        )
    if solicitud.tipo_certificado not in TIPOS_CERTIFICADO:
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="INVALIDA",
            error="certificate_type_invalid",
        )
    if not _campos_completos(solicitud):
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="INCOMPLETA",
            error="required_fields_missing",
        )
    if aprobacion is not None and not _aprobacion_valida(aprobacion):
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="INVALIDA",
            error="approval_invalid",
        )
    # Control central de la HU: todo pedido de emisión que pueda terminar en
    # una emisión exige el fake explícito. Se compara el tipo exacto y no con
    # isinstance, para que una subclase que sí emita no pueda pasar por acá.
    # Es el candado que permite tener el ciclo de vida completo implementado
    # sin capacidad real de emisión. Una decisión de rechazo no emite nunca,
    # así que no exige destino.
    if (
        emitir
        and (aprobacion is None or aprobacion.aprobada)
        and type(destino) is not DestinoCertificadosFake
    ):
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="INVALIDA",
            error="offline_destination_required",
        )

    existente = registro.obtener(idempotency_key)

    if aprobacion is None:
        if emitir:
            # Emisión sin decisión nueva: la autoriza el estado APROBADA, que
            # sólo se alcanza con las dos aprobaciones registradas. Un pedido
            # de emisión sin registro o sobre uno todavía en validación es
            # inválido y no crea ni mueve nada; sobre un registro que ya pasó
            # de ese punto —emitido, fallido, rechazado, indeterminado— es un
            # reintento y se responde como duplicado.
            if existente is None or existente.estado in (
                {"PENDIENTE_VALIDACION"} | ESTADOS_PARCIALES_APROBACION
            ):
                return _resultado(
                    log_path=log_path,
                    solicitud=solicitud,
                    correlation_id=correlation_id,
                    idempotency_key=idempotency_key,
                    estado="INVALIDA",
                    error="approval_required",
                )
            if existente.estado != "APROBADA":
                return _duplicada(
                    log_path, solicitud, correlation_id, idempotency_key
                )
            return _emitir(
                registro=registro,
                log_path=log_path,
                solicitud=solicitud,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
                destino=destino,
                titulo=existente.asunto,
                cuerpo=existente.cuerpo,
            )
        if existente is not None:
            return _duplicada(
                log_path, solicitud, correlation_id, idempotency_key
            )
        titulo_nuevo, cuerpo_nuevo = _renderizar(solicitud)
        if not registro.crear(idempotency_key, titulo_nuevo, cuerpo_nuevo):
            return _duplicada(
                log_path, solicitud, correlation_id, idempotency_key
            )
        return _finalizar(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="PENDIENTE_VALIDACION",
            titulo=titulo_nuevo,
            cuerpo=cuerpo_nuevo,
        )

    # A partir de acá hay una decisión humana que registrar. Si el borrador
    # todavía no existe, la decisión lo materializa primero.
    if existente is None:
        titulo_nuevo, cuerpo_nuevo = _renderizar(solicitud)
        if registro.crear(idempotency_key, titulo_nuevo, cuerpo_nuevo):
            existente = BorradorRegistrado(
                estado="PENDIENTE_VALIDACION",
                asunto=titulo_nuevo,
                cuerpo=cuerpo_nuevo,
            )
        else:
            existente = registro.obtener(idempotency_key)
    if existente is None:
        raise RuntimeError("registro de idempotencia inconsistente")
    titulo, cuerpo = existente.asunto, existente.cuerpo

    if not aprobacion.aprobada:
        if not registro.transicionar(
            idempotency_key,
            frozenset({"PENDIENTE_VALIDACION"} | ESTADOS_PARCIALES_APROBACION),
            "RECHAZADA",
        ):
            return _duplicada(
                log_path, solicitud, correlation_id, idempotency_key
            )
        return _finalizar(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="RECHAZADA",
            titulo=titulo,
            cuerpo=cuerpo,
            aprobacion=aprobacion,
        )

    # Cada rol deja su propio estado parcial; la aprobación del otro rol es la
    # única que completa el circuito. Dos compare-and-set en cadena cierran la
    # carrera entre aprobaciones simultáneas de roles distintos.
    parcial_propia, parcial_ajena = _PARCIAL_POR_ROL[aprobacion.rol]
    if registro.transicionar(
        idempotency_key, frozenset({"PENDIENTE_VALIDACION"}), parcial_propia
    ):
        estado_actual = parcial_propia
    elif registro.transicionar(
        idempotency_key, frozenset({parcial_ajena}), "APROBADA"
    ):
        estado_actual = "APROBADA"
    else:
        return _duplicada(log_path, solicitud, correlation_id, idempotency_key)

    if not emitir or estado_actual != "APROBADA":
        # Si se pidió emitir pero falta la otra aprobación, el estado devuelto
        # lo dice explícitamente: la decisión quedó registrada y no se emitió.
        return _finalizar(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado=estado_actual,
            titulo=titulo,
            cuerpo=cuerpo,
            aprobacion=aprobacion,
        )

    return _emitir(
        registro=registro,
        log_path=log_path,
        solicitud=solicitud,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        destino=destino,
        titulo=titulo,
        cuerpo=cuerpo,
        aprobacion=aprobacion,
    )


def _emitir(
    *,
    registro: RegistroCertificados,
    log_path: Path,
    solicitud: SolicitudCertificado,
    correlation_id: str,
    idempotency_key: str,
    destino: DestinoCertificados,
    titulo: str,
    cuerpo: str,
    aprobacion: AprobacionHumana | None = None,
) -> ResultadoCertificado:
    """Reserva la emisión antes de intentarla, desde `APROBADA` solamente.

    Si el proceso muere en la emisión, el registro queda en
    EMISION_RESERVADA y un reintento no vuelve a emitir, porque ya no está en
    APROBADA. Se prefiere un certificado no emitido a uno emitido dos veces.
    El PDF que sale del pipeline ya no lleva la marca de borrador: la marca
    existe hasta la aprobación completa, y emitir exige las dos.
    """

    if not registro.transicionar(
        idempotency_key,
        frozenset({"APROBADA"}),
        "EMISION_RESERVADA",
    ):
        return _duplicada(log_path, solicitud, correlation_id, idempotency_key)
    assert type(destino) is DestinoCertificadosFake
    pdf = generar_pdf_certificado(cuerpo, borrador=False)
    try:
        destino.emitir(
            idempotency_key=idempotency_key,
            titulo=titulo,
            pdf=pdf,
        )
    except Exception:
        registro.transicionar(
            idempotency_key, frozenset({"EMISION_RESERVADA"}), "FALLIDA"
        )
        return _resultado(
            log_path=log_path,
            solicitud=solicitud,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            estado="FALLIDA",
            error="fake_emission_failed",
            titulo=titulo,
            cuerpo=cuerpo,
            aprobacion=aprobacion,
        )
    registro.transicionar(
        idempotency_key, frozenset({"EMISION_RESERVADA"}), "EMITIDA_SIMULADA"
    )
    return _finalizar(
        log_path=log_path,
        solicitud=solicitud,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        estado="EMITIDA_SIMULADA",
        titulo=titulo,
        cuerpo=cuerpo,
        pdf=pdf,
        aprobacion=aprobacion,
    )


def _duplicada(
    log_path: Path,
    solicitud: SolicitudCertificado,
    correlation_id: str,
    idempotency_key: str,
) -> ResultadoCertificado:
    return _resultado(
        log_path=log_path,
        solicitud=solicitud,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        estado="DUPLICADA",
        error="idempotency_duplicate",
    )


def _finalizar(
    *,
    log_path: Path,
    solicitud: SolicitudCertificado,
    correlation_id: str,
    idempotency_key: str,
    estado: str,
    titulo: str,
    cuerpo: str,
    aprobacion: AprobacionHumana | None = None,
    pdf: bytes | None = None,
) -> ResultadoCertificado:
    # Todo estado que conserva el borrador devuelve su PDF con marca: la marca
    # es lo que lo inhabilita como documento hasta la aprobación completa.
    return _resultado(
        log_path=log_path,
        solicitud=solicitud,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        estado=estado,
        error=None,
        titulo=titulo,
        cuerpo=cuerpo,
        pdf=pdf if pdf is not None else generar_pdf_certificado(cuerpo, borrador=True),
        aprobacion=aprobacion,
    )


def _renderizar(solicitud: SolicitudCertificado) -> tuple[str, str]:
    """Arma título y texto canónico desde una plantilla fija. Sin modelo.

    Un certificado es un documento administrativo: no hay nada que redactar y
    sí un riesgo concreto si un modelo altera un nombre, un documento o una
    fecha. Por eso HU-014 es puramente determinista. El texto canónico no
    lleva la marca de borrador: la marca la agrega el PDF según el estado.
    """

    encabezado, verbo = _TEXTO_POR_TIPO[solicitud.tipo_certificado]
    titulo = f"{encabezado} — {solicitud.actividad.strip()}"
    cuerpo = (
        f"{encabezado}\n\n"
        f"{solicitud.organiza.strip()} certifica que\n"
        f"{solicitud.nombre_titular.strip()} "
        f"(documento {solicitud.documento_titular.strip()})\n"
        f"{verbo} la actividad: {solicitud.actividad.strip()}.\n"
        f"Fecha: {solicitud.fecha.strip()}\n"
        f"Referencia: {solicitud.id_certificado.strip()}\n"
        f"Firma: {solicitud.firmante.strip()}\n\n"
        "Documento provisional sin firma digital ni validez institucional.\n"
    )
    return titulo, cuerpo


def generar_pdf_certificado(cuerpo: str, *, borrador: bool) -> bytes:
    """PDF mínimo y determinista con stdlib: una página A4, texto Helvetica.

    La estructura es fija (catálogo, páginas, página, fuente, contenido), los
    offsets del xref se calculan sobre los bytes emitidos y no hay timestamps
    ni IDs de documento: mismas líneas, mismos bytes. Con `borrador=True` la
    primera línea es la marca `BORRADOR — NO EMITIR`.
    """

    lineas = ([MARCADOR_BORRADOR, ""] if borrador else []) + cuerpo.splitlines()
    contenido = (
        b"BT /F1 12 Tf 72 770 Td 18 TL\n"
        + b"".join(b"(" + _escapar_texto_pdf(linea) + b") Tj T*\n" for linea in lineas)
        + b"ET"
    )
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(contenido)).encode("ascii") + b" >>\nstream\n"
        + contenido + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for numero, objeto in enumerate(objetos, start=1):
        offsets.append(len(pdf))
        pdf += f"{numero} 0 obj\n".encode("ascii") + objeto + b"\nendobj\n"
    xref = len(pdf)
    pdf += f"xref\n0 {len(objetos) + 1}\n".encode("ascii")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode("ascii")
    pdf += (
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode("ascii")
    return bytes(pdf)


def _escapar_texto_pdf(linea: str) -> bytes:
    """Escapa una línea para un string literal PDF, byte a byte.

    El texto se codifica en cp1252 (la base de WinAnsiEncoding, la que asume
    una fuente estándar): lo que no entra queda como `?` y nunca rompe el
    documento. Paréntesis y barra se escapan, y todo byte fuera del ASCII
    imprimible va como octal, así el stream es estable y no depende de la
    codificación del lector.
    """

    partes = []
    for byte in linea.encode("cp1252", errors="replace"):
        if byte in (0x28, 0x29, 0x5C):  # ( ) y barra invertida
            partes.append(b"\\" + bytes([byte]))
        elif byte < 0x20 or byte > 0x7E:
            partes.append(f"\\{byte:03o}".encode("ascii"))
        else:
            partes.append(bytes([byte]))
    return b"".join(partes)


def _campos_completos(solicitud: SolicitudCertificado) -> bool:
    if ID_RE.fullmatch(solicitud.id_certificado) is None:
        return False
    return all(
        isinstance(getattr(solicitud, campo), str)
        and bool(getattr(solicitud, campo).strip())
        for campo in REQUIRED_FIELDS
    )


def _tipos_solicitud_validos(solicitud: SolicitudCertificado) -> bool:
    return all(isinstance(valor, str) for valor in asdict(solicitud).values())


def _idempotency_key(solicitud: SolicitudCertificado) -> str:
    """Deriva la clave del contenido completo de la solicitud.

    Al incluir todos los campos, cambiar cualquier dato —el titular, la
    actividad— produce una clave distinta y por lo tanto un certificado
    nuevo, que es lo correcto: es otro documento. Reemitir exactamente la
    misma solicitud, en cambio, choca contra la clave existente.
    """

    canonico = json.dumps(
        {"contract": CONTRACT_VERSION, **asdict(solicitud)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda valor: f"<invalid:{type(valor).__name__}>",
    )
    return _hash(canonico)


def _resultado(
    *,
    log_path: Path,
    solicitud: SolicitudCertificado,
    correlation_id: str,
    idempotency_key: str,
    estado: str,
    error: str | None,
    titulo: str | None = None,
    cuerpo: str | None = None,
    pdf: bytes | None = None,
    aprobacion: AprobacionHumana | None = None,
) -> ResultadoCertificado:
    entrada = json.dumps(
        asdict(solicitud),
        ensure_ascii=False,
        sort_keys=True,
        default=lambda valor: f"<invalid:{type(valor).__name__}>",
    )
    # La línea de auditoría no lleva nombre, documento ni texto del
    # certificado: sólo hashes. `holder_hash` permite verificar después que se
    # emitió a la persona correcta sin guardar el dato personal en un segundo
    # lugar, y `pdf_hash` es el rastro del artefacto, emitido o borrador.
    auditoria = {
        "hu": HU,
        "contract_version": CONTRACT_VERSION,
        "template_version": TEMPLATE_VERSION,
        "policy_status": POLICY_STATUS,
        "correlation_id": correlation_id,
        "idempotency_key": idempotency_key,
        "estado": estado,
        "resultado": error or "ok",
        "certificate_type": solicitud.tipo_certificado
        if isinstance(solicitud.tipo_certificado, str)
        else None,
        "input_hash": _hash(entrada),
        "holder_hash": _hash(
            f"{solicitud.nombre_titular}|{solicitud.documento_titular}"
        ),
        "output_hash": _hash((titulo or "") + "\n" + (cuerpo or "")),
        "pdf_hash": hashlib.sha256(pdf).hexdigest() if pdf is not None else None,
        "human_decision_present": aprobacion is not None,
        "human_decision_hash": _hash(
            json.dumps(asdict(aprobacion), ensure_ascii=False, sort_keys=True)
        )
        if aprobacion is not None
        else None,
        # El rol queda en claro para poder evidenciar que las dos aprobaciones
        # vinieron de roles distintos; no es un dato personal.
        "approval_role": aprobacion.rol if aprobacion is not None else None,
        "emission_mode": "fake" if estado == "EMITIDA_SIMULADA" else "none",
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(auditoria, ensure_ascii=False, sort_keys=True) + "\n")
    return ResultadoCertificado(
        estado=estado,
        idempotency_key=idempotency_key,
        log_path=log_path,
        correlation_id=correlation_id,
        titulo=titulo,
        cuerpo=cuerpo,
        pdf=pdf,
        error=error,
    )
