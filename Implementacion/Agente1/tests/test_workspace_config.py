import json

import pytest

from agente1.workspace_config import (
    ConfiguracionWorkspaceError,
    TokenEntornoProvider,
    cargar_configuracion_workspace,
)


ENV_VALIDO = {
    "AGENTE1_WORKSPACE_AMBIENTE": "D2",
    "AGENTE1_WORKSPACE_SPREADSHEET_ID": "sheet_ID-123",
    "AGENTE1_WORKSPACE_RANGO_A1": "'Solicitudes SEU'!A1:I200",
    "AGENTE1_WORKSPACE_FOLDER_ID": "folder_ID-456",
    "AGENTE1_WORKSPACE_TEMPLATE_ID": "template_ID-789",
    "AGENTE1_WORKSPACE_TIMEOUT_S": "10",
    "AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES": "1048576",
}


def test_carga_config_completa_y_expone_solo_resumen_redactado():
    config = cargar_configuracion_workspace(ENV_VALIDO)

    assert config.ambiente == "D2"
    assert config.spreadsheet_id == "sheet_ID-123"
    assert config.rango_a1 == "'Solicitudes SEU'!A1:I200"
    assert config.folder_id == "folder_ID-456"
    assert config.template_id == "template_ID-789"
    assert config.timeout_s == 10.0
    assert config.max_response_bytes == 1_048_576
    assert config.sheets_host == "sheets.googleapis.com"
    assert config.docs_host == "docs.googleapis.com"
    assert config.drive_host == "www.googleapis.com"

    resumen = json.dumps(config.resumen_seguro(), sort_keys=True)
    for secreto in ("sheet_ID-123", "folder_ID-456", "template_ID-789"):
        assert secreto not in resumen
    assert "D2" in resumen
    assert "sheets.googleapis.com" in resumen


@pytest.mark.parametrize(
    ("clave", "valor"),
    [
        ("AGENTE1_WORKSPACE_AMBIENTE", "produccion"),
        ("AGENTE1_WORKSPACE_AMBIENTE", "D2\nD3"),
        ("AGENTE1_WORKSPACE_SPREADSHEET_ID", "https://evil.invalid/id"),
        ("AGENTE1_WORKSPACE_FOLDER_ID", ""),
        ("AGENTE1_WORKSPACE_TEMPLATE_ID", "id con espacios"),
        ("AGENTE1_WORKSPACE_RANGO_A1", ""),
        ("AGENTE1_WORKSPACE_RANGO_A1", "Hoja!A1:I20\nAuthorization: secreto"),
        ("AGENTE1_WORKSPACE_RANGO_A1", "https://evil.invalid/A1:I20"),
        ("AGENTE1_WORKSPACE_TIMEOUT_S", "0"),
        ("AGENTE1_WORKSPACE_TIMEOUT_S", "nan"),
        ("AGENTE1_WORKSPACE_TIMEOUT_S", "121"),
        ("AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES", "0"),
        ("AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES", "1048577"),
    ],
)
def test_rechaza_configuracion_invalida_sin_repetir_valores(clave, valor):
    env = {**ENV_VALIDO, clave: valor}

    with pytest.raises(ConfiguracionWorkspaceError) as error:
        cargar_configuracion_workspace(env)

    assert error.value.code == "workspace_config_invalid"
    if valor:
        assert valor not in str(error.value)


def test_rechaza_config_incompleta_con_codigo_cerrado():
    env = {**ENV_VALIDO}
    del env["AGENTE1_WORKSPACE_FOLDER_ID"]

    with pytest.raises(ConfiguracionWorkspaceError) as error:
        cargar_configuracion_workspace(env)

    assert error.value.code == "workspace_config_incomplete"
    assert "FOLDER" not in str(error.value)


def test_rechaza_variables_desconocidas_del_namespace_para_evitar_typos():
    env = {**ENV_VALIDO, "AGENTE1_WORKSPACE_SPREEDSHEET_ID": "oops"}

    with pytest.raises(ConfiguracionWorkspaceError) as error:
        cargar_configuracion_workspace(env)

    assert error.value.code == "workspace_config_unknown_key"
    assert "SPREEDSHEET" not in str(error.value)


def test_token_provider_lee_en_invocacion_y_nunca_lo_expone(monkeypatch):
    monkeypatch.setenv("AGENTE1_WORKSPACE_ACCESS_TOKEN", "TOKEN_ULTRA_SECRETO")
    provider = TokenEntornoProvider()

    assert provider.obtener_access_token() == "TOKEN_ULTRA_SECRETO"
    assert "TOKEN_ULTRA_SECRETO" not in repr(provider)


@pytest.mark.parametrize("token", ["", " token", "token\nX-Secreto: valor", "x" * 8193])
def test_token_provider_rechaza_valores_inseguros_con_error_redactado(monkeypatch, token):
    monkeypatch.setenv("AGENTE1_WORKSPACE_ACCESS_TOKEN", token)

    with pytest.raises(ConfiguracionWorkspaceError) as error:
        TokenEntornoProvider().obtener_access_token()

    assert error.value.code == "workspace_token_unavailable"
    if token:
        assert token not in str(error.value)


def test_token_no_puede_configurarse_con_nombre_arbitrario():
    with pytest.raises(TypeError):
        TokenEntornoProvider("OTRO_TOKEN")
