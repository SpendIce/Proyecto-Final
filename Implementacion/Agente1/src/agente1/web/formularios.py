"""Lectura de formularios acotada antes de procesar multipart."""
from __future__ import annotations

from starlette.datastructures import FormData
from starlette.exceptions import HTTPException
from starlette.requests import Request


async def leer_formulario_acotado(
    request: Request, *, max_bytes: int, max_files: int = 0, max_fields: int = 8
) -> FormData:
    # Content-Length no alcanza: también se limita el cuerpo por chunks.
    # El límite previo al parser impide que UploadFile derive datos a disco.
    cuerpo = bytearray()
    async for fragmento in request.stream():
        if len(cuerpo) + len(fragmento) > max_bytes:
            raise HTTPException(413, "Formulario demasiado grande")
        cuerpo.extend(fragmento)

    async def recibir():
        return {"type": "http.request", "body": bytes(cuerpo), "more_body": False}

    acotado = Request(request.scope, receive=recibir)
    try:
        return await acotado.form(
            max_files=max_files, max_fields=max_fields, max_part_size=max_bytes
        )
    except ValueError:
        raise HTTPException(400, "Formulario inválido") from None
