"""HU-014/#75: emisión en vivo del lote de cierre, con decisiones y Gmail.

Cubre el circuito entero de `certificados_emision.py` sin red y sin datos
personales reales: parseo estricto de la lista de cierre, la compuerta de
la línea descriptiva (#74), la aprobación del lote atada al hash por el
Form de decisiones (#72), la entrega por `gmail.send` con lista de prueba
(#40), la marca de prueba de cada PDF y la retención mínima posterior.
"""

import base64
import json
from email import policy as email_policy
from email.parser import BytesParser
from pathlib import Path

import pytest

from agente1.certificados_emision import (
    ListaCierreError,
    hash_lista_cierre,
    objeto_lote_cierre,
    parsear_lista_cierre,
    procesar_emision_certificados,
    revisar_aprobacion_lote,
)
from agente1.confirmaciones import (
    ROL_APROBACION_SEMANTICA,
    ROL_APROBACION_UTILITARIA,
    _hash,
)
from agente1.decisiones_form import (
    EnlacesDecisiones,
    RegistroDecisiones,
    ResultadoDecision,
)
from agente1.fuentes import CsvFuenteSolicitudes
from agente1.gmail_envio import GmailDestinoConfirmaciones
from agente1.google_workspace import (
    GoogleSheetsLectorValores,
    RespuestaHttp,
)
from agente1.linea_descriptiva import (
    linea_descriptiva_aprobada,
    objeto_id_linea_descriptiva,
)

ROOT = Path(__file__).parents[1]

CORREO_CARGADOR = "aux.cursos@example.test"
CORREO_APROBADOR = "coordinador@example.test"
CORREO_RGC = "rgc@example.test"
CORREO_OTRO = "otro.coordinador@example.test"

LINEA = (
    "El certificado acredita la participación según la condición declarada "
    "por el docente a cargo de la actividad."
)
LINEA_OTRA = "Una línea descriptiva distinta, que no es la aprobada."

ENCABEZADO_LISTA = ["nombre", "apellido", "dni", "mail", "tratamiento", "condicion"]

PERSONAS = [
    ["Ana", "Pérez", "30123456", "ana.perez@example.test", "Sra.", "asistencia"],
    ["Bruno", "Sosa", "30222333", "bruno.sosa@example.test", "Sr.", "aprobacion"],
    ["Carla", "Ruiz", "30444555", "carla.ruiz@example.test", "Srta.", "asistencia"],
]

MAILS_PERMITIDOS = frozenset(
    {CORREO_APROBADOR, CORREO_CARGADOR}
    | {fila[3] for fila in PERSONAS}
)

ACTIVIDAD_ID = "SYN-014"
ACTIVIDAD_CSV = (
    "id_actividad,titulo,descripcion,fecha_inicio,fecha_fin,modalidad,"
    "duracion_horas,organiza\n"
    f"{ACTIVIDAD_ID},NotebookLM Nivel 2,Taller de capacitación docente,"
    "2026-09-10,2026-09-11,híbrida,12,Secretaría de Extensión Universitaria\n"
)


class _LectorStub:
    """Lector de lista en memoria: mismas filas que devolvería la Sheet."""

    def __init__(self, filas: list[list[str]] | Exception) -> None:
        self._filas = filas

    def leer_valores(self) -> list[object]:
        if isinstance(self._filas, Exception):
            raise self._filas
        return list(self._filas)


class TokenFijo:
    def __init__(self, token: str = "TOKEN_GMAIL_SECRETO") -> None:
        self.token = token
        self.invocaciones = 0

    def obtener_access_token(self) -> str:
        self.invocaciones += 1
        return self.token


class TransporteSecuencia:
    def __init__(self, respuestas: list[RespuestaHttp | Exception]) -> None:
        self.respuestas = list(respuestas)
        self.solicitudes: list[dict[str, object]] = []

    def request(self, **kwargs) -> RespuestaHttp:
        self.solicitudes.append(kwargs)
        respuesta = self.respuestas[len(self.solicitudes) - 1]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


class TransporteSoloSheet:
    """Transporte fake que sólo sirve `values.get` de Sheets."""

    def __init__(self, values: list[list[object]]) -> None:
        self.values = values
        self.solicitudes: list[dict[str, object]] = []

    def request(self, *, host: str, **kwargs) -> RespuestaHttp:
        self.solicitudes.append({"host": host})
        assert host == "sheets.googleapis.com"
        return RespuestaHttp(
            200, json.dumps({"values": self.values}).encode("utf-8")
        )


def _ok_envio(n: int) -> list[RespuestaHttp]:
    return [
        RespuestaHttp(200, json.dumps({"id": f"msg-{i}"}).encode("utf-8"))
        for i in range(n)
    ]


def _destino(
    respuestas: list[RespuestaHttp | Exception],
    permitidos=frozenset(MAILS_PERMITIDOS),
) -> tuple[GmailDestinoConfirmaciones, TransporteSecuencia, TokenFijo]:
    transporte = TransporteSecuencia(respuestas)
    tokens = TokenFijo()
    destino = GmailDestinoConfirmaciones(
        destinatarios_permitidos=permitidos,
        token_provider=tokens,
        transport=transporte,
        timeout_s=5,
    )
    return destino, transporte, tokens


def _fuente(tmp_path: Path) -> CsvFuenteSolicitudes:
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(ACTIVIDAD_CSV, encoding="utf-8")
    return CsvFuenteSolicitudes(csv_path)


def _registro(tmp_path: Path) -> RegistroDecisiones:
    return RegistroDecisiones(tmp_path / "estado-decisiones")


def _enlazador(registro: RegistroDecisiones) -> EnlacesDecisiones:
    return EnlacesDecisiones(
        registro=registro,
        form_id="form1decisiones",
        entry_tipo="entry.111",
        entry_objeto="entry.222",
        entry_decision="entry.333",
    )


def _decision(
    *,
    correo: str,
    rol: str,
    tipo: str,
    objeto: str,
    decision: str,
    marca: str = "2026-10-11 09:00:00",
    resultado: str = "registrada",
) -> ResultadoDecision:
    return ResultadoDecision(
        id_respuesta=_hash(f"{correo}|{tipo}|{objeto}|{decision}|{marca}"),
        correo_hash=_hash(correo.lower().strip()),
        rol=rol,
        rol_origen=rol,
        tipo=tipo,
        objeto_id=objeto,
        decision=decision,
        resultado=resultado,
        rechazo_codigo=None,
        marca_temporal_form=marca,
        timestamp="2026-10-11T09:00:01+00:00",
    )


def _aprobar_linea(
    registro: RegistroDecisiones, *, id_actividad: str, texto_linea: str
) -> None:
    """Las dos decisiones de la línea descriptiva, tal como las deja #74."""

    objeto = objeto_id_linea_descriptiva(id_actividad, texto_linea)
    registro.registrar(
        _decision(
            correo=CORREO_RGC,
            rol=ROL_APROBACION_SEMANTICA,
            tipo="linea_descriptiva",
            objeto=objeto,
            decision="apruebo_semantica",
            marca="2026-10-11 08:00:00",
        )
    )
    registro.registrar(
        _decision(
            correo=CORREO_APROBADOR,
            rol=ROL_APROBACION_UTILITARIA,
            tipo="linea_descriptiva",
            objeto=objeto,
            decision="apruebo_utilitaria",
            marca="2026-10-11 08:05:00",
        )
    )


def _aprobar_lote(
    registro: RegistroDecisiones,
    *,
    objeto_lote: str,
    correo: str = CORREO_APROBADOR,
    rol: str = ROL_APROBACION_UTILITARIA,
) -> None:
    registro.registrar(
        _decision(
            correo=correo,
            rol=rol,
            tipo="lote",
            objeto=objeto_lote,
            decision="apruebo_lote",
        )
    )


def _ejecutar(
    tmp_path: Path,
    *,
    filas: list[list[str]] | None = None,
    linea: str | None = LINEA,
    respuestas: list[RespuestaHttp | Exception] | None = None,
    registro: RegistroDecisiones | None = None,
    solicitante_correo: str = CORREO_CARGADOR,
    lector=None,
    destino=None,
):
    """Corre `procesar_emision_certificados` con todo fake e inyectable."""

    registro = registro or _registro(tmp_path)
    transporte = None
    tokens = None
    if destino is None:
        destino, transporte, tokens = _destino(
            respuestas if respuestas is not None else _ok_envio(10)
        )
    resultado = procesar_emision_certificados(
        id_actividad=ACTIVIDAD_ID,
        fuente=_fuente(tmp_path),
        lector_lista=lector or _LectorStub([ENCABEZADO_LISTA] + (filas or PERSONAS)),
        linea_descriptiva=linea,
        registro_decisiones=registro,
        enlaces=_enlazador(registro),
        destino=destino,
        correo_aprobador=CORREO_APROBADOR,
        solicitante_correo=solicitante_correo,
        directorio_salida=tmp_path / "salida",
    )
    return resultado, registro, transporte, tokens


def _mime_de(solicitud: dict[str, object]):
    body = json.loads(solicitud["body"].decode("utf-8"))
    raw = base64.urlsafe_b64decode(body["raw"])
    return BytesParser(policy=email_policy.default).parsebytes(raw)


def _adjunto_pdf_de(mensaje) -> bytes:
    for parte in mensaje.iter_parts():
        if parte.get_content_type() == "application/pdf":
            return parte.get_payload(decode=True)
    raise AssertionError("el correo no lleva adjunto PDF")


def _leer_log(resultado) -> list[dict[str, object]]:
    path = Path(resultado.log_path)
    return [
        json.loads(linea)
        for linea in path.read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]


# --- Lista de cierre: parseo estricto ----------------------------------------


def test_lista_valida_con_las_dos_condiciones():
    personas = parsear_lista_cierre([ENCABEZADO_LISTA] + PERSONAS)
    assert len(personas) == 3
    assert {p.condicion for p in personas} == {"asistencia", "aprobacion"}
    assert personas[0].tratamiento == "Sra."


def test_lista_sin_encabezado_tambien_parsea():
    assert len(parsear_lista_cierre(list(PERSONAS))) == 3


def test_condicion_vacia_bloquea_el_lote():
    fila = list(PERSONAS[0])
    fila[5] = ""
    with pytest.raises(ListaCierreError, match="lista_cierre_condicion_vacia"):
        parsear_lista_cierre([fila])


def test_condicion_invalida_bloquea_el_lote():
    fila = list(PERSONAS[0])
    fila[5] = "presente"
    with pytest.raises(
        ListaCierreError, match="lista_cierre_condicion_invalida"
    ):
        parsear_lista_cierre([fila])
    # Ni mayúsculas ni inferencias: el agente no interpreta la condición.
    fila[5] = "Asistencia"
    with pytest.raises(
        ListaCierreError, match="lista_cierre_condicion_invalida"
    ):
        parsear_lista_cierre([fila])


def test_fila_incompleta_bloquea_el_lote():
    fila = list(PERSONAS[0])
    fila[4] = ""  # tratamiento vacío
    with pytest.raises(ListaCierreError, match="lista_cierre_fila_invalida"):
        parsear_lista_cierre([fila])
    with pytest.raises(ListaCierreError, match="lista_cierre_fila_invalida"):
        parsear_lista_cierre([["Ana", "Pérez"]])


def test_mail_invalido_bloquea_el_lote():
    fila = list(PERSONAS[0])
    fila[3] = "no-es-correo"
    with pytest.raises(ListaCierreError, match="lista_cierre_fila_invalida"):
        parsear_lista_cierre([fila])


def test_duplicado_bloquea_el_lote():
    with pytest.raises(ListaCierreError, match="lista_cierre_duplicada"):
        parsear_lista_cierre([PERSONAS[0], list(PERSONAS[0])])
    otro = list(PERSONAS[0])
    otro[2] = "30999000"  # mismo mail, otro dni
    with pytest.raises(ListaCierreError, match="lista_cierre_duplicada"):
        parsear_lista_cierre([PERSONAS[0], otro])


def test_lista_vacia_bloquea():
    with pytest.raises(ListaCierreError, match="lista_cierre_vacia"):
        parsear_lista_cierre([ENCABEZADO_LISTA])


def test_hash_lista_cambia_con_cualquier_edicion():
    personas = parsear_lista_cierre(list(PERSONAS))
    editada = parsear_lista_cierre(
        [PERSONAS[0], PERSONAS[1], PERSONAS[2][:5] + ["aprobacion"]]
    )
    assert hash_lista_cierre(personas) != hash_lista_cierre(editada)


# --- Compuerta de la línea descriptiva ----------------------------------------


def test_sin_linea_no_se_emite_nada(tmp_path: Path):
    resultado, _, transporte, _ = _ejecutar(tmp_path, linea=None)
    assert resultado.estado == "PENDIENTE_APROBACION"
    assert resultado.error == "linea_descriptiva_ausente"
    assert transporte is None or transporte.solicitudes == []


def test_linea_no_aprobada_no_se_emite(tmp_path: Path):
    resultado, _, transporte, _ = _ejecutar(tmp_path)
    assert resultado.estado == "PENDIENTE_APROBACION"
    assert resultado.error == "linea_descriptiva_no_aprobada"
    assert transporte.solicitudes == []


def test_linea_con_otro_hash_no_habilita(tmp_path: Path):
    registro = _registro(tmp_path)
    _aprobar_linea(registro, id_actividad=ACTIVIDAD_ID, texto_linea=LINEA_OTRA)
    resultado, _, transporte, _ = _ejecutar(tmp_path, registro=registro)
    assert resultado.estado == "PENDIENTE_APROBACION"
    assert resultado.error == "linea_descriptiva_no_aprobada"
    assert transporte.solicitudes == []


def test_decisiones_bajo_tipo_plantilla_no_aprueban_la_linea(
    tmp_path: Path,
):
    """`apruebo_semantica`/`apruebo_utilitaria` registradas como `plantilla`
    sobre el objeto de línea no habilitan: el tipo de decisión aísla los
    circuitos. La aprobación válida es `linea_descriptiva` (#74)."""

    registro = _registro(tmp_path)
    objeto = objeto_id_linea_descriptiva(ACTIVIDAD_ID, LINEA)
    registro.registrar(
        _decision(
            correo=CORREO_RGC,
            rol=ROL_APROBACION_SEMANTICA,
            tipo="plantilla",
            objeto=objeto,
            decision="apruebo_semantica",
        )
    )
    registro.registrar(
        _decision(
            correo=CORREO_APROBADOR,
            rol=ROL_APROBACION_UTILITARIA,
            tipo="plantilla",
            objeto=objeto,
            decision="apruebo_utilitaria",
            marca="2026-10-11 08:05:00",
        )
    )
    assert not linea_descriptiva_aprobada(
        registro, id_actividad=ACTIVIDAD_ID, linea=LINEA
    )


# --- Compuerta del lote -------------------------------------------------------


def test_lote_sin_aprobar_pide_aprobacion_con_muestra(tmp_path: Path):
    registro = _registro(tmp_path)
    _aprobar_linea(registro, id_actividad=ACTIVIDAD_ID, texto_linea=LINEA)
    resultado, registro, transporte, _ = _ejecutar(
        tmp_path, registro=registro, respuestas=_ok_envio(1)
    )

    assert resultado.estado == "PENDIENTE_APROBACION"
    assert resultado.error == "lote_no_aprobado"
    # El objeto quedó declarado pendiente para que el Form lo acepte.
    hash_lista = hash_lista_cierre(parsear_lista_cierre(PERSONAS))
    objeto_lote = objeto_lote_cierre(ACTIVIDAD_ID, hash_lista)
    assert any(
        p["tipo"] == "lote" and p["objeto_id"] == objeto_lote
        for p in registro.pendientes()
    )
    # Un solo correo: el de aprobación, al correo del rol utilitario.
    assert len(transporte.solicitudes) == 1
    mensaje = _mime_de(transporte.solicitudes[0])
    assert mensaje["To"] == CORREO_APROBADOR
    pdf = _adjunto_pdf_de(mensaje)
    assert pdf.startswith(b"%PDF")
    # La muestra lleva las dos marcas: borrador y documento de prueba.
    assert b"BORRADOR" in pdf
    assert b"DOCUMENTO DE PRUEBA" in pdf
    cuerpo = mensaje.get_body(("plain",)).get_content()
    assert "apruebo_lote" in cuerpo
    assert objeto_lote in cuerpo
    assert "form1decisiones" in cuerpo


def test_lista_editada_despues_de_aprobar_no_habilita(tmp_path: Path):
    """La aprobación quedó atada al hash viejo: la lista nueva es otro lote."""

    registro = _registro(tmp_path)
    _aprobar_linea(registro, id_actividad=ACTIVIDAD_ID, texto_linea=LINEA)
    hash_viejo = hash_lista_cierre(parsear_lista_cierre(PERSONAS))
    _aprobar_lote(registro, objeto_lote=objeto_lote_cierre(ACTIVIDAD_ID, hash_viejo))

    filas_nuevas = PERSONAS + [
        ["Dora", "Luna", "30555666", "dora.luna@example.test", "Sra.", "asistencia"]
    ]
    resultado, _, transporte, _ = _ejecutar(
        tmp_path,
        filas=filas_nuevas,
        registro=registro,
        respuestas=_ok_envio(1),
    )
    assert resultado.estado == "PENDIENTE_APROBACION"
    assert resultado.error == "lote_no_aprobado"
    # Se declaró el pendiente del objeto nuevo, distinto del aprobado.
    hash_nuevo = hash_lista_cierre(parsear_lista_cierre(filas_nuevas))
    assert objeto_lote_cierre(ACTIVIDAD_ID, hash_nuevo) != objeto_lote_cierre(
        ACTIVIDAD_ID, hash_viejo
    )


def test_aprobacion_con_rol_equivocado_no_habilita(tmp_path: Path):
    registro = _registro(tmp_path)
    _aprobar_linea(registro, id_actividad=ACTIVIDAD_ID, texto_linea=LINEA)
    hash_lista = hash_lista_cierre(parsear_lista_cierre(PERSONAS))
    objeto = objeto_lote_cierre(ACTIVIDAD_ID, hash_lista)
    _aprobar_lote(registro, objeto_lote=objeto, rol=ROL_APROBACION_SEMANTICA)

    revision = revisar_aprobacion_lote(
        registro, objeto_lote=objeto, cargada_por_correo_hash=_hash(CORREO_CARGADOR)
    )
    assert not revision.aprobada
    assert "aprobador_rol_no_utilitario" in revision.descalificaciones

    resultado, _, transporte, _ = _ejecutar(
        tmp_path, registro=registro, respuestas=_ok_envio(1)
    )
    assert resultado.estado == "PENDIENTE_APROBACION"
    assert resultado.error == "lote_no_aprobado"


def test_aprobacion_del_cargador_no_habilita(tmp_path: Path):
    """El que cargó la lista no puede aprobarla: su decisión no cuenta."""

    registro = _registro(tmp_path)
    _aprobar_linea(registro, id_actividad=ACTIVIDAD_ID, texto_linea=LINEA)
    hash_lista = hash_lista_cierre(parsear_lista_cierre(PERSONAS))
    objeto = objeto_lote_cierre(ACTIVIDAD_ID, hash_lista)
    _aprobar_lote(registro, objeto_lote=objeto, correo=CORREO_CARGADOR)

    revision = revisar_aprobacion_lote(
        registro, objeto_lote=objeto, cargada_por_correo_hash=_hash(CORREO_CARGADOR)
    )
    assert not revision.aprobada
    assert "aprobador_es_cargador" in revision.descalificaciones

    resultado, _, transporte, _ = _ejecutar(
        tmp_path, registro=registro, respuestas=_ok_envio(1)
    )
    assert resultado.estado == "PENDIENTE_APROBACION"
    assert resultado.error == "lote_no_aprobado"


def test_aprobador_distinto_del_cargador_si_habilita(tmp_path: Path):
    registro = _registro(tmp_path)
    _aprobar_linea(registro, id_actividad=ACTIVIDAD_ID, texto_linea=LINEA)
    hash_lista = hash_lista_cierre(parsear_lista_cierre(PERSONAS))
    objeto = objeto_lote_cierre(ACTIVIDAD_ID, hash_lista)
    _aprobar_lote(registro, objeto_lote=objeto, correo=CORREO_OTRO)

    revision = revisar_aprobacion_lote(
        registro, objeto_lote=objeto, cargada_por_correo_hash=_hash(CORREO_CARGADOR)
    )
    assert revision.aprobada
    assert revision.correo_hash_aprobador == _hash(CORREO_OTRO)


# --- Emisión completa ---------------------------------------------------------


def _registro_listo(tmp_path: Path) -> RegistroDecisiones:
    registro = _registro(tmp_path)
    _aprobar_linea(registro, id_actividad=ACTIVIDAD_ID, texto_linea=LINEA)
    hash_lista = hash_lista_cierre(parsear_lista_cierre(PERSONAS))
    _aprobar_lote(
        registro, objeto_lote=objeto_lote_cierre(ACTIVIDAD_ID, hash_lista)
    )
    return registro


def test_emision_completa_entrega_un_pdf_por_titular(tmp_path: Path):
    registro = _registro_listo(tmp_path)
    resultado, _, transporte, tokens = _ejecutar(
        tmp_path, registro=registro, respuestas=_ok_envio(3)
    )

    assert resultado.estado == "EMITIDA"
    assert resultado.emitidas == 3
    assert len(transporte.solicitudes) == 3
    destinatarios = []
    for solicitud in transporte.solicitudes:
        mensaje = _mime_de(solicitud)
        destinatarios.append(mensaje["To"])
        pdf = _adjunto_pdf_de(mensaje)
        assert pdf.startswith(b"%PDF")
        # Marca de prueba permanente, sin marca de borrador en el emitido.
        assert b"DOCUMENTO DE PRUEBA" in pdf
        assert b"BORRADOR" not in pdf
        # El titular y la actividad están en el PDF, con las dos firmas.
        assert b"CERTIFICADO DE" in pdf
        assert b"Moreira" in pdf or b"Sebasti" in pdf
    assert sorted(destinatarios) == sorted(fila[3] for fila in PERSONAS)
    # El token se pidió una vez por correo, siempre después de validar.
    assert tokens.invocaciones == 3


def test_condiciones_se_renderizan_distinto(tmp_path: Path):
    registro = _registro_listo(tmp_path)
    resultado, _, transporte, _ = _ejecutar(
        tmp_path, registro=registro, respuestas=_ok_envio(3)
    )
    assert resultado.estado == "EMITIDA"
    textos = []
    for solicitud in transporte.solicitudes:
        pdf = _adjunto_pdf_de(_mime_de(solicitud))
        textos.append(pdf)
    assert any(b"CERTIFICADO DE APROBACI" in pdf for pdf in textos)
    assert any(b"CERTIFICADO DE ASISTENCIA" in pdf for pdf in textos)


def test_emision_desde_lista_leida_por_sheet(tmp_path: Path):
    """El lector real de `values.get` alimenta el mismo circuito."""

    transporte_sheet = TransporteSoloSheet([ENCABEZADO_LISTA] + PERSONAS)
    lector = GoogleSheetsLectorValores(
        spreadsheet_id="sheet_lista-7",
        rango_a1="'Lista de cierre'!A1:F50",
        token_provider=TokenFijo(),
        transport=transporte_sheet,
        timeout_s=5,
    )
    registro = _registro_listo(tmp_path)
    resultado, _, transporte, _ = _ejecutar(
        tmp_path, registro=registro, lector=lector, respuestas=_ok_envio(3)
    )
    assert resultado.estado == "EMITIDA"
    assert transporte_sheet.solicitudes == [{"host": "sheets.googleapis.com"}]


def test_mail_fuera_de_la_lista_falla_sin_reintento(tmp_path: Path):
    """Un titular fuera de la lista de prueba: su entrega falla antes de la
    red, no se reintenta y el resto del lote sale igual."""

    filas = PERSONAS + [
        ["Eva", "Nadir", "30777888", "eva.nadir@example.test", "Sra.", "aprobacion"]
    ]
    registro = _registro(tmp_path)
    _aprobar_linea(registro, id_actividad=ACTIVIDAD_ID, texto_linea=LINEA)
    hash_lista = hash_lista_cierre(parsear_lista_cierre(filas))
    _aprobar_lote(
        registro, objeto_lote=objeto_lote_cierre(ACTIVIDAD_ID, hash_lista)
    )
    resultado, _, transporte, _ = _ejecutar(
        tmp_path, filas=filas, registro=registro, respuestas=_ok_envio(4)
    )

    assert resultado.estado == "EMITIDA_PARCIAL"
    assert resultado.emitidas == 3
    assert resultado.entregas_fallidas == 1
    # Sólo 3 requests: el cuarto rechazó antes de la red, sin reintento.
    assert len(transporte.solicitudes) == 3
    entregas = [
        e for e in _leer_log(resultado) if e["evento"] == "entrega"
    ]
    assert len(entregas) == 4
    fallida = [e for e in entregas if e["resultado"] == "fallida"]
    assert len(fallida) == 1
    assert fallida[0]["code"] == "recipient_off_test_list"


def test_lista_invalida_no_emite_ni_pide_aprobacion(tmp_path: Path):
    filas = PERSONAS + [["Zoe", "Mía", "30999000", "zoe@example.test", "Sra.", ""]]
    registro = _registro_listo(tmp_path)
    resultado, _, transporte, _ = _ejecutar(
        tmp_path, filas=filas, registro=registro
    )
    assert resultado.estado == "INVALIDA"
    assert resultado.error == "lista_cierre_condicion_vacia"
    assert transporte.solicitudes == []
    eventos = [e["evento"] for e in _leer_log(resultado)]
    assert "lista_invalida" in eventos
    assert "entrega" not in eventos


def test_auditoria_no_lleva_datos_personales(tmp_path: Path):
    registro = _registro_listo(tmp_path)
    resultado, _, _, _ = _ejecutar(
        tmp_path, registro=registro, respuestas=_ok_envio(3)
    )
    assert resultado.estado == "EMITIDA"
    contenido_log = Path(resultado.log_path).read_text(encoding="utf-8")
    for fila in PERSONAS:
        nombre, apellido, dni, mail = fila[0], fila[1], fila[2], fila[3]
        assert nombre not in contenido_log
        assert apellido not in contenido_log
        assert dni not in contenido_log
        assert mail not in contenido_log
        # El hash del titular sí está: permite correlacionar sin retener.
        holder = _hash(f"{nombre}|{apellido}|{dni}")
        assert holder in contenido_log


def test_despues_de_emitir_no_quedan_pdfs_ni_lista(tmp_path: Path):
    """Retención mínima: la salida no guarda PDF ni filas de la lista."""

    registro = _registro_listo(tmp_path)
    resultado, _, _, _ = _ejecutar(
        tmp_path, registro=registro, respuestas=_ok_envio(3)
    )
    assert resultado.estado == "EMITIDA"
    pdfs = list(tmp_path.rglob("*.pdf"))
    assert pdfs == []
    for archivo in tmp_path.rglob("*"):
        if not archivo.is_file():
            continue
        contenido = archivo.read_bytes()
        for fila in PERSONAS:
            assert fila[2].encode() not in contenido  # dni
            assert fila[3].encode() not in contenido  # mail


def test_reemision_es_un_pedido_nuevo(tmp_path: Path):
    """Volver a pedir la emisión no es reintento: corre el circuito otra vez
    sobre la lista vigente y vuelve a entregar."""

    registro = _registro_listo(tmp_path)
    primero, _, t1, _ = _ejecutar(tmp_path, registro=registro, respuestas=_ok_envio(3))
    segundo, _, t2, _ = _ejecutar(tmp_path, registro=registro, respuestas=_ok_envio(3))
    assert primero.estado == "EMITIDA"
    assert segundo.estado == "EMITIDA"
    assert len(t1.solicitudes) == 3
    assert len(t2.solicitudes) == 3


def test_sin_firmas_en_el_repositorio():
    """Ninguna imagen de firma entra a Git: la carpeta de firmas vive en D2."""

    imagenes = [
        p
        for p in (ROOT / "src" / "agente1").rglob("*")
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ]
    assert imagenes == []


def test_actividad_inexistente_es_invalida(tmp_path: Path):
    destino, transporte, _ = _destino(_ok_envio(1))
    resultado = procesar_emision_certificados(
        id_actividad="NO-EXISTE",
        fuente=_fuente(tmp_path),
        lector_lista=_LectorStub([ENCABEZADO_LISTA] + PERSONAS),
        linea_descriptiva=LINEA,
        registro_decisiones=_registro(tmp_path),
        enlaces=_enlazador(_registro(tmp_path)),
        destino=destino,
        correo_aprobador=CORREO_APROBADOR,
        solicitante_correo=CORREO_CARGADOR,
        directorio_salida=tmp_path / "salida",
    )
    assert resultado.estado == "INVALIDA"
    assert resultado.error == "source_request_not_found"
    assert transporte.solicitudes == []


# --- Despacho por la intención del canal (#75) --------------------------------


def test_despacho_emitir_certificados_por_el_seam(tmp_path: Path):
    """«emití los certificados de <id>» entra por el canal, clasifica y
    despacha al emisor configurado. El emisor recibe la actividad y la
    identidad del canal, como la va a recibir en el wiring real."""

    from agente1.interpretacion import (
        IdentidadSolicitante,
        interpretar_solicitud,
    )
    from agente1.procesamiento import FakeGenerator

    registro = _registro_listo(tmp_path)
    destino, transporte, _ = _destino(_ok_envio(3))

    def emisor(*, id_actividad, solicitante):
        return procesar_emision_certificados(
            id_actividad=id_actividad,
            fuente=_fuente(tmp_path),
            lector_lista=_LectorStub([ENCABEZADO_LISTA] + PERSONAS),
            linea_descriptiva=LINEA,
            registro_decisiones=registro,
            enlaces=_enlazador(registro),
            destino=destino,
            correo_aprobador=CORREO_APROBADOR,
            solicitante_correo=solicitante.identificador,
            directorio_salida=tmp_path / "salida",
        )

    resultado = interpretar_solicitud(
        texto=f"emití los certificados de {ACTIVIDAD_ID}",
        solicitante=IdentidadSolicitante(
            identificador=CORREO_CARGADOR, rol="auxiliar_seu"
        ),
        fuente=_fuente(tmp_path),
        directorio_salida=tmp_path / "seam",
        generator=FakeGenerator("{}"),
        emisor_certificados=emisor,
    )
    assert resultado.intencion == "emitir_certificados"
    assert resultado.estado == "EMITIDA"
    assert len(transporte.solicitudes) == 3
    registro_log = json.loads(
        resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
    )
    assert registro_log["resultado"] == "emision_certificados_despachada"


def test_emitir_certificados_sin_emisor_falla_controlado(tmp_path: Path):
    from agente1.interpretacion import (
        IdentidadSolicitante,
        interpretar_solicitud,
    )
    from agente1.procesamiento import FakeGenerator

    resultado = interpretar_solicitud(
        texto=f"emití los certificados de {ACTIVIDAD_ID}",
        solicitante=IdentidadSolicitante(
            identificador=CORREO_CARGADOR, rol="auxiliar_seu"
        ),
        fuente=_fuente(tmp_path),
        directorio_salida=tmp_path / "seam",
        generator=FakeGenerator("{}"),
    )
    assert resultado.intencion == "emitir_certificados"
    assert resultado.estado == "FALLIDA"
    registro_log = json.loads(
        resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
    )
    assert registro_log["resultado"] == "emisor_no_configurado"
