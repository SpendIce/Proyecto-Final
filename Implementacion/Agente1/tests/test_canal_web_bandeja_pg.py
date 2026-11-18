"""Bandeja: archivar, eliminar y reintentar, contra PostgreSQL real (ADR 0023).

Sigue el patrón de `test_canal_web_persistencia.py`: esquema desechable con
todas las migraciones aplicadas —0013 incluida— y los dos roles del canal
conectando de verdad. Los estados que no llegan por un método del
repositorio (por ejemplo `DESCARTADA` para probar la marca) se fijan con
SQL directo: las transiciones tienen sus propias pruebas; acá se prueba
la marca y lo que la bandeja deja ver.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest

from agente1.certificados_emision import PersonaCierre
from agente1.web.certificados_web import (
    EMISION_TERMINAL,
    ESTADO_PENDIENTE,
    RepositorioLotes,
)
from agente1.web.persistencia import (
    MAX_REINTENTOS,
    RepositorioWeb,
)

DSN = os.environ.get("AGENTE1_POSTGRES_DSN")
MIGRACIONES = Path(__file__).resolve().parent.parent / "migrations"

pytestmark = pytest.mark.skipif(
    not DSN,
    reason="sin AGENTE1_POSTGRES_DSN (servicio de CI o base local)",
)

AHORA = datetime.now(timezone.utc)
CAMPOS = {
    "pieza": {"titulo": "Título sintético", "cuerpo": "Texto sintético."},
    "pedido": {"publicos": ["alumnos_ingenieria"], "area_id": "fie"},
}
PERSONAS = (
    PersonaCierre(
        nombre="Persona",
        apellido="Ficticia",
        dni="90000001",
        mail="persona@example.invalid",
        tratamiento="Sr.",
        condicion="aprobacion",
    ),
)
ACTIVIDAD = {
    "id_actividad": "BANDEJA-001",
    "titulo": "Actividad ficticia de la bandeja",
    "duracion_horas": "2",
    "modalidad": "virtual",
    "fecha_inicio": "2026-11-18",
    "organiza": "Organizador ficticio",
}


@pytest.fixture()
def base():
    """Esquema desechable con todas las migraciones aplicadas."""
    esquema = f"test_bandeja_{uuid.uuid4().hex[:10]}"
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


def _sql(esquema: str, consulta: str, parametros: tuple = ()) -> list:
    with psycopg.connect(
        DSN, options=f"-c search_path={esquema}"
    ) as conn:
        return conn.execute(consulta, parametros).fetchall()


def _ejecutar(esquema: str, consulta: str, parametros: tuple = ()) -> None:
    with psycopg.connect(
        DSN, options=f"-c search_path={esquema}"
    ) as conn:
        conn.execute(consulta, parametros)
        conn.commit()


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


def _fijar_estado(esquema: str, id_solicitud: str, estado: str) -> None:
    """Fija `estado_web` directo, para probar la marca sin la transición."""
    _ejecutar(
        esquema,
        "UPDATE solicitudes SET estado_web = %s WHERE id_solicitud = %s",
        (estado, id_solicitud),
    )


# ---------- migración 0013 ----------


def test_migracion_0013_agrega_marcas_y_permiso_puntual() -> None:
    """El `up` declara las dos marcas con su orden temporal y el `down`
    las quita; el permiso de `lotes_certificados` es por columna, como
    0010 lo estableció para el resto."""
    up = (
        MIGRACIONES / "0013_bandeja_archivar_y_eliminar.up.sql"
    ).read_text(encoding="utf-8")
    down = (
        MIGRACIONES / "0013_bandeja_archivar_y_eliminar.down.sql"
    ).read_text(encoding="utf-8")

    assert "ADD COLUMN archivada_en TIMESTAMPTZ" in up
    assert "ADD COLUMN eliminada_en TIMESTAMPTZ" in up
    assert (
        "CHECK (archivada_en IS NULL OR archivada_en >= creada_en)" in up
    )
    assert (
        "CHECK (eliminada_en IS NULL OR eliminada_en >= creada_en)" in up
    )
    assert (
        "GRANT UPDATE (archivada_en) ON lotes_certificados"
        " TO agente1_app" in up
    )
    assert "DROP COLUMN archivada_en" in down
    assert "DROP COLUMN eliminada_en" in down


# ---------- piezas: archivar, desarchivar, eliminar ----------


def test_bandeja_muestra_marcas_y_oculta_eliminadas(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    viva = _crear(repo, "web:viva")
    archivada = _crear(repo, "web:archivada")
    eliminada = _crear(repo, "web:eliminada")
    _fijar_estado(base, archivada.id_solicitud, "DESCARTADA")
    _fijar_estado(base, eliminada.id_solicitud, "ERROR")

    assert repo.archivar_solicitud(
        id_solicitud=archivada.id_solicitud, ahora=AHORA
    ) == "archivada"
    assert repo.eliminar_solicitud(
        id_solicitud=eliminada.id_solicitud, ahora=AHORA
    ) == "eliminada"

    items = repo.bandeja()
    # La eliminada no sale en ninguna vista; la archivada viaja marcada
    # para que la interfaz la muestre sólo en «Archivadas».
    ids = [i.id_solicitud for i in items]
    assert viva.id_solicitud in ids
    assert archivada.id_solicitud in ids
    assert eliminada.id_solicitud not in ids
    por_id = {i.id_solicitud: i for i in items}
    assert por_id[archivada.id_solicitud].archivada_en is not None
    assert por_id[viva.id_solicitud].archivada_en is None
    # El canal y el dueño viajan para que la ruta decida permisos.
    assert por_id[viva.id_solicitud].canal == "web"
    assert por_id[viva.id_solicitud].solicitante_hash == "ab" * 32


@pytest.mark.parametrize(
    "estado", ["APROBADA", "DESCARTADA", "VENCIDA", "ERROR"]
)
def test_archivar_acepta_todo_lo_resuelto(base: str, estado: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, f"web:arch-{estado}")
    _fijar_estado(base, creada.id_solicitud, estado)
    assert repo.archivar_solicitud(
        id_solicitud=creada.id_solicitud, ahora=AHORA
    ) == "archivada"
    # Reenvío idempotente.
    assert repo.archivar_solicitud(id_solicitud=creada.id_solicitud) == (
        "ya_archivada"
    )
    assert repo.desarchivar_solicitud(
        id_solicitud=creada.id_solicitud
    ) == "desarchivada"
    assert repo.desarchivar_solicitud(
        id_solicitud=creada.id_solicitud
    ) == "sin_marca"


@pytest.mark.parametrize("estado", ["EN_COLA", "GENERANDO", "AJUSTANDO", "LISTA"])
def test_archivar_rechaza_lo_que_sigue_vivo(base: str, estado: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, f"web:vivo-{estado}")
    _fijar_estado(base, creada.id_solicitud, estado)
    assert repo.archivar_solicitud(id_solicitud=creada.id_solicitud) == (
        "no_archivable"
    )
    assert repo.eliminar_solicitud(id_solicitud=creada.id_solicitud) == (
        "no_eliminable"
    )
    assert repo.archivar_solicitud(id_solicitud="web-ajena") == (
        "inexistente"
    )


def test_eliminar_deja_la_auditoria_y_la_purga_vacia_la_prosa(
    base: str,
) -> None:
    """Eliminar marca sin borrar: la pieza sigue legible por su detalle
    (la vista lo explica) y la purga diaria vacía su prosa, como la de
    lo cerrado."""
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:elim-purga")
    _fijar_estado(base, creada.id_solicitud, "ERROR")
    assert repo.eliminar_solicitud(
        id_solicitud=creada.id_solicitud, ahora=AHORA
    ) == "eliminada"
    assert repo.eliminar_solicitud(id_solicitud=creada.id_solicitud) == (
        "ya_eliminada"
    )
    # El detalle sigue: sólo desapareció de la bandeja.
    detalle = repo.obtener(creada.id_solicitud)
    assert detalle is not None
    assert detalle.eliminada_en is not None
    purgadas = repo.purgar_prosa(ahora=AHORA)
    assert purgadas >= 2
    textos = _sql(
        base,
        "SELECT texto FROM prosa_transitoria"
        " WHERE id_solicitud = %s",
        (creada.id_solicitud,),
    )
    assert all(f[0] is None for f in textos)


# ---------- reintento ----------


def test_reintentar_encola_y_el_worker_lo_toma(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:reint1")
    trabajo = repo.tomar_trabajo(worker_id="w1")
    assert trabajo is not None
    repo.fallar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=creada.id_solicitud,
        resultado="destination_failure",
        ahora=AHORA,
    )
    assert repo.estado_de(creada.id_solicitud) == "ERROR"

    detalle = repo.obtener(creada.id_solicitud)
    assert detalle is not None
    assert detalle.resultado_fallido == "destination_failure"
    assert detalle.reintentos == 1

    assert repo.reintentar_solicitud(
        id_solicitud=creada.id_solicitud, ahora=AHORA
    ) == "encolado"
    assert repo.estado_de(creada.id_solicitud) == "EN_COLA"
    # El doble clic no encola dos veces: la pieza ya está en la cola.
    assert repo.reintentar_solicitud(id_solicitud=creada.id_solicitud) == (
        "en_curso"
    )

    # La ejecución nueva es una generación más, con su prosa intacta.
    nuevo = repo.tomar_trabajo(worker_id="w2")
    assert nuevo is not None
    assert nuevo.id_solicitud == creada.id_solicitud
    assert nuevo.id_ejecucion != trabajo.id_ejecucion
    assert nuevo.descripcion == "Descripción sintética del pedido."
    assert nuevo.campos["pieza"]["titulo"] == "Título sintético"
    # La fallida queda en el historial con su resultado legible.
    assert _sql(
        base,
        "SELECT estado, resultado FROM ejecuciones"
        " WHERE id_ejecucion = %s",
        (trabajo.id_ejecucion,),
    )[0] == ("FALLIDA", "destination_failure")


def test_reintentar_al_canal_nuevo_con_clave_por_intento(base: str) -> None:
    """Cada reintento lleva su clave determinista `web-reintento:{id}:{n}`
    y su evento; el tope cuenta ejecuciones de generación."""
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:reint2")

    reintentos = 0
    for _ in range(MAX_REINTENTOS):
        trabajo = repo.tomar_trabajo(worker_id="w1")
        assert trabajo is not None
        repo.fallar_trabajo(
            id_ejecucion=trabajo.id_ejecucion,
            id_solicitud=creada.id_solicitud,
            ahora=AHORA,
        )
        assert repo.reintentar_solicitud(
            id_solicitud=creada.id_solicitud, ahora=AHORA
        ) == "encolado"
        reintentos += 1
    assert reintentos == MAX_REINTENTOS

    claves = [
        f[0]
        for f in _sql(
            base,
            "SELECT idempotency_key FROM ejecuciones"
            " WHERE id_solicitud = %s AND clase = 'generacion'"
            " ORDER BY creada_en",
            (creada.id_solicitud,),
        )
    ]
    assert claves[0] == "web:reint2"
    assert claves[1:] == [
        f"web-reintento:{creada.id_solicitud}:{n}"
        for n in range(1, MAX_REINTENTOS + 1)
    ]
    eventos = [
        f[0]
        for f in _sql(
            base,
            "SELECT tipo FROM eventos_ejecucion ee"
            " JOIN ejecuciones e ON e.id_ejecucion = ee.id_ejecucion"
            " WHERE e.id_solicitud = %s AND ee.tipo = 'reintento_encolado'",
            (creada.id_solicitud,),
        )
    ]
    assert len(eventos) == MAX_REINTENTOS

    # Cuarto intento: la pieza agotó los reintentos del mismo pedido.
    ultimo = repo.tomar_trabajo(worker_id="w1")
    assert ultimo is not None
    repo.fallar_trabajo(
        id_ejecucion=ultimo.id_ejecucion,
        id_solicitud=creada.id_solicitud,
        ahora=AHORA,
    )
    assert repo.reintentar_solicitud(id_solicitud=creada.id_solicitud) == (
        "limite_reintentos"
    )


def test_reintentar_rechaza_lo_que_no_es_error(base: str) -> None:
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:reint3")
    assert repo.reintentar_solicitud(id_solicitud=creada.id_solicitud) == (
        "en_curso"
    )
    _fijar_estado(base, creada.id_solicitud, "LISTA")
    assert repo.reintentar_solicitud(id_solicitud=creada.id_solicitud) == (
        "no_reintentable"
    )
    assert repo.reintentar_solicitud(id_solicitud="web-ajena") == (
        "inexistente"
    )


def test_reintentar_sin_prosa_no_toca_nada(base: str) -> None:
    """Si la retención vació el pedido, el reintento se rechaza: encolar
    una ejecución sin campos sólo castigaría al modelo."""
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:reint4")
    trabajo = repo.tomar_trabajo(worker_id="w1")
    assert trabajo is not None
    repo.fallar_trabajo(
        id_ejecucion=trabajo.id_ejecucion,
        id_solicitud=creada.id_solicitud,
        ahora=AHORA,
    )
    # La purga de la retención vació la prosa con la pieza cerrada en
    # error; el reintento lo detecta y no encola nada.
    with _fabrica(base)() as conn:
        conn.execute(
            "UPDATE prosa_transitoria SET texto = NULL, purgada_en = %s"
            " WHERE id_solicitud = %s",
            (AHORA, creada.id_solicitud),
        )
        conn.commit()
    assert repo.reintentar_solicitud(id_solicitud=creada.id_solicitud) == (
        "sin_prosa"
    )
    assert repo.estado_de(creada.id_solicitud) == "ERROR"
    assert repo.tomar_trabajo(worker_id="w2") is None


def test_reintentar_devuelve_a_la_vista_la_archivada(base: str) -> None:
    """Una pieza en marcha no puede quedar escondida: el reintento
    desarchiva."""
    repo = RepositorioWeb(_fabrica(base))
    creada = _crear(repo, "web:reint5")
    _fijar_estado(base, creada.id_solicitud, "ERROR")
    assert repo.archivar_solicitud(
        id_solicitud=creada.id_solicitud, ahora=AHORA
    ) == "archivada"
    assert repo.reintentar_solicitud(
        id_solicitud=creada.id_solicitud, ahora=AHORA
    ) == "encolado"
    detalle = repo.obtener(creada.id_solicitud)
    assert detalle is not None
    assert detalle.archivada_en is None
    assert detalle.estado_web == "EN_COLA"


# ---------- lotes ----------


def _lote(repo: RepositorioLotes) -> object:
    return repo.crear(
        id_actividad=ACTIVIDAD["id_actividad"],
        actividad=ACTIVIDAD,
        personas=PERSONAS,
        linea_descriptiva="Línea descriptiva sintética",
        generada_por_hash="cd" * 32,
        origen_creacion="google",
        ahora=AHORA,
    )


def _emision(base: str, id_lote: str, estado: str) -> None:
    """Siembra un trabajo de emisión: terminal exige `terminada_en`."""
    expira = AHORA + timedelta(days=1)
    terminada = expira if estado in EMISION_TERMINAL else None
    _ejecutar(
        base,
        "INSERT INTO emisiones_certificados (id_emision, id_lote, modo,"
        " estado, terminada_en, expira_en, creada_en, actualizada_en)"
        " VALUES (%s,%s,'real',%s,%s,%s,%s,%s)",
        (
            f"eme-{uuid.uuid4().hex[:12]}", id_lote, estado, terminada,
            expira, AHORA, AHORA,
        ),
    )


def test_archivar_lote_por_regla_de_emision(base: str) -> None:
    repo = RepositorioLotes(_fabrica(base))
    lote = _lote(repo)

    # Pendiente de aprobación: nunca se esconde.
    assert repo.archivar_lote(id_lote=lote.id_lote, ahora=AHORA) == (
        "no_archivable"
    )
    assert repo.archivar_lote(id_lote="lote-ajeno") == "inexistente"

    # Aprobado sin emitir: puede pedirse la emisión todavía.
    repo.decidir(
        id_lote=lote.id_lote,
        hash_lote=lote.objeto_lote,
        accion="aprobar",
        validador_hash="cd" * 32,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="google",
        version_agente="0.12.0",
        ahora=AHORA,
    )
    assert repo.archivar_lote(id_lote=lote.id_lote, ahora=AHORA) == (
        "no_archivable"
    )

    # Con la emisión terminada, se archiva y vuelve con el filtro.
    _emision(base, lote.id_lote, "EMITIDA")
    assert repo.archivar_lote(id_lote=lote.id_lote, ahora=AHORA) == (
        "archivado"
    )
    assert repo.archivar_lote(id_lote=lote.id_lote) == "ya_archivado"
    assert [lote.id_lote for lote in repo.listar()] == []
    archivados = repo.listar(incluir_archivados=True)
    assert [lote.id_lote for lote in archivados] == [lote.id_lote]
    assert archivados[0].archivada_en is not None
    assert repo.desarchivar_lote(id_lote=lote.id_lote) == "desarchivado"
    assert repo.desarchivar_lote(id_lote=lote.id_lote) == "sin_marca"
    assert [lote.id_lote for lote in repo.listar()] == [lote.id_lote]


def test_archivar_lote_descartado_y_emision_en_curso(base: str) -> None:
    """Un lote descartado se archiva siempre —no puede emitir nada—; un
    aprobado con emisión en marcha se queda a la vista."""
    repo = RepositorioLotes(_fabrica(base))
    lote = _lote(repo)
    repo.decidir(
        id_lote=lote.id_lote,
        hash_lote=lote.objeto_lote,
        accion="descartar",
        validador_hash="ef" * 32,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="google",
        version_agente="0.12.0",
        ahora=AHORA,
    )
    assert repo.archivar_lote(id_lote=lote.id_lote, ahora=AHORA) == (
        "archivado"
    )

    repo2 = RepositorioLotes(_fabrica(base))
    lote2 = repo2.crear(
        id_actividad="BANDEJA-002",
        actividad={**ACTIVIDAD, "id_actividad": "BANDEJA-002"},
        personas=PERSONAS,
        linea_descriptiva="Otra línea sintética",
        generada_por_hash="cd" * 32,
        origen_creacion="google",
        ahora=AHORA,
    )
    repo2.decidir(
        id_lote=lote2.id_lote,
        hash_lote=lote2.objeto_lote,
        accion="aprobar",
        validador_hash="cd" * 32,
        rol="APROBADOR_CONTENIDO",
        origen_identidad="google",
        version_agente="0.12.0",
        ahora=AHORA,
    )
    _emision(base, lote2.id_lote, "ENVIANDO")
    assert repo2.archivar_lote(id_lote=lote2.id_lote, ahora=AHORA) == (
        "no_archivable"
    )


def test_listar_orden_prioriza_lo_pendiente_con_archivados(
    base: str,
) -> None:
    """Con el filtro activo, lo pendiente sigue arriba: nunca se esconde
    detrás de «Archivadas»."""
    repo = RepositorioLotes(_fabrica(base))
    _lote(repo)
    repo.crear(
        id_actividad="BANDEJA-003",
        actividad={**ACTIVIDAD, "id_actividad": "BANDEJA-003"},
        personas=PERSONAS,
        linea_descriptiva="Tercera línea sintética",
        generada_por_hash="cd" * 32,
        origen_creacion="google",
        ahora=AHORA + timedelta(seconds=1),
    )
    pendiente = repo.listar()[0]
    assert pendiente.estado == ESTADO_PENDIENTE
    assert repo.archivar_lote(
        id_lote=pendiente.id_lote, ahora=AHORA
    ) == "no_archivable"
    # El orden con archivados incluidos no cambia.
    todo = repo.listar(incluir_archivados=True)
    assert todo[0].estado == ESTADO_PENDIENTE
    assert {lote.estado for lote in todo} == {ESTADO_PENDIENTE}
