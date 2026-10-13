"""Respaldo diario del estado local en Drive y restauración (#86).

Cubre el artefacto (conjunto declarado, manifiesto, hashes), el puerto de
destino en sus dos implementaciones —la carpeta fake declarada y el
adapter real de Drive con transporte inyectado—, el paso diario con su
auditoría y su aviso, y la restauración con la marca
`ENVIO_INDETERMINADO` para las aprobaciones posteriores.
"""

import hashlib
import io
import json
import tarfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from agente1.confirmaciones import (
    RegistroConfirmacionesArchivo,
)
from agente1.respaldo import (
    AUDITORIA_NOMBRE,
    MANIFEST_RECORD,
    MAX_ARTEFACTO_BYTES,
    NOMBRE_MANIFIESTO,
    AvisoOperadorJsonl,
    CarpetaRespaldoLocal,
    ConfiguracionRespaldoError,
    GoogleDriveRespaldoDiario,
    RespaldoDiarioError,
    RespaldoRemoto,
    cargar_configuracion_respaldo,
    construir_artefacto,
    correr_respaldo_diario,
    nombre_respaldo,
    restaurar_estado_respaldo,
)

MARCA = datetime(2026, 10, 5, 13, 0, tzinfo=timezone.utc)  # lunes, en ventana
FECHA = date(2026, 10, 5)
CARPETA_ID = "a" * 44


def poblar_salida(directorio: Path) -> None:
    (directorio / "logs").mkdir(parents=True)
    (directorio / "manifests").mkdir(parents=True)
    (directorio / "estado-canal-form").mkdir()
    (directorio / "estado-decisiones").mkdir()
    (directorio / "cola-envios").mkdir()
    (directorio / "logs" / "ejecuciones.jsonl").write_text(
        '{"evento":"x"}\n', encoding="utf-8"
    )
    (directorio / "manifests" / "m.json").write_text("{}", encoding="utf-8")
    (directorio / "insumos-procesados.jsonl").write_text("proc\n", encoding="utf-8")
    (directorio / "estado-canal-form" / "atendidos-canal-form.jsonl").write_text(
        "atendido\n", encoding="utf-8"
    )
    (directorio / "estado-decisiones" / "decisiones-pendientes.jsonl").write_text(
        "pendiente\n", encoding="utf-8"
    )
    (directorio / "cola-envios" / f"{'ab' * 32}.json").write_text(
        "{}", encoding="utf-8"
    )
    # Lo que NO es estado declarado: no puede entrar al artefacto.
    (directorio / "borradores").mkdir()
    (directorio / "borradores" / "borrador.md").write_text(
        "borrador", encoding="utf-8"
    )
    (directorio / "scheduler-corrida.lock").write_text("", encoding="utf-8")


def clave(numero: int) -> str:
    return hashlib.sha256(f"caso-{numero}".encode()).hexdigest()


# El camino de transiciones reales para materializar cada estado: cada
# paso es un compare-and-set contra el estado anterior, igual que haría el
# pipeline. `transicionar` no exige el estado declarado del pipeline: la
# secuencia respeta el orden real.
_CAMINOS_ESTADO: dict[str, list[str]] = {
    "PENDIENTE_VALIDACION": [],
    "APROBADA_UTILITARIA": ["APROBADA_UTILITARIA"],
    "APROBADA_SEMANTICA": ["APROBADA_SEMANTICA"],
    "APROBADA": ["APROBADA_UTILITARIA", "APROBADA"],
    "ENVIO_ENCOLADO": ["APROBADA_UTILITARIA", "APROBADA", "ENVIO_ENCOLADO"],
    "ENVIO_RESERVADO": [
        "APROBADA_UTILITARIA",
        "APROBADA",
        "ENVIO_ENCOLADO",
        "ENVIO_RESERVADO",
    ],
    "EMISION_RESERVADA": ["APROBADA_UTILITARIA", "APROBADA", "EMISION_RESERVADA"],
    "ENVIO_INDETERMINADO": [
        "APROBADA_UTILITARIA",
        "APROBADA",
        "ENVIO_ENCOLADO",
        "ENVIO_RESERVADO",
        "ENVIO_INDETERMINADO",
    ],
    "ENVIADA_SIMULADA": [
        "APROBADA_UTILITARIA",
        "APROBADA",
        "ENVIO_ENCOLADO",
        "ENVIO_RESERVADO",
        "ENVIADA_SIMULADA",
    ],
    "FALLIDA": [
        "APROBADA_UTILITARIA",
        "APROBADA",
        "ENVIO_ENCOLADO",
        "ENVIO_RESERVADO",
        "FALLIDA",
    ],
    "RECHAZADA": ["RECHAZADA"],
}


def crear_en_estado(
    registro: RegistroConfirmacionesArchivo, key: str, estado: str
) -> None:
    """Materializa una entrada en el estado pedido, por transiciones reales."""

    assert registro.crear(key, "asunto", "cuerpo")
    actual = "PENDIENTE_VALIDACION"
    for paso in _CAMINOS_ESTADO[estado]:
        assert registro.transicionar(key, frozenset({actual}), paso)
        actual = paso


def lineas_auditoria(directorio: Path) -> list[dict[str, object]]:
    ruta = directorio / "logs" / AUDITORIA_NOMBRE
    if not ruta.exists():
        return []
    return [
        json.loads(texto)
        for texto in ruta.read_text(encoding="utf-8").splitlines()
        if texto.strip()
    ]


class DestinoStub:
    """DestinoRespaldos de prueba: registra qué se pidió, con fallas opt-in."""

    def __init__(
        self,
        remotos=(),
        *,
        error_subir: str | None = None,
        error_listar: str | None = None,
        errores_borrar: frozenset[str] = frozenset(),
    ) -> None:
        self.remotos = list(remotos)
        self.error_subir = error_subir
        self.error_listar = error_listar
        self.errores_borrar = errores_borrar
        self.subidas: list[tuple[str, bytes]] = []
        self.borrados: list[str] = []

    def subir(self, *, nombre: str, contenido: bytes) -> str:
        if self.error_subir:
            raise RespaldoDiarioError(self.error_subir, etapa="subida")
        self.subidas.append((nombre, contenido))
        return f"stub-id-{nombre}"

    def listar(self):
        if self.error_listar:
            raise RespaldoDiarioError(self.error_listar, etapa="listado")
        return tuple(self.remotos)

    def borrar(self, *, archivo_id: str) -> None:
        if archivo_id in self.errores_borrar:
            raise RespaldoDiarioError("drive_unavailable", etapa="borrado")
        self.borrados.append(archivo_id)


class AvisoStub:
    def __init__(self, *, fallar: bool = False) -> None:
        self.llamados: list[tuple[str, str]] = []
        self.fallar = fallar

    def avisar(self, *, asunto: str, cuerpo: str) -> str:
        if self.fallar:
            raise RuntimeError("aviso caido")
        self.llamados.append((asunto, cuerpo))
        return "enviado"


class TokenStub:
    def __init__(self) -> None:
        self.llamados = 0

    def obtener_access_token(self) -> str:
        self.llamados += 1
        return "token-prueba"


class TransporteStub:
    def __init__(self, *respuestas) -> None:
        self.respuestas = list(respuestas)
        self.llamadas: list[dict[str, object]] = []

    def request(self, *, method, host, target, headers, body, deadline, max_response_bytes):
        self.llamadas.append(
            {
                "method": method,
                "host": host,
                "target": target,
                "headers": headers,
                "body": body,
            }
        )
        if not self.respuestas:
            raise RuntimeError("sin respuesta programada")
        return self.respuestas.pop(0)


def respuesta(status: int, documento: dict | None = None):
    from agente1.google_workspace import RespuestaHttp

    return RespuestaHttp(
        status=status,
        body=(
            b""
            if documento is None
            else json.dumps(documento).encode("utf-8")
        ),
    )


# ---------------------------------------------------------------------------
# Configuración por entorno
# ---------------------------------------------------------------------------


def test_config_ausente_devuelve_none() -> None:
    assert cargar_configuracion_respaldo({}) is None


def test_config_clave_desconocida_rechazada() -> None:
    with pytest.raises(ConfiguracionRespaldoError) as exc:
        cargar_configuracion_respaldo({"AGENTE1_RESPALDO_INVENTADA": "x"})
    assert exc.value.code == "respaldo_config_unknown_key"


def test_config_fake_declarada() -> None:
    config = cargar_configuracion_respaldo(
        {"AGENTE1_RESPALDO_CARPETA_FAKE": "/tmp/carpeta"}
    )
    assert config is not None
    assert config.modo == "fake_local"
    assert config.carpeta_fake == Path("/tmp/carpeta")
    assert config.carpeta_id is None


@pytest.mark.parametrize(
    "environ, codigo",
    [
        # Las dos carpetas: el destino tiene que ser inequívoco.
        (
            {
                "AGENTE1_RESPALDO_CARPETA_FAKE": "/tmp/x",
                "AGENTE1_RESPALDO_CARPETA_ID": CARPETA_ID,
            },
            "respaldo_config_incomplete",
        ),
        # Carpeta live sin aviso ni confirmación.
        ({"AGENTE1_RESPALDO_CARPETA_ID": CARPETA_ID}, "respaldo_config_incomplete"),
        # Carpeta live con aviso pero sin el segundo opt-in.
        (
            {
                "AGENTE1_RESPALDO_CARPETA_ID": CARPETA_ID,
                "AGENTE1_RESPALDO_AVISO_DESTINATARIO": "operador@example.com",
            },
            "respaldo_config_write_not_confirmed",
        ),
        # Id de carpeta que no cumple la forma.
        (
            {
                "AGENTE1_RESPALDO_CARPETA_ID": "../malo",
                "AGENTE1_RESPALDO_AVISO_DESTINATARIO": "operador@example.com",
                "AGENTE1_RESPALDO_CONFIRMAR_ESCRITURA": "SI",
            },
            "respaldo_config_invalid",
        ),
        # Aviso declarado en modo fake: es una trampa silenciosa.
        (
            {
                "AGENTE1_RESPALDO_CARPETA_FAKE": "/tmp/x",
                "AGENTE1_RESPALDO_AVISO_DESTINATARIO": "operador@example.com",
            },
            "respaldo_config_invalid",
        ),
        # Timeout fuera de rango.
        (
            {
                "AGENTE1_RESPALDO_CARPETA_FAKE": "/tmp/x",
                "AGENTE1_RESPALDO_TIMEOUT_S": "9999",
            },
            "respaldo_config_invalid",
        ),
        (
            {
                "AGENTE1_RESPALDO_CARPETA_FAKE": "/tmp/x",
                "AGENTE1_RESPALDO_TIMEOUT_S": "abc",
            },
            "respaldo_config_invalid",
        ),
    ],
)
def test_config_invalida(environ: dict[str, str], codigo: str) -> None:
    with pytest.raises(ConfiguracionRespaldoError) as exc:
        cargar_configuracion_respaldo(environ)
    assert exc.value.code == codigo


def test_config_live_completa() -> None:
    config = cargar_configuracion_respaldo(
        {
            "AGENTE1_RESPALDO_CARPETA_ID": CARPETA_ID,
            "AGENTE1_RESPALDO_AVISO_DESTINATARIO": "operador@example.com",
            "AGENTE1_RESPALDO_CONFIRMAR_ESCRITURA": "SI",
        }
    )
    assert config is not None and config.modo == "live"
    resumen = config.resumen_seguro()
    assert CARPETA_ID not in json.dumps(resumen)


# ---------------------------------------------------------------------------
# El artefacto
# ---------------------------------------------------------------------------


def test_artefacto_empaqueta_el_estado_declarado(tmp_path: Path) -> None:
    salida = tmp_path / "salida"
    registro_dir = tmp_path / "registro"
    poblar_salida(salida)
    registro = RegistroConfirmacionesArchivo(registro_dir)
    assert registro.crear(clave(1), "asunto", "cuerpo")

    artefacto = construir_artefacto(
        directorio_salida=salida,
        registro_confirmaciones=registro_dir,
        marca=MARCA,
    )

    with tarfile.open(fileobj=io.BytesIO(artefacto.contenido), mode="r:gz") as tar:
        nombres = {miembro.name for miembro in tar.getmembers()}
        assert nombres == {
            NOMBRE_MANIFIESTO,
            "salida/logs/ejecuciones.jsonl",
            "salida/manifests/m.json",
            "salida/insumos-procesados.jsonl",
            "salida/estado-canal-form/atendidos-canal-form.jsonl",
            "salida/estado-decisiones/decisiones-pendientes.jsonl",
            f"salida/cola-envios/{'ab' * 32}.json",
            f"registro-confirmaciones/{clave(1)}.json",
        }
        manifiesto = json.loads(
            tar.extractfile(NOMBRE_MANIFIESTO).read().decode("utf-8")
        )
    assert manifiesto["record"] == MANIFEST_RECORD
    assert manifiesto["creado_en"] == MARCA.isoformat()
    por_ruta = {e["ruta"]: e for e in manifiesto["archivos"]}
    esperado = (salida / "logs" / "ejecuciones.jsonl").read_bytes()
    assert por_ruta["salida/logs/ejecuciones.jsonl"]["sha256"] == hashlib.sha256(
        esperado
    ).hexdigest()
    # Los borradores generados y el lock no son estado: no viajan.
    assert artefacto.archivos == len(nombres) - 1


def test_artefacto_es_determinista_para_el_mismo_estado(tmp_path: Path) -> None:
    salida = tmp_path / "salida"
    registro_dir = tmp_path / "registro"
    poblar_salida(salida)
    RegistroConfirmacionesArchivo(registro_dir)

    primero = construir_artefacto(
        directorio_salida=salida, registro_confirmaciones=registro_dir, marca=MARCA
    )
    segundo = construir_artefacto(
        directorio_salida=salida, registro_confirmaciones=registro_dir, marca=MARCA
    )
    assert primero.sha256 == segundo.sha256


def test_artefacto_exige_marca_con_zona(tmp_path: Path) -> None:
    with pytest.raises(RespaldoDiarioError) as exc:
        construir_artefacto(
            directorio_salida=tmp_path,
            registro_confirmaciones=None,
            marca=datetime(2026, 10, 5, 13, 0),
        )
    assert exc.value.code == "respaldo_marca_invalid"


# ---------------------------------------------------------------------------
# Carpeta fake declarada
# ---------------------------------------------------------------------------


def test_carpeta_fake_crea_lista_y_borra_los_propios(tmp_path: Path) -> None:
    carpeta = CarpetaRespaldoLocal(tmp_path / "fake")
    nombre = nombre_respaldo(FECHA)

    archivo_id = carpeta.subir(nombre=nombre, contenido=b"datos")
    (remoto,) = carpeta.listar()
    assert remoto.nombre == nombre
    assert remoto.archivo_id == archivo_id

    # Crear nunca es sobrescribir: un nombre repetido es anomalía.
    with pytest.raises(RespaldoDiarioError) as exc:
        carpeta.subir(nombre=nombre, contenido=b"otro")
    assert exc.value.code == "respaldo_destino_duplicate"
    assert (tmp_path / "fake" / nombre).read_bytes() == b"datos"

    carpeta.borrar(archivo_id=archivo_id)
    assert carpeta.listar() == ()
    with pytest.raises(RespaldoDiarioError):
        carpeta.borrar(archivo_id=archivo_id)


# ---------------------------------------------------------------------------
# Adapter real de Drive (transporte inyectado, sin red)
# ---------------------------------------------------------------------------


def drive_con(transport: TransporteStub, token: TokenStub) -> GoogleDriveRespaldoDiario:
    return GoogleDriveRespaldoDiario(
        carpeta_id=CARPETA_ID, token_provider=token, transport=transport
    )


def test_drive_subir_es_create_multipart_y_nunca_update(tmp_path: Path) -> None:
    transport = TransporteStub(respuesta(200, {"id": "archivo-nuevo-1"}))
    token = TokenStub()
    drive = drive_con(transport, token)

    nombre = nombre_respaldo(FECHA)
    archivo_id = drive.subir(nombre=nombre, contenido=b"tar-falso")

    assert archivo_id == "archivo-nuevo-1"
    (llamada,) = transport.llamadas
    assert llamada["method"] == "POST"
    assert llamada["host"] == "www.googleapis.com"
    assert llamada["target"].startswith("/upload/drive/v3/files")
    assert "uploadType=multipart" in llamada["target"]
    cuerpo = llamada["body"]
    boundary = b"--a1r" + hashlib.sha256(b"tar-falso").hexdigest()[:48].encode()
    assert cuerpo.count(boundary) == 3  # dos partes y el cierre
    assert b'"name":"' + nombre.encode() + b'"' in cuerpo
    assert f'"parents":["{CARPETA_ID}"]'.encode() in cuerpo
    assert b'"appProperties":{"agente1_respaldo":"v1"}' in cuerpo
    assert b"tar-falso" in cuerpo
    assert llamada["headers"]["Authorization"] == "Bearer token-prueba"
    # La única operación de escritura es create: no existe update en la API.
    assert not hasattr(drive, "actualizar") and not hasattr(drive, "update")


def test_drive_listar_acota_a_carpeta_y_marker(tmp_path: Path) -> None:
    transport = TransporteStub(
        respuesta(
            200,
            {
                "files": [
                    {
                        "id": "f1",
                        "name": "agente1-respaldo-2026-10-01.tar.gz",
                        "appProperties": {"agente1_respaldo": "v1"},
                    }
                ]
            },
        )
    )
    drive = drive_con(transport, TokenStub())

    (remoto,) = drive.listar()
    assert remoto == RespaldoRemoto(
        archivo_id="f1", nombre="agente1-respaldo-2026-10-01.tar.gz"
    )
    (llamada,) = transport.llamadas
    assert llamada["method"] == "GET"
    assert llamada["target"].startswith("/drive/v3/files?")
    assert CARPETA_ID in llamada["target"]
    # La query exige la carpeta, no-borrados y el marker de procedencia.
    assert "appProperties" in llamada["target"]


def test_drive_listar_rechaza_respuesta_sin_marker(tmp_path: Path) -> None:
    transport = TransporteStub(
        respuesta(
            200,
            {
                "files": [
                    {
                        "id": "f1",
                        "name": "agente1-respaldo-2026-10-01.tar.gz",
                        "appProperties": {},
                    }
                ]
            },
        )
    )
    drive = drive_con(transport, TokenStub())
    with pytest.raises(RespaldoDiarioError) as exc:
        drive.listar()
    assert exc.value.code == "drive_response_invalid"


def test_drive_listar_rechaza_nombre_ajeno(tmp_path: Path) -> None:
    # Si el scope se amplía algún día, la procedencia sigue exigida: un
    # archivo sin la convención de nombre invalida el listado.
    transport = TransporteStub(
        respuesta(
            200,
            {
                "files": [
                    {
                        "id": "f1",
                        "name": "documento-de-otra-app.tar.gz",
                        "appProperties": {"agente1_respaldo": "v1"},
                    }
                ]
            },
        )
    )
    drive = drive_con(transport, TokenStub())
    with pytest.raises(RespaldoDiarioError) as exc:
        drive.listar()
    assert exc.value.code == "drive_response_invalid"


def test_drive_borrar_es_delete_por_id(tmp_path: Path) -> None:
    transport = TransporteStub(respuesta(204))
    drive = drive_con(transport, TokenStub())

    drive.borrar(archivo_id="archivo-1")
    (llamada,) = transport.llamadas
    assert llamada["method"] == "DELETE"
    assert llamada["target"].startswith("/drive/v3/files/archivo-1")


def test_drive_borrar_tolera_404(tmp_path: Path) -> None:
    transport = TransporteStub(respuesta(404))
    drive = drive_con(transport, TokenStub())
    drive.borrar(archivo_id="archivo-ya-ausente")  # ya no está: el fin se cumplió


@pytest.mark.parametrize(
    "status, codigo",
    [
        (401, "drive_auth_denied"),
        (403, "drive_auth_denied"),
        (404, "drive_resource_not_found"),
        (429, "drive_rate_limited"),
        (500, "drive_unavailable"),
    ],
)
def test_drive_errores_cerrados(status: int, codigo: str) -> None:
    transport = TransporteStub(respuesta(status, {"error": "x"}))
    drive = drive_con(transport, TokenStub())
    with pytest.raises(RespaldoDiarioError) as exc:
        drive.listar()
    assert exc.value.code == codigo


def test_drive_pide_token_por_operacion() -> None:
    transport = TransporteStub(
        respuesta(200, {"files": []}),
        respuesta(200, {"files": []}),
        respuesta(200, {"id": "nuevo-1"}),
    )
    token = TokenStub()
    drive = drive_con(transport, token)

    drive.listar()
    drive.listar()
    drive.subir(nombre=nombre_respaldo(FECHA), contenido=b"x")

    assert token.llamados == 3


def test_drive_respuesta_mal_formada() -> None:
    transport = TransporteStub(respuesta(200, {"id": 123}))
    drive = drive_con(transport, TokenStub())
    with pytest.raises(RespaldoDiarioError) as exc:
        drive.subir(nombre=nombre_respaldo(FECHA), contenido=b"x")
    assert exc.value.code == "drive_response_invalid"


def test_drive_rechaza_artefacto_sobre_el_tope() -> None:
    drive = drive_con(TransporteStub(), TokenStub())
    with pytest.raises(RespaldoDiarioError) as exc:
        drive.subir(
            nombre=nombre_respaldo(FECHA),
            contenido=b"x" * (MAX_ARTEFACTO_BYTES + 1),
        )
    assert exc.value.code == "respaldo_artefacto_too_large"


# ---------------------------------------------------------------------------
# El paso diario
# ---------------------------------------------------------------------------


def test_paso_diario_sube_un_archivo_nuevo_y_audita(tmp_path: Path) -> None:
    salida = tmp_path / "salida"
    registro_dir = tmp_path / "registro"
    poblar_salida(salida)
    RegistroConfirmacionesArchivo(registro_dir)
    destino = DestinoStub()

    resultado = correr_respaldo_diario(
        directorio_salida=salida,
        destino=destino,
        registro_confirmaciones=registro_dir,
        ahora=MARCA,
    )

    assert resultado.subido
    assert resultado.nombre == "agente1-respaldo-2026-10-05.tar.gz"
    (subida,) = destino.subidas
    assert subida[0] == resultado.nombre
    # El artefacto se abre y el manifiesto verifica.
    with tarfile.open(fileobj=io.BytesIO(subida[1]), mode="r:gz") as tar:
        assert NOMBRE_MANIFIESTO in tar.getnames()
    (linea,) = lineas_auditoria(salida)
    assert linea["evento"] == "respaldo_subido"
    assert linea["nombre"] == resultado.nombre
    assert linea["artefacto_sha256"] == resultado.artefacto_sha256
    # La auditoría lleva el hash del id remoto, no el id.
    assert "stub-id" not in json.dumps(linea)
    assert linea["archivo_id_hash"] == hashlib.sha256(
        f"stub-id-{resultado.nombre}".encode()
    ).hexdigest()


def test_paso_diario_omite_si_ya_existe_el_de_hoy(tmp_path: Path) -> None:
    salida = tmp_path / "salida"
    salida.mkdir(parents=True)
    nombre = nombre_respaldo(FECHA)

    destino = DestinoStub(
        remotos=[RespaldoRemoto(archivo_id="id-previo", nombre=nombre)]
    )

    resultado = correr_respaldo_diario(
        directorio_salida=salida, destino=destino, ahora=MARCA
    )

    assert not resultado.subido and resultado.omitido_existente
    assert destino.subidas == []
    (linea,) = lineas_auditoria(salida)
    assert linea["evento"] == "respaldo_omitido_existente"


def test_paso_diario_borra_solo_los_propios_vencidos(tmp_path: Path) -> None:
    salida = tmp_path / "salida"
    salida.mkdir(parents=True)
    vencido = nombre_respaldo(FECHA - timedelta(days=31))
    al_dia = nombre_respaldo(FECHA - timedelta(days=30))  # no supera aún
    ajeno = "respaldo-de-otro-sistema-2020-01-01.tar.gz"
    destino = DestinoStub(
        remotos=[
            RespaldoRemoto(archivo_id="id-vencido", nombre=vencido),
            RespaldoRemoto(archivo_id="id-al-dia", nombre=al_dia),
            RespaldoRemoto(archivo_id="id-ajeno", nombre=ajeno),
        ]
    )

    resultado = correr_respaldo_diario(
        directorio_salida=salida, destino=destino, ahora=MARCA
    )

    # Sólo el propio y vencido: ni el que está al día ni el ajeno.
    assert destino.borrados == ["id-vencido"]
    assert resultado.eliminados == (vencido,)
    eventos = [linea["evento"] for linea in lineas_auditoria(salida)]
    assert eventos == ["respaldo_subido", "respaldo_eliminado"]
    eliminado = lineas_auditoria(salida)[1]
    assert eliminado["fecha_respaldo"] == (FECHA - timedelta(days=31)).isoformat()
    assert eliminado["nombre"] == vencido
    assert "id-vencido" not in json.dumps(eliminado)


def test_falla_de_subida_audita_avisa_y_propaga(tmp_path: Path) -> None:
    salida = tmp_path / "salida"
    salida.mkdir(parents=True)
    aviso = AvisoStub()
    destino = DestinoStub(error_subir="drive_unavailable")

    with pytest.raises(RespaldoDiarioError) as exc:
        correr_respaldo_diario(
            directorio_salida=salida,
            destino=destino,
            aviso=aviso,
            ahora=MARCA,
        )
    assert exc.value.code == "drive_unavailable"

    eventos = {e["evento"]: e for e in lineas_auditoria(salida)}
    assert eventos["respaldo_fallido"]["error"] == "drive_unavailable"
    assert eventos["respaldo_fallido"]["etapa"] == "subida"
    assert eventos["aviso_operador"]["resultado"] == "enviado"
    # El aviso fue con el código, sin contenido ni credenciales.
    (asunto, cuerpo) = aviso.llamados[0]
    assert "drive_unavailable" in cuerpo
    assert "token" not in cuerpo


def test_falla_de_aviso_no_tapa_la_falla_original(tmp_path: Path) -> None:
    salida = tmp_path / "salida"
    salida.mkdir(parents=True)
    aviso = AvisoStub(fallar=True)

    with pytest.raises(RespaldoDiarioError) as exc:
        correr_respaldo_diario(
            directorio_salida=salida,
            destino=DestinoStub(error_subir="drive_rate_limited"),
            aviso=aviso,
            ahora=MARCA,
        )
    assert exc.value.code == "drive_rate_limited"
    eventos = {e["evento"]: e for e in lineas_auditoria(salida)}
    assert eventos["aviso_operador"]["resultado"] == "fallido"


def test_sin_destino_de_aviso_queda_asentado(tmp_path: Path) -> None:
    salida = tmp_path / "salida"
    salida.mkdir(parents=True)
    with pytest.raises(RespaldoDiarioError):
        correr_respaldo_diario(
            directorio_salida=salida,
            destino=DestinoStub(error_subir="drive_unavailable"),
            ahora=MARCA,
        )
    eventos = {e["evento"]: e for e in lineas_auditoria(salida)}
    assert eventos["aviso_operador"]["resultado"] == "sin_destino"


def test_borrado_parcial_audita_cada_caso_y_falla_el_paso(tmp_path: Path) -> None:
    salida = tmp_path / "salida"
    salida.mkdir(parents=True)
    v1 = nombre_respaldo(FECHA - timedelta(days=31))
    v2 = nombre_respaldo(FECHA - timedelta(days=32))
    destino = DestinoStub(
        remotos=[
            RespaldoRemoto(archivo_id="id-a", nombre=v1),
            RespaldoRemoto(archivo_id="id-b", nombre=v2),
        ],
        errores_borrar=frozenset({"id-a"}),
    )

    with pytest.raises(RespaldoDiarioError) as exc:
        correr_respaldo_diario(
            directorio_salida=salida, destino=destino, ahora=MARCA
        )
    assert exc.value.code == "respaldo_borrado_error"
    # El que sí se pudo borrar quedó borrado y auditado; el otro tiene su
    # línea de falla. El reintento del próximo tick es seguro.
    assert destino.borrados == ["id-b"]
    eventos = [e["evento"] for e in lineas_auditoria(salida)]
    assert "respaldo_eliminado" in eventos
    assert "respaldo_eliminar_fallido" in eventos


def test_aviso_offline_queda_registrado_en_jsonl(tmp_path: Path) -> None:
    ruta = tmp_path / "avisos" / "avisos.jsonl"
    aviso = AvisoOperadorJsonl(ruta)
    assert aviso.avisar(asunto="a", cuerpo="c") == "registrado_offline"
    (linea,) = [
        json.loads(t) for t in ruta.read_text(encoding="utf-8").splitlines()
    ]
    assert linea["record"] == "agente1_aviso_operador_v1"
    assert linea["modo"] == "offline_fake"
    assert linea["asunto"] == "a"


# ---------------------------------------------------------------------------
# Restauración
# ---------------------------------------------------------------------------


def armar_artefacto(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Un artefacto real sobre un estado poblado, guardado en disco."""

    salida = tmp_path / "origen-salida"
    registro_dir = tmp_path / "origen-registro"
    poblar_salida(salida)
    RegistroConfirmacionesArchivo(registro_dir)
    artefacto = construir_artefacto(
        directorio_salida=salida,
        registro_confirmaciones=registro_dir,
        marca=MARCA,
    )
    ruta = tmp_path / nombre_respaldo(FECHA)
    ruta.write_bytes(artefacto.contenido)
    return ruta, salida, registro_dir


def test_restaurar_repone_sin_sobreescribir(tmp_path: Path) -> None:
    artefacto, salida_origen, _ = armar_artefacto(tmp_path)
    destino_salida = tmp_path / "destino" / "salida"
    destino_registro = tmp_path / "destino" / "registro"
    # Un archivo ya presente, distinto del del respaldo: es conflicto,
    # nunca una sobreescritura silenciosa.
    ruta_conflicto = destino_salida / "logs" / "ejecuciones.jsonl"
    ruta_conflicto.parent.mkdir(parents=True)
    ruta_conflicto.write_text("otro contenido\n", encoding="utf-8")

    resultado = restaurar_estado_respaldo(
        artefacto_path=artefacto,
        directorio_salida=destino_salida,
        registro_confirmaciones=destino_registro,
    )

    assert resultado.marca == MARCA.isoformat()
    assert resultado.conflictos == ("salida/logs/ejecuciones.jsonl",)
    assert ruta_conflicto.read_text(encoding="utf-8") == "otro contenido\n"
    # El resto del estado quedó repuesto.
    assert (
        destino_salida / "insumos-procesados.jsonl"
    ).read_bytes() == (salida_origen / "insumos-procesados.jsonl").read_bytes()
    assert resultado.archivos_restaurados == 5  # todos menos el conflicto
    # Los permisos son los del estado del agente.
    assert oct(
        (destino_salida / "insumos-procesados.jsonl").stat().st_mode & 0o777
    ) == "0o600"


def test_restaurar_rechaza_artefacto_corrupto(tmp_path: Path) -> None:
    artefacto, _, _ = armar_artefacto(tmp_path)
    contenido = artefacto.read_bytes()
    # Altera el tar sin tocar el manifiesto: los hashes no cierran.
    corrupto = tmp_path / "corrupto.tar.gz"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        with tarfile.open(fileobj=io.BytesIO(contenido), mode="r:gz") as origen:
            for miembro in origen.getmembers():
                datos = origen.extractfile(miembro).read()
                if miembro.name == NOMBRE_MANIFIESTO:
                    datos = datos.replace(b'"bytes"', b'"bytesX"', 1)
                info = tarfile.TarInfo(miembro.name)
                info.size = len(datos)
                tar.addfile(info, io.BytesIO(datos))
    corrupto.write_bytes(buffer.getvalue())

    with pytest.raises(RespaldoDiarioError) as exc:
        restaurar_estado_respaldo(
            artefacto_path=corrupto,
            directorio_salida=tmp_path / "destino",
            registro_confirmaciones=tmp_path / "registro",
        )
    assert exc.value.code == "respaldo_artefacto_invalid"
    assert not (tmp_path / "destino").exists()


def test_restaurar_sin_registro_exigido_por_el_artefacto(tmp_path: Path) -> None:
    salida_origen = tmp_path / "salida"
    registro_dir = tmp_path / "registro"
    RegistroConfirmacionesArchivo(registro_dir).crear(clave(9), "a", "b")
    artefacto = construir_artefacto(
        directorio_salida=salida_origen,
        registro_confirmaciones=registro_dir,
        marca=MARCA,
    )
    ruta = tmp_path / "a.tar.gz"
    ruta.write_bytes(artefacto.contenido)

    with pytest.raises(RespaldoDiarioError) as exc:
        restaurar_estado_respaldo(
            artefacto_path=ruta,
            directorio_salida=tmp_path / "destino",
            registro_confirmaciones=None,
        )
    assert exc.value.code == "respaldo_registro_destino_ausente"


def test_restaurar_marca_indeterminadas_las_aprobaciones_posteriores(
    tmp_path: Path,
) -> None:
    """La prueba del issue: reservas y aprobaciones posteriores a la marca.

    Escenario: el respaldo corre en T y después el mundo siguió hasta la
    pérdida del host. El operador restaura el artefacto sobre un directorio
    donde conviven el estado del respaldo y archivos escritos después
    (por ejemplo, por un intento de recuperación): lo que el snapshot no
    pudo afirmar queda `ENVIO_INDETERMINADO`, sin reenvío, hasta que una
    persona lo cruce contra Gmail Enviados.
    """

    salida_origen = tmp_path / "origen-salida"
    registro_origen = tmp_path / "origen-registro"
    poblar_salida(salida_origen)
    antes = MARCA - timedelta(hours=2)
    despues = MARCA + timedelta(hours=2)

    registro = RegistroConfirmacionesArchivo(registro_origen, clock=lambda: antes)
    # Anteriores a la marca: se respetan.
    crear_en_estado(registro, clave(1), "APROBADA")
    crear_en_estado(registro, clave(2), "ENVIO_ENCOLADO")
    crear_en_estado(registro, clave(3), "ENVIADA_SIMULADA")
    crear_en_estado(registro, clave(4), "PENDIENTE_VALIDACION")
    artefacto = construir_artefacto(
        directorio_salida=salida_origen,
        registro_confirmaciones=registro_origen,
        marca=MARCA,
    )
    ruta = tmp_path / nombre_respaldo(FECHA)
    ruta.write_bytes(artefacto.contenido)

    # En el directorio a restaurar viven además entradas posteriores a la
    # marca: el mundo siguió después del respaldo.
    destino_registro = tmp_path / "destino-registro"
    posterior = RegistroConfirmacionesArchivo(
        destino_registro, clock=lambda: despues
    )
    crear_en_estado(posterior, clave(5), "APROBADA")
    crear_en_estado(posterior, clave(6), "APROBADA_SEMANTICA")
    crear_en_estado(posterior, clave(7), "ENVIO_ENCOLADO")
    crear_en_estado(posterior, clave(8), "ENVIO_RESERVADO")
    crear_en_estado(posterior, clave(9), "EMISION_RESERVADA")
    crear_en_estado(posterior, clave(10), "PENDIENTE_VALIDACION")
    # Y una entrada posterior pero terminal: el registro dice ENVIADA,
    # no es reserva ni aprobación, así que la marca no la toca — es una
    # evidencia para el cruce humano, no una orden de envío.
    crear_en_estado(posterior, clave(11), "ENVIADA_SIMULADA")

    resultado = restaurar_estado_respaldo(
        artefacto_path=ruta,
        directorio_salida=tmp_path / "destino-salida",
        registro_confirmaciones=destino_registro,
    )

    indeterminados = set(resultado.indeterminados)
    assert indeterminados == {clave(5), clave(6), clave(7), clave(8), clave(9)}

    registro_final = RegistroConfirmacionesArchivo(destino_registro)
    estados = {
        num: registro_final.obtener(clave(num)).estado for num in range(1, 12)
    }
    # Reservas: cada una hacia el indeterminado de su pipeline.
    assert estados[8] == "ENVIO_INDETERMINADO"
    assert estados[9] == "EMISION_INDETERMINADA"
    # Aprobaciones posteriores a la marca.
    assert estados[5] == "ENVIO_INDETERMINADO"
    assert estados[6] == "ENVIO_INDETERMINADO"
    assert estados[7] == "ENVIO_INDETERMINADO"
    # Lo que no es reserva ni aprobación posterior: intacto.
    assert estados[1] == "APROBADA"
    assert estados[2] == "ENVIO_ENCOLADO"
    assert estados[3] == "ENVIADA_SIMULADA"
    assert estados[4] == "PENDIENTE_VALIDACION"
    assert estados[10] == "PENDIENTE_VALIDACION"
    assert estados[11] == "ENVIADA_SIMULADA"

    # Lo indeterminado no se reenvía: ningún pipeline toma como entrada
    # `ENVIO_INDETERMINADO` — no queda ninguna reserva que reconciliar y
    # ninguna posterior en estado entregable.
    assert registro_final.listar_por_estado("ENVIO_RESERVADO") == ()
    assert registro_final.listar_por_estado("EMISION_RESERVADA") == ()
    encoladas = registro_final.listar_por_estado("ENVIO_ENCOLADO")
    assert clave(2) in encoladas  # pre-marca: sigue su ciclo normal
    assert not {clave(5), clave(7)} & set(encoladas)

    # La restauración quedó en la auditoría con hashes, sin contenido.
    (linea,) = [
        e for e in lineas_auditoria(tmp_path / "destino-salida")
        if e["evento"] == "restauracion_respaldo"
    ]
    assert linea["indeterminados"] == 5
    assert "asunto" not in json.dumps(linea)
    assert "cuerpo" not in json.dumps(linea)


def test_restaurar_idempotente_sobre_estado_igual(tmp_path: Path) -> None:
    artefacto, _, _ = armar_artefacto(tmp_path)
    destino_salida = tmp_path / "destino" / "salida"
    destino_registro = tmp_path / "destino" / "registro"

    restaurar_estado_respaldo(
        artefacto_path=artefacto,
        directorio_salida=destino_salida,
        registro_confirmaciones=destino_registro,
    )
    segundo = restaurar_estado_respaldo(
        artefacto_path=artefacto,
        directorio_salida=destino_salida,
        registro_confirmaciones=destino_registro,
    )
    assert segundo.archivos_restaurados == 0
    assert segundo.archivos_omitidos > 0
    assert segundo.conflictos == ()
