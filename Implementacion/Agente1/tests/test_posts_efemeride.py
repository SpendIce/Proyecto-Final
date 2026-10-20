"""Post de efeméride HU-011 desde Historia Viva (#85).

El post se genera desde el puerto `HistoriaViva` —con el fake y también a
través del `ClienteHistoriaViva` con transporte fake—, compone el material
con `componer_material_efemeride`, pasa los mismos gates del carril
estructurado de `posts.py` y deja un borrador `PENDIENTE_VALIDACION` con las
citas de cada fragmento y la procedencia declarada. Sin material no hay post.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from agente1 import FakeGenerator, procesar_post_efemeride
from agente1.decisiones_form import ID_RE as DECISION_ID_RE
from agente1.destinos import DestinoBorradoresError
from agente1.historia_viva import (
    Fragmento,
    HistoriaVivaFake,
    RangoHistorico,
)
from agente1.historia_viva_cliente import (
    ClienteHistoriaViva,
    TransporteHistoriaVivaFake,
)
from agente1.politica_redes import POLITICAS_DEFAULT, PoliticaPost
from agente1.posts import CONTRATO_CREATIVO_V2
from agente1.posts_efemeride import PROCEDENCIA_SINTETICA


def rango(desde: date, hasta: date, precision: str = "dia") -> RangoHistorico:
    return RangoHistorico(desde=desde, hasta=hasta, precision=precision)


def fragmento(
    *,
    fragmento_id: str = "frg-001",
    pieza_id: str = "pie-001",
    texto: str = "El acta consigna la apertura de los primeros cursos.",
    rango_: RangoHistorico | None = None,
    tipo: str = "acta",
    ubicacion: str | None = "página 3",
) -> Fragmento:
    return Fragmento(
        fragmento_id=fragmento_id,
        pieza_id=pieza_id,
        texto=texto,
        rango=rango_ or rango(date(1926, 8, 7), date(1926, 8, 7)),
        tipo=tipo,
        resumen_pieza="Acta sintética de prueba",
        url_original="https://ejemplo.invalid/piezas/1",
        validada_el=date(2026, 1, 15),
        ubicacion=ubicacion,
    )


CTA_POR_CANAL = {
    "instagram": "Encontrá el enlace en nuestro perfil.",
    "linkedin": "Más información en el enlace de esta publicación.",
}


def salida_efemeride(canal: str = "instagram", **cambios: object) -> str:
    salida: dict[str, object] = {
        "gancho": "Un día como hoy dejó huella en nuestra historia.",
        "prosa": "Cada efeméride es una invitación a mirar el camino recorrido "
        "por la Facultad y a compartirlo con la comunidad.",
        "cta": CTA_POR_CANAL[canal],
        "hashtags": ["#FIE", "#Efemerides"],
    }
    salida.update(cambios)
    return json.dumps(salida, ensure_ascii=False)


def ultimo_registro(log_path: Path) -> dict:
    return json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])


def cliente_con_fragmentos(*fragmentos: Fragmento) -> HistoriaVivaFake:
    return HistoriaVivaFake(fragmentos=fragmentos)


# --- Generación desde el puerto -------------------------------------------------


@pytest.mark.parametrize("canal", ["instagram", "linkedin"])
def test_el_post_se_genera_desde_el_puerto_con_citas_y_procedencia(
    tmp_path: Path, canal: str
):
    resultado = procesar_post_efemeride(
        historia_viva=cliente_con_fragmentos(fragmento()),
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal=canal,
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride(canal)),
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert resultado.borrador_path is not None
    borrador = resultado.borrador_path.read_text(encoding="utf-8")
    assert borrador.startswith("# BORRADOR — NO PUBLICAR\n\n")
    assert "_Procedencia: insumo de A2 (Historia Viva" in borrador
    # El texto del fragmento va literal y cada fragmento lleva su cita con
    # identidad de pieza y de fragmento más la expresión temporal exacta.
    assert "El acta consigna la apertura de los primeros cursos." in borrador
    assert (
        "Fuente: pie-001 / frg-001, página 3 (7 de agosto de 1926)" in borrador
    )
    assert "Efeméride: 7 de agosto de 1926" in borrador
    assert "Un día como hoy dejó huella en nuestra historia." in borrador
    assert "#FIE #Efemerides" in borrador
    registro = ultimo_registro(resultado.log_path)
    assert registro["estado"] == "PENDIENTE_VALIDACION"
    assert registro["resultado"] == "borrador_generado"
    assert registro["HU"] == "HU-011"
    assert registro["canal"] == canal
    assert registro["contract_version"] == "post_efemeride_input_v1"
    assert registro["output_contract_version"] == "post_creative_efemeride_v1"
    assert registro["renderer_version"] == "post_efemeride_renderer_v1"
    assert registro["prompt_version"] == f"post_{canal}_efemeride_v1"
    assert registro["data_origin"] == "insumo_a2"
    assert registro["hv_contract_status"] == "BORRADOR_HISTORIA_VIVA"
    assert registro["hv_fragmentos"] == 1
    assert registro["hv_piezas_fuente"] == ["pie-001"]
    assert registro["hv_consulta"]["desde"] == "1926-08-07"
    assert registro["hv_consulta"]["precision"] == "dia"


def test_el_pipeline_no_depende_del_adapter_sino_del_puerto(tmp_path: Path):
    """El mismo flujo corre sobre el cliente validado, con transporte fake.

    Es la prueba de inyección: `ClienteHistoriaViva` valida el cuerpo crudo
    contra el contrato candidato y produce los objetos del dominio; el
    pipeline no sabe ni le interesa si detrás hay red.
    """

    fragmento_crudo = {
        "fragmento_id": "frg_777",
        "pieza_id": "pza_777",
        "texto": "La gacetilla sintética anuncia la primera cursada.",
        "fecha_inicio": "1926-08-07",
        "fecha_fin": "1926-08-07",
        "precision_fecha": "dia",
        "tipo": "nota",
        "resumen_pieza": "Pieza sintética",
        "url_original": "https://ejemplo.invalid/validar.html?pieza=777",
        "validada_el": "2026-01-15T10:00:00Z",
        "pagina": None,
        "seccion": None,
    }
    transporte = TransporteHistoriaVivaFake(
        respuestas={
            "get_fragmentos": {
                "total": 1,
                "limite": 10,
                "fragmentos": [fragmento_crudo],
            }
        }
    )
    cliente = ClienteHistoriaViva(transporte)

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    borrador = resultado.borrador_path.read_text(encoding="utf-8")
    assert "Fuente: pza_777 / frg_777 (7 de agosto de 1926)" in borrador


def test_un_solo_fragmento_por_post_en_orden_de_historia_viva(tmp_path: Path):
    """El post cita una sola referencia: la primera que entra, en orden.

    Las dos caben, así que se elige la primera; la segunda queda como
    referencia no utilizada, listada fuera del cuerpo.
    """

    cliente = cliente_con_fragmentos(
        fragmento(fragmento_id="frg-001", pieza_id="pie-002", texto="Texto uno."),
        fragmento(
            fragmento_id="frg-002",
            pieza_id="pie-001",
            texto="Texto dos distinto.",
            ubicacion=None,
        ),
    )

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 1),
        hasta=date(1926, 8, 31),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
        precision="mes",
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    borrador = resultado.borrador_path.read_text(encoding="utf-8")
    assert "Texto uno." in borrador
    assert "Texto dos distinto." not in borrador
    assert borrador.count("Fuente: pie-002 / frg-001, página 3 (7 de agosto de 1926)") == 1
    assert "Fuente: pie-001 / frg-002" not in borrador
    assert (
        "- pie-001 / frg-002 (7 de agosto de 1926): no se usa: el post cita una "
        "sola referencia" in borrador
    )
    registro = ultimo_registro(resultado.log_path)
    assert registro["hv_fragmentos"] == 2
    assert registro["hv_fragmentos_elegibles"] == 2
    assert registro["hv_fragmentos_publicados"] == 1
    assert registro["hv_piezas_fuente"] == ["pie-002"]


def test_la_precision_de_fecha_se_conserva_en_la_cita(tmp_path: Path):
    """Un fragmento con precisión de mes no se presenta como día exacto."""

    cliente = cliente_con_fragmentos(
        fragmento(
            rango_=rango(date(1926, 8, 1), date(1926, 8, 31), "mes"),
            ubicacion=None,
        )
    )

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 1),
        hasta=date(1926, 8, 31),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
        precision="mes",
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    borrador = resultado.borrador_path.read_text(encoding="utf-8")
    assert "Fuente: pie-001 / frg-001 (agosto de 1926)" in borrador
    assert "Efeméride: agosto de 1926" in borrador
    assert "7 de agosto" not in borrador


def test_el_tema_viaja_en_la_consulta_y_en_la_auditoria_como_hash(tmp_path: Path):
    cliente = cliente_con_fragmentos(fragmento())

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 1),
        hasta=date(1926, 8, 31),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
        tema="apertura",
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    (consulta,) = cliente.consultas
    assert consulta.texto == "apertura"
    registro = ultimo_registro(resultado.log_path)
    assert registro["hv_consulta"]["tema_hash"] is not None
    assert "apertura" not in resultado.log_path.read_text(encoding="utf-8")


# --- Selección del fragmento por fecha y por extensión ---------------------------

# Los fragmentos «que no entran» miden 3500 caracteres: más que el techo de
# LinkedIn (3000), el mayor de los dos canales desde DEF-A1-025.


@pytest.mark.parametrize("canal", ["instagram", "linkedin"])
def test_el_primero_que_no_entra_se_descarta_y_se_prueba_el_siguiente(
    tmp_path: Path, canal: str
):
    """Varios candidatos: el primero no entra y se publica el siguiente."""

    cliente = cliente_con_fragmentos(
        fragmento(
            fragmento_id="frg-largo",
            pieza_id="pie-largo",
            texto="x" * 3500,
        ),
        fragmento(
            fragmento_id="frg-util",
            pieza_id="pie-util",
            texto="Un texto breve que entra.",
            ubicacion=None,
        ),
    )

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal=canal,
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride(canal)),
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    borrador = resultado.borrador_path.read_text(encoding="utf-8")
    assert "Un texto breve que entra." in borrador
    assert "Fuente: pie-util / frg-util (7 de agosto de 1926)" in borrador
    assert "x" * 3500 not in borrador
    assert "REFERENCIAS NO UTILIZADAS" in borrador
    assert (
        "- pie-largo / frg-largo (7 de agosto de 1926): no entra completa en el "
        "canal" in borrador
    )
    registro = ultimo_registro(resultado.log_path)
    assert registro["hv_fragmentos"] == 2
    assert registro["hv_fragmentos_elegibles"] == 2
    assert registro["hv_fragmentos_publicados"] == 1
    assert registro["hv_piezas_fuente"] == ["pie-util"]
    assert registro["referencias_excluidas"] == [
        {
            "referencia": "pie-largo / frg-largo",
            "motivo": "no_entra_completo_en_el_canal",
        }
    ]


def test_la_consulta_no_se_limita_a_uno_para_poder_descartar_al_primero(
    tmp_path: Path,
):
    cliente = cliente_con_fragmentos(
        fragmento(fragmento_id="frg-001", pieza_id="pie-001", texto="x" * 3500),
        fragmento(
            fragmento_id="frg-002",
            pieza_id="pie-002",
            texto="Entra sin problema.",
            ubicacion=None,
        ),
    )

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
        limite=10,
    )

    (consulta,) = cliente.consultas
    assert consulta.limite == 10
    assert resultado.estado == "PENDIENTE_VALIDACION"
    registro = ultimo_registro(resultado.log_path)
    assert registro["hv_consulta"]["limite"] == 10
    assert registro["hv_fragmentos"] == 2
    assert registro["hv_fragmentos_publicados"] == 1


def test_solapamiento_temporal_no_sustenta_la_fecha(tmp_path: Path):
    """«Entre 2015 y 2019» no sustenta una efeméride de abril de 2016."""

    class GeneratorNoInvocable:
        modelo = "fake-no-invocar"
        num_predict = None

        def generar(self, prompt: str) -> str:
            raise AssertionError("sin elegibles no hay generación")

    cliente = cliente_con_fragmentos(
        fragmento(
            rango_=rango(date(2015, 1, 1), date(2019, 12, 31), "rango"),
            ubicacion=None,
        )
    )

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(2016, 4, 1),
        hasta=date(2016, 4, 30),
        precision="mes",
        canal="instagram",
        directorio_salida=tmp_path,
        generator=GeneratorNoInvocable(),
    )

    assert resultado.estado == "INCOMPLETA"
    assert resultado.borrador_path is None
    registro = ultimo_registro(resultado.log_path)
    assert registro["resultado"] == "material_insuficiente"
    assert registro["motivo_material"] == "sin_fecha_elegible"
    assert registro["hv_fragmentos"] == 1
    assert registro["hv_fragmentos_elegibles"] == 0
    assert registro["referencias_excluidas"] == [
        {
            "referencia": "pie-001 / frg-001",
            "motivo": "fuera_del_periodo_consultado",
        }
    ]
    assert not list((tmp_path / "borradores").glob("*"))


@pytest.mark.parametrize(
    "precision_fuente,desde_fuente,hasta_fuente,esperado",
    [
        ("dia", date(1926, 8, 7), date(1926, 8, 7), "PENDIENTE_VALIDACION"),
        ("mes", date(1926, 8, 1), date(1926, 8, 31), "PENDIENTE_VALIDACION"),
        ("anio", date(1926, 1, 1), date(1926, 12, 31), "INCOMPLETA"),
        ("decada", date(1920, 1, 1), date(1929, 12, 31), "INCOMPLETA"),
    ],
    ids=["dia", "mes", "anio", "decada"],
)
def test_la_precision_declarada_no_se_trata_como_fecha_exacta(
    tmp_path: Path,
    precision_fuente: str,
    desde_fuente: date,
    hasta_fuente: date,
    esperado: str,
):
    """La fecha de la fuente tiene que caer dentro del mes consultado.

    Un día o un mes de agosto de 1926 quedan dentro; un año o una década no
    quedan dentro de agosto y por eso no sustentan esa efeméride.
    """

    cliente = cliente_con_fragmentos(
        fragmento(
            rango_=rango(desde_fuente, hasta_fuente, precision_fuente),
            ubicacion=None,
        )
    )

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 1),
        hasta=date(1926, 8, 31),
        precision="mes",
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
    )

    assert resultado.estado == esperado


def test_un_mes_no_queda_dentro_de_una_consulta_de_un_dia(tmp_path: Path):
    """La precisión de la fuente y la de la consulta se comparan tal cual."""

    cliente = cliente_con_fragmentos(
        fragmento(
            rango_=rango(date(1926, 8, 1), date(1926, 8, 31), "mes"),
            ubicacion=None,
        )
    )

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        precision="dia",
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
    )

    assert resultado.estado == "INCOMPLETA"
    assert (
        ultimo_registro(resultado.log_path)["motivo_material"]
        == "sin_fecha_elegible"
    )


def test_la_referencia_excluida_queda_fuera_del_cuerpo_publicable(tmp_path: Path):
    cliente = cliente_con_fragmentos(
        fragmento(
            fragmento_id="frg-fuera",
            pieza_id="pie-fuera",
            texto="No debe publicarse.",
            rango_=rango(date(1926, 1, 1), date(1926, 12, 31), "anio"),
            ubicacion=None,
        ),
        fragmento(
            fragmento_id="frg-ok",
            pieza_id="pie-ok",
            texto="Este sí se publica.",
            ubicacion=None,
        ),
    )

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    borrador = resultado.borrador_path.read_text(encoding="utf-8")
    assert "Este sí se publica." in borrador
    # La prosa de lo excluido no se publica ni aparece en la nota de referencias.
    assert "No debe publicarse." not in borrador
    cuerpo, separador, referencias = borrador.partition(
        "\nREFERENCIAS NO UTILIZADAS\n"
    )
    assert separador
    assert "pie-fuera / frg-fuera" not in cuerpo
    assert "pie-fuera / frg-fuera" in referencias
    assert "la fecha sustentada queda fuera del período consultado" in referencias


@pytest.mark.parametrize("canal", ["instagram", "linkedin"])
def test_el_gate_de_hechos_sigue_vigente_en_ambos_canales(
    tmp_path: Path, canal: str
):
    salida_rota = json.dumps(
        {
            "gancho": "Un día como hoy dejó huella en nuestra historia.",
            "prosa": "El acta consigna la apertura de los primeros cursos.",
            "cta": CTA_POR_CANAL[canal],
            "hashtags": ["#FIE"],
        },
        ensure_ascii=False,
    )

    resultado = procesar_post_efemeride(
        historia_viva=cliente_con_fragmentos(fragmento()),
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal=canal,
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_rota),
    )

    assert resultado.estado == "FALLIDA"
    assert resultado.borrador_path is None
    registro = ultimo_registro(resultado.log_path)
    assert "source_fact_in_creative_field" in registro["validation_errors"]


# --- Sin material y fallas de la fuente ------------------------------------------


def test_consulta_vacia_no_genera_post_ni_invoca_al_generador(tmp_path: Path):
    class GeneratorNoInvocable:
        modelo = "fake-no-invocar"
        num_predict = None

        def generar(self, prompt: str) -> str:
            raise AssertionError("sin material no hay generación")

    resultado = procesar_post_efemeride(
        historia_viva=HistoriaVivaFake(),
        desde=date(1900, 1, 1),
        hasta=date(1900, 12, 31),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=GeneratorNoInvocable(),
    )

    assert resultado.estado == "INCOMPLETA"
    assert resultado.borrador_path is None
    assert resultado.error == "La consulta no devolvió material histórico"
    registro = ultimo_registro(resultado.log_path)
    assert registro["resultado"] == "material_insuficiente"
    assert registro["validation_errors"] == ["material_insuficiente"]
    assert registro["hv_fragmentos"] == 0
    assert registro["data_origin"] == "insumo_a2"
    assert not list((tmp_path / "borradores").glob("*"))


def test_historia_viva_caida_termina_fallida_sin_borrador(tmp_path: Path):
    cliente = HistoriaVivaFake(
        fragmentos=(fragmento(),),
        falla_en={"buscar_fragmentos": "historia_viva_rate_limited"},
    )

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 1),
        hasta=date(1926, 8, 31),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
    )

    assert resultado.estado == "FALLIDA"
    assert resultado.borrador_path is None
    registro = ultimo_registro(resultado.log_path)
    assert registro["resultado"] == "source_failure"
    assert registro["source_error_code"] == "historia_viva_rate_limited"


def test_un_puerto_que_devuelve_basura_es_falla_de_intercambio(tmp_path: Path):
    class PuertoBasura:
        def buscar_fragmentos(self, consulta):
            return ({"no": "es un fragmento"},)

        def obtener_pieza(self, pieza_id):
            return None

        def registrar_aporte(self, aporte):
            raise AssertionError

    resultado = procesar_post_efemeride(
        historia_viva=PuertoBasura(),
        desde=date(1926, 8, 1),
        hasta=date(1926, 8, 31),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
    )

    assert resultado.estado == "FALLIDA"
    registro = ultimo_registro(resultado.log_path)
    assert registro["source_error_code"] == "historia_viva_response_invalid"


def test_un_fragmento_con_controles_no_se_renderiza(tmp_path: Path):
    cliente = cliente_con_fragmentos(
        fragmento(texto="Texto\u202eoculto de prueba")
    )

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 1),
        hasta=date(1926, 8, 31),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
    )

    assert resultado.estado == "FALLIDA"
    registro = ultimo_registro(resultado.log_path)
    assert registro["validation_errors"] == ["source_rendering_unsafe"]


def test_un_fragmento_que_narra_una_aprobacion_si_se_cita(tmp_path: Path):
    """El gate de estado no cae sobre el texto citado.

    «El Consejo aprobó…» es afirmación atribuida a la fuente citada, no un
    estado del borrador: prohibirla haría imposible citar la historia.
    """

    cliente = cliente_con_fragmentos(
        fragmento(texto="El Consejo aprobó la creación del instituto.")
    )

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 1),
        hasta=date(1926, 8, 31),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert "El Consejo aprobó la creación del instituto." in (
        resultado.borrador_path.read_text(encoding="utf-8")
    )


# --- Los mismos gates de HU-011 ----------------------------------------------------


@pytest.mark.parametrize(
    "salida_rota",
    [
        "no es json",
        '{"gancho":"Un día como hoy dejó huella en nuestra historia.","prosa":"Cada efeméride es una invitación a mirar el camino recorrido por la Facultad.","cta":"Encontrá el enlace en nuestro perfil."}',
        json.dumps(
            {
                "gancho": "Un día como hoy dejó huella en nuestra historia.",
                "prosa": "El acta consigna la apertura de los primeros cursos.",
                "cta": "Encontrá el enlace en nuestro perfil.",
                "hashtags": ["#FIE"],
            },
            ensure_ascii=False,
        ),
        json.dumps(
            {
                "gancho": "Recordamos lo que pasó un 7 de agosto.",
                "prosa": "Cada efeméride es una invitación a mirar el camino "
                "recorrido por la Facultad.",
                "cta": "Encontrá el enlace en nuestro perfil.",
                "hashtags": ["#FIE"],
            },
            ensure_ascii=False,
        ),
        json.dumps(
            {
                "gancho": "Un día como hoy dejó huella en nuestra historia.",
                "prosa": "La primera cursada de la Facultad sumó 20 asistentes ese año.",
                "cta": "Encontrá el enlace en nuestro perfil.",
                "hashtags": ["#FIE"],
            },
            ensure_ascii=False,
        ),
        json.dumps(
            {
                "gancho": "Un día como hoy dejó huella en nuestra historia.",
                "prosa": "Cada efeméride es una invitación a mirar el camino.",
                "cta": "Encontrá el enlace en nuestro perfil.",
                "hashtags": ["#Inventado"],
            },
            ensure_ascii=False,
        ),
    ],
    ids=[
        "json_invalid",
        "json_fields_invalid",
        "texto_citado_en_prosa",
        "fecha_en_gancho",
        "numero_en_prosa",
        "hashtag_fuera_de_allowlist",
    ],
)
def test_la_salida_del_modelo_pasa_los_mismos_gates(
    tmp_path: Path, salida_rota: str
):
    resultado = procesar_post_efemeride(
        historia_viva=cliente_con_fragmentos(fragmento()),
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_rota),
    )

    assert resultado.estado == "FALLIDA"
    assert resultado.borrador_path is None
    registro = ultimo_registro(resultado.log_path)
    assert registro["estado"] == "FALLIDA"
    assert registro["resultado"] in {"salida_no_conforme", "salida_vacia"}


def test_la_prosa_no_puede_nombrar_el_mes_de_la_efemeride(tmp_path: Path):
    """«en agosto» ya es afirmar la fecha: la fecha la agrega el renderer."""

    salida = json.dumps(
        {
            "gancho": "Un día como hoy dejó huella en nuestra historia.",
            "prosa": "Cada efeméride de agosto invita a mirar el camino.",
            "cta": "Encontrá el enlace en nuestro perfil.",
            "hashtags": ["#FIE"],
        },
        ensure_ascii=False,
    )

    resultado = procesar_post_efemeride(
        historia_viva=cliente_con_fragmentos(fragmento()),
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida),
    )

    assert resultado.estado == "FALLIDA"
    registro = ultimo_registro(resultado.log_path)
    assert "source_fact_in_creative_field" in registro["validation_errors"]


def test_un_error_de_contenido_reintenta_con_feedback(tmp_path: Path):
    """Mismo reintento acotado que `posts.py`, con instrucción de efeméride."""

    salidas = iter(
        [
            json.dumps(
                {
                    "gancho": "Un día como hoy dejó huella en nuestra historia.",
                    "prosa": "El acta consigna la apertura de los primeros cursos.",
                    "cta": "Encontrá el enlace en nuestro perfil.",
                    "hashtags": ["#FIE"],
                },
                ensure_ascii=False,
            ),
            salida_efemeride(),
        ]
    )
    prompts_vistos: list[str] = []

    class GeneratorSecuencial:
        modelo = "fake-secuencial"
        num_predict = None

        def generar(self, prompt: str) -> str:
            prompts_vistos.append(prompt)
            return next(salidas)

    resultado = procesar_post_efemeride(
        historia_viva=cliente_con_fragmentos(fragmento()),
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=GeneratorSecuencial(),
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert len(prompts_vistos) == 2
    assert "CORRECCION_OBLIGATORIA" in prompts_vistos[1]
    assert "source_fact_in_creative_field" in prompts_vistos[1]
    assert "textos citados" in prompts_vistos[1]
    lineas = resultado.log_path.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 2
    primero = json.loads(lineas[0])
    assert primero["resultado"] == "reintento_pendiente"
    assert primero["intento"] == 1


def test_el_error_del_generador_no_reintenta(tmp_path: Path):
    llamadas = 0

    class GeneratorRoto:
        modelo = "fake-roto"
        num_predict = None

        def generar(self, prompt: str) -> str:
            nonlocal llamadas
            llamadas += 1
            raise RuntimeError("ollama caído")

    resultado = procesar_post_efemeride(
        historia_viva=cliente_con_fragmentos(fragmento()),
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=GeneratorRoto(),
    )

    assert resultado.estado == "FALLIDA"
    assert llamadas == 1
    registro = ultimo_registro(resultado.log_path)
    assert registro["resultado"] == "error_generacion"


# --- Entrada inválida -------------------------------------------------------------


def test_canal_fuera_del_catalogo_es_invalida(tmp_path: Path):
    resultado = procesar_post_efemeride(
        historia_viva=cliente_con_fragmentos(fragmento()),
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal="tiktok",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
    )

    assert resultado.estado == "INVALIDA"
    registro = ultimo_registro(resultado.log_path)
    assert registro["resultado"] == "channel_invalid"
    assert registro["validation_errors"] == ["channel_not_allowed"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"hasta": date(1926, 8, 1), "desde": date(1926, 8, 7)},
        {"precision": "aproximada"},
        {"tema": ""},
        {"tema": "x" * 301},
        {"tema": "tema\ncon salto"},
        {"limite": 0},
        {"limite": 51},
        {"procedencia": "inventada"},
    ],
    ids=[
        "rango_invertido",
        "precision_desconocida",
        "tema_vacio",
        "tema_largo",
        "tema_control",
        "limite_cero",
        "limite_max",
        "procedencia_desconocida",
    ],
)
def test_la_consulta_invalida_no_llega_al_puerto(tmp_path: Path, kwargs):
    base = {
        "desde": date(1926, 8, 7),
        "hasta": date(1926, 8, 7),
        "canal": "instagram",
        "directorio_salida": tmp_path,
        "generator": FakeGenerator(salida_efemeride()),
    }
    base.update(kwargs)
    cliente = cliente_con_fragmentos(fragmento())

    resultado = procesar_post_efemeride(historia_viva=cliente, **base)

    assert resultado.estado == "INVALIDA"
    registro = ultimo_registro(resultado.log_path)
    assert registro["resultado"] == "consulta_invalida"
    assert registro["validation_errors"] == ["consulta_invalida"]
    assert cliente.consultas == []


def test_una_politica_incompatible_con_la_allowlist_es_invalida(tmp_path: Path):
    politica = PoliticaPost(
        version="post_instagram_policy_provisional_v1",
        status="PROVISIONAL_NO_INSTITUCIONAL",
        max_chars=1000,
        min_hashtags=6,
        max_hashtags=10,
    )
    cliente = cliente_con_fragmentos(fragmento())

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
        politica=politica,
    )

    assert resultado.estado == "INVALIDA"
    registro = ultimo_registro(resultado.log_path)
    assert registro["validation_errors"] == ["structured_policy_incompatible"]
    assert cliente.consultas == []


def test_un_contrato_de_otra_familia_no_llega_al_puerto(tmp_path: Path):
    cliente = cliente_con_fragmentos(fragmento())

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
        contrato=CONTRATO_CREATIVO_V2,
    )

    assert resultado.estado == "INVALIDA"
    registro = ultimo_registro(resultado.log_path)
    assert registro["resultado"] == "contract_incompatible"
    assert registro["validation_errors"] == ["efemeride_contract_incompatible"]
    assert cliente.consultas == []


def test_la_falla_del_destino_se_audita_como_tal(tmp_path: Path):
    class DestinoRoto:
        def guardar(self, id_solicitud: str, contenido: str):
            raise DestinoBorradoresError("destination_unavailable")

    resultado = procesar_post_efemeride(
        historia_viva=cliente_con_fragmentos(fragmento()),
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
        destino=DestinoRoto(),
    )

    assert resultado.estado == "FALLIDA"
    registro = ultimo_registro(resultado.log_path)
    assert registro["resultado"] == "destination_failure"
    assert registro["destination_error_code"] == "destination_unavailable"


# --- Procedencia e identidad -------------------------------------------------------


def test_la_procedencia_sintetica_se_declara_en_auditoria_y_borrador(tmp_path: Path):
    resultado = procesar_post_efemeride(
        historia_viva=cliente_con_fragmentos(fragmento()),
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal="instagram",
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride()),
        procedencia=PROCEDENCIA_SINTETICA,
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    borrador = resultado.borrador_path.read_text(encoding="utf-8")
    assert "material sintético de prueba" in borrador
    assert ultimo_registro(resultado.log_path)["data_origin"] == "synthetic_test"


def test_el_id_del_borrador_es_determinista_y_objeto_de_decision(tmp_path: Path):
    args = {
        "historia_viva": cliente_con_fragmentos(fragmento()),
        "desde": date(1926, 8, 7),
        "hasta": date(1926, 8, 7),
        "canal": "instagram",
        "generator": FakeGenerator(salida_efemeride()),
    }
    primero = procesar_post_efemeride(directorio_salida=tmp_path / "a", **args)
    segundo = procesar_post_efemeride(directorio_salida=tmp_path / "b", **args)

    assert primero.borrador_path.name == segundo.borrador_path.name
    assert primero.borrador_path.name.startswith("efemeride-1926-08-07-")
    assert primero.borrador_path.stem.endswith("-instagram")
    # El nombre del archivo es el objeto sobre el que decide la SEU en el
    # Form de decisiones: tiene que pasar su allowlist.
    assert DECISION_ID_RE.fullmatch(primero.borrador_path.stem) is not None


def test_otra_procedencia_no_cambia_el_determinismo(tmp_path: Path):
    """Mismo pedido → mismo borrador; tema distinto → otro objeto."""

    base = {
        "historia_viva": cliente_con_fragmentos(fragmento()),
        "desde": date(1926, 8, 1),
        "hasta": date(1926, 8, 31),
        "canal": "instagram",
        "directorio_salida": tmp_path,
        "generator": FakeGenerator(salida_efemeride()),
    }
    sin_tema = procesar_post_efemeride(**base)
    con_tema = procesar_post_efemeride(tema="apertura", **base)

    assert sin_tema.borrador_path.name != con_tema.borrador_path.name


@pytest.mark.parametrize("canal", ["instagram", "linkedin"])
def test_sin_fragmento_que_entre_informa_material_no_utilizable(
    tmp_path: Path, canal: str
):
    """Si ningún candidato entra completo, no hay borrador y se dice por qué."""

    cliente = cliente_con_fragmentos(fragmento(texto="x" * 3500))
    politica = POLITICAS_DEFAULT[canal]

    resultado = procesar_post_efemeride(
        historia_viva=cliente,
        desde=date(1926, 8, 7),
        hasta=date(1926, 8, 7),
        canal=canal,
        directorio_salida=tmp_path,
        generator=FakeGenerator(salida_efemeride(canal)),
        politica=politica,
    )

    assert resultado.estado == "INCOMPLETA"
    assert resultado.borrador_path is None
    assert resultado.error == "Ningún fragmento elegible entra completo en el canal"
    registro = ultimo_registro(resultado.log_path)
    assert registro["resultado"] == "material_no_utilizable"
    assert registro["hv_fragmentos_elegibles"] == 1
    assert registro["hv_fragmentos_publicados"] == 0
    assert registro["validation_errors"] == ["length_out_of_range"]
    assert not list((tmp_path / "borradores").glob("*"))
