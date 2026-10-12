"""Corte 4 del diseño HU-012 (D8/D9): instrucciones y confirmación por pago.

Estas pruebas ejercitan el sexto tipo del catálogo v2 —`instrucciones_pago`—
y la confirmación de inscripción que la cuota 1 en `PAGO_CONFIRMADO` o
`BONIFICADA` habilita. Fijan que el correo de preinscripción con el plan de
pago se genera como borrador con el `asunto_preinscripcion` exacto del plan
—la llave con la que la respuesta con el comprobante se asocia después
(§4.2)—, que el cuerpo sale de la plantilla provisional con los datos del
plan, que la corrida enumera los candidatos a confirmación sin producirla
—un comprobante meramente presentado no alcanza (D1)— y que el circuito es
el de siempre: doble aprobación por pieza, sólo el destino habilitado
entrega y la idempotencia cubre las corridas repetidas.
"""

import json
from pathlib import Path

import pytest
from test_pagos import (
    ACTIVIDAD_ID,
    ASUNTO,
    HOY,
    PDF_A,
    PLAN_NOTEBOOKLM,
    escribir_eml,
    escribir_padron,
    escribir_plan,
    situacion,
)

from agente1.buzon import BuzonPropioEml
from agente1.cli_pagos import informe_a_dict
from agente1.confirmaciones import (
    ROL_APROBACION_SEMANTICA,
    ROL_APROBACION_UTILITARIA,
    TIPO_INSTRUCCIONES_PAGO,
    AprobacionHumana,
    ColaEnviosMemoria,
    CuotaInstrucciones,
    DatosInstruccionesPago,
    DestinoConfirmacionesFake,
    RegistroConfirmacionesMemoria,
    SolicitudConfirmacion,
    drenar_envios,
    procesar_confirmacion,
)
from agente1.instrucciones_pago import (
    solicitud_confirmacion_inscripcion,
    solicitud_instrucciones_pago,
)
from agente1.pagos import (
    ESTADO_BONIFICADA,
    ESTADO_COMPROBANTE_PRESENTADO,
    ESTADO_PAGO_CONFIRMADO,
    ESTADO_PENDIENTE,
    MOTIVO_ASUNTO_NO_COINCIDE,
    NOVEDAD_BONIFICADO,
    NOVEDAD_CONFIRMADO_FUNDACION,
    NovedadPago,
    Preinscripto,
    cargar_padron_csv,
    cargar_plan_pagos_csv,
    correr_control_pagos,
)

CONTACTO = "extension@example.test"
ORGANIZA = "Secretaría de Extensión Universitaria"


def plan():
    """El plan del caso de referencia: una cuota, medios y bonificaciones."""
    return cargar_plan_pagos_csv(PLAN_NOTEBOOKLM)


def preinscripto_ana() -> Preinscripto:
    """La fila del padrón que el builder consume: el dominio de `pagos.py`."""
    return Preinscripto(
        id_inscripcion="PRE-001",
        actividad_id=ACTIVIDAD_ID,
        nombre_destinatario="Ana Pérez",
        email_destinatario="ana.perez@example.test",
        bonificado=False,
    )


def pedido_instrucciones(**cambios) -> SolicitudConfirmacion:
    solicitud = solicitud_instrucciones_pago(
        plan=plan(), preinscripto=preinscripto_ana(), contacto=CONTACTO
    )
    if cambios:
        from dataclasses import replace

        solicitud = replace(solicitud, **cambios)
    return solicitud


def aprobacion(*, rol: str) -> AprobacionHumana:
    return AprobacionHumana(
        aprobada=True,
        validador="Validador SEU de prueba",
        rol=rol,
        fecha_iso="2026-09-22T18:00:00-03:00",
    )


def procesar(tmp_path: Path, registro, **extra):
    return procesar_confirmacion(
        solicitud=extra.pop("solicitud", pedido_instrucciones()),
        directorio_salida=tmp_path / "salida",
        registro=registro,
        **extra,
    )


def aprobar_ambos(
    tmp_path: Path, registro, solicitud: SolicitudConfirmacion
) -> None:
    procesar(
        tmp_path,
        registro,
        solicitud=solicitud,
        aprobacion=aprobacion(rol=ROL_APROBACION_SEMANTICA),
    )
    procesar(
        tmp_path,
        registro,
        solicitud=solicitud,
        aprobacion=aprobacion(rol=ROL_APROBACION_UTILITARIA),
    )


def novedad(
    id_inscripcion: str = "PRE-001",
    tipo: str = NOVEDAD_CONFIRMADO_FUNDACION,
    valor: str = "1",
    fila: int = 2,
) -> NovedadPago:
    return NovedadPago(
        id_inscripcion=id_inscripcion,
        tipo=tipo,
        valor=valor,
        fecha="2026-09-21",
        responsable="Departamento Cursos Complementarios",
        fila=fila,
    )


def corrida(tmp_path, *, novedades=()):
    plan_cargado = cargar_plan_pagos_csv(tmp_path / "plan.csv")
    padron_cargado = cargar_padron_csv(
        tmp_path / "padron.csv", actividad_id=plan_cargado.actividad_id
    )
    return correr_control_pagos(
        plan=plan_cargado,
        padron=padron_cargado,
        buzon=BuzonPropioEml(tmp_path / "buzon"),
        hoy=HOY,
        novedades=novedades,
    )


# --- El borrador de instrucciones de pago (D8) ---------------------------------


def test_el_borrador_lleva_el_asunto_del_plan_y_el_plan_en_el_cuerpo(tmp_path):
    resultado = procesar(tmp_path, RegistroConfirmacionesMemoria())

    assert resultado.estado == "PENDIENTE_VALIDACION"
    # El asunto es el del plan, exacto: ni marca de borrador ni asunto_base.
    assert resultado.asunto == ASUNTO
    assert "BORRADOR" not in resultado.asunto
    # La marca viaja en el cuerpo, que es donde el destino la exige.
    assert "BORRADOR — NO ENVIAR" in resultado.cuerpo
    # El plan completo en el cuerpo: cuota, medios, bonificaciones, fechas.
    assert "- Cuota 1: $20.000." in resultado.cuerpo
    assert "Medios de pago: transferencia, Mercado Pago." in resultado.cuerpo
    assert (
        "Bonificaciones: alumnos FIE, personal FIE, egresados FIE."
        in resultado.cuerpo
    )
    assert "Inicio: 2026-10-05." in resultado.cuerpo
    assert "Inscripción abierta hasta: 2026-09-29." in resultado.cuerpo
    assert "comprobante" in resultado.cuerpo
    assert "Ana Pérez" in resultado.cuerpo
    assert f"Contacto: {CONTACTO}" in resultado.cuerpo


def test_el_cuerpo_es_determinista_entre_procesos(tmp_path):
    """Dos procesamientos sobre registros distintos producen el mismo texto y
    la misma clave: el borrador no depende de azar ni de reloj."""
    primera = procesar(tmp_path / "a", RegistroConfirmacionesMemoria())
    segunda = procesar(tmp_path / "b", RegistroConfirmacionesMemoria())

    assert (primera.asunto, primera.cuerpo) == (segunda.asunto, segunda.cuerpo)
    assert primera.idempotency_key == segunda.idempotency_key


def test_respuesta_al_asunto_del_borrador_se_asocia_al_plan(tmp_path):
    """El preinscripto responde «Re: <asunto del plan>» con su comprobante y
    la corrida lo asocia: por eso el asunto del borrador no lleva marca."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "ana.eml",
        remitente="Ana Pérez <ana.perez@example.test>",
        asunto=f"Re: {ASUNTO}",
        adjuntos=(("comprobante.pdf", "application/pdf", PDF_A),),
    )

    informe = corrida(tmp_path)

    ana = situacion(informe, "PRE-001")
    assert ana.cuotas[0].estado == ESTADO_COMPROBANTE_PRESENTADO
    assert informe.no_asociadas == ()


def test_un_asunto_distinto_al_del_plan_no_asocia(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "ana.eml",
        remitente="ana.perez@example.test",
        asunto="Re: consulta por el curso",
        adjuntos=(("comprobante.pdf", "application/pdf", PDF_A),),
    )

    informe = corrida(tmp_path)

    assert informe.no_asociadas[0].motivo == MOTIVO_ASUNTO_NO_COINCIDE
    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_PENDIENTE


# --- El circuito es el de siempre ------------------------------------------------


def test_ciclo_completo_con_doble_aprobacion_y_destino_fake(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    destino = DestinoConfirmacionesFake()
    pedido = pedido_instrucciones()

    parcial = procesar(
        tmp_path,
        registro,
        solicitud=pedido,
        aprobacion=aprobacion(rol=ROL_APROBACION_SEMANTICA),
        destino=destino,
        enviar=True,
    )
    aprobada = procesar(
        tmp_path,
        registro,
        solicitud=pedido,
        aprobacion=aprobacion(rol=ROL_APROBACION_UTILITARIA),
    )
    entrega = procesar(
        tmp_path, registro, solicitud=pedido, destino=destino, enviar=True
    )

    # Una sola aprobación no entrega, igual que con los otros tipos.
    assert parcial.estado == "APROBADA_SEMANTICA"
    assert aprobada.estado == "APROBADA"
    assert entrega.estado == "ENVIADA_SIMULADA"
    assert len(destino.entregas) == 1
    assert destino.entregas[0].asunto == ASUNTO


def test_encolada_drena_con_el_mismo_asunto(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    destino = DestinoConfirmacionesFake()
    pedido = pedido_instrucciones()
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
    assert destino.entregas[0].asunto == ASUNTO


def test_reprocesar_la_misma_solicitud_es_duplicada(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    pedido = pedido_instrucciones()

    procesar(tmp_path, registro, solicitud=pedido)
    repetida = procesar(tmp_path, registro, solicitud=pedido)

    assert repetida.estado == "DUPLICADA"


def test_el_plan_cambia_la_clave_de_idempotencia(tmp_path):
    """Otro monto u otro asunto es otra comunicación: no puede absorberse."""
    otro_plan = DatosInstruccionesPago(
        asunto_preinscripcion=ASUNTO,
        cuotas=(CuotaInstrucciones(nro=1, monto=25000),),
        medios_pago=("transferencia",),
        bonificaciones=(),
    )
    base = procesar(tmp_path / "a", RegistroConfirmacionesMemoria())
    distinta = procesar(
        tmp_path / "b",
        RegistroConfirmacionesMemoria(),
        solicitud=pedido_instrucciones(datos_pago=otro_plan),
    )

    assert base.idempotency_key != distinta.idempotency_key


# --- Validación cerrada del dato específico --------------------------------------


def test_sin_datos_pago_la_solicitud_es_incompleta(tmp_path):
    resultado = procesar(
        tmp_path,
        RegistroConfirmacionesMemoria(),
        solicitud=pedido_instrucciones(datos_pago=None),
    )

    assert resultado.estado == "INCOMPLETA"
    assert resultado.error == "required_fields_missing"
    assert resultado.cuerpo is None


@pytest.mark.parametrize(
    "datos_pago",
    [
        DatosInstruccionesPago(
            asunto_preinscripcion="  ",
            cuotas=(CuotaInstrucciones(nro=1, monto=20000),),
            medios_pago=("transferencia",),
            bonificaciones=(),
        ),
        DatosInstruccionesPago(
            asunto_preinscripcion=ASUNTO,
            cuotas=(),
            medios_pago=("transferencia",),
            bonificaciones=(),
        ),
        DatosInstruccionesPago(
            asunto_preinscripcion=ASUNTO,
            cuotas=(CuotaInstrucciones(nro=1, monto=0),),
            medios_pago=("transferencia",),
            bonificaciones=(),
        ),
        DatosInstruccionesPago(
            asunto_preinscripcion=ASUNTO,
            cuotas=(CuotaInstrucciones(nro=1, monto=20000, vencimiento="29/09"),),
            medios_pago=("transferencia",),
            bonificaciones=(),
        ),
    ],
)
def test_datos_pago_mal_formados_son_solicitud_incompleta(tmp_path, datos_pago):
    resultado = procesar(
        tmp_path,
        RegistroConfirmacionesMemoria(),
        solicitud=pedido_instrucciones(datos_pago=datos_pago),
    )

    assert resultado.estado == "INCOMPLETA"
    assert resultado.error == "required_fields_missing"


def test_la_auditoria_no_lleva_el_plan_ni_datos_personales(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    pedido = pedido_instrucciones()
    procesar(tmp_path, registro, solicitud=pedido)
    aprobar_ambos(tmp_path, registro, pedido)
    resultado = procesar(
        tmp_path,
        registro,
        solicitud=pedido,
        destino=DestinoConfirmacionesFake(),
        enviar=True,
    )
    assert resultado.estado == "ENVIADA_SIMULADA"

    texto = resultado.log_path.read_text(encoding="utf-8")
    # La auditoría conserva hashes: ni el correo, ni los medios, ni montos.
    for dato in (
        "ana.perez@example.test",
        "Ana Pérez",
        "Mercado Pago",
        "transferencia",
        "20.000",
        "20000",
    ):
        assert dato not in texto
    ultima = json.loads(texto.splitlines()[-1])
    assert ultima["tipo_notificacion"] == TIPO_INSTRUCCIONES_PAGO


# --- Los candidatos a confirmación (D9) -------------------------------------------


def test_cuota_1_confirmada_por_la_fundacion_genera_candidato(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path, novedades=[novedad()])

    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_PAGO_CONFIRMADO
    [candidato] = informe.candidatos_confirmacion
    assert candidato.id_inscripcion == "PRE-001"
    assert candidato.razon == ESTADO_PAGO_CONFIRMADO
    assert candidato.email_destinatario == "ana.perez@example.test"


def test_bonificada_en_el_padron_genera_candidato(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(
        tmp_path,
        filas=(
            ("PRE-001", "Ana Pérez", "ana.perez@example.test", "si"),
            ("PRE-002", "Bruno García", "bruno.garcia@example.test", "no"),
        ),
    )
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path)

    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_BONIFICADA
    [candidato] = informe.candidatos_confirmacion
    assert candidato.id_inscripcion == "PRE-001"
    assert candidato.razon == ESTADO_BONIFICADA


def test_novedad_bonificado_genera_candidato(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(
        tmp_path,
        novedades=[novedad(tipo=NOVEDAD_BONIFICADO, valor="")],
    )

    [candidato] = informe.candidatos_confirmacion
    assert candidato.id_inscripcion == "PRE-001"
    assert candidato.razon == ESTADO_BONIFICADA


def test_comprobante_presentado_no_genera_candidato(tmp_path):
    """Un comprobante no es un pago (D1): la Fundación es la que verifica."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "ana.eml",
        remitente="ana.perez@example.test",
        adjuntos=(("comprobante.pdf", "application/pdf", PDF_A),),
    )

    informe = corrida(tmp_path)

    assert situacion(informe, "PRE-001").cuotas[0].estado == (
        ESTADO_COMPROBANTE_PRESENTADO
    )
    assert informe.candidatos_confirmacion == ()


def test_cuota_pendiente_no_genera_candidato(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path)

    assert informe.candidatos_confirmacion == ()


def test_el_informe_serializado_expone_los_candidatos(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    salida = informe_a_dict(corrida(tmp_path, novedades=[novedad()]))

    assert salida["candidatos_confirmacion"] == [
        {
            "id_inscripcion": "PRE-001",
            "nombre_destinatario": "Ana Pérez",
            "email_destinatario": "ana.perez@example.test",
            "razon": ESTADO_PAGO_CONFIRMADO,
        }
    ]


def test_el_candidato_arma_la_confirmacion_de_inscripcion(tmp_path):
    """D9: el candidato produce la solicitud del tipo `inscripcion` —no un
    tipo nuevo— y tramita por el circuito por envío con la doble aprobación."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()
    informe = corrida(tmp_path, novedades=[novedad()])
    [candidato] = informe.candidatos_confirmacion

    solicitud = solicitud_confirmacion_inscripcion(
        plan=cargar_plan_pagos_csv(tmp_path / "plan.csv"),
        candidato=candidato,
        contacto=CONTACTO,
        organiza=ORGANIZA,
    )

    registro = RegistroConfirmacionesMemoria()
    destino = DestinoConfirmacionesFake()
    borrador = procesar(tmp_path, registro, solicitud=solicitud)
    assert borrador.estado == "PENDIENTE_VALIDACION"
    assert solicitud.tipo_notificacion == "inscripcion"
    assert "Registramos tu inscripción a:" in borrador.cuerpo

    aprobar_ambos(tmp_path, registro, solicitud)
    entrega = procesar(
        tmp_path, registro, solicitud=solicitud, destino=destino, enviar=True
    )
    assert entrega.estado == "ENVIADA_SIMULADA"
    assert len(destino.entregas) == 1


def test_la_confirmacion_es_idempotente_si_la_corrida_se_repite(tmp_path):
    """La corrida puede enumerar el mismo candidato dos veces —no persiste
    estado— y el registro de HU-012 impide la segunda confirmación."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()
    plan_cargado = cargar_plan_pagos_csv(tmp_path / "plan.csv")
    primera = corrida(tmp_path, novedades=[novedad()])
    segunda = corrida(tmp_path, novedades=[novedad()])

    assert primera.candidatos_confirmacion == segunda.candidatos_confirmacion

    registro = RegistroConfirmacionesMemoria()
    for informe in (primera, segunda):
        solicitud = solicitud_confirmacion_inscripcion(
            plan=plan_cargado,
            candidato=informe.candidatos_confirmacion[0],
            contacto=CONTACTO,
            organiza=ORGANIZA,
        )
        resultado = procesar(tmp_path, registro, solicitud=solicitud)

    assert resultado.estado == "DUPLICADA"


def test_instrucciones_y_confirmacion_son_comunicaciones_distintas(tmp_path):
    """El correo de instrucciones y la confirmación sobre la misma
    inscripción no colisionan: son dos piezas del circuito por envío."""
    registro = RegistroConfirmacionesMemoria()
    instrucciones = pedido_instrucciones()
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()
    informe = corrida(tmp_path, novedades=[novedad()])
    confirmacion = solicitud_confirmacion_inscripcion(
        plan=cargar_plan_pagos_csv(tmp_path / "plan.csv"),
        candidato=informe.candidatos_confirmacion[0],
        contacto=CONTACTO,
        organiza=ORGANIZA,
    )

    una = procesar(tmp_path, registro, solicitud=instrucciones)
    otra = procesar(tmp_path, registro, solicitud=confirmacion)

    assert una.idempotency_key != otra.idempotency_key
    assert otra.estado == "PENDIENTE_VALIDACION"
