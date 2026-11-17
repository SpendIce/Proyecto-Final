"""HU-014/#126: plantilla SEU del certificado de aprobación.

Cubre la composición reproducible del diseño recibido (A4 horizontal,
doble borde, símbolo FIE, bloques Secretario/Decano), la parametrización
de nombre/apellido/DNI/actividad/horas/fecha —el caso NotebookLM compone
24 horas sin heredar las 12 del ejemplo—, las marcas de prueba y de
borrador, los recursos de firma desde custodia fuera de Git con recurso
sintético versionado, la ausencia del tercer firmante invisible del XML
y la pendiente explícita de la variante de asistencia.
"""

import re
import zlib
from pathlib import Path

import pytest

from agente1.certificados_plantilla_seu import (
    FIRMANTES_SEU,
    PAGINA_ANCHO,
    RECURSOS_IMAGEN,
    DatosCertificadoSeu,
    RecursosFirmaDirectorio,
    RecursosFirmaError,
    fecha_lugar_texto,
    generar_pdf_certificado_seu,
    horas_reloj_texto,
)

FIXTURES = Path(__file__).parent / "fixtures" / "recursos-firma"


def _datos(**cambios) -> DatosCertificadoSeu:
    base = {
        "nombre": "Bruno",
        "apellido": "Prueba Dos",
        "dni": "30222333",
        "actividad": "INTELIGENCIA ARTIFICIAL APLICADA A LA EDUCACIÓN Y GESTIÓN: NOTEBOOKLM - NIVEL 2",
        "horas": horas_reloj_texto("24"),
        "fecha": fecha_lugar_texto("2026-10-05"),
        "linea_descriptiva": (
            "El certificado acredita la participación según la condición "
            "declarada por el docente a cargo."
        ),
    }
    base.update(cambios)
    return DatosCertificadoSeu(**base)


def _recursos() -> RecursosFirmaDirectorio:
    return RecursosFirmaDirectorio(FIXTURES)


def _contenido(pdf: bytes) -> bytes:
    """Los streams del documento descomprimidos: ahí queda el texto."""

    partes = [pdf]
    pos = 0
    while True:
        ini = pdf.find(b"stream\n", pos)
        if ini < 0:
            break
        ini += len(b"stream\n")
        fin = pdf.find(b"\nendstream", ini)
        if fin < 0:
            break
        try:
            partes.append(zlib.decompress(pdf[ini:fin]))
        except zlib.error:
            pass
        pos = fin + 1
    return b"\n".join(partes)


# --- Textos derivados de parámetros -------------------------------------------


def test_horas_en_palabras():
    assert horas_reloj_texto("12") == "DOCE"
    assert horas_reloj_texto("24") == "VEINTICUATRO"
    assert horas_reloj_texto("1") == "UN"
    assert horas_reloj_texto("45") == "CUARENTA Y CINCO"
    # Lo que no es entero chico se imprime tal cual, sin interpretar.
    assert horas_reloj_texto("abc") == "abc"
    assert horas_reloj_texto("150") == "150"


def test_fecha_lugar_mes_y_anio():
    assert (
        fecha_lugar_texto("2026-10-05")
        == "Ciudad Autónoma de Buenos Aires, octubre de 2026."
    )
    assert fecha_lugar_texto("octubre de 2026").endswith("octubre de 2026.")


# --- Composición ------------------------------------------------------------


def test_pdf_determinista_byte_a_byte():
    a = generar_pdf_certificado_seu(_datos(), recursos=_recursos())
    b = generar_pdf_certificado_seu(_datos(), recursos=_recursos())
    assert a == b
    assert a.startswith(b"%PDF")


def test_pagina_a4_horizontal():
    pdf = generar_pdf_certificado_seu(_datos(), recursos=_recursos())
    assert b"/MediaBox [0 0 841.92 595.2]" in pdf


def test_parametros_en_el_documento_sin_herencia_del_ejemplo():
    """NotebookLM compone su título y sus 24 h: nada del ejemplo queda fijo."""

    pdf = generar_pdf_certificado_seu(_datos(), recursos=_recursos())
    contenido = _contenido(pdf)
    assert b"Bruno Prueba Dos" in contenido
    assert b"30222333" in contenido
    assert b"NOTEBOOKLM" in contenido
    assert b"VEINTICUATRO" in contenido
    assert b"octubre de 2026" in contenido
    # Ni el título ni la carga del ejemplo recibido quedan en la plantilla.
    assert b"Gesti" not in contenido
    assert b"DOCE" not in contenido


def test_otro_caso_compone_otros_datos():
    datos = _datos(
        nombre="Ana",
        apellido="Prueba Uno",
        dni="30111222",
        actividad="Curso de Inteligencia Artificial Aplicada a la Gestión Documental",
        horas=horas_reloj_texto("12"),
        fecha=fecha_lugar_texto("2026-10-31"),
    )
    contenido = _contenido(
        generar_pdf_certificado_seu(datos, recursos=_recursos())
    )
    assert b"Ana Prueba Uno" in contenido
    assert b"DOCE" in contenido
    assert b"VEINTICUATRO" not in contenido


def test_marcas_de_prueba_y_borrador():
    emitido = _contenido(
        generar_pdf_certificado_seu(_datos(), recursos=_recursos())
    )
    assert b"DOCUMENTO DE PRUEBA" in emitido
    assert b"BORRADOR" not in emitido
    muestra = _contenido(
        generar_pdf_certificado_seu(
            _datos(), recursos=_recursos(), borrador=True
        )
    )
    assert b"BORRADOR" in muestra
    assert b"DOCUMENTO DE PRUEBA" in muestra


def test_dos_bloques_de_firma_sin_tercer_firmante():
    """El XML del DOCX arrastra un bloque de Director que el render no
    muestra: la composición sólo tiene Secretario y Decano."""

    contenido = _contenido(
        generar_pdf_certificado_seu(_datos(), recursos=_recursos())
    )
    assert b"MOREIRA" in contenido
    assert b"SECRETARIO DE EXTENSI" in contenido
    assert b"FIORITO" in contenido
    assert b"DECANO" in contenido
    # El tercer firmante invisible heredado no se compone.
    assert b"DIRECTOR" not in contenido


# --- Solapado de la firma sobre el texto del firmante -----------------------


def _stream_contenido(pdf: bytes) -> bytes:
    """El stream de operadores de la página, sin descomprimir."""

    ini = pdf.rfind(b"\nstream\n")
    if ini < 0:
        raise AssertionError("el PDF no tiene stream de contenido")
    fin = pdf.find(b"\nendstream", ini)
    if fin < 0:
        raise AssertionError("el stream de contenido no cierra")
    return pdf[ini + len(b"\nstream\n") : fin]


def _imagenes_y_textos(contenido: bytes) -> tuple[list[dict], list[dict]]:
    """Operadores de imagen y de texto, en el orden del stream."""

    imagenes: list[dict] = []
    textos: list[dict] = []
    for orden, linea in enumerate(contenido.splitlines()):
        imagen = re.search(
            rb"q ([\d.]+) 0 0 ([\d.]+) ([\d.]+) ([\d.]+) cm /Im\d+ Do Q",
            linea,
        )
        if imagen is not None:
            ancho, alto, x, y = (float(valor) for valor in imagen.groups())
            imagenes.append(
                {"orden": orden, "x0": x, "x1": x + ancho, "y0": y, "y1": y + alto}
            )
        texto = re.search(rb"1 0 0 1 ([\d.]+) ([\d.]+) Tm \((.*)\) Tj", linea)
        if texto is not None:
            textos.append(
                {"orden": orden, "y": float(texto.group(2)), "texto": texto.group(3)}
            )
    return imagenes, textos


def test_firma_se_solapa_sobre_el_nombre_y_se_dibuja_antes():
    """Pedido SEU del 17/11/2026: los trazos cruzan el nombre del firmante.

    La imagen se emite antes que el texto para que nombre y cargo queden
    legibles encima.
    """

    contenido = _stream_contenido(
        generar_pdf_certificado_seu(_datos(), recursos=_recursos())
    )
    imagenes, textos = _imagenes_y_textos(contenido)
    # Símbolo + una imagen por firmante, en el orden en que se emiten.
    assert len(imagenes) == 1 + len(FIRMANTES_SEU)
    firmas = imagenes[-len(FIRMANTES_SEU) :]
    for indice, firmante in enumerate(FIRMANTES_SEU):
        apellido = firmante.nombre.split()[-1].encode("utf-8")
        nombre = next(t for t in textos if apellido in t["texto"])
        cargo = next(
            t for t in textos if firmante.cargo.split()[0].encode("utf-8") in t["texto"]
        )
        firma = firmas[indice]
        # La caja dibujada cruza la línea base del nombre y el texto va encima.
        assert firma["y0"] < nombre["y"] < firma["y1"]
        assert firma["orden"] < nombre["orden"] < cargo["orden"]
        cx = PAGINA_ANCHO * (0.30 if indice == 0 else 0.62)
        assert abs((firma["x0"] + firma["x1"]) / 2 - cx) < 0.5


def test_espacio_reservado_sin_recursos_no_pisa_el_nombre():
    """Sin imagen no hay firma falsa: el espacio marcado queda sobre el texto."""

    contenido = _stream_contenido(
        generar_pdf_certificado_seu(_datos(), recursos=None)
    )
    reservados = re.findall(
        rb"q 0\.75 G 0\.5 w [\d.]+ ([\d.]+) 120\.00 46\.00 re S Q", contenido
    )
    assert len(reservados) == len(FIRMANTES_SEU)
    for y_inferior in reservados:
        assert float(y_inferior) > 68


# --- Recursos de firma -------------------------------------------------------


def test_con_recursos_las_imagenes_quedan_embebidas():
    pdf = generar_pdf_certificado_seu(_datos(), recursos=_recursos())
    assert pdf.count(b"/Subtype /Image") == 3
    assert pdf.count(b" Do Q") == 3


def test_sin_recursos_los_espacios_quedan_marcados():
    pdf = generar_pdf_certificado_seu(_datos(), recursos=None)
    contenido = _contenido(pdf)
    assert b"insumo restringido no provisto" in contenido
    # Ninguna imagen: ni símbolo ni firmas.
    assert b"/Subtype /Image" not in pdf


def test_recurso_individual_faltante_deja_su_espacio(tmp_path: Path):
    (tmp_path / "simbolo-fie.png").write_bytes(
        (FIXTURES / "simbolo-fie.png").read_bytes()
    )
    pdf = generar_pdf_certificado_seu(
        _datos(), recursos=RecursosFirmaDirectorio(tmp_path)
    )
    contenido = _contenido(pdf)
    assert pdf.count(b"/Subtype /Image") == 1
    assert contenido.count(b"insumo restringido no provisto") == 2


def test_imagen_invalida_rechaza_controlado(tmp_path: Path):
    (tmp_path / "firma-decano.png").write_bytes(b"esto no es una imagen")
    with pytest.raises(RecursosFirmaError, match="firma_imagen_invalida"):
        generar_pdf_certificado_seu(
            _datos(), recursos=RecursosFirmaDirectorio(tmp_path)
        )


def test_directorio_resuelve_solo_nombres_del_contrato(tmp_path: Path):
    (tmp_path / "firma-decano.txt").write_text("no es imagen")
    (tmp_path / "../fuera.png").parent.mkdir(exist_ok=True)
    recursos = RecursosFirmaDirectorio(tmp_path)
    assert recursos.leer("firma-decano") is None  # extensión no admitida
    assert recursos.leer("../fuera") is None  # el nombre no es del contrato
    assert recursos.leer("INEXISTENTE") is None


def test_los_tres_recursos_del_contrato_existen_en_fixtures():
    """El recurso sintético versionado cubre el contrato de nombres."""

    recursos = _recursos()
    for nombre in RECURSOS_IMAGEN:
        assert recursos.leer(nombre) is not None, nombre
    for firmante in FIRMANTES_SEU:
        assert recursos.leer(firmante.recurso) is not None


# --- Decodificadores de imagen -------------------------------------------------


def _png_fake(ancho: int, alto: int, color_rgb: bytes) -> bytes:
    """PNG 8-bit RGB mínimo y válido, generado para el test."""

    import struct

    crudo = bytearray()
    for _y in range(alto):
        crudo.append(0)
        crudo += color_rgb * ancho

    def chunk(tipo, datos):
        import zlib as _z

        return (
            struct.pack(">I", len(datos))
            + tipo
            + datos
            + struct.pack(">I", _z.crc32(tipo + datos) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(crudo), 6))
        + chunk(b"IEND", b"")
    )


def test_png_rgb_decodifica_y_se_embebe(tmp_path: Path):
    (tmp_path / "simbolo-fie.png").write_bytes(
        _png_fake(4, 4, b"\x20\x40\x60")
    )
    pdf = generar_pdf_certificado_seu(
        _datos(), recursos=RecursosFirmaDirectorio(tmp_path)
    )
    assert b"/Filter /FlateDecode" in pdf
    assert pdf.count(b"/Subtype /Image") == 1


def test_jpeg_se_embebe_por_dct(tmp_path: Path):
    """Un JPEG mínimo con SOF0 leíble viaja crudo con DCTDecode."""

    import struct

    sof = (
        b"\xff\xd8"  # SOI
        + b"\xff\xe0\x00\x10" + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        + b"\xff\xc0\x00\x11\x08" + struct.pack(">HH", 8, 10) + b"\x03"
        + b"\x01\x22\x00\x02\x11\x01\x03\x11\x01"
        + b"\xff\xd9"  # EOI
    )
    (tmp_path / "firma-decano.jpg").write_bytes(sof)
    pdf = generar_pdf_certificado_seu(
        _datos(), recursos=RecursosFirmaDirectorio(tmp_path)
    )
    assert b"/Filter /DCTDecode" in pdf
    assert b"/Width 10 /Height 8" in pdf


# --- La variante de asistencia queda pendiente ---------------------------------


def test_plantilla_seu_es_solo_de_aprobacion():
    """El documento compuesto es de aprobación: no hay texto de asistencia
    ni conversión entre condiciones; la variante espera definición SEU."""

    contenido = _contenido(
        generar_pdf_certificado_seu(_datos(), recursos=_recursos())
    )
    assert b"APROBAR" in contenido
    assert b"ASISTENCIA" not in contenido
    assert b"asisti" not in contenido.lower()
