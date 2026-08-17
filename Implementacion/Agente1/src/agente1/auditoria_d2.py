"""Auditoría offline y fail-closed de invariantes de seguridad D2/D3.

El reporte deliberadamente no replica el manifest: sólo expone códigos, conteos y
hashes opacos para que sea recuperable sin transformarse en un nuevo canal de fuga.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import re
from typing import Any

from .google_workspace import DOCS_HOST, DRIVE_HOST, SHEETS_HOST


MANIFEST_SCHEMA = "security-d2-manifest-v1"
REPORT_SCHEMA = "security-d2-report-v1"
BORRADOR_MARKER = "# BORRADOR — NO PUBLICAR\n\n"
SAFE_OUTPUT_STATUS = "PENDIENTE_VALIDACION"
RESOURCE_KINDS = frozenset({"spreadsheet", "folder", "template"})
WORKSPACE_HOSTS = frozenset({SHEETS_HOST, DOCS_HOST, DRIVE_HOST})
SAFE_REVOCATION_CODES = frozenset(
    {"workspace_auth_denied", "workspace_auth_unavailable", "docs_auth_denied"}
)
_EMAIL_RE = re.compile(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+\S+")
_DISTRIBUTION_RE = re.compile(
    r"(?i)(?:/permissions(?:[/?]|$)|:send(?:[/?]|$)|:publish(?:[/?]|$)|"
    r"/publish(?:[/?]|$)|/share(?:[/?]|$)|/messages(?:[/?]|$))"
)
_DISTRIBUTION_HOST_RE = re.compile(
    r"(?i)(?:instagram|facebook|linkedin|twitter|x\.com|mail\.googleapis)"
)
_SENSITIVE_KEY_RE = re.compile(
    r"(?i)(?:authorization|access_?token|refresh_?token|prompt|contact|body|content)"
)
_SAFE_ERROR_CODE_RE = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")


def auditar_manifest(manifest: object) -> dict[str, object]:
    """Valida un manifest de observaciones ya sanitizado, sin ejecutar red."""
    if not _contrato_basico_valido(manifest):
        return _reporte_invalido()

    assert isinstance(manifest, dict)
    run_id = manifest["run_id"]
    sensitive_values = _valores_sensibles(manifest["sensitive"])
    if sensitive_values is None:
        return _reporte_invalido()

    checks = [
        _check(
            "logs_redacted",
            _seccion_redactada(manifest["logs"], sensitive_values),
        ),
        _check(
            "resources_allowlisted",
            _recursos_permitidos(manifest["resources"], manifest["allowlist"]),
        ),
        _check(
            "remote_errors_redacted",
            _errores_remotos_redactados(
                manifest["remote_errors"], sensitive_values
            ),
        ),
        _check(
            "no_distribution_endpoints",
            _sin_endpoints_distribucion(manifest["http_calls"]),
        ),
        _check(
            "revocation_blocks",
            _revocacion_bloquea(manifest["revocation_probe"]),
        ),
        _check(
            "outputs_are_drafts",
            _salidas_son_borradores(manifest["outputs"]),
        ),
    ]
    return {
        "schema_version": REPORT_SCHEMA,
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "run_id_hash": _hash_opaco(run_id),
        "checks": checks,
        "error_code": None,
    }


def serializar_reporte(reporte: Mapping[str, object]) -> str:
    """Serializa determinísticamente para guardar evidencia versionable."""
    return json.dumps(reporte, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _reporte_invalido() -> dict[str, object]:
    return {
        "schema_version": REPORT_SCHEMA,
        "status": "INVALID",
        "run_id_hash": None,
        "checks": [],
        "error_code": "manifest_contract_invalid",
    }


def _contrato_basico_valido(manifest: object) -> bool:
    if not isinstance(manifest, dict):
        return False
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        return False
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id or len(run_id) > 256:
        return False
    if manifest.get("mode") != "offline_fake":
        return False
    for key in (
        "allowlist",
        "sensitive",
        "resources",
        "http_calls",
        "logs",
        "remote_errors",
        "outputs",
        "revocation_probe",
    ):
        if key not in manifest:
            return False
    return (
        isinstance(manifest["allowlist"], dict)
        and isinstance(manifest["sensitive"], dict)
        and all(
            isinstance(manifest[key], list)
            for key in (
                "resources",
                "http_calls",
                "logs",
                "remote_errors",
                "outputs",
            )
        )
        and isinstance(manifest["revocation_probe"], dict)
    )


def _valores_sensibles(sensitive: object) -> tuple[str, ...] | None:
    if not isinstance(sensitive, dict):
        return None
    if set(sensitive) != {"tokens", "prompts", "contacts", "bodies"}:
        return None
    valores: list[str] = []
    for grupo in sensitive.values():
        if not isinstance(grupo, list) or any(
            not isinstance(valor, str) or not valor for valor in grupo
        ):
            return None
        valores.extend(grupo)
    return tuple(valores)


def _seccion_redactada(section: object, sensitive_values: Sequence[str]) -> bool:
    if _contiene_clave_sensible(section):
        return False
    for valor in _strings(section):
        if _BEARER_RE.search(valor) or _EMAIL_RE.search(valor):
            return False
        if any(secreto in valor for secreto in sensitive_values):
            return False
    return True


def _errores_remotos_redactados(
    remote_errors: object, sensitive_values: Sequence[str]
) -> bool:
    if not isinstance(remote_errors, list):
        return False
    if not _seccion_redactada(remote_errors, sensitive_values):
        return False
    return all(
        isinstance(error, dict)
        and set(error) == {"code"}
        and isinstance(error["code"], str)
        and _SAFE_ERROR_CODE_RE.fullmatch(error["code"]) is not None
        for error in remote_errors
    )


def _recursos_permitidos(resources: object, allowlist: object) -> bool:
    if not isinstance(resources, list) or not isinstance(allowlist, dict):
        return False
    if set(allowlist) != RESOURCE_KINDS:
        return False
    permitidos: dict[str, frozenset[str]] = {}
    for kind in RESOURCE_KINDS:
        values = allowlist.get(kind)
        if not isinstance(values, list) or any(
            not isinstance(value, str) or not value for value in values
        ):
            return False
        permitidos[kind] = frozenset(values)
    for resource in resources:
        if not isinstance(resource, dict) or set(resource) != {"kind", "id"}:
            return False
        kind, resource_id = resource["kind"], resource["id"]
        if (
            not isinstance(kind, str)
            or not isinstance(resource_id, str)
            or kind not in permitidos
            or resource_id not in permitidos[kind]
        ):
            return False
    return True


def _sin_endpoints_distribucion(http_calls: object) -> bool:
    if not isinstance(http_calls, list):
        return False
    for call in http_calls:
        if not isinstance(call, dict):
            return False
        method, host, target = (
            call.get("method"),
            call.get("host"),
            call.get("target"),
        )
        if not all(isinstance(value, str) and value for value in (method, host, target)):
            return False
        normalized_host = host.lower()
        if (
            normalized_host not in WORKSPACE_HOSTS
            or not target.startswith("/")
            or method not in {"GET", "POST"}
            or _DISTRIBUTION_HOST_RE.search(host)
            or _DISTRIBUTION_RE.search(target)
        ):
            return False
    return True


def _revocacion_bloquea(probe: object) -> bool:
    return (
        isinstance(probe, dict)
        and probe.get("simulated") is True
        and probe.get("result") == "BLOCKED"
        and probe.get("error_code") in SAFE_REVOCATION_CODES
        and probe.get("draft_created") is False
    )


def _salidas_son_borradores(outputs: object) -> bool:
    if not isinstance(outputs, list) or not outputs:
        return False
    return all(
        isinstance(output, dict)
        and output.get("status") == SAFE_OUTPUT_STATUS
        and isinstance(output.get("content"), str)
        and output["content"].startswith(BORRADOR_MARKER)
        for output in outputs
    )


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [item for nested in value.values() for item in _strings(nested)]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [item for nested in value for item in _strings(nested)]
    return []


def _contiene_clave_sensible(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            isinstance(key, str) and _SENSITIVE_KEY_RE.search(key)
            or _contiene_clave_sensible(nested)
            for key, nested in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contiene_clave_sensible(nested) for nested in value)
    return False


def _check(check_id: str, passed: bool) -> dict[str, object]:
    return {
        "id": check_id,
        "passed": passed,
        "result_code": "ok" if passed else "invariant_failed",
    }


def _hash_opaco(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
