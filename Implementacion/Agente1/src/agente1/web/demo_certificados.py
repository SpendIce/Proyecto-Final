"""POST web que siembra el lote de certificados de demostración (#168).

El dominio vive en `agente1.lote_demo`, compartido con el script de
consola: misma semilla y mismo `objeto_lote` determinista, así que la
siembra devuelve el lote que ya exista sin duplicar ni pisar la
decisión. La marca «demostración — sin validez» es `es_lote_demo`, que
reconoce al lote por su objeto aun después de la purga de `personas`.

`crear_app` registra la ruta sólo con `config.modo_demo`: fuera de la
demo el POST es 404 porque la ruta no existe. El handler revalida modo
vigente, CSRF y rol igual —la autorización es del backend, no del
cableado ni del formulario— y sólo escribe la fila del lote: no emite
ni envía nada.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping

from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse

from ..certificados_emision import ListaCierreError
from ..confirmaciones import ROL_APROBADOR_CONTENIDO
from ..lote_demo import (
    ACTIVIDAD_DEMO,
    CODIGO_ACTIVIDAD_AUSENTE,
    RepositorioLotesDemoPuerto,
    actividad_demo,
    crear_lote_demo,
    personas_demo,
)
from .certificados_web import (
    Autorizar,
    CsrfOk,
    DestinoLogin,
    LoteCertificadosError,
    Render,
    RolDe,
)

_AVISOS_ERROR = {
    CODIGO_ACTIVIDAD_AUSENTE: (
        "La actividad de demostración (FIE-DIF-02) no está en la fuente "
        "de actividades ni en los datos del repositorio."
    ),
}
_AVISO_GENERICO = "El lote de demostración no se pudo crear."


def registrar_rutas_demo_certificados(
    app: FastAPI,
    *,
    repositorio: RepositorioLotesDemoPuerto,
    autorizar: Autorizar,
    render: Render,
    rol_de: RolDe,
    csrf_ok: CsrfOk,
    destino_login: DestinoLogin,
    actividades: Iterable[Mapping[str, str]] | None,
    demo_activa: Callable[[], bool],
) -> None:
    """Cablea el POST que siembra el lote demo; la lógica queda acá.

    `crear_app` lo llama sólo con `config.modo_demo` activo, así que fuera
    de la demo la ruta no existe. El handler revalida el modo vigente y
    el rol igual: la autorización es del backend, no del cableado.
    """

    @app.post("/demo/lote-certificados")
    async def crear_lote(request: Request) -> Response:
        sesion = autorizar(request)
        if sesion is None:
            return destino_login()
        form = await request.form()
        if not csrf_ok(sesion, str(form.get("csrf", ""))):
            return render("sin_permiso.html", request, status_code=403)
        if not demo_activa():
            return render("sin_permiso.html", request, status_code=403)
        if rol_de(sesion) != ROL_APROBADOR_CONTENIDO:
            return render("sin_permiso.html", request, status_code=403)
        try:
            lote = crear_lote_demo(
                repositorio,
                id_actividad=ACTIVIDAD_DEMO,
                actividad=actividad_demo(actividades),
                personas=personas_demo(),
                generador_correo=sesion.correo,
            )
        except (LoteCertificadosError, ListaCierreError) as error:
            return render(
                "demo_lote_error.html",
                request,
                status_code=409,
                sesion=sesion,
                aviso=_AVISOS_ERROR.get(error.code, _AVISO_GENERICO),
            )
        return RedirectResponse(
            f"/certificados/{lote.id_lote}", status_code=303
        )


__all__ = ["registrar_rutas_demo_certificados"]
