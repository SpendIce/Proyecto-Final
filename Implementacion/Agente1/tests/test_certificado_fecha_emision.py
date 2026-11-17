"""El certificado de aprobación se fecha con el mes de emisión, como la SEU.

El PDF institucional de la SEU (17/11/2026) de un taller que terminó en
octubre dice «Ciudad Autónoma de Buenos Aires, noviembre de 2026»: la
fecha es la de la emisión, no la del fin de la actividad. Decisión de
Juani del 17/11/2026.

- Lote aprobado: la fecha es la de la aprobación, en hora argentina, así el
  ZIP sigue siendo determinista.
- Muestra de un lote pendiente: la fecha del día.
"""

from __future__ import annotations

import io
import zipfile
import zlib
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from agente1.certificados_emision import (
    PersonaCierre,
    generar_pdf_certificado_lote,
    generar_pdf_muestra_lote,
)
from agente1.emisiones_certificados import construir_zip_certificados

_ACTIVIDAD = {
    "titulo": "Taller “Prueba de fechado”",
    "duracion_horas": "14",
    "modalidad": "virtual",
    "fecha_inicio": "2026-10-07",
    "fecha_fin": "2026-10-27",
    "organiza": "Facultad de Ingeniería del Ejército",
}

_PERSONA = PersonaCierre(
    nombre="Ana",
    apellido="Prueba",
    dni="30222333",
    mail="ana@example.invalid",
    tratamiento="Sr./Sra.",
    condicion="aprobacion",
)

_ARGENTINA = timezone(timedelta(hours=-3))
_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def _texto(pdf: bytes) -> bytes:
    partes = [pdf]
    pos = 0
    while (ini := pdf.find(b"stream\n", pos)) >= 0:
        ini += len(b"stream\n")
        fin = pdf.find(b"\nendstream", ini)
        try:
            partes.append(zlib.decompress(pdf[ini:fin]))
        except zlib.error:
            pass
        pos = fin
    return b"\n".join(partes)


def test_el_certificado_lleva_el_mes_de_emision_y_no_el_fin_de_la_actividad() -> None:
    pdf, _ = generar_pdf_certificado_lote(
        persona=_PERSONA,
        actividad=dict(_ACTIVIDAD),
        linea_descriptiva="",
        id_certificado="cert-prueba",
        fecha_emision=date(2026, 11, 18),
    )
    texto = _texto(pdf)
    assert b"noviembre de 2026" in texto
    assert b"octubre de 2026" not in texto


def test_el_zip_de_un_lote_aprobado_se_fecha_con_la_aprobacion_en_hora_argentina() -> None:
    # 01/12 a las 02:00 UTC es todavía 30/11 en Buenos Aires.
    lote = SimpleNamespace(
        id_lote="lote-prueba",
        id_actividad="PRUEBA-01",
        actividad=dict(_ACTIVIDAD),
        personas=(_PERSONA,),
        linea_descriptiva="",
        decidida_en=datetime(2026, 12, 1, 2, 0, tzinfo=timezone.utc),
    )
    crudo = construir_zip_certificados(lote=lote, demo=True)
    with zipfile.ZipFile(io.BytesIO(crudo)) as archivo:
        pdf = archivo.read(archivo.namelist()[0])
    texto = _texto(pdf)
    assert b"noviembre de 2026" in texto
    assert b"diciembre de 2026" not in texto
    assert construir_zip_certificados(lote=lote, demo=True) == crudo


def test_la_muestra_sin_aprobacion_se_fecha_con_el_dia() -> None:
    pdf = generar_pdf_muestra_lote(
        persona=_PERSONA,
        actividad=dict(_ACTIVIDAD),
        linea_descriptiva="",
    )
    hoy = datetime.now(_ARGENTINA).date()
    esperado = f"{_MESES[hoy.month - 1]} de {hoy.year}".encode()
    assert esperado in _texto(pdf)
