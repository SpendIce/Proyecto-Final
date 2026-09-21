"""Recuperación de HU-014: la idempotencia tiene que sobrevivir al reinicio, y
una reserva de emisión interrumpida se cierra sin volver a emitir.

El registro en memoria alcanza para una corrida; el que importa es el que
aguanta una caída entre reservar la emisión y saber el resultado —o entre una
aprobación y la otra, porque el circuito exige las dos. El registro durable es
el de HU-012, reutilizado por `RegistroCertificadosArchivo`.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from agente1.certificados import (
    DestinoCertificadosFake,
    RegistroCertificadosArchivo,
    SolicitudCertificado,
    procesar_certificado,
    reconciliar_emisiones_reservadas,
)
from agente1.confirmaciones import (
    AprobacionHumana,
    ROL_APROBACION_SEMANTICA,
    ROL_APROBACION_UTILITARIA,
)


def solicitud(**cambios: str) -> SolicitudCertificado:
    datos = {
        "id_certificado": "CERT-DUR-001",
        "nombre_titular": "Ana Pérez",
        "documento_titular": "30123456",
        "tipo_certificado": "ASISTENCIA",
        "actividad": "Taller sintético de robótica",
        "fecha": "28 de agosto de 2026",
        "organiza": "Secretaría de Extensión Universitaria",
        "firmante": "Coordinación de Extensión",
    }
    datos.update(cambios)
    return SolicitudCertificado(**datos)


def aprobacion(*, aprobada: bool = True, rol: str) -> AprobacionHumana:
    return AprobacionHumana(
        aprobada=aprobada,
        validador="Validador SEU de prueba",
        rol=rol,
        fecha_iso="2026-08-17T18:00:00-03:00",
    )


def semantica(**kwargs) -> AprobacionHumana:
    return aprobacion(rol=ROL_APROBACION_SEMANTICA, **kwargs)


def utilitaria(**kwargs) -> AprobacionHumana:
    return aprobacion(rol=ROL_APROBACION_UTILITARIA, **kwargs)


def registro_en(tmp_path: Path) -> RegistroCertificadosArchivo:
    return RegistroCertificadosArchivo(tmp_path / "registro")


def procesar(tmp_path: Path, registro, **extra):
    return procesar_certificado(
        solicitud=extra.pop("solicitud", solicitud()),
        directorio_salida=tmp_path / "salida",
        registro=registro,
        **extra,
    )


def aprobar_ambos(tmp_path: Path, registro) -> None:
    procesar(tmp_path, registro, aprobacion=semantica())
    procesar(tmp_path, registro, aprobacion=utilitaria())


# --- Estados observables -----------------------------------------------------


def test_generacion_aprobaciones_reserva_y_emision_son_estados_distintos(
    tmp_path,
):
    registro = registro_en(tmp_path)
    destino = DestinoCertificadosFake()

    generada = procesar(tmp_path, registro)
    semantica_parcial = procesar(tmp_path, registro, aprobacion=semantica())
    aprobada = procesar(tmp_path, registro, aprobacion=utilitaria())
    emitida = procesar(tmp_path, registro, destino=destino, emitir=True)

    assert generada.estado == "PENDIENTE_VALIDACION"
    assert semantica_parcial.estado == "APROBADA_SEMANTICA"
    assert aprobada.estado == "APROBADA"
    assert emitida.estado == "EMITIDA_SIMULADA"
    # La reserva no es un estado que el llamador pida: es el paso intermedio que
    # deja rastro si el proceso muere. Se observa reconciliando, no acá.
    assert len(destino.emisiones) == 1


# --- Durabilidad -------------------------------------------------------------


def test_la_idempotencia_sobrevive_a_reiniciar_el_proceso(tmp_path):
    """El caso que el registro en memoria no cubre.

    Si al reiniciar no queda rastro de las aprobaciones, un reintento vuelve a
    emitir. Acá el segundo registro es un objeto nuevo sobre el mismo
    directorio, que es lo que ve un proceso recién arrancado.
    """

    primero = registro_en(tmp_path)
    aprobar_ambos(tmp_path, primero)

    segundo = registro_en(tmp_path)
    destino = DestinoCertificadosFake()
    reintento = procesar(tmp_path, segundo, destino=destino, emitir=True)

    assert reintento.estado == "EMITIDA_SIMULADA"
    assert len(destino.emisiones) == 1

    tercero = registro_en(tmp_path)
    otro_destino = DestinoCertificadosFake()
    duplicado = procesar(
        tmp_path, tercero, destino=otro_destino, emitir=True
    )

    assert duplicado.estado == "DUPLICADA"
    assert otro_destino.emisiones == []


def test_una_aprobacion_parcial_sobrevive_al_reinicio(tmp_path):
    """La primera de las dos aprobaciones también es durable.

    Si el proceso muere entre la aprobación semántica y la utilitaria, el
    reinicio encuentra el estado parcial y la segunda aprobación completa el
    circuito sin repetir la primera.
    """

    procesar(tmp_path, registro_en(tmp_path), aprobacion=semantica())

    reanudado = registro_en(tmp_path)
    segunda = procesar(tmp_path, reanudado, aprobacion=utilitaria())
    assert segunda.estado == "APROBADA"

    destino = DestinoCertificadosFake()
    emision = procesar(tmp_path, registro_en(tmp_path), destino=destino, emitir=True)
    assert emision.estado == "EMITIDA_SIMULADA"
    assert len(destino.emisiones) == 1


def test_un_rechazo_sobrevive_al_reinicio_y_no_se_puede_aprobar_despues(
    tmp_path,
):
    procesar(
        tmp_path,
        registro_en(tmp_path),
        aprobacion=semantica(aprobada=False),
    )

    destino = DestinoCertificadosFake()
    reintento = procesar(
        tmp_path,
        registro_en(tmp_path),
        aprobacion=utilitaria(),
        destino=destino,
        emitir=True,
    )

    assert reintento.estado == "DUPLICADA"
    assert destino.emisiones == []


def test_el_registro_durable_guarda_el_estado_con_permisos_restrictivos(
    tmp_path,
):
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
        registro.crear("../escape", "Título", "Texto")


def test_un_registro_corrupto_se_trata_como_ausente_y_no_habilita_emision(
    tmp_path,
):
    registro = registro_en(tmp_path)
    procesar(tmp_path, registro, aprobacion=semantica())
    (archivo,) = list((tmp_path / "registro").glob("*.json"))
    archivo.write_text("{ esto no es json", encoding="utf-8")
    clave = archivo.stem

    assert registro.obtener(clave) is None
    assert registro.transicionar(clave, frozenset({"APROBADA"}), "EMISION_RESERVADA") is (
        False
    )


# --- Reconciliación ----------------------------------------------------------


def _llevar_a_reserva(tmp_path):
    """Aprueba con los dos roles y reserva la emisión, sin emitir."""
    registro = registro_en(tmp_path)
    aprobar_ambos(tmp_path, registro)
    (archivo,) = list((tmp_path / "registro").glob("*.json"))
    clave = archivo.stem
    assert registro.transicionar(clave, frozenset({"APROBADA"}), "EMISION_RESERVADA")
    return registro, clave


def test_una_reserva_interrumpida_se_reconcilia_sin_volver_a_emitir(tmp_path):
    """El proceso murió entre reservar y saber el resultado.

    Nadie puede afirmar si la emisión ocurrió, así que reintentar sería apostar
    a que no. La reconciliación deja el registro en un estado que exige una
    decisión humana y no emite nada.
    """

    registro, clave = _llevar_a_reserva(tmp_path)

    reconciliadas = reconciliar_emisiones_reservadas(registro_en(tmp_path))

    assert [reserva.idempotency_key for reserva in reconciliadas] == [clave]
    assert reconciliadas[0].estado == "EMISION_INDETERMINADA"
    assert registro.obtener(clave).estado == "EMISION_INDETERMINADA"


def test_desde_indeterminado_el_pipeline_no_vuelve_a_emitir(tmp_path):
    registro, _ = _llevar_a_reserva(tmp_path)
    reconciliar_emisiones_reservadas(registro)

    destino = DestinoCertificadosFake()
    reintento = procesar(
        tmp_path, registro, aprobacion=semantica(), destino=destino, emitir=True
    )

    assert reintento.estado == "DUPLICADA"
    assert destino.emisiones == []


def test_reconciliar_no_toca_los_estados_terminales(tmp_path):
    registro = registro_en(tmp_path)
    destino = DestinoCertificadosFake()
    aprobar_ambos(tmp_path, registro)
    procesar(tmp_path, registro, destino=destino, emitir=True)

    assert reconciliar_emisiones_reservadas(registro) == ()
    (archivo,) = list((tmp_path / "registro").glob("*.json"))
    assert registro.obtener(archivo.stem).estado == "EMITIDA_SIMULADA"


def test_una_emision_fallida_queda_fallida_y_no_es_una_reserva_colgada(
    tmp_path,
):
    registro = registro_en(tmp_path)
    aprobar_ambos(tmp_path, registro)
    destino = DestinoCertificadosFake(error="fallo sintético del fake")

    resultado = procesar(tmp_path, registro, destino=destino, emitir=True)

    assert resultado.estado == "FALLIDA"
    assert reconciliar_emisiones_reservadas(registro) == ()


# --- Concurrencia ------------------------------------------------------------


def test_varias_emisiones_en_paralelo_producen_una_sola(tmp_path):
    registro = registro_en(tmp_path)
    aprobar_ambos(tmp_path, registro)
    destino = DestinoCertificadosFake()

    def emitir(indice: int):
        return procesar_certificado(
            solicitud=solicitud(),
            directorio_salida=tmp_path / f"salida-{indice}",
            registro=registro_en(tmp_path),
            destino=destino,
            emitir=True,
        )

    with ThreadPoolExecutor(max_workers=8) as ejecutor:
        resultados = list(ejecutor.map(emitir, range(8)))

    estados = [resultado.estado for resultado in resultados]
    assert estados.count("EMITIDA_SIMULADA") == 1
    assert estados.count("DUPLICADA") == 7
    assert len(destino.emisiones) == 1


def test_varias_creaciones_en_paralelo_crean_un_solo_borrador(tmp_path):
    def generar(indice: int):
        return procesar_certificado(
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
        ({"tipo_certificado": "DIPLOMA"}, "certificate_type_invalid"),
        ({"tipo_certificado": ""}, "certificate_type_invalid"),
        ({"actividad": ""}, "required_fields_missing"),
        ({"id_certificado": ""}, "required_fields_missing"),
    ],
)
def test_una_solicitud_invalida_no_deja_rastro_en_el_registro(
    tmp_path, cambio, esperado
):
    registro = registro_en(tmp_path)

    resultado = procesar(tmp_path, registro, solicitud=solicitud(**cambio))

    assert resultado.error == esperado
    assert list((tmp_path / "registro").glob("*.json")) == []


def test_una_emision_sin_registro_previo_no_crea_nada(tmp_path):
    registro = registro_en(tmp_path)

    resultado = procesar(
        tmp_path, registro, destino=DestinoCertificadosFake(), emitir=True
    )

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "approval_required"
    assert list((tmp_path / "registro").glob("*.json")) == []


# --- Auditoría y adapters ----------------------------------------------------


def test_la_auditoria_no_copia_titular_documento_ni_texto(tmp_path):
    registro = registro_en(tmp_path)
    destino = DestinoCertificadosFake()
    aprobar_ambos(tmp_path, registro)

    resultado = procesar(tmp_path, registro, destino=destino, emitir=True)

    registrado = resultado.log_path.read_text(encoding="utf-8")
    assert "Ana Pérez" not in registrado
    assert "30123456" not in registrado
    assert "Taller sintético de robótica" not in registrado
    ultima = json.loads(registrado.strip().splitlines()[-1])
    assert ultima["emission_mode"] == "fake"
    assert len(ultima["pdf_hash"]) == 64


def test_ningun_adapter_productivo_de_emision_queda_habilitado(tmp_path):
    class DestinoQueParecePeroNoEs(DestinoCertificadosFake):
        pass

    resultado = procesar(
        tmp_path,
        registro_en(tmp_path),
        aprobacion=semantica(),
        destino=DestinoQueParecePeroNoEs(),
        emitir=True,
    )

    assert resultado.estado != "EMITIDA_SIMULADA"
