"""Medición del nivel verificado de los SLO (#88).

Cubre el criterio de cada indicador sobre registros sintéticos: agenda
reconstruida vs. corridas disparadas, el join del CSV de respuestas del
Form, los p95, los incidentes que quedan fuera de la muestra, las
declaraciones (`muestra insuficiente`, `sin_fuente`, `pendiente #50/#51`)
y la integridad del gate sobre los artefactos locales.
"""

import hashlib
from datetime import date, datetime
from datetime import time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from agente1.medicion_slo import (
    FuentesAuditoria,
    LecturaLog,
    _id_pedido_canal,
    _leer_jsonl,
    indicador_aprobacion_envio,
    indicador_disponibilidad,
    indicador_integridad_gate,
    indicador_latencia_piezas,
    indicador_tiempo_atencion,
    medir_nivel_slo,
    render_markdown,
    segundos_en_ventana,
    ticks_agenda,
)

ZONA = ZoneInfo("America/Argentina/Buenos_Aires")
LUNES = date(2026, 10, 12)  # lunes
MARTES = date(2026, 10, 13)
DOMINGO = date(2026, 10, 18)


def config(**cambios):
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
    from agente1.scheduler import ConfiguracionScheduler

    return ConfiguracionScheduler(**base)


def tick(dia: date, hora: int, minuto: int = 0) -> str:
    return datetime(
        dia.year, dia.month, dia.day, hora, minuto, tzinfo=ZONA
    ).isoformat()


def corrida(previsto: str, *, resultado="completada", inicio=None, fin=None,
            en_ventana=True):
    entrada = {
        "record": "scheduler_corrida_v1",
        "correlation_id": "c1",
        "fecha": (previsto or inicio or "")[:10],
        "zona": ZONA.key,
        "en_ventana": en_ventana,
        "inicio_previsto": previsto,
    }
    if inicio is not None:
        entrada["inicio_real"] = inicio
    if fin is not None:
        entrada["fin"] = fin
    if resultado is not None:
        entrada["resultado"] = resultado
    return entrada


def instante_en(dia: date, hora: int, minuto: int = 0, segundo: int = 0) -> str:
    return datetime(
        dia.year, dia.month, dia.day, hora, minuto, segundo, tzinfo=ZONA
    ).isoformat()


# ---------------------------------------------------------------------------
# Agenda y ventana
# ---------------------------------------------------------------------------


def test_ticks_agenda_solo_dias_habiles():
    ticks = ticks_agenda(LUNES, DOMINGO, config())
    assert all(t.date().isoweekday() in {1, 2, 3, 4, 5} for t in ticks)
    # 8:00 a 16:00 cada 300 s => 96 ticks por día, 5 días hábiles.
    assert len(ticks) == 96 * 5
    assert ticks[0] == datetime(2026, 10, 12, 8, 0, tzinfo=ZONA)
    # el último tick es 15:55, no 16:00 (ventana semiabierta)
    ultimo_dia = [t for t in ticks if t.date() == date(2026, 10, 16)]
    assert ultimo_dia[-1].time() == dtime(15, 55)


def test_ticks_agenda_respeta_config_de_ventana():
    ticks = ticks_agenda(
        LUNES,
        LUNES,
        config(intervalo_s=3600, dias=frozenset({1}), desde=dtime(9), hasta=dtime(11)),
    )
    assert [t.time() for t in ticks] == [dtime(9, 0), dtime(10, 0)]


def test_segundos_en_ventana_descuenta_fuera_de_horario():
    # aprobado 15:30 del viernes, enviado 8:30 del lunes: dentro de la
    # ventana corren 30 min del viernes y 30 del lunes (3600 s); el fin
    # de semana no cuenta.
    aprobacion = datetime(2026, 10, 16, 15, 30, tzinfo=ZONA)
    envio = datetime(2026, 10, 19, 8, 30, tzinfo=ZONA)
    assert segundos_en_ventana(aprobacion, envio, config()) == 3600.0
    # todo fuera de la ventana
    assert (
        segundos_en_ventana(
            datetime(2026, 10, 17, 10, 0, tzinfo=ZONA),
            datetime(2026, 10, 17, 12, 0, tzinfo=ZONA),
            config(),
        )
        == 0.0
    )


# ---------------------------------------------------------------------------
# Disponibilidad
# ---------------------------------------------------------------------------


def _corridas_completadas(dia: date, horas=(8,)):
    entradas = []
    for hora in horas:
        previsto = tick(dia, hora)
        inicio = instante_en(dia, hora, 0, 3)
        fin = instante_en(dia, hora, 0, 40)
        entradas.append(corrida(previsto, inicio=inicio, fin=fin))
    return entradas


def test_disponibilidad_completa():
    indicador = indicador_disponibilidad(
        entradas=tuple(_corridas_completadas(LUNES, (8,))),
        estado_fuente="ok",
        desde=LUNES,
        hasta=LUNES,
        config=config(
            dias=frozenset({1}), desde=dtime(8, 0), hasta=dtime(8, 5)
        ),
        muestra_minima=1,
    )
    assert indicador["nivel"] == 1.0
    assert indicador["cumple"] is True
    assert indicador["detalle"]["corridas_programadas"] == 1
    assert indicador["detalle"]["completadas_a_tiempo"] == 1


def test_disponibilidad_tick_sin_disparo_baja_el_nivel():
    # agenda de 3 ticks, sólo 2 disparados y completados.
    indicador = indicador_disponibilidad(
        entradas=tuple(
            _corridas_completadas(LUNES, (8,))
            + [
                corrida(
                    tick(LUNES, 8, 5),
                    inicio=instante_en(LUNES, 8, 5, 1),
                    fin=instante_en(LUNES, 8, 5, 40),
                )
            ]
        ),
        estado_fuente="ok",
        desde=LUNES,
        hasta=LUNES,
        config=config(dias=frozenset({1}), desde=dtime(8), hasta=dtime(8, 15)),
        muestra_minima=1,
    )
    assert indicador["detalle"]["corridas_programadas"] == 3
    assert indicador["detalle"]["sin_disparo"] == 1
    assert indicador["nivel"] == pytest.approx(2 / 3)
    assert indicador["cumple"] is False


def test_disponibilidad_falla_y_tardia_no_cuentan():
    previsto_falla = tick(LUNES, 8, 5)
    entradas = tuple(
        _corridas_completadas(LUNES, (8,))
        + [
            corrida(
                previsto_falla,
                resultado="falla",
                inicio=instante_en(LUNES, 8, 5, 1),
                fin=instante_en(LUNES, 8, 6),
            ),
            # completada pero cerró después del slot (5 min de gracia)
            corrida(
                tick(LUNES, 8, 10),
                inicio=instante_en(LUNES, 8, 10, 1),
                fin=instante_en(LUNES, 8, 16),
            ),
        ]
    )
    indicador = indicador_disponibilidad(
        entradas=entradas,
        estado_fuente="ok",
        desde=LUNES,
        hasta=LUNES,
        config=config(dias=frozenset({1}), desde=dtime(8), hasta=dtime(8, 15)),
        muestra_minima=1,
    )
    assert indicador["detalle"]["falladas"] == 1
    assert indicador["detalle"]["completadas_tardias"] == 1
    assert indicador["nivel"] == pytest.approx(1 / 3)


def test_disponibilidad_omite_disparos_fuera_de_ventana_y_agenda():
    entradas = tuple(
        _corridas_completadas(LUNES, (8,))
        + [
            corrida(
                None, resultado="omitida_ventana", en_ventana=False,
                inicio=instante_en(LUNES, 20, 0),
                fin=instante_en(LUNES, 20, 0, 1),
            ),
            # un previsto que no pertenece a la agenda del rango
            corrida(
                tick(DOMINGO, 8),
                inicio=instante_en(DOMINGO, 8, 0, 1),
                fin=instante_en(DOMINGO, 8, 0, 30),
            ),
        ]
    )
    indicador = indicador_disponibilidad(
        entradas=entradas,
        estado_fuente="ok",
        desde=LUNES,
        hasta=LUNES,
        config=config(dias=frozenset({1}), desde=dtime(8), hasta=dtime(8, 5)),
        muestra_minima=1,
    )
    assert indicador["nivel"] == 1.0
    assert indicador["detalle"]["entradas_fuera_de_ventana"] == 1
    assert indicador["detalle"]["entradas_fuera_de_agenda"] == 1


def test_disponibilidad_fuente_ausente_e_invalida():
    ausente = indicador_disponibilidad(
        entradas=(),
        estado_fuente="ausente",
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=20,
    )
    assert ausente["nivel_verificado"] == "sin_fuente"
    assert ausente["nivel"] is None
    assert ausente["huecos"]

    invalida = indicador_disponibilidad(
        entradas=(),
        estado_fuente="invalida",
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=20,
    )
    assert invalida["nivel_verificado"] == "sin_fuente"


def test_disponibilidad_muestra_insuficiente_declara():
    indicador = indicador_disponibilidad(
        entradas=tuple(_corridas_completadas(LUNES, (8,))),
        estado_fuente="ok",
        desde=LUNES,
        hasta=LUNES,
        config=config(dias=frozenset({1}), desde=dtime(8), hasta=dtime(8, 5)),
        muestra_minima=20,
    )
    assert indicador["nivel_verificado"] == "muestra insuficiente (n=1)"
    assert indicador["cumple"] is None


# ---------------------------------------------------------------------------
# Tiempo de atención
# ---------------------------------------------------------------------------


def _csv_respuestas(tmp_path: Path, filas) -> Path:
    path = tmp_path / "respuestas.csv"
    lineas = ["Marca temporal,Dirección de correo electrónico,pedido"]
    for marca, correo, texto in filas:
        lineas.append(f"{marca},{correo},{texto}")
    path.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return path


def _atendido(marca, correo, texto, *, aviso="enviada", cuando=None):
    return {
        "version": "canal_form_atendidos_v1",
        "id_pedido": _id_pedido_canal(marca, correo.lower(), texto),
        "solicitante_hash": "h" * 64,
        "rol": "operador",
        "identidad_canal": "correo_verificado_form",
        "rol_origen": "padron",
        "estado": "PENDIENTE_VALIDACION",
        "intencion": "gacetilla",
        "aviso": aviso,
        "aviso_codigo": None,
        "correlation_id": "c1",
        "timestamp": cuando or instante_en(LUNES, 9, 0),
    }


def test_id_pedido_canal_coincide_con_el_adapter():
    from agente1.canal_form import _id_pedido

    assert _id_pedido_canal(
        "2026-10-12 08:30:00", "ope@fie.edu.ar", "generá la gacetilla"
    ) == _id_pedido("2026-10-12 08:30:00", "ope@fie.edu.ar", "generá la gacetilla")


def test_tiempo_atencion_mide_delta_desde_la_marca(tmp_path):
    marca = "2026-10-12 08:30:00"
    csv_path = _csv_respuestas(
        tmp_path, [(marca, "ope@fie.edu.ar", "generá la gacetilla")]
    )
    atendidos = (
        _atendido(
            marca,
            "ope@fie.edu.ar",
            "generá la gacetilla",
            cuando=instante_en(LUNES, 8, 35),
        ),
    )
    indicador = indicador_tiempo_atencion(
        atendidos=atendidos,
        estado_fuente="ok",
        respuestas_csv=csv_path,
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=1,
    )
    # 8:30 → 8:35 = 300 s, dentro del objetivo 300+300.
    assert indicador["nivel"] == pytest.approx(300.0)
    assert indicador["cumple"] is True
    assert indicador["detalle"]["aviso_enviada"] == 1


def test_tiempo_atencion_sin_csv_declara_sin_fuente(tmp_path):
    indicador = indicador_tiempo_atencion(
        atendidos=(_atendido("m", "ope@fie.edu.ar", "t"),),
        estado_fuente="ok",
        respuestas_csv=None,
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=1,
    )
    assert indicador["nivel_verificado"] == "sin_fuente"
    assert indicador["cumple"] is None
    assert any("marca temporal" in h for h in indicador["huecos"])


def test_tiempo_atencion_aviso_no_enviado_queda_fuera(tmp_path):
    marca = "2026-10-12 08:30:00"
    csv_path = _csv_respuestas(
        tmp_path, [(marca, "ope@fie.edu.ar", "pedido sin resolver")]
    )
    atendidos = (
        _atendido(
            marca, "ope@fie.edu.ar", "pedido sin resolver", aviso="fallida"
        ),
    )
    indicador = indicador_tiempo_atencion(
        atendidos=atendidos,
        estado_fuente="ok",
        respuestas_csv=csv_path,
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=1,
    )
    assert indicador["n"] == 0
    assert indicador["detalle"]["aviso_rechazada_o_fallida"] == 1


def test_tiempo_atencion_formato_us_de_marca(tmp_path):
    marca = "10/12/2026 8:30"
    csv_path = _csv_respuestas(
        tmp_path, [(marca, "ope@fie.edu.ar", "pedido")]
    )
    atendidos = (
        _atendido(marca, "ope@fie.edu.ar", "pedido",
                  cuando=instante_en(LUNES, 8, 45)),
    )
    indicador = indicador_tiempo_atencion(
        atendidos=atendidos,
        estado_fuente="ok",
        respuestas_csv=csv_path,
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=1,
    )
    assert indicador["nivel"] == pytest.approx(900.0)


# ---------------------------------------------------------------------------
# Latencia por pieza
# ---------------------------------------------------------------------------


def test_latencia_por_pieza_declara_pendiente_50_51():
    ejecuciones = LecturaLog(
        tuple(
            {
                "HU": "HU-010",
                "estado": "PENDIENTE_VALIDACION",
                "latencia_s": float(i),
                "modelo": "fake-determinista",
                "timestamp": instante_en(LUNES, 10, i % 60),
            }
            for i in range(25)
        )
    )
    indicador = indicador_latencia_piezas(
        logs={"ejecuciones.jsonl": ejecuciones},
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=20,
    )
    assert indicador["nivel_verificado"] == "pendiente #50/#51"
    assert indicador["cumple"] is None
    por_tipo = indicador["detalle"]["por_tipo"]
    assert por_tipo["gacetilla"]["n"] == 25
    assert por_tipo["gacetilla"]["p95_s"] == pytest.approx(22.8)
    assert por_tipo["gacetilla"]["modelos"] == ["fake-determinista"]


def test_latencia_linea_descriptiva_declara_hueco():
    lineas = LecturaLog(
        (
            {
                "HU": "HU-014",
                "estado": "PENDIENTE_VALIDACION",
                "resultado": "linea_generada",
                "timestamp": instante_en(LUNES, 10),
            },
        )
    )
    indicador = indicador_latencia_piezas(
        logs={"lineas-descriptivas.jsonl": lineas},
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=20,
    )
    assert any("latencia_s" in h for h in indicador["huecos"])
    assert indicador["nivel_verificado"] == "sin_fuente"


# ---------------------------------------------------------------------------
# Aprobación → envío
# ---------------------------------------------------------------------------


def _cadena_lote(tmp_path: Path, *, estado_final="ENVIADA_SIMULADA",
                 aprob=None, envio=None, con_decisiones=True):
    """Lote autorizado con un ítem: decisiones, lotes y registro."""

    lote_id = "lote-abc"
    plantilla_id = "tpl-abc"
    clave = "a" * 64
    aprob = aprob or instante_en(LUNES, 9, 0)
    envio = envio or instante_en(LUNES, 9, 3)

    procesadas = (
        (
            {
                "tipo": "plantilla",
                "objeto_id": plantilla_id,
                "decision": "apruebo_semantica",
                "resultado": "registrada",
                "timestamp": aprob,
            },
            {
                "tipo": "plantilla",
                "objeto_id": plantilla_id,
                "decision": "apruebo_utilitaria",
                "resultado": "registrada",
                "timestamp": aprob,
            },
            {
                "tipo": "lote",
                "objeto_id": lote_id,
                "decision": "apruebo_lote",
                "resultado": "registrada",
                "timestamp": aprob,
            },
        )
        if con_decisiones
        else ()
    )
    lotes = (
        {
            "evento": "autorizacion_lote",
            "estado": "AUTORIZADA",
            "lote_id": lote_id,
            "plantilla_id": plantilla_id,
            "timestamp": aprob,
        },
        {
            "evento": "encolado_lote",
            "estado": "ENVIO_ENCOLADO",
            "lote_id": lote_id,
            "idempotency_key": clave,
            "timestamp": aprob,
        },
    )
    registros = {
        clave: {
            "estado": estado_final,
            "creado_en": aprob,
            "actualizado_en": envio,
        }
    }
    return lotes, procesadas, registros


def test_aprobacion_envio_mide_delta(tmp_path):
    lotes, procesadas, registros = _cadena_lote(
        tmp_path,
        aprob=instante_en(LUNES, 9, 0),
        envio=instante_en(LUNES, 9, 4),
    )
    indicador = indicador_aprobacion_envio(
        lotes=lotes,
        estado_lotes="ok",
        procesadas=procesadas,
        estado_decisiones="ok",
        registros=registros,
        estado_registro="ok",
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=1,
    )
    assert indicador["nivel"] == pytest.approx(240.0)
    assert indicador["cumple"] is True  # 240 <= 2*300
    assert indicador["detalle"]["items_entregados"] == 1


def test_aprobacion_envio_indeterminado_es_incidente(tmp_path):
    lotes, procesadas, registros = _cadena_lote(
        tmp_path, estado_final="ENVIO_INDETERMINADO"
    )
    indicador = indicador_aprobacion_envio(
        lotes=lotes,
        estado_lotes="ok",
        procesadas=procesadas,
        estado_decisiones="ok",
        registros=registros,
        estado_registro="ok",
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=1,
    )
    assert indicador["n"] == 0
    assert indicador["detalle"]["incidentes_indeterminado"] == 1


def test_aprobacion_envio_sin_decision_declara_sin_ancla(tmp_path):
    lotes, _, registros = _cadena_lote(tmp_path, con_decisiones=False)
    indicador = indicador_aprobacion_envio(
        lotes=lotes,
        estado_lotes="ok",
        procesadas=(),
        estado_decisiones="ok",
        registros=registros,
        estado_registro="ok",
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=1,
    )
    assert indicador["n"] == 0
    assert indicador["detalle"]["items_sin_ancla"] == 1


def test_aprobacion_envio_descuenta_tiempo_fuera_de_ventana(tmp_path):
    # aprobado viernes 15:59, enviado lunes 8:01: sólo 60+60 s en ventana.
    lunes_siguiente = date(2026, 10, 19)
    lotes, procesadas, registros = _cadena_lote(
        tmp_path,
        aprob=instante_en(date(2026, 10, 16), 15, 59),
        envio=instante_en(lunes_siguiente, 8, 1),
    )
    # el encolado cayó el viernes: el rango tiene que incluirlo.
    lotes = (
        lotes[0],
        {**lotes[1], "timestamp": instante_en(date(2026, 10, 16), 15, 59)},
    )
    indicador = indicador_aprobacion_envio(
        lotes=lotes,
        estado_lotes="ok",
        procesadas=procesadas,
        estado_decisiones="ok",
        registros=registros,
        estado_registro="ok",
        desde=date(2026, 10, 16),
        hasta=date(2026, 10, 19),
        config=config(),
        muestra_minima=1,
    )
    assert indicador["nivel"] == pytest.approx(120.0)
    assert indicador["detalle"]["delta_total_s"]["n"] == 1
    assert indicador["detalle"]["delta_total_s"]["max_s"] > 120.0


# ---------------------------------------------------------------------------
# Integridad del gate
# ---------------------------------------------------------------------------


def test_integridad_gate_todo_conforme(tmp_path):
    cuerpo = "BORRADOR — NO PUBLICAR\n\npieza"
    output_hash = hashlib.sha256(cuerpo.encode("utf-8")).hexdigest()
    (tmp_path / "borradores").mkdir()
    (tmp_path / "borradores" / "pieza.md").write_text(cuerpo, encoding="utf-8")

    ejecuciones = LecturaLog(
        (
            {
                "estado": "PENDIENTE_VALIDACION",
                "resultado": "borrador_generado",
                "output_hash": output_hash,
                "correlation_id": "c1",
                "timestamp": instante_en(LUNES, 10),
            },
        )
    )
    clave = "b" * 64
    lotes = (
        {
            "evento": "autorizacion_lote",
            "estado": "AUTORIZADA",
            "lote_id": "lote-abc",
            "timestamp": instante_en(LUNES, 10),
        },
        {
            "evento": "encolado_lote",
            "lote_id": "lote-abc",
            "idempotency_key": clave,
            "timestamp": instante_en(LUNES, 10),
        },
    )
    registros = {clave: {"estado": "ENVIADA_SIMULADA"}}

    indicador = indicador_integridad_gate(
        logs={"ejecuciones.jsonl": ejecuciones},
        directorio_borradores=tmp_path / "borradores",
        lotes=lotes,
        recordatorios=(),
        confirmaciones=(),
        registros=registros,
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=1,
    )
    assert indicador["nivel"] == 1.0
    assert indicador["cumple"] is True
    assert indicador["detalle"]["violaciones_total"] == 0


def test_integridad_gate_presentada_no_conforme_es_violacion(tmp_path):
    ejecuciones = LecturaLog(
        (
            {
                "estado": "PENDIENTE_VALIDACION",
                "resultado": "borrador_generado",
                "output_hash": "x" * 64,
                "correlation_id": "c-bad",
                "validation_errors": ["cuerpo vacío"],
                "timestamp": instante_en(LUNES, 10),
            },
        )
    )
    indicador = indicador_integridad_gate(
        logs={"ejecuciones.jsonl": ejecuciones},
        directorio_borradores=None,
        lotes=(),
        recordatorios=(),
        confirmaciones=(),
        registros={},
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=1,
    )
    assert indicador["nivel"] == 0.0
    assert indicador["cumple"] is False
    assert indicador["detalle"]["violaciones_total"] == 1


def test_integridad_gate_archivo_huerfano_es_violacion(tmp_path):
    (tmp_path / "borradores").mkdir()
    (tmp_path / "borradores" / "intruso.md").write_text(
        "sin línea de auditoría", encoding="utf-8"
    )
    indicador = indicador_integridad_gate(
        logs={},
        directorio_borradores=tmp_path / "borradores",
        lotes=(),
        recordatorios=(),
        confirmaciones=(),
        registros={},
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=1,
    )
    assert indicador["nivel"] == 0.0
    assert indicador["detalle"]["violaciones_total"] == 1


def test_integridad_gate_envio_sin_traza_es_violacion():
    registros = {"c" * 64: {"estado": "ENVIADA_SIMULADA"}}
    indicador = indicador_integridad_gate(
        logs={},
        directorio_borradores=None,
        lotes=(),
        recordatorios=(),
        confirmaciones=(),
        registros=registros,
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=1,
    )
    assert indicador["nivel"] == 0.0
    assert indicador["detalle"]["violaciones_total"] == 1


def test_integridad_gate_emitida_simulada_es_hueco_no_violacion():
    registros = {"d" * 64: {"estado": "EMITIDA_SIMULADA"}}
    indicador = indicador_integridad_gate(
        logs={},
        directorio_borradores=None,
        lotes=(),
        recordatorios=(),
        confirmaciones=(),
        registros=registros,
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        muestra_minima=1,
    )
    assert indicador["detalle"]["violaciones_total"] == 0
    assert any("emisión" in h or "certificados" in h for h in indicador["huecos"])


# ---------------------------------------------------------------------------
# Reporte integral
# ---------------------------------------------------------------------------


def test_leer_jsonl_invalido_se_declara(tmp_path):
    path = tmp_path / "roto.jsonl"
    path.write_text("{no es json}\n", encoding="utf-8")
    assert _leer_jsonl(path).estado == "invalida"
    assert _leer_jsonl(tmp_path / "no-existe.jsonl").estado == "ausente"


def test_medir_nivel_slo_estructura_y_rango(tmp_path):
    (tmp_path / "logs").mkdir()
    fuentes = FuentesAuditoria(directorio=tmp_path)
    reporte = medir_nivel_slo(
        fuentes=fuentes,
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        corte=datetime(2026, 10, 12, 16, 0, tzinfo=ZONA),
        muestra_minima=5,
    )
    assert reporte["record"] == "nivel_verificado_slo_v1"
    assert set(reporte["indicadores"]) == {
        "disponibilidad",
        "tiempo_atencion",
        "latencia_por_pieza",
        "aprobacion_envio",
        "integridad_gate",
    }
    assert reporte["rango"] == {"desde": "2026-10-12", "hasta": "2026-10-12"}
    assert reporte["corte"] == "2026-10-12T16:00:00-03:00"
    assert reporte["configuracion"]["intervalo_s"] == 300
    # sin fuentes, todo queda declarado
    assert (
        reporte["indicadores"]["disponibilidad"]["nivel_verificado"]
        == "sin_fuente"
    )


def test_medir_nivel_slo_rechaza_rango_invertido(tmp_path):
    with pytest.raises(ValueError):
        medir_nivel_slo(
            fuentes=FuentesAuditoria(directorio=tmp_path),
            desde=MARTES,
            hasta=LUNES,
            config=config(),
            corte=datetime(2026, 10, 12, 16, 0, tzinfo=ZONA),
        )


def test_medir_nivel_slo_rechaza_corte_sin_zona(tmp_path):
    with pytest.raises(ValueError):
        medir_nivel_slo(
            fuentes=FuentesAuditoria(directorio=tmp_path),
            desde=LUNES,
            hasta=LUNES,
            config=config(),
            corte=datetime(2026, 10, 12, 16, 0),
        )


def test_render_markdown_declara_comando_y_celdas(tmp_path):
    (tmp_path / "logs").mkdir()
    reporte = medir_nivel_slo(
        fuentes=FuentesAuditoria(directorio=tmp_path),
        desde=LUNES,
        hasta=LUNES,
        config=config(),
        corte=datetime(2026, 10, 12, 16, 0, tzinfo=ZONA),
    )
    texto = render_markdown(reporte, comando="medir_nivel_slo.py --directorio x")
    assert "medir_nivel_slo.py --directorio x" in texto
    assert "pendiente #50/#51" in texto
    assert "Nivel verificado" in texto
    # la tabla no publica un número inventado para la disponibilidad
    assert "muestra insuficiente" in texto or "sin_fuente" in texto
