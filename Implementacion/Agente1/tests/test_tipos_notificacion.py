"""HU-012 ampliada (bible 22/09 + control de pagos): catálogo de tipos v2.

La HU pasó de «confirmaciones de inscripción» a «notificaciones automáticas
de inscripción, participación, situación de pagos y aprobación», y el
diseño de control de pagos agregó `recordatorio_pago` con circuito por lote.
Estas pruebas fijan que el catálogo es cerrado y coherente con la matriz de
orígenes, que los tipos por envío recorren el mismo pipeline con la misma
doble aprobación —incluida `situacion_pagos`, que en v2 se habilita al
derivar su dato del plan de pagos en lugar del dato `DESCONOCIDO` de v1—,
que `recordatorio_pago` no puede tramitar por solicitud individual, y que
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
    MODO_CIRCUITO_LOTE,
    MODO_CIRCUITO_POR_ENVIO,
    MODOS_CIRCUITO,
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
    modo_circuito,
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


def test_el_catalogo_es_cerrado_y_tiene_los_tipos_de_la_bible_y_pagos() -> None:
    assert CONTRACT_VERSION == "tipos_notificacion_v2"
    assert STATUS == "CANDIDATO_PENDIENTE_CONFIRMACION_SEU"
    assert CATALOGO["x-hu"] == "HU-012"
    assert CATALOGO["x-habilita-envio"] is False
    assert CATALOGO["x-reemplaza"] == "tipos_notificacion_v1"
    assert TIPOS_NOTIFICACION == frozenset(
        {
            "inscripcion",
            "participacion",
            "situacion_pagos",
            "aprobacion",
            "recordatorio_pago",
        }
    )
    assert TIPO_NOTIFICACION_PREDETERMINADO == "inscripcion"
    assert MODOS_CIRCUITO == frozenset({"por_envio", "lote"})


@pytest.mark.parametrize("tipo", sorted(TIPOS_NOTIFICACION))
def test_cada_tipo_declara_campos_origenes_plantilla_y_procedencia(
    tipo: str,
) -> None:
    item = descripcion_tipo(tipo)

    assert item["procedencia_tipo"] == "CONFIRMADO_SEU"
    assert item["modo_circuito"] in MODOS_CIRCUITO
    assert item["campos_requeridos"]
    assert set(item["campos_requeridos"]) <= set(REQUIRED_FIELDS) | {
        "email_destinatario"
    }
    assert set(item["origenes_admisibles"]) <= set(ORIGENES_DE_INSCRIPCION)
    assert set(item["datos_especificos"].values()) <= PROCEDENCIAS
    assert set(item["motivos_de_bloqueo"]) <= MOTIVOS_DE_BLOQUEO
    assert item["plantilla"]["asunto_base"].strip()
    assert item["plantilla"]["frase_evento"].strip()


def test_los_tipos_por_envio_exigen_los_campos_confirmados() -> None:
    """Los cuatro tipos que tramitan por solicitud usan el mismo set de
    campos: el contacto del inscripto, confirmado por la SEU el 22/09."""
    for tipo in ("inscripcion", "participacion", "situacion_pagos", "aprobacion"):
        assert modo_circuito(tipo) == MODO_CIRCUITO_POR_ENVIO
        assert set(campos_requeridos(tipo)) == set(REQUIRED_FIELDS) | {
            "email_destinatario"
        }


def test_recordatorio_pago_declara_el_modo_lote_y_sus_campos() -> None:
    item = descripcion_tipo("recordatorio_pago")

    assert modo_circuito("recordatorio_pago") == MODO_CIRCUITO_LOTE
    # El ítem consume los datos de contacto del padrón y del plan; no usa
    # los campos del evento (`fecha`, `lugar`, `organiza`) de una solicitud.
    assert set(item["campos_requeridos"]) == {
        "id_inscripcion",
        "nombre_destinatario",
        "email_destinatario",
        "actividad",
        "contacto",
    }
    # Todo lo que la SEU no confirmó queda declarado como supuesto, no como
    # desconocido: nada en el lote depende de un dato sin fundamento.
    assert set(item["datos_especificos"].values()) == {"SUPUESTO_TECNICO"}
    assert item["motivos_de_bloqueo"] == []


def test_situacion_pagos_ya_no_declara_el_dato_desconocido_de_v1() -> None:
    """En v2 la situación de pagos se deriva del plan, el padrón, el buzón y
    las novedades: `situacion_deuda_o_saldo` desaparece del catálogo."""
    item = descripcion_tipo("situacion_pagos")

    assert "situacion_deuda_o_saldo" not in item["datos_especificos"]
    assert "origen_datos_especificos" not in item
    assert datos_sin_origen_confirmado("situacion_pagos") == ()
    assert set(item["datos_especificos"].values()) == {"SUPUESTO_TECNICO"}
    assert item["motivos_de_bloqueo"] == []


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


@pytest.mark.parametrize("tipo", sorted(TIPOS_NOTIFICACION))
def test_los_cinco_tipos_quedan_habilitados_en_v2(tipo: str) -> None:
    """En v2 ningún tipo tiene un dato `DESCONOCIDO`: el bloqueo por dato
    sin fundamento sigue en el catálogo pero hoy no se aplica a ninguno."""
    decision = evaluar_tipo(tipo)

    assert decision.habilitado is True
    assert decision.motivos == ()


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


def test_situacion_pagos_recorre_el_ciclo_completo_en_v2(tmp_path: Path) -> None:
    """La situación de pagos tramita por envío como los demás tipos: borrador,
    doble aprobación por pieza y entrega contra el fake."""
    registro = RegistroConfirmacionesMemoria()
    destino = DestinoConfirmacionesFake()
    pedido = solicitud(tipo_notificacion="situacion_pagos")

    borrador = procesar(tmp_path, registro, solicitud=pedido)
    parcial = procesar(tmp_path, registro, solicitud=pedido, aprobacion=semantica())
    aprobada = procesar(tmp_path, registro, solicitud=pedido, aprobacion=utilitaria())
    entrega = procesar(
        tmp_path, registro, solicitud=pedido, destino=destino, enviar=True
    )

    assert borrador.estado == "PENDIENTE_VALIDACION"
    assert borrador.asunto == (
        "[BORRADOR — NO ENVIAR] Notificación de situación de pagos"
    )
    assert "Registramos la situación de pagos de:" in borrador.cuerpo
    assert parcial.estado == "APROBADA_SEMANTICA"
    assert aprobada.estado == "APROBADA"
    assert entrega.estado == "ENVIADA_SIMULADA"
    assert len(destino.entregas) == 1


def test_recordatorio_pago_no_tramita_por_solicitud_individual(
    tmp_path: Path,
) -> None:
    """El tipo `lote` nunca produce borrador por la vía por-envío: sus ítems
    nacen de la planificación de la corrida y se encolan en `recordatorios`."""
    registro = RegistroConfirmacionesMemoria()
    destino = DestinoConfirmacionesFake()
    pedido = solicitud(tipo_notificacion="recordatorio_pago")

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
        assert resultado.error == "notification_mode_mismatch"
        assert resultado.cuerpo is None
    # Nada quedó registrado: el modo incorrecto no materializa borrador.
    assert registro.obtener(borrador.idempotency_key) is None
    assert destino.entregas == []


def test_la_auditoria_del_modo_incorrecto_nombra_tipo_y_modo(
    tmp_path: Path,
) -> None:
    pedido = solicitud(tipo_notificacion="recordatorio_pago")
    resultado = procesar(tmp_path, RegistroConfirmacionesMemoria(), solicitud=pedido)

    linea = json.loads(
        resultado.log_path.read_text(encoding="utf-8").splitlines()[-1]
    )
    assert linea["tipo_notificacion"] == "recordatorio_pago"
    assert linea["resultado"] == "notification_mode_mismatch"
    assert linea["modo_circuito"] == "lote"
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
