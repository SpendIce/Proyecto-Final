"""Canal del Form con la firma de área opcional y los públicos del catálogo
cerrado (#154).

La hoja de respuestas v3 lee las columnas estructuradas del contrato
`canal_form_respuestas_v3`: tipo de gacetilla, actividad condicional, área
emisora, firma de área como opción separada del área, públicos
destinatarios por catálogo cerrado y pedido libre. Estas pruebas ejercitan
el adapter: la firma es un campo del pedido y los públicos sólo deciden a
quién se envía la pieza —quedan declarados en el registro y visibles en el
aviso, sin entrar al prompt ni cambiar el texto. Las filas que no cumplen
las listas cerradas terminan en un desenlace acotado del canal, sin
generación y sin núcleo. Las lecturas de las formas v1 y v2 quedan
cubiertas por `tests/test_canal_form.py` y
`tests/test_canal_form_respuestas_v2.py`, con un caso de regresión v2 al
final.
"""

from __future__ import annotations

import base64
import json
from email import message_from_bytes, policy
from pathlib import Path

from agente1.canal import atender_canal
from agente1.canal_form import (
    ATENDIDOS_NOMBRE,
    CONTRATO_HOJA_V1,
    CONTRATO_HOJA_V2,
    CONTRATO_HOJA_V3,
    CanalFormPedidos,
    PadronRoles,
    cargar_configuracion_canal_form,
    nombre_de_publico,
)
from agente1.confirmaciones import MARCADOR_BORRADOR
from agente1.fuentes import CsvFuenteSolicitudes
from agente1.gacetillas import construir_prompt
from agente1.gmail_envio import GmailDestinoConfirmaciones
from agente1.google_workspace import GoogleSheetsLectorValores, RespuestaHttp
from agente1.procesamiento import FakeGenerator

ROOT = Path(__file__).parents[1]
DATASET = ROOT / "data" / "actividades_sinteticas.csv"
CONTRATO_V3 = (
    ROOT
    / "src"
    / "agente1"
    / "contracts"
    / "canal_form_respuestas_v3.json"
)
CATALOGO_PUBLICOS = (
    ROOT
    / "src"
    / "agente1"
    / "contracts"
    / "publicos_destinatarios_v1.json"
)

CORREO_SOLICITANTE = "solicitante@example.invalid"
CORREO_DESCONOCIDO = "fuera@example.invalid"
ROL_HABILITADO = "coordinador_seu"
ID_ACTIVIDAD = "SYN-001"
AREA_VALIDA = "secretaria_academica"
PUBLICO_VALIDO = "alumnos_ingenieria"
NOMBRE_PUBLICO = "Alumnos de ingeniería"

MARCA = "2026-11-11 09:30:00"
FORM_ID = "FORM_ID_RESPUESTAS-10"
ENTRY_ID = "entry.987654321"

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


class GeneradorEspia(FakeGenerator):
    """FakeGenerator que recuerda los prompts que recibió.

    La barrera de #154 —el público nunca entra al prompt— se verifica sobre
    el prompt real que el pipeline le pasa al modelo, no sobre una
    suposición de qué campos viajan.
    """

    def __init__(self, respuesta: str) -> None:
        super().__init__(respuesta)
        self.prompts: list[str] = []

    def generar(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return super().generar(prompt)


def fila_v3(
    tipo: str,
    *,
    actividad: str = "",
    area: str = "",
    firma: str = "",
    publicos: str = "",
    texto: str = "",
    correo: str = CORREO_SOLICITANTE,
    marca: str = MARCA,
) -> list[str]:
    """Una fila tal como la deja el Form v3 con las preguntas fijas."""

    return [marca, correo, tipo, actividad, area, firma, publicos, texto]


ENCABEZADOS_V3 = [
    "Marca temporal",
    "Dirección de correo electrónico",
    "Tipo de gacetilla",
    "Actividad",
    "Área emisora",
    "¿La pieza lleva firma de área?",
    "Públicos destinatarios",
    "Escribí tu pedido",
]


def _padron() -> PadronRoles:
    return PadronRoles({CORREO_SOLICITANTE: ROL_HABILITADO})


def crear_canal(
    tmp_path: Path,
    *,
    values: list[list[object]],
    contrato_hoja: str = CONTRATO_HOJA_V3,
) -> tuple[CanalFormPedidos, TransporteRouter]:
    router = TransporteRouter(values=values)
    canal = CanalFormPedidos(
        lector=GoogleSheetsLectorValores(
            spreadsheet_id="sheet_respuestas-1",
            rango_a1="'Form Responses 1'!A1:H200",
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
    *,
    generator: FakeGenerator | None = None,
) -> tuple[object, ...]:
    return atender_canal(
        canal,
        fuente=CsvFuenteSolicitudes(DATASET),
        directorio_salida=tmp_path / "salida",
        generator=generator or FakeGenerator(BORRADOR_CONFORME),
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


# --- El contrato y el catálogo de públicos -----------------------------------


def test_el_contrato_v3_declara_las_columnas_nuevas() -> None:
    contrato = json.loads(CONTRATO_V3.read_text(encoding="utf-8"))
    columnas = contrato["columnas"]
    # Las columnas v2 conservan su posición: una hoja v2 no cambia de forma
    # por la llegada de la v3.
    assert columnas["marca_temporal"] == 0
    assert columnas["correo"] == 1
    assert columnas["tipo_gacetilla"] == 2
    assert columnas["actividad"] == 3
    assert columnas["area_emisora"] == 4
    assert columnas["pedido"] == 7
    # Las nuevas se agregan entre el área y el pedido, como las declara el
    # contrato versionado.
    assert columnas["firma_de_area"] == 5
    assert columnas["publicos"] == 6


def test_el_catalogo_de_publicos_lleva_solo_id_y_nombre() -> None:
    catalogo = json.loads(CATALOGO_PUBLICOS.read_text(encoding="utf-8"))
    publicos = catalogo["publicos"]
    assert [publico["id"] for publico in publicos] == [PUBLICO_VALIDO]
    for publico in publicos:
        # El repo es público: las direcciones de los grupos de Workspace no
        # se versionan; el catálogo lleva sólo id y nombre.
        assert set(publico) == {"id", "nombre"}
    assert NOMBRE_PUBLICO in json.dumps(catalogo, ensure_ascii=False)


def test_el_nombre_del_publico_sale_del_catalogo_cerrado() -> None:
    assert nombre_de_publico(PUBLICO_VALIDO) == NOMBRE_PUBLICO
    assert nombre_de_publico("padres") is None
    assert nombre_de_publico("") is None


def test_config_acepta_las_tres_versiones_de_hoja() -> None:
    env_base = {
        "AGENTE1_FORM_PEDIDOS_SHEET_ID": "sheet_respuestas-1",
        "AGENTE1_FORM_PEDIDOS_RANGO_A1": "'Form Responses 1'!A1:H200",
        "AGENTE1_FORM_PEDIDOS_FORM_ID": "form_respuestas-1",
        "AGENTE1_FORM_PEDIDOS_ENTRY_ID": ENTRY_ID,
        "AGENTE1_FORM_PEDIDOS_TIMEOUT_S": "5",
        "AGENTE1_PADRON_ROLES_PATH": "/tmp/padron-roles.csv",
    }
    for version in (CONTRATO_HOJA_V1, CONTRATO_HOJA_V2, CONTRATO_HOJA_V3):
        config = cargar_configuracion_canal_form(
            dict(env_base, AGENTE1_FORM_PEDIDOS_HOJA_CONTRATO=version)
        )
        assert config.contrato_hoja == version


# --- Despacho con públicos ---------------------------------------------------


def test_difusion_con_un_publico_despacha_y_lo_declara(tmp_path: Path) -> None:
    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V3,
            fila_v3(
                "difusion_de_actividad",
                actividad=ID_ACTIVIDAD,
                publicos=PUBLICO_VALIDO,
            ),
        ],
    )
    pendientes = canal.leer_pendientes()
    assert len(pendientes) == 1
    pedido = pendientes[0]
    # El público es del pedido, no del texto: la estructura lo declara y el
    # vocabulario determinístico del despacho no lo lleva.
    assert pedido.texto == f"gacetilla actividad {ID_ACTIVIDAD}"
    assert pedido.estructura == {
        "tipo": "difusion_de_actividad",
        "actividad": ID_ACTIVIDAD,
        "publicos": PUBLICO_VALIDO,
    }

    resultados = _atender(canal, router, tmp_path)
    assert len(resultados) == 1
    assert resultados[0].estado == "PENDIENTE_VALIDACION"

    registro = _atendidos(tmp_path)[0]
    assert registro["contrato_hoja"] == CONTRATO_HOJA_V3
    assert registro["declarado"]["publicos"] == PUBLICO_VALIDO

    # La revisión lo ve con el nombre institucional del catálogo.
    cuerpo = _cuerpo(_correos_gmail(router)[0])
    assert f"Públicos: {NOMBRE_PUBLICO}" in cuerpo


def test_el_publico_no_entra_al_prompt_del_modelo(tmp_path: Path) -> None:
    """El prompt que recibe el modelo no lleva ni el id ni el nombre."""

    espia = GeneradorEspia(BORRADOR_CONFORME)
    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V3,
            fila_v3(
                "difusion_de_actividad",
                actividad=ID_ACTIVIDAD,
                publicos=PUBLICO_VALIDO,
            ),
        ],
    )
    resultados = _atender(canal, router, tmp_path, generator=espia)
    assert resultados[0].estado == "PENDIENTE_VALIDACION"
    assert len(espia.prompts) == 1
    prompt = espia.prompts[0]
    assert PUBLICO_VALIDO not in prompt
    assert NOMBRE_PUBLICO not in prompt
    assert "publicos" not in prompt


def test_el_publico_no_cambia_el_cuerpo_generado(tmp_path: Path) -> None:
    """El mismo pedido con y sin la columna de público produce el mismo borrador.

    El pipeline v3 no despacha sin público (#154), así que la comparación es
    contra la hoja v2, que no tiene la columna: el público no puede alterar
    la pieza porque nunca viaja a ella.
    """

    def borrador_de(
        directorio: Path, values: list[list[object]], contrato: str
    ) -> str:
        canal, router = crear_canal(
            directorio, values=values, contrato_hoja=contrato
        )
        resultados = _atender(canal, router, directorio)
        assert resultados[0].estado == "PENDIENTE_VALIDACION"
        ref = resultados[0].referencia_borrador
        assert ref is not None and ref.path is not None
        return ref.path.read_text(encoding="utf-8")

    con_publico = borrador_de(
        tmp_path / "v3",
        [
            ENCABEZADOS_V3,
            fila_v3(
                "difusion_de_actividad",
                actividad=ID_ACTIVIDAD,
                publicos=PUBLICO_VALIDO,
            ),
        ],
        CONTRATO_HOJA_V3,
    )
    sin_publico = borrador_de(
        tmp_path / "v2",
        [
            [
                "Marca temporal",
                "Dirección de correo electrónico",
                "Tipo de gacetilla",
                "Actividad",
                "Área emisora",
                "Escribí tu pedido",
            ],
            [
                MARCA,
                CORREO_SOLICITANTE,
                "difusion_de_actividad",
                ID_ACTIVIDAD,
                "",
                "",
            ],
        ],
        CONTRATO_HOJA_V2,
    )
    assert con_publico == sin_publico
    assert NOMBRE_PUBLICO not in con_publico
    assert PUBLICO_VALIDO not in con_publico


def test_el_prompt_del_tipo_excluye_publicos() -> None:
    """Barrera de `construir_prompt`: `publicos` nunca entra a datos_fuente.

    La fila de actividades no trae `publicos`, pero el filtro no depende del
    llamador: un campo del pedido que decide a quién se envía no puede
    terminar adentro del prompt aunque llegue.
    """

    prompt = construir_prompt(
        "saludo_o_efemeride",
        {
            "efemeride": "Día del Ejército",
            "fecha": "2026-05-29",
            "publicos": PUBLICO_VALIDO,
        },
    )
    assert PUBLICO_VALIDO not in prompt
    assert "publicos" not in prompt


# --- Firma de área como opción separada --------------------------------------


def test_firma_de_area_default_conserva_la_firma(tmp_path: Path) -> None:
    """Celda vacía y «Sí» valen lo mismo: la pieza firma con el área.

    Los tipos con área hoy bloquean en `tipo_sin_despacho` —el canal aún no
    les pide los datos que confirman—, así que el código que prueba el
    campo válido es ese: la validación de la firma pasó antes.
    """

    for indice, firma in enumerate(("", "Sí", "si", "No", "no")):
        subdir = tmp_path / str(indice)
        canal, router = crear_canal(
            subdir,
            values=[
                ENCABEZADOS_V3,
                fila_v3(
                    "aviso_de_otra_area",
                    area=AREA_VALIDA,
                    firma=firma,
                    publicos=PUBLICO_VALIDO,
                ),
            ],
        )
        _assert_bloqueo(
            subdir,
            router,
            canal,
            codigo="tipo_sin_despacho",
            trozo_mensaje="todavía no despacha en este canal",
            texto_prohibido=None,
        )


def test_firma_de_area_fuera_de_las_opciones_bloquea(tmp_path: Path) -> None:
    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V3,
            fila_v3(
                "aviso_de_otra_area",
                area=AREA_VALIDA,
                firma="quizá",
                publicos=PUBLICO_VALIDO,
            ),
        ],
    )
    _assert_bloqueo(
        tmp_path,
        router,
        canal,
        codigo="firma_de_area_invalida",
        trozo_mensaje="firma de área",
        texto_prohibido="quizá",
    )


def test_tipo_sin_area_no_lee_la_celda_de_firma(tmp_path: Path) -> None:
    """En los tipos sin área la firma no se lee: «no» no puede bloquearlos."""

    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V3,
            fila_v3(
                "cronica_de_evento",
                firma="No",
                publicos=PUBLICO_VALIDO,
            ),
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


# --- Los bloqueos del canal por públicos --------------------------------------


def test_pedido_sin_publico_no_genera(tmp_path: Path) -> None:
    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V3,
            fila_v3("difusion_de_actividad", actividad=ID_ACTIVIDAD),
        ],
    )
    _assert_bloqueo(
        tmp_path,
        router,
        canal,
        codigo="publicos_requeridos",
        trozo_mensaje="elegí al menos uno",
        texto_prohibido=None,
    )


def test_publico_fuera_del_catalogo_bloquea(tmp_path: Path) -> None:
    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V3,
            fila_v3(
                "difusion_de_actividad",
                actividad=ID_ACTIVIDAD,
                publicos="padres",
            ),
        ],
    )
    _assert_bloqueo(
        tmp_path,
        router,
        canal,
        codigo="publico_fuera_de_padron",
        trozo_mensaje="catálogo cerrado",
        texto_prohibido="padres",
    )


def test_publico_repetido_bloquea(tmp_path: Path) -> None:
    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V3,
            fila_v3(
                "difusion_de_actividad",
                actividad=ID_ACTIVIDAD,
                publicos=f"{PUBLICO_VALIDO},{PUBLICO_VALIDO}",
            ),
        ],
    )
    _assert_bloqueo(
        tmp_path,
        router,
        canal,
        codigo="publicos_repetidos",
        trozo_mensaje="más de una vez",
        texto_prohibido=None,
    )


def test_pedido_estructurado_con_publicos_declarados_en_el_registro(
    tmp_path: Path,
) -> None:
    """El público queda declarado en la solicitud y visible en la revisión."""

    canal, router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_V3,
            fila_v3(
                "difusion_de_actividad",
                actividad=ID_ACTIVIDAD,
                publicos=PUBLICO_VALIDO,
            ),
        ],
    )
    _atender(canal, router, tmp_path)
    registro = _atendidos(tmp_path)[0]
    assert registro["declarado"] == {
        "tipo": "difusion_de_actividad",
        "actividad": ID_ACTIVIDAD,
        "publicos": PUBLICO_VALIDO,
    }


# --- Regresión v2 -------------------------------------------------------------


def test_lectura_v2_sigue_igual(tmp_path: Path) -> None:
    """Regresión: la hoja v2 no tiene las columnas nuevas y se lee como antes."""

    valores = [
        [
            "Marca temporal",
            "Dirección de correo electrónico",
            "Tipo de gacetilla",
            "Actividad",
            "Área emisora",
            "Escribí tu pedido",
        ],
        [MARCA, CORREO_SOLICITANTE, "difusion_de_actividad", ID_ACTIVIDAD, "", ""],
    ]
    canal, router = crear_canal(
        tmp_path, values=valores, contrato_hoja=CONTRATO_HOJA_V2
    )
    pendientes = canal.leer_pendientes()
    assert len(pendientes) == 1
    assert pendientes[0].estructura == {
        "tipo": "difusion_de_actividad",
        "actividad": ID_ACTIVIDAD,
    }
    resultados = _atender(canal, router, tmp_path)
    assert resultados[0].estado == "PENDIENTE_VALIDACION"
    registro = _atendidos(tmp_path)[0]
    assert registro["contrato_hoja"] == CONTRATO_HOJA_V2
    assert "publicos" not in registro["declarado"]
    # Sin la columna de públicos el aviso queda como el de v2.
    cuerpo = _cuerpo(_correos_gmail(router)[0])
    assert "Públicos:" not in cuerpo
