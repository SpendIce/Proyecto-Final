"""Contratos operativos fail-closed sobre manifests sanitizados.

Este módulo no conoce IDs de Workspace, cuerpos, contactos ni credenciales. Sus
salidas son planes o reportes: nunca publica, comparte, borra ni modifica recursos.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
import re
from typing import Any, Protocol


HEALTH_INPUT_SCHEMA = "agente1-health-input-v1"
HEALTH_REPORT_SCHEMA = "agente1-health-report-v1"
RETENTION_REPORT_SCHEMA = "agente1-retention-plan-v1"
CONSOLIDATED_REPORT_SCHEMA = "agente1-consolidated-report-v1"

_HASH_RE = re.compile(r"[0-9a-f]{64}\Z")
_CODE_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,127}\Z")
_SCHEMA_RE = re.compile(r"evidencia_[a-z0-9_]+_v[0-9]+\Z")
_EMAIL_RE = re.compile(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+\S+")
_SENSITIVE_KEY_RE = re.compile(
    r"(?i)(?:authorization|token|secret|password|contact|content|body|prompt|"
    r"document_?id|spreadsheet_?id|folder_?id|template_?id)"
)
_ARTIFACT_KINDS = frozenset({"contract", "prompt", "dataset", "runtime"})
_ARTIFACT_STATUS = frozenset({"AVAILABLE", "MISSING"})
_PROBE_RESULTS = frozenset({"READABLE", "DENIED", "UNAVAILABLE"})
_RECONCILIATION_STATES = frozenset(
    {"PERSISTIDO", "SIN_REFERENCIA", "REFERENCIADO"}
)
_RETENTION_STATES = frozenset({"CERRADO", "PENDIENTE_VALIDACION"})
_RETENTION_ROOTS = frozenset({"salida", "evidencias"})


class ContratoOperativoInvalido(ValueError):
    """Error público estable sin incluir valores recibidos."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ProbeLectura(Protocol):
    """Única capacidad live admitida por health: una lectura sin argumentos."""

    def probar_lectura(self) -> str: ...


def evaluar_health(
    manifest: object,
    *,
    live: bool = False,
    live_opt_in: bool = False,
    probe: ProbeLectura | None = None,
) -> dict[str, object]:
    """Evalúa salud offline; el probe live requiere doble opt-in y es read-only."""
    if not _health_manifest_valido(manifest):
        raise ContratoOperativoInvalido("health_manifest_invalid")
    assert isinstance(manifest, dict)

    if live and (not live_opt_in or probe is None):
        raise ContratoOperativoInvalido("health_live_not_authorized")

    checks = {
        "artifacts": "PASS"
        if all(item["status"] == "AVAILABLE" for item in manifest["artifacts"])
        else "FAIL",
        "config": "PASS"
        if manifest["config"]["status"] == "VALID"
        and manifest["config"]["resources_configured"] is True
        else "FAIL",
        "runtime": "PASS" if manifest["runtime"]["status"] == "READY" else "FAIL",
    }
    live_result = "NOT_REQUESTED"
    if live:
        assert probe is not None
        try:
            raw_result: object = probe.probar_lectura()
        except Exception:
            raw_result = None
        if isinstance(raw_result, str) and raw_result in _PROBE_RESULTS:
            live_result = raw_result
        else:
            live_result = "UNAVAILABLE"

    passed = all(value == "PASS" for value in checks.values())
    if live:
        passed = passed and live_result == "READABLE"
    return {
        "schema_version": HEALTH_REPORT_SCHEMA,
        "ambiente": manifest["ambiente"],
        "mode": "live_read_only" if live else "offline",
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "live_probe": live_result,
    }


def planificar_reconciliacion(records: object) -> dict[str, object]:
    """Clasifica referencias opacas; deliberadamente no acepta IDs ni acciones."""
    if not isinstance(records, list):
        raise ContratoOperativoInvalido("reconciliation_invalid")
    items: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    for record in records:
        if (
            not isinstance(record, dict)
            or set(record) != {"draft_hash", "manifest_hash", "state"}
            or not _es_hash(record["draft_hash"])
            or not _es_hash(record["manifest_hash"])
            or record["state"] not in _RECONCILIATION_STATES
        ):
            raise ContratoOperativoInvalido("reconciliation_invalid")
        instruction = (
            "REVISAR_MANUAL"
            if record["state"] == "SIN_REFERENCIA"
            else "SIN_ACCION"
        )
        counts[instruction] += 1
        items.append(
            {
                "draft_hash": record["draft_hash"],
                "state": record["state"],
                "instruction": instruction,
            }
        )
    return {
        "schema_version": "agente1-reconciliation-plan-v1",
        "status": "REQUIERE_REVISION"
        if counts["REVISAR_MANUAL"]
        else "SIN_HUERFANOS_DETECTADOS",
        "counts": {
            "REVISAR_MANUAL": counts["REVISAR_MANUAL"],
            "SIN_ACCION": counts["SIN_ACCION"],
        },
        "items": items,
    }


def planificar_retencion(
    base_dir: Path,
    records: object,
    *,
    now: datetime,
    retention_days: int,
) -> dict[str, object]:
    """Produce un dry-run opaco; no ofrece una operación de borrado."""
    if (
        not isinstance(records, list)
        or not isinstance(retention_days, int)
        or isinstance(retention_days, bool)
        or not 1 <= retention_days <= 3650
        or now.tzinfo is None
    ):
        raise ContratoOperativoInvalido("retention_policy_invalid")
    base = base_dir.resolve(strict=True)
    items: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    for record in records:
        if not _retention_record_valido(record):
            raise ContratoOperativoInvalido("retention_record_invalid")
        assert isinstance(record, dict)
        _validar_path_retencion(base, record["relative_path"])
        created_at = _parse_utc(record["created_at"])
        expired = (now.astimezone(UTC) - created_at).days >= retention_days
        if expired and record["state"] == "CERRADO":
            decision, reason = "CANDIDATO_BORRADO_MANUAL", "retention_expired"
        else:
            decision, reason = "CONSERVAR", "retention_active"
        counts[decision] += 1
        items.append(
            {
                "ref_hash": record["ref_hash"],
                "decision": decision,
                "reason_code": reason,
            }
        )
    return {
        "schema_version": RETENTION_REPORT_SCHEMA,
        "dry_run": True,
        "policy": {"retention_days": retention_days},
        "counts": {
            "CANDIDATO_BORRADO_MANUAL": counts["CANDIDATO_BORRADO_MANUAL"],
            "CONSERVAR": counts["CONSERVAR"],
        },
        "items": items,
    }


def consolidar_manifests(manifests: object) -> dict[str, object]:
    """Agrega manifests mínimos; entradas con PII o secretos cuentan inválidas."""
    if not isinstance(manifests, list):
        raise ContratoOperativoInvalido("consolidated_input_invalid")
    statuses: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    invalid = 0
    for manifest in manifests:
        if not _manifest_consolidable(manifest):
            invalid += 1
            continue
        assert isinstance(manifest, dict)
        statuses[manifest["status"]] += 1
        errors.update(manifest["error_codes"])
    return {
        "schema_version": CONSOLIDATED_REPORT_SCHEMA,
        "total": len(manifests),
        "valid": len(manifests) - invalid,
        "invalid": invalid,
        "by_status": dict(sorted(statuses.items())),
        "error_codes": dict(sorted(errors.items())),
    }


def _health_manifest_valido(manifest: object) -> bool:
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version",
        "ambiente",
        "config",
        "runtime",
        "artifacts",
    }:
        return False
    config, runtime, artifacts = (
        manifest["config"],
        manifest["runtime"],
        manifest["artifacts"],
    )
    return (
        manifest["schema_version"] == HEALTH_INPUT_SCHEMA
        and manifest["ambiente"] in {"D2", "D3"}
        and isinstance(config, dict)
        and set(config) == {"status", "resources_configured", "config_hash"}
        and config["status"] in {"VALID", "INVALID"}
        and isinstance(config["resources_configured"], bool)
        and _es_hash(config["config_hash"])
        and isinstance(runtime, dict)
        and set(runtime) == {"status", "runtime_hash"}
        and runtime["status"] in {"READY", "UNAVAILABLE"}
        and _es_hash(runtime["runtime_hash"])
        and isinstance(artifacts, list)
        and bool(artifacts)
        and all(
            isinstance(item, dict)
            and set(item) == {"kind", "ref_hash", "status"}
            and item["kind"] in _ARTIFACT_KINDS
            and _es_hash(item["ref_hash"])
            and item["status"] in _ARTIFACT_STATUS
            for item in artifacts
        )
        and not _contiene_dato_sensible(manifest)
    )


def _retention_record_valido(record: object) -> bool:
    return (
        isinstance(record, dict)
        and set(record) == {"ref_hash", "relative_path", "created_at", "state"}
        and _es_hash(record["ref_hash"])
        and isinstance(record["relative_path"], str)
        and isinstance(record["created_at"], str)
        and record["state"] in _RETENTION_STATES
    )


def _validar_path_retencion(base: Path, raw: str) -> None:
    try:
        pure = PurePosixPath(raw)
        if (
            not raw
            or pure.is_absolute()
            or any(part in {"", ".", ".."} for part in pure.parts)
            or pure.parts[0] not in _RETENTION_ROOTS
        ):
            raise ValueError
        current = base
        for part in pure.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError
        resolved = current.resolve(strict=True)
        if not resolved.is_file() or not resolved.is_relative_to(base):
            raise ValueError
    except (OSError, RuntimeError, ValueError):
        raise ContratoOperativoInvalido("retention_path_invalid") from None


def _parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(UTC)
    except (TypeError, ValueError, OverflowError):
        raise ContratoOperativoInvalido("retention_record_invalid") from None


def _manifest_consolidable(manifest: object) -> bool:
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"schema_version", "status", "error_codes"}
        or not isinstance(manifest["schema_version"], str)
        or _SCHEMA_RE.fullmatch(manifest["schema_version"]) is None
        or not isinstance(manifest["status"], str)
        or _CODE_RE.fullmatch(manifest["status"]) is None
        or not isinstance(manifest["error_codes"], list)
        or any(
            not isinstance(code, str) or _CODE_RE.fullmatch(code) is None
            for code in manifest["error_codes"]
        )
    ):
        return False
    return not _contiene_dato_sensible(manifest)


def _contiene_dato_sensible(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            not isinstance(key, str)
            or _SENSITIVE_KEY_RE.search(key) is not None
            or _contiene_dato_sensible(nested)
            for key, nested in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contiene_dato_sensible(nested) for nested in value)
    return isinstance(value, str) and (
        _EMAIL_RE.search(value) is not None or _BEARER_RE.search(value) is not None
    )


def _es_hash(value: object) -> bool:
    return isinstance(value, str) and _HASH_RE.fullmatch(value) is not None
