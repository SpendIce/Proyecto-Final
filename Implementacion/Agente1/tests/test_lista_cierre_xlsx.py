"""Lectura del Excel de la SEU para el pedido de certificados (#193).

Todo el material es sintético y se genera con `openpyxl` en el propio test:
nombres y correos `@example.invalid`, nunca datos reales. Se prueban las dos
formas admitidas (plantilla de seis columnas y planilla de la SEU con
aprobados + inscripción), el cruce por mail y los rechazos de seguridad
antes de que exista un lote.
"""

from __future__ import annotations

import io
import zipfile
from datetime import datetime

import pytest
from openpyxl import Workbook

from agente1.certificados_emision import (
    ListaCierreError,
    hash_lista_cierre,
)
from agente1.lista_cierre_xlsx import (
    MAX_DESCOMPRIMIDO_BYTES,
    MAX_XLSX_BYTES,
    parsear_xlsx_lista_cierre,
)
from agente1.web.pedido_certificados import parsear_csv_lista_cierre

MIME_XLSX = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _libro(hojas: dict[str, list[list[object]]]) -> bytes:
    libro = Workbook()
    libro.remove(libro.active)
    for nombre, filas in hojas.items():
        hoja = libro.create_sheet(nombre)
        for fila in filas:
            hoja.append(fila)
    destino = io.BytesIO()
    libro.save(destino)
    return destino.getvalue()


def _vacia(celdas: int) -> list[None]:
    return [None] * celdas


def _aprobados_seu() -> list[list[object]]:
    return [
        _vacia(4),
        [
            "PEREZ Ana",
            "PEREZ Ana",
            30123456.0,
            "Ana.Perez@Example.Invalid",
        ],
        [
            "DE LA FUENTE Juan",
            "DE LA FUENTE Juan",
            "DNI 30111222",
            "juan.delafuente@example.invalid",
        ],
        [
            "GOMEZ MARIA",
            "gomez maria",
            "DNI 27.111.222",
            "maria.gomez@example.invalid",
        ],
        [
            "FERNANDEZ PEDRO",
            "Fernandez Pedro",
            30123457,
            "pedro.fernandez@example.invalid",
        ],
    ]


def _inscripcion_seu() -> list[list[object]]:
    return [
        [None, "Pérez, Ana", "DNI 30.123.456", None, "ana.perez@example.invalid"],
        [
            2,
            "Gómez, María (DNI 27111222)",
            "DNI 99.999.999",
            datetime(2026, 11, 17, 10, 0),
            "maria.gomez@example.invalid",
        ],
        [
            3,
            "De la Fuente, Juan",
            "DNI 1.111.111",
            datetime(2026, 11, 17, 10, 0),
            "JUAN.DELAFUENTE@EXAMPLE.INVALID",
        ],
        _vacia(5),
        [
            5,
            "Apodo, Pedro",
            "DNI 30123457",
            datetime(2026, 11, 17, 10, 0),
            "pedro.fernandez@example.invalid",
        ],
    ]


def _xlsx_seu(aprobados=None, inscripcion=None) -> bytes:
    return _libro(
        {
            "Hoja 1": _aprobados_seu() if aprobados is None else aprobados,
            "Worksheet": (
                _inscripcion_seu() if inscripcion is None else inscripcion
            ),
        }
    )


def test_forma_seu_cruza_por_mail_y_prefiere_aprobados() -> None:
    personas = parsear_xlsx_lista_cierre(
        _xlsx_seu(), tratamiento="Sra.", condicion="aprobacion"
    )

    assert [(p.apellido, p.nombre) for p in personas] == [
        ("PEREZ", "Ana"),
        ("DE LA FUENTE", "Juan"),
        ("GOMEZ", "Maria"),
        ("Apodo", "Pedro"),
    ]
    assert [p.dni for p in personas] == [
        "30123456",
        "30111222",
        "27111222",
        "30123457",
    ]
    assert [p.mail for p in personas] == [
        "ana.perez@example.invalid",
        "juan.delafuente@example.invalid",
        "maria.gomez@example.invalid",
        "pedro.fernandez@example.invalid",
    ]
    assert {(p.tratamiento, p.condicion) for p in personas} == {
        ("Sra.", "aprobacion")
    }


def test_plantilla_de_seis_columnas_da_el_mismo_hash_que_el_csv() -> None:
    plantilla = [
        ["nombre", "apellido", "dni", "mail", "tratamiento", "condicion"],
        [
            "Ana",
            "Prueba",
            "11111111",
            "ana.prueba@example.invalid",
            "Sra.",
            "aprobacion",
        ],
        [
            "Luis",
            "Ejemplo",
            "22222222",
            "luis.ejemplo@example.invalid",
            "Sr.",
            "asistencia",
        ],
    ]
    csv = (
        "nombre;apellido;dni;mail;tratamiento;condicion\n"
        "Ana;Prueba;11111111;ana.prueba@example.invalid;Sra.;aprobacion\n"
        "Luis;Ejemplo;22222222;luis.ejemplo@example.invalid;Sr.;asistencia\n"
    )

    desde_xlsx = parsear_xlsx_lista_cierre(
        _libro({"Hoja 1": plantilla}),
        tratamiento="Dr.",
        condicion="asistencia",
    )
    desde_csv = parsear_csv_lista_cierre(csv.encode())

    assert desde_xlsx == desde_csv
    assert hash_lista_cierre(desde_xlsx) == hash_lista_cierre(desde_csv)


def test_plantilla_con_filas_vacias_al_principio() -> None:
    plantilla = [
        _vacia(6),
        ["nombre", "apellido", "dni", "mail", "tratamiento", "condicion"],
        ["Ana", "Prueba", "11111111", "ana@example.invalid", "Sra.", "aprobacion"],
    ]

    personas = parsear_xlsx_lista_cierre(_libro({"Hoja 1": plantilla}))

    assert len(personas) == 1
    assert personas[0].mail == "ana@example.invalid"


def test_sin_hoja_de_inscripcion_falla() -> None:
    contenido = _libro({"Hoja 1": _aprobados_seu()})

    with pytest.raises(ListaCierreError) as error:
        parsear_xlsx_lista_cierre(
            contenido, tratamiento="Sra.", condicion="aprobacion"
        )

    assert error.value.code == "lista_cierre_xlsx_sin_inscripcion"


def test_aprobado_sin_cruce_por_mail_falla_con_su_fila() -> None:
    aprobados = [
        [
            "PEREZ Ana",
            "PEREZ Ana",
            "DNI 30123456",
            "ana.perez@example.invalid",
        ],
        [
            "SIN CRUCE",
            "SIN CRUCE",
            "DNI 30111222",
            "sin.cruce@example.invalid",
        ],
    ]
    inscripcion = [
        [1, "Pérez, Ana", "DNI 30.123.456", None, "ana.perez@example.invalid"]
    ]

    with pytest.raises(ListaCierreError) as error:
        parsear_xlsx_lista_cierre(
            _xlsx_seu(aprobados, inscripcion),
            tratamiento="Sra.",
            condicion="aprobacion",
        )

    assert error.value.code == "lista_cierre_xlsx_sin_cruce"
    assert error.value.fila == 2


def test_dni_invalido_falla_con_la_fila_de_aprobados() -> None:
    aprobados = [
        [
            "PEREZ Ana",
            "PEREZ Ana",
            "DNI 123",
            "ana.perez@example.invalid",
        ]
    ]
    inscripcion = [
        [1, "Pérez, Ana", "DNI 30.123.456", None, "ana.perez@example.invalid"]
    ]

    with pytest.raises(ListaCierreError) as error:
        parsear_xlsx_lista_cierre(
            _xlsx_seu(aprobados, inscripcion),
            tratamiento="Sra.",
            condicion="aprobacion",
        )

    assert error.value.code == "lista_cierre_xlsx_dni"
    assert error.value.fila == 1


def test_mail_duplicado_lo_rechaza_la_validacion_del_circuito() -> None:
    aprobados = [
        [
            "PEREZ Ana",
            "PEREZ Ana",
            "DNI 30123456",
            "ana.perez@example.invalid",
        ],
        [
            "OTRA Ana",
            "OTRA Ana",
            "DNI 30111222",
            "ANA.PEREZ@EXAMPLE.INVALID",
        ],
    ]
    inscripcion = [
        [1, "Pérez, Ana", "DNI 30.123.456", None, "ana.perez@example.invalid"],
        [2, "Otra, Ana", "DNI 30111222", None, "ana.perez@example.invalid"],
    ]

    with pytest.raises(ListaCierreError) as error:
        parsear_xlsx_lista_cierre(
            _xlsx_seu(aprobados, inscripcion),
            tratamiento="Sra.",
            condicion="aprobacion",
        )

    assert error.value.code == "lista_cierre_duplicada"


def test_zip_corrupto_falla_antes_de_abrir_openpyxl() -> None:
    with pytest.raises(ListaCierreError) as error:
        parsear_xlsx_lista_cierre(
            b"PK\x03\x04esto no es un zip completo",
            tratamiento="Sra.",
            condicion="aprobacion",
        )

    assert error.value.code == "lista_cierre_xlsx_invalido"


def test_macro_vbaproject_falla() -> None:
    destino = io.BytesIO()
    with zipfile.ZipFile(destino, "w") as archivo:
        archivo.writestr("xl/vbaProject.bin", b"macros sinteticas")
        archivo.writestr("[Content_Types].xml", b"<Types/>")

    with pytest.raises(ListaCierreError) as error:
        parsear_xlsx_lista_cierre(
            destino.getvalue(), tratamiento="Sra.", condicion="aprobacion"
        )

    assert error.value.code == "lista_cierre_xlsx_macros"


def test_descomprimido_por_encima_del_tope_falla() -> None:
    destino = io.BytesIO()
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as archivo:
        archivo.writestr("xl/hoja.xml", b"0" * (MAX_DESCOMPRIMIDO_BYTES + 1))

    assert len(destino.getvalue()) < MAX_XLSX_BYTES
    with pytest.raises(ListaCierreError) as error:
        parsear_xlsx_lista_cierre(
            destino.getvalue(), tratamiento="Sra.", condicion="aprobacion"
        )

    assert error.value.code == "lista_cierre_xlsx_comprimido"


def test_archivo_por_encima_de_dos_mb_falla() -> None:
    with pytest.raises(ListaCierreError) as error:
        parsear_xlsx_lista_cierre(
            b"x" * (MAX_XLSX_BYTES + 1),
            tratamiento="Sra.",
            condicion="aprobacion",
        )

    assert error.value.code == "lista_cierre_xlsx_grande"


def test_ninguna_hoja_reconocible_remite_a_la_plantilla() -> None:
    contenido = _libro(
        {"Hoja 1": [["una", "hoja"], ["cualquiera", "sin", "forma"]]}
    )

    with pytest.raises(ListaCierreError) as error:
        parsear_xlsx_lista_cierre(
            contenido, tratamiento="Sra.", condicion="aprobacion"
        )

    assert error.value.code == "lista_cierre_xlsx_formato"


def test_la_inscripcion_tolera_filas_incompletas_de_quien_no_aprobo() -> None:
    # La hoja de inscripción la llena cada inscripto: en la planilla real
    # aparece una fila sin mail ni fecha. Esa fila no puede cruzar con
    # nadie, así que no invalida la hoja; sólo se ignora.
    inscripcion = _inscripcion_seu() + [
        [None, "Sinmail, Alguien", "DNI 30999888"],
        [7, "Sin coma en el nombre", "DNI 30999887", None, "x@example.invalid"],
    ]

    personas = parsear_xlsx_lista_cierre(
        _xlsx_seu(inscripcion=inscripcion),
        tratamiento="Sr./Sra.",
        condicion="aprobacion",
    )

    assert len(personas) == 4


def test_un_aprobado_cuya_inscripcion_esta_incompleta_no_cruza() -> None:
    aprobados = _aprobados_seu() + [
        [
            "SINMAIL Alguien",
            "SINMAIL Alguien",
            "DNI 30999888",
            "alguien@example.invalid",
        ]
    ]
    inscripcion = _inscripcion_seu() + [
        [None, "Sinmail, Alguien", "DNI 30999888"],
    ]

    with pytest.raises(ListaCierreError) as error:
        parsear_xlsx_lista_cierre(
            _xlsx_seu(aprobados=aprobados, inscripcion=inscripcion),
            tratamiento="Sr./Sra.",
            condicion="aprobacion",
        )

    assert error.value.code == "lista_cierre_xlsx_sin_cruce"
    assert error.value.fila == 6


def test_tamano_declarado_falso_no_rompe_la_lectura_y_se_rechaza() -> None:
    # Un zip que declara menos bytes de los que realmente descomprime:
    # `zipfile` corta la salida en el tamaño declarado y falla por CRC al
    # leer las filas. Tiene que volver como Excel inválido, no como 500.
    import struct

    original = _xlsx_seu()
    hoja = "xl/worksheets/sheet1.xml"
    destino = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as entrada, zipfile.ZipFile(
        destino, "w", zipfile.ZIP_DEFLATED
    ) as salida:
        for info in entrada.infolist():
            datos = entrada.read(info.filename)
            if info.filename == hoja:
                datos = datos.replace(b"</sheetData>", b"<row/>" * 200_000 + b"</sheetData>")
            salida.writestr(info.filename, datos)
    crudo = bytearray(destino.getvalue())
    nombre = hoja.encode()
    local = crudo.find(b"PK\x03\x04" + b"\x00" * 0)
    while local != -1:
        if crudo[local + 30 : local + 30 + len(nombre)] == nombre:
            struct.pack_into("<I", crudo, local + 22, 4096)
            break
        local = crudo.find(b"PK\x03\x04", local + 4)
    central = crudo.find(b"PK\x01\x02")
    while central != -1:
        if crudo[central + 46 : central + 46 + len(nombre)] == nombre:
            struct.pack_into("<I", crudo, central + 24, 4096)
            break
        central = crudo.find(b"PK\x01\x02", central + 4)

    with pytest.raises(ListaCierreError) as error:
        parsear_xlsx_lista_cierre(
            bytes(crudo), tratamiento="Sr./Sra.", condicion="aprobacion"
        )

    assert error.value.code == "lista_cierre_xlsx_invalido"
