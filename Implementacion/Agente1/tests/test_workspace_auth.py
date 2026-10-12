"""Provider OAuth de refresh token: intercambio acotado, trío de secretos
todo-o-nada, errores como códigos cerrados y factory que prefiere la
credencial durable sin esconder una configuración a medias."""

import json
from urllib.parse import parse_qs

import pytest

from agente1.google_workspace import RespuestaHttp
from agente1.workspace_auth import (
    CLIENT_ID_ENV,
    CLIENT_SECRET_ENV,
    OAUTH_TOKEN_HOST,
    REFRESH_TOKEN_ENV,
    OAuthRefreshTokenProvider,
    construir_token_provider,
)
from agente1.workspace_config import (
    ConfiguracionWorkspaceError,
    TokenEntornoProvider,
)

CLIENT_ID = "12345.apps.googleusercontent.com"
CLIENT_SECRET = "GOCSPX-secreto-sintetico"
REFRESH_TOKEN = "1//refresh-token-sintetico"


class TransporteCaptura:
    def __init__(self, respuesta: RespuestaHttp | None = None) -> None:
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
                "headers": headers,
                "body": body,
            }
        )
        if self.respuesta is None:
            raise RuntimeError("sin red en la prueba")
        return self.respuesta


def respuesta_token(payload: dict[str, object], status: int = 200) -> RespuestaHttp:
    return RespuestaHttp(status=status, body=json.dumps(payload).encode())


def provider_con(transport: TransporteCaptura) -> OAuthRefreshTokenProvider:
    return OAuthRefreshTokenProvider(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        refresh_token=REFRESH_TOKEN,
        transport=transport,
    )


def env_oauth_completo() -> dict[str, str]:
    return {
        CLIENT_ID_ENV: CLIENT_ID,
        CLIENT_SECRET_ENV: CLIENT_SECRET,
        REFRESH_TOKEN_ENV: REFRESH_TOKEN,
    }


def test_intercambio_exitoso_devuelve_el_access_token():
    transporte = TransporteCaptura(respuesta_token({"access_token": "ya29.sintetico"}))
    token = provider_con(transporte).obtener_access_token()
    assert token == "ya29.sintetico"

    solicitud = transporte.solicitudes[0]
    assert solicitud["method"] == "POST"
    assert solicitud["host"] == OAUTH_TOKEN_HOST
    assert solicitud["target"] == "/token"
    assert solicitud["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    # El secreto sólo viaja dentro del POST, codificado como formulario.
    formulario = parse_qs(solicitud["body"].decode())
    assert formulario["grant_type"] == ["refresh_token"]
    assert formulario["client_id"] == [CLIENT_ID]
    assert formulario["client_secret"] == [CLIENT_SECRET]
    assert formulario["refresh_token"] == [REFRESH_TOKEN]


def test_cada_invocacion_hace_un_intercambio_nuevo():
    transporte = TransporteCaptura(respuesta_token({"access_token": "ya29.x"}))
    proveedor = provider_con(transporte)
    proveedor.obtener_access_token()
    proveedor.obtener_access_token()
    assert len(transporte.solicitudes) == 2


@pytest.mark.parametrize("status", [400, 401, 403])
def test_token_revocado_o_denegado_falla_con_codigo_denied(status):
    transporte = TransporteCaptura(
        respuesta_token({"error": "invalid_grant"}, status=status)
    )
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider_con(transporte).obtener_access_token()
    assert error.value.code == "workspace_token_exchange_denied"


def test_falla_del_endpoint_no_se_reintenta():
    transporte = TransporteCaptura(respuesta_token({}, status=500))
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider_con(transporte).obtener_access_token()
    assert error.value.code == "workspace_token_exchange_unavailable"
    assert len(transporte.solicitudes) == 1


def test_rate_limit_del_endpoint_tiene_codigo_propio():
    transporte = TransporteCaptura(respuesta_token({}, status=429))
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider_con(transporte).obtener_access_token()
    assert error.value.code == "workspace_token_exchange_rate_limited"


def test_respuesta_sin_access_token_es_invalida():
    transporte = TransporteCaptura(respuesta_token({"token_type": "Bearer"}))
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider_con(transporte).obtener_access_token()
    assert error.value.code == "workspace_token_exchange_response_invalid"


def test_respuesta_no_json_es_invalida():
    transporte = TransporteCaptura(RespuestaHttp(status=200, body=b"<html>"))
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider_con(transporte).obtener_access_token()
    assert error.value.code == "workspace_token_exchange_response_invalid"


def test_token_devuelto_con_whitespace_se_rechaza():
    transporte = TransporteCaptura(
        respuesta_token({"access_token": "ya29\ninyectado: si"})
    )
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider_con(transporte).obtener_access_token()
    assert error.value.code == "workspace_token_exchange_response_invalid"


def test_falla_de_red_se_traduce_a_unavailable():
    transporte = TransporteCaptura(respuesta=None)
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider_con(transporte).obtener_access_token()
    assert error.value.code == "workspace_token_exchange_unavailable"


@pytest.mark.parametrize(
    "campo",
    ["client_id", "client_secret", "refresh_token"],
)
def test_secreto_con_whitespace_se_rechaza_en_el_constructor(campo):
    kwargs = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
    }
    kwargs[campo] = "valor\ncon\nsalto"
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        OAuthRefreshTokenProvider(**kwargs, transport=TransporteCaptura())
    assert error.value.code == "workspace_auth_config_invalid"


def test_desde_entorno_sin_variables_falla_como_missing():
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        OAuthRefreshTokenProvider.desde_entorno({})
    assert error.value.code == "workspace_auth_config_missing"


def test_desde_entorno_con_trio_parcial_falla_como_incomplete():
    parcial = {CLIENT_ID_ENV: CLIENT_ID, REFRESH_TOKEN_ENV: REFRESH_TOKEN}
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        OAuthRefreshTokenProvider.desde_entorno(parcial)
    assert error.value.code == "workspace_auth_config_incomplete"


def test_desde_entorno_completo_construye_provider():
    proveedor = OAuthRefreshTokenProvider.desde_entorno(env_oauth_completo())
    assert isinstance(proveedor, OAuthRefreshTokenProvider)


def test_factory_prefiere_refresh_token_cuando_el_trio_esta_completo():
    proveedor = construir_token_provider(env_oauth_completo())
    assert isinstance(proveedor, OAuthRefreshTokenProvider)


def test_factory_cae_al_token_de_entorno_sin_config_oauth():
    proveedor = construir_token_provider({})
    assert isinstance(proveedor, TokenEntornoProvider)


def test_factory_no_esconde_un_trio_a_medias():
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        construir_token_provider({CLIENT_ID_ENV: CLIENT_ID})
    assert error.value.code == "workspace_auth_config_incomplete"


def test_repr_no_expone_los_secretos():
    proveedor = provider_con(TransporteCaptura())
    representacion = repr(proveedor)
    assert CLIENT_ID not in representacion
    assert CLIENT_SECRET not in representacion
    assert REFRESH_TOKEN not in representacion
    assert "redacted" in representacion
