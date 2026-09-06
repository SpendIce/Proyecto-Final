"""Puerto de salida: se exige la marca de borrador, se rechazan identificadores
fuera de la allowlist y no se puede escribir fuera del directorio de salida."""

import json

import pytest

from agente1.destinos import (
    BORRADOR_MARKER,
    DestinoBorradores,
    DestinoBorradoresError,
    MarkdownDestinoBorradores,
)
from agente1.fuentes import COLUMNAS_GACETILLA
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


def test_core_usa_destino_inyectado_despues_del_gate(tmp_path):
    fila = dict(
        zip(
            COLUMNAS_GACETILLA,
            [
                "SYN-DESTINO",
                "Actividad destino",
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

    class FuenteFalsa:
        def obtener(self, id_solicitud: str):
            return fila

    class DestinoCaptura:
        def __init__(self) -> None:
            self.llamadas: list[tuple[str, str]] = []

        def guardar(self, id_solicitud: str, contenido: str):
            from agente1.destinos import ReferenciaBorrador

            self.llamadas.append((id_solicitud, contenido))
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
    assert destino.llamadas == [
        ("SYN-DESTINO", BORRADOR_MARKER + contenido_generado + "\n")
    ]
    registro_serializado = resultado.log_path.read_text(encoding="utf-8")
    registro = json.loads(registro_serializado)
    assert registro["destination_type"] == "fake"
    assert registro["borrador_ref_hash"]
    assert "ref-opaca" not in registro_serializado
