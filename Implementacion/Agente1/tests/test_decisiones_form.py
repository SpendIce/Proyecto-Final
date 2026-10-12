"""HU-013/#72 — Registro de decisiones por el segundo Google Form.

La Sheet de respuestas del Form «Registro de decisiones» se lee por posición
de columna con el mismo `values.get` de Sheets (GET, nunca escritura); la
identidad es el correo verificado y el rol sale del padrón externo (ADR
0005); la decisión se valida contra un catálogo cerrado y contra el registro
de objetos pendientes —un link alterado con un id que el agente no declaró
se rechaza—; cada respuesta procesada queda en `decisiones-procesadas.jsonl`
sin correo en claro; y registrar no dispara nada: la difusión la hace una
persona a mano.
"""

from __future__ import annotations

import base64
from email import message_from_bytes
from email import policy
import hashlib
import importlib.util
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from agente1.canal import atender_canal
from agente1.canal_form import (
    ATENDIDOS_NOMBRE,
    CanalFormPedidos,
    LectorValoresCsv,
    PadronRoles,
    ROL_NO_EN_PADRON,
)
from agente1.confirmaciones import (
    MARCADOR_BORRADOR,
    ROL_APROBACION_SEMANTICA,
    ROL_APROBACION_UTILITARIA,
)
from agente1.decisiones_form import (
    CanalFormDecisiones,
    ConfiguracionFormDecisiones,
    DECISIONES_POR_TIPO,
    DECISION_APRUEBO_LOTE,
    DECISION_APRUEBO_SEMANTICA,
    DECISION_APRUEBO_UTILITARIA,
    DECISION_DESCARTE,
    DECISION_PUBLIQUE,
    DecisionesFormError,
    EnlacesDecisiones,
    PENDIENTES_NOMBRE,
    PROCESADAS_NOMBRE,
    RegistroDecisiones,
    ResultadoDecision,
    TIPO_LOTE,
    TIPO_PLANTILLA,
    TIPO_PUBLICACION,
    cargar_configuracion_form_decisiones,
    crear_lector_decisiones,
)
from agente1.fuentes import CsvFuenteSolicitudes, FuenteSolicitudesError
from agente1.gmail_envio import GmailDestinoConfirmaciones
from agente1.google_workspace import (
    GoogleSheetsLectorValores,
    RespuestaHttp,
)
from agente1.procesamiento import FakeGenerator
from agente1.workspace_config import ConfiguracionWorkspaceError


ROOT = Path(__file__).parents[1]
DATASET = ROOT / "data" / "actividades_sinteticas.csv"
SCRIPT_RUNNER = ROOT / "scripts" / "registrar_form_decisiones.py"

# Correos sintéticos: el dominio del Form es institucional pero en las
# pruebas todo correo es de `example.invalid` y el padrón es de prueba.
CORREO_SOLICITANTE = "solicitante@example.invalid"
CORREO_RGC = "rgc-seu@example.invalid"
CORREO_COORD = "coord-seu@example.invalid"
CORREO_AUX = "auxiliar-seu@example.invalid"
CORREO_DESCONOCIDO = "desconocido@example.invalid"

ENCABEZADOS_DECISIONES = [
    "Marca temporal",
    "Dirección de correo electrónico",
    "Tipo de decisión",
    "Objeto de la decisión",
    "Decisión",
]

FORM_DECISIONES_ID = "FORM_DECISIONES-3"
ENTRY_TIPO = "entry.000000021"
ENTRY_OBJETO = "entry.000000022"
ENTRY_DECISION = "entry.000000023"

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

# Salida creativa conforme del pipeline de posts: el mismo JSON que usa
# `test_interpretacion.py` para el canal instagram.
_POST_CONFORME = json.dumps(
    {
        "gancho": "Una propuesta para aprender y compartir.",
        "prosa": "Sumate a una experiencia pensada para la comunidad.",
        "cta": "Encontrá el enlace en nuestro perfil.",
        "hashtags": ["#FIE", "#UNDEF"],
    },
    ensure_ascii=False,
)


def _padron() -> PadronRoles:
    """Padrón sintético: roles operativos para pedir, roles de decisión.

    `coordinador_seu`/`auxiliar_seu` habilitan pedidos en el núcleo pero no
    autorizan decisiones; los dos roles del acta autorizan decisiones pero
    no pasan el filtro de pedidos. Así el circuito entero se ensaya con la
    separación de roles que el padrón real va a tener.
    """

    return PadronRoles(
        {
            CORREO_SOLICITANTE: "coordinador_seu",
            CORREO_AUX: "auxiliar_seu",
            CORREO_RGC: ROL_APROBACION_SEMANTICA,
            CORREO_COORD: ROL_APROBACION_UTILITARIA,
        }
    )


def _registro(tmp_path: Path) -> RegistroDecisiones:
    return RegistroDecisiones(tmp_path / "estado-decisiones")


def _enlazador(tmp_path: Path) -> EnlacesDecisiones:
    return EnlacesDecisiones(
        registro=_registro(tmp_path),
        form_id=FORM_DECISIONES_ID,
        entry_tipo=ENTRY_TIPO,
        entry_objeto=ENTRY_OBJETO,
        entry_decision=ENTRY_DECISION,
    )


def fila_decision(
    correo: str = CORREO_RGC,
    tipo: str = TIPO_PUBLICACION,
    objeto: str = "obj-1",
    decision: str = DECISION_PUBLIQUE,
    marca: str = "2026-10-11 09:00:00",
) -> list[str]:
    """Una fila tal como la deja el Form de decisiones, correo verificado."""

    return [marca, correo, tipo, objeto, decision]


class TokenFijo:
    def obtener_access_token(self) -> str:
        return "TOKEN_ULTRA_SECRETO"


class TransporteSoloSheet:
    """Transporte fake que sólo conoce `sheets.googleapis.com`.

    Sirve al lector crudo del Form de decisiones y, a la vez, prueba por
    construcción que el canal de decisiones no llama a ningún otro host:
    un request a Gmail o Drive rompe la prueba en vez de fingirse — la
    decisión registrada no dispara ni correo ni publicación.
    """

    def __init__(
        self,
        *,
        values: list[list[object]] | None = None,
        falla: Exception | None = None,
    ) -> None:
        self.values = list(values or [])
        self.falla = falla
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
            {"method": method, "host": host, "target": target}
        )
        if host != "sheets.googleapis.com":
            raise AssertionError(f"request a un host no previsto: {host}")
        if self.falla is not None:
            raise self.falla
        return RespuestaHttp(
            200, json.dumps({"values": self.values}).encode("utf-8")
        )


def _lector_sheet(router: TransporteSoloSheet) -> GoogleSheetsLectorValores:
    return GoogleSheetsLectorValores(
        spreadsheet_id="sheet_decisiones-9",
        rango_a1="'Form Responses 1'!A1:E200",
        token_provider=TokenFijo(),
        transport=router,
        timeout_s=5,
    )


def _canal(
    tmp_path: Path,
    *,
    values: list[list[object]] | None = None,
    padron: PadronRoles | None = None,
    router: TransporteSoloSheet | None = None,
    registro: RegistroDecisiones | None = None,
) -> tuple[CanalFormDecisiones, TransporteSoloSheet]:
    router = router or TransporteSoloSheet(values=values or [])
    canal = CanalFormDecisiones(
        lector=_lector_sheet(router),
        padron=padron or _padron(),
        registro=registro or _registro(tmp_path),
    )
    return canal, router


def _procesadas(tmp_path: Path) -> list[dict[str, object]]:
    path = tmp_path / "estado-decisiones" / PROCESADAS_NOMBRE
    if not path.exists():
        return []
    return [
        json.loads(linea)
        for linea in path.read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]


def _pendientes(tmp_path: Path) -> list[dict[str, object]]:
    path = tmp_path / "estado-decisiones" / PENDIENTES_NOMBRE
    if not path.exists():
        return []
    return [
        json.loads(linea)
        for linea in path.read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]


def _declarar_publicacion(tmp_path: Path, objeto: str = "obj-1") -> None:
    _registro(tmp_path).declarar_pendiente(
        tipo=TIPO_PUBLICACION,
        objeto_id=objeto,
        detalle={"pieza": "gacetilla"},
    )


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


# --- Registro de objetos pendientes ------------------------------------------


def test_declarar_pendiente_abre_el_objeto_y_es_idempotente(
    tmp_path: Path,
) -> None:
    registro = _registro(tmp_path)
    registro.declarar_pendiente(tipo=TIPO_LOTE, objeto_id="lote-2026-10")
    registro.declarar_pendiente(tipo=TIPO_LOTE, objeto_id="lote-2026-10")

    assert registro.es_pendiente(tipo=TIPO_LOTE, objeto_id="lote-2026-10")
    assert not registro.es_pendiente(tipo=TIPO_PLANTILLA, objeto_id="lote-2026-10")
    # La misma apertura no se duplica: una línea por (tipo, objeto).
    assert len(_pendientes(tmp_path)) == 1
    pendiente = _pendientes(tmp_path)[0]
    assert pendiente["version"] == "decisiones_pendientes_v1"
    assert pendiente["declarado_en"].endswith("+00:00")


def test_declarar_pendiente_rechaza_tipo_u_objeto_invalidos(
    tmp_path: Path,
) -> None:
    registro = _registro(tmp_path)
    with pytest.raises(DecisionesFormError, match="decision_tipo_invalid"):
        registro.declarar_pendiente(tipo="meme", objeto_id="obj-1")
    with pytest.raises(DecisionesFormError, match="decision_objeto_invalid"):
        registro.declarar_pendiente(
            tipo=TIPO_LOTE, objeto_id="../fuera del formato"
        )


def test_registro_corrupto_interrumpe_antes_de_procesar(
    tmp_path: Path,
) -> None:
    _declarar_publicacion(tmp_path, "obj-2")
    # El archivo se corrompe después de la declaración: una línea que no es
    # el contrato de pendientes.
    with (tmp_path / "estado-decisiones" / PENDIENTES_NOMBRE).open(
        "a", encoding="utf-8"
    ) as fh:
        fh.write("no es json\n")
    canal, _ = _canal(
        tmp_path, values=[fila_decision(objeto="obj-2")]
    )
    with pytest.raises(
        DecisionesFormError, match="decisiones_registry_invalid"
    ):
        canal.atender()
    # No se registró nada: ante un registro inconsistente no se improvisa.
    assert _procesadas(tmp_path) == []


def test_registro_procesadas_corrupto_falla_cerrado(tmp_path: Path) -> None:
    directorio = tmp_path / "estado-decisiones"
    directorio.mkdir(parents=True)
    (directorio / PROCESADAS_NOMBRE).write_text(
        '{"version": "otra"}\n', "utf-8"
    )
    canal, _ = _canal(tmp_path, values=[])
    with pytest.raises(
        DecisionesFormError, match="decisiones_registry_invalid"
    ):
        canal.atender()


# --- Links prellenados --------------------------------------------------------


def test_enlace_decision_precarga_los_tres_campos(tmp_path: Path) -> None:
    enlazador = _enlazador(tmp_path)
    url = enlazador.enlace(
        tipo=TIPO_PUBLICACION, objeto_id="obj-1", decision=DECISION_PUBLIQUE
    )
    parseado = urlparse(url)
    assert FORM_DECISIONES_ID in parseado.path
    parametros = parse_qs(parseado.query)
    assert parametros[ENTRY_TIPO] == [TIPO_PUBLICACION]
    assert parametros[ENTRY_OBJETO] == ["obj-1"]
    assert parametros[ENTRY_DECISION] == [DECISION_PUBLIQUE]


def test_enlaces_para_plantilla_mintean_uno_por_rol(tmp_path: Path) -> None:
    enlazador = _enlazador(tmp_path)
    enlaces = enlazador.enlaces_para(
        tipo=TIPO_PLANTILLA, objeto_id="confirmacion_inscripcion_v1"
    )
    assert set(enlaces) == {
        DECISION_APRUEBO_SEMANTICA,
        DECISION_APRUEBO_UTILITARIA,
    }
    for decision, url in enlaces.items():
        assert (
            parse_qs(urlparse(url).query)[ENTRY_DECISION] == [decision]
        )


def test_enlace_rechaza_pares_fuera_del_catalogo(tmp_path: Path) -> None:
    enlazador = _enlazador(tmp_path)
    with pytest.raises(DecisionesFormError, match="decision_link_invalid"):
        enlazador.enlace(
            tipo=TIPO_PUBLICACION,
            objeto_id="obj-1",
            decision=DECISION_APRUEBO_LOTE,
        )
    with pytest.raises(DecisionesFormError, match="decision_link_invalid"):
        enlazador.enlace(
            tipo=TIPO_LOTE, objeto_id="lote 1 con espacios", decision=DECISION_APRUEBO_LOTE
        )


def test_declarar_y_enlaces_abre_el_objeto(tmp_path: Path) -> None:
    enlazador = _enlazador(tmp_path)
    enlaces = enlazador.declarar_y_enlaces(
        tipo=TIPO_LOTE, objeto_id="lote-2026-10"
    )
    assert set(enlaces) == {DECISION_APRUEBO_LOTE}
    assert _registro(tmp_path).es_pendiente(
        tipo=TIPO_LOTE, objeto_id="lote-2026-10"
    )


# --- Configuración por entorno -------------------------------------------------


def _env_decisiones() -> dict[str, str]:
    return {
        "AGENTE1_FORM_DECISIONES_SHEET_ID": "sheet_decisiones-9",
        "AGENTE1_FORM_DECISIONES_RANGO_A1": "'Respuestas'!A1:E500",
        "AGENTE1_FORM_DECISIONES_FORM_ID": FORM_DECISIONES_ID,
        "AGENTE1_FORM_DECISIONES_ENTRY_TIPO": ENTRY_TIPO,
        "AGENTE1_FORM_DECISIONES_ENTRY_OBJETO": ENTRY_OBJETO,
        "AGENTE1_FORM_DECISIONES_ENTRY_DECISION": ENTRY_DECISION,
        "AGENTE1_FORM_DECISIONES_TIMEOUT_S": "10",
        "AGENTE1_PADRON_ROLES_PATH": "/tmp/padron.csv",
    }


def test_configuracion_valida_y_resumen_solo_hashes() -> None:
    config = cargar_configuracion_form_decisiones(_env_decisiones())
    assert isinstance(config, ConfiguracionFormDecisiones)
    resumen = config.resumen_seguro()
    for clave, valor in resumen.items():
        if clave == "timeout_s":
            continue
        assert isinstance(valor, str) and len(valor) == 64
    assert "sheet_decisiones-9" not in repr(config)


@pytest.mark.parametrize(
    ("clave", "valor"),
    [
        ("AGENTE1_FORM_DECISIONES_SHEET_ID", "sheet con espacios"),
        ("AGENTE1_FORM_DECISIONES_RANGO_A1", "A1:E500"),
        ("AGENTE1_FORM_DECISIONES_FORM_ID", "form con espacios"),
        ("AGENTE1_FORM_DECISIONES_ENTRY_TIPO", "entry.notanumero"),
        ("AGENTE1_FORM_DECISIONES_ENTRY_DECISION", "ENTRY.000000023"),
        ("AGENTE1_FORM_DECISIONES_TIMEOUT_S", "0"),
        ("AGENTE1_FORM_DECISIONES_TIMEOUT_S", "121"),
        ("AGENTE1_FORM_DECISIONES_TIMEOUT_S", "abc"),
    ],
)
def test_configuracion_rechaza_valores_invalidos(
    clave: str, valor: str
) -> None:
    env = _env_decisiones()
    env[clave] = valor
    with pytest.raises(
        ConfiguracionWorkspaceError,
        match="canal_form_decisiones_config_invalid",
    ):
        cargar_configuracion_form_decisiones(env)


def test_configuracion_rechaza_claves_desconocidas() -> None:
    env = _env_decisiones()
    env["AGENTE1_FORM_DECISIONES_TIPEADO_MAL"] = "x"
    with pytest.raises(
        ConfiguracionWorkspaceError,
        match="canal_form_decisiones_config_unknown_key",
    ):
        cargar_configuracion_form_decisiones(env)
    env = _env_decisiones()
    env["AGENTE1_PADRON_OTRA"] = "x"
    with pytest.raises(
        ConfiguracionWorkspaceError,
        match="canal_form_decisiones_config_unknown_key",
    ):
        cargar_configuracion_form_decisiones(env)


def test_configuracion_rechaza_incompleta() -> None:
    env = _env_decisiones()
    del env["AGENTE1_FORM_DECISIONES_ENTRY_DECISION"]
    with pytest.raises(
        ConfiguracionWorkspaceError,
        match="canal_form_decisiones_config_incomplete",
    ):
        cargar_configuracion_form_decisiones(env)


def test_lector_desde_config_arma_el_values_get() -> None:
    config = cargar_configuracion_form_decisiones(_env_decisiones())
    router = TransporteSoloSheet(values=[])
    lector = crear_lector_decisiones(
        config=config, token_provider=TokenFijo(), transport=router
    )
    lector.leer_valores()
    solicitud = router.solicitudes[0]
    assert solicitud["method"] == "GET"
    assert solicitud["target"].startswith(
        "/v4/spreadsheets/sheet_decisiones-9/values/"
    )


# --- Decisión registrada -------------------------------------------------------


def test_publicacion_publique_del_rgc_se_registra_con_identidad_y_fecha(
    tmp_path: Path,
) -> None:
    _declarar_publicacion(tmp_path)
    marca = "2026-10-11 09:00:00"
    canal, _ = _canal(
        tmp_path,
        values=[ENCABEZADOS_DECISIONES, fila_decision(marca=marca)],
    )

    resultados = canal.atender()

    assert len(resultados) == 1
    resultado = resultados[0]
    assert resultado.resultado == "registrada"
    assert resultado.rechazo_codigo is None
    assert resultado.tipo == TIPO_PUBLICACION
    assert resultado.objeto_id == "obj-1"
    assert resultado.decision == DECISION_PUBLIQUE
    assert resultado.rol == ROL_APROBACION_SEMANTICA
    assert resultado.rol_origen == "padron"
    # Identidad verificada y fecha con zona horaria, tal como pide el AC.
    assert resultado.correo_hash == _hash(CORREO_RGC)
    assert resultado.timestamp.endswith("+00:00")
    assert resultado.marca_temporal_form == marca
    # Y en la auditoría la línea completa, sin el correo en claro.
    lineas = _procesadas(tmp_path)
    assert len(lineas) == 1
    linea = lineas[0]
    assert linea["identidad_canal"] == "correo_verificado_form"
    assert linea["correo_hash"] == _hash(CORREO_RGC)
    assert CORREO_RGC not in json.dumps(linea)


def test_publicacion_descarte_del_coordinador_tambien_registra(
    tmp_path: Path,
) -> None:
    _declarar_publicacion(tmp_path)
    canal, _ = _canal(
        tmp_path,
        values=[
            fila_decision(correo=CORREO_COORD, decision=DECISION_DESCARTE)
        ],
    )
    (resultado,) = canal.atender()
    assert resultado.resultado == "registrada"
    assert resultado.rol == ROL_APROBACION_UTILITARIA


# --- Rechazos registrados ------------------------------------------------------


def test_decision_de_correo_fuera_del_padron_se_rechaza_y_registra(
    tmp_path: Path,
) -> None:
    _declarar_publicacion(tmp_path)
    canal, _ = _canal(
        tmp_path,
        values=[fila_decision(correo=CORREO_DESCONOCIDO)],
    )
    (resultado,) = canal.atender()
    assert resultado.resultado == "rechazada"
    assert resultado.rechazo_codigo == "fuera_de_padron"
    assert resultado.rol == ROL_NO_EN_PADRON
    assert resultado.rol_origen == "fuera_de_padron"
    assert _procesadas(tmp_path)[0]["resultado"] == "rechazada"


@pytest.mark.parametrize(
    ("correo", "tipo", "decision", "rol_esperado"),
    [
        # Un rol operativo del padrón puede pedir piezas pero no decide.
        (CORREO_AUX, TIPO_PUBLICACION, DECISION_PUBLIQUE, "auxiliar_seu"),
        # La aprobación utilitaria no es del RGC ni la semántica del Coord.
        (CORREO_RGC, TIPO_PLANTILLA, DECISION_APRUEBO_UTILITARIA, ROL_APROBACION_SEMANTICA),
        (CORREO_COORD, TIPO_PLANTILLA, DECISION_APRUEBO_SEMANTICA, ROL_APROBACION_UTILITARIA),
        # El lote es decisión utilitaria: el RGC no lo habilita.
        (CORREO_RGC, TIPO_LOTE, DECISION_APRUEBO_LOTE, ROL_APROBACION_SEMANTICA),
    ],
)
def test_decision_con_rol_que_no_corresponde_se_rechaza_y_registra(
    tmp_path: Path,
    correo: str,
    tipo: str,
    decision: str,
    rol_esperado: str,
) -> None:
    objeto = f"{tipo}-obj-1"
    _registro(tmp_path).declarar_pendiente(tipo=tipo, objeto_id=objeto)
    canal, _ = _canal(
        tmp_path,
        values=[
            fila_decision(
                correo=correo, tipo=tipo, objeto=objeto, decision=decision
            )
        ],
    )
    (resultado,) = canal.atender()
    assert resultado.resultado == "rechazada"
    assert resultado.rechazo_codigo == "rol_no_corresponde"
    assert resultado.rol == rol_esperado
    assert resultado.rol_origen == "padron"
    # Igual queda en la auditoría con la decisión que se intentó.
    assert _procesadas(tmp_path)[0]["rechazo_codigo"] == "rol_no_corresponde"


@pytest.mark.parametrize(
    ("tipo", "decision", "codigo"),
    [
        ("meme", DECISION_PUBLIQUE, "tipo_desconocido"),
        (TIPO_PUBLICACION, DECISION_APRUEBO_LOTE, "decision_fuera_de_catalogo"),
        (TIPO_LOTE, "descarte", "decision_fuera_de_catalogo"),
    ],
)
def test_link_alterado_en_tipo_o_decision_se_rechaza(
    tmp_path: Path, tipo: str, decision: str, codigo: str
) -> None:
    _declarar_publicacion(tmp_path)
    canal, _ = _canal(
        tmp_path,
        values=[fila_decision(tipo=tipo, decision=decision)],
    )
    (resultado,) = canal.atender()
    assert resultado.resultado == "rechazada"
    assert resultado.rechazo_codigo == codigo


def test_link_alterado_con_id_inexistente_se_rechaza(tmp_path: Path) -> None:
    # El objeto nunca fue declarado: el link pudo venir alterado de otro
    # correo o fabricado a mano.
    canal, _ = _canal(
        tmp_path, values=[fila_decision(objeto="obj-inventado-99")]
    )
    (resultado,) = canal.atender()
    assert resultado.resultado == "rechazada"
    assert resultado.rechazo_codigo == "objeto_inexistente"
    assert _procesadas(tmp_path)[0]["objeto_id"] == "obj-inventado-99"


def test_objeto_sin_forma_de_identificador_se_rechaza(tmp_path: Path) -> None:
    canal, _ = _canal(
        tmp_path,
        values=[fila_decision(objeto="../etc/passwd con espacios")],
    )
    (resultado,) = canal.atender()
    assert resultado.rechazo_codigo == "objeto_invalido"


# --- Filas no atribuibles y deduplicación --------------------------------------


@pytest.mark.parametrize(
    "fila",
    [
        ENCABEZADOS_DECISIONES,
        ["2026-10-11 09:00:00", "no-es-correo", "publicacion", "obj-1", "publique"],
        ["", CORREO_RGC, TIPO_PUBLICACION, "obj-1", DECISION_PUBLIQUE],
        [],
    ],
)
def test_fila_sin_identidad_verificable_se_omite_sin_registrar(
    tmp_path: Path, fila: list[str]
) -> None:
    _declarar_publicacion(tmp_path)
    canal, _ = _canal(tmp_path, values=[fila])
    assert canal.atender() == ()
    assert _procesadas(tmp_path) == []


def test_misma_respuesta_releida_no_se_duplica(tmp_path: Path) -> None:
    _declarar_publicacion(tmp_path)
    fila = fila_decision()
    canal, _ = _canal(tmp_path, values=[fila, list(fila)])
    assert len(canal.atender()) == 1
    # Y una segunda corrida no reprocesa ni la registrada ni la rechazada.
    assert canal.atender() == ()
    assert len(_procesadas(tmp_path)) == 1


def test_dos_decisiones_distintas_sobre_el_mismo_objeto_quedan_ambas(
    tmp_path: Path,
) -> None:
    """«Lo publiqué» y después «lo descarté» son dos eventos: el registro es
    append-only y la interpretación del conjunto la hace el consumidor."""

    _declarar_publicacion(tmp_path)
    canal, _ = _canal(
        tmp_path,
        values=[
            fila_decision(marca="2026-10-11 09:00:00"),
            fila_decision(
                decision=DECISION_DESCARTE, marca="2026-10-11 10:30:00"
            ),
        ],
    )
    resultados = canal.atender()
    assert [r.resultado for r in resultados] == ["registrada", "registrada"]
    assert len(_procesadas(tmp_path)) == 2


def test_hoja_rota_propaga_el_error_de_fuente(tmp_path: Path) -> None:
    router = TransporteSoloSheet(falla=ConnectionError("sin red"))
    canal, _ = _canal(tmp_path, router=router)
    with pytest.raises(FuenteSolicitudesError, match="workspace_unavailable"):
        canal.atender()


def test_registrar_no_toca_ningun_host_que_no_sea_sheets(
    tmp_path: Path,
) -> None:
    """La decisión no dispara acciones: sólo se lee la Sheet de respuestas.

    `TransporteSoloSheet` rompe la prueba ante cualquier request que no sea
    la lectura del Form — Gmail, Drive o un endpoint de publicación—, así
    que pasar verde acá es la prueba estructural de que registrar una
    decisión no publica ni envía nada.
    """

    _declarar_publicacion(tmp_path)
    canal, router = _canal(
        tmp_path, values=[ENCABEZADOS_DECISIONES, fila_decision()]
    )
    canal.atender()
    hosts = {solicitud["host"] for solicitud in router.solicitudes}
    assert hosts == {"sheets.googleapis.com"}


# --- Aprobaciones de plantilla y de lote ----------------------------------------


def test_plantilla_registra_las_dos_aprobaciones_por_rol(
    tmp_path: Path,
) -> None:
    """La versión de plantilla queda aprobada cuando las dos decisiones
    existen: la semántica del RGC y la utilitaria del Coordinador."""

    version = "confirmacion_inscripcion_provisional_v1"
    _registro(tmp_path).declarar_pendiente(
        tipo=TIPO_PLANTILLA, objeto_id=version
    )
    canal, _ = _canal(
        tmp_path,
        values=[
            fila_decision(
                correo=CORREO_RGC,
                tipo=TIPO_PLANTILLA,
                objeto=version,
                decision=DECISION_APRUEBO_SEMANTICA,
                marca="2026-10-11 09:00:00",
            ),
            fila_decision(
                correo=CORREO_COORD,
                tipo=TIPO_PLANTILLA,
                objeto=version,
                decision=DECISION_APRUEBO_UTILITARIA,
                marca="2026-10-11 09:05:00",
            ),
        ],
    )
    resultados = canal.atender()
    assert [r.resultado for r in resultados] == ["registrada", "registrada"]
    procesadas = _procesadas(tmp_path)
    assert {
        (linea["rol"], linea["decision"]) for linea in procesadas
    } == {
        (ROL_APROBACION_SEMANTICA, DECISION_APRUEBO_SEMANTICA),
        (ROL_APROBACION_UTILITARIA, DECISION_APRUEBO_UTILITARIA),
    }


def test_lote_registra_la_aprobacion_que_habilita_envios(
    tmp_path: Path,
) -> None:
    """«Apruebo el lote» del Coordinador: el detalle del pendiente lleva el
    contexto (la actividad cuyos envíos se habilitan) sin prosa libre."""

    _registro(tmp_path).declarar_pendiente(
        tipo=TIPO_LOTE,
        objeto_id="lote-syn-001-2026-10",
        detalle={"actividad": "SYN-001", "uso": "habilitar_envios"},
    )
    canal, _ = _canal(
        tmp_path,
        values=[
            fila_decision(
                correo=CORREO_COORD,
                tipo=TIPO_LOTE,
                objeto="lote-syn-001-2026-10",
                decision=DECISION_APRUEBO_LOTE,
            )
        ],
    )
    (resultado,) = canal.atender()
    assert resultado.resultado == "registrada"
    assert resultado.rol == ROL_APROBACION_UTILITARIA
    pendiente = _pendientes(tmp_path)[0]
    assert pendiente["detalle"]["actividad"] == "SYN-001"


# --- Circuito completo: pedido -> correo con links -> decisión ----------------


class TransporteRouterDosForms:
    """Transporte fake del circuito completo: dos Sheets, Drive/Docs y Gmail.

    Enruta por host como la red real y por spreadsheet_id dentro de Sheets,
    así el mismo transporte sirve a la hoja de pedidos y a la de decisiones.
    Un request a un host no previsto rompe la prueba en lugar de fingirse.
    """

    def __init__(
        self,
        *,
        values_pedidos: list[list[object]],
        doc_id: str = "doc_copiado-777",
    ) -> None:
        self.values_pedidos = list(values_pedidos)
        self.values_decisiones: list[list[object]] = []
        self.doc_id = doc_id
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
            }
        )
        if host == "sheets.googleapis.com":
            if "sheet_respuestas-1" in target:
                return RespuestaHttp(
                    200,
                    json.dumps({"values": self.values_pedidos}).encode(),
                )
            if "sheet_decisiones-9" in target:
                return RespuestaHttp(
                    200,
                    json.dumps({"values": self.values_decisiones}).encode(),
                )
            raise AssertionError(f"spreadsheet no previsto: {target}")
        if host == "www.googleapis.com":
            return RespuestaHttp(
                200, json.dumps({"id": self.doc_id}).encode("utf-8")
            )
        if host == "docs.googleapis.com":
            return RespuestaHttp(200, b'{"replies":[{}]}')
        if host == "gmail.googleapis.com":
            return RespuestaHttp(200, b'{"id":"msg_enviado-1"}')
        raise AssertionError(f"request a un host no previsto: {host}")

    def cuerpos_gmail(self) -> list[str]:
        mensajes = []
        for solicitud in self.solicitudes:
            if solicitud["host"] != "gmail.googleapis.com":
                continue
            crudo = json.loads(solicitud["body"])["raw"]
            mensaje = message_from_bytes(
                base64.urlsafe_b64decode(crudo), policy=policy.default
            )
            mensajes.append(mensaje.get_body(("plain",)).get_content())
        return mensajes


def _extraer_enlace_decision(cuerpo: str, etiqueta: str) -> dict[str, str]:
    """Del cuerpo del aviso extrae la línea `etiqueta: <url>` y sus params."""

    prefijo = f"{etiqueta}: https://docs.google.com/forms/"
    linea = next(
        (linea for linea in cuerpo.splitlines() if linea.startswith(prefijo)),
        None,
    )
    assert linea is not None, f"el aviso no trae el link «{etiqueta}»"
    url = linea[len(etiqueta) + 2 :].strip()
    return parse_qs(urlparse(url).query)


def _circuito_pedido_borrador(
    tmp_path: Path,
    *,
    texto_pedido: str,
    generator: FakeGenerator,
) -> tuple[TransporteRouterDosForms, str]:
    """Pedido -> borrador -> aviso con links. Devuelve el router y el id del
    objeto de decisión que el correo declaró (el `entry_objeto` del link)."""

    router = TransporteRouterDosForms(
        values_pedidos=[
            ["Marca temporal", "Dirección de correo electrónico", "Escribí tu pedido"],
            ["2026-10-10 09:00:00", CORREO_SOLICITANTE, texto_pedido],
        ]
    )
    enlazador = EnlacesDecisiones(
        registro=_registro(tmp_path),
        form_id=FORM_DECISIONES_ID,
        entry_tipo=ENTRY_TIPO,
        entry_objeto=ENTRY_OBJETO,
        entry_decision=ENTRY_DECISION,
    )
    canal = CanalFormPedidos(
        lector=GoogleSheetsLectorValores(
            spreadsheet_id="sheet_respuestas-1",
            rango_a1="'Form Responses 1'!A1:C200",
            token_provider=TokenFijo(),
            transport=router,
            timeout_s=5,
        ),
        padron=_padron(),
        avisos=GmailDestinoConfirmaciones(
            destinatarios_permitidos={CORREO_SOLICITANTE},
            token_provider=TokenFijo(),
            transport=router,
            timeout_s=5,
        ),
        directorio_estado=tmp_path / "estado-canal-form",
        form_id="FORM_ID_RESPUESTAS-9",
        entry_id="entry.123456789",
        decisiones=enlazador,
    )
    from agente1.google_workspace import (
        GoogleDrivePlantillaDestinoBorradores,
    )

    resultados = atender_canal(
        canal,
        fuente=CsvFuenteSolicitudes(DATASET),
        directorio_salida=tmp_path / "salida",
        generator=generator,
        destino=GoogleDrivePlantillaDestinoBorradores(
            plantilla_id="template_ALLOWLIST-1",
            carpeta_id="carpeta_ALLOWLIST-1",
            token_provider=TokenFijo(),
            transport=router,
            timeout_s=5,
        ),
    )
    assert len(resultados) == 1
    assert resultados[0].estado == "PENDIENTE_VALIDACION"

    (cuerpo,) = router.cuerpos_gmail()
    assert MARCADOR_BORRADOR in cuerpo
    parametros = _extraer_enlace_decision(cuerpo, "Lo publiqué")
    assert parametros[ENTRY_TIPO] == [TIPO_PUBLICACION]
    assert parametros[ENTRY_DECISION] == [DECISION_PUBLIQUE]
    (objeto_id,) = parametros[ENTRY_OBJETO]
    # El otro link también está y apunta al mismo objeto.
    parametros_descarte = _extraer_enlace_decision(cuerpo, "Lo descarté")
    assert parametros_descarte[ENTRY_DECISION] == [DECISION_DESCARTE]
    assert parametros_descarte[ENTRY_OBJETO] == [objeto_id]
    return router, objeto_id


def _canal_decisiones(tmp_path: Path, router: TransporteRouterDosForms):
    return CanalFormDecisiones(
        lector=_lector_sheet(router),
        padron=_padron(),
        registro=_registro(tmp_path),
    )


def test_circuito_completo_publica_gacetilla_y_registra_la_decision(
    tmp_path: Path,
) -> None:
    """HU-010: el correo del borrador de gacetilla trae los links, la
    decisión «lo publiqué» del RGC se valida y queda en la auditoría, y el
    agente no ejecutó ninguna acción de publicación."""

    router, objeto_id = _circuito_pedido_borrador(
        tmp_path,
        texto_pedido="gacetilla SYN-001",
        generator=FakeGenerator(_BORRADOR_CONFORME),
    )
    # El objeto quedó declarado como publicación de una gacetilla.
    pendiente = _pendientes(tmp_path)[0]
    assert pendiente["tipo"] == TIPO_PUBLICACION
    assert pendiente["objeto_id"] == objeto_id
    assert pendiente["detalle"]["pieza"] == "gacetilla"
    # Y el registro de atendidos lo correlaciona.
    atendido = json.loads(
        (tmp_path / "estado-canal-form" / ATENDIDOS_NOMBRE)
        .read_text(encoding="utf-8")
        .strip()
    )
    assert atendido["decisiones_objeto"] == objeto_id

    # La persona publica a mano y manda el Form: llega la fila.
    router.values_decisiones = [
        ENCABEZADOS_DECISIONES,
        fila_decision(correo=CORREO_RGC, objeto=objeto_id),
    ]
    (resultado,) = _canal_decisiones(tmp_path, router).atender()

    assert resultado.resultado == "registrada"
    assert resultado.decision == DECISION_PUBLIQUE
    linea = _procesadas(tmp_path)[0]
    assert linea["identidad_canal"] == "correo_verificado_form"
    assert linea["rol"] == ROL_APROBACION_SEMANTICA
    assert linea["timestamp"].endswith("+00:00")
    # Nada más se tocó: un solo gmail.send (el aviso) y ninguna otra escritura.
    assert (
        len(
            [
                s
                for s in router.solicitudes
                if s["host"] == "gmail.googleapis.com"
            ]
        )
        == 1
    )


def test_circuito_completo_descarte_de_post_registra_sin_publicar(
    tmp_path: Path,
) -> None:
    """HU-011: el borrador de post trae los mismos links y «lo descarté»
    del Coordinador queda registrado con su rol — sin acción del agente."""

    router, objeto_id = _circuito_pedido_borrador(
        tmp_path,
        texto_pedido="post de instagram para SYN-001",
        generator=FakeGenerator(_POST_CONFORME),
    )
    assert _pendientes(tmp_path)[0]["detalle"]["pieza"] == "post"

    router.values_decisiones = [
        fila_decision(
            correo=CORREO_COORD, objeto=objeto_id, decision=DECISION_DESCARTE
        )
    ]
    (resultado,) = _canal_decisiones(tmp_path, router).atender()

    assert resultado.resultado == "registrada"
    assert resultado.decision == DECISION_DESCARTE
    assert resultado.rol == ROL_APROBACION_UTILITARIA
    assert (
        len(
            [
                s
                for s in router.solicitudes
                if s["host"] == "gmail.googleapis.com"
            ]
        )
        == 1
    )


def test_sin_puente_de_decisiones_el_aviso_no_trae_links(
    tmp_path: Path,
) -> None:
    """Con `decisiones=None` el canal corre igual pero sin links ni pendiente:
    el puente es opt-in y el correo no promete lo que no se registró."""

    router = TransporteRouterDosForms(
        values_pedidos=[
            ["Marca temporal", "Dirección de correo electrónico", "Escribí tu pedido"],
            ["2026-10-10 09:00:00", CORREO_SOLICITANTE, "gacetilla SYN-001"],
        ]
    )
    canal = CanalFormPedidos(
        lector=GoogleSheetsLectorValores(
            spreadsheet_id="sheet_respuestas-1",
            rango_a1="'Form Responses 1'!A1:C200",
            token_provider=TokenFijo(),
            transport=router,
            timeout_s=5,
        ),
        padron=_padron(),
        avisos=GmailDestinoConfirmaciones(
            destinatarios_permitidos={CORREO_SOLICITANTE},
            token_provider=TokenFijo(),
            transport=router,
            timeout_s=5,
        ),
        directorio_estado=tmp_path / "estado-canal-form",
        form_id="FORM_ID_RESPUESTAS-9",
        entry_id="entry.123456789",
    )
    from agente1.google_workspace import (
        GoogleDrivePlantillaDestinoBorradores,
    )

    atender_canal(
        canal,
        fuente=CsvFuenteSolicitudes(DATASET),
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(_BORRADOR_CONFORME),
        destino=GoogleDrivePlantillaDestinoBorradores(
            plantilla_id="template_ALLOWLIST-1",
            carpeta_id="carpeta_ALLOWLIST-1",
            token_provider=TokenFijo(),
            transport=router,
            timeout_s=5,
        ),
    )
    (cuerpo,) = router.cuerpos_gmail()
    assert "Lo publiqué" not in cuerpo
    assert _pendientes(tmp_path) == []


# --- Runner offline -------------------------------------------------------------


def _cargar_runner():
    spec = importlib.util.spec_from_file_location(
        "registrar_form_decisiones_test", SCRIPT_RUNNER
    )
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_runner_offline_declara_registra_y_rechaza(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """El runner ensaya el circuito sin red: declara un lote, registra la
    aprobación del Coordinador y rechaza la de un correo fuera del padrón."""

    modulo = _cargar_runner()
    respuestas = tmp_path / "respuestas.csv"
    respuestas.write_text(
        "Marca temporal,Correo,Tipo,Objeto,Decisión\n"
        f"2026-10-11 09:00:00,{CORREO_COORD},{TIPO_LOTE},lote-2026-10,{DECISION_APRUEBO_LOTE}\n"
        f"2026-10-11 09:10:00,{CORREO_DESCONOCIDO},{TIPO_LOTE},lote-2026-10,{DECISION_APRUEBO_LOTE}\n",
        encoding="utf-8",
    )
    padron = tmp_path / "padron.csv"
    padron.write_text(
        f"correo,rol\n{CORREO_COORD},{ROL_APROBACION_UTILITARIA}\n",
        encoding="utf-8",
    )

    salida = modulo.main(
        [
            "--directorio",
            str(tmp_path / "trabajo"),
            "--respuestas-csv",
            str(respuestas),
            "--padron",
            str(padron),
            "--declarar",
            f"{TIPO_LOTE}:lote-2026-10",
        ]
    )

    assert salida == 0
    lineas = [
        json.loads(linea)
        for linea in capsys.readouterr().out.splitlines()
        if linea.strip()
    ]
    declarado = lineas[0]["declarado"]
    assert declarado["tipo"] == TIPO_LOTE
    assert set(declarado["enlaces"]) == {DECISION_APRUEBO_LOTE}
    resultados = {linea["resultado"] for linea in lineas[1:-1]}
    assert resultados == {"registrada", "rechazada"}
    resumen = lineas[-1]
    assert resumen["procesadas"] == 2
    # La auditoría quedó en el directorio compartido.
    procesadas = (
        tmp_path
        / "trabajo"
        / "estado-decisiones"
        / PROCESADAS_NOMBRE
    ).read_text(encoding="utf-8")
    assert '"resultado": "registrada"' in procesadas or '"resultado":"registrada"' in procesadas
    assert CORREO_COORD not in procesadas


def test_runner_offline_rechaza_declaracion_invalida(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    modulo = _cargar_runner()
    respuestas = tmp_path / "respuestas.csv"
    respuestas.write_text("marca,correo,tipo,objeto,decision\n", "utf-8")
    salida = modulo.main(
        [
            "--directorio",
            str(tmp_path / "trabajo"),
            "--respuestas-csv",
            str(respuestas),
            "--declarar",
            "lote:id con espacios",
        ]
    )
    assert salida == 2
    assert json.loads(capsys.readouterr().out.strip())["resultado"] == (
        "runner_declaracion_invalid"
    )


def test_lector_csv_del_canal_de_pedidos_sirve_a_la_hoja_de_decisiones(
    tmp_path: Path,
) -> None:
    """El mismo `LectorValoresCsv` lee la hoja de cinco columnas: el offline
    del Form de decisiones reusa el mecanismo del Form de pedidos (#71)."""

    csv_path = tmp_path / "respuestas.csv"
    csv_path.write_text(
        "Marca temporal,Correo,Tipo,Objeto,Decisión\n"
        f"2026-10-11 09:00:00,{CORREO_RGC},{TIPO_PUBLICACION},obj-9,{DECISION_PUBLIQUE}\n",
        encoding="utf-8",
    )
    _registro(tmp_path).declarar_pendiente(
        tipo=TIPO_PUBLICACION, objeto_id="obj-9"
    )
    canal = CanalFormDecisiones(
        lector=LectorValoresCsv(csv_path),
        padron=_padron(),
        registro=_registro(tmp_path),
    )
    (resultado,) = canal.atender()
    assert resultado.resultado == "registrada"
    assert resultado.objeto_id == "obj-9"
