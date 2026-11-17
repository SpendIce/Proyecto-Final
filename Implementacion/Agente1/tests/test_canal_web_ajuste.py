"""Ajuste generativo sobre la revisión vigente del canal web.

Tres capas, como el resto de la suite del canal:

- La generación: el prompt versionado recibe el texto base y la indicación,
  y la salida pasa por la marca y el gate de la pieza.
- La persistencia contra PostgreSQL real: el ajuste encola una ejecución
  propia, crea una revisión nueva con base declarada y deja obsoleta la
  decisión sobre la revisión anterior.
- El worker con generador y destino falsos: éxito, salida vacía y fallo
  del Doc; y la app con el repositorio real y `DocsCanalMemoria`, para el
  formulario, los permisos, el CSRF, la idempotencia y el estado
  «Ajustando…».
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from agente1.canal_form import PadronRoles
from agente1.destinos import BORRADOR_MARKER, DestinoBorradoresError
from agente1.gacetillas import renderizar
from agente1.presupuesto import PresupuestoAgotadoError
from agente1.procesamiento import FakeGenerator
from agente1.web.ajuste import (
    ajustar_texto,
    construir_prompt_ajuste,
)
from agente1.web.app import CLIENT_ID_PRUEBA, ConfiguracionWeb, crear_app
from agente1.web.docs_canal import DocsCanalMemoria
from agente1.web.identidad import IdentidadVerificada, VerificadorFake
from agente1.web.persistencia import (
    ConflictoIdempotencia,
    RepositorioWeb,
    TrabajoWeb,
)
from agente1.web.sesiones import SesionesMemoria
from agente1.web.worker import DestinoPorMarcaMemoria, correr_una_vez

DSN = os.environ.get("AGENTE1_POSTGRES_DSN")
MIGRACIONES = Path(__file__).resolve().parent.parent / "migrations"
AHORA = datetime.now(timezone.utc)

CORREO_SEU = "solicitante@example.invalid"
CORREO_LECTOR = "lector@example.invalid"
CORREO_APROBADOR = "aprobador@example.invalid"

CAMPOS = {
    "titulo": "Jornada sintética de extensión",
    "cuerpo": "La jornada reunió a estudiantes y docentes en la facultad.",
}
TEXTO_VALIDO = (
    BORRADOR_MARKER + renderizar("cronica_de_evento", CAMPOS) + "\n"
)

CAMPOS_SIETE_TIPOS = {
    "difusion_de_actividad": {
        "titulo": "Curso sintético de extensión",
        "bajada": "La Secretaría de Extensión Universitaria abre la inscripción.",
        "cuerpo": "La actividad se dicta en la sede de la facultad.",
        "fecha_inicio": "2026-11-20",
        "contacto": "extension@example.invalid",
    },
    "cronica_de_evento": dict(CAMPOS),
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
        "convocatoria": "la convocatoria interna de tutores",
        "requisitos": "tener dos años de antigüedad",
        "fecha_limite": "2026-11-15",
        "area_emisora": "Secretaría Académica",
        "contacto": "doe@example.invalid",
    },
    "saludo_o_efemeride": {
        "titulo": "Día del Ingeniero",
        "cuerpo": "Saludamos a quienes ejercen la profesión con compromiso.",
    },
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


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


# ====================== generación y prompt ======================


def test_el_prompt_lleva_el_texto_base_y_la_indicacion() -> None:
    prompt = construir_prompt_ajuste(
        texto_base="Documento de prueba.",
        indicacion="más breve",
    )
    assert "Documento de prueba." in prompt
    assert "más breve" in prompt
    assert "BORRADOR — NO PUBLICAR" in prompt
    assert "no inventes" in prompt.lower()


def test_el_texto_base_no_se_reinterpreta_como_marcador() -> None:
    prompt = construir_prompt_ajuste(
        texto_base="Documento con {indicacion} literal.",
        indicacion="más breve",
    )
    assert "Documento con {indicacion} literal." in prompt


def test_ajuste_valido_conserva_la_marca_y_pasa_el_gate() -> None:
    cuerpo_ajustado = "La jornada reunió a estudiantes y docentes."
    salida = (
        BORRADOR_MARKER
        + renderizar(
            "cronica_de_evento", {**CAMPOS, "cuerpo": cuerpo_ajustado}
        )
        + "\n"
    )

    texto, errores = ajustar_texto(
        texto_base=TEXTO_VALIDO,
        indicacion="más breve",
        tipo="cronica_de_evento",
        campos=CAMPOS,
        generator=FakeGenerator(salida),
    )

    assert errores == []
    assert texto.startswith(BORRADOR_MARKER)
    assert cuerpo_ajustado in texto


@pytest.mark.parametrize("tipo", CAMPOS_SIETE_TIPOS)
def test_el_ajuste_sigue_sirviendo_para_los_siete_tipos(tipo: str) -> None:
    """La normalización y el gate no pierden ninguno de los siete tipos."""
    campos = CAMPOS_SIETE_TIPOS[tipo]
    base = BORRADOR_MARKER + renderizar(tipo, campos) + "\n"

    texto, errores = ajustar_texto(
        texto_base=base,
        indicacion="tono más formal",
        tipo=tipo,
        campos=campos,
        generator=FakeGenerator(base),
    )

    assert errores == [], (tipo, errores)
    assert texto.startswith(BORRADOR_MARKER)
    assert "Asunto:" in texto


def test_la_base_con_correccion_humana_del_titulo_pasa_el_gate() -> None:
    """Si la persona corrigió el título en el Doc, el ajuste parte de esa
    corrección y el gate no le exige el título viejo del pedido."""
    titulo_corregido = "Jornada de extensión (título corregido a mano)"
    base_corregida = (
        BORRADOR_MARKER
        + renderizar(
            "cronica_de_evento",
            {**CAMPOS, "titulo": titulo_corregido},
        )
        + "\n"
    )
    salida = (
        BORRADOR_MARKER
        + renderizar(
            "cronica_de_evento",
            {
                **CAMPOS,
                "titulo": titulo_corregido,
                "cuerpo": "La jornada reunió a estudiantes y docentes.",
            },
        )
        + "\n"
    )

    texto, errores = ajustar_texto(
        texto_base=base_corregida,
        indicacion="más breve",
        tipo="cronica_de_evento",
        campos=CAMPOS,
        generator=FakeGenerator(salida),
    )

    assert errores == []
    assert titulo_corregido in texto


def test_el_asunto_de_la_base_no_lo_reescribe_el_modelo() -> None:
    """El asunto es fijo de la forma: aunque el modelo lo cambie, se repone
    el de la base para que el Doc no pierda el título confirmado."""
    salida = _texto_ajustado("La jornada reunió a la comunidad.")
    lineas = salida.splitlines()
    indice = next(
        posicion
        for posicion, linea in enumerate(lineas)
        if linea.startswith("Asunto:")
    )
    lineas[indice] = "Asunto: Jornada sintética de extensión — reescrito"
    texto, errores = ajustar_texto(
        texto_base=TEXTO_VALIDO,
        indicacion="más breve",
        tipo="cronica_de_evento",
        campos=CAMPOS,
        generator=FakeGenerator("\n".join(lineas)),
    )

    assert errores == []
    assert texto.count("Asunto:") == 1
    assert "Asunto: Jornada sintética de extensión\n" in texto
    assert "— reescrito" not in texto


def test_la_marca_repetida_no_se_duplica() -> None:
    salida = (
        "# BORRADOR — NO PUBLICAR\n"
        + renderizar("cronica_de_evento", {
            **CAMPOS, "cuerpo": "La jornada reunió a estudiantes."
        })
        + "\n"
    )

    texto, errores = ajustar_texto(
        texto_base=TEXTO_VALIDO,
        indicacion="más breve",
        tipo="cronica_de_evento",
        campos=CAMPOS,
        generator=FakeGenerator(salida),
    )

    assert errores == []
    assert texto.count("BORRADOR — NO PUBLICAR") == 1
    assert texto.startswith(BORRADOR_MARKER)


def test_salida_vacia_no_produce_pieza() -> None:
    texto, errores = ajustar_texto(
        texto_base=TEXTO_VALIDO,
        indicacion="más breve",
        tipo="cronica_de_evento",
        campos=CAMPOS,
        generator=FakeGenerator("   "),
    )
    assert texto == ""
    assert errores == ["salida_vacia"]


def test_salida_que_pierde_los_hechos_falla_el_gate() -> None:
    texto, errores = ajustar_texto(
        texto_base=TEXTO_VALIDO,
        indicacion="resumí",
        tipo="cronica_de_evento",
        campos=CAMPOS,
        generator=FakeGenerator(
            BORRADOR_MARKER + "Un texto genérico sin los datos.\n"
        ),
    )
    assert texto == ""
    assert "hecho_perdido" in errores


# ====================== persistencia PostgreSQL ======================


@pytest.fixture()
def base():
    """Esquema desechable con todas las migraciones y un repositorio real."""
    if not DSN:
        pytest.skip("sin AGENTE1_POSTGRES_DSN (servicio de CI o base local)")
    esquema = f"test_ajuste_{uuid.uuid4().hex[:10]}"
    admin = psycopg.connect(DSN, autocommit=True)
    admin.execute(f'CREATE SCHEMA "{esquema}"')
    try:
        with psycopg.connect(
            DSN, options=f"-c search_path={esquema}"
        ) as conn:
            for up in sorted(MIGRACIONES.glob("*.up.sql")):
                conn.execute(up.read_text(encoding="utf-8"))
        yield esquema
    finally:
        admin.execute(f'DROP SCHEMA "{esquema}" CASCADE')
        admin.close()


def _fabrica(esquema: str):
    return lambda: psycopg.connect(
        DSN, options=f"-c search_path={esquema}", autocommit=False
    )


def _solicitud_en_lista(
    repo: RepositorioWeb,
    docs: DocsCanalMemoria | None = None,
    *,
    texto: str = TEXTO_VALIDO,
) -> tuple[str, str]:
    """Deja una solicitud web en LISTA con su revisión 1 y su Doc."""
    creada = repo.crear_solicitud(
        idempotency_key=f"web:{uuid.uuid4().hex}",
        solicitante_hash="ab" * 32,
        rol="coordinador_seu",
        tipo_pieza="cronica_de_evento",
        actividad_ref=None,
        descripcion="Pedido sintético de prueba.",
        campos={"pieza": dict(CAMPOS), "pedido": {"publicos": []}},
        canal="web",
        ahora=AHORA,
    )
    if docs is not None:
        doc = docs.buscar_o_crear(
            marca=creada.id_solicitud,
            id_solicitud=creada.id_solicitud,
            contenido=texto,
            nombre=None,
        )
        doc_ref = doc.doc_ref
    else:
        doc_ref = f"doc-{creada.id_solicitud}"
    trabajo = repo.tomar_trabajo(worker_id="gen", ahora=AHORA)
    assert trabajo is not None
    id_borrador = repo.completar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=creada.id_solicitud,
        texto_generado=texto,
        referencia=doc_ref,
        doc_ref=doc_ref,
        head_revision_id="head-1",
        doc_url=f"https://docs.google.com/document/d/{doc_ref}/edit",
        texto_documento=texto,
        ahora=AHORA,
    )
    return creada.id_solicitud, id_borrador


def _ajustar(repo: RepositorioWeb, id_solicitud: str, base_id: str, **kwargs):
    detalle = repo.obtener(id_solicitud)
    assert detalle is not None
    vigente = next(
        r for r in detalle.revisiones if r.id_borrador == base_id
    )
    datos = {
        "idempotency_key": f"ajuste:{uuid.uuid4().hex}",
        "id_solicitud": id_solicitud,
        "id_borrador_base": base_id,
        "base_output_hash": vigente.output_hash,
        "indicacion": "más breve",
        "solicitante_hash": "cd" * 32,
        "rol": "coordinador_seu",
        "origen_identidad": "demo",
        "version_agente": "0.0.0-test",
        "ahora": AHORA,
    }
    datos.update(kwargs)
    return repo.crear_ajuste(**datos)


def _texto_ajustado(cuerpo: str) -> str:
    return (
        BORRADOR_MARKER
        + renderizar("cronica_de_evento", {**CAMPOS, "cuerpo": cuerpo})
        + "\n"
    )


def test_ajuste_crea_revision_nueva_y_conserva_la_anterior(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    id_solicitud, id_base = _solicitud_en_lista(repo)

    resultado = _ajustar(repo, id_solicitud, id_base)
    assert resultado.codigo == "encolado"
    assert repo.estado_de(id_solicitud) == "AJUSTANDO"

    trabajo = repo.tomar_trabajo(worker_id="w-ajuste", ahora=AHORA)
    assert trabajo is not None
    assert trabajo.clase == "ajuste"
    assert trabajo.indicacion == "más breve"
    assert trabajo.texto_base == TEXTO_VALIDO
    assert trabajo.id_borrador_base == id_base
    assert trabajo.id_ajuste == resultado.id_ajuste

    nuevo = _texto_ajustado("La jornada reunió a estudiantes y docentes.")
    id_nuevo = repo.completar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=id_solicitud,
        texto_generado=nuevo,
        referencia="doc-1",
        doc_ref="doc-1",
        head_revision_id="head-2",
        doc_url="https://docs.google.com/document/d/doc-1/edit",
        texto_documento=nuevo,
        origen="ajuste_generativo",
        id_borrador_base=id_base,
        id_ajuste=trabajo.id_ajuste,
        ahora=AHORA,
    )

    detalle = repo.obtener(id_solicitud)
    assert detalle is not None
    assert detalle.estado_web == "LISTA"
    assert len(detalle.revisiones) == 2
    anterior, ajustada = detalle.revisiones
    assert anterior.id_borrador == id_base
    assert anterior.origen == "generada"
    assert anterior.indicacion is None
    assert ajustada.id_borrador == id_nuevo
    assert ajustada.numero_revision == 2
    assert ajustada.origen == "ajuste_generativo"
    assert ajustada.indicacion == "más breve"
    assert detalle.texto_vigente == nuevo

    with psycopg.connect(
        DSN, options=f"-c search_path={base}"
    ) as conn:
        fila = conn.execute(
            "SELECT id_borrador_base FROM borradores WHERE id_borrador = %s",
            (id_nuevo,),
        ).fetchone()
        ajuste = conn.execute(
            "SELECT indicacion_hash, rol, origen_identidad, version_agente"
            " FROM ajustes WHERE id_ajuste = %s",
            (trabajo.id_ajuste,),
        ).fetchone()
    assert fila == (id_base,)
    assert ajuste == (
        _sha("más breve"), "coordinador_seu", "demo", "0.0.0-test"
    )


def test_decision_sobre_la_revision_anterior_queda_obsoleta(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    id_solicitud, id_base = _solicitud_en_lista(repo)
    _ajustar(repo, id_solicitud, id_base)
    trabajo = repo.tomar_trabajo(worker_id="w-ajuste", ahora=AHORA)
    assert trabajo is not None
    nuevo = _texto_ajustado("Cuerpo corregido por el ajuste.")
    id_nuevo = repo.completar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=id_solicitud,
        texto_generado=nuevo,
        referencia="doc-1",
        doc_ref="doc-1",
        head_revision_id="head-2",
        texto_documento=nuevo,
        origen="ajuste_generativo",
        id_borrador_base=id_base,
        id_ajuste=trabajo.id_ajuste,
        ahora=AHORA,
    )

    obsoleta = repo.registrar_decision(
        id_solicitud=id_solicitud,
        id_borrador=id_base,
        decision="APROBADA",
        doc_hash=_sha(nuevo),
        texto_doc=nuevo,
        validador_hash="ef" * 32,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="demo",
        version_agente="0.0.0-test",
        ahora=AHORA,
    )
    assert obsoleta.codigo == "revision_obsoleta"
    assert repo.estado_de(id_solicitud) == "LISTA"

    aprobada = repo.registrar_decision(
        id_solicitud=id_solicitud,
        id_borrador=id_nuevo,
        decision="APROBADA",
        doc_hash=_sha(nuevo),
        texto_doc=nuevo,
        validador_hash="ef" * 32,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="demo",
        version_agente="0.0.0-test",
        ahora=AHORA,
    )
    assert aprobada.codigo == "aprobada"
    assert repo.estado_de(id_solicitud) == "APROBADA"


def test_reenvio_idempotente_y_otro_ajuste_en_curso(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    id_solicitud, id_base = _solicitud_en_lista(repo)
    llave = "ajuste:k1"

    primera = _ajustar(repo, id_solicitud, id_base, idempotency_key=llave)
    assert primera.codigo == "encolado"

    repetida = _ajustar(repo, id_solicitud, id_base, idempotency_key=llave)
    assert repetida.codigo == "existente"
    assert repetida.id_ejecucion == primera.id_ejecucion

    with pytest.raises(ConflictoIdempotencia):
        _ajustar(
            repo,
            id_solicitud,
            id_base,
            idempotency_key=llave,
            indicacion="tono más formal",
        )

    en_curso = _ajustar(repo, id_solicitud, id_base)
    assert en_curso.codigo == "ajuste_en_curso"


def test_ajuste_rechaza_solicitud_cerrada(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    id_solicitud, id_base = _solicitud_en_lista(repo)
    repo.registrar_decision(
        id_solicitud=id_solicitud,
        id_borrador=id_base,
        decision="APROBADA",
        doc_hash=_sha(TEXTO_VALIDO),
        texto_doc=TEXTO_VALIDO,
        validador_hash="ef" * 32,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="demo",
        version_agente="0.0.0-test",
        ahora=AHORA,
    )
    assert _ajustar(repo, id_solicitud, id_base).codigo == "cerrada"


# ====================== worker con dobles ======================


class RepoWorkerFalso:
    """Repositorio mínimo del worker: un trabajo y el cierre que dejó."""

    def __init__(self, trabajo: TrabajoWeb) -> None:
        self._trabajo = trabajo
        self.completado: dict | None = None
        self.fallado: dict | None = None

    def tomar_trabajo(self, **_kwargs) -> TrabajoWeb:
        trabajo, self._trabajo = self._trabajo, None
        return trabajo

    def completar_trabajo(self, **kwargs) -> str:
        self.completado = kwargs
        return "borr-2"

    def fallar_trabajo(self, **kwargs) -> None:
        self.fallado = kwargs


class FuenteVacia:
    def obtener(self, id_actividad):
        raise KeyError(id_actividad)

    def enumerar(self):
        return []


class DestinoEspia:
    def __init__(self) -> None:
        self.llamadas: list[dict] = []

    def buscar_o_crear(self, **kwargs):
        self.llamadas.append(kwargs)
        raise AssertionError("no debió escribir el Doc")

    def compartir(self, doc_ref: str, correo: str) -> None:
        pass


class DestinoQueFalla:
    def buscar_o_crear(self, **_kwargs):
        raise DestinoBorradoresError("drive_unavailable")

    def compartir(self, doc_ref: str, correo: str) -> None:
        pass


class DestinoQueRompe:
    """Un error no previsto del adapter del Doc, fuera del contrato del puerto."""

    def buscar_o_crear(self, **_kwargs):
        raise ValueError("falla inesperada del adapter")

    def compartir(self, doc_ref: str, correo: str) -> None:
        pass


def _trabajo_ajuste(
    texto_base: str = TEXTO_VALIDO, *, intentos: int = 0
) -> TrabajoWeb:
    return TrabajoWeb(
        id_ejecucion="webe-a1",
        id_solicitud="web-a1",
        tipo_pieza="cronica_de_evento",
        actividad_ref=None,
        rol="coordinador_seu",
        solicitante_hash="ab" * 32,
        descripcion=None,
        campos={"pieza": dict(CAMPOS)},
        clase="ajuste",
        id_ajuste="aju-1",
        id_borrador_base="borr-1",
        indicacion="más breve",
        texto_base=texto_base,
        intentos=intentos,
    )


def test_worker_ajuste_exitoso_crea_la_revision(tmp_path: Path) -> None:
    trabajo = _trabajo_ajuste()
    repo = RepoWorkerFalso(trabajo)
    destino = DestinoPorMarcaMemoria()
    nuevo = _texto_ajustado("La jornada reunió a la comunidad educativa.")

    resultado = correr_una_vez(
        repositorio=repo,
        worker_id="w1",
        fuente=FuenteVacia(),
        generator=FakeGenerator(nuevo),
        directorio_salida=tmp_path,
        destino=destino,
    )

    assert resultado is trabajo
    assert repo.completado is not None
    assert repo.completado["origen"] == "ajuste_generativo"
    assert repo.completado["id_borrador_base"] == "borr-1"
    assert repo.completado["id_ajuste"] == "aju-1"
    assert repo.completado["texto_documento"] == nuevo
    assert destino.docs["web-a1"]["contenido"] == nuevo
    assert repo.fallado is None


def test_worker_salida_vacia_falla_sin_tocar_el_doc(tmp_path: Path) -> None:
    repo = RepoWorkerFalso(_trabajo_ajuste())
    destino = DestinoEspia()

    correr_una_vez(
        repositorio=repo,
        worker_id="w1",
        fuente=FuenteVacia(),
        generator=FakeGenerator(""),
        directorio_salida=tmp_path,
        destino=destino,
    )

    assert destino.llamadas == []
    assert repo.fallado is not None
    assert repo.fallado["resultado"] == "salida_vacia"
    assert repo.completado is None


def test_worker_fallo_del_doc_deja_error_visible(tmp_path: Path) -> None:
    repo = RepoWorkerFalso(_trabajo_ajuste())

    correr_una_vez(
        repositorio=repo,
        worker_id="w1",
        fuente=FuenteVacia(),
        generator=FakeGenerator(
            _texto_ajustado("La jornada reunió a estudiantes.")
        ),
        directorio_salida=tmp_path,
        destino=DestinoQueFalla(),
    )

    assert repo.completado is None
    assert repo.fallado is not None
    assert repo.fallado["resultado"] == "destination_failure"


# ====================== app: formulario y POST ======================


@dataclass
class Mundo:
    client: TestClient
    repo: RepositorioWeb
    docs: DocsCanalMemoria
    sesiones: SesionesMemoria


def _mundo(base: str, *, correo: str = CORREO_SEU) -> Mundo:
    repo = RepositorioWeb(_fabrica(base))
    docs = DocsCanalMemoria()
    sesiones = SesionesMemoria()
    padron = PadronRoles(
        {
            CORREO_SEU: "coordinador_seu",
            CORREO_LECTOR: "lector_seu",
            CORREO_APROBADOR: "APROBADOR_CONTENIDO",
        }
    )
    verificador = VerificadorFake(
        {
            "tok-seu": IdentidadVerificada("s1", CORREO_SEU, "x.invalid"),
            "tok-lector": IdentidadVerificada(
                "s2", CORREO_LECTOR, "x.invalid"
            ),
        }
    )
    app = crear_app(
        config=ConfiguracionWeb(
            google_client_id=CLIENT_ID_PRUEBA,
            modo_prueba=True,
            cookie_secure=False,
        ),
        verificador=verificador,
        padron=padron,
        repositorio=repo,
        sesiones=sesiones,
        actividades=[],
        exportador=docs,
        version_agente="0.0.0-test",
    )
    client = TestClient(app, base_url="http://testserver")
    formulario = client.get("/ingresar")
    csrf = formulario.text.split('name="csrf" value="', 1)[1].split(
        '"', 1
    )[0]
    token = "tok-seu" if correo == CORREO_SEU else "tok-lector"
    client.post(
        "/ingresar",
        data={"credential": token, "csrf": csrf},
        follow_redirects=False,
    )
    return Mundo(client, repo, docs, sesiones)


def _csrf(mundo: Mundo) -> str:
    return next(iter(mundo.sesiones._sesiones.values())).csrf_token


def _crear_lista(mundo: Mundo, *, texto: str = TEXTO_VALIDO) -> tuple[str, str]:
    return _solicitud_en_lista(mundo.repo, mundo.docs, texto=texto)


def _post_ajuste(
    mundo: Mundo,
    id_solicitud: str,
    *,
    indicacion: str = "más breve",
    llave: str = "k1",
    csrf: str | None = None,
):
    return mundo.client.post(
        f"/solicitudes/{id_solicitud}/ajustar",
        data={
            "csrf": _csrf(mundo) if csrf is None else csrf,
            "llave": llave,
            "indicacion": indicacion,
        },
        follow_redirects=False,
    )


def _contar(base: str, consulta: str, parametros: tuple = ()) -> int:
    with psycopg.connect(
        DSN, options=f"-c search_path={base}"
    ) as conn:
        return conn.execute(consulta, parametros).fetchone()[0]


def test_el_formulario_solo_aparece_con_revision_y_permiso(base: str) -> None:
    mundo = _mundo(base)
    id_solicitud, _ = _crear_lista(mundo)

    detalle = mundo.client.get(f"/solicitudes/{id_solicitud}")
    assert "Pedir ajuste" in detalle.text
    assert 'name="indicacion"' in detalle.text

    lector = _mundo(base, correo=CORREO_LECTOR)
    assert "Pedir ajuste" not in lector.client.get(
        f"/solicitudes/{id_solicitud}"
    ).text


def test_sin_revision_no_se_muestra_el_formulario(base: str) -> None:
    mundo = _mundo(base)
    creada = mundo.repo.crear_solicitud(
        idempotency_key=f"web:{uuid.uuid4().hex}",
        solicitante_hash="ab" * 32,
        rol="coordinador_seu",
        tipo_pieza="cronica_de_evento",
        actividad_ref=None,
        descripcion=None,
        campos={"pieza": dict(CAMPOS)},
        canal="web",
        ahora=AHORA,
    )
    detalle = mundo.client.get(f"/solicitudes/{creada.id_solicitud}")
    assert "Pedir ajuste" not in detalle.text

    respuesta = _post_ajuste(mundo, creada.id_solicitud)
    assert respuesta.status_code == 400


def test_post_ajuste_importa_el_doc_y_encola(base: str) -> None:
    mundo = _mundo(base)
    id_solicitud, _ = _crear_lista(mundo)
    detalle = mundo.repo.obtener(id_solicitud)
    assert detalle is not None and detalle.doc_ref is not None
    editado = _texto_ajustado("Texto corregido a mano en el Doc.")
    mundo.docs.editar(detalle.doc_ref, editado)

    respuesta = _post_ajuste(mundo, id_solicitud)

    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == f"/solicitudes/{id_solicitud}"
    actualizado = mundo.repo.obtener(id_solicitud)
    assert actualizado is not None
    assert actualizado.estado_web == "AJUSTANDO"
    assert len(actualizado.revisiones) == 2
    importada = actualizado.revisiones[-1]
    assert importada.origen == "editada_docs"
    assert actualizado.texto_vigente == editado

    ajuste = mundo.repo.buscar_ajuste(idempotency_key="ajuste:k1")
    assert ajuste is not None
    assert ajuste.id_solicitud == id_solicitud
    assert _contar(
        base,
        "SELECT count(*) FROM ajustes WHERE id_solicitud = %s",
        (id_solicitud,),
    ) == 1

    pagina = mundo.client.get(f"/solicitudes/{id_solicitud}")
    assert "Ajustando…" in pagina.text
    assert 'id="indicacion"' not in pagina.text
    assert mundo.client.get(
        f"/solicitudes/{id_solicitud}/estado"
    ).json() == {"estado": "AJUSTANDO"}


def test_post_ajuste_sin_csrf_da_403(base: str) -> None:
    mundo = _mundo(base)
    id_solicitud, _ = _crear_lista(mundo)
    respuesta = _post_ajuste(mundo, id_solicitud, csrf="inventado")
    assert respuesta.status_code == 403
    assert mundo.repo.estado_de(id_solicitud) == "LISTA"


def test_post_ajuste_con_rol_sin_permiso_da_403(base: str) -> None:
    mundo = _mundo(base)
    id_solicitud, _ = _crear_lista(mundo)
    lector = _mundo(base, correo=CORREO_LECTOR)
    respuesta = _post_ajuste(lector, id_solicitud)
    assert respuesta.status_code == 403
    assert mundo.repo.estado_de(id_solicitud) == "LISTA"


def test_post_ajuste_rechaza_decidida(base: str) -> None:
    mundo = _mundo(base)
    id_solicitud, id_base = _crear_lista(mundo)
    mundo.repo.registrar_decision(
        id_solicitud=id_solicitud,
        id_borrador=id_base,
        decision="APROBADA",
        doc_hash=_sha(TEXTO_VALIDO),
        texto_doc=TEXTO_VALIDO,
        validador_hash="ef" * 32,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="demo",
        version_agente="0.0.0-test",
        ahora=AHORA,
    )
    respuesta = _post_ajuste(mundo, id_solicitud)
    assert respuesta.status_code == 409
    assert mundo.repo.buscar_ajuste(idempotency_key="ajuste:k1") is None
    assert "Pedir ajuste" not in mundo.client.get(
        f"/solicitudes/{id_solicitud}"
    ).text


def test_indicacion_fuera_de_rango_rechaza(base: str) -> None:
    mundo = _mundo(base)
    id_solicitud, _ = _crear_lista(mundo)
    assert _post_ajuste(
        mundo, id_solicitud, indicacion="ok", llave="k1"
    ).status_code == 400
    assert _post_ajuste(
        mundo, id_solicitud, indicacion="x" * 501, llave="k2"
    ).status_code == 400
    assert _post_ajuste(
        mundo, id_solicitud, indicacion="válida", llave="x" * 201
    ).status_code == 400
    assert _contar(
        base,
        "SELECT count(*) FROM ajustes WHERE id_solicitud = %s",
        (id_solicitud,),
    ) == 0


def test_post_ajuste_con_otro_en_curso_da_409(base: str) -> None:
    mundo = _mundo(base)
    id_solicitud, _ = _crear_lista(mundo)
    assert _post_ajuste(mundo, id_solicitud, llave="k1").status_code == 303

    respuesta = _post_ajuste(
        mundo, id_solicitud, indicacion="tono más formal", llave="k2"
    )

    assert respuesta.status_code == 409
    assert "Ya hay un ajuste en curso" in respuesta.text
    assert _contar(
        base,
        "SELECT count(*) FROM ajustes WHERE id_solicitud = %s",
        (id_solicitud,),
    ) == 1


def test_post_ajuste_idempotente_y_llave_repetida(base: str) -> None:
    mundo = _mundo(base)
    id_solicitud, _ = _crear_lista(mundo)

    assert _post_ajuste(mundo, id_solicitud).status_code == 303
    assert _post_ajuste(mundo, id_solicitud).status_code == 303
    assert _contar(
        base,
        "SELECT count(*) FROM ajustes WHERE id_solicitud = %s",
        (id_solicitud,),
    ) == 1

    respuesta = _post_ajuste(
        mundo, id_solicitud, indicacion="tono más formal"
    )
    assert respuesta.status_code == 409


# ============ robustez del ajuste (demo 17/11, Ollama real) ============


class GeneradorSecuencia:
    """Devuelve las respuestas en orden y guarda los prompts recibidos."""

    modelo = "fake-secuencia"
    num_predict = None

    def __init__(self, *respuestas: str) -> None:
        self._respuestas = list(respuestas)
        self.prompts: list[str] = []

    def generar(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._respuestas.pop(0) if self._respuestas else ""


class GeneradorQueFalla:
    """Levanta el error del adapter, como un Ollama caído o agotado."""

    modelo = "fake-falla"
    num_predict = None

    def __init__(self, error: Exception) -> None:
        self._error = error
        self.llamadas = 0

    def generar(self, prompt: str) -> str:
        self.llamadas += 1
        raise self._error


class RepoAjusteConReintento(RepoWorkerFalso):
    """Devuelve el mismo ajuste hasta que el worker lo cierra.

    Emula la reserva: si el worker no falla el trabajo, otra corrida lo
    vuelve a tomar. Sirve para comprobar que un fallo del generador no se
    reintenta tres veces por reserva.
    """

    def tomar_trabajo(self, **_kwargs) -> TrabajoWeb | None:
        return None if self.fallado is not None else self._trabajo


@pytest.mark.parametrize(
    ("error", "codigo"),
    [
        # TimeoutError es el contrato del puerto; el adapter de Ollama
        # convierte timeout y red en RuntimeError.
        (TimeoutError("agotado"), "timeout_generador"),
        (
            RuntimeError("No se pudo contactar al generador local"),
            "generador_error",
        ),
        (
            PresupuestoAgotadoError("El presupuesto no alcanzó"),
            "presupuesto_agotado",
        ),
    ],
)
def test_worker_ajuste_con_fallo_del_generador_vuelve_a_lista_sin_reintento(
    tmp_path: Path, error: Exception, codigo: str
) -> None:
    """El adapter que falla no deja la solicitud AJUSTANDO: el primer fallo
    cierra el ajuste, vuelve a LISTA y se registra una sola vez."""
    trabajo = _trabajo_ajuste(intentos=1)
    repo = RepoAjusteConReintento(trabajo)
    generador = GeneradorQueFalla(error)

    for _ in range(3):
        correr_una_vez(
            repositorio=repo,
            worker_id="w1",
            fuente=FuenteVacia(),
            generator=generador,
            directorio_salida=tmp_path,
            destino=DestinoEspia(),
        )

    assert generador.llamadas == 1
    assert repo.completado is None
    assert repo.fallado is not None
    assert repo.fallado["estado_solicitud"] == "LISTA"
    assert repo.fallado["resultado"] == "error_generacion"

    lineas = (tmp_path / "logs" / "ajustes.jsonl").read_text().splitlines()
    assert len(lineas) == 1
    registro = json.loads(lineas[0])
    assert registro["resultado"] == "error_generacion"
    assert registro["intentos"] == 1
    assert registro["duracion_ms"] >= 0
    assert registro["fallos"][0]["intento"] == 1
    assert registro["fallos"][0]["codigos"] == [codigo]
    assert "más breve" not in lineas[0]
    assert str(error) not in lineas[0]


def _sin_pie(texto: str) -> str:
    return texto[: texto.rindex("\n--\n")] + "\n"


def test_el_modelo_no_reescribe_el_pie_institucional() -> None:
    """El pie (después de `--`) es fijo de la forma: no viaja al modelo y
    se repone tal cual, aunque la salida lo omita o lo cambie."""

    nuevo = _texto_ajustado("La jornada reunió a la comunidad.")
    generador = GeneradorSecuencia(
        _sin_pie(nuevo),
    )
    texto, errores = ajustar_texto(
        texto_base=TEXTO_VALIDO,
        indicacion="más breve",
        tipo="cronica_de_evento",
        campos=CAMPOS,
        generator=generador,
    )

    assert errores == []
    assert "Av. Cabildo" not in generador.prompts[0]
    assert texto.rstrip("\n").endswith(TEXTO_VALIDO.rstrip("\n").split("\n--\n")[1])
    assert "La jornada reunió a la comunidad." in texto

    cambiado = _sin_pie(nuevo) + "--\nFacultad inventada\n"
    texto, errores = ajustar_texto(
        texto_base=TEXTO_VALIDO,
        indicacion="más breve",
        tipo="cronica_de_evento",
        campos=CAMPOS,
        generator=GeneradorSecuencia(cambiado),
    )
    assert errores == []
    assert "Facultad inventada" not in texto
    assert "Av. Cabildo" in texto


def test_reintenta_una_vez_si_la_salida_no_sirve() -> None:
    generador = GeneradorSecuencia(
        "", _texto_ajustado("La jornada reunió a la comunidad.")
    )
    texto, errores = ajustar_texto(
        texto_base=TEXTO_VALIDO,
        indicacion="más breve",
        tipo="cronica_de_evento",
        campos=CAMPOS,
        generator=generador,
    )

    assert errores == []
    assert len(generador.prompts) == 2
    assert "La jornada reunió a la comunidad." in texto


def test_worker_ajuste_fallido_vuelve_a_lista_y_deja_registro(
    tmp_path: Path,
) -> None:
    """Un ajuste que no sirve no inutiliza la solicitud: la revisión
    vigente sigue y se puede aprobar o pedir otro ajuste. El motivo queda
    en `logs/ajustes.jsonl` (códigos, sin prosa)."""

    repo = RepoWorkerFalso(_trabajo_ajuste())

    correr_una_vez(
        repositorio=repo,
        worker_id="w1",
        fuente=FuenteVacia(),
        generator=GeneradorSecuencia("", ""),
        directorio_salida=tmp_path,
        destino=DestinoEspia(),
    )

    assert repo.fallado is not None
    assert repo.fallado["estado_solicitud"] == "LISTA"
    lineas = (tmp_path / "logs" / "ajustes.jsonl").read_text().splitlines()
    registro = json.loads(lineas[-1])
    assert registro["resultado"] == "salida_vacia"
    assert registro["errores"] == ["salida_vacia"]
    assert registro["intentos"] == 2
    assert registro["duracion_ms"] >= 0
    assert [fallo["intento"] for fallo in registro["fallos"]] == [1, 2]
    assert [fallo["codigos"] for fallo in registro["fallos"]] == [
        ["salida_vacia"],
        ["salida_vacia"],
    ]
    assert all(fallo["duracion_ms"] >= 0 for fallo in registro["fallos"])
    assert registro["id_solicitud"] == "web-a1"
    assert "más breve" not in lineas[-1]


class GeneradorFallaEnElSegundoIntento:
    """Primera salida inválida y después el timeout real del adapter."""

    modelo = "fake-falla-segundo"
    num_predict = None

    def __init__(self) -> None:
        self.llamadas = 0

    def generar(self, prompt: str) -> str:
        self.llamadas += 1
        if self.llamadas == 1:
            return ""
        raise TimeoutError("agotado")


def test_worker_ajuste_con_error_no_previsto_tambien_vuelve_a_lista(
    tmp_path: Path,
) -> None:
    """Un fallo fuera del contrato del generador no reintenta por reserva y
    deja duración y código por intento en el registro."""
    repo = RepoWorkerFalso(_trabajo_ajuste(intentos=1))

    correr_una_vez(
        repositorio=repo,
        worker_id="w1",
        fuente=FuenteVacia(),
        generator=FakeGenerator(
            _texto_ajustado("La jornada reunió a la comunidad.")
        ),
        directorio_salida=tmp_path,
        destino=DestinoQueRompe(),
    )

    assert repo.fallado is not None
    assert repo.fallado["estado_solicitud"] == "LISTA"
    assert repo.fallado["resultado"] == "error_generacion"
    lineas = (tmp_path / "logs" / "ajustes.jsonl").read_text().splitlines()
    registro = json.loads(lineas[-1])
    assert registro["duracion_ms"] >= 0
    assert registro["fallos"][0]["codigos"] == ["error_no_previsto"]
    assert "falla inesperada" not in lineas[-1]


def test_un_timeout_en_el_segundo_intento_no_se_reintenta_de_nuevo(
    tmp_path: Path,
) -> None:
    repo = RepoWorkerFalso(_trabajo_ajuste(intentos=1))
    generador = GeneradorFallaEnElSegundoIntento()

    correr_una_vez(
        repositorio=repo,
        worker_id="w1",
        fuente=FuenteVacia(),
        generator=generador,
        directorio_salida=tmp_path,
        destino=DestinoEspia(),
    )

    assert generador.llamadas == 2
    assert repo.fallado is not None
    assert repo.fallado["estado_solicitud"] == "LISTA"
    assert repo.fallado["resultado"] == "error_generacion"
    lineas = (tmp_path / "logs" / "ajustes.jsonl").read_text().splitlines()
    registro = json.loads(lineas[-1])
    assert registro["intentos"] == 2
    assert [fallo["codigos"] for fallo in registro["fallos"]] == [
        ["salida_vacia"],
        ["timeout_generador"],
    ]
    assert "agotado" not in lineas[-1]


def test_worker_usa_el_generador_de_ajuste_si_lo_hay(tmp_path: Path) -> None:
    repo = RepoWorkerFalso(_trabajo_ajuste())
    ajuste = GeneradorSecuencia(_texto_ajustado("La jornada reunió a todos."))

    correr_una_vez(
        repositorio=repo,
        worker_id="w1",
        fuente=FuenteVacia(),
        generator=GeneradorSecuencia(),
        generator_ajuste=ajuste,
        directorio_salida=tmp_path,
        destino=DestinoPorMarcaMemoria(),
    )

    assert repo.completado is not None
    assert len(ajuste.prompts) == 1


def test_worker_ajuste_con_timeout_deja_lista_en_la_base(
    base: str, tmp_path: Path
) -> None:
    """Con la persistencia real, el fallo del generador cierra la ejecución
    y devuelve la solicitud a LISTA sin crear una revisión nueva."""
    repo = RepositorioWeb(_fabrica(base))
    id_solicitud, id_base = _solicitud_en_lista(repo)
    _ajustar(repo, id_solicitud, id_base)

    correr_una_vez(
        repositorio=repo,
        worker_id="w-ajuste",
        fuente=FuenteVacia(),
        generator=GeneradorQueFalla(TimeoutError("agotado")),
        directorio_salida=tmp_path,
        destino=DestinoEspia(),
        ahora=AHORA,
    )

    detalle = repo.obtener(id_solicitud)
    assert detalle is not None
    assert detalle.estado_web == "LISTA"
    assert len(detalle.revisiones) == 1
    lineas = (tmp_path / "logs" / "ajustes.jsonl").read_text().splitlines()
    assert json.loads(lineas[-1])["resultado"] == "error_generacion"


def test_ajuste_fallido_deja_la_solicitud_en_lista_con_aviso(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    id_solicitud, id_base = _solicitud_en_lista(repo)
    _ajustar(repo, id_solicitud, id_base)
    trabajo = repo.tomar_trabajo(worker_id="w-ajuste", ahora=AHORA)
    assert trabajo is not None

    repo.fallar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=id_solicitud,
        resultado="salida_no_conforme",
        estado_solicitud="LISTA",
        ahora=AHORA,
    )

    detalle = repo.obtener(id_solicitud)
    assert detalle is not None
    assert detalle.estado_web == "LISTA"
    assert detalle.ultimo_ajuste_fallido == "salida_no_conforme"
    assert len(detalle.revisiones) == 1


def test_la_vista_avisa_que_el_ultimo_ajuste_no_se_aplico(base: str) -> None:
    mundo = _mundo(base)
    id_solicitud, id_base = _crear_lista(mundo)
    _ajustar(mundo.repo, id_solicitud, id_base)
    trabajo = mundo.repo.tomar_trabajo(worker_id="w-ajuste", ahora=AHORA)
    assert trabajo is not None
    mundo.repo.fallar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=id_solicitud,
        resultado="salida_no_conforme",
        estado_solicitud="LISTA",
        ahora=AHORA,
    )

    html = mundo.client.get(f"/solicitudes/{id_solicitud}").text

    assert "El último ajuste no se aplicó" in html
    assert "Pedir ajuste" in html
    assert "La generación falló" not in html
