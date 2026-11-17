"""Canal web del Agente 1: ingreso, sesión, autorización y pedido guiado.

Cubre los requisitos de seguridad del diseño §3 y del ADR 0014: el ID token
se verifica en el servidor (acá con tokens firmados por claves de prueba y
con el verificador fake inyectado), la sesión vive sólo en memoria con sus
dos vencimientos, el rol se resuelve contra el padrón en cada request, CSRF
en lo que modifica estado y acceso directo a solicitudes sólo con sesión.
El repositorio se inyecta en memoria: la persistencia real se prueba contra
PostgreSQL en `test_canal_web_persistencia.py`.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agente1.canal_form import PadronRoles
from agente1.web.app import (
    CLIENT_ID_PRUEBA,
    ConfiguracionInvalida,
    ConfiguracionWeb,
    crear_app,
    validar_configuracion,
)
from agente1.web.identidad import (
    IdentidadVerificada,
    VerificacionIdentidadError,
    VerificadorFake,
    VerificadorGoogle,
)
from agente1.web.persistencia import (
    ConflictoIdempotencia,
    DetalleSolicitud,
    ItemBandeja,
    SolicitudCreada,
)
from agente1.web.sesiones import SesionesMemoria

AHORA = [datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc)]


def _ahora() -> datetime:
    return AHORA[0]


class RepositorioMemoria:
    """El puerto del repositorio implementado en memoria para la app."""

    def __init__(self) -> None:
        self.llaves: dict[str, tuple[str, str]] = {}
        self.solicitudes: dict[str, dict[str, Any]] = {}

    def crear_solicitud(
        self,
        *,
        idempotency_key: str,
        solicitante_hash: str,
        rol: str,
        tipo_pieza: str,
        actividad_ref: str | None,
        descripcion: str,
        campos: dict,
        canal: str = "web",
        ahora: datetime | None = None,
    ) -> SolicitudCreada:
        ahora = ahora or _ahora()
        if idempotency_key in self.llaves:
            id_prev, hash_prev = self.llaves[idempotency_key]
            if hash_prev != solicitante_hash:
                raise ConflictoIdempotencia()
            return SolicitudCreada(
                id_solicitud=id_prev, id_ejecucion="webe-x", creada=False
            )
        id_solicitud = f"web-{len(self.solicitudes):04d}"
        self.llaves[idempotency_key] = (id_solicitud, solicitante_hash)
        self.solicitudes[id_solicitud] = {
            "tipo_pieza": tipo_pieza,
            "actividad_ref": actividad_ref,
            "estado_web": "EN_COLA",
            "rol": rol,
            "solicitante_hash": solicitante_hash,
            "canal": canal,
            "creada_en": ahora,
            "ultima_actividad_en": ahora,
            "descripcion": descripcion,
            "campos": campos,
            "texto_generado": None,
            "revisiones": (),
        }
        return SolicitudCreada(
            id_solicitud=id_solicitud, id_ejecucion="webe-x", creada=True
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
        )

    def estado_de(self, id_solicitud: str) -> str | None:
        s = self.solicitudes.get(id_solicitud)
        return s["estado_web"] if s else None


@dataclass
class Mundo:
    client: TestClient
    repo: RepositorioMemoria
    sesiones: SesionesMemoria
    hoy: list | None = None


CORREO_SEU = "solicitante@example.invalid"
CORREO_LECTOR = "lector@example.invalid"
CORREO_EXTERNO = "externo@example.invalid"


def _mundo(
    monkeypatch: pytest.MonkeyPatch | None = None,
    publicos_extra: dict[str, str] | None = None,
) -> Mundo:
    padron = PadronRoles(
        {CORREO_SEU: "coordinador_seu", CORREO_LECTOR: "lector_seu"}
    )
    sesiones = SesionesMemoria(ahora=_ahora)
    verificador = VerificadorFake(
        {
            "tok-seu": IdentidadVerificada("sub-seu", CORREO_SEU, "x.invalid"),
            "tok-lector": IdentidadVerificada(
                "sub-lector", CORREO_LECTOR, "x.invalid"
            ),
            "tok-externo": IdentidadVerificada(
                "sub-externo", CORREO_EXTERNO, "externo.invalid"
            ),
        }
    )
    if monkeypatch is not None and publicos_extra:
        from agente1.web import app as modulo_app

        real = modulo_app.publicos_destinatarios
        monkeypatch.setattr(
            modulo_app,
            "publicos_destinatarios",
            lambda: {**real(), **publicos_extra},
        )
    repo = RepositorioMemoria()
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
        actividades=[
            {
                "id_actividad": "SYN-001",
                "titulo": "Taller",
                "fecha_inicio": "2026-11-20",
                "fecha_fin": "",
                "organiza": "SEU",
            }
        ],
    )
    return Mundo(TestClient(app), repo, sesiones)


@pytest.fixture()
def mundo() -> Mundo:
    return _mundo()


def _ingresar(client: TestClient, token: str = "tok-seu"):
    """Login del modo prueba: GET para el CSRF propio y POST con él."""
    formulario = client.get("/ingresar")
    marca = 'name="csrf" value="'
    csrf = formulario.text.split(marca, 1)[1].split('"', 1)[0]
    return client.post(
        "/ingresar",
        data={"credential": token, "csrf": csrf},
        follow_redirects=False,
    )


def _csrf_de(mundo: Mundo) -> str:
    sesion = next(iter(mundo.sesiones._sesiones.values()))
    return sesion.csrf_token


def test_login_crea_sesion_y_cookie_segura(mundo: Mundo) -> None:
    respuesta = _ingresar(mundo.client)
    assert respuesta.status_code == 303
    cookie = respuesta.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "a1_sesion=" in cookie
    # Rol habilitado: «Nuevo pedido» es la entrada principal.
    assert respuesta.headers["location"] == "/nuevo-pedido"


def test_token_invalido_rechaza(mundo: Mundo) -> None:
    respuesta = _ingresar(mundo.client, "token-trucho")
    assert respuesta.status_code == 200
    assert "verificar" in respuesta.text


def test_correo_fuera_del_padron_no_tiene_permiso(mundo: Mundo) -> None:
    # El token verifica pero el correo no figura en el padrón: 403.
    respuesta = _ingresar(mundo.client, "tok-externo")
    assert respuesta.status_code == 403
    assert "a1_sesion" not in respuesta.headers.get("set-cookie", "")
    # Sin sesión, la bandeja manda al ingreso.
    respuesta2 = mundo.client.get("/bandeja", follow_redirects=False)
    assert respuesta2.status_code == 303


def test_bandeja_requiere_sesion(mundo: Mundo) -> None:
    respuesta = mundo.client.get("/bandeja", follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/ingresar"


def test_acceso_directo_a_solicitud_requiere_sesion(mundo: Mundo) -> None:
    respuesta = mundo.client.get(
        "/solicitudes/web-0000", follow_redirects=False
    )
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/ingresar"


def test_sesion_vence_por_inactividad(mundo: Mundo) -> None:
    _ingresar(mundo.client)
    AHORA[0] = AHORA[0] + timedelta(minutes=31)
    respuesta = mundo.client.get("/bandeja", follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/ingresar"


def test_sesion_vence_por_vida_maxima(mundo: Mundo) -> None:
    _ingresar(mundo.client)
    AHORA[0] = AHORA[0] + timedelta(hours=8, minutes=1)
    respuesta = mundo.client.get("/bandeja", follow_redirects=False)
    assert respuesta.status_code == 303


def test_sesion_no_sobrevive_al_reinicio(mundo: Mundo) -> None:
    _ingresar(mundo.client)
    sid = mundo.client.cookies.get("a1_sesion")
    # Reinicio del proceso: el registro en memoria queda vacío.
    mundo.sesiones._sesiones.clear()
    mundo.client.cookies.set("a1_sesion", sid)
    respuesta = mundo.client.get("/bandeja", follow_redirects=False)
    assert respuesta.status_code == 303


def test_logout_cierra_la_sesion(mundo: Mundo) -> None:
    _ingresar(mundo.client)
    csrf = _csrf_de(mundo)
    # Sin CSRF la sesión sigue viva.
    mundo.client.post("/salir", data={"csrf": "trucho"})
    assert (
        mundo.client.get("/bandeja", follow_redirects=False).status_code
        == 200
    )
    mundo.client.post("/salir", data={"csrf": csrf})
    assert (
        mundo.client.get("/bandeja", follow_redirects=False).status_code
        == 303
    )


def test_nuevo_pedido_exige_csrf(mundo: Mundo) -> None:
    _ingresar(mundo.client)
    respuesta = mundo.client.post(
        "/nuevo-pedido",
        data={"tipo": "cronica_de_evento", "csrf": "trucho"},
        follow_redirects=False,
    )
    assert respuesta.status_code == 403


def test_nuevo_pedido_crea_solicitud_durable(mundo: Mundo) -> None:
    _ingresar(mundo.client)
    csrf = _csrf_de(mundo)
    cuerpo = {
        "csrf": csrf,
        "llave": "llave-1",
        "tipo": "cronica_de_evento",
        "area": "fie",
        "firma": "si",
        "campo_titulo": "Crónica de la muestra",
        "campo_cuerpo": "Texto confirmado por la persona.",
        "descripcion": "Difundir la muestra del taller.",
        "publicos": "alumnos_ingenieria",
    }
    respuesta = mundo.client.post(
        "/nuevo-pedido", data=cuerpo, follow_redirects=False
    )
    assert respuesta.status_code == 303
    ubicacion = respuesta.headers["location"]
    assert ubicacion.startswith("/solicitudes/web-")
    # El reenvío con la misma llave no crea otra solicitud (prueba 3).
    repetido = mundo.client.post(
        "/nuevo-pedido", data=cuerpo, follow_redirects=False
    )
    assert repetido.headers["location"] == ubicacion
    assert len(mundo.repo.solicitudes) == 1
    detalle = mundo.client.get(ubicacion)
    assert detalle.status_code == 200
    assert "Crónica de la muestra" in detalle.text


def test_nuevo_pedido_rol_no_habilitado_da_403(mundo: Mundo) -> None:
    _ingresar(mundo.client, "tok-lector")
    csrf = _csrf_de(mundo)
    respuesta = mundo.client.post(
        "/nuevo-pedido",
        data={"csrf": csrf, "llave": "l", "tipo": "cronica_de_evento"},
        follow_redirects=False,
    )
    assert respuesta.status_code == 403


def test_nuevo_pedido_campos_invalidos(mundo: Mundo) -> None:
    _ingresar(mundo.client)
    csrf = _csrf_de(mundo)
    respuesta = mundo.client.post(
        "/nuevo-pedido",
        data={
            "csrf": csrf,
            "llave": "l2",
            "tipo": "tipo_inventado",
            "area": "fie",
        },
        follow_redirects=False,
    )
    assert respuesta.status_code == 400


def test_nuevo_pedido_publico_invalido(mundo: Mundo) -> None:
    _ingresar(mundo.client)
    csrf = _csrf_de(mundo)
    respuesta = mundo.client.post(
        "/nuevo-pedido",
        data={
            "csrf": csrf,
            "llave": "l4",
            "tipo": "cronica_de_evento",
            "area": "fie",
            "firma": "si",
            "campo_titulo": "T",
            "campo_cuerpo": "C",
            "publicos": "grupo_inventado",
        },
        follow_redirects=False,
    )
    assert respuesta.status_code == 400


def test_estado_json_polling(mundo: Mundo) -> None:
    _ingresar(mundo.client)
    csrf = _csrf_de(mundo)
    mundo.client.post(
        "/nuevo-pedido",
        data={
            "csrf": csrf,
            "llave": "l3",
            "tipo": "difusion_de_actividad",
            "actividad": "SYN-001",
            "area": "fie",
            "firma": "si",
            "descripcion": "Difundir el taller.",
            "publicos": "alumnos_ingenieria",
        },
        follow_redirects=False,
    )
    id_solicitud = next(iter(mundo.repo.solicitudes))
    respuesta = mundo.client.get(f"/solicitudes/{id_solicitud}/estado")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "EN_COLA"
    sin_sesion = TestClient(mundo.client.app)
    assert (
        sin_sesion.get(f"/solicitudes/{id_solicitud}/estado").status_code
        == 401
    )


def test_verificador_google_con_claves_de_prueba() -> None:
    """Un ID token firmado por una clave de prueba verifica firma, iss,
    aud, exp y hd por el mismo camino del verificador real (ADR 0014)."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    publica = clave.public_key().public_numbers()

    def b64(valor: bytes) -> str:
        return base64.urlsafe_b64encode(valor).rstrip(b"=").decode()

    def b64int(n: int) -> str:
        largo = (n.bit_length() + 7) // 8
        return b64(n.to_bytes(largo, "big"))

    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "prueba",
                "use": "sig",
                "alg": "RS256",
                "n": b64int(publica.n),
                "e": b64int(publica.e),
            }
        ]
    }

    class RespuestaJwks:
        status = 200
        headers: dict = {}
        data = json.dumps(jwks).encode()

    class RequestJwks:
        def __call__(self, url, **kwargs):
            return RespuestaJwks()

    def firmar(payload: dict) -> str:
        encabezado = b64(
            json.dumps({"alg": "RS256", "kid": "prueba", "typ": "JWT"}).encode()
        )
        cuerpo = b64(json.dumps(payload).encode())
        firma = clave.sign(
            f"{encabezado}.{cuerpo}".encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return f"{encabezado}.{cuerpo}.{b64(firma)}"

    ahora = int(time.time())
    base_payload = {
        "iss": "https://accounts.google.com",
        "sub": "sub-prueba",
        "email": "alguien@example.invalid",
        "email_verified": True,
        "hd": "example.invalid",
        "aud": "cliente-prueba",
        "iat": ahora,
        "exp": ahora + 600,
    }
    verificador = VerificadorGoogle(
        client_id="cliente-prueba",
        dominio="example.invalid",
        request=RequestJwks(),
        certs_url="https://prueba.invalid/jwks",
    )
    identidad = verificador.verificar(firmar(dict(base_payload)))
    assert identidad.correo == "alguien@example.invalid"
    assert identidad.sub == "sub-prueba"

    # aud equivocada
    with pytest.raises(VerificacionIdentidadError):
        verificador.verificar(
            firmar({**base_payload, "aud": "otro-cliente"})
        )
    # hd de otro dominio
    with pytest.raises(VerificacionIdentidadError):
        verificador.verificar(
            firmar({**base_payload, "hd": "otro.invalid"})
        )
    # exp vencida
    with pytest.raises(VerificacionIdentidadError):
        verificador.verificar(
            firmar({**base_payload, "exp": ahora - 10})
        )
    # iss ajeno a Google
    with pytest.raises(VerificacionIdentidadError):
        verificador.verificar(
            firmar({**base_payload, "iss": "https://falso.invalid"})
        )


# ---------- salvaguardas del modo prueba y del modo real ----------


def _config_prueba(**kwargs: Any) -> ConfiguracionWeb:
    base = {
        "google_client_id": CLIENT_ID_PRUEBA,
        "modo_prueba": True,
        "cookie_secure": False,
    }
    base.update(kwargs)
    return ConfiguracionWeb(**base)


def test_modo_prueba_rechaza_client_id_real() -> None:
    with pytest.raises(ConfiguracionInvalida):
        validar_configuracion(
            _config_prueba(google_client_id="123.apps.googleusercontent.com")
        )


def test_modo_prueba_rechaza_cookie_secure() -> None:
    with pytest.raises(ConfiguracionInvalida):
        validar_configuracion(_config_prueba(cookie_secure=True))


def test_modo_prueba_rechaza_host_no_loopback() -> None:
    with pytest.raises(ConfiguracionInvalida):
        validar_configuracion(_config_prueba(), host="0.0.0.0")
    with pytest.raises(ConfiguracionInvalida):
        validar_configuracion(_config_prueba(), host="192.168.1.10")
    # Loopback sí: es donde el modo prueba tiene sentido.
    validar_configuracion(_config_prueba(), host="127.0.0.1")
    validar_configuracion(_config_prueba(), host="localhost")


def test_modo_prueba_rechaza_contenedor() -> None:
    with pytest.raises(ConfiguracionInvalida):
        validar_configuracion(_config_prueba(), en_contenedor=True)


def test_modo_real_exige_client_id() -> None:
    with pytest.raises(ConfiguracionInvalida):
        validar_configuracion(
            ConfiguracionWeb(google_client_id="", dominio_hd="x.invalid")
        )


def test_modo_real_exige_dominio() -> None:
    with pytest.raises(ConfiguracionInvalida):
        validar_configuracion(
            ConfiguracionWeb(google_client_id="c", dominio_hd=None)
        )


# ---------- CSRF del login ----------


def test_login_prueba_rechaza_post_sin_csrf(mundo: Mundo) -> None:
    respuesta = mundo.client.post(
        "/ingresar",
        data={"credential": "tok-seu"},
        follow_redirects=False,
    )
    assert respuesta.status_code == 403
    assert "a1_sesion" not in respuesta.headers.get("set-cookie", "")


def test_login_prueba_rechaza_csrf_sin_cookie(mundo: Mundo) -> None:
    respuesta = mundo.client.post(
        "/ingresar",
        data={"credential": "tok-seu", "csrf": "inventado"},
        follow_redirects=False,
    )
    assert respuesta.status_code == 403


def _mundo_real() -> Mundo:
    """App en modo real con verificador fake inyectado por el mismo seam.

    El verificador no es el de Google pero el camino es el real: exige el
    double-submit `g_csrf_token` como haría el formulario de GIS.
    """
    padron = PadronRoles({CORREO_SEU: "coordinador_seu"})
    verificador = VerificadorFake(
        {"tok-seu": IdentidadVerificada("sub-seu", CORREO_SEU, "x.invalid")}
    )
    repo = RepositorioMemoria()
    app = crear_app(
        config=ConfiguracionWeb(
            google_client_id="cliente-real",
            dominio_hd="x.invalid",
            modo_prueba=False,
        ),
        verificador=verificador,
        padron=padron,
        repositorio=repo,
        sesiones=SesionesMemoria(ahora=_ahora),
    )
    return Mundo(TestClient(app), repo, SesionesMemoria())


def test_login_real_exige_g_csrf_token() -> None:
    mundo_real = _mundo_real()
    client = mundo_real.client
    # Sin cookie ni campo: rechazo.
    assert (
        client.post("/ingresar", data={"credential": "tok-seu"}).status_code
        == 403
    )
    # Cookie sin el campo del formulario: rechazo.
    client.cookies.set("g_csrf_token", "valor-1")
    assert (
        client.post("/ingresar", data={"credential": "tok-seu"}).status_code
        == 403
    )
    # Campo que no coincide con la cookie: rechazo.
    assert (
        client.post(
            "/ingresar",
            data={"credential": "tok-seu", "g_csrf_token": "otro"},
        ).status_code
        == 403
    )
    # Double-submit correcto: sigue la verificación del token.
    respuesta = client.post(
        "/ingresar",
        data={"credential": "tok-seu", "g_csrf_token": "valor-1"},
        follow_redirects=False,
    )
    assert respuesta.status_code == 303


# ---------- sesión vencida: también los POST se rechazan ----------


def test_post_rechazado_con_sesion_vencida(mundo: Mundo) -> None:
    _ingresar(mundo.client)
    csrf = _csrf_de(mundo)
    AHORA[0] = AHORA[0] + timedelta(minutes=31)
    respuesta = mundo.client.post(
        "/nuevo-pedido",
        data={"csrf": csrf, "llave": "l", "tipo": "cronica_de_evento"},
        follow_redirects=False,
    )
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/ingresar"
    assert mundo.repo.solicitudes == {}


# ---------- formulario: contratos y preservación ----------


def test_formulario_conserva_publicos_multiples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # El catálogo real hoy tiene un solo público; para probar que la
    # preservación no pierde selecciones múltiples se amplía con un id
    # sintético por el mismo accesor público que usa la app.
    mundo = _mundo(
        monkeypatch,
        publicos_extra={"docentes_no_docentes": "Docentes y no docentes"},
    )
    _ingresar(mundo.client)
    csrf = _csrf_de(mundo)
    respuesta = mundo.client.post(
        "/nuevo-pedido",
        data={
            "csrf": csrf,
            "llave": "l5",
            "tipo": "cronica_de_evento",
            # Sin los campos requeridos del contrato: re-render con error.
            "publicos": ["alumnos_ingenieria", "docentes_no_docentes"],
        },
        follow_redirects=False,
    )
    assert respuesta.status_code == 400
    html = respuesta.text
    import re

    marcados = re.findall(
        r'<input type="checkbox" name="publicos" value="([^"]+)"\s*checked',
        html,
    )
    assert sorted(marcados) == [
        "alumnos_ingenieria",
        "docentes_no_docentes",
    ]


def test_formulario_muestra_datos_institucionales(mundo: Mundo) -> None:
    _ingresar(mundo.client)
    respuesta = mundo.client.get("/nuevo-pedido")
    assert respuesta.status_code == 200
    # La ficha de la actividad viaja en los datos del select: título,
    # fechas y organiza salen del catálogo, no se escriben a mano.
    assert 'data-titulo="Taller"' in respuesta.text
    assert 'data-fechas="2026-11-20' in respuesta.text
    assert 'data-organiza="SEU"' in respuesta.text


def test_formulario_no_pide_area_donde_el_contrato_no_la_usa(
    mundo: Mundo,
) -> None:
    _ingresar(mundo.client)
    html = mundo.client.get("/nuevo-pedido").text
    # crónica no usa área emisora según su contrato de entrada.
    import re

    opciones = re.findall(
        r'<option value="([a-z_]+)"[^>]*data-area="([^"]*)"', html
    )
    por_tipo = dict(opciones)
    assert por_tipo["cronica_de_evento"] == ""
    assert por_tipo["aviso_de_otra_area"] == "1"


def test_pedido_sin_publicos_requeridos_da_error(mundo: Mundo) -> None:
    _ingresar(mundo.client)
    csrf = _csrf_de(mundo)
    respuesta = mundo.client.post(
        "/nuevo-pedido",
        data={
            "csrf": csrf,
            "llave": "l6",
            "tipo": "cronica_de_evento",
            "campo_titulo": "T",
            "campo_cuerpo": "C",
        },
        follow_redirects=False,
    )
    assert respuesta.status_code == 400


def test_titulos_legibles_en_bandeja_y_detalle(mundo: Mundo) -> None:
    _ingresar(mundo.client)
    csrf = _csrf_de(mundo)
    mundo.client.post(
        "/nuevo-pedido",
        data={
            "csrf": csrf,
            "llave": "l7",
            "tipo": "cronica_de_evento",
            "campo_titulo": "Crónica de la muestra",
            "campo_cuerpo": "Texto confirmado.",
            "publicos": "alumnos_ingenieria",
        },
        follow_redirects=False,
    )
    bandeja = mundo.client.get("/bandeja")
    # El título del pedido aparece, no el código técnico como título.
    assert "Crónica de la muestra" in bandeja.text
    detalle = mundo.client.get("/solicitudes/web-0000")
    assert "<h1" in detalle.text
    assert detalle.text.index("Crónica de la muestra") < detalle.text.index(
        "web-0000"
    )


def test_difusion_usa_titulo_del_catalogo(mundo: Mundo) -> None:
    _ingresar(mundo.client)
    csrf = _csrf_de(mundo)
    mundo.client.post(
        "/nuevo-pedido",
        data={
            "csrf": csrf,
            "llave": "l8",
            "tipo": "difusion_de_actividad",
            "actividad": "SYN-001",
            "publicos": "alumnos_ingenieria",
        },
        follow_redirects=False,
    )
    bandeja = mundo.client.get("/bandeja")
    # El título institucional de la actividad, no el id técnico.
    assert "Taller" in bandeja.text


# ---------- prueba 9 del ADR 0016: los logs no llevan token ni prosa ----------


def test_logs_sin_token_ni_prosa(
    mundo: Mundo, caplog, tmp_path
) -> None:
    """Ni el token del ingreso ni la prosa del pedido aparecen en los logs
    de la app ni del worker (prueba 9, con marcadores sintéticos)."""
    import logging

    from agente1.web.persistencia import TrabajoWeb
    from agente1.web.worker import correr_una_vez

    prosa_marcada = "PROSA-MARCADA-" + "p" * 8
    with caplog.at_level(logging.DEBUG):
        _ingresar(mundo.client)  # el token "tok-seu" viaja en el POST
        csrf = _csrf_de(mundo)
        mundo.client.post(
            "/nuevo-pedido",
            data={
                "csrf": csrf,
                "llave": "l9",
                "tipo": "cronica_de_evento",
                "campo_titulo": "Título",
                "campo_cuerpo": prosa_marcada,
            },
            follow_redirects=False,
        )

        # El worker corre sobre un repo fake con la prosa marcada y una
        # generación que falla: sus líneas tampoco la llevan.
        class RepoFalla:
            def __init__(self) -> None:
                self.trabajo = TrabajoWeb(
                    id_ejecucion="e1",
                    id_solicitud="web-1",
                    tipo_pieza="cronica_de_evento",
                    actividad_ref=None,
                    rol="coordinador_seu",
                    solicitante_hash="ab" * 32,
                    canal="web",
                    descripcion=prosa_marcada,
                    campos={"pieza": {"titulo": "T", "cuerpo": prosa_marcada}},
                    intentos=3,
                )

            def tomar_trabajo(self, **_kw):
                trabajo, self.trabajo = self.trabajo, None
                return trabajo

            def fallar_trabajo(self, **_kw):
                pass

            def completar_trabajo(self, **_kw):
                raise AssertionError("no debía completarse")

        class FuenteVacia:
            def obtener(self, id_actividad):
                raise KeyError(id_actividad)

            def enumerar(self):
                return []

        class GeneradorRoto:
            modelo = "fake-roto"

            def generate(self, prompt: str, num_predict: int = 0) -> str:
                raise RuntimeError("caída sintética")

        class DestinoVacio:
            def buscar_o_crear(self, **_kw):
                raise RuntimeError("sin destino")

        correr_una_vez(
            repositorio=RepoFalla(),
            worker_id="w-test",
            fuente=FuenteVacia(),
            generator=GeneradorRoto(),
            directorio_salida=tmp_path,
            destino=DestinoVacio(),
            max_intentos=3,
        )

    registro = "\n".join(r.getMessage() for r in caplog.records)
    assert "tok-seu" not in registro
    assert prosa_marcada not in registro


# ---------- modo demostración sin login (#149, ADR 0019) ----------
#
# El modo demo reemplaza la verificación de Google por la elección de una
# identidad del padrón, para la presentación sin el client ID de DSI (#62).
# Tiene sus propias salvaguardas: fecha de vencimiento acotada, lista
# cerrada de correos del padrón, cookie Secure, y no convive con el modo
# prueba ni con un client ID real.


def _config_demo(**kwargs: Any) -> ConfiguracionWeb:
    base: dict[str, Any] = {
        "google_client_id": "",
        "modo_demo": True,
        "demo_hasta": date(2026, 11, 19),
        "demo_correos": (CORREO_SEU, CORREO_LECTOR),
        "cookie_secure": True,
    }
    base.update(kwargs)
    return ConfiguracionWeb(**base)


_PADRON_DEMO = PadronRoles(
    {CORREO_SEU: "coordinador_seu", CORREO_LECTOR: "lector_seu"}
)


def _validar_demo(config: ConfiguracionWeb, **kwargs: Any) -> None:
    validar_configuracion(
        config,
        padron=_PADRON_DEMO,
        hoy=lambda: date(2026, 11, 16),
        **kwargs,
    )


def _mundo_demo(**kwargs: Any) -> Mundo:
    """App en modo demostración con el reloj inyectado.

    `mundo.hoy[0]` es la fecha que el servidor consulta en cada request:
    moverla simula el paso del vencimiento sin reloj real.
    """
    hoy = kwargs.pop("hoy", None) or [date(2026, 11, 16)]
    sesiones = SesionesMemoria(ahora=_ahora)
    repo = RepositorioMemoria()
    app = crear_app(
        config=_config_demo(**kwargs),
        verificador=VerificadorFake({}),
        padron=_PADRON_DEMO,
        repositorio=repo,
        sesiones=sesiones,
        actividades=[],
        hoy=lambda: hoy[0],
    )
    # La demo corre detrás de HTTPS (tailscale serve o túnel SSH): sin él
    # las cookies `Secure` — exigidas por el modo — no viajan.
    client = TestClient(app, base_url="https://testserver")
    return Mundo(client, repo, sesiones, hoy)


def _ingresar_demo(
    client: TestClient, correo: str = CORREO_SEU, **extra: str
):
    """Login del modo demo: GET para el CSRF propio y POST con el correo."""
    formulario = client.get("/ingresar")
    marca = 'name="csrf" value="'
    csrf = formulario.text.split(marca, 1)[1].split('"', 1)[0]
    return client.post(
        "/ingresar",
        data={"correo": correo, "csrf": csrf, **extra},
        follow_redirects=False,
    )


# --- salvaguardas de arranque: un rechazo por combinación insegura ---


def test_modo_demo_exige_fecha_de_vencimiento() -> None:
    with pytest.raises(ConfiguracionInvalida):
        _validar_demo(_config_demo(demo_hasta=None))


def test_modo_demo_exige_lista_de_correos() -> None:
    with pytest.raises(ConfiguracionInvalida):
        _validar_demo(_config_demo(demo_correos=()))


def test_modo_demo_rechaza_fecha_ya_pasada() -> None:
    with pytest.raises(ConfiguracionInvalida):
        validar_configuracion(
            _config_demo(demo_hasta=date(2026, 11, 15)),
            padron=_PADRON_DEMO,
            hoy=lambda: date(2026, 11, 16),
        )
    # El día del vencimiento todavía es válido: la demo corre ese día.
    _validar_demo(_config_demo(demo_hasta=date(2026, 11, 16)))


def test_modo_demo_rechaza_fecha_a_mas_de_14_dias() -> None:
    with pytest.raises(ConfiguracionInvalida):
        _validar_demo(_config_demo(demo_hasta=date(2026, 12, 1)))
    # Justo 14 días es el límite aceptado.
    _validar_demo(_config_demo(demo_hasta=date(2026, 11, 30)))


def test_modo_demo_rechaza_correo_fuera_del_padron() -> None:
    with pytest.raises(ConfiguracionInvalida):
        _validar_demo(
            _config_demo(
                demo_correos=(CORREO_SEU, CORREO_EXTERNO)
            )
        )


def test_modo_demo_no_convive_con_modo_prueba() -> None:
    with pytest.raises(ConfiguracionInvalida):
        _validar_demo(_config_demo(modo_prueba=True))


def test_modo_demo_rechaza_client_id_de_google() -> None:
    with pytest.raises(ConfiguracionInvalida):
        _validar_demo(
            _config_demo(google_client_id="123.apps.googleusercontent.com")
        )


def test_modo_demo_exige_cookie_secure() -> None:
    with pytest.raises(ConfiguracionInvalida):
        _validar_demo(_config_demo(cookie_secure=False))


def test_modo_demo_puede_correr_en_contenedor_y_red_interna() -> None:
    # La exposición la limita el compose (puerto en 127.0.0.1 del host) y
    # el acceso entra por tailscale serve o túnel SSH, así que el contenedor
    # y un bind no-loopback no son señal de despliegue indebido como en el
    # modo prueba.
    _validar_demo(_config_demo(), host="0.0.0.0", en_contenedor=True)


# --- ingreso por elección de identidad del padrón ---


def test_login_demo_ofrece_select_con_roles_del_padron() -> None:
    mundo = _mundo_demo()
    respuesta = mundo.client.get("/ingresar")
    assert respuesta.status_code == 200
    assert "Entrar como" in respuesta.text
    assert CORREO_SEU in respuesta.text
    assert CORREO_LECTOR in respuesta.text
    # El rol mostrado sale del padrón, no del navegador.
    assert "coordinador_seu" in respuesta.text
    assert "lector_seu" in respuesta.text
    # Sin el script de Google en esta página.
    assert "accounts.google.com/gsi/client" not in respuesta.text


def test_login_demo_crea_sesion_y_cookie_segura() -> None:
    mundo = _mundo_demo()
    respuesta = _ingresar_demo(mundo.client)
    assert respuesta.status_code == 303
    cookie = respuesta.headers["set-cookie"]
    assert "a1_sesion=" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert respuesta.headers["location"] == "/nuevo-pedido"
    sesion = next(iter(mundo.sesiones._sesiones.values()))
    assert sesion.correo == CORREO_SEU
    assert sesion.origen == "demo"


def test_login_demo_rechaza_correo_fuera_de_la_lista() -> None:
    # El correo está en el padrón pero no en AGENTE1_WEB_DEMO_CORREOS.
    mundo = _mundo_demo(demo_correos=(CORREO_SEU,))
    respuesta = _ingresar_demo(mundo.client, correo=CORREO_LECTOR)
    assert respuesta.status_code == 403
    assert "a1_sesion" not in respuesta.headers.get("set-cookie", "")
    assert len(mundo.sesiones) == 0


def test_login_demo_ignora_el_rol_enviado_por_el_navegador() -> None:
    mundo = _mundo_demo()
    respuesta = _ingresar_demo(
        mundo.client, rol="admin_total", correo=CORREO_SEU
    )
    assert respuesta.status_code == 303
    sesion = next(iter(mundo.sesiones._sesiones.values()))
    # El rol lo resuelve el padrón; el campo del formulario no pesa nada.
    assert sesion.rol == "coordinador_seu"


def test_login_demo_exige_csrf() -> None:
    mundo = _mundo_demo()
    # Sin CSRF: rechazo.
    assert (
        mundo.client.post("/ingresar", data={"correo": CORREO_SEU}).status_code
        == 403
    )
    # CSRF que no coincide con la cookie: rechazo.
    assert (
        mundo.client.post(
            "/ingresar",
            data={"correo": CORREO_SEU, "csrf": "inventado"},
        ).status_code
        == 403
    )
    assert len(mundo.sesiones) == 0


def test_login_demo_correo_sin_rol_en_padron_da_403() -> None:
    # El arranque exige que cada correo de la lista esté en el padrón; si el
    # padrón cambia en caliente, el POST vuelve a consultarlo y no deja pasar.
    class PadronVivo:
        def __init__(self) -> None:
            self.roles = {
                CORREO_SEU: "coordinador_seu",
                CORREO_LECTOR: "lector_seu",
            }

        def rol_para(self, correo: str) -> str | None:
            return self.roles.get(correo)

    padron_vivo = PadronVivo()
    repo = RepositorioMemoria()
    sesiones = SesionesMemoria(ahora=_ahora)
    app = crear_app(
        config=_config_demo(),
        verificador=VerificadorFake({}),
        padron=padron_vivo,
        repositorio=repo,
        sesiones=sesiones,
        hoy=lambda: date(2026, 11, 16),
    )
    # El correo figura en la lista demo pero ya no tiene rol en el padrón.
    del padron_vivo.roles[CORREO_SEU]
    client = TestClient(app, base_url="https://testserver")
    respuesta = _ingresar_demo(client, correo=CORREO_SEU)
    assert respuesta.status_code == 403
    assert len(sesiones) == 0


# --- vencimiento en ejecución ---


def test_demo_vencida_responde_503_en_todo_menos_estaticos() -> None:
    mundo = _mundo_demo()
    _ingresar_demo(mundo.client)
    assert mundo.hoy is not None
    mundo.hoy[0] = date(2026, 11, 20)  # pasado el 19/11 declarado
    for ruta in ("/bandeja", "/nuevo-pedido", "/ingresar", "/salud", "/"):
        respuesta = mundo.client.get(ruta, follow_redirects=False)
        assert respuesta.status_code == 503, ruta
        assert "demostración venció" in respuesta.text
    # Los estáticos siguen sirviendo (la página del 503 necesita el CSS).
    assert mundo.client.get("/estaticos/estilos.css").status_code == 200


def test_demo_vencida_invalida_las_sesiones_vivas() -> None:
    mundo = _mundo_demo()
    _ingresar_demo(mundo.client)
    assert len(mundo.sesiones) == 1
    assert mundo.hoy is not None
    mundo.hoy[0] = date(2026, 11, 20)
    mundo.client.get("/bandeja", follow_redirects=False)
    assert len(mundo.sesiones) == 0


def test_banda_demo_visible_y_con_fecha() -> None:
    mundo = _mundo_demo()
    ingreso = mundo.client.get("/ingresar")
    assert "Modo demostración" in ingreso.text
    assert "19/11/2026" in ingreso.text
    _ingresar_demo(mundo.client)
    bandeja = mundo.client.get("/bandeja")
    assert "Modo demostración" in bandeja.text
    assert "sin verificación de identidad" in bandeja.text


def test_banda_demo_no_aparece_en_modo_prueba(mundo: Mundo) -> None:
    respuesta = mundo.client.get("/ingresar")
    assert "Modo demostración" not in respuesta.text


# --- trazabilidad honesta: el origen queda marcado ---


def test_pedido_demo_se_registra_con_canal_web_demo() -> None:
    mundo = _mundo_demo()
    _ingresar_demo(mundo.client)
    csrf = _csrf_de(mundo)
    respuesta = mundo.client.post(
        "/nuevo-pedido",
        data={
            "csrf": csrf,
            "llave": "demo-1",
            "tipo": "cronica_de_evento",
            "campo_titulo": "Crónica de la demo",
            "campo_cuerpo": "Texto confirmado.",
            "publicos": "alumnos_ingenieria",
        },
        follow_redirects=False,
    )
    assert respuesta.status_code == 303
    solicitud = next(iter(mundo.repo.solicitudes.values()))
    # La solicitud no puede figurar como identidad verificada por Google:
    # su canal declara el origen demo.
    assert solicitud["canal"] == "web-demo"
    detalle = mundo.client.get(respuesta.headers["location"])
    assert "demostración" in detalle.text


def test_formulario_muestra_como_se_completa_la_frase_de_cada_campo(
    mundo: Mundo,
) -> None:
    """Demo 17/11: «Hecho» sin más llevaba a escribir una oración entera
    («Por tareas…») que la fórmula del aviso inserta en medio de otra."""

    _ingresar(mundo.client)
    html = mundo.client.get("/nuevo-pedido").text
    assert "Se informa a la comunidad … que …" in html
    assert 'aria-describedby="ayuda_hecho_aviso_de_otra_area"' in html


def test_bandeja_agrupa_por_estado_y_colapsa_los_errores(mundo: Mundo) -> None:
    """Demo 17/11: los pedidos con error quedaban mezclados con los que
    esperan revisión. No se borran (auditoría): van agrupados al final."""

    _ingresar(mundo.client)
    for llave, titulo in (("b1", "Pieza en revisión"), ("b2", "Pieza aprobada"), ("b3", "Pieza fallida")):
        mundo.client.post(
            "/nuevo-pedido",
            data={
                "csrf": _csrf_de(mundo),
                "llave": llave,
                "tipo": "cronica_de_evento",
                "campo_titulo": titulo,
                "campo_cuerpo": "Texto confirmado.",
                "publicos": "alumnos_ingenieria",
            },
            follow_redirects=False,
        )
    mundo.repo.solicitudes["web-0000"]["estado_web"] = "LISTA"
    mundo.repo.solicitudes["web-0001"]["estado_web"] = "APROBADA"
    mundo.repo.solicitudes["web-0002"]["estado_web"] = "ERROR"

    html = mundo.client.get("/bandeja").text

    assert html.index("Pendientes") < html.index("Pieza en revisión")
    assert html.index("Cerradas") < html.index("Pieza aprobada")
    errores = html.index('<details class="bandeja-errores"')
    assert errores < html.index("Pieza fallida")
    assert html.index("Pieza en revisión") < html.index("Pieza aprobada") < errores
    assert "Con error (1)" in html
