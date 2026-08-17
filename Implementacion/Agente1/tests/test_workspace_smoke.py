import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "workspace_smoke.py"
ENV_VALIDO = {
    "AGENTE1_WORKSPACE_AMBIENTE": "D2",
    "AGENTE1_WORKSPACE_SPREADSHEET_ID": "sheet_ID-123",
    "AGENTE1_WORKSPACE_RANGO_A1": "'Solicitudes SEU'!A1:I200",
    "AGENTE1_WORKSPACE_FOLDER_ID": "folder_ID-456",
    "AGENTE1_WORKSPACE_TEMPLATE_ID": "template_ID-789",
    "AGENTE1_WORKSPACE_TIMEOUT_S": "10",
    "AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES": "1048576",
}


def ejecutar(*args: str, env: dict[str, str] | None = None):
    entorno = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "src"),
        **(env or {}),
    }
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        env=entorno,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def test_smoke_por_defecto_solo_valida_config_y_no_requiere_token():
    resultado = ejecutar(env=ENV_VALIDO)

    assert resultado.returncode == 0
    salida = json.loads(resultado.stdout)
    assert salida["modo"] == "validacion"
    assert salida["resultado"] == "configuracion_valida"
    assert salida["ambiente"] == "D2"
    assert resultado.stderr == ""
    serializado = resultado.stdout
    for secreto in ("sheet_ID-123", "folder_ID-456", "template_ID-789"):
        assert secreto not in serializado


def test_smoke_config_incompleta_falla_cerrado_y_sin_valores():
    resultado = ejecutar(env={"AGENTE1_WORKSPACE_AMBIENTE": "D2"})

    assert resultado.returncode == 2
    salida = json.loads(resultado.stdout)
    assert salida == {"resultado": "workspace_config_incomplete"}


def test_modo_live_exige_flag_explicito_e_id_pero_token_no_es_flag():
    ayuda = ejecutar("--help", env=ENV_VALIDO)
    assert ayuda.returncode == 0
    assert "--access-token" not in ayuda.stdout
    assert "--token" not in ayuda.stdout

    sin_id = ejecutar("--live", env=ENV_VALIDO)
    assert sin_id.returncode == 2
    assert json.loads(sin_id.stdout) == {"resultado": "live_request_invalid"}


def test_modo_live_sin_token_falla_antes_de_red_y_no_filtra_ids():
    env = {**ENV_VALIDO, "AGENTE1_WORKSPACE_ACCESS_TOKEN": ""}
    resultado = ejecutar("--live", "--id-solicitud", "SYN-001", env=env)

    assert resultado.returncode == 3
    salida = json.loads(resultado.stdout)
    assert salida["resultado"] == "workspace_auth_unavailable"
    assert "SYN-001" not in resultado.stdout
    assert "sheet_ID-123" not in resultado.stdout


def test_smoke_no_acepta_argumentos_desconocidos_ni_imprime_entorno():
    resultado = ejecutar("--access-token", "TOKEN_ULTRA_SECRETO", env=ENV_VALIDO)

    assert resultado.returncode != 0
    assert "TOKEN_ULTRA_SECRETO" not in resultado.stdout
    assert "TOKEN_ULTRA_SECRETO" not in resultado.stderr
