"""Canal web del Agente 1 (issue #149, ADR 0014 y ADR 0016).

La base del canal: login con Google verificado en el servidor, sesiones sólo
en memoria, autorización por padrón en cada request, bandeja compartida de
la SEU, pedido guiado durable e idempotente y worker de generación con
reserva por plazo. La revisión, edición en Docs, ajustes y decisión son del
issue #153.
"""

from .identidad import (
    IdentidadVerificada,
    VerificacionIdentidadError,
    VerificadorGoogle,
    VerificadorIdToken,
)
from .sesiones import (
    INACTIVIDAD_MAX,
    VIDA_MAX,
    Sesion,
    SesionesMemoria,
)

__all__ = [
    "INACTIVIDAD_MAX",
    "VIDA_MAX",
    "IdentidadVerificada",
    "Sesion",
    "SesionesMemoria",
    "VerificacionIdentidadError",
    "VerificadorGoogle",
    "VerificadorIdToken",
]
