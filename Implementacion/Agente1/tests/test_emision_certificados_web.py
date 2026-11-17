"""El servicio web de la emisión durable, contra la cola real (#168).

La interfaz que la UI consume es la de `EmisionCertificadosWeb`: estos
tests la ejercen con `RepositorioEmisiones` y `RepositorioLotes` sobre
PostgreSQL real (con `SET ROLE`, sin claves nuevas), motor y destino
falsos — ningún correo sale.
"""

from __future__ import annotations

import io
import os
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest

from agente1.canal_form import PadronRoles, hash_correo
from agente1.certificados_emision import (
    PersonaCierre,
    ResultadoEmisionCertificados,
)
from agente1.confirmaciones import ROL_APROBADOR_CONTENIDO
from agente1.decisiones_form import (
    DECISION_APRUEBO_CONTENIDO,
    RESULTADO_REGISTRADA,
    TIPO_LINEA_DESCRIPTIVA,
    RegistroDecisiones,
    ResultadoDecision,
)
from agente1.emisiones_certificados import (
    ESTADO_INDETERMINADA,
    RepositorioEmisiones,
)
from agente1.linea_descriptiva import objeto_id_linea_descriptiva
from agente1.web.certificados_web import (
    RepositorioLotes,
)
from agente1.web.emision_certificados import (
    ESTADO_BLOQUEADA,
    ESTADO_EMITIDA_WEB,
    ESTADO_EMITIENDO,
    ESTADO_EN_COLA,
    ESTADO_GENERADA_DEMO_WEB,
    ESTADO_INDETERMINADA_WEB,
    ESTADO_SIN_PEDIDO,
    ActorCertificadosWeb,
    EmisionCertificadosWeb,
    ErrorEmisionWeb,
    EstadoEmisionWeb,
)

MIGRACIONES = Path(__file__).resolve().parent.parent / "migrations"
DSN = os.environ.get("AGENTE1_POSTGRES_DSN")
AHORA = datetime(2026, 11, 17, 9, 0, tzinfo=timezone.utc)
CORREO = "aprobador@example.invalid"
LINEA = "Línea descriptiva del lote web."
ACTIVIDAD = {
    "titulo": "Curso del canal web",
    "duracion_horas": "8",
    "modalidad": "online",
    "fecha_inicio": "2026-11-01",
    "fecha_fin": "2026-11-02",
    "organiza": "Facultad de Ingeniería del Ejército",
}


def _personas() -> tuple[PersonaCierre, ...]:
    return (
        PersonaCierre(
            nombre="Ana",
            apellido="Prueba",
            dni="90000011",
            mail="ana.prueba@example.invalid",
            tratamiento="Sra.",
            condicion="asistencia",
        ),
    )


@pytest.fixture()
def base_pg():
    if not DSN:
        pytest.skip("sin AGENTE1_POSTGRES_DSN (servicio de CI o base local)")
    esquema = f"test_webemision_{uuid.uuid4().hex[:10]}"
    admin = psycopg.connect(DSN, autocommit=True)
    admin.execute(f'CREATE SCHEMA "{esquema}"')
    try:
        with psycopg.connect(DSN, autocommit=True) as conn:
            conn.execute(f'SET search_path TO "{esquema}"')
            for up in sorted(MIGRACIONES.glob("*.up.sql")):
                conn.execute(up.read_text(encoding="utf-8"))
            conn.execute(
                f'GRANT USAGE ON SCHEMA "{esquema}"'
                " TO agente1_app, agente1_mantenimiento"
            )
        yield esquema
    finally:
        admin.execute(f'DROP SCHEMA "{esquema}" CASCADE')
        admin.close()


def _fabrica(esquema: str, rol: str = "agente1_app"):
    def abrir():
        conn = psycopg.connect(
            DSN, options=f"-c search_path={esquema}", autocommit=False
        )
        conn.execute(f"SET ROLE {rol}")
        conn.commit()
        return conn

    return abrir


def _actor(*, correo: str = CORREO, demo: bool = False) -> ActorCertificadosWeb:
    return ActorCertificadosWeb(
        solicitante_hash=hash_correo(correo),
        rol=ROL_APROBADOR_CONTENIDO,
        origen_identidad="demo" if demo else "google",
        modo_demo=demo,
    )


def _lote(lotes: RepositorioLotes, *, origen: str, id_actividad="FIE-WEB-01"):
    lote = lotes.crear(
        id_actividad=id_actividad,
        actividad=dict(ACTIVIDAD),
        personas=_personas(),
        linea_descriptiva=LINEA,
        generada_por_hash=hash_correo(CORREO),
        origen_creacion=origen,
        ahora=AHORA,
    )
    lotes.decidir(
        id_lote=lote.id_lote,
        hash_lote=lote.objeto_lote,
        accion="aprobar",
        validador_hash=hash_correo(CORREO),
        rol=ROL_APROBADOR_CONTENIDO,
        origen_identidad=origen,
        version_agente="0.9.0",
        ahora=AHORA,
    )
    return lotes.obtener(lote.id_lote)


def _registro_con_linea(tmp_path: Path, lote) -> RegistroDecisiones:
    registro = RegistroDecisiones(tmp_path / "decisiones")
    registro.registrar(
        ResultadoDecision(
            id_respuesta="b" * 64,
            correo_hash=hash_correo(CORREO),
            rol=ROL_APROBADOR_CONTENIDO,
            rol_origen="padron",
            tipo=TIPO_LINEA_DESCRIPTIVA,
            objeto_id=objeto_id_linea_descriptiva(
                lote.id_actividad, lote.linea_descriptiva
            ),
            decision=DECISION_APRUEBO_CONTENIDO,
            resultado=RESULTADO_REGISTRADA,
            rechazo_codigo=None,
            marca_temporal_form=AHORA.isoformat(),
            timestamp=AHORA.isoformat(),
        )
    )
    return registro


def _servicio(
    esquema: str,
    *,
    modo_demo: bool = False,
    padron=None,
    registro_decisiones=None,
    motor=None,
    fabrica_destino=None,
    modo_envio: str = "prueba",
) -> EmisionCertificadosWeb:
    return EmisionCertificadosWeb(
        lotes=RepositorioLotes(_fabrica(esquema)),
        emisiones=RepositorioEmisiones(_fabrica(esquema)),
        padron=padron
        if padron is not None
        else PadronRoles({CORREO: ROL_APROBADOR_CONTENIDO}),
        registro_decisiones=registro_decisiones,
        directorio_salida=Path("/tmp/emisiones-test"),
        fabrica_destino=fabrica_destino,
        modo_demo=modo_demo,
        modo_envio=modo_envio,
        motor=motor or _motor_ok,
    )


def _motor_ok(**kwargs) -> ResultadoEmisionCertificados:
    return ResultadoEmisionCertificados(
        estado="EMITIDA",
        correlation_id="cid",
        log_path="/tmp/no",
        resumen="ok",
        emitidas=len(kwargs["lector_lista"].leer_valores()),
    )


class DestinoMemoria:
    modo = "prueba"

    def __init__(self) -> None:
        self.entregas: list[dict] = []

    def entregar(self, **kwargs) -> None:
        self.entregas.append(kwargs)


# --- el estado visible ------------------------------------------------------


def test_lote_aprobado_sin_pedido_esta_disponible(base_pg: str) -> None:
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="demo")
    servicio = _servicio(base_pg, modo_demo=True)
    estado = servicio.consultar(lote.id_lote, actor=_actor(demo=True))
    assert isinstance(estado, EstadoEmisionWeb)
    assert estado.estado == ESTADO_SIN_PEDIDO
    assert estado.disponible is True
    assert estado.es_demo is True
    assert estado.descargable is False


def test_consultar_rechaza_lote_inexistente(base_pg: str) -> None:
    servicio = _servicio(base_pg)
    with pytest.raises(ErrorEmisionWeb) as error:
        servicio.consultar("lote-nada", actor=_actor())
    assert error.value.code == "inexistente"


def test_consultar_rechaza_rol_ajeno(base_pg: str) -> None:
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="google")
    servicio = _servicio(
        base_pg, padron=PadronRoles({CORREO: "LECTOR"})
    )
    with pytest.raises(ErrorEmisionWeb) as error:
        servicio.consultar(lote.id_lote, actor=_actor())
    assert error.value.code == "rol_no_autorizado"


# --- pedir la emisión ---------------------------------------------------------


def test_solicitar_demo_encola_sin_generar_ni_enviar(base_pg: str) -> None:
    """El POST sólo deja la fila PENDIENTE: el ZIP lo compone el worker."""
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="demo")
    servicio = _servicio(base_pg, modo_demo=True)
    estado = servicio.solicitar(
        lote.id_lote, hash_lote=lote.objeto_lote, actor=_actor(demo=True)
    )
    assert estado.estado == ESTADO_EN_COLA
    emision = RepositorioEmisiones(_fabrica(base_pg)).obtener_por_lote(
        lote.id_lote
    )
    assert emision is not None
    assert emision.estado == "PENDIENTE"
    assert emision.modo == "demo"


def test_doble_post_devuelve_el_trabajo_existente(base_pg: str) -> None:
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="demo")
    servicio = _servicio(base_pg, modo_demo=True)
    primero = servicio.solicitar(
        lote.id_lote, hash_lote=lote.objeto_lote, actor=_actor(demo=True)
    )
    segundo = servicio.solicitar(
        lote.id_lote, hash_lote=lote.objeto_lote, actor=_actor(demo=True)
    )
    assert primero.estado == segundo.estado == ESTADO_EN_COLA
    assert len(RepositorioEmisiones(_fabrica(base_pg)).listar()) == 1


def test_solicitar_rechaza_hash_obsoleto(base_pg: str) -> None:
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="google")
    servicio = _servicio(base_pg)
    with pytest.raises(ErrorEmisionWeb) as error:
        servicio.solicitar(
            lote.id_lote, hash_lote="0" * 64, actor=_actor()
        )
    assert error.value.code == "lote_obsoleto"


def test_solicitar_rechaza_quien_no_genero(base_pg: str) -> None:
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="google")
    servicio = _servicio(
        base_pg,
        padron=PadronRoles(
            {
                CORREO: ROL_APROBADOR_CONTENIDO,
                "otro@example.invalid": ROL_APROBADOR_CONTENIDO,
            }
        ),
    )
    with pytest.raises(ErrorEmisionWeb) as error:
        servicio.solicitar(
            lote.id_lote,
            hash_lote=lote.objeto_lote,
            actor=_actor(correo="otro@example.invalid"),
        )
    assert error.value.code == "aprobador_no_es_generador"


def test_solicitar_real_en_contexto_demo_no_encola(base_pg: str) -> None:
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="google")
    servicio = _servicio(base_pg, modo_demo=True)
    with pytest.raises(ErrorEmisionWeb) as error:
        servicio.solicitar(
            lote.id_lote, hash_lote=lote.objeto_lote, actor=_actor()
        )
    assert error.value.code == "demo_no_emite_real"


def test_solicitar_demo_fuera_de_modo_no_encola(base_pg: str) -> None:
    """El lote demo es demo para siempre: sin modo demo se bloquea."""
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="demo")
    servicio = _servicio(base_pg, modo_demo=False)
    with pytest.raises(ErrorEmisionWeb) as error:
        servicio.solicitar(
            lote.id_lote, hash_lote=lote.objeto_lote, actor=_actor()
        )
    assert error.value.code == "demo_fuera_de_modo"


def test_solicitar_real_bloqueada_devuelve_bloqueos_sin_encolar(
    base_pg: str,
) -> None:
    """Con insumos faltantes el POST no encola: vuelve BLOQUEADA."""
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="google")
    servicio = _servicio(base_pg, registro_decisiones=None, padron=None)
    estado = servicio.solicitar(
        lote.id_lote, hash_lote=lote.objeto_lote, actor=_actor()
    )
    assert estado.estado == ESTADO_BLOQUEADA
    assert "config_incompleta" in estado.bloqueos
    assert (
        RepositorioEmisiones(_fabrica(base_pg)).obtener_por_lote(
            lote.id_lote
        )
        is None
    )


def test_lote_real_con_linea_aprobada_no_tiene_bloqueos_de_linea(
    base_pg: str, tmp_path: Path
) -> None:
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="google")
    registro = _registro_con_linea(tmp_path, lote)
    servicio = _servicio(base_pg, registro_decisiones=registro)
    estado = servicio.consultar(lote.id_lote, actor=_actor())
    assert "linea_descriptiva_no_aprobada" not in estado.bloqueos
    assert "config_incompleta" not in estado.bloqueos


def test_solicitar_real_encola_en_modo_prueba(
    base_pg: str, tmp_path: Path
) -> None:
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="google")
    registro = _registro_con_linea(tmp_path, lote)
    servicio = _servicio(base_pg, registro_decisiones=registro)
    estado = servicio.solicitar(
        lote.id_lote, hash_lote=lote.objeto_lote, actor=_actor()
    )
    assert estado.estado == ESTADO_EN_COLA
    assert estado.es_demo is False


# --- worker y descarga --------------------------------------------------------


def test_el_ciclo_completo_demo_genera_y_descarga_sin_mutar(
    base_pg: str, tmp_path: Path
) -> None:
    """PENDIENTE → worker → GENERADA_DEMO → descargar devuelve el ZIP y
    no toca la fila."""
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="demo")
    servicio = _servicio(base_pg, modo_demo=True)
    servicio.solicitar(
        lote.id_lote, hash_lote=lote.objeto_lote, actor=_actor(demo=True)
    )
    id_emision = servicio.correr_una_vez(worker_id="w-demo")
    assert id_emision is not None
    estado = servicio.consultar(lote.id_lote, actor=_actor(demo=True))
    assert estado.estado == ESTADO_GENERADA_DEMO_WEB
    assert estado.descargable is True
    assert estado.generadas == 1
    antes = RepositorioEmisiones(_fabrica(base_pg)).obtener_por_lote(
        lote.id_lote
    )
    contenido = servicio.descargar(lote.id_lote, actor=_actor(demo=True))
    assert contenido[:4] == b"PK\x03\x04"
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        assert z.namelist() == ["certificado-001.pdf"]
    despues = RepositorioEmisiones(_fabrica(base_pg)).obtener_por_lote(
        lote.id_lote
    )
    assert despues.estado == antes.estado
    assert despues.actualizada_en == antes.actualizada_en


def test_descargar_antes_de_generar_rechaza(base_pg: str) -> None:
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="demo")
    servicio = _servicio(base_pg, modo_demo=True)
    with pytest.raises(ErrorEmisionWeb) as error:
        servicio.descargar(lote.id_lote, actor=_actor(demo=True))
    assert error.value.code == "estado_invalido"


def test_descargar_lote_real_rechaza(base_pg: str) -> None:
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="google")
    servicio = _servicio(base_pg)
    with pytest.raises(ErrorEmisionWeb) as error:
        servicio.descargar(lote.id_lote, actor=_actor())
    assert error.value.code == "lote_no_demo"


def test_el_ciclo_completo_real_emite_con_motor_y_destino(
    base_pg: str, tmp_path: Path
) -> None:
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="google")
    registro = _registro_con_linea(tmp_path, lote)
    destino = DestinoMemoria()
    servicio = _servicio(
        base_pg,
        registro_decisiones=registro,
        fabrica_destino=lambda: destino,
    )
    estado = servicio.solicitar(
        lote.id_lote, hash_lote=lote.objeto_lote, actor=_actor()
    )
    assert estado.estado == ESTADO_EN_COLA
    id_emision = servicio.correr_una_vez(worker_id="w-1")
    assert id_emision is not None
    estado = servicio.consultar(lote.id_lote, actor=_actor())
    assert estado.estado == ESTADO_EMITIDA_WEB
    assert estado.enviadas == 1


def test_trabajo_indeterminado_se_muestra_sin_reintento(
    base_pg: str, tmp_path: Path
) -> None:
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="google")
    registro = _registro_con_linea(tmp_path, lote)
    servicio = _servicio(base_pg, registro_decisiones=registro)
    servicio.solicitar(
        lote.id_lote, hash_lote=lote.objeto_lote, actor=_actor()
    )
    emisiones = RepositorioEmisiones(_fabrica(base_pg))
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None and trabajo.token_reserva
    emisiones.marcar_enviando(
        id_emision=trabajo.id_emision,
        token=trabajo.token_reserva,
        ahora=AHORA,
    )
    emisiones.reconciliar(
        ahora=datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)
    )
    estado = servicio.consultar(lote.id_lote, actor=_actor())
    assert estado.estado == ESTADO_INDETERMINADA_WEB
    assert "emision_indeterminada" in estado.bloqueos
    assert estado.disponible is False
    # Ni solicitar ni correr reaniman el trabajo.
    assert servicio.correr_una_vez(worker_id="w-2") is None
    estado2 = servicio.solicitar(
        lote.id_lote, hash_lote=lote.objeto_lote, actor=_actor()
    )
    assert estado2.estado == ESTADO_INDETERMINADA_WEB


def test_el_estado_traduce_la_cola(base_pg: str, tmp_path: Path) -> None:
    """RESERVADA se muestra EN_COLA y ENVIANDO como EMITIENDO."""
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="google")
    registro = _registro_con_linea(tmp_path, lote)
    servicio = _servicio(base_pg, registro_decisiones=registro)
    servicio.solicitar(
        lote.id_lote, hash_lote=lote.objeto_lote, actor=_actor()
    )
    emisiones = RepositorioEmisiones(_fabrica(base_pg))
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert servicio.consultar(lote.id_lote, actor=_actor()).estado == (
        ESTADO_EN_COLA
    )
    assert trabajo is not None and trabajo.token_reserva
    emisiones.marcar_enviando(
        id_emision=trabajo.id_emision,
        token=trabajo.token_reserva,
        ahora=AHORA,
    )
    assert servicio.consultar(lote.id_lote, actor=_actor()).estado == (
        ESTADO_EMITIENDO
    )
    emisiones.finalizar(
        id_emision=trabajo.id_emision,
        token=trabajo.token_reserva,
        estado=ESTADO_INDETERMINADA,
        ahora=AHORA,
    )
    assert servicio.consultar(lote.id_lote, actor=_actor()).estado == (
        ESTADO_INDETERMINADA_WEB
    )


def test_actor_nulo_siempre_rechaza(base_pg: str) -> None:
    lotes = RepositorioLotes(_fabrica(base_pg))
    lote = _lote(lotes, origen="demo")
    servicio = _servicio(base_pg, modo_demo=True)
    with pytest.raises(ErrorEmisionWeb):
        servicio.consultar(lote.id_lote, actor=None)
    with pytest.raises(ErrorEmisionWeb):
        servicio.solicitar(
            lote.id_lote, hash_lote=lote.objeto_lote, actor=None
        )
    with pytest.raises(ErrorEmisionWeb):
        servicio.descargar(lote.id_lote, actor=None)


def test_correr_una_vez_sin_cola_rechaza() -> None:
    servicio = EmisionCertificadosWeb(
        lotes=RepositorioLotes(lambda: None),
        emisiones=None,
    )
    with pytest.raises(ErrorEmisionWeb) as error:
        servicio.correr_una_vez(worker_id="w-1")
    assert error.value.code == "cola_no_configurada"


def test_sin_trabajo_correr_devuelve_none(base_pg: str) -> None:
    servicio = _servicio(base_pg)
    assert servicio.correr_una_vez(worker_id="w-1") is None


def test_la_interfaz_del_contrato_es_la_unica_expuesta() -> None:
    """Las firmas públicas son exactamente las del contrato: ni alias ni
    métodos extra en la superficie."""
    publicos = {
        nombre
        for nombre in dir(EmisionCertificadosWeb)
        if not nombre.startswith("_")
    }
    assert publicos == {
        "consultar",
        "solicitar",
        "descargar",
        "correr_una_vez",
    }
