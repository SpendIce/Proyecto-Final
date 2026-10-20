"""Adapter `gmail.send` con lista de prueba (D11/D12, ticket #40).

Cubre la construcción cercada —sin lista no hay destino—, la validación por
entrega antes de cualquier llamada de red, el envío real contra transporte
fake, la traducción de errores HTTP a códigos y la integración con el
circuito de HU-012: el candado pasó de «sólo el fake por tipo exacto» a
«fake, o Gmail con lista activa», y una subclase, un envoltorio o cualquier
otro destino sigue rechazado. Ninguna prueba usa red.
"""

import base64
import json
from email import policy as email_policy
from email.parser import BytesParser
from pathlib import Path

import pytest

from agente1.confirmaciones import (
    ROL_APROBACION_SEMANTICA,
    ROL_APROBACION_UTILITARIA,
    AprobacionHumana,
    ColaEnviosMemoria,
    DestinoConfirmacionesFake,
    EntregaRechazadaError,
    RegistroConfirmacionesMemoria,
    SolicitudConfirmacion,
    drenar_envios,
    procesar_confirmacion,
)
from agente1.gmail_envio import (
    DESTINATARIOS_PRUEBA_ENV,
    GMAIL_HOST,
    GMAIL_SEND_TARGET,
    AdjuntoCorreo,
    GmailDestinoConfirmaciones,
    GmailEnvioError,
    cargar_destinatarios_prueba,
)
from agente1.google_workspace import (
    MAX_WORKSPACE_RESPONSE_BYTES,
    RespuestaHttp,
    _RespuestaDemasiadoGrande,
)
from agente1.workspace_config import ConfiguracionWorkspaceError

LISTA = frozenset({"ana.perez@example.test", "beto@example.test"})
CUERPO_BORRADOR = "BORRADOR — NO ENVIAR\n\nCuerpo de la confirmación.\n"


class TokenFijo:
    def __init__(self, token: str = "TOKEN_GMAIL_SECRETO") -> None:
        self.token = token
        self.invocaciones = 0

    def obtener_access_token(self) -> str:
        self.invocaciones += 1
        return self.token


class TransporteSecuencia:
    def __init__(self, respuestas: list[RespuestaHttp | Exception]) -> None:
        self.respuestas = respuestas
        self.solicitudes: list[dict[str, object]] = []

    def request(self, **kwargs) -> RespuestaHttp:
        self.solicitudes.append(kwargs)
        respuesta = self.respuestas[len(self.solicitudes) - 1]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


def crear_destino(
    respuestas: list[RespuestaHttp | Exception],
    **kwargs,
) -> tuple[GmailDestinoConfirmaciones, TransporteSecuencia, TokenFijo]:
    transporte = TransporteSecuencia(respuestas)
    tokens = TokenFijo()
    destino = GmailDestinoConfirmaciones(
        destinatarios_permitidos=kwargs.pop(
            "destinatarios_permitidos", LISTA
        ),
        token_provider=tokens,
        transport=transporte,
        **kwargs,
    )
    return destino, transporte, tokens


def mensaje_de(solicitud_transporte: dict[str, object]):
    """Decodifica el `raw` de la llamada a `gmail.send` y parsea el MIME."""

    cuerpo_http = json.loads(solicitud_transporte["body"])
    raw = base64.urlsafe_b64decode(cuerpo_http["raw"])
    return BytesParser(policy=email_policy.default).parsebytes(raw)


# --- Construcción cercada -----------------------------------------------------


@pytest.mark.parametrize(
    "lista_invalida",
    [
        [],
        (),
        set(),
        ["   "],
        ["no-es-un-email"],
        ["ana.perez@example.test", "mal@"],
        [123],
        "ana.perez@example.test",
        None,
        [f"usuario{i}@example.test" for i in range(101)],
    ],
)
def test_sin_lista_valida_no_se_construye_el_destino(lista_invalida):
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        GmailDestinoConfirmaciones(
            destinatarios_permitidos=lista_invalida,
            token_provider=TokenFijo(),
            transport=TransporteSecuencia([]),
        )
    assert error.value.code == "gmail_test_list_invalid"


@pytest.mark.parametrize("timeout", [0, -1, 121, "10", None, True])
def test_timeout_invalido_impide_construir(timeout):
    with pytest.raises(ValueError, match="Gmail"):
        GmailDestinoConfirmaciones(
            destinatarios_permitidos=LISTA,
            token_provider=TokenFijo(),
            transport=TransporteSecuencia([]),
            timeout_s=timeout,
        )


def test_la_lista_se_normaliza_a_minusculas_sin_espacios():
    destino, _, _ = crear_destino(
        [],
        destinatarios_permitidos=[" Ana.Perez@Example.TEST "],
    )
    assert destino._destinatarios_permitidos == {"ana.perez@example.test"}


def test_repr_no_expone_las_direcciones():
    destino, _, _ = crear_destino([])
    assert "ana.perez@example.test" not in repr(destino)


# --- Lista desde configuración fuera del repo ----------------------------------


def test_lista_ausente_impide_construir_desde_entorno():
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        cargar_destinatarios_prueba({})
    assert error.value.code == "gmail_test_list_missing"

    with pytest.raises(ConfiguracionWorkspaceError) as error:
        GmailDestinoConfirmaciones.desde_entorno(
            {}, token_provider=TokenFijo(), transport=TransporteSecuencia([])
        )
    assert error.value.code == "gmail_test_list_missing"


@pytest.mark.parametrize("crudo", ["", "   ", "ana.perez@", "a@b, malformado"])
def test_lista_vacia_o_invalida_impide_construir_desde_entorno(crudo):
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        cargar_destinatarios_prueba({DESTINATARIOS_PRUEBA_ENV: crudo})
    assert error.value.code in {
        "gmail_test_list_missing",
        "gmail_test_list_invalid",
    }


def test_lista_separada_por_coma_se_normaliza_y_deduplica():
    lista = cargar_destinatarios_prueba(
        {
            DESTINATARIOS_PRUEBA_ENV: (
                " Ana.Perez@example.test , beto@example.test,ANA.PEREZ@example.test"
            )
        }
    )
    assert lista == {"ana.perez@example.test", "beto@example.test"}


# --- Envío contra transporte fake ----------------------------------------------


def test_envio_real_post_a_gmail_send_con_mime_completo():
    destino, transporte, tokens = crear_destino(
        [RespuestaHttp(200, b'{"id":"18f9abc0123","threadId":"18f9abc0123"}')]
    )

    destino.entregar(
        idempotency_key="a" * 64,
        destinatario="ana.perez@example.test",
        asunto="[BORRADOR — NO ENVIAR] Confirmación de inscripción",
        cuerpo=CUERPO_BORRADOR,
    )

    assert tokens.invocaciones == 1
    assert len(transporte.solicitudes) == 1
    (llamada,) = transporte.solicitudes
    assert llamada["method"] == "POST"
    assert llamada["host"] == GMAIL_HOST == "gmail.googleapis.com"
    assert llamada["target"] == GMAIL_SEND_TARGET == (
        "/gmail/v1/users/me/messages/send"
    )
    assert llamada["headers"] == {
        "Accept": "application/json",
        "Authorization": "Bearer TOKEN_GMAIL_SECRETO",
        "Content-Type": "application/json; charset=utf-8",
    }
    assert llamada["max_response_bytes"] == MAX_WORKSPACE_RESPONSE_BYTES

    mensaje = mensaje_de(llamada)
    # El marcador de borrador viaja en el cuerpo mientras rija la lista: la
    # marca «NO PUBLICAR» de los borradores y la «NO ENVIAR» de HU-012.
    assert str(mensaje["To"]) == "ana.perez@example.test"
    assert (
        str(mensaje["Subject"])
        == "[BORRADOR — NO ENVIAR] Confirmación de inscripción"
    )
    # El valor del header se compara normalizado: Python 3.12.3 devuelve el
    # espacio de continuación del encabezado como parte del valor y 3.12.14 no.
    # Lo que importa es que la clave completa viaje, no el espacio de formato.
    assert str(mensaje["X-Agente1-Idempotency-Key"]).strip() == "a" * 64
    cuerpo = mensaje.get_content()
    assert cuerpo.startswith("# BORRADOR — NO PUBLICAR")
    assert "BORRADOR — NO ENVIAR" in cuerpo
    assert "Cuerpo de la confirmación." in cuerpo


def test_destinatario_en_lista_con_otras_mayusculas_tambien_entrega():
    destino, transporte, _ = crear_destino([RespuestaHttp(200, b'{"id":"x"}')])

    destino.entregar(
        idempotency_key="b" * 64,
        destinatario="ANA.PEREZ@example.test",
        asunto="asunto",
        cuerpo=CUERPO_BORRADOR,
    )

    assert len(transporte.solicitudes) == 1
    mensaje = mensaje_de(transporte.solicitudes[0])
    assert str(mensaje["To"]) == "ana.perez@example.test"


# --- Rechazos de política antes de cualquier llamada de red --------------------


def test_destinatario_fuera_de_la_lista_se_rechaza_antes_de_la_red():
    destino, transporte, tokens = crear_destino([])

    with pytest.raises(EntregaRechazadaError) as error:
        destino.entregar(
            idempotency_key="a" * 64,
            destinatario="intruso@example.test",
            asunto="asunto",
            cuerpo=CUERPO_BORRADOR,
        )

    assert error.value.code == "recipient_off_test_list"
    assert tokens.invocaciones == 0
    assert transporte.solicitudes == []


@pytest.mark.parametrize(
    ("asunto", "cuerpo", "codigo"),
    [
        ("asunto\nCc: otro@example.test", CUERPO_BORRADOR, "message_contract_invalid"),
        ("asunto\rnormal", CUERPO_BORRADOR, "message_contract_invalid"),
        ("", CUERPO_BORRADOR, "message_contract_invalid"),
        (None, CUERPO_BORRADOR, "message_contract_invalid"),
        ("asunto", "texto sin marca", "draft_marker_missing"),
        ("asunto", None, "message_contract_invalid"),
    ],
)
def test_contrato_del_mensaje_se_rechaza_antes_de_la_red(asunto, cuerpo, codigo):
    destino, transporte, tokens = crear_destino([])

    with pytest.raises(EntregaRechazadaError) as error:
        destino.entregar(
            idempotency_key="a" * 64,
            destinatario="ana.perez@example.test",
            asunto=asunto,
            cuerpo=cuerpo,
        )

    assert error.value.code == codigo
    assert tokens.invocaciones == 0
    assert transporte.solicitudes == []


@pytest.mark.parametrize("clave", ["no-es-hash", "A" * 64, 123])
def test_clave_que_no_es_hash_se_rechaza_antes_de_la_red(clave):
    destino, transporte, tokens = crear_destino([])

    with pytest.raises(EntregaRechazadaError) as error:
        destino.entregar(
            idempotency_key=clave,
            destinatario="ana.perez@example.test",
            asunto="asunto",
            cuerpo=CUERPO_BORRADOR,
        )

    assert error.value.code == "message_contract_invalid"
    assert tokens.invocaciones == 0
    assert transporte.solicitudes == []


# --- Errores del medio: HTTP, timeout, respuesta excesiva ----------------------


@pytest.mark.parametrize(
    ("respuesta", "codigo"),
    [
        (RespuestaHttp(400, b"secreto@example.invalid"), "gmail_request_invalid"),
        (RespuestaHttp(401, b"secreto@example.invalid"), "gmail_auth_denied"),
        (RespuestaHttp(403, b"secreto@example.invalid"), "gmail_auth_denied"),
        (RespuestaHttp(429, b"secreto@example.invalid"), "gmail_rate_limited"),
        (RespuestaHttp(500, b"secreto@example.invalid"), "gmail_unavailable"),
        (RespuestaHttp(503, b"secreto@example.invalid"), "gmail_unavailable"),
        (RespuestaHttp(200, b"no-json-secreto"), "gmail_response_invalid"),
        (RespuestaHttp(200, b"{}"), "gmail_response_invalid"),
        (RespuestaHttp(200, b'{"id":"id con espacios"}'), "gmail_response_invalid"),
        (
            RespuestaHttp(200, b"x" * (MAX_WORKSPACE_RESPONSE_BYTES + 1)),
            "gmail_response_too_large",
        ),
        (_RespuestaDemasiadoGrande(), "gmail_response_too_large"),
        (TimeoutError("timeout secreto@example.invalid"), "gmail_unavailable"),
        (OSError("TOKEN_GMAIL_SECRETO en error"), "gmail_unavailable"),
        (RuntimeError("workspace_unavailable"), "gmail_unavailable"),
    ],
)
def test_falla_del_medio_da_codigo_sin_filtrar_datos(respuesta, codigo):
    destino, transporte, _ = crear_destino([respuesta])

    with pytest.raises(GmailEnvioError) as error:
        destino.entregar(
            idempotency_key="a" * 64,
            destinatario="ana.perez@example.test",
            asunto="asunto",
            cuerpo=CUERPO_BORRADOR,
        )

    assert error.value.code == codigo
    assert len(transporte.solicitudes) == 1
    assert "secreto@example.invalid" not in str(error.value)
    assert "TOKEN_GMAIL_SECRETO" not in str(error.value)


def test_token_indisponible_o_malformado_da_auth_unavailable():
    class TokenRoto:
        def obtener_access_token(self) -> str:
            raise RuntimeError("secreto")

    for provider in (TokenRoto(), TokenFijo("con\nsalto"), TokenFijo("  ")):
        destino = GmailDestinoConfirmaciones(
            destinatarios_permitidos=LISTA,
            token_provider=provider,
            transport=TransporteSecuencia([]),
        )
        with pytest.raises(GmailEnvioError) as error:
            destino.entregar(
                idempotency_key="a" * 64,
                destinatario="ana.perez@example.test",
                asunto="asunto",
                cuerpo=CUERPO_BORRADOR,
            )
        assert error.value.code == "gmail_auth_unavailable"
        assert "secreto" not in str(error.value)


# --- Integración con el circuito de HU-012 -------------------------------------


def solicitud(**cambios: str) -> SolicitudConfirmacion:
    datos = {
        "id_inscripcion": "INS-001",
        "nombre_destinatario": "Ana Pérez",
        "email_destinatario": "ana.perez@example.test",
        "actividad": "Taller de robótica educativa",
        "fecha": "28 de agosto de 2026, 18:00",
        "lugar": "Aula 4",
        "organiza": "Secretaría de Extensión Universitaria",
        "contacto": "extension@example.test",
    }
    datos.update(cambios)
    return SolicitudConfirmacion(**datos)


def aprobacion(rol: str) -> AprobacionHumana:
    return AprobacionHumana(
        aprobada=True,
        validador="Validador SEU de prueba",
        rol=rol,
        fecha_iso="2026-10-12T18:00:00-03:00",
    )


def aprobar_ambos(tmp_path: Path, registro, solicitud_) -> None:
    procesar_confirmacion(
        solicitud=solicitud_,
        directorio_salida=tmp_path,
        registro=registro,
        aprobacion=aprobacion(ROL_APROBACION_SEMANTICA),
    )
    procesar_confirmacion(
        solicitud=solicitud_,
        directorio_salida=tmp_path,
        registro=registro,
        aprobacion=aprobacion(ROL_APROBACION_UTILITARIA),
    )


def test_gmail_con_lista_es_destino_habilitado_y_entrega(tmp_path: Path):
    registro = RegistroConfirmacionesMemoria()
    aprobar_ambos(tmp_path, registro, solicitud())
    destino, transporte, _ = crear_destino([RespuestaHttp(200, b'{"id":"m1"}')])

    resultado = procesar_confirmacion(
        solicitud=solicitud(),
        directorio_salida=tmp_path,
        registro=registro,
        destino=destino,
        enviar=True,
    )

    assert resultado.estado == "ENVIADA_SIMULADA"
    assert len(transporte.solicitudes) == 1
    ultima = json.loads(
        resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
    )
    assert ultima["delivery_mode"] == "gmail_test_list"
    assert ultima["estado"] == "ENVIADA_SIMULADA"


def test_destinatario_fuera_de_lista_queda_fallida_no_reintentable(tmp_path: Path):
    pedido = solicitud(email_destinatario="intruso@example.test")
    registro = RegistroConfirmacionesMemoria()
    aprobar_ambos(tmp_path, registro, pedido)
    destino, transporte, _ = crear_destino([])

    resultado = procesar_confirmacion(
        solicitud=pedido,
        directorio_salida=tmp_path,
        registro=registro,
        destino=destino,
        enviar=True,
    )

    assert resultado.estado == "FALLIDA"
    assert resultado.error == "recipient_off_test_list"
    assert transporte.solicitudes == []
    assert registro.obtener(resultado.idempotency_key).estado == "FALLIDA"
    # La línea de auditoría del rechazo existe y no expone el destinatario.
    lineas = resultado.log_path.read_text(encoding="utf-8").splitlines()
    assert json.loads(lineas[-1])["resultado"] == "recipient_off_test_list"
    assert "intruso@example.test" not in "\n".join(lineas)
    # FALLIDA es terminal: un nuevo pedido de envío es duplicado, no reintento.
    reintento = procesar_confirmacion(
        solicitud=pedido,
        directorio_salida=tmp_path,
        registro=registro,
        destino=destino,
        enviar=True,
    )
    assert reintento.estado == "DUPLICADA"
    assert transporte.solicitudes == []


def test_subclase_envoltorio_u_otro_destino_siguen_rechazados(tmp_path: Path):
    class GmailHijo(GmailDestinoConfirmaciones):
        pass

    class Envoltorio:
        def __init__(self, interno) -> None:
            self._interno = interno

        def entregar(self, **kwargs) -> None:
            return self._interno.entregar(**kwargs)

    class DestinoCualquiera:
        def __init__(self) -> None:
            self.invocado = False

        def entregar(self, **_) -> None:
            self.invocado = True

    gmail, transporte, _ = crear_destino([])
    destinos_rechazados = [
        GmailHijo(
            destinatarios_permitidos=LISTA,
            token_provider=TokenFijo(),
            transport=transporte,
        ),
        Envoltorio(gmail),
        DestinoCualquiera(),
        object(),
        None,
    ]
    for destino in destinos_rechazados:
        registro = RegistroConfirmacionesMemoria()
        aprobar_ambos(tmp_path, registro, solicitud())
        resultado = procesar_confirmacion(
            solicitud=solicitud(),
            directorio_salida=tmp_path,
            registro=registro,
            destino=destino,
            enviar=True,
        )
        assert resultado.estado == "INVALIDA"
        assert resultado.error == "offline_destination_required"
    assert transporte.solicitudes == []


def test_worker_tambien_rechaza_subclase_envoltorio_u_otro_destino(tmp_path: Path):
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    aprobar_ambos(tmp_path, registro, solicitud())
    encolada = procesar_confirmacion(
        solicitud=solicitud(),
        directorio_salida=tmp_path,
        registro=registro,
        asincrono=True,
        cola=cola,
    )
    assert encolada.estado == "ENVIO_ENCOLADO"

    gmail, transporte, _ = crear_destino([])

    class GmailHijo(GmailDestinoConfirmaciones):
        pass

    class Envoltorio:
        def __init__(self, interno) -> None:
            self._interno = interno

        def entregar(self, **kwargs) -> None:
            return self._interno.entregar(**kwargs)

    for destino in (
        GmailHijo(
            destinatarios_permitidos=LISTA,
            token_provider=TokenFijo(),
            transport=transporte,
        ),
        Envoltorio(gmail),
        DestinoConfirmacionesFake,
    ):
        assert (
            drenar_envios(
                registro=registro,
                cola=cola,
                destino=destino,
                directorio_salida=tmp_path / "salida",
            )
            == ()
        )
    # Ni la clase fake como objeto tipo (no instancia) habilita al worker.
    assert len(cola.pendientes()) == 1
    assert (
        registro.obtener(encolada.idempotency_key).estado == "ENVIO_ENCOLADO"
    )
    assert transporte.solicitudes == []


def test_worker_gmail_entrega_y_el_rechazo_no_reintenta(tmp_path: Path):
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    pedido = solicitud()
    aprobar_ambos(tmp_path, registro, pedido)
    procesar_confirmacion(
        solicitud=pedido,
        directorio_salida=tmp_path,
        registro=registro,
        asincrono=True,
        cola=cola,
    )

    destino, transporte, _ = crear_destino([RespuestaHttp(200, b'{"id":"m1"}')])
    (resultado,) = drenar_envios(
        registro=registro,
        cola=cola,
        destino=destino,
        directorio_salida=tmp_path / "salida",
    )
    assert resultado.resolucion == "entregada"
    assert len(transporte.solicitudes) == 1
    lineas = (
        (tmp_path / "salida" / "logs" / "confirmaciones-hu012.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert json.loads(lineas[-1])["delivery_mode"] == "gmail_test_list"

    # Un ítem con destinatario fuera de la lista no reintenta: FALLIDA y fuera.
    pedido_fuera = solicitud(
        id_inscripcion="INS-002", email_destinatario="intruso@example.test"
    )
    aprobar_ambos(tmp_path, registro, pedido_fuera)
    encolada = procesar_confirmacion(
        solicitud=pedido_fuera,
        directorio_salida=tmp_path,
        registro=registro,
        asincrono=True,
        cola=cola,
    )
    assert encolada.estado == "ENVIO_ENCOLADO"
    (rechazo,) = drenar_envios(
        registro=registro,
        cola=cola,
        destino=destino,
        directorio_salida=tmp_path / "salida",
    )
    assert rechazo.resolucion == "fallida"
    assert rechazo.intento == 1
    assert registro.obtener(encolada.idempotency_key).estado == "FALLIDA"
    # No quedó nada en la cola para reintentar y no hubo segunda llamada.
    assert cola.pendientes() == ()
    assert len(transporte.solicitudes) == 1
    assert (
        drenar_envios(
            registro=registro,
            cola=cola,
            destino=destino,
            directorio_salida=tmp_path / "salida",
        )
        == ()
    )
    lineas = (
        (tmp_path / "salida" / "logs" / "confirmaciones-hu012.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert json.loads(lineas[-1])["resultado"] == "recipient_off_test_list"


def test_auditoria_gmail_no_expone_destinatario_ni_token(tmp_path: Path):
    registro = RegistroConfirmacionesMemoria()
    aprobar_ambos(tmp_path, registro, solicitud())
    destino, transporte, _ = crear_destino([RespuestaHttp(200, b'{"id":"m1"}')])
    resultado = procesar_confirmacion(
        solicitud=solicitud(),
        directorio_salida=tmp_path,
        registro=registro,
        destino=destino,
        enviar=True,
    )

    texto = resultado.log_path.read_text(encoding="utf-8")
    for sensible in (
        "ana.perez@example.test",
        "Ana Pérez",
        "TOKEN_GMAIL_SECRETO",
        "Taller de robótica educativa",
    ):
        assert sensible not in texto
    # La llamada sale por el transporte fake: nunca hubo red en la prueba.
    assert len(transporte.solicitudes) == 1


# --- Adjunto acotado (#75) ----------------------------------------------------
# Un correo puede llevar a lo sumo un adjunto `AdjuntoCorreo`: el PDF del
# certificado al titular y el PDF de muestra al correo de aprobación del
# lote. La validación corre entera antes del token y de la red, igual que la
# lista de prueba, y el endpoint declarado sigue siendo `messages/send`.

PDF_SINTETICO = b"%PDF-1.4\ncontenido sintetico\n%%EOF\n"


def test_envio_con_adjunto_pdf_mime_multipart():
    destino, transporte, _ = crear_destino(
        [RespuestaHttp(200, b'{"id":"m1"}')]
    )

    destino.entregar(
        idempotency_key="a" * 64,
        destinatario="ana.perez@example.test",
        asunto="[Agente 1] Certificado",
        cuerpo=CUERPO_BORRADOR,
        adjunto=AdjuntoCorreo(
            nombre="cert-001.pdf", contenido=PDF_SINTETICO
        ),
    )

    assert len(transporte.solicitudes) == 1
    mensaje = mensaje_de(transporte.solicitudes[0])
    assert mensaje.is_multipart()
    partes = list(mensaje.iter_parts())
    assert len(partes) == 2
    assert partes[0].get_content_type() == "text/plain"
    adjunto = partes[1]
    assert adjunto.get_content_type() == "application/pdf"
    assert adjunto.get_filename() == "cert-001.pdf"
    assert adjunto.get_payload(decode=True) == PDF_SINTETICO
    # El endpoint y el método no cambian: el adjunto va dentro del `raw`.
    assert transporte.solicitudes[0]["target"] == GMAIL_SEND_TARGET


@pytest.mark.parametrize(
    "adjunto",
    [
        # Nombre inseguro para la cabecera filename.
        AdjuntoCorreo(nombre="cert?.pdf", contenido=PDF_SINTETICO),
        AdjuntoCorreo(nombre="cert\nBcc: x@y.test.pdf", contenido=PDF_SINTETICO),
        AdjuntoCorreo(nombre="carpeta/cert.pdf", contenido=PDF_SINTETICO),
        AdjuntoCorreo(nombre="", contenido=PDF_SINTETICO),
        # Contenido vacío o desbocado.
        AdjuntoCorreo(nombre="cert.pdf", contenido=b""),
        AdjuntoCorreo(nombre="cert.pdf", contenido=b"x" * (5 * 1024 * 1024 + 1)),
        # Tipo fuera del allowlist (hoy sólo PDF).
        AdjuntoCorreo(
            nombre="cert.txt", contenido=PDF_SINTETICO, tipo_mime="text/plain"
        ),
        # Ni siquiera un AdjuntoCorreo.
        "cert.pdf",
        ("cert.pdf", PDF_SINTETICO),
    ],
)
def test_adjunto_invalido_se_rechaza_antes_de_la_red(adjunto):
    destino, transporte, tokens = crear_destino([])

    with pytest.raises(EntregaRechazadaError) as error:
        destino.entregar(
            idempotency_key="a" * 64,
            destinatario="ana.perez@example.test",
            asunto="asunto",
            cuerpo=CUERPO_BORRADOR,
            adjunto=adjunto,
        )

    assert error.value.code == "attachment_contract_invalid"
    assert tokens.invocaciones == 0
    assert transporte.solicitudes == []


def test_correo_sin_adjunto_no_cambia():
    """Regresión: sin `adjunto` el mensaje sigue siendo texto plano."""

    destino, transporte, _ = crear_destino([RespuestaHttp(200, b'{"id":"m1"}')])
    destino.entregar(
        idempotency_key="a" * 64,
        destinatario="ana.perez@example.test",
        asunto="asunto",
        cuerpo=CUERPO_BORRADOR,
    )
    mensaje = mensaje_de(transporte.solicitudes[0])
    assert not mensaje.is_multipart()
    assert mensaje.get_content_type() == "text/plain"
