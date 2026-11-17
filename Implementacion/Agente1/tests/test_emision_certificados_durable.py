"""Emisión durable del lote de certificados aprobado en la web (#168).

El circuito real sigue siendo `procesar_emision_certificados`; la cola
sólo guarda el trabajo y el puntero al snapshot del lote. Los datos de
los titulares quedan en `lotes_certificados` (la lista que se mostró al
aprobar), nunca en la cola, y la descarga se compone al vuelo.

Los casos de reserva, expiración y caída se prueban contra PostgreSQL
real: un doble es incapaz de reproducir `FOR UPDATE SKIP LOCKED`. Las
conexiones usan `SET ROLE` sobre el esquema desechable —los roles del
canal se ejercen con sus privilegios reales, sin tocar claves globales.
"""

from __future__ import annotations

import io
import os
import re
import threading
import uuid
import zipfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest

from agente1.canal_form import PadronRoles, hash_correo
from agente1.certificados_emision import (
    PersonaCierre,
    ResultadoEmisionCertificados,
)
from agente1.confirmaciones import (
    ROL_APROBADOR_CONTENIDO,
    EntregaRechazadaError,
)
from agente1.decisiones_form import (
    DECISION_APRUEBO_CONTENIDO,
    DECISION_APRUEBO_LOTE,
    RESULTADO_REGISTRADA,
    TIPO_LINEA_DESCRIPTIVA,
    TIPO_LOTE,
    RegistroDecisiones,
    ResultadoDecision,
)
from agente1.emisiones_certificados import (
    ESTADO_EMITIDA,
    ESTADO_EMITIDA_PARCIAL,
    ESTADO_EXPIRADA,
    ESTADO_FALLIDA,
    ESTADO_GENERADA_DEMO,
    ESTADO_INDETERMINADA,
    ESTADO_PENDIENTE,
    ESTADO_RESERVADA,
    FuenteActividadSnapshot,
    LectorListaSnapshot,
    RepositorioEmisiones,
    construir_zip_certificados,
    ejecutar_trabajo_demo,
    ejecutar_trabajo_emision,
    nombre_zip,
)
from agente1.linea_descriptiva import objeto_id_linea_descriptiva
from agente1.web.certificados_web import (
    ESTADO_APROBADA,
    RepositorioLotes,
)

MIGRACIONES = Path(__file__).resolve().parent.parent / "migrations"
DSN = os.environ.get("AGENTE1_POSTGRES_DSN")
AHORA = datetime(2026, 11, 17, 9, 0, tzinfo=timezone.utc)
CORREO = "aprobador@example.invalid"
LINEA = "Línea descriptiva aprobada para el lote durable."
ACTIVIDAD = {
    "titulo": "Curso de prueba durable",
    "duracion_horas": "8",
    "modalidad": "presencial",
    "fecha_inicio": "2026-11-01",
    "fecha_fin": "2026-11-02",
    "organiza": "Facultad de Ingeniería del Ejército",
}
_FORMATO_CODIGO_SQL = re.compile(r"[A-Za-z0-9_.-]{1,64}")


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
        PersonaCierre(
            nombre="Bruno",
            apellido="Prueba",
            dni="90000012",
            mail="bruno.prueba@example.invalid",
            tratamiento="Sr.",
            condicion="asistencia",
        ),
    )


@pytest.fixture()
def base_pg():
    """Esquema desechable con las migraciones y los roles del canal."""
    if not DSN:
        pytest.skip("sin AGENTE1_POSTGRES_DSN (servicio de CI o base local)")
    esquema = f"test_durable_{uuid.uuid4().hex[:10]}"
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


def _fabrica(esquema: str, rol: str | None = "agente1_app"):
    """Conexiones al esquema como rol del canal, sin claves nuevas."""

    def abrir():
        conn = psycopg.connect(
            DSN, options=f"-c search_path={esquema}", autocommit=False
        )
        if rol is not None:
            conn.execute(f"SET ROLE {rol}")
            conn.commit()
        return conn

    return abrir


def _lotes(esquema: str, rol: str = "agente1_app") -> RepositorioLotes:
    return RepositorioLotes(_fabrica(esquema, rol))


def _emisiones(esquema: str, rol: str = "agente1_app") -> RepositorioEmisiones:
    return RepositorioEmisiones(_fabrica(esquema, rol))


def _crear_lote(
    repo: RepositorioLotes,
    *,
    origen: str | None = "google",
    id_actividad: str = "FIE-DUR-01",
):
    return repo.crear(
        id_actividad=id_actividad,
        actividad=dict(ACTIVIDAD),
        personas=_personas(),
        linea_descriptiva=LINEA,
        generada_por_hash=hash_correo(CORREO),
        origen_creacion=origen,
        ahora=AHORA,
    )


def _aprobar(repo: RepositorioLotes, lote, *, ahora: datetime = AHORA):
    return repo.decidir(
        id_lote=lote.id_lote,
        hash_lote=lote.objeto_lote,
        accion="aprobar",
        validador_hash=hash_correo(CORREO),
        rol=ROL_APROBADOR_CONTENIDO,
        origen_identidad="google",
        version_agente="0.9.0",
        ahora=ahora,
    )


def _registro(tmp_path: Path) -> RegistroDecisiones:
    return RegistroDecisiones(tmp_path / "decisiones")


def _registrar_linea(registro: RegistroDecisiones, lote) -> None:
    registro.registrar(
        ResultadoDecision(
            id_respuesta="c" * 64,
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


def _registrar_aprobaciones(registro: RegistroDecisiones, lote) -> None:
    _registrar_linea(registro, lote)
    registro.registrar(
        ResultadoDecision(
            id_respuesta="d" * 64,
            correo_hash=hash_correo(CORREO),
            rol=ROL_APROBADOR_CONTENIDO,
            rol_origen="padron",
            tipo=TIPO_LOTE,
            objeto_id=lote.objeto_lote,
            decision=DECISION_APRUEBO_LOTE,
            resultado=RESULTADO_REGISTRADA,
            rechazo_codigo=None,
            marca_temporal_form=AHORA.isoformat(),
            timestamp=AHORA.isoformat(),
        )
    )


class MotorEspia:
    def __init__(self) -> None:
        self.llamadas: list[dict] = []

    def __call__(self, **kwargs):
        self.llamadas.append(kwargs)
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


class DestinoTransporteRoto:
    """Lanza en cada entrega: el transporte pudo haber mandado."""

    modo = "produccion"

    def __init__(self, error: Exception | None = None) -> None:
        self.entregas = 0
        self._error = error or RuntimeError("timeout leyendo respuesta")

    def entregar(self, **kwargs) -> None:
        self.entregas += 1
        raise self._error


# --- cola y snapshot --------------------------------------------------------


def test_la_cola_no_guarda_datos_de_titulares(base_pg: str) -> None:
    with psycopg.connect(
        DSN, options=f"-c search_path={base_pg}"
    ) as conn:
        columnas = {
            fila[0]
            for fila in conn.execute(
                "SELECT column_name FROM information_schema.columns"
                " WHERE table_name = 'emisiones_certificados'"
            ).fetchall()
        }
    assert columnas
    for prohibida in ("dni", "mail", "nombre", "apellido", "personas"):
        assert prohibida not in columnas


def test_encolar_es_idempotente_y_entra_pendiente(base_pg: str) -> None:
    lotes = _lotes(base_pg)
    emisiones = _emisiones(base_pg)
    lote = _crear_lote(lotes)
    assert _aprobar(lotes, lote).codigo == "aprobada"
    primero = emisiones.encolar(id_lote=lote.id_lote, ahora=AHORA)
    segundo = emisiones.encolar(id_lote=lote.id_lote, ahora=AHORA)
    assert primero.id_emision == segundo.id_emision
    assert primero.estado == ESTADO_PENDIENTE
    assert primero.total == 0
    assert len(emisiones.listar()) == 1


def test_origen_invalido_no_entra_en_la_base(base_pg: str) -> None:
    lotes = _lotes(base_pg)
    with pytest.raises(Exception):
        _crear_lote(lotes, origen="web")


def test_el_snapshot_no_relee_la_fuente_mutable() -> None:
    actividad = dict(ACTIVIDAD)
    personas = _personas()
    fuente = FuenteActividadSnapshot(actividad)
    lector = LectorListaSnapshot(personas)
    actividad["titulo"] = "Título cambiado después de aprobar"
    personas_mutables = list(personas)
    personas_mutables[0] = replace(personas_mutables[0], nombre="Otro")
    assert fuente.obtener("FIE-DUR-01")["titulo"] == ACTIVIDAD["titulo"]
    filas = lector.leer_valores()
    assert filas[0][0] == "Ana"
    assert filas[1][0] == "Bruno"


# --- reserva, expiración y caída -------------------------------------------


def _trabajo_encolado(esquema: str, *, origen: str | None = "google"):
    lotes = _lotes(esquema)
    lote = _crear_lote(lotes, origen=origen)
    assert _aprobar(lotes, lote).codigo == "aprobada"
    emisiones = _emisiones(esquema)
    modo = "demo" if origen == "demo" else "real"
    emisiones.encolar(id_lote=lote.id_lote, modo=modo, ahora=AHORA)
    return lotes, emisiones, lote


def test_dos_workers_no_toman_el_mismo_trabajo(base_pg: str) -> None:
    _lotes_repo, emisiones, _lote = _trabajo_encolado(base_pg)
    barrera = threading.Barrier(2)
    tomados: list[str | None] = []
    guardia = threading.Lock()

    def trabajador(nombre: str) -> None:
        repo = _emisiones(base_pg)
        barrera.wait()
        trabajo = repo.reclamar(worker_id=nombre, ahora=AHORA)
        with guardia:
            tomados.append(trabajo.id_emision if trabajo else None)

    hilos = [
        threading.Thread(target=trabajador, args=(f"w-{i}",))
        for i in range(2)
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert len([t for t in tomados if t]) == 1
    assert tomados.count(None) == 1


def test_reserva_vencida_vuelve_a_pendiente(base_pg: str) -> None:
    _lotes_repo, emisiones, _lote = _trabajo_encolado(base_pg)
    primero = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert primero is not None
    assert primero.estado == ESTADO_RESERVADA
    assert primero.id_emision.startswith("emi-")
    despues = AHORA + timedelta(hours=1)
    assert emisiones.reconciliar(ahora=despues) >= 1
    segundo = emisiones.reclamar(worker_id="w-2", ahora=despues)
    assert segundo is not None
    assert segundo.id_emision == primero.id_emision


def test_caida_durante_el_envio_queda_indeterminada_y_no_se_reintenta(
    base_pg: str,
) -> None:
    _lotes_repo, emisiones, _lote = _trabajo_encolado(base_pg)
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None
    assert trabajo.token_reserva
    assert emisiones.marcar_enviando(
        id_emision=trabajo.id_emision,
        token=trabajo.token_reserva,
        ahora=AHORA,
    )
    despues = AHORA + timedelta(hours=1)
    emisiones.reconciliar(ahora=despues)
    actual = emisiones.obtener_por_lote(_lote.id_lote)
    assert actual is not None
    assert actual.estado == ESTADO_INDETERMINADA
    assert emisiones.reclamar(worker_id="w-2", ahora=despues) is None


def test_trabajo_vencido_expira_y_no_se_reclama(base_pg: str) -> None:
    lotes = _lotes(base_pg)
    lote = _crear_lote(lotes)
    assert _aprobar(lotes, lote).codigo == "aprobada"
    emisiones = _emisiones(base_pg)
    emisiones.encolar(
        id_lote=lote.id_lote,
        ahora=AHORA,
        expira_en=AHORA + timedelta(hours=1),
    )
    despues = AHORA + timedelta(hours=2)
    emisiones.reconciliar(ahora=despues)
    actual = emisiones.obtener_por_lote(lote.id_lote)
    assert actual is not None
    assert actual.estado == ESTADO_EXPIRADA
    assert emisiones.reclamar(worker_id="w-1", ahora=despues) is None


# --- ejecución del motor ---------------------------------------------------


def test_el_worker_usa_el_motor_real_con_el_snapshot_aprobado(
    base_pg: str, tmp_path: Path
) -> None:
    lotes, emisiones, lote = _trabajo_encolado(base_pg)
    registro = _registro(tmp_path)
    _registrar_aprobaciones(registro, lote)
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None
    motor = MotorEspia()
    resultado = ejecutar_trabajo_emision(
        trabajo,
        repositorio=emisiones,
        lotes=lotes,
        padron=PadronRoles({CORREO: ROL_APROBADOR_CONTENIDO}),
        registro_decisiones=registro,
        directorio_salida=tmp_path / "salida",
        fabrica_destino=DestinoMemoria,
        motor=motor,
        ahora=AHORA,
    )
    assert resultado.estado == ESTADO_EMITIDA
    assert len(motor.llamadas) == 1
    llamada = motor.llamadas[0]
    assert (
        llamada["fuente"].obtener("FIE-DUR-01")["titulo"]
        == ACTIVIDAD["titulo"]
    )
    assert llamada["solicitante_correo"] == CORREO
    actual = emisiones.obtener_por_lote(lote.id_lote)
    assert actual is not None
    assert actual.estado == ESTADO_EMITIDA
    assert actual.enviadas == 2


def test_rol_revocado_no_llama_al_motor_ni_envia(
    base_pg: str, tmp_path: Path
) -> None:
    lotes, emisiones, lote = _trabajo_encolado(base_pg)
    registro = _registro(tmp_path)
    _registrar_aprobaciones(registro, lote)
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None
    motor = MotorEspia()
    resultado = ejecutar_trabajo_emision(
        trabajo,
        repositorio=emisiones,
        lotes=lotes,
        padron=PadronRoles({CORREO: "COORDINADOR"}),
        registro_decisiones=registro,
        directorio_salida=tmp_path / "salida",
        fabrica_destino=DestinoMemoria,
        motor=motor,
        ahora=AHORA,
    )
    assert resultado.estado == ESTADO_FALLIDA
    assert resultado.codigo == "rol_revocado"
    assert motor.llamadas == []
    actual = emisiones.obtener_por_lote(lote.id_lote)
    assert actual is not None
    assert actual.estado == ESTADO_FALLIDA
    assert actual.error_codigo == "rol_revocado"


def test_el_motor_real_emite_el_lote_y_deja_la_cola_emitida(
    base_pg: str, tmp_path: Path
) -> None:
    lotes, emisiones, lote = _trabajo_encolado(base_pg)
    registro = _registro(tmp_path)
    _registrar_aprobaciones(registro, lote)
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None
    destino = DestinoMemoria()
    resultado = ejecutar_trabajo_emision(
        trabajo,
        repositorio=emisiones,
        lotes=lotes,
        padron=PadronRoles({CORREO: ROL_APROBADOR_CONTENIDO}),
        registro_decisiones=registro,
        directorio_salida=tmp_path / "salida",
        fabrica_destino=lambda: destino,
        ahora=AHORA,
    )
    assert resultado.estado == ESTADO_EMITIDA
    assert len(destino.entregas) == 2
    actual = emisiones.obtener_por_lote(lote.id_lote)
    assert actual is not None
    assert actual.estado == ESTADO_EMITIDA
    assert actual.enviadas == 2


# --- entrega ambigua y códigos estables ------------------------------------


def _motor_como_el_real(**kwargs) -> ResultadoEmisionCertificados:
    """Imita el contrato del motor: traga la excepción de cada entrega,
    sigue con la siguiente persona y cierra con la prosa
    "N entregas fallidas"."""
    destino = kwargs["destino"]
    filas = kwargs["lector_lista"].leer_valores()
    emitidas = 0
    fallidas = 0
    for indice, _fila in enumerate(filas):
        try:
            destino.entregar(
                idempotency_key=f"k-{indice}",
                destinatario="x@example.invalid",
                asunto="a",
                cuerpo="c",
            )
        except Exception:
            fallidas += 1
            continue
        emitidas += 1
    estado = (
        "EMITIDA"
        if fallidas == 0
        else "EMITIDA_PARCIAL"
        if emitidas
        else "FALLIDA"
    )
    return ResultadoEmisionCertificados(
        estado=estado,
        correlation_id="cid",
        log_path="/tmp/no",
        resumen="ok",
        error=f"{fallidas} entregas fallidas" if fallidas else None,
        emitidas=emitidas,
        entregas_fallidas=fallidas,
    )


def _ejecutar_con_destino(
    base_pg: str, tmp_path: Path, destino
):
    lotes, emisiones, lote = _trabajo_encolado(base_pg)
    registro = _registro(tmp_path)
    _registrar_aprobaciones(registro, lote)
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None
    resultado = ejecutar_trabajo_emision(
        trabajo,
        repositorio=emisiones,
        lotes=lotes,
        padron=PadronRoles({CORREO: ROL_APROBADOR_CONTENIDO}),
        registro_decisiones=registro,
        directorio_salida=tmp_path / "salida",
        fabrica_destino=lambda: destino,
        motor=_motor_como_el_real,
        ahora=AHORA,
    )
    actual = emisiones.obtener_por_lote(lote.id_lote)
    return resultado, actual


def test_transporte_roto_es_indeterminado_aun_sin_envios(
    base_pg: str, tmp_path: Path
) -> None:
    """Una excepción de transporte no es una falla limpia: pudo salir."""
    destino = DestinoTransporteRoto()
    resultado, actual = _ejecutar_con_destino(base_pg, tmp_path, destino)
    assert resultado.estado == ESTADO_INDETERMINADA
    assert actual is not None
    assert actual.estado == ESTADO_INDETERMINADA
    assert actual.error_codigo == "entrega_ambigua"
    # La segunda entrega se bloqueó en el wrapper: el transporte la vio
    # una sola vez, no por cada titular del lote.
    assert destino.entregas == 1


def test_transporte_roto_tras_un_envio_tambien_es_indeterminado(
    base_pg: str, tmp_path: Path
) -> None:
    """Con un envío confirmado, la siguiente excepción sigue siendo
    indeterminada: no se puede saber si el resto salió."""

    class PrimeroBienLuegoRoto:
        modo = "produccion"

        def __init__(self) -> None:
            self.entregas = 0

        def entregar(self, **kwargs) -> None:
            self.entregas += 1
            if self.entregas > 1:
                raise RuntimeError("conexión caída")

    destino = PrimeroBienLuegoRoto()
    resultado, actual = _ejecutar_con_destino(base_pg, tmp_path, destino)
    assert resultado.estado == ESTADO_INDETERMINADA
    assert actual is not None
    assert actual.estado == ESTADO_INDETERMINADA
    assert actual.enviadas == 1
    assert actual.error_codigo == "entrega_ambigua"


def test_rechazo_de_politica_es_falla_limpia_y_codigo_sql_seguro(
    base_pg: str, tmp_path: Path
) -> None:
    """`EntregaRechazadaError` es por destinatario: falla sin ambigüedad
    y el código persistido no es la prosa del motor."""

    class TodosRechazados:
        modo = "produccion"

        def __init__(self) -> None:
            self.entregas = 0

        def entregar(self, **kwargs) -> None:
            self.entregas += 1
            raise EntregaRechazadaError("destinatario_no_aprobado")

    destino = TodosRechazados()
    resultado, actual = _ejecutar_con_destino(base_pg, tmp_path, destino)
    assert resultado.estado == ESTADO_FALLIDA
    assert actual is not None
    assert actual.estado == ESTADO_FALLIDA
    # El motor devuelve "2 entregas fallidas"; el CHECK de la columna no
    # admite espacios y la fila guarda el código estable.
    assert actual.error_codigo == "entregas_fallidas"
    assert _FORMATO_CODIGO_SQL.fullmatch(actual.error_codigo)


def test_emision_parcial_tambien_usa_codigo_sql_seguro(
    base_pg: str, tmp_path: Path
) -> None:
    class UnoSiUnoNo:
        modo = "produccion"

        def __init__(self) -> None:
            self.entregas = 0

        def entregar(self, **kwargs) -> None:
            self.entregas += 1
            if self.entregas == 2:
                raise EntregaRechazadaError("destinatario_no_aprobado")

    destino = UnoSiUnoNo()
    resultado, actual = _ejecutar_con_destino(base_pg, tmp_path, destino)
    assert resultado.estado == ESTADO_EMITIDA_PARCIAL
    assert actual is not None
    assert actual.estado == ESTADO_EMITIDA_PARCIAL
    assert actual.enviadas == 1
    assert actual.fallidas == 1
    assert _FORMATO_CODIGO_SQL.fullmatch(actual.error_codigo or "")


# --- aprobación y origen ----------------------------------------------------


def test_el_worker_repara_solo_el_apruebo_lote(
    base_pg: str, tmp_path: Path
) -> None:
    """Si la fila SQL comprobó la aprobación pero el JSONL no la tiene,
    el worker la proyecta — y sólo el `apruebo_lote`, nunca la línea."""
    lotes, emisiones, lote = _trabajo_encolado(base_pg)
    registro = _registro(tmp_path)
    _registrar_linea(registro, lote)  # línea sí, lote no
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None
    destino = DestinoMemoria()
    resultado = ejecutar_trabajo_emision(
        trabajo,
        repositorio=emisiones,
        lotes=lotes,
        padron=PadronRoles({CORREO: ROL_APROBADOR_CONTENIDO}),
        registro_decisiones=registro,
        directorio_salida=tmp_path / "salida",
        fabrica_destino=lambda: destino,
        ahora=AHORA,
    )
    assert resultado.estado == ESTADO_EMITIDA
    # El `apruebo_lote` reparado quedó con la identidad de la fila.
    entradas = list(registro.procesadas())
    lote_asientos = [
        e for e in entradas
        if e["tipo"] == TIPO_LOTE and e["decision"] == DECISION_APRUEBO_LOTE
    ]
    assert len(lote_asientos) == 1
    assert lote_asientos[0]["correo_hash"] == hash_correo(CORREO)
    assert lote_asientos[0]["objeto_id"] == lote.objeto_lote


def test_sin_aprobacion_de_linea_el_lote_queda_bloqueado(
    base_pg: str, tmp_path: Path
) -> None:
    """La línea nunca la fabrica el worker: falta = falla, no invención."""
    lotes, emisiones, lote = _trabajo_encolado(base_pg)
    registro = _registro(tmp_path)
    # Sólo el `apruebo_lote`: la línea queda sin asentar a propósito.
    registro.registrar(
        ResultadoDecision(
            id_respuesta="d" * 64,
            correo_hash=hash_correo(CORREO),
            rol=ROL_APROBADOR_CONTENIDO,
            rol_origen="padron",
            tipo=TIPO_LOTE,
            objeto_id=lote.objeto_lote,
            decision=DECISION_APRUEBO_LOTE,
            resultado=RESULTADO_REGISTRADA,
            rechazo_codigo=None,
            marca_temporal_form=AHORA.isoformat(),
            timestamp=AHORA.isoformat(),
        )
    )
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None
    destino = DestinoMemoria()
    resultado = ejecutar_trabajo_emision(
        trabajo,
        repositorio=emisiones,
        lotes=lotes,
        padron=PadronRoles({CORREO: ROL_APROBADOR_CONTENIDO}),
        registro_decisiones=registro,
        directorio_salida=tmp_path / "salida",
        fabrica_destino=lambda: destino,
        ahora=AHORA,
    )
    assert resultado.estado == ESTADO_FALLIDA
    assert destino.entregas == []
    entradas = list(registro.procesadas())
    linea_asientos = [
        e for e in entradas
        if e["tipo"] == TIPO_LINEA_DESCRIPTIVA
    ]
    # El worker no inventó la aprobación de la línea.
    assert linea_asientos == []


def test_lote_demo_nunca_llega_al_carril_real(
    base_pg: str, tmp_path: Path
) -> None:
    """El origen demo es permanente: ni el carril real ni Gmail, aunque
    alguien haya encolado la fila como `real`."""
    lotes = _lotes(base_pg)
    lote_demo = _crear_lote(
        lotes, origen="demo", id_actividad="FIE-DUR-DEMO"
    )
    assert _aprobar(lotes, lote_demo).codigo == "aprobada"
    emisiones = _emisiones(base_pg)
    emisiones.encolar(id_lote=lote_demo.id_lote, modo="real", ahora=AHORA)
    registro = _registro(tmp_path)
    _registrar_aprobaciones(registro, lote_demo)
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None
    assert trabajo.id_lote == lote_demo.id_lote
    destino = DestinoMemoria()
    resultado = ejecutar_trabajo_emision(
        trabajo,
        repositorio=emisiones,
        lotes=lotes,
        padron=PadronRoles({CORREO: ROL_APROBADOR_CONTENIDO}),
        registro_decisiones=registro,
        directorio_salida=tmp_path / "salida",
        fabrica_destino=lambda: destino,
        ahora=AHORA,
        modo_demo=False,
    )
    assert resultado.estado == ESTADO_FALLIDA
    assert resultado.codigo == "lote_demo_no_envia"
    assert destino.entregas == []


def test_modo_demo_no_emite_lotes_reales(
    base_pg: str, tmp_path: Path
) -> None:
    lotes, emisiones, lote = _trabajo_encolado(base_pg)
    registro = _registro(tmp_path)
    _registrar_aprobaciones(registro, lote)
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None
    destino = DestinoMemoria()
    resultado = ejecutar_trabajo_emision(
        trabajo,
        repositorio=emisiones,
        lotes=lotes,
        padron=PadronRoles({CORREO: ROL_APROBADOR_CONTENIDO}),
        registro_decisiones=registro,
        directorio_salida=tmp_path / "salida",
        fabrica_destino=lambda: destino,
        ahora=AHORA,
        modo_demo=True,
    )
    assert resultado.estado == ESTADO_FALLIDA
    assert resultado.codigo == "modo_demo_no_envia"
    assert destino.entregas == []


# --- carril demo ------------------------------------------------------------


def test_trabajo_demo_espera_al_worker_para_generar(base_pg: str) -> None:
    """Encolar demo deja PENDIENTE: GENERADA_DEMO llega tras el render."""
    lotes, emisiones, lote = _trabajo_encolado(base_pg, origen="demo")
    pendiente = emisiones.obtener_por_lote(lote.id_lote)
    assert pendiente is not None
    assert pendiente.estado == ESTADO_PENDIENTE
    assert pendiente.modo == "demo"
    trabajo = emisiones.reclamar(worker_id="w-demo", ahora=AHORA)
    assert trabajo is not None
    resultado = ejecutar_trabajo_demo(
        trabajo,
        repositorio=emisiones,
        lotes=lotes,
        padron=PadronRoles({CORREO: ROL_APROBADOR_CONTENIDO}),
        modo_demo=True,
        ahora=AHORA,
    )
    assert resultado.estado == ESTADO_GENERADA_DEMO
    actual = emisiones.obtener_por_lote(lote.id_lote)
    assert actual is not None
    assert actual.estado == ESTADO_GENERADA_DEMO
    assert actual.total == 2
    assert actual.retencion_hasta is not None
    assert emisiones.reclamar(worker_id="w-demo", ahora=AHORA) is None


def test_trabajo_demo_sin_modo_demo_cierra_fallida(base_pg: str) -> None:
    """Un trabajo demo en un runtime no-demo se bloquea, no se envía."""
    lotes, emisiones, lote = _trabajo_encolado(base_pg, origen="demo")
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None
    resultado = ejecutar_trabajo_demo(
        trabajo,
        repositorio=emisiones,
        lotes=lotes,
        modo_demo=False,
        ahora=AHORA,
    )
    assert resultado.estado == ESTADO_FALLIDA
    assert resultado.codigo == "demo_fuera_de_modo"
    actual = emisiones.obtener_por_lote(lote.id_lote)
    assert actual is not None
    assert actual.estado == ESTADO_FALLIDA


def test_trabajo_demo_revalida_el_rol_si_hay_padron(base_pg: str) -> None:
    lotes, emisiones, lote = _trabajo_encolado(base_pg, origen="demo")
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None
    resultado = ejecutar_trabajo_demo(
        trabajo,
        repositorio=emisiones,
        lotes=lotes,
        padron=PadronRoles({CORREO: "LECTOR"}),
        modo_demo=True,
        ahora=AHORA,
    )
    assert resultado.estado == ESTADO_FALLIDA
    assert resultado.codigo == "rol_revocado"


def test_trabajo_demo_sin_padron_igual_compone(base_pg: str) -> None:
    lotes, emisiones, lote = _trabajo_encolado(base_pg, origen="demo")
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None
    resultado = ejecutar_trabajo_demo(
        trabajo,
        repositorio=emisiones,
        lotes=lotes,
        padron=None,
        modo_demo=True,
        ahora=AHORA,
    )
    assert resultado.estado == ESTADO_GENERADA_DEMO


def test_zip_demo_es_determinista_y_sin_datos_en_los_nombres() -> None:
    from agente1.web.certificados_web import LoteCertificados

    lote = LoteCertificados(
        id_lote="lote-abc123",
        id_actividad="FIE-DUR-01",
        objeto_lote="a" * 64,
        hash_lista="b" * 64,
        actividad=dict(ACTIVIDAD),
        personas=_personas(),
        cantidad_personas=2,
        linea_descriptiva=LINEA,
        linea_descriptiva_hash="c" * 64,
        plantilla_muestra="certificado_seu_aprobacion_v1",
        estado=ESTADO_APROBADA,
        generada_por_hash=hash_correo(CORREO),
        creada_en=AHORA,
        origen_creacion="demo",
    )
    primero = construir_zip_certificados(lote=lote, demo=True)
    segundo = construir_zip_certificados(lote=lote, demo=True)
    assert primero == segundo
    nombre = nombre_zip(lote.id_lote)
    assert nombre.startswith("certificados-")
    assert "90000011" not in nombre
    assert "ana.prueba" not in nombre
    with zipfile.ZipFile(io.BytesIO(primero)) as z:
        nombres = z.namelist()
        assert nombres == ["certificado-001.pdf", "certificado-002.pdf"]
        for nombre_pdf in nombres:
            assert "90000011" not in nombre_pdf
            assert "ana.prueba" not in nombre_pdf
            assert b"DOCUMENTO DE PRUEBA" in z.read(nombre_pdf)


# --- retención ---------------------------------------------------------------


def _mantenimiento(esquema: str) -> RepositorioLotes:
    return RepositorioLotes(_fabrica(esquema, "agente1_mantenimiento"))


def test_purga_legacy_sin_trabajo_es_inmediata(base_pg: str) -> None:
    """El lote sin `origen_creacion` purga como antes: en la decisión."""
    lotes = _lotes(base_pg)
    lote = _crear_lote(lotes, origen=None)
    assert _aprobar(lotes, lote).codigo == "aprobada"
    assert _mantenimiento(base_pg).purgar_cerrados(ahora=AHORA) == 1
    purgado = lotes.obtener(lote.id_lote)
    assert purgado is not None
    assert purgado.personas == ()


def test_purga_nuevo_origen_sin_trabajo_espera_el_abandono(
    base_pg: str,
) -> None:
    """Un lote `google` aprobado sin emisión aguanta 30 días: puede
    pedirse todavía; un lote legacy en la misma corrida ya purga."""
    lotes = _lotes(base_pg)
    nuevo = _crear_lote(lotes, origen="google")
    assert _aprobar(lotes, nuevo).codigo == "aprobada"
    purga = _mantenimiento(base_pg)
    assert purga.purgar_cerrados(ahora=AHORA) == 0
    assert lotes.obtener(nuevo.id_lote).personas
    assert (
        purga.purgar_cerrados(ahora=AHORA + timedelta(days=31)) == 1
    )


def test_purga_descartada_de_origen_nuevo_es_inmediata(base_pg: str) -> None:
    """El descarte no puede emitir: la retención mínima corre igual."""
    lotes = _lotes(base_pg)
    lote = _crear_lote(lotes, origen="google")
    assert (
        lotes.decidir(
            id_lote=lote.id_lote,
            hash_lote=lote.objeto_lote,
            accion="descartar",
            validador_hash=hash_correo(CORREO),
            rol=ROL_APROBADOR_CONTENIDO,
            origen_identidad="google",
            version_agente="0.9.0",
            ahora=AHORA,
        ).codigo
        == "descartada"
    )
    assert _mantenimiento(base_pg).purgar_cerrados(ahora=AHORA) == 1


def test_purga_nunca_toca_trabajo_activo(base_pg: str) -> None:
    _lotes_repo, _emisiones_repo, lote = _trabajo_encolado(base_pg)
    purga = _mantenimiento(base_pg)
    for delta in (
        timedelta(days=31),
        timedelta(days=400),
    ):
        assert purga.purgar_cerrados(ahora=AHORA + delta) == 0
    assert _lotes_repo.obtener(lote.id_lote).personas


def test_purga_nunca_toca_indeterminada(base_pg: str) -> None:
    _lotes_repo, emisiones, lote = _trabajo_encolado(base_pg)
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None and trabajo.token_reserva
    assert emisiones.marcar_enviando(
        id_emision=trabajo.id_emision,
        token=trabajo.token_reserva,
        ahora=AHORA,
    )
    emisiones.reconciliar(ahora=AHORA + timedelta(hours=1))
    purga = _mantenimiento(base_pg)
    assert purga.purgar_cerrados(ahora=AHORA + timedelta(days=400)) == 0
    assert _lotes_repo.obtener(lote.id_lote).personas


def test_purga_terminal_espera_la_retencion(base_pg: str) -> None:
    _lotes_repo, emisiones, lote = _trabajo_encolado(base_pg)
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None and trabajo.token_reserva
    emisiones.finalizar(
        id_emision=trabajo.id_emision,
        token=trabajo.token_reserva,
        estado=ESTADO_EMITIDA,
        total=2,
        enviadas=2,
        ahora=AHORA,
    )
    purga = _mantenimiento(base_pg)
    assert purga.purgar_cerrados(ahora=AHORA) == 0
    assert purga.purgar_cerrados(ahora=AHORA + timedelta(days=31)) == 1


def test_purga_demo_generada_espera_su_retencion(base_pg: str) -> None:
    _lotes_repo, emisiones, lote = _trabajo_encolado(
        base_pg, origen="demo"
    )
    trabajo = emisiones.reclamar(worker_id="w-1", ahora=AHORA)
    assert trabajo is not None and trabajo.token_reserva
    emisiones.finalizar(
        id_emision=trabajo.id_emision,
        token=trabajo.token_reserva,
        estado=ESTADO_GENERADA_DEMO,
        total=2,
        ahora=AHORA,
    )
    purga = _mantenimiento(base_pg)
    # La retención demo es de días, no la de 30 del real: a los 3 días
    # la descarga ya no tiene sentido y el snapshot se retira.
    assert purga.purgar_cerrados(ahora=AHORA) == 0
    assert purga.purgar_cerrados(ahora=AHORA + timedelta(days=3)) == 1
