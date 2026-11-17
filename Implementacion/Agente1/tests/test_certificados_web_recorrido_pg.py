"""Pedido HTTP → aprobación → worker durable → ZIP, con el rol SQL real."""
from __future__ import annotations

import io
import os
import uuid
import zipfile
from datetime import date, timedelta
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from agente1.canal_form import PadronRoles
from agente1.confirmaciones import ROL_APROBADOR_CONTENIDO
from agente1.decisiones_form import RegistroDecisiones
from agente1.web.app import ConfiguracionWeb, crear_app
from agente1.web.certificados_web import RepositorioLotes
from agente1.web.emision_certificados_runtime import construir_emision_certificados_web
from agente1.web.identidad import VerificadorFake
from agente1.web.persistencia import RepositorioWeb
from agente1.web.sesiones import SesionesMemoria

DSN = os.environ.get("AGENTE1_POSTGRES_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="requiere PostgreSQL de pruebas")
CORREO = "aprobador@example.invalid"
CSV = (
    "nombre;apellido;dni;mail;tratamiento;condicion\n"
    "Persona;Ficticia;90000001;persona@example.invalid;Sr.;aprobacion\n"
    "Otra;Ficticia;90000002;otra@example.invalid;Sra.;asistencia\n"
).encode()
ACTIVIDAD = {
    "id_actividad": "DEMO-CERT-001",
    "titulo": "Actividad ficticia para demostración",
    "duracion_horas": "2",
    "modalidad": "virtual",
    "fecha_inicio": "2026-11-18",
    "fecha_fin": "2026-11-19",
    "organiza": "Organizador ficticio",
}


@pytest.fixture()
def conexion():
    esquema = "test_recorrido_cert_" + uuid.uuid4().hex[:10]
    with psycopg.connect(DSN, autocommit=True) as admin:
        admin.execute(f'CREATE SCHEMA "{esquema}"')
        try:
            admin.execute(f'SET search_path TO "{esquema}"')
            migraciones = Path(__file__).resolve().parent.parent / "migrations"
            for sql in sorted(migraciones.glob("*.up.sql")):
                admin.execute(sql.read_text())
            admin.execute(f'GRANT USAGE ON SCHEMA "{esquema}" TO agente1_app, agente1_mantenimiento')

            def abrir():
                conn = psycopg.connect(DSN, options=f"-c search_path={esquema}")
                conn.execute("SET ROLE agente1_app")
                conn.commit()
                return conn

            yield abrir
        finally:
            admin.execute(f'DROP SCHEMA "{esquema}" CASCADE')


def test_recorrido_demo_completo_sin_registro_institucional(conexion, tmp_path):
    padron = tmp_path / "padron.csv"
    padron.write_text(f"correo,rol\n{CORREO},{ROL_APROBADOR_CONTENIDO}\n")
    decisiones = tmp_path / "decisiones"
    entorno = {
        "AGENTE1_PADRON_ROLES_CSV": str(padron),
        "AGENTE1_DECISIONES_DIR": str(decisiones),
        "AGENTE1_SALIDA_DIR": str(tmp_path / "salida"),
        "AGENTE1_WEB_MODO_DEMO": "si",
        "AGENTE1_WEB_DEMO_HASTA": (date.today() + timedelta(days=1)).isoformat(),
    }
    servicio = construir_emision_certificados_web(entorno, conexion_factory=conexion)
    lotes = RepositorioLotes(conexion)
    sesiones = SesionesMemoria()
    registro = RegistroDecisiones(decisiones)
    app = crear_app(
        config=ConfiguracionWeb(
            google_client_id="", modo_demo=True, cookie_secure=True,
            demo_hasta=date.today() + timedelta(days=1), demo_correos=(CORREO,),
        ),
        verificador=VerificadorFake({}), padron=PadronRoles({CORREO: ROL_APROBADOR_CONTENIDO}),
        repositorio=RepositorioWeb(conexion), lotes=lotes, sesiones=sesiones,
        actividades=[ACTIVIDAD], registro_decisiones=registro, emision_certificados=servicio,
    )
    with TestClient(app, base_url="https://testserver") as client:
        pagina = client.get("/ingresar")
        csrf = pagina.text.split('name="csrf" value="', 1)[1].split('"', 1)[0]
        assert client.post("/ingresar", data={"correo": CORREO, "csrf": csrf}, follow_redirects=False).status_code == 303
        csrf = next(iter(sesiones._sesiones.values())).csrf_token
        datos = {"csrf": csrf, "actividad": ACTIVIDAD["id_actividad"], "linea_descriptiva": "Introducción a herramientas para el análisis documental."}
        respuesta = client.post("/certificados/pedir", data=datos, files={"lista": ("cierre.csv", CSV, "text/csv")}, follow_redirects=False)
        assert respuesta.status_code == 303
        ruta = respuesta.headers["location"]
        lote = lotes.obtener(ruta.rsplit("/", 1)[1])
        assert lote.origen_creacion == "demo"
        assert lote.actividad["fecha_fin"] == ACTIVIDAD["fecha_fin"]
        assert client.post("/certificados/pedir", data=datos, files={"lista": ("cierre.csv", CSV, "text/csv")}, follow_redirects=False).headers["location"] == ruta
        assert client.post("/certificados/pedir", data={**datos, "linea_descriptiva": "Herramientas introductorias para organizar documentos."}, files={"lista": ("cierre.csv", CSV, "text/csv")}).status_code == 409
        assert client.get(ruta + "/emision/descargar").status_code != 200
        assert client.post(ruta + "/decidir", data={"csrf": csrf, "hash_lote": lote.objeto_lote, "accion": "aprobar", "confirmar": "si"}).status_code == 200
        assert registro.procesadas() == ()
        assert lotes.obtener(lote.id_lote).estado == "APROBADA"
        assert servicio.correr_una_vez(worker_id="antes-del-pedido") is None
        for _ in range(2):
            assert client.post(ruta + "/emision", data={"csrf": csrf, "hash_lote": lote.objeto_lote}).status_code in (200, 303)
        assert servicio.correr_una_vez(worker_id="demo-real-pg") is not None
        assert servicio.correr_una_vez(worker_id="segundo-worker") is None
        pagina = client.get(ruta + "/emision")
        assert "demostración" in pagina.text
        descarga = client.get(ruta + "/emision/descargar")
        assert descarga.status_code == 200
        with zipfile.ZipFile(io.BytesIO(descarga.content)) as archivo:
            assert len(archivo.namelist()) == 2
            assert all(nombre.startswith("certificado-") and nombre.endswith(".pdf") for nombre in archivo.namelist())
            assert all(archivo.read(nombre).startswith(b"%PDF") for nombre in archivo.namelist())
        assert registro.procesadas() == ()
        with conexion() as conn:
            fila = conn.execute("SELECT estado, total, enviadas FROM emisiones_certificados WHERE id_lote=%s", (lote.id_lote,)).fetchone()
        assert fila == ("GENERADA_DEMO", 2, 0)

@pytest.mark.parametrize("timeout", [False, True])
def test_motor_y_adapter_gmail_con_transporte_simulado(conexion, tmp_path, timeout):
    """Motor y MIME reales; transporte local. Ningún correo sale de la prueba."""
    import base64
    import json
    from email import policy
    from email.parser import BytesParser

    from agente1.canal_form import hash_correo
    from agente1.emisiones_certificados import RepositorioEmisiones
    from agente1.gmail_envio import GmailDestinoConfirmaciones
    from agente1.google_workspace import RespuestaHttp
    from agente1.web.certificados_web import registrar_aprobacion_en_registro
    from agente1.web.emision_certificados import (
        ActorCertificadosWeb,
        EmisionCertificadosWeb,
    )
    from agente1.web.pedido_certificados import parsear_csv_lista_cierre

    solicitudes = []

    class TokenPrueba:
        def obtener_access_token(self):
            return "token-sintetico-sin-validez"

    class TransporteLocal:
        def request(self, **kwargs):
            solicitudes.append(kwargs)
            if timeout:
                raise TimeoutError("resultado de entrega desconocido")
            return RespuestaHttp(status=200, body=b'{"id":"simulado-1"}')

    personas = parsear_csv_lista_cierre(CSV.replace(b";aprobacion", b";asistencia"))
    repo = RepositorioLotes(conexion)
    lote = repo.crear(
        id_actividad=ACTIVIDAD["id_actividad"], actividad=ACTIVIDAD, personas=personas,
        linea_descriptiva="Introducción a herramientas para el análisis documental.",
        generada_por_hash=hash_correo(CORREO), origen_creacion="google",
    )
    repo.decidir(
        id_lote=lote.id_lote, hash_lote=lote.objeto_lote, accion="aprobar",
        validador_hash=hash_correo(CORREO), rol=ROL_APROBADOR_CONTENIDO,
        origen_identidad="google", version_agente="0.0.0-test",
    )
    lote = repo.obtener(lote.id_lote)
    registro = RegistroDecisiones(tmp_path / "decisiones")
    registrar_aprobacion_en_registro(registro, lote=lote, validador_hash=hash_correo(CORREO), rol=ROL_APROBADOR_CONTENIDO)
    destino = GmailDestinoConfirmaciones(
        destinatarios_permitidos=[p.mail for p in personas], token_provider=TokenPrueba(),
        transport=TransporteLocal(), modo="prueba",
    )
    cola = RepositorioEmisiones(conexion)
    servicio = EmisionCertificadosWeb(
        lotes=repo, emisiones=cola, registro_decisiones=registro,
        padron=PadronRoles({CORREO: ROL_APROBADOR_CONTENIDO}),
        directorio_salida=tmp_path / "salida", fabrica_destino=lambda: destino,
        modo_envio="prueba",
    )
    actor = ActorCertificadosWeb(hash_correo(CORREO), ROL_APROBADOR_CONTENIDO, "google", False)
    assert servicio.solicitar(lote.id_lote, hash_lote=lote.objeto_lote, actor=actor).estado == "EN_COLA"
    assert servicio.correr_una_vez(worker_id="motor-real-transporte-local") is not None
    estado = servicio.consultar(lote.id_lote, actor=actor)
    assert estado.estado == ("EMISION_INDETERMINADA" if timeout else "EMITIDA")
    assert len(solicitudes) == (1 if timeout else 2)
    servicio.solicitar(lote.id_lote, hash_lote=lote.objeto_lote, actor=actor)
    assert servicio.correr_una_vez(worker_id="no-reenviar") is None
    assert len(solicitudes) == (1 if timeout else 2)
    if not timeout:
        for solicitud in solicitudes:
            cuerpo = json.loads(solicitud["body"])
            mime = BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(cuerpo["raw"]))
            adjuntos = list(mime.iter_attachments())
            assert len(adjuntos) == 1
            assert adjuntos[0].get_payload(decode=True).startswith(b"%PDF")
