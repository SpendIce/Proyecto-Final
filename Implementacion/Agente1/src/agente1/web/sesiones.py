"""Sesiones del canal web: sólo en memoria (ADR 0016 §sesiones).

La sesión vive en el proceso del servidor: nunca se escribe a disco, a la
base ni a logs. Se vence a los 30 minutos de inactividad y a las 8 horas de
vida como máximo; si el proceso se reinicia, todas las sesiones se pierden
y la persona vuelve a ingresar. Guarda el `sub` de Google, el correo (para
volver a resolver el rol contra el padrón en cada request), el rol vigente
y el token CSRF. Nunca guarda el ID token.

Decisiones que no se ven en el código:

- **Sólo memoria es la decisión, no una limitación** (ADR 0016): una
  sesión durable en la base obligaría a purgarla, auditarla y respaldarla
  — más superficie para guardar lo mismo que el navegador ya pide de
  nuevo en un minuto. Perderlas todas con un reinicio es aceptable: el
  login es un clic de Google, no un trámite.
- **El rol vive en la sesión pero no manda**: se guarda para mostrar la
  interfaz coherente, y la autorización lo vuelve a resolver contra el
  padrón en cada request. Si el padrón cambia el rol a mitad de sesión,
  el próximo request ve el rol nuevo — nunca el que quedó guardado.
- **El ID token no se guarda**: una vez verificado, la sesión conserva
  `sub` y correo para reconocer a la persona. El token es una credencial
  efímera de Google; retenerlo no compra nada y lo convierte en secreto
  que proteger.
"""

from __future__ import annotations

import hmac
import secrets
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

INACTIVIDAD_MAX = timedelta(minutes=30)
VIDA_MAX = timedelta(hours=8)


@dataclass(frozen=True)
class Sesion:
    """Estado de una sesión viva. `csrf_token` protege los formularios."""

    sid: str
    sub: str
    correo: str
    rol: str
    csrf_token: str
    creada_en: datetime
    ultimo_uso_en: datetime


class SesionesMemoria:
    """Registro de sesiones en memoria del proceso.

    `ahora` es la costura de tiempo para pruebas; en producción es UTC real.
    """

    def __init__(self, *, ahora: Callable[[], datetime] | None = None) -> None:
        self._sesiones: dict[str, Sesion] = {}
        self._ahora = ahora or (lambda: datetime.now(timezone.utc))

    def crear(self, *, sub: str, correo: str, rol: str) -> Sesion:
        ahora = self._ahora()
        sesion = Sesion(
            sid=secrets.token_urlsafe(32),
            sub=sub,
            correo=correo,
            rol=rol,
            csrf_token=secrets.token_urlsafe(32),
            creada_en=ahora,
            ultimo_uso_en=ahora,
        )
        self._sesiones[sesion.sid] = sesion
        return sesion

    def obtener(self, sid: str | None) -> Sesion | None:
        """Devuelve la sesión viva o `None` si no existe o venció.

        Cada consulta exitosa renueva la marca de uso (la inactividad se
        mide desde el último pedido, no desde el ingreso).
        """
        if not sid:
            return None
        sesion = self._sesiones.get(sid)
        if sesion is None:
            return None
        ahora = self._ahora()
        if (
            ahora - sesion.ultimo_uso_en > INACTIVIDAD_MAX
            or ahora - sesion.creada_en > VIDA_MAX
        ):
            self._sesiones.pop(sid, None)
            return None
        sesion = replace(sesion, ultimo_uso_en=ahora)
        self._sesiones[sid] = sesion
        return sesion

    def verificar_csrf(self, sesion: Sesion, token: str | None) -> bool:
        return bool(token) and hmac.compare_digest(sesion.csrf_token, token)

    def cerrar(self, sid: str | None) -> None:
        if sid:
            self._sesiones.pop(sid, None)

    def __len__(self) -> int:
        return len(self._sesiones)
