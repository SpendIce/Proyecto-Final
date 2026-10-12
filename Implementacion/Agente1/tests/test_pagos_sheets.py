"""Lectura de plan, padrón y novedades desde las pestañas de la planilla D2.

Estas pruebas ejercitan `GoogleSheetsFuentePagos` con el transporte HTTP
falso —el mismo patrón de `test_google_sheets`— y fijan las dos propiedades
del ticket: que los tres lectores producen exactamente las mismas
estructuras de dominio que los loaders CSV sobre la misma tabla (se prueba
por igualdad contra los fixtures versionados), y que una pestaña faltante o
con encabezado distinto falla explícito, nunca con una lista vacía. También
fijan los límites del lector compartido —planilla y rangos como allowlist,
tope de respuesta, deadline, un request por pestaña— y el modo `--planilla`
del subcomando `control-pagos`.
"""

import csv
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import quote

import pytest

from agente1.buzon import AdjuntoMensaje, BuzonPropioMemoria, MensajeBuzon
from agente1.cli_pagos import main as main_control_pagos
from agente1.google_workspace import (
    MAX_WORKSPACE_RESPONSE_BYTES,
    RespuestaHttp,
    _RespuestaDemasiadoGrande,
)
from agente1.pagos import (
    ControlPagosError,
    cargar_novedades_csv,
    cargar_padron_csv,
    cargar_plan_pagos_csv,
    correr_control_pagos,
)
from agente1.pagos_sheets import (
    RANGO_NOVEDADES_ENV,
    RANGO_PADRON_ENV,
    RANGO_PLAN_ENV,
    SPREADSHEET_ID_ENV,
    GoogleSheetsFuentePagos,
)
from agente1.workspace_config import (
    TOKEN_ENV,
    ConfiguracionWorkspaceError,
    TokenEntornoProvider,
)
from test_google_sheets import TransporteCaptura


ROOT = Path(__file__).parents[1]
PLAN_NOTEBOOKLM = ROOT / "data" / "plan_pagos_notebooklm_n2.csv"
PADRON_SINTETICO = ROOT / "data" / "padron_pagos_sintetico.csv"
NOVEDADES_SINTETICAS = ROOT / "data" / "novedades_pago_sinteticas.csv"
ACTIVIDAD_ID = "EJEMPLO-NOTEBOOKLM-N2"
ASUNTO = "Pre-Inscripción NotebookLM Nivel 2"
HOY = date(2026, 9, 22)

RANGO_PLAN = "'Plan de pagos'!A1:D40"
RANGO_PADRON = "'Padron NotebookLM'!A1:E200"
RANGO_NOVEDADES = "'Novedades de pago'!A1:E200"

ENCABEZADO_PADRON = [
    "id_inscripcion",
    "actividad_id",
    "nombre_destinatario",
    "email_destinatario",
]
ENCABEZADO_NOVEDADES = [
    "id_inscripcion",
    "tipo",
    "valor",
    "fecha",
    "responsable",
]


class TokenFijo:
    def __init__(self, token: str = "TOKEN_ULTRA_SECRETO") -> None:
        self.token = token
        self.invocaciones = 0

    def obtener_access_token(self) -> str:
        self.invocaciones += 1
        return self.token


class TransporteEnrutado:
    """Fake que responde por pestaña: decide la respuesta según el target.

    Sirve para la corrida completa y para las pruebas del CLI en proceso: las
    tres lecturas de una corrida viajan por el mismo adapter y cada una tiene
    que llegar a su propio rango.
    """

    def __init__(self, respuestas_por_rango: dict[str, RespuestaHttp]) -> None:
        self.respuestas_por_rango = respuestas_por_rango
        self.solicitudes: list[dict[str, object]] = []

    def request(self, **kwargs) -> RespuestaHttp:
        self.solicitudes.append(kwargs)
        target = kwargs["target"]
        for marca, respuesta in self.respuestas_por_rango.items():
            if marca in target:
                return respuesta
        return RespuestaHttp(status=400, body=b"rango desconocido")


def tabla_csv(path: Path) -> list[list[str]]:
    """La tabla como la devuelve `values.get` sobre el mismo contenido que el
    CSV versionado: listas de celdas de texto, con el encabezado primero."""

    with path.open(encoding="utf-8", newline="") as archivo:
        return [fila for fila in csv.reader(archivo) if fila]


def respuesta_values(filas: list[list[object]]) -> RespuestaHttp:
    return RespuestaHttp(
        status=200,
        body=json.dumps({"range": "pestana!A1:Z99", "values": filas}).encode(),
    )


def crear_fuente(
    respuesta: RespuestaHttp,
    *,
    token_provider: TokenFijo | None = None,
    timeout_s: float = 5,
) -> tuple[GoogleSheetsFuentePagos, TransporteCaptura, TokenFijo]:
    """El adapter con un transporte que responde lo mismo a cualquier rango:
    las pruebas de un solo lector no necesitan enrutar."""

    transporte = TransporteCaptura(respuesta)
    tokens = token_provider or TokenFijo()
    fuente = GoogleSheetsFuentePagos(
        spreadsheet_id="sheet_ID-123",
        rango_plan=RANGO_PLAN,
        rango_padron=RANGO_PADRON,
        rango_novedades=RANGO_NOVEDADES,
        token_provider=tokens,
        transport=transporte,
        timeout_s=timeout_s,
    )
    return fuente, transporte, tokens


def crear_fuente_enrutada(
    respuestas_por_rango: dict[str, RespuestaHttp],
) -> tuple[GoogleSheetsFuentePagos, TransporteEnrutado]:
    transporte = TransporteEnrutado(respuestas_por_rango)
    fuente = GoogleSheetsFuentePagos(
        spreadsheet_id="sheet_ID-123",
        rango_plan=RANGO_PLAN,
        rango_padron=RANGO_PADRON,
        rango_novedades=RANGO_NOVEDADES,
        token_provider=TokenFijo(),
        transport=transporte,
        timeout_s=5,
    )
    return fuente, transporte


# --- Equivalencia con los CSV: mismas estructuras de dominio ------------------


def test_planilla_plan_produce_el_mismo_plan_que_el_csv():
    fuente, _, _ = crear_fuente(respuesta_values(tabla_csv(PLAN_NOTEBOOKLM)))

    assert fuente.cargar_plan() == cargar_plan_pagos_csv(PLAN_NOTEBOOKLM)


def test_planilla_padron_produce_el_mismo_padron_que_el_csv():
    fuente, _, _ = crear_fuente(respuesta_values(tabla_csv(PADRON_SINTETICO)))

    assert fuente.cargar_padron(actividad_id=ACTIVIDAD_ID) == cargar_padron_csv(
        PADRON_SINTETICO, actividad_id=ACTIVIDAD_ID
    )


def test_planilla_novedades_producen_las_mismas_novedades_que_el_csv():
    fuente, _, _ = crear_fuente(
        respuesta_values(tabla_csv(NOVEDADES_SINTETICAS))
    )

    novedades = fuente.cargar_novedades()

    assert novedades == cargar_novedades_csv(NOVEDADES_SINTETICAS)
    # `fila` numera igual que en el CSV: encabezado = 1, datos desde 2.
    assert [novedad.fila for novedad in novedades] == [2, 3]


# --- Forma del request: un GET por pestaña, dentro de los límites -------------


@pytest.mark.parametrize(
    ("metodo", "rango"),
    [
        ("cargar_plan", RANGO_PLAN),
        ("cargar_novedades", RANGO_NOVEDADES),
    ],
)
def test_planilla_hace_un_solo_get_al_rango_fijado(metodo, rango):
    filas = tabla_csv(
        PLAN_NOTEBOOKLM if metodo == "cargar_plan" else NOVEDADES_SINTETICAS
    )
    fuente, transporte, tokens = crear_fuente(respuesta_values(filas))
    antes = time.monotonic()

    if metodo == "cargar_plan":
        fuente.cargar_plan()
    else:
        fuente.cargar_novedades()

    assert tokens.invocaciones == 1
    assert len(transporte.solicitudes) == 1
    solicitud = transporte.solicitudes[0]
    assert solicitud["method"] == "GET"
    assert solicitud["host"] == "sheets.googleapis.com"
    assert solicitud["target"] == (
        f"/v4/spreadsheets/sheet_ID-123/values/{quote(rango, safe='')}"
        "?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE"
    )
    assert solicitud["headers"] == {
        "Accept": "application/json",
        "Authorization": "Bearer TOKEN_ULTRA_SECRETO",
    }
    assert solicitud["body"] is None
    assert solicitud["deadline"] >= antes + 4.9
    assert solicitud["max_response_bytes"] == MAX_WORKSPACE_RESPONSE_BYTES


def test_planilla_padron_pide_su_propio_rango():
    fuente, transporte, _ = crear_fuente(
        respuesta_values(tabla_csv(PADRON_SINTETICO))
    )

    fuente.cargar_padron(actividad_id=ACTIVIDAD_ID)

    assert len(transporte.solicitudes) == 1
    assert "Padron" in transporte.solicitudes[0]["target"]


def test_planilla_cada_lectura_es_un_request_a_su_pestana():
    fuente, transporte = crear_fuente_enrutada(
        {
            "Plan": respuesta_values(tabla_csv(PLAN_NOTEBOOKLM)),
            "Padron": respuesta_values(tabla_csv(PADRON_SINTETICO)),
            "Novedades": respuesta_values(tabla_csv(NOVEDADES_SINTETICAS)),
        }
    )

    plan = fuente.cargar_plan()
    fuente.cargar_padron(actividad_id=plan.actividad_id)
    fuente.cargar_novedades()

    assert len(transporte.solicitudes) == 3
    targets = [solicitud["target"] for solicitud in transporte.solicitudes]
    assert "Plan" in targets[0]
    assert "Padron" in targets[1]
    assert "Novedades" in targets[2]


# --- Fallas explícitas: nunca una lista vacía ---------------------------------


@pytest.mark.parametrize(
    "metodo",
    ["cargar_plan", "cargar_padron", "cargar_novedades"],
)
def test_planilla_pestana_faltante_falla_explicito(metodo):
    # Un rango que nombra una pestaña inexistente devuelve 400: para la
    # corrida es «la fuente no está», con código propio — nunca una lista.
    fuente, _, _ = crear_fuente(RespuestaHttp(status=400, body=b"bad range"))

    with pytest.raises(ControlPagosError) as error:
        if metodo == "cargar_plan":
            fuente.cargar_plan()
        elif metodo == "cargar_padron":
            fuente.cargar_padron(actividad_id=ACTIVIDAD_ID)
        else:
            fuente.cargar_novedades()

    assert error.value.code == "workspace_range_invalid"


@pytest.mark.parametrize(
    "metodo",
    ["cargar_plan", "cargar_padron", "cargar_novedades"],
)
@pytest.mark.parametrize(
    ("status", "codigo"),
    [
        (401, "workspace_auth_denied"),
        (403, "workspace_auth_denied"),
        (404, "workspace_source_not_found"),
        (429, "workspace_rate_limited"),
        (500, "workspace_unavailable"),
    ],
)
def test_planilla_mapea_http_sin_filtrar_token_o_cuerpo(metodo, status, codigo):
    secreto = "correo-secreto@example.invalid"
    fuente, _, _ = crear_fuente(RespuestaHttp(status=status, body=secreto.encode()))

    with pytest.raises(ControlPagosError) as error:
        if metodo == "cargar_plan":
            fuente.cargar_plan()
        elif metodo == "cargar_padron":
            fuente.cargar_padron(actividad_id=ACTIVIDAD_ID)
        else:
            fuente.cargar_novedades()

    assert error.value.code == codigo
    assert str(error.value) == codigo
    assert secreto not in str(error.value)
    assert "TOKEN_ULTRA_SECRETO" not in str(error.value)


@pytest.mark.parametrize(
    ("respuesta", "codigo"),
    [
        (
            RespuestaHttp(status=200, body=b"no-json-secreto"),
            "workspace_response_invalid",
        ),
        (RespuestaHttp(status=200, body=b"[]"), "workspace_response_invalid"),
        (RespuestaHttp(status=200, body=b"{}"), "workspace_response_invalid"),
        # Un rango vacío responde 200 pero omite `values`: es una fuente sin
        # la forma prometida — error explícito, no lista vacía.
        (
            RespuestaHttp(status=200, body=b'{"range": "p!A1:E9"}'),
            "workspace_response_invalid",
        ),
        (
            RespuestaHttp(status=200, body=b'{"values": "no-lista"}'),
            "workspace_response_invalid",
        ),
        (
            RespuestaHttp(status=200, body=b"x" * (MAX_WORKSPACE_RESPONSE_BYTES + 1)),
            "workspace_response_too_large",
        ),
    ],
)
def test_planilla_rechaza_respuesta_invalida_y_sobredimensionada(respuesta, codigo):
    fuente, _, _ = crear_fuente(respuesta)

    with pytest.raises(ControlPagosError) as error:
        fuente.cargar_novedades()

    assert error.value.code == codigo
    assert "no-json-secreto" not in str(error.value)


@pytest.mark.parametrize(
    ("filas", "codigo"),
    [
        # Encabezado corto, distinto o con columna fuera del contrato.
        ([["campo", "valor"], ["x", "1"]], "plan_encabezado_invalid"),
        (
            [["campo", "valor", "procedencia", "extra"]],
            "plan_encabezado_invalid",
        ),
        (
            [["valor", "campo", "procedencia"]],
            "plan_encabezado_invalid",
        ),
        (
            [["campo", "campo", "procedencia"]],
            "plan_encabezado_invalid",
        ),
        # La pestaña existe pero no tiene ni encabezado.
        ([[]], "plan_encabezado_invalid"),
        ([], "plan_encabezado_invalid"),
        # Fila más larga que el encabezado o con celda que no es texto.
        (
            [
                ["campo", "valor", "procedencia"],
                ["actividad_id", "A", "SUPUESTO_TECNICO", "sobra"],
            ],
            "plan_fila_invalid",
        ),
        (
            [
                ["campo", "valor", "procedencia"],
                ["actividad_id", 42, "SUPUESTO_TECNICO"],
            ],
            "plan_fila_invalid",
        ),
        (
            [["campo", "valor", "procedencia"], "no-es-fila"],
            "plan_fila_invalid",
        ),
    ],
)
def test_planilla_plan_rechaza_tabla_invalida(filas, codigo):
    fuente, _, _ = crear_fuente(respuesta_values(filas))

    with pytest.raises(ControlPagosError) as error:
        fuente.cargar_plan()

    assert error.value.code == codigo


@pytest.mark.parametrize(
    ("filas", "codigo"),
    [
        (
            [["id_inscripcion", "actividad_id", "nombre_destinatario"]],
            "padron_encabezado_invalid",
        ),
        (
            [[*ENCABEZADO_PADRON, "sospechosa"]],
            "padron_encabezado_invalid",
        ),
        (
            [
                ENCABEZADO_PADRON,
                ["PRE-1", "OTRA-ACTIVIDAD", "Ana", "ana@example.test"],
            ],
            "padron_actividad_distinta",
        ),
        (
            [
                ENCABEZADO_PADRON,
                ["PRE-1", ACTIVIDAD_ID, "Ana", "ana@example.test"],
                ["PRE-1", ACTIVIDAD_ID, "Ana", "ana@example.test"],
            ],
            "padron_id_duplicado",
        ),
        (
            [
                ENCABEZADO_PADRON,
                ["PRE-1", ACTIVIDAD_ID, "Ana"],
                # Falta el email: la fila recortada queda con email vacío.
            ],
            "padron_fila_invalid",
        ),
    ],
)
def test_planilla_padron_rechaza_tabla_invalida(filas, codigo):
    fuente, _, _ = crear_fuente(respuesta_values(filas))

    with pytest.raises(ControlPagosError) as error:
        fuente.cargar_padron(actividad_id=ACTIVIDAD_ID)

    assert error.value.code == codigo


@pytest.mark.parametrize(
    ("filas", "codigo"),
    [
        (
            [["tipo", "valor", "fecha", "responsable", "id_inscripcion"]],
            "novedades_encabezado_invalid",
        ),
        (
            [
                ENCABEZADO_NOVEDADES,
                ["PRE-1", "BONIFICADO", "", "2026-09-21", "Dep", "sobra"],
            ],
            "novedades_fila_invalid",
        ),
    ],
)
def test_planilla_novedades_rechaza_tabla_invalida(filas, codigo):
    fuente, _, _ = crear_fuente(respuesta_values(filas))

    with pytest.raises(ControlPagosError) as error:
        fuente.cargar_novedades()

    assert error.value.code == codigo


def test_planilla_pestana_con_solo_encabezado_si_devuelve_lista_vacia():
    # Es el único vacío legítimo: encabezado correcto y cero datos — igual
    # que un CSV con sólo su encabezado.
    fuente, _, _ = crear_fuente(respuesta_values([ENCABEZADO_NOVEDADES]))

    assert fuente.cargar_novedades() == []


def test_planilla_salta_filas_vacias_como_lineas_en_blanco():
    filas = [
        ENCABEZADO_PADRON,
        ["PRE-1", ACTIVIDAD_ID, "Ana", "ana@example.test"],
        [],  # fila en blanco dentro del rango
        ["PRE-2", ACTIVIDAD_ID, "Bruno", "bruno@example.test"],
    ]
    fuente, _, _ = crear_fuente(respuesta_values(filas))

    padron = fuente.cargar_padron(actividad_id=ACTIVIDAD_ID)

    assert [p.id_inscripcion for p in padron] == ["PRE-1", "PRE-2"]


def test_planilla_completa_celdas_vacias_del_final():
    # Sheets recorta la celda vacía del final: `bonificado` ausente en la
    # fila es lo mismo que `,` al final del CSV — condición no verificable.
    filas = [
        [*ENCABEZADO_PADRON, "bonificado"],
        ["PRE-1", ACTIVIDAD_ID, "Ana", "ana@example.test"],
    ]
    fuente, _, _ = crear_fuente(respuesta_values(filas))

    (persona,) = fuente.cargar_padron(actividad_id=ACTIVIDAD_ID)

    assert persona.bonificado is None


# --- Configuración, token y transporte ----------------------------------------


@pytest.mark.parametrize(
    ("spreadsheet_id", "rango_plan", "rango_padron", "rango_novedades"),
    [
        ("https://evil.invalid/sheet", RANGO_PLAN, RANGO_PADRON, RANGO_NOVEDADES),
        (
            "sheet-ok",
            "Plan!A1:D9\nAuthorization: secreto",
            RANGO_PADRON,
            RANGO_NOVEDADES,
        ),
        ("sheet-ok", RANGO_PLAN, "", RANGO_NOVEDADES),
        ("sheet-ok", RANGO_PLAN, RANGO_PADRON, "Novedades!A1:E9\x7f"),
    ],
)
def test_planilla_rechaza_config_que_podria_alterar_host_o_headers(
    spreadsheet_id, rango_plan, rango_padron, rango_novedades
):
    transporte = TransporteCaptura(respuesta_values([]))

    with pytest.raises(ValueError, match="configuración de Google Sheets inválida"):
        GoogleSheetsFuentePagos(
            spreadsheet_id=spreadsheet_id,
            rango_plan=rango_plan,
            rango_padron=rango_padron,
            rango_novedades=rango_novedades,
            token_provider=TokenFijo(),
            transport=transporte,
        )

    assert transporte.solicitudes == []


@pytest.mark.parametrize("timeout_s", [0, -1, 121, float("inf"), True, "5"])
def test_planilla_rechaza_timeout_fuera_de_rango(timeout_s):
    with pytest.raises(ValueError, match="configuración de Google Sheets inválida"):
        GoogleSheetsFuentePagos(
            spreadsheet_id="sheet-ok",
            rango_plan=RANGO_PLAN,
            rango_padron=RANGO_PADRON,
            rango_novedades=RANGO_NOVEDADES,
            token_provider=TokenFijo(),
            transport=TransporteCaptura(respuesta_values([])),
            timeout_s=timeout_s,
        )


def test_planilla_rechaza_token_vacio_o_con_inyeccion_sin_invocar_transporte():
    for token in ("", "token\r\nX-Secreto: valor"):
        transporte = TransporteCaptura(respuesta_values([]))
        fuente = GoogleSheetsFuentePagos(
            spreadsheet_id="sheet-ok",
            rango_plan=RANGO_PLAN,
            rango_padron=RANGO_PADRON,
            rango_novedades=RANGO_NOVEDADES,
            token_provider=TokenFijo(token),
            transport=transporte,
        )

        with pytest.raises(ControlPagosError) as error:
            fuente.cargar_plan()

        assert error.value.code == "workspace_auth_unavailable"
        if token:
            assert token not in str(error.value)
        assert transporte.solicitudes == []


def test_planilla_transport_error_se_redacta_y_no_reintenta():
    class TransporteQueFalla:
        invocaciones = 0

        def request(self, **kwargs):
            self.invocaciones += 1
            raise OSError("TOKEN_ULTRA_SECRETO correo-secreto@example.invalid")

    transporte = TransporteQueFalla()
    fuente = GoogleSheetsFuentePagos(
        spreadsheet_id="sheet-ok",
        rango_plan=RANGO_PLAN,
        rango_padron=RANGO_PADRON,
        rango_novedades=RANGO_NOVEDADES,
        token_provider=TokenFijo(),
        transport=transporte,
    )

    with pytest.raises(ControlPagosError) as error:
        fuente.cargar_novedades()

    assert error.value.code == "workspace_unavailable"
    assert str(error.value) == "workspace_unavailable"
    assert transporte.invocaciones == 1


def test_planilla_respuesta_demasiado_grande_desde_el_transporte():
    class TransporteGrande:
        def request(self, **kwargs):
            raise _RespuestaDemasiadoGrande

    fuente = GoogleSheetsFuentePagos(
        spreadsheet_id="sheet-ok",
        rango_plan=RANGO_PLAN,
        rango_padron=RANGO_PADRON,
        rango_novedades=RANGO_NOVEDADES,
        token_provider=TokenFijo(),
        transport=TransporteGrande(),
    )

    with pytest.raises(ControlPagosError) as error:
        fuente.cargar_plan()

    assert error.value.code == "workspace_response_too_large"


# --- Carga desde el entorno ----------------------------------------------------


def _env_planilla(**reemplazos):
    env = {
        SPREADSHEET_ID_ENV: "sheet_ID-123",
        RANGO_PLAN_ENV: RANGO_PLAN,
        RANGO_PADRON_ENV: RANGO_PADRON,
        RANGO_NOVEDADES_ENV: RANGO_NOVEDADES,
    }
    env.update(reemplazos)
    return env


def test_desde_entorno_exige_las_cuatro_variables():
    for clave in _env_planilla():
        env = _env_planilla()
        del env[clave]

        with pytest.raises(ConfiguracionWorkspaceError) as error:
            GoogleSheetsFuentePagos.desde_entorno(
                env, token_provider=TokenFijo()
            )

        assert error.value.code == "pagos_sheets_config_incomplete"


def test_desde_entorno_rechaza_valores_mal_formados():
    transporte = TransporteCaptura(respuesta_values([]))

    for env in (
        _env_planilla(**{SPREADSHEET_ID_ENV: "id/con/barras"}),
        _env_planilla(**{RANGO_PLAN_ENV: "Plan!A1:D9\nX: y"}),
        _env_planilla(**{RANGO_NOVEDADES_ENV: "x" * 300}),
    ):
        with pytest.raises(ConfiguracionWorkspaceError) as error:
            GoogleSheetsFuentePagos.desde_entorno(
                env, token_provider=TokenFijo(), transport=transporte
            )

        assert error.value.code == "pagos_sheets_config_invalid"
    assert transporte.solicitudes == []


def test_desde_entorno_construye_el_adapter_con_los_rangos_declarados():
    transporte = TransporteCaptura(respuesta_values(tabla_csv(NOVEDADES_SINTETICAS)))

    fuente = GoogleSheetsFuentePagos.desde_entorno(
        _env_planilla(), token_provider=TokenFijo(), transport=transporte
    )
    fuente.cargar_novedades()

    assert "Novedades" in transporte.solicitudes[0]["target"]


# --- Corrida de punta a punta alimentada por la planilla -----------------------


def mensaje_buzon(remitente: str) -> MensajeBuzon:
    return MensajeBuzon(
        remitente=remitente,
        asunto=f"Re: {ASUNTO}",
        fecha=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
        message_id=f"<respuesta-{remitente.split('@')[0]}>",
        adjuntos=(
            AdjuntoMensaje(
                tipo="application/pdf",
                sha256=hashlib.sha256(b"%PDF-1.4 comprobante").hexdigest(),
                nombre="comprobante.pdf",
            ),
        ),
    )


def test_corrida_desde_planilla_produce_el_informe_completo():
    """Plan, padrón y novedades por la planilla; el buzón por el fake. La
    corrida no distingue el soporte: el informe es el mismo que daría el CSV."""
    fuente, _ = crear_fuente_enrutada(
        {
            "Plan": respuesta_values(tabla_csv(PLAN_NOTEBOOKLM)),
            "Padron": respuesta_values(tabla_csv(PADRON_SINTETICO)),
            "Novedades": respuesta_values(tabla_csv(NOVEDADES_SINTETICAS)),
        }
    )
    plan = fuente.cargar_plan()
    padron = fuente.cargar_padron(actividad_id=plan.actividad_id)
    novedades = fuente.cargar_novedades()
    buzon = BuzonPropioMemoria(
        # Carla responde desde la dirección alternativa que el Departamento
        # cargó como novedad EMAIL_ALTERNATIVO.
        [mensaje_buzon("carla.lopez.personal@example.test")]
    )

    informe = correr_control_pagos(
        plan=plan, padron=padron, buzon=buzon, hoy=HOY, novedades=novedades
    )

    situaciones = {s.id_inscripcion: s for s in informe.situaciones}
    # Ana: la novedad CONFIRMADO_FUNDACION pisa lo derivado del buzón (D1).
    assert situaciones["PRE-NBLM2-001"].cuotas[0].estado == "PAGO_CONFIRMADO"
    # Bruno: bonificado según la columna del padrón.
    assert situaciones["PRE-NBLM2-002"].cuotas[0].estado == "BONIFICADA"
    # Carla: el comprobante llegó por la dirección alternativa declarada.
    assert situaciones["PRE-NBLM2-003"].cuotas[0].estado == (
        "COMPROBANTE_PRESENTADO"
    )
    assert informe.no_asociadas == ()
    assert len(informe.novedades_aplicadas) == 2


# --- El subcomando `control-pagos --planilla` ----------------------------------


def _entorno_planilla(monkeypatch, tmp_path):
    for clave, valor in _env_planilla().items():
        monkeypatch.setenv(clave, valor)
    monkeypatch.setenv(TOKEN_ENV, "TOKEN_ULTRA_SECRETO")
    buzon = tmp_path / "buzon"
    buzon.mkdir()
    return buzon


def test_cli_planilla_corre_la_corrida_con_transporte_fake(
    tmp_path, monkeypatch, capsys
):
    buzon = _entorno_planilla(monkeypatch, tmp_path)
    transporte = TransporteEnrutado(
        {
            "Plan": respuesta_values(tabla_csv(PLAN_NOTEBOOKLM)),
            "Padron": respuesta_values(tabla_csv(PADRON_SINTETICO)),
            "Novedades": respuesta_values(tabla_csv(NOVEDADES_SINTETICAS)),
        }
    )

    salida = main_control_pagos(
        [
            "--planilla",
            "--buzon", str(buzon),
            "--fecha", "2026-09-22",
        ],
        transport=transporte,
    )

    assert salida == 0
    respuesta = json.loads(capsys.readouterr().out)
    assert respuesta["estado"] == "OK"
    assert respuesta["actividad_id"] == ACTIVIDAD_ID
    assert len(transporte.solicitudes) == 3
    assert all(s["host"] == "sheets.googleapis.com" for s in transporte.solicitudes)


def test_cli_planilla_reporta_falla_de_pestana_con_codigo(
    tmp_path, monkeypatch, capsys
):
    buzon = _entorno_planilla(monkeypatch, tmp_path)
    transporte = TransporteEnrutado({})  # toda pestaña responde 400

    salida = main_control_pagos(
        ["--planilla", "--buzon", str(buzon), "--fecha", "2026-09-22"],
        transport=transporte,
    )

    assert salida == 2
    respuesta = json.loads(capsys.readouterr().out)
    assert respuesta == {
        "estado": "INVALIDA",
        "error": "workspace_range_invalid",
    }


def correr_cli(
    *args: str, env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(ROOT / "src")
    # Los secretos y la configuración de la planilla no pueden venir del
    # entorno del desarrollador: el subproceso siempre parte sin ellos.
    for clave in (
        TOKEN_ENV,
        SPREADSHEET_ID_ENV,
        RANGO_PLAN_ENV,
        RANGO_PADRON_ENV,
        RANGO_NOVEDADES_ENV,
    ):
        entorno.pop(clave, None)
    if env_extra:
        entorno.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "agente1", "control-pagos", *args],
        check=False,
        capture_output=True,
        text=True,
        env=entorno,
    )


def test_cli_planilla_sin_configuracion_reporta_config_incomplete(tmp_path):
    (tmp_path / "buzon").mkdir()

    proceso = correr_cli(
        "--planilla", "--buzon", str(tmp_path / "buzon"), "--fecha", "2026-09-22"
    )

    assert proceso.returncode == 2
    respuesta = json.loads(proceso.stdout)
    assert respuesta == {
        "estado": "INVALIDA",
        "error": "pagos_sheets_config_incomplete",
    }


def test_cli_planilla_rechaza_rutas_csv(tmp_path):
    proceso = correr_cli(
        "--planilla",
        "--plan", str(PLAN_NOTEBOOKLM),
        "--buzon", str(tmp_path),
        "--fecha", "2026-09-22",
    )

    assert proceso.returncode == 2
    # argparse reporta por stderr; stdout no lleva datos.
    assert proceso.stdout == ""
    assert "--planilla" in proceso.stderr


def test_cli_modo_csv_sigue_exigiendo_plan_y_padron(tmp_path):
    (tmp_path / "buzon").mkdir()

    proceso = correr_cli(
        "--buzon", str(tmp_path / "buzon"), "--fecha", "2026-09-22"
    )

    assert proceso.returncode == 2
    assert proceso.stdout == ""


def test_cli_planilla_falla_sin_token_sin_tocar_red(tmp_path):
    (tmp_path / "buzon").mkdir()

    proceso = correr_cli(
        "--planilla",
        "--buzon", str(tmp_path / "buzon"),
        "--fecha", "2026-09-22",
        env_extra=_env_planilla(),
    )

    # El token falta: el adapter lo pide antes de cualquier request y falla
    # con el código cerrado, así esta prueba nunca sale a la red.
    assert proceso.returncode == 2
    respuesta = json.loads(proceso.stdout)
    assert respuesta == {
        "estado": "INVALIDA",
        "error": "workspace_auth_unavailable",
    }


def test_token_de_entorno_alimenta_el_modo_planilla(monkeypatch):
    # `TokenEntornoProvider` lee AGENTE1_WORKSPACE_ACCESS_TOKEN: con la
    # variable declarada el request sale firmado.
    transporte = TransporteCaptura(respuesta_values(tabla_csv(NOVEDADES_SINTETICAS)))
    fuente = GoogleSheetsFuentePagos.desde_entorno(
        _env_planilla(),
        token_provider=TokenEntornoProvider(),
        transport=transporte,
    )
    monkeypatch.setenv(TOKEN_ENV, "TOKEN_ULTRA_SECRETO")

    fuente.cargar_novedades()

    assert transporte.solicitudes[0]["headers"]["Authorization"] == (
        "Bearer TOKEN_ULTRA_SECRETO"
    )
