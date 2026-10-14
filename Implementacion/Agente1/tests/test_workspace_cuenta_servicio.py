"""Cuenta de servicio con delegación: assertion RS256, lista cerrada de
cuentas suplantables, auditoría por token y la garantía de que no hay otro
camino para pedir un token (ADR 0011, issue #98).

Todas las pruebas corren offline: la credencial es una clave RSA generada
localmente y el intercambio usa un transporte falso. Nada de esto acredita una
corrida contra Google; eso es el paso en vivo del runbook.
"""

import base64
import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import parse_qs

import pytest

from agente1.google_workspace import RespuestaHttp
from agente1.workspace_auth import (
    CUENTA_AUDITORIA_NOMBRE,
    CUENTA_AUDITORIA_RECORD,
    IMPERSONATED_ACCOUNT_ENV,
    OAUTH_TOKEN_AUDIENCE,
    OAUTH_TOKEN_HOST,
    SCOPE_STRING_CUENTA_SERVICIO,
    SERVICE_ACCOUNT_KEY_ENV,
    CuentaServicioDelegadaProvider,
    OAuthRefreshTokenProvider,
    _validar_cuentas_suplantables,
    cargar_cuentas_suplantables,
    construir_token_provider,
    normalizar_cuenta,
    sha256_cuenta,
)
from agente1.workspace_config import (
    ConfiguracionWorkspaceError,
    TokenEntornoProvider,
)

CUENTA = "bot_ia1@fie.undef.edu.ar"
CLIENT_EMAIL = "svc-agente1@proyecto-dsi.iam.gserviceaccount.com"
CUENTAS_CERRADAS = frozenset({sha256_cuenta(CUENTA)})
PEM_SINTETICA = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkq\n-----END PRIVATE KEY-----\n"
SRC = Path(__file__).resolve().parents[1] / "src" / "agente1"


class TransporteCaptura:
    def __init__(self, respuesta: RespuestaHttp | None = None) -> None:
        self.respuesta = respuesta
        self.solicitudes: list[dict[str, object]] = []

    def request(
        self,
        *,
        method: str,
        host: str,
        target: str,
        headers: dict[str, str],
        body: bytes | None,
        deadline: float,
        max_response_bytes: int,
    ) -> RespuestaHttp:
        self.solicitudes.append(
            {
                "method": method,
                "host": host,
                "target": target,
                "headers": headers,
                "body": body,
            }
        )
        if self.respuesta is None:
            raise RuntimeError("sin red en la prueba")
        return self.respuesta


def respuesta_token(payload: dict[str, object], status: int = 200) -> RespuestaHttp:
    return RespuestaHttp(status=status, body=json.dumps(payload).encode())


def escribir_clave(ruta: Path, *, client_email: str = CLIENT_EMAIL, private_key: str = PEM_SINTETICA) -> Path:
    ruta.write_text(
        json.dumps(
            {
                "type": "service_account",
                "client_email": client_email,
                "private_key": private_key,
            }
        ),
        encoding="utf-8",
    )
    return ruta


@pytest.fixture
def clave_rsa(tmp_path: Path) -> Path:
    if shutil.which("openssl") is None:
        pytest.skip("openssl no disponible para firmar")
    pem = subprocess.run(
        ["openssl", "genrsa", "2048"], capture_output=True, check=True
    ).stdout.decode("ascii")
    return escribir_clave(tmp_path / "clave.json", private_key=pem)


def provider(
    *,
    transport: TransporteCaptura,
    ruta: Path,
    cuenta: str = CUENTA,
    cuentas: frozenset[str] = CUENTAS_CERRADAS,
    directorio: Path | None = None,
) -> CuentaServicioDelegadaProvider:
    return CuentaServicioDelegadaProvider(
        key_path=str(ruta),
        cuenta=cuenta,
        cuentas_suplantables=cuentas,
        transport=transport,
        directorio_auditoria=directorio,
    )


def partes_del_assertion(cuerpo: bytes) -> tuple[dict[str, object], dict[str, object], str]:
    formulario = parse_qs(cuerpo.decode())
    assert formulario["grant_type"] == ["urn:ietf:params:oauth:grant-type:jwt-bearer"]
    token = formulario["assertion"][0]
    encabezado_b64, reclamos_b64, firma_b64 = token.split(".")
    return _decodificar(encabezado_b64), _decodificar(reclamos_b64), firma_b64


def _decodificar(segmento: str) -> dict[str, object]:
    relleno = "=" * (-len(segmento) % 4)
    return json.loads(base64.urlsafe_b64decode(segmento + relleno))


def env_cuenta_servicio(ruta: Path, cuenta: str = CUENTA) -> dict[str, str]:
    return {
        SERVICE_ACCOUNT_KEY_ENV: str(ruta),
        IMPERSONATED_ACCOUNT_ENV: cuenta,
    }


# --- Intercambio y assertion -------------------------------------------


def test_intercambio_jwt_bearer_exitoso_y_reclamos(clave_rsa: Path):
    transporte = TransporteCaptura(respuesta_token({"access_token": "ya29.sintetico"}))
    token = provider(transport=transporte, ruta=clave_rsa).obtener_access_token()
    assert token == "ya29.sintetico"

    solicitud = transporte.solicitudes[0]
    assert solicitud["method"] == "POST"
    assert solicitud["host"] == OAUTH_TOKEN_HOST
    assert solicitud["target"] == "/token"
    assert solicitud["headers"]["Content-Type"] == "application/x-www-form-urlencoded"

    encabezado, reclamos, _ = partes_del_assertion(solicitud["body"])
    assert encabezado == {"alg": "RS256", "typ": "JWT"}
    assert reclamos["iss"] == CLIENT_EMAIL
    assert reclamos["sub"] == CUENTA
    assert reclamos["aud"] == OAUTH_TOKEN_AUDIENCE
    assert reclamos["scope"] == SCOPE_STRING_CUENTA_SERVICIO
    assert reclamos["exp"] > reclamos["iat"]


def test_firma_rs256_se_verifica_con_la_clave_publica(clave_rsa: Path, tmp_path: Path):
    transporte = TransporteCaptura(respuesta_token({"access_token": "ya29.sintetico"}))
    provider(transport=transporte, ruta=clave_rsa).obtener_access_token()

    cuerpo = transporte.solicitudes[0]["body"]
    # El assertion viaja urlencoded; se rearma el mensaje firmado desde el JWT.
    formulario = parse_qs(cuerpo.decode())
    assertion = formulario["assertion"][0]
    encabezado_b64, reclamos_b64, firma_b64 = assertion.split(".")
    mensaje = f"{encabezado_b64}.{reclamos_b64}".encode("ascii")
    firma = base64.urlsafe_b64decode(firma_b64 + "=" * (-len(firma_b64) % 4))

    clave = json.loads(clave_rsa.read_text(encoding="utf-8"))["private_key"]
    priv = tmp_path / "priv.pem"
    pub = tmp_path / "pub.pem"
    datos = tmp_path / "datos.bin"
    firma_path = tmp_path / "firma.bin"
    priv.write_text(clave, encoding="utf-8")
    datos.write_bytes(mensaje)
    firma_path.write_bytes(firma)
    subprocess.run(
        ["openssl", "rsa", "-in", str(priv), "-pubout", "-out", str(pub)],
        capture_output=True,
        check=True,
    )
    resultado = subprocess.run(
        [
            "openssl",
            "dgst",
            "-sha256",
            "-verify",
            str(pub),
            "-signature",
            str(firma_path),
            str(datos),
        ],
        capture_output=True,
        check=True,
    )
    assert b"Verified OK" in resultado.stdout


def test_cuenta_se_normaliza_antes_de_la_lista_y_del_sub(clave_rsa: Path):
    transporte = TransporteCaptura(respuesta_token({"access_token": "ya29.x"}))
    proveedor = provider(
        transport=transporte, ruta=clave_rsa, cuenta="  BOT_IA1@FIE.UNDEF.EDU.AR "
    )
    assert proveedor.cuenta_suplantada_sha256 == sha256_cuenta(CUENTA)
    proveedor.obtener_access_token()
    _, reclamos, _ = partes_del_assertion(transporte.solicitudes[0]["body"])
    assert reclamos["sub"] == CUENTA
    assert normalizar_cuenta("  BOT_IA1@FIE.UNDEF.EDU.AR ") == CUENTA


def test_cada_invocacion_hace_un_intercambio_nuevo(clave_rsa: Path):
    transporte = TransporteCaptura(respuesta_token({"access_token": "ya29.x"}))
    proveedor = provider(transport=transporte, ruta=clave_rsa)
    proveedor.obtener_access_token()
    proveedor.obtener_access_token()
    assert len(transporte.solicitudes) == 2


# --- Lista cerrada ------------------------------------------------------


def test_cuenta_fuera_de_la_lista_no_arranca(clave_rsa: Path):
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider(transport=TransporteCaptura(), ruta=clave_rsa, cuenta="otra@fie.undef.edu.ar")
    assert error.value.code == "workspace_impersonation_not_allowed"


def test_factory_rechaza_cuenta_fuera_de_la_lista(clave_rsa: Path):
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        construir_token_provider(env_cuenta_servicio(clave_rsa, "otra@fie.undef.edu.ar"))
    assert error.value.code == "workspace_impersonation_not_allowed"


def test_lista_cerrada_contiene_la_cuenta_tecnica():
    assert sha256_cuenta(CUENTA) in cargar_cuentas_suplantables()


def test_lista_cerrada_no_guarda_la_direccion_en_claro():
    assert CUENTA not in json.dumps(sorted(cargar_cuentas_suplantables()))


def test_contrato_lista_cerrada_rechaza_formas_abiertas():
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        _validar_cuentas_suplantables({"schema_version": "otro", "cuentas_sha256": ["a" * 64]})
    assert error.value.code == "workspace_cuentas_suplantables_invalid"
    for documento in (
        {"schema_version": "agente1_cuentas_suplantables_v1", "cuentas_sha256": []},
        {"schema_version": "agente1_cuentas_suplantables_v1", "cuentas_sha256": [CUENTA]},
        {"schema_version": "agente1_cuentas_suplantables_v1"},
        "no-es-un-dict",
    ):
        with pytest.raises(ConfiguracionWorkspaceError) as error:
            _validar_cuentas_suplantables(documento)
        assert error.value.code == "workspace_cuentas_suplantables_invalid"


# --- Clave ausente, ilegible o malformada -------------------------------


def test_clave_ausente_falla_sin_filtrar_la_ruta(tmp_path: Path):
    ruta = tmp_path / "no-existe.json"
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider(transport=TransporteCaptura(), ruta=ruta).obtener_access_token()
    assert error.value.code == "workspace_key_unreadable"
    assert str(ruta) not in str(error.value)


def test_clave_malformada_falla_sin_filtrar_contenido(tmp_path: Path):
    ruta = tmp_path / "clave.json"
    ruta.write_text("{ no es json", encoding="utf-8")
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider(transport=TransporteCaptura(), ruta=ruta).obtener_access_token()
    assert error.value.code == "workspace_key_invalid"
    assert "no es json" not in str(error.value)


def test_clave_sin_campos_requeridos_falla(tmp_path: Path):
    ruta = tmp_path / "clave.json"
    ruta.write_text(json.dumps({"type": "service_account"}), encoding="utf-8")
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider(transport=TransporteCaptura(), ruta=ruta).obtener_access_token()
    assert error.value.code == "workspace_key_invalid"


def test_clave_con_json_no_objeto_falla(tmp_path: Path):
    ruta = tmp_path / "clave.json"
    ruta.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider(transport=TransporteCaptura(), ruta=ruta).obtener_access_token()
    assert error.value.code == "workspace_key_invalid"


# --- Intercambio denegado y sin reintentos ------------------------------


@pytest.mark.parametrize("status", [400, 401, 403])
def test_intercambio_denegado_falla_con_denied_y_sin_reintento(status: int, clave_rsa: Path):
    transporte = TransporteCaptura(respuesta_token({"error": "invalid_grant"}, status=status))
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider(transport=transporte, ruta=clave_rsa).obtener_access_token()
    assert error.value.code == "workspace_token_exchange_denied"
    assert len(transporte.solicitudes) == 1


def test_falla_del_endpoint_no_se_reintenta(clave_rsa: Path):
    transporte = TransporteCaptura(respuesta_token({}, status=500))
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider(transport=transporte, ruta=clave_rsa).obtener_access_token()
    assert error.value.code == "workspace_token_exchange_unavailable"
    assert len(transporte.solicitudes) == 1


def test_rate_limit_tiene_codigo_propio(clave_rsa: Path):
    transporte = TransporteCaptura(respuesta_token({}, status=429))
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider(transport=transporte, ruta=clave_rsa).obtener_access_token()
    assert error.value.code == "workspace_token_exchange_rate_limited"


def test_respuesta_sin_access_token_es_invalida(clave_rsa: Path):
    transporte = TransporteCaptura(respuesta_token({"token_type": "Bearer"}))
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider(transport=transporte, ruta=clave_rsa).obtener_access_token()
    assert error.value.code == "workspace_token_exchange_response_invalid"


def test_falla_de_red_se_traduce_a_unavailable(clave_rsa: Path):
    transporte = TransporteCaptura(respuesta=None)
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider(transport=transporte, ruta=clave_rsa).obtener_access_token()
    assert error.value.code == "workspace_token_exchange_unavailable"


# --- Firma con openssl --------------------------------------------------


def test_sin_openssl_falla_cerrado(tmp_path: Path, monkeypatch):
    ruta = escribir_clave(tmp_path / "clave.json")
    monkeypatch.setattr("agente1.workspace_auth._resolver_openssl", lambda: None)
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider(transport=TransporteCaptura(), ruta=ruta).obtener_access_token()
    assert error.value.code == "workspace_auth_signing_unavailable"


# --- Auditoría ----------------------------------------------------------


def test_auditoria_registra_hash_y_version(clave_rsa: Path, tmp_path: Path):
    transporte = TransporteCaptura(respuesta_token({"access_token": "ya29.x"}))
    salida = tmp_path / "salida"
    provider(transport=transporte, ruta=clave_rsa, directorio=salida).obtener_access_token()

    lineas = (salida / "logs" / CUENTA_AUDITORIA_NOMBRE).read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 1
    entrada = json.loads(lineas[0])
    assert entrada["record"] == CUENTA_AUDITORIA_RECORD
    assert entrada["cuenta_suplantada_sha256"] == sha256_cuenta(CUENTA)
    assert entrada["version"] == "0.1.0"
    assert entrada["resultado"] == "emitido"
    assert entradas_iso(entrada["ejecutado_en"])
    assert CUENTA not in lineas[0]


def test_auditoria_no_se_escribe_si_el_intercambio_falla(clave_rsa: Path, tmp_path: Path):
    transporte = TransporteCaptura(respuesta_token({"error": "invalid_grant"}, status=403))
    salida = tmp_path / "salida"
    with pytest.raises(ConfiguracionWorkspaceError):
        provider(transport=transporte, ruta=clave_rsa, directorio=salida).obtener_access_token()
    assert not (salida / "logs" / CUENTA_AUDITORIA_NOMBRE).exists()


def test_auditoria_escrita_antes_de_entregar_el_token(clave_rsa: Path, tmp_path: Path):
    """La auditoría no es best-effort: si no se puede escribir, no hay token."""

    transporte = TransporteCaptura(respuesta_token({"access_token": "ya29.x"}))
    salida = tmp_path / "salida"
    # `logs` como archivo hace que el append falle con OSError.
    (salida / "logs").parent.mkdir(parents=True, exist_ok=True)
    (salida / "logs").write_text("no es un directorio", encoding="utf-8")
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        provider(transport=transporte, ruta=clave_rsa, directorio=salida).obtener_access_token()
    assert error.value.code == "workspace_cuenta_audit_unavailable"


def entradas_iso(valor: object) -> bool:
    from datetime import datetime

    return isinstance(valor, str) and datetime.fromisoformat(valor) is not None


# --- Factory: la cuenta de servicio es la elegida -----------------------


def test_factory_prefiere_cuenta_de_servicio_sobre_oauth(clave_rsa: Path):
    env = env_cuenta_servicio(clave_rsa)
    env.update(
        {
            "AGENTE1_WORKSPACE_OAUTH_CLIENT_ID": "12345.apps.googleusercontent.com",
            "AGENTE1_WORKSPACE_OAUTH_CLIENT_SECRET": "GOCSPX-secreto",
            "AGENTE1_WORKSPACE_OAUTH_REFRESH_TOKEN": "1//refresh",
        }
    )
    proveedor = construir_token_provider(env)
    assert isinstance(proveedor, CuentaServicioDelegadaProvider)


def test_factory_no_cae_a_oauth_con_cuenta_de_servicio_a_medias(clave_rsa: Path):
    env = {
        SERVICE_ACCOUNT_KEY_ENV: str(clave_rsa),
        "AGENTE1_WORKSPACE_OAUTH_CLIENT_ID": "12345.apps.googleusercontent.com",
        "AGENTE1_WORKSPACE_OAUTH_CLIENT_SECRET": "GOCSPX-secreto",
        "AGENTE1_WORKSPACE_OAUTH_REFRESH_TOKEN": "1//refresh",
    }
    with pytest.raises(ConfiguracionWorkspaceError) as error:
        construir_token_provider(env)
    assert error.value.code == "workspace_auth_config_incomplete"


def test_factory_usa_oauth_cuando_no_hay_cuenta_de_servicio():
    env = {
        "AGENTE1_WORKSPACE_OAUTH_CLIENT_ID": "12345.apps.googleusercontent.com",
        "AGENTE1_WORKSPACE_OAUTH_CLIENT_SECRET": "GOCSPX-secreto",
        "AGENTE1_WORKSPACE_OAUTH_REFRESH_TOKEN": "1//refresh",
    }
    assert isinstance(construir_token_provider(env), OAuthRefreshTokenProvider)


def test_factory_cae_al_token_de_entorno_sin_credenciales_durables():
    assert isinstance(construir_token_provider({}), TokenEntornoProvider)


def test_repr_no_expone_la_cuenta_ni_la_ruta(clave_rsa: Path):
    representacion = repr(provider(transport=TransporteCaptura(), ruta=clave_rsa))
    assert CUENTA not in representacion
    assert str(clave_rsa) not in representacion
    assert "redacted" in representacion


# --- Garantía de camino único -------------------------------------------


# Marcadores que sólo deben aparecer en el único módulo que pide tokens. Si
# alguien agrega un segundo camino que firma un assertion o intercambia un
# token, esta prueba falla.
_MARCADORES_DE_TOKEN = (
    "grant_type",
    "jwt-bearer",
    "refresh_token",
    "assertion",
    "oauth2.googleapis.com",
    "client_secret",
    "private_key",
)


def test_ningun_otro_camino_pide_un_token():
    infractores: dict[str, list[str]] = {}
    for ruta in sorted(SRC.rglob("*.py")):
        if ruta.name == "workspace_auth.py":
            continue
        texto = ruta.read_text(encoding="utf-8")
        encontrados = [marcador for marcador in _MARCADORES_DE_TOKEN if marcador in texto]
        if encontrados:
            infractores[ruta.relative_to(SRC).as_posix()] = encontrados
    assert infractores == {}


def test_el_provider_es_el_unico_que_define_obtener_access_token():
    # Están `google_workspace` (el Protocol `AccessTokenProvider`) y
    # `workspace_config` (`TokenEntornoProvider`, el token efímero de
    # desarrollo). Un módulo nuevo con esta implementación falla acá.
    definiciones: list[str] = []
    for ruta in sorted(SRC.rglob("*.py")):
        if "def obtener_access_token" in ruta.read_text(encoding="utf-8"):
            definiciones.append(ruta.name)
    assert set(definiciones) == {
        "google_workspace.py",
        "workspace_auth.py",
        "workspace_config.py",
    }
