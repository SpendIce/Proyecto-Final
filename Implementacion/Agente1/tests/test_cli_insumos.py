"""Subcomando `insumos-agentes`: corrida offline por CSV y doble opt-in live.

Offline se ejercita la interfaz completa —tabla CSV, directorio con el
registro, generador fake— igual que la corrida real contra la pestaña.
"""

import csv
import json
from pathlib import Path

import pytest

from agente1.cli_insumos import main as main_insumos
from agente1.insumos_corrida import COLUMNAS_INSUMOS_AGENTES_V1


def envelope_evento() -> dict[str, object]:
    return {
        "schema": "agente1.insumo.v1",
        "schema_version": "1.0.0",
        "channel": "a1.communication_input",
        "producer": "A3",
        "producer_schema_version": "a3_candidate_v1",
        "correlation_id": "corr-cli-sintetico-001",
        "timestamp": "2026-10-01T10:00:00-03:00",
        "data_origin": "provisional_producer",
        "provenance": {
            "sources": [{"ref": "opaque:cli:src-1", "sha256": "a" * 64}]
        },
        "payload": {
            "type": "evento",
            "content": {
                "titulo": "Evento sintético",
                "descripcion": "Actividad ficticia del insumo.",
                "fecha_inicio": "2026-10-15",
                "publico": "Comunidad ficticia",
                "organiza": "Equipo ficticio",
                "contacto": "pruebas@example.invalid",
                "fuente": "opaque:A3:informe-1",
            },
        },
    }


SALIDA_CONFORME = (
    "## TÍTULO\n"
    "Evento sintético\n\n"
    "## DATOS DE LA ACTIVIDAD\n"
    "Fecha: 2026-10-15\n"
    "Organiza: Equipo ficticio\n\n"
    "## CONTACTO\n"
    "pruebas@example.invalid\n\n"
    "## BAJADA\n"
    "Borrador sintético para validar el flujo técnico.\n\n"
    "## CUERPO\n"
    "La actividad requiere revisión humana antes de cualquier publicación."
)


def escribir_tabla(path: Path, *filas: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.writer(archivo)
        writer.writerow(COLUMNAS_INSUMOS_AGENTES_V1)
        writer.writerows(filas)


def test_cli_offline_procesa_la_tabla_y_vuelca_informe(
    tmp_path: Path, capsys
) -> None:
    tabla = tmp_path / "insumos.csv"
    directorio = tmp_path / "salida"
    escribir_tabla(
        tabla,
        [json.dumps(envelope_evento(), ensure_ascii=False), "ope-1", "", ""],
    )

    codigo = main_insumos(
        [
            "--tabla",
            str(tabla),
            "--directorio",
            str(directorio),
            "--fake-output",
            SALIDA_CONFORME,
        ]
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 0
    assert salida["estado"] == "OK"
    assert salida["filas_escritas"] == 1
    (fila,) = salida["filas"]
    assert fila["estado"] == "borrador generado"
    assert fila["correlation_id"] == "corr-cli-sintetico-001"
    # El informe no arrastra el payload ni el contenido generado.
    assert "Actividad ficticia" not in json.dumps(salida)
    # La pestaña offline quedó con su estado escrito.
    with tabla.open(encoding="utf-8", newline="") as archivo:
        filas = list(csv.reader(archivo))
    assert filas[1][2] == "borrador generado"
    # El registro de idempotencia quedó persistido en el directorio.
    assert (directorio / "insumos-procesados.jsonl").exists()


def test_cli_offline_rechaza_encabezado_invalido(tmp_path: Path, capsys) -> None:
    tabla = tmp_path / "insumos.csv"
    tabla.write_text("a,b,c,d\n1,2,3,4\n", encoding="utf-8")

    codigo = main_insumos(
        [
            "--tabla",
            str(tabla),
            "--directorio",
            str(tmp_path / "salida"),
            "--fake-output",
            SALIDA_CONFORME,
        ]
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 2
    assert salida == {
        "estado": "INVALIDA",
        "error": "insumos_encabezado_invalid",
    }


def test_cli_offline_exige_tabla(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main_insumos(
            ["--directorio", str(tmp_path), "--fake-output", "x"]
        )


def test_cli_exige_generador(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main_insumos(
            [
                "--tabla",
                str(tmp_path / "t.csv"),
                "--directorio",
                str(tmp_path),
            ]
        )


def test_cli_live_exige_doble_opt_in(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main_insumos(
            [
                "--directorio",
                str(tmp_path),
                "--ollama-model",
                "modelo-x",
                "--live",
            ]
        )


def test_cli_live_rechaza_tabla_offline(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main_insumos(
            [
                "--tabla",
                str(tmp_path / "t.csv"),
                "--directorio",
                str(tmp_path),
                "--ollama-model",
                "modelo-x",
                "--live",
                "--confirm-write-workspace",
            ]
        )


def test_cli_live_exige_modelo_real(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main_insumos(
            [
                "--directorio",
                str(tmp_path),
                "--fake-output",
                SALIDA_CONFORME,
                "--live",
                "--confirm-write-workspace",
            ]
        )


def test_cli_live_sin_configuracion_falla_cerrado(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    for clave in (
        "AGENTE1_WORKSPACE_AMBIENTE",
        "AGENTE1_WORKSPACE_SPREADSHEET_ID",
        "AGENTE1_WORKSPACE_RANGO_A1",
        "AGENTE1_WORKSPACE_FOLDER_ID",
        "AGENTE1_WORKSPACE_TEMPLATE_ID",
        "AGENTE1_WORKSPACE_TIMEOUT_S",
        "AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES",
        "AGENTE1_WORKSPACE_ACCESS_TOKEN",
        "AGENTE1_WORKSPACE_OAUTH_CLIENT_ID",
        "AGENTE1_WORKSPACE_OAUTH_CLIENT_SECRET",
        "AGENTE1_WORKSPACE_OAUTH_REFRESH_TOKEN",
        "AGENTE1_INSUMOS_RANGO_A1",
    ):
        monkeypatch.delenv(clave, raising=False)

    codigo = main_insumos(
        [
            "--directorio",
            str(tmp_path),
            "--ollama-model",
            "modelo-x",
            "--live",
            "--confirm-write-workspace",
        ]
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 2
    assert salida["estado"] == "INVALIDA"
    assert salida["error"].startswith(("workspace_config_", "insumos_config_"))
