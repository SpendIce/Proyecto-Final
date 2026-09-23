"""HU-012 ampliada (bible 22/09): catálogo cerrado de tipos de notificación.

La HU pasó de «confirmaciones de inscripción» a «notificaciones automáticas
de inscripción, participación, situación de pagos y aprobación». Estas
pruebas fijan que el catálogo es cerrado y coherente con la matriz de
orígenes, que `participacion` y `aprobacion` recorren el mismo pipeline con
la misma doble aprobación, que `situacion_pagos` queda declarada pero no
produce nada mientras el dato de deuda no tenga origen confirmado, y que
`inscripcion` no cambió de comportamiento.
"""

import json
from importlib.resources import files
from pathlib import Path

import pytest

from agente1.confirmaciones import (
    AprobacionHumana,
    ColaEnviosMemoria,
    DestinoConfirmacionesFake,
    RegistroConfirmacionesMemoria,
    REQUIRED_FIELDS,
    ROL_APROBACION_SEMANTICA,
    ROL_APROBACION_UTILITARIA,
    SolicitudConfirmacion,
    drenar_envios,
    procesar_confirmacion,
)
from agente1.origenes_inscripcion import ORIGENES_DE_INSCRIPCION
from agente1.tipos_notificacion import (
    CATALOGO,
    CONTRACT_VERSION,
    MOTIVOS_DE_BLOQUEO,
    PROCEDENCIAS,
    STATUS,
    TIPO_NOTIFICACION_PREDETERMINADO,
    TIPOS,
    TIPOS_NOTIFICACION,
    DecisionTipoNotificacion,
    TipoNotificacionDesconocidoError,
    campos_requeridos,
    datos_sin_origen_confirmado,
    descripcion_tipo,
    evaluar_tipo,
)


ROOT = Path(__file__).parents[1]


def solicitud(**cambios: str) -> SolicitudConfirmacion:
    datos = {
        "id_inscripcion": "INS-TIP-001",
        "nombre_destinatario": "Ana Pérez",
        "email_destinatario": "ana.perez@example.test",
        "actividad": "Taller de robótica educativa",
        "fecha": "28 de agosto de 2026, 18:00",
        "lugar": "Aula 4",
        "organiza": "Secretaría de Extensión Universitaria",
        "contacto": "extension@example.test",
    }
    datos.update(cambios)
    return SolicitudConfirmacion(**datos)


def aprobacion(*, aprobada: bool = True, rol: str) -> AprobacionHumana:
    return AprobacionHumana(
        aprobada=aprobada,
        validador="Validador SEU de prueba",
        rol=rol,
        fecha_iso="2026-08-17T18:00:00-03:00",
    )


def semantica(**kwargs) -> AprobacionHumana:
    return aprobacion(rol=ROL_APROBACION_SEMANTICA, **kwargs)


def utilitaria(**kwargs) -> AprobacionHumana:
    return aprobacion(rol=ROL_APROBACION_UTILITARIA, **kwargs)


def procesar(tmp_path: Path, registro, **extra):
    return procesar_confirmacion(
        solicitud=extra.pop("solicitud", solicitud()),
        directorio_salida=tmp_path / "salida",
        registro=registro,
        **extra,
    )


def aprobar_ambos(tmp_path: Path, registro, solicitud_: SolicitudConfirmacion) -> None:
    procesar(tmp_path, registro, solicitud=solicitud_, aprobacion=semantica())
    procesar(tmp_path, registro, solicitud=solicitud_, aprobacion=utilitaria())


# --- El catálogo como contrato -----------------------------------------------


def test_el_catalogo_es_cerrado_y_tiene_los_cuatro_tipos_de_la_bible() -> None:
    assert CONTRACT_VERSION == "tipos_notificacion_v1"
    assert STATUS == "CANDIDATO_PENDIENTE_CONFIRMACION_SEU"
    assert CATALOGO["x-hu"] == "HU-012"
    assert CATALOGO["x-habilita-envio"] is False
    assert TIPOS_NOTIFICACION == frozenset(
        {"inscripcion", "participacion", "situacion_pagos", "aprobacion"}
    )
    assert TIPO_NOTIFICACION_PREDETERMINADO == "inscripcion"


@pytest.mark.parametrize("tipo", sorted(TIPOS_NOTIFICACION))
def test_cada_tipo_declara_campos_origenes_plantilla_y_procedencia(
    tipo: str,
) -> None:
    item = descripcion_tipo(tipo)

    assert item["procedencia_tipo"] == "CONFIRMADO_SEU"
    assert item["campos_requeridos"]
    assert set(item["campos_requeridos"]) <= set(REQUIRED_FIELDS) | {
        "email_destinatario"
    }
    assert set(item["origenes_admisibles"]) <= set(ORIGENES_DE_INSCRIPCION)
    assert set(item["datos_especificos"].values()) <= PROCEDENCIAS
    assert set(item["motivos_de_bloqueo"]) <= MOTIVOS_DE_BLOQUEO
    assert item["plantilla"]["asunto_base"].strip()
    assert item["plantilla"]["frase_evento"].strip()


def test_los_tipos_habilitados_exigen_los_campos_confirmados() -> None:
    """Los tres tipos que entran al pipeline usan el mismo set de campos:
    el contacto del inscripto, confirmado por la SEU el 22/09."""
    for tipo in ("inscripcion", "participacion", "aprobacion"):
        assert set(campos_requeridos(tipo)) == set(REQUIRED_FIELDS) | {
            "email_destinatario"
        }


def test_situacion_pagos_declara_su_dato_de_deuda_como_desconocido() -> None:
    item = descripcion_tipo("situacion_pagos")

    assert item["datos_especificos"] == {"situacion_deuda_o_saldo": "DESCONOCIDO"}
    assert item["origen_datos_especificos"] == "DESCONOCIDO"
    assert datos_sin_origen_confirmado("situacion_pagos") == (
        "situacion_deuda_o_saldo",
    )
    assert "dato_especifico_sin_origen_confirmado" in item["motivos_de_bloqueo"]


def test_la_procedencia_desconocida_es_lo_que_bloquea_un_tipo() -> None:
    """Coherencia interna: un tipo tiene el motivo de bloqueo por dato
    específico si y sólo si declara algún dato como DESCONOCIDO."""
    for tipo in TIPOS_NOTIFICACION:
        item = descripcion_tipo(tipo)
        tiene_desconocido = bool(datos_sin_origen_confirmado(tipo))
        declara_bloqueo = (
            "dato_especifico_sin_origen_confirmado" in item["motivos_de_bloqueo"]
        )
        assert tiene_desconocido == declara_bloqueo


# --- La decisión de tipo ------------------------------------------------------


@pytest.mark.parametrize(
    "tipo", ["inscripcion", "participacion", "aprobacion"]
)
def test_tipos_con_datos_confirmados_quedan_habilitados(tipo: str) -> None:
    decision = evaluar_tipo(tipo)

    assert decision.habilitado is True
    assert decision.motivos == ()


def test_situacion_pagos_no_se_habilita_mientras_no_haya_origen() -> None:
    decision = evaluar_tipo("situacion_pagos")

    assert decision.habilitado is False
    assert "dato_especifico_sin_origen_confirmado" in decision.motivos
    assert set(decision.motivos) <= MOTIVOS_DE_BLOQUEO


def test_un_origen_fuera_de_los_admisibles_agrega_motivo() -> None:
    decision = evaluar_tipo("participacion", origen="GOOGLE_FORMS")

    assert decision.habilitado is False
    assert "origen_no_admitido_para_tipo" in decision.motivos


def test_un_origen_admisible_no_agrega_motivo() -> None:
    decision = evaluar_tipo("participacion", origen="SIU_GUARANI_EXTENSION")

    assert "origen_no_admitido_para_tipo" not in decision.motivos
    assert decision.habilitado is True


def test_tipo_fuera_del_catalogo_se_rechaza() -> None:
    with pytest.raises(TipoNotificacionDesconocidoError):
        evaluar_tipo("promocion")


def test_decision_habilitada_con_motivos_es_forma_invalida() -> None:
    """Impide construir una decisión que diga «sí» arrastrando bloqueos."""
    with pytest.raises(ValueError):
        DecisionTipoNotificacion(
            tipo="inscripcion",
            origen=None,
            habilitado=True,
            motivos=("dato_especifico_sin_origen_confirmado",),
        )
    with pytest.raises(ValueError):
        DecisionTipoNotificacion(
            tipo="inscripcion", origen=None, habilitado=False, motivos=()
        )


# --- El pipeline por tipo ------------------------------------------------------


def test_participacion_recorre_el_ciclo_completo_con_doble_aprobacion(
    tmp_path: Path,
) -> None:
    registro = RegistroConfirmacionesMemoria()
    destino = DestinoConfirmacionesFake()
    pedido = solicitud(tipo_notificacion="participacion")

    borrador = procesar(tmp_path, registro, solicitud=pedido)
    parcial = procesar(tmp_path, registro, solicitud=pedido, aprobacion=semantica())

    assert borrador.estado == "PENDIENTE_VALIDACION"
    assert borrador.asunto == "[BORRADOR — NO ENVIAR] Notificación de participación"
    assert "Registramos tu participación en: Taller de robótica educativa." in (
        borrador.cuerpo
    )
    assert parcial.estado == "APROBADA_SEMANTICA"
    assert destino.entregas == []

    aprobada = procesar(tmp_path, registro, solicitud=pedido, aprobacion=utilitaria())
    entrega = procesar(
        tmp_path, registro, solicitud=pedido, destino=destino, enviar=True
    )

    assert aprobada.estado == "APROBADA"
    assert entrega.estado == "ENVIADA_SIMULADA"
    assert len(destino.entregas) == 1


def test_aprobacion_exige_las_dos_decisiones_antes_de_entregar(
    tmp_path: Path,
) -> None:
    registro = RegistroConfirmacionesMemoria()
    destino = DestinoConfirmacionesFake()
    pedido = solicitud(tipo_notificacion="aprobacion")

    # Una sola aprobación no alcanza, igual que con inscripción.
    parcial = procesar(
        tmp_path,
        registro,
        solicitud=pedido,
        aprobacion=utilitaria(),
        destino=destino,
        enviar=True,
    )
    aprobada = procesar(tmp_path, registro, solicitud=pedido, aprobacion=semantica())
    entrega = procesar(
        tmp_path, registro, solicitud=pedido, destino=destino, enviar=True
    )

    assert parcial.estado == "APROBADA_UTILITARIA"
    assert "Registramos tu aprobación de: Taller de robótica educativa." in (
        parcial.cuerpo
    )
    assert aprobada.estado == "APROBADA"
    assert entrega.estado == "ENVIADA_SIMULADA"
    assert len(destino.entregas) == 1


def test_participacion_encolada_drena_como_cualquier_confirmacion(
    tmp_path: Path,
) -> None:
    """La cola y el worker no conocen el tipo ni necesitan conocerlo."""
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    destino = DestinoConfirmacionesFake()
    pedido = solicitud(tipo_notificacion="participacion")
    aprobar_ambos(tmp_path, registro, pedido)

    encolada = procesar(
        tmp_path, registro, solicitud=pedido, cola=cola, asincrono=True
    )
    resultados = drenar_envios(
        registro=registro,
        cola=cola,
        destino=destino,
        directorio_salida=tmp_path / "salida",
    )

    assert encolada.estado == "ENVIO_ENCOLADO"
    assert [r.resolucion for r in resultados] == ["entregada"]
    assert len(destino.entregas) == 1
    assert destino.entregas[0].idempotency_key == encolada.idempotency_key


def test_situacion_pagos_se_rechaza_fail_closed_en_toda_via(tmp_path: Path) -> None:
    """Ni borrador ni envío: el dato de deuda no tiene origen confirmado."""
    registro = RegistroConfirmacionesMemoria()
    destino = DestinoConfirmacionesFake()
    pedido = solicitud(tipo_notificacion="situacion_pagos")

    borrador = procesar(tmp_path, registro, solicitud=pedido)
    con_aprobacion = procesar(
        tmp_path,
        registro,
        solicitud=pedido,
        aprobacion=semantica(),
        destino=destino,
        enviar=True,
    )
    encolada = procesar(
        tmp_path,
        registro,
        solicitud=pedido,
        aprobacion=utilitaria(),
        cola=ColaEnviosMemoria(),
        asincrono=True,
    )

    for resultado in (borrador, con_aprobacion, encolada):
        assert resultado.estado == "INVALIDA"
        assert resultado.error == "notification_type_blocked"
        assert resultado.cuerpo is None
    # Nada quedó registrado: el tipo bloqueado no materializa borrador.
    assert registro.obtener(borrador.idempotency_key) is None
    assert destino.entregas == []


def test_la_auditoria_del_bloqueo_nombra_el_tipo_y_el_motivo(
    tmp_path: Path,
) -> None:
    pedido = solicitud(tipo_notificacion="situacion_pagos")
    resultado = procesar(tmp_path, RegistroConfirmacionesMemoria(), solicitud=pedido)

    linea = json.loads(
        resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
    )
    assert linea["tipo_notificacion"] == "situacion_pagos"
    assert linea["resultado"] == "notification_type_blocked"
    assert linea["motivos_bloqueo_tipo"] == [
        "dato_especifico_sin_origen_confirmado"
    ]
    # La auditoría sigue sin datos personales ni texto en claro.
    assert "ana.perez@example.test" not in resultado.log_path.read_text(
        encoding="utf-8"
    )


def test_tipo_inexistente_es_pedido_mal_formado(tmp_path: Path) -> None:
    resultado = procesar(
        tmp_path,
        RegistroConfirmacionesMemoria(),
        solicitud=solicitud(tipo_notificacion="promocion"),
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "notification_type_invalid"
    assert resultado.cuerpo is None


def test_tipo_no_string_falla_cerrado_sin_renderizar(tmp_path: Path) -> None:
    resultado = procesar(
        tmp_path,
        RegistroConfirmacionesMemoria(),
        solicitud=solicitud(tipo_notificacion=None),
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "input_contract_invalid"
    assert resultado.cuerpo is None


def test_participacion_incompleta_sigue_siendo_incompleta(tmp_path: Path) -> None:
    resultado = procesar(
        tmp_path,
        RegistroConfirmacionesMemoria(),
        solicitud=solicitud(tipo_notificacion="participacion", fecha=""),
    )

    assert resultado.estado == "INCOMPLETA"
    assert resultado.error == "required_fields_missing"


def test_el_tipo_distingue_la_comunicacion_en_la_idempotencia(
    tmp_path: Path,
) -> None:
    """Participación e inscripción sobre la misma inscripción son dos
    comunicaciones distintas: no pueden colisionar ni marcarse duplicadas."""
    registro = RegistroConfirmacionesMemoria()
    inscripcion = solicitud()
    participacion = solicitud(tipo_notificacion="participacion")

    primera = procesar(tmp_path, registro, solicitud=inscripcion)
    segunda = procesar(tmp_path, registro, solicitud=participacion)

    assert primera.idempotency_key != segunda.idempotency_key
    assert segunda.estado == "PENDIENTE_VALIDACION"


def test_la_linea_de_auditoria_registra_el_tipo(tmp_path: Path) -> None:
    pedido = solicitud(tipo_notificacion="participacion")
    resultado = procesar(tmp_path, RegistroConfirmacionesMemoria(), solicitud=pedido)

    linea = json.loads(
        resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
    )
    assert linea["tipo_notificacion"] == "participacion"
    assert linea["hu"] == "HU-012"


# --- Regresión: inscripción no cambió -------------------------------------------


def test_inscripcion_sigue_siendo_el_default_y_renderiza_igual(
    tmp_path: Path,
) -> None:
    """Una solicitud sin tipo es una inscripción y produce el borrador de
    siempre, byte a byte contra el golden versionado."""
    pedido = SolicitudConfirmacion(
        id_inscripcion="INS-001",
        nombre_destinatario="Ana Pérez",
        email_destinatario="ana.perez@example.test",
        actividad="Taller de robótica educativa",
        fecha="28 de agosto de 2026, 18:00",
        lugar="Aula 4",
        organiza="Secretaría de Extensión Universitaria",
        contacto="extension@example.test",
    )
    assert pedido.tipo_notificacion == "inscripcion"

    resultado = procesar(tmp_path, RegistroConfirmacionesMemoria(), solicitud=pedido)

    esperado = (
        ROOT / "golden" / "confirmaciones" / "inscripcion-base.txt"
    ).read_text(encoding="utf-8")
    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert f"ASUNTO: {resultado.asunto}\n\n{resultado.cuerpo}" == esperado


def test_inscripcion_declara_el_mismo_contrato_de_campos_que_antes() -> None:
    """El catálogo no le exige a inscripción nada que el pipeline no exigiera."""
    assert set(campos_requeridos("inscripcion")) == set(REQUIRED_FIELDS) | {
        "email_destinatario"
    }
