"""Una decisión demo nunca habilita una emisión institucional posterior."""

from __future__ import annotations

from datetime import timedelta

import pytest
from test_emision_certificados_durable import (
    AHORA,
    CORREO,
    MotorEspia,
    _aprobar,
    _crear_lote,
    _emisiones,
    _lotes,
)
from test_emision_certificados_durable import base_pg as base_pg

from agente1.canal_form import PadronRoles, hash_correo
from agente1.confirmaciones import ROL_APROBADOR_CONTENIDO
from agente1.decisiones_form import (
    TIPO_LINEA_DESCRIPTIVA,
    RegistroDecisiones,
    ResultadoDecision,
)
from agente1.linea_descriptiva import objeto_id_linea_descriptiva
from agente1.web.emision_certificados import (
    ActorCertificadosWeb,
    EmisionCertificadosWeb,
    ErrorEmisionWeb,
)


@pytest.mark.parametrize("origen", [None, "google"])
def test_worker_real_no_proyecta_una_decision_demo(base_pg, tmp_path, origen) -> None:
    lotes = _lotes(base_pg)
    lote = _crear_lote(lotes, origen=origen)
    decision = lotes.decidir(
        id_lote=lote.id_lote,
        hash_lote=lote.objeto_lote,
        accion="aprobar",
        validador_hash=hash_correo(CORREO),
        rol=ROL_APROBADOR_CONTENIDO,
        origen_identidad="demo",
        version_agente="0.0.0-test",
        ahora=AHORA,
    )
    assert decision.codigo == "aprobada"
    registro = RegistroDecisiones(tmp_path / "decisiones")
    # La línea ya tenía una aprobación genuina; sólo el lote se decidió en demo.
    registro.registrar(
        ResultadoDecision(
            id_respuesta="a" * 64,
            correo_hash=hash_correo(CORREO),
            rol=ROL_APROBADOR_CONTENIDO,
            rol_origen="padron",
            tipo=TIPO_LINEA_DESCRIPTIVA,
            objeto_id=objeto_id_linea_descriptiva(lote.id_actividad, lote.linea_descriptiva),
            decision="apruebo_contenido",
            resultado="registrada",
            rechazo_codigo=None,
            marca_temporal_form=AHORA.isoformat(),
            timestamp=AHORA.isoformat(),
        )
    )
    anteriores = registro.procesadas()
    emisiones = _emisiones(base_pg)
    emisiones.encolar(id_lote=lote.id_lote, modo="real", ahora=AHORA)
    motor = MotorEspia()
    destinos = []

    def destino():
        destinos.append(True)
        raise AssertionError("una decisión demo no debe construir un destino")

    servicio = EmisionCertificadosWeb(
        lotes=lotes,
        emisiones=emisiones,
        padron=PadronRoles({CORREO: ROL_APROBADOR_CONTENIDO}),
        registro_decisiones=registro,
        directorio_salida=tmp_path / "salida",
        fabrica_destino=destino,
        motor=motor,
        modo_demo=False,
    )

    assert servicio.correr_una_vez(worker_id="procedencia", ahora=AHORA) is not None

    actual = emisiones.obtener_por_lote(lote.id_lote)
    assert actual.estado == "FALLIDA"
    assert actual.error_codigo == "identidad_no_verificada"
    assert registro.procesadas() == anteriores
    assert motor.llamadas == []
    assert destinos == []


def test_post_real_rechaza_identidad_demo_aunque_el_modo_este_apagado(base_pg) -> None:
    lotes = _lotes(base_pg)
    lote = _crear_lote(lotes)
    assert _aprobar(lotes, lote).codigo == "aprobada"
    emisiones = _emisiones(base_pg)
    servicio = EmisionCertificadosWeb(
        lotes=lotes,
        emisiones=emisiones,
        padron=PadronRoles({CORREO: ROL_APROBADOR_CONTENIDO}),
        modo_demo=False,
    )
    actor = ActorCertificadosWeb(
        solicitante_hash=hash_correo(CORREO),
        rol=ROL_APROBADOR_CONTENIDO,
        origen_identidad="demo",
        modo_demo=False,
    )

    with pytest.raises(ErrorEmisionWeb) as error:
        servicio.solicitar(lote.id_lote, hash_lote=lote.objeto_lote, actor=actor)

    assert error.value.code == "identidad_no_verificada"
    assert emisiones.listar() == []


@pytest.mark.parametrize("origen", ["google", "demo", None])
def test_pedido_abandonado_sin_aprobar_purga_solo_el_origen_nuevo(base_pg, origen):
    lotes = _lotes(base_pg)
    lote = _crear_lote(lotes, origen=origen)
    mantenimiento = _lotes(base_pg, "agente1_mantenimiento")
    assert mantenimiento.purgar_cerrados(ahora=AHORA + timedelta(days=29)) == 0
    assert mantenimiento.purgar_cerrados(ahora=AHORA + timedelta(days=31)) == (0 if origen is None else 1)
    guardado = lotes.obtener(lote.id_lote)
    assert bool(guardado.personas) is (origen is None)
