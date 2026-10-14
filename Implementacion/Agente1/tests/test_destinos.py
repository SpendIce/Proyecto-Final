"""Puerto de salida: se exige la marca de borrador, se rechazan identificadores
fuera de la allowlist y no se puede escribir fuera del directorio de salida."""

import json
from datetime import date

import pytest

import agente1.procesamiento as procesamiento
from agente1.destinos import (
    BORRADOR_MARKER,
    DestinoBorradores,
    DestinoBorradoresError,
    MarkdownDestinoBorradores,
)
from agente1.fuentes import COLUMNAS_ACTIVIDADES_V2
from agente1.procesamiento import FakeGenerator, procesar_solicitud


def test_markdown_es_adapter_del_port_y_preserva_ruta_conocida(tmp_path):
    destino: DestinoBorradores = MarkdownDestinoBorradores(tmp_path / "salida")
    contenido = BORRADOR_MARKER + "Contenido controlado.\n"

    referencia = destino.guardar("SYN-001", contenido)

    assert referencia.tipo == "markdown"
    assert referencia.path == tmp_path / "salida" / "borradores" / "SYN-001.md"
    assert referencia.referencia == str(referencia.path)
    assert referencia.path.read_text(encoding="utf-8") == contenido


def test_markdown_rechaza_id_inseguro_y_contenido_sin_marker(tmp_path):
    destino = MarkdownDestinoBorradores(tmp_path / "salida")

    for id_solicitud, contenido in [
        ("../escape", BORRADOR_MARKER + "Texto."),
        ("SYN-001", "Texto sin control."),
    ]:
        with pytest.raises(DestinoBorradoresError) as error:
            destino.guardar(id_solicitud, contenido)

        assert error.value.code == "destination_contract_invalid"
    assert not (tmp_path / "salida").exists()


def test_core_usa_destino_inyectado_despues_del_gate(tmp_path, monkeypatch):
    fila = dict(
        zip(
            COLUMNAS_ACTIVIDADES_V2,
            [
                "SYN-DESTINO",
                "Actividad destino",
                "Caso controlado",
                "2026-08-05",
                "",
                "",
                "",
                "",
                "",
                "Comunidad ficticia",
                "Equipo de prueba",
                "pruebas@example.invalid",
                "Dataset sintético",
                "",
                "",
            ],
            strict=True,
        )
    )

    class FuenteFalsa:
        def obtener(self, id_solicitud: str):
            return fila

    class DestinoCaptura:
        def __init__(self) -> None:
            self.llamadas: list[tuple[str, str, str | None]] = []

        def guardar(self, id_solicitud: str, contenido: str, *, nombre=None):
            from agente1.destinos import ReferenciaBorrador

            self.llamadas.append((id_solicitud, contenido, nombre))
            return ReferenciaBorrador(tipo="fake", referencia="ref-opaca")

    contenido_generado = (
        "## TÍTULO\nActividad destino\n\n"
        "## DATOS DE LA ACTIVIDAD\nFecha: 2026-08-05\n"
        "Organiza: Equipo de prueba\n\n"
        "## CONTACTO\npruebas@example.invalid\n\n"
        "## BAJADA\nCaso sintético controlado.\n\n"
        "## CUERPO\nLa actividad requiere validación humana."
    )
    destino = DestinoCaptura()
    # El nombre del Doc depende de la fecha de generación: se fija para que la
    # regresión sea determinista.
    monkeypatch.setattr(
        procesamiento, "_fecha_generacion", lambda: date(2026, 10, 14)
    )

    resultado = procesar_solicitud(
        fuente=FuenteFalsa(),
        id_solicitud="SYN-DESTINO",
        directorio_salida=tmp_path / "salida",
        generator=FakeGenerator(contenido_generado),
        destino=destino,
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert resultado.borrador_path is None
    assert resultado.referencia_borrador is not None
    assert resultado.referencia_borrador.referencia == "ref-opaca"
    # Lo que recibe el destino es el mail renderizado (no la ficha): la ficha
    # validada es la entrada intermedia del renderer determinista.
    mail_esperado = (
        "Asunto: Actividad destino\n\n"
        "La Facultad de Ingeniería del Ejército invita a Comunidad ficticia "
        "a participar de la siguiente actividad.\n\n"
        "Caso sintético controlado.\n\n"
        "La actividad requiere validación humana.\n\n"
        "📅 miércoles 5 de agosto de 2026\n"
        "Organiza: Equipo de prueba\n\n"
        "Consultas: pruebas@example.invalid\n\n"
        "Departamento de Cursos Complementarios\n"
        "Secretaría de Extensión Universitaria\n\n"
        "--\n"
        "Facultad de Ingeniería del Ejército\n"
        '"Grl Div Manuel N Savio"\n'
        "UNDEF\n"
        "Tel: (011) 4779-3300\n"
        "Av. Cabildo 15 – CABA\n"
        "www.fie.undef.edu.ar"
    )
    # El tercer elemento es el nombre del Doc que el pipeline declara para el
    # destino remoto: la convención «BORRADOR — Fie informa D-M <título>»
    # (#102, #107), con el prefijo de marca para reconocerlo desde Drive.
    assert destino.llamadas == [
        (
            "SYN-DESTINO",
            BORRADOR_MARKER + mail_esperado + "\n",
            "BORRADOR — Fie informa 14-10 Actividad destino",
        )
    ]
    registro_serializado = resultado.log_path.read_text(encoding="utf-8")
    registro = json.loads(registro_serializado)
    assert registro["destination_type"] == "fake"
    assert registro["borrador_ref_hash"]
    assert "ref-opaca" not in registro_serializado
