"""Emisión durable del lote de certificados en la web (#168, contrato).

El servicio `EmisionCertificadosWeb` lo implementa el backend del
contrato; acá se prueba la UI contra un fake del puerto inyectado en
`crear_app`:

- El **GET** de `/certificados/{id}/emision` sólo consulta: muestra el
  estado en castellano, los bloqueos accionables y la distinción
  «demostración» vs «oficiales enviados», y nunca encola.
- El **POST** es la única vía que pide la emisión: exige sesión, CSRF,
  rol y el hash persistido del lote, y arma el actor desde la sesión.
- La **descarga** del ZIP de demostración va autorizada y no toca
  estado; el nombre del archivo no lleva datos personales.
- El **checkbox** «Apruebo la línea descriptiva y la lista del lote» es
  obligatorio en lotes del pedido nuevo (`origen_creacion` declarado) y
  el puente asienta la `apruebo_contenido` de la línea exacta además de
  la `apruebo_lote`; en lotes legacy nada de eso cambia.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agente1.canal_form import PadronRoles, hash_correo
from agente1.certificados_emision import PersonaCierre
from agente1.confirmaciones import ROL_APROBADOR_CONTENIDO
from agente1.decisiones_form import TIPO_LINEA_DESCRIPTIVA, RegistroDecisiones
from agente1.linea_descriptiva import (
    linea_descriptiva_aprobada,
    revisar_aprobacion_lote,
)
from agente1.web.app import CLIENT_ID_PRUEBA, ConfiguracionWeb, crear_app
from agente1.web.certificados_web import (
    ESTADO_APROBADA,
    ESTADO_PENDIENTE,
    LoteCertificados,
    ResultadoDecisionLote,
)
from agente1.web.identidad import IdentidadVerificada, VerificadorFake
from agente1.web.sesiones import SesionesMemoria

CORREO_APROBADOR = "aprobador@example.invalid"
CORREO_COORDINADOR = "coordinador@example.invalid"
TOKEN_APROBADOR = "tok-aprobador"
TOKEN_COORDINADOR = "tok-coordinador"
HOY_DEMO = date(2026, 11, 16)
DEMO_HASTA = date(2026, 11, 19)
AHORA = datetime(2026, 11, 17, 9, 0, tzinfo=timezone.utc)

ACTIVIDAD = {
    "titulo": "Curso Inteligencia Artificial Aplicada a la Gestión Documental",
    "duracion_horas": "24",
    "modalidad": "online y autogestionado",
    "fecha_inicio": "2026-06-25",
    "organiza": "Facultad de Ingeniería del Ejército",
}
LINEA = (
    "Curso introductorio sobre herramientas de inteligencia artificial "
    "para organizar y analizar información institucional."
)


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
    )


def _lote(
    *,
    estado: str = ESTADO_PENDIENTE,
    origen_creacion: str | None = None,
) -> LoteCertificados:
    lote = LoteCertificados(
        id_lote="lote-abc123",
        id_actividad="FIE-DIF-02",
        objeto_lote="f" * 64,
        hash_lista="e" * 64,
        actividad=dict(ACTIVIDAD),
        personas=_personas(),
        cantidad_personas=1,
        linea_descriptiva=LINEA,
        linea_descriptiva_hash=hashlib.sha256(
            LINEA.encode("utf-8")
        ).hexdigest(),
        plantilla_muestra="certificado_seu_aprobacion_v1",
        estado=estado,
        generada_por_hash=hash_correo(CORREO_APROBADOR),
        creada_en=AHORA,
    )
    if origen_creacion is not None:
        object.__setattr__(lote, "origen_creacion", origen_creacion)
    return lote


class ErrorEmision(RuntimeError):
    """El `ErrorEmisionWeb` del contrato: `RuntimeError` con `code`."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _estado(estado: str = "SIN_PEDIDO", **cambios) -> SimpleNamespace:
    """El `EstadoEmisionWeb` del contrato, por atributos."""
    datos: dict[str, Any] = {
        "codigo": None,
        "bloqueos": (),
        "generadas": 0,
        "enviadas": 0,
        "fallidas": 0,
        "es_demo": False,
        "disponible": False,
        "descargable": False,
    }
    datos.update(cambios)
    return SimpleNamespace(estado=estado, **datos)


class EmisionFalsa:
    """El puerto `EmisionCertificadosWeb` en memoria.

    Registra las llamadas para afirmar lo que la UI hace y lo que no:
    el GET nunca encola y el POST llega al servicio con el actor de la
    sesión y el hash persistido.
    """

    def __init__(self, estado: SimpleNamespace | None = None) -> None:
        self.estado = estado or _estado()
        self.consultas: list[tuple[str, object]] = []
        self.solicitudes: list[tuple[str, str, object]] = []
        self.descargas: list[tuple[str, object]] = []
        self.zip = b"PK\x03\x04-demo"
        self.error_consultar: str | None = None
        self.error_solicitar: str | None = None
        self.error_descargar: str | None = None

    def consultar(self, id_lote: str, *, actor) -> SimpleNamespace:
        self.consultas.append((id_lote, actor))
        if self.error_consultar:
            raise ErrorEmision(self.error_consultar)
        return self.estado

    def solicitar(
        self, id_lote: str, *, hash_lote: str, actor
    ) -> SimpleNamespace:
        self.solicitudes.append((id_lote, hash_lote, actor))
        if self.error_solicitar:
            raise ErrorEmision(self.error_solicitar)
        return self.estado

    def descargar(self, id_lote: str, *, actor) -> bytes:
        self.descargas.append((id_lote, actor))
        if self.error_descargar:
            raise ErrorEmision(self.error_descargar)
        return self.zip


class RepositorioLotesMemoria:
    """El puerto del repositorio de lotes, en memoria, para la app."""

    def __init__(self, lotes: tuple[LoteCertificados, ...] = ()) -> None:
        self._lotes = {lote.id_lote: lote for lote in lotes}
        self.llamadas_decidir: list[dict[str, Any]] = []

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
        self.llamadas_decidir.append(
            {"id_lote": id_lote, "accion": accion}
        )
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
            estado=ESTADO_APROBADA if accion == "aprobar" else "DESCARTADA",
            decidida_en=ahora or AHORA,
            decidida_por_hash=validador_hash,
            rol_decision=rol,
            origen_identidad=origen_identidad,
            version_agente=version_agente,
        )
        # `origen_creacion` es columna en el backend: la fila la conserva
        # igual que conserva objeto y generador. `replace` no la ve como
        # campo en este worktree y la reponemos igual que la lectura real.
        origen = getattr(lote, "origen_creacion", None)
        if origen is not None:
            object.__setattr__(nuevo, "origen_creacion", origen)
        self._lotes[id_lote] = nuevo
        return ResultadoDecisionLote(
            "aprobada" if accion == "aprobar" else "descartada",
            id_lote=id_lote,
        )


class _RepositorioWebVacio:
    def bandeja(self) -> list:
        return []

    def obtener(self, id_solicitud: str):
        return None


@dataclass
class Mundo:
    client: TestClient
    lotes: RepositorioLotesMemoria
    sesiones: SesionesMemoria
    emision: EmisionFalsa | None


def _mundo(
    lotes: tuple[LoteCertificados, ...] = (),
    *,
    emision: EmisionFalsa | None = None,
    registro_decisiones=None,
    modo_demo: bool = False,
) -> Mundo:
    padron = PadronRoles(
        {
            CORREO_APROBADOR: ROL_APROBADOR_CONTENIDO,
            CORREO_COORDINADOR: "coordinador_seu",
        }
    )
    sesiones = SesionesMemoria()
    config = ConfiguracionWeb(
        google_client_id="" if modo_demo else CLIENT_ID_PRUEBA,
        modo_demo=modo_demo,
        modo_prueba=not modo_demo,
        demo_hasta=DEMO_HASTA if modo_demo else None,
        demo_correos=(
            (CORREO_APROBADOR, CORREO_COORDINADOR) if modo_demo else ()
        ),
        cookie_secure=modo_demo,
    )
    repo_lotes = RepositorioLotesMemoria(lotes)
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
        actividades=[],
        lotes=repo_lotes,
        hoy=lambda: HOY_DEMO,
        version_agente="0.9.0",
        registro_decisiones=registro_decisiones,
        emision_certificados=emision,
    )
    base_url = "https://testserver" if modo_demo else "http://testserver"
    return Mundo(TestClient(app, base_url=base_url), repo_lotes, sesiones, emision)


def _csrf_login(client: TestClient) -> str:
    formulario = client.get("/ingresar")
    return formulario.text.split('name="csrf" value="', 1)[1].split('"', 1)[0]


def _ingresar(client: TestClient, token: str = TOKEN_APROBADOR) -> None:
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


def _post_emision(
    mundo: Mundo, id_lote: str = "lote-abc123", **datos: str
):
    base = {"csrf": _csrf(mundo), "hash_lote": "f" * 64}
    base.update(datos)
    return mundo.client.post(
        f"/certificados/{id_lote}/emision", data=base
    )


def _decidir(mundo: Mundo, id_lote: str = "lote-abc123", **datos: str):
    base = {
        "csrf": _csrf(mundo),
        "hash_lote": "f" * 64,
        "accion": "aprobar",
    }
    base.update(datos)
    return mundo.client.post(
        f"/certificados/{id_lote}/decidir", data=base
    )


# --- el servicio ausente mantiene el comportamiento legacy -------------------


def test_sin_servicio_no_hay_rutas_ni_enlace() -> None:
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),))
    _ingresar(mundo.client)
    pagina = mundo.client.get("/certificados/lote-abc123")
    assert pagina.status_code == 200
    assert "/emision" not in pagina.text
    assert (
        mundo.client.get("/certificados/lote-abc123/emision").status_code
        == 404
    )
    assert (
        mundo.client.get(
            "/certificados/lote-abc123/emision/descargar"
        ).status_code
        == 404
    )


# --- vista de emisión ---------------------------------------------------------


def test_get_emision_muestra_estado_y_solo_consulta() -> None:
    emision = EmisionFalsa(
        _estado("BLOQUEADA", bloqueos=("signature_resources_missing",))
    )
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    pagina = mundo.client.get("/certificados/lote-abc123/emision")
    assert pagina.status_code == 200
    assert "Bloqueada" in pagina.text
    assert "Faltan las firmas en custodia" in pagina.text
    # El GET consultó y nada más: no se pidió ni se descargó nada.
    assert len(emision.consultas) == 1
    assert emision.solicitudes == []
    assert emision.descargas == []


def test_get_emision_sin_pedido_no_ofrece_formulario() -> None:
    emision = EmisionFalsa(_estado("SIN_PEDIDO"))
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    pagina = mundo.client.get("/certificados/lote-abc123/emision")
    assert pagina.status_code == 200
    assert "Sin emisión pedida" in pagina.text
    assert "Pedir emisión" not in pagina.text


def test_get_emision_con_disponible_ofrece_el_post() -> None:
    emision = EmisionFalsa(_estado("SIN_PEDIDO", disponible=True))
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    pagina = mundo.client.get("/certificados/lote-abc123/emision")
    assert "Pedir emisión" in pagina.text


def test_emision_indeterminada_se_nombra_sin_reintento() -> None:
    emision = EmisionFalsa(_estado("EMISION_INDETERMINADA"))
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    pagina = mundo.client.get("/certificados/lote-abc123/emision")
    assert "indeterminada" in pagina.text
    assert "no reintenta" in pagina.text


def test_consultar_rechazado_da_sin_permiso() -> None:
    emision = EmisionFalsa()
    emision.error_consultar = "no_es_generador"
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    assert (
        mundo.client.get("/certificados/lote-abc123/emision").status_code
        == 403
    )


def test_lote_aprobado_enlaza_a_la_emision() -> None:
    mundo = _mundo(
        (_lote(estado=ESTADO_APROBADA),), emision=EmisionFalsa()
    )
    _ingresar(mundo.client)
    pagina = mundo.client.get("/certificados/lote-abc123")
    assert "/certificados/lote-abc123/emision" in pagina.text


def test_puertas_de_emision() -> None:
    emision = EmisionFalsa()
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    respuesta = mundo.client.get(
        "/certificados/lote-abc123/emision", follow_redirects=False
    )
    assert respuesta.status_code == 303
    _ingresar(mundo.client, TOKEN_COORDINADOR)
    assert (
        mundo.client.get("/certificados/lote-abc123/emision").status_code
        == 403
    )
    assert emision.consultas == []


def test_emision_de_lote_inexistente_da_404() -> None:
    mundo = _mundo((), emision=EmisionFalsa())
    _ingresar(mundo.client)
    assert (
        mundo.client.get("/certificados/lote-nada/emision").status_code
        == 404
    )


# --- POST: la única vía que encola ---------------------------------------------


def test_post_emision_pasa_actor_y_hash_al_servicio() -> None:
    emision = EmisionFalsa(_estado("EN_COLA"))
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    pagina = _post_emision(mundo)
    assert pagina.status_code == 200
    assert "En cola" in pagina.text
    assert len(emision.solicitudes) == 1
    id_lote, hash_lote, actor = emision.solicitudes[0]
    assert id_lote == "lote-abc123"
    assert hash_lote == "f" * 64
    assert actor.solicitante_hash == hash_correo(CORREO_APROBADOR)
    assert actor.rol == ROL_APROBADOR_CONTENIDO
    assert actor.origen_identidad == "google"
    assert actor.modo_demo is False


def test_post_emision_exige_csrf() -> None:
    emision = EmisionFalsa()
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    respuesta = mundo.client.post(
        "/certificados/lote-abc123/emision",
        data={"csrf": "inventado", "hash_lote": "f" * 64},
    )
    assert respuesta.status_code == 403
    assert emision.solicitudes == []


def test_post_emision_exige_rol_aprobador() -> None:
    emision = EmisionFalsa()
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client, TOKEN_COORDINADOR)
    assert _post_emision(mundo).status_code == 403
    assert emision.solicitudes == []


def test_post_emision_con_hash_viejo_no_encola() -> None:
    emision = EmisionFalsa()
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    respuesta = _post_emision(mundo, hash_lote="0" * 64)
    assert respuesta.status_code == 409
    assert "hash del lote no coincide" in respuesta.text
    assert emision.solicitudes == []


def test_doble_post_devuelve_el_trabajo_del_servicio() -> None:
    emision = EmisionFalsa(_estado("EN_COLA"))
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    primero = _post_emision(mundo)
    segundo = _post_emision(mundo)
    assert primero.status_code == 200 and segundo.status_code == 200
    assert "En cola" in segundo.text
    # La deduplicación es durable, del servicio: la UI le pasa ambos
    # pedidos y muestra lo que el servicio devuelve.
    assert len(emision.solicitudes) == 2


def test_error_del_servicio_muestra_aviso_sin_encolar() -> None:
    emision = EmisionFalsa()
    emision.error_solicitar = "lote_no_aprobado"
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    respuesta = _post_emision(mundo)
    assert respuesta.status_code == 200
    assert "todavía no está aprobado" in respuesta.text


# --- descarga del ZIP de demostración -------------------------------------------


def test_descargar_entrega_el_zip_con_nombre_seguro() -> None:
    emision = EmisionFalsa(
        _estado("GENERADA_DEMO", descargable=True, es_demo=True)
    )
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    respuesta = mundo.client.get(
        "/certificados/lote-abc123/emision/descargar"
    )
    assert respuesta.status_code == 200
    assert respuesta.content == b"PK\x03\x04-demo"
    assert respuesta.headers["content-type"] == "application/zip"
    nombre = respuesta.headers["content-disposition"]
    assert "certificados-demo-lote-abc123.zip" in nombre
    assert "@" not in nombre
    assert len(emision.descargas) == 1
    assert emision.descargas[0][0] == "lote-abc123"


def test_descargar_rechazado_da_sin_permiso() -> None:
    emision = EmisionFalsa()
    emision.error_descargar = "estado_invalido"
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    assert (
        mundo.client.get(
            "/certificados/lote-abc123/emision/descargar"
        ).status_code
        == 403
    )


def test_descargar_no_ofrece_enlace_hasta_generada_demo() -> None:
    emision = EmisionFalsa(_estado("EMITIENDO", es_demo=True))
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    pagina = mundo.client.get("/certificados/lote-abc123/emision")
    assert "emision/descargar" not in pagina.text


# --- la distinción demostración vs oficiales -------------------------------------


def test_emision_demo_se_marca_como_prueba_sin_envio() -> None:
    emision = EmisionFalsa(
        _estado(
            "GENERADA_DEMO",
            es_demo=True,
            generadas=6,
            descargable=True,
        )
    )
    lote = _lote(estado=ESTADO_APROBADA, origen_creacion="demo")
    mundo = _mundo((lote,), emision=emision, modo_demo=True)
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    pagina = mundo.client.get("/certificados/lote-abc123/emision")
    assert pagina.status_code == 200
    assert "Generada · demostración" in pagina.text
    assert "documentos de prueba" in pagina.text
    assert "sin validez institucional" in pagina.text
    assert "de demostración (no enviadas)" in pagina.text
    assert "emision/descargar" in pagina.text


def test_emision_oficial_muestra_generadas_y_enviadas() -> None:
    emision = EmisionFalsa(
        _estado("EMITIDA_PARCIAL", generadas=6, enviadas=5, fallidas=1)
    )
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    pagina = mundo.client.get("/certificados/lote-abc123/emision")
    assert "Emitida parcialmente" in pagina.text
    assert "Enviadas" in pagina.text
    assert "documentos de prueba" not in pagina.text


def test_lote_demo_fuera_de_demo_no_accede_a_emision() -> None:
    lote = _lote(estado=ESTADO_APROBADA, origen_creacion="demo")
    mundo = _mundo((lote,), emision=EmisionFalsa())
    _ingresar(mundo.client)
    # Sesión Google en instancia normal: el lote demo está aislado.
    assert (
        mundo.client.get("/certificados/lote-abc123/emision").status_code
        == 403
    )


def test_actor_demo_declara_modo_demo() -> None:
    emision = EmisionFalsa(_estado("EN_COLA", es_demo=True))
    lote = _lote(estado=ESTADO_APROBADA, origen_creacion="demo")
    mundo = _mundo((lote,), emision=emision, modo_demo=True)
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    _post_emision(mundo)
    _, _, actor = emision.solicitudes[0]
    assert actor.modo_demo is True
    assert actor.origen_identidad == "demo"


# --- el checkbox de la aprobación explícita -------------------------------------


def test_lote_del_pedido_exige_el_checkbox_para_aprobar() -> None:
    mundo = _mundo((_lote(origen_creacion="google"),))
    _ingresar(mundo.client)
    respuesta = _decidir(mundo)
    assert respuesta.status_code == 200
    assert "marcá la casilla" in respuesta.text
    assert mundo.lotes.llamadas_decidir == []
    assert mundo.lotes.obtener("lote-abc123").estado == ESTADO_PENDIENTE


def test_con_checkbox_la_aprobacion_queda(tmp_path) -> None:
    registro = RegistroDecisiones(tmp_path)
    mundo = _mundo(
        (_lote(origen_creacion="google"),),
        registro_decisiones=registro,
    )
    _ingresar(mundo.client)
    respuesta = _decidir(mundo, confirmar="si")
    assert respuesta.status_code == 200
    lote = mundo.lotes.obtener("lote-abc123")
    assert lote is not None and lote.estado == ESTADO_APROBADA
    # El puente asienta la línea exacta y el lote, con los tipos del
    # catálogo institucional.
    revision = revisar_aprobacion_lote(
        registro,
        objeto_lote=lote.objeto_lote,
        generada_por_correo_hash=hash_correo(CORREO_APROBADOR),
    )
    assert revision.aprobada is True
    assert linea_descriptiva_aprobada(
        registro, id_actividad="FIE-DIF-02", linea=LINEA
    ) is True


def test_descartar_no_exige_el_checkbox(tmp_path) -> None:
    registro = RegistroDecisiones(tmp_path)
    mundo = _mundo(
        (_lote(origen_creacion="google"),),
        registro_decisiones=registro,
    )
    _ingresar(mundo.client)
    respuesta = _decidir(mundo, accion="descartar")
    assert respuesta.status_code == 200
    assert mundo.lotes.obtener("lote-abc123").estado == "DESCARTADA"
    assert registro.procesadas() == ()


def test_lote_legacy_aprueba_sin_checkbox_y_solo_asienta_el_lote(
    tmp_path,
) -> None:
    registro = RegistroDecisiones(tmp_path)
    mundo = _mundo((_lote(),), registro_decisiones=registro)
    _ingresar(mundo.client)
    respuesta = _decidir(mundo)
    assert respuesta.status_code == 200
    lote = mundo.lotes.obtener("lote-abc123")
    assert lote is not None and lote.estado == ESTADO_APROBADA
    assert revisar_aprobacion_lote(
        registro,
        objeto_lote=lote.objeto_lote,
        generada_por_correo_hash=hash_correo(CORREO_APROBADOR),
    ).aprobada is True
    # La línea de un lote legacy ya la aprobó el circuito anterior: la
    # web no escribe una `linea_descriptiva` nueva.
    assert not [
        entrada
        for entrada in registro.procesadas()
        if entrada.get("tipo") == TIPO_LINEA_DESCRIPTIVA
    ]


def test_pagina_del_pedido_muestra_el_checkbox_y_el_legacy_no() -> None:
    mundo = _mundo(
        (_lote(origen_creacion="google"), _lote_legacy())
    )
    _ingresar(mundo.client)
    pagina = mundo.client.get("/certificados/lote-abc123")
    assert "Apruebo la línea descriptiva y la lista del lote" in pagina.text
    pagina_legacy = mundo.client.get("/certificados/lote-legacy")
    assert (
        "Apruebo la línea descriptiva y la lista del lote"
        not in pagina_legacy.text
    )


def _lote_legacy() -> LoteCertificados:
    return replace(
        _lote(),
        id_lote="lote-legacy",
        objeto_lote="a" * 64,
    )


def test_aprobar_lote_google_en_demo_no_registra_decisiones(tmp_path) -> None:
    registro = RegistroDecisiones(tmp_path)
    mundo = _mundo(
        (_lote(origen_creacion="google"),),
        registro_decisiones=registro,
        modo_demo=True,
    )
    _ingresar_demo(mundo.client, CORREO_APROBADOR)
    respuesta = _decidir(mundo, confirmar="si")
    assert respuesta.status_code == 200
    assert registro.procesadas() == ()

@pytest.mark.parametrize("accion", ["emision", "decidir"])
@pytest.mark.parametrize("tamano", [16, 2 * 1024 * 1024])
def test_post_del_lote_rechaza_archivos_antes_de_crear_temporales(monkeypatch, accion, tamano) -> None:
    import starlette.formparsers

    def temporal_prohibido(*args, **kwargs):
        raise AssertionError("El formulario de decisión no admite archivos")

    emision = EmisionFalsa()
    mundo = _mundo((_lote(estado=ESTADO_APROBADA),), emision=emision)
    _ingresar(mundo.client)
    monkeypatch.setattr(starlette.formparsers, "SpooledTemporaryFile", temporal_prohibido)
    respuesta = mundo.client.post(
        f"/certificados/lote-abc123/{accion}",
        data={"csrf": "invalido"}, files={"inesperado": ("x.csv", b"x" * tamano)},
    )
    assert respuesta.status_code in (400, 413)
    assert emision.solicitudes == []
    assert mundo.lotes.llamadas_decidir == []
