"""Lectura del Excel de la SEU para el pedido de certificados (#193).

El módulo no conoce FastAPI: recibe los bytes del upload y devuelve las
mismas `PersonaCierre` que el CSV, pasando por
`certificados_emision.parsear_lista_cierre`. Así la validación, los
errores `ListaCierreError` y el hash del lote son los del circuito, sin
una segunda copia de las reglas.

Admite dos formas, detectadas por la forma de las hojas y no por su
nombre (los archivos de la SEU traen «Hoja 1», «Worksheet» o lo que
decida Excel):

- **Plantilla propia:** una hoja cuya primera fila no vacía es la
  cabecera `COLUMNAS_LISTA_CIERRE`. Se usa tal cual: tratamiento y
  condición salen de la planilla.
- **Planilla de la SEU:** una hoja de aprobados con cuatro celdas por
  fila (`APELLIDO(S) Nombre(s)`, el mismo nombre, `DNI 99999999`, mail) y
  una hoja de inscripción con cinco (`nº`, `Apellido(s), Nombre(s)`,
  `DNI 99999999`, fecha y hora, mail). El cruce es por mail y el nombre
  corregido de aprobados manda sobre el tipeado en la inscripción.

El archivo es de un usuario autenticado pero no confiable: se acota el
tamaño, se inspecciona el zip antes de abrir openpyxl, se rechazan las
macros y la bomba de descompresión, y se lee en modo `read_only` con
`data_only=True`. Ningún dato de la planilla sale en un log ni en un
mensaje de error: los errores dicen el número de fila, nada más.
"""

from __future__ import annotations

import io
import unicodedata
import zipfile
from datetime import date, datetime

from openpyxl import Workbook, load_workbook

from .certificados_emision import (
    COLUMNAS_LISTA_CIERRE,
    MAX_FILAS_LISTA_CIERRE,
    ListaCierreError,
    PersonaCierre,
    parsear_lista_cierre,
)

MAX_XLSX_BYTES = 2 * 1024 * 1024
MAX_DESCOMPRIMIDO_BYTES = 30 * 1024 * 1024
MAX_FILAS_INSCRIPCION = 20_000

_MINUSCULAS_NOMBRE = frozenset({"de", "del", "la"})


def parsear_xlsx_lista_cierre(
    contenido: bytes,
    *,
    tratamiento: str = "",
    condicion: str = "",
) -> tuple[PersonaCierre, ...]:
    """Bytes de un `.xlsx` → personas validadas, todo o nada.

    `tratamiento` y `condicion` sólo se usan en la forma de la SEU: en
    ambas filas se aplican a todas las personas. En la plantilla propia
    mandan las columnas del archivo.
    """
    _validar_contenedor(contenido)
    libro = _abrir_libro(contenido)
    try:
        hojas = _leer_hojas(libro)
    except ListaCierreError:
        raise
    except Exception:
        # openpyxl en `read_only` descomprime cada hoja recién al iterarla:
        # un zip con tamaños declarados falsos falla acá por CRC (zipfile
        # nunca entrega más bytes que los declarados) y vuelve como Excel
        # inválido, no como error del servidor.
        raise ListaCierreError("lista_cierre_xlsx_invalido") from None
    finally:
        libro.close()

    for filas in hojas:
        if _es_plantilla(filas):
            return _parsear_plantilla(filas)

    aprobados = next((filas for filas in hojas if _es_aprobados(filas)), None)
    inscripcion = next(
        (filas for filas in hojas if _es_inscripcion(filas)), None
    )
    if aprobados is None and inscripcion is None:
        raise ListaCierreError("lista_cierre_xlsx_formato")
    if aprobados is None:
        raise ListaCierreError("lista_cierre_xlsx_sin_aprobados")
    if inscripcion is None:
        raise ListaCierreError("lista_cierre_xlsx_sin_inscripcion")
    return _cruzar_aprobados(aprobados, inscripcion, tratamiento, condicion)


def _validar_contenedor(contenido: bytes) -> None:
    if not contenido:
        raise ListaCierreError("lista_cierre_xlsx_vacia")
    if len(contenido) > MAX_XLSX_BYTES:
        raise ListaCierreError("lista_cierre_xlsx_grande")
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as archivo:
            infos = archivo.infolist()
            if any(
                info.filename.lower().endswith("vbaproject.bin")
                for info in infos
            ):
                raise ListaCierreError("lista_cierre_xlsx_macros")
            if (
                sum(info.file_size for info in infos)
                > MAX_DESCOMPRIMIDO_BYTES
            ):
                raise ListaCierreError("lista_cierre_xlsx_comprimido")
    except ListaCierreError:
        raise
    except (zipfile.BadZipFile, OSError, ValueError):
        raise ListaCierreError("lista_cierre_xlsx_invalido") from None


def _abrir_libro(contenido: bytes) -> Workbook:
    try:
        return load_workbook(
            io.BytesIO(contenido), read_only=True, data_only=True
        )
    except Exception:
        raise ListaCierreError("lista_cierre_xlsx_invalido") from None


def _leer_hojas(libro: Workbook) -> list[list[tuple[int, list[str]]]]:
    hojas: list[list[tuple[int, list[str]]]] = []
    for hoja in libro.worksheets:
        filas: list[tuple[int, list[str]]] = []
        for numero, fila in enumerate(
            hoja.iter_rows(values_only=True), start=1
        ):
            if numero > MAX_FILAS_INSCRIPCION:
                raise ListaCierreError(
                    "lista_cierre_xlsx_inscripcion_filas"
                )
            celdas = [_texto_celda(valor) for valor in fila]
            while celdas and not celdas[-1]:
                celdas.pop()
            if not celdas:
                continue
            filas.append((numero, celdas))
        hojas.append(filas)
    return hojas


def _texto_celda(valor: object) -> str:
    """Convierte la celda a texto sin perder un DNI numérico.

    openpyxl devuelve números como `int` o `float` y fechas como objetos:
    un DNI 30123456 o 30123456.0 tiene que quedar «30123456», no
    «30123456.0».
    """
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "VERDADERO" if valor else "FALSO"
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    if isinstance(valor, datetime):
        return valor.isoformat(sep=" ")
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor).strip()


def _es_plantilla(filas: list[tuple[int, list[str]]]) -> bool:
    if not filas:
        return False
    return filas[0][1] == list(COLUMNAS_LISTA_CIERRE)


def _parsear_plantilla(
    filas: list[tuple[int, list[str]]],
) -> tuple[PersonaCierre, ...]:
    if len(filas) - 1 > MAX_FILAS_LISTA_CIERRE:
        raise ListaCierreError("lista_cierre_xlsx_filas")
    desde = filas[0][0]
    try:
        return parsear_lista_cierre([list(celdas) for _, celdas in filas])
    except ListaCierreError as error:
        if error.fila is None:
            raise
        # El parser numera la lista que recibe; se traduce a la fila real
        # de la hoja para que el aviso no mienta si había filas vacías.
        raise ListaCierreError(
            error.code, fila=desde + error.fila - 1
        ) from None


def _es_aprobados(filas: list[tuple[int, list[str]]]) -> bool:
    if not filas:
        return False
    for _, celdas in filas:
        if len(celdas) != 4:
            return False
        nombre, repetido, dni, mail = celdas
        if not all((nombre, repetido, dni, mail)):
            return False
        if _normalizar(nombre) != _normalizar(repetido):
            return False
        if not any(caracter.isdigit() for caracter in dni):
            return False
        if "@" not in mail:
            return False
    return True


def _es_fila_inscripcion(celdas: list[str]) -> bool:
    if len(celdas) != 5:
        return False
    _numero, nombre, dni, _fecha, mail = celdas
    return (
        "," in nombre
        and any(caracter.isdigit() for caracter in dni)
        and "@" in mail
    )


def _es_inscripcion(filas: list[tuple[int, list[str]]]) -> bool:
    """La hoja la llena cada inscripto: se reconoce por mayoría.

    Una fila incompleta (sin mail, sin coma) no puede cruzar con ningún
    aprobado y se ignora al indexar; un aprobado que no cruza igual bloquea
    el lote. Por eso tolerar filas sucias acá no relaja la validación.
    """
    if not filas:
        return False
    validas = sum(1 for _, celdas in filas if _es_fila_inscripcion(celdas))
    return validas * 2 > len(filas)


def _cruzar_aprobados(
    aprobados: list[tuple[int, list[str]]],
    inscripcion: list[tuple[int, list[str]]],
    tratamiento: str,
    condicion: str,
) -> tuple[PersonaCierre, ...]:
    if len(aprobados) > MAX_FILAS_LISTA_CIERRE:
        raise ListaCierreError("lista_cierre_xlsx_filas")
    indice = _indice_inscripcion(inscripcion)
    filas: list[list[str]] = []
    numeros: list[int] = []
    for numero, celdas in aprobados:
        _nombre_aprobado, _repetido, dni_texto, mail_texto = celdas
        dni = _dni_digitos(dni_texto)
        if dni is None:
            raise ListaCierreError("lista_cierre_xlsx_dni", fila=numero)
        mail = mail_texto.strip().casefold()
        referencia = indice.get(mail)
        if referencia is None:
            raise ListaCierreError(
                "lista_cierre_xlsx_sin_cruce", fila=numero
            )
        fila_inscripcion, nombre_inscripcion = referencia
        nombre, apellido = _nombre_y_apellido(
            _nombre_aprobado, nombre_inscripcion, fila_inscripcion
        )
        filas.append(
            [nombre, apellido, dni, mail, tratamiento, condicion]
        )
        numeros.append(numero)
    try:
        return parsear_lista_cierre(filas)
    except ListaCierreError as error:
        if error.fila is None:
            raise
        raise ListaCierreError(
            error.code, fila=numeros[error.fila - 1]
        ) from None


def _indice_inscripcion(
    filas: list[tuple[int, list[str]]],
) -> dict[str, tuple[int, str]]:
    indice: dict[str, tuple[int, str]] = {}
    for numero, celdas in filas:
        if not _es_fila_inscripcion(celdas):
            continue
        indice.setdefault(celdas[4].strip().casefold(), (numero, celdas[1]))
    return indice


def _nombre_y_apellido(
    nombre_aprobado: str,
    nombre_inscripcion: str,
    fila_inscripcion: int,
) -> tuple[str, str]:
    apellido_inscripcion, _, nombre_inscripcion = (
        nombre_inscripcion.partition(",")
    )
    apellido_inscripcion = _compactar(apellido_inscripcion)
    nombre_inscripcion = _compactar(nombre_inscripcion)
    palabras_aprobado = nombre_aprobado.split()
    palabras_apellido = apellido_inscripcion.split()
    if (
        palabras_apellido
        and len(palabras_aprobado) > len(palabras_apellido)
        and [
            _normalizar(palabra)
            for palabra in palabras_aprobado[: len(palabras_apellido)]
        ]
        == [_normalizar(palabra) for palabra in palabras_apellido]
    ):
        apellido = " ".join(palabras_aprobado[: len(palabras_apellido)])
        nombre = " ".join(palabras_aprobado[len(palabras_apellido):])
        return _capitalizar_nombre(nombre), apellido
    if not apellido_inscripcion or not nombre_inscripcion:
        raise ListaCierreError(
            "lista_cierre_xlsx_inscripcion_invalida",
            fila=fila_inscripcion,
        )
    return (
        _capitalizar_nombre(nombre_inscripcion),
        apellido_inscripcion,
    )


def _capitalizar_nombre(nombre: str) -> str:
    if not (nombre.isupper() or nombre.islower()):
        return nombre
    return " ".join(
        palabra.lower()
        if palabra.lower() in _MINUSCULAS_NOMBRE
        else palabra.capitalize()
        for palabra in nombre.split()
    )


def _normalizar(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(
        caracter
        for caracter in sin_acentos
        if not unicodedata.combining(caracter)
    )
    return " ".join(sin_acentos.casefold().split())


def _compactar(texto: str) -> str:
    return " ".join(texto.split())


def _dni_digitos(texto: str) -> str | None:
    digitos = "".join(caracter for caracter in texto if caracter.isdigit())
    if len(digitos) in (7, 8):
        return digitos
    return None


__all__ = [
    "MAX_DESCOMPRIMIDO_BYTES",
    "MAX_FILAS_INSCRIPCION",
    "MAX_XLSX_BYTES",
    "parsear_xlsx_lista_cierre",
]
