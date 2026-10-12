"""Exportación de la pestaña de actividades de D2 a CSV.

Cubre: el CSV sale con el encabezado exacto del contrato v2 y lo lee
`CsvFuenteSolicitudes` sin transformación, el sidecar registra la fecha de
exportación y el commit de la base, y el volcado corre sobre el adapter de
Sheets con transporte fake (sin red ni Workspace real).
"""

import csv
import importlib.util
import json
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(__file__).parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "exportar_actividades_d2", ROOT / "scripts" / "exportar_actividades_d2.py"
)
assert _SPEC is not None and _SPEC.loader is not None
_modulo = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_modulo)

from agente1.fuentes import COLUMNAS_ACTIVIDADES_V2, CsvFuenteSolicitudes
from agente1.google_workspace import GoogleSheetsFuenteSolicitudes, RespuestaHttp


class _TokenFijo:
    def obtener_access_token(self) -> str:
        return "TOKEN_ULTRA_SECRETO"


class _TransporteFijo:
    def __init__(self, respuesta: RespuestaHttp) -> None:
        self.respuesta = respuesta
        self.solicitudes: list[dict[str, object]] = []

    def request(self, **kwargs: object) -> RespuestaHttp:
        self.solicitudes.append(kwargs)
        return self.respuesta


def _respuesta_values(filas: list[list[str]]) -> RespuestaHttp:
    return RespuestaHttp(
        status=200,
        body=json.dumps(
            {"range": "Actividades!A1:O20", "values": filas}
        ).encode(),
    )


def _fila_d2(id_actividad: str) -> list[str]:
    return [
        id_actividad,
        "Taller D2",
        "Caso exportado",
        "2026-08-05",
        "2026-08-19",
        "2026-08-03",
        "14:00",
        "presencial",
        "6",
        "estudiantes",
        "Equipo D2",
        "contacto@example.invalid",
        "https://example.invalid/informe",
        "https://example.invalid/inscripcion",
        "Aula D2",
    ]


def test_exporta_csv_con_encabezado_v2_legible_por_el_adapter(tmp_path: Path):
    transporte = _TransporteFijo(
        _respuesta_values(
            [
                list(COLUMNAS_ACTIVIDADES_V2),
                _fila_d2("D2-001"),
                _fila_d2("D2-002"),
            ]
        )
    )
    fuente = GoogleSheetsFuenteSolicitudes(
        spreadsheet_id="sheet_D2",
        rango_a1="Actividades!A1:O20",
        token_provider=_TokenFijo(),
        transport=transporte,
        timeout_s=5,
    )
    csv_path = tmp_path / "actividades_d2.csv"

    manifest = _modulo.exportar_actividades(
        fuente=fuente,
        csv_path=csv_path,
        commit_base="abc123",
        fecha_exportacion=datetime(2026, 10, 1, 12, 30, tzinfo=timezone.utc),
    )

    # Una sola lectura GET contra Sheets: el exportador es tan de sólo lectura
    # como la fuente que consume.
    assert len(transporte.solicitudes) == 1
    assert transporte.solicitudes[0]["method"] == "GET"

    # El CSV sale con el encabezado exacto del contrato y el adapter lo
    # consume sin transformación: obtener y enumerar ven los 15 campos.
    with csv_path.open(encoding="utf-8", newline="") as archivo:
        assert archivo.readline().strip() == ",".join(COLUMNAS_ACTIVIDADES_V2)
    lector = CsvFuenteSolicitudes(csv_path)
    fila = lector.obtener("D2-001")
    assert tuple(fila) == COLUMNAS_ACTIVIDADES_V2
    assert fila["fecha_inicio"] == "2026-08-05"
    assert fila["enlace_inscripcion"] == "https://example.invalid/inscripcion"
    assert [f["id_actividad"] for f in lector.enumerar()] == ["D2-001", "D2-002"]

    # El sidecar registra fecha de exportación y commit de la base.
    meta_path = csv_path.with_suffix(".csv.meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["schema_version"] == "exportacion_actividades_d2_v1"
    assert meta["columnas_contrato"] == "actividades_planilla_v2"
    assert meta["columnas"] == list(COLUMNAS_ACTIVIDADES_V2)
    assert meta["fecha_exportacion"] == "2026-10-01T12:30:00+00:00"
    assert meta["commit_base"] == "abc123"
    assert meta["filas"] == 2
    assert meta["csv_sha256"] == manifest["csv_sha256"]


def test_exporta_campos_opcionales_vacios_como_columnas_vacias(tmp_path: Path):
    fila_minima = _fila_d2("D2-003")
    for indice in (4, 5, 6, 7, 8, 13, 14):  # opcionales vacíos
        fila_minima[indice] = ""
    transporte = _TransporteFijo(
        _respuesta_values([list(COLUMNAS_ACTIVIDADES_V2), fila_minima])
    )
    fuente = GoogleSheetsFuenteSolicitudes(
        spreadsheet_id="sheet_D2",
        rango_a1="Actividades!A1:O20",
        token_provider=_TokenFijo(),
        transport=transporte,
        timeout_s=5,
    )
    csv_path = tmp_path / "actividades_d2.csv"

    _modulo.exportar_actividades(
        fuente=fuente,
        csv_path=csv_path,
        commit_base="def456",
        fecha_exportacion=datetime(2026, 10, 2, tzinfo=timezone.utc),
    )

    fila = CsvFuenteSolicitudes(csv_path).obtener("D2-003")
    for opcional in (
        "fecha_fin",
        "fecha_limite_inscripcion",
        "hora",
        "modalidad",
        "duracion_horas",
        "enlace_inscripcion",
        "lugar",
    ):
        assert fila[opcional] == ""


class _FuenteMemoria:
    def __init__(self, filas: list[dict[str, str]]) -> None:
        self._filas = filas

    def enumerar(self) -> list[dict[str, str]]:
        return self._filas


def test_exportador_acepta_cualquier_fuente_del_puerto(tmp_path: Path):
    csv_path = tmp_path / "export.csv"

    manifest = _modulo.exportar_actividades(
        fuente=_FuenteMemoria([]),
        csv_path=csv_path,
        commit_base="000aaa",
        fecha_exportacion=datetime(2026, 10, 3, tzinfo=timezone.utc),
    )

    assert manifest["filas"] == 0
    assert CsvFuenteSolicitudes(csv_path).enumerar() == []
    assert manifest["fecha_exportacion"] == "2026-10-03T00:00:00+00:00"
