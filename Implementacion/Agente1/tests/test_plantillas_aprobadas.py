"""Mecanismo de plantillas aprobadas por tipo para el modo producción (#142).

Cubre el contrato completo de `plantillas_aprobadas.py`: la carga del
archivo declarado por `AGENTE1_PLANTILLAS_APROBADAS_PATH` con sus fallas
cerradas, la sustitución `{{variable}}` que no deja llaves sueltas, el
listado de variables que un texto declara, la forma que toda plantilla
exige por tipo, el id de versión que ata la aprobación al hash del texto,
la consulta al registro de decisiones y la fuente única del modo.

Todas las plantillas de estas pruebas son sintéticas y se declaran acá:
no son redacciones institucionales — las de la SEU siguen pendientes y el
circuito las carga desde fuera del repo —.
"""

import json
from pathlib import Path

import pytest

from agente1.decisiones_form import (
    DECISION_APRUEBO_CONTENIDO,
    RESULTADO_REGISTRADA,
    TIPO_PLANTILLA,
    RegistroDecisiones,
    ResultadoDecision,
)
from agente1.plantillas_aprobadas import (
    LINEA_PROVISIONAL,
    PLANTILLAS_APROBADAS_PATH_ENV,
    PlantillaAprobadaError,
    PlantillaCorreo,
    cargar_plantillas_aprobadas,
    id_version_plantilla,
    modo_envio_efectivo,
    plantilla_version_registrada,
    renderizar_plantilla,
    validar_forma_plantilla,
    variables_plantilla,
)
from agente1.workspace_config import ConfiguracionWorkspaceError

MARCADOR_BORRADOR = "BORRADOR — NO ENVIAR"

# Plantilla sintética declarada para las pruebas: estructura igual a la
# que el archivo de producción espera, redacción inventada sólo para el
# test, no la aprueba nadie.
PLANTILLA_INSCRIPCION_SINTETICA = {
    "asunto": "Confirmación de {{actividad}}",
    "cuerpo": (
        "Hola {{nombre_destinatario}},\n\n"
        "{{frase_evento}}: {{actividad}}.\n"
        "Fecha: {{fecha}}\n"
        "Lugar: {{lugar}}\n"
        "Organiza: {{organiza}}\n\n"
        "Contacto: {{contacto}}\n"
    ),
}


def _archivo(tmp_path: Path, datos: object) -> Path:
    path = tmp_path / "plantillas.json"
    path.write_text(json.dumps(datos), encoding="utf-8")
    return path


# --- Carga del archivo --------------------------------------------------------


def test_carga_un_archivo_bien_formado(tmp_path: Path):
    path = _archivo(
        tmp_path,
        {
            "inscripcion": PLANTILLA_INSCRIPCION_SINTETICA,
            "instrucciones_pago": {"cuerpo": "Cuerpo {{contacto}}"},
        },
    )

    plantillas = cargar_plantillas_aprobadas(
        {PLANTILLAS_APROBADAS_PATH_ENV: str(path)}
    )

    assert set(plantillas) == {"inscripcion", "instrucciones_pago"}
    assert plantillas["inscripcion"].asunto == "Confirmación de {{actividad}}"
    assert plantillas["instrucciones_pago"].asunto is None


def test_sin_la_variable_de_entorno_falla_cerrado(tmp_path: Path):
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        cargar_plantillas_aprobadas({})
    assert error.value.code == "approved_templates_file_missing"

    with pytest.raises(ConfiguracionWorkspaceError) as error:
        cargar_plantillas_aprobadas({PLANTILLAS_APROBADAS_PATH_ENV: "   "})
    assert error.value.code == "approved_templates_file_missing"


def test_un_path_ilegible_es_missing(tmp_path: Path):
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        cargar_plantillas_aprobadas(
            {PLANTILLAS_APROBADAS_PATH_ENV: str(tmp_path / "no-existe.json")}
        )
    assert error.value.code == "approved_templates_file_missing"


@pytest.mark.parametrize(
    "datos",
    [
        "no es json",
        [1, 2],
        {},
        {"tipo mal": {"cuerpo": "x"}},
        {"inscripcion": "texto"},
        {"inscripcion": {"cuerpo": "x", "extra": 1}},
        {"inscripcion": {"asunto": "a"}},
        {"inscripcion": {"cuerpo": "   "}},
        {"inscripcion": {"cuerpo": "x", "asunto": ""}},
    ],
)
def test_la_forma_invalida_es_invalid(tmp_path: Path, datos):
    path = tmp_path / "plantillas.json"
    path.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(ConfiguracionWorkspaceError) as error:
        cargar_plantillas_aprobadas(
            {PLANTILLAS_APROBADAS_PATH_ENV: str(path)}
        )
    assert error.value.code == "approved_templates_file_invalid"


@pytest.mark.parametrize(
    "marca",
    ["BORRADOR — NO ENVIAR", "# BORRADOR — NO PUBLICAR", "BORRADOR — NO EMITIR"],
)
def test_una_plantilla_marcada_no_es_texto_aprobado(tmp_path: Path, marca):
    path = _archivo(
        tmp_path, {"inscripcion": {"cuerpo": f"{marca}\n\nTexto."}}
    )

    with pytest.raises(ConfiguracionWorkspaceError) as error:
        cargar_plantillas_aprobadas(
            {PLANTILLAS_APROBADAS_PATH_ENV: str(path)}
        )
    assert error.value.code == "approved_templates_file_invalid"


def test_la_marca_en_el_asunto_tambien_se_rechaza(tmp_path: Path):
    path = _archivo(
        tmp_path,
        {
            "inscripcion": {
                "asunto": "BORRADOR — NO ENVIAR — asunto",
                "cuerpo": "Texto limpio.",
            }
        },
    )

    with pytest.raises(ConfiguracionWorkspaceError) as error:
        cargar_plantillas_aprobadas(
            {PLANTILLAS_APROBADAS_PATH_ENV: str(path)}
        )
    assert error.value.code == "approved_templates_file_invalid"


# --- Sustitución de variables ---------------------------------------------------


def test_variables_plantilla_lista_los_nombres_declarados():
    assert variables_plantilla(
        "Hola {{ nombre_destinatario }}, tu actividad es {{actividad}}. "
        "Repetir {{actividad}} no cuenta dos veces."
    ) == frozenset({"nombre_destinatario", "actividad"})
    assert variables_plantilla("Sin variables.") == frozenset()


def test_renderizar_plantilla_sustituye_todas_las_llaves():
    cuerpo = renderizar_plantilla(
        PLANTILLA_INSCRIPCION_SINTETICA["cuerpo"],
        {
            "nombre_destinatario": "Ana Pérez",
            "frase_evento": "tu inscripción a",
            "actividad": "Taller sintético",
            "fecha": "mañana",
            "lugar": "Aula 1",
            "organiza": "SEU",
            "contacto": "extension@example.test",
        },
    )

    assert "{{" not in cuerpo
    assert "Ana Pérez" in cuerpo
    assert "tu inscripción a: Taller sintético." in cuerpo


def test_una_variable_sin_valor_frena_la_composicion():
    with pytest.raises(PlantillaAprobadaError) as error:
        renderizar_plantilla("Hola {{nombre_destinatario}}.", {})
    assert error.value.code == "template_variable_without_value"


# --- Forma por tipo -------------------------------------------------------------


def test_validar_forma_acepta_la_forma_declarada():
    plantilla = PlantillaCorreo(
        asunto="Aviso de {{actividad}}",
        cuerpo="Hola {{nombre_destinatario}}, {{actividad}}.",
    )

    assert (
        validar_forma_plantilla(
            plantilla,
            asunto_requerido=True,
            variables_permitidas=frozenset(
                {"actividad", "nombre_destinatario"}
            ),
        )
        is None
    )


def test_validar_forma_exige_el_asunto_cuando_el_tipo_lo_pide():
    plantilla = PlantillaCorreo(asunto=None, cuerpo="Cuerpo.")

    assert (
        validar_forma_plantilla(
            plantilla,
            asunto_requerido=True,
            variables_permitidas=frozenset(),
        )
        == "approved_template_invalid"
    )
    assert (
        validar_forma_plantilla(
            plantilla,
            asunto_requerido=False,
            variables_permitidas=frozenset(),
        )
        is None
    )


def test_validar_forma_rechaza_una_variable_desconocida():
    plantilla = PlantillaCorreo(
        asunto="Aviso",
        cuerpo="Tu saldo es {{saldo_misterioso}}.",
    )

    assert (
        validar_forma_plantilla(
            plantilla,
            asunto_requerido=True,
            variables_permitidas=frozenset({"nombre_destinatario"}),
        )
        == "approved_template_invalid"
    )


# --- Versión y aprobación registrada -------------------------------------------


def test_el_id_de_version_deriva_del_texto_integro():
    plantilla = PlantillaCorreo(asunto="A", cuerpo="Cuerpo uno.")
    otra = PlantillaCorreo(asunto="A", cuerpo="Cuerpo dos.")

    id_uno = id_version_plantilla("inscripcion", plantilla)
    assert id_uno.startswith("tpl-inscripcion-")
    assert id_uno != id_version_plantilla("inscripcion", otra)
    # El asunto también es parte del texto aprobado.
    assert id_uno != id_version_plantilla(
        "inscripcion", PlantillaCorreo(asunto="B", cuerpo="Cuerpo uno.")
    )
    # El tipo es parte del objeto: el mismo texto en otro tipo es otra versión.
    assert id_uno != id_version_plantilla("participacion", plantilla)


def _registrar_aprobacion(
    registro: RegistroDecisiones,
    *,
    tipo: str,
    plantilla: PlantillaCorreo,
    rol: str = "APROBADOR_CONTENIDO",
    correlativo: int = 1,
) -> None:
    """La `apruebo_contenido` registrada sobre la versión de la plantilla."""

    registro.registrar(
        ResultadoDecision(
            id_respuesta=f"{correlativo:064x}",
            correo_hash="a" * 64,
            rol=rol,
            rol_origen="padron",
            tipo=TIPO_PLANTILLA,
            objeto_id=id_version_plantilla(tipo, plantilla),
            decision=DECISION_APRUEBO_CONTENIDO,
            resultado=RESULTADO_REGISTRADA,
            rechazo_codigo=None,
            marca_temporal_form="2026-10-11 09:00:00",
            timestamp="2026-10-11T09:00:00+00:00",
        )
    )


def test_una_version_con_decision_registrada_esta_aprobada(tmp_path: Path):
    registro = RegistroDecisiones(tmp_path / "estado-decisiones")
    plantilla = PlantillaCorreo(asunto="Aviso", cuerpo="Cuerpo.")

    assert not plantilla_version_registrada(
        registro, tipo="inscripcion", plantilla=plantilla
    )
    _registrar_aprobacion(registro, tipo="inscripcion", plantilla=plantilla)
    assert plantilla_version_registrada(
        registro, tipo="inscripcion", plantilla=plantilla
    )


def test_un_texto_editado_no_hereda_la_aprobacion(tmp_path: Path):
    registro = RegistroDecisiones(tmp_path / "estado-decisiones")
    plantilla = PlantillaCorreo(asunto="Aviso", cuerpo="Cuerpo original.")
    _registrar_aprobacion(registro, tipo="inscripcion", plantilla=plantilla)

    editada = PlantillaCorreo(asunto="Aviso", cuerpo="Cuerpo retocado.")
    assert not plantilla_version_registrada(
        registro, tipo="inscripcion", plantilla=editada
    )


def test_otro_rol_no_habilita_la_version(tmp_path: Path):
    registro = RegistroDecisiones(tmp_path / "estado-decisiones")
    plantilla = PlantillaCorreo(asunto="Aviso", cuerpo="Cuerpo.")
    _registrar_aprobacion(
        registro, tipo="inscripcion", plantilla=plantilla, rol="APROBADOR_PAGOS"
    )

    assert not plantilla_version_registrada(
        registro, tipo="inscripcion", plantilla=plantilla
    )


def test_sin_registro_no_hay_aprobacion_verificable():
    plantilla = PlantillaCorreo(asunto="Aviso", cuerpo="Cuerpo.")

    assert not plantilla_version_registrada(
        None, tipo="inscripcion", plantilla=plantilla
    )


# --- Fuente única del modo --------------------------------------------------------


class _DestinoConModo:
    def __init__(self, modo: str) -> None:
        self.modo = modo


def test_el_modo_lo_declara_el_destino():
    destino = _DestinoConModo("produccion")

    assert modo_envio_efectivo(destino, None) == "produccion"
    assert modo_envio_efectivo(destino, "produccion") == "produccion"


def test_un_parametro_que_no_coincide_falla_cerrado():
    destino = _DestinoConModo("prueba")

    assert modo_envio_efectivo(destino, "produccion") is None


def test_sin_destino_el_parametro_es_la_fuente():
    assert modo_envio_efectivo(None, "produccion") == "produccion"
    assert modo_envio_efectivo(None, None) == "prueba"


def test_un_destino_sin_modo_declarado_es_prueba():
    class _SinModo:
        pass

    assert modo_envio_efectivo(_SinModo(), None) == "prueba"


def test_plantilla_correo_es_inmutable():
    plantilla = PlantillaCorreo(asunto="A", cuerpo="C")

    with pytest.raises(AttributeError):
        plantilla.cuerpo = "otro"  # type: ignore[misc]


def test_la_linea_provisional_sigue_declarada():
    # La constante sigue existiendo: es el texto que el circuito de prueba
    # escribe dentro de los documentos provisionales.
    assert "plantilla provisional" in LINEA_PROVISIONAL
