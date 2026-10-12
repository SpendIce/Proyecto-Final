"""Scheduler local de corridas programadas (#84).

Ejercita la agenda sin el timer ni el bucle reales: `disparar` responde a
un tick con reloj inyectado y `bucle` avanza un reloj falso con el
`dormir` que recibe, así todo el camino programado queda probado sin
esperar ni tocar systemd.
"""

import fcntl
import json
import os
from datetime import datetime, timedelta
from datetime import time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from agente1.scheduler import (
    ConfiguracionScheduler,
    ConfiguracionSchedulerError,
    PasoDiario,
    RegistroCorridasArchivo,
    SchedulerError,
    bucle,
    cargar_configuracion_scheduler,
    disparar,
    en_ventana,
    lock_corrida,
    proximo_disparo,
    tick_previsto,
)

ZONA = ZoneInfo("America/Argentina/Buenos_Aires")


def config(**cambios) -> ConfiguracionScheduler:
    base = {
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


def en_ventana_cfg(dia: int, hora: int, minuto: int = 0) -> datetime:
    # 2026-10-05 es lunes; sumar `dia - 1` días ubica cualquier día ISO.
    fecha = datetime(2026, 10, 5, hora, minuto, tzinfo=ZONA) + timedelta(days=dia - 1)
    return fecha


def corrida_ok() -> dict[str, object]:
    return {
        "estado": "OK",
        "filas_leidas": 3,
        "filas_nuevas": 1,
        "filas_escritas": 1,
        "filas_omitidas": 2,
        "filas_bloqueadas": 0,
        "filas_fallidas": 0,
        "filas": [{"fila": 2, "correlation_id": "x"}],
    }


class Reloj:
    """Reloj falso que el `dormir` del bucle hace avanzar."""

    def __init__(self, inicio: datetime) -> None:
        self.instante = inicio
        self.esperas: list[float] = []

    def __call__(self) -> datetime:
        return self.instante

    def dormir(self, segundos: float) -> None:
        self.esperas.append(segundos)
        self.instante += timedelta(seconds=segundos)


def test_configuracion_por_defecto() -> None:
    cfg = cargar_configuracion_scheduler({})
    assert cfg.intervalo_s == 300
    assert cfg.dias == frozenset({1, 2, 3, 4, 5})
    assert cfg.desde == dtime(8, 0) and cfg.hasta == dtime(16, 0)
    assert cfg.zona.key == "America/Argentina/Buenos_Aires"
    assert cfg.registro_confirmaciones is None


def test_configuracion_acepta_variables(tmp_path: Path) -> None:
    cfg = cargar_configuracion_scheduler(
        {
            "AGENTE1_SCHEDULER_INTERVALO_S": "120",
            "AGENTE1_SCHEDULER_VENTANA_DIAS": "2,4",
            "AGENTE1_SCHEDULER_VENTANA_DESDE": "09:30",
            "AGENTE1_SCHEDULER_VENTANA_HASTA": "17:45",
            "AGENTE1_SCHEDULER_TZ": "UTC",
            "AGENTE1_SCHEDULER_REPO": str(tmp_path),
            "AGENTE1_SCHEDULER_REGISTRO_CONFIRMACIONES": str(tmp_path / "reg"),
        }
    )
    assert cfg.intervalo_s == 120
    assert cfg.dias == frozenset({2, 4})
    assert cfg.desde == dtime(9, 30) and cfg.hasta == dtime(17, 45)
    assert cfg.zona == ZoneInfo("UTC")
    assert cfg.repo == tmp_path
    assert cfg.registro_confirmaciones == tmp_path / "reg"


@pytest.mark.parametrize(
    "env",
    [
        {"AGENTE1_SCHEDULER_SOPORTE": "x"},
        {"AGENTE1_SCHEDULER_INTERVALO_S": "0"},
        {"AGENTE1_SCHEDULER_INTERVALO_S": "abc"},
        {"AGENTE1_SCHEDULER_VENTANA_DIAS": "0"},
        {"AGENTE1_SCHEDULER_VENTANA_DIAS": "8"},
        {"AGENTE1_SCHEDULER_VENTANA_DIAS": ""},
        {"AGENTE1_SCHEDULER_VENTANA_DIAS": "lunes"},
        {"AGENTE1_SCHEDULER_VENTANA_DESDE": "8:00"},
        {"AGENTE1_SCHEDULER_VENTANA_DESDE": "24:00"},
        {"AGENTE1_SCHEDULER_TZ": "Marte/Olympus"},
        {"AGENTE1_SCHEDULER_REPO": "  "},
        {"AGENTE1_SCHEDULER_REGISTRO_CONFIRMACIONES": ""},
    ],
    ids=[
        "clave_desconocida",
        "intervalo_cero",
        "intervalo_texto",
        "dia_cero",
        "dia_ocho",
        "dias_vacios",
        "dias_texto",
        "hora_sin_cero",
        "hora_24",
        "tz_inexistente",
        "repo_vacio",
        "registro_vacio",
    ],
)
def test_configuracion_rechaza_valores_invalidos(env: dict) -> None:
    with pytest.raises(ConfiguracionSchedulerError) as excinfo:
        cargar_configuracion_scheduler(env)
    assert excinfo.value.code.startswith("scheduler_config_")


def test_configuracion_desde_mayor_que_hasta_es_invalida() -> None:
    with pytest.raises(ConfiguracionSchedulerError) as excinfo:
        cargar_configuracion_scheduler(
            {
                "AGENTE1_SCHEDULER_VENTANA_DESDE": "16:00",
                "AGENTE1_SCHEDULER_VENTANA_HASTA": "08:00",
            }
        )
    assert excinfo.value.code == "scheduler_config_invalid"


@pytest.mark.parametrize(
    "instante, esperado",
    [
        (en_ventana_cfg(1, 8), True),  # lunes 08:00, borde inclusivo
        (en_ventana_cfg(1, 12, 30), True),
        (en_ventana_cfg(1, 15, 59), True),
        (en_ventana_cfg(1, 16), False),  # cierre exclusivo
        (en_ventana_cfg(1, 7, 59), False),
        (en_ventana_cfg(6, 10), False),  # sábado
        (en_ventana_cfg(7, 10), False),  # domingo
    ],
    ids=[
        "apertura",
        "mediodia",
        "ultimo_minuto",
        "cierre",
        "antes",
        "sabado",
        "domingo",
    ],
)
def test_en_ventana(instante: datetime, esperado: bool) -> None:
    assert en_ventana(instante, config()) is esperado


def test_tick_previsto_redondea_al_ultimo_tick() -> None:
    cfg = config(intervalo_s=300)
    # 10:07 cae entre el tick de 10:05 y el de 10:10: responde al de 10:05.
    assert tick_previsto(en_ventana_cfg(1, 10, 7), cfg) == en_ventana_cfg(1, 10, 5)
    # Un disparo exactamente en el tick responde a ese tick.
    assert tick_previsto(en_ventana_cfg(1, 10, 10), cfg) == en_ventana_cfg(1, 10, 10)


def test_tick_previsto_fuera_de_ventana_es_none() -> None:
    cfg = config()
    assert tick_previsto(en_ventana_cfg(6, 10), cfg) is None
    assert tick_previsto(en_ventana_cfg(1, 18), cfg) is None


def test_proximo_disparo_salta_dias_y_fin_de_semana() -> None:
    cfg = config(intervalo_s=300)
    # Viernes después del cierre: el próximo tick es lunes 08:00.
    proximo = proximo_disparo(en_ventana_cfg(5, 18), cfg)
    assert proximo == en_ventana_cfg(8, 8)
    # Dentro de la ventana es el próximo múltiplo del intervalo.
    proximo = proximo_disparo(en_ventana_cfg(2, 10, 7), cfg)
    assert proximo == en_ventana_cfg(2, 10, 10)
    # Exactamente sobre un tick, ese mismo tick.
    proximo = proximo_disparo(en_ventana_cfg(2, 10, 10), cfg)
    assert proximo == en_ventana_cfg(2, 10, 10)


def test_lock_corrida_excluye_al_segundo_tomador(tmp_path: Path) -> None:
    with lock_corrida(tmp_path) as primero:
        assert primero is True
        with lock_corrida(tmp_path) as segundo:
            assert segundo is False
    # Liberado el primero, un tercero puede tomarlo.
    with lock_corrida(tmp_path) as tercero:
        assert tercero is True


def test_lock_corrida_excluye_entre_procesos(tmp_path: Path) -> None:
    # El lock es de archivo: otro descriptor sobre la misma ruta compite.
    ruta = tmp_path / "scheduler-corrida.lock"
    with lock_corrida(tmp_path) as adquirido:
        assert adquirido is True
        descriptor = os.open(ruta, os.O_RDWR)
        try:
            with pytest.raises(OSError):
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(descriptor)


def test_disparar_completada_asienta_la_linea(tmp_path: Path) -> None:
    entrada = disparar(
        ahora=en_ventana_cfg(1, 10, 7),
        corrida=corrida_ok,
        config=config(),
        directorio=tmp_path,
    )
    assert entrada["record"] == "scheduler_corrida_v1"
    assert entrada["resultado"] == "completada"
    assert entrada["en_ventana"] is True
    assert entrada["fecha"] == "2026-10-05"
    assert entrada["inicio_previsto"].startswith("2026-10-05T10:05:00")
    assert entrada["inicio_real"] <= entrada["fin"]
    assert entrada["corrida"] == {
        "estado": "OK",
        "filas_leidas": 3,
        "filas_nuevas": 1,
        "filas_escritas": 1,
        "filas_omitidas": 2,
        "filas_bloqueadas": 0,
        "filas_fallidas": 0,
    }
    # El detalle por fila del informe nunca llega al log del scheduler.
    assert "filas" not in entrada["corrida"]
    assert entrada["correlation_id"]

    (linea,) = RegistroCorridasArchivo(tmp_path).entradas()
    assert linea == entrada


def test_disparar_fuera_de_ventana_no_corre(tmp_path: Path) -> None:
    llamadas = []

    def corrida() -> dict:
        llamadas.append(1)
        return {}

    entrada = disparar(
        ahora=en_ventana_cfg(6, 10),
        corrida=corrida,
        config=config(),
        directorio=tmp_path,
    )
    assert llamadas == []
    assert entrada["resultado"] == "omitida_ventana"
    assert entrada["en_ventana"] is False
    assert entrada["inicio_previsto"] is None


def test_disparar_duplicado_no_repite_el_tick(tmp_path: Path) -> None:
    llamadas = []

    def corrida() -> dict:
        llamadas.append(1)
        return {"estado": "OK"}

    ahora = en_ventana_cfg(1, 10, 5)
    disparar(ahora=ahora, corrida=corrida, config=config(), directorio=tmp_path)
    entrada = disparar(
        ahora=ahora, corrida=corrida, config=config(), directorio=tmp_path
    )
    assert entrada["resultado"] == "omitida_duplicada"
    assert len(llamadas) == 1


def test_disparar_falla_se_reintenta_en_otro_tick(tmp_path: Path) -> None:
    def corrida_rota() -> dict:
        raise RuntimeError("sin red")

    ahora = en_ventana_cfg(1, 10, 5)
    entrada = disparar(
        ahora=ahora, corrida=corrida_rota, config=config(), directorio=tmp_path
    )
    assert entrada["resultado"] == "falla"
    assert entrada["detalle"] == "scheduler_corrida_error"

    # El tick fallido no deduplica: el disparo del tick siguiente corre.
    entrada = disparar(
        ahora=ahora + timedelta(seconds=300),
        corrida=corrida_ok,
        config=config(),
        directorio=tmp_path,
    )
    assert entrada["resultado"] == "completada"


def test_disparar_falla_oserror_tiene_codigo_de_entrada(tmp_path: Path) -> None:
    def corrida() -> dict:
        raise FileNotFoundError("tabla.csv")

    entrada = disparar(
        ahora=en_ventana_cfg(1, 10, 5),
        corrida=corrida,
        config=config(),
        directorio=tmp_path,
    )
    assert entrada["detalle"] == "entrada_inaccesible"


def test_disparar_informe_sin_forma_es_falla(tmp_path: Path) -> None:
    entrada = disparar(
        ahora=en_ventana_cfg(1, 10, 5),
        corrida=lambda: object(),  # type: ignore[return-value]
        config=config(),
        directorio=tmp_path,
    )
    assert entrada["resultado"] == "falla"
    assert entrada["detalle"] == "scheduler_corrida_invalid"


def test_disparar_con_lock_tomado_es_omitida(tmp_path: Path) -> None:
    llamadas = []
    with lock_corrida(tmp_path):
        entrada = disparar(
            ahora=en_ventana_cfg(1, 10, 5),
            corrida=lambda: llamadas.append(1) or {},
            config=config(),
            directorio=tmp_path,
        )
    assert llamadas == []
    assert entrada["resultado"] == "omitida_lock"


def test_log_ilegible_invalida_la_lectura(tmp_path: Path) -> None:
    registro = RegistroCorridasArchivo(tmp_path)
    registro.path.parent.mkdir(parents=True, exist_ok=True)
    registro.path.write_text("{ no json }\n", encoding="utf-8")
    with pytest.raises(SchedulerError) as excinfo:
        registro.entradas()
    assert excinfo.value.code == "scheduler_log_invalid"

    # Una entrada con forma inválida también invalida todo el registro.
    registro.path.write_text(
        json.dumps({"record": "scheduler_corrida_v1", "resultado": "inventado"}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(SchedulerError):
        registro.entradas()


def test_mantenimiento_corre_una_vez_por_dia(tmp_path: Path) -> None:
    llamadas = []

    def paso() -> None:
        llamadas.append(1)

    pasos = [PasoDiario("purga", paso)]
    ahora = en_ventana_cfg(1, 8)
    primera = disparar(
        ahora=ahora,
        corrida=corrida_ok,
        config=config(),
        directorio=tmp_path,
        pasos_diarios=pasos,
        pasos_declarados=("respaldo",),
    )
    assert primera["mantenimiento"] == {
        "purga": "completada",
        "respaldo": "pendiente",
    }
    # El segundo disparo del día no repite el slot.
    segunda = disparar(
        ahora=ahora + timedelta(seconds=300),
        corrida=corrida_ok,
        config=config(),
        directorio=tmp_path,
        pasos_diarios=pasos,
        pasos_declarados=("respaldo",),
    )
    assert "mantenimiento" not in segunda
    assert len(llamadas) == 1
    # Al día siguiente el slot vuelve a correr.
    manana = ahora + timedelta(days=1)
    tercera = disparar(
        ahora=manana,
        corrida=corrida_ok,
        config=config(),
        directorio=tmp_path,
        pasos_diarios=pasos,
    )
    assert tercera["mantenimiento"] == {"purga": "completada"}
    assert len(llamadas) == 2


def test_mantenimiento_fallido_se_reintenta_en_el_tick_siguiente(
    tmp_path: Path,
) -> None:
    estado = {"falla": True}

    def paso() -> None:
        if estado["falla"]:
            raise RuntimeError("purga sin disco")

    pasos = [PasoDiario("purga", paso)]
    ahora = en_ventana_cfg(1, 8)
    primera = disparar(
        ahora=ahora,
        corrida=corrida_ok,
        config=config(),
        directorio=tmp_path,
        pasos_diarios=pasos,
    )
    assert primera["mantenimiento"] == {"purga": "falla"}

    estado["falla"] = False
    segunda = disparar(
        ahora=ahora + timedelta(seconds=300),
        corrida=corrida_ok,
        config=config(),
        directorio=tmp_path,
        pasos_diarios=pasos,
    )
    assert segunda["mantenimiento"] == {"purga": "completada"}


def test_bucle_espera_al_tick_y_dispara(tmp_path: Path) -> None:
    reloj = Reloj(en_ventana_cfg(1, 10, 7))
    corridas = []

    def corrida() -> dict:
        corridas.append(reloj.instante)
        return {"estado": "OK"}

    resultado = bucle(
        corrida=corrida,
        config=config(intervalo_s=300),
        directorio=tmp_path,
        dormir=reloj.dormir,
        clock=reloj,
        max_disparos=2,
    )
    assert resultado == 0
    # Dormir de 10:07 a 10:10 y de 10:10 a 10:15.
    assert reloj.esperas == [180.0, 300.0]
    assert [c.time() for c in corridas] == [dtime(10, 10), dtime(10, 15)]

    entradas = RegistroCorridasArchivo(tmp_path).entradas()
    assert [e["resultado"] for e in entradas] == ["completada", "completada"]
    assert entradas[0]["inicio_previsto"].startswith("2026-10-05T10:10:00")


def test_bucle_fuera_de_ventana_duerme_hasta_el_proximo_tick(
    tmp_path: Path,
) -> None:
    # Viernes 18:00: duerme todo el fin de semana hasta el lunes 08:00.
    reloj = Reloj(en_ventana_cfg(5, 18))
    bucle(
        corrida=lambda: {"estado": "OK"},
        config=config(),
        directorio=tmp_path,
        dormir=reloj.dormir,
        clock=reloj,
        max_disparos=1,
    )
    (espera,) = reloj.esperas
    assert espera == (en_ventana_cfg(8, 8) - en_ventana_cfg(5, 18)).total_seconds()


def test_entrada_del_log_sobrevive_relectura(tmp_path: Path) -> None:
    registro = RegistroCorridasArchivo(tmp_path)
    ahora = en_ventana_cfg(1, 9)
    disparar(ahora=ahora, corrida=corrida_ok, config=config(), directorio=tmp_path)
    disparar(
        ahora=en_ventana_cfg(1, 20),
        corrida=corrida_ok,
        config=config(),
        directorio=tmp_path,
    )
    entradas = registro.entradas()
    assert len(entradas) == 2
    assert {e["resultado"] for e in entradas} == {
        "completada",
        "omitida_ventana",
    }
    # Las líneas son JSON válido y append-only bajo logs/.
    texto = (tmp_path / "logs" / "scheduler-corridas.jsonl").read_text(encoding="utf-8")
    assert len([linea for linea in texto.splitlines() if linea]) == 2
