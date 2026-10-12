"""Adapter del canal de pedidos por Google Form (#71).

La Sheet de respuestas se lee por posición de columna con el mismo
`values.get` de Sheets (GET, nunca escritura); la identidad es el correo
verificado y el rol sale del padrón externo (ADR 0005); el aviso sale por
`gmail.send` cercado por la lista de direcciones de prueba; el registro de
atendidos —la única escritura del adapter— nunca lleva prosa ni correo en
claro; y el link de repregunta precarga sólo identificadores, nunca la
prosa del pedido.
"""

from __future__ import annotations

import base64
import json
from email import message_from_bytes, policy
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from agente1.canal import atender_canal
from agente1.canal_form import (
    ATENDIDOS_NOMBRE,
    ROL_NO_EN_PADRON,
    CanalFormError,
    CanalFormPedidos,
    LectorValoresCsv,
    PadronRoles,
    cargar_configuracion_canal_form,
    cargar_padron_roles_csv,
)
from agente1.confirmaciones import MARCADOR_BORRADOR
from agente1.fuentes import CsvFuenteSolicitudes, FuenteSolicitudesError
from agente1.gmail_envio import GMAIL_SEND_TARGET, GmailDestinoConfirmaciones
from agente1.google_workspace import (
    GoogleDrivePlantillaDestinoBorradores,
    GoogleSheetsLectorValores,
    RespuestaHttp,
)
from agente1.interpretacion import RegistroPendientesMemoria
from agente1.procesamiento import FakeGenerator
from agente1.workspace_config import ConfiguracionWorkspaceError

ROOT = Path(__file__).parents[1]
DATASET = ROOT / "data" / "actividades_sinteticas.csv"

CORREO_SOLICITANTE = "solicitante@example.invalid"
CORREO_COORDINADORA = "coordinadora@example.invalid"
CORREO_DESCONOCIDO = "desconocido@example.invalid"
ROL_HABILITADO = "coordinador_seu"
ROL_NO_HABILITADO = "invitado_sin_permisos"

ENCABEZADOS_HOJA = [
    "Marca temporal",
    "Dirección de correo electrónico",
    "Escribí tu pedido",
]
FORM_ID = "FORM_ID_RESPUESTAS-9"
ENTRY_ID = "entry.123456789"

_BORRADOR_CONFORME = (
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

# Mismos hechos que las filas de `_FuenteAmbiguasCompletas`: la ficha que el
# modelo simulado devuelve cuando la referencia ambigua ya se resolvió.
_BORRADOR_AMB_CONFORME = (
    "## TÍTULO\n"
    "Taller de robótica educativa\n\n"
    "## DATOS DE LA ACTIVIDAD\n"
    "Fecha: 2026-09-01\n"
    "Organiza: Equipo ambiguo\n"
    "Lugar: Aula de prueba\n\n"
    "## CONTACTO\n"
    "pruebas@example.invalid\n\n"
    "## BAJADA\n"
    "Bajada breve de prueba.\n\n"
    "## CUERPO\n"
    "Cuerpo breve de prueba."
)


class TokenFijo:
    def __init__(self, token: str = "TOKEN_ULTRA_SECRETO") -> None:
        self.token = token
        self.invocaciones = 0

    def obtener_access_token(self) -> str:
        self.invocaciones += 1
        return self.token


class TransporteRouter:
    """Transporte fake por host: Sheet de respuestas, Drive/Docs y Gmail.

    Enruta por host como haría la red real, así una misma instancia sirve al
    lector de la Sheet, al destino de borradores y al envío del aviso. Un
    request a cualquier otro host —`forms.googleapis.com` ni siquiera está
    en la allowlist— rompe la prueba en lugar de fingirse.
    """

    def __init__(
        self,
        *,
        values: list[list[object]] | None = None,
        doc_id: str = "doc_copiado-777",
        gmail_error: Exception | None = None,
    ) -> None:
        self.values = list(values or [])
        self.doc_id = doc_id
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
        if host == "www.googleapis.com":
            return RespuestaHttp(
                200, json.dumps({"id": self.doc_id}).encode("utf-8")
            )
        if host == "docs.googleapis.com":
            return RespuestaHttp(200, b'{"replies":[{}]}')
        if host == "gmail.googleapis.com":
            if self.gmail_error is not None:
                raise self.gmail_error
            return RespuestaHttp(200, b'{"id":"msg_enviado-1"}')
        raise AssertionError(f"request a un host no previsto: {host}")


def fila_respuesta(
    correo: str = CORREO_SOLICITANTE,
    texto: str = "gacetilla SYN-001",
    marca: str = "2026-10-10 09:00:00",
) -> list[str]:
    """Una fila tal como la deja el Form de correo verificado y un campo."""

    return [marca, correo, texto]


def _padron_default() -> PadronRoles:
    return PadronRoles(
        {
            CORREO_SOLICITANTE: ROL_HABILITADO,
            CORREO_COORDINADORA: "auxiliar_seu",
        }
    )


def crear_canal(
    tmp_path: Path,
    *,
    values: list[list[object]] | None = None,
    padron: PadronRoles | None = None,
    destinatarios: set[str] | None = None,
    gmail_error: Exception | None = None,
    doc_id: str = "doc_copiado-777",
) -> tuple[CanalFormPedidos, TransporteRouter]:
    router = TransporteRouter(
        values=values if values is not None else [ENCABEZADOS_HOJA, fila_respuesta()],
        doc_id=doc_id,
        gmail_error=gmail_error,
    )
    canal = CanalFormPedidos(
        lector=GoogleSheetsLectorValores(
            spreadsheet_id="sheet_respuestas-1",
            rango_a1="'Form Responses 1'!A1:C200",
            token_provider=TokenFijo(),
            transport=router,
            timeout_s=5,
        ),
        padron=padron or _padron_default(),
        avisos=GmailDestinoConfirmaciones(
            destinatarios_permitidos=destinatarios or {CORREO_SOLICITANTE},
            token_provider=TokenFijo(),
            transport=router,
            timeout_s=5,
        ),
        directorio_estado=tmp_path / "estado",
        form_id=FORM_ID,
        entry_id=ENTRY_ID,
    )
    return canal, router


def _destino_drive(router: TransporteRouter) -> GoogleDrivePlantillaDestinoBorradores:
    return GoogleDrivePlantillaDestinoBorradores(
        plantilla_id="template_ALLOWLIST-1",
        carpeta_id="carpeta_ALLOWLIST-1",
        token_provider=TokenFijo(),
        transport=router,
        timeout_s=5,
    )


def _atender(
    canal: CanalFormPedidos,
    router: TransporteRouter,
    tmp_path: Path,
    *,
    fuente=None,
    generator=None,
    registro=None,
):
    return atender_canal(
        canal,
        fuente=fuente or CsvFuenteSolicitudes(DATASET),
        directorio_salida=tmp_path / "salida",
        generator=generator or FakeGenerator(_BORRADOR_CONFORME),
        destino=_destino_drive(router),
        registro_pendientes=registro,
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
        crudo = json.loads(solicitud["body"])["raw"]
        mensajes.append(
            message_from_bytes(
                base64.urlsafe_b64decode(crudo), policy=policy.default
            )
        )
    return mensajes


def _cuerpo(mensaje: object) -> str:
    return mensaje.get_body(("plain",)).get_content()


class _FuenteAmbiguasCompletas:
    """Dos actividades empatadas pero completas: la repregunta y su
    resolución se ejercitan de punta a punta, con borrador al final."""

    _FILA_BASE = {
        "descripcion": "Actividad de prueba para el taller ambiguo.",
        "publico": "Comunidad universitaria",
        "contacto": "pruebas@example.invalid",
        "fuente": "https://example.invalid/taller",
        "lugar": "Aula de prueba",
        "titulo": "Taller de robótica educativa",
        "fecha_inicio": "2026-09-01",
        "organiza": "Equipo ambiguo",
    }

    def obtener(self, id_actividad: str) -> dict[str, str]:
        for fila in self.enumerar():
            if fila["id_actividad"] == id_actividad:
                return fila
        raise AssertionError("la actividad resuelta debería existir")

    def enumerar(self) -> list[dict[str, str]]:
        return [
            {**self._FILA_BASE, "id_actividad": "AMB-001"},
            {**self._FILA_BASE, "id_actividad": "AMB-002"},
        ]


# --- Lector crudo de la hoja -------------------------------------------------


def test_lector_devuelve_las_filas_crudas_y_arma_el_get() -> None:
    router = TransporteRouter(
        values=[ENCABEZADOS_HOJA, fila_respuesta(), ["", "", ""]]
    )
    lector = GoogleSheetsLectorValores(
        spreadsheet_id="sheet_respuestas-1",
        rango_a1="'Form Responses 1'!A1:C200",
        token_provider=TokenFijo(),
        transport=router,
        timeout_s=5,
    )

    values = lector.leer_valores()

    assert values == router.values
    solicitud = router.solicitudes[0]
    assert solicitud["method"] == "GET"
    assert solicitud["host"] == "sheets.googleapis.com"
    assert solicitud["target"] == (
        "/v4/spreadsheets/sheet_respuestas-1/values/"
        "%27Form%20Responses%201%27%21A1%3AC200"
        "?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE"
    )
    assert solicitud["headers"]["Authorization"] == "Bearer TOKEN_ULTRA_SECRETO"
    assert solicitud["body"] is None


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (401, "workspace_auth_denied"),
        (403, "workspace_auth_denied"),
        (429, "workspace_rate_limited"),
        (500, "workspace_unavailable"),
        (404, "workspace_source_not_found"),
    ],
)
def test_lector_mapea_errores_http_a_codigos(status: int, code: str) -> None:
    class TransporteFijo:
        def request(self, **kwargs) -> RespuestaHttp:
            return RespuestaHttp(status, b"{}")

    lector = GoogleSheetsLectorValores(
        spreadsheet_id="sheet_respuestas-1",
        rango_a1="Hoja!A1:C10",
        token_provider=TokenFijo(),
        transport=TransporteFijo(),
        timeout_s=5,
    )

    with pytest.raises(FuenteSolicitudesError) as exc:
        lector.leer_valores()
    assert exc.value.code == code


def test_lector_rechaza_respuesta_sin_values() -> None:
    class TransporteFijo:
        def request(self, **kwargs) -> RespuestaHttp:
            return RespuestaHttp(200, b'{"range":"Hoja!A1:C10"}')

    lector = GoogleSheetsLectorValores(
        spreadsheet_id="sheet_respuestas-1",
        rango_a1="Hoja!A1:C10",
        token_provider=TokenFijo(),
        transport=TransporteFijo(),
        timeout_s=5,
    )

    with pytest.raises(FuenteSolicitudesError) as exc:
        lector.leer_valores()
    assert exc.value.code == "workspace_response_invalid"


def test_lector_rechaza_json_roto_y_caida_de_transporte() -> None:
    class TransporteMalformado:
        def request(self, **kwargs) -> RespuestaHttp:
            return RespuestaHttp(200, b"not json{{{")

    class TransporteCaido:
        def request(self, **kwargs) -> RespuestaHttp:
            raise OSError("caída simulada")

    for transporte, code in (
        (TransporteMalformado(), "workspace_response_invalid"),
        (TransporteCaido(), "workspace_unavailable"),
    ):
        lector = GoogleSheetsLectorValores(
            spreadsheet_id="sheet_respuestas-1",
            rango_a1="Hoja!A1:C10",
            token_provider=TokenFijo(),
            transport=transporte,
            timeout_s=5,
        )
        with pytest.raises(FuenteSolicitudesError) as exc:
            lector.leer_valores()
        assert exc.value.code == code


def test_lector_rechaza_un_token_invalido_sin_tocar_la_red() -> None:
    router = TransporteRouter()
    lector = GoogleSheetsLectorValores(
        spreadsheet_id="sheet_respuestas-1",
        rango_a1="Hoja!A1:C10",
        token_provider=TokenFijo(token="token\ncon\nsaltos"),
        transport=router,
        timeout_s=5,
    )

    with pytest.raises(FuenteSolicitudesError) as exc:
        lector.leer_valores()
    assert exc.value.code == "workspace_auth_unavailable"
    assert router.solicitudes == []


def test_lector_valida_la_configuracion_al_construir() -> None:
    base = {
        "spreadsheet_id": "sheet_ok-1",
        "rango_a1": "Hoja!A1:C10",
        "timeout_s": 5,
    }
    for kwargs in (
        {**base, "spreadsheet_id": "id con espacios"},
        {**base, "rango_a1": "x" * 300},
        {**base, "rango_a1": ""},
        {**base, "timeout_s": 0},
        {**base, "timeout_s": float("inf")},
        {**base, "timeout_s": "10"},
    ):
        with pytest.raises(ValueError):
            GoogleSheetsLectorValores(
                token_provider=TokenFijo(),
                transport=TransporteRouter(),
                **kwargs,
            )


# --- Padrón de roles (ADR 0005) ----------------------------------------------


def test_padron_normaliza_correos_y_roles() -> None:
    padron = PadronRoles({"  Coord@Example.INVALID  ": " coordinador_seu "})

    assert padron.rol_para("coord@example.invalid") == "coordinador_seu"
    assert padron.rol_para("  coord@example.invalid ") == "coordinador_seu"
    assert padron.rol_para("otro@example.invalid") is None
    assert padron.rol_para(None) is None


@pytest.mark.parametrize(
    "mapeo",
    [
        {},
        {"no-es-correo": "coordinador_seu"},
        {"coord@example.invalid": "rol con espacios"},
        {"coord@example.invalid": ""},
        "no es un mapeo",
        [("a@example.invalid", "coordinador_seu")],
    ],
)
def test_padron_rechaza_entradas_invalidas(mapeo: object) -> None:
    with pytest.raises(ConfiguracionWorkspaceError) as exc:
        PadronRoles(mapeo)  # type: ignore[arg-type]
    assert exc.value.code == "padron_roles_invalid"


def test_cargar_padron_csv_lee_correo_rol(tmp_path: Path) -> None:
    path = tmp_path / "padron.csv"
    path.write_text(
        "correo,rol\n"
        f"{CORREO_SOLICITANTE},coordinador_seu\n"
        f" {CORREO_COORDINADORA} , auxiliar_seu \n",
        encoding="utf-8",
    )

    padron = cargar_padron_roles_csv(path)

    assert padron.rol_para(CORREO_SOLICITANTE) == "coordinador_seu"
    assert padron.rol_para(CORREO_COORDINADORA) == "auxiliar_seu"


@pytest.mark.parametrize(
    "contenido",
    [
        # Encabezados distintos del contrato correo,rol.
        "email,rol\na@example.invalid,coordinador_seu\n",
        "correo,rol,extra\na@example.invalid,coordinador_seu,x\n",
        # Correo duplicado: una línea pisaría a la otra en silencio.
        "correo,rol\na@example.invalid,coordinador_seu\na@example.invalid,auxiliar_seu\n",
        # Rol vacío.
        "correo,rol\na@example.invalid,\n",
        # Correo inválido.
        "correo,rol\nno-es-correo,coordinador_seu\n",
    ],
)
def test_cargar_padron_csv_rechaza_archivos_invalidos(
    tmp_path: Path, contenido: str
) -> None:
    path = tmp_path / "padron.csv"
    path.write_text(contenido, encoding="utf-8")

    with pytest.raises(ConfiguracionWorkspaceError) as exc:
        cargar_padron_roles_csv(path)
    assert exc.value.code == "padron_roles_invalid"


def test_cargar_padron_csv_archivo_ausente(tmp_path: Path) -> None:
    with pytest.raises(ConfiguracionWorkspaceError) as exc:
        cargar_padron_roles_csv(tmp_path / "no_existe.csv")
    assert exc.value.code == "padron_roles_missing"


def test_padron_desde_entorno_requiere_la_variable(tmp_path: Path) -> None:
    with pytest.raises(ConfiguracionWorkspaceError) as exc:
        PadronRoles.desde_entorno({})
    assert exc.value.code == "padron_roles_missing"

    path = tmp_path / "padron.csv"
    path.write_text(f"correo,rol\n{CORREO_SOLICITANTE},auxiliar_seu\n", encoding="utf-8")
    padron = PadronRoles.desde_entorno({"AGENTE1_PADRON_ROLES_PATH": str(path)})
    assert padron.rol_para(CORREO_SOLICITANTE) == "auxiliar_seu"


# --- Configuración por entorno ------------------------------------------------


def _env_config(tmp_path: Path) -> dict[str, str]:
    return {
        "AGENTE1_FORM_PEDIDOS_SHEET_ID": "sheet_respuestas-1",
        "AGENTE1_FORM_PEDIDOS_RANGO_A1": "'Form Responses 1'!A1:C200",
        "AGENTE1_FORM_PEDIDOS_FORM_ID": FORM_ID,
        "AGENTE1_FORM_PEDIDOS_ENTRY_ID": ENTRY_ID,
        "AGENTE1_FORM_PEDIDOS_TIMEOUT_S": "15",
        "AGENTE1_PADRON_ROLES_PATH": str(tmp_path / "padron.csv"),
    }


def test_config_form_valida_y_publica_solo_hashes(tmp_path: Path) -> None:
    config = cargar_configuracion_canal_form(_env_config(tmp_path))

    assert config.sheet_id == "sheet_respuestas-1"
    assert config.form_id == FORM_ID
    assert config.entry_id == ENTRY_ID
    assert config.timeout_s == 15.0
    resumen = config.resumen_seguro()
    texto = json.dumps(resumen)
    assert config.sheet_id not in texto
    assert config.form_id not in texto
    assert str(config.padron_path) not in texto
    assert resumen["entry_id"] == ENTRY_ID


@pytest.mark.parametrize(
    ("clave", "valor"),
    [
        ("AGENTE1_FORM_PEDIDOS_SHEET_ID", "id con espacios"),
        ("AGENTE1_FORM_PEDIDOS_RANGO_A1", "HojaSinCerrar!A1"),
        ("AGENTE1_FORM_PEDIDOS_FORM_ID", "form con espacios"),
        ("AGENTE1_FORM_PEDIDOS_ENTRY_ID", "123456789"),
        ("AGENTE1_FORM_PEDIDOS_ENTRY_ID", "entry.abc"),
        ("AGENTE1_FORM_PEDIDOS_TIMEOUT_S", "no_es_numero"),
        ("AGENTE1_FORM_PEDIDOS_TIMEOUT_S", "0"),
        ("AGENTE1_FORM_PEDIDOS_TIMEOUT_S", "9999"),
        ("AGENTE1_PADRON_ROLES_PATH", ""),
    ],
)
def test_config_form_rechaza_valores_invalidos(
    tmp_path: Path, clave: str, valor: str
) -> None:
    env = _env_config(tmp_path)
    env[clave] = valor

    with pytest.raises(ConfiguracionWorkspaceError) as exc:
        cargar_configuracion_canal_form(env)
    assert exc.value.code == "canal_form_config_invalid"


def test_config_form_rechaza_entorno_incompleto(tmp_path: Path) -> None:
    env = _env_config(tmp_path)
    env.pop("AGENTE1_FORM_PEDIDOS_FORM_ID")

    with pytest.raises(ConfiguracionWorkspaceError) as exc:
        cargar_configuracion_canal_form(env)
    assert exc.value.code == "canal_form_config_incomplete"


def test_config_form_rechaza_claves_desconocidas_del_prefijo(
    tmp_path: Path,
) -> None:
    env = _env_config(tmp_path)
    env["AGENTE1_FORM_PEDIDOS_OTRA_COSA"] = "x"
    env2 = _env_config(tmp_path)
    env2["AGENTE1_PADRON_EXTRA"] = "x"

    for env in (env, env2):
        with pytest.raises(ConfiguracionWorkspaceError) as exc:
            cargar_configuracion_canal_form(env)
        assert exc.value.code == "canal_form_config_unknown_key"


# --- Lector CSV offline --------------------------------------------------------


def test_lector_csv_offline_devuelve_filas_como_listas(tmp_path: Path) -> None:
    path = tmp_path / "respuestas.csv"
    path.write_text(
        "Marca temporal,Correo,Pedido\n"
        f"2026-10-10 09:00:00,{CORREO_SOLICITANTE},gacetilla SYN-001\n",
        encoding="utf-8",
    )

    assert LectorValoresCsv(path).leer_valores() == [
        ["Marca temporal", "Correo", "Pedido"],
        ["2026-10-10 09:00:00", CORREO_SOLICITANTE, "gacetilla SYN-001"],
    ]


# --- Lectura de pendientes -----------------------------------------------------


def test_pendientes_omite_encabezados_y_filas_no_reconocibles(
    tmp_path: Path,
) -> None:
    canal, _router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_HOJA,
            fila_respuesta(),
            ["", CORREO_SOLICITANTE, "sin marca temporal"],
            ["2026-10-10 09:05:00", "no-es-correo", "sin correo válido"],
            ["2026-10-10 09:06:00"],  # fila corta, sin correo
            {"no": "una lista"},  # fila que no es una lista
        ],
    )

    pedidos = canal.leer_pendientes()

    assert len(pedidos) == 1
    pedido = pedidos[0]
    assert pedido.texto == "gacetilla SYN-001"
    assert pedido.solicitante.identificador == CORREO_SOLICITANTE
    assert pedido.solicitante.rol == ROL_HABILITADO
    # El id es un hash: estable entre lecturas y sin datos en claro.
    assert len(pedido.id_pedido) == 64
    int(pedido.id_pedido, 16)
    assert CORREO_SOLICITANTE.split("@")[0] not in pedido.id_pedido


def test_pendientes_deduplica_la_misma_respuesta(tmp_path: Path) -> None:
    # La misma fila repetida (un reenvío de Sheet, una importación doble) es
    # un solo pedido: mismo id, mismo atendido.
    canal, _router = crear_canal(
        tmp_path,
        values=[ENCABEZADOS_HOJA, fila_respuesta(), fila_respuesta()],
    )

    assert len(canal.leer_pendientes()) == 1


def test_correo_fuera_de_padron_recibe_el_rol_centinela(tmp_path: Path) -> None:
    canal, _router = crear_canal(
        tmp_path,
        values=[ENCABEZADOS_HOJA, fila_respuesta(correo=CORREO_DESCONOCIDO)],
    )

    (pedido,) = canal.leer_pendientes()

    assert pedido.solicitante.rol == ROL_NO_EN_PADRON
    assert pedido.solicitante.identificador == CORREO_DESCONOCIDO


def test_correo_en_padron_recibe_su_rol(tmp_path: Path) -> None:
    canal, _router = crear_canal(
        tmp_path,
        values=[
            ENCABEZADOS_HOJA,
            fila_respuesta(correo="  COORDINADORA@EXAMPLE.INVALID "),
        ],
    )

    (pedido,) = canal.leer_pendientes()

    assert pedido.solicitante.identificador == CORREO_COORDINADORA
    assert pedido.solicitante.rol == "auxiliar_seu"


def test_la_sheet_rota_propaga_error_de_fuente_no_lista_vacia(
    tmp_path: Path,
) -> None:
    class LectorCaido:
        def leer_valores(self) -> list[object]:
            raise FuenteSolicitudesError("workspace_unavailable")

    canal = CanalFormPedidos(
        lector=LectorCaido(),
        padron=_padron_default(),
        avisos=GmailDestinoConfirmaciones(
            destinatarios_permitidos={CORREO_SOLICITANTE},
            token_provider=TokenFijo(),
            transport=TransporteRouter(),
        ),
        directorio_estado=tmp_path / "estado",
        form_id=FORM_ID,
        entry_id=ENTRY_ID,
    )

    with pytest.raises(FuenteSolicitudesError):
        canal.leer_pendientes()


def test_registro_atendidos_corrupto_frena_la_lectura(tmp_path: Path) -> None:
    canal, _router = crear_canal(tmp_path)
    estado = tmp_path / "estado"
    estado.mkdir(parents=True)
    (estado / ATENDIDOS_NOMBRE).write_text("{no es json}\n", encoding="utf-8")

    with pytest.raises(CanalFormError) as exc:
        canal.leer_pendientes()
    assert exc.value.code == "canal_form_registry_invalid"


def test_canal_valida_sus_dependencias_al_construir(tmp_path: Path) -> None:
    padron = _padron_default()
    avisos = GmailDestinoConfirmaciones(
        destinatarios_permitidos={CORREO_SOLICITANTE},
        token_provider=TokenFijo(),
        transport=TransporteRouter(),
    )
    for kwargs in (
        {"lector": object()},
        {"lector": LectorValoresCsv(tmp_path / "x.csv"), "padron": {}},
        {"lector": LectorValoresCsv(tmp_path / "x.csv"), "form_id": "id mal"},
        {"lector": LectorValoresCsv(tmp_path / "x.csv"), "entry_id": "otra"},
        {"lector": LectorValoresCsv(tmp_path / "x.csv"), "directorio_estado": "str"},
    ):
        base = {
            "padron": padron,
            "avisos": avisos,
            "directorio_estado": tmp_path / "estado",
            "form_id": FORM_ID,
            "entry_id": ENTRY_ID,
        }
        base.update(kwargs)
        with pytest.raises(ValueError):
            CanalFormPedidos(**base)


# --- Atención de punta a punta ---------------------------------------------------


def test_pedido_autorizado_termina_en_borrador_y_aviso_gmail(
    tmp_path: Path,
) -> None:
    canal, router = crear_canal(tmp_path)

    resultados = _atender(canal, router, tmp_path)

    assert [r.estado for r in resultados] == ["PENDIENTE_VALIDACION"]
    assert resultados[0].referencia_borrador is not None
    assert resultados[0].referencia_borrador.referencia == "doc_copiado-777"

    # El flujo tocó los tres servicios en orden: leyó la Sheet, copió la
    # plantilla al drive allowlisted, volcó el texto y mandó el aviso.
    metodos_por_host = [(s["host"], s["method"]) for s in router.solicitudes]
    assert ("sheets.googleapis.com", "GET") in metodos_por_host
    assert ("www.googleapis.com", "POST") in metodos_por_host
    assert ("docs.googleapis.com", "POST") in metodos_por_host
    assert ("gmail.googleapis.com", "POST") in metodos_por_host

    copia = next(
        s for s in router.solicitudes if s["host"] == "www.googleapis.com"
    )
    assert json.loads(copia["body"])["parents"] == ["carpeta_ALLOWLIST-1"]
    envio = next(
        s for s in router.solicitudes if s["host"] == "gmail.googleapis.com"
    )
    assert envio["target"] == GMAIL_SEND_TARGET

    (mensaje,) = _correos_gmail(router)
    assert mensaje["To"] == CORREO_SOLICITANTE
    assert "Pedido" in mensaje["Subject"]
    cuerpo = _cuerpo(mensaje)
    assert MARCADOR_BORRADOR in cuerpo
    assert (
        "https://docs.google.com/document/d/doc_copiado-777/edit" in cuerpo
    )

    (registro,) = _atendidos(tmp_path)
    assert registro["estado"] == "PENDIENTE_VALIDACION"
    assert registro["aviso"] == "enviada"
    assert registro["rol"] == ROL_HABILITADO
    assert registro["rol_origen"] == "padron"
    assert registro["identidad_canal"] == "correo_verificado_form"
    assert len(registro["solicitante_hash"]) == 64

    # El pedido ya atendido no vuelve a aparecer.
    assert canal.leer_pendientes() == ()


def test_el_adapter_solo_lee_la_sheet_nunca_escribe_nada(tmp_path: Path) -> None:
    canal, router = crear_canal(tmp_path)
    _atender(canal, router, tmp_path)

    for solicitud in router.solicitudes:
        if solicitud["host"] == "sheets.googleapis.com":
            assert solicitud["method"] == "GET"
            assert solicitud["body"] is None
        assert "forms" not in solicitud["host"]


def test_desconocido_es_rechazado_registrado_y_avisado(tmp_path: Path) -> None:
    canal, router = crear_canal(
        tmp_path,
        values=[ENCABEZADOS_HOJA, fila_respuesta(correo=CORREO_DESCONOCIDO)],
        destinatarios={CORREO_DESCONOCIDO},
    )

    resultados = _atender(canal, router, tmp_path)

    assert [r.estado for r in resultados] == ["RECHAZADA"]
    (registro,) = _atendidos(tmp_path)
    assert registro["rol"] == ROL_NO_EN_PADRON
    assert registro["rol_origen"] == "fuera_de_padron"
    assert registro["aviso"] == "enviada"
    assert "generar" not in json.dumps(registro)

    (mensaje,) = _correos_gmail(router)
    cuerpo = _cuerpo(mensaje)
    assert "rechazado" in cuerpo


def test_aviso_a_destinatario_fuera_de_la_lista_queda_rechazado(
    tmp_path: Path,
) -> None:
    # El desconocido no está en la lista de prueba: la entrega se rechaza
    # antes de la red y el pedido igual queda atendido — repetirlo duplicaría
    # el rechazo sin cambiar nada.
    canal, router = crear_canal(
        tmp_path,
        values=[ENCABEZADOS_HOJA, fila_respuesta(correo=CORREO_DESCONOCIDO)],
        destinatarios={CORREO_SOLICITANTE},
    )

    resultados = _atender(canal, router, tmp_path)

    assert [r.estado for r in resultados] == ["RECHAZADA"]
    (registro,) = _atendidos(tmp_path)
    assert registro["aviso"] == "rechazada"
    assert registro["aviso_codigo"] == "recipient_off_test_list"
    assert not any(
        s["host"] == "gmail.googleapis.com" for s in router.solicitudes
    )


def test_rol_del_padron_no_habilitado_es_rechazado(tmp_path: Path) -> None:
    canal, router = crear_canal(
        tmp_path,
        padron=PadronRoles({CORREO_SOLICITANTE: ROL_NO_HABILITADO}),
    )

    resultados = _atender(canal, router, tmp_path)

    assert [r.estado for r in resultados] == ["RECHAZADA"]
    (registro,) = _atendidos(tmp_path)
    assert registro["rol"] == ROL_NO_HABILITADO
    assert registro["rol_origen"] == "padron"
    (mensaje,) = _correos_gmail(router)
    assert "rechazado" in _cuerpo(mensaje)


def test_texto_vacio_es_un_pedido_que_rechaza_el_nucleo(tmp_path: Path) -> None:
    canal, router = crear_canal(
        tmp_path, values=[ENCABEZADOS_HOJA, fila_respuesta(texto="")]
    )

    resultados = _atender(canal, router, tmp_path)

    assert [r.estado for r in resultados] == ["INVALIDA"]
    (registro,) = _atendidos(tmp_path)
    assert registro["estado"] == "INVALIDA"
    (mensaje,) = _correos_gmail(router)
    assert "válido" in _cuerpo(mensaje)


def test_una_falla_de_gmail_no_rompe_la_atencion_ni_la_evidence(
    tmp_path: Path,
) -> None:
    canal, router = crear_canal(tmp_path, gmail_error=OSError("caída simulada"))

    resultados = _atender(canal, router, tmp_path)

    assert [r.estado for r in resultados] == ["PENDIENTE_VALIDACION"]
    (registro,) = _atendidos(tmp_path)
    assert registro["aviso"] == "fallida"
    assert registro["aviso_codigo"] == "gmail_unavailable"
    assert canal.leer_pendientes() == ()


def test_segunda_corrida_sin_pedidos_nuevos_no_reenvia(tmp_path: Path) -> None:
    canal, router = crear_canal(tmp_path)
    _atender(canal, router, tmp_path)
    envios = sum(
        1 for s in router.solicitudes if s["host"] == "gmail.googleapis.com"
    )

    resultados = _atender(canal, router, tmp_path)

    assert resultados == ()
    assert (
        sum(1 for s in router.solicitudes if s["host"] == "gmail.googleapis.com")
        == envios
    )


def test_ni_el_registro_ni_el_aviso_persisten_la_prosa_del_pedido(
    tmp_path: Path,
) -> None:
    prosa = "gacetilla SYN-001 y además esta frase distintiva ZZZQQ919"
    canal, router = crear_canal(
        tmp_path, values=[ENCABEZADOS_HOJA, fila_respuesta(texto=prosa)]
    )

    _atender(canal, router, tmp_path)

    atendidos_crudo = (
        (tmp_path / "estado" / ATENDIDOS_NOMBRE).read_text(encoding="utf-8")
    )
    assert "ZZZQQ919" not in atendidos_crudo
    assert CORREO_SOLICITANTE not in atendidos_crudo
    (mensaje,) = _correos_gmail(router)
    assert "ZZZQQ919" not in _cuerpo(mensaje)


# --- Repregunta por link prellenado --------------------------------------------


def _atender_repregunta(tmp_path: Path, texto: str):
    canal, router = crear_canal(
        tmp_path, values=[ENCABEZADOS_HOJA, fila_respuesta(texto=texto)]
    )
    registro = RegistroPendientesMemoria()
    resultados = _atender(
        canal,
        router,
        tmp_path,
        fuente=_FuenteAmbiguasCompletas(),
        registro=registro,
    )
    return canal, router, registro, resultados


def test_repregunta_envia_links_prellenados_con_ids_sin_prosa(
    tmp_path: Path,
) -> None:
    prosa = "quiero la gacetilla del taller de robotica educativa por favor"
    canal, router, _reg, resultados = _atender_repregunta(tmp_path, prosa)

    assert [r.estado for r in resultados] == ["PENDIENTE_DESAMBIGUACION"]
    (mensaje,) = _correos_gmail(router)
    cuerpo = _cuerpo(mensaje)

    enlaces = [
        linea.strip()
        for linea in cuerpo.splitlines()
        if "docs.google.com/forms" in linea
    ]
    assert len(enlaces) == 2
    valores_precargados = {
        parse_qs(urlparse(enlace).query)[ENTRY_ID][0] for enlace in enlaces
    }
    ref = _atendidos(tmp_path)[0]["id_pedido"][:12]
    assert valores_precargados == {
        f"gacetilla actividad AMB-001 (pedido {ref})",
        f"gacetilla actividad AMB-002 (pedido {ref})",
    }
    # El valor precargado lleva identificadores solamente: ni la prosa del
    # pedido ni una frase suya viaja en el link de repregunta.
    for enlace in enlaces:
        assert "usp=pp_url" in enlace
        assert "por%20favor" not in enlace
        assert "robotica" not in parse_qs(urlparse(enlace).query)[ENTRY_ID][0]
    (registro,) = _atendidos(tmp_path)
    assert registro["estado"] == "PENDIENTE_DESAMBIGUACION"


def test_repregunta_de_post_precarga_la_palabra_clave_post(tmp_path: Path) -> None:
    _canal, router, _reg, resultados = _atender_repregunta(
        tmp_path, "post para instagram del taller de robotica educativa"
    )

    assert [r.estado for r in resultados] == ["PENDIENTE_DESAMBIGUACION"]
    (mensaje,) = _correos_gmail(router)
    enlaces = [
        linea.strip()
        for linea in _cuerpo(mensaje).splitlines()
        if "docs.google.com/forms" in linea
    ]
    valores = {
        parse_qs(urlparse(enlace).query)[ENTRY_ID][0] for enlace in enlaces
    }
    assert {v.split(" actividad ")[0] for v in valores} == {"post"}


def test_la_respuesta_al_link_resuelve_la_candidata_elegida(
    tmp_path: Path,
) -> None:
    """El turno siguiente llega como otra fila del Form, sin prosa heredada.

    El texto que el link precargó —`gacetilla actividad AMB-001 (pedido
    <ref>)`— trae el identificador explícito de la actividad, así que el
    núcleo lo resuelve directo: no depende del pendiente de quince minutos.
    """
    canal, router, registro, _ = _atender_repregunta(
        tmp_path, "quiero la gacetilla del taller de robotica educativa"
    )
    ref = _atendidos(tmp_path)[0]["id_pedido"][:12]

    # Segunda respuesta del mismo correo, distinta marca temporal: es lo que
    # el Form escribe cuando la persona envía el link prellenado.
    router.values = [
        ENCABEZADOS_HOJA,
        fila_respuesta(texto="quiero la gacetilla del taller de robotica educativa"),
        fila_respuesta(
            texto=f"gacetilla actividad AMB-001 (pedido {ref})",
            marca="2026-10-10 09:40:00",
        ),
    ]
    resultados = _atender(
        canal,
        router,
        tmp_path,
        fuente=_FuenteAmbiguasCompletas(),
        generator=FakeGenerator(_BORRADOR_AMB_CONFORME),
        registro=registro,
    )

    assert [r.estado for r in resultados] == ["PENDIENTE_VALIDACION"]
    copia = next(
        s
        for s in reversed(router.solicitudes)
        if s["host"] == "www.googleapis.com"
    )
    assert json.loads(copia["body"])["name"].endswith("AMB-001")
    assert len(_atendidos(tmp_path)) == 2
    assert len(_correos_gmail(router)) == 2


def test_el_link_de_seguimiento_no_arrastra_la_prosa_original(
    tmp_path: Path,
) -> None:
    """Si la prosa original viajara al segundo turno, una frase plantada en
    ella reaparecería en el flujo. Sólo los identificadores hacen el viaje."""
    prosa = "dame la gacetilla del taller de robotica educativa FRASEX887"
    canal, router, registro, _ = _atender_repregunta(tmp_path, prosa)
    ref = _atendidos(tmp_path)[0]["id_pedido"][:12]

    router.values = [
        ENCABEZADOS_HOJA,
        fila_respuesta(texto=prosa),
        fila_respuesta(
            texto=f"gacetilla actividad AMB-001 (pedido {ref})",
            marca="2026-10-10 09:41:00",
        ),
    ]
    _atender(
        canal,
        router,
        tmp_path,
        fuente=_FuenteAmbiguasCompletas(),
        generator=FakeGenerator(_BORRADOR_AMB_CONFORME),
        registro=registro,
    )

    atendidos_crudo = (
        (tmp_path / "estado" / ATENDIDOS_NOMBRE).read_text(encoding="utf-8")
    )
    assert "FRASEX887" not in atendidos_crudo
    for mensaje in _correos_gmail(router):
        assert "FRASEX887" not in _cuerpo(mensaje)


# --- Camino offline con CSV ------------------------------------------------------


def test_canal_offline_sobre_csv_atiende_el_pedido_completo(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "respuestas.csv"
    csv_path.write_text(
        "Marca temporal,Correo,Pedido\n"
        f"2026-10-10 09:00:00,{CORREO_SOLICITANTE},gacetilla SYN-001\n",
        encoding="utf-8",
    )
    router = TransporteRouter()
    canal = CanalFormPedidos(
        lector=LectorValoresCsv(csv_path),
        padron=_padron_default(),
        avisos=GmailDestinoConfirmaciones(
            destinatarios_permitidos={CORREO_SOLICITANTE},
            token_provider=TokenFijo(),
            transport=router,
        ),
        directorio_estado=tmp_path / "estado",
        form_id=FORM_ID,
        entry_id=ENTRY_ID,
    )

    resultados = _atender(canal, router, tmp_path)

    assert [r.estado for r in resultados] == ["PENDIENTE_VALIDACION"]
    (registro,) = _atendidos(tmp_path)
    assert registro["aviso"] == "enviada"
    # En offline no hay Sheets: sólo las llamadas del destino y del aviso.
    assert not any(
        s["host"] == "sheets.googleapis.com" for s in router.solicitudes
    )
