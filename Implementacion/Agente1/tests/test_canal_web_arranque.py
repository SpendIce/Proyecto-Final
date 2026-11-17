"""Arranque del canal web: credencial de Workspace y versión del agente.

El servidor y el worker del Doc por solicitud (#153) tienen que usar la misma
credencial durable que el resto de los adapters live (`construir_token_provider`,
ADR 0011): cuenta de servicio con delegación y lista cerrada de cuentas
suplantables, o el respaldo OAuth explícito. Un `TokenEntornoProvider` suelto
sólo lee el token efímero y deja el stack sin Doc.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from agente1.google_workspace import MAX_WORKSPACE_RESPONSE_BYTES
from agente1.workspace_auth import (
    IMPERSONATED_ACCOUNT_ENV,
    SERVICE_ACCOUNT_KEY_ENV,
    CuentaServicioDelegadaProvider,
    sha256_cuenta,
)
from agente1.workspace_config import TokenEntornoProvider

ROOT = Path(__file__).resolve().parents[1]
CUENTA = "bot_ia1@fie.undef.edu.ar"


def _cargar_script(nombre: str):
    spec = importlib.util.spec_from_file_location(
        f"{nombre}_test", ROOT / "scripts" / f"{nombre}.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


def _entorno(tmp_path: Path, *, cuenta: str = CUENTA) -> dict[str, str]:
    padron = tmp_path / "padron.csv"
    padron.write_text(
        "correo,rol\ncoordinador@example.invalid,coordinador_seu\n",
        encoding="utf-8",
    )
    return {
        "AGENTE1_POSTGRES_DSN": "postgresql://no-se-conecta/agente1",
        "AGENTE1_PADRON_ROLES_CSV": str(padron),
        "AGENTE1_TABLA": str(ROOT / "data" / "actividades_sinteticas.csv"),
        "AGENTE1_WEB_MODO_PRUEBA": "si",
        "AGENTE1_WEB_COOKIE_SECURE": "no",
        "AGENTE1_WEB_DOCS": "si",
        "AGENTE1_ESTADO": str(tmp_path / "estado"),
        "AGENTE1_WORKSPACE_AMBIENTE": "D2",
        "AGENTE1_WORKSPACE_SPREADSHEET_ID": "sheet_1",
        "AGENTE1_WORKSPACE_RANGO_A1": "'Respuestas'!A1:I500",
        "AGENTE1_WORKSPACE_FOLDER_ID": "folder_1",
        "AGENTE1_WORKSPACE_TEMPLATE_ID": "template_1",
        "AGENTE1_WORKSPACE_TIMEOUT_S": "10",
        "AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES": str(
            MAX_WORKSPACE_RESPONSE_BYTES
        ),
        SERVICE_ACCOUNT_KEY_ENV: str(tmp_path / "clave.json"),
        IMPERSONATED_ACCOUNT_ENV: cuenta,
    }


def _capturar_destino(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    capturado: dict[str, Any] = {}

    class DestinoFalso:
        def __init__(self, **kwargs: Any) -> None:
            capturado.update(kwargs)

    monkeypatch.setattr(
        "agente1.google_workspace.GoogleDocsDestinoPorMarca", DestinoFalso
    )
    return capturado


def test_servidor_web_usa_la_credencial_durable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    capturado = _capturar_destino(monkeypatch)

    def crear_app_falso(**kwargs: Any) -> object:
        capturado["exportador"] = kwargs["exportador"]
        return object()

    monkeypatch.setattr("agente1.web.app.crear_app", crear_app_falso)
    modulo = _cargar_script("servidor_web")

    codigo = modulo.main(["--una-ruta"], environ=_entorno(tmp_path))

    assert codigo == 0
    proveedor = capturado["token_provider"]
    assert isinstance(proveedor, CuentaServicioDelegadaProvider)
    assert not isinstance(proveedor, TokenEntornoProvider)
    assert proveedor.cuenta_suplantada_sha256 == sha256_cuenta(CUENTA)


def test_worker_canal_web_usa_la_credencial_durable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    capturado = _capturar_destino(monkeypatch)
    monkeypatch.setattr(
        "agente1.web.worker.correr_una_vez", lambda **_kwargs: None
    )
    modulo = _cargar_script("worker_canal_web")

    codigo = modulo.main(
        [
            "--tabla",
            str(ROOT / "data" / "actividades_sinteticas.csv"),
            "--salida",
            str(tmp_path / "salida"),
            "--generador-salida",
            "texto fijo",
            "--destino-docs",
            "--una-vez",
        ],
        environ=_entorno(tmp_path),
    )

    assert codigo == 0
    proveedor = capturado["token_provider"]
    assert isinstance(proveedor, CuentaServicioDelegadaProvider)
    assert proveedor.cuenta_suplantada_sha256 == sha256_cuenta(CUENTA)


def test_servidor_web_rechaza_cuenta_fuera_de_la_lista(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    modulo = _cargar_script("servidor_web")

    codigo = modulo.main(
        ["--una-ruta"],
        environ=_entorno(tmp_path, cuenta="otra@fie.undef.edu.ar"),
    )

    assert codigo == 2
    salida = json.loads(capsys.readouterr().out)
    assert salida == {
        "status": "INVALID",
        "error_code": "web_workspace_config_invalid",
    }


def test_worker_canal_web_genera_con_ollama_sin_thinking(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Con thinking, gemma4 gasta el `num_predict` antes de responder.

    Mismo defecto que el scheduler corrigió en la 0.5.3: el primer pedido
    real del canal web en el servidor (16/11) terminó en `error_generacion`
    a los 133 s con la respuesta vacía.
    """
    capturado: dict[str, Any] = {}

    class GeneradorFalso:
        def __init__(self, **kwargs: Any) -> None:
            capturado.update(kwargs)

    monkeypatch.setattr("agente1.ollama.OllamaGenerator", GeneradorFalso)
    monkeypatch.setattr(
        "agente1.web.worker.correr_una_vez", lambda **_kwargs: None
    )
    modulo = _cargar_script("worker_canal_web")

    codigo = modulo.main(
        [
            "--tabla",
            str(ROOT / "data" / "actividades_sinteticas.csv"),
            "--salida",
            str(tmp_path / "salida"),
            "--ollama-model",
            "gemma4:e4b",
            "--destino-fake",
            "--una-vez",
        ],
        environ=_entorno(tmp_path),
    )

    assert codigo == 0
    assert capturado["modelo"] == "gemma4:e4b"
    assert capturado["think"] is False


def test_destino_docs_deja_en_stderr_el_codigo_del_token(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`workspace_auth_unavailable` sola no distingue la causa en el servidor."""
    from agente1.destinos import DestinoBorradoresError
    from agente1.google_workspace import GoogleDocsDestinoPorMarca
    from agente1.workspace_config import ConfiguracionWorkspaceError

    class ProveedorQueFalla:
        def obtener_access_token(self) -> str:
            raise ConfiguracionWorkspaceError("workspace_key_unreadable")

    destino = GoogleDocsDestinoPorMarca(
        plantilla_id="plantilla_1",
        carpeta_id="carpeta_1",
        token_provider=ProveedorQueFalla(),
        timeout_s=5,
    )
    with pytest.raises(DestinoBorradoresError) as error:
        destino._obtener_token()
    assert error.value.code == "workspace_auth_unavailable"
    assert "workspace_key_unreadable" in capsys.readouterr().err


def test_worker_canal_web_ajusta_con_mas_margen_de_tokens(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """El ajuste reescribe una pieza entera: con el `num_predict` de la
    generación (512) el modelo puede cortar la salida. Usa el techo."""
    creados: list[dict[str, Any]] = []
    pasado: dict[str, Any] = {}

    class GeneradorFalso:
        def __init__(self, **kwargs: Any) -> None:
            creados.append(kwargs)

    def correr(**kwargs: Any) -> None:
        pasado.update(kwargs)

    monkeypatch.setattr("agente1.ollama.OllamaGenerator", GeneradorFalso)
    monkeypatch.setattr("agente1.web.worker.correr_una_vez", correr)
    modulo = _cargar_script("worker_canal_web")

    codigo = modulo.main(
        [
            "--tabla",
            str(ROOT / "data" / "actividades_sinteticas.csv"),
            "--salida",
            str(tmp_path / "salida"),
            "--ollama-model",
            "gemma4:e4b",
            "--destino-fake",
            "--una-vez",
        ],
        environ=_entorno(tmp_path),
    )

    assert codigo == 0
    from agente1.ollama import MAX_OLLAMA_NUM_PREDICT, MAX_OLLAMA_TIMEOUT_S

    ajuste = [c for c in creados if c.get("num_predict") == MAX_OLLAMA_NUM_PREDICT]
    assert len(ajuste) == 1
    assert ajuste[0]["think"] is False
    assert ajuste[0]["timeout_s"] == MAX_OLLAMA_TIMEOUT_S
    assert pasado["generator_ajuste"] is not pasado["generator"]
