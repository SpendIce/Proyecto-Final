"""Doc por solicitud, revisiones y decisión del canal web (#153, ADR 0016).

Tres capas, como el resto de la suite del canal:

- El adapter `GoogleDocsDestinoPorMarca` contra un transporte HTTP falso:
  búsqueda por la marca de la solicitud antes de crear, reutilización sin
  duplicar Doc, volcado y `writer` opcional.
- La persistencia contra PostgreSQL real: completar con Doc, importar
  sin cambios y con cambios, y las pruebas 2 y 4 del ADR 0016 — la
  decisión no deja estado parcial y la decisión sobre un Doc cambiado se
  rechaza registrando la revisión nueva.
- La app con repositorio en memoria y el fake `DocsCanalMemoria`:
  «Traer cambios», «Aprobar/Descartar» con rol, CSRF y proveniencia demo.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agente1.canal_form import PadronRoles
from agente1.destinos import BORRADOR_MARKER, DestinoBorradoresError
from agente1.google_workspace import (
    GoogleDocsDestinoPorMarca,
    RespuestaHttp,
)
from agente1.web.app import ConfiguracionWeb, crear_app
from agente1.web.docs_canal import DocsCanalMemoria
from agente1.web.identidad import IdentidadVerificada, VerificadorFake
from agente1.web.persistencia import (
    DetalleSolicitud,
    ItemBandeja,
    RepositorioWeb,
    ResultadoDecisionWeb,
    ResultadoImportacion,
    RevisionPieza,
    SolicitudCreada,
)
from agente1.web.sesiones import SesionesMemoria

AHORA = datetime.now(timezone.utc)
DSN = os.environ.get("AGENTE1_POSTGRES_DSN")
MIGRACIONES = Path(__file__).resolve().parent.parent / "migrations"


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


# ============================ adapter Workspace ============================


class TokenFijo:
    def obtener_access_token(self) -> str:
        return "TOKEN_SECRETO"


class TransporteSecuencia:
    def __init__(self, respuestas: list[RespuestaHttp | Exception]) -> None:
        self.respuestas = respuestas
        self.solicitudes: list[dict[str, Any]] = []

    def request(self, **kwargs) -> RespuestaHttp:
        self.solicitudes.append(kwargs)
        respuesta = self.respuestas[len(self.solicitudes) - 1]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


def _destino(
    respuestas: list[RespuestaHttp | Exception],
) -> tuple[GoogleDocsDestinoPorMarca, TransporteSecuencia]:
    transporte = TransporteSecuencia(respuestas)
    return (
        GoogleDocsDestinoPorMarca(
            plantilla_id="plantilla_OK-1",
            carpeta_id="carpeta_OK-1",
            token_provider=TokenFijo(),
            transport=transporte,
            timeout_s=5,
        ),
        transporte,
    )


def _export(texto: str) -> RespuestaHttp:
    return RespuestaHttp(200, texto.encode("utf-8"))


def test_destino_crea_doc_cuando_la_marca_no_existe() -> None:
    destino, transporte = _destino(
        [
            RespuestaHttp(200, b'{"files":[]}'),
            RespuestaHttp(200, b'{"id":"doc-nuevo-1"}'),
            RespuestaHttp(200, b'{"replies":[{}]}'),
            _export(BORRADOR_MARKER + "Texto del Doc.\n"),
            RespuestaHttp(200, b'{"headRevisionId":"42"}'),
        ]
    )

    resultado = destino.buscar_o_crear(
        marca="web-0001",
        id_solicitud="web-0001",
        contenido=BORRADOR_MARKER + "Texto del Doc.\n",
        nombre=None,
    )

    assert resultado.doc_ref == "doc-nuevo-1"
    assert resultado.head_revision_id == "42"
    assert resultado.doc_url == (
        "https://docs.google.com/document/d/doc-nuevo-1/edit"
    )
    assert resultado.texto_documento == BORRADOR_MARKER + "Texto del Doc.\n"
    buscar, copiar, volcar, _exportar, _head = transporte.solicitudes
    # La búsqueda por marca precede a la copia: marca en `appProperties`.
    assert "a1_solicitud" in buscar["target"]
    assert copiar["target"].startswith(
        "/drive/v3/files/plantilla_OK-1/copy"
    )
    cuerpo = json.loads(copiar["body"])
    assert cuerpo["appProperties"]["a1_solicitud"] == "web-0001"
    assert cuerpo["parents"] == ["carpeta_OK-1"]
    assert volcar["host"] == "docs.googleapis.com"


def test_destino_reutiliza_el_doc_de_la_marca_sin_crear() -> None:
    destino, transporte = _destino(
        [
            RespuestaHttp(
                200,
                b'{"files":[{"id":"doc-viejo-1","headRevisionId":"7"}]}',
            ),
            _export(BORRADOR_MARKER + "Texto del Doc.\n"),  # ya tiene el contenido
            _export(BORRADOR_MARKER + "Texto del Doc.\n"),
            RespuestaHttp(200, b'{"headRevisionId":"9"}'),
        ]
    )

    resultado = destino.buscar_o_crear(
        marca="web-0002",
        id_solicitud="web-0002",
        contenido=BORRADOR_MARKER + "Texto del Doc.\n",
        nombre=None,
    )

    assert resultado.doc_ref == "doc-viejo-1"
    # Ningún POST de copia: el Doc existente se reutilizó.
    assert all(
        s["method"] == "GET" for s in transporte.solicitudes
    )


def test_destino_reescribe_si_la_corrida_anterior_dejo_otro_texto() -> None:
    destino, transporte = _destino(
        [
            RespuestaHttp(
                200, b'{"files":[{"id":"doc-viejo-2"}]}'
            ),
            _export("restos de una corrida caída"),
            RespuestaHttp(
                200, b'{"body":{"content":[{"endIndex":30}]}}'
            ),
            RespuestaHttp(200, b'{"replies":[{}]}'),
            _export(BORRADOR_MARKER + "Texto nuevo.\n"),
            RespuestaHttp(200, b'{"headRevisionId":"11"}'),
        ]
    )

    resultado = destino.buscar_o_crear(
        marca="web-0003",
        id_solicitud="web-0003",
        contenido=BORRADOR_MARKER + "Texto nuevo.\n",
        nombre=None,
    )

    assert resultado.doc_ref == "doc-viejo-2"
    reemplazo = transporte.solicitudes[3]
    assert reemplazo["target"].endswith(":batchUpdate")
    pedidos = json.loads(reemplazo["body"])["requests"]
    assert pedidos[0]["deleteContentRange"]["range"]["endIndex"] == 29
    assert pedidos[1]["insertText"]["text"] == BORRADOR_MARKER + "Texto nuevo.\n"


def test_destino_marca_duplicada_es_estado_corrupto() -> None:
    destino, _ = _destino(
        [
            RespuestaHttp(
                200,
                b'{"files":[{"id":"a1"},{"id":"b2"}]}',
            )
        ]
    )
    with pytest.raises(DestinoBorradoresError) as error:
        destino.buscar_o_crear(
            marca="web-x", id_solicitud="web-x",
            contenido=BORRADOR_MARKER + "x", nombre=None,
        )
    assert error.value.code == "drive_response_invalid"


def test_compartir_da_writer_al_correo_sin_notificacion() -> None:
    destino, transporte = _destino([RespuestaHttp(200, b'{"id":"p1"}')])

    destino.compartir("doc-1", "persona@example.invalid")

    (permiso,) = transporte.solicitudes
    assert permiso["method"] == "POST"
    assert permiso["target"].endswith(
        "/permissions?supportsAllDrives=true&sendNotificationEmail=false"
    )
    assert json.loads(permiso["body"]) == {
        "type": "user",
        "role": "writer",
        "emailAddress": "persona@example.invalid",
    }


def test_compartir_rechaza_correo_invalido_sin_http() -> None:
    destino, transporte = _destino([])
    with pytest.raises(DestinoBorradoresError):
        destino.compartir("doc-1", "no-es-correo")
    assert transporte.solicitudes == []


def test_exportar_texto_devuelve_el_cuerpo() -> None:
    destino, transporte = _destino([_export("contenido plano")])
    assert destino.exportar_texto("doc-9") == "contenido plano"
    assert "/export?mimeType=text%2Fplain" in transporte.solicitudes[0]["target"]


# ============================ persistencia real ============================

necesita_pg = pytest.mark.skipif(not DSN, reason="sin AGENTE1_POSTGRES_DSN")


@pytest.fixture()
def base():
    """Esquema desechable con las migraciones 0001+ aplicadas."""
    import psycopg

    esquema = f"test_docs_{uuid.uuid4().hex[:10]}"
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
    import psycopg

    return lambda: psycopg.connect(
        DSN, options=f"-c search_path={esquema}", autocommit=False
    )


def _crear(repo: RepositorioWeb, llave: str):
    return repo.crear_solicitud(
        idempotency_key=llave,
        solicitante_hash="ab" * 32,
        rol="coordinador_seu",
        tipo_pieza="cronica_de_evento",
        actividad_ref=None,
        descripcion="Descripción sintética.",
        campos={"pieza": {"titulo": "T"}, "pedido": {}},
        ahora=AHORA,
    )


def _trabajo_completo(repo: RepositorioWeb, id_solicitud: str):
    """Reserva + asienta con Doc: deja la solicitud en `LISTA` con Doc."""
    trabajo = repo.tomar_trabajo(worker_id="w1")
    assert trabajo is not None and trabajo.id_solicitud == id_solicitud
    return repo.completar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=trabajo.id_solicitud,
        texto_generado="Texto generado.\n",
        referencia="doc-1",
        doc_ref="doc-1",
        head_revision_id="7",
        doc_url="https://docs.google.com/document/d/doc-1/edit",
        texto_documento="Texto generado.\n",
        ahora=AHORA,
    )


@necesita_pg
def test_completar_trabajo_asienta_doc_y_revision(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:d1")
    id_borrador = _trabajo_completo(repo, creada.id_solicitud)

    detalle = repo.obtener(creada.id_solicitud)
    assert detalle is not None
    assert detalle.estado_web == "LISTA"
    assert detalle.doc_ref == "doc-1"
    assert detalle.doc_url == (
        "https://docs.google.com/document/d/doc-1/edit"
    )
    assert detalle.texto_vigente == "Texto generado.\n"
    assert len(detalle.revisiones) == 1
    revision = detalle.revisiones[0]
    assert revision.id_borrador == id_borrador
    assert revision.numero_revision == 1
    assert revision.origen == "generada"
    assert revision.doc_ref == "doc-1"
    assert revision.head_revision_id == "7"
    assert revision.output_hash == _sha("Texto generado.\n")


@necesita_pg
def test_importar_sin_cambios_no_crea_revision(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:d2")
    _trabajo_completo(repo, creada.id_solicitud)

    resultado = repo.importar_revision(
        id_solicitud=creada.id_solicitud,
        texto="Texto generado.\n",
        ahora=AHORA,
    )

    assert resultado.codigo == "sin_cambios"
    assert len(repo.obtener(creada.id_solicitud).revisiones) == 1


@necesita_pg
def test_importar_con_cambios_crea_revision_nueva(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:d3")
    _trabajo_completo(repo, creada.id_solicitud)

    resultado = repo.importar_revision(
        id_solicitud=creada.id_solicitud,
        texto="Texto editado en Docs.\n",
        ahora=AHORA,
    )

    assert resultado.codigo == "importada"
    assert resultado.numero_revision == 2
    detalle = repo.obtener(creada.id_solicitud)
    assert len(detalle.revisiones) == 2
    assert detalle.revisiones[1].origen == "editada_docs"
    assert detalle.texto_vigente == "Texto editado en Docs.\n"
    # La primera revisión no se sobrescribió.
    assert detalle.revisiones[0].output_hash == _sha("Texto generado.\n")


@necesita_pg
def test_decision_aprobada_cierra_con_metadatos(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:d4")
    id_borrador = _trabajo_completo(repo, creada.id_solicitud)

    resultado = repo.registrar_decision(
        id_solicitud=creada.id_solicitud,
        id_borrador=id_borrador,
        decision="APROBADA",
        doc_hash=_sha("Texto generado.\n"),
        texto_doc="Texto generado.\n",
        validador_hash="cd" * 32,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="google",
        version_agente="0.5.10",
        ahora=AHORA,
    )

    assert resultado.codigo == "aprobada"
    assert repo.estado_de(creada.id_solicitud) == "APROBADA"
    with _fabrica(base)() as conn:
        fila = conn.execute(
            "SELECT decision, rol, origen_identidad, version_agente,"
            " senal, cantidad_ajustes FROM validaciones"
            " WHERE id_borrador = %s",
            (id_borrador,),
        ).fetchone()
    assert fila == (
        "APROBADA", "APROBADOR_CONTENIDO", "google", "0.5.10",
        "sin_cambios", 0,
    )


@necesita_pg
def test_decision_descartada_cierra(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:d5")
    id_borrador = _trabajo_completo(repo, creada.id_solicitud)

    resultado = repo.registrar_decision(
        id_solicitud=creada.id_solicitud,
        id_borrador=id_borrador,
        decision="RECHAZADA",
        doc_hash=_sha("Texto generado.\n"),
        texto_doc="Texto generado.\n",
        validador_hash="cd" * 32,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="demo",
        version_agente="0.5.10",
        ahora=AHORA,
    )

    assert resultado.codigo == "descartada"
    assert repo.estado_de(creada.id_solicitud) == "DESCARTADA"


@necesita_pg
def test_decision_con_doc_cambiado_importa_y_rechaza(base: str) -> None:
    """Prueba 4 del ADR 0016: la decisión sobre un Doc que cambió no se
    asienta; se registra la revisión nueva y la página muestra la vigente.
    """
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:d6")
    id_borrador = _trabajo_completo(repo, creada.id_solicitud)

    resultado = repo.registrar_decision(
        id_solicitud=creada.id_solicitud,
        id_borrador=id_borrador,
        decision="APROBADA",
        doc_hash=_sha("Texto cambiado después de mostrar.\n"),
        texto_doc="Texto cambiado después de mostrar.\n",
        validador_hash="cd" * 32,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="google",
        version_agente="0.5.10",
        ahora=AHORA,
    )

    assert resultado.codigo == "doc_cambiado"
    detalle = repo.obtener(creada.id_solicitud)
    # La solicitud sigue abierta y la vigente es la revisión importada.
    assert detalle.estado_web == "LISTA"
    assert len(detalle.revisiones) == 2
    assert detalle.revisiones[1].origen == "editada_docs"
    assert detalle.texto_vigente == "Texto cambiado después de mostrar.\n"
    with _fabrica(base)() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM validaciones"
            " WHERE id_borrador = %s",
            (id_borrador,),
        ).fetchone()[0] == 0


@necesita_pg
def test_decision_obsoleta_rechaza(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:d7")
    vieja = _trabajo_completo(repo, creada.id_solicitud)
    repo.importar_revision(
        id_solicitud=creada.id_solicitud,
        texto="Edición importada.\n",
        ahora=AHORA,
    )

    resultado = repo.registrar_decision(
        id_solicitud=creada.id_solicitud,
        id_borrador=vieja,  # ya no es la vigente
        decision="APROBADA",
        doc_hash=_sha("Edición importada.\n"),
        texto_doc="Edición importada.\n",
        validador_hash="cd" * 32,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="google",
        version_agente="0.5.10",
        ahora=AHORA,
    )

    assert resultado.codigo == "revision_obsoleta"
    assert repo.estado_de(creada.id_solicitud) == "LISTA"


@necesita_pg
def test_decision_duplicada_es_rechazo_idempotente(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:d8")
    id_borrador = _trabajo_completo(repo, creada.id_solicitud)
    repo.registrar_decision(
        id_solicitud=creada.id_solicitud,
        id_borrador=id_borrador,
        decision="APROBADA",
        doc_hash=_sha("Texto generado.\n"),
        texto_doc="Texto generado.\n",
        validador_hash="cd" * 32,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="google",
        version_agente="0.5.10",
        ahora=AHORA,
    )

    resultado = repo.registrar_decision(
        id_solicitud=creada.id_solicitud,
        id_borrador=id_borrador,
        decision="APROBADA",
        doc_hash=_sha("Texto generado.\n"),
        texto_doc="Texto generado.\n",
        validador_hash="cd" * 32,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="google",
        version_agente="0.5.10",
        ahora=AHORA,
    )

    assert resultado.codigo == "cerrada"
    with _fabrica(base)() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM validaciones WHERE id_borrador = %s",
            (id_borrador,),
        ).fetchone()[0] == 1


@necesita_pg
def test_decision_fallida_no_deja_estado_parcial(base: str) -> None:
    """Prueba 2 del ADR 0016: una caída a mitad de la decisión no deja ni
    decisión ni cierre parcial — toda la operación es una transacción.
    """
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:d9")
    id_borrador = _trabajo_completo(repo, creada.id_solicitud)

    # Una violación de integridad dentro de la tx simula la caída: el
    # origen de identidad inválido revienta el CHECK de la migración.
    with pytest.raises(Exception):
        repo.registrar_decision(
            id_solicitud=creada.id_solicitud,
            id_borrador=id_borrador,
            decision="APROBADA",
            doc_hash=_sha("Texto generado.\n"),
            texto_doc="Texto generado.\n",
            validador_hash="cd" * 32,
            rol="APROBADOR_CONTENIDO",
            origen_identidad="origen_trucho",
            version_agente="0.5.10",
            ahora=AHORA,
        )

    assert repo.estado_de(creada.id_solicitud) == "LISTA"
    with _fabrica(base)() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM validaciones WHERE id_borrador = %s",
            (id_borrador,),
        ).fetchone()[0] == 0


@necesita_pg
def test_prosa_importada_entra_en_la_purga(base: str) -> None:
    """La prosa `importado` de una revisión se vacía con la del resto al
    cerrar la solicitud (ADR 0016): quedan hash y marcas, nunca texto."""
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:d10")
    _trabajo_completo(repo, creada.id_solicitud)
    importada = repo.importar_revision(
        id_solicitud=creada.id_solicitud,
        texto="Edición que quedará purgada.\n",
        ahora=AHORA,
    )
    repo.registrar_decision(
        id_solicitud=creada.id_solicitud,
        id_borrador=importada.id_borrador,
        decision="APROBADA",
        doc_hash=_sha("Edición que quedará purgada.\n"),
        texto_doc="Edición que quedará purgada.\n",
        validador_hash="cd" * 32,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="google",
        version_agente="0.5.10",
        ahora=AHORA,
    )

    purgadas = repo.vencer_y_purgar(ahora=AHORA).purgadas
    assert purgadas > 0
    with _fabrica(base)() as conn:
        textos = conn.execute(
            "SELECT texto, texto_hash, clase FROM prosa_transitoria"
            " WHERE id_solicitud = %s",
            (creada.id_solicitud,),
        ).fetchall()
    assert all(t[0] is None for t in textos)
    assert {t[2] for t in textos} >= {"generado", "importado"}
    # Los hashes quedan: la trazabilidad sobrevive a la purga.
    assert all(t[1] is not None for t in textos)


# ============================ flujos de la app ============================

CORREO_SEU = "solicitante@example.invalid"
CORREO_APROBADOR = "aprobador@example.invalid"
CORREO_LECTOR = "lector@example.invalid"


class RepoRevisiones:
    """Repositorio en memoria con el contrato de #153.

    Fiel a lo que la app consume: revisiones por solicitud, `doc_ref` y
    los resultados `sin_cambios`/`importada`/`doc_cambiado`/etc. que el
    repositorio real garantiza en PostgreSQL.
    """

    def __init__(self) -> None:
        self.solicitudes: dict[str, dict[str, Any]] = {}
        self.decisiones: list[dict[str, Any]] = []

    def crear_solicitud(self, **kwargs) -> SolicitudCreada:
        id_solicitud = f"web-{len(self.solicitudes):04d}"
        self.solicitudes[id_solicitud] = {
            "tipo_pieza": kwargs["tipo_pieza"],
            "actividad_ref": kwargs["actividad_ref"],
            "estado_web": "EN_COLA",
            "rol": kwargs["rol"],
            "solicitante_hash": kwargs["solicitante_hash"],
            "canal": kwargs["canal"],
            "creada_en": kwargs["ahora"],
            "ultima_actividad_en": kwargs["ahora"],
            "descripcion": kwargs["descripcion"],
            "campos": kwargs["campos"],
            "texto_generado": None,
            "revisiones": (),
            "doc_ref": None,
            "doc_url": None,
            "texto_vigente": None,
        }
        return SolicitudCreada(
            id_solicitud=id_solicitud, id_ejecucion="webe-x", creada=True
        )

    def lista_con_doc(
        self, id_solicitud: str, doc_ref: str, texto: str
    ) -> None:
        """El estado que deja el worker: `LISTA` con revisión 1 y Doc."""
        s = self.solicitudes[id_solicitud]
        s["estado_web"] = "LISTA"
        s["doc_ref"] = doc_ref
        s["doc_url"] = (
            f"https://docs.google.com/document/d/{doc_ref}/edit"
        )
        s["texto_generado"] = texto
        s["texto_vigente"] = texto
        s["revisiones"] = (
            RevisionPieza(
                id_borrador="borr-1",
                numero_revision=1,
                output_hash=_sha(texto),
                doc_ref=doc_ref,
                head_revision_id="7",
                creada_en=AHORA,
                origen="generada",
            ),
        )

    def bandeja(self) -> list[ItemBandeja]:
        return [
            ItemBandeja(
                id_solicitud=sid,
                tipo_pieza=s["tipo_pieza"],
                actividad_ref=s["actividad_ref"],
                estado_web=s["estado_web"],
                titulo=s["campos"].get("pieza", {}).get("titulo"),
                creada_en=s["creada_en"],
                ultima_actividad_en=s["ultima_actividad_en"],
            )
            for sid, s in self.solicitudes.items()
        ]

    def obtener(self, id_solicitud: str) -> DetalleSolicitud | None:
        s = self.solicitudes.get(id_solicitud)
        if s is None:
            return None
        return DetalleSolicitud(
            id_solicitud=id_solicitud,
            tipo_pieza=s["tipo_pieza"],
            actividad_ref=s["actividad_ref"],
            estado_web=s["estado_web"],
            rol=s["rol"],
            solicitante_hash=s["solicitante_hash"],
            canal=s["canal"],
            creada_en=s["creada_en"],
            ultima_actividad_en=s["ultima_actividad_en"],
            descripcion=s["descripcion"],
            campos=s["campos"],
            texto_generado=s["texto_generado"],
            revisiones=s["revisiones"],
            doc_ref=s["doc_ref"],
            doc_url=s["doc_url"],
            texto_vigente=s["texto_vigente"],
        )

    def estado_de(self, id_solicitud: str) -> str | None:
        s = self.solicitudes.get(id_solicitud)
        return s["estado_web"] if s else None

    def importar_revision(
        self,
        *,
        id_solicitud: str,
        texto: str,
        ahora: datetime | None = None,
    ) -> ResultadoImportacion:
        s = self.solicitudes.get(id_solicitud)
        if s is None:
            return ResultadoImportacion("inexistente")
        if s["estado_web"] != "LISTA" or s["doc_ref"] is None:
            return ResultadoImportacion("no_disponible")
        vigente = s["revisiones"][-1]
        if vigente.output_hash == _sha(texto):
            return ResultadoImportacion("sin_cambios")
        numero = len(s["revisiones"]) + 1
        nuevo = RevisionPieza(
            id_borrador=f"borr-{numero}",
            numero_revision=numero,
            output_hash=_sha(texto),
            doc_ref=s["doc_ref"],
            head_revision_id=None,
            creada_en=ahora or AHORA,
            origen="editada_docs",
        )
        s["revisiones"] = (*s["revisiones"], nuevo)
        s["texto_vigente"] = texto
        return ResultadoImportacion(
            "importada", numero_revision=numero, id_borrador=nuevo.id_borrador
        )

    def registrar_decision(
        self,
        *,
        id_solicitud: str,
        id_borrador: str,
        decision: str,
        doc_hash: str,
        texto_doc: str | None,
        validador_hash: str,
        rol: str,
        origen_identidad: str,
        version_agente: str,
        ahora: datetime | None = None,
    ) -> ResultadoDecisionWeb:
        s = self.solicitudes.get(id_solicitud)
        if s is None:
            return ResultadoDecisionWeb("inexistente")
        if s["estado_web"] != "LISTA":
            return ResultadoDecisionWeb("cerrada")
        vigente = s["revisiones"][-1]
        if vigente.id_borrador != id_borrador:
            return ResultadoDecisionWeb("revision_obsoleta")
        if vigente.output_hash != doc_hash:
            self.importar_revision(
                id_solicitud=id_solicitud,
                texto=texto_doc or "",
                ahora=ahora,
            )
            return ResultadoDecisionWeb("doc_cambiado")
        if any(d["id_borrador"] == id_borrador for d in self.decisiones):
            return ResultadoDecisionWeb("duplicada")
        self.decisiones.append(
            {
                "id_borrador": id_borrador,
                "decision": decision,
                "validador_hash": validador_hash,
                "rol": rol,
                "origen_identidad": origen_identidad,
                "version_agente": version_agente,
            }
        )
        s["estado_web"] = (
            "APROBADA" if decision == "APROBADA" else "DESCARTADA"
        )
        return ResultadoDecisionWeb(
            "aprobada" if decision == "APROBADA" else "descartada",
            id_borrador=id_borrador,
        )


@dataclass
class MundoDocs:
    client: TestClient
    repo: RepoRevisiones
    sesiones: SesionesMemoria
    docs: DocsCanalMemoria


def _mundo_docs(
    modo_demo: bool = False,
) -> MundoDocs:
    padron = PadronRoles(
        {
            CORREO_SEU: "coordinador_seu",
            CORREO_APROBADOR: "APROBADOR_CONTENIDO",
            CORREO_LECTOR: "lector_seu",
        }
    )
    sesiones = SesionesMemoria()
    verificador = VerificadorFake(
        {
            "tok-seu": IdentidadVerificada("s1", CORREO_SEU, "x.invalid"),
            "tok-apro": IdentidadVerificada(
                "s2", CORREO_APROBADOR, "x.invalid"
            ),
            "tok-lector": IdentidadVerificada(
                "s3", CORREO_LECTOR, "x.invalid"
            ),
        }
    )
    repo = RepoRevisiones()
    docs = DocsCanalMemoria()
    from agente1.web.app import CLIENT_ID_PRUEBA

    config = ConfiguracionWeb(
        google_client_id="" if modo_demo else CLIENT_ID_PRUEBA,
        modo_demo=modo_demo,
        modo_prueba=not modo_demo,
        demo_hasta=date(2026, 11, 19) if modo_demo else None,
        demo_correos=(CORREO_SEU, CORREO_APROBADOR) if modo_demo else (),
        cookie_secure=modo_demo,
    )
    app = crear_app(
        config=config,
        verificador=verificador,
        padron=padron,
        repositorio=repo,
        sesiones=sesiones,
        actividades=[],
        exportador=docs,
        version_agente="0.0.0-test",
        hoy=lambda: date(2026, 11, 16),
    )
    base_url = "https://testserver" if modo_demo else "http://testserver"
    return MundoDocs(TestClient(app, base_url=base_url), repo, sesiones, docs)


def _ingresar(client: TestClient, token: str) -> None:
    formulario = client.get("/ingresar")
    marca = 'name="csrf" value="'
    csrf = formulario.text.split(marca, 1)[1].split('"', 1)[0]
    client.post(
        "/ingresar",
        data={"credential": token, "csrf": csrf},
        follow_redirects=False,
    )


def _ingresar_demo(client: TestClient, correo: str) -> None:
    formulario = client.get("/ingresar")
    marca = 'name="csrf" value="'
    csrf = formulario.text.split(marca, 1)[1].split('"', 1)[0]
    client.post(
        "/ingresar",
        data={"correo": correo, "csrf": csrf},
        follow_redirects=False,
    )


def _csrf(mundo: MundoDocs) -> str:
    sesion = next(iter(mundo.sesiones._sesiones.values()))
    return sesion.csrf_token


def _solicitud_lista(
    mundo: MundoDocs, texto: str = "Borrador inicial.\n"
) -> str:
    """Crea la solicitud y la deja en `LISTA` con Doc en el fake."""
    creada = mundo.repo.crear_solicitud(
        idempotency_key="web:k1",
        solicitante_hash="ab" * 32,
        rol="coordinador_seu",
        tipo_pieza="cronica_de_evento",
        actividad_ref=None,
        descripcion="desc",
        campos={"pieza": {}, "pedido": {}},
        canal="web",
        ahora=AHORA,
    )
    resultado = mundo.docs.buscar_o_crear(
        marca=creada.id_solicitud,
        id_solicitud=creada.id_solicitud,
        contenido=texto,
        nombre=None,
    )
    mundo.repo.lista_con_doc(
        creada.id_solicitud, resultado.doc_ref, texto
    )
    return creada.id_solicitud


def test_traer_cambios_sin_cambios_avisa() -> None:
    mundo = _mundo_docs()
    _ingresar(mundo.client, "tok-seu")
    sid = _solicitud_lista(mundo)

    respuesta = mundo.client.post(
        f"/solicitudes/{sid}/traer-cambios",
        data={"csrf": _csrf(mundo)},
    )

    assert respuesta.status_code == 200
    assert "no tiene cambios" in respuesta.text.lower()
    assert len(mundo.repo.obtener(sid).revisiones) == 1


def test_traer_cambios_con_cambios_importa_revision() -> None:
    mundo = _mundo_docs()
    _ingresar(mundo.client, "tok-seu")
    sid = _solicitud_lista(mundo)
    doc_ref = mundo.repo.obtener(sid).doc_ref
    mundo.docs.editar(doc_ref, "Edición de la persona en el Doc.\n")

    respuesta = mundo.client.post(
        f"/solicitudes/{sid}/traer-cambios",
        data={"csrf": _csrf(mundo)},
    )

    assert "Revisión nueva" in respuesta.text
    detalle = mundo.repo.obtener(sid)
    assert len(detalle.revisiones) == 2
    assert detalle.revisiones[1].origen == "editada_docs"
    assert detalle.texto_vigente == "Edición de la persona en el Doc.\n"


def test_detalle_muestra_enlace_doc_y_revisiones() -> None:
    mundo = _mundo_docs()
    _ingresar(mundo.client, "tok-seu")
    sid = _solicitud_lista(mundo)

    respuesta = mundo.client.get(f"/solicitudes/{sid}")

    assert "Editar en Google Docs" in respuesta.text
    assert "editada en Docs" not in respuesta.text  # aún no hay
    assert "generada" in respuesta.text
    assert "vigente" in respuesta.text


def test_aprobar_con_hash_vigente_cierra() -> None:
    mundo = _mundo_docs()
    _ingresar(mundo.client, "tok-apro")
    sid = _solicitud_lista(mundo)
    vigente = mundo.repo.obtener(sid).revisiones[-1]

    respuesta = mundo.client.post(
        f"/solicitudes/{sid}/decidir",
        data={
            "csrf": _csrf(mundo),
            "revision": vigente.id_borrador,
            "accion": "aprobar",
        },
    )

    assert "aprobada" in respuesta.text.lower()
    assert mundo.repo.estado_de(sid) == "APROBADA"
    decision = mundo.repo.decisiones[0]
    assert decision["rol"] == "APROBADOR_CONTENIDO"
    assert decision["origen_identidad"] == "google"
    assert decision["version_agente"] == "0.0.0-test"


def test_aprobar_con_doc_cambiado_rechaza() -> None:
    mundo = _mundo_docs()
    _ingresar(mundo.client, "tok-apro")
    sid = _solicitud_lista(mundo)
    doc_ref = mundo.repo.obtener(sid).doc_ref
    # La persona editó el Doc después de que la página mostró la revisión.
    mundo.docs.editar(doc_ref, "El Doc cambió.\n")
    vigente = mundo.repo.obtener(sid).revisiones[-1]

    respuesta = mundo.client.post(
        f"/solicitudes/{sid}/decidir",
        data={
            "csrf": _csrf(mundo),
            "revision": vigente.id_borrador,
            "accion": "aprobar",
        },
    )

    assert "El Doc cambió" in respuesta.text
    assert mundo.repo.estado_de(sid) == "LISTA"
    assert mundo.repo.decisiones == []


def test_decidir_con_rol_no_autorizado_da_403() -> None:
    mundo = _mundo_docs()
    _ingresar(mundo.client, "tok-lector")
    sid = _solicitud_lista(mundo)
    vigente = mundo.repo.obtener(sid).revisiones[-1]

    respuesta = mundo.client.post(
        f"/solicitudes/{sid}/decidir",
        data={
            "csrf": _csrf(mundo),
            "revision": vigente.id_borrador,
            "accion": "aprobar",
        },
    )

    assert respuesta.status_code == 403
    assert mundo.repo.decisiones == []


def test_decidir_sin_csrf_da_403() -> None:
    mundo = _mundo_docs()
    _ingresar(mundo.client, "tok-apro")
    sid = _solicitud_lista(mundo)

    respuesta = mundo.client.post(
        f"/solicitudes/{sid}/decidir",
        data={"csrf": "trucho", "revision": "borr-1", "accion": "aprobar"},
    )

    assert respuesta.status_code == 403


def test_descartar_cierra_como_descartada() -> None:
    mundo = _mundo_docs()
    _ingresar(mundo.client, "tok-apro")
    sid = _solicitud_lista(mundo)
    vigente = mundo.repo.obtener(sid).revisiones[-1]

    mundo.client.post(
        f"/solicitudes/{sid}/decidir",
        data={
            "csrf": _csrf(mundo),
            "revision": vigente.id_borrador,
            "accion": "descartar",
        },
    )

    assert mundo.repo.estado_de(sid) == "DESCARTADA"


def test_decision_duplicada_no_reescribe() -> None:
    mundo = _mundo_docs()
    _ingresar(mundo.client, "tok-apro")
    sid = _solicitud_lista(mundo)
    vigente = mundo.repo.obtener(sid).revisiones[-1]
    datos = {
        "csrf": _csrf(mundo),
        "revision": vigente.id_borrador,
        "accion": "aprobar",
    }
    mundo.client.post(f"/solicitudes/{sid}/decidir", data=datos)

    respuesta = mundo.client.post(f"/solicitudes/{sid}/decidir", data=datos)

    assert "cerrada" in respuesta.text.lower()
    assert len(mundo.repo.decisiones) == 1


def test_sesion_demo_registra_origen_demo_en_la_decision() -> None:
    mundo = _mundo_docs(modo_demo=True)
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    sid = _solicitud_lista(mundo)
    vigente = mundo.repo.obtener(sid).revisiones[-1]

    mundo.client.post(
        f"/solicitudes/{sid}/decidir",
        data={
            "csrf": _csrf(mundo),
            "revision": vigente.id_borrador,
            "accion": "aprobar",
        },
    )

    assert mundo.repo.decisiones[0]["origen_identidad"] == "demo"


def test_bandeja_muestra_estados_de_revision() -> None:
    mundo = _mundo_docs()
    _ingresar(mundo.client, "tok-seu")
    sid = _solicitud_lista(mundo)

    respuesta = mundo.client.get("/bandeja")
    assert "En revisión" in respuesta.text
    # Tras la aprobación la bandeja muestra el cierre.
    mundo.repo.solicitudes[sid]["estado_web"] = "APROBADA"
    respuesta = mundo.client.get("/bandeja")
    assert "Aprobada" in respuesta.text
