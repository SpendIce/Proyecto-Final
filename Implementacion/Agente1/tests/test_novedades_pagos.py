"""Novedades de pago del Departamento (§6.2 del diseño HU-012).

Estas pruebas ejercitan la interfaz pública de la corrida —
`correr_control_pagos` con el parámetro `novedades` — para cada tipo del
catálogo `novedades_pago_v1`: confirmación de la Fundación, comprobante
rechazado, comprobante que cubre N cuotas, dirección alternativa y
bonificado. Fijan la precedencia de las novedades sobre lo derivado del
buzón, que un error de la novedad se informa con motivo y nunca se aplica ni
se ignora, y la marca «bonificación no verificable» de D14. El loader
`cargar_novedades_csv` se prueba sobre la forma del CSV.
"""

import csv
import hashlib
from datetime import date, datetime, timezone

import pytest
from test_pagos import (
    HOY,
    PDF_A,
    PDF_B,
    escribir_eml,
    escribir_padron,
    escribir_plan,
    situacion,
)

from agente1.buzon import BuzonPropioEml
from agente1.pagos import (
    CONTRATO_NOVEDADES,
    ESTADO_BONIFICADA,
    ESTADO_COMPROBANTE_PRESENTADO,
    ESTADO_PAGO_CONFIRMADO,
    ESTADO_PENDIENTE,
    MOTIVO_NOVEDAD_DATO_INVALID,
    MOTIVO_NOVEDAD_INSCRIPCION_DESCONOCIDA,
    MOTIVO_NOVEDAD_NO_APLICABLE,
    MOTIVO_NOVEDAD_TIPO_DESCONOCIDO,
    MOTIVO_NOVEDAD_VALOR_INVALID,
    MOTIVO_REMITENTE_AMBIGUO,
    MOTIVO_REMITENTE_SIN_COINCIDENCIA,
    MOTIVOS_NOVEDAD_INVALIDA,
    NOVEDAD_BONIFICADO,
    NOVEDAD_COMPROBANTE_CUBRE_N_CUOTAS,
    NOVEDAD_COMPROBANTE_RECHAZADO,
    NOVEDAD_CONFIRMADO_FUNDACION,
    NOVEDAD_EMAIL_ALTERNATIVO,
    NOVEDADES_CONTRACT_VERSION,
    TIPOS_NOVEDAD,
    ControlPagosError,
    NovedadPago,
    cargar_novedades_csv,
    cargar_padron_csv,
    cargar_plan_pagos_csv,
    correr_control_pagos,
)


def novedad(
    id_inscripcion: str = "PRE-001",
    tipo: str = NOVEDAD_CONFIRMADO_FUNDACION,
    valor: str = "1",
    fecha: str = "2026-09-21",
    responsable: str = "Departamento Cursos Complementarios",
    fila: int = 2,
) -> NovedadPago:
    """Una novedad como la cargaría el Departamento en la pestaña."""
    return NovedadPago(
        id_inscripcion=id_inscripcion,
        tipo=tipo,
        valor=valor,
        fecha=fecha,
        responsable=responsable,
        fila=fila,
    )


def corrida(tmp_path, *, hoy: date = HOY, novedades=()):
    """La corrida por su interfaz: plan, padrón y buzón del directorio, más
    las novedades recibidas como entrada."""
    plan = cargar_plan_pagos_csv(tmp_path / "plan.csv")
    padron = cargar_padron_csv(
        tmp_path / "padron.csv", actividad_id=plan.actividad_id
    )
    return correr_control_pagos(
        plan=plan,
        padron=padron,
        buzon=BuzonPropioEml(tmp_path / "buzon"),
        hoy=hoy,
        novedades=novedades,
    )


def escribir_novedades(directorio, filas) -> None:
    """La pestaña «Novedades de pago» exportada a CSV con su encabezado."""
    with (directorio / "novedades.csv").open(
        "w", encoding="utf-8", newline=""
    ) as archivo:
        writer = csv.writer(archivo)
        writer.writerow(
            ["id_inscripcion", "tipo", "valor", "fecha", "responsable"]
        )
        writer.writerows(filas)


def buzon_con_comprobante(tmp_path, remitente="ana.perez@example.test", datos=PDF_A):
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "respuesta.eml",
        remitente=remitente,
        adjuntos=(("comprobante.pdf", "application/pdf", datos),),
    )
    return buzon


def motivos_error(informe):
    return {e.novedad.fila: e.motivo for e in informe.novedades_con_error}


# --- El contrato de novedades -------------------------------------------------


def test_el_contrato_de_novedades_es_versionado_y_catalogo_cerrado():
    assert NOVEDADES_CONTRACT_VERSION == "novedades_pago_v1"
    assert CONTRATO_NOVEDADES["x-status"] == "CANDIDATO_PENDIENTE_CONFIRMACION_SEU"
    assert CONTRATO_NOVEDADES["x-hu"] == "HU-012"
    assert CONTRATO_NOVEDADES["x-habilita-envio"] is False
    assert TIPOS_NOVEDAD == {
        NOVEDAD_CONFIRMADO_FUNDACION,
        NOVEDAD_COMPROBANTE_RECHAZADO,
        NOVEDAD_COMPROBANTE_CUBRE_N_CUOTAS,
        NOVEDAD_EMAIL_ALTERNATIVO,
        NOVEDAD_BONIFICADO,
    }
    assert MOTIVOS_NOVEDAD_INVALIDA == {
        MOTIVO_NOVEDAD_DATO_INVALID,
        MOTIVO_NOVEDAD_TIPO_DESCONOCIDO,
        MOTIVO_NOVEDAD_VALOR_INVALID,
        MOTIVO_NOVEDAD_INSCRIPCION_DESCONOCIDA,
        MOTIVO_NOVEDAD_NO_APLICABLE,
    }
    assert CONTRATO_NOVEDADES["forma_csv"]["columnas"] == [
        "id_inscripcion",
        "tipo",
        "valor",
        "fecha",
        "responsable",
    ]


# --- CONFIRMADO_FUNDACION -----------------------------------------------------


def test_confirmado_fundacion_marca_pago_confirmado_sin_comprobante(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path, novedades=[novedad()])

    ana = situacion(informe, "PRE-001")
    assert ana.cuotas[0].estado == ESTADO_PAGO_CONFIRMADO
    assert ana.cuotas_cubiertas == 1
    assert informe.novedades_aplicadas == (novedad(),)
    assert informe.novedades_con_error == ()


def test_un_comprobante_presentado_nunca_alcanza_pago_confirmado(tmp_path):
    """D1: el comprobante declara que la persona dice haber pagado; el pago
    confirmado sólo sale de la novedad de la Fundación."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon_con_comprobante(tmp_path)

    informe = corrida(tmp_path)

    assert situacion(informe, "PRE-001").cuotas[0].estado == (
        ESTADO_COMPROBANTE_PRESENTADO
    )


def test_confirmado_fundacion_tiene_precedencia_sobre_el_buzon(tmp_path):
    """El comprobante queda como rastro, pero el estado pasa a ser el de la
    novedad del Departamento (§6.2)."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon_con_comprobante(tmp_path)

    informe = corrida(tmp_path, novedades=[novedad()])

    cuota = situacion(informe, "PRE-001").cuotas[0]
    assert cuota.estado == ESTADO_PAGO_CONFIRMADO
    assert cuota.comprobante is not None
    assert cuota.comprobante.sha256 == hashlib.sha256(PDF_A).hexdigest()


def test_confirmado_apunta_a_la_cuota_que_indica_el_valor(tmp_path):
    escribir_plan(
        tmp_path,
        filas_extra=(
            ("cantidad_cuotas", "2", "SUPUESTO_TECNICO"),
            ("cuota_2_monto", "20000", "SUPUESTO_TECNICO"),
            ("cuota_2_vencimiento", "", "DESCONOCIDO"),
        ),
    )
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path, novedades=[novedad(valor="2")])

    ana = situacion(informe, "PRE-001")
    assert [c.estado for c in ana.cuotas] == [
        ESTADO_PENDIENTE,
        ESTADO_PAGO_CONFIRMADO,
    ]
    assert ana.cuotas_cubiertas == 1


# --- COMPROBANTE_RECHAZADO ----------------------------------------------------


def test_comprobante_rechazado_devuelve_la_cuota_a_pendiente(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon_con_comprobante(tmp_path)

    informe = corrida(
        tmp_path, novedades=[novedad(tipo=NOVEDAD_COMPROBANTE_RECHAZADO)]
    )

    ana = situacion(informe, "PRE-001")
    assert ana.cuotas[0].estado == ESTADO_PENDIENTE
    assert ana.cuotas_cubiertas == 0
    # El comprobante sigue existiendo pero ya no cubre la cuota: se informa.
    assert len(ana.comprobantes_sin_cuota) == 1
    assert ana.comprobantes_sin_cuota[0].sha256 == hashlib.sha256(
        PDF_A
    ).hexdigest()


def test_la_cuota_rechazada_recalcula_vencida_con_el_hoy_de_la_corrida(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon_con_comprobante(tmp_path)

    informe = corrida(
        tmp_path,
        hoy=date(2026, 9, 30),
        novedades=[novedad(tipo=NOVEDAD_COMPROBANTE_RECHAZADO)],
    )

    assert situacion(informe, "PRE-001").cuotas[0].vencida is True


def test_rechazado_sobre_cuota_sin_comprobante_es_novedad_no_aplicable(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(
        tmp_path, novedades=[novedad(tipo=NOVEDAD_COMPROBANTE_RECHAZADO)]
    )

    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_PENDIENTE
    assert informe.novedades_aplicadas == ()
    assert motivos_error(informe) == {2: MOTIVO_NOVEDAD_NO_APLICABLE}


def test_rechazado_no_deshace_una_confirmacion_de_la_fundacion(tmp_path):
    """Si el Departamento confirmó el ingreso, un rechazo posterior del
    comprobante no puede bajarla a pendiente: se informa, no se aplica."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon_con_comprobante(tmp_path)

    informe = corrida(
        tmp_path,
        novedades=[
            novedad(valor="1", fila=2),
            novedad(tipo=NOVEDAD_COMPROBANTE_RECHAZADO, valor="1", fila=3),
        ],
    )

    assert situacion(informe, "PRE-001").cuotas[0].estado == (
        ESTADO_PAGO_CONFIRMADO
    )
    assert motivos_error(informe) == {3: MOTIVO_NOVEDAD_NO_APLICABLE}


# --- COMPROBANTE_CUBRE_N_CUOTAS -----------------------------------------------


def test_un_comprobante_que_cubre_n_cuotas_cubre_desde_la_uno(tmp_path):
    """§4.3: un solo comprobante que cubre dos cuotas se corrige por novedad."""
    escribir_plan(
        tmp_path,
        filas_extra=(
            ("cantidad_cuotas", "2", "SUPUESTO_TECNICO"),
            ("cuota_2_monto", "20000", "SUPUESTO_TECNICO"),
            ("cuota_2_vencimiento", "", "DESCONOCIDO"),
        ),
    )
    escribir_padron(tmp_path)
    buzon_con_comprobante(tmp_path)

    informe = corrida(
        tmp_path,
        novedades=[novedad(tipo=NOVEDAD_COMPROBANTE_CUBRE_N_CUOTAS, valor="2")],
    )

    ana = situacion(informe, "PRE-001")
    assert ana.cuotas_cubiertas == 2
    assert [c.estado for c in ana.cuotas] == [
        ESTADO_COMPROBANTE_PRESENTADO,
        ESTADO_COMPROBANTE_PRESENTADO,
    ]
    # El mismo comprobante queda asignado a las dos cuotas.
    assert {c.comprobante.sha256 for c in ana.cuotas} == {
        hashlib.sha256(PDF_A).hexdigest()
    }
    assert ana.comprobantes_sin_cuota == ()


def test_cubre_n_corre_la_asignacion_de_los_otros_comprobantes(tmp_path):
    """Con el primer comprobante cubriendo N, los demás siguen desde N+1."""
    escribir_plan(
        tmp_path,
        filas_extra=(
            ("cantidad_cuotas", "3", "SUPUESTO_TECNICO"),
            ("cuota_2_monto", "20000", "SUPUESTO_TECNICO"),
            ("cuota_2_vencimiento", "", "DESCONOCIDO"),
            ("cuota_3_monto", "20000", "SUPUESTO_TECNICO"),
            ("cuota_3_vencimiento", "", "DESCONOCIDO"),
        ),
    )
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "primero.eml",
        message_id="<m1@example.test>",
        fecha=datetime(2026, 9, 18, 10, 0, tzinfo=timezone.utc),
        adjuntos=(("a.pdf", "application/pdf", PDF_A),),
    )
    escribir_eml(
        buzon,
        "segundo.eml",
        message_id="<m2@example.test>",
        fecha=datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc),
        adjuntos=(("b.pdf", "application/pdf", PDF_B),),
    )

    informe = corrida(
        tmp_path,
        novedades=[novedad(tipo=NOVEDAD_COMPROBANTE_CUBRE_N_CUOTAS, valor="2")],
    )

    ana = situacion(informe, "PRE-001")
    assert ana.cuotas[0].comprobante.sha256 == hashlib.sha256(PDF_A).hexdigest()
    assert ana.cuotas[1].comprobante.sha256 == hashlib.sha256(PDF_A).hexdigest()
    assert ana.cuotas[2].comprobante.sha256 == hashlib.sha256(PDF_B).hexdigest()
    assert ana.cuotas_cubiertas == 3


def test_cubre_n_sin_comprobante_presentado_es_novedad_no_aplicable(tmp_path):
    """«El comprobante cubre N cuotas» presupone un comprobante: sin él, la
    premisa no se sostiene y la novedad se informa como incoherente."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(
        tmp_path,
        novedades=[novedad(tipo=NOVEDAD_COMPROBANTE_CUBRE_N_CUOTAS, valor="1")],
    )

    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_PENDIENTE
    assert motivos_error(informe) == {2: MOTIVO_NOVEDAD_NO_APLICABLE}


# --- EMAIL_ALTERNATIVO --------------------------------------------------------


def test_direccion_alternativa_asocia_las_respuestas_a_la_persona(tmp_path):
    """§4.2: quien responde desde otra dirección quedaba en «no asociadas»;
    la novedad carga la correspondencia y la respuesta cuenta."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon_con_comprobante(tmp_path, remitente="ana.personal@example.test")

    informe = corrida(
        tmp_path,
        novedades=[
            novedad(
                tipo=NOVEDAD_EMAIL_ALTERNATIVO, valor="ana.personal@example.test"
            )
        ],
    )

    ana = situacion(informe, "PRE-001")
    assert ana.cuotas[0].estado == ESTADO_COMPROBANTE_PRESENTADO
    assert informe.no_asociadas == ()
    assert informe.novedades_aplicadas[0].tipo == NOVEDAD_EMAIL_ALTERNATIVO


def test_sin_la_novedad_la_direccion_desconocida_sigue_sin_asociarse(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon_con_comprobante(tmp_path, remitente="ana.personal@example.test")

    informe = corrida(tmp_path)

    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_PENDIENTE
    assert informe.no_asociadas[0].motivo == MOTIVO_REMITENTE_SIN_COINCIDENCIA


def test_alternativa_que_colisiona_con_otra_persona_da_ambigua(tmp_path):
    """Si la alternativa coincide con el correo del padrón de otra persona,
    el remitente ya no es único: va a «no asociadas», no se adivina."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon_con_comprobante(tmp_path, remitente="bruno.garcia@example.test")

    informe = corrida(
        tmp_path,
        novedades=[
            novedad(
                tipo=NOVEDAD_EMAIL_ALTERNATIVO, valor="bruno.garcia@example.test"
            )
        ],
    )

    assert informe.no_asociadas[0].motivo == MOTIVO_REMITENTE_AMBIGUO
    for s in informe.situaciones:
        assert s.cuotas[0].estado == ESTADO_PENDIENTE


# --- BONIFICADO ---------------------------------------------------------------


def test_novedad_bonificado_marca_todas_las_cuotas_bonificadas(tmp_path):
    escribir_plan(
        tmp_path,
        filas_extra=(
            ("cantidad_cuotas", "2", "SUPUESTO_TECNICO"),
            ("cuota_2_monto", "20000", "SUPUESTO_TECNICO"),
            ("cuota_2_vencimiento", "", "DESCONOCIDO"),
        ),
    )
    escribir_padron(tmp_path)
    buzon_con_comprobante(tmp_path)

    informe = corrida(
        tmp_path, novedades=[novedad(tipo=NOVEDAD_BONIFICADO, valor="")]
    )

    ana = situacion(informe, "PRE-001")
    assert [c.estado for c in ana.cuotas] == [
        ESTADO_BONIFICADA,
        ESTADO_BONIFICADA,
    ]
    assert ana.cuotas_cubiertas == 2
    assert len(ana.comprobantes_sin_cuota) == 1


def test_bonificado_por_novedad_gana_sobre_el_no_del_padron(tmp_path):
    """La novedad del Departamento tiene precedencia: un «no» del padrón no
    impide la bonificación cargada a mano."""
    escribir_plan(tmp_path)
    escribir_padron(
        tmp_path,
        filas=(
            ("PRE-001", "Ana Pérez", "ana.perez@example.test", "no"),
        ),
    )
    (tmp_path / "buzon").mkdir()

    informe = corrida(
        tmp_path, novedades=[novedad(tipo=NOVEDAD_BONIFICADO, valor="")]
    )

    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_BONIFICADA


def test_novedad_de_cuota_sobre_persona_bonificada_es_no_aplicable(tmp_path):
    """Una persona bonificada no tiene cuotas que confirmar ni rechazar: la
    novedad de cuota se informa como incoherente, no se descarta."""
    escribir_plan(tmp_path)
    escribir_padron(
        tmp_path,
        filas=(
            ("PRE-001", "Ana Pérez", "ana.perez@example.test", "si"),
        ),
    )
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path, novedades=[novedad()])

    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_BONIFICADA
    assert motivos_error(informe) == {2: MOTIVO_NOVEDAD_NO_APLICABLE}


# --- Bonificación no verificable (D14) ----------------------------------------


def test_bonificacion_no_verificable_sin_columna_y_plan_con_bonificaciones(
    tmp_path,
):
    """D14: el plan tiene bonificaciones y el padrón no informa la condición;
    el recordatorio se arma igual pero la marca queda expuesta."""
    escribir_plan(
        tmp_path,
        filas_extra=(
            (
                "categorias_bonificadas",
                "alumnos FIE|personal FIE",
                "OBSERVADO_DOCUMENTO",
            ),
        ),
    )
    escribir_padron(tmp_path, con_bonificado=False)
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path)

    for s in informe.situaciones:
        assert s.bonificacion_no_verificable is True
        assert s.cuotas[0].estado == ESTADO_PENDIENTE


def test_bonificacion_verificable_cuando_el_padron_informa_la_condicion(
    tmp_path,
):
    escribir_plan(
        tmp_path,
        filas_extra=(
            (
                "categorias_bonificadas",
                "alumnos FIE|personal FIE",
                "OBSERVADO_DOCUMENTO",
            ),
        ),
    )
    escribir_padron(tmp_path)  # con columna bonificado informada
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path)

    for s in informe.situaciones:
        assert s.bonificacion_no_verificable is False


def test_sin_bonificaciones_en_el_plan_no_hay_nada_que_verificar(tmp_path):
    escribir_plan(tmp_path)  # sin categorias_bonificadas
    escribir_padron(tmp_path, con_bonificado=False)
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path)

    for s in informe.situaciones:
        assert s.bonificacion_no_verificable is False


# --- Errores de la novedad: informados, nunca aplicados ni ignorados ----------


def test_inscripcion_inexistente_se_informa_como_error(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(
        tmp_path, novedades=[novedad(id_inscripcion="PRE-INEXISTENTE")]
    )

    assert motivos_error(informe) == {2: MOTIVO_NOVEDAD_INSCRIPCION_DESCONOCIDA}
    assert informe.novedades_aplicadas == ()
    for s in informe.situaciones:
        assert s.cuotas[0].estado == ESTADO_PENDIENTE


def test_tipo_desconocido_se_informa_como_error(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path, novedades=[novedad(tipo="PAGO_RECIBIDO")])

    assert motivos_error(informe) == {2: MOTIVO_NOVEDAD_TIPO_DESCONOCIDO}
    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_PENDIENTE


@pytest.mark.parametrize("valor", ["", "tres", "0", "2", "-1"])
def test_valor_de_cuota_fuera_de_forma_se_informa_como_error(tmp_path, valor):
    escribir_plan(tmp_path)  # una sola cuota: sólo el valor "1" es válido
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path, novedades=[novedad(valor=valor)])

    assert motivos_error(informe) == {2: MOTIVO_NOVEDAD_VALOR_INVALID}
    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_PENDIENTE


def test_direccion_alternativa_mal_formada_es_valor_invalid(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(
        tmp_path,
        novedades=[novedad(tipo=NOVEDAD_EMAIL_ALTERNATIVO, valor="no-es-email")],
    )

    assert motivos_error(informe) == {2: MOTIVO_NOVEDAD_VALOR_INVALID}


def test_bonificado_con_valor_es_valor_invalid(tmp_path):
    """BONIFICADO no consume valor: un valor cargado delata una fila mal
    armada y se informa en lugar de ignorarse."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(
        tmp_path, novedades=[novedad(tipo=NOVEDAD_BONIFICADO, valor="100%")]
    )

    assert motivos_error(informe) == {2: MOTIVO_NOVEDAD_VALOR_INVALID}
    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_PENDIENTE


@pytest.mark.parametrize(
    "campo_roto",
    [
        {"id_inscripcion": ""},
        {"fecha": "ayer"},
        {"fecha": ""},
        {"responsable": ""},
    ],
    ids=["id_vacio", "fecha_texto", "fecha_vacia", "responsable_vacio"],
)
def test_dato_estructural_invalido_se_informa_como_error(tmp_path, campo_roto):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path, novedades=[novedad(**campo_roto)])

    assert motivos_error(informe) == {2: MOTIVO_NOVEDAD_DATO_INVALID}


def test_una_novedad_con_error_no_frena_a_la_siguiente(tmp_path):
    """Cada novedad se juzga por su cuenta: la inválida se informa y la
    válida de otra persona se aplica igual."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(
        tmp_path,
        novedades=[
            novedad(id_inscripcion="PRE-INEXISTENTE", fila=2),
            novedad(id_inscripcion="PRE-002", fila=3),
        ],
    )

    assert motivos_error(informe) == {2: MOTIVO_NOVEDAD_INSCRIPCION_DESCONOCIDA}
    assert [n.id_inscripcion for n in informe.novedades_aplicadas] == ["PRE-002"]
    assert situacion(informe, "PRE-002").cuotas[0].estado == (
        ESTADO_PAGO_CONFIRMADO
    )


def test_las_novedades_entran_al_informe_con_su_trazabilidad(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(
        tmp_path,
        novedades=[
            novedad(fila=2, responsable="Dep. Cursos"),
            novedad(tipo="INVENTADO", fila=3, responsable="Dep. Cursos"),
        ],
    )

    aplicada = informe.novedades_aplicadas[0]
    assert aplicada.fila == 2
    assert aplicada.fecha == "2026-09-21"
    assert aplicada.responsable == "Dep. Cursos"
    error = informe.novedades_con_error[0]
    assert error.novedad.fila == 3
    assert error.motivo == MOTIVO_NOVEDAD_TIPO_DESCONOCIDO


def test_orden_del_archivo_dentro_de_la_persona_la_ultima_gana(tmp_path):
    """Dos novedades sobre la misma cuota se aplican en orden de archivo:
    la confirmación primero y la extensión del comprobante después dejan a la
    cuota 2 en comprobante presentado, no confirmada."""
    escribir_plan(
        tmp_path,
        filas_extra=(
            ("cantidad_cuotas", "2", "SUPUESTO_TECNICO"),
            ("cuota_2_monto", "20000", "SUPUESTO_TECNICO"),
            ("cuota_2_vencimiento", "", "DESCONOCIDO"),
        ),
    )
    escribir_padron(tmp_path)
    buzon_con_comprobante(tmp_path)

    informe = corrida(
        tmp_path,
        novedades=[
            novedad(valor="2", fila=2),
            novedad(tipo=NOVEDAD_COMPROBANTE_CUBRE_N_CUOTAS, valor="2", fila=3),
        ],
    )

    ana = situacion(informe, "PRE-001")
    assert [c.estado for c in ana.cuotas] == [
        ESTADO_COMPROBANTE_PRESENTADO,
        ESTADO_COMPROBANTE_PRESENTADO,
    ]


def test_la_corrida_sin_novedades_se_comporta_como_antes(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon_con_comprobante(tmp_path)

    informe = corrida(tmp_path)

    assert situacion(informe, "PRE-001").cuotas[0].estado == (
        ESTADO_COMPROBANTE_PRESENTADO
    )
    assert informe.novedades_aplicadas == ()
    assert informe.novedades_con_error == ()


def test_la_corrida_con_novedades_es_determinista(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon_con_comprobante(tmp_path)
    novedades = [
        novedad(fila=2),
        novedad(tipo="INVENTADO", fila=3),
    ]

    assert corrida(tmp_path, novedades=novedades) == corrida(
        tmp_path, novedades=novedades
    )


# --- Loader del CSV -----------------------------------------------------------


def test_cargar_novedades_csv_devuelve_las_filas_con_su_numero(tmp_path):
    escribir_novedades(
        tmp_path,
        [
            ("PRE-001", "CONFIRMADO_FUNDACION", "1", "2026-09-21", "Dep."),
            ("PRE-002", "EMAIL_ALTERNATIVO", "b@example.test", "2026-09-22", "Dep."),
        ],
    )

    novedades = cargar_novedades_csv(tmp_path / "novedades.csv")

    assert [n.fila for n in novedades] == [2, 3]
    assert novedades[0].tipo == NOVEDAD_CONFIRMADO_FUNDACION
    assert novedades[1].valor == "b@example.test"


def test_novedades_con_encabezado_equivocado_se_rechaza_entero(tmp_path):
    ruta = tmp_path / "novedades.csv"
    ruta.write_text(
        "tipo,id_inscripcion,valor,fecha,responsable\n"
        "CONFIRMADO_FUNDACION,PRE-001,1,2026-09-21,Dep.\n",
        encoding="utf-8",
    )

    with pytest.raises(ControlPagosError) as excinfo:
        cargar_novedades_csv(ruta)
    assert excinfo.value.code == "novedades_encabezado_invalid"


def test_novedades_con_columna_desconocida_se_rechaza_entero(tmp_path):
    ruta = tmp_path / "novedades.csv"
    ruta.write_text(
        "id_inscripcion,tipo,valor,fecha,responsable,extra\n"
        "PRE-001,CONFIRMADO_FUNDACION,1,2026-09-21,Dep.,x\n",
        encoding="utf-8",
    )

    with pytest.raises(ControlPagosError) as excinfo:
        cargar_novedades_csv(ruta)
    assert excinfo.value.code == "novedades_encabezado_invalid"


def test_novedades_con_fila_desalineada_se_rechaza_entero(tmp_path):
    ruta = tmp_path / "novedades.csv"
    ruta.write_text(
        "id_inscripcion,tipo,valor,fecha,responsable\n"
        "PRE-001,CONFIRMADO_FUNDACION,1\n",
        encoding="utf-8",
    )

    with pytest.raises(ControlPagosError) as excinfo:
        cargar_novedades_csv(ruta)
    assert excinfo.value.code == "novedades_fila_invalid"


def test_novedades_desde_csv_atravesando_el_loader(tmp_path):
    """El camino completo de la fuente: CSV → loader → corrida."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()
    escribir_novedades(
        tmp_path,
        [
            ("PRE-001", "CONFIRMADO_FUNDACION", "1", "2026-09-21", "Dep."),
            ("PRE-9", "CONFIRMADO_FUNDACION", "1", "2026-09-21", "Dep."),
        ],
    )

    plan = cargar_plan_pagos_csv(tmp_path / "plan.csv")
    padron = cargar_padron_csv(
        tmp_path / "padron.csv", actividad_id=plan.actividad_id
    )
    informe = correr_control_pagos(
        plan=plan,
        padron=padron,
        buzon=BuzonPropioEml(tmp_path / "buzon"),
        hoy=HOY,
        novedades=cargar_novedades_csv(tmp_path / "novedades.csv"),
    )

    assert situacion(informe, "PRE-001").cuotas[0].estado == (
        ESTADO_PAGO_CONFIRMADO
    )
    assert motivos_error(informe) == {3: MOTIVO_NOVEDAD_INSCRIPCION_DESCONOCIDA}
