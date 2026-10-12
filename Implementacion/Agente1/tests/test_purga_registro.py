"""Purga de datos personales del registro de confirmaciones (#87).

La retención acotada (ADR 0009, término del glosario): el texto del borrador
y los datos de la persona viven en el registro sólo durante el ciclo de
envío y la ventana de reconciliación de 30 días. Vencida la ventana, un
registro en estado terminal se reescribe sin `asunto` ni `cuerpo` y
conserva la clave de idempotencia, el estado, las fechas y el hash del
contenido borrado, así que purgar nunca habilita un reenvío.

`ENVIO_INDETERMINADO` (y su par de certificados, `EMISION_INDETERMINADA`),
todo estado no terminal y cualquier estado desconocido no se tocan:
siguen a la vista hasta que una persona decida. Cada corrida deja una
línea de auditoría con la cantidad purgada y un hash del conjunto de
claves, nunca contenido.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys

import pytest

from agente1.confirmaciones import (
    AprobacionHumana,
    DestinoConfirmacionesFake,
    ESTADOS_PURGABLES,
    RegistroConfirmacionesArchivo,
    ROL_APROBACION_SEMANTICA,
    ROL_APROBACION_UTILITARIA,
    SolicitudConfirmacion,
    VENTANA_RECONCILIACION_DIAS,
    _hash,
    correr_purga_registro,
    procesar_confirmacion,
)


ROOT = Path(__file__).parents[1]
CLAVE_A = "a" * 64
CLAVE_B = "b" * 64
AHORA = datetime(2026, 10, 12, 15, 0, 0, tzinfo=timezone.utc)
HACE_VENCIDA = AHORA - timedelta(days=VENTANA_RECONCILIACION_DIAS + 1)
DENTRO_VENTANA = AHORA - timedelta(days=VENTANA_RECONCILIACION_DIAS - 1)
TEXTO_PERSONAL = "Confirmamos la inscripción de Ana Pérez, DNI 30.123.456"


def solicitud(**cambios: str) -> SolicitudConfirmacion:
    datos = {
        "id_inscripcion": "INS-PURGA-001",
        "nombre_destinatario": "Ana Pérez",
        "email_destinatario": "ana.perez@example.test",
        "actividad": "Taller sintético de extensión",
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


def registro_viejo(tmp_path: Path) -> RegistroConfirmacionesArchivo:
    """Registro cuyo reloj está corrido atrás: todo lo que se escriba con él
    queda fechado fuera de la ventana de reconciliación."""

    return RegistroConfirmacionesArchivo(
        tmp_path / "registro", clock=lambda: HACE_VENCIDA
    )


def crear_en_estado(
    registro: RegistroConfirmacionesArchivo, clave: str, estado: str
) -> None:
    assert registro.crear(clave, "Asunto con nombre", TEXTO_PERSONAL)
    if estado != "PENDIENTE_VALIDACION":
        assert registro.transicionar(
            clave, frozenset({"PENDIENTE_VALIDACION"}), estado
        )


def lineas_auditoria(directorio_salida: Path) -> list[dict]:
    ruta = directorio_salida / "logs" / "confirmaciones-hu012.jsonl"
    if not ruta.exists():
        return []
    return [
        json.loads(linea)
        for linea in ruta.read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]


def test_terminal_vencido_se_purga_y_conserva_traza(tmp_path: Path):
    registro = registro_viejo(tmp_path)
    crear_en_estado(registro, CLAVE_A, "ENVIADA_SIMULADA")
    hash_previo = registro.obtener(CLAVE_A).output_hash

    resultado = correr_purga_registro(
        registro=registro, directorio_salida=tmp_path / "salida", ahora=AHORA
    )

    assert resultado.purgadas == (CLAVE_A,)
    purgado = registro.obtener(CLAVE_A)
    assert purgado is not None
    assert purgado.asunto == "" and purgado.cuerpo == ""
    # La clave sigue siendo el nombre del archivo: la idempotencia no se toca.
    assert (tmp_path / "registro" / f"{CLAVE_A}.json").exists()
    assert purgado.estado == "ENVIADA_SIMULADA"
    assert purgado.creado_en is not None
    assert purgado.actualizado_en is not None
    assert purgado.purgado_en == AHORA.isoformat()
    # El hash del contenido borrado queda como evidencia de qué se purgó.
    assert purgado.output_hash == hash_previo
    assert purgado.output_hash == _hash("Asunto con nombre\n" + TEXTO_PERSONAL)


def test_todos_los_estados_purgables_vencidos_se_purgan(tmp_path: Path):
    registro = registro_viejo(tmp_path)
    claves = {}
    for i, estado in enumerate(sorted(ESTADOS_PURGABLES)):
        clave = f"{i:0>2}" + "c" * 62
        crear_en_estado(registro, clave, estado)
        claves[estado] = clave

    purgadas = registro.purgar_terminadas(ahora=AHORA)

    assert set(purgadas) == set(claves.values())
    for estado, clave in claves.items():
        registro_leido = registro.obtener(clave)
        assert registro_leido.estado == estado
        assert registro_leido.asunto == ""
        assert registro_leido.cuerpo == ""


def test_estados_no_terminales_indeterminados_y_desconocidos_no_se_purgan(
    tmp_path: Path,
):
    registro = registro_viejo(tmp_path)
    estados_intocables = (
        "PENDIENTE_VALIDACION",
        "APROBADA_SEMANTICA",
        "APROBADA_UTILITARIA",
        "APROBADA",
        "ENVIO_ENCOLADO",
        "ENVIO_RESERVADO",
        "ENVIO_INDETERMINADO",
        "EMISION_INDETERMINADA",
        "EMISION_RESERVADA",
        "ESTADO_DESCONOCIDO_FUTURO",
    )
    for i, estado in enumerate(estados_intocables):
        crear_en_estado(registro, f"{i:0>2}" + "d" * 62, estado)

    purgadas = registro.purgar_terminadas(ahora=AHORA)

    assert purgadas == ()
    for i, estado in enumerate(estados_intocables):
        registro_leido = registro.obtener(f"{i:0>2}" + "d" * 62)
        assert registro_leido.asunto == "Asunto con nombre"
        assert registro_leido.cuerpo == TEXTO_PERSONAL
        assert registro_leido.purgado_en is None


def test_terminal_reciente_no_se_purga(tmp_path: Path):
    registro = RegistroConfirmacionesArchivo(
        tmp_path / "registro", clock=lambda: DENTRO_VENTANA
    )
    crear_en_estado(registro, CLAVE_A, "ENVIADA_SIMULADA")

    purgadas = registro.purgar_terminadas(ahora=AHORA)

    assert purgadas == ()
    assert registro.obtener(CLAVE_A).cuerpo == TEXTO_PERSONAL


def test_terminal_justo_en_el_corte_no_se_purga(tmp_path: Path):
    """El límite es estricto: en el instante exacto del corte todavía hay
    texto; un segundo más viejo ya es purgable."""
    en_el_corte = AHORA - timedelta(days=VENTANA_RECONCILIACION_DIAS)
    registro = RegistroConfirmacionesArchivo(
        tmp_path / "registro", clock=lambda: en_el_corte
    )
    crear_en_estado(registro, CLAVE_A, "ENVIADA_SIMULADA")
    assert registro.purgar_terminadas(ahora=AHORA) == ()

    recien_vencido = RegistroConfirmacionesArchivo(
        tmp_path / "otro",
        clock=lambda: en_el_corte - timedelta(seconds=1),
    )
    crear_en_estado(recien_vencido, CLAVE_B, "ENVIADA_SIMULADA")
    assert recien_vencido.purgar_terminadas(ahora=AHORA) == (CLAVE_B,)


def test_registro_anterior_a_los_campos_usa_mtime(tmp_path: Path):
    """Un registro escrito antes de que existieran las fechas se mide por el
    `mtime` del archivo, y la purga deja asentada la fecha que usó."""
    directorio = tmp_path / "registro"
    registro = RegistroConfirmacionesArchivo(directorio)
    ruta = directorio / f"{CLAVE_A}.json"
    ruta.write_text(
        json.dumps(
            {
                "estado": "ENVIADA_SIMULADA",
                "asunto": "Asunto viejo",
                "cuerpo": TEXTO_PERSONAL,
            }
        ),
        encoding="utf-8",
    )
    viejo = HACE_VENCIDA.timestamp()
    os.utime(ruta, (viejo, viejo))

    purgadas = registro.purgar_terminadas(ahora=AHORA)

    assert purgadas == (CLAVE_A,)
    purgado = registro.obtener(CLAVE_A)
    assert purgado.asunto == ""
    # La purga deja en `actualizado_en` la fecha del archivo que midió.
    assert purgado.actualizado_en is not None
    assert purgado.output_hash == _hash("Asunto viejo\n" + TEXTO_PERSONAL)


def test_purgar_dos_veces_es_idempotente(tmp_path: Path):
    registro = registro_viejo(tmp_path)
    crear_en_estado(registro, CLAVE_A, "ENVIADA_SIMULADA")

    assert registro.purgar_terminadas(ahora=AHORA) == (CLAVE_A,)
    assert registro.purgar_terminadas(ahora=AHORA) == ()


def test_archivo_ilegible_o_nombre_ajeno_no_se_toca(tmp_path: Path):
    directorio = tmp_path / "registro"
    registro = RegistroConfirmacionesArchivo(directorio)
    (directorio / f"{CLAVE_A}.json").write_text("{no es json", encoding="utf-8")
    (directorio / "notas.json").write_text(
        json.dumps(
            {"estado": "ENVIADA_SIMULADA", "asunto": "x", "cuerpo": "y"}
        ),
        encoding="utf-8",
    )

    assert registro.purgar_terminadas(ahora=AHORA) == ()
    assert (directorio / f"{CLAVE_A}.json").read_text() == "{no es json"
    assert "ENVIADA_SIMULADA" in (directorio / "notas.json").read_text()


def test_auditoria_por_corrida_con_cantidad_y_hash_sin_contenido(
    tmp_path: Path,
):
    salida = tmp_path / "salida"
    registro = registro_viejo(tmp_path)
    crear_en_estado(registro, CLAVE_A, "ENVIADA_SIMULADA")

    resultado = correr_purga_registro(
        registro=registro, directorio_salida=salida, ahora=AHORA
    )
    # Una corrida sin nada que purgar también deja su línea.
    correr_purga_registro(
        registro=registro, directorio_salida=salida, ahora=AHORA
    )

    crudo = (salida / "logs" / "confirmaciones-hu012.jsonl").read_text(
        encoding="utf-8"
    )
    assert "Ana Pérez" not in crudo
    assert TEXTO_PERSONAL not in crudo
    assert "Asunto con nombre" not in crudo
    lineas = [l for l in lineas_auditoria(salida) if l["evento"] == "purga_retencion"]
    assert len(lineas) == 2
    primera, segunda = lineas
    assert primera["purgados"] == 1
    assert primera["claves_hash"] == _hash(CLAVE_A)
    assert primera["ventana_dias"] == VENTANA_RECONCILIACION_DIAS
    assert primera["correlation_id"] == resultado.correlation_id
    assert segunda["purgados"] == 0
    assert segunda["claves_hash"] == _hash("")
    assert segunda["correlation_id"] != primera["correlation_id"]
    # La auditoría previa no se pierde: las líneas anexan, no reemplazan.
    assert resultado.log_path == salida / "logs" / "confirmaciones-hu012.jsonl"


def test_clave_purgada_sigue_bloqueando_la_creacion(tmp_path: Path):
    registro = registro_viejo(tmp_path)
    crear_en_estado(registro, CLAVE_A, "ENVIADA_SIMULADA")
    registro.purgar_terminadas(ahora=AHORA)

    # El archivo sigue ahí: `crear` con la misma clave choca como siempre.
    assert not registro.crear(CLAVE_A, "Otro asunto", "Otro cuerpo")
    assert registro.obtener(CLAVE_A).estado == "ENVIADA_SIMULADA"


def test_confirmacion_enviada_y_purgada_no_se_reenvia(tmp_path: Path):
    """Fin a fin: la doble aprobación envía una vez, la purga borra el texto
    y ningún pedido posterior —con o sin aprobación— vuelve a entregar."""
    salida = tmp_path / "salida"
    registro = RegistroConfirmacionesArchivo(
        tmp_path / "registro", clock=lambda: HACE_VENCIDA
    )
    destino = DestinoConfirmacionesFake()
    solicitud_ = solicitud()

    procesar_confirmacion(
        solicitud=solicitud_,
        directorio_salida=salida,
        registro=registro,
        aprobacion=aprobacion(rol=ROL_APROBACION_SEMANTICA),
    )
    enviada = procesar_confirmacion(
        solicitud=solicitud_,
        directorio_salida=salida,
        registro=registro,
        aprobacion=aprobacion(rol=ROL_APROBACION_UTILITARIA),
        destino=destino,
        enviar=True,
    )
    assert enviada.estado == "ENVIADA_SIMULADA"
    assert len(destino.entregas) == 1

    correr_purga_registro(
        registro=registro, directorio_salida=salida, ahora=AHORA
    )

    # Reintento de envío sin decisión nueva: duplicado, no re-entrega.
    reintento = procesar_confirmacion(
        solicitud=solicitud_,
        directorio_salida=salida,
        registro=registro,
        destino=destino,
        enviar=True,
    )
    assert reintento.estado == "DUPLICADA"
    assert len(destino.entregas) == 1
    # Ni una nueva aprobación ni una corrida sin pedido de envío materializan
    # un borrador nuevo: el registro purgado responde siempre duplicado.
    con_aprobacion = procesar_confirmacion(
        solicitud=solicitud_,
        directorio_salida=salida,
        registro=registro,
        aprobacion=aprobacion(rol=ROL_APROBACION_UTILITARIA),
        destino=destino,
        enviar=True,
    )
    assert con_aprobacion.estado == "DUPLICADA"
    sin_envio = procesar_confirmacion(
        solicitud=solicitud_,
        directorio_salida=salida,
        registro=registro,
    )
    assert sin_envio.estado == "DUPLICADA"
    assert sin_envio.asunto is None and sin_envio.cuerpo is None
    assert len(destino.entregas) == 1


def test_purga_y_idempotencia_sobreviven_al_reinicio(tmp_path: Path):
    salida = tmp_path / "salida"
    registro = registro_viejo(tmp_path)
    crear_en_estado(registro, CLAVE_A, "ENVIADA_SIMULADA")
    correr_purga_registro(
        registro=registro, directorio_salida=salida, ahora=AHORA
    )

    # Otro proceso sobre el mismo directorio ve el registro purgado.
    registro_nuevo = RegistroConfirmacionesArchivo(tmp_path / "registro")
    purgado = registro_nuevo.obtener(CLAVE_A)
    assert purgado.asunto == "" and purgado.purgado_en is not None
    assert not registro_nuevo.crear(CLAVE_A, "Asunto", "Cuerpo")
    assert registro_nuevo.purgar_terminadas(ahora=AHORA) == ()


def test_purga_concurrente_no_deja_registros_rotos(tmp_path: Path):
    registro = registro_viejo(tmp_path)
    claves = [f"{i:0>2}" + "e" * 62 for i in range(12)]
    for clave in claves:
        crear_en_estado(registro, clave, "ENVIADA_SIMULADA")

    # Dos corridas de purga simultáneas y transiciones de lectura de estado:
    # cualquier combinación termina con registros íntegros y a lo sumo una
    # corrida cuenta cada clave.
    with ThreadPoolExecutor(max_workers=4) as pool:
        corridas = list(
            pool.map(
                lambda _: registro.purgar_terminadas(ahora=AHORA),
                range(3),
            )
        )
        lecturas = list(pool.map(registro.obtener, claves))

    total = sorted(clave for corrida in corridas for clave in corrida)
    assert total == claves
    for clave in claves:
        registro_leido = registro.obtener(clave)
        assert registro_leido is not None
        assert registro_leido.estado == "ENVIADA_SIMULADA"
        assert registro_leido.asunto == ""
        assert registro_leido.purgado_en == AHORA.isoformat()
    for registro_leido in lecturas:
        assert registro_leido is not None
        assert registro_leido.estado == "ENVIADA_SIMULADA"


def test_parametros_invalidos_fallan_cerrado(tmp_path: Path):
    registro = RegistroConfirmacionesArchivo(tmp_path / "registro")
    crear_en_estado(registro, CLAVE_A, "ENVIADA_SIMULADA")
    os.utime(
        tmp_path / "registro" / f"{CLAVE_A}.json",
        (HACE_VENCIDA.timestamp(), HACE_VENCIDA.timestamp()),
    )

    with pytest.raises(ValueError):
        registro.purgar_terminadas(
            ahora=datetime(2026, 10, 12, 15, 0, 0)  # sin zona
        )
    with pytest.raises(ValueError):
        registro.purgar_terminadas(ahora=AHORA, ventana_dias=0)
    with pytest.raises(ValueError):
        registro.purgar_terminadas(ahora=AHORA, ventana_dias=-5)
    # Los parámetros malos no purgaron nada.
    assert registro.obtener(CLAVE_A).cuerpo == TEXTO_PERSONAL


def test_cli_purga_registro_manual(tmp_path: Path):
    """El comando manual corre la purga, reporta en JSON y audita: es el
    mismo punto de entrada que el scheduler (#84) invocará una vez por día."""
    salida = tmp_path / "salida"
    registro = registro_viejo(tmp_path)
    crear_en_estado(registro, CLAVE_A, "ENVIADA_SIMULADA")
    crear_en_estado(registro, CLAVE_B, "ENVIO_INDETERMINADO")

    corrida = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "purgar_registro.py"),
            "--registro",
            str(tmp_path / "registro"),
            "--salida",
            str(salida),
            "--ahora",
            AHORA.isoformat(),
        ],
        capture_output=True,
        text=True,
    )

    assert corrida.returncode == 0, corrida.stderr
    reporte = json.loads(corrida.stdout)
    assert reporte["status"] == "OK"
    assert reporte["purgados"] == 1
    assert reporte["claves_hash"] == _hash(CLAVE_A)
    assert "Ana Pérez" not in corrida.stdout
    assert TEXTO_PERSONAL not in corrida.stdout
    assert Path(reporte["log_path"]) == (
        salida / "logs" / "confirmaciones-hu012.jsonl"
    )
    # El indeterminado sigue con su texto; el terminal quedó purgado.
    assert registro.obtener(CLAVE_B).cuerpo == TEXTO_PERSONAL
    assert registro.obtener(CLAVE_A).cuerpo == ""


def test_cli_falla_cerrado_sin_registro(tmp_path: Path):
    corrida = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "purgar_registro.py"),
            "--registro",
            str(tmp_path / "inexistente"),
            "--salida",
            str(tmp_path / "salida"),
        ],
        capture_output=True,
        text=True,
    )

    assert corrida.returncode == 2
    reporte = json.loads(corrida.stdout)
    assert reporte["status"] == "INVALID"
    assert reporte["error_code"] == "purge_arguments_invalid"


def test_cli_rechaza_ahora_sin_zona(tmp_path: Path):
    RegistroConfirmacionesArchivo(tmp_path / "registro")
    corrida = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "purgar_registro.py"),
            "--registro",
            str(tmp_path / "registro"),
            "--salida",
            str(tmp_path / "salida"),
            "--ahora",
            "2026-10-12T15:00:00",
        ],
        capture_output=True,
        text=True,
    )

    assert corrida.returncode == 2
    assert json.loads(corrida.stdout)["status"] == "INVALID"
