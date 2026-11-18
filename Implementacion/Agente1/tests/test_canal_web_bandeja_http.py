"""Bandeja por HTTP: archivar, eliminar y reintentar, con TestClient.

El mismo criterio de dos niveles del resto del canal web: las reglas del
repositorio están probadas contra PostgreSQL en
`test_canal_web_bandeja_pg.py`; acá se prueba el cableado HTTP — sesión,
CSRF, permiso por dueño, cierre demo (ADR 0019) y las vistas — contra la
app real con repositorios en memoria.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from agente1.canal_form import PadronRoles, hash_correo
from agente1.confirmaciones import ROL_APROBADOR_CONTENIDO
from agente1.web.app import CLIENT_ID_PRUEBA, ConfiguracionWeb, crear_app
from agente1.web.certificados_web import (
    ESTADO_DESCARTADA,
    ESTADO_PENDIENTE,
    LoteCertificados,
    ResultadoDecisionLote,
)
from agente1.web.identidad import IdentidadVerificada, VerificadorFake
from agente1.web.persistencia import (
    ESTADOS_ARCHIVABLES,
    MAX_REINTENTOS,
    DetalleSolicitud,
    ItemBandeja,
)
from agente1.web.sesiones import SesionesMemoria

CORREO_APROBADOR = "aprobador@example.invalid"
CORREO_COORDINADOR = "coordinador@example.invalid"
TOKEN_APROBADOR = "tok-aprobador"
TOKEN_COORDINADOR = "tok-coordinador"
AHORA = datetime(2026, 11, 18, 21, 0, tzinfo=timezone.utc)
HOY_DEMO = date(2026, 11, 18)
DEMO_HASTA = date(2026, 11, 20)
HASH_APROBADOR = hash_correo(CORREO_APROBADOR)
HASH_COORDINADOR = hash_correo(CORREO_COORDINADOR)
HASH_TERCERO = hash_correo("tercero@example.invalid")
CAMPOS = {
    "pieza": {"titulo": "Pieza sintética"},
    "pedido": {"publicos": []},
}


@dataclass
class Pieza:
    """Una pieza del fake: lo que la bandeja y el detalle necesitan."""

    id: str
    estado_web: str
    titulo: str
    dueno: str
    canal: str = "web"
    archivada_en: datetime | None = None
    eliminada_en: datetime | None = None
    resultado_fallido: str | None = None
    reintentos: int = 1
    campos: dict[str, Any] = field(default_factory=lambda: dict(CAMPOS))


class RepositorioWebBandejaMemoria:
    """El puerto del repo web en memoria, con las reglas de ADR 0023."""

    def __init__(self, *piezas: Pieza) -> None:
        self._piezas = {p.id: p for p in piezas}
        self.llamadas: list[tuple[str, str]] = []

    def bandeja(self) -> list[ItemBandeja]:
        return [
            ItemBandeja(
                id_solicitud=p.id,
                tipo_pieza="cronica_de_evento",
                actividad_ref=None,
                estado_web=p.estado_web,
                titulo=p.titulo,
                creada_en=AHORA,
                ultima_actividad_en=AHORA,
                canal=p.canal,
                solicitante_hash=p.dueno,
                archivada_en=p.archivada_en,
            )
            for p in self._piezas.values()
            if p.eliminada_en is None
        ]

    def obtener(self, id_solicitud: str) -> DetalleSolicitud | None:
        p = self._piezas.get(id_solicitud)
        if p is None:
            return None
        return DetalleSolicitud(
            id_solicitud=p.id,
            tipo_pieza="cronica_de_evento",
            actividad_ref=None,
            estado_web=p.estado_web,
            rol="coordinador_seu",
            solicitante_hash=p.dueno,
            canal=p.canal,
            creada_en=AHORA,
            ultima_actividad_en=AHORA,
            descripcion="Descripción sintética.",
            campos=p.campos,
            texto_generado=None,
            revisiones=(),
            archivada_en=p.archivada_en,
            eliminada_en=p.eliminada_en,
            resultado_fallido=p.resultado_fallido,
            reintentos=p.reintentos,
        )

    def encabezado_de(self, id_solicitud: str) -> tuple[str, str] | None:
        p = self._piezas.get(id_solicitud)
        return None if p is None else (p.canal, p.dueno)

    def archivar_solicitud(
        self, *, id_solicitud: str, ahora: datetime | None = None
    ) -> str:
        self.llamadas.append(("archivar", id_solicitud))
        p = self._piezas[id_solicitud]
        if p.archivada_en is not None:
            return "ya_archivada"
        if p.estado_web not in ESTADOS_ARCHIVABLES:
            return "no_archivable"
        p.archivada_en = ahora or AHORA
        return "archivada"

    def desarchivar_solicitud(self, *, id_solicitud: str) -> str:
        self.llamadas.append(("desarchivar", id_solicitud))
        p = self._piezas[id_solicitud]
        if p.archivada_en is None:
            return "sin_marca"
        p.archivada_en = None
        return "desarchivada"

    def eliminar_solicitud(
        self, *, id_solicitud: str, ahora: datetime | None = None
    ) -> str:
        self.llamadas.append(("eliminar", id_solicitud))
        p = self._piezas[id_solicitud]
        if p.eliminada_en is not None:
            return "ya_eliminada"
        if p.estado_web not in ESTADOS_ARCHIVABLES:
            return "no_eliminable"
        p.eliminada_en = ahora or AHORA
        return "eliminada"

    def reintentar_solicitud(
        self, *, id_solicitud: str, ahora: datetime | None = None
    ) -> str:
        self.llamadas.append(("reintentar", id_solicitud))
        p = self._piezas[id_solicitud]
        if p.estado_web != "ERROR":
            return "en_curso" if p.estado_web == "EN_COLA" else (
                "no_reintentable"
            )
        if p.reintentos > MAX_REINTENTOS:
            return "limite_reintentos"
        p.estado_web = "EN_COLA"
        p.reintentos += 1
        p.archivada_en = None
        return "encolado"


def _lote(
    id_lote: str,
    estado: str,
    *,
    origen_creacion: str | None = None,
) -> LoteCertificados:
    lote = LoteCertificados(
        id_lote=id_lote,
        id_actividad="BANDEJA-HTTP-1",
        objeto_lote=hashlib.sha256(id_lote.encode()).hexdigest(),
        hash_lista=hashlib.sha256(b"lista"),
        actividad={"titulo": "Actividad sintética"},
        personas=(),
        cantidad_personas=0,
        linea_descriptiva="Línea sintética",
        linea_descriptiva_hash=hashlib.sha256(b"linea").hexdigest(),
        plantilla_muestra="certificado_seu_aprobacion_v1",
        estado=estado,
        generada_por_hash=HASH_APROBADOR,
        creada_en=AHORA,
    )
    if origen_creacion is not None:
        object.__setattr__(lote, "origen_creacion", origen_creacion)
    return lote


class RepositorioLotesArchivoMemoria:
    """El puerto de lotes en memoria, sólo lo que la bandeja usa."""

    def __init__(self, *lotes: LoteCertificados) -> None:
        self._lotes = {lote.id_lote: lote for lote in lotes}
        self.llamadas: list[tuple[str, str]] = []

    def listar(
        self, *, incluir_archivados: bool = False
    ) -> list[LoteCertificados]:
        return [
            lote for lote in self._lotes.values()
            if incluir_archivados
            or getattr(lote, "archivada_en", None) is None
        ]

    def obtener(self, id_lote: str) -> LoteCertificados | None:
        return self._lotes.get(id_lote)

    def decidir(self, **datos: Any) -> ResultadoDecisionLote:
        return ResultadoDecisionLote("duplicada")

    def archivar_lote(
        self, *, id_lote: str, ahora: datetime | None = None
    ) -> str:
        self.llamadas.append(("archivar", id_lote))
        lote = self._lotes[id_lote]
        if getattr(lote, "archivada_en", None) is not None:
            return "ya_archivado"
        if lote.estado != ESTADO_DESCARTADA:
            return "no_archivable"
        object.__setattr__(lote, "archivada_en", ahora or AHORA)
        return "archivado"

    def desarchivar_lote(self, *, id_lote: str) -> str:
        self.llamadas.append(("desarchivar", id_lote))
        lote = self._lotes[id_lote]
        if getattr(lote, "archivada_en", None) is None:
            return "sin_marca"
        object.__setattr__(lote, "archivada_en", None)
        return "desarchivado"


@dataclass
class Mundo:
    client: TestClient
    repo: RepositorioWebBandejaMemoria
    lotes: RepositorioLotesArchivoMemoria
    sesiones: SesionesMemoria


def _mundo(
    *,
    piezas: tuple[Pieza, ...] = (),
    lotes: tuple[LoteCertificados, ...] = (),
    modo_demo: bool = False,
) -> Mundo:
    padron = PadronRoles(
        {
            CORREO_APROBADOR: ROL_APROBADOR_CONTENIDO,
            CORREO_COORDINADOR: "coordinador_seu",
        }
    )
    sesiones = SesionesMemoria(ahora=lambda: AHORA)
    repo = RepositorioWebBandejaMemoria(*piezas)
    repo_lotes = RepositorioLotesArchivoMemoria(*lotes)
    config = ConfiguracionWeb(
        google_client_id="" if modo_demo else CLIENT_ID_PRUEBA,
        modo_prueba=not modo_demo,
        modo_demo=modo_demo,
        demo_hasta=DEMO_HASTA if modo_demo else None,
        demo_correos=(
            (CORREO_APROBADOR, CORREO_COORDINADOR)
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
        repositorio=repo,
        sesiones=sesiones,
        actividades=[],
        lotes=repo_lotes,
        hoy=lambda: HOY_DEMO,
        version_agente="0.12.0",
    )
    base_url = "https://testserver" if modo_demo else "http://testserver"
    return Mundo(TestClient(app, base_url=base_url), repo, repo_lotes, sesiones)


def _csrf_login(client: TestClient) -> str:
    formulario = client.get("/ingresar")
    marca = 'name="csrf" value="'
    return formulario.text.split(marca, 1)[1].split('"', 1)[0]


def _ingresar(client: TestClient, token: str) -> None:
    respuesta = client.post(
        "/ingresar",
        data={"credential": token, "csrf": _csrf_login(client)},
        follow_redirects=False,
    )
    assert respuesta.status_code == 303


def _ingresar_demo(client: TestClient, correo: str) -> None:
    respuesta = client.post(
        "/ingresar",
        data={"correo": correo, "csrf": _csrf_login(client)},
        follow_redirects=False,
    )
    assert respuesta.status_code == 303


def _csrf(mundo: Mundo) -> str:
    return next(iter(mundo.sesiones._sesiones.values())).csrf_token


# --- permisos por fila ------------------------------------------------------


def test_bandeja_muestra_acciones_solo_del_dueno() -> None:
    """El coordinador archiva y elimina lo suyo; lo de terceros ni se
    ofrece, y lo que está en curso no tiene acciones."""
    propia_error = Pieza(
        "web-propia-error", "ERROR", "Propia con error",
        dueno=HASH_COORDINADOR,
    )
    ajena_error = Pieza(
        "web-ajena-error", "ERROR", "Ajena con error",
        dueno=HASH_TERCERO,
    )
    propia_viva = Pieza(
        "web-propia-viva", "EN_COLA", "Propia en curso",
        dueno=HASH_COORDINADOR,
    )
    mundo = _mundo(piezas=(propia_error, ajena_error, propia_viva))
    _ingresar(mundo.client, TOKEN_COORDINADOR)

    html = mundo.client.get("/bandeja").text
    assert f'action="/solicitudes/{propia_error.id}/archivar"' in html
    assert f'action="/solicitudes/{propia_error.id}/eliminar"' in html
    assert f'action="/solicitudes/{ajena_error.id}/archivar"' not in html
    assert f'action="/solicitudes/{ajena_error.id}/eliminar"' not in html
    assert f'action="/solicitudes/{propia_viva.id}/archivar"' not in html
    # Sin archivadas, no se ofrece el filtro vacío.
    assert 'href="/bandeja?archivadas=1"' not in html


def test_aprobador_archiva_lo_ajeno_pero_no_lo_elimina() -> None:
    """El aprobador puede archivar la pieza de otro; eliminarla es sólo
    del dueño (ADR 0023)."""
    ajena = Pieza(
        "web-ajena-descartada", "DESCARTADA", "Ajena descartada",
        dueno=HASH_TERCERO,
    )
    mundo = _mundo(piezas=(ajena,))
    _ingresar(mundo.client, TOKEN_APROBADOR)

    html = mundo.client.get("/bandeja").text
    assert f'action="/solicitudes/{ajena.id}/archivar"' in html
    assert f'action="/solicitudes/{ajena.id}/eliminar"' not in html


def test_bandeja_sin_login_redirige() -> None:
    mundo = _mundo()
    respuesta = mundo.client.get("/bandeja", follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/ingresar"


# --- archivar, desarchivar, eliminar ---------------------------------------


def test_archivar_y_desarchivar_por_http() -> None:
    propia = Pieza(
        "web-propia-cerrada", "DESCARTADA", "Propia descartada",
        dueno=HASH_COORDINADOR,
    )
    mundo = _mundo(piezas=(propia,))
    _ingresar(mundo.client, TOKEN_COORDINADOR)
    csrf = _csrf(mundo)

    # Sin CSRF no pasa nada.
    rechazado = mundo.client.post(
        f"/solicitudes/{propia.id}/archivar", data={"csrf": "x"}
    )
    assert rechazado.status_code == 403
    assert mundo.repo.llamadas == []

    respuesta = mundo.client.post(
        f"/solicitudes/{propia.id}/archivar",
        data={"csrf": csrf},
        follow_redirects=False,
    )
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/bandeja"

    html = mundo.client.get("/bandeja").text
    assert propia.titulo not in html
    assert 'href="/bandeja?archivadas=1"' in html

    archivadas = mundo.client.get("/bandeja?archivadas=1").text
    assert propia.titulo in archivadas
    assert f'action="/solicitudes/{propia.id}/desarchivar"' in archivadas
    assert f'action="/solicitudes/{propia.id}/archivar"' not in archivadas

    volver = mundo.client.post(
        f"/solicitudes/{propia.id}/desarchivar",
        data={"csrf": csrf},
        follow_redirects=False,
    )
    assert volver.status_code == 303
    assert volver.headers["location"] == "/bandeja?archivadas=1"
    assert propia.titulo in mundo.client.get("/bandeja").text


def test_eliminar_del_dueno_la_oculta_de_toda_vista() -> None:
    propia = Pieza(
        "web-propia-prueba", "ERROR", "Prueba a eliminar",
        dueno=HASH_COORDINADOR,
    )
    mundo = _mundo(piezas=(propia,))
    _ingresar(mundo.client, TOKEN_COORDINADOR)

    respuesta = mundo.client.post(
        f"/solicitudes/{propia.id}/eliminar",
        data={"csrf": _csrf(mundo)},
        follow_redirects=False,
    )
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/bandeja"

    assert propia.titulo not in mundo.client.get("/bandeja").text
    assert (
        propia.titulo not in mundo.client.get("/bandeja?archivadas=1").text
    )
    # El detalle sigue: sólo desapareció de la bandeja, y lo explica.
    detalle = mundo.client.get(f"/solicitudes/{propia.id}").text
    assert "fue eliminada de la bandeja por quien la creó" in detalle


def test_eliminar_pieza_ajena_rechazado() -> None:
    ajena = Pieza(
        "web-ajena-error", "ERROR", "Ajena con error",
        dueno=HASH_TERCERO,
    )
    mundo = _mundo(piezas=(ajena,))
    _ingresar(mundo.client, TOKEN_APROBADOR)

    respuesta = mundo.client.post(
        f"/solicitudes/{ajena.id}/eliminar",
        data={"csrf": _csrf(mundo)},
        follow_redirects=False,
    )
    assert respuesta.status_code == 403
    assert ("eliminar", ajena.id) not in mundo.repo.llamadas


def test_aviso_de_accion_rechazada_en_la_bandeja() -> None:
    """El POST que el repositorio rechaza vuelve con un aviso legible de
    código cerrado; un código desconocido no muestra nada."""
    viva = Pieza(
        "web-propia-viva", "EN_COLA", "Propia en curso",
        dueno=HASH_COORDINADOR,
    )
    mundo = _mundo(piezas=(viva,))
    _ingresar(mundo.client, TOKEN_COORDINADOR)

    respuesta = mundo.client.post(
        f"/solicitudes/{viva.id}/archivar",
        data={"csrf": _csrf(mundo)},
        follow_redirects=False,
    )
    assert respuesta.status_code == 303
    assert "aviso=no_archivable" in respuesta.headers["location"]
    html = mundo.client.get("/bandeja?aviso=no_archivable").text
    assert "No se archivó" in html
    sin_aviso = mundo.client.get("/bandeja?aviso=codigo_raro").text
    assert "No se archivó" not in sin_aviso


# --- modo demo no toca lo real ---------------------------------------------


def test_demo_solo_opera_piezas_de_la_demo() -> None:
    """La sesión demo archiva lo que creó la propia demo; lo real ni se
    ofrece, porque la marca cambiaría la bandeja de todos (ADR 0019)."""
    real = Pieza(
        "web-real-error", "ERROR", "Real con error",
        dueno=HASH_APROBADOR,
    )
    demo = Pieza(
        "web-demo-error", "ERROR", "Demo con error",
        dueno=HASH_COORDINADOR, canal="web-demo",
    )
    mundo = _mundo(piezas=(real, demo), modo_demo=True)
    _ingresar_demo(mundo.client, CORREO_COORDINADOR)
    csrf = _csrf(mundo)

    rechazado = mundo.client.post(
        f"/solicitudes/{real.id}/archivar",
        data={"csrf": csrf},
        follow_redirects=False,
    )
    assert rechazado.status_code == 403

    aceptado = mundo.client.post(
        f"/solicitudes/{demo.id}/archivar",
        data={"csrf": csrf},
        follow_redirects=False,
    )
    assert aceptado.status_code == 303
    assert ("archivar", demo.id) in mundo.repo.llamadas


# --- reintentar -------------------------------------------------------------


def test_reintentar_pieza_con_error() -> None:
    propia = Pieza(
        "web-propia-error", "ERROR", "Propia con error",
        dueno=HASH_COORDINADOR, resultado_fallido="destination_failure",
    )
    mundo = _mundo(piezas=(propia,))
    _ingresar(mundo.client, TOKEN_COORDINADOR)

    detalle = mundo.client.get(f"/solicitudes/{propia.id}").text
    # El motivo legible sale del resultado durable, no del log del worker.
    assert "no respondió" in detalle
    assert f'action="/solicitudes/{propia.id}/reintentar"' in detalle

    respuesta = mundo.client.post(
        f"/solicitudes/{propia.id}/reintentar",
        data={"csrf": _csrf(mundo)},
        follow_redirects=False,
    )
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == f"/solicitudes/{propia.id}"
    assert ("reintentar", propia.id) in mundo.repo.llamadas
    assert propia.estado_web == "EN_COLA"


def test_reintentar_agotado_avisa_y_no_ofrece_boton() -> None:
    agotada = Pieza(
        "web-propia-agotada", "ERROR", "Propia agotada",
        dueno=HASH_COORDINADOR, reintentos=MAX_REINTENTOS + 1,
    )
    mundo = _mundo(piezas=(agotada,))
    _ingresar(mundo.client, TOKEN_COORDINADOR)

    detalle = mundo.client.get(f"/solicitudes/{agotada.id}").text
    assert "agotó sus reintentos" in detalle
    assert f'action="/solicitudes/{agotada.id}/reintentar"' not in detalle

    respuesta = mundo.client.post(
        f"/solicitudes/{agotada.id}/reintentar",
        data={"csrf": _csrf(mundo)},
        follow_redirects=False,
    )
    assert respuesta.status_code == 409
    assert "agotó sus reintentos" in respuesta.text


# --- lotes ------------------------------------------------------------------


def test_lotes_archivar_y_desarchivar_por_http() -> None:
    pendiente = _lote("lote-pendiente-http", ESTADO_PENDIENTE)
    descartado = _lote(
        "lote-descartado-http", ESTADO_DESCARTADA,
        origen_creacion="google",
    )
    mundo = _mundo(lotes=(pendiente, descartado))
    _ingresar(mundo.client, TOKEN_APROBADOR)
    csrf = _csrf(mundo)

    html = mundo.client.get("/bandeja").text
    # Pendiente no se archiva: esconder una decisión esperando es mentir.
    assert f'action="/certificados/{pendiente.id_lote}/archivar"' not in html
    assert f'action="/certificados/{descartado.id_lote}/archivar"' in html

    respuesta = mundo.client.post(
        f"/certificados/{descartado.id_lote}/archivar",
        data={"csrf": csrf},
        follow_redirects=False,
    )
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/bandeja#certificados"

    bandeja = mundo.client.get("/bandeja").text
    assert descartado.id_lote not in bandeja
    archivadas = mundo.client.get("/bandeja?archivadas=1").text
    assert descartado.id_lote in archivadas
    assert (
        f'action="/certificados/{descartado.id_lote}/desarchivar"'
        in archivadas
    )

    rechazado = mundo.client.post(
        f"/certificados/{pendiente.id_lote}/archivar",
        data={"csrf": csrf},
        follow_redirects=False,
    )
    assert rechazado.status_code == 303
    assert "aviso=no_archivable" in rechazado.headers["location"]

    volver = mundo.client.post(
        f"/certificados/{descartado.id_lote}/desarchivar",
        data={"csrf": csrf},
        follow_redirects=False,
    )
    assert volver.status_code == 303
    assert volver.headers["location"] == "/bandeja?archivadas=1#certificados"
    assert descartado.id_lote in mundo.client.get("/bandeja").text


def test_lotes_archivar_requiere_aprobador() -> None:
    descartado = _lote("lote-descartado-rol", ESTADO_DESCARTADA)
    mundo = _mundo(lotes=(descartado,))
    _ingresar(mundo.client, TOKEN_COORDINADOR)

    respuesta = mundo.client.post(
        f"/certificados/{descartado.id_lote}/archivar",
        data={"csrf": _csrf(mundo)},
        follow_redirects=False,
    )
    assert respuesta.status_code == 403
    assert mundo.lotes.llamadas == []
