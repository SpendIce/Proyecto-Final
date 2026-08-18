from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from agente1.operaciones_seguras import (
    ContratoOperativoInvalido,
    consolidar_manifests,
    evaluar_health,
    planificar_reconciliacion,
    planificar_retencion,
)


HASH_A = "a" * 64
HASH_B = "b" * 64


def _health_manifest() -> dict[str, object]:
    return {
        "schema_version": "agente1-health-input-v1",
        "ambiente": "D2",
        "config": {
            "status": "VALID",
            "resources_configured": True,
            "config_hash": HASH_A,
        },
        "runtime": {
            "status": "READY",
            "runtime_hash": HASH_B,
        },
        "artifacts": [
            {"kind": "contract", "ref_hash": HASH_A, "status": "AVAILABLE"},
            {"kind": "prompt", "ref_hash": HASH_B, "status": "AVAILABLE"},
        ],
    }


class _ProbeLectura:
    def __init__(self, result: str = "READABLE") -> None:
        self.calls = 0
        self.result = result

    def probar_lectura(self) -> str:
        self.calls += 1
        return self.result


def test_health_es_offline_por_defecto_y_no_expone_referencias() -> None:
    probe = _ProbeLectura()

    report = evaluar_health(_health_manifest(), probe=probe)

    assert report == {
        "schema_version": "agente1-health-report-v1",
        "ambiente": "D2",
        "mode": "offline",
        "status": "PASS",
        "checks": {
            "artifacts": "PASS",
            "config": "PASS",
            "runtime": "PASS",
        },
        "live_probe": "NOT_REQUESTED",
    }
    assert probe.calls == 0
    assert HASH_A not in repr(report)


def test_health_live_requiere_opt_in_y_probe_read_only() -> None:
    probe = _ProbeLectura()

    report = evaluar_health(
        _health_manifest(), live=True, live_opt_in=True, probe=probe
    )

    assert report["mode"] == "live_read_only"
    assert report["live_probe"] == "READABLE"
    assert report["status"] == "PASS"
    assert probe.calls == 1


@pytest.mark.parametrize("unsafe_result", [[], {}, None, object()])
def test_health_live_normaliza_resultados_no_string_sin_excepcion(
    unsafe_result: object,
) -> None:
    probe = _ProbeLectura(unsafe_result)  # type: ignore[arg-type]

    report = evaluar_health(
        _health_manifest(), live=True, live_opt_in=True, probe=probe
    )

    assert report["live_probe"] == "UNAVAILABLE"
    assert report["status"] == "FAIL"
    assert repr(unsafe_result) not in repr(report)


def test_health_falla_si_los_recursos_no_estan_configurados() -> None:
    manifest = _health_manifest()
    manifest["config"]["resources_configured"] = False

    report = evaluar_health(manifest)

    assert report["status"] == "FAIL"
    assert report["checks"]["config"] == "FAIL"


@pytest.mark.parametrize(
    ("live_opt_in", "probe"),
    [(False, _ProbeLectura()), (True, None)],
)
def test_health_live_falla_cerrado_sin_condiciones_explicitas(
    live_opt_in: bool, probe: object
) -> None:
    with pytest.raises(ContratoOperativoInvalido, match="health_live_not_authorized"):
        evaluar_health(
            _health_manifest(), live=True, live_opt_in=live_opt_in, probe=probe
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda m: m.update(document_id="raw-id"),
        lambda m: m["config"].update(access_token="Bearer secreto"),
        lambda m: m["artifacts"].append(
            {"kind": "prompt", "ref_hash": "no-es-hash", "status": "AVAILABLE"}
        ),
    ],
)
def test_health_rechaza_ids_secretos_y_hashes_malformados(mutation) -> None:
    manifest = _health_manifest()
    mutation(manifest)

    with pytest.raises(ContratoOperativoInvalido, match="health_manifest_invalid"):
        evaluar_health(manifest)


def test_reconciliacion_solo_emite_estado_e_instruccion_no_destructiva() -> None:
    report = planificar_reconciliacion(
        [
            {
                "draft_hash": HASH_A,
                "manifest_hash": HASH_B,
                "state": "SIN_REFERENCIA",
            },
            {
                "draft_hash": HASH_B,
                "manifest_hash": HASH_A,
                "state": "REFERENCIADO",
            },
        ]
    )

    assert report["status"] == "REQUIERE_REVISION"
    assert report["counts"] == {"REVISAR_MANUAL": 1, "SIN_ACCION": 1}
    assert report["items"][0] == {
        "draft_hash": HASH_A,
        "state": "SIN_REFERENCIA",
        "instruction": "REVISAR_MANUAL",
    }
    assert "delete" not in repr(report).lower()
    assert "document" not in repr(report).lower()


@pytest.mark.parametrize(
    "record",
    [
        {"draft_hash": HASH_A, "manifest_hash": HASH_B, "state": "BORRADO"},
        {
            "draft_hash": HASH_A,
            "manifest_hash": HASH_B,
            "state": "SIN_REFERENCIA",
            "document_id": "raw-id",
        },
        {"draft_hash": "../secreto", "manifest_hash": HASH_B, "state": "PERSISTIDO"},
    ],
)
def test_reconciliacion_rechaza_estados_operaciones_e_ids_no_permitidos(record) -> None:
    with pytest.raises(ContratoOperativoInvalido, match="reconciliation_invalid"):
        planificar_reconciliacion([record])


def test_retencion_solo_genera_plan_dry_run_con_referencias_opacas(
    tmp_path: Path,
) -> None:
    (tmp_path / "salida").mkdir()
    artifact = tmp_path / "salida" / "run.json"
    artifact.write_text("{}", encoding="utf-8")

    report = planificar_retencion(
        tmp_path,
        [
            {
                "ref_hash": HASH_A,
                "relative_path": "salida/run.json",
                "created_at": "2026-07-01T00:00:00Z",
                "state": "CERRADO",
            }
        ],
        now=datetime(2026, 8, 17, tzinfo=UTC),
        retention_days=30,
    )

    assert report == {
        "schema_version": "agente1-retention-plan-v1",
        "dry_run": True,
        "policy": {"retention_days": 30},
        "counts": {"CANDIDATO_BORRADO_MANUAL": 1, "CONSERVAR": 0},
        "items": [
            {
                "ref_hash": HASH_A,
                "decision": "CANDIDATO_BORRADO_MANUAL",
                "reason_code": "retention_expired",
            }
        ],
    }
    assert artifact.exists()
    assert "run.json" not in repr(report)


@pytest.mark.parametrize("relative_path", ["../secret", "/etc/passwd", "salida/../../x"])
def test_retencion_rechaza_traversal_y_paths_absolutos(
    tmp_path: Path, relative_path: str
) -> None:
    with pytest.raises(ContratoOperativoInvalido, match="retention_path_invalid"):
        planificar_retencion(
            tmp_path,
            [
                {
                    "ref_hash": HASH_A,
                    "relative_path": relative_path,
                    "created_at": "2026-08-01T00:00:00Z",
                    "state": "CERRADO",
                }
            ],
            now=datetime(2026, 8, 17, tzinfo=UTC),
            retention_days=30,
        )


def test_retencion_rechaza_symlink_aunque_apunte_dentro_de_allowlist(
    tmp_path: Path,
) -> None:
    (tmp_path / "salida").mkdir()
    (tmp_path / "real.json").write_text("{}", encoding="utf-8")
    (tmp_path / "salida" / "link.json").symlink_to(tmp_path / "real.json")

    with pytest.raises(ContratoOperativoInvalido, match="retention_path_invalid"):
        planificar_retencion(
            tmp_path,
            [
                {
                    "ref_hash": HASH_A,
                    "relative_path": "salida/link.json",
                    "created_at": "2026-07-01T00:00:00Z",
                    "state": "CERRADO",
                }
            ],
            now=datetime(2026, 8, 17, tzinfo=UTC),
            retention_days=30,
        )


def test_reporte_consolidado_agrega_solo_conteos_y_codigos() -> None:
    report = consolidar_manifests(
        [
            {
                "schema_version": "evidencia_hu010_v1",
                "status": "PENDIENTE_VALIDACION",
                "error_codes": [],
            },
            {
                "schema_version": "evidencia_hu011_v1",
                "status": "NO_CONFORME",
                "error_codes": ["date_missing", "contact_missing"],
            },
            {"malformed": True},
        ]
    )

    assert report == {
        "schema_version": "agente1-consolidated-report-v1",
        "total": 3,
        "valid": 2,
        "invalid": 1,
        "by_status": {"NO_CONFORME": 1, "PENDIENTE_VALIDACION": 1},
        "error_codes": {"contact_missing": 1, "date_missing": 1},
    }


@pytest.mark.parametrize(
    "manifest",
    [
        {
            "schema_version": "evidencia_v1",
            "status": "PASS",
            "error_codes": [],
            "contact": "persona@fie.undef.edu.ar",
        },
        {
            "schema_version": "evidencia_v1",
            "status": "PASS",
            "error_codes": [],
            "authorization": "Bearer secreto",
        },
    ],
)
def test_reporte_trata_manifests_con_pii_o_secretos_como_invalidos(manifest) -> None:
    report = consolidar_manifests([manifest])

    assert report["valid"] == 0
    assert report["invalid"] == 1
    assert "secreto" not in repr(report)
    assert "persona@" not in repr(report)
