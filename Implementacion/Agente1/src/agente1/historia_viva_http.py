"""Transporte HTTP del contrato `/v1` de Historia Viva (#12).

Implementa `TransporteHistoriaViva` sobre `http.client`, como los demás
adapters del agente. El cliente (`historia_viva_cliente.py`) valida los cuerpos;
este módulo sólo arma los pedidos y traduce las fallas.

Decisiones que no se ven en el código:

- **Sólo los parámetros del contrato.** `/v1` responde `400` a un parámetro
  desconocido, así que la búsqueda manda exactamente `q`, `desde`, `hasta`,
  `tipo` y `limite`, nada de trazabilidad propia en la query.
- **Se decide por `codigo`, no por el status.** Cada `codigo` de `/v1` tiene
  su traducción al vocabulario cerrado de `historia_viva.py`. Un `codigo` que
  el contrato no conoce cae por familia: todo `4xx` es un pedido inválido y no
  se reintenta; un `5xx` es indisponibilidad. `404 pieza_no_disponible` en
  `GET /v1/piezas/{id}` es ausencia (`None`), no error; `404 ruta_inexistente`
  sí es error, porque delata una URL base mal configurada.
- **Ningún texto remoto sale de acá.** Del error se toman el `codigo`, el
  `Retry-After` (segundos) y `X-Solicitud-Id` validado; el `mensaje` se
  descarta, como en los demás adapters.
- **El token se lee en cada pedido.** `token` es un callable: rotar el token
  (varios activos, vencen a los 180 días) no exige reiniciar el agente. Es un
  string opaco; sólo se rechaza lo que rompería la cabecera.
- **`cabeceras_extra` es para las pruebas.** El mock Prism elige el escenario
  con `Prefer`; esa cabecera se inyecta al construir el transporte y no puede
  pisar `Authorization`, `Idempotency-Key` ni las de contenido.
- **El canal `ninguno` viaja como `null`.** Es la forma de `/v1` para un
  contenido sin canal propio, como una gacetilla.
- **El token vive en un archivo fuera del repositorio.** La configuración
  (`AGENTE1_HV_BASE_URL`, `AGENTE1_HV_TOKEN_ARCHIVO`) apunta a un archivo
  que no puede estar dentro de un repo git ni ser legible por otros usuarios;
  se relee en cada pedido, así que rotar el token es reemplazar el archivo.
"""

from __future__ import annotations

import json
import os
import re
import stat
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

from .historia_viva import Aporte, ConsultaFragmentos, HistoriaVivaError
from .historia_viva_cliente import (
    ClienteHistoriaViva,
    PoliticaCliente,
    RelojEspera,
    RespuestaAporte,
)

MAX_RESPUESTA_BYTES = 8 * 1_048_576

# Traducción de cada `codigo` de `/v1` (1.1.0-rc1) al vocabulario cerrado.
CODIGOS_V1 = {
    "parametros_invalidos": "historia_viva_request_invalid",
    "idempotency_key_reutilizada": "historia_viva_request_invalid",
    "fuente_inexistente": "historia_viva_request_invalid",
    "ruta_inexistente": "historia_viva_request_invalid",
    "pieza_no_disponible": "historia_viva_request_invalid",
    "token_invalido": "historia_viva_unauthorized",
    "operacion_no_permitida": "historia_viva_forbidden",
    "aporte_rechazado": "historia_viva_aporte_rechazado",
    "limite_superado": "historia_viva_rate_limited",
    "servicio_no_disponible": "historia_viva_unavailable",
}

_CABECERAS_PROPIAS = frozenset(
    {"authorization", "idempotency-key", "content-type", "accept", "content-length", "host"}
)
_CABECERA_RE = re.compile(r"[A-Za-z0-9-]{1,64}\Z")
_VALOR_CABECERA_RE = re.compile(r"[\x20-\x7e]{1,512}\Z")
_RETRY_AFTER_RE = re.compile(r"[0-9]{1,6}\Z")

_PREFIX = "AGENTE1_HV_"
ENV_BASE_URL = "AGENTE1_HV_BASE_URL"
ENV_TOKEN_ARCHIVO = "AGENTE1_HV_TOKEN_ARCHIVO"
_ALLOWED_KEYS = frozenset({ENV_BASE_URL, ENV_TOKEN_ARCHIVO})
MAX_TOKEN_BYTES = 4096


class ConfiguracionHistoriaVivaError(ValueError):
    """Configuración de Historia Viva rota; lleva un código, nunca valores."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ConfiguracionHistoriaViva:
    base_url: str
    token_archivo: Path


def cargar_configuracion_historia_viva(
    environ: Mapping[str, str] | None = None,
) -> ConfiguracionHistoriaViva | None:
    """Lee `AGENTE1_HV_*`; `None` cuando Historia Viva no está configurada.

    Mismo contrato que los otros loaders: una clave propia desconocida se
    rechaza, un valor vacío o una de las dos claves sin la otra es
    configuración rota, y el archivo del token tiene que estar fuera de todo
    repositorio git y no ser legible por el grupo ni por otros.
    """

    env = os.environ if environ is None else environ
    if any(clave.startswith(_PREFIX) and clave not in _ALLOWED_KEYS for clave in env):
        raise ConfiguracionHistoriaVivaError("historia_viva_config_unknown_key")
    if not any(clave in env for clave in _ALLOWED_KEYS):
        return None
    base_url = (env.get(ENV_BASE_URL) or "").strip()
    archivo = (env.get(ENV_TOKEN_ARCHIVO) or "").strip()
    if not base_url or not archivo:
        raise ConfiguracionHistoriaVivaError("historia_viva_config_incomplete")
    try:
        TransporteHistoriaVivaHttp(base_url, lambda: "")
    except ValueError:
        raise ConfiguracionHistoriaVivaError("historia_viva_config_base_url") from None
    ruta = Path(archivo).expanduser().resolve()
    if not ruta.is_file():
        raise ConfiguracionHistoriaVivaError("historia_viva_config_token_missing")
    if _dentro_de_repo_git(ruta):
        raise ConfiguracionHistoriaVivaError("historia_viva_config_token_in_repo")
    if ruta.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ConfiguracionHistoriaVivaError("historia_viva_config_token_permissions")
    return ConfiguracionHistoriaViva(base_url=base_url, token_archivo=ruta)


def token_desde_archivo(ruta: Path) -> Callable[[], str]:
    """Token releído en cada pedido; si no se puede leer, el pedido no sale."""

    def leer() -> str:
        try:
            with ruta.open("rb") as archivo:
                datos = archivo.read(MAX_TOKEN_BYTES + 1)
        except OSError:
            return ""
        if len(datos) > MAX_TOKEN_BYTES:
            return ""
        try:
            return datos.decode("ascii").strip()
        except UnicodeDecodeError:
            return ""

    return leer


def construir_cliente_historia_viva(
    config: ConfiguracionHistoriaViva,
    *,
    politica: PoliticaCliente | None = None,
    reloj: RelojEspera | None = None,
    cabeceras_extra: Mapping[str, str] | None = None,
) -> ClienteHistoriaViva:
    transporte = TransporteHistoriaVivaHttp(
        config.base_url,
        token_desde_archivo(config.token_archivo),
        cabeceras_extra=cabeceras_extra,
    )
    return ClienteHistoriaViva(transporte, politica=politica, reloj=reloj)


def _dentro_de_repo_git(ruta: Path) -> bool:
    return any((ancestro / ".git").exists() for ancestro in ruta.parents)


class _RespuestaCruda:
    def __init__(self, status: int, cuerpo: bytes, cabeceras: Mapping[str, str]) -> None:
        self.status = status
        self.cuerpo = cuerpo
        self.cabeceras = cabeceras


class TransporteHistoriaVivaHttp:
    """`TransporteHistoriaViva` contra una instancia real (o el mock) de `/v1`."""

    def __init__(
        self,
        base_url: str,
        token: Callable[[], str],
        *,
        cabeceras_extra: Mapping[str, str] | None = None,
    ) -> None:
        partes = urlsplit(base_url)
        if (
            partes.scheme not in {"http", "https"}
            or not partes.hostname
            or partes.query
            or partes.fragment
            or partes.username
        ):
            raise ValueError("base_url de Historia Viva inválida")
        self._https = partes.scheme == "https"
        self._host = partes.hostname
        self._port = partes.port
        self._prefijo = partes.path.rstrip("/")
        self._token = token
        extra = dict(cabeceras_extra or {})
        for nombre, valor in extra.items():
            if (
                not _CABECERA_RE.fullmatch(nombre)
                or nombre.lower() in _CABECERAS_PROPIAS
                or not _VALOR_CABECERA_RE.fullmatch(valor)
            ):
                raise ValueError("cabecera extra no admitida")
        self._extra = extra

    def get_fragmentos(
        self, consulta: ConsultaFragmentos, *, timeout: float
    ) -> dict[str, Any]:
        parametros: list[tuple[str, str]] = []
        if consulta.texto is not None:
            parametros.append(("q", consulta.texto))
        if consulta.desde is not None:
            parametros.append(("desde", consulta.desde.isoformat()))
        if consulta.hasta is not None:
            parametros.append(("hasta", consulta.hasta.isoformat()))
        if consulta.tipo is not None:
            parametros.append(("tipo", consulta.tipo))
        parametros.append(("limite", str(consulta.limite)))
        respuesta = self._pedir("GET", "/v1/fragmentos?" + urlencode(parametros), timeout=timeout)
        if respuesta.status != 200:
            raise _error_desde(respuesta)
        return _json(respuesta)

    def get_pieza(self, pieza_id: str, *, timeout: float) -> dict[str, Any] | None:
        ruta = "/v1/piezas/" + quote(pieza_id, safe="")
        respuesta = self._pedir("GET", ruta, timeout=timeout)
        if respuesta.status == 200:
            return _json(respuesta)
        if respuesta.status == 404 and _codigo(respuesta) == "pieza_no_disponible":
            return None
        raise _error_desde(respuesta)

    def post_aporte(self, aporte: Aporte, *, timeout: float) -> RespuestaAporte:
        cuerpo = {
            "titulo": aporte.titulo,
            "cuerpo": aporte.cuerpo,
            "tipo_contenido": aporte.tipo_contenido,
            "canal": None if aporte.canal == "ninguno" else aporte.canal,
            "piezas_fuente": list(aporte.piezas_fuente),
            "fragmentos_fuente": list(aporte.fragmentos_fuente),
        }
        respuesta = self._pedir(
            "POST",
            "/v1/aportes",
            timeout=timeout,
            cuerpo=json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"),
            cabeceras={
                "Content-Type": "application/json",
                "Idempotency-Key": aporte.clave_idempotencia,
            },
        )
        if respuesta.status in (200, 201):
            return RespuestaAporte(cuerpo=_json(respuesta), repetido=respuesta.status == 200)
        raise _error_desde(respuesta)

    def _pedir(
        self,
        metodo: str,
        ruta: str,
        *,
        timeout: float,
        cuerpo: bytes | None = None,
        cabeceras: Mapping[str, str] | None = None,
    ) -> _RespuestaCruda:
        token = self._token()
        if not isinstance(token, str) or not _VALOR_CABECERA_RE.fullmatch(token) or " " in token:
            # Sin token utilizable no hay pedido: es la misma situación que
            # un token vencido, y se registra igual.
            raise HistoriaVivaError("historia_viva_unauthorized")
        todas = {
            **self._extra,
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            **(cabeceras or {}),
        }
        deadline = time.monotonic() + timeout
        clase = HTTPSConnection if self._https else HTTPConnection
        conexion: HTTPConnection | None = None
        try:
            conexion = clase(self._host, self._port, timeout=_restante(deadline))
            conexion.request(metodo, self._prefijo + ruta, body=cuerpo, headers=todas)
            _ajustar_timeout(conexion, deadline)
            respuesta = conexion.getresponse()
            leido = bytearray()
            while len(leido) <= MAX_RESPUESTA_BYTES:
                _ajustar_timeout(conexion, deadline)
                bloque = respuesta.read1(min(65_536, MAX_RESPUESTA_BYTES + 1 - len(leido)))
                if not bloque:
                    break
                leido.extend(bloque)
            if len(leido) > MAX_RESPUESTA_BYTES:
                raise HistoriaVivaError("historia_viva_response_invalid")
            return _RespuestaCruda(
                respuesta.status,
                bytes(leido),
                {nombre.lower(): valor for nombre, valor in respuesta.getheaders()},
            )
        except (HTTPException, OSError, TimeoutError):
            # Sin respuesta (red, timeout, conexión cortada): transitorio. En un
            # POST no se sabe si el aporte quedó registrado; por eso el cliente
            # no reintenta aportes salvo que la política lo pida.
            raise HistoriaVivaError("historia_viva_unavailable") from None
        finally:
            if conexion is not None:
                conexion.close()


def _restante(deadline: float) -> float:
    restante = deadline - time.monotonic()
    if restante <= 0:
        raise TimeoutError
    return restante


def _ajustar_timeout(conexion: HTTPConnection, deadline: float) -> None:
    restante = _restante(deadline)
    conexion.timeout = restante
    if conexion.sock is not None:
        conexion.sock.settimeout(restante)


def _json(respuesta: _RespuestaCruda) -> dict[str, Any]:
    tipo = respuesta.cabeceras.get("content-type", "")
    if not tipo.split(";")[0].strip().lower() == "application/json":
        raise HistoriaVivaError("historia_viva_response_invalid")
    try:
        documento = json.loads(respuesta.cuerpo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HistoriaVivaError("historia_viva_response_invalid") from None
    if not isinstance(documento, dict):
        raise HistoriaVivaError("historia_viva_response_invalid")
    return documento


def _codigo(respuesta: _RespuestaCruda) -> str | None:
    try:
        documento = json.loads(respuesta.cuerpo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    codigo = documento.get("codigo") if isinstance(documento, dict) else None
    return codigo if isinstance(codigo, str) else None


def _solicitud_id(respuesta: _RespuestaCruda) -> str | None:
    try:
        documento = json.loads(respuesta.cuerpo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        documento = None
    if isinstance(documento, dict) and isinstance(documento.get("solicitud_id"), str):
        return documento["solicitud_id"]
    return respuesta.cabeceras.get("x-solicitud-id")


def _error_desde(respuesta: _RespuestaCruda) -> HistoriaVivaError:
    codigo = CODIGOS_V1.get(_codigo(respuesta) or "")
    if codigo is None:
        if 400 <= respuesta.status < 500:
            codigo = "historia_viva_request_invalid"
        elif respuesta.status >= 500:
            codigo = "historia_viva_unavailable"
        else:
            codigo = "historia_viva_response_invalid"
    retry_after = respuesta.cabeceras.get("retry-after", "")
    return HistoriaVivaError(
        codigo,
        reintentar_en=float(retry_after) if _RETRY_AFTER_RE.fullmatch(retry_after) else None,
        solicitud_id=_solicitud_id(respuesta),
    )
