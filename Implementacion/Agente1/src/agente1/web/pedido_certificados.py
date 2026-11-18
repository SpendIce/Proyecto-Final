"""Pedido web del lote de certificados (#168, ADR 0018).

GET/POST `/certificados/pedir`: quien tiene rol `APROBADOR_CONTENIDO`
elige una actividad del catálogo ya cargado por la app, sube la lista de
cierre en CSV y escribe la línea descriptiva. Crear el lote no envía
correos ni registra aprobaciones: después se revisan actividad, lista y
línea en la página del lote y ahí se decide.

Decisiones que no se ven en el código:

- **La ficha de la actividad es la del catálogo, nunca la del formulario.**
  El id viaja en el POST; los datos se proyectan de la fila de la fuente
  en el servidor. Si a la fila le faltan campos institucionales (título,
  horas, modalidad, fecha de inicio u organiza), el pedido se rechaza con
  `actividad_datos_incompletos`: no se completan con valores supuestos,
  el bloqueo queda visible y concreto.
- **El CSV se parsea en memoria y acotado.** No se escribe a disco: se
  leen como mucho `MAX_CSV_BYTES` y `MAX_CSV_FILAS` filas. La codificación
  es UTF-8 (se acepta la marca BOM de Excel) y el delimitador «;» o «,»
  sólo si la cabecera queda bien delimitada con las seis columnas
  contractuales, en ese orden. La validación es toda o nada: una fila
  inválida rechaza el lote entero y el error dice el número de fila del
  archivo, sin volcar su contenido.
- **La identidad del lote es la lista + la actividad.** Repetir el mismo
  pedido devuelve el lote existente —el `objeto_lote` es único—. Si la
  lista ya está con otra ficha de actividad, otra línea descriptiva u otro
  generador, se rechaza el pedido con un conflicto explícito: no se
  ignora la redacción nueva, no se sobrescribe lo aprobado y nadie se
  apropia del lote ajeno.
- **`origen_creacion` viene de la sesión, no del formulario.** Una sesión
  de demostración produce un lote `demo` (que nunca puentea al registro
  institucional y emite sólo el ZIP de prueba); una sesión Google produce
  un lote real. El argumento lo agrega el backend del contrato a
  `RepositorioLotes.crear`.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Protocol

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.datastructures import FormData, UploadFile
from starlette.exceptions import HTTPException

from ..canal_form import hash_correo
from ..certificados_emision import (
    COLUMNAS_LISTA_CIERRE,
    MAX_FILAS_LISTA_CIERRE,
    ListaCierreError,
    PersonaCierre,
    parsear_lista_cierre,
)
from ..confirmaciones import ROL_APROBADOR_CONTENIDO
from ..linea_descriptiva import (
    hash_linea_descriptiva,
    normalizar_linea,
    validar_linea_descriptiva,
)
from ..lista_cierre_xlsx import (
    MAX_FILAS_INSCRIPCION,
    MAX_XLSX_BYTES,
    parsear_xlsx_lista_cierre,
)
from .certificados_web import (
    _REQUERIDOS_ACTIVIDAD,
    Autorizar,
    CsrfOk,
    DestinoLogin,
    LoteCertificados,
    LoteCertificadosError,
    Render,
    RolDe,
)
from .formularios import leer_formulario_acotado
from .sesiones import Sesion

MAX_CSV_BYTES = 512 * 1024
MAX_CSV_FILAS = MAX_FILAS_LISTA_CIERRE
MAX_FORM_BYTES = MAX_XLSX_BYTES + 16 * 1024
MAX_LINEA_CARACTERES = 300

COLUMNAS_CSV = " · ".join(COLUMNAS_LISTA_CIERRE)

# El CSV de muestra que baja la persona: filas ficticias con el dominio
# reservado `example.invalid`, nunca datos reales.
_PLANTILLA_LISTA_CSV = (
    "nombre;apellido;dni;mail;tratamiento;condicion\r\n"
    "Persona;Ficticia;90000001;persona.ficticia@example.invalid;Sr.;aprobacion\r\n"
    "Otra;Ficticia;90000002;otra.ficticia@example.invalid;Sra.;asistencia\r\n"
)


class RepositorioPedidoPuerto(Protocol):
    """El `crear` idempotente del circuito de lotes.

    `origen_creacion` lo agrega el backend del contrato (migración 0012):
    la web lo pasa desde la sesión y nunca desde el formulario.
    """

    def crear(
        self,
        *,
        id_actividad: str,
        actividad: dict[str, str],
        personas: tuple[PersonaCierre, ...],
        linea_descriptiva: str,
        generada_por_hash: str,
        origen_creacion: str | None = None,
        ahora: datetime | None = None,
    ) -> LoteCertificados: ...


_MENSAJES_CAMPO = {
    "actividad_invalida": "Elegí una actividad de la lista.",
    "actividad_datos_incompletos": (
        "A la actividad le faltan datos en la fuente institucional: "
        "{faltantes}. El lote no se crea con valores supuestos: "
        "completalos en la fuente y volvé a pedir."
    ),
    "actividad_id_invalida": "La actividad elegida no es válida.",
    "linea_descriptiva_ausente": "Escribí la línea descriptiva.",
    "linea_descriptiva_invalida": "La línea descriptiva no sirve.",
    "lista_cierre_csv_ausente": "Subí la lista de cierre en CSV o Excel.",
    "lista_cierre_csv_vacia": "El archivo está vacío.",
    "lista_cierre_csv_grande": (
        "El archivo supera el máximo de {max_kb} KB."
    ),
    "lista_cierre_csv_filas": (
        "La lista supera el máximo de {max_filas} filas."
    ),
    "lista_cierre_csv_codificacion": (
        "El archivo no es UTF-8. Exportá la planilla como CSV UTF-8."
    ),
    "lista_cierre_csv_cabecera": (
        "La primera fila tiene que ser la cabecera "
        "«nombre;apellido;dni;mail;tratamiento;condicion», con «;» o «,» "
        "bien delimitados."
    ),
    "lista_cierre_xlsx_vacia": "El archivo Excel está vacío.",
    "lista_cierre_xlsx_grande": (
        "El archivo Excel supera el máximo de {max_xlsx_mb} MB."
    ),
    "lista_cierre_xlsx_invalido": (
        "El archivo no es un Excel válido (.xlsx)."
    ),
    "lista_cierre_xlsx_comprimido": (
        "El Excel descomprimido supera el máximo permitido."
    ),
    "lista_cierre_xlsx_macros": (
        "El Excel tiene macros: no se aceptan archivos con macros."
    ),
    "lista_cierre_xlsx_formato": (
        "No se reconoce el formato del Excel: usá la plantilla de seis "
        "columnas o el Excel de la SEU con hoja de aprobados y de "
        "inscripción."
    ),
    "lista_cierre_xlsx_sin_aprobados": (
        "El Excel no tiene una hoja de aprobados reconocible."
    ),
    "lista_cierre_xlsx_sin_inscripcion": (
        "El Excel de la SEU no tiene hoja de inscripción."
    ),
    "lista_cierre_xlsx_sin_cruce": (
        "La fila {fila} de aprobados no tiene una fila de inscripción con "
        "el mismo mail."
    ),
    "lista_cierre_xlsx_dni": (
        "La fila {fila} de aprobados no tiene un DNI de 7 u 8 dígitos."
    ),
    "lista_cierre_xlsx_inscripcion_invalida": (
        "La inscripción no tiene «Apellido(s), Nombre(s)» en la fila "
        "{fila}."
    ),
    "lista_cierre_xlsx_filas": (
        "La hoja de aprobados supera el máximo de {max_filas} filas."
    ),
    "lista_cierre_xlsx_inscripcion_filas": (
        "La hoja de inscripción supera el máximo de "
        "{max_filas_inscripcion} filas."
    ),
    "lista_cierre_vacia": "La lista no tiene ninguna persona.",
    "lista_cierre_fila_invalida": (
        "La fila {fila} de la lista no sirve: tiene que tener las seis "
        "columnas completas y un mail válido."
    ),
    "lista_cierre_condicion_vacia": (
        "La fila {fila} no tiene condición."
    ),
    "lista_cierre_condicion_invalida": (
        "La fila {fila} tiene una condición que no es «asistencia» ni "
        "«aprobacion»."
    ),
    "lista_cierre_duplicada": (
        "La fila {fila} repite un DNI o un mail que ya está en la lista."
    ),
}

_MENSAJES_LINEA = {
    "linea_tipo_invalido": "La línea no es texto.",
    "linea_caracteres_invalidos": (
        "La línea tiene caracteres que no se pueden usar."
    ),
    "linea_multiple": "La línea tiene que ser una sola línea de texto.",
    "linea_vacia": "La línea está vacía.",
    "linea_excedida": "La línea es demasiado larga.",
    "linea_corta": "La línea es demasiado corta.",
    "unauthorized_number": "La línea no puede llevar cifras.",
    "unauthorized_date": "La línea no puede llevar fechas.",
    "unauthorized_duration": "La línea no puede llevar duraciones.",
    "unauthorized_email": "La línea no puede llevar correos.",
    "unauthorized_url": "La línea no puede llevar enlaces.",
    "unauthorized_amount": "La línea no puede llevar importes.",
    "unauthorized_place": "La línea no puede nombrar lugares.",
    "unauthorized_action_claim": (
        "La línea no puede afirmar acciones fuera del certificado."
    ),
    "non_rioplatense_register": "La línea no usa el registro rioplatense.",
    "unauthorized_fact_claim": (
        "La línea no puede afirmar hechos que van en la ficha de la "
        "actividad o en la plantilla."
    ),
    "prompt_injection_echo": "La línea no puede llevar instrucciones.",
    "source_fact_in_creative_field": (
        "La línea repite el título de la actividad: ese dato ya lo pone "
        "la plantilla."
    ),
}

_AVISOS_CONFLICTO = {
    "otro_generador": (
        "Esa lista ya está registrada por otra identidad: el lote sólo "
        "lo puede aprobar quien lo generó."
    ),
    "actividad_distinta": (
        "Esa lista ya está registrada con otra ficha de actividad. "
        "Revisá la fuente institucional: no se reemplaza lo aprobado."
    ),
    "linea_distinta": (
        "Esa lista ya está registrada con otra línea descriptiva. La "
        "redacción nueva no reemplaza a la que ya se pidió: revisala en "
        "el lote existente."
    ),
}

_CODIGOS_LISTA = frozenset(
    codigo
    for codigo in _MENSAJES_CAMPO
    if codigo.startswith("lista_cierre")
)


def parsear_csv_lista_cierre(contenido: bytes) -> tuple[PersonaCierre, ...]:
    """Bytes del upload → personas validadas, toda o nada.

    Acota los bytes, exige UTF-8 y la cabecera contractual con «;» o «,»
    bien delimitados, y después le da cada fila al `parsear_lista_cierre`
    del circuito: las mismas reglas de la emisión, con el número de fila
    del archivo en cada rechazo.
    """
    if not contenido:
        raise ListaCierreError("lista_cierre_csv_vacia")
    if len(contenido) > MAX_CSV_BYTES:
        raise ListaCierreError("lista_cierre_csv_grande")
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ListaCierreError("lista_cierre_csv_codificacion") from None
    filas = _filas_delimitadas(texto)
    con_datos = sum(1 for fila in filas[1:] if any(str(c).strip() for c in fila))
    if con_datos > MAX_CSV_FILAS:
        raise ListaCierreError("lista_cierre_csv_filas")
    # Contrato estricto de seis columnas por fila: el parser del circuito
    # trunca celdas extra porque la planilla las arrastra vacías, pero un
    # CSV mal armado no se arregla adivinando.
    for indice, fila in enumerate(filas[1:], start=2):
        if all(not str(c).strip() for c in fila):
            continue
        if len(fila) != len(COLUMNAS_LISTA_CIERRE):
            raise ListaCierreError(
                "lista_cierre_fila_invalida", fila=indice
            )
    correos: set[str] = set()
    for indice, fila in enumerate(filas[1:], start=2):
        if not any(c.strip() for c in fila):
            continue
        correo = fila[3].strip().casefold()
        if correo in correos:
            raise ListaCierreError("lista_cierre_duplicada", fila=indice)
        correos.add(correo)
    return parsear_lista_cierre(filas)


def _es_xlsx(nombre: str, contenido: bytes) -> bool:
    """El Excel se reconoce por magia zip + extensión, nunca por MIME."""
    return nombre.casefold().endswith(".xlsx") and contenido.startswith(
        b"PK\x03\x04"
    )


def _filas_delimitadas(texto: str) -> list[list[str]]:
    """Filas del CSV con el delimitador que deja la cabecera contractual.

    Se prueba «;» y «,» contra la primera fila: sólo se acepta el
    delimitador que la separa en las seis columnas, en ese orden. Un
    archivo sin cabecera o delimitado de otra forma se rechaza.
    """
    for delimitador in (";", ","):
        try:
            filas = [
                [str(celda) for celda in fila]
                for fila in csv.reader(
                    io.StringIO(texto), delimiter=delimitador, strict=True
                )
            ]
        except csv.Error:
            continue
        if not filas:
            continue
        if [c.strip() for c in filas[0]] == list(COLUMNAS_LISTA_CIERRE):
            return filas
    raise ListaCierreError("lista_cierre_csv_cabecera")


async def _formulario_acotado(request: Request) -> FormData:
    try:
        return await leer_formulario_acotado(
            request, max_bytes=MAX_FORM_BYTES, max_files=1, max_fields=5
        )
    except HTTPException as error:
        codigo = (
            "lista_cierre_csv_grande" if error.status_code == 413
            else "lista_cierre_csv_cabecera"
        )
        raise ListaCierreError(codigo) from None


def registrar_rutas_pedido_certificados(
    app: FastAPI,
    *,
    repositorio: RepositorioPedidoPuerto,
    autorizar: Autorizar,
    render: Render,
    rol_de: RolDe,
    csrf_ok: CsrfOk,
    destino_login: DestinoLogin,
    actividades: Iterable[Mapping[str, str]],
) -> None:
    """Cablea el pedido del lote; la lógica queda en este módulo.

    Las rutas fijas (`/certificados/pedir`, `/certificados/plantilla-
    lista.csv`) se registran antes que `/certificados/{id_lote}`: con el
    orden al revés, «pedir» resolvería como un id de lote.
    """
    actividades_por_id = {
        str(fila.get("id_actividad", "")): fila for fila in actividades
    }

    def _fichas_actividades() -> list[dict[str, object]]:
        fichas = []
        for id_actividad, fila in actividades_por_id.items():
            datos = {
                campo: str(fila.get(campo, "") or "").strip()
                for campo in _REQUERIDOS_ACTIVIDAD
            }
            fecha_fin = str(fila.get("fecha_fin", "") or "").strip()
            fichas.append(
                {
                    "id": id_actividad,
                    "titulo": datos["titulo"] or id_actividad,
                    "fechas": (
                        f"{datos['fecha_inicio']} al {fecha_fin}"
                        if fecha_fin
                        else datos["fecha_inicio"]
                    ),
                    "horas": datos["duracion_horas"],
                    "modalidad": datos["modalidad"],
                    "organiza": datos["organiza"],
                    "incompleta": not all(datos.values()),
                }
            )
        return fichas

    def _render_form(
        request: Request,
        sesion: Sesion,
        *,
        errores: dict[str, str] | None = None,
        detalles: dict[str, object] | None = None,
        valores: dict[str, str] | None = None,
        aviso: str | None = None,
        aviso_lote: str | None = None,
        status_code: int = 200,
    ) -> HTMLResponse:
        errores = errores or {}
        detalles = detalles or {}
        return render(
            "pedido_certificados.html",
            request,
            sesion=sesion,
            csrf=sesion.csrf_token,
            actividades=_fichas_actividades(),
            errores=errores,
            mensajes=_mensajes(errores, detalles),
            valores=valores or {},
            aviso=aviso,
            aviso_lote=aviso_lote,
            max_kb=MAX_CSV_BYTES // 1024,
            max_xlsx_mb=MAX_XLSX_BYTES // (1024 * 1024),
            max_filas=MAX_CSV_FILAS,
            max_filas_inscripcion=MAX_FILAS_INSCRIPCION,
            max_linea=MAX_LINEA_CARACTERES,
            columnas_csv=COLUMNAS_CSV,
            status_code=status_code,
        )

    def _mensajes(
        errores: dict[str, str], detalles: dict[str, object]
    ) -> dict[str, list[str]]:
        """Texto humano de cada error, con los detalles sin PII."""
        mensajes: dict[str, list[str]] = {}
        for campo, codigo in errores.items():
            if campo == "linea" and codigo == "linea_descriptiva_invalida":
                codigos = detalles.get("linea_codigos", ())
                mensajes[campo] = [
                    _MENSAJES_LINEA.get(c, f"La línea no sirve ({c}).")
                    for c in codigos
                ] or [_MENSAJES_CAMPO[codigo]]
                continue
            plantilla = _MENSAJES_CAMPO.get(codigo)
            if plantilla is None:
                mensajes[campo] = [f"No se pudo crear el lote ({codigo})."]
                continue
            mensajes[campo] = [
                plantilla.format(
                    fila=detalles.get("lista_fila", "?"),
                    faltantes=", ".join(
                        detalles.get("actividad_faltantes", ())
                    ),
                    max_kb=MAX_CSV_BYTES // 1024,
                    max_xlsx_mb=MAX_XLSX_BYTES // (1024 * 1024),
                    max_filas=MAX_CSV_FILAS,
                    max_filas_inscripcion=MAX_FILAS_INSCRIPCION,
                )
            ]
        return mensajes

    @app.get("/certificados/pedir", response_class=HTMLResponse)
    def pedir_form(request: Request) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        if rol_de(sesion) != ROL_APROBADOR_CONTENIDO:
            return render("sin_permiso.html", request, status_code=403)
        return _render_form(request, sesion)

    @app.get("/certificados/plantilla-lista.csv")
    def plantilla_lista(request: Request) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        if rol_de(sesion) != ROL_APROBADOR_CONTENIDO:
            return render("sin_permiso.html", request, status_code=403)
        return Response(
            content=_PLANTILLA_LISTA_CSV,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": (
                    'attachment; filename="plantilla-lista-cierre.csv"'
                )
            },
        )

    @app.post("/certificados/pedir", response_class=HTMLResponse)
    async def pedir(request: Request) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        if rol_de(sesion) != ROL_APROBADOR_CONTENIDO:
            return render("sin_permiso.html", request, status_code=403)
        try:
            form = await _formulario_acotado(request)
        except ListaCierreError as error:
            return _render_form(
                request, sesion, errores={"lista": error.code}, status_code=400
            )
        if not csrf_ok(sesion, str(form.get("csrf", ""))):
            await form.close()
            return render("sin_permiso.html", request, status_code=403)

        valores = {
            "actividad": str(form.get("actividad", "")).strip(),
            "linea_descriptiva": str(
                form.get("linea_descriptiva", "")
            ).strip(),
            "tratamiento": str(form.get("tratamiento", "")).strip(),
            "condicion": str(form.get("condicion", "")).strip(),
        }
        errores: dict[str, str] = {}
        detalles: dict[str, object] = {}

        id_actividad = valores["actividad"]
        fila_actividad = actividades_por_id.get(id_actividad)
        datos_actividad: dict[str, str] = {}
        if fila_actividad is None:
            errores["actividad"] = "actividad_invalida"
        else:
            datos_actividad = {
                campo: str(fila_actividad.get(campo, "") or "").strip()
                for campo in _REQUERIDOS_ACTIVIDAD
            }
            faltantes = [
                campo
                for campo in _REQUERIDOS_ACTIVIDAD
                if not datos_actividad[campo]
            ]
            if faltantes:
                errores["actividad"] = "actividad_datos_incompletos"
                detalles["actividad_faltantes"] = faltantes
            fecha_fin = str(fila_actividad.get("fecha_fin", "") or "").strip()
            if fecha_fin:
                datos_actividad["fecha_fin"] = fecha_fin

        linea = normalizar_linea(valores["linea_descriptiva"])
        if not linea:
            errores["linea"] = "linea_descriptiva_ausente"
        else:
            codigos = validar_linea_descriptiva(
                valores["linea_descriptiva"],
                titulo_actividad=datos_actividad.get("titulo"),
            )
            if codigos:
                errores["linea"] = "linea_descriptiva_invalida"
                detalles["linea_codigos"] = codigos

        upload = form.get("lista")
        personas: tuple[PersonaCierre, ...] = ()
        if not isinstance(upload, UploadFile) or not upload.filename:
            errores["lista"] = "lista_cierre_csv_ausente"
        else:
            contenido = await upload.read(MAX_XLSX_BYTES + 1)
            try:
                if _es_xlsx(upload.filename, contenido):
                    personas = parsear_xlsx_lista_cierre(
                        contenido,
                        tratamiento=valores["tratamiento"],
                        condicion=valores["condicion"],
                    )
                else:
                    personas = parsear_csv_lista_cierre(contenido)
            except ListaCierreError as error:
                errores["lista"] = error.code
                if error.fila is not None:
                    detalles["lista_fila"] = error.fila

        await form.close()
        if errores:
            return _render_form(
                request,
                sesion,
                errores=errores,
                detalles=detalles,
                valores=valores,
                status_code=400,
            )

        hash_generador = hash_correo(sesion.correo)
        try:
            lote = repositorio.crear(
                id_actividad=id_actividad,
                actividad=datos_actividad,
                personas=personas,
                linea_descriptiva=linea,
                generada_por_hash=hash_generador,
                origen_creacion=sesion.origen,
            )
        except LoteCertificadosError as error:
            if error.code in _CODIGOS_LISTA:
                campo = "lista"
            elif error.code.startswith("linea"):
                campo = "linea"
            elif error.code.startswith("actividad"):
                campo = "actividad"
            else:
                return _render_form(
                    request,
                    sesion,
                    valores=valores,
                    aviso=f"No se pudo crear el lote ({error.code}).",
                    status_code=409,
                )
            return _render_form(
                request,
                sesion,
                errores={campo: error.code},
                valores=valores,
                status_code=400,
            )
        except ListaCierreError as error:
            return _render_form(
                request,
                sesion,
                errores={"lista": error.code},
                detalles=(
                    {"lista_fila": error.fila}
                    if error.fila is not None
                    else {}
                ),
                valores=valores,
                status_code=400,
            )

        conflicto = None
        if lote.generada_por_hash != hash_generador:
            conflicto = "otro_generador"
        elif lote.actividad != datos_actividad:
            conflicto = "actividad_distinta"
        elif lote.linea_descriptiva_hash != hash_linea_descriptiva(linea):
            conflicto = "linea_distinta"
        if conflicto is not None:
            return _render_form(
                request,
                sesion,
                valores=valores,
                aviso=_AVISOS_CONFLICTO[conflicto],
                aviso_lote=lote.id_lote,
                status_code=409,
            )
        return RedirectResponse(
            f"/certificados/{lote.id_lote}", status_code=303
        )


__all__ = [
    "COLUMNAS_CSV",
    "MAX_CSV_BYTES",
    "MAX_CSV_FILAS",
    "MAX_LINEA_CARACTERES",
    "MAX_XLSX_BYTES",
    "RepositorioPedidoPuerto",
    "parsear_csv_lista_cierre",
    "registrar_rutas_pedido_certificados",
]
