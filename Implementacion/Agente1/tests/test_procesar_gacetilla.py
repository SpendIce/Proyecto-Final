import csv
import json

import pytest

from agente1 import FakeGenerator, procesar_fila_csv


class GeneratorQueNoDebeInvocarse:
    modelo = "fake-no-invocar"

    def generar(self, prompt: str) -> str:
        raise AssertionError("El generador no debe invocarse con datos incompletos")


class GeneratorQueCapturaPrompt:
    modelo = "fake-captura"

    def __init__(self) -> None:
        self.prompt = ""

    def generar(self, prompt: str) -> str:
        self.prompt = prompt
        return "Borrador capturado."


class GeneratorQueFalla:
    modelo = "fake-falla"

    def generar(self, prompt: str) -> str:
        raise RuntimeError("fallo remoto con secreto pruebas@example.invalid")


def test_fila_completa_genera_borrador_pendiente_y_log(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=[
                "id_solicitud",
                "titulo",
                "descripcion",
                "fecha",
                "publico",
                "organiza",
                "contacto",
                "fuente",
                "lugar",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "id_solicitud": "SYN-001",
                "titulo": "Taller sintético de vinculación",
                "descripcion": "Actividad ficticia para probar el flujo.",
                "fecha": "2026-08-05",
                "publico": "Comunidad universitaria ficticia",
                "organiza": "Equipo de prueba",
                "contacto": "pruebas@example.invalid",
                "fuente": "Dataset sintético versionado",
                "lugar": "Aula de prueba",
            }
        )

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-001",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator("Borrador sintético generado."),
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert resultado.borrador_path is not None
    assert resultado.borrador_path.read_text(encoding="utf-8") == (
        "# BORRADOR — NO PUBLICAR\n\n"
        "Borrador sintético generado.\n"
    )
    registro = json.loads(resultado.log_path.read_text(encoding="utf-8"))
    assert registro["id_solicitud"] == "SYN-001"
    assert registro["estado"] == "PENDIENTE_VALIDACION"
    assert registro["resultado"] == "borrador_generado"
    log_serializado = resultado.log_path.read_text(encoding="utf-8")
    assert "pruebas@example.invalid" not in log_serializado
    assert "Actividad ficticia para probar el flujo." not in log_serializado
    assert "Borrador sintético generado." not in log_serializado
    assert registro["input_hash"]
    assert registro["output_hash"]


def test_fila_incompleta_no_genera_borrador_y_registra_error(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=[
                "id_solicitud",
                "titulo",
                "descripcion",
                "fecha",
                "publico",
                "organiza",
                "contacto",
                "fuente",
                "lugar",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "id_solicitud": "SYN-002",
                "titulo": "Actividad sintética incompleta",
                "descripcion": "Caso ficticio sin contacto.",
                "fecha": "2026-08-06",
                "publico": "Público ficticio",
                "organiza": "Equipo de prueba",
                "contacto": "",
                "fuente": "Dataset sintético versionado",
                "lugar": "",
            }
        )

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-002",
        directorio_salida=tmp_path / "salida",
        generator=GeneratorQueNoDebeInvocarse(),
    )

    assert resultado.estado == "INCOMPLETA"
    assert resultado.borrador_path is None
    assert resultado.error == "Campos obligatorios faltantes: contacto"
    assert not (tmp_path / "salida" / "borradores").exists()
    registro = json.loads(resultado.log_path.read_text(encoding="utf-8"))
    assert registro["estado"] == "INCOMPLETA"
    assert registro["resultado"] == "datos_incompletos"
    assert registro["error"] == "Campos obligatorios faltantes: contacto"


def test_prompt_versionado_solo_solicita_un_borrador(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=[
                "id_solicitud",
                "titulo",
                "descripcion",
                "fecha",
                "publico",
                "organiza",
                "contacto",
                "fuente",
                "lugar",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "id_solicitud": "SYN-003",
                "titulo": "Jornada sintética",
                "descripcion": "Datos exclusivamente ficticios.",
                "fecha": "2026-08-07",
                "publico": "Público ficticio",
                "organiza": "Equipo de prueba",
                "contacto": "pruebas@example.invalid",
                "fuente": "Dataset sintético versionado",
                "lugar": "",
            }
        )
    generator = GeneratorQueCapturaPrompt()

    procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-003",
        directorio_salida=tmp_path / "salida",
        generator=generator,
    )

    assert "PROMPT_VERSION: gacetilla_v1" in generator.prompt
    assert "No inventes información" in generator.prompt
    assert "No apruebes, publiques ni envíes" in generator.prompt


def test_id_solicitud_no_permite_salir_del_directorio_de_borradores(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente\n"
        "../escape,Título,Descripción,2026-08-05,Público,Equipo,contacto@example.invalid,Sintética\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="id_solicitud inválido"):
        procesar_fila_csv(
            csv_path=csv_path,
            id_solicitud="../escape",
            directorio_salida=tmp_path / "salida",
            generator=FakeGenerator("No debe generarse."),
        )

    assert not (tmp_path / "salida").exists()
    assert not (tmp_path / "escape.md").exists()


def test_falla_del_generador_se_registra_sin_datos_y_no_crea_borrador(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente\n"
        "SYN-FAIL,Título secreto,Descripción,2026-08-05,Público,Equipo,pruebas@example.invalid,Sintética\n",
        encoding="utf-8",
    )

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-FAIL",
        directorio_salida=tmp_path / "salida",
        generator=GeneratorQueFalla(),
    )

    assert resultado.estado == "FALLIDA"
    assert resultado.borrador_path is None
    assert resultado.error == "Falló la generación del borrador"
    assert not (tmp_path / "salida" / "borradores").exists()
    registro_serializado = resultado.log_path.read_text(encoding="utf-8")
    registro = json.loads(registro_serializado)
    assert registro["resultado"] == "error_generacion"
    assert registro["estado"] == "FALLIDA"
    assert "pruebas@example.invalid" not in registro_serializado
    assert "Título secreto" not in registro_serializado
    assert "fallo remoto" not in registro_serializado


def test_salida_vacia_se_registra_como_fallida_y_no_crea_borrador(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente\n"
        "SYN-EMPTY,Título,Descripción,2026-08-05,Público,Equipo,contacto@example.invalid,Sintética\n",
        encoding="utf-8",
    )

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-EMPTY",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(" \n\t "),
    )

    assert resultado.estado == "FALLIDA"
    assert resultado.borrador_path is None
    assert resultado.error == "El generador devolvió contenido vacío"
    assert not (tmp_path / "salida" / "borradores").exists()
    registro = json.loads(resultado.log_path.read_text(encoding="utf-8"))
    assert registro["resultado"] == "salida_vacia"
    assert registro["output_hash"] is None


def test_csv_truncado_trata_valores_none_como_datos_incompletos(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente\n"
        "SYN-TRUNC,Título,Descripción,2026-08-05,Público,Equipo\n",
        encoding="utf-8",
    )

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-TRUNC",
        directorio_salida=tmp_path / "salida",
        generator=GeneratorQueNoDebeInvocarse(),
    )

    assert resultado.estado == "INCOMPLETA"
    assert resultado.borrador_path is None
    assert resultado.error == "Campos obligatorios faltantes: contacto, fuente"
    assert not (tmp_path / "salida" / "borradores").exists()
    registro = json.loads(resultado.log_path.read_text(encoding="utf-8"))
    assert registro["resultado"] == "datos_incompletos"
