"""Persistencia del canal web contra PostgreSQL real (ADR 0016, #149).

Cubre las pruebas del ADR que correspondan a esta base: idempotencia de la
entrada (prueba 3 aplicada a crear solicitudes), reserva con plazo y
recuperación del trabajo tras una caída (prueba 1), vencimiento de
solicitudes inactivas y purga de prosa transitoria (pruebas 5 y 9) y las
restricciones del rol de aplicación `agente1_app` sobre la auditoría
(prueba 7). Las pruebas 2 y 4 (decisiones de revisión) son del issue #153.

Cada prueba corre sobre un esquema desechable del mismo cluster que usa la
suite de migraciones (`AGENTE1_POSTGRES_DSN`, servicio de CI o local);
sin DSN se salta sin romper la determinística del resto.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest

from agente1.web.persistencia import (
    ConflictoIdempotencia,
    RepositorioWeb,
)

DSN = os.environ.get("AGENTE1_POSTGRES_DSN")
MIGRACIONES = Path(__file__).resolve().parent.parent / "migrations"

pytestmark = pytest.mark.skipif(
    not DSN,
    reason="sin AGENTE1_POSTGRES_DSN (servicio de CI o base local)",
)

# Pasado real: las tablas rechazan marcas de tiempo futuras (trigger del
# esquema del spike). El `now` del import queda unos milisegundos atrás.
AHORA = datetime.now(timezone.utc)
CAMPOS = {
    "pieza": {"titulo": "Título sintético", "cuerpo": "Texto sintético."},
    "pedido": {"publicos": ["alumnos_ingenieria"], "area_id": "fie"},
}


@pytest.fixture()
def base():
    """Esquema desechable con las migraciones 0001 a 0005 aplicadas."""
    esquema = f"test_web_{uuid.uuid4().hex[:10]}"
    admin = psycopg.connect(DSN, autocommit=True)
    admin.execute(f'CREATE SCHEMA "{esquema}"')
    try:
        with psycopg.connect(
            DSN, options=f"-c search_path={esquema}"
        ) as conn:
            for up in sorted(MIGRACIONES.glob("*.up.sql")):
                conn.execute(up.read_text(encoding="utf-8"))
        yield esquema
    finally:
        admin.execute(f'DROP SCHEMA "{esquema}" CASCADE')
        admin.close()


def _fabrica(esquema: str):
    return lambda: psycopg.connect(
        DSN, options=f"-c search_path={esquema}", autocommit=False
    )


def _crear(repo: RepositorioWeb, llave: str, **kwargs):
    datos = {
        "idempotency_key": llave,
        "solicitante_hash": "ab" * 32,
        "rol": "coordinador_seu",
        "tipo_pieza": "cronica_de_evento",
        "actividad_ref": None,
        "descripcion": "Descripción sintética del pedido.",
        "campos": CAMPOS,
        "ahora": AHORA,
    }
    datos.update(kwargs)
    return repo.crear_solicitud(**datos)


def test_creacion_idempotente(base: str) -> None:
    """Prueba 3 (aplicada a crear): doble envío con la misma llave es una
    sola solicitud; la misma llave con otra firma es conflicto."""
    repo = RepositorioWeb(_fabrica(base))
    primera = _crear(repo, "web:k1")
    assert primera.creada
    segunda = _crear(repo, "web:k1")
    assert not segunda.creada
    assert segunda.id_solicitud == primera.id_solicitud
    assert segunda.id_ejecucion == primera.id_ejecucion
    with pytest.raises(ConflictoIdempotencia):
        _crear(repo, "web:k1", descripcion="otra cosa")


def test_bandeja_y_detalle(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:b1")
    items = repo.bandeja()
    assert [i.id_solicitud for i in items] == [creada.id_solicitud]
    assert items[0].estado_web == "EN_COLA"
    assert items[0].titulo == "Título sintético"
    detalle = repo.obtener(creada.id_solicitud)
    assert detalle is not None
    assert detalle.descripcion == "Descripción sintética del pedido."
    assert detalle.campos["pieza"]["titulo"] == "Título sintético"
    assert repo.obtener("web-ajena") is None
    assert repo.estado_de(creada.id_solicitud) == "EN_COLA"


def test_reserva_con_plazo_y_recuperacion(base: str) -> None:
    """Prueba 1: si el worker cae tras reservar, la ejecución vuelve a ser
    tomable cuando `reservada_hasta` vence, sin duplicar la pieza."""
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:r1")
    trabajo = repo.tomar_trabajo(worker_id="w1", plazo_segundos=300)
    assert trabajo is not None
    assert trabajo.id_ejecucion == creada.id_ejecucion
    # Reserva vigente: otro worker no la toma.
    assert repo.tomar_trabajo(worker_id="w2") is None
    assert repo.estado_de(creada.id_solicitud) == "GENERANDO"
    # El worker cayó: vence la reserva y otro la retoma con su prosa.
    with _fabrica(base)() as conn:
        conn.execute(
            "UPDATE ejecuciones SET reservada_hasta = %s"
            " WHERE id_ejecucion = %s",
            (AHORA - timedelta(seconds=1), trabajo.id_ejecucion),
        )
        conn.commit()
    retomado = repo.tomar_trabajo(worker_id="w2")
    assert retomado is not None
    assert retomado.id_ejecucion == trabajo.id_ejecucion
    assert retomado.descripcion == "Descripción sintética del pedido."
    assert retomado.campos["pieza"]["titulo"] == "Título sintético"
    id_borrador = repo.completar_trabajo(
        id_ejecucion=retomado.id_ejecucion,
        id_solicitud=retomado.id_solicitud,
        texto_generado="Texto generado sintético.",
        referencia="referencia-sintetica",
        doc_ref="doc/1",
        head_revision_id="rev-1",
    )
    assert repo.estado_de(creada.id_solicitud) == "LISTA"
    detalle = repo.obtener(creada.id_solicitud)
    assert detalle.revisiones[0].id_borrador == id_borrador
    assert detalle.revisiones[0].numero_revision == 1
    assert detalle.texto_generado == "Texto generado sintético."
    # No queda trabajo tomable.
    assert repo.tomar_trabajo(worker_id="w3") is None


def test_fallo_marca_error(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:f1")
    trabajo = repo.tomar_trabajo(worker_id="w1")
    repo.fallar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=creada.id_solicitud,
        error_code="generator_unavailable",
    )
    assert repo.estado_de(creada.id_solicitud) == "ERROR"


def test_vencida_y_purga_de_prosa(base: str) -> None:
    """Pruebas 5 y 9: la inactiva vence tras 30 días; al cierre se vacía
    la prosa transitoria y quedan sólo clase, hash y marcas."""
    repo = RepositorioWeb(_fabrica(base))
    # Aprobada ayer y abierta vieja (vence).
    aprobada = _crear(repo, "web:p1")
    vencida = _crear(
        repo, "web:p2", ahora=AHORA - timedelta(days=31)
    )
    fabrica = _fabrica(base)
    with fabrica() as conn:
        conn.execute(
            "UPDATE solicitudes SET estado_web = 'APROBADA'"
            " WHERE id_solicitud = %s",
            (aprobada.id_solicitud,),
        )
        conn.commit()
    resultado = repo.vencer_y_purgar(ahora=AHORA)
    assert resultado.vencidas == 1
    assert resultado.purgadas >= 2
    assert repo.estado_de(vencida.id_solicitud) == "VENCIDA"
    # Tras la purga: los textos ya no están en la base; queda el hash.
    with fabrica() as conn:
        filas = conn.execute(
            "SELECT p.clase, p.texto, p.texto_hash, p.purgada_en"
            " FROM prosa_transitoria p"
            " JOIN solicitudes s ON s.id_solicitud = p.id_solicitud"
            " WHERE s.canal = 'web'"
        ).fetchall()
    assert all(texto is None for _, texto, _, _ in filas)
    assert all(h for _, _, h, _ in filas)
    assert all(p for _, _, _, p in filas)
    detalle = repo.obtener(aprobada.id_solicitud)
    assert detalle.descripcion is None
    assert detalle.campos == {}


def test_auditoria_solo_inserta(base: str) -> None:
    """Prueba 7: `agente1_app` no puede modificar ni borrar eventos."""
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:a1")
    fabrica = _fabrica(base)
    with fabrica() as conn:
        # En `public` el rol hereda USAGE de PUBLIC; en el esquema de la
        # prueba hay que dárselo como haría el despliegue en otro esquema.
        conn.execute(f'GRANT USAGE ON SCHEMA "{base}" TO agente1_app')
        conn.execute("ALTER ROLE agente1_app PASSWORD 'prueba-web'")
        conn.commit()
    # Conexión real con el rol de la aplicación (sin superuser del DSN).
    info = psycopg.conninfo.conninfo_to_dict(DSN)
    info["user"] = "agente1_app"
    info["password"] = "prueba-web"
    dsn_app = psycopg.conninfo.make_conninfo(**info)
    with psycopg.connect(
        dsn_app, options=f"-c search_path={base}", autocommit=False
    ) as conn:
        # SELECT e INSERT funcionan: es su trabajo.
        conn.execute("SELECT count(*) FROM eventos_ejecucion").fetchone()
        conn.execute(
            "INSERT INTO eventos_ejecucion (id_ejecucion, tipo, ocurrido_en)"
            " VALUES (%s, 'reserva_tomada', now())",
            (creada.id_ejecucion,),
        )
        conn.rollback()
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "UPDATE eventos_ejecucion SET tipo = 'x'"
                " WHERE id_ejecucion = %s",
                (creada.id_ejecucion,),
            )
        conn.rollback()
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "DELETE FROM eventos_ejecucion WHERE id_ejecucion = %s",
                (creada.id_ejecucion,),
            )


def test_no_hay_prosa_en_trazabilidad(base: str) -> None:
    """Prueba 9: la trazabilidad tiene hashes y metadatos, nunca texto."""
    repo = RepositorioWeb(_fabrica(base))
    texto_marcador = "PROSA-QUE-NO-DEBE-QUEDAR-" + uuid.uuid4().hex[:8]
    creada = _crear(repo, "web:t1", descripcion=texto_marcador)
    trabajo = repo.tomar_trabajo(worker_id="w1")
    repo.completar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=creada.id_solicitud,
        texto_generado=texto_marcador,
        referencia="ref",
        doc_ref=None,
        head_revision_id=None,
    )
    fabrica = _fabrica(base)
    with fabrica() as conn:
        conn.execute(
            "UPDATE solicitudes SET estado_web = 'APROBADA'"
            " WHERE id_solicitud = %s",
            (creada.id_solicitud,),
        )
        conn.commit()
    repo.vencer_y_purgar()
    with fabrica() as conn:
        for tabla in (
            "solicitudes",
            "ejecuciones",
            "borradores",
            "eventos_ejecucion",
            "prosa_transitoria",
        ):
            filas = conn.execute(
                f"SELECT * FROM {tabla} LIMIT 500"
            ).fetchall()
            for fila in filas:
                for celda in fila:
                    assert texto_marcador not in str(celda)


def test_roles_creados_por_migracion(base: str) -> None:
    """Los roles de BD del canal existen tras correr 0005."""
    with psycopg.connect(DSN, autocommit=True) as conn:
        roles = {
            r[0]
            for r in conn.execute(
                "SELECT rolname FROM pg_roles"
                " WHERE rolname IN ('agente1_app','agente1_mantenimiento')"
            ).fetchall()
        }
    assert roles == {"agente1_app", "agente1_mantenimiento"}


def test_json_campos_redondea(base: str) -> None:
    """`campos` viaja como JSONB y vuelve íntegro al detalle."""
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:j1")
    detalle = repo.obtener(creada.id_solicitud)
    assert json.loads(json.dumps(detalle.campos)) == detalle.campos
    assert detalle.campos == CAMPOS
