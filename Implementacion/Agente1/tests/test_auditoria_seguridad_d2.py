"""Auditoría de seguridad D2/D3: cada uno de los seis controles falla cuando
debe (secreto en logs, recurso fuera de allowlist, endpoint de distribución,
revocación que no bloquea, salida sin marca de borrador) y un manifest que no
cumple el contrato da INVALID, nunca PASS."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agente1.auditoria_d2 import WORKSPACE_HOSTS, auditar_manifest
from agente1.google_workspace import DOCS_HOST, DRIVE_HOST, SHEETS_HOST

ROOT = Path(__file__).parents[1]


def _manifest_seguro() -> dict[str, object]:
    return {
        "schema_version": "security-d2-manifest-v1",
        "run_id": "D2-SYN-001",
        "mode": "offline_fake",
        "allowlist": {
            "spreadsheet": ["sheet-permitida"],
            "folder": ["folder-permitida"],
            "template": ["template-permitida"],
        },
        "sensitive": {
            "tokens": ["token-ultrasecreto"],
            "prompts": ["prompt completo privado"],
            "contacts": ["persona@fie.undef.edu.ar"],
            "bodies": ["cuerpo remoto privado"],
        },
        "resources": [
            {"kind": "spreadsheet", "id": "sheet-permitida"},
            {"kind": "folder", "id": "folder-permitida"},
            {"kind": "template", "id": "template-permitida"},
        ],
        "http_calls": [
            {
                "method": "GET",
                "host": "sheets.googleapis.com",
                "target": "/v4/spreadsheets/sheet-permitida/values/solicitudes",
            },
            {
                "method": "POST",
                "host": "docs.googleapis.com",
                "target": "/v1/documents/doc-borrador:batchUpdate",
            },
        ],
        "logs": [
            {"event": "source_read", "resource_hash": "a" * 64},
            {"event": "draft_saved", "reference_hash": "b" * 64},
        ],
        "remote_errors": [{"code": "workspace_auth_denied"}],
        "outputs": [
            {
                "status": "PENDIENTE_VALIDACION",
                "content": "# BORRADOR — NO PUBLICAR\n\nTexto sintético.",
            }
        ],
        "revocation_probe": {
            "simulated": True,
            "result": "BLOCKED",
            "error_code": "workspace_auth_denied",
            "draft_created": False,
        },
    }


def test_manifest_seguro_produce_reporte_redactado_sin_datos_sensibles() -> None:
    manifest = _manifest_seguro()

    reporte = auditar_manifest(manifest)

    assert reporte["status"] == "PASS"
    assert reporte["run_id_hash"] is not None
    assert all(check["passed"] for check in reporte["checks"])
    serializado = json.dumps(reporte, ensure_ascii=False)
    for secreto in (
        "token-ultrasecreto",
        "prompt completo privado",
        "persona@fie.undef.edu.ar",
        "cuerpo remoto privado",
        "sheet-permitida",
        "folder-permitida",
        "template-permitida",
        "doc-borrador",
        "Texto sintético",
    ):
        assert secreto not in serializado


@pytest.mark.parametrize(
    ("mutar", "check_id"),
    [
        (
            lambda m: m["logs"].append(
                {"event": "bad", "detail": "Bearer token-ultrasecreto"}
            ),
            "logs_redacted",
        ),
        (
            lambda m: m["resources"].append(
                {"kind": "spreadsheet", "id": "sheet-no-permitida"}
            ),
            "resources_allowlisted",
        ),
        (
            lambda m: m["remote_errors"].append(
                {"code": "remote_error", "detail": "cuerpo remoto privado"}
            ),
            "remote_errors_redacted",
        ),
        (
            lambda m: m["http_calls"].append(
                {
                    "method": "POST",
                    "host": "www.googleapis.com",
                    "target": "/drive/v3/files/doc/permissions",
                }
            ),
            "no_distribution_endpoints",
        ),
        (
            lambda m: m["revocation_probe"].update({"result": "ALLOWED"}),
            "revocation_blocks",
        ),
        (
            lambda m: m["outputs"].append(
                {"status": "PUBLICADO", "content": "Contenido público"}
            ),
            "outputs_are_drafts",
        ),
    ],
)
def test_invariantes_fallan_de_forma_independiente(mutar, check_id: str) -> None:
    manifest = _manifest_seguro()
    mutar(manifest)

    reporte = auditar_manifest(manifest)

    assert reporte["status"] == "FAIL"
    checks = {check["id"]: check for check in reporte["checks"]}
    assert checks[check_id]["passed"] is False


def test_logs_rechazan_campos_sensibles_aunque_el_valor_no_este_declarado() -> None:
    manifest = _manifest_seguro()
    manifest["logs"].append({"event": "bad", "access_token": "otro-valor"})

    reporte = auditar_manifest(manifest)

    checks = {check["id"]: check for check in reporte["checks"]}
    assert checks["logs_redacted"]["passed"] is False


def test_errores_remotos_solo_aceptan_codigo_sin_detalle() -> None:
    manifest = _manifest_seguro()
    manifest["remote_errors"] = [
        {"code": "workspace_unavailable", "detail": "mensaje remoto inocuo"}
    ]

    reporte = auditar_manifest(manifest)

    checks = {check["id"]: check for check in reporte["checks"]}
    assert checks["remote_errors_redacted"]["passed"] is False


def test_http_rechaza_hosts_no_workspace_aunque_el_path_no_diga_publicar() -> None:
    manifest = _manifest_seguro()
    manifest["http_calls"].append(
        {"method": "POST", "host": "example.invalid", "target": "/collect"}
    )

    reporte = auditar_manifest(manifest)

    checks = {check["id"]: check for check in reporte["checks"]}
    assert checks["no_distribution_endpoints"]["passed"] is False


def test_manifest_invalido_falla_cerrado_sin_reflejar_el_payload() -> None:
    reporte = auditar_manifest(
        {"schema_version": "otra", "run_id": "token-ultrasecreto"}
    )

    assert reporte == {
        "schema_version": "security-d2-report-v1",
        "status": "INVALID",
        "run_id_hash": None,
        "checks": [],
        "error_code": "manifest_contract_invalid",
    }


def test_check_de_endpoints_no_se_elude_con_mayusculas_o_query() -> None:
    manifest = _manifest_seguro()
    manifest["http_calls"].append(
        {
            "method": "POST",
            "host": "WWW.GOOGLEAPIS.COM",
            "target": "/drive/v3/files/doc/Permissions?sendNotificationEmail=false",
        }
    )

    reporte = auditar_manifest(manifest)

    checks = {check["id"]: check for check in reporte["checks"]}
    assert checks["no_distribution_endpoints"]["passed"] is False


def test_allowlist_de_hosts_reutiliza_constantes_del_adapter_productivo() -> None:
    assert WORKSPACE_HOSTS == {SHEETS_HOST, DOCS_HOST, DRIVE_HOST}
    assert DRIVE_HOST == "www.googleapis.com"

    manifest = _manifest_seguro()
    manifest["http_calls"].append(
        {
            "method": "POST",
            "host": "drive.googleapis.com",
            "target": "/drive/v3/files/template/copy",
        }
    )

    reporte = auditar_manifest(manifest)
    checks = {check["id"]: check for check in reporte["checks"]}
    assert checks["no_distribution_endpoints"]["passed"] is False


def test_cli_guarda_reporte_redactado_y_devuelve_cero(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    report_path = tmp_path / "report.json"
    manifest_path.write_text(
        json.dumps(_manifest_seguro(), ensure_ascii=False), encoding="utf-8"
    )
    env = os.environ.copy()
    env["PYTHONPYCACHEPREFIX"] = str(tmp_path / "pycache")

    proceso = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "auditar_seguridad_d2.py"),
            "--manifest",
            str(manifest_path),
            "--reporte",
            str(report_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert proceso.returncode == 0, proceso.stderr
    assert json.loads(proceso.stdout) == {"status": "PASS"}
    reporte = report_path.read_text(encoding="utf-8")
    assert json.loads(reporte)["status"] == "PASS"
    assert "token-ultrasecreto" not in reporte


def test_cli_es_offline_y_rechaza_manifest_live(tmp_path: Path) -> None:
    manifest = _manifest_seguro()
    manifest["mode"] = "live"
    manifest_path = tmp_path / "manifest-live.json"
    report_path = tmp_path / "report.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    proceso = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "auditar_seguridad_d2.py"),
            "--manifest",
            str(manifest_path),
            "--reporte",
            str(report_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proceso.returncode == 2
    assert json.loads(report_path.read_text(encoding="utf-8"))["status"] == "INVALID"


# --- La única excepción de distribución: `gmail.send` con lista activa (D12) ---


def _llamada_gmail_send() -> dict[str, str]:
    return {
        "method": "POST",
        "host": "gmail.googleapis.com",
        "target": "/gmail/v1/users/me/messages/send",
    }


def _check_distribucion(reporte: dict[str, object]) -> bool:
    checks = {check["id"]: check for check in reporte["checks"]}
    return checks["no_distribution_endpoints"]["passed"]


def test_gmail_send_pasa_solo_si_el_manifest_declara_lista_activa() -> None:
    manifest = _manifest_seguro()
    manifest["http_calls"].append(_llamada_gmail_send())
    manifest["gmail_send"] = {"test_list_active": True}

    assert _check_distribucion(auditar_manifest(manifest)) is True


def test_gmail_send_sin_declaracion_o_sin_lista_activa_falla() -> None:
    for declaracion in (
        None,
        {"test_list_active": False},
    ):
        manifest = _manifest_seguro()
        manifest["http_calls"].append(_llamada_gmail_send())
        if declaracion is not None:
            manifest["gmail_send"] = declaracion

        reporte = auditar_manifest(manifest)

        assert reporte["status"] == "FAIL"
        assert _check_distribucion(reporte) is False


def test_gmail_send_con_lista_activa_y_hash_de_lista_pasa() -> None:
    manifest = _manifest_seguro()
    manifest["http_calls"].append(_llamada_gmail_send())
    manifest["gmail_send"] = {
        "test_list_active": True,
        "recipients_hash": "c" * 64,
    }

    assert _check_distribucion(auditar_manifest(manifest)) is True


@pytest.mark.parametrize(
    "llamada",
    [
        # La lectura del buzón propio es otra excepción (ADR 0004), independiente
        # de la lista: se cubre en `test_buzon_gmail.py`. Otras rutas de Gmail
        # no son la excepción de D12.
        {"method": "GET", "host": "gmail.googleapis.com", "target": "/gmail/v1/users/me/messages/send"},
        {"method": "POST", "host": "gmail.googleapis.com", "target": "/gmail/v1/users/me/messages/send?x=1"},
        {"method": "POST", "host": "gmail.googleapis.com", "target": "/gmail/v1/users/otro/messages/send"},
        {"method": "POST", "host": "gmail.googleapis.com", "target": "/gmail/v1/users/me/messages/send/extra"},
        {"method": "PUT", "host": "gmail.googleapis.com", "target": "/gmail/v1/users/me/messages/send"},
        # El host viejo de correo y cualquier otro servicio siguen prohibidos.
        {"method": "POST", "host": "mail.googleapis.com", "target": "/v1/send"},
        {"method": "POST", "host": "www.googleapis.com", "target": "/gmail/v1/users/me/messages/send"},
    ],
)
def test_ninguna_otra_llamada_de_distribucion_pasa_aun_con_lista_activa(
    llamada: dict[str, str],
) -> None:
    manifest = _manifest_seguro()
    manifest["http_calls"].append(_llamada_gmail_send())
    manifest["http_calls"].append(llamada)
    manifest["gmail_send"] = {"test_list_active": True}

    reporte = auditar_manifest(manifest)

    assert reporte["status"] == "FAIL"
    assert _check_distribucion(reporte) is False


@pytest.mark.parametrize(
    "declaracion",
    [
        "test_list_active",
        {"test_list_active": "yes"},
        {"test_list_active": True, "sorpresa": 1},
        {"recipients_hash": "no-es-hex"},
        {"test_list_active": True, "recipients_hash": "C" * 64},
        {"test_list_active": True, "recipients_hash": 7},
    ],
)
def test_la_declaracion_gmail_del_manifest_es_de_contrato_cerrado(
    declaracion: object,
) -> None:
    manifest = _manifest_seguro()
    manifest["http_calls"].append(_llamada_gmail_send())
    manifest["gmail_send"] = declaracion

    reporte = auditar_manifest(manifest)

    # Contrato inválido: fail-closed, no un check «con matices».
    assert reporte["status"] == "INVALID"
    assert reporte["checks"] == []


# --- La otra cara de la excepción: modo producción con lista aprobada (#141) ---
# El mismo endpoint de `gmail.send` se admite con una declaración explícita de
# modo producción. El contrato sigue cerrado: los dos modos no pueden estar
# activos a la vez, y sin declaración el envío sigue prohibido.


def test_gmail_send_pasa_con_modo_produccion_declarado() -> None:
    manifest = _manifest_seguro()
    manifest["http_calls"].append(_llamada_gmail_send())
    manifest["gmail_send"] = {"production_active": True}

    assert _check_distribucion(auditar_manifest(manifest)) is True


def test_gmail_send_produccion_admite_hash_de_la_lista_aprobada() -> None:
    manifest = _manifest_seguro()
    manifest["http_calls"].append(_llamada_gmail_send())
    manifest["gmail_send"] = {
        "production_active": True,
        "recipients_hash": "d" * 64,
    }

    assert _check_distribucion(auditar_manifest(manifest)) is True


def test_gmail_send_con_modo_produccion_inactivo_sigue_fallando() -> None:
    manifest = _manifest_seguro()
    manifest["http_calls"].append(_llamada_gmail_send())
    manifest["gmail_send"] = {"production_active": False}

    reporte = auditar_manifest(manifest)

    assert reporte["status"] == "FAIL"
    assert _check_distribucion(reporte) is False


def test_los_dos_modos_activos_a_la_vez_son_contrato_invalido() -> None:
    manifest = _manifest_seguro()
    manifest["http_calls"].append(_llamada_gmail_send())
    manifest["gmail_send"] = {
        "test_list_active": True,
        "production_active": True,
    }

    reporte = auditar_manifest(manifest)

    # Ambigüedad bajo la que se envió: fail-closed, no un check con matices.
    assert reporte["status"] == "INVALID"
    assert reporte["checks"] == []


@pytest.mark.parametrize(
    "declaracion",
    [
        {"production_active": "yes"},
        {"test_list_active": None},
        {"production_active": None},
        {"production_active": True, "sorpresa": 1},
        {"recipients_hash": "c" * 64},
        {},
    ],
)
def test_la_declaracion_de_produccion_tambien_es_de_contrato_cerrado(
    declaracion: object,
) -> None:
    manifest = _manifest_seguro()
    manifest["http_calls"].append(_llamada_gmail_send())
    manifest["gmail_send"] = declaracion

    reporte = auditar_manifest(manifest)

    assert reporte["status"] == "INVALID"
    assert reporte["checks"] == []


def test_produccion_no_habilita_ninguna_otra_ruta_de_gmail() -> None:
    manifest = _manifest_seguro()
    manifest["http_calls"].append(_llamada_gmail_send())
    manifest["http_calls"].append(
        {
            "method": "POST",
            "host": "gmail.googleapis.com",
            "target": "/gmail/v1/users/me/messages/abc/modify",
        }
    )
    manifest["gmail_send"] = {"production_active": True}

    reporte = auditar_manifest(manifest)

    assert reporte["status"] == "FAIL"
    assert _check_distribucion(reporte) is False
