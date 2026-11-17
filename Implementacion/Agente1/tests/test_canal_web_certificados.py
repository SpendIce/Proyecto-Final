"""Lote de certificados en la web del Agente 1 (#168, ADR 0018).

Dos niveles, como el resto del canal web:

- La **vista y la decisión** se prueban por HTTP contra la app real con el
  repositorio de lotes en memoria: la bandeja, la página del lote, la
  muestra descargable marcada borrador y los avisos de decisión.
- El **repositorio** se prueba contra PostgreSQL real: alta idempotente por
  hash de la lista, decisión con `SELECT … FOR UPDATE` que registra
  identidad, rol, origen y versión, y los rechazos por duplicada,
  obsoleta, rol ajeno o gestor distinto. Sin `AGENTE1_POSTGRES_DSN` ese
  bloque se saltea, igual que la persistencia del resto del canal.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from agente1.canal_form import PadronRoles, hash_correo
from agente1.certificados_emision import PersonaCierre
from agente1.confirmaciones import ROL_APROBADOR_CONTENIDO
from agente1.decisiones_form import (
    DECISION_APRUEBO_CONTENIDO,
    RESULTADO_REGISTRADA,
    TIPO_PLANTILLA,
    RegistroDecisiones,
    ResultadoDecision,
)
from agente1.linea_descriptiva import revisar_aprobacion_lote
from agente1.plantillas_aprobadas import PlantillaCorreo, id_version_plantilla
from agente1.web.app import CLIENT_ID_PRUEBA, ConfiguracionWeb, crear_app
from agente1.web.certificados_web import (
    ESTADO_APROBADA,
    ESTADO_DESCARTADA,
    ESTADO_PENDIENTE,
    LoteCertificados,
    RepositorioLotes,
    ResultadoDecisionLote,
    estado_firmas,
    estado_plantillas,
)
from agente1.web.identidad import IdentidadVerificada, VerificadorFake
from agente1.web.sesiones import SesionesMemoria

CORREO_APROBADOR = "aprobador@example.invalid"
CORREO_OTRO_APROBADOR = "otra.persona@example.invalid"
CORREO_COORDINADOR = "coordinador@example.invalid"
TOKEN_APROBADOR = "tok-aprobador"
TOKEN_COORDINADOR = "tok-coordinador"
AHORA = datetime(2026, 11, 17, 9, 0, tzinfo=timezone.utc)
MIGRACIONES = Path(__file__).resolve().parent.parent / "migrations"


def _personas() -> tuple[PersonaCierre, ...]:
    return (
        PersonaCierre(
            nombre="Persona Ficticia 1",
            apellido="Demo",
            dni="90000001",
            mail="persona.ficticia.1@example.invalid",
            tratamiento="Sr.",
            condicion="aprobacion",
        ),
        PersonaCierre(
            nombre="Persona Ficticia 2",
            apellido="Demo",
            dni="90000002",
            mail="persona.ficticia.2@example.invalid",
            tratamiento="Sra.",
            condicion="aprobacion",
        ),
    )


ACTIVIDAD = {
    "titulo": "Curso Inteligencia Artificial Aplicada a la Gestión Documental",
    "duracion_horas": "24",
    "modalidad": "online y autogestionado",
    "fecha_inicio": "2026-06-25",
    "fecha_fin": "2026-08-06",
    "organiza": "Facultad de Ingeniería del Ejército",
}
LINEA = (
    "Curso introductorio sobre herramientas de inteligencia artificial "
    "para organizar y analizar información institucional."
)


def _lote(
    *,
    id_lote: str = "lote-abc123",
    estado: str = ESTADO_PENDIENTE,
    generada_por: str = CORREO_APROBADOR,
) -> LoteCertificados:
    personas = _personas()
    return LoteCertificados(
        id_lote=id_lote,
        id_actividad="FIE-DIF-02",
        objeto_lote="f" * 64,
        hash_lista="e" * 64,
        actividad=dict(ACTIVIDAD),
        personas=personas,
        cantidad_personas=len(personas),
        linea_descriptiva=LINEA,
        linea_descriptiva_hash=hashlib.sha256(
            LINEA.encode("utf-8")
        ).hexdigest(),
        plantilla_muestra="certificado_seu_aprobacion_v1",
        estado=estado,
        generada_por_hash=hash_correo(generada_por),
        creada_en=AHORA,
        decidida_en=None,
        decidida_por_hash=None,
        rol_decision=None,
        origen_identidad=None,
        version_agente=None,
    )


class RepositorioLotesMemoria:
    """El puerto del repositorio de lotes, en memoria, para la app."""

    def __init__(self, lotes: tuple[LoteCertificados, ...] | None = None) -> None:
        self._lotes = {lote.id_lote: lote for lote in (lotes or ())}
        self.llamadas: list[dict[str, Any]] = []
        self.codigo = "aprobada"

    def listar(self) -> list[LoteCertificados]:
        return list(self._lotes.values())

    def obtener(self, id_lote: str) -> LoteCertificados | None:
        return self._lotes.get(id_lote)

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
        self.llamadas.append(
            {
                "id_lote": id_lote,
                "hash_lote": hash_lote,
                "accion": accion,
                "validador_hash": validador_hash,
                "rol": rol,
                "origen_identidad": origen_identidad,
                "version_agente": version_agente,
            }
        )
        lote = self._lotes.get(id_lote)
        if lote is None:
            return ResultadoDecisionLote("inexistente")
        if lote.estado != ESTADO_PENDIENTE:
            return ResultadoDecisionLote("duplicada")
        if self.codigo not in ("aprobada", "descartada"):
            return ResultadoDecisionLote(self.codigo)
        nuevo = replace(
            lote,
            estado=(
                ESTADO_APROBADA
                if self.codigo == "aprobada"
                else ESTADO_DESCARTADA
            ),
            decidida_en=AHORA,
            decidida_por_hash=validador_hash,
            rol_decision=rol,
            origen_identidad=origen_identidad,
            version_agente=version_agente,
        )
        self._lotes[id_lote] = nuevo
        return ResultadoDecisionLote(self.codigo, id_lote=id_lote)


@dataclass
class Mundo:
    client: TestClient
    lotes: RepositorioLotesMemoria
    sesiones: SesionesMemoria


def _mundo(
    lotes: tuple[LoteCertificados, ...] | None = None,
    *,
    registro_decisiones=None,
    plantillas_aprobadas=None,
) -> Mundo:
    padron = PadronRoles(
        {
            CORREO_APROBADOR: ROL_APROBADOR_CONTENIDO,
            CORREO_OTRO_APROBADOR: ROL_APROBADOR_CONTENIDO,
            CORREO_COORDINADOR: "coordinador_seu",
        }
    )
    sesiones = SesionesMemoria(ahora=lambda: AHORA)
    verificador = VerificadorFake(
        {
            TOKEN_APROBADOR: IdentidadVerificada(
                "sub-aprobador", CORREO_APROBADOR, "x.invalid"
            ),
            TOKEN_COORDINADOR: IdentidadVerificada(
                "sub-coordinador", CORREO_COORDINADOR, "x.invalid"
            ),
        }
    )
    repo_lotes = RepositorioLotesMemoria(lotes)
    app = crear_app(
        config=ConfiguracionWeb(
            google_client_id=CLIENT_ID_PRUEBA,
            modo_prueba=True,
            cookie_secure=False,
        ),
        verificador=verificador,
        padron=padron,
        repositorio=_RepositorioWebVacio(),
        sesiones=sesiones,
        actividades=[],
        lotes=repo_lotes,
        version_agente="0.6.3",
        registro_decisiones=registro_decisiones,
        plantillas_aprobadas=plantillas_aprobadas,
    )
    return Mundo(TestClient(app), repo_lotes, sesiones)


class _RepositorioWebVacio:
    """Lo mínimo del repositorio de piezas para una bandeja vacía."""

    def bandeja(self) -> list:
        return []

    def obtener(self, id_solicitud: str):
        return None


def _ingresar(client: TestClient, token: str = TOKEN_APROBADOR) -> None:
    formulario = client.get("/ingresar")
    marca = 'name="csrf" value="'
    csrf = formulario.text.split(marca, 1)[1].split('"', 1)[0]
    respuesta = client.post(
        "/ingresar",
        data={"credential": token, "csrf": csrf},
        follow_redirects=False,
    )
    assert respuesta.status_code == 303


def _csrf(mundo: Mundo) -> str:
    return next(iter(mundo.sesiones._sesiones.values())).csrf_token


# --- vista del lote -------------------------------------------------------


def test_bandeja_muestra_la_seccion_de_lotes() -> None:
    mundo = _mundo((_lote(),))
    _ingresar(mundo.client)
    respuesta = mundo.client.get("/bandeja")
    assert respuesta.status_code == 200
    assert "Lotes de certificados" in respuesta.text
    assert "Curso Inteligencia Artificial" in respuesta.text
    assert "/certificados/lote-abc123" in respuesta.text


def test_pagina_del_lote_muestra_actividad_lista_hash_y_plantilla() -> None:
    mundo = _mundo((_lote(),))
    _ingresar(mundo.client)
    respuesta = mundo.client.get("/certificados/lote-abc123")
    assert respuesta.status_code == 200
    cuerpo = respuesta.text
    assert "FIE-DIF-02" in cuerpo
    assert "Persona Ficticia 1" in cuerpo
    assert "aprobacion" in cuerpo
    assert "2" in cuerpo  # cantidad de personas
    assert "f" * 64 in cuerpo  # hash del lote
    assert "certificado_seu_aprobacion_v1" in cuerpo
    assert "BORRADOR" in cuerpo
    assert "Firmas disponibles" in cuerpo


def test_descarga_de_la_muestra_es_pdf_borrador() -> None:
    mundo = _mundo((_lote(),))
    _ingresar(mundo.client)
    respuesta = mundo.client.get("/certificados/lote-abc123/muestra.pdf")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("application/pdf")
    assert "attachment" in respuesta.headers["content-disposition"]
    assert respuesta.content.startswith(b"%PDF")
    assert b"BORRADOR" in respuesta.content
    assert b"NO EMITIR" in respuesta.content
    assert b"Persona Ficticia 1" in respuesta.content


def test_lote_inexistente_da_404() -> None:
    mundo = _mundo(())
    _ingresar(mundo.client)
    assert mundo.client.get("/certificados/lote-nada").status_code == 404


def test_pagina_del_lote_requiere_sesion() -> None:
    mundo = _mundo((_lote(),))
    respuesta = mundo.client.get(
        "/certificados/lote-abc123", follow_redirects=False
    )
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/ingresar"


# --- decisión -------------------------------------------------------------


def test_aprobar_exige_csrf() -> None:
    mundo = _mundo((_lote(),))
    _ingresar(mundo.client)
    respuesta = mundo.client.post(
        "/certificados/lote-abc123/decidir",
        data={"hash_lote": "f" * 64, "accion": "aprobar"},
        follow_redirects=False,
    )
    assert respuesta.status_code == 403
    assert mundo.lotes.llamadas == []


def test_aprobar_ata_la_decision_al_hash_y_a_la_identidad() -> None:
    mundo = _mundo((_lote(),))
    _ingresar(mundo.client)
    respuesta = mundo.client.post(
        "/certificados/lote-abc123/decidir",
        data={
            "csrf": _csrf(mundo),
            "hash_lote": "f" * 64,
            "accion": "aprobar",
        },
    )
    assert respuesta.status_code == 200
    assert "Lote aprobado" in respuesta.text
    llamada = mundo.lotes.llamadas[-1]
    assert llamada["hash_lote"] == "f" * 64
    assert llamada["rol"] == ROL_APROBADOR_CONTENIDO
    assert llamada["validador_hash"] == hashlib.sha256(
        CORREO_APROBADOR.encode("utf-8")
    ).hexdigest()
    assert llamada["origen_identidad"] == "google"
    assert llamada["version_agente"] == "0.6.3"


def test_aprobar_sin_firmas_avisa_que_no_se_emite() -> None:
    mundo = _mundo((_lote(),))
    _ingresar(mundo.client)
    respuesta = mundo.client.post(
        "/certificados/lote-abc123/decidir",
        data={
            "csrf": _csrf(mundo),
            "hash_lote": "f" * 64,
            "accion": "aprobar",
        },
    )
    assert respuesta.status_code == 200
    assert "Lote aprobado. No se emite: faltan firmas (R2)." in respuesta.text


def test_descartar_el_lote_cierra_sin_emision() -> None:
    mundo = _mundo((_lote(),))
    mundo.lotes.codigo = "descartada"
    _ingresar(mundo.client)
    respuesta = mundo.client.post(
        "/certificados/lote-abc123/decidir",
        data={
            "csrf": _csrf(mundo),
            "hash_lote": "f" * 64,
            "accion": "descartar",
        },
    )
    assert respuesta.status_code == 200
    assert "Lote descartado" in respuesta.text
    assert mundo.lotes.llamadas[-1]["accion"] == "descartar"


@pytest.mark.parametrize(
    ("codigo", "mensaje"),
    [
        ("duplicada", "La decisión ya estaba registrada"),
        ("lote_obsoleto", "El hash del lote no coincide"),
        ("aprobador_no_es_generador", "lo aprueba quien lo generó"),
        ("aprobador_rol_no_autorizado", "rol no habilita"),
    ],
)
def test_rechazos_de_decision_muestran_su_mensaje(
    codigo: str, mensaje: str
) -> None:
    mundo = _mundo((_lote(),))
    mundo.lotes.codigo = codigo
    _ingresar(mundo.client)
    respuesta = mundo.client.post(
        "/certificados/lote-abc123/decidir",
        data={
            "csrf": _csrf(mundo),
            "hash_lote": "f" * 64,
            "accion": "aprobar",
        },
    )
    assert respuesta.status_code == 200
    assert mensaje in respuesta.text


# --- repositorio PostgreSQL ----------------------------------------------


DSN = os.environ.get("AGENTE1_POSTGRES_DSN")
CLAVES_ROLES = {
    "agente1_app": "prueba-lote-app",
    "agente1_mantenimiento": "prueba-lote-mant",
}


@pytest.fixture()
def base_pg():
    if not DSN:
        pytest.skip("sin AGENTE1_POSTGRES_DSN (servicio de CI o base local)")
    esquema = f"test_lote_{uuid.uuid4().hex[:10]}"
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


def _repo(
    esquema: str, rol: str = "agente1_app"
) -> RepositorioLotes:
    info = psycopg.conninfo.conninfo_to_dict(DSN)
    info["user"] = rol
    info["password"] = CLAVES_ROLES[rol]
    dsn = psycopg.conninfo.make_conninfo(**info)
    return RepositorioLotes(
        lambda: psycopg.connect(
            dsn, options=f"-c search_path={esquema}", autocommit=False
        )
    )


def _crear(repo: RepositorioLotes) -> LoteCertificados:
    return repo.crear(
        id_actividad="FIE-DIF-02",
        actividad=dict(ACTIVIDAD),
        personas=_personas(),
        linea_descriptiva=LINEA,
        generada_por_hash=hash_correo(CORREO_APROBADOR),
    )


def _decidir(repo: RepositorioLotes, lote: LoteCertificados, **cambios):
    datos = {
        "id_lote": lote.id_lote,
        "hash_lote": lote.objeto_lote,
        "accion": "aprobar",
        "validador_hash": hash_correo(CORREO_APROBADOR),
        "rol": ROL_APROBADOR_CONTENIDO,
        "origen_identidad": "demo",
        "version_agente": "0.6.3",
    }
    datos.update(cambios)
    return repo.decidir(**datos)


def test_crear_lote_es_idempotente_por_hash_de_lista(base_pg: str) -> None:
    repo = _repo(base_pg)
    primero = _crear(repo)
    segundo = _crear(repo)
    assert primero.id_lote == segundo.id_lote
    assert primero.objeto_lote == segundo.objeto_lote
    assert primero.cantidad_personas == 2
    assert len(repo.listar()) == 1

    otras = list(_personas())
    otras[0] = replace(otras[0], condicion="asistencia")
    distinto = repo.crear(
        id_actividad="FIE-DIF-02",
        actividad=dict(ACTIVIDAD),
        personas=tuple(otras),
        linea_descriptiva=LINEA,
        generada_por_hash=hash_correo(CORREO_APROBADOR),
    )
    assert distinto.id_lote != primero.id_lote
    assert distinto.objeto_lote != primero.objeto_lote
    assert len(repo.listar()) == 2


def test_decidir_registra_identidad_rol_origen_y_version(
    base_pg: str,
) -> None:
    repo = _repo(base_pg)
    lote = _crear(repo)
    resultado = _decidir(repo, lote)
    assert resultado.codigo == "aprobada"
    decidido = repo.obtener(lote.id_lote)
    assert decidido is not None
    assert decidido.estado == ESTADO_APROBADA
    assert decidido.decidida_por_hash == hash_correo(CORREO_APROBADOR)
    assert decidido.rol_decision == ROL_APROBADOR_CONTENIDO
    assert decidido.origen_identidad == "demo"
    assert decidido.version_agente == "0.6.3"
    assert decidido.decidida_en is not None


def test_decidir_duplicada_rechaza_la_segunda(base_pg: str) -> None:
    repo = _repo(base_pg)
    lote = _crear(repo)
    assert _decidir(repo, lote).codigo == "aprobada"
    assert _decidir(repo, lote).codigo == "duplicada"
    assert repo.obtener(lote.id_lote).estado == ESTADO_APROBADA


def test_decidir_hash_obsoleto_no_toca_el_lote(base_pg: str) -> None:
    repo = _repo(base_pg)
    lote = _crear(repo)
    resultado = _decidir(repo, lote, hash_lote="0" * 64)
    assert resultado.codigo == "lote_obsoleto"
    assert repo.obtener(lote.id_lote).estado == ESTADO_PENDIENTE


def test_aprobar_lo_hace_quien_genero_el_lote(base_pg: str) -> None:
    repo = _repo(base_pg)
    lote = _crear(repo)
    resultado = _decidir(
        repo, lote, validador_hash=hash_correo(CORREO_OTRO_APROBADOR)
    )
    assert resultado.codigo == "aprobador_no_es_generador"
    assert repo.obtener(lote.id_lote).estado == ESTADO_PENDIENTE


def test_un_rol_ajeno_no_habilita_la_decision(base_pg: str) -> None:
    repo = _repo(base_pg)
    lote = _crear(repo)
    resultado = _decidir(repo, lote, rol="coordinador_seu")
    assert resultado.codigo == "aprobador_rol_no_autorizado"
    assert repo.obtener(lote.id_lote).estado == ESTADO_PENDIENTE


def test_descartar_no_exige_ser_el_generador(base_pg: str) -> None:
    repo = _repo(base_pg)
    lote = _crear(repo)
    resultado = _decidir(
        repo,
        lote,
        accion="descartar",
        validador_hash=hash_correo(CORREO_OTRO_APROBADOR),
    )
    assert resultado.codigo == "descartada"
    assert repo.obtener(lote.id_lote).estado == ESTADO_DESCARTADA


def test_decidir_un_lote_inexistente_no_crea_nada(base_pg: str) -> None:
    repo = _repo(base_pg)
    resultado = repo.decidir(
        id_lote="lote-nada",
        hash_lote="0" * 64,
        accion="aprobar",
        validador_hash=hash_correo(CORREO_APROBADOR),
        rol=ROL_APROBADOR_CONTENIDO,
        origen_identidad="demo",
        version_agente="0.6.3",
    )
    assert resultado.codigo == "inexistente"


def test_la_purga_retira_la_lista_y_conserva_hash_y_decision(
    base_pg: str,
) -> None:
    repo = _repo(base_pg)
    lote = _crear(repo)
    _decidir(repo, lote)
    mantenimiento = _repo(base_pg, rol="agente1_mantenimiento")
    assert mantenimiento.purgar_cerrados() == 1
    purgado = repo.obtener(lote.id_lote)
    assert purgado is not None
    assert purgado.personas == ()
    assert purgado.linea_descriptiva is None
    assert purgado.linea_descriptiva_hash == lote.linea_descriptiva_hash
    assert purgado.cantidad_personas == 2
    assert purgado.objeto_lote == lote.objeto_lote
    assert purgado.decidida_por_hash == hash_correo(CORREO_APROBADOR)
    assert mantenimiento.purgar_cerrados() == 0


# --- script de demo -------------------------------------------------------


SCRIPT_DEMO = Path(__file__).parents[1] / "scripts" / "demo_lote_certificados.py"


def _script_demo():
    spec = importlib.util.spec_from_file_location(
        "demo_lote_certificados_test", SCRIPT_DEMO
    )
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_la_demo_usa_personas_ficticias_sin_correos_reales() -> None:
    modulo = _script_demo()
    personas = modulo.personas_demo(6)
    assert len(personas) == 6
    assert all("Persona Ficticia" in p.nombre for p in personas)
    assert all(p.mail.endswith("@example.invalid") for p in personas)
    assert all(p.condicion == "aprobacion" for p in personas)
    assert len({p.dni for p in personas}) == 6


def test_la_demo_encuentra_la_actividad_del_corpus() -> None:
    modulo = _script_demo()
    datos, origen, horas_demo = modulo._cargar_actividad(
        "FIE-DIF-02", [modulo.CORPUS_ACTIVIDADES]
    )
    assert datos["titulo"].startswith("Curso Inteligencia Artificial")
    assert datos["duracion_horas"] == "24"
    assert datos["organiza"] == "Facultad de Ingeniería del Ejército"
    assert origen.endswith("corpus-fie-informa-difusiones.csv")
    assert horas_demo is True


def test_la_demo_no_corre_sin_dsn(capsys) -> None:
    modulo = _script_demo()
    assert modulo.main([], environ={}) == 2
    salida = json.loads(capsys.readouterr().out)
    assert salida == {"status": "INVALID", "error_code": "demo_dsn_ausente"}


def test_la_demo_rechaza_una_cantidad_fuera_del_rango(capsys) -> None:
    modulo = _script_demo()
    codigo = modulo.main(
        ["--dsn", "postgresql://x/y", "--cantidad", "3"],
        environ={"AGENTE1_WEB_DEMO_CORREOS": CORREO_APROBADOR},
    )
    assert codigo == 2
    salida = json.loads(capsys.readouterr().out)
    assert salida["error_code"] == "demo_cantidad_invalida"


def test_aprobar_web_asienta_el_apruebo_lote_en_el_registro(tmp_path) -> None:
    registro = RegistroDecisiones(tmp_path)
    mundo = _mundo((_lote(),), registro_decisiones=registro)
    _ingresar(mundo.client)
    respuesta = mundo.client.post(
        "/certificados/lote-abc123/decidir",
        data={
            "csrf": _csrf(mundo),
            "hash_lote": "f" * 64,
            "accion": "aprobar",
        },
    )
    assert respuesta.status_code == 200
    revision = revisar_aprobacion_lote(
        registro,
        objeto_lote="f" * 64,
        generada_por_correo_hash=hash_correo(CORREO_APROBADOR),
    )
    assert revision.aprobada is True


def test_la_asistencia_no_exige_imagenes_de_firma() -> None:
    assert estado_firmas(None, ("asistencia",)).disponible is True
    assert estado_firmas(None, ("aprobacion",)).disponible is False


def test_plantilla_de_asistencia_con_aprobacion_registrada(tmp_path) -> None:
    plantilla = PlantillaCorreo(
        asunto="Certificado de {{nombre}}",
        cuerpo="Certificamos que {{nombre}} {{apellido}}.\n{{bloque_firmas}}",
    )
    registro = RegistroDecisiones(tmp_path)
    marca = AHORA.isoformat()
    registro.registrar(
        ResultadoDecision(
            id_respuesta=hashlib.sha256(b"plantilla-asistencia").hexdigest(),
            correo_hash=hash_correo(CORREO_APROBADOR),
            rol=ROL_APROBADOR_CONTENIDO,
            rol_origen="padron",
            tipo=TIPO_PLANTILLA,
            objeto_id=id_version_plantilla(
                "certificado_asistencia", plantilla
            ),
            decision=DECISION_APRUEBO_CONTENIDO,
            resultado=RESULTADO_REGISTRADA,
            rechazo_codigo=None,
            marca_temporal_form=marca,
            timestamp=marca,
        )
    )
    estados = estado_plantillas(
        ("asistencia",),
        plantillas_aprobadas={"certificado_asistencia": plantilla},
        registro_decisiones=registro,
    )
    assert len(estados) == 1
    assert estados[0].aprobada is True
    assert estados[0].nombre == id_version_plantilla(
        "certificado_asistencia", plantilla
    )


def test_otro_rol_no_ve_ni_decide_el_lote() -> None:
    mundo = _mundo((_lote(),))
    _ingresar(mundo.client, TOKEN_COORDINADOR)
    assert (
        mundo.client.get("/certificados/lote-abc123").status_code == 403
    )
    respuesta = mundo.client.post(
        "/certificados/lote-abc123/decidir",
        data={"csrf": _csrf(mundo), "hash_lote": "f" * 64, "accion": "aprobar"},
    )
    assert respuesta.status_code == 403
    assert mundo.lotes.llamadas == []
    assert "Lotes de certificados" not in mundo.client.get("/bandeja").text
