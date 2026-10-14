"""Manifest de versión y verificación de integridad (#92, ADR 0010).

Ejercita el módulo completo —barrido controlado, determinismo, comparación y
gate fail-closed con su auditoría— más los dos scripts por su interfaz real:
el generador `scripts/manifest_version.py` y el manifest de corte, que ahora
referencia la versión y el hash del manifest en lugar de su lista de fuentes.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agente1.manifest_version import (
    AUDITORIA_NOMBRE,
    AUDITORIA_RECORD,
    MANIFEST_VERSION_NOMBRE,
    MANIFEST_VERSION_SCHEMA,
    IntegridadError,
    comparar_archivos,
    construir_manifest,
    leer_manifest,
    listar_controlados,
    serializar_manifest,
    sha256_archivo,
    validar_manifest,
    verificar_integridad_al_arrancar,
    version_desde_pyproject,
)

ROOT = Path(__file__).resolve().parents[1]


def arbol_controlado(base: Path, *rutas: str) -> None:
    for ruta in rutas:
        archivo = base / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(f"contenido de {ruta}\n", encoding="utf-8")


def escribir_manifest(base: Path, manifest: dict, nombre: str = MANIFEST_VERSION_NOMBRE) -> Path:
    ruta = base / nombre
    ruta.write_text(serializar_manifest(manifest), encoding="utf-8")
    return ruta


def manifest_de(base: Path, *rutas: str) -> dict:
    arbol_controlado(base, *rutas)
    (base / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "1.2.3"\n', encoding="utf-8"
    )
    return construir_manifest(base)


# --- Barrido controlado -------------------------------------------------


def test_barrido_controlado_ordena_y_excluye_build(tmp_path: Path) -> None:
    arbol_controlado(
        tmp_path,
        "src/agente1/b.py",
        "src/agente1/a.py",
        "src/agente1/__pycache__/a.cpython-312.pyc",
        "src/agente1/prompts/p.txt",
        "src/agente1_poc.egg-info/PKG-INFO",
        "migrations/0001.up.sql",
        "scripts/uno.py",
        "systemd/u.service",
        "uv.lock",
    )
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n', encoding="utf-8")
    # Ruido fuera de lo controlado: no entra.
    arbol_controlado(tmp_path, "data/actividades.csv", "tests/test_x.py", "README.md")

    listado = listar_controlados(tmp_path)

    assert listado == (
        "migrations/0001.up.sql",
        "pyproject.toml",
        "scripts/uno.py",
        "src/agente1/a.py",
        "src/agente1/b.py",
        "src/agente1/prompts/p.txt",
        "systemd/u.service",
        "uv.lock",
    )
    assert not any("__pycache__" in ruta for ruta in listado)
    assert not any("egg-info" in ruta for ruta in listado)


def test_barrido_controlado_no_depende_del_orden_de_creacion(tmp_path: Path) -> None:
    uno = tmp_path / "uno"
    dos = tmp_path / "dos"
    rutas = ("src/z.py", "src/a.py", "src/m/n.py", "scripts/s.py")
    arbol_controlado(uno, *rutas)
    arbol_controlado(dos, *reversed(rutas))

    assert listar_controlados(uno) == listar_controlados(dos)


def test_barrido_controlado_espeja_gitignore(tmp_path: Path) -> None:
    """Lo controlado coincide con lo versionado: nada de más ni de menos.

    Usa `--others --exclude-standard` para incluir los archivos nuevos que
    todavía no están en el índice, que es exactamente lo que ve el barrido.
    """

    try:
        salida = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git no disponible para el cotejo")

    def controlada(linea: str) -> bool:
        if linea in {"uv.lock", "pyproject.toml"}:
            return True
        return linea.split("/", 1)[0] in {"src", "migrations", "scripts", "systemd"}

    versionados = tuple(
        sorted(linea for linea in salida.stdout.splitlines() if linea and controlada(linea))
    )
    assert listar_controlados(ROOT) == versionados


# --- Determinismo y versión --------------------------------------------


def test_manifest_es_determinista(tmp_path: Path) -> None:
    uno = tmp_path / "uno"
    dos = tmp_path / "dos"
    arbol_controlado(uno, "src/a.py", "scripts/s.py")
    (uno / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n', encoding="utf-8")
    arbol_controlado(dos, "src/a.py", "scripts/s.py")
    (dos / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n', encoding="utf-8")

    manifest_uno = construir_manifest(uno, version="9.9")
    manifest_dos = construir_manifest(dos, version="9.9")

    assert serializar_manifest(manifest_uno) == serializar_manifest(manifest_dos)
    assert manifest_uno["schema_version"] == MANIFEST_VERSION_SCHEMA
    assert manifest_uno["version"] == "9.9"


def test_manifest_toma_la_version_de_pyproject(tmp_path: Path) -> None:
    manifest_de(tmp_path, "src/a.py")

    assert version_desde_pyproject(tmp_path) == "1.2.3"
    assert construir_manifest(tmp_path)["version"] == "1.2.3"


def test_manifest_sin_archivos_controlados_falla(tmp_path: Path) -> None:
    with pytest.raises(IntegridadError) as excinfo:
        construir_manifest(tmp_path, version="1.0")

    assert excinfo.value.code == "manifest_sin_archivos"


def test_version_invalida_falla(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")

    with pytest.raises(IntegridadError) as excinfo:
        version_desde_pyproject(tmp_path)

    assert excinfo.value.code == "manifest_version_invalido"


# --- Contrato del manifest ---------------------------------------------


@pytest.mark.parametrize(
    "mutacion",
    [
        {"schema_version": "otro"},
        {"version": ""},
        {"archivos_sha256": {}},
        {"archivos_sha256": {"/etc/passwd": "a" * 64}},
        {"archivos_sha256": {"../fuera.py": "a" * 64}},
        {"archivos_sha256": {"data/actividades.csv": "a" * 64}},
        {"archivos_sha256": {"src/a.py": "no-es-un-hash"}},
    ],
)
def test_validar_manifest_rechaza_formas_abiertas(mutacion: dict) -> None:
    base = {
        "schema_version": MANIFEST_VERSION_SCHEMA,
        "version": "1.0.0",
        "archivos_sha256": {"src/a.py": "a" * 64},
    }
    base.update(mutacion)

    with pytest.raises(IntegridadError) as excinfo:
        validar_manifest(base)

    assert excinfo.value.code == "manifest_version_invalido"


# --- Comparación --------------------------------------------------------


def test_comparar_detecta_modificado_faltante_y_sobrante(tmp_path: Path) -> None:
    manifest = manifest_de(tmp_path, "src/a.py", "src/b.py", "src/c.py")
    (tmp_path / "src/a.py").write_text("otra cosa\n", encoding="utf-8")
    (tmp_path / "src/b.py").unlink()
    (tmp_path / "src/nuevo.py").write_text("nuevo\n", encoding="utf-8")

    discrepancias = {d["archivo"]: d for d in comparar_archivos(tmp_path, manifest["archivos_sha256"])}

    assert discrepancias["src/a.py"]["motivo"] == "modificado"
    assert discrepancias["src/a.py"]["hash_encontrado"] != discrepancias["src/a.py"]["hash_esperado"]
    assert discrepancias["src/b.py"]["motivo"] == "faltante"
    assert discrepancias["src/b.py"]["hash_encontrado"] is None
    assert discrepancias["src/nuevo.py"]["motivo"] == "sobrante"
    assert discrepancias["src/nuevo.py"]["hash_esperado"] is None


# --- Gate de arranque ---------------------------------------------------


def test_arranque_conforme_audita_pass(tmp_path: Path) -> None:
    raiz = tmp_path / "agente"
    salida = tmp_path / "salida"
    manifest = manifest_de(raiz, "src/a.py", "scripts/s.py")
    escribir_manifest(raiz, manifest)

    entrada = verificar_integridad_al_arrancar(directorio_salida=salida, raiz=raiz)

    assert entrada["resultado"] == "PASS"
    assert entrada["motivo"] is None
    assert entrada["version"] == "1.2.3"
    assert entrada["archivos_esperados"] == len(manifest["archivos_sha256"])
    lineas = (salida / "logs" / AUDITORIA_NOMBRE).read_text(encoding="utf-8").splitlines()
    assert json.loads(lineas[-1])["record"] == AUDITORIA_RECORD


def test_arranque_modificado_no_arranca_y_audita_los_dos_hashes(tmp_path: Path) -> None:
    raiz = tmp_path / "agente"
    salida = tmp_path / "salida"
    manifest = manifest_de(raiz, "src/a.py")
    escribir_manifest(raiz, manifest)
    esperado = manifest["archivos_sha256"]["src/a.py"]
    (raiz / "src/a.py").write_text("alterado a mano\n", encoding="utf-8")

    with pytest.raises(IntegridadError) as excinfo:
        verificar_integridad_al_arrancar(directorio_salida=salida, raiz=raiz)

    assert excinfo.value.code == "integridad_archivos_no_coinciden"
    entrada = json.loads(
        (salida / "logs" / AUDITORIA_NOMBRE).read_text(encoding="utf-8").splitlines()[-1]
    )
    assert entrada["resultado"] == "FAIL"
    assert entrada["motivo"] == "integridad_archivos_no_coinciden"
    assert entrada["discrepancias"] == [
        {
            "archivo": "src/a.py",
            "motivo": "modificado",
            "hash_esperado": esperado,
            "hash_encontrado": sha256_archivo(raiz / "src/a.py"),
        }
    ]


def test_arranque_faltante_no_arranca(tmp_path: Path) -> None:
    raiz = tmp_path / "agente"
    salida = tmp_path / "salida"
    escribir_manifest(raiz, manifest_de(raiz, "src/a.py"))
    (raiz / "src/a.py").unlink()

    with pytest.raises(IntegridadError):
        verificar_integridad_al_arrancar(directorio_salida=salida, raiz=raiz)

    entrada = json.loads(
        (salida / "logs" / AUDITORIA_NOMBRE).read_text(encoding="utf-8").splitlines()[-1]
    )
    assert entrada["discrepancias"][0]["motivo"] == "faltante"


def test_arranque_sobrante_no_arranca(tmp_path: Path) -> None:
    raiz = tmp_path / "agente"
    salida = tmp_path / "salida"
    escribir_manifest(raiz, manifest_de(raiz, "src/a.py"))
    arbol_controlado(raiz, "src/colado.py")

    with pytest.raises(IntegridadError):
        verificar_integridad_al_arrancar(directorio_salida=salida, raiz=raiz)

    entrada = json.loads(
        (salida / "logs" / AUDITORIA_NOMBRE).read_text(encoding="utf-8").splitlines()[-1]
    )
    assert entrada["discrepancias"][0]["motivo"] == "sobrante"
    assert entrada["discrepancias"][0]["hash_esperado"] is None


def test_arranque_sin_manifest_falla_cerrado(tmp_path: Path) -> None:
    raiz = tmp_path / "agente"
    arbol_controlado(raiz, "src/a.py")
    salida = tmp_path / "salida"

    with pytest.raises(IntegridadError) as excinfo:
        verificar_integridad_al_arrancar(directorio_salida=salida, raiz=raiz)

    assert excinfo.value.code == "manifest_version_ausente"
    entrada = json.loads(
        (salida / "logs" / AUDITORIA_NOMBRE).read_text(encoding="utf-8").splitlines()[-1]
    )
    assert entrada["resultado"] == "FAIL"
    assert entrada["motivo"] == "manifest_version_ausente"
    assert entrada["manifest_version_sha256"] is None


def test_arranque_con_manifest_invalido_falla_cerrado(tmp_path: Path) -> None:
    raiz = tmp_path / "agente"
    arbol_controlado(raiz, "src/a.py")
    (raiz / MANIFEST_VERSION_NOMBRE).write_text("{ no es json", encoding="utf-8")
    salida = tmp_path / "salida"

    with pytest.raises(IntegridadError) as excinfo:
        verificar_integridad_al_arrancar(directorio_salida=salida, raiz=raiz)

    assert excinfo.value.code == "manifest_version_invalido"
    entrada = json.loads(
        (salida / "logs" / AUDITORIA_NOMBRE).read_text(encoding="utf-8").splitlines()[-1]
    )
    assert entrada["motivo"] == "manifest_version_invalido"
    assert isinstance(entrada["manifest_version_sha256"], str)


def test_leer_manifest_distingue_ausente_de_invalido(tmp_path: Path) -> None:
    with pytest.raises(IntegridadError) as ausente:
        leer_manifest(tmp_path / "no-existe.json")
    assert ausente.value.code == "manifest_version_ausente"

    invalido = tmp_path / "manifest-version.json"
    invalido.write_text(json.dumps({"schema_version": "otro"}), encoding="utf-8")
    with pytest.raises(IntegridadError) as malo:
        leer_manifest(invalido)
    assert malo.value.code == "manifest_version_invalido"


# --- Scripts ------------------------------------------------------------


def test_script_generador_es_determinista_y_refleja_el_arbol() -> None:
    primera = subprocess.run(
        [sys.executable, "scripts/manifest_version.py", "--version", "9.9.9"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    segunda = subprocess.run(
        [sys.executable, "scripts/manifest_version.py", "--version", "9.9.9"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert primera.stdout == segunda.stdout
    manifest = json.loads(primera.stdout)
    assert manifest["version"] == "9.9.9"
    assert manifest["schema_version"] == MANIFEST_VERSION_SCHEMA
    assert "src/agente1/manifest_version.py" in manifest["archivos_sha256"]
    assert "scripts/manifest_version.py" in manifest["archivos_sha256"]


def test_script_generador_escribe_archivo(tmp_path: Path) -> None:
    destino = tmp_path / "manifest-version.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/manifest_version.py",
            "--version",
            "9.9.9",
            "--salida",
            str(destino),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(destino.read_text(encoding="utf-8"))["version"] == "9.9.9"


def test_manifest_corte_referencia_version_y_manifest() -> None:
    salida = subprocess.run(
        [sys.executable, "scripts/manifest_corte.py", "--corte", "2026-10-14"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    manifest = json.loads(salida.stdout)

    assert "fuentes_sha256" not in manifest
    assert manifest["corte"] == "2026-10-14"
    assert manifest["version"] == leer_manifest(ROOT / MANIFEST_VERSION_NOMBRE)["version"]
    assert manifest["manifest_version_sha256"] == sha256_archivo(
        ROOT / MANIFEST_VERSION_NOMBRE
    )
    # El dataset del corte se hashea aunque no sea un archivo controlado: sin
    # su hash la evidencia del corte no se reproduce.
    assert manifest["datos_sinteticos_sha256"] == {
        "data/actividades_sinteticas.csv": sha256_archivo(
            ROOT / "data" / "actividades_sinteticas.csv"
        )
    }
    assert manifest["configuracion"]["prompt_version_gacetilla"]
