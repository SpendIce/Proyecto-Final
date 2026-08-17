from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "preparar_validacion_seu.py"
SPEC = importlib.util.spec_from_file_location("preparar_validacion_seu", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _pending_acta() -> dict[str, object]:
    return {
        "schema_version": "acta_validacion_seu_v1",
        "estado": "PENDIENTE",
        "persona_revisora": "",
        "rol_area": "",
        "fecha_hora": "",
        "decision": "PENDIENTE",
        "referencia_evidencia": "",
        "muestras": [],
    }


def _muestra_aprobada(sample_id: str) -> dict[str, object]:
    return {
        "id": sample_id,
        "decision": "APROBADO_COMO_BORRADOR",
        "puntajes": {
            "precision": 4,
            "tono": 4,
            "ajuste_canal": 4,
            "gramatica": 4,
            "longitud": 4,
            "alucinaciones": 4,
        },
        "controles_obligatorios": {
            "hechos_contrastados": True,
            "sin_claim_publicacion": True,
            "sin_datos_innecesarios": True,
        },
        "observaciones": "",
    }


def _acta_aprobada() -> dict[str, object]:
    acta = _pending_acta()
    acta.update(
        {
            "estado": "CERRADA",
            "persona_revisora": "Persona designada",
            "rol_area": "SEU",
            "fecha_hora": "2026-08-20T14:00:00-03:00",
            "decision": "APROBADO_COMO_BORRADOR",
            "referencia_evidencia": "ACTA-SEU-001",
            "motivo_decision": "",
            "muestras": [
                _muestra_aprobada(sample_id)
                for sample_id in sorted(MODULE.IDS_MUESTRA_REQUERIDOS)
            ],
        }
    )
    return acta


def test_acta_pendiente_admite_campos_humanos_vacios() -> None:
    MODULE.validar_acta(_pending_acta())


@pytest.mark.parametrize("campo", ["persona_revisora", "rol_area", "fecha_hora"])
def test_aprobacion_sin_identidad_o_fecha_es_rechazada(campo: str) -> None:
    acta = _acta_aprobada()
    acta[campo] = ""

    with pytest.raises(MODULE.ActaInvalida, match=campo):
        MODULE.validar_acta(acta)


def test_aprobacion_sin_puntajes_o_controles_completos_es_rechazada() -> None:
    acta = _acta_aprobada()
    acta["muestras"][0]["puntajes"] = {"precision": 4}

    with pytest.raises(MODULE.ActaInvalida, match="criterios requeridos"):
        MODULE.validar_acta(acta)


def test_bool_no_es_un_puntaje_entero_valido() -> None:
    acta = _acta_aprobada()
    acta["muestras"][0]["puntajes"]["precision"] = True

    with pytest.raises(MODULE.ActaInvalida, match="enteros entre 1 y 4"):
        MODULE.validar_acta(acta)


def test_control_truthy_no_reemplaza_booleano_true() -> None:
    acta = _acta_aprobada()
    acta["muestras"][0]["controles_obligatorios"]["hechos_contrastados"] = "false"

    with pytest.raises(MODULE.ActaInvalida, match="booleanos"):
        MODULE.validar_acta(acta)


def test_aprobacion_exige_puntaje_minimo_tres() -> None:
    acta = _acta_aprobada()
    acta["muestras"][0]["puntajes"]["precision"] = 2
    acta["muestras"][0]["observaciones"] = "La fecha no coincide."

    with pytest.raises(MODULE.ActaInvalida, match="mínimo 3"):
        MODULE.validar_acta(acta)


def test_puntaje_bajo_exige_observacion() -> None:
    acta = _acta_aprobada()
    acta["decision"] = "REQUIERE_AJUSTES"
    acta["motivo_decision"] = "Hay correcciones pendientes."
    acta["muestras"][0]["decision"] = "REQUIERE_AJUSTES"
    acta["muestras"][0]["puntajes"]["precision"] = 2

    with pytest.raises(MODULE.ActaInvalida, match="puntaje menor que 3"):
        MODULE.validar_acta(acta)


def test_aprobacion_requiere_la_muestra_versionada_completa() -> None:
    acta = _acta_aprobada()
    acta["muestras"] = acta["muestras"][:-1]

    with pytest.raises(MODULE.ActaInvalida, match="nueve muestras"):
        MODULE.validar_acta(acta)


def test_muestra_malformada_se_rechaza_sin_attribute_error() -> None:
    acta = _acta_aprobada()
    acta["muestras"][0] = "M-001"

    with pytest.raises(MODULE.ActaInvalida, match="objeto"):
        MODULE.validar_acta(acta)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("id", ["M-001"]), ("decision", ["APROBADO_COMO_BORRADOR"])],
)
def test_campos_muestra_no_hashables_se_rechazan_sin_type_error(
    campo: str, valor: object
) -> None:
    acta = _acta_aprobada()
    acta["muestras"][0][campo] = valor

    with pytest.raises(MODULE.ActaInvalida):
        MODULE.validar_acta(acta)


def test_decision_global_no_hashable_se_rechaza_sin_type_error() -> None:
    acta = _acta_aprobada()
    acta["decision"] = ["APROBADO_COMO_BORRADOR"]

    with pytest.raises(MODULE.ActaInvalida, match="decision no reconocida"):
        MODULE.validar_acta(acta)


@pytest.mark.parametrize("decision", ["REQUIERE_AJUSTES", "RECHAZADO"])
def test_ajuste_o_rechazo_exigen_motivo_y_observacion(decision: str) -> None:
    acta = _acta_aprobada()
    acta["decision"] = decision
    acta["muestras"][0]["decision"] = decision

    with pytest.raises(MODULE.ActaInvalida, match="motivo_decision"):
        MODULE.validar_acta(acta)

    acta["motivo_decision"] = "Motivo global documentado."
    with pytest.raises(MODULE.ActaInvalida, match="observación"):
        MODULE.validar_acta(acta)


def test_fecha_de_cierre_debe_ser_iso8601_con_zona() -> None:
    acta = _acta_aprobada()
    acta["fecha_hora"] = "17/08/2026"

    with pytest.raises(MODULE.ActaInvalida, match="ISO 8601"):
        MODULE.validar_acta(acta)


def test_manifest_solo_incluye_referencias_hashes_y_no_contenido(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    artifact = repo / "evidencia.md"
    secret = "Contacto de prueba que no debe copiarse al manifest"
    artifact.write_text(secret, encoding="utf-8")
    acta_path = repo / "acta.json"
    acta_path.write_text(json.dumps(_pending_acta()), encoding="utf-8")

    manifest = MODULE.preparar_manifest(
        repo_root=repo,
        referencias=[{"id": "REF-001", "path": "evidencia.md"}],
        acta_path=acta_path,
    )
    serialized = json.dumps(manifest, ensure_ascii=False)

    assert secret not in serialized
    assert "persona_revisora" not in serialized
    assert manifest["estado"] == "PENDIENTE"
    assert manifest["publicacion_o_envio_ejecutado"] is False
    assert manifest["referencias"] == [
        {
            "id": "REF-001",
            "sha256": hashlib.sha256(secret.encode()).hexdigest(),
            "bytes": len(secret.encode()),
        }
    ]


def test_manifest_rechaza_referencias_fuera_del_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    acta_path = repo / "acta.json"
    acta_path.write_text(json.dumps(_pending_acta()), encoding="utf-8")

    with pytest.raises(ValueError, match="fuera del repositorio"):
        MODULE.preparar_manifest(
            repo,
            [{"id": "REF-001", "path": "../externo.txt"}],
            acta_path,
        )


def test_manifest_no_refleja_filename_con_email_y_rechaza_id_no_opaco(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    email = "persona@fie.undef.edu.ar"
    artifact = repo / email
    artifact.write_text("contenido", encoding="utf-8")
    acta_path = repo / "acta.json"
    acta_path.write_text(json.dumps(_pending_acta()), encoding="utf-8")

    manifest = MODULE.preparar_manifest(
        repo,
        [{"id": "REF-001", "path": email}],
        acta_path,
    )
    assert email not in json.dumps(manifest)

    with pytest.raises(ValueError, match="identificador opaco"):
        MODULE.preparar_manifest(
            repo,
            [{"id": email, "path": email}],
            acta_path,
        )


def test_error_de_referencia_no_repite_path_con_pii(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    acta_path = repo / "acta.json"
    acta_path.write_text(json.dumps(_pending_acta()), encoding="utf-8")
    email = "persona@fie.undef.edu.ar"

    with pytest.raises(FileNotFoundError) as error:
        MODULE.preparar_manifest(
            repo,
            [{"id": "REF-001", "path": email}],
            acta_path,
        )

    assert email not in str(error.value)
