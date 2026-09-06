"""Puerto de persistencia: idempotencia por firma completa, transiciones válidas
de estado, invariantes de borrador/output_hash, rechazo de timestamps futuros
y baja lógica que nunca borra filas."""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timedelta, timezone

import pytest

from agente1.persistencia import (
    BorradorNuevo,
    ConflictoIdempotencia,
    DefectoNuevo,
    EjecucionNueva,
    EstadoEjecucion,
    EstadoInvalido,
    InMemoryRepositorioEjecuciones,
    RepositorioEjecuciones,
    ResultadoEjecucion,
    ValidacionNueva,
)


AHORA = datetime(2026, 8, 17, 18, 0, tzinfo=timezone.utc)


def nuevo_repo() -> InMemoryRepositorioEjecuciones:
    return InMemoryRepositorioEjecuciones(
        clock=lambda: AHORA + timedelta(days=400)
    )


def nueva_ejecucion(**cambios: object) -> EjecucionNueva:
    valores: dict[str, object] = {
        "id_solicitud": "SOL-001",
        "id_ejecucion": "EJE-001",
        "idempotency_key": "hu011:SOL-001:instagram:v2",
        "correlation_id": "corr-001",
        "hu": "HU-011",
        "input_hash": "a" * 64,
        "fuente_tipo": "google_sheets",
        "creada_en": AHORA,
    }
    valores.update(cambios)
    return EjecucionNueva(**valores)  # type: ignore[arg-type]


def test_adapter_memoria_implementa_puerto_y_inicio_idempotente() -> None:
    repo = nuevo_repo()

    primera = repo.iniciar(nueva_ejecucion())
    repetida = repo.iniciar(nueva_ejecucion())

    assert isinstance(repo, RepositorioEjecuciones)
    assert primera == repetida
    assert len(repo.snapshot().ejecuciones) == 1
    assert len(repo.snapshot().solicitudes) == 1


def test_idempotencia_rechaza_reutilizar_clave_con_otro_input() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())

    with pytest.raises(ConflictoIdempotencia):
        repo.iniciar(nueva_ejecucion(input_hash="b" * 64, id_ejecucion="EJE-002"))

    assert len(repo.snapshot().ejecuciones) == 1


def test_correlation_id_es_unico() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())

    with pytest.raises(ConflictoIdempotencia):
        repo.iniciar(
            nueva_ejecucion(
                id_solicitud="SOL-002",
                id_ejecucion="EJE-002",
                idempotency_key="otra-clave",
            )
        )


def test_solicitud_existente_rechaza_cambio_de_fuente() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())

    with pytest.raises(ConflictoIdempotencia, match="fuente"):
        repo.iniciar(
            nueva_ejecucion(
                id_ejecucion="EJE-002",
                idempotency_key="hu011:SOL-001:linkedin:v2",
                correlation_id="corr-002",
                fuente_tipo="csv",
            )
        )

    assert len(repo.snapshot().ejecuciones) == 1


def test_solicitud_existente_rechaza_ejecucion_retroactiva() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())

    with pytest.raises(EstadoInvalido, match="anterior"):
        repo.iniciar(
            nueva_ejecucion(
                id_ejecucion="EJE-002",
                idempotency_key="hu011:SOL-001:linkedin:v2",
                correlation_id="corr-002",
                creada_en=AHORA - timedelta(seconds=1),
            )
        )

    assert len(repo.snapshot().ejecuciones) == 1


def test_completar_persiste_estado_borrador_y_evento_atomicamente() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())

    repo.completar(
        ResultadoEjecucion(
            id_ejecucion="EJE-001",
            estado=EstadoEjecucion.PENDIENTE_VALIDACION,
            resultado="borrador_generado",
            finalizada_en=AHORA + timedelta(seconds=2),
            output_hash="b" * 64,
            borrador=BorradorNuevo(
                id_borrador="BOR-001",
                referencia_hash="c" * 64,
                output_hash="b" * 64,
                canal="instagram",
                creada_en=AHORA + timedelta(seconds=2),
            ),
        )
    )

    snapshot = repo.snapshot()
    assert snapshot.ejecuciones["EJE-001"].estado is EstadoEjecucion.PENDIENTE_VALIDACION
    assert snapshot.borradores["BOR-001"].referencia_hash == "c" * 64
    assert snapshot.eventos[-1].tipo == "borrador_generado"


def test_completar_rollback_si_resultado_y_borrador_no_son_coherentes() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())
    antes = repo.snapshot()

    with pytest.raises(EstadoInvalido):
        repo.completar(
            ResultadoEjecucion(
                id_ejecucion="EJE-001",
                estado=EstadoEjecucion.FALLIDA,
                resultado="error_generacion",
                finalizada_en=AHORA + timedelta(seconds=2),
                borrador=BorradorNuevo(
                    id_borrador="BOR-001",
                    referencia_hash="c" * 64,
                    output_hash="b" * 64,
                    canal="instagram",
                    creada_en=AHORA + timedelta(seconds=2),
                ),
            )
        )

    assert repo.snapshot() == antes


def test_completar_rechaza_timestamps_anteriores_al_inicio() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())

    with pytest.raises(EstadoInvalido, match="anterior"):
        repo.completar(
            ResultadoEjecucion(
                id_ejecucion="EJE-001",
                estado=EstadoEjecucion.FALLIDA,
                resultado="error_generacion",
                finalizada_en=AHORA - timedelta(seconds=1),
            )
        )

    assert repo.snapshot().ejecuciones["EJE-001"].estado is EstadoEjecucion.INICIADA


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("id_solicitud", "persona@example.com"),
        ("id_ejecucion", "Bearer secret"),
        ("correlation_id", "corr/raw"),
        ("idempotency_key", "Bearer secret"),
        ("hu", "HU-011 secreto"),
        ("fuente_tipo", "persona@example.com"),
    ],
)
def test_inicio_rechaza_identificadores_y_codigos_no_contractuales(
    campo: str, valor: str
) -> None:
    repo = nuevo_repo()

    with pytest.raises(ValueError):
        repo.iniciar(nueva_ejecucion(**{campo: valor}))

    assert not repo.snapshot().eventos


@pytest.mark.parametrize(
    ("resultado", "error_code"),
    [
        ("persona@example.com", None),
        ("error_generacion", "Bearer secret"),
    ],
)
def test_resultado_rechaza_texto_libre_y_secretos(
    resultado: str, error_code: str | None
) -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())

    with pytest.raises(ValueError):
        repo.completar(
            ResultadoEjecucion(
                id_ejecucion="EJE-001",
                estado=EstadoEjecucion.FALLIDA,
                resultado=resultado,
                error_code=error_code,
                finalizada_en=AHORA,
            )
        )

    assert [evento.tipo for evento in repo.snapshot().eventos] == ["ejecucion_iniciada"]


@pytest.mark.parametrize(
    ("estado", "resultado", "output_hash", "error_code"),
    [
        (EstadoEjecucion.FALLIDA, "error_generacion", "b" * 64, None),
        (
            EstadoEjecucion.PENDIENTE_VALIDACION,
            "borrador_generado",
            "b" * 64,
            "generator_unavailable",
        ),
    ],
)
def test_resultado_rechaza_hash_o_error_incompatibles_con_estado(
    estado: EstadoEjecucion,
    resultado: str,
    output_hash: str | None,
    error_code: str | None,
) -> None:
    borrador = None
    if estado is EstadoEjecucion.PENDIENTE_VALIDACION:
        borrador = BorradorNuevo(
            id_borrador="BOR-001",
            referencia_hash="c" * 64,
            output_hash="b" * 64,
            canal="instagram",
            creada_en=AHORA,
        )

    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())
    with pytest.raises(EstadoInvalido):
        repo.completar(
            ResultadoEjecucion(
                id_ejecucion="EJE-001",
                estado=estado,
                resultado=resultado,
                finalizada_en=AHORA,
                output_hash=output_hash,
                error_code=error_code,
                borrador=borrador,
            )
        )


def test_tipo_evento_de_resultado_es_interno_y_no_copia_resultado() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())

    repo.completar(
        ResultadoEjecucion(
            id_ejecucion="EJE-001",
            estado=EstadoEjecucion.FALLIDA,
            resultado="error_generacion",
            error_code="generator_unavailable",
            finalizada_en=AHORA,
        )
    )

    assert repo.snapshot().eventos[-1].tipo == "ejecucion_fallida"


def test_borrador_rechaza_canal_e_identificador_no_contractuales() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())

    with pytest.raises(ValueError):
        repo.completar(
            ResultadoEjecucion(
                id_ejecucion="EJE-001",
                estado=EstadoEjecucion.PENDIENTE_VALIDACION,
                resultado="borrador_generado",
                finalizada_en=AHORA,
                output_hash="b" * 64,
                borrador=BorradorNuevo(
                    id_borrador="persona@example.com",
                    referencia_hash="c" * 64,
                    output_hash="b" * 64,
                    canal="Bearer secret",
                    creada_en=AHORA,
                ),
            )
        )


def test_validacion_actualiza_borrador_y_ejecucion_en_una_operacion() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())
    repo.completar(
        ResultadoEjecucion(
            id_ejecucion="EJE-001",
            estado=EstadoEjecucion.PENDIENTE_VALIDACION,
            resultado="borrador_generado",
            finalizada_en=AHORA,
            output_hash="b" * 64,
            borrador=BorradorNuevo(
                id_borrador="BOR-001",
                referencia_hash="c" * 64,
                output_hash="b" * 64,
                canal="linkedin",
                creada_en=AHORA,
            ),
        )
    )

    repo.registrar_validacion(
        ValidacionNueva(
            id_validacion="VAL-001",
            id_borrador="BOR-001",
            decision="APROBADA",
            validador_ref_hash="d" * 64,
            checklist_version="seu_v1",
            registrada_en=AHORA + timedelta(minutes=5),
        )
    )

    snapshot = repo.snapshot()
    assert snapshot.borradores["BOR-001"].estado == "APROBADO"
    assert snapshot.ejecuciones["EJE-001"].estado is EstadoEjecucion.APROBADA
    assert snapshot.validaciones["VAL-001"].validador_ref_hash == "d" * 64


def test_validacion_rechaza_timestamp_anterior_al_borrador() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())
    repo.completar(
        ResultadoEjecucion(
            id_ejecucion="EJE-001",
            estado=EstadoEjecucion.PENDIENTE_VALIDACION,
            resultado="borrador_generado",
            finalizada_en=AHORA,
            output_hash="b" * 64,
            borrador=BorradorNuevo(
                id_borrador="BOR-001",
                referencia_hash="c" * 64,
                output_hash="b" * 64,
                canal="instagram",
                creada_en=AHORA,
            ),
        )
    )

    with pytest.raises(EstadoInvalido, match="anterior"):
        repo.registrar_validacion(
            ValidacionNueva(
                id_validacion="VAL-001",
                id_borrador="BOR-001",
                decision="APROBADA",
                validador_ref_hash="d" * 64,
                checklist_version="seu_v1",
                registrada_en=AHORA - timedelta(seconds=1),
            )
        )

    assert not repo.snapshot().validaciones


def test_registra_defecto_sin_contenido_sensible() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())

    repo.registrar_defecto(
        DefectoNuevo(
            id_defecto="DEF-001",
            id_ejecucion="EJE-001",
            codigo="salida_no_conforme",
            severidad="ALTA",
            evidencia_hash="e" * 64,
            creado_en=AHORA,
        )
    )

    defecto = repo.snapshot().defectos["DEF-001"]
    assert defecto.codigo == "salida_no_conforme"
    nombres = {campo.name for campo in fields(defecto)}
    assert nombres.isdisjoint({"contenido", "email", "contacto", "token", "prompt"})


def test_defecto_rechaza_timestamp_anterior_a_la_ejecucion() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())

    with pytest.raises(EstadoInvalido, match="anterior"):
        repo.registrar_defecto(
            DefectoNuevo(
                id_defecto="DEF-001",
                id_ejecucion="EJE-001",
                codigo="salida_no_conforme",
                severidad="ALTA",
                evidencia_hash="e" * 64,
                creado_en=AHORA - timedelta(seconds=1),
            )
        )

    assert not repo.snapshot().defectos


def test_retencion_marca_eliminacion_logica_sin_borrar_trazabilidad() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())
    repo.completar(
        ResultadoEjecucion(
            id_ejecucion="EJE-001",
            estado=EstadoEjecucion.FALLIDA,
            resultado="error_generacion",
            finalizada_en=AHORA,
        )
    )

    cantidad = repo.eliminar_logicamente_anteriores(
        antes_de=AHORA + timedelta(days=30),
        eliminado_en=AHORA + timedelta(days=31),
    )

    snapshot = repo.snapshot()
    assert cantidad == 1
    assert snapshot.ejecuciones["EJE-001"].eliminado_en is not None
    assert snapshot.solicitudes["SOL-001"].eliminado_en is not None
    assert snapshot.eventos[-1].tipo == "retencion_eliminacion_logica"


def test_retencion_alcanza_validacion_asociada() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())
    repo.completar(
        ResultadoEjecucion(
            id_ejecucion="EJE-001",
            estado=EstadoEjecucion.PENDIENTE_VALIDACION,
            resultado="borrador_generado",
            finalizada_en=AHORA,
            output_hash="b" * 64,
            borrador=BorradorNuevo(
                id_borrador="BOR-001",
                referencia_hash="c" * 64,
                output_hash="b" * 64,
                canal="instagram",
                creada_en=AHORA,
            ),
        )
    )
    repo.registrar_validacion(
        ValidacionNueva(
            id_validacion="VAL-001",
            id_borrador="BOR-001",
            decision="RECHAZADA",
            validador_ref_hash="d" * 64,
            checklist_version="seu_v1",
            registrada_en=AHORA + timedelta(minutes=1),
        )
    )

    repo.eliminar_logicamente_anteriores(
        antes_de=AHORA + timedelta(days=30),
        eliminado_en=AHORA + timedelta(days=31),
    )

    assert repo.snapshot().validaciones["VAL-001"].eliminado_en is not None


def test_retencion_no_elimina_borradores_pendientes_de_validacion() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())
    repo.completar(
        ResultadoEjecucion(
            id_ejecucion="EJE-001",
            estado=EstadoEjecucion.PENDIENTE_VALIDACION,
            resultado="borrador_generado",
            finalizada_en=AHORA,
            output_hash="b" * 64,
            borrador=BorradorNuevo(
                id_borrador="BOR-001",
                referencia_hash="c" * 64,
                output_hash="b" * 64,
                canal="linkedin",
                creada_en=AHORA,
            ),
        )
    )

    cantidad = repo.eliminar_logicamente_anteriores(
        antes_de=AHORA + timedelta(days=365),
        eliminado_en=AHORA + timedelta(days=366),
    )

    assert cantidad == 0
    assert repo.snapshot().borradores["BOR-001"].eliminado_en is None


def test_retencion_rechaza_corte_posterior_a_fecha_de_eliminacion() -> None:
    repo = nuevo_repo()
    repo.iniciar(nueva_ejecucion())
    repo.completar(
        ResultadoEjecucion(
            id_ejecucion="EJE-001",
            estado=EstadoEjecucion.FALLIDA,
            resultado="error_generacion",
            finalizada_en=AHORA,
        )
    )

    with pytest.raises(ValueError, match="corte"):
        repo.eliminar_logicamente_anteriores(
            antes_de=AHORA + timedelta(days=2),
            eliminado_en=AHORA + timedelta(days=1),
        )


def test_rechaza_timestamp_futuro_segun_reloj_inyectado() -> None:
    repo = InMemoryRepositorioEjecuciones(clock=lambda: AHORA)

    with pytest.raises(ValueError, match="futuro"):
        repo.iniciar(nueva_ejecucion(creada_en=AHORA + timedelta(seconds=1)))


@pytest.mark.parametrize("fecha", [datetime(2026, 8, 17), AHORA.replace(tzinfo=None)])
def test_rechaza_timestamps_sin_zona_horaria(fecha: datetime) -> None:
    repo = nuevo_repo()

    with pytest.raises(ValueError, match="zona horaria"):
        repo.iniciar(nueva_ejecucion(creada_en=fecha))
