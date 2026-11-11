"""HU-014 (#126) — Plantilla SEU del certificado de aprobación.

La SEU entregó el 19/10/2026 la plantilla institucional editable de
**aprobación** (ficha `Documentos/Reuniones/SEU-2026-10-19/`): un A4
horizontal con doble borde, símbolo FIE centrado arriba, denominación de
facultad y universidad, título de la actividad, cuerpo de aprobación con
el destinatario como variable, lugar/fecha y dos bloques visibles de
firma (Secretario de Extensión y Decano). Este módulo la reproduce como
**plantilla de composición**: cada elemento se declara por posición y
tamaño en un PDF determinista de una página, generado sólo con stdlib.

Decisiones de la integración:

- **Sin firmas versionadas.** Las imágenes de firma y el símbolo llegan
  por `RecursosFirma`, un puerto que resuelve bytes de imagen desde una
  carpeta restringida fuera del repo (`RecursosFirmaDirectorio`); en vivo
  la declara la configuración (`AGENTE1_CERTIFICADOS_RECURSOS_DIR`). Un
  recurso ausente no inventa una firma: se dibuja el espacio reservado
  marcado como insumo restringido no provisto. Para ensayos hay recursos
  sintéticos versionados en `tests/fixtures/recursos-firma/`, que no
  representan a ninguna persona.
- **Sin tercer firmante.** El XML del DOCX arrastra un cuadro de texto
  con otro nombre y cargo que el render no muestra (queda fuera de la
  página): no se compone. Los únicos bloques son los dos visibles.
- **Parámetros, no herencia.** Nombre, apellido, DNI, actividad, horas y
  fecha llegan como datos: el caso NotebookLM compone con su título y
  sus 24 horas; nada del ejemplo (Gestión Documental, 12 h) queda
  fijado en la plantilla.
- **Marca permanente.** Todo documento lleva
  `DOCUMENTO DE PRUEBA — SIN VALIDEZ`; la muestra previa a la aprobación
  agrega `BORRADOR — NO EMITIR`, igual que en el circuito provisional.
- **Sólo aprobación.** La SEU no entregó la variante de asistencia:
  este renderer no la implementa (`condicion` `asistencia` sigue por la
  plantilla provisional, declarada pendiente de definición SEU).
- **Espaciado propio.** El render LibreOffice del cierre mostró un
  encabezado con espaciado irregular del DOCX; acá cada línea se compone
  con posición declarada, sin heredar esa irregularidad ni rediseñar el
  documento. La compatibilidad tipográfica final (manual visual Encode
  Sans/Roboto vs. Calibri/Arial del archivo) queda a la revisión SEU:
  se usa Helvetica base-14 como sustituta estándar y se documenta.
- **Determinismo.** Sin timestamps ni IDs de documento, imágenes
  embebidas con compresión fija: mismos datos y mismos recursos,
  mismos bytes. El `pdf_hash` de la auditoría sigue siendo reproducible.

La línea descriptiva aprobada (#74) se compone debajo del cuerpo, más
chica y en oblicua: no es parte del diseño recibido pero sí del contrato
de emisión, y su lugar queda declarado para la revisión.
"""

from __future__ import annotations

import re
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .certificados import MARCA_PRUEBA, MARCADOR_BORRADOR, _escapar_texto_pdf

TEMPLATE_VERSION_SEU = "certificado_seu_aprobacion_v1"

# Página A4 horizontal en puntos (297 × 210 mm).
PAGINA_ANCHO = 841.92
PAGINA_ALTO = 595.2

_COLOR_TINTA = "0.18 0.18 0.18"  # #2e2e2e del documento recibido
_COLOR_NEGRO = "0 0 0"

# Los recursos que la composición sabe pedir. Se resuelven por nombre de
# archivo sin extensión dentro del directorio restringido; el nombre es
# el contrato entre la plantilla y la custodia.
RECURSO_SIMBOLO_FIE = "simbolo-fie"
RECURSOS_IMAGEN = (
    RECURSO_SIMBOLO_FIE,
    "firma-secretario",
    "firma-decano",
)
_EXTENSIONES_IMAGEN = (".png", ".jpg", ".jpeg")


@dataclass(frozen=True)
class FirmanteSeu:
    """Un bloque de firma visible: grado, nombre, cargo y recurso de imagen.

    `recurso` es el nombre de archivo (sin extensión) que el custodio
    guarda en la carpeta restringida; `None` deja el espacio reservado.
    """

    grado: str
    nombre: str
    cargo: str
    recurso: str | None


# Los dos bloques visibles del documento recibido, con sus textos tal
# cual. El grado y el cargo van en líneas propias, como en el original.
FIRMANTES_SEU = (
    FirmanteSeu(
        grado="Teniente Coronel",
        nombre="SEBASTIÁN ERNESTO MOREIRA",
        cargo="SECRETARIO DE EXTENSIÓN UNIVERSITARIA",
        recurso="firma-secretario",
    ),
    FirmanteSeu(
        grado="Coronel",
        nombre="DAVID FIORITO",
        cargo="DECANO DE LA FACULTAD DE INGENIERIA DEL EJERCITO",
        recurso="firma-decano",
    ),
)


@dataclass(frozen=True)
class DatosCertificadoSeu:
    """Los parámetros que completa el emisor por cada certificado.

    `fecha` llega ya expresada como la va a imprimir la línea de lugar
    (ver `fecha_lugar_texto`); `horas` llega como la va a imprimir el
    cuerpo (ver `horas_reloj_texto`). Ningún campo puede ser `None`: la
    plantilla no inventa datos.
    """

    nombre: str
    apellido: str
    dni: str
    actividad: str
    horas: str
    fecha: str
    linea_descriptiva: str


class RecursosFirma(Protocol):
    """Puerto de custodia: resuelve el contenido de un recurso de imagen.

    Devuelve los bytes del archivo o `None` cuando el recurso no está
    provisto. No hay lectura implícita del repo ni de rutas fijas.
    """

    def leer(self, nombre: str) -> bytes | None: ...


class RecursosFirmaDirectorio:
    """Recursos desde una carpeta restringida fuera del repo.

    Busca `<directorio>/<nombre>.<png|jpg|jpeg>` en ese orden y sólo eso:
    un nombre fuera del contrato de recursos no se resuelve nunca. La
    carpeta y sus permisos los controla la custodia (D2); el agente sólo
    lee.
    """

    def __init__(self, directorio: Path | str) -> None:
        self._directorio = Path(directorio)

    def leer(self, nombre: str) -> bytes | None:
        if not isinstance(nombre, str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9-]*", nombre
        ):
            return None
        for extension in _EXTENSIONES_IMAGEN:
            candidato = self._directorio / f"{nombre}{extension}"
            if candidato.is_file():
                return candidato.read_bytes()
        return None


class RecursosFirmaError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


# --- Fecha y horas como texto de la plantilla --------------------------------

_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

_FECHA_ISO_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def fecha_lugar_texto(fecha: str, *, lugar: str = "Ciudad Autónoma de Buenos Aires") -> str:
    """La línea de lugar y fecha del documento recibido.

    Una fecha ISO (`AAAA-MM-DD`) se expresa como en el original: mes y
    año (`octubre de 2026`). Un valor que no es ISO se imprime tal cual:
    la plantilla no reformatea lo que no reconoce.
    """

    fecha = (fecha or "").strip()
    encontrado = _FECHA_ISO_RE.search(fecha)
    if encontrado:
        mes = int(encontrado.group(2))
        if 1 <= mes <= 12:
            return f"{lugar}, {_MESES[mes - 1]} de {encontrado.group(1)}."
    return f"{lugar}, {fecha}." if fecha else f"{lugar}."


_UNIDADES = (
    "", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO",
    "NUEVE", "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE",
    "DIECISÉIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE", "VEINTE",
)
_VEINTES = (
    "VEINTE", "VEINTIÚN", "VEINTIDÓS", "VEINTITRÉS", "VEINTICUATRO",
    "VEINTICINCO", "VEINTISÉIS", "VEINTISIETE", "VEINTIOCHO", "VEINTINUEVE",
)
_DECENAS = (
    "", "", "", "TREINTA", "CUARENTA", "CINCUENTA",
    "SESENTA", "SETENTA", "OCHENTA", "NOVENTA",
)


def _numero_en_palabras(n: int) -> str:
    if n <= 20:
        return _UNIDADES[n]
    if n < 30:
        return _VEINTES[n - 20]
    decena, unidad = divmod(n, 10)
    palabra = _DECENAS[decena]
    return f"{palabra} Y {_UNIDADES[unidad]}" if unidad else palabra


def horas_reloj_texto(horas: str) -> str:
    """Las horas como las escribe la plantilla: en letras y mayúsculas.

    `DOCE` en el ejemplo de 12 horas; `VEINTICUATRO` para NotebookLM.
    Un valor que no es entero de 1 a 99 se imprime tal cual llegó: la
    plantilla completa variables, no interpreta la carga horaria.
    """

    texto = (horas or "").strip()
    try:
        numero = int(texto)
    except ValueError:
        return texto
    if not 1 <= numero <= 99:
        return texto
    return _numero_en_palabras(numero)


# --- Decodificación de imágenes (stdlib) --------------------------------------


def _jpeg_dimensiones(datos: bytes) -> tuple[int, int]:
    """Ancho y alto de un JPEG leyendo sus marcadores SOF."""

    if len(datos) < 4 or datos[:2] != b"\xff\xd8":
        raise RecursosFirmaError("firma_imagen_invalida")
    pos = 2
    while pos + 9 < len(datos):
        if datos[pos] != 0xFF:
            pos += 1
            continue
        marcador = datos[pos + 1]
        pos += 2
        if marcador in (0xD8, 0xD9) or 0xD0 <= marcador <= 0xD7:
            continue
        largo = struct.unpack(">H", datos[pos : pos + 2])[0]
        if marcador in (0xC0, 0xC1, 0xC2):
            alto, ancho = struct.unpack(">HH", datos[pos + 3 : pos + 7])
            return ancho, alto
        pos += largo
    raise RecursosFirmaError("firma_imagen_invalida")


def _png_a_rgb(datos: bytes) -> tuple[int, int, bytes]:
    """Decodifica un PNG 8-bit no entrelazado y lo aplana sobre blanco.

    Soporta los tipos de color 0 (gris), 2 (RGB), 3 (paleta), 4 (gris+alfa)
    y 6 (RGBA) con los cinco filtros de scanline. El alfa se compone sobre
    fondo blanco —las firmas y el símbolo se estampan sobre papel— así el
    PDF queda en un solo `DeviceRGB` flateado, sin SMask. Lo que no entra
    en ese contrato (16 bits, Adam7, corrupción) es `firma_imagen_invalida`.
    """

    if not datos.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RecursosFirmaError("firma_imagen_invalida")
    pos = 8
    ihdr = None
    paleta = None
    idat = bytearray()
    while pos + 8 <= len(datos):
        largo, tipo = struct.unpack(">I4s", datos[pos : pos + 8])
        cuerpo = datos[pos + 8 : pos + 8 + largo]
        if len(cuerpo) != largo:
            raise RecursosFirmaError("firma_imagen_invalida")
        if tipo == b"IHDR":
            ihdr = cuerpo
        elif tipo == b"PLTE":
            paleta = cuerpo
        elif tipo == b"IDAT":
            idat += cuerpo
        elif tipo == b"IEND":
            break
        pos += 12 + largo
    if ihdr is None or not idat:
        raise RecursosFirmaError("firma_imagen_invalida")
    ancho, alto, bits, color, _comp, _filtro, interlace = struct.unpack(
        ">IIBBBBB", ihdr
    )
    if bits != 8 or interlace != 0:
        raise RecursosFirmaError("firma_imagen_invalida")
    canales = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
    if canales is None or (color == 3 and paleta is None):
        raise RecursosFirmaError("firma_imagen_invalida")
    crudo = zlib.decompress(bytes(idat))
    paso = ancho * canales
    esperado = (paso + 1) * alto
    if len(crudo) < esperado:
        raise RecursosFirmaError("firma_imagen_invalida")
    filas = bytearray(paso * alto)
    anterior = bytearray(paso)
    src = 0
    for y in range(alto):
        filtro = crudo[src]
        src += 1
        linea = bytearray(crudo[src : src + paso])
        src += paso
        for x in range(paso):
            a = linea[x - canales] if x >= canales else 0
            b = anterior[x]
            c = anterior[x - canales] if x >= canales else 0
            if filtro == 1:
                linea[x] = (linea[x] + a) & 0xFF
            elif filtro == 2:
                linea[x] = (linea[x] + b) & 0xFF
            elif filtro == 3:
                linea[x] = (linea[x] + (a + b) // 2) & 0xFF
            elif filtro == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                linea[x] = (linea[x] + pred) & 0xFF
            elif filtro != 0:
                raise RecursosFirmaError("firma_imagen_invalida")
        filas[y * paso : (y + 1) * paso] = linea
        anterior = linea
    rgb = bytearray(ancho * alto * 3)
    for i in range(ancho * alto):
        if color == 0:
            g = filas[i]
            rgb[3 * i : 3 * i + 3] = bytes((g, g, g))
        elif color == 2:
            rgb[3 * i : 3 * i + 3] = filas[3 * i : 3 * i + 3]
        elif color == 3:
            indice = filas[i]
            rgb[3 * i : 3 * i + 3] = paleta[3 * indice : 3 * indice + 3]
        elif color == 4:
            g, alfa = filas[2 * i], filas[2 * i + 1]
            v = (g * alfa + 255 * (255 - alfa)) // 255
            rgb[3 * i : 3 * i + 3] = bytes((v, v, v))
        else:  # 6, RGBA
            r, g, b, alfa = filas[4 * i : 4 * i + 4]
            rgb[3 * i] = (r * alfa + 255 * (255 - alfa)) // 255
            rgb[3 * i + 1] = (g * alfa + 255 * (255 - alfa)) // 255
            rgb[3 * i + 2] = (b * alfa + 255 * (255 - alfa)) // 255
    return ancho, alto, bytes(rgb)


@dataclass(frozen=True)
class _Imagen:
    nombre: str
    ancho: int
    alto: int
    objeto: bytes  # diccionario + stream ya armados, sin el encabezado `n 0 obj`


def _cargar_imagen(nombre: str, datos: bytes) -> _Imagen:
    """Convierte bytes PNG/JPEG en un XObject de imagen, o `firma_imagen_invalida`."""

    if datos[:2] == b"\xff\xd8":
        ancho, alto = _jpeg_dimensiones(datos)
        stream = datos
        extra = b"/Filter /DCTDecode"
    elif datos.startswith(b"\x89PNG"):
        ancho, alto, rgb = _png_a_rgb(datos)
        stream = zlib.compress(rgb, 6)
        extra = b"/Filter /FlateDecode"
    else:
        raise RecursosFirmaError("firma_imagen_invalida")
    objeto = (
        f"<< /Type /XObject /Subtype /Image /Width {ancho} /Height {alto} "
        f"/ColorSpace /DeviceRGB /BitsPerComponent 8 {extra.decode()} "
        f"/Length {len(stream)} >>\nstream\n".encode("ascii")
        + stream
        + b"\nendstream"
    )
    return _Imagen(nombre=nombre, ancho=ancho, alto=alto, objeto=objeto)


# --- Métrica aproximada de Helvetica para centrado y envoltura -----------------

# Ancho estimado por carácter en milésimas de em para Helvetica sobre
# WinAnsi. No es la tabla AFM: es una aproximación por clases que alcanza
# para centrar una línea y envolver sin derramar del borde (el ajuste de
# fidelidad fina queda a la revisión SEU).
_ANCHOS = {
    "ijlI.,;:!|'’´`¡íì": 260,
    "fjrt()[]{}\"": 330,
    "mwMW": 850,
    "JFLTZ-–—/\\": 450,
    " ": 278,
}


def _ancho_caracter(caracter: str) -> int:
    for clase, ancho in _ANCHOS.items():
        if caracter in clase:
            return ancho
    if caracter.isupper() or caracter.isdigit():
        return 700
    return 520


def _ancho_texto(texto: str, tamano: float) -> float:
    """Ancho estimado de una línea en puntos, para centrar/envolver."""

    unidades = sum(_ancho_caracter(caracter) for caracter in texto)
    return unidades / 1000 * tamano


def _envolver(texto: str, tamano: float, ancho_max: float) -> list[str]:
    """Corta un texto en líneas que no superen `ancho_max` (estimado)."""

    lineas: list[str] = []
    for cruda in texto.splitlines():
        palabras = cruda.split(" ")
        actual = ""
        for palabra in palabras:
            candidata = f"{actual} {palabra}".strip()
            if actual and _ancho_texto(candidata, tamano) > ancho_max:
                lineas.append(actual)
                actual = palabra
            else:
                actual = candidata
        lineas.append(actual)
    return lineas or [""]


# --- Composición de la página --------------------------------------------------

_MARGEN_BORDE_EXT = 28.35  # 1 cm
_MARGEN_BORDE_INT = 35.43  # 1.25 cm


def _linea_centrada(texto: str, tamano: float, y: float, fuente: str) -> bytes:
    """Una línea centrada en la página. `fuente` es F1/F2/F3."""

    x = max(_MARGEN_BORDE_INT + 6, (PAGINA_ANCHO - _ancho_texto(texto, tamano)) / 2)
    return (
        f"BT /{fuente} {tamano} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm ".encode("ascii")
        + b"("
        + _escapar_texto_pdf(texto)
        + b") Tj ET\n"
    )


def _linea_derecha(texto: str, tamano: float, y: float, fuente: str) -> bytes:
    x = PAGINA_ANCHO - _MARGEN_BORDE_INT - 14 - _ancho_texto(texto, tamano)
    return (
        f"BT /{fuente} {tamano} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm ".encode("ascii")
        + b"("
        + _escapar_texto_pdf(texto)
        + b") Tj ET\n"
    )


def _imagen_en_caja(
    nombre_xobject: str, cx: float, y_inferior: float, caja_ancho: float, caja_alto: float, img: _Imagen
) -> bytes:
    """Escala la imagen conservando proporción, centrada en su caja."""

    escala = min(caja_ancho / img.ancho, caja_alto / img.alto)
    ancho, alto = img.ancho * escala, img.alto * escala
    x = cx - ancho / 2
    return (
        f"q {ancho:.2f} 0 0 {alto:.2f} {x:.2f} {y_inferior + (caja_alto - alto) / 2:.2f} cm "
        f"/{nombre_xobject} Do Q\n"
    ).encode("ascii")


def _caja_pendiente(cx: float, y_inferior: float, ancho: float, alto: float, leyenda: str) -> bytes:
    """El espacio reservado de un recurso no provisto: nunca una firma falsa."""

    x = cx - ancho / 2
    salida = (
        f"q 0.75 G 0.5 w {x:.2f} {y_inferior:.2f} {ancho:.2f} {alto:.2f} re S Q\n"
    ).encode("ascii")
    salida += (
        f"BT /F1 6.5 Tf 1 0 0 1 {x + 2:.2f} {y_inferior + 3:.2f} Tm ".encode("ascii")
        + b"("
        + _escapar_texto_pdf(leyenda)
        + b") Tj ET\n"
    )
    return salida


def generar_pdf_certificado_seu(
    datos: DatosCertificadoSeu,
    *,
    recursos: RecursosFirma | None = None,
    firmantes: tuple[FirmanteSeu, ...] = FIRMANTES_SEU,
    borrador: bool = False,
) -> bytes:
    """Compone el certificado de aprobación con el diseño SEU recibido.

    Una página A4 horizontal, doble borde, símbolo FIE, encabezado
    institucional, título de la actividad, cuerpo con destinatario en
    negrita, lugar/fecha, línea descriptiva y los dos bloques de firma.
    `recursos` resuelve el símbolo y las firmas desde la custodia; cada
    recurso ausente deja su espacio reservado declarado. Determinista:
    mismo `datos`, mismos recursos, mismos bytes.
    """

    imagenes: dict[str, _Imagen] = {}
    if recursos is not None:
        pedidos = set(RECURSOS_IMAGEN) | {
            f.recurso for f in firmantes if f.recurso is not None
        }
        for nombre in pedidos:
            crudo = recursos.leer(nombre)
            if crudo is not None:
                imagenes[nombre] = _cargar_imagen(nombre, crudo)

    # Nombre de XObject por recurso, en el mismo orden que `_ensamblar_pdf`.
    nombre_xobj = {
        nombre: f"Im{i}" for i, nombre in enumerate(sorted(imagenes))
    }

    partes: list[bytes] = []
    # Doble borde, trazo negro fino (0.75 pt como el original).
    for margen in (_MARGEN_BORDE_EXT, _MARGEN_BORDE_INT):
        partes.append(
            f"q {_COLOR_NEGRO} RG 0.75 w "
            f"{margen:.2f} {margen:.2f} {PAGINA_ANCHO - 2 * margen:.2f} "
            f"{PAGINA_ALTO - 2 * margen:.2f} re S Q\n".encode("ascii")
        )

    partes.append(f"q {_COLOR_TINTA} rg {_COLOR_TINTA} RG\n".encode("ascii"))

    # Marcas de prueba: primera línea visible, dentro del borde.
    y = PAGINA_ALTO - _MARGEN_BORDE_INT - 16
    if borrador:
        partes.append(_linea_centrada(MARCADOR_BORRADOR, 12, y, "F2"))
        y -= 15
    partes.append(_linea_centrada(MARCA_PRUEBA, 11, y, "F2"))

    # Símbolo FIE: centrado en lo alto, como en el original.
    simbolo = imagenes.get(RECURSO_SIMBOLO_FIE)
    y_simbolo = y - 176
    if simbolo is not None:
        partes.append(
            _imagen_en_caja(
                nombre_xobj[RECURSO_SIMBOLO_FIE],
                PAGINA_ANCHO / 2, y_simbolo, 164, 164, simbolo,
            )
        )
    else:
        partes.append(
            _caja_pendiente(
                PAGINA_ANCHO / 2, y_simbolo + 54, 90, 56, "[símbolo FIE: insumo restringido no provisto]"
            )
        )

    # Encabezado institucional y título de la actividad.
    y = y_simbolo - 16
    partes.append(_linea_centrada("Facultad de Ingeniería del Ejército", 22, y, "F2"))
    y -= 25
    partes.append(_linea_centrada("“Grl Div Manuel Nicolás Savio”", 20, y, "F2"))
    y -= 25
    partes.append(_linea_centrada("Universidad de la Defensa Nacional", 16, y, "F2"))
    y -= 28
    for linea in _envolver(datos.actividad.strip(), 19, 660):
        partes.append(_linea_centrada(linea, 19, y, "F2"))
        y -= 22

    # Cuerpo: el destinatario en negrita dentro de la frase, como el DOCX.
    y -= 12
    destinatario = f"{datos.nombre.strip()} {datos.apellido.strip()}, DNI {datos.dni.strip()}"
    frase = (
        "Se extiende el presente CERTIFICADO a "
        + destinatario
        + f" por APROBAR el mencionado curso, de {datos.horas.strip()} "
        "horas reloj de duración."
    )
    for cruda in _envolver(frase, 17, 700):
        partes.append(_linea_centrada_mixta(cruda, 17, y, destinatario))
        y -= 20

    # Línea descriptiva aprobada (#74), más chica y en oblicua.
    linea = datos.linea_descriptiva.strip()
    if linea:
        y -= 4
        for cruda in _envolver(linea, 12, 620):
            partes.append(_linea_centrada(cruda, 12, y, "F3"))
            y -= 14

    # Lugar y fecha a la derecha, cerrando el flujo del cuerpo; el mínimo
    # protege la zona fija de las firmas si el contenido se estira.
    partes.append(_linea_derecha(datos.fecha.strip(), 16, max(y - 22, 150), "F1"))

    # Bloques de firma: imagen arriba y texto abajo, como el original.
    centros = (PAGINA_ANCHO * 0.30, PAGINA_ANCHO * 0.62)
    for indice, firmante in enumerate(firmantes):
        cx = centros[indice] if indice < len(centros) else PAGINA_ANCHO / 2
        imagen = imagenes.get(firmante.recurso or "")
        if imagen is not None:
            partes.append(
                _imagen_en_caja(
                    nombre_xobj[firmante.recurso or ""], cx, 78, 86, 64, imagen
                )
            )
        else:
            partes.append(
                _caja_pendiente(cx, 84, 120, 46, "[firma: insumo restringido no provisto]")
            )
        encabezado = f"{firmante.grado} {firmante.nombre}".strip()
        partes.append(_linea_centrada_en(encabezado, 9, 68, cx))
        partes.append(_linea_centrada_en(firmante.cargo, 8, 58, cx))

    partes.append(b"Q\n")
    return _ensamblar_pdf(partes, imagenes)


def _linea_centrada_en(texto: str, tamano: float, y: float, cx: float) -> bytes:
    x = cx - _ancho_texto(texto, tamano) / 2
    return (
        f"BT /F1 {tamano} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm ".encode("ascii")
        + b"("
        + _escapar_texto_pdf(texto)
        + b") Tj ET\n"
    )


def _linea_centrada_mixta(texto: str, tamano: float, y: float, segmento_negrita: str) -> bytes:
    """Línea centrada con `segmento_negrita` impreso en F2 dentro del texto."""

    ancho_total = _ancho_texto(texto, tamano)
    x = max(_MARGEN_BORDE_INT + 8, (PAGINA_ANCHO - ancho_total) / 2)
    salida = bytearray(f"BT {tamano} TL 1 0 0 1 {x:.2f} {y:.2f} Tm ".encode("ascii"))
    resto = texto
    while resto:
        indice = resto.find(segmento_negrita) if segmento_negrita else -1
        if indice < 0:
            tramo, fuente, resto = resto, "F1", ""
        elif indice == 0:
            tramo, fuente = segmento_negrita, "F2"
            resto = resto[len(segmento_negrita) :]
        else:
            tramo, fuente, resto = resto[:indice], "F1", resto[indice:]
        salida += f"/{fuente} {tamano} Tf ".encode("ascii")
        salida += b"(" + _escapar_texto_pdf(tramo) + b") Tj "
    return bytes(salida) + b"ET\n"


def _ensamblar_pdf(partes: list[bytes], imagenes: dict[str, _Imagen]) -> bytes:
    """Arma el PDF: catálogo, página, 3 fuentes, XObjects y contenido.

    Misma estructura determinista que `generar_pdf_certificado`: objetos
    en orden fijo, xref calculado sobre los bytes emitidos, sin fechas
    ni identificadores de documento.
    """

    contenido = b"".join(partes)
    nombres = sorted(imagenes)
    xobjects = "".join(f" /Im{i} {7 + i} 0 R" for i in range(len(nombres)))
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGINA_ANCHO} {PAGINA_ALTO}] "
            "/Resources << /Font << /F1 4 0 R /F2 5 0 R /F3 6 0 R >>"
            f" /XObject <<{xobjects} >> >> /Contents {7 + len(nombres)} 0 R >>"
        ).encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>",
    ]
    for nombre in nombres:
        objetos.append(imagenes[nombre].objeto)
    objetos.append(
        f"<< /Length {len(contenido)} >>\nstream\n".encode("ascii")
        + contenido
        + b"\nendstream"
    )
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for numero, objeto in enumerate(objetos, start=1):
        offsets.append(len(pdf))
        pdf += f"{numero} 0 obj\n".encode("ascii") + objeto + b"\nendobj\n"
    xref = len(pdf)
    pdf += f"xref\n0 {len(objetos) + 1}\n".encode("ascii")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode("ascii")
    pdf += (
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode("ascii")
    return bytes(pdf)


__all__ = [
    "DatosCertificadoSeu",
    "FirmanteSeu",
    "FIRMANTES_SEU",
    "RECURSOS_IMAGEN",
    "RECURSO_SIMBOLO_FIE",
    "RecursosFirma",
    "RecursosFirmaDirectorio",
    "RecursosFirmaError",
    "TEMPLATE_VERSION_SEU",
    "fecha_lugar_texto",
    "generar_pdf_certificado_seu",
    "horas_reloj_texto",
]
