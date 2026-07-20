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


def salida_conforme(
    *,
    titulo: str,
    fecha: str,
    organiza: str,
    contacto: str,
    lugar: str | None = None,
) -> str:
    lugar_linea = f"\nLugar: {lugar}" if lugar else ""
    return (
        "## TÍTULO\n"
        f"{titulo}\n\n"
        "## DATOS DE LA ACTIVIDAD\n"
        f"Fecha: {fecha}\n"
        f"Organiza: {organiza}{lugar_linea}\n\n"
        "## CONTACTO\n"
        f"{contacto}\n\n"
        "## BAJADA\n"
        "Borrador sintético para validar el flujo técnico.\n\n"
        "## CUERPO\n"
        "La actividad requiere revisión humana antes de cualquier publicación."
    )


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

    contenido = salida_conforme(
        titulo="Taller sintético de vinculación",
        fecha="2026-08-05",
        organiza="Equipo de prueba",
        contacto="pruebas@example.invalid",
        lugar="Aula de prueba",
    )
    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-001",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(contenido),
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert resultado.borrador_path is not None
    assert resultado.borrador_path.read_text(encoding="utf-8") == (
        f"# BORRADOR — NO PUBLICAR\n\n{contenido}\n"
    )
    registro = json.loads(resultado.log_path.read_text(encoding="utf-8"))
    assert registro["id_solicitud"] == "SYN-001"
    assert registro["estado"] == "PENDIENTE_VALIDACION"
    assert registro["resultado"] == "borrador_generado"
    log_serializado = resultado.log_path.read_text(encoding="utf-8")
    assert "pruebas@example.invalid" not in log_serializado
    assert "Actividad ficticia para probar el flujo." not in log_serializado
    assert contenido not in log_serializado
    assert registro["input_hash"]
    assert registro["output_hash"]
    assert registro["num_predict"] is None


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

    assert "PROMPT_VERSION: gacetilla_v2" in generator.prompt
    assert "CONTRACT_VERSION: gacetilla_input_v1" in generator.prompt
    assert "PROVISIONAL_NO_INSTITUCIONAL" in generator.prompt
    assert "## DATOS DE LA ACTIVIDAD" in generator.prompt
    assert generator.prompt.index("## DATOS DE LA ACTIVIDAD") < generator.prompt.index(
        "## BAJADA"
    )
    assert "--- FIN BORRADOR ---" not in generator.prompt
    assert "Encuentro ficticio de ejemplo" in generator.prompt
    assert "No inventes información" in generator.prompt
    assert "No apruebes, publiques ni envíes" in generator.prompt


def test_id_solicitud_no_permite_salir_del_directorio_de_borradores(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente\n"
        "../escape,Título,Descripción,2026-08-05,Público,Equipo,contacto@example.invalid,Sintética\n",
        encoding="utf-8",
    )

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="../escape",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator("No debe generarse."),
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.borrador_path is None
    registro = resultado.log_path.read_text(encoding="utf-8")
    assert "../escape" not in registro
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


def test_salida_no_conforme_se_audita_sin_crear_borrador(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente,lugar\n"
        "SYN-BASURA,Título verificable,Descripción,2026-08-10,Público,Equipo,contacto@example.invalid,Sintética,Aula 1\n",
        encoding="utf-8",
    )
    salida_basura = (
        "## TÍTULO\nTexto genérico sin hechos.\n\n## BAJADA\nTexto genérico.\n\n"
        "## CUERPO\n" + "contenido irrelevante " * 20 + "\n\n"
        "## DATOS DE LA ACTIVIDAD\nSin datos.\n\n## CONTACTO\nNo informado."
    )

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-BASURA",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(salida_basura),
    )

    assert resultado.estado == "FALLIDA"
    assert resultado.borrador_path is None
    assert resultado.error == "La salida generada no cumple el contrato mínimo"
    assert not (tmp_path / "salida" / "borradores").exists()
    log_serializado = resultado.log_path.read_text(encoding="utf-8")
    registro = json.loads(log_serializado)
    assert registro["resultado"] == "salida_no_conforme"
    assert registro["output_hash"] is None
    assert registro["validation_errors"]
    assert all("Título verificable" not in codigo for codigo in registro["validation_errors"])
    assert salida_basura not in log_serializado


def test_validacion_de_hechos_tolera_acentos_y_case_sin_evaluar_tono(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente,lugar\n"
        "SYN-NORM,Jornada de innovación,Descripción,2026-08-11,Público,Área Técnica,Contacto@Example.Invalid,Sintética,Salón Güemes\n",
        encoding="utf-8",
    )
    contenido = salida_conforme(
        titulo="JORNADA DE INNOVACION",
        fecha="2026-08-11",
        organiza="AREA TECNICA",
        contacto="contacto@example.invalid",
        lugar="SALON GUEMES",
    )

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-NORM",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(contenido),
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert resultado.borrador_path is not None


def test_lugar_opcional_ausente_no_se_inventa_ni_se_exige(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente,lugar\n"
        "SYN-SIN-LUGAR,Jornada remota,Descripción,2026-08-12,Público,Equipo,contacto@example.invalid,Sintética,\n",
        encoding="utf-8",
    )
    contenido = salida_conforme(
        titulo="Jornada remota",
        fecha="2026-08-12",
        organiza="Equipo",
        contacto="contacto@example.invalid",
    )

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-SIN-LUGAR",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(contenido),
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"


def test_salida_truncada_sin_puntuacion_final_se_rechaza(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente,lugar\n"
        "SYN-CORTE,Jornada de cierre,Descripción,2026-08-13,Público,Equipo,contacto@example.invalid,Sintética,Aula 2\n",
        encoding="utf-8",
    )
    contenido = salida_conforme(
        titulo="Jornada de cierre",
        fecha="2026-08-13",
        organiza="Equipo",
        contacto="contacto@example.invalid",
        lugar="Aula 2",
    ).removesuffix(".")

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-CORTE",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(contenido),
    )

    assert resultado.estado == "FALLIDA"
    assert resultado.borrador_path is None
    registro = json.loads(resultado.log_path.read_text(encoding="utf-8"))
    assert registro["resultado"] == "salida_no_conforme"


def test_hechos_extensos_no_cuentan_como_limite_de_prosa(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente,lugar\n"
        "SYN-LARGO,Jornada extensa con muchos datos fuente legítimos para una actividad académica universitaria de prueba controlada,Descripción,2026-08-14,Público,Equipo organizador con denominación institucional sintética extensa,contacto@example.invalid,Sintética,Aula 3\n",
        encoding="utf-8",
    )
    contenido = salida_conforme(
        titulo="Jornada extensa con muchos datos fuente legítimos para una actividad académica universitaria de prueba controlada",
        fecha="2026-08-14",
        organiza="Equipo organizador con denominación institucional sintética extensa",
        contacto="contacto@example.invalid",
        lugar="Aula 3",
    )

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-LARGO",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(contenido),
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert resultado.borrador_path is not None


@pytest.mark.parametrize(
    "cuerpo",
    [
        "Primera oración completa. Segunda oración no permitida.",
        "Una salida con exactamente trece palabras distintas supera el máximo mecánico permitido ahora.",
    ],
)
def test_cuerpo_debe_ser_una_oracion_de_hasta_12_palabras(tmp_path, cuerpo):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente,lugar\n"
        "SYN-CUERPO,Jornada breve,Descripción,2026-08-15,Público,Equipo,contacto@example.invalid,Sintética,Aula 4\n",
        encoding="utf-8",
    )
    contenido = salida_conforme(
        titulo="Jornada breve",
        fecha="2026-08-15",
        organiza="Equipo",
        contacto="contacto@example.invalid",
        lugar="Aula 4",
    ).replace(
        "La actividad requiere revisión humana antes de cualquier publicación.", cuerpo
    )

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-CUERPO",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(contenido),
    )

    assert resultado.estado == "FALLIDA"
    assert resultado.borrador_path is None


@pytest.mark.parametrize("mutacion", ["preambulo", "duplicada", "hechos_cruzados"])
def test_parser_rechaza_texto_externo_duplicados_y_hechos_fuera_de_seccion(
    tmp_path, mutacion
):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente,lugar\n"
        "SYN-ESTRICTO,Jornada estricta,Descripción,2026-08-16,Público,Equipo,contacto@example.invalid,Sintética,Aula 5\n",
        encoding="utf-8",
    )
    contenido = salida_conforme(
        titulo="Jornada estricta",
        fecha="2026-08-16",
        organiza="Equipo",
        contacto="contacto@example.invalid",
        lugar="Aula 5",
    )
    if mutacion == "preambulo":
        contenido = "Texto externo.\n" + contenido
    elif mutacion == "duplicada":
        contenido = contenido.replace("## BAJADA", "## TÍTULO\nExtra\n\n## BAJADA")
    else:
        contenido = contenido.replace("Jornada estricta", "Título genérico", 1)
        contenido = contenido.replace(
            "La actividad requiere", "La Jornada estricta requiere", 1
        )

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-ESTRICTO",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(contenido),
    )

    assert resultado.estado == "FALLIDA"
    registro = json.loads(resultado.log_path.read_text(encoding="utf-8"))
    assert registro["validation_errors"]


def test_fuente_sin_lugar_prohibe_linea_lugar(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente,lugar\n"
        "SYN-NO-LUGAR,Jornada remota,Descripción,2026-08-17,Público,Equipo,contacto@example.invalid,Sintética,\n",
        encoding="utf-8",
    )
    contenido = salida_conforme(
        titulo="Jornada remota",
        fecha="2026-08-17",
        organiza="Equipo",
        contacto="contacto@example.invalid",
    ).replace("Organiza: Equipo", "Organiza: Equipo\nLugar: Inventado")

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-NO-LUGAR",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(contenido),
    )

    assert resultado.estado == "FALLIDA"
    registro = json.loads(resultado.log_path.read_text(encoding="utf-8"))
    assert "unexpected_place" in registro["validation_errors"]


@pytest.mark.parametrize(
    ("reemplazo", "codigo"),
    [
        (("Jornada exacta", "Prefijo Jornada exacta sufijo"), "title_mismatch"),
        (("Fecha: 2026-08-18", "Fecha: otra 2026-08-18"), "date_mismatch"),
        (("Organiza: Equipo", "Organiza: Otro Equipo"), "organizer_mismatch"),
        (("Lugar: Aula 6", "Lugar: Otra Aula 6"), "place_mismatch"),
        (("contacto@example.invalid", "otro-contacto@example.invalid"), "contact_mismatch"),
    ],
)
def test_hechos_etiquetados_requieren_igualdad_normalizada(
    tmp_path, reemplazo, codigo
):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente,lugar\n"
        "SYN-EXACTO,Jornada exacta,Descripción,2026-08-18,Público,Equipo,contacto@example.invalid,Sintética,Aula 6\n",
        encoding="utf-8",
    )
    contenido = salida_conforme(
        titulo="Jornada exacta",
        fecha="2026-08-18",
        organiza="Equipo",
        contacto="contacto@example.invalid",
        lugar="Aula 6",
    ).replace(*reemplazo, 1)

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-EXACTO",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(contenido),
    )

    assert resultado.estado == "FALLIDA"
    registro = json.loads(resultado.log_path.read_text(encoding="utf-8"))
    assert codigo in registro["validation_errors"]


def test_documento_corto_pero_estructuralmente_valido_se_acepta(tmp_path):
    csv_path = tmp_path / "actividades.csv"
    csv_path.write_text(
        "id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente,lugar\n"
        "SYN-MIN,A,D,1,P,O,c@x.invalid,F,\n",
        encoding="utf-8",
    )
    contenido = (
        "## TÍTULO\nA\n\n## DATOS DE LA ACTIVIDAD\nFecha: 1\nOrganiza: O\n\n"
        "## CONTACTO\nc@x.invalid\n\n## BAJADA\nBreve.\n\n## CUERPO\nVálido."
    )
    assert len(contenido) < 200

    resultado = procesar_fila_csv(
        csv_path=csv_path,
        id_solicitud="SYN-MIN",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(contenido),
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"


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
