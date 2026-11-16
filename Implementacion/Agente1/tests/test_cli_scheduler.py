"""Subcomando `scheduler`: el disparo de las corridas programadas (#84).

Ejercita `--una-corrida` con `--ahora` fijo contra la tabla CSV offline:
el mismo camino que corre el timer `systemd --user`, sin systemd. La
purga diaria se verifica invocando el script real de #87 como subproceso,
igual que lo haría el slot diario en el host.
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import agente1.cli_scheduler as cli_scheduler
from agente1.cli_scheduler import _pasos_diarios
from agente1.cli_scheduler import main as main_scheduler
from agente1.insumos_corrida import COLUMNAS_INSUMOS_AGENTES_V1
from agente1.scheduler import LOCK_NOMBRE, LOG_NOMBRE

ZONA = ZoneInfo("America/Argentina/Buenos_Aires")
# 2026-10-05 es lunes.
DENTRO = "2026-10-05T10:07:00-03:00"
TICK = "2026-10-05T10:05:00-03:00"
FUERA = "2026-10-04T10:07:00-03:00"  # domingo


def envelope_evento() -> dict[str, object]:
    return {
        "schema": "agente1.insumo.v1",
        "schema_version": "1.0.0",
        "channel": "a1.communication_input",
        "producer": "A3",
        "producer_schema_version": "a3_candidate_v1",
        "correlation_id": "corr-sched-sintetico-001",
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


def escribir_tabla(path: Path, *filas: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.writer(archivo)
        writer.writerow(COLUMNAS_INSUMOS_AGENTES_V1)
        writer.writerows(filas)


def tabla_y_directorio(tmp_path: Path) -> tuple[Path, Path]:
    tabla = tmp_path / "insumos.csv"
    directorio = tmp_path / "salida"
    escribir_tabla(
        tabla,
        [json.dumps(envelope_evento(), ensure_ascii=False), "ope-1", "", ""],
    )
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


def log_path(directorio: Path) -> Path:
    return directorio / "logs" / LOG_NOMBRE


def test_una_corrida_offline_completa_y_audita(tmp_path: Path, capsys) -> None:
    tabla, directorio = tabla_y_directorio(tmp_path)

    codigo = main_scheduler(
        ["--una-corrida", "--ahora", DENTRO, *args_offline(tabla, directorio)],
        environ={},
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 0
    assert salida["record"] == "scheduler_corrida_v1"
    assert salida["resultado"] == "completada"
    assert salida["en_ventana"] is True
    assert salida["inicio_previsto"].startswith(TICK)
    assert salida["corrida"]["filas_escritas"] == 1
    # El log del scheduler nunca arrastra el payload ni el contenido.
    assert "Actividad ficticia" not in json.dumps(salida)
    assert "filas" not in salida["corrida"]
    # La pestaña offline quedó con su estado escrito, igual que con la
    # corrida manual.
    with tabla.open(encoding="utf-8", newline="") as archivo:
        filas = list(csv.reader(archivo))
    assert filas[1][2] == "borrador generado"
    # La línea quedó asentada en el log versionado.
    (linea,) = [
        json.loads(texto)
        for texto in log_path(directorio).read_text(encoding="utf-8").splitlines()
        if texto.strip()
    ]
    assert linea == salida


def test_una_corrida_fuera_de_ventana_omite_sin_tocar(tmp_path: Path, capsys) -> None:
    tabla, directorio = tabla_y_directorio(tmp_path)

    codigo = main_scheduler(
        ["--una-corrida", "--ahora", FUERA, *args_offline(tabla, directorio)],
        environ={},
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 0
    assert salida["resultado"] == "omitida_ventana"
    assert salida["en_ventana"] is False
    assert salida["inicio_previsto"] is None
    # La fila quedó pendiente para la próxima ventana.
    with tabla.open(encoding="utf-8", newline="") as archivo:
        filas = list(csv.reader(archivo))
    assert filas[1][2] == ""


def test_segundo_disparo_del_mismo_tick_es_duplicado(tmp_path: Path, capsys) -> None:
    tabla, directorio = tabla_y_directorio(tmp_path)
    argv = ["--una-corrida", "--ahora", DENTRO, *args_offline(tabla, directorio)]

    assert main_scheduler(argv, environ={}) == 0
    capsys.readouterr()
    codigo = main_scheduler(argv, environ={})

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 0
    assert salida["resultado"] == "omitida_duplicada"


def test_falla_de_la_corrida_queda_asentada_y_devuelve_2(
    tmp_path: Path, capsys
) -> None:
    directorio = tmp_path / "salida"

    codigo = main_scheduler(
        [
            "--una-corrida",
            "--ahora",
            DENTRO,
            "--tabla",
            str(tmp_path / "inexistente.csv"),
            "--directorio",
            str(directorio),
            "--fake-output",
            SALIDA_CONFORME,
        ],
        environ={},
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 2
    assert salida["resultado"] == "falla"
    assert salida["detalle"] == "entrada_inaccesible"
    # La falla quedó auditada con el código cerrado.
    (linea,) = log_path(directorio).read_text(encoding="utf-8").splitlines()
    assert json.loads(linea)["detalle"] == "entrada_inaccesible"


def test_configuracion_scheduler_invalida_falla_cerrada(tmp_path: Path, capsys) -> None:
    tabla, directorio = tabla_y_directorio(tmp_path)

    codigo = main_scheduler(
        ["--una-corrida", *args_offline(tabla, directorio)],
        environ={"AGENTE1_SCHEDULER_INVENTADA": "x"},
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 2
    assert salida == {
        "estado": "INVALIDA",
        "error": "scheduler_config_unknown_key",
    }


def test_ahora_mal_formado_falla_cerrada(tmp_path: Path, capsys) -> None:
    tabla, directorio = tabla_y_directorio(tmp_path)

    codigo = main_scheduler(
        [
            "--una-corrida",
            "--ahora",
            "el martes",
            *args_offline(tabla, directorio),
        ],
        environ={},
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 2
    assert salida["estado"] == "INVALIDA"


def test_exige_elegir_un_mecanismo(tmp_path: Path) -> None:
    tabla, directorio = tabla_y_directorio(tmp_path)
    with pytest.raises(SystemExit):
        main_scheduler(args_offline(tabla, directorio), environ={})


def test_ahora_solo_aplica_a_una_corrida(tmp_path: Path) -> None:
    tabla, directorio = tabla_y_directorio(tmp_path)
    with pytest.raises(SystemExit):
        main_scheduler(
            ["--loop", "--ahora", DENTRO, *args_offline(tabla, directorio)],
            environ={},
        )


def test_max_disparos_solo_aplica_al_loop(tmp_path: Path) -> None:
    tabla, directorio = tabla_y_directorio(tmp_path)
    with pytest.raises(SystemExit):
        main_scheduler(
            [
                "--una-corrida",
                "--max-disparos",
                "1",
                *args_offline(tabla, directorio),
            ],
            environ={},
        )


def test_loop_un_disparo_con_reloj_en_tick(tmp_path: Path, capsys) -> None:
    tabla, directorio = tabla_y_directorio(tmp_path)
    instante = datetime(2026, 10, 5, 10, 5, tzinfo=ZONA)

    codigo = main_scheduler(
        ["--loop", "--max-disparos", "1", *args_offline(tabla, directorio)],
        environ={},
        clock=lambda: instante,
    )

    assert codigo == 0
    (linea,) = log_path(directorio).read_text(encoding="utf-8").splitlines()
    entrada = json.loads(linea)
    assert entrada["resultado"] == "completada"
    assert entrada["inicio_previsto"].startswith(TICK)
    capsys.readouterr()


def test_loop_fuera_de_ventana_duerme_sin_correr(tmp_path: Path) -> None:
    """Fuera de la ventana el bucle espera al próximo tick y no dispara.

    El `dormir` inyectado avanza el reloj falso directamente al próximo
    tick de agenda, así el camino del bucle queda ejercitado sin esperar.
    """

    tabla, directorio = tabla_y_directorio(tmp_path)
    # Domingo 10:07: el bucle duerme hasta el lunes 08:00 y corre ahí.
    instante = {"ahora": datetime(2026, 10, 4, 10, 7, tzinfo=ZONA)}
    dormidas: list[float] = []

    def dormir(segundos: float) -> None:
        dormidas.append(segundos)
        instante["ahora"] += timedelta(seconds=segundos)

    codigo = main_scheduler(
        ["--loop", "--max-disparos", "1", *args_offline(tabla, directorio)],
        environ={},
        clock=lambda: instante["ahora"],
        dormir=dormir,
    )

    assert codigo == 0
    # Una sola espera: del domingo 10:07 al lunes 08:00.
    assert dormidas == [
        (
            datetime(2026, 10, 5, 8, 0, tzinfo=ZONA)
            - datetime(2026, 10, 4, 10, 7, tzinfo=ZONA)
        ).total_seconds()
    ]
    assert instante["ahora"] == datetime(2026, 10, 5, 8, 0, tzinfo=ZONA)
    (linea,) = log_path(directorio).read_text(encoding="utf-8").splitlines()
    assert json.loads(linea)["resultado"] == "completada"


def test_purga_diaria_invoca_el_script_real(tmp_path: Path, capsys) -> None:
    """El slot diario corre la purga de #87 como subproceso, una vez por día.

    `AGENTE1_SCHEDULER_REPO` apunta al checkout real (donde está el
    script) y `AGENTE1_SCHEDULER_REGISTRO_CONFIRMACIONES` a un registro
    vacío: la purga corre de verdad y asienta su propio log.
    """

    tabla, directorio = tabla_y_directorio(tmp_path)
    registro = tmp_path / "registro-confirmaciones"
    registro.mkdir()
    repo = Path(__file__).resolve().parents[3]

    codigo = main_scheduler(
        ["--una-corrida", "--ahora", DENTRO, *args_offline(tabla, directorio)],
        environ={
            "AGENTE1_SCHEDULER_REPO": str(repo),
            "AGENTE1_SCHEDULER_REGISTRO_CONFIRMACIONES": str(registro),
        },
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 0
    # Sin DSN del canal la purga web queda declarada, como el respaldo.
    assert salida["mantenimiento"] == {
        "purga": "completada",
        "purga_canal_web": "pendiente",
        "respaldo": "pendiente",
    }
    # El propio log de la purga (#87) quedó asentado bajo el directorio.
    assert (directorio / "logs" / "confirmaciones-hu012.jsonl").exists()


def test_sin_registro_de_confirmaciones_no_hay_purga(tmp_path: Path, capsys) -> None:
    tabla, directorio = tabla_y_directorio(tmp_path)
    repo = Path(__file__).resolve().parents[3]

    codigo = main_scheduler(
        ["--una-corrida", "--ahora", DENTRO, *args_offline(tabla, directorio)],
        environ={"AGENTE1_SCHEDULER_REPO": str(repo)},
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 0
    # Sin registro configurado el slot sólo declara los pasos futuros.
    assert salida["mantenimiento"] == {
        "purga_canal_web": "pendiente",
        "respaldo": "pendiente",
    }


def test_lock_de_archivo_presente_en_el_directorio(tmp_path: Path, capsys) -> None:
    tabla, directorio = tabla_y_directorio(tmp_path)
    main_scheduler(
        ["--una-corrida", "--ahora", DENTRO, *args_offline(tabla, directorio)],
        environ={},
    )
    capsys.readouterr()
    assert (directorio / LOCK_NOMBRE).exists()


def test_ahora_sin_zona_se_toma_como_utc(tmp_path: Path, capsys) -> None:
    """Un `--ahora` sin offset se interpreta como UTC, no como hora local."""

    tabla, directorio = tabla_y_directorio(tmp_path)
    # 13:05 UTC son las 10:05 en Buenos Aires: cae dentro de la ventana.
    codigo = main_scheduler(
        [
            "--una-corrida",
            "--ahora",
            "2026-10-05T13:05:00",
            *args_offline(tabla, directorio),
        ],
        environ={},
    )

    salida = json.loads(capsys.readouterr().out)
    assert codigo == 0
    assert salida["resultado"] == "completada"
    assert salida["inicio_previsto"].startswith(TICK)


def test_cli_rutea_el_subcomando_scheduler(tmp_path: Path, capsys) -> None:
    from agente1.cli import main as main_cli

    tabla, directorio = tabla_y_directorio(tmp_path)
    codigo = main_cli(
        [
            "scheduler",
            "--una-corrida",
            "--ahora",
            FUERA,
            *args_offline(tabla, directorio),
        ]
    )
    salida = json.loads(capsys.readouterr().out)
    assert codigo == 0
    assert salida["resultado"] == "omitida_ventana"


REPO_SCHEDULER = Path(__file__).resolve().parents[3]


class _ResultadoSubproceso:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode


def _pasos_web(tmp_path: Path, env: dict[str, str]):
    config = SimpleNamespace(repo=REPO_SCHEDULER, registro_confirmaciones=None)
    return _pasos_diarios(config, tmp_path / "salida", env)


def _fake_run(llamadas: list[str], codigos: dict[str, int]):
    def correr(comando, **_kwargs):
        script = Path(comando[1]).name
        llamadas.append(script)
        return _ResultadoSubproceso(codigos.get(script, 0))

    return correr


def test_purga_web_configurada_con_solo_el_dsn_de_la_app(
    tmp_path: Path, monkeypatch
) -> None:
    """Con un DSN alcanza para invocar; el script falla cerrado y frena el respaldo."""
    llamadas: list[str] = []
    monkeypatch.setattr(
        cli_scheduler.subprocess,
        "run",
        _fake_run(
            llamadas,
            {"purgar_canal_web.py": 2, "respaldar_estado.py": 0},
        ),
    )
    pasos, declarados = _pasos_web(
        tmp_path,
        {
            "AGENTE1_POSTGRES_DSN": "postgresql://app",
            "AGENTE1_RESPALDO_CARPETA_FAKE": str(tmp_path / "carpeta"),
        },
    )
    assert [paso.nombre for paso in pasos] == ["purga_canal_web", "respaldo"]
    assert declarados == ()
    with pytest.raises(RuntimeError, match="purga_canal_web_error"):
        pasos[0].correr()
    with pytest.raises(RuntimeError, match="respaldo_tras_purga_fallida"):
        pasos[1].correr()
    assert llamadas == ["purgar_canal_web.py"]


def test_purga_web_configurada_con_solo_el_dsn_de_mantenimiento(
    tmp_path: Path, monkeypatch
) -> None:
    """El DSN de mantenimiento solo también alcanza; el script falla cerrado."""
    llamadas: list[str] = []
    monkeypatch.setattr(
        cli_scheduler.subprocess,
        "run",
        _fake_run(
            llamadas,
            {"purgar_canal_web.py": 2, "respaldar_estado.py": 0},
        ),
    )
    pasos, declarados = _pasos_web(
        tmp_path,
        {
            "AGENTE1_POSTGRES_DSN_MANTENIMIENTO": "postgresql://mant",
            "AGENTE1_RESPALDO_CARPETA_FAKE": str(tmp_path / "carpeta"),
        },
    )
    assert [paso.nombre for paso in pasos] == ["purga_canal_web", "respaldo"]
    assert declarados == ()
    with pytest.raises(RuntimeError, match="purga_canal_web_error"):
        pasos[0].correr()
    with pytest.raises(RuntimeError, match="respaldo_tras_purga_fallida"):
        pasos[1].correr()
    assert llamadas == ["purgar_canal_web.py"]


def test_sin_ningun_dsn_la_purga_web_queda_pendiente(
    tmp_path: Path, monkeypatch
) -> None:
    """Sin DSN no se invoca la purga y el respaldo no queda bloqueado."""
    llamadas: list[str] = []
    monkeypatch.setattr(
        cli_scheduler.subprocess,
        "run",
        _fake_run(llamadas, {"respaldar_estado.py": 0}),
    )
    pasos, declarados = _pasos_web(
        tmp_path,
        {"AGENTE1_RESPALDO_CARPETA_FAKE": str(tmp_path / "carpeta")},
    )
    assert [paso.nombre for paso in pasos] == ["respaldo"]
    assert declarados == ("purga_canal_web",)
    pasos[0].correr()
    assert llamadas == ["respaldar_estado.py"]


def test_con_los_dos_dsn_purga_y_respaldo_corren_en_orden(
    tmp_path: Path, monkeypatch
) -> None:
    """Con ambos DSN, la purga y el respaldo se ejecutan en ese orden."""
    llamadas: list[str] = []
    monkeypatch.setattr(
        cli_scheduler.subprocess,
        "run",
        _fake_run(
            llamadas,
            {"purgar_canal_web.py": 0, "respaldar_estado.py": 0},
        ),
    )
    pasos, declarados = _pasos_web(
        tmp_path,
        {
            "AGENTE1_POSTGRES_DSN": "postgresql://app",
            "AGENTE1_POSTGRES_DSN_MANTENIMIENTO": "postgresql://mant",
            "AGENTE1_RESPALDO_CARPETA_FAKE": str(tmp_path / "carpeta"),
        },
    )
    assert [paso.nombre for paso in pasos] == ["purga_canal_web", "respaldo"]
    assert declarados == ()
    for paso in pasos:
        paso.correr()
    assert llamadas == ["purgar_canal_web.py", "respaldar_estado.py"]
