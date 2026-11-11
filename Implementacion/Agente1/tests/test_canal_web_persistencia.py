"""Persistencia del canal web contra PostgreSQL real (ADR 0016, #149).

Cubre las pruebas del ADR que corresponden a esta base: idempotencia de la
entrada (prueba 3 aplicada a crear solicitudes), reserva con plazo y
recuperación sin duplicar el Doc (prueba 1), vencimiento, purga, VACUUM y
exclusión de la prosa del respaldo (prueba 5), restauración determinística
(6), roles reales de la base (7) y trazabilidad sin prosa (9). Las pruebas
2 y 4 (decisiones de revisión) son del issue #153.

Los roles se prueban como tales: la suite conecta con `agente1_app` y con
`agente1_mantenimiento` de verdad, no como superusuario — así los permisos
que se prueban son los del despliegue. Los métodos de sólo-lectura que la
suite necesita viven acá como helpers, no en el repositorio de producción.

Cada prueba corre sobre un esquema desechable del mismo cluster que usa la
suite de migraciones (`AGENTE1_POSTGRES_DSN`, servicio de CI o local);
sin DSN se salta sin romper la determinística del resto.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest

from agente1.respaldo import entorno_libpq
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
CLAVES_ROLES = {
    "agente1_app": "prueba-web-app",
    "agente1_mantenimiento": "prueba-web-mant",
}


@pytest.fixture()
def base():
    """Esquema desechable con las migraciones 0001 a 0005 aplicadas.

    Además deja a los dos roles con clave y `USAGE` del esquema, como el
    despliegue haría en el suyo: las pruebas de rol conectan con ellos.
    """
    esquema = f"test_web_{uuid.uuid4().hex[:10]}"
    admin = psycopg.connect(DSN, autocommit=True)
    admin.execute(f'CREATE SCHEMA "{esquema}"')
    try:
        with psycopg.connect(
            DSN, options=f"-c search_path={esquema}"
        ) as conn:
            for up in sorted(MIGRACIONES.glob("*.up.sql")):
                conn.execute(up.read_text(encoding="utf-8"))
            for rol, clave in CLAVES_ROLES.items():
                conn.execute(
                    f'GRANT USAGE ON SCHEMA "{esquema}" TO {rol}'
                )
                conn.execute(f"ALTER ROLE {rol} PASSWORD '{clave}'")
        yield esquema
    finally:
        admin.execute(f'DROP SCHEMA "{esquema}" CASCADE')
        admin.close()


def _dsn_rol(rol: str, *, esquema: str | None = None) -> str:
    """El DSN de la suite apuntando a un rol del canal, con su clave.

    `esquema` fija `search_path` por `options` (lo que el despliegue
    resuelve con el esquema propio): hace falta para los subprocesos
    libpq y para el VACUUM no calificado.
    """
    info = psycopg.conninfo.conninfo_to_dict(DSN)
    info["user"] = rol
    info["password"] = CLAVES_ROLES[rol]
    if esquema is not None:
        info["options"] = f"-c search_path={esquema}"
    return psycopg.conninfo.make_conninfo(**info)


def _fabrica(esquema: str, rol: str | None = None):
    dsn = DSN if rol is None else _dsn_rol(rol)
    return lambda: psycopg.connect(
        dsn, options=f"-c search_path={esquema}", autocommit=False
    )


# ---------- helpers de test (antes métodos de sólo-prueba del repo) ----------


def _prosa_textos(esquema: str, id_solicitud: str) -> list[str | None]:
    with psycopg.connect(
        DSN, options=f"-c search_path={esquema}"
    ) as conn:
        return [
            f[0]
            for f in conn.execute(
                "SELECT texto FROM prosa_transitoria"
                " WHERE id_solicitud = %s ORDER BY secuencia",
                (id_solicitud,),
            ).fetchall()
        ]


def _ejecucion_estado(esquema: str, id_ejecucion: str) -> tuple | None:
    with psycopg.connect(
        DSN, options=f"-c search_path={esquema}"
    ) as conn:
        return conn.execute(
            "SELECT estado, resultado, reservada_hasta, output_hash"
            " FROM ejecuciones WHERE id_ejecucion = %s",
            (id_ejecucion,),
        ).fetchone()


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
    assert retomado.intentos == 2
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


def test_reintentos_acotados_terminan_en_error(
    base: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """El límite de reintentos del worker cierra la ejecución FALLIDA y
    deja la solicitud `ERROR`, visible en la bandeja — sin retry eterno.

    La excepción inesperada se provoca desde fuera del pipeline (éste
    convierte sus fallas en resultados, que cierran de inmediato): una
    caída de infraestructura llega al `except Exception` de la corrida.
    """
    from agente1.web.worker import DestinoPorMarcaMemoria, correr_una_vez

    def genera_que_cae(trabajo, **_kwargs):
        raise RuntimeError("infraestructura caída")

    monkeypatch.setattr(
        "agente1.web.worker._generar_pieza", genera_que_cae
    )
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:reint1")
    for esperado in (1, 2, 3):
        trabajo = correr_una_vez(
            repositorio=repo,
            worker_id="w1",
            fuente=_fuente_vacia(),
            generator=FakeGen(),
            directorio_salida=tmp_path,
            destino=DestinoPorMarcaMemoria(),
            max_intentos=3,
        )
        assert trabajo is not None
        assert trabajo.intentos == esperado
        # La reserva de la corrida caída vence por tiempo; se vence a mano.
        with _fabrica(base)() as conn:
            conn.execute(
                "UPDATE ejecuciones SET reservada_hasta = %s"
                " WHERE id_ejecucion = %s",
                (AHORA - timedelta(seconds=1), creada.id_ejecucion),
            )
            conn.commit()
    assert repo.estado_de(creada.id_solicitud) == "ERROR"
    ejecucion = _ejecucion_estado(base, creada.id_ejecucion)
    assert ejecucion[0] == "FALLIDA"
    assert ejecucion[1] == "error_generacion"


class FakeGen:
    """Generador mínimo: la ruta `extrae_y_confirma` no lo invoca."""

    modelo = "fake-ok"

    def generate(self, prompt: str, num_predict: int = 0) -> str:
        return "Texto confirmado por la persona."


def _fuente_vacia():
    class Fuente:
        def obtener(self, id_actividad):
            raise KeyError(id_actividad)

        def enumerar(self):
            return []

    return Fuente()


def test_caida_sin_duplicar_documento(
    base: str, tmp_path: Path
) -> None:
    """Prueba 1 aplicada al destino: si la corrida muere entre el Doc y el
    asiento, la siguiente reutiliza el Doc por la marca de la solicitud."""
    from agente1.web.worker import (
        DestinoPorMarcaMemoria,
        _generar_pieza,
        correr_una_vez,
    )

    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:doc1")
    destino = DestinoPorMarcaMemoria()

    # Primera corrida interrumpida tras crear el Doc: la generación corre
    # pero el asiento nunca llega (el proceso murió en el medio).
    trabajo = repo.tomar_trabajo(worker_id="w1")
    _generar_pieza(
        trabajo,
        fuente=_fuente_vacia(),
        generator=FakeGen(),
        directorio_salida=tmp_path,
        destino=destino,
    )
    assert len(destino.docs) == 1
    with _fabrica(base)() as conn:
        conn.execute(
            "UPDATE ejecuciones SET reservada_hasta = %s"
            " WHERE id_ejecucion = %s",
            (AHORA - timedelta(seconds=1), trabajo.id_ejecucion),
        )
        conn.commit()

    # Segunda corrida: retoma la misma ejecución y el destino encuentra el
    # Doc por la marca — no crea otro.
    retomado = correr_una_vez(
        repositorio=repo,
        worker_id="w2",
        fuente=_fuente_vacia(),
        generator=FakeGen(),
        directorio_salida=tmp_path,
        destino=destino,
    )
    assert retomado is not None
    assert len(destino.docs) == 1
    assert creada.id_solicitud in destino.docs
    assert repo.estado_de(creada.id_solicitud) == "LISTA"


def test_vencida_y_purga_repartidas_por_rol(base: str) -> None:
    """Pruebas 5 y 7 con los roles reales: `agente1_app` vence y
    `agente1_mantenimiento` purga — ninguno puede hacer la parte del otro."""
    repo = RepositorioWeb(_fabrica(base))
    aprobada = _crear(repo, "web:p1")
    vencida = _crear(repo, "web:p2", ahora=AHORA - timedelta(days=31))
    with _fabrica(base)() as conn:
        conn.execute(
            "UPDATE solicitudes SET estado_web = 'APROBADA'"
            " WHERE id_solicitud = %s",
            (aprobada.id_solicitud,),
        )
        conn.commit()

    repo_app = RepositorioWeb(_fabrica(base, rol="agente1_app"))
    vencidas = repo_app.vencer_solicitudes(ahora=AHORA)
    assert vencidas == 1
    assert repo.estado_de(vencida.id_solicitud) == "VENCIDA"

    # El rol de la app no puede vaciar la prosa: no es su permiso.
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        repo_app.purgar_prosa(ahora=AHORA)

    repo_mant = RepositorioWeb(
        _fabrica(base, rol="agente1_mantenimiento")
    )
    purgadas = repo_mant.purgar_prosa(ahora=AHORA)
    assert purgadas >= 2
    # Tras la purga: los textos ya no están; quedan clase, hash y marca.
    with _fabrica(base)() as conn:
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


def test_purga_vacuum_y_respaldo_sin_prosa(base: str) -> None:
    """Prueba 5 completa: purga como mantenimiento, VACUUM verificable y
    el volcado del día sin la prosa purgada."""
    if shutil.which("pg_dump") is None:
        pytest.skip("sin pg_dump en el entorno")
    repo = RepositorioWeb(_fabrica(base))
    marcador = "PROSA-PURGABLE-" + uuid.uuid4().hex[:8]
    creada = _crear(repo, "web:pv1", descripcion=marcador)
    with _fabrica(base)() as conn:
        conn.execute(
            "UPDATE solicitudes SET estado_web = 'APROBADA'"
            " WHERE id_solicitud = %s",
            (creada.id_solicitud,),
        )
        conn.commit()

    # La purga corre con el rol de mantenimiento, como en el scheduler.
    repo_mant = RepositorioWeb(
        _fabrica(base, rol="agente1_mantenimiento")
    )
    repo_mant.purgar_prosa(ahora=AHORA)

    # VACUUM sobre la tabla, con el DSN del rol dueño — verificable por
    # la estadística del catálogo (last_vacuum queda asentada al correrlo;
    # la publicación del stats collector puede tardar un instante).
    RepositorioWeb.vaciar_prosa(
        _dsn_rol("agente1_mantenimiento", esquema=base)
    )
    import time

    vacuum_marcado = False
    for _ in range(40):
        with _fabrica(base)() as conn:
            fila = conn.execute(
                "SELECT last_vacuum FROM pg_stat_user_tables"
                " WHERE schemaname = %s AND relname = 'prosa_transitoria'",
                (base,),
            ).fetchone()
        if fila and fila[0] is not None:
            vacuum_marcado = True
            break
        time.sleep(0.25)
    assert vacuum_marcado
    assert all(
        t is None for t in _prosa_textos(base, creada.id_solicitud)
    )

    # El volcado del día del esquema no contiene la prosa purgada.
    proceso = subprocess.run(
        [
            shutil.which("pg_dump"),
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "-n",
            base,
        ],
        capture_output=True,
        env={**os.environ, **entorno_libpq(_dsn_rol("agente1_app"))},
    )
    assert proceso.returncode == 0, proceso.stderr.decode()
    assert marcador.encode() not in proceso.stdout


def test_restauracion_deterministica(base: str) -> None:
    """Prueba 6: restaurar el volcado devuelve los estados al del respaldo,
    sin indeterminados nuevos — el `--clean --if-exists` reemplaza, no suma."""
    if shutil.which("pg_dump") is None or shutil.which("psql") is None:
        pytest.skip("sin pg_dump/psql en el entorno")
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:rest1")
    # Estado respaldado: la solicitud abierta recién creada.
    dump = subprocess.run(
        [
            shutil.which("pg_dump"),
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "-n",
            base,
        ],
        capture_output=True,
        env={**os.environ, **entorno_libpq(DSN)},
    ).stdout
    assert creada.id_solicitud.encode() in dump
    # El cliente pg_dump 18 emite `SET transaction_timeout`, GUC que el
    # servidor 16 no conoce: en producción el cliente es 16 (Dockerfile);
    # acá se depura la línea para que la restauración corra limpia.
    dump = b"".join(
        linea + b"\n"
        for linea in dump.splitlines()
        if b"transaction_timeout" not in linea
    )

    # El estado avanza post-respaldo: genera y termina la pieza.
    trabajo = repo.tomar_trabajo(worker_id="w1")
    repo.completar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=creada.id_solicitud,
        texto_generado="Texto post-respaldo.",
        referencia="ref",
        doc_ref="doc/x",
        head_revision_id="h",
    )
    assert repo.estado_de(creada.id_solicitud) == "LISTA"

    # Restaurar el volcado devuelve el esquema a como estaba.
    with tempfile.NamedTemporaryFile(suffix=".pgdump") as temporal:
        temporal.write(dump)
        temporal.flush()
        proceso = subprocess.run(
            [
                shutil.which("psql"),
                "-X",
                "-q",
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                temporal.name,
            ],
            capture_output=True,
            env={**os.environ, **entorno_libpq(DSN)},
        )
    assert proceso.returncode == 0, proceso.stderr.decode()
    # El estado vuelve al del respaldo; no aparecen indeterminados nuevos.
    # La ejecución queda `INICIADA`: así estaba asentada al volcar, antes
    # de la primera reserva.
    assert repo.estado_de(creada.id_solicitud) == "EN_COLA"
    ejecucion = _ejecucion_estado(base, creada.id_ejecucion)
    assert ejecucion[0] == "INICIADA"
    # Y la ejecución vuelve a ser tomable, como en el momento del respaldo.
    assert repo.tomar_trabajo(worker_id="w9") is not None


def test_auditoria_solo_inserta(base: str) -> None:
    """Prueba 7: `agente1_app` no puede modificar ni borrar eventos."""
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:a1")
    # Conexión real con el rol de la aplicación (sin superuser del DSN).
    with psycopg.connect(
        _dsn_rol("agente1_app"),
        options=f"-c search_path={base}",
        autocommit=False,
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
        conn.rollback()
        # Tampoco vacía la prosa: la purga es del rol de mantenimiento.
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "UPDATE prosa_transitoria SET texto = NULL"
            )
        conn.rollback()


def test_mantenimiento_purga_y_no_escribe_ciclo(base: str) -> None:
    """`agente1_mantenimiento` vacía la prosa y asienta el evento, pero no
    escribe el ciclo de vida de la solicitud."""
    repo = RepositorioWeb(_fabrica(base))
    _crear(repo, "web:m1")
    repo_mant = RepositorioWeb(
        _fabrica(base, rol="agente1_mantenimiento")
    )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        repo_mant.vencer_solicitudes(ahora=AHORA)
    # Purga sí, como dueña de la tabla.
    assert repo_mant.purgar_prosa(ahora=AHORA) >= 0


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
