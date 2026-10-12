"""Adapters de la corrida de pagos que leen las pestañas de la planilla D2.

`GoogleSheetsFuentePagos` es el camino Workspace de las tres fuentes tabulares
de `correr_control_pagos` —el plan de pago, el padrón y las novedades del
Departamento— para la demo en vivo. Produce exactamente las mismas estructuras
de dominio que los loaders CSV (`PlanPago`, `list[Preinscripto]`,
`list[NovedadPago]`), porque comparte con ellos la interpretación de las
filas: el `values` de cada pestaña pasa por `pagos._filas_desde_tabla`, que
valida el encabezado con la misma regla posicional del CSV, y después por los
mismos `pagos._*_desde_filas` que usan `cargar_*_csv`. La corrida no sabe de
dónde vienen las fuentes (ADR 0003).

Decisiones que no se ven en el código:

- **Los tres rangos se fijan al construir el adapter.** Igual que el lector de
  la pestaña de actividades, la planilla y los rangos son la allowlist
  efectiva del recurso: el agente no puede pedir otra hoja ni otro rango en
  tiempo de ejecución. Toda la validación de configuración ocurre en el
  constructor, para que un despliegue mal configurado falle al arrancar.
- **Mismas guardas que el resto de los adapters de Workspace.** Mismo
  transporte `TransporteHttp` con deadline absoluto y tope de respuesta de
  1 MiB, mismo token efímero pedido por operación al `AccessTokenProvider`,
  misma traducción de errores a códigos sin datos adentro. El único host que
  toca es `sheets.googleapis.com` con `values.get`: el scope `spreadsheets`
  ya concedido alcanza, no hay otro host ni otro scope.
- **`FORMATTED_VALUE` por la misma razón que el lector de actividades.** Lo
  que devuelve la API es lo que ve una persona en la celda —una fecha como la
  escribió quien cargó la pestaña—, que es lo que el contrato espera.
- **Una pestaña faltante o vacía nunca devuelve una lista vacía.** Un rango
  que nombra una pestaña que no existe devuelve HTTP 400, que se traduce a
  `workspace_range_invalid`; un rango sin datos devuelve una respuesta sin
  `values`, que es `workspace_response_invalid`; una pestaña con encabezado
  distinto es el `*_encabezado_invalid` del CSV. Los tres caminos fallan
  explícito: una lista vacía sólo puede salir de una pestaña con el
  encabezado correcto y cero filas de datos, que es lo que el CSV produce
  para el mismo contenido.
- **Los errores viajan como `ControlPagosError`.** Es el error de las fuentes
  de la corrida, así el subcomando `control-pagos` los reporta con su código
  igual que los del CSV, sin distinguir el soporte del que salieron.

La configuración vive en el entorno, fuera del repo, como el resto de la
configuración de Workspace: el identificador de la planilla es el mismo
`AGENTE1_WORKSPACE_SPREADSHEET_ID` del camino D2 (es la misma planilla, no un
recurso nuevo) y los tres rangos van en variables propias del prefijo
`AGENTE1_PAGOS_`, que el loader de Workspace no conoce ni necesita.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
import math
import os
import time
from urllib.parse import quote

from .google_workspace import (
    AccessTokenProvider,
    MAX_WORKSPACE_RESPONSE_BYTES,
    MAX_WORKSPACE_TIMEOUT_S,
    SHEETS_HOST,
    HttpsWorkspaceTransport,
    TransporteHttp,
    ID_RE,
    _RespuestaDemasiadoGrande,
    _codigo_http,
)
from .pagos import (
    COLUMNAS_NOVEDADES,
    COLUMNAS_PADRON,
    COLUMNAS_PADRON_OBLIGATORIAS,
    COLUMNAS_PLAN,
    COLUMNAS_PLAN_OBLIGATORIAS,
    ControlPagosError,
    NovedadPago,
    PlanPago,
    Preinscripto,
    _filas_desde_tabla,
    _novedades_desde_filas,
    _padron_desde_filas,
    _plan_desde_filas,
)
from .workspace_config import ConfiguracionWorkspaceError


# La planilla es la misma D2 de los adapters de Workspace: la allowlist del
# recurso no cambia por leerle más pestañas. Los rangos de las pestañas de
# pagos van en variables propias porque no forman parte del contrato de
# `workspace_config` (que exige plantilla y carpeta, ajenas a esta corrida).
SPREADSHEET_ID_ENV = "AGENTE1_WORKSPACE_SPREADSHEET_ID"
RANGO_PLAN_ENV = "AGENTE1_PAGOS_RANGO_PLAN"
RANGO_PADRON_ENV = "AGENTE1_PAGOS_RANGO_PADRON"
RANGO_NOVEDADES_ENV = "AGENTE1_PAGOS_RANGO_NOVEDADES"
_RANGOS_ENV = (RANGO_PLAN_ENV, RANGO_PADRON_ENV, RANGO_NOVEDADES_ENV)


class GoogleSheetsFuentePagos:
    """Lee las tres pestañas de la corrida de pagos de la planilla D2.

    Un adapter por planilla: la planilla y los tres rangos se fijan en el
    constructor y no hay forma de pedir otro recurso después. Los tres
    métodos hacen un único `values.get` cada uno —tres llamadas por corrida—
    y devuelven las mismas estructuras que los loaders CSV, así que la
    corrida y su informe son indistinguibles del camino por archivos.
    """

    def __init__(
        self,
        *,
        spreadsheet_id: str,
        rango_plan: str,
        rango_padron: str,
        rango_novedades: str,
        token_provider: AccessTokenProvider,
        transport: TransporteHttp | None = None,
        timeout_s: float = 10.0,
    ) -> None:
        if (
            not isinstance(spreadsheet_id, str)
            or ID_RE.fullmatch(spreadsheet_id) is None
            or any(
                not isinstance(rango, str)
                or not 1 <= len(rango) <= 256
                or any(
                    ord(caracter) < 32 or ord(caracter) == 127
                    for caracter in rango
                )
                for rango in (rango_plan, rango_padron, rango_novedades)
            )
            or isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s)
            or not 0 < timeout_s <= MAX_WORKSPACE_TIMEOUT_S
        ):
            raise ValueError("configuración de Google Sheets inválida")
        self._spreadsheet_id = spreadsheet_id
        self._rango_plan = rango_plan
        self._rango_padron = rango_padron
        self._rango_novedades = rango_novedades
        self._token_provider = token_provider
        self._transport = transport or HttpsWorkspaceTransport()
        self._timeout_s = float(timeout_s)

    @classmethod
    def desde_entorno(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        token_provider: AccessTokenProvider,
        transport: TransporteHttp | None = None,
        timeout_s: float = 10.0,
    ) -> "GoogleSheetsFuentePagos":
        """Construye el adapter con la planilla y los rangos del entorno.

        Es el camino productivo del subcomando `control-pagos --planilla`.
        Las cuatro variables son exigidas juntas —falta alguna, no hay
        adapter— y un valor mal formado también impide que el objeto exista.
        Los errores son `ConfiguracionWorkspaceError` con código cerrado,
        nunca con el valor adentro.
        """

        env = os.environ if environ is None else environ
        claves = (SPREADSHEET_ID_ENV, *_RANGOS_ENV)
        if any(not (env.get(clave) or "").strip() for clave in claves):
            raise ConfiguracionWorkspaceError("pagos_sheets_config_incomplete")
        try:
            return cls(
                spreadsheet_id=env[SPREADSHEET_ID_ENV],
                rango_plan=env[RANGO_PLAN_ENV],
                rango_padron=env[RANGO_PADRON_ENV],
                rango_novedades=env[RANGO_NOVEDADES_ENV],
                token_provider=token_provider,
                transport=transport,
                timeout_s=timeout_s,
            )
        except ValueError:
            raise ConfiguracionWorkspaceError(
                "pagos_sheets_config_invalid"
            ) from None

    def cargar_plan(self) -> PlanPago:
        """El plan de pago de la actividad, leído de su pestaña."""

        filas = _filas_desde_tabla(
            self._leer_values(self._rango_plan),
            COLUMNAS_PLAN_OBLIGATORIAS,
            COLUMNAS_PLAN,
            "plan",
        )
        return _plan_desde_filas(filas)

    def cargar_padron(self, *, actividad_id: str) -> list[Preinscripto]:
        """El padrón de la actividad, leído de su pestaña.

        Toma `actividad_id` igual que `cargar_padron_csv`: todas las filas
        tienen que pertenecer a esa actividad o la pestaña entera se rechaza.
        """

        filas = _filas_desde_tabla(
            self._leer_values(self._rango_padron),
            COLUMNAS_PADRON_OBLIGATORIAS,
            COLUMNAS_PADRON,
            "padron",
        )
        return _padron_desde_filas(filas, actividad_id)

    def cargar_novedades(self) -> list[NovedadPago]:
        """Las novedades del Departamento, leídas de su pestaña (§6.2).

        Una pestaña con sólo el encabezado produce una lista vacía —igual que
        el CSV con sólo encabezado— porque «no hay novedades cargadas» es un
        dato legítimo; lo que nunca produce lista vacía es una pestaña
        faltante o con encabezado distinto.
        """

        filas = _filas_desde_tabla(
            self._leer_values(self._rango_novedades),
            COLUMNAS_NOVEDADES,
            COLUMNAS_NOVEDADES,
            "novedades",
        )
        return _novedades_desde_filas(filas)

    def _leer_values(self, rango_a1: str) -> list[object]:
        """Un `values.get` del rango fijado: validación cruda, sin interpretar.

        La traducción de la respuesta a filas de dominio es trabajo de
        `pagos._filas_desde_tabla`; acá sólo se comprueba que la respuesta sea
        un `values` de Sheets bien formado y se mapean las fallas del medio a
        los códigos del vocabulario de Workspace.
        """

        token = self._obtener_token()
        # `FORMATTED_VALUE` devuelve lo que ve una persona en la celda, no el
        # valor serial interno: una fecha llega como la escribió quien cargó
        # la pestaña, que es lo que el contrato espera leer.
        target = (
            f"/v4/spreadsheets/{self._spreadsheet_id}/values/"
            f"{quote(rango_a1, safe='')}"
            "?majorDimension=ROWS&valueRenderOption=FORMATTED_VALUE"
        )
        try:
            respuesta = self._transport.request(
                method="GET",
                host=SHEETS_HOST,
                target=target,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                body=None,
                deadline=time.monotonic() + self._timeout_s,
                max_response_bytes=MAX_WORKSPACE_RESPONSE_BYTES,
            )
        except _RespuestaDemasiadoGrande:
            raise ControlPagosError("workspace_response_too_large") from None
        except Exception:
            # `from None` corta la cadena a propósito: el mensaje original del
            # transporte puede contener la URL con el id de la planilla, y
            # estos errores terminan en logs y reportes.
            raise ControlPagosError("workspace_unavailable") from None

        if len(respuesta.body) > MAX_WORKSPACE_RESPONSE_BYTES:
            raise ControlPagosError("workspace_response_too_large")
        if respuesta.status != 200:
            raise ControlPagosError(_codigo_respuesta(respuesta.status))
        try:
            documento = json.loads(respuesta.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ControlPagosError("workspace_response_invalid") from None
        if not isinstance(documento, dict) or not isinstance(
            documento.get("values"), list
        ):
            # Un rango sin datos responde 200 pero omite `values`; para las
            # pestañas de pagos eso no es una tabla vacía sino una fuente que
            # no está en la forma prometida — falla explícito, nunca lista
            # vacía.
            raise ControlPagosError("workspace_response_invalid")
        return documento["values"]

    def _obtener_token(self) -> str:
        try:
            token = self._token_provider.obtener_access_token()
        except Exception:
            raise ControlPagosError("workspace_auth_unavailable") from None
        if (
            not isinstance(token, str)
            or not token.strip()
            or token != token.strip()
            or "\r" in token
            or "\n" in token
        ):
            raise ControlPagosError("workspace_auth_unavailable")
        return token


def _codigo_respuesta(status: int) -> str:
    """HTTP a código de auditoría, con el 400 propio de `values.get`.

    En `values.get` un 400 significa que el rango no se pudo resolver —la
    pestaña faltante es el caso esperado— y merece código propio: no es lo
    mismo «la pestaña no está» que «Sheets no responde». El resto de la tabla
    es la misma del lector de actividades.
    """

    if status == 400:
        return "workspace_range_invalid"
    return _codigo_http(status)
