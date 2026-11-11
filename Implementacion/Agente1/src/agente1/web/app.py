"""Aplicación web del canal del Agente 1 (issue #149).

HTML servido por FastAPI + Jinja2, del mismo origen: sin SPA ni
empaquetado de JavaScript. Lo que corre en el navegador es mínimo: el
botón de Google Identity Services y el
polling del estado «generando». Seguridad del diseño §3 y ADR 0014: el ID
token se verifica en el servidor, la sesión vive sólo en memoria, toda
escritura exige CSRF y el rol se resuelve contra el padrón en cada request;
nunca se acepta rol ni correo enviados por el navegador.

Decisiones que no se ven en el código:

- **La bandeja la ve todo el padrón SEU; crear pide rol habilitado**
  (definición del 11/11/2026). `autorizar` sólo exige sesión viva más rol
  vigente del padrón; el gate de `ROLES_HABILITADOS` vive en el pedido
  guiado, que es donde nace la solicitud.
- **La entrada principal es «Nuevo pedido»** (ajuste del 04/11): `/` y el
  retorno del login apuntan ahí cuando el rol puede pedir; el resto del
  padrón aterriza en la bandeja, que es lo suyo.
- **El CSRF del login no es el de la sesión** (todavía no hay sesión):
  en modo real se valida el double-submit `g_csrf_token` que pone Google
  Identity Services —cookie contra campo del formulario—; en modo prueba
  el formulario lleva un `a1_login_csrf` propio, misma doctrina.
- **La configuración se valida al construir la app**: modo real exige
  client ID y dominio `hd`; modo prueba se niega a correr con cookie
  `Secure` — una cookie segura jamás llega por HTTP de desarrollo, así
  que un modo prueba «seguro» sólo puede ser un despliegue mal armado.
- **La validación del pedido sale de los contratos**, no de una lista
  propia: cada tipo declara en su contrato de entrada si usa área emisora,
  firma de área y qué campos pide, y en el catálogo de tipos si pide
  públicos. El formulario no ofrece ni exige lo que el tipo no usa, y el
  servidor vuelve a validarlo todo.
- **El hash del solicitante es hash del correo** (ADR 0016), igual que el
  resto de la auditoría del sistema: el `sub` de Google queda en la
  sesión en memoria, nunca en la base.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..canal_form import (
    PadronRoles,
    areas_emisoras,
    publicos_destinatarios,
)
from ..gacetillas import (
    cargar_entrada,
    requiere_actividad,
    requiere_publicos,
    tipos,
)
from ..interpretacion import ROLES_HABILITADOS
from .identidad import VerificacionIdentidadError, VerificadorIdToken
from .persistencia import (
    ConflictoIdempotencia,
    DetalleSolicitud,
    RepositorioWeb,
)
from .sesiones import Sesion, SesionesMemoria

_COOKIE = "a1_sesion"
_COOKIE_CSRF_LOGIN = "a1_login_csrf"
_COOKIE_CSRF_GIS = "g_csrf_token"
_ESTADOS_VISIBLES = {
    "EN_COLA": "En cola",
    "GENERANDO": "Generando",
    "LISTA": "Lista para revisar",
    "ERROR": "Con error",
    "APROBADA": "Aprobada",
    "DESCARTADA": "Descartada",
    "VENCIDA": "Vencida",
}
_NOMBRES_TIPOS = {
    "difusion_de_actividad": "Difusión de actividad",
    "cronica_de_evento": "Crónica de evento",
    "aviso_de_otra_area": "Aviso de otra área",
    "convocatoria_interna": "Convocatoria interna",
    "saludo_o_efemeride": "Saludo o efeméride",
    "fallecimiento": "Fallecimiento",
    "newsletter": "Newsletter",
}
_CAMPOS_AREA = {"cuerpo", "hecho", "condicion", "requisitos", "convocatoria"}
_HOSTS_LOCALES = frozenset({"127.0.0.1", "localhost"})
CLIENT_ID_PRUEBA = "modo-prueba"


class ConfiguracionInvalida(ValueError):
    """La configuración declarada no puede servir el canal con seguridad."""


@dataclass(frozen=True)
class ConfiguracionWeb:
    """Config declarada por entorno: nada institucional queda en el repo.

    `google_client_id` y `dominio_hd` los entrega DSI (#62): en modo real
    son obligatorios los dos — sin dominio no hay `hd` que exigir y el
    diseño §3 lo hace cerrar en vez de dejar pasar cualquier cuenta.
    """

    google_client_id: str
    dominio_hd: str | None = None
    modo_prueba: bool = False
    cookie_secure: bool = True


class PedidoInvalido(ValueError):
    def __init__(self, code: str, campo: str) -> None:
        self.code = code
        self.campo = campo
        super().__init__(code)


def validar_configuracion(
    config: ConfiguracionWeb,
    *,
    host: str | None = None,
    en_contenedor: bool = False,
) -> None:
    """Cierra el arranque cuando la combinación declarada es insegura.

    Modo real: exige client ID y dominio `hd` — sin ellos no hay nada que
    verificar del token y el canal quedaría abierto a cualquiera.

    Modo prueba: es un verificador fake que acepta tokens inventados, así
    que se niega a arrancar si hay cualquier señal de un despliegue real:
    un client ID de Google configurado, cookie `Secure` (imposible por el
    HTTP local donde el modo sirve), un host que no sea loopback o el
    entrypoint del contenedor. Cualquiera de esas marcas significa que el
    modo prueba llegó a un lugar donde nunca debió estar.
    """
    if config.modo_prueba:
        if config.google_client_id != CLIENT_ID_PRUEBA:
            raise ConfiguracionInvalida(
                "modo_prueba con client ID de Google configurado"
            )
        if config.cookie_secure:
            raise ConfiguracionInvalida(
                "modo_prueba con cookie Secure exige HTTP local"
            )
        if host is not None and host not in _HOSTS_LOCALES:
            raise ConfiguracionInvalida(
                f"modo_prueba fuera de loopback: {host}"
            )
        if en_contenedor:
            raise ConfiguracionInvalida(
                "modo_prueba dentro del contenedor de despliegue"
            )
        return
    if not config.google_client_id:
        raise ConfiguracionInvalida("modo real sin client ID de Google")
    if not config.dominio_hd:
        raise ConfiguracionInvalida("modo real sin dominio institucional")


def _campos_por_tipo() -> dict[str, dict[str, Any]]:
    """Ficha del formulario por tipo, derivada de los contratos de entrada.

    Para cada tipo declara si el contrato usa área emisora y firma de área
    (los pide el formulario como select de padrón y opción separada, no
    como inputs libres) y la lista de campos que sí son texto. Si el
    contrato del tipo no carga, el tipo queda marcado `disponible=False` y
    la interfaz lo muestra «todavía no disponible»: no se inventa un
    formulario para un tipo sin contrato.
    """
    resultado: dict[str, dict[str, Any]] = {}
    for tipo in tipos():
        ficha: dict[str, Any] = {
            "disponible": True,
            "usa_area": False,
            "usa_firma": False,
            "campos": [],
        }
        try:
            entrada = cargar_entrada(tipo)
        except Exception:
            ficha["disponible"] = False
            resultado[tipo] = ficha
            continue
        propiedades = entrada.get("properties", {})
        requeridos = set(entrada["required"])
        ficha["usa_area"] = "area_emisora" in propiedades
        ficha["usa_firma"] = "firma_de_area" in propiedades
        campos = []
        if not requiere_actividad(tipo):
            # Con ficha de actividad el contrato se llena de la fuente
            # institucional, no del formulario: la persona sólo elige la
            # actividad y sus datos se muestran de sólo lectura.
            for nombre in propiedades:
                if nombre in ("area_emisora", "firma_de_area"):
                    continue
                campos.append(
                    {
                        "nombre": nombre,
                        "requerido": nombre in requeridos,
                        "area": nombre in _CAMPOS_AREA,
                    }
                )
        ficha["campos"] = campos
        resultado[tipo] = ficha
    return resultado


def crear_app(
    *,
    config: ConfiguracionWeb,
    verificador: VerificadorIdToken,
    padron: PadronRoles,
    repositorio: RepositorioWeb,
    sesiones: SesionesMemoria | None = None,
    actividades: list[dict[str, str]] | None = None,
    host: str | None = None,
    en_contenedor: bool = False,
) -> FastAPI:
    """Fábrica de la app: todo servicio externo entra inyectado.

    `actividades` es la lista visible de la fuente de solicitudes (sólo
    lectura), para el select condicional del pedido con sus datos
    institucionales. `host` y `en_contenedor` alimentan las salvaguardas
    del modo prueba (`validar_configuracion`).
    """
    validar_configuracion(config, host=host, en_contenedor=en_contenedor)
    sesiones = sesiones if sesiones is not None else SesionesMemoria()
    base = Path(__file__).resolve().parent
    plantillas = Jinja2Templates(directory=str(base / "plantillas"))
    areas = areas_emisoras()
    publicos = publicos_destinatarios()
    fichas_por_tipo = _campos_por_tipo()
    actividades = actividades or []
    actividades_por_id = {
        str(a.get("id_actividad", "")): a for a in actividades
    }

    app = FastAPI(title="Agente 1 — Canal web", docs_url=None, redoc_url=None)
    app.mount(
        "/estaticos",
        StaticFiles(directory=str(base / "estaticos")),
        name="estaticos",
    )

    def render(
        nombre: str,
        request: Request,
        status_code: int = 200,
        **ctx: Any,
    ) -> HTMLResponse:
        return plantillas.TemplateResponse(
            request=request,
            name=nombre,
            context={"config": config, **ctx},
            status_code=status_code,
        )

    def sesion_de(request: Request) -> Sesion | None:
        return sesiones.obtener(request.cookies.get(_COOKIE))

    def autorizar(request: Request) -> Sesion | None:
        """Sesión viva + rol vigente del padrón, en cada request."""
        sesion = sesion_de(request)
        if sesion is None:
            return None
        rol = padron.rol_para(sesion.correo)
        if rol is None:
            sesiones.cerrar(sesion.sid)
            return None
        return sesion

    def rol_de(sesion: Sesion) -> str | None:
        return padron.rol_para(sesion.correo)

    def puede_pedir(sesion: Sesion) -> bool:
        return rol_de(sesion) in ROLES_HABILITADOS

    def destino_login() -> RedirectResponse:
        return RedirectResponse("/ingresar", status_code=303)

    def destino_inicio(sesion: Sesion) -> RedirectResponse:
        return RedirectResponse(
            "/nuevo-pedido" if puede_pedir(sesion) else "/bandeja",
            status_code=303,
        )

    def csrf_ok(sesion: Sesion, token: str | None) -> bool:
        return sesiones.verificar_csrf(sesion, token)

    def _double_submit(request: Request, valor: str | None, cookie: str) -> bool:
        """Comparación cookie↔formulario del login, en tiempo constante."""
        de_cookie = request.cookies.get(cookie)
        return bool(de_cookie) and bool(valor) and hmac.compare_digest(
            de_cookie, valor
        )

    # ---------- ingreso ----------

    @app.get("/", response_class=HTMLResponse)
    def raiz(request: Request) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        return destino_inicio(sesion)

    def _render_ingresar(
        request: Request, error: str | None, status_code: int = 200
    ) -> HTMLResponse:
        """El formulario de ingreso con su CSRF de double-submit reemitido.

        En modo prueba el token lo pone la app (cookie `a1_login_csrf`
        contra campo `csrf`); en modo real lo pone Google Identity
        Services en `g_csrf_token` y acá no hay nada que reemitir.
        """
        csrf_login = ""
        if config.modo_prueba:
            csrf_login = secrets.token_urlsafe(32)
        respuesta = render(
            "ingresar.html",
            request,
            status_code=status_code,
            error=error,
            csrf_login=csrf_login,
        )
        if csrf_login:
            respuesta.set_cookie(
                _COOKIE_CSRF_LOGIN,
                csrf_login,
                httponly=True,
                secure=config.cookie_secure,
                samesite="strict",
                path="/ingresar",
            )
        return respuesta

    @app.get("/ingresar", response_class=HTMLResponse)
    def ingresar_form(request: Request) -> Response:
        sesion = autorizar(request)
        if sesion is not None:
            return destino_inicio(sesion)
        return _render_ingresar(request, error=None)

    @app.post("/ingresar", response_class=HTMLResponse)
    def ingresar(
        request: Request,
        credential: str = Form(""),
        csrf: str = Form(""),
        g_csrf_token: str = Form(""),
    ) -> Response:
        if config.modo_prueba:
            if not _double_submit(request, csrf, _COOKIE_CSRF_LOGIN):
                return _render_ingresar(
                    request,
                    status_code=403,
                    error="El formulario venció. Recargá la página.",
                )
        elif not _double_submit(
            request, g_csrf_token, _COOKIE_CSRF_GIS
        ):
            return _render_ingresar(
                request,
                status_code=403,
                error="No pudimos validar el formulario de ingreso.",
            )
        try:
            identidad = verificador.verificar(credential)
        except VerificacionIdentidadError:
            return _render_ingresar(
                request,
                error="No pudimos verificar tu identidad. Probá de nuevo.",
            )
        rol = padron.rol_para(identidad.correo)
        if rol is None:
            return render(
                "sin_permiso.html", request, status_code=403
            )
        sesion = sesiones.crear(
            sub=identidad.sub, correo=identidad.correo, rol=rol
        )
        respuesta = destino_inicio(sesion)
        respuesta.set_cookie(
            _COOKIE,
            sesion.sid,
            httponly=True,
            secure=config.cookie_secure,
            samesite="lax",
            max_age=8 * 3600,
            path="/",
        )
        return respuesta

    @app.get("/sin-permiso", response_class=HTMLResponse)
    def sin_permiso(request: Request) -> Response:
        return render("sin_permiso.html", request, status_code=403)

    @app.post("/salir")
    def salir(request: Request, csrf: str = Form("")) -> Response:
        sesion = sesion_de(request)
        if sesion is None or not csrf_ok(sesion, csrf):
            return destino_login()
        sesiones.cerrar(sesion.sid)
        respuesta = RedirectResponse("/ingresar", status_code=303)
        respuesta.delete_cookie(_COOKIE, path="/")
        return respuesta

    # ---------- bandeja y detalle ----------

    @app.get("/bandeja", response_class=HTMLResponse)
    def bandeja(request: Request) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        items = [
            {
                "id": i.id_solicitud,
                "tipo": _NOMBRES_TIPOS.get(i.tipo_pieza, i.tipo_pieza),
                "estado": i.estado_web,
                "estado_visible": _ESTADOS_VISIBLES.get(
                    i.estado_web, i.estado_web
                ),
                "titulo": i.titulo
                or actividades_por_id.get(i.actividad_ref or "", {}).get(
                    "titulo"
                )
                or _NOMBRES_TIPOS.get(i.tipo_pieza, i.tipo_pieza),
                "creada": i.creada_en.strftime("%d/%m/%Y %H:%M"),
            }
            for i in repositorio.bandeja()
        ]
        return render(
            "bandeja.html",
            request,
            sesion=sesion,
            items=items,
        )

    @app.get("/solicitudes/{id_solicitud}", response_class=HTMLResponse)
    def detalle(request: Request, id_solicitud: str) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        detalle_sol = repositorio.obtener(id_solicitud)
        if detalle_sol is None:
            return render("sin_permiso.html", request, status_code=404)
        return _render_detalle(request, sesion, detalle_sol)

    def _render_detalle(
        request: Request, sesion: Sesion, detalle_sol: DetalleSolicitud
    ) -> HTMLResponse:
        campos_pieza = detalle_sol.campos.get("pieza", {})
        campos_pedido = detalle_sol.campos.get("pedido", {})
        actividad = actividades_por_id.get(detalle_sol.actividad_ref or "")
        titulo = (
            campos_pieza.get("titulo")
            or (actividad or {}).get("titulo")
            or _NOMBRES_TIPOS.get(detalle_sol.tipo_pieza)
        )
        return render(
            "solicitud.html",
            request,
            sesion=sesion,
            s=detalle_sol,
            titulo=titulo,
            actividad=actividad,
            tipo=_NOMBRES_TIPOS.get(
                detalle_sol.tipo_pieza, detalle_sol.tipo_pieza
            ),
            estado_visible=_ESTADOS_VISIBLES.get(
                detalle_sol.estado_web, detalle_sol.estado_web
            ),
            campos_pieza=campos_pieza,
            publicos=[
                publicos.get(p, p) for p in campos_pedido.get("publicos", [])
            ],
            revisiones=detalle_sol.revisiones,
        )

    @app.get("/solicitudes/{id_solicitud}/estado")
    def estado(request: Request, id_solicitud: str) -> Response:
        if autorizar(request) is None:
            return JSONResponse({"estado": "no_autorizado"}, status_code=401)
        estado_web = repositorio.estado_de(id_solicitud)
        if estado_web is None:
            return JSONResponse({"estado": "no_existe"}, status_code=404)
        return JSONResponse({"estado": estado_web})

    # ---------- pedido guiado ----------

    def _formulario_ctx(sesion: Sesion, llave: str) -> dict[str, Any]:
        return {
            "sesion": sesion,
            "csrf": sesion.csrf_token,
            "llave": llave,
            "tipos": [
                {
                    "id": t,
                    "nombre": _NOMBRES_TIPOS.get(t, t),
                    "actividad": requiere_actividad(t),
                    "publicos": requiere_publicos(t),
                    "usa_area": fichas_por_tipo[t]["usa_area"],
                    "usa_firma": fichas_por_tipo[t]["usa_firma"],
                    "disponible": fichas_por_tipo[t]["disponible"],
                }
                for t in tipos()
            ],
            "campos_por_tipo": {
                t: f["campos"] for t, f in fichas_por_tipo.items()
            },
            "areas": areas,
            "publicos": publicos,
            "actividades": actividades,
        }

    @app.get("/nuevo-pedido", response_class=HTMLResponse)
    def nuevo_pedido_form(request: Request) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        if not puede_pedir(sesion):
            return render("sin_permiso.html", request, status_code=403)
        return render(
            "nuevo_pedido.html",
            request,
            errores={},
            valores={},
            **_formulario_ctx(sesion, uuid.uuid4().hex),
        )

    def _validar_pedido(form: Any) -> dict[str, Any]:
        """Valida el pedido del lado del servidor y arma sus campos.

        Las reglas salen del contrato del tipo —el mismo que valida el
        canal Form—: área y firma sólo si el contrato las usa, públicos
        según el catálogo de tipos y campos según `properties`/`required`
        de la entrada. Todo valor estructurado sale de listas cerradas;
        la prosa va separada, nunca como instrucción (ADR 0001).
        """
        tipo = str(form.get("tipo", ""))
        ficha = fichas_por_tipo.get(tipo)
        if ficha is None:
            raise PedidoInvalido("tipo_no_declarado", "tipo")
        if not ficha["disponible"]:
            raise PedidoInvalido("tipo_no_disponible", "tipo")

        actividad_ref = None
        if requiere_actividad(tipo):
            actividad_ref = str(form.get("actividad", "")).strip()
            if actividad_ref not in actividades_por_id:
                raise PedidoInvalido("actividad_requerida", "actividad")

        area_id = None
        if ficha["usa_area"]:
            area_id = str(form.get("area", "")).strip()
            if area_id not in areas:
                raise PedidoInvalido("area_invalida", "area")
        firma = None
        if ficha["usa_firma"]:
            firma = str(form.get("firma", "si")).strip().lower()
            if firma not in ("si", "no"):
                raise PedidoInvalido("firma_invalida", "firma")

        publicos_ids = [str(p) for p in form.getlist("publicos") if str(p)]
        if any(p not in publicos for p in publicos_ids):
            raise PedidoInvalido("publico_invalido", "publicos")
        if requiere_publicos(tipo) and not publicos_ids:
            raise PedidoInvalido("publicos_requeridos", "publicos")

        campos_pieza: dict[str, str] = {}
        for campo in ficha["campos"]:
            valor = str(form.get(f"campo_{campo['nombre']}", "")).strip()
            if campo["requerido"] and not valor:
                raise PedidoInvalido("campo_requerido", campo["nombre"])
            if valor:
                campos_pieza[campo["nombre"]] = valor
        if ficha["usa_area"]:
            campos_pieza["area_emisora"] = areas[area_id]
            if ficha["usa_firma"]:
                campos_pieza["firma_de_area"] = firma
        if actividad_ref is not None:
            # El título institucional de la actividad viaja en la ficha del
            # pedido: la bandeja y el detalle lo muestran sin resolver de
            # nuevo, y el pipeline de difusión lo toma de la fuente igual.
            campos_pieza.setdefault(
                "titulo", actividades_por_id[actividad_ref].get("titulo", "")
            )

        campos = {
            "pieza": campos_pieza,
            "pedido": {
                "publicos": publicos_ids,
                "area_id": area_id,
                "firma": firma,
                "asunto": str(form.get("asunto", "")).strip(),
            },
        }
        descripcion = str(form.get("descripcion", "")).strip()
        return {
            "tipo": tipo,
            "actividad_ref": actividad_ref,
            "campos": campos,
            "descripcion": descripcion,
        }

    @app.post("/nuevo-pedido", response_class=HTMLResponse)
    async def nuevo_pedido(request: Request) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        form = await request.form()
        if not csrf_ok(sesion, str(form.get("csrf", ""))):
            return render("sin_permiso.html", request, status_code=403)
        rol = rol_de(sesion)
        if rol not in ROLES_HABILITADOS:
            return render("sin_permiso.html", request, status_code=403)
        llave = str(form.get("llave", "")).strip() or uuid.uuid4().hex
        try:
            pedido = _validar_pedido(form)
        except PedidoInvalido as exc:
            return render(
                "nuevo_pedido.html",
                request,
                errores={exc.campo: exc.code},
                valores={
                    **{k: v for k, v in form.items()},
                    "publicos": [str(p) for p in form.getlist("publicos")],
                },
                status_code=400,
                **_formulario_ctx(sesion, llave),
            )
        if len(llave) > 250:
            llave = uuid.uuid4().hex
        try:
            creada = repositorio.crear_solicitud(
                idempotency_key=f"web:{llave}",
                solicitante_hash=_hash_solicitante(sesion),
                rol=rol,
                tipo_pieza=pedido["tipo"],
                actividad_ref=pedido["actividad_ref"],
                descripcion=pedido["descripcion"] or None,
                campos=pedido["campos"],
                ahora=datetime.now(timezone.utc),
            )
        except ConflictoIdempotencia:
            return render(
                "nuevo_pedido.html",
                request,
                errores={"llave": "idempotency_conflict"},
                valores={},
                status_code=409,
                **_formulario_ctx(sesion, uuid.uuid4().hex),
            )
        return RedirectResponse(
            f"/solicitudes/{creada.id_solicitud}", status_code=303
        )

    @app.get("/salud")
    def salud() -> dict[str, str]:
        return {"estado": "ok"}

    return app


def _hash_solicitante(sesion: Sesion) -> str:
    """Hash del correo del solicitante (ADR 0016), como el resto de la auditoría."""
    return hashlib.sha256(sesion.correo.encode("utf-8")).hexdigest()
