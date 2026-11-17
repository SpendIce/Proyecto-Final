"""Runtime desplegable de la emisión durable (#168): entrypoint, compose
y la fábrica del servicio web — que siempre construye, sin red ni DB."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker" / "compose.yaml"
sys.path.insert(0, str(ROOT / "src"))


def _cargar(nombre: str, ruta: Path):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


def test_el_entrypoint_lanza_el_worker_de_certificados() -> None:
    ep = _cargar(
        "entrypoint_durable",
        ROOT / "scripts" / "contenedor_entrypoint.py",
    )
    comando = ep.comando_para(["worker-certificados", "--una-vez"])
    assert comando[1].endswith("scripts/worker_certificados_web.py")
    assert comando[2:] == ["--una-vez"]


def test_el_compose_declara_el_worker_sin_ollama() -> None:
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    servicio = compose["services"]["worker-certificados"]
    assert "canal-web" in servicio["profiles"]
    assert servicio["command"][0] == "worker-certificados"
    entorno = servicio["environment"]
    for clave in (
        "AGENTE1_POSTGRES_DSN",
        "AGENTE1_PADRON_ROLES_CSV",
        "AGENTE1_DECISIONES_DIR",
        "AGENTE1_CERTIFICADOS_RECURSOS_DIR",
        "AGENTE1_PLANTILLAS_APROBADAS_PATH",
        "AGENTE1_WEB_MODO_DEMO",
        "AGENTE1_ESTADO",
        "AGENTE1_ENV_FILE",
    ):
        assert clave in entorno
    assert "migrador" in servicio["depends_on"]
    assert "ollama" not in servicio["depends_on"]
    # Certificados no genera texto: sin la red interna del modelo.
    assert "modelo" not in servicio["networks"]
    assert set(servicio["networks"]) == {"canal", "salida"}


def test_el_compose_expone_los_recursos_a_la_web() -> None:
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    entorno = compose["services"]["web"]["environment"]
    assert "AGENTE1_CERTIFICADOS_RECURSOS_DIR" in entorno
    assert "AGENTE1_PLANTILLAS_APROBADAS_PATH" in entorno


def test_el_worker_sin_dsn_falla_cerrado_sin_tocar_la_base() -> None:
    worker = _cargar(
        "worker_certificados",
        ROOT / "scripts" / "worker_certificados_web.py",
    )
    assert worker.main([], environ={}) == 2


def test_la_fabrica_construye_sin_red_ni_base(tmp_path) -> None:
    """Con el entorno vacío el servicio existe: lo que falta queda como
    bloqueo, no como excepción de arranque ni conexión abierta."""
    from agente1.web.emision_certificados_runtime import (
        construir_emision_certificados_web,
    )

    conexiones = []

    def fabrica():
        conexiones.append(True)
        raise AssertionError("la fábrica no debe conectar en arranque")

    servicio = construir_emision_certificados_web(
        {}, conexion_factory=fabrica
    )
    assert servicio is not None
    assert conexiones == []
    # Sin padrón ni entorno Gmail, el servicio levanta igual: la
    # pantalla muestra los bloqueos en vez de caer.
    for metodo in ("consultar", "solicitar", "descargar", "correr_una_vez"):
        assert callable(getattr(servicio, metodo))


def test_la_fabrica_solo_conecta_cuando_un_metodo_lo_pide() -> None:
    from agente1.web.emision_certificados import (
        ActorCertificadosWeb,
        ErrorEmisionWeb,
    )
    from agente1.web.emision_certificados_runtime import (
        construir_emision_certificados_web,
    )

    conexiones = []

    def fabrica():
        conexiones.append(True)
        return object()  # sin `.execute`: basta ver que se llamó

    servicio = construir_emision_certificados_web(
        {}, conexion_factory=fabrica
    )
    assert conexiones == []
    actor = ActorCertificadosWeb(
        solicitante_hash="a" * 64,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="google",
        modo_demo=False,
    )
    # Sin actor se rechaza antes de la base: la fábrica sigue cerrada.
    with pytest.raises(ErrorEmisionWeb):
        servicio.consultar("lote-1", actor=None)
    assert conexiones == []
    # Con actor válido el método pide el lote: ahí recién se conecta.
    with pytest.raises(Exception):
        servicio.consultar("lote-1", actor=actor)
    assert conexiones == [True]
