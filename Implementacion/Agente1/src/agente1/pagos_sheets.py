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

- **El HTTP no se vuelve a escribir.** El adapter compone un
  `GoogleSheetsLectorValores` por pestaña —el lector crudo de `values.get`
  que #71 extrajo del adapter de actividades— así que hereda todas las
  guardas del lector de Sheets existente: planilla y rango fijados al
  construir como allowlist efectiva, deadline absoluto, tope de respuesta de
  1 MiB, token efímero por operación y errores por código sin datos adentro.
  El único host que toca es `sheets.googleapis.com`: el scope `spreadsheets`
  ya concedido alcanza, no hay otro host ni otro scope.
- **Los errores del lector se traducen a `ControlPagosError`.** El lector
  crudo habla en `FuenteSolicitudesError` porque nació del puerto de
  solicitudes; las fuentes de la corrida hablan en `ControlPagosError`, así
  el subcomando `control-pagos` reporta cualquier falla con su código igual
  que las del CSV, sin distinguir el soporte del que salió. El código se
  conserva: es el mismo vocabulario `workspace_*`.
- **Los tres rangos se fijan al construir el adapter.** Tres lectores, un
  request por pestaña, tres llamadas por corrida; no hay forma de pedir otra
  hoja ni otro rango en tiempo de ejecución.
- **Una pestaña faltante o vacía nunca devuelve una lista vacía.** Un rango
  que nombra una pestaña que no existe responde HTTP 400 y el lector lo
  traduce a `workspace_unavailable`; un rango sin datos responde sin
  `values`, que es `workspace_response_invalid`; una pestaña con encabezado
  distinto es el `*_encabezado_invalid` del CSV. Los tres caminos fallan
  explícito: una lista vacía sólo puede salir de una pestaña con el
  encabezado correcto y cero filas de datos, que es lo que el CSV produce
  para el mismo contenido.

La configuración vive en el entorno, fuera del repo, como el resto de la
configuración de Workspace: el identificador de la planilla es el mismo
`AGENTE1_WORKSPACE_SPREADSHEET_ID` del camino D2 (es la misma planilla, no un
recurso nuevo) y los tres rangos van en variables propias del prefijo
`AGENTE1_PAGOS_`, que el loader de Workspace no conoce ni necesita.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from .fuentes import FuenteSolicitudesError
from .google_workspace import (
    AccessTokenProvider,
    GoogleSheetsLectorValores,
    TransporteHttp,
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
    constructor —cada uno arma su `GoogleSheetsLectorValores`, que hace su
    propia validación, así un despliegue mal configurado falla al arrancar—
    y no hay forma de pedir otro recurso después. Los tres métodos hacen un
    único `values.get` cada uno y devuelven las mismas estructuras que los
    loaders CSV, así que la corrida y su informe son indistinguibles del
    camino por archivos.
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
        # Cada lector valida su rango y su planilla al construirse: si la
        # configuración es inválida, el primero en fallar levanta el
        # ValueError antes de que el adapter exista.
        self._lector_plan = GoogleSheetsLectorValores(
            spreadsheet_id=spreadsheet_id,
            rango_a1=rango_plan,
            token_provider=token_provider,
            transport=transport,
            timeout_s=timeout_s,
        )
        self._lector_padron = GoogleSheetsLectorValores(
            spreadsheet_id=spreadsheet_id,
            rango_a1=rango_padron,
            token_provider=token_provider,
            transport=transport,
            timeout_s=timeout_s,
        )
        self._lector_novedades = GoogleSheetsLectorValores(
            spreadsheet_id=spreadsheet_id,
            rango_a1=rango_novedades,
            token_provider=token_provider,
            transport=transport,
            timeout_s=timeout_s,
        )

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
            _leer_tabla(self._lector_plan),
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
            _leer_tabla(self._lector_padron),
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
            _leer_tabla(self._lector_novedades),
            COLUMNAS_NOVEDADES,
            COLUMNAS_NOVEDADES,
            "novedades",
        )
        return _novedades_desde_filas(filas)


def _leer_tabla(lector: GoogleSheetsLectorValores) -> list[object]:
    """El `values` crudo, con el error traducido al vocabulario de la corrida.

    El lector compartido reporta en `FuenteSolicitudesError` por haber nacido
    del puerto de solicitudes; para la corrida toda fuente falla en
    `ControlPagosError`. El código se pasa tal cual — es la misma tabla
    `workspace_*` — y `from None` corta la cadena para que no viaje contexto
    del dominio equivocado.
    """

    try:
        return lector.leer_valores()
    except FuenteSolicitudesError as exc:
        raise ControlPagosError(exc.code) from None
