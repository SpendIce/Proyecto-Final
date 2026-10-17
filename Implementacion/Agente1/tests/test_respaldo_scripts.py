"""Scripts del respaldo diario y su cableado en el scheduler (#86).

Ejercita `scripts/respaldar_estado.py` y `scripts/restaurar_respaldo.py`
por su `main` con entorno inyectado — el mismo camino que corre el slot
diario — y la composición del mantenimiento diario en `cli_scheduler`:
purga antes que respaldo, respaldo sólo cuando el entorno lo declara y la
corrida sigue cuando el paso falla.
"""

import csv
import json
import sys
import tarfile
from datetime import date, datetime, timezone
from pathlib import Path

from agente1.cli_scheduler import main as main_scheduler
from agente1.insumos_corrida import COLUMNAS_INSUMOS_AGENTES_V1
from agente1.respaldo import (
    AUDITORIA_NOMBRE,
    AVISOS_OFFLINE_NOMBRE,
    NOMBRE_MANIFIESTO,
    nombre_respaldo,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import respaldar_estado  # noqa: E402
import restaurar_respaldo  # noqa: E402

REPO = ROOT.parents[1]
MARCA = "2026-10-05T13:00:00+00:00"  # lunes 10:00 en Buenos Aires
DENTRO = "2026-10-05T10:07:00-03:00"

SALIDA_CONFORME = (
    "## TÍTULO\n"
    "Evento sintético\n\n"
    "## DATOS DE LA ACTIVIDAD\n"
    "Fecha: 2026-10-15\n"
    "Organiza: Equipo ficticio\n\n"
    "## CONTACTO\n"
    "pruebas@example.invalid\n\n"
    "## BAJADA\n"
    "Propuesta abierta para acercar la ingeniería a la comunidad.\n\n"
    "## CUERPO\n"
    "La facultad acompaña la actividad con información y un espacio de consulta para el público asistente."
)


def poblar_salida(directorio: Path) -> None:
    (directorio / "logs").mkdir(parents=True)
    (directorio / "logs" / "ejecuciones.jsonl").write_text(
        '{"evento":"x"}\n', encoding="utf-8"
    )


def tabla_y_directorio(tmp_path: Path) -> tuple[Path, Path]:
    tabla = tmp_path / "insumos.csv"
    directorio = tmp_path / "salida"
    envelope = {
        "schema": "agente1.insumo.v1",
        "schema_version": "1.0.0",
        "channel": "a1.communication_input",
        "producer": "A3",
        "producer_schema_version": "a3_candidate_v1",
        "correlation_id": "corr-respaldo-test-001",
        "timestamp": "2026-10-01T10:00:00-03:00",
        "data_origin": "provisional_producer",
        "provenance": {"sources": [{"ref": "opaque:cli:src-1", "sha256": "a" * 64}]},
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
    with tabla.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.writer(archivo)
        writer.writerow(COLUMNAS_INSUMOS_AGENTES_V1)
        writer.writerow([json.dumps(envelope, ensure_ascii=False), "ope-1", "", ""])
    return tabla, directorio


def args_offline(tabla: Path, directorio: Path) -> list[str]:
    return [
        "--tabla",
        str(tabla),
        "--directorio",
        str(directorio),
        "--fake-output",
        SALIDA_CONFORME,
    ]


# ---------------------------------------------------------------------------
# scripts/respaldar_estado.py
# ---------------------------------------------------------------------------


def test_script_respaldar_modo_fake(tmp_path: Path, capsys) -> None:
    salida = tmp_path / "salida"
    registro = tmp_path / "registro"
    poblar_salida(salida)
    registro.mkdir()
    carpeta = tmp_path / "carpeta-drive-fake"

    codigo = respaldar_estado.main(
        ["--salida", str(salida), "--registro", str(registro), "--ahora", MARCA],
        environ={"AGENTE1_RESPALDO_CARPETA_FAKE": str(carpeta)},
    )

    salida_json = json.loads(capsys.readouterr().out)
    assert codigo == 0
    assert salida_json["status"] == "OK"
    assert salida_json["modo"] == "fake_local"
    assert salida_json["subido"] is True
    # El artefacto quedó en la carpeta fake con el nombre del día.
    artefacto = carpeta / nombre_respaldo(
        datetime(2026, 10, 5, tzinfo=timezone.utc).date()
    )
    assert artefacto.is_file()
    with tarfile.open(artefacto, "r:gz") as tar:
        assert NOMBRE_MANIFIESTO in tar.getnames()


def test_script_respaldar_sin_config_falla_cerrada(tmp_path: Path, capsys) -> None:
    codigo = respaldar_estado.main(
        ["--salida", str(tmp_path)], environ={}
    )
    salida = json.loads(capsys.readouterr().out)
    assert codigo == 2
    assert salida["error_code"] == "respaldo_config_incomplete"


def test_script_respaldar_config_desconocida(tmp_path: Path, capsys) -> None:
    codigo = respaldar_estado.main(
        ["--salida", str(tmp_path)],
        environ={"AGENTE1_RESPALDO_OTRA": "x"},
    )
    assert codigo == 2
    assert (
        json.loads(capsys.readouterr().out)["error_code"]
        == "respaldo_config_unknown_key"
    )


def test_script_respaldar_live_exige_lista_de_prueba(tmp_path: Path, capsys) -> None:
    """En live el aviso no puede salir sin la lista de Gmail: config rota."""

    carpeta_id = "a" * 44
    codigo = respaldar_estado.main(
        ["--salida", str(tmp_path)],
        environ={
            "AGENTE1_RESPALDO_CARPETA_ID": carpeta_id,
            "AGENTE1_RESPALDO_CONFIRMAR_ESCRITURA": "SI",
            "AGENTE1_RESPALDO_AVISO_DESTINATARIO": "operador@example.com",
        },
    )
    assert codigo == 2
    assert (
        json.loads(capsys.readouterr().out)["error_code"]
        == "gmail_test_list_missing"
    )


def test_script_respaldar_live_aviso_fuera_de_lista(tmp_path: Path, capsys) -> None:
    carpeta_id = "a" * 44
    codigo = respaldar_estado.main(
        ["--salida", str(tmp_path)],
        environ={
            "AGENTE1_RESPALDO_CARPETA_ID": carpeta_id,
            "AGENTE1_RESPALDO_CONFIRMAR_ESCRITURA": "SI",
            "AGENTE1_RESPALDO_AVISO_DESTINATARIO": "operador@example.com",
            "AGENTE1_GMAIL_DESTINATARIOS_PRUEBA": "otro@example.com",
        },
    )
    assert codigo == 2
    assert (
        json.loads(capsys.readouterr().out)["error_code"]
        == "respaldo_aviso_off_test_list"
    )


def test_script_respaldar_falla_de_destino_avisa_offline(
    tmp_path: Path, capsys
) -> None:
    """El paso falla → el aviso al operador queda en el fake declarado."""

    salida = tmp_path / "salida"
    poblar_salida(salida)
    carpeta = tmp_path / "carpeta"
    # Un directorio que ocupa el nombre del artefacto de hoy: `listar` lo
    # ignora (no es archivo) pero `subir` no puede crear el archivo — la
    # falla es determinística y sin juegos de permisos.
    (carpeta / nombre_respaldo(date(2026, 10, 5))).mkdir(parents=True)

    codigo = respaldar_estado.main(
        ["--salida", str(salida), "--ahora", MARCA],
        environ={"AGENTE1_RESPALDO_CARPETA_FAKE": str(carpeta)},
    )

    assert codigo == 2
    avisos = salida / "logs" / AVISOS_OFFLINE_NOMBRE
    (linea,) = [
        json.loads(t) for t in avisos.read_text(encoding="utf-8").splitlines()
    ]
    assert linea["modo"] == "offline_fake"
    assert "falló" in linea["asunto"]
    # La falla también quedó en la auditoría del respaldo.
    auditoria = salida / "logs" / AUDITORIA_NOMBRE
    eventos = {
        json.loads(t)["evento"]
        for t in auditoria.read_text(encoding="utf-8").splitlines()
    }
    assert "respaldo_fallido" in eventos


# ---------------------------------------------------------------------------
# scripts/restaurar_respaldo.py
# ---------------------------------------------------------------------------


def test_script_restaurar_end_to_end(tmp_path: Path, capsys) -> None:
    salida = tmp_path / "salida-origen"
    registro = tmp_path / "registro-origen"
    poblar_salida(salida)
    registro.mkdir()
    carpeta = tmp_path / "carpeta"
    respaldar_estado.main(
        ["--salida", str(salida), "--registro", str(registro), "--ahora", MARCA],
        environ={"AGENTE1_RESPALDO_CARPETA_FAKE": str(carpeta)},
    )
    capsys.readouterr()
    (artefacto,) = list(carpeta.glob("*.tar.gz"))

    destino_salida = tmp_path / "destino-salida"
    destino_registro = tmp_path / "destino-registro"
    codigo = restaurar_respaldo.main(
        [
            "--artefacto",
            str(artefacto),
            "--salida",
            str(destino_salida),
            "--registro",
            str(destino_registro),
        ]
    )

    salida_json = json.loads(capsys.readouterr().out)
    assert codigo == 0
    assert salida_json["status"] == "OK"
    assert salida_json["archivos_restaurados"] > 0
    assert (destino_salida / "logs" / "ejecuciones.jsonl").exists()


def test_script_restaurar_artefacto_inexistente(tmp_path: Path, capsys) -> None:
    codigo = restaurar_respaldo.main(
        [
            "--artefacto",
            str(tmp_path / "no-existe.tar.gz"),
            "--salida",
            str(tmp_path / "salida"),
        ]
    )
    assert codigo == 2
    assert (
        json.loads(capsys.readouterr().out)["error_code"]
        == "respaldo_entrada_inaccesible"
    )


# ---------------------------------------------------------------------------
# Cableado en el slot diario del scheduler
# ---------------------------------------------------------------------------


def env_scheduler(
    registro: Path, carpeta_fake: Path
) -> dict[str, str]:
    return {
        "AGENTE1_SCHEDULER_REPO": str(REPO),
        "AGENTE1_SCHEDULER_REGISTRO_CONFIRMACIONES": str(registro),
        "AGENTE1_RESPALDO_CARPETA_FAKE": str(carpeta_fake),
    }


def test_scheduler_corre_purga_y_respaldo_en_orden(
    tmp_path: Path, capsys
) -> None:
    """Configurado, el respaldo corre detrás de la purga en el slot diario."""

    tabla, directorio = tabla_y_directorio(tmp_path)
    registro = tmp_path / "registro-confirmaciones"
    registro.mkdir()
    carpeta = tmp_path / "carpeta"

    codigo = main_scheduler(
        ["--una-corrida", "--ahora", DENTRO, *args_offline(tabla, directorio)],
        environ=env_scheduler(registro, carpeta),
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 0
    assert salida["resultado"] == "completada"
    assert salida["mantenimiento"] == {
        "purga": "completada",
        "respaldo": "completada",
    }
    # El artefacto del día quedó en la carpeta fake: el mecanismo real del
    # paso corrió contra el destino declarado, sin red.
    assert list(carpeta.glob("agente1-respaldo-*.tar.gz"))


def test_scheduler_respaldo_falla_no_detiene_la_corrida(
    tmp_path: Path, capsys
) -> None:
    """Un respaldo roto se asienta `falla` y la corrida sigue su camino."""

    tabla, directorio = tabla_y_directorio(tmp_path)
    registro = tmp_path / "registro-confirmaciones"
    registro.mkdir()
    # La carpeta fake no es un directorio: la subida falla cerrada.
    carpeta = tmp_path / "carpeta"
    carpeta.write_text("ocupado", encoding="utf-8")

    codigo = main_scheduler(
        ["--una-corrida", "--ahora", DENTRO, *args_offline(tabla, directorio)],
        environ=env_scheduler(registro, carpeta),
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 0
    assert salida["resultado"] == "completada"
    assert salida["mantenimiento"] == {
        "purga": "completada",
        "respaldo": "falla",
    }
    # La corrida hizo lo suyo igual: la fila quedó escrita.
    with tabla.open(encoding="utf-8", newline="") as archivo:
        assert list(csv.reader(archivo))[1][2] == "borrador generado"


def test_scheduler_respaldo_falla_si_la_purga_fallo(tmp_path: Path, capsys) -> None:
    """Ningún artefacto conserva texto que la retención ya venció: si la
    purga del día falla, el respaldo del día también se asienta `falla`."""

    tabla, directorio = tabla_y_directorio(tmp_path)
    # El registro apunta a algo que no es directorio: la purga sale 2.
    registro = tmp_path / "registro-roto"
    registro.write_text("no es un directorio", encoding="utf-8")
    carpeta = tmp_path / "carpeta"

    codigo = main_scheduler(
        ["--una-corrida", "--ahora", DENTRO, *args_offline(tabla, directorio)],
        environ=env_scheduler(registro, carpeta),
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 0
    assert salida["mantenimiento"] == {"purga": "falla", "respaldo": "falla"}
    # Y no se subió ningún artefacto.
    assert not list(carpeta.glob("*.tar.gz"))


def test_scheduler_sin_carpeta_respaldo_queda_pendiente(
    tmp_path: Path, capsys
) -> None:
    """Sin `AGENTE1_RESPALDO_*` el paso se asienta `pendiente`, como antes."""

    tabla, directorio = tabla_y_directorio(tmp_path)
    registro = tmp_path / "registro-confirmaciones"
    registro.mkdir()

    codigo = main_scheduler(
        ["--una-corrida", "--ahora", DENTRO, *args_offline(tabla, directorio)],
        environ={
            "AGENTE1_SCHEDULER_REPO": str(REPO),
            "AGENTE1_SCHEDULER_REGISTRO_CONFIRMACIONES": str(registro),
        },
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 0
    assert salida["mantenimiento"] == {
        "purga": "completada",
        "respaldo": "pendiente",
    }


def test_scheduler_respaldo_config_rota_se_asienta_falla(
    tmp_path: Path, capsys
) -> None:
    """Una `AGENTE1_RESPALDO_*` mal cargada no queda muda: el paso falla."""

    tabla, directorio = tabla_y_directorio(tmp_path)
    registro = tmp_path / "registro-confirmaciones"
    registro.mkdir()
    env = env_scheduler(registro, tmp_path / "carpeta")
    # Carpeta fake + destinatario declarado: combinación inválida.
    env["AGENTE1_RESPALDO_AVISO_DESTINATARIO"] = "operador@example.com"

    codigo = main_scheduler(
        ["--una-corrida", "--ahora", DENTRO, *args_offline(tabla, directorio)],
        environ=env,
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 0
    assert salida["mantenimiento"]["respaldo"] == "falla"
    assert salida["resultado"] == "completada"
