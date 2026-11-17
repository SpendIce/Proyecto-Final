"""Restauración del respaldo y la cola durable de emisiones web (#168).

El volcado `postgres/` del artefacto se aplica con `psql` en una sola
transacción que además reconcilia la cola durable de emisión de
certificados (migración 0012 del worktree backend): todo trabajo real que
el snapshot dejó en un estado capaz de enviar (`PENDIENTE`, `RESERVADA`,
`ENVIANDO`) pasa a `INDETERMINADA` (la vista web muestra
`EMISION_INDETERMINADA`) y nunca vuelve a ser
reservable. Un respaldo anterior a un envío no lo repite. Los trabajos
demo no se marcan: no tienen efectos externos y se regeneran pidiéndolos
de nuevo. Un respaldo previo a la migración no tiene la tabla: la
reconciliación es condicional.

Corre contra PostgreSQL real (`AGENTE1_POSTGRES_DSN`, esquemas
desechables): lo que se prueba es el estado que queda en la base, no el
texto del SQL. Los roles del canal se ejercen con `SET ROLE`, sin
`ALTER ROLE ... PASSWORD` (la clave mutaría el rol a nivel clúster).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest

from agente1.canal_form import hash_correo
from agente1.certificados_emision import PersonaCierre
from agente1.respaldo import (
    RespaldoDiarioError,
    construir_artefacto,
    entorno_libpq,
    restaurar_estado_respaldo,
)
from agente1.web.certificados_web import RepositorioLotes

DSN = os.environ.get("AGENTE1_POSTGRES_DSN")
MIGRACIONES = Path(__file__).resolve().parent.parent / "migrations"

pytestmark = pytest.mark.skipif(
    not DSN,
    reason="sin AGENTE1_POSTGRES_DSN (servicio de CI o base local)",
)

AHORA = datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc)
MARCA = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
CORREO = "generador@example.invalid"
ACTIVIDAD = {
    "titulo": "Curso sintético restauración",
    "duracion_horas": "4",
    "modalidad": "virtual",
    "fecha_inicio": "2026-11-01",
    "organiza": "Organización ficticia de prueba",
}

@pytest.fixture()
def esquema():
    """Fábrica de esquemas desechables con migraciones aplicadas.

    `con_cola=True` aplica la migración real 0012; `False` reproduce un
    esquema pre-0012 para los respaldos legacy.
    """

    if shutil.which("pg_dump") is None or shutil.which("psql") is None:
        pytest.skip("sin pg_dump/psql en el entorno")
    creados: list[str] = []
    admin = psycopg.connect(DSN, autocommit=True)

    def crear(*, con_cola: bool = True) -> str:
        nombre = f"test_rest_{uuid.uuid4().hex[:10]}"
        admin.execute(f'CREATE SCHEMA "{nombre}"')
        ups = sorted(MIGRACIONES.glob("*.up.sql"))
        with psycopg.connect(
            DSN, options=f"-c search_path={nombre}", autocommit=True
        ) as conn:
            for up in ups:
                if not con_cola and up.name >= "0012":
                    continue
                conn.execute(up.read_text(encoding="utf-8"))
            conn.execute(
                f'GRANT USAGE ON SCHEMA "{nombre}"'
                " TO agente1_app, agente1_mantenimiento"
            )
        creados.append(nombre)
        return nombre

    yield crear
    for nombre in creados:
        admin.execute(f'DROP SCHEMA "{nombre}" CASCADE')
    admin.close()


def _fabrica(esquema: str, rol: str = "agente1_app"):
    """Conexiones al esquema con el rol del canal vía `SET ROLE`.

    Siembra y verifica con los permisos reales del despliegue, sin
    `ALTER ROLE ... PASSWORD`: el `SET ROLE` del superusuario acota los
    permisos a esta conexión y nada más.
    """

    def abrir():
        conn = psycopg.connect(
            DSN, options=f"-c search_path={esquema}", autocommit=False
        )
        conn.execute(f"SET ROLE {rol}")
        conn.commit()
        return conn

    return abrir


def _lote(esquema: str, sufijo: str) -> str:
    """Lote de certificados real para colgarle la emisión (FK exige lote)."""

    repo = RepositorioLotes(_fabrica(esquema))
    lote = repo.crear(
        id_actividad=f"ACT-REST-{sufijo}",
        actividad=dict(ACTIVIDAD),
        personas=(
            PersonaCierre(
                nombre="Ana",
                apellido="Prueba",
                dni="90000011",
                mail="ana.prueba@example.invalid",
                tratamiento="Sra.",
                condicion="asistencia",
            ),
        ),
        linea_descriptiva=f"Línea descriptiva del lote {sufijo}.",
        generada_por_hash=hash_correo(CORREO),
        ahora=AHORA,
    )
    return lote.id_lote


def _insertar_emision(
    esquema: str,
    id_lote: str,
    *,
    estado: str,
    modo: str = "real",
    ahora: datetime = AHORA,
    total: int = 0,
    enviadas: int = 0,
    fallidas: int = 0,
    error_codigo: str | None = None,
) -> str:
    """Una fila de la cola durable en el estado pedido, con sus CHECK felices."""

    reservada = estado in ("RESERVADA", "ENVIANDO")
    terminada = estado in (
        "EMITIDA",
        "EMITIDA_PARCIAL",
        "FALLIDA",
        "INDETERMINADA",
        "GENERADA_DEMO",
        "EXPIRADA",
    )
    id_emision = f"emi-{uuid.uuid4().hex[:12]}"
    retencion = None
    if terminada and estado != "INDETERMINADA":
        retencion = ahora + timedelta(
            days=2 if modo == "demo" else 30
        )
    with _fabrica(esquema)() as conn:
        conn.execute(
            "INSERT INTO emisiones_certificados (id_emision, id_lote, modo,"
            " estado, intentos, reservada_por, token_reserva, reservada_hasta,"
            " iniciada_en, terminada_en, expira_en, retencion_hasta, total,"
            " enviadas, fallidas, error_codigo, creada_en, actualizada_en)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                id_emision,
                id_lote,
                modo,
                estado,
                1 if reservada else 0,
                "worker-test" if reservada else None,
                "a" * 64 if reservada else None,
                ahora + timedelta(minutes=15) if reservada else None,
                ahora if estado == "ENVIANDO" else None,
                ahora if terminada else None,
                ahora + timedelta(hours=72),
                retencion,
                total,
                enviadas,
                fallidas,
                error_codigo,
                ahora,
                ahora,
            ),
        )
        conn.commit()
    return id_emision


def _fila_emision(esquema: str, id_lote: str) -> dict:
    """La fila cruda de la cola, leída como superusuario.

    La restauración recrea las tablas con el rol del DSN y los GRANT del
    esquema no sobreviven al `--clean`, así que la verificación corre con
    el usuario de la suite, no con `agente1_app`.
    """

    with psycopg.connect(
        DSN, options=f"-c search_path={esquema}"
    ) as conn:
        fila = conn.execute(
            "SELECT id_emision, modo, estado, intentos, reservada_por,"
            " token_reserva, reservada_hasta, iniciada_en, terminada_en,"
            " retencion_hasta, total, enviadas, fallidas"
            " FROM emisiones_certificados WHERE id_lote = %s",
            (id_lote,),
        ).fetchone()
    assert fila is not None
    return {
        "id_emision": fila[0],
        "modo": fila[1],
        "estado": fila[2],
        "intentos": fila[3],
        "reservada_por": fila[4],
        "token_reserva": fila[5],
        "reservada_hasta": fila[6],
        "iniciada_en": fila[7],
        "terminada_en": fila[8],
        "retencion_hasta": fila[9],
        "total": fila[10],
        "enviadas": fila[11],
        "fallidas": fila[12],
    }


def _reservables(esquema: str) -> list[str]:
    """Lo que un worker podría tomar ahora: la WHERE real de la reserva."""

    with psycopg.connect(
        DSN, options=f"-c search_path={esquema}", autocommit=True
    ) as conn:
        filas = conn.execute(
            "SELECT id_emision FROM emisiones_certificados"
            " WHERE estado = 'PENDIENTE' AND expira_en > now()"
            " ORDER BY creada_en FOR UPDATE SKIP LOCKED",
        ).fetchall()
    return [fila[0] for fila in filas]


def _dump_esquema(esquema: str) -> bytes:
    """El `pg_dump` del día, como `respaldar_estado.py` pero por esquema."""

    proceso = subprocess.run(
        [
            shutil.which("pg_dump"),
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "-n",
            esquema,
        ],
        capture_output=True,
        env={**os.environ, **entorno_libpq(DSN)},
    )
    assert proceso.returncode == 0, proceso.stderr.decode()
    # El cliente pg_dump 18 emite `SET transaction_timeout`, GUC que el
    # servidor 16 no conoce: en producción el cliente es 16 (Dockerfile),
    # así que se depura la línea como hace la suite del canal web.
    return b"".join(
        linea + b"\n"
        for linea in proceso.stdout.splitlines()
        if b"transaction_timeout" not in linea
    )


def _restaurar(tmp_path: Path, dump: bytes):
    """Artefacto con el volcado + `restaurar_estado_respaldo`, como el runbook."""

    origen = tmp_path / "origen" / "salida"
    (origen / "logs").mkdir(parents=True)
    artefacto = construir_artefacto(
        directorio_salida=origen,
        registro_confirmaciones=None,
        marca=MARCA,
        postgres_dump=dump,
    )
    ruta = tmp_path / "respaldo.tar.gz"
    ruta.write_bytes(artefacto.contenido)
    return restaurar_estado_respaldo(
        artefacto_path=ruta,
        directorio_salida=tmp_path / "destino" / "salida",
        registro_confirmaciones=None,
        postgres_dsn=DSN,
    )


def _evento_restauracion(audit_path: Path) -> dict:
    lineas = audit_path.read_text(encoding="utf-8").strip().splitlines()
    eventos = [json.loads(linea) for linea in lineas]
    return next(e for e in eventos if e["evento"] == "restauracion_respaldo")


def test_respaldo_con_envio_posterior_no_reenvia(esquema, tmp_path) -> None:
    """El caso del contrato: backup → envío posterior → restaurar.

    El respaldo se toma con la emisión real `PENDIENTE`; después el worker
    la ejecuta (la entrega queda asentada `EMITIDA`). Al restaurar, el
    snapshot devuelve la fila a `PENDIENTE`, pero la misma transacción la
    marca `INDETERMINADA`: ningún worker la puede reservar y no hay un
    segundo envío.
    """

    esq = esquema(con_cola=True)
    lote = _lote(esq, "ENVIO1")
    _insertar_emision(esq, lote, estado="PENDIENTE")
    dump = _dump_esquema(esq)

    # Post-respaldo el trabajo corrió de verdad: entregó sus dos correos.
    with psycopg.connect(
        DSN, options=f"-c search_path={esq}", autocommit=True
    ) as conn:
        conn.execute(
            "UPDATE emisiones_certificados SET estado = 'EMITIDA',"
            " terminada_en = now(), retencion_hasta = now(),"
            " total = 2, enviadas = 2 WHERE id_lote = %s",
            (lote,),
        )

    resultado = _restaurar(tmp_path, dump)

    fila = _fila_emision(esq, lote)
    assert fila["estado"] == "INDETERMINADA"
    assert fila["terminada_en"] is not None
    # La reserva se limpia entera y la retención queda NULL, como exigen
    # los CHECK de la cola para el estado indeterminado.
    assert fila["reservada_por"] is None
    assert fila["token_reserva"] is None
    assert fila["reservada_hasta"] is None
    assert fila["retencion_hasta"] is None
    # Cero envíos nuevos: el trabajo ya no existe para la reserva.
    assert _reservables(esq) == []
    assert resultado.emisiones_pg_indeterminadas == 1
    evento = _evento_restauracion(resultado.audit_path)
    assert evento["emisiones_pg_indeterminadas"] == 1
    assert evento["postgres_restaurado"] is True


@pytest.mark.parametrize("estado", ["RESERVADA", "ENVIANDO"])
def test_emision_en_curso_queda_indeterminada(
    esquema, tmp_path, estado: str
) -> None:
    """Reservada o enviando al momento del respaldo: igual de dudosa.

    Una fila `RESERVADA` restaurada conservaría su token y podría cerrarse
    por un worker vivo; una `ENVIANDO` ya pudo mandar correo. Las dos
    pasan a `INDETERMINADA` con la reserva limpiada.
    """

    esq = esquema(con_cola=True)
    lote = _lote(esq, f"CUR-{estado[:4]}")
    _insertar_emision(esq, lote, estado=estado)
    dump = _dump_esquema(esq)

    resultado = _restaurar(tmp_path, dump)

    fila = _fila_emision(esq, lote)
    assert fila["estado"] == "INDETERMINADA"
    assert fila["reservada_por"] is None
    assert fila["token_reserva"] is None
    assert fila["reservada_hasta"] is None
    assert fila["retencion_hasta"] is None
    assert fila["terminada_en"] is not None
    assert _reservables(esq) == []
    assert resultado.emisiones_pg_indeterminadas == 1


def test_terminales_y_demo_se_conservan(esquema, tmp_path) -> None:
    """Lo ya terminado no se marca pendiente ni indeterminado.

    `EMITIDA`, `EMITIDA_PARCIAL`, `FALLIDA`, `INDETERMINADA` y `EXPIRADA`
    son finales: restaurarlas no cambia nada (la `INDETERMINADA` vieja
    conserva su `terminada_en` original, no la del restore). El trabajo
    demo tampoco se toca: sin efectos externos, si se pierde se repide.
    """

    esq = esquema(con_cola=True)
    casos = [
        ("EMITIDA", "real", {"total": 2, "enviadas": 2}),
        ("EMITIDA_PARCIAL", "real", {"total": 2, "enviadas": 1, "fallidas": 1}),
        ("FALLIDA", "real", {"total": 2, "fallidas": 1, "error_codigo": "error_motor"}),
        ("INDETERMINADA", "real", {"total": 2, "enviadas": 1}),
        ("EXPIRADA", "real", {}),
        ("GENERADA_DEMO", "demo", {}),
    ]
    lotes: dict[str, str] = {}
    for indice, (estado, modo, extra) in enumerate(casos):
        lote = _lote(esq, f"TER{indice}")
        _insertar_emision(
            esq, lote, estado=estado, modo=modo, **extra
        )
        lotes[f"{estado}-{modo}"] = lote
    dump = _dump_esquema(esq)
    esperadas = {clave: _fila_emision(esq, lote) for clave, lote in lotes.items()}

    resultado = _restaurar(tmp_path, dump)

    for clave, lote in lotes.items():
        fila = _fila_emision(esq, lote)
        anterior = esperadas[clave]
        assert fila["estado"] == anterior["estado"], clave
        assert fila["terminada_en"] == anterior["terminada_en"], clave
        assert fila["retencion_hasta"] == anterior["retencion_hasta"], clave
        assert fila["enviadas"] == anterior["enviadas"], clave
        assert fila["fallidas"] == anterior["fallidas"], clave
    # La marca no tocó nada: cero filas reconciliadas en esta restauración.
    assert resultado.emisiones_pg_indeterminadas == 0


def test_respaldo_legacy_sin_tabla_emisiones(esquema, tmp_path) -> None:
    """Un respaldo anterior a la migración no tiene la cola: restaura limpio."""

    esq = esquema(con_cola=False)
    with psycopg.connect(
        DSN, options=f"-c search_path={esq}"
    ) as conn:
        assert conn.execute(
            "SELECT count(*) FROM information_schema.tables"
            " WHERE table_schema = %s AND table_name = 'emisiones_certificados'",
            (esq,),
        ).fetchone()[0] == 0
    dump = _dump_esquema(esq)

    resultado = _restaurar(tmp_path, dump)

    assert resultado.emisiones_pg_indeterminadas == 0
    with psycopg.connect(
        DSN, options=f"-c search_path={esq}"
    ) as conn:
        assert conn.execute(
            "SELECT count(*) FROM information_schema.tables"
            " WHERE table_schema = %s AND table_name = 'emisiones_certificados'",
            (esq,),
        ).fetchone()[0] == 0


def test_texto_dentro_del_dump_no_marca_un_esquema_ajeno(esquema, tmp_path) -> None:
    restaurado = esquema(con_cola=True)
    ajeno = esquema(con_cola=True)
    lote_restaurado = _lote(restaurado, "AISLADO1")
    lote_ajeno = _lote(ajeno, "AISLADO2")
    _insertar_emision(restaurado, lote_restaurado, estado="PENDIENTE")
    _insertar_emision(ajeno, lote_ajeno, estado="PENDIENTE")
    anterior = _fila_emision(ajeno, lote_ajeno)
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(f'CREATE TABLE "{restaurado}".texto_de_prueba (texto text)')
        # Es un dato del COPY de pg_dump, no una sentencia para ejecutar.
        conn.execute(
            f'INSERT INTO "{restaurado}".texto_de_prueba VALUES (%s)',
            (f"CREATE TABLE {ajeno}.emisiones_certificados (",),
        )
    dump = _dump_esquema(restaurado)

    resultado = _restaurar(tmp_path, dump)

    assert _fila_emision(restaurado, lote_restaurado)["estado"] == "INDETERMINADA"
    assert _fila_emision(ajeno, lote_ajeno) == anterior
    assert resultado.emisiones_pg_indeterminadas == 1


def test_falla_del_dump_no_deja_estado_parcial(esquema, tmp_path) -> None:
    """Un volcado que falla a mitad no puede dejar la cola a medias.

    La importación y la marca son una sola transacción: si el script aborta,
    la base queda como antes: la tabla y su fila `PENDIENTE` intactas.
    Sin atomicidad la tabla quedaría recreada con otra forma.
    """

    esq = esquema(con_cola=True)
    lote = _lote(esq, "FAIL1")
    _insertar_emision(esq, lote, estado="PENDIENTE")
    dump = (
        f'DROP TABLE IF EXISTS "{esq}".emisiones_certificados;\n'
        f'CREATE TABLE "{esq}".emisiones_certificados (id int);\n'
        f'INSERT INTO "{esq}".emisiones_certificados VALUES (1);\n'
        "SELECT funcion_inexistente_para_fallar();\n"
    ).encode()

    with pytest.raises(RespaldoDiarioError) as exc:
        _restaurar(tmp_path, dump)
    assert exc.value.code == "respaldo_postgres_fallido"

    fila = _fila_emision(esq, lote)
    assert fila["estado"] == "PENDIENTE"
    # La cola conserva su forma real: el DDL inyectado se revirtió entero.
    assert _reservables(esq) == [fila["id_emision"]]


@pytest.mark.parametrize("aprobar_antes", [True, False])
def test_respaldo_sin_trabajo_no_habilita_reenvio(esquema, tmp_path, aprobar_antes) -> None:
    esq = esquema(con_cola=True)
    id_lote = _lote(esq, "SINTRABAJO")
    repo = RepositorioLotes(_fabrica(esq))
    lote = repo.obtener(id_lote)
    if aprobar_antes:
        resultado = repo.decidir(
            id_lote=id_lote, hash_lote=lote.objeto_lote, accion="aprobar",
            validador_hash=hash_correo(CORREO), rol="APROBADOR_CONTENIDO",
            origen_identidad="google", version_agente="0.0.0-test", ahora=AHORA,
        )
        assert resultado.codigo == "aprobada"
    dump = _dump_esquema(esq)
    # El trabajo se creó y emitió después de la copia: la copia no lo conoce.
    _insertar_emision(esq, id_lote, estado="EMITIDA", total=1, enviadas=1)
    resultado = _restaurar(tmp_path, dump)
    fila = _fila_emision(esq, id_lote)
    assert fila["estado"] == "INDETERMINADA"
    assert fila["enviadas"] == 0  # El respaldo no puede afirmar cuántos salieron.
    assert _reservables(esq) == []
    assert resultado.emisiones_pg_indeterminadas == 1
