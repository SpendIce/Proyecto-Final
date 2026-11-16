"""Adapter `gmail.send` con lista de prueba y modo producción (D11/D12, #40/#141).

Cubre la construcción cercada —sin lista no hay destino—, la validación por
entrega antes de cualquier llamada de red, el envío real contra transporte
fake, la traducción de errores HTTP a códigos y la integración con el
circuito de HU-012: el candado pasó de «sólo el fake por tipo exacto» a
«fake, o Gmail con lista activa», y una subclase, un envoltorio o cualquier
otro destino sigue rechazado. El modo producción (#141) agrega su propia
lista aprobada, falla cerrado sin ella y no lleva marcas de borrador. Ninguna
prueba usa red.
"""

import base64
import json
from email import policy as email_policy
from email.parser import BytesParser
from pathlib import Path

import pytest

from agente1.confirmaciones import (
    ROL_APROBADOR_CONTENIDO,
    AprobacionHumana,
    ColaEnviosMemoria,
    DestinoConfirmacionesFake,
    EntregaRechazadaError,
    ItemEnvio,
    RegistroConfirmacionesMemoria,
    SolicitudConfirmacion,
    drenar_envios,
    procesar_confirmacion,
)
from agente1.decisiones_form import (
    DECISION_APRUEBO_CONTENIDO,
    RESULTADO_REGISTRADA,
    TIPO_PLANTILLA,
    RegistroDecisiones,
    ResultadoDecision,
)
from agente1.gmail_envio import (
    DESTINATARIOS_APROBADOS_ENV,
    DESTINATARIOS_PRUEBA_ENV,
    GMAIL_HOST,
    GMAIL_SEND_TARGET,
    MODO_ENVIO_ENV,
    MODO_ENVIO_PRODUCCION,
    MODO_ENVIO_PRUEBA,
    AdjuntoCorreo,
    GmailDestinoConfirmaciones,
    GmailEnvioError,
    cargar_destinatarios_aprobados,
    cargar_destinatarios_prueba,
    cargar_modo_envio,
)
from agente1.google_workspace import (
    MAX_WORKSPACE_RESPONSE_BYTES,
    RespuestaHttp,
    _RespuestaDemasiadoGrande,
)
from agente1.plantillas_aprobadas import (
    PlantillaCorreo,
    id_version_plantilla,
)
from agente1.workspace_config import ConfiguracionWorkspaceError

LISTA = frozenset({"ana.perez@example.test", "beto@example.test"})
LISTA_APROBADA = frozenset(
    {"direccion.extension@example.test", "coordinacion@example.test"}
)
CUERPO_BORRADOR = "BORRADOR — NO ENVIAR\n\nCuerpo de la confirmación.\n"
CUERPO_APROBADO = (
    "Estimada comunidad:\n\n"
    "La actividad quedó confirmada. Los esperamos.\n\n"
    "Secretaría de Extensión Universitaria\n"
)


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


def aprobar(tmp_path: Path, registro, solicitud_) -> None:
    procesar_confirmacion(
        solicitud=solicitud_,
        directorio_salida=tmp_path,
        registro=registro,
        aprobacion=aprobacion(ROL_APROBADOR_CONTENIDO),
    )


def test_gmail_con_lista_es_destino_habilitado_y_entrega(tmp_path: Path):
    registro = RegistroConfirmacionesMemoria()
    aprobar(tmp_path, registro, solicitud())
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
    aprobar(tmp_path, registro, pedido)
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
        aprobar(tmp_path, registro, solicitud())
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
    aprobar(tmp_path, registro, solicitud())
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
    aprobar(tmp_path, registro, pedido)
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
    aprobar(tmp_path, registro, pedido_fuera)
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
    aprobar(tmp_path, registro, solicitud())
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


# --- Modo producción opt-in (#141) --------------------------------------------
# El default no cambia: sin `AGENTE1_GMAIL_MODO` todo sigue como en la sección
# anterior. Producción se habilita con un nombre explícito y su propia lista
# aprobada, vive fuera del repo y falla cerrado si falta o si un destinatario
# queda afuera. El transporte y el token siguen siendo fakes.


def destino_produccion(
    respuestas: list[RespuestaHttp | Exception],
    **kwargs,
) -> tuple[GmailDestinoConfirmaciones, TransporteSecuencia, TokenFijo]:
    return crear_destino(
        respuestas,
        destinatarios_permitidos=kwargs.pop(
            "destinatarios_permitidos", LISTA_APROBADA
        ),
        modo=MODO_ENVIO_PRODUCCION,
        **kwargs,
    )


def test_el_modo_por_defecto_sigue_siendo_prueba():
    assert cargar_modo_envio({}) == MODO_ENVIO_PRUEBA
    destino, _, _ = crear_destino([])
    assert destino.modo == MODO_ENVIO_PRUEBA

    desde_env = GmailDestinoConfirmaciones.desde_entorno(
        {DESTINATARIOS_PRUEBA_ENV: "ana.perez@example.test"},
        token_provider=TokenFijo(),
        transport=TransporteSecuencia([]),
    )
    assert desde_env.modo == MODO_ENVIO_PRUEBA
    assert desde_env._destinatarios_permitidos == {"ana.perez@example.test"}


@pytest.mark.parametrize("crudo", ["", "   ", "produccion_total", "PROD", "test"])
def test_modo_desconocido_o_vacio_falla_cerrado(crudo):
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        cargar_modo_envio({MODO_ENVIO_ENV: crudo})
    assert error.value.code == "gmail_mode_invalid"

    with pytest.raises(ConfiguracionWorkspaceError) as error:
        GmailDestinoConfirmaciones(
            destinatarios_permitidos=LISTA_APROBADA,
            token_provider=TokenFijo(),
            transport=TransporteSecuencia([]),
            modo=crudo,
        )
    assert error.value.code == "gmail_mode_invalid"


def test_modo_se_normaliza_sin_espacios_ni_mayusculas():
    assert cargar_modo_envio({MODO_ENVIO_ENV: " Produccion "}) == MODO_ENVIO_PRODUCCION


def test_produccion_sin_lista_aprobada_no_se_construye():
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        GmailDestinoConfirmaciones.desde_entorno(
            {MODO_ENVIO_ENV: MODO_ENVIO_PRODUCCION},
            token_provider=TokenFijo(),
            transport=TransporteSecuencia([]),
        )
    assert error.value.code == "gmail_production_list_missing"


def test_produccion_no_usa_la_lista_de_prueba_como_sustituta():
    entorno = {
        MODO_ENVIO_ENV: MODO_ENVIO_PRODUCCION,
        DESTINATARIOS_PRUEBA_ENV: "ana.perez@example.test",
    }
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        GmailDestinoConfirmaciones.desde_entorno(
            entorno, token_provider=TokenFijo(), transport=TransporteSecuencia([])
        )
    assert error.value.code == "gmail_production_list_missing"


@pytest.mark.parametrize(
    "lista_invalida",
    [
        [],
        (),
        ["   "],
        ["no-es-un-email"],
        ["direccion.extension@example.test", "mal@"],
        [123],
        "direccion.extension@example.test",
        None,
        [f"usuario{i}@example.test" for i in range(1001)],
    ],
)
def test_produccion_con_lista_invalida_no_se_construye(lista_invalida):
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        GmailDestinoConfirmaciones(
            destinatarios_permitidos=lista_invalida,
            token_provider=TokenFijo(),
            transport=TransporteSecuencia([]),
            modo=MODO_ENVIO_PRODUCCION,
        )
    assert error.value.code == "gmail_production_list_invalid"


def test_produccion_lee_la_lista_aprobada_y_no_la_de_prueba():
    lista = cargar_destinatarios_aprobados(
        {
            DESTINATARIOS_APROBADOS_ENV: (
                " Direccion.Extension@example.test , coordinacion@example.test"
            )
        }
    )
    assert lista == LISTA_APROBADA

    destino = GmailDestinoConfirmaciones.desde_entorno(
        {
            MODO_ENVIO_ENV: MODO_ENVIO_PRODUCCION,
            DESTINATARIOS_PRUEBA_ENV: "ana.perez@example.test",
            DESTINATARIOS_APROBADOS_ENV: (
                "direccion.extension@example.test, coordinacion@example.test"
            ),
        },
        token_provider=TokenFijo(),
        transport=TransporteSecuencia([]),
    )
    assert destino.modo == MODO_ENVIO_PRODUCCION
    assert destino._destinatarios_permitidos == LISTA_APROBADA
    assert "ana.perez@example.test" not in destino._destinatarios_permitidos


def test_produccion_destinatario_fuera_de_lista_se_rechaza_antes_de_la_red():
    destino, transporte, tokens = destino_produccion([])

    with pytest.raises(EntregaRechazadaError) as error:
        destino.entregar(
            idempotency_key="a" * 64,
            destinatario="ana.perez@example.test",
            asunto="Asunto institucional",
            cuerpo=CUERPO_APROBADO,
        )

    assert error.value.code == "recipient_off_approved_list"
    assert tokens.invocaciones == 0
    assert transporte.solicitudes == []


def test_produccion_envia_sin_marcas_de_borrador():
    destino, transporte, tokens = destino_produccion(
        [RespuestaHttp(200, b'{"id":"m1"}')]
    )

    destino.entregar(
        idempotency_key="a" * 64,
        destinatario="direccion.extension@example.test",
        asunto="Confirmación de la actividad",
        cuerpo=CUERPO_APROBADO,
    )

    assert tokens.invocaciones == 1
    (llamada,) = transporte.solicitudes
    assert llamada["method"] == "POST"
    assert llamada["host"] == GMAIL_HOST
    assert llamada["target"] == GMAIL_SEND_TARGET
    assert llamada["headers"]["Authorization"] == "Bearer TOKEN_GMAIL_SECRETO"
    assert llamada["max_response_bytes"] == MAX_WORKSPACE_RESPONSE_BYTES
    mensaje = mensaje_de(llamada)
    assert str(mensaje["To"]) == "direccion.extension@example.test"
    assert str(mensaje["Subject"]) == "Confirmación de la actividad"
    cuerpo = mensaje.get_content().replace("\r\n", "\n")
    assert cuerpo == CUERPO_APROBADO
    assert "BORRADOR — NO ENVIAR" not in cuerpo
    assert "BORRADOR — NO PUBLICAR" not in cuerpo
    assert not cuerpo.startswith("# BORRADOR")


@pytest.mark.parametrize(
    "cuerpo",
    [CUERPO_BORRADOR, "# BORRADOR — NO PUBLICAR\n\nTexto aprobado.\n"],
)
def test_produccion_rechaza_un_cuerpo_con_marcas_de_borrador(cuerpo):
    destino, transporte, tokens = destino_produccion([])

    with pytest.raises(EntregaRechazadaError) as error:
        destino.entregar(
            idempotency_key="a" * 64,
            destinatario="direccion.extension@example.test",
            asunto="Asunto institucional",
            cuerpo=cuerpo,
        )

    assert error.value.code == "draft_marker_in_production"
    assert tokens.invocaciones == 0
    assert transporte.solicitudes == []


def test_prueba_sigue_exigiendo_la_marca_de_borrador():
    destino, transporte, tokens = crear_destino([])

    with pytest.raises(EntregaRechazadaError) as error:
        destino.entregar(
            idempotency_key="a" * 64,
            destinatario="ana.perez@example.test",
            asunto="Asunto",
            cuerpo=CUERPO_APROBADO,
        )

    assert error.value.code == "draft_marker_missing"
    assert tokens.invocaciones == 0
    assert transporte.solicitudes == []


def test_produccion_con_adjunto_valido_mantiene_mime_multipart():
    destino, transporte, _ = destino_produccion(
        [RespuestaHttp(200, b'{"id":"m1"}')]
    )

    destino.entregar(
        idempotency_key="a" * 64,
        destinatario="direccion.extension@example.test",
        asunto="Certificado",
        cuerpo=CUERPO_APROBADO,
        adjunto=AdjuntoCorreo(nombre="cert-001.pdf", contenido=PDF_SINTETICO),
    )

    mensaje = mensaje_de(transporte.solicitudes[0])
    assert mensaje.is_multipart()
    partes = list(mensaje.iter_parts())
    texto = partes[0].get_content().replace("\r\n", "\n")
    assert texto == CUERPO_APROBADO
    assert "BORRADOR — NO PUBLICAR" not in texto
    assert partes[1].get_content_type() == "application/pdf"
    assert partes[1].get_filename() == "cert-001.pdf"
    assert transporte.solicitudes[0]["target"] == GMAIL_SEND_TARGET


@pytest.mark.parametrize(
    "adjunto",
    [
        AdjuntoCorreo(nombre="cert?.pdf", contenido=PDF_SINTETICO),
        AdjuntoCorreo(nombre="cert.pdf", contenido=b""),
        AdjuntoCorreo(
            nombre="cert.txt", contenido=PDF_SINTETICO, tipo_mime="text/plain"
        ),
        "cert.pdf",
    ],
)
def test_produccion_rechaza_adjunto_invalido_antes_de_la_red(adjunto):
    destino, transporte, tokens = destino_produccion([])

    with pytest.raises(EntregaRechazadaError) as error:
        destino.entregar(
            idempotency_key="a" * 64,
            destinatario="direccion.extension@example.test",
            asunto="Certificado",
            cuerpo=CUERPO_APROBADO,
            adjunto=adjunto,
        )

    assert error.value.code == "attachment_contract_invalid"
    assert tokens.invocaciones == 0
    assert transporte.solicitudes == []


@pytest.mark.parametrize(
    ("respuesta", "codigo"),
    [
        (RespuestaHttp(400, b"secreto@example.invalid"), "gmail_request_invalid"),
        (RespuestaHttp(401, b"secreto@example.invalid"), "gmail_auth_denied"),
        (RespuestaHttp(429, b"secreto@example.invalid"), "gmail_rate_limited"),
        (RespuestaHttp(500, b"secreto@example.invalid"), "gmail_unavailable"),
        (
            RespuestaHttp(200, b"x" * (MAX_WORKSPACE_RESPONSE_BYTES + 1)),
            "gmail_response_too_large",
        ),
        (TimeoutError("timeout secreto@example.invalid"), "gmail_unavailable"),
    ],
)
def test_produccion_traduce_errores_del_medio_con_el_mismo_codigo(respuesta, codigo):
    destino, transporte, _ = destino_produccion([respuesta])

    with pytest.raises(GmailEnvioError) as error:
        destino.entregar(
            idempotency_key="a" * 64,
            destinatario="direccion.extension@example.test",
            asunto="Asunto institucional",
            cuerpo=CUERPO_APROBADO,
        )

    assert error.value.code == codigo
    assert len(transporte.solicitudes) == 1
    assert "secreto@example.invalid" not in str(error.value)


def test_el_worker_audita_el_modo_produccion(tmp_path: Path):
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    clave = "d" * 64
    assert registro.crear(clave, "Asunto institucional", CUERPO_APROBADO)
    assert registro.transicionar(
        clave, frozenset({"PENDIENTE_VALIDACION"}), "APROBADA"
    )
    assert registro.transicionar(clave, frozenset({"APROBADA"}), "ENVIO_ENCOLADO")
    assert cola.encolar(
        ItemEnvio(
            idempotency_key=clave,
            destinatario="direccion.extension@example.test",
            input_hash="e" * 64,
        )
    )
    destino, transporte, _ = destino_produccion(
        [RespuestaHttp(200, b'{"id":"m1"}')]
    )

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
    ultima = json.loads(lineas[-1])
    assert ultima["delivery_mode"] == "gmail_production"
    assert ultima["estado"] == "ENVIADA_SIMULADA"


def test_produccion_sigue_rechazando_cualquier_cuerpo_marcado():
    """El adapter no afloja: un cuerpo marcado no llega ni al token.

    Con el modo producción del renderer (#142) el cuerpo que viaja ya no
    lleva marcas, pero la guarda del adapter queda como última línea:
    si algo marcado se le escapa a cualquier camino, se rechaza antes de
    la red.
    """

    destino, transporte, tokens = destino_produccion([])

    with pytest.raises(EntregaRechazadaError) as error:
        destino.entregar(
            idempotency_key="a" * 64,
            destinatario="direccion.extension@example.test",
            asunto="Asunto institucional",
            cuerpo=CUERPO_BORRADOR,
        )

    assert error.value.code == "draft_marker_in_production"
    assert tokens.invocaciones == 0
    assert transporte.solicitudes == []


# Plantilla sintética declarada para las pruebas del circuito en
# producción (#142): no es una redacción institucional — las de la SEU
# siguen pendientes y llegan por `AGENTE1_PLANTILLAS_APROBADAS_PATH` —.
PLANTILLA_INSCRIPCION_SINTETICA = {
    "inscripcion": PlantillaCorreo(
        asunto="Confirmación de {{actividad}}",
        cuerpo=(
            "Hola {{nombre_destinatario}},\n\n"
            "{{frase_evento}}: {{actividad}}.\n"
            "Fecha: {{fecha}}\n"
            "Lugar: {{lugar}}\n"
            "Organiza: {{organiza}}\n\n"
            "Contacto: {{contacto}}\n"
        ),
    )
}


def _registrar_plantilla(
    registro: RegistroDecisiones,
    *,
    tipo: str,
    plantilla: PlantillaCorreo,
    rol: str = ROL_APROBADOR_CONTENIDO,
) -> None:
    """La `apruebo_contenido` registrada sobre la versión de la plantilla.

    Es el hecho que habilita el modo producción (#142, definición del
    11/11): no basta que el archivo declare el texto, la versión exacta
    tiene que figurar en el registro de decisiones.
    """

    registro.registrar(
        ResultadoDecision(
            id_respuesta=f"{1:064x}",
            correo_hash="a" * 64,
            rol=rol,
            rol_origen="padron",
            tipo=TIPO_PLANTILLA,
            objeto_id=id_version_plantilla(tipo, plantilla),
            decision=DECISION_APRUEBO_CONTENIDO,
            resultado=RESULTADO_REGISTRADA,
            rechazo_codigo=None,
            marca_temporal_form="2026-10-11 09:00:00",
            timestamp="2026-10-11T09:00:00+00:00",
        )
    )


def _decisiones_con_inscripcion(tmp_path: Path) -> RegistroDecisiones:
    """Registro con la aprobación de la plantilla sintética `inscripcion`."""

    registro = RegistroDecisiones(tmp_path / "estado-decisiones")
    _registrar_plantilla(
        registro,
        tipo="inscripcion",
        plantilla=PLANTILLA_INSCRIPCION_SINTETICA["inscripcion"],
    )
    return registro


def aprobar_en_produccion(
    tmp_path: Path, registro, solicitud_, decisiones=None
) -> None:
    """La aprobación única con el borrador ya compuesto en producción."""

    procesar_confirmacion(
        solicitud=solicitud_,
        directorio_salida=tmp_path,
        registro=registro,
        aprobacion=aprobacion(ROL_APROBADOR_CONTENIDO),
        modo_envio=MODO_ENVIO_PRODUCCION,
        plantillas_aprobadas=PLANTILLA_INSCRIPCION_SINTETICA,
        decisiones=(
            decisiones
            if decisiones is not None
            else _decisiones_con_inscripcion(tmp_path)
        ),
    )


def test_en_produccion_el_circuito_entrega_el_cuerpo_aprobado(tmp_path: Path):
    """El cierre de #142: la plantilla aprobada por tipo compone el cuerpo.

    Con `modo_envio="produccion"` y la plantilla sintética declarada, el
    borrador que se registra no lleva marcas y el destino de producción lo
    entrega: el `raw` del `gmail.send` viaja limpio y sin el prefijo MIME
    de borrador.
    """

    registro = RegistroConfirmacionesMemoria()
    decisiones = _decisiones_con_inscripcion(tmp_path)
    aprobar_en_produccion(tmp_path, registro, solicitud(), decisiones)
    destino, transporte, _ = destino_produccion(
        [RespuestaHttp(200, b'{"id":"m1"}')],
        destinatarios_permitidos=LISTA_APROBADA | {"ana.perez@example.test"},
    )

    resultado = procesar_confirmacion(
        solicitud=solicitud(),
        directorio_salida=tmp_path,
        registro=registro,
        destino=destino,
        enviar=True,
        modo_envio=MODO_ENVIO_PRODUCCION,
        plantillas_aprobadas=PLANTILLA_INSCRIPCION_SINTETICA,
        decisiones=decisiones,
    )

    assert resultado.estado == "ENVIADA_SIMULADA"
    assert len(transporte.solicitudes) == 1
    mensaje = mensaje_de(transporte.solicitudes[0])
    cuerpo = mensaje.get_content()
    assert "BORRADOR" not in cuerpo
    assert "Ana Pérez" in cuerpo
    assert "Taller de robótica educativa" in cuerpo
    assert not mensaje.get_content().startswith("# BORRADOR")
    ultima = json.loads(
        resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
    )
    assert ultima["delivery_mode"] == "gmail_production"


def test_en_produccion_sin_la_plantilla_del_tipo_es_invalida(tmp_path: Path):
    """Pedir producción sin plantilla aprobada del tipo no compone nada."""

    resultado = procesar_confirmacion(
        solicitud=solicitud(),
        directorio_salida=tmp_path,
        registro=RegistroConfirmacionesMemoria(),
        modo_envio=MODO_ENVIO_PRODUCCION,
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "approved_template_missing"


def test_en_produccion_una_plantilla_mal_formada_es_invalida(tmp_path: Path):
    """Variable desconocida en la plantilla del tipo: la forma no cierra."""

    plantilla_rara = {
        "inscripcion": PlantillaCorreo(
            asunto="Confirmación",
            cuerpo="Texto con {{dato_que_no_existe}}.",
        )
    }

    resultado = procesar_confirmacion(
        solicitud=solicitud(),
        directorio_salida=tmp_path,
        registro=RegistroConfirmacionesMemoria(),
        modo_envio=MODO_ENVIO_PRODUCCION,
        plantillas_aprobadas=plantilla_rara,
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "approved_template_invalid"


def test_un_modo_de_envio_desconocido_es_invalida(tmp_path: Path):
    resultado = procesar_confirmacion(
        solicitud=solicitud(),
        directorio_salida=tmp_path,
        registro=RegistroConfirmacionesMemoria(),
        modo_envio="espacial",
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "send_mode_invalid"


def test_un_borrador_de_prueba_no_sirve_para_envio_de_produccion(
    tmp_path: Path,
):
    """El registro conserva lo aprobado: un borrador marcado no se entrega.

    Si la pieza se aprobó compuesta en prueba, un envío de producción no
    la reescribe en silencio — entregaría algo distinto de lo aprobado —:
    sale `INVALIDA` y la pieza se vuelve a tramitar en producción.
    """

    registro = RegistroConfirmacionesMemoria()
    aprobar(tmp_path, registro, solicitud())  # aprobada en prueba
    destino, transporte, _ = destino_produccion(
        [], destinatarios_permitidos=LISTA_APROBADA | {"ana.perez@example.test"}
    )

    resultado = procesar_confirmacion(
        solicitud=solicitud(),
        directorio_salida=tmp_path,
        registro=registro,
        destino=destino,
        enviar=True,
        modo_envio=MODO_ENVIO_PRODUCCION,
        plantillas_aprobadas=PLANTILLA_INSCRIPCION_SINTETICA,
        decisiones=_decisiones_con_inscripcion(tmp_path),
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "template_body_mismatch"
    assert transporte.solicitudes == []


def test_en_prueba_el_circuito_conserva_las_marcas_de_siempre(tmp_path: Path):
    """El default no se movió: `prueba` arma el mismo borrador marcado."""

    registro = RegistroConfirmacionesMemoria()
    resultado = procesar_confirmacion(
        solicitud=solicitud(),
        directorio_salida=tmp_path,
        registro=registro,
        aprobacion=aprobacion(ROL_APROBADOR_CONTENIDO),
    )

    assert resultado.estado != "INVALIDA"
    guardada = registro.obtener(resultado.idempotency_key)
    assert guardada.cuerpo.startswith(CUERPO_BORRADOR.splitlines()[0])
    assert guardada.asunto.startswith("[BORRADOR — NO ENVIAR]")


def test_repr_en_produccion_tampoco_expone_las_direcciones():
    destino, _, _ = destino_produccion([])
    representacion = repr(destino)
    assert "direccion.extension@example.test" not in representacion
    assert "produccion" in representacion


def test_en_produccion_sin_la_aprobacion_de_version_es_invalida(
    tmp_path: Path,
):
    """La plantilla en el archivo sin `apruebo_contenido` no autoriza.

    La definición del 11/11 (#125): «aprobada» es un hecho del registro,
    no del archivo — una versión sin la decisión registrada se rechaza
    con código propio y nada se compone.
    """

    resultado = procesar_confirmacion(
        solicitud=solicitud(),
        directorio_salida=tmp_path,
        registro=RegistroConfirmacionesMemoria(),
        modo_envio=MODO_ENVIO_PRODUCCION,
        plantillas_aprobadas=PLANTILLA_INSCRIPCION_SINTETICA,
        decisiones=RegistroDecisiones(tmp_path / "estado-decisiones"),
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "template_version_unapproved"


def test_en_produccion_una_version_editada_despues_pierde_la_aprobacion(
    tmp_path: Path,
):
    """El id ata la decisión al hash: un texto distinto es otra versión."""

    decisiones = _decisiones_con_inscripcion(tmp_path)
    plantilla_editada = {
        "inscripcion": PlantillaCorreo(
            asunto="Confirmación de {{actividad}}",
            cuerpo="Texto cambiado después de la aprobación. {{contacto}}",
        )
    }

    resultado = procesar_confirmacion(
        solicitud=solicitud(),
        directorio_salida=tmp_path,
        registro=RegistroConfirmacionesMemoria(),
        modo_envio=MODO_ENVIO_PRODUCCION,
        plantillas_aprobadas=plantilla_editada,
        decisiones=decisiones,
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "template_version_unapproved"


def test_el_cuerpo_de_produccion_en_modo_prueba_se_rechaza(tmp_path: Path):
    """El cierre de #142 al revés: el mismo cuerpo sin marca no entra en prueba.

    No es un texto genérico: es el cuerpo que el renderer compone desde la
    plantilla aprobada. Si esa pieza llega al destino de prueba —que exige
    la marca de borrador— el adapter la rechaza antes de la red.
    """

    registro = RegistroConfirmacionesMemoria()
    decisiones = _decisiones_con_inscripcion(tmp_path)
    resultado = procesar_confirmacion(
        solicitud=solicitud(),
        directorio_salida=tmp_path,
        registro=registro,
        aprobacion=aprobacion(ROL_APROBADOR_CONTENIDO),
        modo_envio=MODO_ENVIO_PRODUCCION,
        plantillas_aprobadas=PLANTILLA_INSCRIPCION_SINTETICA,
        decisiones=decisiones,
    )
    assert resultado.estado == "APROBADA"
    cuerpo_produccion = registro.obtener(
        resultado.idempotency_key
    ).cuerpo
    assert "BORRADOR" not in cuerpo_produccion

    destino_prueba, transporte, tokens = crear_destino([])
    with pytest.raises(EntregaRechazadaError) as error:
        destino_prueba.entregar(
            idempotency_key=resultado.idempotency_key,
            destinatario="ana.perez@example.test",
            asunto="Confirmación",
            cuerpo=cuerpo_produccion,
        )
    assert error.value.code == "draft_marker_missing"
    assert tokens.invocaciones == 0
    assert transporte.solicitudes == []


def test_en_produccion_un_destinatario_fuera_de_la_lista_falla_sin_reintento(
    tmp_path: Path,
):
    """Cierre #142 + lista aprobada: el cuerpo renderizado no llega a la red.

    El destinatario de la solicitud no está en `destinatarios_permitidos`
    del adapter de producción: la entrega se rechaza por política con
    `recipient_off_approved_list`, queda `FALLIDA` y no se reintenta.
    """

    registro = RegistroConfirmacionesMemoria()
    decisiones = _decisiones_con_inscripcion(tmp_path)
    aprobar_en_produccion(tmp_path, registro, solicitud(), decisiones)
    # LISTA_APROBADA no incluye el destinatario de `solicitud()`.
    destino, transporte, _ = destino_produccion([])

    resultado = procesar_confirmacion(
        solicitud=solicitud(),
        directorio_salida=tmp_path,
        registro=registro,
        destino=destino,
        enviar=True,
        modo_envio=MODO_ENVIO_PRODUCCION,
        plantillas_aprobadas=PLANTILLA_INSCRIPCION_SINTETICA,
        decisiones=decisiones,
    )

    assert resultado.estado == "FALLIDA"
    assert resultado.error == "recipient_off_approved_list"
    assert transporte.solicitudes == []
