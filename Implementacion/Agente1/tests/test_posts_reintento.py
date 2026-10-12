"""Reintento acotado con feedback de regla en el camino estructurado.

La medición live del 22/09 (`evidencias/medicion-hu011-v3-post-seu-2026-09-22.md`)
dejó la brecha de HU-011 v3 en obediencia del modelo: tuteo y fragmentos del
título a pesar del prompt. Estas pruebas cubren el mecanismo que la ataca —
un segundo intento con las reglas caídas como instrucción adicional— y sus
bordes: qué se reintenta, qué no, y cómo queda auditado.
"""

import json
from pathlib import Path

import pytest

from agente1.fuentes import CsvFuenteSolicitudes
from agente1.posts import (
    CODIGOS_REINTENTABLES,
    CONTRATO_CREATIVO_V2,
    CONTRATO_CREATIVO_V3,
    INSTRUCCION_REINTENTO_POR_CODIGO,
    MAX_INTENTOS_GENERACION,
    procesar_post,
    procesar_post_estructurado,
)
from agente1.presupuesto import PresupuestoAgotadoError

ROOT = Path(__file__).parents[1]
DATASET = ROOT / "data" / "actividades_sinteticas.csv"

CREATIVIDAD_CONFORME = {
    "gancho": "¿Buscás un espacio para compartir lo que sabés?",
    "prosa": (
        "Te invitamos a sumarte a una propuesta abierta, pensada para que "
        "puedas intercambiar experiencias y aprender junto a otras personas."
    ),
    "cta": "Sumate y participá de la propuesta.",
    "hashtags": ["#FIE", "#UNDEF"],
}
CREATIVIDAD_TUTEO = dict(
    CREATIVIDAD_CONFORME,
    cta="Inscríbete y conocé nuevas propuestas para participar.",
)
CREATIVIDAD_CON_NUMERO = dict(
    CREATIVIDAD_CONFORME,
    prosa="Nos encontramos el 5 de agosto a compartir experiencias con otras personas.",
)
CREATIVIDAD_V2_CONFORME = {
    "gancho": "Una propuesta para aprender y compartir.",
    "prosa": "Sumate a una experiencia pensada para la comunidad.",
    "cta": "Encontrá el enlace en nuestro perfil.",
    "hashtags": ["#FIE", "#UNDEF"],
}


def _salida(creatividad: dict[str, object]) -> str:
    return json.dumps(creatividad, ensure_ascii=False, sort_keys=True)


class GeneradorSecuencia:
    """Fake que responde en orden: la lista ejercita el reintento.

    Cada elemento puede ser una salida o una excepción a lanzar; agotada la
    lista repite el último elemento. `prompts` conserva lo que el pipeline le
    mandó, para verificar que el segundo intento lleva un prompt distinto.
    """

    modelo = "fake-secuencia"
    num_predict = None

    def __init__(self, salidas: list[object]) -> None:
        self._salidas = list(salidas)
        self.prompts: list[str] = []

    def generar(self, prompt: str) -> str:
        self.prompts.append(prompt)
        salida = self._salidas[min(len(self.prompts), len(self._salidas)) - 1]
        if isinstance(salida, Exception):
            raise salida
        return str(salida)


def _procesar(salidas: list[object], tmp_path: Path, contrato=CONTRATO_CREATIVO_V3):
    generador = GeneradorSecuencia(salidas)
    resultado = procesar_post_estructurado(
        fuente=CsvFuenteSolicitudes(DATASET),
        id_solicitud="SYN-001",
        canal="instagram",
        directorio_salida=tmp_path,
        generator=generador,
        contrato=contrato,
    )
    return resultado, generador


def _lineas(resultado) -> list[dict[str, object]]:
    return [
        json.loads(linea)
        for linea in resultado.log_path.read_text(encoding="utf-8").splitlines()
    ]


def test_cada_codigo_reintentable_tiene_instruccion_de_feedback() -> None:
    """Sin instrucción el reintento reenviaría el mismo prompt: con
    `temperature=0` la salida sería idéntica a la ya rechazada."""
    assert CODIGOS_REINTENTABLES == frozenset(INSTRUCCION_REINTENTO_POR_CODIGO)


def test_falla_de_contenido_reintenta_con_feedback_y_conforma(tmp_path: Path) -> None:
    resultado, generador = _procesar(
        [_salida(CREATIVIDAD_TUTEO), _salida(CREATIVIDAD_CONFORME)], tmp_path
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert resultado.borrador_path is not None
    assert len(generador.prompts) == 2
    # Con `temperature=0` el segundo prompt tiene que ser distinto del primero:
    # el feedback va dentro de la zona de instrucciones, antes de los datos no
    # confiables, y nombra la regla caída sin citar el literal rechazado.
    assert generador.prompts[1] != generador.prompts[0]
    assert "CORRECCION_OBLIGATORIA" not in generador.prompts[0]
    assert "CORRECCION_OBLIGATORIA" in generador.prompts[1]
    assert "[non_rioplatense_register]" in generador.prompts[1]
    assert generador.prompts[1].index("CORRECCION_OBLIGATORIA") < generador.prompts[
        1
    ].index("DATOS_JSON_INICIO")

    lineas = _lineas(resultado)
    assert len(lineas) == 2
    assert lineas[0]["resultado"] == "reintento_pendiente"
    assert lineas[0]["intento"] == 1
    assert "non_rioplatense_register" in lineas[0]["validation_errors"]
    assert lineas[1]["resultado"] == "borrador_generado"
    assert lineas[1]["intento"] == 2
    assert all(linea["correlation_id"] == resultado.correlation_id for linea in lineas)


def test_reintento_agotado_queda_fallida_y_audita_los_dos_intentos(
    tmp_path: Path,
) -> None:
    resultado, generador = _procesar(
        [_salida(CREATIVIDAD_TUTEO), _salida(CREATIVIDAD_TUTEO)], tmp_path
    )

    assert resultado.estado == "FALLIDA"
    assert resultado.borrador_path is None
    assert len(generador.prompts) == MAX_INTENTOS_GENERACION
    lineas = _lineas(resultado)
    assert len(lineas) == 2
    assert lineas[0]["resultado"] == "reintento_pendiente"
    assert lineas[0]["intento"] == 1
    # La terminal conserva el vocabulario de siempre; `intento` es lo que la
    # distingue de una `salida_no_conforme` de primer intento.
    assert lineas[1]["resultado"] == "salida_no_conforme"
    assert lineas[1]["intento"] == 2
    assert lineas[1]["estado"] == "FALLIDA"
    # El log no copia la prosa rechazada ni datos de la actividad.
    serializado = resultado.log_path.read_text(encoding="utf-8")
    assert "Inscríbete y conocé" not in serializado
    assert "Taller sintético" not in serializado


def test_la_falla_terminal_reporta_los_errores_del_ultimo_intento(
    tmp_path: Path,
) -> None:
    resultado, _ = _procesar(
        [_salida(CREATIVIDAD_TUTEO), _salida(CREATIVIDAD_CON_NUMERO)], tmp_path
    )

    assert resultado.estado == "FALLIDA"
    lineas = _lineas(resultado)
    assert "non_rioplatense_register" in lineas[0]["validation_errors"]
    assert "unauthorized_number" in lineas[1]["validation_errors"]
    assert "non_rioplatense_register" not in lineas[1]["validation_errors"]


@pytest.mark.parametrize(
    ("salidas", "resultado_esperado"),
    [
        # Forma inválida o vacía: el parseo es determinista, el reintento no
        # lo arregla aunque la siguiente salida preparada sea conforme.
        (['{"gancho":"A"', _salida(CREATIVIDAD_CONFORME)], "salida_no_conforme"),
        (["", _salida(CREATIVIDAD_CONFORME)], "salida_vacia"),
        # Infraestructura: ni el presupuesto ni el transporte se corrigen con
        # otro prompt.
        (
            [PresupuestoAgotadoError("agotado"), _salida(CREATIVIDAD_CONFORME)],
            "presupuesto_agotado",
        ),
        (
            [RuntimeError("transporte"), _salida(CREATIVIDAD_CONFORME)],
            "error_generacion",
        ),
    ],
)
def test_fallas_que_no_son_de_contenido_no_reintentan(
    salidas: list[object], resultado_esperado: str, tmp_path: Path
) -> None:
    resultado, generador = _procesar(salidas, tmp_path)

    assert resultado.estado == "FALLIDA"
    assert len(generador.prompts) == 1
    lineas = _lineas(resultado)
    assert len(lineas) == 1
    assert lineas[0]["resultado"] == resultado_esperado
    assert lineas[0]["intento"] == 1


def test_presupuesto_agotado_en_el_reintento_cierra_la_ejecucion(
    tmp_path: Path,
) -> None:
    """Una falla de infraestructura en el segundo intento no abre un tercero."""
    resultado, generador = _procesar(
        [_salida(CREATIVIDAD_TUTEO), PresupuestoAgotadoError("agotado")], tmp_path
    )

    assert resultado.estado == "FALLIDA"
    assert len(generador.prompts) == 2
    lineas = _lineas(resultado)
    assert lineas[0]["resultado"] == "reintento_pendiente"
    assert lineas[1]["resultado"] == "presupuesto_agotado"
    assert lineas[1]["intento"] == 2


def test_el_reintento_tambien_aplica_al_contrato_v2(tmp_path: Path) -> None:
    """`creative_slot_not_in_catalog` es de redacción: la misma corrección."""
    creatividad_fuera_de_catalogo = dict(
        CREATIVIDAD_V2_CONFORME, gancho="Una frase que no está en el catálogo."
    )
    resultado, generador = _procesar(
        [_salida(creatividad_fuera_de_catalogo), _salida(CREATIVIDAD_V2_CONFORME)],
        tmp_path,
        contrato=CONTRATO_CREATIVO_V2,
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert len(generador.prompts) == 2
    lineas = _lineas(resultado)
    assert "creative_slot_not_in_catalog" in lineas[0]["validation_errors"]
    assert "[creative_slot_not_in_catalog]" in generador.prompts[1]


def test_camino_heredado_text_v1_no_reintenta(tmp_path: Path) -> None:
    """El reintento es del contrato estructurado; `text-v1` queda como estaba."""
    salida_incompleta = (
        "CANAL: instagram\nTEXTO:\nSumate a la actividad.\nHASHTAGS:\n#Actividad"
    )
    generador = GeneradorSecuencia([salida_incompleta, "no debe usarse"])
    resultado = procesar_post(
        fuente=CsvFuenteSolicitudes(DATASET),
        id_solicitud="SYN-001",
        canal="instagram",
        directorio_salida=tmp_path,
        generator=generador,
    )

    assert resultado.estado == "FALLIDA"
    assert len(generador.prompts) == 1
    lineas = _lineas(resultado)
    assert len(lineas) == 1
    assert lineas[0]["resultado"] == "salida_no_conforme"
    assert "intento" not in lineas[0]


def test_fallas_previas_a_la_generacion_auditan_intento_cero(tmp_path: Path) -> None:
    """`intento: 0` dice que la ejecución nunca llegó al generador."""
    generador = GeneradorSecuencia([_salida(CREATIVIDAD_CONFORME)])
    resultado = procesar_post_estructurado(
        fuente=CsvFuenteSolicitudes(DATASET),
        id_solicitud="SYN-002",  # caso negativo de la matriz: sin contacto
        canal="instagram",
        directorio_salida=tmp_path,
        generator=generador,
        contrato=CONTRATO_CREATIVO_V3,
    )

    assert resultado.estado == "INCOMPLETA"
    assert generador.prompts == []
    lineas = _lineas(resultado)
    assert len(lineas) == 1
    assert lineas[0]["resultado"] == "datos_incompletos"
    assert lineas[0]["intento"] == 0
