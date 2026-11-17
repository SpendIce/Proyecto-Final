"""Permiso de ajuste sobre la prosa del canal web (migración 0011).

`completar_trabajo` enlaza la indicación de un ajuste con la revisión que
produjo mediante `UPDATE prosa_transitoria SET id_borrador = ...`. 0005
concedió a `agente1_app` sólo SELECT e INSERT sobre esa tabla, así que en
producción el worker fallaba al completar un ajuste con
`InsufficientPrivilege` y la solicitud quedaba en `AJUSTANDO`
(`worker.py:514` -> `persistencia.py:838`).

La suite de ajuste (`test_canal_web_ajuste.py`) conecta como dueño del
esquema y no ve el permiso. Acá se usa el rol real con `SET ROLE`: las
comprobaciones de privilegio son las de `agente1_app`, sin cambiar la
clave de roles globales que otros tests comparten.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest

from agente1.web.persistencia import RepositorioWeb

DSN = os.environ.get("AGENTE1_POSTGRES_DSN")
MIGRACIONES = Path(__file__).resolve().parent.parent / "migrations"
AHORA = datetime.now(timezone.utc)
MIGRACION_0011 = "0011_permisos_ajuste_prosa"
INDICACION = "más breve"
TEXTO_BASE = "La jornada reunió a estudiantes y docentes en la facultad."
TEXTO_AJUSTADO = "La jornada reunió a estudiantes y docentes."

pytestmark = pytest.mark.skipif(
    not DSN,
    reason="sin AGENTE1_POSTGRES_DSN (servicio de CI o base local)",
)


@pytest.fixture()
def base():
    """Esquema desechable con todas las migraciones y los roles del canal."""
    assert DSN is not None
    esquema = f"test_permisos_{uuid.uuid4().hex[:10]}"
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


def _fabrica(esquema: str, rol: str | None = None):
    """Fábrica de conexiones al esquema, opcionalmente como rol del canal."""

    def abrir():
        conn = psycopg.connect(
            DSN, options=f"-c search_path={esquema}", autocommit=False
        )
        if rol is not None:
            conn.execute(f"SET ROLE {rol}")
            conn.commit()
        return conn

    return abrir


def _solicitud_en_lista(repo: RepositorioWeb) -> tuple[str, str]:
    """Deja una solicitud web con su primera revisión, como el worker real."""
    creada = repo.crear_solicitud(
        idempotency_key=f"web:{uuid.uuid4().hex}",
        solicitante_hash="ab" * 32,
        rol="coordinador_seu",
        tipo_pieza="cronica_de_evento",
        actividad_ref=None,
        descripcion="Pedido sintético de prueba.",
        campos={"pieza": {"titulo": "Jornada sintética"}},
        ahora=AHORA,
    )
    trabajo = repo.tomar_trabajo(worker_id="gen", ahora=AHORA)
    assert trabajo is not None
    id_borrador = repo.completar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=creada.id_solicitud,
        texto_generado=TEXTO_BASE,
        referencia="doc-1",
        doc_ref="doc-1",
        head_revision_id="head-1",
        ahora=AHORA,
    )
    return creada.id_solicitud, id_borrador


def _encolar_ajuste(
    repo: RepositorioWeb, id_solicitud: str, id_borrador_base: str
):
    detalle = repo.obtener(id_solicitud)
    assert detalle is not None
    vigente = next(
        r for r in detalle.revisiones if r.id_borrador == id_borrador_base
    )
    return repo.crear_ajuste(
        idempotency_key=f"ajuste:{uuid.uuid4().hex}",
        id_solicitud=id_solicitud,
        id_borrador_base=id_borrador_base,
        base_output_hash=vigente.output_hash,
        indicacion=INDICACION,
        solicitante_hash="cd" * 32,
        rol="coordinador_seu",
        origen_identidad="demo",
        version_agente="0.0.0-test",
        ahora=AHORA,
    )


def _completar_ajuste(repo: RepositorioWeb, trabajo) -> str:
    return repo.completar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=trabajo.id_solicitud,
        texto_generado=TEXTO_AJUSTADO,
        referencia="doc-1",
        doc_ref="doc-1",
        head_revision_id="head-2",
        texto_documento=TEXTO_AJUSTADO,
        origen="ajuste_generativo",
        id_borrador_base=trabajo.id_borrador_base,
        id_ajuste=trabajo.id_ajuste,
        ahora=AHORA,
    )


def _aplicar_migracion(esquema: str, sufijo: str) -> None:
    archivo = MIGRACIONES / f"{MIGRACION_0011}.{sufijo}.sql"
    with psycopg.connect(
        DSN, options=f"-c search_path={esquema}", autocommit=True
    ) as conn:
        conn.execute(archivo.read_text(encoding="utf-8"))


def _puede_actualizar_id_borrador(esquema: str) -> bool:
    with _fabrica(esquema, "agente1_app")() as conn:
        try:
            with conn.transaction():
                conn.execute(
                    "UPDATE prosa_transitoria SET id_borrador = NULL"
                    " WHERE clase = 'ajuste'"
                )
        except psycopg.errors.InsufficientPrivilege:
            return False
    return True


def test_agente1_app_completa_ajuste_y_enlaza_la_indicacion(base: str) -> None:
    """Con 0011, la revisión nueva declara su base y la indicación queda
    enlazada para el historial. Sin el permiso, el mismo camino falla (ver
    el test siguiente)."""
    repo = RepositorioWeb(_fabrica(base, "agente1_app"))
    id_solicitud, id_base = _solicitud_en_lista(repo)

    resultado = _encolar_ajuste(repo, id_solicitud, id_base)
    assert resultado.codigo == "encolado"
    assert repo.estado_de(id_solicitud) == "AJUSTANDO"

    trabajo = repo.tomar_trabajo(worker_id="w-ajuste", ahora=AHORA)
    assert trabajo is not None
    assert trabajo.clase == "ajuste"
    assert trabajo.indicacion == INDICACION
    assert trabajo.texto_base == TEXTO_BASE

    id_nuevo = _completar_ajuste(repo, trabajo)

    detalle = repo.obtener(id_solicitud)
    assert detalle is not None
    assert detalle.estado_web == "LISTA"
    assert detalle.texto_vigente == TEXTO_AJUSTADO
    assert [r.id_borrador for r in detalle.revisiones] == [id_base, id_nuevo]
    anterior, ajustada = detalle.revisiones
    assert anterior.indicacion is None
    assert ajustada.numero_revision == 2
    assert ajustada.origen == "ajuste_generativo"
    assert ajustada.indicacion == INDICACION

    with _fabrica(base)() as conn:
        enlace = conn.execute(
            "SELECT id_borrador FROM prosa_transitoria"
            " WHERE id_ejecucion = %s AND clase = 'ajuste'",
            (trabajo.id_ejecucion,),
        ).fetchone()
    assert enlace == (id_nuevo,)


def test_sin_el_permiso_completar_ajuste_falla_y_sigue_ajustando(
    base: str,
) -> None:
    """Reproduce la falla de producción: con el grant de 0011 revocado, el
    `completar_trabajo` real aborta y no deja revisión nueva; la solicitud
    sigue en `AJUSTANDO`, que es el estado que veía la SEU."""
    repo = RepositorioWeb(_fabrica(base, "agente1_app"))
    id_solicitud, id_base = _solicitud_en_lista(repo)
    _encolar_ajuste(repo, id_solicitud, id_base)
    trabajo = repo.tomar_trabajo(worker_id="w-ajuste", ahora=AHORA)
    assert trabajo is not None
    assert repo.estado_de(id_solicitud) == "AJUSTANDO"

    _aplicar_migracion(base, "down")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _completar_ajuste(repo, trabajo)

    detalle = repo.obtener(id_solicitud)
    assert detalle is not None
    assert detalle.estado_web == "AJUSTANDO"
    assert detalle.texto_vigente == TEXTO_BASE
    assert [r.id_borrador for r in detalle.revisiones] == [id_base]


def test_agente1_app_no_puede_tocar_texto_hash_ni_borrar_prosa(
    base: str,
) -> None:
    """0011 concede sólo `UPDATE (id_borrador)`: el texto, su hash, las
    demás columnas y el borrado siguen vedados a la app."""
    repo = RepositorioWeb(_fabrica(base, "agente1_app"))
    _solicitud_en_lista(repo)

    sentencias = (
        "UPDATE prosa_transitoria SET texto = NULL"
        " WHERE clase = 'generado'",
        "UPDATE prosa_transitoria SET texto_hash = repeat('0', 64)"
        " WHERE clase = 'generado'",
        "UPDATE prosa_transitoria SET id_solicitud = id_solicitud"
        " WHERE clase = 'generado'",
        "DELETE FROM prosa_transitoria WHERE clase = 'generado'",
        "TRUNCATE prosa_transitoria",
    )
    with _fabrica(base, "agente1_app")() as conn:
        for sentencia in sentencias:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with conn.transaction():
                    conn.execute(sentencia)


def test_agente1_app_no_modifica_ni_borra_la_auditoria(base: str) -> None:
    """La auditoría conserva el reparto de 0005: la app sólo inserta."""
    repo = RepositorioWeb(_fabrica(base, "agente1_app"))
    _solicitud_en_lista(repo)

    with _fabrica(base, "agente1_app")() as conn:
        for sentencia in (
            "UPDATE eventos_ejecucion SET tipo = 'alterado'",
            "DELETE FROM eventos_ejecucion",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with conn.transaction():
                    conn.execute(sentencia)


def test_mantenimiento_conserva_la_propiedad_y_la_purga(base: str) -> None:
    """0011 no cambia el dueño de la tabla ni el permiso de purga."""
    repo = RepositorioWeb(_fabrica(base, "agente1_app"))
    id_solicitud, _ = _solicitud_en_lista(repo)

    with _fabrica(base)() as conn:
        duenio = conn.execute(
            "SELECT pg_get_userbyid(relowner) FROM pg_class"
            " WHERE oid = 'prosa_transitoria'::regclass"
        ).fetchone()[0]
    assert duenio == "agente1_mantenimiento"

    with _fabrica(base, "agente1_app")() as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with conn.transaction():
                conn.execute(
                    "ALTER TABLE prosa_transitoria OWNER TO agente1_app"
                )
        with conn.transaction():
            conn.execute(
                "UPDATE solicitudes SET estado_web = 'APROBADA'"
                " WHERE id_solicitud = %s",
                (id_solicitud,),
            )

    repo_mant = RepositorioWeb(_fabrica(base, "agente1_mantenimiento"))
    assert repo_mant.purgar_prosa(ahora=AHORA) >= 2
    with _fabrica(base)() as conn:
        sin_texto = conn.execute(
            "SELECT count(*) FROM prosa_transitoria"
            " WHERE id_solicitud = %s AND texto IS NOT NULL",
            (id_solicitud,),
        ).fetchone()[0]
    assert sin_texto == 0


def test_down_revierte_el_permiso_y_up_lo_restituye(base: str) -> None:
    """El `down` vuelve al reparto de 0010 y el `up` lo recompone."""
    assert _puede_actualizar_id_borrador(base)
    _aplicar_migracion(base, "down")
    assert not _puede_actualizar_id_borrador(base)
    _aplicar_migracion(base, "up")
    assert _puede_actualizar_id_borrador(base)
