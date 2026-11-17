"""Siembra del lote de demostración desde la web (#168, ADR 0019).

Dos niveles, como el resto del canal web:

- El **camino web** se prueba por HTTP contra la app real con el
  repositorio de lotes en memoria: el botón sólo en modo demostración y
  para `APROBADOR_CONTENIDO`, el POST con CSRF, los rechazos fuera de
  demo, por rol ajeno o con la demo vencida, la idempotencia del doble
  clic y la marca «demostración — sin validez» en bandeja y página.
- La **semilla contra PostgreSQL real** se prueba con `crear_lote_demo`
  sobre `RepositorioLotes`: misma fila por `objeto_lote`, resembrar sin
  duplicar y la decisión conservada. Sin `AGENTE1_POSTGRES_DSN` ese
  bloque se saltea, igual que la persistencia del resto del canal.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from agente1 import lote_demo
from agente1.canal_form import PadronRoles, hash_correo
from agente1.certificados_emision import (
    PersonaCierre,
    hash_lista_cierre,
    objeto_lote_cierre,
)
from agente1.confirmaciones import ROL_APROBADOR_CONTENIDO
from agente1.decisiones_form import RegistroDecisiones
from agente1.linea_descriptiva import revisar_aprobacion_lote
from agente1.lote_demo import (
    ACTIVIDAD_DEMO,
    ID_LOTE_DEMO,
    actividad_demo,
    crear_lote_demo,
    es_lote_demo,
    personas_demo,
)
from agente1.web.app import CLIENT_ID_PRUEBA, ConfiguracionWeb, crear_app
from agente1.web.certificados_web import (
    ESTADO_APROBADA,
    ESTADO_DESCARTADA,
    ESTADO_PENDIENTE,
    LoteCertificados,
    RepositorioLotes,
    ResultadoDecisionLote,
)
from agente1.web.identidad import IdentidadVerificada, VerificadorFake
from agente1.web.sesiones import SesionesMemoria

CORREO_APROBADOR = "aprobador@example.invalid"
CORREO_OTRO_APROBADOR = "otra.persona@example.invalid"
CORREO_COORDINADOR = "coordinador@example.invalid"
TOKEN_APROBADOR = "tok-aprobador"
TOKEN_COORDINADOR = "tok-coordinador"
HOY_DEMO = date(2026, 11, 16)
DEMO_HASTA = date(2026, 11, 19)
AHORA = datetime(2026, 11, 17, 9, 0, tzinfo=timezone.utc)
MIGRACIONES = Path(__file__).resolve().parent.parent / "migrations"

ACTIVIDAD_ROW = {
    "id_actividad": "FIE-DIF-02",
    "titulo": (
        "Curso Inteligencia Artificial Aplicada a la Gestión "
        "Documental I - 3ª Edición"
    ),
    "duracion_horas": "",
    "modalidad": "online y autogestionado",
    "fecha_inicio": "2026-06-25",
    "fecha_fin": "2026-08-06",
    "organiza": "Facultad de Ingeniería del Ejército",
}


class RepositorioLotesMemoria:
    """El puerto del repositorio de lotes, en memoria, para la app.

    `crear` respeta el contrato idempotente del puerto: la fila se
    identifica por el objeto canónico (actividad + hash de la lista, las
    funciones reales del circuito) y un alta repetida devuelve la fila
    existente sin tocarla.
    """

    def __init__(self) -> None:
        self._lotes: dict[str, LoteCertificados] = {}
        self.llamadas_crear: list[dict[str, Any]] = []

    def listar(self) -> list[LoteCertificados]:
        return list(self._lotes.values())

    def obtener(self, id_lote: str) -> LoteCertificados | None:
        return self._lotes.get(id_lote)

    def crear(
        self,
        *,
        id_actividad: str,
        actividad: dict[str, str],
        personas: tuple[PersonaCierre, ...],
        linea_descriptiva: str,
        generada_por_hash: str,
        ahora: datetime | None = None,
    ) -> LoteCertificados:
        self.llamadas_crear.append(
            {
                "id_actividad": id_actividad,
                "generada_por_hash": generada_por_hash,
            }
        )
        objeto = objeto_lote_cierre(
            id_actividad, hash_lista_cierre(personas)
        )
        for lote in self._lotes.values():
            if lote.objeto_lote == objeto:
                return lote
        id_lote = f"lote-{objeto[:16]}"
        lote = LoteCertificados(
            id_lote=id_lote,
            id_actividad=id_actividad,
            objeto_lote=objeto,
            hash_lista=hash_lista_cierre(personas),
            actividad=dict(actividad),
            personas=personas,
            cantidad_personas=len(personas),
            linea_descriptiva=linea_descriptiva,
            linea_descriptiva_hash=hashlib.sha256(
                linea_descriptiva.encode("utf-8")
            ).hexdigest(),
            plantilla_muestra="certificado_seu_aprobacion_v1",
            estado=ESTADO_PENDIENTE,
            generada_por_hash=generada_por_hash,
            creada_en=ahora or AHORA,
        )
        self._lotes[id_lote] = lote
        return lote

    def decidir(
        self,
        *,
        id_lote: str,
        hash_lote: str,
        accion: str,
        validador_hash: str,
        rol: str,
        origen_identidad: str,
        version_agente: str,
        ahora: datetime | None = None,
    ) -> ResultadoDecisionLote:
        lote = self._lotes.get(id_lote)
        if lote is None:
            return ResultadoDecisionLote("inexistente")
        if lote.estado != ESTADO_PENDIENTE:
            return ResultadoDecisionLote("duplicada")
        if rol != ROL_APROBADOR_CONTENIDO:
            return ResultadoDecisionLote("aprobador_rol_no_autorizado")
        if hash_lote != lote.objeto_lote:
            return ResultadoDecisionLote("lote_obsoleto")
        if accion == "aprobar" and validador_hash != lote.generada_por_hash:
            return ResultadoDecisionLote("aprobador_no_es_generador")
        nuevo = replace(
            lote,
            estado=(
                ESTADO_APROBADA if accion == "aprobar" else ESTADO_DESCARTADA
            ),
            decidida_en=ahora or AHORA,
            decidida_por_hash=validador_hash,
            rol_decision=rol,
            origen_identidad=origen_identidad,
            version_agente=version_agente,
        )
        self._lotes[id_lote] = nuevo
        return ResultadoDecisionLote(
            "aprobada" if accion == "aprobar" else "descartada",
            id_lote=id_lote,
        )


class _RepositorioWebVacio:
    """Lo mínimo del repositorio de piezas para una bandeja vacía."""

    def bandeja(self) -> list:
        return []

    def obtener(self, id_solicitud: str):
        return None


@dataclass
class Mundo:
    client: TestClient
    lotes: RepositorioLotesMemoria
    sesiones: SesionesMemoria
    reloj: dict[str, date]


def _mundo(
    *,
    modo_demo: bool = True,
    actividades: list[dict[str, str]] | None = None,
    hoy: date = HOY_DEMO,
    registro_decisiones=None,
) -> Mundo:
    padron = PadronRoles(
        {
            CORREO_APROBADOR: ROL_APROBADOR_CONTENIDO,
            CORREO_OTRO_APROBADOR: ROL_APROBADOR_CONTENIDO,
            CORREO_COORDINADOR: "coordinador_seu",
        }
    )
    sesiones = SesionesMemoria()
    reloj = {"fecha": hoy}
    repo_lotes = RepositorioLotesMemoria()
    config = ConfiguracionWeb(
        google_client_id="" if modo_demo else CLIENT_ID_PRUEBA,
        modo_demo=modo_demo,
        modo_prueba=not modo_demo,
        demo_hasta=DEMO_HASTA if modo_demo else None,
        demo_correos=(
            (CORREO_APROBADOR, CORREO_OTRO_APROBADOR, CORREO_COORDINADOR)
            if modo_demo
            else ()
        ),
        cookie_secure=modo_demo,
    )
    app = crear_app(
        config=config,
        verificador=VerificadorFake(
            {
                TOKEN_APROBADOR: IdentidadVerificada(
                    "sub-aprobador", CORREO_APROBADOR, "x.invalid"
                ),
                TOKEN_COORDINADOR: IdentidadVerificada(
                    "sub-coordinador", CORREO_COORDINADOR, "x.invalid"
                ),
            }
        ),
        padron=padron,
        repositorio=_RepositorioWebVacio(),
        sesiones=sesiones,
        actividades=(
            [dict(ACTIVIDAD_ROW)] if actividades is None else actividades
        ),
        lotes=repo_lotes,
        hoy=lambda: reloj["fecha"],
        version_agente="0.8.1",
        registro_decisiones=registro_decisiones,
    )
    base_url = "https://testserver" if modo_demo else "http://testserver"
    return Mundo(
        TestClient(app, base_url=base_url), repo_lotes, sesiones, reloj
    )


def _csrf_login(client: TestClient) -> str:
    formulario = client.get("/ingresar")
    marca = 'name="csrf" value="'
    return formulario.text.split(marca, 1)[1].split('"', 1)[0]


def _ingresar_demo(client: TestClient, correo: str) -> None:
    respuesta = client.post(
        "/ingresar",
        data={"correo": correo, "csrf": _csrf_login(client)},
        follow_redirects=False,
    )
    assert respuesta.status_code == 303


def _ingresar_prueba(client: TestClient, token: str) -> None:
    respuesta = client.post(
        "/ingresar",
        data={"credential": token, "csrf": _csrf_login(client)},
        follow_redirects=False,
    )
    assert respuesta.status_code == 303


def _csrf(mundo: Mundo) -> str:
    return next(iter(mundo.sesiones._sesiones.values())).csrf_token


def _sembrar(client: TestClient, csrf: str, **kwargs):
    return client.post(
        "/demo/lote-certificados",
        data={"csrf": csrf, **kwargs},
        follow_redirects=False,
    )


def _aprobar(client: TestClient, mundo: Mundo, id_lote: str) -> None:
    lote = mundo.lotes.obtener(id_lote)
    respuesta = client.post(
        f"/certificados/{id_lote}/decidir",
        data={
            "csrf": _csrf(mundo),
            "hash_lote": lote.objeto_lote,
            "accion": "aprobar",
        },
    )
    assert respuesta.status_code == 200


# --- el botón y sus puertas ------------------------------------------------


def test_el_boton_solo_aparece_en_demo_para_el_aprobador() -> None:
    mundo = _mundo()
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    bandeja = mundo.client.get("/bandeja")
    assert 'action="/demo/lote-certificados"' in bandeja.text
    assert "Crear lote de demostración" in bandeja.text
    assert "sin validez institucional" in bandeja.text


def test_otro_rol_no_ve_el_boton_en_la_bandeja() -> None:
    mundo = _mundo()
    _ingresar_demo(mundo.client, CORREO_COORDINADOR)
    bandeja = mundo.client.get("/bandeja")
    assert "/demo/lote-certificados" not in bandeja.text
    assert "Lotes de certificados" not in bandeja.text


def test_fuera_de_demo_no_hay_boton_ni_ruta() -> None:
    mundo = _mundo(modo_demo=False)
    _ingresar_prueba(mundo.client, TOKEN_APROBADOR)
    bandeja = mundo.client.get("/bandeja")
    assert "/demo/lote-certificados" not in bandeja.text
    respuesta = _sembrar(mundo.client, csrf=_csrf(mundo))
    assert respuesta.status_code == 404
    assert mundo.lotes.listar() == []


def test_sembrar_sin_sesion_redirige_al_ingreso() -> None:
    mundo = _mundo()
    respuesta = _sembrar(mundo.client, csrf="cualquiera")
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/ingresar"


def test_sembrar_exige_csrf() -> None:
    mundo = _mundo()
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    respuesta = _sembrar(mundo.client, csrf="")
    assert respuesta.status_code == 403
    respuesta = _sembrar(mundo.client, csrf="token-inventado")
    assert respuesta.status_code == 403
    assert mundo.lotes.llamadas_crear == []
    assert mundo.lotes.listar() == []


def test_sembrar_niega_un_rol_que_no_es_aprobador() -> None:
    mundo = _mundo()
    _ingresar_demo(mundo.client, CORREO_COORDINADOR)
    respuesta = _sembrar(mundo.client, csrf=_csrf(mundo))
    assert respuesta.status_code == 403
    assert mundo.lotes.llamadas_crear == []
    assert mundo.lotes.listar() == []


def test_la_demo_vencida_niega_la_siembra() -> None:
    mundo = _mundo()
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    mundo.reloj["fecha"] = date(2026, 11, 20)  # pasó DEMO_HASTA
    respuesta = _sembrar(mundo.client, csrf=_csrf(mundo))
    assert respuesta.status_code == 503
    assert "demostración venció" in respuesta.text
    assert mundo.lotes.listar() == []


# --- siembra, marca y decisión ---------------------------------------------


def test_sembrar_crea_el_lote_y_redirige_a_su_pagina() -> None:
    mundo = _mundo()
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    respuesta = _sembrar(mundo.client, csrf=_csrf(mundo))
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == f"/certificados/{ID_LOTE_DEMO}"

    lote = mundo.lotes.obtener(ID_LOTE_DEMO)
    assert lote is not None
    assert lote.estado == ESTADO_PENDIENTE
    assert lote.cantidad_personas == 6
    assert lote.generada_por_hash == hash_correo(CORREO_APROBADOR)
    assert all(p.mail.endswith("@example.invalid") for p in lote.personas)

    pagina = mundo.client.get(respuesta.headers["location"])
    assert pagina.status_code == 200
    assert "FIE-DIF-02" in pagina.text
    assert "Persona Ficticia 1" in pagina.text
    assert "Lote de demostración" in pagina.text
    assert "sin validez institucional" in pagina.text


def test_la_bandeja_marca_el_lote_como_demostracion() -> None:
    mundo = _mundo()
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    _sembrar(mundo.client, csrf=_csrf(mundo))
    bandeja = mundo.client.get("/bandeja")
    assert f"/certificados/{ID_LOTE_DEMO}" in bandeja.text
    assert "demostración — sin validez" in bandeja.text


def test_el_lote_llega_a_la_decision_con_marca_demo() -> None:
    mundo = _mundo()
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    _sembrar(mundo.client, csrf=_csrf(mundo))
    _aprobar(mundo.client, mundo, ID_LOTE_DEMO)
    lote = mundo.lotes.obtener(ID_LOTE_DEMO)
    assert lote is not None
    assert lote.estado == ESTADO_APROBADA
    assert lote.decidida_por_hash == hash_correo(CORREO_APROBADOR)
    # La decisión de una sesión demo queda marcada como tal: nunca como
    # identidad verificada por Google (ADR 0019).
    assert lote.origen_identidad == "demo"
    assert lote.rol_decision == ROL_APROBADOR_CONTENIDO


def test_doble_click_no_duplica_el_lote() -> None:
    mundo = _mundo()
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    primero = _sembrar(mundo.client, csrf=_csrf(mundo))
    segundo = _sembrar(mundo.client, csrf=_csrf(mundo))
    assert primero.status_code == 303
    assert segundo.status_code == 303
    assert primero.headers["location"] == segundo.headers["location"]
    assert len(mundo.lotes.listar()) == 1


def test_resembrar_no_pierde_la_decision_aprobada() -> None:
    mundo = _mundo()
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    _sembrar(mundo.client, csrf=_csrf(mundo))
    _aprobar(mundo.client, mundo, ID_LOTE_DEMO)
    respuesta = _sembrar(mundo.client, csrf=_csrf(mundo))
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == f"/certificados/{ID_LOTE_DEMO}"
    lote = mundo.lotes.obtener(ID_LOTE_DEMO)
    assert lote is not None
    assert lote.estado == ESTADO_APROBADA
    assert lote.decidida_por_hash == hash_correo(CORREO_APROBADOR)
    assert len(mundo.lotes.listar()) == 1


def test_sembrar_no_asienta_nada_en_el_registro(tmp_path) -> None:
    registro = RegistroDecisiones(tmp_path)
    mundo = _mundo(registro_decisiones=registro)
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    _sembrar(mundo.client, csrf=_csrf(mundo))
    # Crear el lote no registra ninguna aprobación ni dispara salidas:
    # la aprobación sigue siendo una decisión humana aparte.
    assert registro.procesadas() == ()


def test_aprobar_el_demo_no_habilita_ningun_otro_lote(tmp_path) -> None:
    registro = RegistroDecisiones(tmp_path)
    mundo = _mundo(registro_decisiones=registro)
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    _sembrar(mundo.client, csrf=_csrf(mundo))
    _aprobar(mundo.client, mundo, ID_LOTE_DEMO)
    objeto_demo = lote_demo.OBJETO_LOTE_DEMO
    revision_demo = revisar_aprobacion_lote(
        registro,
        objeto_lote=objeto_demo,
        generada_por_correo_hash=hash_correo(CORREO_APROBADOR),
    )
    assert revision_demo.aprobada is True
    # La aprobación quedó atada al objeto de la lista ficticia: un lote
    # real, con otro objeto, sigue sin aprobación.
    objeto_real = objeto_lote_cierre("FIE-DIF-02", "ab" * 32)
    revision_real = revisar_aprobacion_lote(
        registro,
        objeto_lote=objeto_real,
        generada_por_correo_hash=hash_correo(CORREO_APROBADOR),
    )
    assert revision_real.aprobada is False


def test_sin_la_actividad_en_la_tabla_cae_al_corpus_del_repo() -> None:
    # Si la tabla montada no trae FIE-DIF-02 —p.ej. actividades.csv de
    # otra edición— la siembra usa los datasets del repo, igual que el
    # script de consola.
    mundo = _mundo(actividades=[])
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    respuesta = _sembrar(mundo.client, csrf=_csrf(mundo))
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == f"/certificados/{ID_LOTE_DEMO}"
    lote = mundo.lotes.obtener(ID_LOTE_DEMO)
    assert lote is not None
    assert lote.actividad["titulo"].startswith(
        "Curso Inteligencia Artificial"
    )


def test_sin_la_actividad_la_siembra_avisa(monkeypatch) -> None:
    mundo = _mundo(actividades=[])
    monkeypatch.setattr(lote_demo, "rutas_respaldo", lambda: ())
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    respuesta = _sembrar(mundo.client, csrf=_csrf(mundo))
    assert respuesta.status_code == 409
    assert "FIE-DIF-02" in respuesta.text
    assert "no está en la fuente" in respuesta.text
    assert mundo.lotes.listar() == []


# --- dominio compartido con el script de consola ----------------------------


SCRIPT_DEMO = (
    Path(__file__).parents[1] / "scripts" / "demo_lote_certificados.py"
)


def _script_demo():
    spec = importlib.util.spec_from_file_location(
        "demo_lote_certificados_test", SCRIPT_DEMO
    )
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_el_dominio_es_el_mismo_que_el_script() -> None:
    modulo = _script_demo()
    assert modulo.ACTIVIDAD_DEMO == ACTIVIDAD_DEMO
    assert modulo.personas_demo is personas_demo
    assert modulo.crear_lote_demo is crear_lote_demo


def test_la_marca_reconoce_el_lote_que_siembra_el_script() -> None:
    modulo = _script_demo()
    objeto_script = objeto_lote_cierre(
        modulo.ACTIVIDAD_DEMO,
        hash_lista_cierre(modulo.personas_demo()),
    )
    assert lote_demo.OBJETO_LOTE_DEMO == objeto_script
    assert ID_LOTE_DEMO == f"lote-{objeto_script[:16]}"
    mundo = _mundo()
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    _sembrar(mundo.client, csrf=_csrf(mundo))
    lote = mundo.lotes.obtener(ID_LOTE_DEMO)
    assert lote is not None
    assert es_lote_demo(lote) is True
    # Otro lote, con otra lista, no lleva la marca.
    otro = replace(lote, objeto_lote="0" * 64)
    assert es_lote_demo(otro) is False


def test_la_actividad_cae_a_los_datasets_del_repo() -> None:
    datos = actividad_demo([])
    assert datos["titulo"].startswith("Curso Inteligencia Artificial")
    assert datos["organiza"] == "Facultad de Ingeniería del Ejército"
    # La fila del corpus no declara la carga horaria: se completa con el
    # valor declarado de demo, igual que en el script.
    assert datos["duracion_horas"] == "24"


def test_sin_la_actividad_en_ningun_lado_el_error_es_declarado() -> None:
    from agente1.web.certificados_web import LoteCertificadosError

    with pytest.raises(LoteCertificadosError) as error:
        actividad_demo([], rutas=())
    assert error.value.code == "demo_actividad_ausente"


# --- PostgreSQL real --------------------------------------------------------

DSN = os.environ.get("AGENTE1_POSTGRES_DSN")
CLAVES_ROLES = {
    "agente1_app": "prueba-lote-app",
    "agente1_mantenimiento": "prueba-lote-mant",
}


@pytest.fixture()
def base_pg():
    if not DSN:
        pytest.skip("sin AGENTE1_POSTGRES_DSN (servicio de CI o base local)")
    esquema = f"test_lote_demo_{uuid.uuid4().hex[:10]}"
    admin = psycopg.connect(DSN, autocommit=True)
    admin.execute(f'CREATE SCHEMA "{esquema}"')
    try:
        with psycopg.connect(
            DSN, options=f"-c search_path={esquema}"
        ) as conn:
            for up in sorted(MIGRACIONES.glob("*.up.sql")):
                conn.execute(up.read_text(encoding="utf-8"))
            for rol, clave in CLAVES_ROLES.items():
                conn.execute(
                    f'GRANT USAGE ON SCHEMA "{esquema}" TO {rol}'
                )
                conn.execute(f"ALTER ROLE {rol} PASSWORD '{clave}'")
        yield esquema
    finally:
        admin.execute(f'DROP SCHEMA "{esquema}" CASCADE')
        admin.close()


def _repo(esquema: str) -> RepositorioLotes:
    info = psycopg.conninfo.conninfo_to_dict(DSN)
    info["user"] = "agente1_app"
    info["password"] = CLAVES_ROLES["agente1_app"]
    dsn = psycopg.conninfo.make_conninfo(**info)
    return RepositorioLotes(
        lambda: psycopg.connect(
            dsn, options=f"-c search_path={esquema}", autocommit=False
        )
    )


def _sembrar_en_base(
    repo: RepositorioLotes, correo: str
) -> LoteCertificados:
    return crear_lote_demo(
        repo,
        id_actividad=ACTIVIDAD_DEMO,
        actividad=actividad_demo([dict(ACTIVIDAD_ROW)]),
        personas=personas_demo(),
        generador_correo=correo,
    )


def test_la_siembra_web_es_idempotente_en_la_base(base_pg: str) -> None:
    repo = _repo(base_pg)
    primero = _sembrar_en_base(repo, CORREO_APROBADOR)
    segundo = _sembrar_en_base(repo, CORREO_APROBADOR)
    assert primero.id_lote == segundo.id_lote == ID_LOTE_DEMO
    assert primero.objeto_lote == segundo.objeto_lote
    assert len(repo.listar()) == 1
    lote = repo.obtener(primero.id_lote)
    assert lote is not None
    assert all(
        p.mail.endswith("@example.invalid") for p in lote.personas
    )
    assert lote.generada_por_hash == hash_correo(CORREO_APROBADOR)


def test_resembrar_conserva_la_decision_en_la_base(base_pg: str) -> None:
    repo = _repo(base_pg)
    lote = _sembrar_en_base(repo, CORREO_APROBADOR)
    decidido = repo.decidir(
        id_lote=lote.id_lote,
        hash_lote=lote.objeto_lote,
        accion="aprobar",
        validador_hash=hash_correo(CORREO_APROBADOR),
        rol=ROL_APROBADOR_CONTENIDO,
        origen_identidad="demo",
        version_agente="0.8.1",
    )
    assert decidido.codigo == "aprobada"
    # Reintentar la siembra —doble clic, otra sesión demo— devuelve la
    # misma fila sin tocar estado ni decisión.
    de_nuevo = _sembrar_en_base(repo, CORREO_OTRO_APROBADOR)
    assert de_nuevo.id_lote == lote.id_lote
    assert de_nuevo.estado == ESTADO_APROBADA
    assert de_nuevo.decidida_por_hash == hash_correo(CORREO_APROBADOR)
    persistido = repo.obtener(lote.id_lote)
    assert persistido is not None
    assert persistido.estado == ESTADO_APROBADA
    assert persistido.origen_identidad == "demo"
    assert len(repo.listar()) == 1
