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
- **Firma solapada.** La imagen va en una caja de 90×65 pt con el borde
  inferior en 62 pt, alineada al fondo y centrada en el firmante, y se
  emite antes que el texto, como pidió la SEU el 17/11/2026: queda casi
  entera sobre el nombre y sólo sus trazos inferiores lo cruzan; el cargo
  queda debajo y el texto se lee encima.
- **Ajuste al PDF del 17/11/2026.** El encabezado va en una línea
  (facultad 17 pt, universidad 13 pt), el título se achica desde 17 hasta
  13 pt para entrar en una línea y el cuerpo va en oblicua de 15 pt con el
  destinatario en negrita oblicua. El sustantivo del cuerpo sigue la
  primera palabra del título (taller, curso, seminario, jornada,
  diplomatura) y el DNI se imprime con separador de miles cuando son 7 u
  8 dígitos.
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
- **Espaciado propio.** Cada línea se compone con posición declarada, sin
  heredar el espaciado del DOCX ni rediseñar el documento. La
  compatibilidad tipográfica final (manual visual Encode Sans/Roboto vs.
  Calibri/Arial del archivo) queda a la revisión SEU: se usa Helvetica
  base-14 como sustituta estándar y se documenta. Calibri queda fuera de
  alcance por licencia.
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
import unicodedata
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .certificados import MARCA_PRUEBA, MARCADOR_BORRADOR, _escapar_texto_pdf

TEMPLATE_VERSION_SEU = "certificado_seu_aprobacion_v2"

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


# --- Destinatario y tipo de actividad ----------------------------------------

# La primera palabra del título decide cómo nombra el cuerpo a la
# actividad. Sin coincidencia se conserva «el mencionado curso».
_SUSTANTIVOS_ACTIVIDAD = {
    "taller": ("el", "taller"),
    "curso": ("el", "curso"),
    "seminario": ("el", "seminario"),
    "jornada": ("la", "jornada"),
    "diplomatura": ("la", "diplomatura"),
}


def _sin_diacriticos(texto: str) -> str:
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caracter)
    )


def _mencion_actividad_texto(actividad: str) -> str:
    """«el mencionado taller», «la mencionada jornada», etc.

    Sólo la primera palabra del título decide el sustantivo; se compara
    sin mayúsculas ni tildes. Si no es un tipo conocido, se mantiene el
    texto histórico «el mencionado curso».
    """

    palabras = (actividad or "").strip().split()
    if not palabras:
        return "el mencionado curso"
    primera = re.sub(r"^[^\w]+|[^\w]+$", "", palabras[0])
    clave = _sin_diacriticos(primera).lower()
    articulo, sustantivo = _SUSTANTIVOS_ACTIVIDAD.get(clave, ("el", "curso"))
    mencionado = "mencionada" if articulo == "la" else "mencionado"
    return f"{articulo} {mencionado} {sustantivo}"


def _dni_texto(dni: str) -> str:
    """El DNI con separador de miles si son 7 u 8 dígitos; si no, tal cual.

    Acepta el número con o sin puntos y espacios. Un pasaporte o cualquier
    otro formato se imprime como llegó: la plantilla no lo interpreta.
    """

    crudo = (dni or "").strip()
    digitos = re.sub(r"[\s.]", "", crudo)
    if not re.fullmatch(r"\d{7,8}", digitos):
        return crudo
    if len(digitos) == 7:
        return f"{digitos[0]}.{digitos[1:4]}.{digitos[4:]}"
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:]}"


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
    "ijlI.,;:!|'’´`¡íì": 278,
    "fjrt()[]{}\"“”": 333,
    "mwMW": 861,
    "JFLTZ-–—/\\": 540,
    " ": 278,
}


def _ancho_caracter(caracter: str, *, negrita: bool) -> int:
    for clase, ancho in _ANCHOS.items():
        if caracter in clase:
            return ancho
    if caracter.isdigit():
        return 556
    if caracter.isupper():
        return 700
    return 570 if negrita else 556


def _ancho_texto(texto: str, tamano: float, *, negrita: bool = False) -> float:
    """Ancho estimado de una línea en puntos, para centrar/envolver."""

    unidades = sum(
        _ancho_caracter(caracter, negrita=negrita) for caracter in texto
    )
    return unidades / 1000 * tamano


def _envolver(
    texto: str, tamano: float, ancho_max: float, *, negrita: bool = False
) -> list[str]:
    """Corta un texto en líneas que no superen `ancho_max` (estimado)."""

    lineas: list[str] = []
    for cruda in texto.splitlines():
        palabras = cruda.split(" ")
        actual = ""
        for palabra in palabras:
            candidata = f"{actual} {palabra}".strip()
            if (
                actual
                and _ancho_texto(candidata, tamano, negrita=negrita) > ancho_max
            ):
                lineas.append(actual)
                actual = palabra
            else:
                actual = candidata
        lineas.append(actual)
    return lineas or [""]


def _envolver_unidades(
    unidades: list[str], tamano: float, ancho_max: float
) -> list[str]:
    """Como `_envolver`, pero una unidad nunca se parte entre líneas."""

    lineas: list[str] = []
    actual = ""
    for unidad in unidades:
        candidata = f"{actual} {unidad}".strip()
        if actual and _ancho_texto(candidata, tamano) > ancho_max:
            lineas.append(actual)
            actual = unidad
        else:
            actual = candidata
    lineas.append(actual)
    return lineas


def _titulo_actividad_lineas(actividad: str) -> list[tuple[str, float]]:
    """El título en una línea, achicado; a 13 pt se envuelve si no entra."""

    texto = (actividad or "").strip()
    for tamano in _TAMANOS_TITULO:
        if _ancho_texto(texto, tamano, negrita=True) <= _ANCHO_UTIL_TITULO:
            return [(texto, float(tamano))]
    return [
        (linea, 13.0)
        for linea in _envolver(
            texto, 13, _ANCHO_UTIL_TITULO, negrita=True
        )
    ]


# --- Composición de la página --------------------------------------------------

_MARGEN_BORDE_EXT = 28.35  # 1 cm
_MARGEN_BORDE_INT = 35.43  # 1.25 cm

# Bloque de firma: caja de la imagen y líneas base del nombre y el cargo.
# La caja se apoya en 62 pt —casi entera sobre el nombre en 68— y la
# imagen se alinea a su fondo; el texto, emitido después, queda encima.
_CAJA_FIRMA_ANCHO = 90
_CAJA_FIRMA_ALTO = 65
_Y_CAJA_FIRMA_INFERIOR = 62
_Y_NOMBRE_FIRMANTE = 68
_Y_CARGO_FIRMANTE = 58

# El título entra en una línea achicándose desde 17 pt; a 13 pt, si no
# entra, se envuelve. El ancho útil deja aire dentro del doble borde.
_ANCHO_UTIL_TITULO = 620
_TAMANOS_TITULO = (17, 16, 15, 14, 13)


def _linea_centrada(texto: str, tamano: float, y: float, fuente: str) -> bytes:
    """Una línea centrada en la página. `fuente` es F1/F2/F3/F4."""

    ancho = _ancho_texto(texto, tamano, negrita=fuente == "F2")
    x = max(_MARGEN_BORDE_INT + 6, (PAGINA_ANCHO - ancho) / 2)
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
    nombre_xobject: str,
    cx: float,
    y_inferior: float,
    caja_ancho: float,
    caja_alto: float,
    img: _Imagen,
    *,
    alinear_al_fondo: bool = False,
) -> bytes:
    """Escala la imagen conservando proporción, centrada en su caja.

    Con `alinear_al_fondo` la imagen apoya en el borde inferior de la caja;
    así la firma queda casi entera sobre el nombre, sin deformarla.
    """

    escala = min(caja_ancho / img.ancho, caja_alto / img.alto)
    ancho, alto = img.ancho * escala, img.alto * escala
    x = cx - ancho / 2
    y = y_inferior if alinear_al_fondo else y_inferior + (caja_alto - alto) / 2
    return (
        f"q {ancho:.2f} 0 0 {alto:.2f} {x:.2f} {y:.2f} cm "
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
    marcar_prueba: bool = True,
) -> bytes:
    """Compone el certificado de aprobación con el diseño SEU recibido.

    Una página A4 horizontal, doble borde, símbolo FIE, encabezado
    institucional, título de la actividad, cuerpo con destinatario en
    negrita, lugar/fecha, línea descriptiva y los dos bloques de firma.
    `recursos` resuelve el símbolo y las firmas desde la custodia; cada
    recurso ausente deja su espacio reservado declarado. Determinista:
    mismo `datos`, mismos recursos, mismos bytes.

    `marcar_prueba` (default `True`) deja la línea «DOCUMENTO DE PRUEBA —
    SIN VALIDEZ»: sólo se apaga cuando el circuito corre en modo
    producción (#142), donde el diseño aprobado es la pieza real.
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
    if marcar_prueba:
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

    # Encabezado institucional en una línea, como el PDF del 17/11/2026.
    y = y_simbolo - 16
    partes.append(
        _linea_centrada(
            "Facultad de Ingeniería del Ejército "
            "“Grl Div Manuel Nicolás Savio”",
            17,
            y,
            "F2",
        )
    )
    y -= 20
    partes.append(
        _linea_centrada("Universidad de la Defensa Nacional", 13, y, "F2")
    )
    y -= 26
    for linea, tamano in _titulo_actividad_lineas(datos.actividad):
        partes.append(_linea_centrada(linea, tamano, y, "F2"))
        y -= tamano + 3

    # Cuerpo en oblicua; el destinatario en negrita oblicua, como el DOCX.
    y -= 12
    destinatario = (
        f"{datos.nombre.strip()} {datos.apellido.strip().upper()}, "
        f"DNI {_dni_texto(datos.dni)}"
    )
    mencion = _mencion_actividad_texto(datos.actividad)
    unidades = (
        "Se extiende el presente CERTIFICADO a".split()
        + [destinatario]
        + (
            f"por APROBAR {mencion}, de {datos.horas.strip()} "
            "horas reloj de duración."
        ).split()
    )
    for cruda in _envolver_unidades(unidades, 15, 700):
        partes.append(
            _linea_centrada_mixta(
                cruda,
                15,
                y,
                destinatario,
                fuente_normal="F3",
                fuente_negrita="F4",
            )
        )
        y -= 17

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

    # Bloques de firma: la imagen se centra en la línea del nombre para
    # que los trazos la crucen (pedido SEU del 17/11/2026). El texto se
    # emite después y queda legible encima.
    centros = (PAGINA_ANCHO * 0.30, PAGINA_ANCHO * 0.62)
    for indice, firmante in enumerate(firmantes):
        cx = centros[indice] if indice < len(centros) else PAGINA_ANCHO / 2
        imagen = imagenes.get(firmante.recurso or "")
        if imagen is not None:
            partes.append(
                _imagen_en_caja(
                    nombre_xobj[firmante.recurso or ""],
                    cx,
                    _Y_CAJA_FIRMA_INFERIOR,
                    _CAJA_FIRMA_ANCHO,
                    _CAJA_FIRMA_ALTO,
                    imagen,
                    alinear_al_fondo=True,
                )
            )
        else:
            partes.append(
                _caja_pendiente(cx, 84, 120, 46, "[firma: insumo restringido no provisto]")
            )
        encabezado = f"{firmante.grado} {firmante.nombre}".strip()
        partes.append(
            _linea_centrada_en(encabezado, 9, _Y_NOMBRE_FIRMANTE, cx)
        )
        partes.append(
            _linea_centrada_en(firmante.cargo, 8, _Y_CARGO_FIRMANTE, cx)
        )

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


def _linea_centrada_mixta(
    texto: str,
    tamano: float,
    y: float,
    segmento_negrita: str,
    *,
    fuente_normal: str = "F1",
    fuente_negrita: str = "F2",
) -> bytes:
    """Línea centrada con `segmento_negrita` en la fuente de negrita."""

    extra = 0.0
    if segmento_negrita and segmento_negrita in texto:
        extra = _ancho_texto(
            segmento_negrita, tamano, negrita=True
        ) - _ancho_texto(segmento_negrita, tamano)
    ancho_total = _ancho_texto(texto, tamano) + extra
    x = max(_MARGEN_BORDE_INT + 8, (PAGINA_ANCHO - ancho_total) / 2)
    salida = bytearray(f"BT {tamano} TL 1 0 0 1 {x:.2f} {y:.2f} Tm ".encode("ascii"))
    resto = texto
    while resto:
        indice = resto.find(segmento_negrita) if segmento_negrita else -1
        if indice < 0:
            tramo, fuente, resto = resto, fuente_normal, ""
        elif indice == 0:
            tramo, fuente = segmento_negrita, fuente_negrita
            resto = resto[len(segmento_negrita) :]
        else:
            tramo, fuente, resto = resto[:indice], fuente_normal, resto[indice:]
        salida += f"/{fuente} {tamano} Tf ".encode("ascii")
        salida += b"(" + _escapar_texto_pdf(tramo) + b") Tj "
    return bytes(salida) + b"ET\n"


def _ensamblar_pdf(partes: list[bytes], imagenes: dict[str, _Imagen]) -> bytes:
    """Arma el PDF: catálogo, página, 4 fuentes, XObjects y contenido.

    Misma estructura determinista que `generar_pdf_certificado`: objetos
    en orden fijo, xref calculado sobre los bytes emitidos, sin fechas
    ni identificadores de documento.
    """

    contenido = b"".join(partes)
    nombres = sorted(imagenes)
    xobjects = "".join(f" /Im{i} {8 + i} 0 R" for i in range(len(nombres)))
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGINA_ANCHO} {PAGINA_ALTO}] "
            "/Resources << /Font << /F1 4 0 R /F2 5 0 R /F3 6 0 R /F4 7 0 R >>"
            f" /XObject <<{xobjects} >> >> /Contents {8 + len(nombres)} 0 R >>"
        ).encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-BoldOblique /Encoding /WinAnsiEncoding >>",
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
