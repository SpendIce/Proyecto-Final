"""Aplicación web del canal del Agente 1 (issue #149).

HTML servido por FastAPI + Jinja2, del mismo origen: sin SPA ni build de
frontend. JavaScript mínimo: el botón de Google Identity Services y el
polling del estado «generando». Seguridad del diseño §3 y ADR 0014: el ID
token se verifica en el servidor, la sesión vive sólo en memoria, toda
escritura exige CSRF y el rol se resuelve contra el padrón en cada request;
nunca se acepta rol ni correo enviados por el navegador.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..canal_form import PadronRoles
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


@dataclass(frozen=True)
class ConfiguracionWeb:
    """Config declarada por entorno: nada institucional queda en el repo."""

    google_client_id: str
    dominio_hd: str | None = None
    modo_prueba: bool = False
    cookie_secure: bool = True


class PedidoInvalido(ValueError):
    def __init__(self, code: str, campo: str) -> None:
        self.code = code
        self.campo = campo
        super().__init__(code)


def _catalogo_areas() -> dict[str, str]:
    contrato = json.loads(
        files("agente1")
        .joinpath("contracts", "areas_emisoras_v2.json")
        .read_text(encoding="utf-8")
    )
    return {str(a["id"]): str(a["nombre"]) for a in contrato["areas"]}


def _catalogo_publicos() -> dict[str, str]:
    contrato = json.loads(
        files("agente1")
        .joinpath("contracts", "publicos_destinatarios_v1.json")
        .read_text(encoding="utf-8")
    )
    return {str(p["id"]): str(p["nombre"]) for p in contrato["publicos"]}


def _campos_por_tipo() -> dict[str, list[dict[str, Any]]]:
    """Campos del formulario por tipo, desde los contratos de entrada.

    `area_emisora` y `firma_de_area` salen del formulario aparte (el área
    es un select de catálogo y la firma una opción separada), así que no se
    repiten como inputs libres.
    """
    resultado: dict[str, list[dict[str, Any]]] = {}
    for tipo in tipos():
        if tipo == "difusion_de_actividad":
            resultado[tipo] = []
            continue
        entrada = cargar_entrada(tipo)
        requeridos = set(entrada["required"])
        campos = []
        for nombre, prop in entrada.get("properties", {}).items():
            if nombre in ("area_emisora", "firma_de_area"):
                continue
            campos.append(
                {
                    "nombre": nombre,
                    "requerido": nombre in requeridos,
                    "area": nombre in _CAMPOS_AREA,
                }
            )
        resultado[tipo] = campos
    return resultado


def crear_app(
    *,
    config: ConfiguracionWeb,
    verificador: VerificadorIdToken,
    padron: PadronRoles,
    repositorio: RepositorioWeb,
    sesiones: SesionesMemoria | None = None,
    actividades: list[dict[str, str]] | None = None,
) -> FastAPI:
    """Fábrica de la app: todo servicio externo entra inyectado.

    `actividades` es la lista visible de la fuente de solicitudes (sólo
    lectura), para el select condicional del pedido.
    """
    sesiones = sesiones if sesiones is not None else SesionesMemoria()
    base = Path(__file__).resolve().parent
    plantillas = Jinja2Templates(directory=str(base / "plantillas"))
    areas = _catalogo_areas()
    publicos = _catalogo_publicos()
    campos_por_tipo = _campos_por_tipo()
    actividades = actividades or []

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

    def destino_login() -> RedirectResponse:
        return RedirectResponse("/ingresar", status_code=303)

    def csrf_ok(sesion: Sesion, token: str | None) -> bool:
        return sesiones.verificar_csrf(sesion, token)

    # ---------- ingreso ----------

    @app.get("/", response_class=HTMLResponse)
    def raiz(request: Request) -> Response:
        return RedirectResponse(
            "/bandeja" if autorizar(request) else "/ingresar",
            status_code=303,
        )

    @app.get("/ingresar", response_class=HTMLResponse)
    def ingresar_form(request: Request) -> Response:
        if autorizar(request):
            return RedirectResponse("/bandeja", status_code=303)
        return render("ingresar.html", request, error=None)

    @app.post("/ingresar", response_class=HTMLResponse)
    def ingresar(request: Request, credential: str = Form("")) -> Response:
        try:
            identidad = verificador.verificar(credential)
        except VerificacionIdentidadError:
            return render(
                "ingresar.html",
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
        respuesta = RedirectResponse("/bandeja", status_code=303)
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
                "titulo": i.titulo or i.actividad_ref or i.id_solicitud,
                "actividad": i.actividad_ref,
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
        return render(
            "solicitud.html",
            request,
            sesion=sesion,
            s=detalle_sol,
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
                }
                for t in tipos()
            ],
            "campos_por_tipo": campos_por_tipo,
            "areas": areas,
            "publicos": publicos,
            "actividades": actividades,
        }

    @app.get("/nuevo-pedido", response_class=HTMLResponse)
    def nuevo_pedido_form(request: Request) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        return render(
            "nuevo_pedido.html",
            request,
            errores={},
            valores={},
            **_formulario_ctx(sesion, uuid.uuid4().hex),
        )

    def _validar_pedido(form: dict[str, Any]) -> dict[str, Any]:
        """Valida el pedido del lado del servidor y arma sus campos.

        Devuelve `{"tipo", "actividad_ref", "campos", "descripcion"}` o
        levanta `PedidoInvalido`. Todo valor estructurado sale de listas
        cerradas; la prosa va separada, nunca como instrucción (ADR 0001).
        """
        tipo = str(form.get("tipo", ""))
        if tipo not in tipos():
            raise PedidoInvalido("tipo_no_declarado", "tipo")

        actividad_ref = None
        if requiere_actividad(tipo):
            actividad_ref = str(form.get("actividad", "")).strip()
            ids = {a.get("id_actividad") for a in actividades}
            if actividad_ref not in ids:
                raise PedidoInvalido("actividad_requerida", "actividad")

        area_id = str(form.get("area", "")).strip()
        if area_id not in areas:
            raise PedidoInvalido("area_invalida", "area")
        firma = str(form.get("firma", "si")).strip().lower()
        if firma not in ("si", "no"):
            raise PedidoInvalido("firma_invalida", "firma")
        publicos_ids = [str(p) for p in form.getlist("publicos") if str(p)]
        if any(p not in publicos for p in publicos_ids):
            raise PedidoInvalido("publico_invalido", "publicos")
        if requiere_publicos(tipo) and not publicos_ids:
            raise PedidoInvalido("publicos_requeridos", "publicos")

        campos_pieza: dict[str, str] = {}
        for campo in campos_por_tipo[tipo]:
            valor = str(form.get(f"campo_{campo['nombre']}", "")).strip()
            if campo["requerido"] and not valor:
                raise PedidoInvalido("campo_requerido", campo["nombre"])
            if valor:
                campos_pieza[campo["nombre"]] = valor
        if not requiere_actividad(tipo):
            if "area_emisora" in {
                p for p in cargar_entrada(tipo).get("properties", {})
            }:
                campos_pieza["area_emisora"] = areas[area_id]
            campos_pieza["firma_de_area"] = firma

        descripcion = str(form.get("descripcion", "")).strip()
        campos = {
            "pieza": campos_pieza,
            "pedido": {
                "publicos": publicos_ids,
                "area_id": area_id,
                "firma": firma,
                "asunto": str(form.get("asunto", "")).strip(),
            },
        }
        return {
            "tipo": tipo,
            "actividad_ref": actividad_ref,
            "campos": campos,
            "descripcion": descripcion or "Sin descripción adicional.",
        }

    @app.post("/nuevo-pedido", response_class=HTMLResponse)
    async def nuevo_pedido(request: Request) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        form = await request.form()
        if not csrf_ok(sesion, str(form.get("csrf", ""))):
            return render("sin_permiso.html", request, status_code=403)
        rol = padron.rol_para(sesion.correo)
        if rol not in ROLES_HABILITADOS:
            return render("sin_permiso.html", request, status_code=403)
        try:
            pedido = _validar_pedido(form)
        except PedidoInvalido as exc:
            llave = str(form.get("llave", "")) or uuid.uuid4().hex
            return render(
                "nuevo_pedido.html",
                request,
                errores={exc.campo: exc.code},
                valores={k: v for k, v in form.items()},
                status_code=400,
                **_formulario_ctx(sesion, llave),
            )
        llave = str(form.get("llave", "")).strip()
        if not llave or len(llave) > 250:
            llave = uuid.uuid4().hex
        try:
            creada = repositorio.crear_solicitud(
                idempotency_key=f"web:{llave}",
                solicitante_hash=_hash_solicitante(sesion),
                rol=rol,
                tipo_pieza=pedido["tipo"],
                actividad_ref=pedido["actividad_ref"],
                descripcion=pedido["descripcion"],
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
    import hashlib

    return hashlib.sha256(sesion.sub.encode("utf-8")).hexdigest()
