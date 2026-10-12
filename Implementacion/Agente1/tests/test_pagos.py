"""HU-012 pagos: corrida de control sobre una carpeta `.eml`.

Estas pruebas ejercitan la única interfaz pública de la corrida —
`correr_control_pagos` — con el plan de pago en CSV, el padrón en CSV y un
buzón de archivos `.eml` en un directorio temporal: asociación por asunto
normalizado y remitente único, comprobante presentado por adjunto PDF o
imagen, deduplicación por sha256, asignación cronológica a cuotas, respuestas
no asociadas con su motivo, cuotas bonificadas, el fallback de la fecha de
referencia y la bandera `vencida` según el `hoy` explícito. También fijan el
contrato `plan_pagos_actividad_v1`, la procedencia por dato del fixture
NotebookLM Nivel 2 y que ningún contenido de cuerpos o adjuntos llega a la
salida (ADR 0001).
"""

import csv
from datetime import date, datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime
import hashlib
import json
from pathlib import Path

import pytest

from agente1.buzon import (
    AdjuntoMensaje,
    BuzonPropioEml,
    BuzonPropioError,
    BuzonPropioMemoria,
    MensajeBuzon,
)
from agente1.cli_pagos import informe_a_dict
from agente1.pagos import (
    CAMPOS_ACTIVIDAD,
    CONTRACT_VERSION,
    CONTRATO_PLAN,
    ESTADO_BONIFICADA,
    ESTADO_COMPROBANTE_PRESENTADO,
    ESTADO_PAGO_CONFIRMADO,
    ESTADO_PENDIENTE,
    MOTIVOS_NO_ASOCIADA,
    MOTIVO_ASUNTO_NO_COINCIDE,
    MOTIVO_REMITENTE_AMBIGUO,
    MOTIVO_REMITENTE_NO_INFORMADO,
    MOTIVO_REMITENTE_SIN_COINCIDENCIA,
    PROCEDENCIAS_DATO,
    STATUS,
    ControlPagosError,
    cargar_padron_csv,
    cargar_plan_pagos_csv,
    correr_control_pagos,
)


ROOT = Path(__file__).parents[1]
PLAN_NOTEBOOKLM = ROOT / "data" / "plan_pagos_notebooklm_n2.csv"
ACTIVIDAD_ID = "EJEMPLO-NOTEBOOKLM-N2"
ASUNTO = "Pre-Inscripción NotebookLM Nivel 2"
HOY = date(2026, 9, 22)

PDF_A = b"%PDF-1.4 comprobante A"
PDF_B = b"%PDF-1.4 comprobante B"
PNG_A = b"\x89PNG captura A"


def escribir_eml(
    directorio: Path,
    nombre: str,
    *,
    remitente: str | None = "ana.perez@example.test",
    asunto: str = f"Re: {ASUNTO}",
    message_id: str = "<msg@example.test>",
    fecha: datetime | None = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
    adjuntos: tuple[tuple[str, str, bytes], ...] = (),
    cuerpo: str = "Adjunto el comprobante.",
) -> Path:
    """Arma un `.eml` a mano (D16): respuesta con metadatos controlados."""

    mensaje = EmailMessage()
    if remitente is not None:
        mensaje["From"] = remitente
    mensaje["Subject"] = asunto
    if fecha is not None:
        mensaje["Date"] = format_datetime(fecha)
    mensaje["Message-ID"] = message_id
    mensaje.set_content(cuerpo)
    for nombre_adjunto, tipo, datos in adjuntos:
        principal, subtipo = tipo.split("/")
        mensaje.add_attachment(
            datos, maintype=principal, subtype=subtipo, filename=nombre_adjunto
        )
    ruta = directorio / nombre
    ruta.write_bytes(mensaje.as_bytes())
    return ruta


def escribir_plan(
    directorio: Path, filas_extra: tuple[tuple[str, str, str], ...] = ()
) -> Path:
    """Plan mínimo de una cuota; `filas_extra` extiende o pisa datos."""

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


def corrida(tmp_path: Path, *, hoy: date = HOY, plan_csv=None, padron_csv=None):
    """Carga plan y padrón del directorio y corre contra `buzon/` del mismo."""
    plan_path = plan_csv or tmp_path / "plan.csv"
    padron_path = padron_csv or tmp_path / "padron.csv"
    plan = cargar_plan_pagos_csv(plan_path)
    padron = cargar_padron_csv(padron_path, actividad_id=plan.actividad_id)
    return correr_control_pagos(
        plan=plan,
        padron=padron,
        buzon=BuzonPropioEml(tmp_path / "buzon"),
        hoy=hoy,
    )


def situacion(informe, id_inscripcion):
    return next(
        s for s in informe.situaciones if s.id_inscripcion == id_inscripcion
    )


# --- El contrato y el fixture -------------------------------------------------


def test_el_contrato_del_plan_es_versionado_y_declara_procedencia_por_dato():
    assert CONTRACT_VERSION == "plan_pagos_actividad_v1"
    assert STATUS == "CANDIDATO_PENDIENTE_CONFIRMACION_SEU"
    assert CONTRATO_PLAN["x-hu"] == "HU-012"
    assert CONTRATO_PLAN["x-habilita-envio"] is False
    assert PROCEDENCIAS_DATO == frozenset(
        {"OBSERVADO_DOCUMENTO", "SUPUESTO_TECNICO", "DESCONOCIDO"}
    )
    for grupo in ("campos_actividad", "campos_cuota"):
        for campo, item in CONTRATO_PLAN[grupo].items():
            assert item["procedencia_caso_referencia"] in PROCEDENCIAS_DATO, campo
    assert set(CONTRATO_PLAN["estados_derivados_cuota"]) == {
        ESTADO_BONIFICADA,
        ESTADO_PAGO_CONFIRMADO,
        ESTADO_COMPROBANTE_PRESENTADO,
        ESTADO_PENDIENTE,
    }
    assert set(CONTRATO_PLAN["motivos_no_asociada"]) == MOTIVOS_NO_ASOCIADA


def test_el_fixture_notebooklm_carga_el_caso_documentado():
    plan = cargar_plan_pagos_csv(PLAN_NOTEBOOKLM)

    assert plan.actividad_id == ACTIVIDAD_ID
    assert len(plan.cuotas) == 1
    assert plan.cuotas[0].monto == 20000
    assert plan.cuotas[0].vencimiento is None
    assert set(plan.categorias_bonificadas) == {
        "alumnos FIE",
        "personal FIE",
        "egresados FIE",
    }
    assert set(plan.medios_pago) == {"transferencia", "Mercado Pago"}
    # Sin vencimiento propio, la referencia cae en la fecha límite (29/09).
    assert plan.fecha_referencia(plan.cuotas[0]) == date(2026, 9, 29)
    # Cada dato del fixture declara una procedencia válida.
    assert set(plan.procedencias) >= CAMPOS_ACTIVIDAD | {"cuota_1_monto"}
    assert set(plan.procedencias.values()) <= PROCEDENCIAS_DATO
    assert plan.procedencias["cuota_1_vencimiento"] == "DESCONOCIDO"
    assert plan.procedencias["asunto_preinscripcion"] == "SUPUESTO_TECNICO"


def test_sin_fecha_limite_la_referencia_cae_en_el_inicio(tmp_path):
    escribir_plan(
        tmp_path, filas_extra=(("fecha_limite_inscripcion", "", "DESCONOCIDO"),)
    )
    plan = cargar_plan_pagos_csv(tmp_path / "plan.csv")

    assert plan.fecha_limite_inscripcion is None
    assert plan.fecha_referencia(plan.cuotas[0]) == date(2026, 10, 5)


def test_un_vencimiento_propio_gana_sobre_el_fallback(tmp_path):
    escribir_plan(
        tmp_path, filas_extra=(("cuota_1_vencimiento", "2026-09-25", "OBSERVADO_DOCUMENTO"),)
    )
    plan = cargar_plan_pagos_csv(tmp_path / "plan.csv")

    assert plan.fecha_referencia(plan.cuotas[0]) == date(2026, 9, 25)


# --- Asociación y comprobantes -------------------------------------------------


def test_respuesta_con_pdf_asociada_cuenta_como_comprobante(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "ana.eml",
        remitente="Ana Pérez <ana.perez@example.test>",
        adjuntos=(("comprobante.pdf", "application/pdf", PDF_A),),
    )

    informe = corrida(tmp_path)

    ana = situacion(informe, "PRE-001")
    assert ana.cuotas_cubiertas == 1
    assert informe.situaciones[0].cuotas[0].nro_cuota == 1
    cuota = ana.cuotas[0]
    assert cuota.estado == ESTADO_COMPROBANTE_PRESENTADO
    assert cuota.comprobante is not None
    assert cuota.comprobante.sha256 == hashlib.sha256(PDF_A).hexdigest()
    assert cuota.vencida is False
    bruno = situacion(informe, "PRE-002")
    assert bruno.cuotas_cubiertas == 0
    assert bruno.cuotas[0].estado == ESTADO_PENDIENTE
    assert informe.no_asociadas == ()


def test_una_imagen_tambien_es_comprobante(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "captura.eml",
        adjuntos=(("captura.png", "image/png", PNG_A),),
    )

    informe = corrida(tmp_path)

    assert situacion(informe, "PRE-001").cuotas[0].estado == (
        ESTADO_COMPROBANTE_PRESENTADO
    )


def test_respuesta_asociada_sin_adjunto_no_es_comprobante(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(buzon, "ana.eml")

    informe = corrida(tmp_path)

    ana = situacion(informe, "PRE-001")
    assert ana.cuotas[0].estado == ESTADO_PENDIENTE
    assert ana.cuotas_cubiertas == 0
    # La respuesta se asoció igual: no figura entre las no asociadas.
    assert informe.no_asociadas == ()


def test_adjunto_no_admitido_no_cuenta_como_comprobante(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "ana.eml",
        adjuntos=(("datos.txt", "text/plain", b"hola"),),
    )

    informe = corrida(tmp_path)

    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_PENDIENTE
    assert informe.no_asociadas == ()


def test_la_misma_captura_dos_veces_cuenta_una_sola_vez(tmp_path):
    escribir_plan(
        tmp_path,
        filas_extra=(
            ("cantidad_cuotas", "2", "SUPUESTO_TECNICO"),
            ("cuota_2_monto", "20000", "SUPUESTO_TECNICO"),
            ("cuota_2_vencimiento", "", "DESCONOCIDO"),
        ),
    )
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    # La misma captura en dos envíos más uno distinto: dos comprobantes, no tres.
    escribir_eml(
        buzon,
        "primero.eml",
        message_id="<m1@example.test>",
        fecha=datetime(2026, 9, 18, 10, 0, tzinfo=timezone.utc),
        adjuntos=(("cap.png", "image/png", PNG_A),),
    )
    escribir_eml(
        buzon,
        "segundo.eml",
        message_id="<m2@example.test>",
        fecha=datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc),
        adjuntos=(("cap-reenviada.png", "image/png", PNG_A),),
    )
    escribir_eml(
        buzon,
        "tercero.eml",
        message_id="<m3@example.test>",
        fecha=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
        adjuntos=(("comprobante.pdf", "application/pdf", PDF_B),),
    )

    informe = corrida(tmp_path)

    ana = situacion(informe, "PRE-001")
    assert ana.cuotas_cubiertas == 2
    assert [c.estado for c in ana.cuotas] == [
        ESTADO_COMPROBANTE_PRESENTADO,
        ESTADO_COMPROBANTE_PRESENTADO,
    ]
    # La cuota 1 recibió la aparición más antigua de la captura repetida.
    assert ana.cuotas[0].comprobante.sha256 == hashlib.sha256(PNG_A).hexdigest()
    assert ana.cuotas[0].comprobante.message_id == "m1@example.test"
    assert ana.cuotas[1].comprobante.sha256 == hashlib.sha256(PDF_B).hexdigest()
    assert ana.comprobantes_sin_cuota == ()


def test_comprobantes_distintos_se_asignan_en_orden_cronologico(tmp_path):
    escribir_plan(
        tmp_path,
        filas_extra=(
            ("cantidad_cuotas", "2", "SUPUESTO_TECNICO"),
            ("cuota_2_monto", "20000", "SUPUESTO_TECNICO"),
            ("cuota_2_vencimiento", "", "DESCONOCIDO"),
        ),
    )
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    # El archivo del comprobante más nuevo se lee antes por nombre: el orden
    # lo decide el encabezado Date, no el nombre del archivo.
    escribir_eml(
        buzon,
        "a-mas-nuevo.eml",
        message_id="<nuevo@example.test>",
        fecha=datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc),
        adjuntos=(("b.pdf", "application/pdf", PDF_B),),
    )
    escribir_eml(
        buzon,
        "z-mas-viejo.eml",
        message_id="<viejo@example.test>",
        fecha=datetime(2026, 9, 18, 10, 0, tzinfo=timezone.utc),
        adjuntos=(("a.pdf", "application/pdf", PDF_A),),
    )

    informe = corrida(tmp_path)

    ana = situacion(informe, "PRE-001")
    assert ana.cuotas[0].comprobante.sha256 == hashlib.sha256(PDF_A).hexdigest()
    assert ana.cuotas[1].comprobante.sha256 == hashlib.sha256(PDF_B).hexdigest()


def test_los_comprobantes_que_exceden_las_cuotas_quedan_informados(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "uno.eml",
        message_id="<m1@example.test>",
        fecha=datetime(2026, 9, 18, 10, 0, tzinfo=timezone.utc),
        adjuntos=(("a.pdf", "application/pdf", PDF_A),),
    )
    escribir_eml(
        buzon,
        "dos.eml",
        message_id="<m2@example.test>",
        fecha=datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc),
        adjuntos=(("b.pdf", "application/pdf", PDF_B),),
    )

    informe = corrida(tmp_path)

    ana = situacion(informe, "PRE-001")
    assert ana.cuotas_cubiertas == 1
    assert len(ana.comprobantes_sin_cuota) == 1
    assert ana.comprobantes_sin_cuota[0].sha256 == hashlib.sha256(
        PDF_B
    ).hexdigest()


# --- No asociadas ---------------------------------------------------------------


def test_asunto_distinto_va_a_no_asociadas(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "otra.eml",
        asunto="Re: Consulta por otro curso",
        adjuntos=(("comprobante.pdf", "application/pdf", PDF_A),),
    )

    informe = corrida(tmp_path)

    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_PENDIENTE
    assert len(informe.no_asociadas) == 1
    no_asociada = informe.no_asociadas[0]
    assert no_asociada.motivo == MOTIVO_ASUNTO_NO_COINCIDE
    assert no_asociada.remitente == "ana.perez@example.test"


def test_remitente_desconocido_va_a_no_asociadas(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "desconocido.eml",
        remitente="otra.direccion@example.test",
        adjuntos=(("comprobante.pdf", "application/pdf", PDF_A),),
    )

    informe = corrida(tmp_path)

    assert informe.no_asociadas[0].motivo == MOTIVO_REMITENTE_SIN_COINCIDENCIA
    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_PENDIENTE


def test_remitente_duplicado_en_el_padron_va_a_no_asociadas(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(
        tmp_path,
        filas=(
            ("PRE-001", "Ana Pérez", "compartido@example.test", "no"),
            ("PRE-002", "Bruno García", "compartido@example.test", "no"),
        ),
    )
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "compartido.eml",
        remitente="compartido@example.test",
        adjuntos=(("comprobante.pdf", "application/pdf", PDF_A),),
    )

    informe = corrida(tmp_path)

    assert informe.no_asociadas[0].motivo == MOTIVO_REMITENTE_AMBIGUO
    for s in informe.situaciones:
        assert s.cuotas[0].estado == ESTADO_PENDIENTE


def test_respuesta_sin_remitente_va_a_no_asociadas(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(buzon, "sin-from.eml", remitente=None)

    informe = corrida(tmp_path)

    assert informe.no_asociadas[0].motivo == MOTIVO_REMITENTE_NO_INFORMADO


def test_no_se_asocia_por_nombre_aunque_el_asunto_coincida(tmp_path):
    """El nombre completo en el From no cuenta: sólo la dirección."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "desde-otra.eml",
        remitente="Ana Pérez <otro.correo@example.test>",
        adjuntos=(("comprobante.pdf", "application/pdf", PDF_A),),
    )

    informe = corrida(tmp_path)

    assert informe.no_asociadas[0].motivo == MOTIVO_REMITENTE_SIN_COINCIDENCIA
    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_PENDIENTE


def test_normalizacion_rv_espacios_y_mayusculas(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "rv.eml",
        asunto="RV:   Pre-Inscripción   NotebookLM   Nivel 2",
        adjuntos=(("comprobante.pdf", "application/pdf", PDF_A),),
    )
    escribir_eml(
        buzon,
        "re-mayus.eml",
        remitente="bruno.garcia@example.test",
        asunto="RE: PRE-INSCRIPCIÓN NOTEBOOKLM NIVEL 2",
        adjuntos=(("comprobante.pdf", "application/pdf", PDF_B),),
    )

    informe = corrida(tmp_path)

    assert situacion(informe, "PRE-001").cuotas_cubiertas == 1
    assert situacion(informe, "PRE-002").cuotas_cubiertas == 1
    assert informe.no_asociadas == ()


# --- Estados derivados ------------------------------------------------------------


def test_pendiente_con_hoy_pasada_la_referencia_marca_vencida(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()

    informe = corrida(tmp_path, hoy=date(2026, 9, 30))

    assert situacion(informe, "PRE-001").cuotas[0].vencida is True


@pytest.mark.parametrize("hoy", [date(2026, 9, 22), date(2026, 9, 29)])
def test_pendiente_hasta_la_referencia_inclusive_no_es_vencida(tmp_path, hoy):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path, hoy=hoy)

    assert situacion(informe, "PRE-001").cuotas[0].vencida is False


def test_comprobante_presentado_nunca_marca_vencida(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "ana.eml",
        adjuntos=(("comprobante.pdf", "application/pdf", PDF_A),),
    )

    informe = corrida(tmp_path, hoy=date(2026, 10, 10))

    cuota = situacion(informe, "PRE-001").cuotas[0]
    assert cuota.estado == ESTADO_COMPROBANTE_PRESENTADO
    assert cuota.vencida is False


def test_preinscripto_bonificado_marca_cuotas_bonificadas(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(
        tmp_path,
        filas=(
            ("PRE-001", "Ana Pérez", "ana.perez@example.test", "si"),
            ("PRE-002", "Bruno García", "bruno.garcia@example.test", "no"),
        ),
    )
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    # Un bonificado que igual manda comprobante: queda informado sin cuota.
    escribir_eml(
        buzon,
        "ana.eml",
        adjuntos=(("comprobante.pdf", "application/pdf", PDF_A),),
    )

    informe = corrida(tmp_path, hoy=date(2026, 10, 10))

    ana = situacion(informe, "PRE-001")
    assert ana.cuotas[0].estado == ESTADO_BONIFICADA
    assert ana.cuotas_cubiertas == 1
    assert len(ana.comprobantes_sin_cuota) == 1
    assert situacion(informe, "PRE-002").cuotas[0].vencida is True


def test_columna_bonificado_ausente_no_marca_bonificada(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path, con_bonificado=False)
    (tmp_path / "buzon").mkdir()

    informe = corrida(tmp_path)

    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_PENDIENTE


def test_la_corrida_es_determinista_sobre_las_mismas_fuentes(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "ana.eml",
        adjuntos=(("comprobante.pdf", "application/pdf", PDF_A),),
    )

    assert corrida(tmp_path) == corrida(tmp_path)


def test_nada_del_cuerpo_ni_del_adjunto_llega_al_informe(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    escribir_eml(
        buzon,
        "ana.eml",
        cuerpo="CUERPO-SECRETO-QUE-NO-DEBE-SALIR",
        adjuntos=(("comprobante.pdf", "application/pdf", b"ADJUNTO-SECRETO"),),
    )

    informe = corrida(tmp_path)
    serializado = json.dumps(informe_a_dict(informe), ensure_ascii=False)

    assert "CUERPO-SECRETO-QUE-NO-DEBE-SALIR" not in serializado
    assert "ADJUNTO-SECRETO" not in serializado


# --- Fuentes: plan y padrón -------------------------------------------------------


def test_plan_con_campo_desconocido_se_rechaza(tmp_path):
    escribir_plan(
        tmp_path, filas_extra=(("campo_inventado", "x", "SUPUESTO_TECNICO"),)
    )
    with pytest.raises(ControlPagosError) as excinfo:
        cargar_plan_pagos_csv(tmp_path / "plan.csv")
    assert excinfo.value.code == "plan_campo_desconocido"


def test_plan_con_procedencia_fuera_de_vocabulario_se_rechaza(tmp_path):
    escribir_plan(
        tmp_path,
        filas_extra=(("fecha_inicio", "2026-10-05", "INVENTADA"),),
    )
    with pytest.raises(ControlPagosError) as excinfo:
        cargar_plan_pagos_csv(tmp_path / "plan.csv")
    assert excinfo.value.code == "plan_procedencia_invalid"


def test_plan_con_cuota_fuera_de_secuencia_se_rechaza(tmp_path):
    escribir_plan(
        tmp_path,
        filas_extra=(
            ("cantidad_cuotas", "2", "SUPUESTO_TECNICO"),
            ("cuota_2_monto", "20000", "SUPUESTO_TECNICO"),
            ("cuota_3_monto", "20000", "SUPUESTO_TECNICO"),
        ),
    )
    with pytest.raises(ControlPagosError) as excinfo:
        cargar_plan_pagos_csv(tmp_path / "plan.csv")
    assert excinfo.value.code == "plan_cuotas_inconsistentes"


def test_plan_sin_dato_obligatorio_se_rechaza(tmp_path):
    escribir_plan(
        tmp_path, filas_extra=(("fecha_inicio", "", "DESCONOCIDO"),)
    )
    with pytest.raises(ControlPagosError) as excinfo:
        cargar_plan_pagos_csv(tmp_path / "plan.csv")
    assert excinfo.value.code == "plan_dato_obligatorio_ausente"


def test_padron_de_otra_actividad_se_rechaza(tmp_path):
    ruta = tmp_path / "padron.csv"
    ruta.write_text(
        "id_inscripcion,actividad_id,nombre_destinatario,email_destinatario\n"
        "PRE-001,OTRA-ACTIVIDAD,Ana,ana@example.test\n",
        encoding="utf-8",
    )
    with pytest.raises(ControlPagosError) as excinfo:
        cargar_padron_csv(ruta, actividad_id=ACTIVIDAD_ID)
    assert excinfo.value.code == "padron_actividad_distinta"


def test_padron_con_id_duplicado_se_rechaza(tmp_path):
    escribir_padron(
        tmp_path,
        filas=(
            ("PRE-001", "Ana Pérez", "ana@example.test", "no"),
            ("PRE-001", "Otra Ana", "otra.ana@example.test", "no"),
        ),
    )
    with pytest.raises(ControlPagosError) as excinfo:
        cargar_padron_csv(tmp_path / "padron.csv", actividad_id=ACTIVIDAD_ID)
    assert excinfo.value.code == "padron_id_duplicado"


def test_la_corrida_acepta_cualquier_implementacion_del_puerto(tmp_path):
    """`BuzonPropioMemoria` corre por la misma interfaz: el adapter Gmail
    futuro entrará por el mismo lugar sin tocar la corrida."""
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    plan = cargar_plan_pagos_csv(tmp_path / "plan.csv")
    padron = cargar_padron_csv(
        tmp_path / "padron.csv", actividad_id=ACTIVIDAD_ID
    )
    buzon = BuzonPropioMemoria(
        [
            MensajeBuzon(
                remitente="ana.perez@example.test",
                asunto=f"Re: {ASUNTO}",
                fecha=None,
                message_id="m1",
                adjuntos=(
                    AdjuntoMensaje(
                        tipo="application/pdf",
                        sha256=hashlib.sha256(PDF_A).hexdigest(),
                        nombre="comprobante.pdf",
                    ),
                ),
            )
        ]
    )

    informe = correr_control_pagos(
        plan=plan, padron=padron, buzon=buzon, hoy=HOY
    )

    assert situacion(informe, "PRE-001").cuotas[0].estado == (
        ESTADO_COMPROBANTE_PRESENTADO
    )


def test_buzon_inexistente_se_rechaza_con_codigo(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)

    with pytest.raises(BuzonPropioError) as excinfo:
        corrida(tmp_path)
    assert excinfo.value.code == "buzon_no_encontrado"


def test_archivos_que_no_son_eml_se_ignoran(tmp_path):
    escribir_plan(tmp_path)
    escribir_padron(tmp_path)
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    (buzon / "nota.txt").write_text("no es un mensaje", encoding="utf-8")
    (buzon / "adjunto.pdf").write_bytes(PDF_A)

    informe = corrida(tmp_path)

    assert informe.no_asociadas == ()
    assert situacion(informe, "PRE-001").cuotas[0].estado == ESTADO_PENDIENTE
