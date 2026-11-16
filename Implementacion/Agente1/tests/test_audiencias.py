"""Regresion del catalogo externo de audiencias y del prellenado de correo.

Ninguna direccion institucional se versiona: las fixtures usan `@example.com`.
El catalogo real vive fuera del repo, en
`~/.config/agente1/audiencias-institucionales.json`, con `chmod 600`.
"""

from __future__ import annotations

import ast
import json
import socket
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from agente1.audiencias import (
    BASE_COMPOSE,
    MAX_URL_COMPOSE,
    ErrorAudiencias,
    audiencias_para,
    cargar_audiencias,
    construir_prellenado,
    url_compose,
)
from agente1.confirmaciones import email_valido

RAIZ_AGENTE = Path(__file__).resolve().parents[1]
SRC = RAIZ_AGENTE / "src"
MODULO = SRC / "agente1" / "audiencias.py"

# Los 18 grupos del listado, sin sus direcciones reales. El id, el nombre, la
# categoria y el alcance son los del catalogo externo; la direccion se reemplaza
# por `@example.com` en la fixture.
GRUPOS = (
    ("alumnos_geomatica", "Alumnos Geomatica", "alumnos_geomatica", "alumnos", "segmentado"),
    ("alumnos_ingenieria", "Alumnos Ingenieria", "alumnosingenieria", "alumnos", "segmentado"),
    ("alumnos_posgrados", "Alumnos Posgrados", "alumnosposgrados", "alumnos", "segmentado"),
    ("alumnos_hys", "Alumnos Tec Higiene y Seguridad", "alumnos_hys", "alumnos", "segmentado"),
    ("alumnos_tec_utn", "Alumnos Tec UTN", "alumnos_tec_utn", "alumnos", "segmentado"),
    ("cfoim", "CFOIM", "cfoim", "institucional", "desconocido"),
    ("comunidad", "Comunidad FIE", "comunidad", "comunidad", "masivo"),
    ("docentes_ingenieria", "Docentes Ingenieria", "docentesingenieria", "docentes", "segmentado"),
    ("docentes_tecnicatura", "Docentes Tecnicatura", "docentestecnicatura", "docentes", "segmentado"),
    ("fieinforma", "FIE Informa", "fieinforma", "institucional", "masivo"),
    ("graduados_civiles", "Graduados Civiles", "graduadosciviles", "graduados", "segmentado"),
    ("graduados_oim", "Graduados OIM", "graduadosoim", "graduados", "desconocido"),
    ("oim_actividad", "Graduados OIM en Actividad", "oimactividad", "graduados", "desconocido"),
    ("personal_gestion", "Personal de Gestion", "personaldegestion", "personal", "interno"),
    ("plana_mayor", "Plana Mayor", "planamayor", "conduccion", "interno"),
    ("secretaria_academica", "Secretaria Academica", "alumnos", "institucional", "interno"),
    ("suboficiales", "Suboficiales", "suboficiales", "personal", "interno"),
    ("soldados", "Soldados", "soldados", "personal", "interno"),
)

USOS_POR_GRUPO = {
    "alumnos_posgrados": ["newsletter"],
    "comunidad": ["fallecimiento"],
    "docentes_ingenieria": ["convocatoria_interna"],
    "docentes_tecnicatura": ["convocatoria_interna"],
    "fieinforma": [
        "difusion_de_actividad",
        "cronica_de_evento",
        "aviso_de_otra_area",
        "saludo_o_efemeride",
    ],
    "graduados_civiles": ["newsletter"],
    "personal_gestion": ["convocatoria_interna"],
    "secretaria_academica": ["difusion_de_actividad"],
}


def _datos_catalogo() -> dict:
    audiencias = []
    for id_grupo, nombre, local, categoria, alcance in GRUPOS:
        audiencia = {
            "id": id_grupo,
            "nombre": nombre,
            "direccion": f"{local}@example.com",
            "categoria": categoria,
            "alcance_esperado": alcance,
            "usos_candidatos": list(USOS_POR_GRUPO.get(id_grupo, [])),
            "estado_aprobacion": "PENDIENTE_SEU",
            "observacion": None,
        }
        if id_grupo in {"fieinforma", "secretaria_academica"}:
            audiencia["origen_uso"] = "DECISION_USUARIO"
        audiencias.append(audiencia)

    return {
        "version": "audiencias_institucionales_v1",
        "fuente": {
            "archivo": "Listado Grupos.pdf",
            "paginas": 2,
            "extraido_con": "pdftotext -raw",
            "fecha_extraccion": "2026-11-16",
            "total_grupos": len(GRUPOS),
            "dominio": "example.com",
        },
        "estado_general": "PENDIENTE_APROBACION_SEU",
        "audiencias": audiencias,
    }


def _escribir_catalogo(tmp_path: Path, datos: dict | None = None) -> Path:
    ruta = tmp_path / "audiencias-institucionales.json"
    ruta.write_text(
        json.dumps(datos if datos is not None else _datos_catalogo(), ensure_ascii=False),
        encoding="utf-8",
    )
    return ruta


def _catalogo(tmp_path: Path):
    return cargar_audiencias(_escribir_catalogo(tmp_path))


def test_los_dieciocho_grupos_cargan_y_validan(tmp_path):
    catalogo = _catalogo(tmp_path)

    assert catalogo.version == "audiencias_institucionales_v1"
    assert catalogo.fuente["total_grupos"] == 18
    assert len(catalogo.audiencias) == 18
    assert {audiencia.id for audiencia in catalogo.audiencias} == {
        grupo[0] for grupo in GRUPOS
    }
    assert all(email_valido(audiencia.direccion) for audiencia in catalogo.audiencias)
    assert all(
        audiencia.estado_aprobacion == "PENDIENTE_SEU"
        for audiencia in catalogo.audiencias
    )
    assert {
        audiencia.id
        for audiencia in catalogo.audiencias
        if audiencia.origen_uso == "DECISION_USUARIO"
    } == {"fieinforma", "secretaria_academica"}


def test_url_con_dieciocho_destinatarios_entra_en_el_limite_y_no_lleva_cuerpo(tmp_path):
    catalogo = _catalogo(tmp_path)
    direcciones = [audiencia.direccion for audiencia in catalogo.audiencias]

    url = url_compose(direcciones, "Gacetilla de prueba")

    assert len(url) <= MAX_URL_COMPOSE
    parametros = parse_qs(urlparse(url).query)
    assert parametros["bcc"][0].count(",") == 17
    assert "body" not in parametros
    assert "to" not in parametros
    assert url.startswith(BASE_COMPOSE)


def test_cuerpo_corto_viaja_en_la_url(tmp_path):
    catalogo = _catalogo(tmp_path)

    prellenado = construir_prellenado(
        "newsletter", "Asunto breve", "Cuerpo breve", catalogo
    )

    parametros = parse_qs(urlparse(prellenado.url).query)
    assert parametros["body"] == ["Cuerpo breve"]
    assert prellenado.cuerpo_portapapeles is None
    assert len(prellenado.url) <= MAX_URL_COMPOSE


def test_cuerpo_largo_vuelve_en_portapapeles_y_la_url_no_lo_lleva(tmp_path):
    catalogo = _catalogo(tmp_path)
    cuerpo = "x" * (MAX_URL_COMPOSE * 2)

    prellenado = construir_prellenado(
        "difusion_de_actividad", "Asunto", cuerpo, catalogo
    )

    assert prellenado.cuerpo_portapapeles == cuerpo
    assert "body=" not in prellenado.url
    assert len(prellenado.url) <= MAX_URL_COMPOSE
    assert parse_qs(urlparse(prellenado.url).query)["bcc"]


def test_cuerpo_que_no_se_pide_vuelve_en_portapapeles(tmp_path):
    catalogo = _catalogo(tmp_path)

    prellenado = construir_prellenado(
        "newsletter",
        "Asunto",
        "Cuerpo que la interfaz copia aparte",
        catalogo,
        incluir_cuerpo=False,
    )

    assert prellenado.cuerpo_portapapeles == "Cuerpo que la interfaz copia aparte"
    assert "body=" not in prellenado.url


def test_duplicados_exactos_colapsan(tmp_path):
    catalogo = _catalogo(tmp_path)

    prellenado = construir_prellenado(
        "difusion_de_actividad",
        "Asunto",
        "Cuerpo",
        catalogo,
        seleccion=["fieinforma", "fieinforma"],
    )

    assert len(prellenado.destinatarios) == 1
    assert prellenado.destinatarios == ("fieinforma@example.com",)

    url = url_compose(
        ["Alumnos_Geomatica@example.com", "alumnos_geomatica@example.com"],
        "Asunto",
    )
    assert parse_qs(urlparse(url).query)["bcc"] == ["alumnos_geomatica@example.com"]


def test_url_usa_quote_y_no_quote_plus():
    url = url_compose(["alumnos_geomatica@example.com"], "Hola mundo")

    assert "su=Hola%20mundo" in url
    assert "su=Hola+mundo" not in url


def test_estado_invalido_falla_cerrado_sin_direcciones(tmp_path):
    datos = _datos_catalogo()
    datos["audiencias"][0]["estado_aprobacion"] = "APROBADO"

    with pytest.raises(ErrorAudiencias) as error:
        cargar_audiencias(_escribir_catalogo(tmp_path, datos))

    assert error.value.codigo == "audiencias_catalogo_invalido"
    assert "@example.com" not in str(error.value)


@pytest.mark.parametrize(
    "campo",
    [
        "id",
        "nombre",
        "direccion",
        "categoria",
        "alcance_esperado",
        "usos_candidatos",
        "estado_aprobacion",
        "observacion",
    ],
)
def test_campo_obligatorio_ausente_falla_cerrado(tmp_path, campo):
    datos = _datos_catalogo()
    del datos["audiencias"][0][campo]

    with pytest.raises(ErrorAudiencias) as error:
        cargar_audiencias(_escribir_catalogo(tmp_path, datos))

    assert error.value.codigo == "audiencias_catalogo_invalido"


@pytest.mark.parametrize(
    "mutacion",
    [
        lambda datos: datos["audiencias"][0].update({"id": "alumnos_ingenieria"}),
        lambda datos: datos["audiencias"][0].update({"direccion": "sin-arroba"}),
        lambda datos: datos["audiencias"][0].update(
            {"direccion": "alumnosingenieria@example.com"}
        ),
        lambda datos: datos["audiencias"][0].update({"categoria": "otra"}),
        lambda datos: datos["audiencias"][0].update({"categoria": []}),
        lambda datos: datos["audiencias"][0].update({"estado_aprobacion": []}),
        lambda datos: datos["audiencias"][0].update({"alcance_esperado": "global"}),
        lambda datos: datos["audiencias"][0].update({"origen_uso": "INVENTADO"}),
        lambda datos: datos["audiencias"][0].update({"usos_candidatos": "texto"}),
        lambda datos: datos.update({"version": "otra_version"}),
        lambda datos: datos["fuente"].update({"total_grupos": 17}),
    ],
)
def test_catalogo_invalido_falla_cerrado_sin_filtrar_direcciones(tmp_path, mutacion):
    datos = _datos_catalogo()
    mutacion(datos)

    with pytest.raises(ErrorAudiencias) as error:
        cargar_audiencias(_escribir_catalogo(tmp_path, datos))

    assert error.value.codigo.startswith("audiencias_")
    assert "@example.com" not in str(error.value)


def test_archivo_inexistente_y_json_roto_fallan_cerrado(tmp_path):
    with pytest.raises(ErrorAudiencias) as error:
        cargar_audiencias(tmp_path / "no-existe.json")
    assert error.value.codigo == "audiencias_no_disponible"

    roto = tmp_path / "roto.json"
    roto.write_text("{no es json", encoding="utf-8")
    with pytest.raises(ErrorAudiencias) as error:
        cargar_audiencias(roto)
    assert error.value.codigo == "audiencias_json_invalido"


def test_audiencias_para_mapea_los_siete_tipos(tmp_path):
    catalogo = _catalogo(tmp_path)

    assert audiencias_para("cronica_de_evento", catalogo) == ("fieinforma",)
    assert audiencias_para("aviso_de_otra_area", catalogo) == ("fieinforma",)
    assert audiencias_para("saludo_o_efemeride", catalogo) == ("fieinforma",)
    assert audiencias_para("fallecimiento", catalogo) == ("comunidad",)
    assert audiencias_para("convocatoria_interna", catalogo) == (
        "docentes_ingenieria",
        "docentes_tecnicatura",
        "personal_gestion",
    )
    assert audiencias_para("newsletter", catalogo) == (
        "graduados_civiles",
        "graduados_oim",
        "alumnos_posgrados",
    )
    assert audiencias_para("difusion_de_actividad", catalogo) == ("fieinforma",)
    assert audiencias_para(
        "difusion_de_actividad", catalogo, es_de_carrera=True
    ) == ("fieinforma", "secretaria_academica")


def test_audiencias_para_rechaza_tipo_desconocido(tmp_path):
    catalogo = _catalogo(tmp_path)

    with pytest.raises(ErrorAudiencias) as error:
        audiencias_para("tipo_inventado", catalogo)

    assert error.value.codigo == "audiencias_tipo_desconocido"


def test_prellenado_no_filtra_por_aprobacion_y_devuelve_pendientes(tmp_path):
    datos = _datos_catalogo()
    for audiencia in datos["audiencias"]:
        if audiencia["id"] == "fieinforma":
            audiencia["estado_aprobacion"] = "APROBADA"
    catalogo = cargar_audiencias(_escribir_catalogo(tmp_path, datos))

    prellenado = construir_prellenado(
        "difusion_de_actividad",
        "Asunto",
        "Cuerpo",
        catalogo,
        seleccion=["fieinforma", "secretaria_academica"],
    )

    assert prellenado.destinatarios == (
        "fieinforma@example.com",
        "alumnos@example.com",
    )
    assert prellenado.audiencias_pendientes == ("secretaria_academica",)


def test_seleccion_desconocida_falla_cerrado(tmp_path):
    catalogo = _catalogo(tmp_path)

    with pytest.raises(ErrorAudiencias) as error:
        construir_prellenado(
            "newsletter", "Asunto", "Cuerpo", catalogo, seleccion=["no_existe"]
        )

    assert error.value.codigo == "audiencias_seleccion_invalida"


def test_ningun_archivo_de_src_contiene_el_dominio_institucional():
    for archivo in SRC.rglob("*"):
        if not archivo.is_file() or "__pycache__" in archivo.parts:
            continue
        assert b"@fie.undef.edu.ar" not in archivo.read_bytes(), archivo


def test_el_modulo_no_importa_gmail_envio_ni_red():
    arbol = ast.parse(MODULO.read_text(encoding="utf-8"))
    modulos: list[str] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.extend(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.append(nodo.module)

    assert not any("gmail_envio" in modulo for modulo in modulos)
    prohibidos = (
        "http.client",
        "socket",
        "requests",
        "urllib.request",
        "googleapiclient",
        "google",
    )
    assert not any(
        modulo == prohibido or modulo.startswith(prohibido + ".")
        for modulo in modulos
        for prohibido in prohibidos
    )


def test_el_prellenado_no_abre_sockets(tmp_path, monkeypatch):
    catalogo = _catalogo(tmp_path)

    def prohibido(*args, **kwargs):
        raise AssertionError("el prellenado no debe abrir sockets")

    monkeypatch.setattr(socket, "socket", prohibido)

    prellenado = construir_prellenado(
        "newsletter", "Asunto", "Cuerpo", catalogo
    )
    assert prellenado.url.startswith(BASE_COMPOSE)
