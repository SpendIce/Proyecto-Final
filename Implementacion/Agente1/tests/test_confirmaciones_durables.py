"""Recuperación de HU-012: la idempotencia tiene que sobrevivir al reinicio, y
una reserva interrumpida se cierra sin volver a entregar.

El registro en memoria alcanza para una corrida; el que importa es el que
aguanta una caída entre reservar el envío y saber el resultado."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from agente1.confirmaciones import (
    AprobacionHumana,
    DestinoConfirmacionesFake,
    RegistroConfirmacionesArchivo,
    SolicitudConfirmacion,
    procesar_confirmacion,
    reconciliar_envios_reservados,
)


def solicitud(**cambios: str) -> SolicitudConfirmacion:
    datos = {
        "id_inscripcion": "INS-DUR-001",
        "nombre_destinatario": "Ana Pérez",
        "email_destinatario": "ana.perez@example.test",
        "actividad": "Taller sintético de robótica",
        "fecha": "28 de agosto de 2026, 18:00",
        "lugar": "Aula 4",
        "organiza": "Secretaría de Extensión Universitaria",
        "contacto": "extension@example.test",
    }
    datos.update(cambios)
    return SolicitudConfirmacion(**datos)


def aprobacion(*, aprobada: bool = True) -> AprobacionHumana:
    return AprobacionHumana(
        aprobada=aprobada,
        validador="Validador SEU de prueba",
        rol="ROL_SIMULADO_NO_INSTITUCIONAL",
        fecha_iso="2026-08-17T18:00:00-03:00",
    )


def registro_en(tmp_path: Path) -> RegistroConfirmacionesArchivo:
    return RegistroConfirmacionesArchivo(tmp_path / "registro")


def procesar(tmp_path: Path, registro, **extra):
    return procesar_confirmacion(
        solicitud=extra.pop("solicitud", solicitud()),
        directorio_salida=tmp_path / "salida",
        registro=registro,
        **extra,
    )


# --- Estados observables -----------------------------------------------------


def test_generacion_aprobacion_reserva_y_entrega_son_estados_distintos(tmp_path):
    registro = registro_en(tmp_path)
    destino = DestinoConfirmacionesFake()

    generada = procesar(tmp_path, registro)
    aprobada = procesar(tmp_path, registro, aprobacion=aprobacion())
    entregada = procesar(
        tmp_path, registro, aprobacion=aprobacion(), destino=destino, enviar=True
    )

    assert generada.estado == "PENDIENTE_VALIDACION"
    assert aprobada.estado == "APROBADA"
    assert entregada.estado == "ENVIADA_SIMULADA"
    # La reserva no es un estado que el llamador pida: es el paso intermedio que
    # deja rastro si el proceso muere. Se observa reconciliando, no acá.
    assert len(destino.entregas) == 1


# --- Durabilidad -------------------------------------------------------------


def test_la_idempotencia_sobrevive_a_reiniciar_el_proceso(tmp_path):
    """El caso que el registro en memoria no cubre.

    Si al reiniciar no queda rastro de la aprobación, un reintento vuelve a
    entregar. Acá el segundo registro es un objeto nuevo sobre el mismo
    directorio, que es lo que ve un proceso recién arrancado.
    """

    primero = registro_en(tmp_path)
    procesar(tmp_path, primero, aprobacion=aprobacion())

    segundo = registro_en(tmp_path)
    destino = DestinoConfirmacionesFake()
    reintento = procesar(
        tmp_path, segundo, aprobacion=aprobacion(), destino=destino, enviar=True
    )

    assert reintento.estado == "ENVIADA_SIMULADA"
    assert len(destino.entregas) == 1

    tercero = registro_en(tmp_path)
    otro_destino = DestinoConfirmacionesFake()
    duplicado = procesar(
        tmp_path, tercero, aprobacion=aprobacion(), destino=otro_destino, enviar=True
    )

    assert duplicado.estado == "DUPLICADA"
    assert otro_destino.entregas == []


def test_un_rechazo_sobrevive_al_reinicio_y_no_se_puede_aprobar_despues(tmp_path):
    procesar(tmp_path, registro_en(tmp_path), aprobacion=aprobacion(aprobada=False))

    destino = DestinoConfirmacionesFake()
    reintento = procesar(
        tmp_path,
        registro_en(tmp_path),
        aprobacion=aprobacion(),
        destino=destino,
        enviar=True,
    )

    assert reintento.estado == "DUPLICADA"
    assert destino.entregas == []


def test_el_registro_durable_guarda_el_estado_con_permisos_restrictivos(tmp_path):
    registro = registro_en(tmp_path)
    procesar(tmp_path, registro)

    directorio = tmp_path / "registro"
    (archivo,) = list(directorio.glob("*.json"))

    assert directorio.stat().st_mode & 0o777 == 0o700
    assert archivo.stat().st_mode & 0o777 == 0o600
    assert json.loads(archivo.read_text(encoding="utf-8"))["estado"] == (
        "PENDIENTE_VALIDACION"
    )


def test_una_clave_que_no_es_un_hash_no_elige_donde_se_escribe(tmp_path):
    registro = registro_en(tmp_path)

    with pytest.raises(ValueError, match="idempotencia"):
        registro.crear("../escape", "Asunto", "Cuerpo")


def test_un_registro_corrupto_se_trata_como_ausente_y_no_habilita_entrega(tmp_path):
    registro = registro_en(tmp_path)
    procesar(tmp_path, registro, aprobacion=aprobacion())
    (archivo,) = list((tmp_path / "registro").glob("*.json"))
    archivo.write_text("{ esto no es json", encoding="utf-8")
    clave = archivo.stem

    assert registro.obtener(clave) is None
    assert registro.transicionar(clave, frozenset({"APROBADA"}), "ENVIO_RESERVADO") is (
        False
    )


# --- Reconciliación ----------------------------------------------------------


def test_una_reserva_interrumpida_se_reconcilia_sin_volver_a_entregar(tmp_path):
    """El proceso murió entre reservar y saber el resultado.

    Nadie puede afirmar si la entrega ocurrió, así que reintentar sería apostar
    a que no. La reconciliación deja el registro en un estado que exige una
    decisión humana y no entrega nada.
    """

    registro = registro_en(tmp_path)
    procesar(tmp_path, registro, aprobacion=aprobacion())
    (archivo,) = list((tmp_path / "registro").glob("*.json"))
    clave = archivo.stem
    assert registro.transicionar(clave, frozenset({"APROBADA"}), "ENVIO_RESERVADO")

    reconciliadas = reconciliar_envios_reservados(registro_en(tmp_path))

    assert [reserva.idempotency_key for reserva in reconciliadas] == [clave]
    assert reconciliadas[0].estado == "ENVIO_INDETERMINADO"
    assert registro.obtener(clave).estado == "ENVIO_INDETERMINADO"


def test_desde_indeterminado_el_pipeline_no_vuelve_a_entregar(tmp_path):
    registro = registro_en(tmp_path)
    procesar(tmp_path, registro, aprobacion=aprobacion())
    (archivo,) = list((tmp_path / "registro").glob("*.json"))
    registro.transicionar(archivo.stem, frozenset({"APROBADA"}), "ENVIO_RESERVADO")
    reconciliar_envios_reservados(registro)

    destino = DestinoConfirmacionesFake()
    reintento = procesar(
        tmp_path, registro, aprobacion=aprobacion(), destino=destino, enviar=True
    )

    assert reintento.estado == "DUPLICADA"
    assert destino.entregas == []


def test_reconciliar_no_toca_los_estados_terminales(tmp_path):
    registro = registro_en(tmp_path)
    destino = DestinoConfirmacionesFake()
    procesar(
        tmp_path, registro, aprobacion=aprobacion(), destino=destino, enviar=True
    )

    assert reconciliar_envios_reservados(registro) == ()
    (archivo,) = list((tmp_path / "registro").glob("*.json"))
    assert registro.obtener(archivo.stem).estado == "ENVIADA_SIMULADA"


def test_una_entrega_fallida_queda_fallida_y_no_es_una_reserva_colgada(tmp_path):
    registro = registro_en(tmp_path)
    destino = DestinoConfirmacionesFake(error="fallo sintético del fake")

    resultado = procesar(
        tmp_path, registro, aprobacion=aprobacion(), destino=destino, enviar=True
    )

    assert resultado.estado == "FALLIDA"
    assert reconciliar_envios_reservados(registro) == ()


# --- Concurrencia ------------------------------------------------------------


def test_varias_entregas_en_paralelo_producen_una_sola(tmp_path):
    registro = registro_en(tmp_path)
    procesar(tmp_path, registro, aprobacion=aprobacion())
    destino = DestinoConfirmacionesFake()

    def entregar(indice: int):
        return procesar_confirmacion(
            solicitud=solicitud(),
            directorio_salida=tmp_path / f"salida-{indice}",
            registro=registro_en(tmp_path),
            aprobacion=aprobacion(),
            destino=destino,
            enviar=True,
        )

    with ThreadPoolExecutor(max_workers=8) as ejecutor:
        resultados = list(ejecutor.map(entregar, range(8)))

    estados = [resultado.estado for resultado in resultados]
    assert estados.count("ENVIADA_SIMULADA") == 1
    assert estados.count("DUPLICADA") == 7
    assert len(destino.entregas) == 1


def test_varias_creaciones_en_paralelo_crean_un_solo_borrador(tmp_path):
    def generar(indice: int):
        return procesar_confirmacion(
            solicitud=solicitud(),
            directorio_salida=tmp_path / f"salida-{indice}",
            registro=registro_en(tmp_path),
        )

    with ThreadPoolExecutor(max_workers=8) as ejecutor:
        resultados = list(ejecutor.map(generar, range(8)))

    estados = [resultado.estado for resultado in resultados]
    assert estados.count("PENDIENTE_VALIDACION") == 1
    assert estados.count("DUPLICADA") == 7
    assert len(list((tmp_path / "registro").glob("*.json"))) == 1


# --- Entradas que no llegan al registro --------------------------------------


@pytest.mark.parametrize(
    ("cambio", "esperado"),
    [
        ({"email_destinatario": "sin-arroba"}, "recipient_invalid"),
        ({"email_destinatario": ""}, "recipient_invalid"),
        ({"actividad": ""}, "required_fields_missing"),
        ({"id_inscripcion": ""}, "required_fields_missing"),
    ],
)
def test_una_solicitud_invalida_no_deja_rastro_en_el_registro(
    tmp_path, cambio, esperado
):
    registro = registro_en(tmp_path)

    resultado = procesar(tmp_path, registro, solicitud=solicitud(**cambio))

    assert resultado.error == esperado
    assert list((tmp_path / "registro").glob("*.json")) == []


# --- Auditoría y adapters ----------------------------------------------------


def test_la_auditoria_no_copia_destinatarios_ni_cuerpos(tmp_path):
    registro = registro_en(tmp_path)
    destino = DestinoConfirmacionesFake()

    resultado = procesar(
        tmp_path, registro, aprobacion=aprobacion(), destino=destino, enviar=True
    )

    registrado = resultado.log_path.read_text(encoding="utf-8")
    assert "ana.perez@example.test" not in registrado
    assert "Ana Pérez" not in registrado
    assert "Taller sintético de robótica" not in registrado
    assert json.loads(registrado.strip().splitlines()[-1])["delivery_mode"] == "fake"


def test_ningun_adapter_productivo_de_correo_queda_habilitado(tmp_path):
    class DestinoQueParecePeroNoEs(DestinoConfirmacionesFake):
        pass

    resultado = procesar(
        tmp_path,
        registro_en(tmp_path),
        aprobacion=aprobacion(),
        destino=DestinoQueParecePeroNoEs(),
        enviar=True,
    )

    assert resultado.estado != "ENVIADA_SIMULADA"
