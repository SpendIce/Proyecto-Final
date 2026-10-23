"""Contrato del empaquetado en contenedores (#143, ADR 0013).

Prueba lo que el contenedor promete hacia afuera, sin Docker:

- el entrypoint carga el env file en tiempo de ejecución, reenvía loopback a
  Ollama sin aflojar el adaptador y no arranca si la integridad no coincide;
- el compose mantiene el aislamiento decidido (Ollama sin egreso, agente sin
  privilegios ni socket de Docker, consola sólo en loopback del host);
- el `Dockerfile` fija la base por digest, corre como no root y no hornea
  secretos ni modelos.

Lo que exige un Docker real (correr la imagen, el egreso efectivo de la red
interna) lo prueba el workflow `agente1-imagen` y queda en la evidencia.
"""

from __future__ import annotations

import importlib.util
import socket
import sys
import threading
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker" / "compose.yaml"
DOCKERFILE = ROOT / "Dockerfile"


def _cargar_entrypoint():
    spec = importlib.util.spec_from_file_location(
        "contenedor_entrypoint", ROOT / "scripts" / "contenedor_entrypoint.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


ep = _cargar_entrypoint()


# --- Entrypoint: env file ------------------------------------------------


def test_env_file_se_lee_con_comentarios_export_y_comillas(tmp_path: Path) -> None:
    archivo = tmp_path / "workspace.env"
    archivo.write_text(
        "# comentario\n\nAGENTE1_A=uno\nexport AGENTE1_B='dos tres'\nAGENTE1_C=\"x=y\"\n",
        encoding="utf-8",
    )
    assert ep.leer_env_file(archivo) == {
        "AGENTE1_A": "uno",
        "AGENTE1_B": "dos tres",
        "AGENTE1_C": "x=y",
    }


def test_env_file_invalido_no_arranca(tmp_path: Path) -> None:
    archivo = tmp_path / "workspace.env"
    archivo.write_text("ESTO NO ES UNA ASIGNACION\n", encoding="utf-8")
    with pytest.raises(ep.ConfigError):
        ep.leer_env_file(archivo)


def test_env_file_declarado_y_ausente_no_arranca(tmp_path: Path) -> None:
    with pytest.raises(ep.ConfigError):
        ep.entorno_hijo({"AGENTE1_ENV_FILE": str(tmp_path / "no-existe.env")})


def test_el_env_file_llega_al_hijo_y_no_al_entorno_del_contenedor(tmp_path: Path) -> None:
    archivo = tmp_path / "workspace.env"
    archivo.write_text("AGENTE1_WORKSPACE_AMBIENTE=D2\n", encoding="utf-8")
    base = {"AGENTE1_ENV_FILE": str(archivo), "PATH": "/usr/bin"}
    hijo = ep.entorno_hijo(base)
    assert hijo["AGENTE1_WORKSPACE_AMBIENTE"] == "D2"
    assert "AGENTE1_WORKSPACE_AMBIENTE" not in base


# --- Entrypoint: relay de loopback ---------------------------------------


@pytest.mark.parametrize("valor", ["ollama", "ollama:", ":11434", "ollama:puerto", "ollama:70000"])
def test_upstream_invalido_no_arranca(valor: str) -> None:
    with pytest.raises(ep.ConfigError):
        ep.parsear_upstream(valor)


def test_upstream_vacio_desactiva_el_relay() -> None:
    assert ep.parsear_upstream("") is None
    assert ep.parsear_upstream("ollama:11434") == ("ollama", 11434)


def test_relay_reenvia_de_loopback_al_upstream_y_vuelve() -> None:
    servidor = socket.create_server(("127.0.0.1", 0))
    puerto_upstream = servidor.getsockname()[1]

    def eco() -> None:
        conexion, _ = servidor.accept()
        with conexion:
            datos = conexion.recv(1024)
            conexion.sendall(b"ollama:" + datos)

    hilo = threading.Thread(target=eco, daemon=True)
    hilo.start()
    relay = ep.Relay(("127.0.0.1", puerto_upstream), puerto=0)
    puerto = relay.iniciar()
    try:
        with socket.create_connection(("127.0.0.1", puerto), timeout=5) as cliente:
            cliente.sendall(b"hola")
            assert cliente.recv(1024) == b"ollama:hola"
    finally:
        relay.detener()
        servidor.close()


def test_relay_escucha_solo_en_loopback() -> None:
    assert ep.RELAY_HOST == "127.0.0.1"
    assert ep.RELAY_PUERTO == 11434


# --- Entrypoint: comandos e integridad -----------------------------------


def test_comandos_del_contenedor() -> None:
    assert ep.comando_para(["verificar"]) is None
    consola = ep.comando_para([])
    assert consola[1].endswith("scripts/demo_visual_plan_b.py")
    assert consola[2:] == ["--host", "0.0.0.0", "--port", "8080"]
    assert ep.comando_para(["scheduler", "--loop"])[1:] == ["-m", "agente1", "scheduler", "--loop"]
    assert ep.comando_para(["smoke", "--live"])[1].endswith("scripts/workspace_smoke.py")
    assert ep.comando_para(["python", "-V"]) == ["python", "-V"]


def test_integridad_que_no_coincide_impide_arrancar(tmp_path: Path, monkeypatch) -> None:
    def falla(estado: Path) -> None:
        raise ep.IntegridadError("integridad_archivos_no_coinciden")

    lanzados: list[object] = []
    monkeypatch.setattr(ep, "verificar", falla)
    monkeypatch.setattr(ep.subprocess, "Popen", lambda *a, **k: lanzados.append(a))
    codigo = ep.main(["consola"], {"AGENTE1_ESTADO": str(tmp_path), "AGENTE1_OLLAMA_UPSTREAM": ""})
    assert codigo == ep.SALIDA_INTEGRIDAD
    assert lanzados == []


def test_config_invalida_impide_arrancar_antes_de_verificar(tmp_path: Path, monkeypatch) -> None:
    verificados: list[Path] = []
    monkeypatch.setattr(ep, "verificar", verificados.append)
    codigo = ep.main(["consola"], {"AGENTE1_ESTADO": str(tmp_path), "AGENTE1_OLLAMA_UPSTREAM": "sin-puerto"})
    assert codigo == ep.SALIDA_CONFIG_INVALIDA
    assert verificados == []


def test_verificar_sale_cero_sin_lanzar_nada(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(ep, "verificar", lambda estado: None)
    monkeypatch.setattr(ep.subprocess, "Popen", lambda *a, **k: pytest.fail("no debe lanzar"))
    assert ep.main(["verificar"], {"AGENTE1_ESTADO": str(tmp_path), "AGENTE1_OLLAMA_UPSTREAM": ""}) == 0


def test_el_hijo_recibe_el_env_file_y_su_codigo_de_salida(tmp_path: Path, monkeypatch) -> None:
    archivo = tmp_path / "workspace.env"
    archivo.write_text("AGENTE1_PRUEBA=valor\n", encoding="utf-8")
    monkeypatch.setattr(ep, "verificar", lambda estado: None)
    codigo = ep.main(
        [sys.executable, "-c", "import os,sys; sys.exit(0 if os.environ['AGENTE1_PRUEBA']=='valor' else 9)"],
        {"AGENTE1_ESTADO": str(tmp_path), "AGENTE1_OLLAMA_UPSTREAM": "", "AGENTE1_ENV_FILE": str(archivo)},
    )
    assert codigo == 0


# --- Compose: aislamiento ------------------------------------------------


@pytest.fixture(scope="module")
def compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def test_ollama_vive_solo_en_una_red_interna(compose: dict) -> None:
    assert compose["networks"]["modelo"]["internal"] is True
    assert compose["services"]["ollama"]["networks"] == ["modelo"]
    assert "ports" not in compose["services"]["ollama"]


def test_ollama_fijado_en_la_version_congelada_y_modelos_en_solo_lectura(compose: dict) -> None:
    ollama = compose["services"]["ollama"]
    assert ollama["image"].startswith("ollama/ollama:0.40.6@sha256:")
    assert any(v.endswith(":/modelos:ro") for v in ollama["volumes"])


@pytest.mark.parametrize("servicio", ["ollama", "consola", "scheduler"])
def test_todos_los_servicios_estan_endurecidos(compose: dict, servicio: str) -> None:
    s = compose["services"][servicio]
    assert s["read_only"] is True
    assert s["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in s["security_opt"]
    assert not s.get("privileged", False)
    assert "network_mode" not in s
    assert s["restart"] == "unless-stopped"
    assert not str(s["user"]).startswith("0")
    for volumen in s.get("volumes", []):
        assert "docker.sock" not in volumen


def test_la_configuracion_del_host_se_monta_en_solo_lectura(compose: dict) -> None:
    for servicio in ("consola", "scheduler"):
        volumenes = compose["services"][servicio]["volumes"]
        config = [v for v in volumenes if "config/agente1" in v]
        assert config and all(v.endswith(":ro") for v in config)


def test_la_consola_se_publica_solo_en_loopback_del_host(compose: dict) -> None:
    for puerto in compose["services"]["consola"]["ports"]:
        assert puerto.startswith("127.0.0.1:")


def test_el_scheduler_queda_apagado_salvo_perfil(compose: dict) -> None:
    assert compose["services"]["scheduler"]["profiles"] == ["scheduler"]


def test_el_agente_llega_a_ollama_por_el_relay(compose: dict) -> None:
    for servicio in ("consola", "scheduler"):
        assert compose["services"][servicio]["environment"]["AGENTE1_OLLAMA_UPSTREAM"] == "ollama:11434"


# --- Dockerfile -----------------------------------------------------------


def test_dockerfile_fija_la_base_por_digest_y_corre_como_no_root() -> None:
    texto = DOCKERFILE.read_text(encoding="utf-8")
    assert "ARG PYTHON_IMAGE=python:3.12-slim@sha256:" in texto
    runtime = texto.split("AS runtime", 1)[1]
    assert "USER 10001" in runtime
    assert 'ENTRYPOINT ["python", "/srv/p100/Implementacion/Agente1/scripts/contenedor_entrypoint.py"]' in runtime


def test_dockerfile_no_hornea_secretos_ni_modelos() -> None:
    runtime = DOCKERFILE.read_text(encoding="utf-8").split("AS runtime", 1)[1]
    copias = [linea for linea in runtime.splitlines() if linea.startswith("COPY")]
    for linea in copias:
        assert ".env" not in linea and ".json" not in linea.replace("manifest-version.json", "")
        assert "models" not in linea and ".runtime" not in linea and "tests" not in linea


def test_el_runtime_lleva_los_datos_que_los_scripts_leen() -> None:
    # `data/` (CSV sintéticos, padrones) y `golden/` (fichas del canal offline)
    # los leen los scripts en tiempo de ejecución; sin ellos HU-012 falla en el
    # contenedor con `runner_unavailable` (encontrado el 23/10 en el servidor).
    runtime = DOCKERFILE.read_text(encoding="utf-8").split("AS runtime", 1)[1]
    for directorio in ("src", "scripts", "data", "golden", "migrations", "systemd", "docker"):
        assert f"COPY {directorio} ./{directorio}" in runtime
