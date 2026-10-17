"""Registro y aviso de cambios en la configuración por entorno (#94, ADR 0010).

La huella sale del `resumen_seguro()` de la configuración de Workspace y se
compara con la de la corrida anterior: la primera vez asienta la base sin
avisar; si no cambió, deja constancia de que se comparó; si cambió, asienta las
claves afectadas —sin sus valores— y avisa por correo. El aviso que falla no
frena la corrida: queda en la auditoría y listo. La rotación del token y del
refresh token no dispara nada porque ninguno entra en la huella.

Los transportes son fakes declarados: se ejerce el camino real de `gmail.send`
(`GmailDestinoConfirmaciones`) sin salir a la red.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from email import message_from_bytes
from pathlib import Path

import pytest

from agente1.config_entorno import (
    AUDITORIA_NOMBRE,
    AVISO_ENVIADO,
    AVISO_FALLIDO,
    AVISO_NO_CONFIGURADO,
    ENV_AVISO_DESTINATARIO,
    RESULTADO_BASE,
    RESULTADO_CAMBIO,
    RESULTADO_SIN_CAMBIO,
    AvisoConfiguracionGmail,
    cargar_destinatario_aviso,
    claves_cambiadas,
    huella_configuracion,
    revisar_configuracion_al_arrancar,
)
from agente1.gmail_envio import GMAIL_SEND_TARGET, GmailDestinoConfirmaciones
from agente1.google_workspace import MAX_WORKSPACE_RESPONSE_BYTES, RespuestaHttp
from agente1.workspace_config import (
    ConfiguracionWorkspaceError,
    cargar_configuracion_workspace,
)

OPERADOR = "operador@example.test"


def entorno_workspace(**extras: str) -> dict[str, str]:
    base = {
        "AGENTE1_WORKSPACE_AMBIENTE": "D2",
        "AGENTE1_WORKSPACE_SPREADSHEET_ID": "planilla-sintetica-1",
        "AGENTE1_WORKSPACE_RANGO_A1": "'Actividades'!A1:I500",
        "AGENTE1_WORKSPACE_FOLDER_ID": "carpeta-sintetica-1",
        "AGENTE1_WORKSPACE_TEMPLATE_ID": "plantilla-sintetica-1",
        "AGENTE1_WORKSPACE_TIMEOUT_S": "30",
        "AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES": str(MAX_WORKSPACE_RESPONSE_BYTES),
    }
    base.update(extras)
    return base


class TokenFijo:
    def obtener_access_token(self) -> str:
        return "token-sintetico"


class TransporteCaptura:
    """Transporte fake: registra las solicitudes y devuelve una respuesta fija."""

    def __init__(self, respuesta: RespuestaHttp) -> None:
        self.respuesta = respuesta
        self.solicitudes: list[dict[str, object]] = []

    def request(
        self,
        *,
        method: str,
        host: str,
        target: str,
        headers: dict[str, str],
        body: bytes | None,
        deadline: float,
        max_response_bytes: int,
    ) -> RespuestaHttp:
        self.solicitudes.append(
            {
                "method": method,
                "host": host,
                "target": target,
                "body": body,
            }
        )
        return self.respuesta


def respuesta_envio_ok() -> RespuestaHttp:
    return RespuestaHttp(status=200, body=b'{"id": "msg-sintetico-1"}')


def aviso_gmail(transport: TransporteCaptura) -> AvisoConfiguracionGmail:
    return AvisoConfiguracionGmail(
        destinatario=OPERADOR,
        destino=GmailDestinoConfirmaciones(
            destinatarios_permitidos=[OPERADOR],
            token_provider=TokenFijo(),
            transport=transport,
        ),
    )


def asientos(directorio: Path) -> list[dict]:
    crudo = (directorio / "logs" / AUDITORIA_NOMBRE).read_text(encoding="utf-8")
    return [json.loads(linea) for linea in crudo.splitlines() if linea]


def texto_del_correo(solicitud: dict) -> str:
    """El cuerpo del correo, decodificado desde el `raw` de `gmail.send`."""

    documento = json.loads(bytes(solicitud["body"]).decode("utf-8"))
    mensaje = message_from_bytes(base64.urlsafe_b64decode(documento["raw"]))
    partes = []
    for parte in mensaje.walk():
        if parte.get_content_maintype() == "multipart":
            continue
        carga = parte.get_payload(decode=True)
        if carga:
            partes.append(carga.decode("utf-8", "replace"))
    return "\n".join(partes)


# --- La huella y el diff de claves --------------------------------------


def test_huella_es_estable_y_claves_cambiadas_nombra_solo_claves() -> None:
    uno = {"b": 2, "a": [1, 2]}
    otro = {"a": [1, 2], "b": 2}

    assert huella_configuracion(uno) == huella_configuracion(otro)
    assert huella_configuracion(uno) != huella_configuracion({"a": [1, 2], "b": 3})
    assert claves_cambiadas(uno, {"a": [1, 2], "b": 3}) == ("b",)
    # Una clave que aparece o desaparece también es un cambio.
    assert claves_cambiadas(uno, {"a": [1, 2], "c": 9}) == ("b", "c")


def test_la_rotacion_de_credenciales_no_altera_la_huella() -> None:
    antes = cargar_configuracion_workspace(
        entorno_workspace(
            AGENTE1_WORKSPACE_ACCESS_TOKEN="token-viejo",
            AGENTE1_WORKSPACE_OAUTH_REFRESH_TOKEN="refresh-viejo",
        )
    )
    despues = cargar_configuracion_workspace(
        entorno_workspace(
            AGENTE1_WORKSPACE_ACCESS_TOKEN="token-nuevo",
            AGENTE1_WORKSPACE_OAUTH_REFRESH_TOKEN="refresh-nuevo",
        )
    )

    assert huella_configuracion(antes.resumen_seguro()) == huella_configuracion(
        despues.resumen_seguro()
    )
    assert "token-viejo" not in json.dumps(antes.resumen_seguro())
    assert "refresh-viejo" not in json.dumps(antes.resumen_seguro())


# --- Los tres desenlaces ------------------------------------------------


def test_primera_corrida_asienta_la_base_sin_avisar(tmp_path: Path) -> None:
    config = cargar_configuracion_workspace(entorno_workspace())
    transport = TransporteCaptura(respuesta_envio_ok())

    resultado = revisar_configuracion_al_arrancar(
        config=config, directorio_salida=tmp_path, aviso=aviso_gmail(transport)
    )

    assert resultado.resultado == RESULTADO_BASE
    assert resultado.huella_anterior is None
    assert resultado.aviso is None
    assert transport.solicitudes == []
    asiento = asientos(tmp_path)[-1]
    assert asiento["resultado"] == RESULTADO_BASE
    assert asiento["aviso"] is None
    assert asiento["claves_cambiadas"] == []
    # La base es el resumen seguro: la corrida siguiente tiene con qué comparar.
    assert asiento["resumen"] == config.resumen_seguro()
    assert asiento["huella"] == huella_configuracion(config.resumen_seguro())


def test_sin_cambio_no_avisa(tmp_path: Path) -> None:
    config = cargar_configuracion_workspace(entorno_workspace())
    transport = TransporteCaptura(respuesta_envio_ok())

    revisar_configuracion_al_arrancar(
        config=config, directorio_salida=tmp_path, aviso=aviso_gmail(transport)
    )
    resultado = revisar_configuracion_al_arrancar(
        config=config, directorio_salida=tmp_path, aviso=aviso_gmail(transport)
    )

    assert resultado.resultado == RESULTADO_SIN_CAMBIO
    assert resultado.claves_cambiadas == ()
    assert resultado.aviso is None
    assert transport.solicitudes == []
    assert asientos(tmp_path)[-1]["resultado"] == RESULTADO_SIN_CAMBIO


def test_cambio_de_una_clave_registra_claves_sin_valores_y_avisa(
    tmp_path: Path,
) -> None:
    anterior = cargar_configuracion_workspace(entorno_workspace())
    actual = cargar_configuracion_workspace(
        entorno_workspace(AGENTE1_WORKSPACE_SPREADSHEET_ID="planilla-sintetica-2")
    )
    transport = TransporteCaptura(respuesta_envio_ok())

    revisar_configuracion_al_arrancar(
        config=anterior, directorio_salida=tmp_path, aviso=aviso_gmail(transport)
    )
    resultado = revisar_configuracion_al_arrancar(
        config=actual, directorio_salida=tmp_path, aviso=aviso_gmail(transport)
    )

    assert resultado.resultado == RESULTADO_CAMBIO
    assert resultado.claves_cambiadas == ("spreadsheet_ref_hash",)
    assert resultado.aviso == AVISO_ENVIADO
    # El aviso salió por el único endpoint de Gmail habilitado.
    assert len(transport.solicitudes) == 1
    assert transport.solicitudes[0]["target"] == GMAIL_SEND_TARGET
    asiento = asientos(tmp_path)[-1]
    assert asiento["resultado"] == RESULTADO_CAMBIO
    assert asiento["claves_cambiadas"] == ["spreadsheet_ref_hash"]
    assert asiento["aviso"] == AVISO_ENVIADO
    # Ni la auditoría ni el correo llevan los identificadores, sólo las claves.
    crudo = (tmp_path / "logs" / AUDITORIA_NOMBRE).read_text(encoding="utf-8")
    assert "planilla-sintetica-1" not in crudo
    assert "planilla-sintetica-2" not in crudo
    correo = texto_del_correo(transport.solicitudes[0])
    assert "spreadsheet_ref_hash" in correo
    assert "planilla-sintetica" not in correo


@pytest.mark.parametrize(
    "clave,valor",
    [
        ("AGENTE1_WORKSPACE_SPREADSHEET_ID", "planilla-otra"),
        ("AGENTE1_WORKSPACE_FOLDER_ID", "carpeta-otra"),
        ("AGENTE1_WORKSPACE_TEMPLATE_ID", "plantilla-otra"),
        ("AGENTE1_WORKSPACE_RANGO_A1", "'Otra hoja'!A1:I500"),
    ],
)
def test_cualquier_identificador_de_workspace_queda_en_la_auditoria(
    tmp_path: Path, clave: str, valor: str
) -> None:
    anterior = cargar_configuracion_workspace(entorno_workspace())
    actual = cargar_configuracion_workspace(entorno_workspace(**{clave: valor}))
    transport = TransporteCaptura(respuesta_envio_ok())

    revisar_configuracion_al_arrancar(config=anterior, directorio_salida=tmp_path)
    resultado = revisar_configuracion_al_arrancar(
        config=actual, directorio_salida=tmp_path, aviso=aviso_gmail(transport)
    )

    assert resultado.resultado == RESULTADO_CAMBIO
    assert len(resultado.claves_cambiadas) == 1
    assert len(transport.solicitudes) == 1
    crudo = (tmp_path / "logs" / AUDITORIA_NOMBRE).read_text(encoding="utf-8")
    assert valor not in crudo


def test_el_aviso_que_falla_queda_en_la_auditoria_y_la_corrida_sigue(
    tmp_path: Path,
) -> None:
    anterior = cargar_configuracion_workspace(entorno_workspace())
    actual = cargar_configuracion_workspace(
        entorno_workspace(AGENTE1_WORKSPACE_FOLDER_ID="carpeta-sintetica-2")
    )
    transport = TransporteCaptura(RespuestaHttp(status=500, body=b"error"))

    revisar_configuracion_al_arrancar(
        config=anterior, directorio_salida=tmp_path, aviso=aviso_gmail(transport)
    )
    resultado = revisar_configuracion_al_arrancar(
        config=actual, directorio_salida=tmp_path, aviso=aviso_gmail(transport)
    )

    assert resultado.resultado == RESULTADO_CAMBIO
    assert resultado.aviso == AVISO_FALLIDO
    assert resultado.aviso_error == "gmail_unavailable"
    asiento = asientos(tmp_path)[-1]
    assert asiento["aviso"] == AVISO_FALLIDO
    assert asiento["aviso_error"] == "gmail_unavailable"

    # El cambio ya quedó asentado: la corrida siguiente no vuelve a avisar.
    siguiente = revisar_configuracion_al_arrancar(
        config=actual, directorio_salida=tmp_path, aviso=aviso_gmail(transport)
    )
    assert siguiente.resultado == RESULTADO_SIN_CAMBIO


def test_sin_direccion_declarada_el_cambio_igual_se_asienta(tmp_path: Path) -> None:
    anterior = cargar_configuracion_workspace(entorno_workspace())
    actual = cargar_configuracion_workspace(
        entorno_workspace(AGENTE1_WORKSPACE_SPREADSHEET_ID="planilla-otra")
    )

    revisar_configuracion_al_arrancar(config=anterior, directorio_salida=tmp_path)
    resultado = revisar_configuracion_al_arrancar(
        config=actual, directorio_salida=tmp_path
    )

    assert resultado.resultado == RESULTADO_CAMBIO
    assert resultado.aviso == AVISO_NO_CONFIGURADO
    assert asientos(tmp_path)[-1]["aviso"] == AVISO_NO_CONFIGURADO


# --- La dirección del aviso ---------------------------------------------


def test_destinatario_declarado_se_valida() -> None:
    assert cargar_destinatario_aviso({}) is None
    assert cargar_destinatario_aviso({ENV_AVISO_DESTINATARIO: OPERADOR}) == OPERADOR

    with pytest.raises(ConfiguracionWorkspaceError) as exc:
        cargar_destinatario_aviso({ENV_AVISO_DESTINATARIO: "no-es-un-correo"})
    assert exc.value.code == "config_entorno_aviso_invalid"


def test_el_asiento_lleva_la_identidad_de_la_version(tmp_path: Path) -> None:
    config = cargar_configuracion_workspace(entorno_workspace())

    revisar_configuracion_al_arrancar(
        config=config,
        directorio_salida=tmp_path,
        clock=lambda: datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc),
    )

    asiento = asientos(tmp_path)[-1]
    assert asiento["record"] == "agente1_config_entorno_v1"
    assert asiento["ejecutado_en"] == "2026-10-14T12:00:00+00:00"
    # La identidad la agrega `registro_auditoria` (#93), no este módulo.
    assert asiento["version_agente"] == "0.4.0"
    assert len(asiento["manifest_version_sha256"]) == 64
