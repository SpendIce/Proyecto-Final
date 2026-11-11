"""Despacho estructurado de gacetillas por el seam del núcleo (#149).

Juani (11/11/2026): los siete tipos de gacetilla se habilitan en la web
«por los controles del núcleo». Este módulo prueba que los siete pasan por
`interpretar_solicitud` con `DespachoGacetilla` —la misma clasificación
determinística, el mismo gate de rol y la misma auditoría HU-013 que un
mensaje de texto— y que ninguno saltea el pipeline del tipo:

- `difusion_de_actividad` sigue por `procesar_solicitud` con la ficha de
  la fuente, como siempre;
- los seis tipos sin ficha van por `procesar_gacetilla_estructurada`, que
  corre el mismo circuito (obligatorios, seam del modo, gate, destino,
  línea de ejecución);
- el texto que acompaña al despacho es derivado y sigue clasificándose:
  si no sale `generar_gacetilla`, el pedido se rechaza por el camino
  normal, nunca por un atajo;
- las indicaciones libres viajan en el texto como dato no privilegiado
  (ADR 0001): entran al hash del registro, nunca al prompt ni al log.

Cubre además los rechazos del propio despacho: tipo fuera de la lista
cerrada, ficha sin actividad declarada y campos obligatorios faltantes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agente1 import FakeGenerator
from agente1.destinos import ReferenciaBorrador
from agente1.fuentes import CsvFuenteSolicitudes
from agente1.interpretacion import (
    ROLES_HABILITADOS,
    DespachoGacetilla,
    IdentidadSolicitante,
    interpretar_solicitud,
)

ROOT = Path(__file__).parents[1]
DATASET = ROOT / "data" / "actividades_sinteticas.csv"
ROL_HABILITADO = next(iter(ROLES_HABILITADOS))
ROL_NO_HABILITADO = "lector_seu"

# Borrador conforme al contrato mínimo de difusión para SYN-001 (mismos
# hechos que la fila del dataset sintético; ver test_interpretacion.py).
BORRADOR_CONFORME = (
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

SALUDO = (
    "En el Día del Ingeniero saludamos a toda la comunidad de la facultad "
    "y reconocemos el trabajo de quienes ejercen la profesión con "
    "compromiso y vocación de servicio."
)

# Campos conformes al contrato de entrada de cada tipo sin ficha: son los
# casos del corpus sintético de `test_gacetillas_formas.py`.
CAMPOS_POR_TIPO: dict[str, dict[str, str]] = {
    "cronica_de_evento": {
        "titulo": "Visita de la comisión de extensión al laboratorio",
        "cuerpo": (
            "La comisión recorrió el laboratorio junto a docentes y "
            "estudiantes, y se acordaron las próximas actividades."
        ),
    },
    "aviso_de_otra_area": {
        "titulo": "Estacionamiento de motos",
        "publico": "educativa",
        "hecho": "el estacionamiento para motos no estará habilitado",
        "fecha": "2026-11-02",
        "condicion": "hasta nuevo aviso",
        "area_emisora": "Facultad de Ingeniería del Ejército",
    },
    "convocatoria_interna": {
        "titulo": "Convocatoria interna de tutores",
        "destinatarios": "docentes de la casa",
        "convocatoria": "la convocatoria interna de tutores del semestre",
        "requisitos": "dos años de antigüedad y disponibilidad horaria",
        "fecha_limite": "2026-11-15",
        "area_emisora": "Secretaría Académica",
        "contacto": "doe@example.invalid",
    },
    "saludo_o_efemeride": {"titulo": "Día del Ingeniero"},
    "fallecimiento": {
        "titulo": "Informar fallecimiento",
        "nombre": "María Ejemplo",
        "rol": "docente de la casa",
        "dia": "viernes 23 de octubre",
        "hora": "11:00",
        "lugar": "Capilla del Instituto",
    },
    "newsletter": {
        "titulo": "Boletín del Observatorio",
        "enlace_adjunto": "https://example.invalid/boletin",
        "area_emisora": "Secretaría de Extensión Universitaria",
    },
}

TIPOS_SIN_ACTIVIDAD = tuple(CAMPOS_POR_TIPO)


class DestinoRegistrador:
    """`DestinoBorradores` mínimo: guarda lo que recibe para verificarlo."""

    def __init__(self) -> None:
        self.llamadas: list[dict] = []

    def guardar(
        self, id_solicitud: str, contenido: str, *, nombre=None
    ) -> ReferenciaBorrador:
        self.llamadas.append(
            {"id_solicitud": id_solicitud, "contenido": contenido}
        )
        return ReferenciaBorrador(
            tipo="docs_fake", referencia=f"doc-{id_solicitud}"
        )


class GeneratorQueNoDebeInvocarse:
    """Los tipos `extrae_y_confirma` no tocan el modelo."""

    modelo = "fake-no-invocar"

    def generate(self, prompt: str, num_predict: int = 0) -> str:
        raise AssertionError(
            "un tipo que extrae y confirma no debe llamar al modelo"
        )


def _identidad(rol: str = ROL_HABILITADO) -> IdentidadSolicitante:
    return IdentidadSolicitante(
        identificador="persona-seu-01", rol=rol
    )


def _despachar(
    tmp_path: Path,
    *,
    tipo: str,
    texto: str | None = None,
    actividad: str | None = None,
    campos: dict[str, str] | None = None,
    solicitante: IdentidadSolicitante | None = None,
    generator=None,
    destino=None,
):
    return interpretar_solicitud(
        texto=texto if texto is not None else f"gacetilla {tipo}",
        solicitante=solicitante or _identidad(),
        fuente=CsvFuenteSolicitudes(DATASET),
        directorio_salida=tmp_path,
        generator=generator or FakeGenerator(BORRADOR_CONFORME),
        destino=destino,
        despacho_gacetilla=DespachoGacetilla(
            tipo=tipo,
            id_solicitud="web-test-1",
            actividad=actividad,
            campos=campos,
        ),
    )


def _ultima_interpretacion(tmp_path: Path) -> dict:
    return json.loads(
        (tmp_path / "logs" / "interpretaciones-hu013.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[-1]
    )


# --- Los siete tipos por el mismo seam --------------------------------------


def test_difusion_por_el_seam_con_actividad_declarada(tmp_path: Path):
    """El tipo con ficha sigue por `procesar_solicitud`: la actividad la
    declaró el canal, la ficha sale del catálogo institucional."""
    destino = DestinoRegistrador()
    resultado = _despachar(
        tmp_path,
        tipo="difusion_de_actividad",
        actividad="SYN-001",
        texto="gacetilla actividad SYN-001",
        destino=destino,
    )
    assert resultado.estado == "PENDIENTE_VALIDACION"
    auditoria = _ultima_interpretacion(tmp_path)
    assert auditoria["resultado"] == "borrador_generado"
    assert auditoria["id_actividad"] == "SYN-001"
    assert len(destino.llamadas) == 1


@pytest.mark.parametrize("tipo", TIPOS_SIN_ACTIVIDAD)
def test_tipos_sin_actividad_por_el_seam(tipo: str, tmp_path: Path):
    """Los seis tipos sin ficha pasan por `procesar_gacetilla_estructurada`
    con los campos del pedido, sin tocar el modelo en `extrae_y_confirma`
    y con el generador sólo en `saludo_o_efemeride`."""
    generator = (
        FakeGenerator(SALUDO)
        if tipo == "saludo_o_efemeride"
        else GeneratorQueNoDebeInvocarse()
    )
    destino = DestinoRegistrador()
    resultado = _despachar(
        tmp_path,
        tipo=tipo,
        campos=CAMPOS_POR_TIPO[tipo],
        generator=generator,
        destino=destino,
    )
    assert resultado.estado == "PENDIENTE_VALIDACION", resultado.error
    assert _ultima_interpretacion(tmp_path)["resultado"] == (
        "borrador_generado"
    )
    assert len(destino.llamadas) == 1
    assert destino.llamadas[0]["id_solicitud"] == "web-test-1"


def test_auditoria_hu013_y_ejecucion_en_tipo_sin_actividad(
    tmp_path: Path,
):
    """El despacho estructurado deja las dos líneas de siempre: la de
    interpretación HU-013 y la de ejecución del pipeline, con modo
    `estructurada` y sin prosa del pedido."""
    marcador = "INDICACION-LIBRE-" + "x" * 8
    resultado = _despachar(
        tmp_path,
        tipo="cronica_de_evento",
        texto=f"gacetilla cronica_de_evento. {marcador}",
        campos=CAMPOS_POR_TIPO["cronica_de_evento"],
        generator=GeneratorQueNoDebeInvocarse(),
    )
    assert resultado.estado == "PENDIENTE_VALIDACION"

    lineas = [
        json.loads(linea)
        for linea in (
            tmp_path / "logs" / "interpretaciones-hu013.jsonl"
        )
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(lineas) == 1
    assert lineas[0]["correlation_id"] == resultado.correlation_id
    assert marcador not in json.dumps(lineas[0])

    ejecuciones = [
        json.loads(linea)
        for linea in (tmp_path / "logs" / "ejecuciones.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(ejecuciones) == 1
    linea = ejecuciones[0]
    assert linea["modo_entrada"] == "estructurada"
    assert linea["tipo_gacetilla"] == "cronica_de_evento"
    assert linea["estado"] == "PENDIENTE_VALIDACION"
    assert linea["resultado"] == "borrador_generado"
    assert marcador not in json.dumps(linea)


# --- Gates que no se saltan --------------------------------------------------


def test_despacho_respeta_gate_de_rol(tmp_path: Path):
    """Un rol no habilitado rechaza también el despacho estructurado, con
    el mismo código que un mensaje de texto."""
    destino = DestinoRegistrador()
    resultado = _despachar(
        tmp_path,
        tipo="cronica_de_evento",
        campos=CAMPOS_POR_TIPO["cronica_de_evento"],
        solicitante=_identidad(rol=ROL_NO_HABILITADO),
        generator=GeneratorQueNoDebeInvocarse(),
        destino=destino,
    )
    assert resultado.estado == "RECHAZADA"
    assert _ultima_interpretacion(tmp_path)["resultado"] == (
        "rol_no_habilitado"
    )
    assert destino.llamadas == []


def test_despacho_exige_clasificacion_gacetilla(tmp_path: Path):
    """Si el texto derivado no clasifica como `generar_gacetilla`, el
    despacho se rechaza por el camino normal del catálogo — el tipo
    declarado no rescata un texto fuera de alcance."""
    resultado = _despachar(
        tmp_path,
        tipo="cronica_de_evento",
        texto="quiero renovar el pasaporte del club",
        campos=CAMPOS_POR_TIPO["cronica_de_evento"],
        generator=GeneratorQueNoDebeInvocarse(),
    )
    assert resultado.estado in {"RECHAZADA", "PENDIENTE_CONFIRMACION"}
    assert _ultima_interpretacion(tmp_path)["resultado"] != (
        "borrador_generado"
    )


def test_tipo_fuera_de_la_lista_cerrada(tmp_path: Path):
    resultado = _despachar(
        tmp_path,
        tipo="comunicado_rectificativo",
        campos={"titulo": "x"},
        generator=GeneratorQueNoDebeInvocarse(),
    )
    assert resultado.estado == "INVALIDA"
    assert _ultima_interpretacion(tmp_path)["resultado"] == (
        "solicitud_invalida"
    )


def test_tipo_con_ficha_sin_actividad_declarada(tmp_path: Path):
    resultado = _despachar(
        tmp_path,
        tipo="difusion_de_actividad",
        actividad=None,
    )
    assert resultado.estado == "INCOMPLETA"
    assert _ultima_interpretacion(tmp_path)["resultado"] == (
        "identificador_no_encontrado"
    )


def test_campos_obligatorios_faltantes(tmp_path: Path):
    """El control de obligatorios corre antes del modelo: sin `cuerpo`
    la crónica termina `INCOMPLETA`, como un pedido incompleto del Form."""
    resultado = _despachar(
        tmp_path,
        tipo="cronica_de_evento",
        campos={"titulo": "Sin cuerpo"},
        generator=GeneratorQueNoDebeInvocarse(),
    )
    assert resultado.estado == "INCOMPLETA"
    assert _ultima_interpretacion(tmp_path)["resultado"] == (
        "datos_incompletos"
    )


def test_tipo_con_ficha_no_despacha_por_via_estructurada(tmp_path: Path):
    """`difusion_de_actividad` nunca va por el camino estructurado aunque
    traiga campos: su pipeline es el de la ficha de la fuente."""
    resultado = _despachar(
        tmp_path,
        tipo="difusion_de_actividad",
        actividad="SYN-001",
        campos={"titulo": "ignorado por la ficha"},
    )
    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert _ultima_interpretacion(tmp_path)["id_actividad"] == "SYN-001"
