"""HU-012 pagos: lote diario de `recordatorio_pago` y su circuito (D3, §5).

Estas pruebas cubren las dos mitades del ticket. La planificación pura en
`pagos.py`: la regla de anticipación `[7, 2]` por omisión y configurable,
la zona horaria de la corrida, la fecha de referencia y el nunca-después,
los estados que evitan el recordatorio (comprobante, pago confirmado,
bonificación), la marca `bonificacion_no_verificable` y la clave de
idempotencia por actividad, inscripción, cuota y anticipación. El circuito
por lote en `recordatorios.py`: la plantilla aprobada una sola vez con
doble decisión, la aprobación utilitaria del lote con su lista exacta de
ítems, el encolado sobre el registro y la cola de HU-012, la entrega sólo
contra el fake y la auditoría sin links, datos bancarios ni datos
personales en claro.
"""

import csv
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime
import json
from pathlib import Path

import pytest

from agente1.buzon import BuzonPropioEml
from agente1.cli_pagos import informe_a_dict
from agente1.confirmaciones import (
    AprobacionHumana,
    CLAVE_REGISTRO_RE,
    ColaEnviosMemoria,
    DestinoConfirmacionesFake,
    RegistroConfirmacionesMemoria,
    ROL_APROBACION_SEMANTICA,
    ROL_APROBACION_UTILITARIA,
    drenar_envios,
)
from agente1.pagos import (
    ANTICIPACIONES_DEFAULT,
    ControlPagosError,
    NovedadPago,
    TIPO_RECORDATORIO_PAGO,
    cargar_novedades_csv,
    cargar_padron_csv,
    cargar_plan_pagos_csv,
    clave_item_recordatorio,
    correr_control_pagos,
    fecha_de_corrida,
    planificar_recordatorios,
)
from agente1.recordatorios import (
    CLAVE_PLANTILLA_RECORDATORIO,
    TEMPLATE_VERSION,
    AprobacionLote,
    aprobar_plantilla_recordatorio,
    correr_lote_recordatorios,
    encolar_lote_recordatorios,
    registrar_plantilla_recordatorio,
    renderizar_recordatorio,
)


ACTIVIDAD_ID = "EJEMPLO-LOTE"
ASUNTO = "Pre-Inscripción Curso de prueba"
REFERENCIA = date(2026, 9, 29)  # fecha_limite_inscripcion del plan de prueba
PDF_A = b"%PDF-1.4 comprobante A"


def escribir_plan(
    directorio: Path, filas_extra: tuple[tuple[str, str, str], ...] = ()
) -> Path:
    """Plan mínimo de una cuota con referencia en 2026-09-29."""

    filas = [
        ("actividad_id", ACTIVIDAD_ID, "SUPUESTO_TECNICO"),
        ("actividad", "Curso sintético", "OBSERVADO_DOCUMENTO"),
        ("asunto_preinscripcion", ASUNTO, "SUPUESTO_TECNICO"),
        ("fecha_inicio", "2026-10-05", "OBSERVADO_DOCUMENTO"),
        ("fecha_limite_inscripcion", "2026-09-29", "OBSERVADO_DOCUMENTO"),
        ("cantidad_cuotas", "1", "OBSERVADO_DOCUMENTO"),
        ("cuota_1_monto", "20000", "OBSERVADO_DOCUMENTO"),
        ("cuota_1_vencimiento", "", "DESCONOCIDO"),
    ]
    for campo, valor, procedencia in filas_extra:
        filas = [fila for fila in filas if fila[0] != campo]
        filas.append((campo, valor, procedencia))
    ruta = directorio / "plan.csv"
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.writer(archivo)
        writer.writerow(["campo", "valor", "procedencia", "evidencia"])
        writer.writerows([(*fila, "") for fila in filas])
    return ruta


def escribir_padron(
    directorio: Path,
    filas: tuple[tuple[str, str, str, str], ...] | None = None,
    *,
    con_bonificado: bool = True,
) -> Path:
    """Padrón de la actividad. Cada fila: id, nombre, email, bonificado."""

    if filas is None:
        filas = (
            ("PRE-001", "Ana Pérez", "ana.perez@example.test", "no"),
            ("PRE-002", "Bruno García", "bruno.garcia@example.test", "no"),
        )
    ruta = directorio / "padron.csv"
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.writer(archivo)
        columnas = [
            "id_inscripcion",
            "actividad_id",
            "nombre_destinatario",
            "email_destinatario",
        ]
        if con_bonificado:
            columnas.append("bonificado")
        writer.writerow(columnas)
        for id_inscripcion, nombre, email, bonificado in filas:
            fila = [id_inscripcion, ACTIVIDAD_ID, nombre, email]
            if con_bonificado:
                fila.append(bonificado)
            writer.writerow(fila)
    return ruta


def escribir_eml(directorio: Path, nombre: str) -> Path:
    """Un `.eml` de Ana con un PDF: comprobante presentado."""

    mensaje = EmailMessage()
    mensaje["From"] = "ana.perez@example.test"
    mensaje["Subject"] = f"Re: {ASUNTO}"
    mensaje["Date"] = format_datetime(
        datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)
    )
    mensaje["Message-ID"] = f"<{nombre}@example.test>"
    mensaje.set_content("Adjunto el comprobante.")
    mensaje.add_attachment(
        PDF_A, maintype="application", subtype="pdf", filename="comprobante.pdf"
    )
    ruta = directorio / nombre
    ruta.write_bytes(mensaje.as_bytes())
    return ruta


def cargar_plan(tmp_path: Path):
    return cargar_plan_pagos_csv(tmp_path / "plan.csv")


def corrida(tmp_path: Path, *, hoy: date, novedades=None):
    plan = cargar_plan(tmp_path)
    padron = cargar_padron_csv(
        tmp_path / "padron.csv", actividad_id=plan.actividad_id
    )
    return correr_control_pagos(
        plan=plan,
        padron=padron,
        buzon=BuzonPropioEml(tmp_path / "buzon"),
        hoy=hoy,
        novedades=novedades or [],
    )


def armar_lote(tmp_path: Path, *, hoy: date = date(2026, 9, 22)):
    """Plan, padrón y corrida mínimos que dejan un lote de dos ítems."""

    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()
    plan = cargar_plan(tmp_path)
    informe = corrida(tmp_path, hoy=hoy)
    return plan, informe.recordatorios


def aprobacion(*, aprobada: bool = True, rol: str) -> AprobacionHumana:
    return AprobacionHumana(
        aprobada=aprobada,
        validador="Validador SEU de prueba",
        rol=rol,
        fecha_iso="2026-09-22T10:00:00-03:00",
    )


def semantica(**kwargs) -> AprobacionHumana:
    return aprobacion(rol=ROL_APROBACION_SEMANTICA, **kwargs)


def utilitaria(**kwargs) -> AprobacionHumana:
    return aprobacion(rol=ROL_APROBACION_UTILITARIA, **kwargs)


def aprobacion_lote(lote, **kwargs) -> AprobacionLote:
    return AprobacionLote(
        aprobacion=utilitaria(**kwargs),
        items=tuple(item.idempotency_key for item in lote.items),
    )


def aprobar_plantilla(registro, directorio) -> None:
    registrar_plantilla_recordatorio(
        registro=registro, directorio_salida=directorio
    )
    aprobar_plantilla_recordatorio(
        registro=registro,
        directorio_salida=directorio,
        aprobacion=semantica(),
    )
    aprobar_plantilla_recordatorio(
        registro=registro,
        directorio_salida=directorio,
        aprobacion=utilitaria(),
    )


# --- Planificación: anticipaciones y fecha ----------------------------------


def test_el_default_es_siete_y_dos_dias_antes(tmp_path):
    assert ANTICIPACIONES_DEFAULT == (7, 2)
    _, lote = armar_lote(tmp_path, hoy=REFERENCIA - timedelta(days=7))

    assert {item.anticipacion_d for item in lote.items} == {7}
    assert {item.nro_cuota for item in lote.items} == {1}
    assert {item.id_inscripcion for item in lote.items} == {"PRE-001", "PRE-002"}

    lote_dos = corrida(tmp_path, hoy=REFERENCIA - timedelta(days=2)).recordatorios
    assert {item.anticipacion_d for item in lote_dos.items} == {2}


def test_un_dia_sin_anticipacion_no_planifica(tmp_path):
    _, lote = armar_lote(tmp_path, hoy=REFERENCIA - timedelta(days=5))
    assert lote.items == ()


def test_las_anticipaciones_son_configurables_por_actividad(tmp_path):
    escribir_plan(tmp_path, filas_extra=(("anticipaciones", "3|1", "SUPUESTO_TECNICO"),))
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()
    plan = cargar_plan(tmp_path)

    assert plan.anticipaciones == (3, 1)
    lote = corrida(tmp_path, hoy=REFERENCIA - timedelta(days=3)).recordatorios
    assert {item.anticipacion_d for item in lote.items} == {3}
    lote = corrida(tmp_path, hoy=REFERENCIA - timedelta(days=1)).recordatorios
    assert {item.anticipacion_d for item in lote.items} == {1}
    # Con otra lista, el default ya no aplica.
    lote = corrida(tmp_path, hoy=REFERENCIA - timedelta(days=7)).recordatorios
    assert lote.items == ()


def test_anticipacion_cero_recuerda_el_dia_de_la_referencia(tmp_path):
    escribir_plan(tmp_path, filas_extra=(("anticipaciones", "0", "SUPUESTO_TECNICO"),))
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    lote = corrida(tmp_path, hoy=REFERENCIA).recordatorios
    assert {item.anticipacion_d for item in lote.items} == {0}


def test_nunca_hay_recordatorio_despues_de_la_referencia(tmp_path):
    escribir_plan(tmp_path, filas_extra=(("anticipaciones", "0|3", "SUPUESTO_TECNICO"),))
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path, hoy=REFERENCIA + timedelta(days=1))
    ana = next(s for s in informe.situaciones if s.id_inscripcion == "PRE-001")
    assert ana.cuotas[0].vencida is True
    assert informe.recordatorios.items == ()


def test_anticipaciones_invalidas_se_rechazan(tmp_path):
    for valor in ("abc", "-1", "3|"):
        escribir_plan(
            tmp_path, filas_extra=(("anticipaciones", valor, "SUPUESTO_TECNICO"),)
        )
        with pytest.raises(ControlPagosError) as excinfo:
            cargar_plan(tmp_path)
        assert excinfo.value.code == "plan_valor_invalid"


def test_anticipaciones_vacias_dan_el_default(tmp_path):
    escribir_plan(tmp_path, filas_extra=(("anticipaciones", "", "SUPUESTO_TECNICO"),))
    plan = cargar_plan(tmp_path)
    assert plan.anticipaciones == ANTICIPACIONES_DEFAULT


def test_el_dia_de_la_corrida_es_el_de_buenos_aires():
    """El «día» se fija en America/Argentina/Buenos_Aires: un instante UTC
    puede ser ya el día siguiente en UTC y todavía el anterior en BA."""
    instante = datetime(2026, 9, 23, 1, 30, tzinfo=timezone.utc)
    assert fecha_de_corrida(instante) == date(2026, 9, 22)
    # Un datetime naive se interpreta como UTC: la función nunca lee la
    # zona del host.
    assert fecha_de_corrida(datetime(2026, 9, 23, 1, 30)) == date(2026, 9, 22)


# --- Planificación: estados que evitan el recordatorio ------------------------


def test_comprobante_presentado_evita_el_recordatorio(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(buzon, "ana.eml")

    lote = corrida(tmp_path, hoy=REFERENCIA - timedelta(days=7)).recordatorios

    assert {item.id_inscripcion for item in lote.items} == {"PRE-002"}


def test_pago_confirmado_evita_el_recordatorio(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()
    novedades = [
        NovedadPago(
            id_inscripcion="PRE-001",
            tipo="CONFIRMADO_FUNDACION",
            valor="1",
            fecha="2026-09-21",
            responsable="Departamento",
            fila=2,
        )
    ]

    lote = corrida(
        tmp_path, hoy=REFERENCIA - timedelta(days=7), novedades=novedades
    ).recordatorios

    assert {item.id_inscripcion for item in lote.items} == {"PRE-002"}


def test_bonificada_evita_el_recordatorio(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(
        tmp_path,
        filas=(
            ("PRE-001", "Ana Pérez", "ana.perez@example.test", "si"),
            ("PRE-002", "Bruno García", "bruno.garcia@example.test", "no"),
        ),
    )
    (tmp_path / "buzon").mkdir()

    lote = corrida(tmp_path, hoy=REFERENCIA - timedelta(days=7)).recordatorios

    assert {item.id_inscripcion for item in lote.items} == {"PRE-002"}


def test_bonificacion_no_verificable_entra_al_lote_marcada(tmp_path):
    """D14: el plan declara bonificados y el padrón no puede acreditar la
    condición — el ítem se planifica igual y queda marcado."""
    escribir_plan(
        tmp_path,
        filas_extra=(
            ("categorias_bonificadas", "alumnos FIE", "OBSERVADO_DOCUMENTO"),
        ),
    )
    escribir_padron(tmp_path, con_bonificado=False)
    (tmp_path / "buzon").mkdir()

    lote = corrida(tmp_path, hoy=REFERENCIA - timedelta(days=7)).recordatorios

    assert len(lote.items) == 2
    assert all(item.bonificacion_no_verificable for item in lote.items)


def test_sin_bonificados_en_el_plan_no_hay_marca(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path, con_bonificado=False)
    (tmp_path / "buzon").mkdir()

    lote = corrida(tmp_path, hoy=REFERENCIA - timedelta(days=7)).recordatorios

    assert all(not item.bonificacion_no_verificable for item in lote.items)


# --- Planificación: claves de idempotencia ------------------------------------


def test_la_clave_deriva_de_actividad_inscripcion_cuota_y_anticipacion():
    clave = clave_item_recordatorio(
        actividad_id=ACTIVIDAD_ID,
        id_inscripcion="PRE-001",
        nro_cuota=1,
        anticipacion_d=7,
    )
    assert CLAVE_REGISTRO_RE.fullmatch(clave)
    # Estable: mismos componentes, misma clave.
    assert clave == clave_item_recordatorio(
        actividad_id=ACTIVIDAD_ID,
        id_inscripcion="PRE-001",
        nro_cuota=1,
        anticipacion_d=7,
    )
    # Cada componente distingue la comunicación.
    for distinta in (
        dict(actividad_id="OTRA"),
        dict(id_inscripcion="PRE-999"),
        dict(nro_cuota=2),
        dict(anticipacion_d=2),
    ):
        parametros = dict(
            actividad_id=ACTIVIDAD_ID,
            id_inscripcion="PRE-001",
            nro_cuota=1,
            anticipacion_d=7,
        )
        parametros.update(distinta)
        assert clave_item_recordatorio(**parametros) != clave


def test_repetir_la_corrida_el_mismo_dia_da_el_mismo_lote(tmp_path):
    _, lote = armar_lote(tmp_path, hoy=REFERENCIA - timedelta(days=7))
    lote_de_nuevo = corrida(
        tmp_path, hoy=REFERENCIA - timedelta(days=7)
    ).recordatorios

    assert lote == lote_de_nuevo
    assert lote.clave_lote == lote_de_nuevo.clave_lote


def test_el_informe_serializado_lleva_el_lote_sin_datos_de_pago(tmp_path):
    escribir_plan(
        tmp_path,
        filas_extra=(
            ("medios_pago", "transferencia|MP https://mp.link/pago", "OBSERVADO_DOCUMENTO"),
        ),
    )
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path, hoy=REFERENCIA - timedelta(days=7))
    serializado = json.dumps(informe_a_dict(informe), ensure_ascii=False)
    lote_dict = informe_a_dict(informe)["recordatorios"]

    assert lote_dict["actividad_id"] == ACTIVIDAD_ID
    assert lote_dict["clave_lote"] == informe.recordatorios.clave_lote
    assert len(lote_dict["items"]) == 2
    item_dict = lote_dict["items"][0]
    assert item_dict["nro_cuota"] == 1
    assert item_dict["anticipacion_d"] == 7
    assert item_dict["fecha_referencia"] == "2026-09-29"
    assert CLAVE_REGISTRO_RE.fullmatch(item_dict["idempotency_key"])
    # Los medios de pago del plan — link incluido — no van al informe: se
    # renderizan en el cuerpo del recordatorio dentro del circuito.
    assert "mp.link" not in serializado
    assert "Medios de pago" not in serializado


# --- La plantilla -------------------------------------------------------------


def test_la_plantilla_se_aprueba_una_sola_vez_con_doble_decision(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    salida = tmp_path / "salida"

    registrada = registrar_plantilla_recordatorio(
        registro=registro, directorio_salida=salida
    )
    parcial = aprobar_plantilla_recordatorio(
        registro=registro, directorio_salida=salida, aprobacion=semantica()
    )
    completa = aprobar_plantilla_recordatorio(
        registro=registro, directorio_salida=salida, aprobacion=utilitaria()
    )

    assert registrada.estado == "PENDIENTE_VALIDACION"
    assert parcial.estado == "APROBADA_SEMANTICA"
    assert completa.estado == "APROBADA"
    assert registro.obtener(CLAVE_PLANTILLA_RECORDATORIO).estado == "APROBADA"
    # Ya aprobada, otra decisión no la mueve: la plantilla se aprobó una vez.
    repetida = aprobar_plantilla_recordatorio(
        registro=registro, directorio_salida=salida, aprobacion=semantica()
    )
    assert repetida.estado == "DUPLICADA"


def test_la_plantilla_rechazada_es_terminal(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    salida = tmp_path / "salida"
    rechazada = aprobar_plantilla_recordatorio(
        registro=registro,
        directorio_salida=salida,
        aprobacion=semantica(aprobada=False),
    )
    assert rechazada.estado == "RECHAZADA"

    _, lote = armar_lote(tmp_path)
    resultado = encolar_lote_recordatorios(
        plan=cargar_plan(tmp_path),
        lote=lote,
        aprobacion_lote=aprobacion_lote(lote),
        registro=registro,
        cola=ColaEnviosMemoria(),
        directorio_salida=salida,
    )
    assert resultado.estado == "INVALIDA"
    assert resultado.error == "template_not_approved"


def test_aprobar_plantilla_sin_registrarla_la_materializa(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    resultado = aprobar_plantilla_recordatorio(
        registro=registro,
        directorio_salida=tmp_path / "salida",
        aprobacion=utilitaria(),
    )
    assert resultado.estado == "APROBADA_UTILITARIA"
    assert registro.obtener(CLAVE_PLANTILLA_RECORDATORIO).estado == (
        "APROBADA_UTILITARIA"
    )


def test_decision_invalida_sobre_la_plantilla_es_invalida(tmp_path):
    resultado = aprobar_plantilla_recordatorio(
        registro=RegistroConfirmacionesMemoria(),
        directorio_salida=tmp_path / "salida",
        aprobacion=AprobacionHumana(
            aprobada=True,
            validador="",
            rol=ROL_APROBACION_SEMANTICA,
            fecha_iso="2026-09-22T10:00:00-03:00",
        ),
    )
    assert resultado.estado == "INVALIDA"
    assert resultado.error == "approval_invalid"


# --- El circuito por lote ------------------------------------------------------


def test_lote_sin_plantilla_no_encola_nada(tmp_path):
    plan, lote = armar_lote(tmp_path)
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()

    resultado = encolar_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=aprobacion_lote(lote),
        registro=registro,
        cola=cola,
        directorio_salida=tmp_path / "salida",
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "template_not_approved"
    assert resultado.items == ()
    assert cola.pendientes() == ()
    assert registro.obtener(lote.items[0].idempotency_key) is None


def test_lote_con_plantilla_pendiente_tampoco_encola(tmp_path):
    plan, lote = armar_lote(tmp_path)
    registro = RegistroConfirmacionesMemoria()
    registrar_plantilla_recordatorio(
        registro=registro, directorio_salida=tmp_path / "salida"
    )

    resultado = encolar_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=aprobacion_lote(lote),
        registro=registro,
        cola=ColaEnviosMemoria(),
        directorio_salida=tmp_path / "salida",
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "template_not_approved"


def test_el_lote_aprobado_se_encola_completo(tmp_path):
    plan, lote = armar_lote(tmp_path)
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    salida = tmp_path / "salida"
    aprobar_plantilla(registro, salida)

    resultado = encolar_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=aprobacion_lote(lote),
        registro=registro,
        cola=cola,
        directorio_salida=salida,
    )

    assert resultado.estado == "ENVIO_ENCOLADO"
    assert {item.estado for item in resultado.items} == {"ENVIO_ENCOLADO"}
    assert len(cola.pendientes()) == 2
    for item in lote.items:
        registro_item = registro.obtener(item.idempotency_key)
        assert registro_item.estado == "ENVIO_ENCOLADO"


def test_la_aprobacion_del_lote_es_utilitaria(tmp_path):
    plan, lote = armar_lote(tmp_path)
    registro = RegistroConfirmacionesMemoria()
    aprobar_plantilla(registro, tmp_path / "salida")

    resultado = encolar_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=AprobacionLote(
            aprobacion=semantica(),
            items=tuple(item.idempotency_key for item in lote.items),
        ),
        registro=registro,
        cola=ColaEnviosMemoria(),
        directorio_salida=tmp_path / "salida",
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "approval_invalid"


def test_una_lista_parcial_no_encola_nada(tmp_path):
    plan, lote = armar_lote(tmp_path)
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    aprobar_plantilla(registro, tmp_path / "salida")

    resultado = encolar_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=AprobacionLote(
            aprobacion=utilitaria(), items=(lote.items[0].idempotency_key,)
        ),
        registro=registro,
        cola=cola,
        directorio_salida=tmp_path / "salida",
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "batch_approval_partial"
    assert cola.pendientes() == ()
    assert registro.obtener(lote.items[0].idempotency_key) is None


def test_una_clave_ajena_en_la_lista_invalida_el_lote(tmp_path):
    plan, lote = armar_lote(tmp_path)
    registro = RegistroConfirmacionesMemoria()
    aprobar_plantilla(registro, tmp_path / "salida")
    ajena = clave_item_recordatorio(
        actividad_id=ACTIVIDAD_ID,
        id_inscripcion="PRE-999",
        nro_cuota=1,
        anticipacion_d=7,
    )

    resultado = encolar_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=AprobacionLote(
            aprobacion=utilitaria(),
            items=tuple(item.idempotency_key for item in lote.items) + (ajena,),
        ),
        registro=registro,
        cola=ColaEnviosMemoria(),
        directorio_salida=tmp_path / "salida",
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "batch_item_unknown"


def test_items_mal_formados_o_repetidos_en_la_lista_son_invalidos(tmp_path):
    plan, lote = armar_lote(tmp_path)
    registro = RegistroConfirmacionesMemoria()
    aprobar_plantilla(registro, tmp_path / "salida")
    claves = tuple(item.idempotency_key for item in lote.items)

    for items in (
        ("no-es-una-clave",) + claves[1:],
        claves + (claves[0],),
    ):
        resultado = encolar_lote_recordatorios(
            plan=plan,
            lote=lote,
            aprobacion_lote=AprobacionLote(
                aprobacion=utilitaria(), items=items
            ),
            registro=registro,
            cola=ColaEnviosMemoria(),
            directorio_salida=tmp_path / "salida",
        )
        assert resultado.estado == "INVALIDA", items
        assert resultado.error == "approval_invalid"


def test_un_lote_rechazado_no_encola(tmp_path):
    plan, lote = armar_lote(tmp_path)
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    aprobar_plantilla(registro, tmp_path / "salida")

    resultado = encolar_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=AprobacionLote(
            aprobacion=utilitaria(aprobada=False),
            items=tuple(item.idempotency_key for item in lote.items),
        ),
        registro=registro,
        cola=cola,
        directorio_salida=tmp_path / "salida",
    )

    assert resultado.estado == "RECHAZADA"
    assert cola.pendientes() == ()


def test_el_lote_vacio_no_encola_nada(tmp_path):
    _, lote = armar_lote(tmp_path, hoy=REFERENCIA - timedelta(days=5))
    plan = cargar_plan(tmp_path)
    registro = RegistroConfirmacionesMemoria()
    aprobar_plantilla(registro, tmp_path / "salida")
    assert lote.items == ()

    resultado = encolar_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=AprobacionLote(aprobacion=utilitaria(), items=()),
        registro=registro,
        cola=ColaEnviosMemoria(),
        directorio_salida=tmp_path / "salida",
    )

    assert resultado.estado == "VACIO"


# --- Entrega e idempotencia ----------------------------------------------------


def test_el_lote_encolado_drena_contra_el_fake(tmp_path):
    plan, lote = armar_lote(tmp_path)
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    destino = DestinoConfirmacionesFake()
    salida = tmp_path / "salida"
    aprobar_plantilla(registro, salida)

    resultado_lote, drenajes = correr_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=aprobacion_lote(lote),
        registro=registro,
        cola=cola,
        destino=destino,
        directorio_salida=salida,
    )

    assert resultado_lote.estado == "ENVIO_ENCOLADO"
    assert [r.resolucion for r in drenajes] == ["entregada", "entregada"]
    assert len(destino.entregas) == 2
    por_clave = {e.idempotency_key: e for e in destino.entregas}
    for item in lote.items:
        assert item.idempotency_key in por_clave
        assert registro.obtener(item.idempotency_key).estado == (
            "ENVIADA_SIMULADA"
        )
    entrega = destino.entregas[0]
    assert entrega.asunto == "[BORRADOR — NO ENVIAR] Recordatorio de pago"
    assert "cuota 1" in entrega.cuerpo
    assert "comprobante" in entrega.cuerpo


def test_repetir_el_lote_el_mismo_dia_no_duplica(tmp_path):
    plan, lote = armar_lote(tmp_path)
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    destino = DestinoConfirmacionesFake()
    salida = tmp_path / "salida"
    aprobar_plantilla(registro, salida)
    correr_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=aprobacion_lote(lote),
        registro=registro,
        cola=cola,
        destino=destino,
        directorio_salida=salida,
    )

    segunda = encolar_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=aprobacion_lote(lote),
        registro=registro,
        cola=cola,
        directorio_salida=salida,
    )
    drenajes = drenar_envios(
        registro=registro, cola=cola, destino=destino, directorio_salida=salida
    )

    assert segunda.estado == "DUPLICADA"
    assert {item.estado for item in segunda.items} == {"DUPLICADA"}
    assert drenajes == ()
    assert len(destino.entregas) == 2


def test_sin_destino_habilitado_el_worker_no_entrega(tmp_path):
    """El candado del fake es el mismo del circuito por envío: la cola se
    llena pero ningún destino ajeno puede drenarla."""
    plan, lote = armar_lote(tmp_path)
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    salida = tmp_path / "salida"
    aprobar_plantilla(registro, salida)
    encolar_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=aprobacion_lote(lote),
        registro=registro,
        cola=cola,
        directorio_salida=salida,
    )

    drenajes = drenar_envios(
        registro=registro,
        cola=cola,
        destino=object(),
        directorio_salida=salida,
    )

    assert drenajes == ()
    assert len(cola.pendientes()) == 2


# --- El cuerpo renderizado -----------------------------------------------------


def test_el_render_es_determinista_y_completo(tmp_path):
    plan, lote = armar_lote(tmp_path)
    item = lote.items[0]

    asunto, cuerpo = renderizar_recordatorio(plan=plan, item=item)
    asunto2, cuerpo2 = renderizar_recordatorio(plan=plan, item=item)

    assert (asunto, cuerpo) == (asunto2, cuerpo2)
    assert asunto == "[BORRADOR — NO ENVIAR] Recordatorio de pago"
    assert cuerpo.startswith("BORRADOR — NO ENVIAR")
    assert "Hola Ana Pérez," in cuerpo
    assert "cuota 1" in cuerpo
    assert "20000" in cuerpo
    assert "2026-09-29" in cuerpo
    assert "en 7 días" in cuerpo
    # El plan de prueba no declara medios: el cuerpo lo dice explícito.
    assert "A confirmar por la Secretaría de Extensión" in cuerpo
    assert "Respondé a este correo adjuntando el comprobante." in cuerpo
    assert "plantilla provisional" in cuerpo


def test_los_medios_del_plan_con_links_van_al_cuerpo_no_al_log(tmp_path):
    escribir_plan(
        tmp_path,
        filas_extra=(
            ("medios_pago", "CBU 0000000000000000000001|MP https://mp.link/pago", "OBSERVADO_DOCUMENTO"),
        ),
    )
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()
    plan = cargar_plan(tmp_path)
    lote = corrida(tmp_path, hoy=REFERENCIA - timedelta(days=7)).recordatorios
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    salida = tmp_path / "salida"
    aprobar_plantilla(registro, salida)

    resultado = correr_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=aprobacion_lote(lote),
        registro=registro,
        cola=cola,
        destino=DestinoConfirmacionesFake(),
        directorio_salida=salida,
    )[0]

    cuerpo = registro.obtener(lote.items[0].idempotency_key).cuerpo
    assert "CBU 0000000000000000000001" in cuerpo
    assert "https://mp.link/pago" in cuerpo
    # La auditoría nunca lleva los datos de pago ni al destinatario: sólo
    # hashes. Los dos logs — el del lote y el del drenaje — quedan limpios.
    texto_logs = ""
    for log in (salida / "logs").glob("*.jsonl"):
        texto_logs += log.read_text(encoding="utf-8")
    for sensible in (
        "CBU 0000000000000000000001",
        "mp.link",
        "ana.perez@example.test",
        "Ana Pérez",
        "bruno.garcia@example.test",
    ):
        assert sensible not in texto_logs


def test_la_marca_de_bonificacion_no_verificable_queda_en_auditoria(tmp_path):
    escribir_plan(
        tmp_path,
        filas_extra=(
            ("categorias_bonificadas", "alumnos FIE", "OBSERVADO_DOCUMENTO"),
        ),
    )
    escribir_padron(tmp_path, con_bonificado=False)
    (tmp_path / "buzon").mkdir()
    plan = cargar_plan(tmp_path)
    lote = corrida(tmp_path, hoy=REFERENCIA - timedelta(days=7)).recordatorios
    registro = RegistroConfirmacionesMemoria()
    salida = tmp_path / "salida"
    aprobar_plantilla(registro, salida)

    resultado = encolar_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=aprobacion_lote(lote),
        registro=registro,
        cola=ColaEnviosMemoria(),
        directorio_salida=salida,
    )

    lineas = [
        json.loads(linea)
        for linea in resultado.log_path.read_text(encoding="utf-8").splitlines()
    ]
    encolados = [linea for linea in lineas if linea["evento"] == "encolado_lote"]
    assert len(encolados) == 2
    assert all(
        linea["bonificacion_no_verificable"] is True for linea in encolados
    )
    autorizacion = next(
        linea for linea in lineas if linea["evento"] == "autorizacion_lote"
    )
    assert autorizacion["estado"] == "AUTORIZADA"
    assert autorizacion["items_count"] == 2
    assert sorted(autorizacion["items_aprobados"]) == sorted(
        item.idempotency_key for item in lote.items
    )
    assert autorizacion["approval_role"] == ROL_APROBACION_UTILITARIA
    assert autorizacion["tipo_notificacion"] == "recordatorio_pago"


def test_los_registros_durables_comparten_la_infraestructura(tmp_path):
    """El lote usa el mismo registro archivo-por-clave que el circuito por
    envío: la idempotencia sobrevive al reinicio del proceso."""
    from agente1.confirmaciones import (
        ColaEnviosArchivo,
        RegistroConfirmacionesArchivo,
    )

    plan, lote = armar_lote(tmp_path)
    registro = RegistroConfirmacionesArchivo(tmp_path / "registro")
    cola = ColaEnviosArchivo(tmp_path / "cola")
    salida = tmp_path / "salida"
    aprobar_plantilla(registro, salida)

    resultado = correr_lote_recordatorios(
        plan=plan,
        lote=lote,
        aprobacion_lote=aprobacion_lote(lote),
        registro=registro,
        cola=cola,
        destino=DestinoConfirmacionesFake(),
        directorio_salida=salida,
    )[0]

    assert resultado.estado == "ENVIO_ENCOLADO"
    for item in lote.items:
        assert registro.obtener(item.idempotency_key).estado == (
            "ENVIADA_SIMULADA"
        )


def test_el_tipo_es_el_del_catalogo(tmp_path):
    assert TIPO_RECORDATORIO_PAGO == "recordatorio_pago"
    assert TEMPLATE_VERSION == "recordatorio_pago_provisional_v1"
