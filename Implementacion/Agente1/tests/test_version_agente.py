"""Identidad de la versión del agente en la auditoría (#93).

Cada versión del agente se instala con su manifest (`manifest-version.json`,
ADR 0010) y todo registro de auditoría nuevo lleva `version_agente` —la de
`pyproject.toml`, fuente única— y `manifest_version_sha256` —el hash del
manifest versionado—. Así una pieza se rastrea hasta la versión exacta y la
huella de lo controlado que la produjo.

La escritura vive en `agente1.registro_auditoria.escribir_registro`: los
módulos delegan ahí, de modo que ningún log nuevo se olvide de la identidad.
Este módulo prueba el helper y, por el camino real de cada productor, la línea
que queda en disco.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from datetime import time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

from agente1 import FakeGenerator, procesar_fila_csv
from agente1.certificados import (
    RegistroCertificadosMemoria,
    SolicitudCertificado,
    procesar_certificado,
)
from agente1.confirmaciones import (
    RegistroConfirmacionesMemoria,
    SolicitudConfirmacion,
    procesar_confirmacion,
)
from agente1.decisiones_form import (
    RESULTADO_REGISTRADA,
    TIPO_LOTE,
    RegistroDecisiones,
    ResultadoDecision,
)
from agente1.insumos_corrida import RegistroInsumosArchivo
from agente1.linea_descriptiva import generar_linea_descriptiva
from agente1.manifest_version import (
    MANIFEST_VERSION_NOMBRE,
    identidad_version_agente,
    sha256_archivo,
    version_desde_pyproject,
)
from agente1.posts import procesar_post
from agente1.recordatorios import registrar_plantilla_recordatorio
from agente1.registro_auditoria import (
    escribir_registro,
    registro_con_identidad,
)
from agente1.respaldo import AuditoriaRespaldo
from agente1.scheduler import ConfiguracionScheduler, disparar

ROOT = Path(__file__).resolve().parents[1]
ZONA = ZoneInfo("America/Argentina/Buenos_Aires")

VERSION_ESPERADA = version_desde_pyproject(ROOT)
HASH_MANIFEST_ESPERADO = sha256_archivo(ROOT / MANIFEST_VERSION_NOMBRE)


def assert_identidad(registro: dict) -> None:
    """El registro lleva la versión instalada y el hash del manifest."""

    assert registro["version_agente"] == VERSION_ESPERADA
    assert registro["manifest_version_sha256"] == HASH_MANIFEST_ESPERADO


def _ultima_linea(path: Path) -> dict:
    lineas = [linea for linea in path.read_text(encoding="utf-8").splitlines() if linea]
    return json.loads(lineas[-1])


def _config_scheduler(**cambios) -> ConfiguracionScheduler:
    base: dict = {
        "intervalo_s": 300,
        "dias": frozenset({1, 2, 3, 4, 5}),
        "desde": dtime(8, 0),
        "hasta": dtime(16, 0),
        "zona": ZONA,
        "repo": Path("/repo"),
        "registro_confirmaciones": None,
    }
    base.update(cambios)
    return ConfiguracionScheduler(**base)


# --- La identidad de la versión -----------------------------------------


def test_identidad_toma_pyproject_y_manifest() -> None:
    identidad = identidad_version_agente()

    assert identidad == {
        "version_agente": VERSION_ESPERADA,
        "manifest_version_sha256": HASH_MANIFEST_ESPERADO,
    }


def test_la_version_sale_de_un_solo_lugar(tmp_path: Path) -> None:
    """Sin argumentos, la versión es la de `pyproject.toml`: no se repite."""

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "7.7.7"\n', encoding="utf-8"
    )

    assert identidad_version_agente(tmp_path)["version_agente"] == "7.7.7"


def test_la_identidad_tolera_que_falte_el_manifest(tmp_path: Path) -> None:
    """Un registro no deja de escribirse porque falte el manifest o el pyproject.

    El fail-closed del arranque es el que exige el manifest en modo operación
    (ADR 0010); la auditoría no puede dejar de asentar por eso.
    """

    identidad = identidad_version_agente(tmp_path)

    assert identidad["version_agente"] is None
    assert identidad["manifest_version_sha256"] is None


def test_registro_con_identidad_pisa_el_valor_viejo() -> None:
    registro = {"evento": "x", "version_agente": "0.0.0-viejo"}

    completo = registro_con_identidad(registro)

    assert completo["evento"] == "x"
    assert completo["version_agente"] == VERSION_ESPERADA
    assert completo["manifest_version_sha256"] == HASH_MANIFEST_ESPERADO
    # No muta el original.
    assert registro["version_agente"] == "0.0.0-viejo"


def test_escribir_registro_anexa_con_identidad_y_orden_estable(tmp_path: Path) -> None:
    path = tmp_path / "logs" / "auditoria.jsonl"

    primera = escribir_registro(path, {"b": 2, "a": 1})
    segunda = escribir_registro(path, {"b": 2, "a": 1})

    assert primera == segunda
    lineas = path.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 2
    # Claves ordenadas: comparables e hasheables.
    assert lineas[0] == lineas[1]
    assert json.loads(lineas[0])["version_agente"] == VERSION_ESPERADA


# --- Cada productor real ------------------------------------------------


def test_ejecuciones_de_gacetilla_llevan_identidad(tmp_path: Path) -> None:
    csv_path = tmp_path / "actividades.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=[
                "id_actividad",
                "titulo",
                "descripcion",
                "fecha_inicio",
                "publico",
                "organiza",
                "contacto",
                "fuente",
            ],
        )
        writer.writeheader()
        # Sin `organiza`: el pipeline corta antes de generar y deja constancia.
        writer.writerow(
            {
                "id_actividad": "SYN-001",
                "titulo": "Taller sintético",
                "descripcion": "Actividad ficticia.",
                "fecha_inicio": "2026-08-05",
                "publico": "Comunidad universitaria",
                "organiza": "",
                "contacto": "pruebas@example.invalid",
                "fuente": "Dataset sintético versionado",
            }
        )

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-001",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator("no se invoca"),
    )

    assert resultado.log_path is not None
    assert_identidad(_ultima_linea(resultado.log_path))


def test_ejecuciones_de_post_llevan_identidad(tmp_path: Path) -> None:
    class FuenteFake:
        def obtener(self, id_actividad: str) -> dict[str, str]:
            return {
                "id_actividad": "SYN-POST-001",
                "titulo": "Taller sintético",
                "descripcion": "Actividad ficticia.",
                "fecha_inicio": "2026-08-20",
                "publico": "Comunidad universitaria",
                "organiza": "Equipo de prueba",
                "contacto": "pruebas@example.invalid",
                "fuente": "Dataset sintético versionado",
                "lugar": "Aula de prueba",
            }

    salida = (
        "CANAL: instagram\n"
        "TEXTO:\nTaller sintético, 2026-08-20, Equipo de prueba, "
        "pruebas@example.invalid, Aula de prueba.\n"
        "HASHTAGS:\n#Taller #ComunidadUniversitaria"
    )
    resultado = procesar_post(
        fuente=FuenteFake(),
        id_solicitud="SYN-POST-001",
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida),
    )

    assert resultado.log_path is not None
    assert_identidad(_ultima_linea(resultado.log_path))


def test_certificados_llevan_identidad(tmp_path: Path) -> None:
    solicitud = SolicitudCertificado(
        id_certificado="CERT-001",
        nombre_titular="Ana Pérez",
        documento_titular="30123456",
        tipo_certificado="APROBACION",
        actividad="Taller de robótica educativa",
        fecha="28 de agosto de 2026",
        organiza="Secretaría de Extensión Universitaria",
        firmante="Coordinación de Extensión",
    )
    resultado = procesar_certificado(
        solicitud=solicitud,
        directorio_salida=tmp_path,
        registro=RegistroCertificadosMemoria(),
    )

    assert_identidad(_ultima_linea(resultado.log_path))


def test_confirmaciones_llevan_identidad(tmp_path: Path) -> None:
    solicitud = SolicitudConfirmacion(
        id_inscripcion="INS-001",
        nombre_destinatario="Ana Pérez",
        email_destinatario="ana.perez@example.test",
        actividad="Taller de robótica educativa",
        fecha="28 de agosto de 2026, 18:00",
        lugar="Aula 4",
        organiza="Secretaría de Extensión Universitaria",
        contacto="extension@example.test",
    )
    resultado = procesar_confirmacion(
        solicitud=solicitud,
        directorio_salida=tmp_path,
        registro=RegistroConfirmacionesMemoria(),
    )

    assert_identidad(_ultima_linea(resultado.log_path))


def test_recordatorios_llevan_identidad(tmp_path: Path) -> None:
    resultado = registrar_plantilla_recordatorio(
        registro=RegistroConfirmacionesMemoria(),
        directorio_salida=tmp_path,
    )

    assert_identidad(_ultima_linea(resultado.log_path))


def test_lineas_descriptivas_llevan_identidad(tmp_path: Path) -> None:
    resultado = generar_linea_descriptiva(
        fila={"id_actividad": "SYN-001", "titulo": "Taller sintético"},
        directorio_salida=tmp_path,
        generator=FakeGenerator("línea que no pasa los gates"),
    )

    assert resultado.estado == "INCOMPLETA"
    assert_identidad(_ultima_linea(resultado.log_path))


def test_decisiones_procesadas_llevan_identidad(tmp_path: Path) -> None:
    registro = RegistroDecisiones(tmp_path)
    registro.registrar(
        ResultadoDecision(
            id_respuesta="resp-001",
            correo_hash="0" * 64,
            rol="coordinador_extension",
            rol_origen="padron",
            tipo=TIPO_LOTE,
            objeto_id="lote-syn-001-abc",
            decision="apruebo_lote",
            resultado=RESULTADO_REGISTRADA,
            rechazo_codigo=None,
            marca_temporal_form="2026-10-14T12:00:00Z",
            timestamp="2026-10-14T12:00:01Z",
        )
    )

    assert_identidad(_ultima_linea(tmp_path / "decisiones-procesadas.jsonl"))


def test_corridas_del_scheduler_llevan_identidad(tmp_path: Path) -> None:
    def corrida() -> dict[str, object]:
        return {"estado": "OK", "filas_leidas": 0, "filas_escritas": 0}

    entrada = disparar(
        ahora=datetime(2026, 10, 5, 10, 7, tzinfo=ZONA),
        corrida=corrida,
        config=_config_scheduler(),
        directorio=tmp_path,
    )

    # La línea devuelta es la misma que quedó asentada.
    assert_identidad(entrada)
    assert_identidad(_ultima_linea(tmp_path / "logs" / "scheduler-corridas.jsonl"))


def test_respaldo_lleva_identidad(tmp_path: Path) -> None:
    AuditoriaRespaldo(tmp_path).anexar(
        evento="respaldo",
        correlation_id="corr-1",
        campos={"estado": "ok"},
    )

    assert_identidad(_ultima_linea(tmp_path / "logs" / "respaldo-diario.jsonl"))


def test_insumos_procesados_llevan_identidad(tmp_path: Path) -> None:
    registro = RegistroInsumosArchivo(tmp_path)
    registro.registrar_inicio(
        "corr-1",
        meta={
            "producer": "A3",
            "payload_type": "evento",
            "payload_hash": "0" * 64,
            "data_origin": "aviso_sintetico",
            "cargado_por": "productor_provisional",
        },
    )

    assert_identidad(_ultima_linea(tmp_path / "insumos-procesados.jsonl"))
