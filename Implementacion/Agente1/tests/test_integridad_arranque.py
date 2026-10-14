"""Cableado del gate de integridad en el modo operación (#92, ADR 0010).

El manifest se genera al cortar una versión; acá se prueba que las corridas
que tocan sistemas reales (`--live`, el camino de las unidades `systemd/`) no
arrancan si un archivo controlado no coincide, y que las corridas offline y la
suite no lo exigen.
"""

import csv
import json
from pathlib import Path

from agente1.cli_insumos import main as main_insumos
from agente1.cli_scheduler import main as main_scheduler
from agente1.google_workspace import MAX_WORKSPACE_RESPONSE_BYTES
from agente1.insumos_corrida import COLUMNAS_INSUMOS_AGENTES_V1
from agente1.manifest_version import (
    AUDITORIA_NOMBRE,
    MANIFEST_VERSION_NOMBRE,
    construir_manifest,
    listar_controlados,
    serializar_manifest,
)

ENTORNO_WORKSPACE = {
    "AGENTE1_WORKSPACE_AMBIENTE": "D2",
    "AGENTE1_WORKSPACE_SPREADSHEET_ID": "sheet-sintetica-1",
    "AGENTE1_WORKSPACE_RANGO_A1": "'Actividades'!A1:I500",
    "AGENTE1_WORKSPACE_FOLDER_ID": "folder-sintetica-1",
    "AGENTE1_WORKSPACE_TEMPLATE_ID": "plantilla-sintetica-1",
    "AGENTE1_WORKSPACE_TIMEOUT_S": "45",
    "AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES": str(MAX_WORKSPACE_RESPONSE_BYTES),
    "AGENTE1_INSUMOS_RANGO_A1": "'Insumos de agentes'!A1:D500",
}
ENTORNO_CREDENCIALES = (
    "AGENTE1_WORKSPACE_ACCESS_TOKEN",
    "AGENTE1_WORKSPACE_OAUTH_CLIENT_ID",
    "AGENTE1_WORKSPACE_OAUTH_CLIENT_SECRET",
    "AGENTE1_WORKSPACE_OAUTH_REFRESH_TOKEN",
)
ENTORNO_SCHEDULER = (
    "AGENTE1_SCHEDULER_INTERVALO_S",
    "AGENTE1_SCHEDULER_VENTANA_DIAS",
    "AGENTE1_SCHEDULER_VENTANA_DESDE",
    "AGENTE1_SCHEDULER_VENTANA_HASTA",
    "AGENTE1_SCHEDULER_TZ",
    "AGENTE1_SCHEDULER_REPO",
    "AGENTE1_SCHEDULER_REGISTRO_CONFIRMACIONES",
)


def preparar_version(tmp_path: Path) -> tuple[Path, dict]:
    """Un árbol controlado chico con su manifest de versión."""

    raiz = tmp_path / "agente"
    (raiz / "src").mkdir(parents=True)
    (raiz / "src" / "a.py").write_text("uno\n", encoding="utf-8")
    (raiz / "pyproject.toml").write_text(
        '[project]\nname = "agente1-poc"\nversion = "1.2.3"\n', encoding="utf-8"
    )
    manifest = construir_manifest(raiz)
    (raiz / MANIFEST_VERSION_NOMBRE).write_text(
        serializar_manifest(manifest), encoding="utf-8"
    )
    return raiz, manifest


def configurar_entorno(monkeypatch, *, con_credencial: bool = False) -> None:
    for clave, valor in ENTORNO_WORKSPACE.items():
        monkeypatch.setenv(clave, valor)
    for clave in ENTORNO_CREDENCIALES:
        if con_credencial and clave == "AGENTE1_WORKSPACE_ACCESS_TOKEN":
            monkeypatch.setenv(clave, "token-sintetico-1")
        else:
            monkeypatch.delenv(clave, raising=False)
    for clave in ENTORNO_SCHEDULER:
        monkeypatch.delenv(clave, raising=False)


def escribir_tabla_vacia(ruta: Path) -> None:
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        csv.writer(archivo).writerow(COLUMNAS_INSUMOS_AGENTES_V1)


def ultima_auditoria(salida: Path) -> dict:
    lineas = (salida / "logs" / AUDITORIA_NOMBRE).read_text(encoding="utf-8").splitlines()
    return json.loads(lineas[-1])


def test_live_no_arranca_si_un_archivo_controlado_difiere(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    raiz, manifest = preparar_version(tmp_path)
    configurar_entorno(monkeypatch)
    monkeypatch.setattr("agente1.manifest_version.raiz_agente", lambda: raiz)
    salida = tmp_path / "salida"
    (raiz / "src" / "a.py").write_text("alterado\n", encoding="utf-8")

    codigo = main_insumos(
        [
            "--directorio",
            str(salida),
            "--ollama-model",
            "modelo-x",
            "--live",
            "--confirm-write-workspace",
        ]
    )

    salida_json = json.loads(capsys.readouterr().out)
    assert codigo == 2
    assert salida_json == {"estado": "INVALIDA", "error": "integridad_archivos_no_coinciden"}
    entrada = ultima_auditoria(salida)
    assert entrada["resultado"] == "FAIL"
    assert entrada["version"] == manifest["version"]
    assert entrada["discrepancias"][0]["archivo"] == "src/a.py"
    assert entrada["discrepancias"][0]["hash_esperado"] != entrada["discrepancias"][0][
        "hash_encontrado"
    ]


def test_live_pasa_el_gate_antes_de_pedir_credenciales(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    raiz, _ = preparar_version(tmp_path)
    configurar_entorno(monkeypatch)
    monkeypatch.setattr("agente1.manifest_version.raiz_agente", lambda: raiz)
    salida = tmp_path / "salida"

    codigo = main_insumos(
        [
            "--directorio",
            str(salida),
            "--ollama-model",
            "modelo-x",
            "--live",
            "--confirm-write-workspace",
        ]
    )

    salida_json = json.loads(capsys.readouterr().out)
    # Llegó hasta la credencial: el gate de integridad ya pasó.
    assert codigo == 2
    assert salida_json == {"estado": "INVALIDA", "error": "workspace_auth_unavailable"}
    assert ultima_auditoria(salida)["resultado"] == "PASS"


def test_scheduler_live_no_arranca_si_un_archivo_controlado_difiere(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    raiz, _ = preparar_version(tmp_path)
    configurar_entorno(monkeypatch)
    monkeypatch.setattr("agente1.manifest_version.raiz_agente", lambda: raiz)
    salida = tmp_path / "salida"
    (raiz / "src" / "a.py").unlink()

    codigo = main_scheduler(
        [
            "--una-corrida",
            "--directorio",
            str(salida),
            "--live",
            "--confirm-write-workspace",
            "--ollama-model",
            "modelo-x",
        ]
    )

    salida_json = json.loads(capsys.readouterr().out)
    assert codigo == 2
    assert salida_json == {"estado": "INVALIDA", "error": "integridad_archivos_no_coinciden"}
    assert ultima_auditoria(salida)["discrepancias"][0]["motivo"] == "faltante"


def test_corrida_offline_no_exige_manifest(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """El modo desarrollo no verifica: ni falta que exista el manifest."""

    configurar_entorno(monkeypatch)
    # La raíz apunta a un árbol sin manifest: si se verificara, no arrancaría.
    monkeypatch.setattr("agente1.manifest_version.raiz_agente", lambda: tmp_path / "sin-manifest")
    tabla = tmp_path / "insumos.csv"
    escribir_tabla_vacia(tabla)
    salida = tmp_path / "salida"

    codigo = main_insumos(
        [
            "--tabla",
            str(tabla),
            "--directorio",
            str(salida),
            "--fake-output",
            "salida",
        ]
    )

    assert codigo == 0
    assert json.loads(capsys.readouterr().out)["estado"] == "OK"
    assert not (salida / "logs" / AUDITORIA_NOMBRE).exists()


def test_el_arbol_de_prueba_no_traiciona_al_barrido(tmp_path: Path) -> None:
    """Contraprueba del helper: el manifest sólo cubre lo controlado."""

    raiz, manifest = preparar_version(tmp_path)
    (raiz / "tests").mkdir()
    (raiz / "tests" / "test_x.py").write_text("pass\n", encoding="utf-8")
    (raiz / "README.md").write_text("texto\n", encoding="utf-8")

    assert listar_controlados(raiz) == tuple(sorted(manifest["archivos_sha256"]))
