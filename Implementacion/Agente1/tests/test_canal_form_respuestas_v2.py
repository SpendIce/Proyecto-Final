"""Canal del Form con el tipo declarado, la actividad condicional y el área
emisora por padrón (#122).

La hoja de respuestas v2 lee las columnas estructuradas del contrato
`canal_form_respuestas_v2` (tipo de gacetilla, actividad condicional, área
emisora, pedido libre). Estas pruebas ejercitan el adapter: el despacho
estructurado entra por el clasificador determinístico de siempre y las filas
que no cumplen las listas cerradas terminan en un desenlace acotado del
canal, sin generación y sin núcleo. La lectura de tres columnas de la forma
v1 queda cubierta por `tests/test_canal_form.py` y un caso de regresión al
final.

La firma de área de la pieza sale del padrón cerrado
(`contracts/areas_emisoras_v1.json`) vía el placeholder `{area_emisora}` de
la forma declarada del tipo: mismas formas de siempre, valor desde el
padrón.
"""

from __future__ import annotations

import base64
import json
from email import message_from_bytes, policy
from pathlib import Path

import pytest

from agente1.canal import atender_canal
from agente1.canal_form import (
    ATENDIDOS_NOMBRE,
    CONTRATO_HOJA_V1,
    CONTRATO_HOJA_V2,
    ETIQUETA_SIN_ACTIVIDAD,
    CanalFormPedidos,
    PadronRoles,
    cargar_configuracion_canal_form,
    es_id_actividad,
    es_opcion_sin_actividad,
    firma_de_area,
)
from agente1.confirmaciones import MARCADOR_BORRADOR
from agente1.fuentes import CsvFuenteSolicitudes
from agente1.gacetillas import confirmar_pieza
from agente1.gmail_envio import GmailDestinoConfirmaciones
from agente1.google_workspace import GoogleSheetsLectorValores, RespuestaHttp
from agente1.procesamiento import FakeGenerator

ROOT = Path(__file__).parents[1]
DATASET = ROOT / "data" / "actividades_sinteticas.csv"

CORREO_SOLICITANTE = "solicitante@example.invalid"
CORREO_DESCONOCIDO = "fuera@example.invalid"
ROL_HABILITADO = "coordinador_seu"
ID_ACTIVIDAD = "SYN-001"
AREA_VALIDA = "secretaria_academica"
TIPO_NO_REQUIERE_ACTIVIDAD = "cronica_de_evento"

MARCA = "2026-10-17 09:30:00"
FORM_ID = "FORM_ID_RESPUESTAS-9"
ENTRY_ID = "entry.123456789"

BORRADOR_CONFORME = (
    "## TÍTULO\n"
    "Taller sintético de vinculación\n\n"
    "## DATOS DE LA ACTIVIDAD\n"
    "Fecha: 2026-08-05\n"
    "Organiza: Departamento de Cursos Complementarios\n"
    "Lugar: Aula 12, Av. Cabildo 15\n\n"
    "## CONTACTO\n"
    "cursos@fie.undef.edu.ar\n\n"
    "## BAJADA\n"
    "Bajada breve de prueba.\n\n"
    "## CUERPO\n"
    "Cuerpo breve de prueba."
)


class TokenFijo:
    """Proveedor de token fijo, igual que en `tests/test_canal_form.py`."""

    def obtener_access_token(self) -> str:
        return "token_fijo_valido-vial-analgesia-vivida-fija"


class TransporteRouter:
    """Transporte fake por host: Sheet de respuestas y Gmail de prueba.

    Sin el host de Docs/Drive: el despacho estructurado usa el destino
    Markdown default, así que un request a otro host rompe la prueba en
    lugar de fingirse.
    """

    def __init__(
        self,
        *,
        values: list[list[object]] | None = None,
        gmail_error: Exception | None = None,
    ) -> None:
        self.values = list(values or [])
        self.gmail_error = gmail_error
        self.solicitudes: list[dict[str, object]] = []

    def request(
        self,
        *,
        method: str,
        host: str,
        target: str,
        headers: dict[str, str],
        body: bytes | None,
        deadline: float,
        max_response_bytes: int,
    ) -> RespuestaHttp:
        self.solicitudes.append(
            {
                "method": method,
                "host": host,
                "target": target,
                "headers": headers,
                "body": body,
                "deadline": deadline,
                "max_response_bytes": max_response_bytes,
            }
        )
        if host == "sheets.googleapis.com":
            return RespuestaHttp(
                200, json.dumps({"values": self.values}).encode("utf-8")
            )
        if host == "gmail.googleapis.com":
            if self.gmail_error is not None:
                raise self.gmail_error
            return RespuestaHttp(200, b'{"id":"msg_enviado-1"}')
        raise AssertionError(f"request a un host no previsto: {host}")


def fila_v2(
    tipo: str,
    *,
    actividad: str = "",
    area: str = "",
    texto: str = "",
    correo: str = CORREO_SOLICITANTE,
    marca: str = MARCA,
) -> list[str]:
    """Una fila tal como la deja el Form v2 con las preguntas fijas."""

    return [marca, correo, tipo, actividad, area, texto]


ENCABEZADOS_V2 = [
    "Marca temporal",
    "Dirección de correo electrónico",
    "Tipo de gacetilla",
    "Actividad",
    "Área emisora",
    "Escribí tu pedido",
]


def _padron() -> PadronRoles:
    return PadronRoles({CORREO_SOLICITANTE: ROL_HABILITADO})


def crear_canal(
    tmp_path: Path,
    *,
    values: list[list[object]],
    contrato_hoja: str = CONTRATO_HOJA_V2,
) -> tuple[CanalFormPedidos, TransporteRouter]:
    router = TransporteRouter(values=values)
    canal = CanalFormPedidos(
        lector=GoogleSheetsLectorValores(
            spreadsheet_id="sheet_respuestas-1",
            rango_a1="'Form Responses 1'!A1:F200",
            token_provider=TokenFijo(),
            transport=router,
            timeout_s=5,
        ),
        padron=_padron(),
        avisos=GmailDestinoConfirmaciones(
            destinatarios_permitidos={CORREO_SOLICITANTE, CORREO_DESCONOCIDO},
            token_provider=TokenFijo(),
            transport=router,
            timeout_s=5,
        ),
        directorio_estado=tmp_path / "estado",
        form_id=FORM_ID,
        entry_id=ENTRY_ID,
        contrato_hoja=contrato_hoja,
    )
    return canal, router


def _atender(
    canal: CanalFormPedidos,
    router: TransporteRouter,
    tmp_path: Path,
) -> tuple[object, ...]:
    return atender_canal(
        canal,
        fuente=CsvFuenteSolicitudes(DATASET),
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(BORRADOR_CONFORME),
    )


def _atendidos(tmp_path: Path) -> list[dict[str, object]]:
    path = tmp_path / "estado" / ATENDIDOS_NOMBRE
    if not path.exists():
        return []
    return [
        json.loads(linea)
        for linea in path.read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]


def _correos_gmail(router: TransporteRouter) -> list[object]:
    """Los mensajes enviados, decodificados del `raw` base64url del request."""

    mensajes = []
    for solicitud in router.solicitudes:
        if solicitud["host"] != "gmail.googleapis.com":
            continue
        crudo = json.loads(solicitud["body"])["raw"]  # type: ignore[index]
        mensajes.append(
            message_from_bytes(
                base64.urlsafe_b64decode(crudo), policy=policy.default
            )
        )
    return mensajes


def _cuerpo(mensaje: object) -> str:
    return str(mensaje.get_body(("plain",)).get_content())


def _assert_bloqueo(
    tmp_path: Path,
    router: TransporteRouter,
    canal: CanalFormPedidos,
    *,
    codigo: str,
    trozo_mensaje: str,
    texto_prohibido: str | None,
) -> None:
    """El desenlace acotado: sin pendientes, un aviso, registro con código.

    `texto_prohibido` es el dato libre de la fila que no puede terminar
    escrito en el registro: ni prosa ni valores que no pasaron la lista
    cerrada.
    """

    assert canal.leer_pendientes() == ()
    mensajes = _correos_gmail(router)
    assert len(mensajes) == 1
    cuerpo = _cuerpo(mensajes[0])
    assert MARCADOR_BORRADOR in cuerpo
    assert trozo_mensaje in cuerpo
    registros = _atendidos(tmp_path)
    assert len(registros) == 1
    registro = registros[0]
    assert registro["estado"] == "INVALIDA"
    assert registro["resultado"] == codigo
    assert registro["origen_hechos"] == "solicitud"
    if texto_prohibido is not None:
        assert texto_prohibido not in json.dumps(registro, ensure_ascii=False)


# --- Listas cerradas que alimenta el canal -----------------------------------


def test_la_opcion_sin_actividad_se_reconoce_normalizada() -> None:
    assert es_opcion_sin_actividad("No es una actividad / no figura")
    assert es_opcion_sin_actividad("  no es UNA actividad / NO figura  ")
    assert not es_opcion_sin_actividad("otra cosa")
    assert not es_opcion_sin_actividad("")


def test_el_identificador_de_actividad_exige_la_forma_de_la_planilla() -> None:
    assert es_id_actividad(ID_ACTIVIDAD)
    assert not es_id_actividad("taller nuevo")
    assert not es_id_actividad("")


def test_la_firma_del_area_sale_del_padron_cerrado() -> None:
    assert firma_de_area("cursos_complementarios") == (
        "Departamento de Cursos Complementarios"
    )
    assert firma_de_area("secretaria_de_extension") == (
        "Secretaría de Extensión Universitaria"
    )
    assert firma_de_area(AREA_VALIDA) == "Secretaría Académica"
    assert firma_de_area("doe") == "DOE"


def test_un_area_fuera_del_padron_no_tiene_firma() -> None:
    assert firma_de_area("estacionamiento") is None
    assert firma_de_area("") is None


def test_la_firma_de_area_se_renderiza_en_la_pieza_sin_tocar_formas() -> None:
    """El wirado área → firma sobre el único hueco que la forma declara.

    La forma del aviso de otra área deja la firma del área como
    `{area_emisora}` en su pie; el valor que imprime la pieza sale del
    padrón cerrado y no del texto libre de la hoja. El bloque `firmante` de
    la forma queda intacto, como el membrete institucional que es.
    """

    pieza, errores = confirmar_pieza(
        "aviso_de_otra_area",
        {
            "titulo": "Estacionamiento parado durante la semana de exámenes",
            "publico": "la comunidad",
            "hecho": "el estacionamiento queda parado",
            "fecha": "2026-11-02",
            "condicion": "con el acceso por la puerta de Cabildo 15",
            "area_emisora": firma_de_area(AREA_VALIDA),
        },
    )
    assert errores == []
    assert "Secretaría Académica" in pieza
    # El membrete institucional de la forma, sin el área equivocada.
    assert "--\n" in pieza
    assert "Facultad de Ingeniería del Ejército" in pieza


# --- Configuración -----------------------------------------------------------

_ENV_BASE = {
    "AGENTE1_FORM_PEDIDOS_SHEET_ID": "sheet_respuestas-1",
    "AGENTE1_FORM_PEDIDOS_RANGO_A1": "'Form Responses 1'!A1:F200",
    "AGENTE1_FORM_PEDIDOS_FORM_ID": "form_respuestas-1",
    "AGENTE1_FORM_PEDIDOS_ENTRY_ID": ENTRY_ID,
    "AGENTE1_FORM_PEDIDOS_TIMEOUT_S": "5",
    "AGENTE1_PADRON_ROLES_PATH": "/tmp/padron-roles.csv",
}


def test_config_sin_variable_queda_en_v1() -> None:
    config = cargar_configuracion_canal_form(_ENV_BASE)
    assert config.contrato_hoja == CONTRATO_HOJA_V1


def test_config_acepta_ambas_versiones_de_hoja() -> None:
    for version in (CONTRATO_HOJA_V1, CONTRATO_HOJA_V2):
        config = cargar_configuracion_canal_form(
            dict(_ENV_BASE, AGENTE1_FORM_PEDIDOS_HOJA_CONTRATO=version)
        )
        assert config.contrato_hoja == version


def test_config_rechaza_hoja_desconocida() -> None:
    with pytest.raises(Exception) as excinfo:
        _ = cargar_configuracion_canal_form(
            dict(
                _ENV_BASE,
                AGENTE1_FORM_PEDIDOS_HOJA_CONTRATO="canal_form_respuestas_v99",
            )
        )
    assert "canal_form_config_invalid" in str(excinfo.value)


def test_config_rechaza_clave_desconocida_del_prefijo() -> None:
    with pytest.raises(Exception) as excinfo:
        _ = cargar_configuracion_canal_form(
            dict(_ENV_BASE, AGENTE1_FORM_PEDIDOS_HOJA_SQL="x")
        )
    assert "canal_form_config_unknown_key" in str(excinfo.value)


# --- Despacho estructurado ---------------------------------------------------


def test_difusion_completa_despacha_por_el_clasificador_de_siempre(
    tmp_path: Path,
) -> None:
    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V2,
            fila_v2("difusion_de_actividad", actividad=ID_ACTIVIDAD),
        ],
    )
    pendientes = canal.leer_pendientes()
    assert len(pendientes) == 1
    pedido = pendientes[0]
    # El texto armado usa el mismo vocabulario determinístico de la
    # repregunta: palabra clave + identificador explícito de la planilla.
    assert pedido.texto == f"gacetilla actividad {ID_ACTIVIDAD}"
    assert pedido.estructura == {
        "tipo": "difusion_de_actividad",
        "actividad": ID_ACTIVIDAD,
    }

    resultados = _atender(canal, router, tmp_path)
    assert len(resultados) == 1
    assert resultados[0].estado == "PENDIENTE_VALIDACION"

    registros = _atendidos(tmp_path)
    assert len(registros) == 1
    registro = registros[0]
    assert registro["contrato_hoja"] == CONTRATO_HOJA_V2
    assert registro["declarado"] == {
        "tipo": "difusion_de_actividad",
        "actividad": ID_ACTIVIDAD,
    }
    # El despacho resuelve los hechos de la pieza en la fuente institucional:
    # eso es lo que declara el registro.
    assert registro["origen_hechos"] == "fuente_institucional"


def test_una_difusion_con_actividad_no_cargada_no_genera(tmp_path: Path) -> None:
    """La planilla manda: el id explícito no registrado falla cerrado.

    Con el identificador bien formado el pedido entra al núcleo igual que
    por prosa, y el núcleo responde `INVALIDA`: desenlace acotado, aviso y
    registro, sin generación. No se inventa ni se da de alta nada.
    """

    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V2,
            fila_v2("difusion_de_actividad", actividad="SYN-999"),
        ],
    )
    pendientes = canal.leer_pendientes()
    assert len(pendientes) == 1
    resultados = _atender(canal, router, tmp_path)
    assert len(resultados) == 1
    assert resultados[0].estado == "INVALIDA"
    registros = _atendidos(tmp_path)
    assert registros[0]["estado"] == "INVALIDA"
    # El pedido estructurado declara lo que trajo y nada más.
    assert registros[0]["declarado"] == {
        "tipo": "difusion_de_actividad",
        "actividad": "SYN-999",
    }


def test_fila_v2_sin_marca_o_con_correo_ajeno_omitida(tmp_path: Path) -> None:
    canal, _ = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V2,
            # Sin correo reconocible no hay a quién responderle: igual que
            # la forma v1, la fila se omite sin pedido.
            fila_v2(
                "difusion_de_actividad",
                actividad=ID_ACTIVIDAD,
                correo="no_es_un_correo",
            ),
            # Sin marca temporal tampoco hay id estable: fila omitida.
            fila_v2(
                "difusion_de_actividad",
                actividad=ID_ACTIVIDAD,
                marca="",
            ),
        ],
    )
    assert canal.leer_pendientes() == ()


# --- Los bloqueos del canal por campo ----------------------------------------


def test_tipo_fuera_de_la_lista_cerrada_no_llega_al_nucleo(tmp_path: Path) -> None:
    canal, router = crear_canal(
        tmp_path,
        values=[ENCABEZADOS_V2, fila_v2("newsletter_equipo_de_visita")],
    )
    _assert_bloqueo(
        tmp_path,
        router,
        canal,
        codigo="tipo_no_declarado",
        trozo_mensaje="lista cerrada de tipos de gacetilla",
        texto_prohibido="newsletter_equipo_de_visita",
    )


def test_difusion_con_la_opcion_sin_actividad_no_registra_nada(
    tmp_path: Path,
) -> None:
    """«No es una actividad / no figura» nunca da de alta una actividad.

    El bloqueo es fail-closed: la planilla manda y cargarla no es tarea de
    este agente. El id de actividad no queda en el registro y no hay
    despacho.
    """

    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V2,
            fila_v2(
                "difusion_de_actividad", actividad=ETIQUETA_SIN_ACTIVIDAD
            ),
        ],
    )
    _assert_bloqueo(
        tmp_path,
        router,
        canal,
        codigo="actividad_no_figura",
        trozo_mensaje="no da de alta ninguna actividad",
        texto_prohibido=ETIQUETA_SIN_ACTIVIDAD,
    )
    registro = _atendidos(tmp_path)[0]
    assert "actividad" not in registro.get("declarado", {})


def test_difusion_con_campo_de_actividad_vacio_termina_acotado(
    tmp_path: Path,
) -> None:

    canal, router = crear_canal(
        tmp_path,
        values=[ENCABEZADOS_V2, fila_v2("difusion_de_actividad", texto="algo")],
    )
    _assert_bloqueo(
        tmp_path,
        router,
        canal,
        codigo="actividad_requerida",
        trozo_mensaje="cargarla no es tarea de este agente",
        texto_prohibido=None,
    )


def test_la_actividad_libre_no_sale_a_resolucion_por_similitud(
    tmp_path: Path,
) -> None:
    """Un texto en la celda de actividad no puede terminar en otra actividad.

    La celda sin forma de identificador ni siquiera viaja: el bloqueo impide
    que el núcleo la resuelva por similitud contra una actividad única y
    clara que puede no ser la que la persona quiso decir.
    """

    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V2,
            fila_v2(
                "difusion_de_actividad",
                actividad="taller de la semana que viene",
            ),
        ],
    )
    _assert_bloqueo(
        tmp_path,
        router,
        canal,
        codigo="actividad_no_identificada",
        trozo_mensaje="la planilla manda",
        texto_prohibido="taller de la semana que viene",
    )
    registro = _atendidos(tmp_path)[0]
    assert "actividad" not in registro.get("declarado", {})


def test_tipo_que_no_lleva_actividad_con_la_celda_elegida_bloquea(
    tmp_path: Path,
) -> None:
    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V2,
            fila_v2(
                TIPO_NO_REQUIERE_ACTIVIDAD,
                actividad=ID_ACTIVIDAD,
            ),
        ],
    )
    _assert_bloqueo(
        tmp_path,
        router,
        canal,
        codigo="actividad_no_aplica",
        trozo_mensaje="no lleva actividad",
        texto_prohibido=ID_ACTIVIDAD,
    )


def test_tipo_que_no_lleva_actividad_acepta_la_opcion_acotada(
    tmp_path: Path,
) -> None:
    """La opción «no figura» lleva los tipos que no la necesitan al bloqueo
    por despacho declarativo, no por campo mal usado."""

    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V2,
            fila_v2(TIPO_NO_REQUIERE_ACTIVIDAD, actividad=ETIQUETA_SIN_ACTIVIDAD),
        ],
    )
    _assert_bloqueo(
        tmp_path,
        router,
        canal,
        codigo="tipo_sin_despacho",
        trozo_mensaje="todavía no despacha en este canal",
        texto_prohibido=ETIQUETA_SIN_ACTIVIDAD,
    )


def test_area_requerida_vacia_bloquea(tmp_path: Path) -> None:

    canal, router = crear_canal(
        tmp_path,
        values=[ENCABEZADOS_V2, fila_v2("aviso_de_otra_area")],
    )
    _assert_bloqueo(
        tmp_path,
        router,
        canal,
        codigo="area_requerida",
        trozo_mensaje="exige área emisora",
        texto_prohibido=None,
    )


def test_area_fuera_del_padron_bloquea(tmp_path: Path) -> None:
    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V2,
            fila_v2("aviso_de_otra_area", area="estacionamiento"),
        ],
    )
    _assert_bloqueo(
        tmp_path,
        router,
        canal,
        codigo="area_fuera_de_padron",
        trozo_mensaje="padrón cerrado del repo",
        texto_prohibido="estacionamiento",
    )


def test_area_que_no_aplica_bloquea_por_tipo(tmp_path: Path) -> None:
    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V2,
            fila_v2(
                "difusion_de_actividad",
                actividad=ID_ACTIVIDAD,
                area="cursos_complementarios",
            ),
        ],
    )
    _assert_bloqueo(
        tmp_path,
        router,
        canal,
        codigo="area_no_aplica",
        trozo_mensaje="aviso de otra área",
        texto_prohibido="cursos_complementarios",
    )


def test_area_confirmada_no_despacha_y_queda_en_el_registro(
    tmp_path: Path,
) -> None:
    """Un pedido estructurado válido de un tipo sin despacho queda bloqueado,
    con el tipo declarado en el registro y su código visible."""

    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V2,
            fila_v2("aviso_de_otra_area", area=AREA_VALIDA),
        ],
    )
    _assert_bloqueo(
        tmp_path,
        router,
        canal,
        codigo="tipo_sin_despacho",
        trozo_mensaje="todavía no despacha en este canal",
        texto_prohibido=None,
    )
    registro = _atendidos(tmp_path)[0]
    assert registro["declarado"] == {"tipo": "aviso_de_otra_area"}


# --- Registro, deduplicación y regresión v1 ----------------------------------


def test_el_registro_de_bloqueos_no_lleva_prosa_ni_correo(tmp_path: Path) -> None:
    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V2,
            fila_v2(
                "difusion_de_actividad",
                actividad=ETIQUETA_SIN_ACTIVIDAD,
                texto="prosa libre que nadie debe ver en el registro",
            ),
        ],
    )
    _atender(canal, router, tmp_path)
    persistido = (tmp_path / "estado" / ATENDIDOS_NOMBRE).read_text(
        encoding="utf-8"
    )
    for prohibido in (
        CORREO_SOLICITANTE,
        ETIQUETA_SIN_ACTIVIDAD,
        "prosa libre que nadie debe ver en el registro",
    ):
        assert prohibido not in persistido


def test_dos_filas_iguales_avisan_una_sola_vez(tmp_path: Path) -> None:
    """La misma respuesta repetida se atiende una vez: aviso y registro.

    El registro de atendidos es la marca de «respondido»: releída la hoja,
    la fila ya no vuelve, igual que un pedido v1.
    """
    valores = [
        ENCABEZADOS_V2,
        fila_v2("difusion_de_actividad", actividad=ETIQUETA_SIN_ACTIVIDAD),
        fila_v2("difusion_de_actividad", actividad=ETIQUETA_SIN_ACTIVIDAD),
    ]
    canal, router = crear_canal(tmp_path, values=valores)
    assert canal.leer_pendientes() == ()
    # Relectura completa: la fila ya está atendida.
    assert canal.leer_pendientes() == ()
    correos = _correos_gmail(router)
    assert len(correos) == 1
    assert len(_atendidos(tmp_path)) == 1


def test_dos_envios_distintos_son_dos_pedidos(tmp_path: Path) -> None:
    """El mismo correo con distinto tipo o actividad produce ids distintos."""

    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V2,
            fila_v2(
                "difusion_de_actividad",
                actividad=ETIQUETA_SIN_ACTIVIDAD,
                marca="2026-10-17 09:30:00",
            ),
            fila_v2(
                "aviso_de_otra_area",
                area=AREA_VALIDA,
                marca="2026-10-17 10:00:00",
            ),
        ],
    )
    assert canal.leer_pendientes() == ()
    correos = _correos_gmail(router)
    assert len(correos) == 2
    registros = _atendidos(tmp_path)
    assert len(registros) == 2
    assert registros[0]["declarado"] == {"tipo": "difusion_de_actividad"}
    assert registros[1]["declarado"] == {"tipo": "aviso_de_otra_area"}


def test_lectura_v1_con_tres_columnas_sigue_igual(tmp_path: Path) -> None:
    """Regresión: la forma v1 es el default y se lee como siempre."""

    valores = [
        [
            "Marca temporal",
            "Dirección de correo electrónico",
            "Escribí tu pedido",
        ],
        [MARCA, CORREO_SOLICITANTE, f"gacetilla {ID_ACTIVIDAD}"],
    ]
    canal, router = crear_canal(
        tmp_path, values=valores, contrato_hoja=CONTRATO_HOJA_V1
    )
    pendientes = canal.leer_pendientes()
    assert len(pendientes) == 1
    assert pendientes[0].texto == f"gacetilla {ID_ACTIVIDAD}"
    assert pendientes[0].estructura is None
    resultados = _atender(canal, router, tmp_path)
    assert resultados[0].estado == "PENDIENTE_VALIDACION"
    registro = _atendidos(tmp_path)[0]
    # En v1 el registro no declara contrato ni estructura: queda como antes.
    assert "contrato_hoja" not in registro
    assert "declarado" not in registro
    assert "origen_hechos" not in registro
