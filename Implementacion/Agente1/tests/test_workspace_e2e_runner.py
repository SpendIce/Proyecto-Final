from __future__ import annotations

import json
import hashlib
import stat
import threading
from pathlib import Path

import pytest

from agente1.destinos import DestinoBorradoresError, ReferenciaBorrador
from agente1.procesamiento import FakeGenerator
from agente1.posts import CONTRATO_SALIDA_ESTRUCTURADA
from agente1.workspace_e2e import (
    DestinoMemoria,
    FuenteMemoria,
    RegistroIdempotenciaArchivo,
    RunnerWorkspaceError,
    crear_dependencias_workspace_live,
    ejecutar_workspace_e2e,
)
from agente1.workspace_config import ConfiguracionWorkspace


FILA = {
    "id_solicitud": "SYN-001",
    "titulo": "Taller sintético de vinculación",
    "descripcion": "Actividad ficticia para probar el flujo.",
    "fecha": "2026-08-05",
    "publico": "Comunidad universitaria ficticia",
    "organiza": "Equipo de prueba",
    "contacto": "pruebas@example.invalid",
    "fuente": "Dataset sintético versionado",
    "lugar": "Aula de prueba",
}
GACETILLA = """## TÍTULO
Taller sintético de vinculación

## DATOS DE LA ACTIVIDAD
Fecha: 2026-08-05
Organiza: Equipo de prueba
Lugar: Aula de prueba

## CONTACTO
pruebas@example.invalid

## BAJADA
Actividad ficticia para validar el flujo.

## CUERPO
El Equipo de prueba invita a la Comunidad universitaria ficticia."""
POST = json.dumps(
    {
        "gancho": "Una propuesta para aprender y compartir.",
        "prosa": "Sumate a una experiencia pensada para la comunidad.",
        "cta": "Consultá los datos y participá.",
        "hashtags": ["#Aprender", "#Comunidad"],
    },
    ensure_ascii=False,
)


def _run(tmp_path: Path, *, tipo: str = "gacetilla", canal: str | None = None, respuesta: str = GACETILLA, destino=None):
    return ejecutar_workspace_e2e(
        tipo=tipo,
        canal=canal,
        id_solicitud="SYN-001",
        fuente=FuenteMemoria(FILA),
        generator=FakeGenerator(respuesta),
        destino=destino or DestinoMemoria(),
        directorio_salida=tmp_path / "out",
        registro=RegistroIdempotenciaArchivo(tmp_path / "state"),
        ambiente="OFFLINE",
    )


def test_compone_gacetilla_y_emite_un_manifest_seguro(tmp_path: Path) -> None:
    resultado = _run(tmp_path)

    assert resultado.estado == "PENDIENTE_VALIDACION"
    manifest = json.loads(resultado.manifest_path.read_text(encoding="utf-8"))
    assert manifest["core_correlation_id"] == resultado.correlation_id
    assert manifest["HU"] == "HU-010"
    assert manifest["pipeline_version"] == "workspace_hu010_gacetilla_v1"
    assert manifest["contract_version"] == "gacetilla_input_v1"
    assert manifest["renderer_version"] == "gacetilla_generator_render_v2"
    assert manifest["destination"]["status"] == "COMPLETE"
    serializado = json.dumps(manifest, ensure_ascii=False)
    for secreto in ("SYN-001", "Taller sintético", "pruebas@example.invalid", "Aula de prueba"):
        assert secreto not in serializado


def test_compone_post_y_exige_canal(tmp_path: Path) -> None:
    resultado = _run(tmp_path, tipo="post", canal="instagram", respuesta=POST)
    assert resultado.estado == "PENDIENTE_VALIDACION"
    manifest = json.loads(resultado.manifest_path.read_text(encoding="utf-8"))
    assert manifest["pipeline_version"] == "workspace_hu011_structured_v2"
    assert manifest["contract_version"] == "post_input_v1+post_creative_output_v2"
    assert manifest["renderer_version"] == "post_deterministic_renderer_v2"

    with pytest.raises(RunnerWorkspaceError, match="runner_channel_required"):
        _run(tmp_path / "otro", tipo="post", canal=None, respuesta=POST)


def test_post_v2_audita_modo_y_hash_del_schema_ollama(tmp_path: Path) -> None:
    canonico = json.dumps(
        CONTRATO_SALIDA_ESTRUCTURADA,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    class GeneratorFormato(FakeGenerator):
        format_mode = "json_schema"
        format_schema_hash = hashlib.sha256(canonico).hexdigest()

    resultado = ejecutar_workspace_e2e(
        tipo="post", canal="instagram", id_solicitud="SYN-001",
        fuente=FuenteMemoria(FILA), generator=GeneratorFormato(POST),
        destino=DestinoMemoria(), directorio_salida=tmp_path / "out",
        registro=RegistroIdempotenciaArchivo(tmp_path / "state"),
    )

    assert resultado.estado == "PENDIENTE_VALIDACION"
    registro = json.loads(
        (tmp_path / "out" / "logs" / "ejecuciones.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[-1]
    )
    assert registro["generation_format"] == "json_schema"
    assert registro["format_schema_hash"] == hashlib.sha256(canonico).hexdigest()


def test_rechaza_tipo_o_canal_antes_de_invocar_la_fuente(tmp_path: Path) -> None:
    fuente = FuenteMemoria(FILA)
    with pytest.raises(RunnerWorkspaceError, match="runner_type_invalid"):
        ejecutar_workspace_e2e(
            tipo="email",
            canal=None,
            id_solicitud="SYN-001",
            fuente=fuente,
            generator=FakeGenerator(GACETILLA),
            destino=DestinoMemoria(),
            directorio_salida=tmp_path,
            registro=RegistroIdempotenciaArchivo(tmp_path / "state"),
        )
    assert fuente.invocaciones == 0


def test_fallo_generador_no_crea_destino_y_es_reintentable(tmp_path: Path) -> None:
    class Roto:
        modelo = "fake-roto"
        num_predict = None

        def generar(self, prompt: str) -> str:
            raise RuntimeError("secreto que no debe filtrarse")

    destino = DestinoMemoria()
    resultado = ejecutar_workspace_e2e(
        tipo="gacetilla", canal=None, id_solicitud="SYN-001",
        fuente=FuenteMemoria(FILA), generator=Roto(), destino=destino,
        directorio_salida=tmp_path / "out",
        registro=RegistroIdempotenciaArchivo(tmp_path / "state"),
    )
    assert resultado.estado == "FALLIDA"
    assert destino.invocaciones == 0
    assert "secreto" not in resultado.manifest_path.read_text(encoding="utf-8")


def test_reintento_no_duplica_un_destino_completado(tmp_path: Path) -> None:
    destino = DestinoMemoria()
    primero = _run(tmp_path, destino=destino)
    segundo = _run(tmp_path, destino=destino)

    assert primero.estado == "PENDIENTE_VALIDACION"
    assert segundo.estado == "DUPLICADA"
    assert segundo.duplicada is True
    assert destino.invocaciones == 1


def test_fallo_destino_con_huerfano_conserva_hash_y_bloquea_repeticion(tmp_path: Path) -> None:
    hash_huerfano = "a" * 64

    class DestinoHuerfano:
        def __init__(self) -> None:
            self.invocaciones = 0

        def guardar(self, id_solicitud: str, contenido: str) -> ReferenciaBorrador:
            self.invocaciones += 1
            raise DestinoBorradoresError(
                "docs_update_failed_orphaned",
                reconciliation_ref_hash=hash_huerfano,
            )

    destino = DestinoHuerfano()
    primero = _run(tmp_path, destino=destino)
    segundo = _run(tmp_path, destino=destino)

    assert primero.estado == "FALLIDA"
    assert primero.reconciliation_ref_hash == hash_huerfano
    assert segundo.estado == "BLOQUEADA_RECONCILIACION"
    assert segundo.reconciliation_ref_hash == hash_huerfano
    assert destino.invocaciones == 1


def test_registro_archivo_es_privado_y_persiste_entre_instancias(tmp_path: Path) -> None:
    destino = DestinoMemoria()
    _run(tmp_path, destino=destino)
    _run(tmp_path, destino=destino)
    archivos = list((tmp_path / "state").glob("*.json"))
    assert len(archivos) == 1
    assert stat.S_IMODE(archivos[0].stat().st_mode) == 0o600


class _Token:
    def obtener_access_token(self) -> str:
        return "token-efimero"


class _Transport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def request(self, *, method, host, target, headers, body, deadline, max_response_bytes):
        from agente1.google_workspace import RespuestaHttp

        self.calls.append((method, host, target))
        if host == "sheets.googleapis.com":
            values = [list(FILA), list(FILA.values())]
            return RespuestaHttp(200, json.dumps({"values": values}).encode())
        if host == "www.googleapis.com":
            return RespuestaHttp(200, b'{"id":"doc-opaco-1"}')
        return RespuestaHttp(200, b"{}")


def _config() -> ConfiguracionWorkspace:
    return ConfiguracionWorkspace(
        ambiente="D2", spreadsheet_id="sheet-private", rango_a1="Datos!A1:I10",
        folder_id="folder-private", template_id="template-private",
        timeout_s=10.0, max_response_bytes=1_048_576,
    )


def test_live_requiere_doble_opt_in_y_token_valido() -> None:
    with pytest.raises(RunnerWorkspaceError, match="runner_live_not_enabled"):
        crear_dependencias_workspace_live(
            habilitar_live=False, confirmar_escritura=True, config=_config(),
            token_provider=_Token(), transport=_Transport(),
        )
    with pytest.raises(RunnerWorkspaceError, match="runner_live_write_not_confirmed"):
        crear_dependencias_workspace_live(
            habilitar_live=True, confirmar_escritura=False, config=_config(),
            token_provider=_Token(), transport=_Transport(),
        )

    config_invalida = ConfiguracionWorkspace(
        ambiente="D2", spreadsheet_id="sheet-private", rango_a1="Datos!A1:I10",
        folder_id="folder-private", template_id="template-private",
        timeout_s=10.0, max_response_bytes=42,
    )
    with pytest.raises(RunnerWorkspaceError, match="runner_live_config_invalid"):
        crear_dependencias_workspace_live(
            habilitar_live=True, confirmar_escritura=True, config=config_invalida,
            token_provider=_Token(), transport=_Transport(),
        )


def test_live_solo_usa_sheets_copy_y_batch_update(tmp_path: Path) -> None:
    transport = _Transport()
    fuente, destino = crear_dependencias_workspace_live(
        habilitar_live=True, confirmar_escritura=True, config=_config(),
        token_provider=_Token(), transport=transport,
    )
    resultado = ejecutar_workspace_e2e(
        tipo="gacetilla", canal=None, id_solicitud="SYN-001", fuente=fuente,
        generator=FakeGenerator(GACETILLA), destino=destino,
        directorio_salida=tmp_path / "out",
        registro=RegistroIdempotenciaArchivo(tmp_path / "state"), ambiente="D2",
        live=True,
    )
    assert resultado.estado == "PENDIENTE_VALIDACION"
    assert [(m, h) for m, h, _ in transport.calls] == [
        ("GET", "sheets.googleapis.com"),
        ("POST", "www.googleapis.com"),
        ("POST", "docs.googleapis.com"),
    ]
    targets = " ".join(target for _, _, target in transport.calls)
    assert "permissions" not in targets
    assert "send" not in targets
    assert "publish" not in targets


def test_manifest_live_no_expone_ids_token_referencia_ni_paths(tmp_path: Path) -> None:
    transport = _Transport()
    fuente, destino = crear_dependencias_workspace_live(
        habilitar_live=True, confirmar_escritura=True, config=_config(),
        token_provider=_Token(), transport=transport,
    )
    resultado = ejecutar_workspace_e2e(
        tipo="gacetilla", canal=None, id_solicitud="SYN-001", fuente=fuente,
        generator=FakeGenerator(GACETILLA), destino=destino,
        directorio_salida=tmp_path / "out",
        registro=RegistroIdempotenciaArchivo(tmp_path / "state"), ambiente="D2", live=True,
    )
    texto = resultado.manifest_path.read_text(encoding="utf-8")
    for secreto in (
        "SYN-001", "sheet-private", "folder-private", "template-private",
        "token-efimero", "doc-opaco-1", str(tmp_path), "pruebas@example.invalid",
    ):
        assert secreto not in texto


def test_registro_corrupto_bloquea_sin_copiar_campos_al_manifest(tmp_path: Path) -> None:
    registro = RegistroIdempotenciaArchivo(tmp_path / "state")
    # Se obtiene el nombre opaco mediante una primera reserva válida y luego se
    # simula corrupción local; el runner debe fallar cerrado y sanitizarla.
    _run(tmp_path)
    archivo = next((tmp_path / "state").glob("*.json"))
    archivo.write_text('{"status":"COMPLETE","destination_type":"secreto@example.invalid"}', encoding="utf-8")

    resultado = _run(tmp_path)
    texto = resultado.manifest_path.read_text(encoding="utf-8")
    assert resultado.estado == "BLOQUEADA_RECONCILIACION"
    assert "secreto@example.invalid" not in texto


def test_timestamp_futuro_bloquea_y_nunca_se_toma_como_complete(tmp_path: Path) -> None:
    _run(tmp_path)
    archivo = next((tmp_path / "state").glob("*.json"))
    payload = json.loads(archivo.read_text(encoding="utf-8"))
    payload["updated_at"] = "2999-01-01T00:00:00+00:00"
    archivo.write_text(json.dumps(payload), encoding="utf-8")

    resultado = _run(tmp_path)
    assert resultado.estado == "BLOQUEADA_RECONCILIACION"


def test_timestamp_ausente_bloquea_y_nunca_se_toma_como_complete(tmp_path: Path) -> None:
    _run(tmp_path)
    archivo = next((tmp_path / "state").glob("*.json"))
    payload = json.loads(archivo.read_text(encoding="utf-8"))
    payload.pop("updated_at")
    archivo.write_text(json.dumps(payload), encoding="utf-8")

    assert _run(tmp_path).estado == "BLOQUEADA_RECONCILIACION"


def test_carrera_reserva_una_sola_escritura_y_bloquea_in_progress(tmp_path: Path) -> None:
    entro = threading.Event()
    liberar = threading.Event()

    class DestinoLento(DestinoMemoria):
        def guardar(self, id_solicitud: str, contenido: str) -> ReferenciaBorrador:
            entro.set()
            assert liberar.wait(timeout=5)
            return super().guardar(id_solicitud, contenido)

    destino = DestinoLento()
    resultados = []
    hilo = threading.Thread(target=lambda: resultados.append(_run(tmp_path, destino=destino)))
    hilo.start()
    assert entro.wait(timeout=5)
    bloqueada = _run(tmp_path, destino=destino)
    liberar.set()
    hilo.join(timeout=5)

    assert bloqueada.estado == "BLOQUEADA_RECONCILIACION"
    assert [resultado.estado for resultado in resultados] == ["PENDIENTE_VALIDACION"]
    assert destino.invocaciones == 1
