"""Puerto de entrada y adapter CSV: id inexistente, id duplicado, contrato de
columnas roto y normalización de campos opcionales."""

import csv
from importlib.resources import files
import json

import pytest

from agente1.fuentes import (
    COLUMNAS_GACETILLA,
    CsvFuenteSolicitudes,
    FuenteSolicitudes,
    FuenteSolicitudesError,
)
from agente1.procesamiento import FakeGenerator, procesar_solicitud


def test_columnas_de_fuentes_siguen_el_contrato_versionado():
    contrato = json.loads(
        files("agente1")
        .joinpath("contracts", "gacetilla_input_v1.schema.json")
        .read_text(encoding="utf-8")
    )

    assert tuple(contrato["properties"]) == COLUMNAS_GACETILLA


def test_csv_es_un_adapter_del_port_fuente_solicitudes(tmp_path):
    csv_path = tmp_path / "solicitudes.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=COLUMNAS_GACETILLA)
        writer.writeheader()
        writer.writerow(
            {
                "id_solicitud": "SYN-001",
                "titulo": "Actividad sintética",
                "descripcion": "Caso de prueba",
                "fecha": "2026-08-05",
                "publico": "Comunidad ficticia",
                "organiza": "Equipo de prueba",
                "contacto": "pruebas@example.invalid",
                "fuente": "Dataset sintético",
                "lugar": "",
            }
        )
    fuente: FuenteSolicitudes = CsvFuenteSolicitudes(csv_path)

    fila = fuente.obtener("SYN-001")

    assert fila["titulo"] == "Actividad sintética"
    assert fila["lugar"] == ""
    assert tuple(fila) == COLUMNAS_GACETILLA


def test_csv_truncado_normaliza_none_para_preservar_validacion_existente(tmp_path):
    csv_path = tmp_path / "solicitudes.csv"
    csv_path.write_text(
        ",".join(COLUMNAS_GACETILLA) + "\n"
        "SYN-TRUNC,Título,Descripción,2026-08-05,Público,Equipo\n",
        encoding="utf-8",
    )

    fila = CsvFuenteSolicitudes(csv_path).obtener("SYN-TRUNC")

    assert fila["contacto"] == ""
    assert fila["fuente"] == ""
    assert fila["lugar"] == ""


def test_csv_rechaza_id_duplicado_sin_copiar_datos_o_path(tmp_path):
    csv_path = tmp_path / "secreto.csv"
    csv_path.write_text(
        ",".join(COLUMNAS_GACETILLA) + "\n"
        + "SYN-DUP," + ",".join(["dato-secreto"] * 8) + "\n"
        + "SYN-DUP," + ",".join(["otro-secreto"] * 8) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(FuenteSolicitudesError) as error:
        CsvFuenteSolicitudes(csv_path).obtener("SYN-DUP")

    assert error.value.code == "source_duplicate_id"
    assert str(error.value) == "source_duplicate_id"
    assert "dato-secreto" not in str(error.value)
    assert "secreto.csv" not in str(error.value)


def test_csv_inexistente_usa_codigo_cerrado(tmp_path):
    csv_path = tmp_path / "solicitudes.csv"
    csv_path.write_text(",".join(COLUMNAS_GACETILLA) + "\n", encoding="utf-8")

    with pytest.raises(FuenteSolicitudesError) as error:
        CsvFuenteSolicitudes(csv_path).obtener("SYN-AUSENTE")

    assert error.value.code == "source_request_not_found"


def test_procesamiento_consume_el_port_sin_conocer_csv(tmp_path):
    class FuenteFalsa:
        def obtener(self, id_solicitud: str) -> dict[str, str]:
            assert id_solicitud == "SYN-PORT"
            return dict(
                zip(
                    COLUMNAS_GACETILLA,
                    [
                        "SYN-PORT",
                        "Actividad por port",
                        "Caso controlado",
                        "2026-08-05",
                        "Comunidad ficticia",
                        "Equipo de prueba",
                        "pruebas@example.invalid",
                        "Dataset sintético",
                        "",
                    ],
                    strict=True,
                )
            )

    contenido = (
        "## TÍTULO\nActividad por port\n\n"
        "## DATOS DE LA ACTIVIDAD\nFecha: 2026-08-05\n"
        "Organiza: Equipo de prueba\n\n"
        "## CONTACTO\npruebas@example.invalid\n\n"
        "## BAJADA\nCaso sintético controlado.\n\n"
        "## CUERPO\nLa actividad requiere validación humana."
    )

    resultado = procesar_solicitud(
        fuente=FuenteFalsa(),
        id_solicitud="SYN-PORT",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(contenido),
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert resultado.borrador_path is not None


class GeneratorQueNoDebeInvocarse:
    modelo = "fake-no-invocar"
    num_predict = None

    def generar(self, prompt: str) -> str:
        raise AssertionError("el generador no debe invocarse")


@pytest.mark.parametrize(
    ("mutacion", "codigo"),
    [
        (lambda fila: {**fila, "id_solicitud": "SYN-OTRA"}, "source_id_mismatch"),
        (lambda fila: {**fila, "titulo": 42}, "source_contract_invalid"),
    ],
)
def test_core_rechaza_fila_fuente_no_confiable_antes_del_generador(
    tmp_path, mutacion, codigo
):
    fila_base = dict(
        zip(
            COLUMNAS_GACETILLA,
            [
                "SYN-TRUST",
                "Título secreto",
                "Descripción secreta",
                "2026-08-05",
                "Público secreto",
                "Equipo secreto",
                "secreto@example.invalid",
                "Fuente secreta",
                "Lugar secreto",
            ],
            strict=True,
        )
    )

    class FuenteNoConfiable:
        def obtener(self, id_solicitud: str):
            return mutacion(fila_base)

    resultado = procesar_solicitud(
        fuente=FuenteNoConfiable(),
        id_solicitud="SYN-TRUST",
        directorio_salida=tmp_path / "salida",
        generator=GeneratorQueNoDebeInvocarse(),
    )

    assert resultado.estado == "FALLIDA"
    assert resultado.borrador_path is None
    assert resultado.correlation_id
    registro_serializado = resultado.log_path.read_text(encoding="utf-8")
    registro = json.loads(registro_serializado)
    assert registro["resultado"] == "source_failure"
    assert registro["source_error_code"] == codigo
    assert "secreto" not in registro_serializado.casefold()
    assert not (tmp_path / "salida" / "borradores").exists()


@pytest.mark.parametrize("incluir_lugar", [False, True])
def test_core_normaliza_lugar_opcional_e_ignora_extras_sin_filtrarlos(
    tmp_path, incluir_lugar
):
    fila = {
        "id_solicitud": "SYN-SCHEMA",
        "titulo": "Actividad schema",
        "descripcion": "Caso controlado",
        "fecha": "2026-08-05",
        "publico": "Comunidad ficticia",
        "organiza": "Equipo de prueba",
        "contacto": "pruebas@example.invalid",
        "fuente": "Dataset sintético",
        "nota_privada": "SECRETO_QUE_NO_DEBE_PASAR",
        "extra_no_string": 42,
    }
    if incluir_lugar:
        fila["lugar"] = "Aula ficticia"

    class FuenteConAdditionalProperties:
        def obtener(self, id_solicitud: str):
            return fila

    class GeneratorQueCaptura:
        modelo = "fake-captura"
        num_predict = None

        def __init__(self) -> None:
            self.prompt = ""

        def generar(self, prompt: str) -> str:
            self.prompt = prompt
            linea_lugar = "\nLugar: Aula ficticia" if incluir_lugar else ""
            return (
                "## TÍTULO\nActividad schema\n\n"
                "## DATOS DE LA ACTIVIDAD\nFecha: 2026-08-05\n"
                f"Organiza: Equipo de prueba{linea_lugar}\n\n"
                "## CONTACTO\npruebas@example.invalid\n\n"
                "## BAJADA\nCaso sintético controlado.\n\n"
                "## CUERPO\nLa actividad requiere validación humana."
            )

    generator = GeneratorQueCaptura()
    resultado = procesar_solicitud(
        fuente=FuenteConAdditionalProperties(),
        id_solicitud="SYN-SCHEMA",
        directorio_salida=tmp_path / "salida",
        generator=generator,
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert "nota_privada" not in generator.prompt
    assert "SECRETO_QUE_NO_DEBE_PASAR" not in generator.prompt
    assert "extra_no_string" not in generator.prompt
    assert "SECRETO_QUE_NO_DEBE_PASAR" not in resultado.log_path.read_text(
        encoding="utf-8"
    )


def test_core_audita_id_invalido_sin_consultar_fuente_ni_copiarlo(tmp_path):
    class FuenteQueNoDebeInvocarse:
        def obtener(self, id_solicitud: str):
            raise AssertionError("la fuente no debe invocarse")

    resultado = procesar_solicitud(
        fuente=FuenteQueNoDebeInvocarse(),
        id_solicitud="../secreto",
        directorio_salida=tmp_path / "salida",
        generator=GeneratorQueNoDebeInvocarse(),
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.correlation_id
    registro_serializado = resultado.log_path.read_text(encoding="utf-8")
    registro = json.loads(registro_serializado)
    assert registro["source_error_code"] == "source_request_invalid"
    assert registro["resultado"] == "source_invalid"
    assert "../secreto" not in registro_serializado
    assert registro["id_solicitud"] is None


def test_core_audita_solicitud_inexistente_con_codigo_cerrado(tmp_path):
    class FuenteSinSolicitud:
        def obtener(self, id_solicitud: str):
            raise FuenteSolicitudesError("source_request_not_found")

    resultado = procesar_solicitud(
        fuente=FuenteSinSolicitud(),
        id_solicitud="SYN-AUSENTE",
        directorio_salida=tmp_path / "salida",
        generator=GeneratorQueNoDebeInvocarse(),
    )

    assert resultado.estado == "INVALIDA"
    registro_serializado = resultado.log_path.read_text(encoding="utf-8")
    registro = json.loads(registro_serializado)
    assert registro["source_error_code"] == "source_request_not_found"
    assert "SYN-AUSENTE" not in registro_serializado


def test_core_no_confia_en_codigo_de_error_emitido_por_una_fuente(tmp_path):
    class FuenteConErrorMalicioso:
        def obtener(self, id_solicitud: str):
            raise FuenteSolicitudesError(
                "TOKEN_SECRETO cuerpo-remoto secreto@example.invalid"
            )

    resultado = procesar_solicitud(
        fuente=FuenteConErrorMalicioso(),
        id_solicitud="SYN-ERROR",
        directorio_salida=tmp_path / "salida",
        generator=GeneratorQueNoDebeInvocarse(),
    )

    registro_serializado = resultado.log_path.read_text(encoding="utf-8")
    registro = json.loads(registro_serializado)
    assert resultado.estado == "FALLIDA"
    assert registro["source_error_code"] == "source_unavailable"
    assert "TOKEN_SECRETO" not in registro_serializado
    assert "secreto@example.invalid" not in registro_serializado
