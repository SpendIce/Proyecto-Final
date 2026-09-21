"""Envío asíncrono de HU-012 (s4d): la confirmación con las dos aprobaciones
se encola (`ENVIO_ENCOLADO`) y un worker separado, `drenar_envios`, la entrega
después con reintentos acotados.

Cubre: encolado idempotente por clave, orden FIFO, drenaje tras la doble
aprobación, presupuesto de reintentos agotado en `FALLIDA`, reinicio a mitad
de cola, descarte de ítems cuyo registro ya no está pendiente y la garantía
de que nada entra a la cola ni se entrega sin las dos aprobaciones. La
entrega sigue siendo exclusivamente contra `DestinoConfirmacionesFake`.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from agente1.confirmaciones import (
    AprobacionHumana,
    ColaEnviosArchivo,
    ColaEnviosMemoria,
    DestinoConfirmacionesFake,
    ItemEnvio,
    RegistroConfirmacionesArchivo,
    RegistroConfirmacionesMemoria,
    ROL_APROBACION_SEMANTICA,
    ROL_APROBACION_UTILITARIA,
    SolicitudConfirmacion,
    drenar_envios,
    procesar_confirmacion,
    reconciliar_envios_reservados,
)


def solicitud(**cambios: str) -> SolicitudConfirmacion:
    datos = {
        "id_inscripcion": "INS-COLA-001",
        "nombre_destinatario": "Ana Pérez",
        "email_destinatario": "ana.perez@example.test",
        "actividad": "Taller de robótica educativa",
        "fecha": "28 de agosto de 2026, 18:00",
        "lugar": "Aula 4",
        "organiza": "Secretaría de Extensión Universitaria",
        "contacto": "extension@example.test",
    }
    datos.update(cambios)
    return SolicitudConfirmacion(**datos)


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


def procesar(tmp_path: Path, registro, **extra):
    return procesar_confirmacion(
        solicitud=extra.pop("solicitud", solicitud()),
        directorio_salida=tmp_path / "salida",
        registro=registro,
        **extra,
    )


def aprobar_ambos(tmp_path: Path, registro, solicitud_=None) -> None:
    procesar(tmp_path, registro, solicitud=solicitud_ or solicitud(), aprobacion=semantica())
    procesar(tmp_path, registro, solicitud=solicitud_ or solicitud(), aprobacion=utilitaria())


def encolar(tmp_path: Path, registro, cola, solicitud_=None):
    return procesar(
        tmp_path,
        registro,
        solicitud=solicitud_ or solicitud(),
        asincrono=True,
        cola=cola,
    )


# --- Encolado ----------------------------------------------------------------


def test_encolar_tras_doble_aprobacion_no_entrega_todavia(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    aprobar_ambos(tmp_path, registro)

    resultado = encolar(tmp_path, registro, cola)

    assert resultado.estado == "ENVIO_ENCOLADO"
    assert resultado.error is None
    assert registro.obtener(resultado.idempotency_key).estado == "ENVIO_ENCOLADO"
    (item,) = cola.pendientes()
    assert item.idempotency_key == resultado.idempotency_key
    assert item.destinatario == "ana.perez@example.test"
    assert item.intentos == 0


def test_la_segunda_aprobacion_puede_dejar_el_envio_encolado(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    procesar(tmp_path, registro, aprobacion=utilitaria())

    resultado = procesar(
        tmp_path, registro, aprobacion=semantica(), asincrono=True, cola=cola
    )

    assert resultado.estado == "ENVIO_ENCOLADO"
    assert len(cola.pendientes()) == 1


def test_encolar_es_idempotente_por_clave(tmp_path):
    """Un mismo pedido encolado dos veces produce un solo ítem y nada más."""
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    aprobar_ambos(tmp_path, registro)

    primero = encolar(tmp_path, registro, cola)
    segundo = encolar(tmp_path, registro, cola)
    # El camino síncrono tampoco puede re-entregar lo que ya está encolado.
    sincrono = procesar(
        tmp_path, registro, destino=DestinoConfirmacionesFake(), enviar=True
    )

    assert primero.estado == "ENVIO_ENCOLADO"
    assert segundo.estado == "DUPLICADA"
    assert sincrono.estado == "DUPLICADA"
    assert len(cola.pendientes()) == 1


def test_encolados_concurrentes_producen_un_solo_item(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    aprobar_ambos(tmp_path, registro)

    def ejecutar(_: int):
        return encolar(tmp_path, registro, cola)

    with ThreadPoolExecutor(max_workers=8) as pool:
        resultados = list(pool.map(ejecutar, range(16)))

    assert sum(r.estado == "ENVIO_ENCOLADO" for r in resultados) == 1
    assert sum(r.estado == "DUPLICADA" for r in resultados) == 15
    assert len(cola.pendientes()) == 1


def test_encolar_exige_cola_explicita(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    aprobar_ambos(tmp_path, registro)

    resultado = procesar(tmp_path, registro, asincrono=True)

    assert resultado.estado == "INVALIDA"
    assert resultado.error == "queue_required"
    # El registro quedó aprobado: el pedido inválido no lo mueve ni lo encola.
    assert registro.obtener(resultado.idempotency_key).estado == "APROBADA"


def test_nada_entra_a_la_cola_sin_las_dos_aprobaciones(tmp_path):
    """Ni una aprobación sola ni un pedido sobre pendiente encolan algo."""
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()

    parcial = procesar(
        tmp_path, registro, aprobacion=semantica(), asincrono=True, cola=cola
    )
    assert parcial.estado == "APROBADA_SEMANTICA"
    assert cola.pendientes() == ()

    sin_aprobar = encolar(tmp_path, registro, cola)
    assert sin_aprobar.estado == "INVALIDA"
    assert sin_aprobar.error == "approval_required"
    assert cola.pendientes() == ()

    # Recién cuando el circuito se completa el encolado es posible.
    encolada = procesar(
        tmp_path, registro, aprobacion=utilitaria(), asincrono=True, cola=cola
    )
    assert encolada.estado == "ENVIO_ENCOLADO"
    assert len(cola.pendientes()) == 1


def test_un_rechazo_no_encola_aunque_se_pida_asincrono(tmp_path):
    cola = ColaEnviosMemoria()
    resultado = procesar(
        tmp_path,
        RegistroConfirmacionesMemoria(),
        aprobacion=semantica(aprobada=False),
        asincrono=True,
        cola=cola,
    )

    assert resultado.estado == "RECHAZADA"
    assert cola.pendientes() == ()


# --- Drenaje -----------------------------------------------------------------


def test_drenar_entrega_en_orden_de_encolado(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    destino = DestinoConfirmacionesFake()
    solicitudes = [
        solicitud(id_inscripcion=f"INS-COLA-{i:03d}") for i in (1, 2, 3)
    ]
    claves = []
    for s in solicitudes:
        aprobar_ambos(tmp_path, registro, s)
        claves.append(encolar(tmp_path, registro, cola, s).idempotency_key)

    resultados = drenar_envios(
        registro=registro,
        cola=cola,
        destino=destino,
        directorio_salida=tmp_path / "salida",
    )

    assert [r.resolucion for r in resultados] == ["entregada"] * 3
    assert [r.idempotency_key for r in resultados] == claves
    assert [e.idempotency_key for e in destino.entregas] == claves
    assert cola.pendientes() == ()
    assert all(
        registro.obtener(clave).estado == "ENVIADA_SIMULADA" for clave in claves
    )


def test_drenar_con_cola_vacia_no_hace_nada(tmp_path):
    resultados = drenar_envios(
        registro=RegistroConfirmacionesMemoria(),
        cola=ColaEnviosMemoria(),
        destino=DestinoConfirmacionesFake(),
        directorio_salida=tmp_path / "salida",
    )
    assert resultados == ()


def test_drenar_sin_fake_explicito_no_procesa_nada(tmp_path):
    """Sin el fake exacto el worker no trabaja: ni entrega ni descarta."""

    class DestinoCualquiera:
        def entregar(self, **_: str) -> None:
            raise AssertionError("no debería llamarse")

    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    aprobar_ambos(tmp_path, registro)
    resultado = encolar(tmp_path, registro, cola)

    assert (
        drenar_envios(
            registro=registro,
            cola=cola,
            destino=DestinoCualquiera(),
            directorio_salida=tmp_path / "salida",
        )
        == ()
    )
    # Ni una subclase del fake habilita la entrega desde el worker.
    assert (
        drenar_envios(
            registro=registro,
            cola=cola,
            destino=type("FakeHijo", (DestinoConfirmacionesFake,), {})(),
            directorio_salida=tmp_path / "salida",
        )
        == ()
    )
    assert len(cola.pendientes()) == 1
    assert registro.obtener(resultado.idempotency_key).estado == "ENVIO_ENCOLADO"


def test_reintento_tras_falla_transitoria_termina_entregado(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    aprobar_ambos(tmp_path, registro)
    resultado = encolar(tmp_path, registro, cola)
    clave = resultado.idempotency_key

    primer_drenaje = drenar_envios(
        registro=registro,
        cola=cola,
        destino=DestinoConfirmacionesFake(error="fallo transitorio"),
        directorio_salida=tmp_path / "salida",
    )
    assert primer_drenaje[0].resolucion == "reintento_pendiente"
    assert primer_drenaje[0].intento == 1
    assert registro.obtener(clave).estado == "ENVIO_ENCOLADO"
    assert cola.pendientes()[0].intentos == 1

    destino = DestinoConfirmacionesFake()
    segundo_drenaje = drenar_envios(
        registro=registro,
        cola=cola,
        destino=destino,
        directorio_salida=tmp_path / "salida",
    )
    assert segundo_drenaje[0].resolucion == "entregada"
    assert segundo_drenaje[0].intento == 2
    assert len(destino.entregas) == 1
    assert registro.obtener(clave).estado == "ENVIADA_SIMULADA"
    assert cola.pendientes() == ()


def test_presupuesto_agotado_deja_la_confirmacion_fallida(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    aprobar_ambos(tmp_path, registro)
    clave = encolar(tmp_path, registro, cola).idempotency_key
    destino = DestinoConfirmacionesFake(error="fallo persistente")

    resoluciones = [
        drenar_envios(
            registro=registro,
            cola=cola,
            destino=destino,
            directorio_salida=tmp_path / "salida",
        )[0]
        for _ in range(3)
    ]

    assert [r.resolucion for r in resoluciones] == [
        "reintento_pendiente",
        "reintento_pendiente",
        "fallida",
    ]
    assert [r.intento for r in resoluciones] == [1, 2, 3]
    assert registro.obtener(clave).estado == "FALLIDA"
    assert cola.pendientes() == ()
    # Un ítem fallido terminal no se reintenta ni se re-entrega.
    assert (
        drenar_envios(
            registro=registro,
            cola=cola,
            destino=DestinoConfirmacionesFake(),
            directorio_salida=tmp_path / "salida",
        )
        == ()
    )


def test_item_sin_presupuesto_restante_falla_sin_intentar(tmp_path):
    """Un ítem que ya consumió su presupuesto en otra corrida no reintenta."""
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    aprobar_ambos(tmp_path, registro)
    clave = encolar(tmp_path, registro, cola).idempotency_key
    item = cola.pendientes()[0]
    cola.reemplazar(
        ItemEnvio(
            idempotency_key=item.idempotency_key,
            destinatario=item.destinatario,
            input_hash=item.input_hash,
            intentos=3,
        )
    )
    destino = DestinoConfirmacionesFake()

    (resultado,) = drenar_envios(
        registro=registro,
        cola=cola,
        destino=destino,
        directorio_salida=tmp_path / "salida",
    )

    assert resultado.resolucion == "fallida"
    assert resultado.intento == 3
    assert destino.entregas == []
    assert registro.obtener(clave).estado == "FALLIDA"


@pytest.mark.parametrize("presupuesto", [0, -1, True, "3"])
def test_presupuesto_invalido_falla_cerrado(tmp_path, presupuesto):
    with pytest.raises(ValueError, match="reintentos"):
        drenar_envios(
            registro=RegistroConfirmacionesMemoria(),
            cola=ColaEnviosMemoria(),
            destino=DestinoConfirmacionesFake(),
            directorio_salida=tmp_path / "salida",
            max_intentos=presupuesto,
        )


# --- Descarte de ítems cuyo registro ya no está pendiente --------------------


def test_item_cuyo_registro_fue_rechazado_no_se_entrega(tmp_path):
    """El ítem quedó encolado pero el registro fue reasignado fuera del pipeline."""
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    aprobar_ambos(tmp_path, registro)
    clave = encolar(tmp_path, registro, cola).idempotency_key
    assert registro.transicionar(
        clave, frozenset({"ENVIO_ENCOLADO"}), "RECHAZADA"
    )
    destino = DestinoConfirmacionesFake()

    (resultado,) = drenar_envios(
        registro=registro,
        cola=cola,
        destino=destino,
        directorio_salida=tmp_path / "salida",
    )

    assert resultado.resolucion == "descartada_sin_entrega"
    assert resultado.estado_registro == "RECHAZADA"
    assert destino.entregas == []
    assert cola.pendientes() == ()


def test_item_de_registro_inexistente_se_descarta(tmp_path):
    cola = ColaEnviosMemoria()
    clave = "a" * 64
    assert cola.encolar(
        ItemEnvio(
            idempotency_key=clave,
            destinatario="nadie@example.test",
            input_hash="b" * 64,
        )
    )
    destino = DestinoConfirmacionesFake()

    (resultado,) = drenar_envios(
        registro=RegistroConfirmacionesMemoria(),
        cola=cola,
        destino=destino,
        directorio_salida=tmp_path / "salida",
    )

    assert resultado.resolucion == "descartada_sin_entrega"
    assert resultado.estado_registro == "AUSENTE"
    assert destino.entregas == []


def test_item_mal_formado_se_descarta_sin_tocar_el_registro(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    aprobar_ambos(tmp_path, registro)
    clave = encolar(tmp_path, registro, ColaEnviosMemoria()).idempotency_key
    cola = ColaEnviosMemoria()
    cola.encolar(
        ItemEnvio(
            idempotency_key=clave,
            destinatario="no-es-un-email",
            input_hash="b" * 64,
        )
    )

    (resultado,) = drenar_envios(
        registro=registro,
        cola=cola,
        destino=DestinoConfirmacionesFake(),
        directorio_salida=tmp_path / "salida",
    )

    assert resultado.resolucion == "descartada_sin_entrega"
    # El ítem inválido no decide el destino del registro: queda encolado para
    # revisión humana, no entregado ni fallido por un ítem ajeno.
    assert registro.obtener(clave).estado == "ENVIO_ENCOLADO"


# --- Durabilidad de la cola ---------------------------------------------------


def test_cola_durable_sobrevive_al_reinicio_y_drena(tmp_path):
    """Un ítem encolado antes de la caída se entrega después del reinicio."""
    registro = RegistroConfirmacionesArchivo(tmp_path / "registro")
    cola = ColaEnviosArchivo(tmp_path / "cola")
    aprobar_ambos(tmp_path, registro)
    encolar(tmp_path, registro, cola)

    registro_reiniciado = RegistroConfirmacionesArchivo(tmp_path / "registro")
    cola_reiniciada = ColaEnviosArchivo(tmp_path / "cola")
    destino = DestinoConfirmacionesFake()
    (resultado,) = drenar_envios(
        registro=registro_reiniciado,
        cola=cola_reiniciada,
        destino=destino,
        directorio_salida=tmp_path / "salida",
    )

    assert resultado.resolucion == "entregada"
    assert len(destino.entregas) == 1
    assert (
        registro_reiniciado.obtener(resultado.idempotency_key).estado
        == "ENVIADA_SIMULADA"
    )
    assert cola_reiniciada.pendientes() == ()


def test_reinicio_a_mitad_de_cola_drena_lo_que_queda(tmp_path):
    """La cola conserva orden e ítems aunque el proceso se reinicie."""
    cola = ColaEnviosArchivo(tmp_path / "cola")
    registro = RegistroConfirmacionesArchivo(tmp_path / "registro")
    solicitudes = [
        solicitud(id_inscripcion=f"INS-COLA-{i:03d}") for i in (1, 2, 3)
    ]
    claves = []
    for s in solicitudes:
        aprobar_ambos(tmp_path, registro, s)
        claves.append(encolar(tmp_path, registro, cola, s).idempotency_key)

    # "Reinicio": instancias nuevas sobre los mismos directorios.
    destino = DestinoConfirmacionesFake()
    resultados = drenar_envios(
        registro=RegistroConfirmacionesArchivo(tmp_path / "registro"),
        cola=ColaEnviosArchivo(tmp_path / "cola"),
        destino=destino,
        directorio_salida=tmp_path / "salida",
    )

    assert [r.idempotency_key for r in resultados] == claves
    assert [e.idempotency_key for e in destino.entregas] == claves


def test_encolado_durable_es_idempotente_entre_procesos(tmp_path):
    cola_a = ColaEnviosArchivo(tmp_path / "cola")
    cola_b = ColaEnviosArchivo(tmp_path / "cola")
    item = ItemEnvio(
        idempotency_key="c" * 64,
        destinatario="ana.perez@example.test",
        input_hash="d" * 64,
    )

    assert cola_a.encolar(item) is True
    assert cola_b.encolar(item) is False
    assert len(ColaEnviosArchivo(tmp_path / "cola").pendientes()) == 1


def test_reserva_colgada_se_reconcilia_y_el_item_no_reentrega(tmp_path):
    """Muerte entre reserva y resultado: la reconciliación cierra y la cola
    descarta el ítem sin volver a entregar."""
    registro = RegistroConfirmacionesArchivo(tmp_path / "registro")
    cola = ColaEnviosArchivo(tmp_path / "cola")
    aprobar_ambos(tmp_path, registro)
    clave = encolar(tmp_path, registro, cola).idempotency_key
    # Simula un worker que reservó y murió antes de saber el resultado.
    assert registro.transicionar(
        clave, frozenset({"ENVIO_ENCOLADO"}), "ENVIO_RESERVADO"
    )

    reconciliadas = reconciliar_envios_reservados(
        RegistroConfirmacionesArchivo(tmp_path / "registro")
    )
    assert [r.idempotency_key for r in reconciliadas] == [clave]

    destino = DestinoConfirmacionesFake()
    (resultado,) = drenar_envios(
        registro=RegistroConfirmacionesArchivo(tmp_path / "registro"),
        cola=ColaEnviosArchivo(tmp_path / "cola"),
        destino=destino,
        directorio_salida=tmp_path / "salida",
    )

    assert resultado.resolucion == "descartada_sin_entrega"
    assert resultado.estado_registro == "ENVIO_INDETERMINADO"
    assert destino.entregas == []
    assert cola.pendientes() == ()


def test_la_cola_durable_guarda_el_item_con_permisos_restrictivos(tmp_path):
    cola = ColaEnviosArchivo(tmp_path / "cola")
    registro = RegistroConfirmacionesArchivo(tmp_path / "registro")
    aprobar_ambos(tmp_path, registro)
    encolar(tmp_path, registro, cola)

    directorio = tmp_path / "cola"
    (archivo,) = list(directorio.glob("*.json"))

    assert directorio.stat().st_mode & 0o777 == 0o700
    assert archivo.stat().st_mode & 0o777 == 0o600
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    assert datos["intentos"] == 0
    assert isinstance(datos["secuencia"], int)


def test_una_clave_que_no_es_un_hash_no_elige_donde_escribe_la_cola(tmp_path):
    cola = ColaEnviosArchivo(tmp_path / "cola")
    item = ItemEnvio(
        idempotency_key="../escape",
        destinatario="ana.perez@example.test",
        input_hash="d" * 64,
    )

    with pytest.raises(ValueError, match="idempotencia"):
        cola.encolar(item)


# --- Auditoría del worker ------------------------------------------------------


def test_cada_intento_del_worker_deja_constancia_auditable(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    aprobar_ambos(tmp_path, registro)
    resultado = encolar(tmp_path, registro, cola)
    destino = DestinoConfirmacionesFake(error="fallo persistente")

    for _ in range(3):
        drenar_envios(
            registro=registro,
            cola=cola,
            destino=destino,
            directorio_salida=tmp_path / "salida",
        )

    lineas = [
        json.loads(linea)
        for linea in (tmp_path / "salida" / "logs" / "confirmaciones-hu012.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    drenajes = [
        linea for linea in lineas if linea.get("evento") == "drenaje_cola_envios"
    ]

    assert [linea["intento"] for linea in drenajes] == [1, 2, 3]
    assert [linea["resultado"] for linea in drenajes] == [
        "delivery_failed_retry_pending",
        "delivery_failed_retry_pending",
        "delivery_failed_budget_exhausted",
    ]
    assert all(
        linea["idempotency_key"] == resultado.idempotency_key
        for linea in drenajes
    )
    assert all(linea["origen_envio"] == "asincrono" for linea in drenajes)
    # La línea del encolado y las del worker comparten el input_hash.
    encolada = next(
        linea for linea in lineas if linea.get("estado") == "ENVIO_ENCOLADO"
    )
    assert all(
        linea["input_hash"] == encolada["input_hash"] for linea in drenajes
    )


def test_la_auditoria_del_worker_no_expone_datos_personales(tmp_path):
    registro = RegistroConfirmacionesMemoria()
    cola = ColaEnviosMemoria()
    aprobar_ambos(tmp_path, registro)
    encolar(tmp_path, registro, cola)

    drenar_envios(
        registro=registro,
        cola=cola,
        destino=DestinoConfirmacionesFake(),
        directorio_salida=tmp_path / "salida",
    )

    texto = (tmp_path / "salida" / "logs" / "confirmaciones-hu012.jsonl").read_text(
        encoding="utf-8"
    )
    for sensible in (
        "ana.perez@example.test",
        "Ana Pérez",
        "Taller de robótica educativa",
        "Confirmación de inscripción",
    ):
        assert sensible not in texto
