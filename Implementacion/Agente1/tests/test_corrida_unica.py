"""Corrida única del Agente 1 (#132): orden, cortes, secretos y evidencia.

Los tests usan dobles de prueba para el subproceso y para HTTP: no abren red
ni tocan Workspace. La clave de la cuenta de servicio es un JSON sintético en
`tmp_path`, con modo 600, y el entorno se pasa explícito.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "corrida_unica.py"
ROOT = Path(__file__).parents[1]


def _cargar_script():
    spec = importlib.util.spec_from_file_location("corrida_unica_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def _clave(tmp_path: Path, modo: int = 0o600) -> Path:
    ruta = tmp_path / "cuenta-servicio.json"
    ruta.write_text(
        json.dumps(
            {
                "type": "service_account",
                "client_email": "bot@example.iam.gserviceaccount.com",
                "private_key": (
                    "-----BEGIN PRIVATE KEY-----\n"
                    "c2ludGV0aWNv\n"
                    "-----END PRIVATE KEY-----\n"
                ),
            }
        ),
        encoding="utf-8",
    )
    ruta.chmod(modo)
    return ruta


def _entorno(tmp_path: Path, **overrides: str) -> dict[str, str]:
    entorno = {
        "AGENTE1_WORKSPACE_AMBIENTE": "D2",
        "AGENTE1_WORKSPACE_SPREADSHEET_ID": "sheet-sintetica",
        "AGENTE1_WORKSPACE_RANGO_A1": "'Respuestas'!A1:I500",
        "AGENTE1_WORKSPACE_FOLDER_ID": "carpeta-sintetica",
        "AGENTE1_WORKSPACE_TEMPLATE_ID": "plantilla-sintetica",
        "AGENTE1_WORKSPACE_TIMEOUT_S": "180",
        "AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES": "1048576",
        "AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY": str(_clave(tmp_path)),
        "AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT": "bot@example.edu.ar",
    }
    entorno.update(overrides)
    return entorno


def _opciones(modulo, tmp_path: Path, *, live: bool = True, **overrides):
    valores = {
        "live": live,
        "modelo": "llama3.2:3b",
        "ollama_version": "0.40.6",
        "id_solicitud": "SYN-001",
        "presupuesto_min": 45.0,
        "evidencia_dir": tmp_path / "evidencia",
        "root": ROOT,
        "salida_e2e": tmp_path / "workspace-e2e",
    }
    valores.update(overrides)
    return modulo.Opciones(**valores)


def _contexto(
    modulo,
    entorno: dict[str, str],
    *,
    ejecutar,
    consultar,
    salida,
    monotonic=None,
    host: str = "labredesfie",
    commit: str = "a" * 40,
):
    return modulo.Contexto(
        environ=entorno,
        host=host,
        commit=commit,
        python="3.12.14",
        plataforma="Linux-6.8-x86_64",
        ahora=lambda: datetime(2026, 10, 21, 7, 0, tzinfo=timezone.utc),
        monotonic=monotonic or (lambda: 0.0),
        ejecutar=ejecutar,
        consultar=consultar,
        salida=salida,
        root=ROOT,
    )


class _Reloj:
    def __init__(self) -> None:
        self.t = 0.0

    def monotonic(self) -> float:
        return self.t

    def avanzar(self, segundos: float) -> None:
        self.t += segundos


class _Consultar:
    def __init__(
        self,
        *,
        version: str = "0.40.6",
        modelos: tuple[str, ...] = ("llama3.2:3b",),
        reloj: _Reloj | None = None,
        avanzar: float = 0.0,
    ) -> None:
        self.version = version
        self.modelos = modelos
        self.reloj = reloj
        self.avanzar_s = avanzar
        self.consultas: list[str] = []

    def __call__(self, url: str, timeout: float) -> object:
        self.consultas.append(url)
        if self.reloj is not None:
            self.reloj.avanzar(self.avanzar_s)
        if url.endswith("/api/version"):
            return {"version": self.version}
        return {"models": [{"name": nombre} for nombre in self.modelos]}


class _ConsultarQueFalla:
    def __call__(self, url: str, timeout: float) -> object:
        raise AssertionError(f"dry-run no debe consultar {url}")


class _Ejecutor:
    """Doble de subprocess: registra comandos y simula los seis runners."""

    def __init__(
        self,
        modulo,
        *,
        fallar_en: str | None = None,
        salida_extra: str = "",
    ) -> None:
        self.modulo = modulo
        self.fallar_en = fallar_en
        self.salida_extra = salida_extra
        self.comandos: list[list[str]] = []
        self.emitidos = 0
        self.manifiestos = 0

    def __call__(self, comando, cwd, environ, timeout):
        self.comandos.append(list(comando))
        nombre = Path(comando[1]).name
        if nombre == self.fallar_en:
            return self.modulo.ResultadoComando(9, "fallo simulado")

        if nombre == "workspace_smoke.py":
            payload = {
                "resultado": "lectura_confirmada",
                "detalle": self.salida_extra,
            }
            return self.modulo.ResultadoComando(0, json.dumps(payload))

        if nombre == "workspace_e2e.py":
            salida = Path(comando[comando.index("--salida") + 1])
            manifests = salida / "manifests"
            manifests.mkdir(parents=True, exist_ok=True)
            self.manifiestos += 1
            (manifests / f"manifest-{self.manifiestos}.json").write_text(
                "{}", encoding="utf-8"
            )
            return self.modulo.ResultadoComando(
                0, json.dumps({"estado": "PENDIENTE_VALIDACION"})
            )

        if nombre == "emitir_certificados.py":
            directorio = Path(comando[comando.index("--directorio") + 1])
            directorio.mkdir(parents=True, exist_ok=True)
            self.emitidos += 1
            log = directorio / "emisiones-certificados-hu014.jsonl"
            evento = {
                "evento": "solicitud_emision",
                "id_actividad": "SYN-001",
            }
            if self.emitidos == 1:
                evento = {
                    "evento": "linea_descriptiva_no_aprobada",
                    "objeto_linea": "linea_descriptiva-SYN-001-" + "b" * 64,
                }
            elif self.emitidos == 2:
                (directorio / "estado-decisiones").mkdir(
                    parents=True, exist_ok=True
                )
                (
                    directorio / "estado-decisiones" / "decisiones-pendientes.jsonl"
                ).write_text(
                    json.dumps(
                        {
                            "tipo": "lote",
                            "objeto_id": "c" * 64,
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                evento = {"evento": "lista_validada", "cantidad": 2}
            else:
                evento = {"evento": "cierre", "emitidas": 2}
            with log.open("a", encoding="utf-8") as archivo:
                archivo.write(json.dumps(evento) + "\n")
            if self.emitidos == 1:
                return self.modulo.ResultadoComando(
                    0,
                    json.dumps(
                        {
                            "estado": "PENDIENTE_APROBACION",
                            "error": "linea_descriptiva_no_aprobada",
                        }
                    ),
                )
            if self.emitidos == 2:
                return self.modulo.ResultadoComando(
                    0,
                    json.dumps(
                        {
                            "estado": "PENDIENTE_APROBACION",
                            "error": "lote_no_aprobado",
                        }
                    ),
                )
            return self.modulo.ResultadoComando(
                0,
                json.dumps(
                    {
                        "estado": "EMITIDA",
                        "emitidas": 2,
                        "entregas_fallidas": 0,
                    }
                ),
            )

        if nombre == "registrar_form_decisiones.py":
            csv = Path(comando[comando.index("--respuestas-csv") + 1])
            filas = max(0, len(csv.read_text(encoding="utf-8").splitlines()) - 1)
            lineas = [
                json.dumps(
                    {
                        "resultado": "registrada",
                        "tipo": "linea_descriptiva",
                        "objeto_id": "b" * 64,
                    }
                )
                for _ in range(filas)
            ]
            lineas.append(json.dumps({"procesadas": filas}))
            return self.modulo.ResultadoComando(0, "\n".join(lineas))

        if nombre == "atender_canal_form.py":
            return self.modulo.ResultadoComando(
                0,
                "\n".join(
                    [
                        json.dumps(
                            {"intencion": "generar_plantilla_actividad"}
                        ),
                        json.dumps({"atendidos": 1}),
                    ]
                ),
            )

        if nombre == "plantilla_actividad_lote_demo.py":
            return self.modulo.ResultadoComando(
                0,
                "\n".join(
                    [
                        json.dumps({"fase": "generacion"}),
                        json.dumps(
                            {
                                "fase": "lote",
                                "estado": "ENVIO_ENCOLADO",
                                "items": 3,
                            }
                        ),
                    ]
                ),
            )

        raise AssertionError(f"comando inesperado: {comando}")


class _EjecutorQueFalla:
    def __call__(self, comando, cwd, environ, timeout):
        raise AssertionError(f"dry-run no debe ejecutar {comando}")


def _leer_corrida(tmp_path: Path) -> dict[str, object]:
    return json.loads((tmp_path / "evidencia" / "corrida.json").read_text())


def test_orden_de_pasos_y_corrida_live_completa(tmp_path: Path) -> None:
    modulo = _cargar_script()
    entorno = _entorno(tmp_path)
    ejecutor = _Ejecutor(modulo)
    salida = io.StringIO()

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path),
        _contexto(
            modulo,
            entorno,
            ejecutar=ejecutor,
            consultar=_Consultar(),
            salida=salida,
        ),
    )

    assert codigo == 0
    assert [Path(c[1]).name for c in ejecutor.comandos] == [
        "workspace_smoke.py",
        "workspace_e2e.py",
        "emitir_certificados.py",
        "registrar_form_decisiones.py",
        "emitir_certificados.py",
        "registrar_form_decisiones.py",
        "emitir_certificados.py",
        "atender_canal_form.py",
        "plantilla_actividad_lote_demo.py",
    ]
    corrida = _leer_corrida(tmp_path)
    assert [paso["id"] for paso in corrida["pasos"]] == [
        "ollama",
        "smoke",
        "gacetilla",
        "hu014",
        "hu012",
    ]
    assert all(paso["estado"] == "ok" for paso in corrida["pasos"])
    assert all(paso["exit_code"] == 0 for paso in corrida["pasos"])
    assert corrida["resultado"] == "OK"


def test_fail_fast_no_ejecuta_los_pasos_siguientes(tmp_path: Path) -> None:
    modulo = _cargar_script()
    entorno = _entorno(tmp_path)
    ejecutor = _Ejecutor(modulo, fallar_en="workspace_smoke.py")
    salida = io.StringIO()

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path),
        _contexto(
            modulo,
            entorno,
            ejecutar=ejecutor,
            consultar=_Consultar(),
            salida=salida,
        ),
    )

    assert codigo == modulo.EXIT_SMOKE
    assert [Path(c[1]).name for c in ejecutor.comandos] == ["workspace_smoke.py"]
    assert "SMOKE DE WORKSPACE (LECTURA)" in salida.getvalue()
    corrida = _leer_corrida(tmp_path)
    estados = {paso["id"]: paso["estado"] for paso in corrida["pasos"]}
    assert estados["ollama"] == "ok"
    assert estados["smoke"] == "fallo"
    assert corrida["pasos"][1]["exit_code"] == modulo.EXIT_SMOKE
    assert estados["gacetilla"] == "no_ejecutado"
    assert estados["hu012"] == "no_ejecutado"


def test_par_de_credenciales_a_medias_falla_antes_de_todo(tmp_path: Path) -> None:
    modulo = _cargar_script()
    entorno = _entorno(tmp_path)
    del entorno["AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT"]
    salida = io.StringIO()

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path),
        _contexto(
            modulo,
            entorno,
            ejecutar=_EjecutorQueFalla(),
            consultar=_ConsultarQueFalla(),
            salida=salida,
        ),
    )

    assert codigo == modulo.EXIT_PREFLIGHT
    assert "a medias" in salida.getvalue()
    assert "IMPERSONATED_ACCOUNT" in salida.getvalue()
    assert "$ " not in salida.getvalue()


def test_permisos_de_clave_incorrectos_fallan(tmp_path: Path) -> None:
    modulo = _cargar_script()
    entorno = _entorno(tmp_path)
    Path(entorno["AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY"]).chmod(0o644)
    salida = io.StringIO()

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path),
        _contexto(
            modulo,
            entorno,
            ejecutar=_EjecutorQueFalla(),
            consultar=_ConsultarQueFalla(),
            salida=salida,
        ),
    )

    assert codigo == modulo.EXIT_PREFLIGHT
    assert "chmod 600" in salida.getvalue()
    assert "permisos 644" in salida.getvalue()


def test_clave_que_es_directorio_falla(tmp_path: Path) -> None:
    modulo = _cargar_script()
    entorno = _entorno(tmp_path)
    entorno["AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY"] = str(tmp_path)
    salida = io.StringIO()

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path),
        _contexto(
            modulo,
            entorno,
            ejecutar=_EjecutorQueFalla(),
            consultar=_ConsultarQueFalla(),
            salida=salida,
        ),
    )

    assert codigo == modulo.EXIT_PREFLIGHT
    assert "directorio" in salida.getvalue()


def test_clave_con_json_invalido_falla(tmp_path: Path) -> None:
    modulo = _cargar_script()
    entorno = _entorno(tmp_path)
    clave = Path(entorno["AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY"])
    clave.write_text("{esto no es json", encoding="utf-8")
    salida = io.StringIO()

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path),
        _contexto(
            modulo,
            entorno,
            ejecutar=_EjecutorQueFalla(),
            consultar=_ConsultarQueFalla(),
            salida=salida,
        ),
    )

    assert codigo == modulo.EXIT_PREFLIGHT
    assert "JSON" in salida.getvalue()


def test_dry_run_no_ejecuta_ni_toca_red(tmp_path: Path) -> None:
    modulo = _cargar_script()
    entorno = _entorno(tmp_path)
    salida = io.StringIO()

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path, live=False),
        _contexto(
            modulo,
            entorno,
            ejecutar=_EjecutorQueFalla(),
            consultar=_ConsultarQueFalla(),
            salida=salida,
        ),
    )

    assert codigo == 0
    texto = salida.getvalue()
    assert "Plan de la corrida live" in texto
    assert "No se tocó red ni Workspace" in texto
    corrida = _leer_corrida(tmp_path)
    assert corrida["modo"] == "dry-run"
    assert all(paso["estado"] == "omitido" for paso in corrida["pasos"])
    assert corrida["ollama_version"] is None


def test_presupuesto_agotado_corta_antes_del_siguiente_paso(tmp_path: Path) -> None:
    modulo = _cargar_script()
    entorno = _entorno(tmp_path)
    reloj = _Reloj()
    ejecutor = _Ejecutor(modulo)
    salida = io.StringIO()

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path),
        _contexto(
            modulo,
            entorno,
            ejecutar=ejecutor,
            consultar=_Consultar(reloj=reloj, avanzar=3000.0),
            salida=salida,
            monotonic=reloj.monotonic,
        ),
    )

    assert codigo == modulo.EXIT_PRESUPUESTO
    assert ejecutor.comandos == []
    assert "CORTE_PRESUPUESTO" in salida.getvalue()
    assert "Smoke de Workspace" in salida.getvalue()
    corrida = _leer_corrida(tmp_path)
    assert corrida["resultado"] == "CORTE_PRESUPUESTO"
    assert corrida["pasos"][0]["estado"] == "ok"
    assert corrida["pasos"][1]["estado"] == "corte_presupuesto"
    assert corrida["pasos"][2]["estado"] == "no_ejecutado"


def test_redaccion_de_secretos_en_log_y_json(tmp_path: Path) -> None:
    modulo = _cargar_script()
    secreto = "ya29.SUPERSECRETO-QUE-NO-DEBE-SALIR"
    pem = "-----BEGIN PRIVATE KEY-----\nc2VjcmV0bw==\n-----END PRIVATE KEY-----"
    entorno = _entorno(
        tmp_path,
        AGENTE1_WORKSPACE_ACCESS_TOKEN=secreto,
    )
    ruta_clave = entorno["AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY"]
    ejecutor = _Ejecutor(
        modulo,
        salida_extra=f"token={secreto} clave={ruta_clave} pem={pem}",
    )
    salida = io.StringIO()

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path),
        _contexto(
            modulo,
            entorno,
            ejecutar=ejecutor,
            consultar=_Consultar(),
            salida=salida,
        ),
    )

    assert codigo == 0
    transcripcion = (tmp_path / "evidencia" / "transcripcion.log").read_text(
        encoding="utf-8"
    )
    corrida = (tmp_path / "evidencia" / "corrida.json").read_text(
        encoding="utf-8"
    )
    for texto in (transcripcion, corrida):
        assert secreto not in texto
        assert ruta_clave not in texto
        assert "BEGIN PRIVATE KEY" not in texto
    assert "<redactado>" in transcripcion or "<ruta-clave>" in transcripcion


def test_evidencia_declara_host_y_commit(tmp_path: Path) -> None:
    modulo = _cargar_script()
    entorno = _entorno(tmp_path)
    salida = io.StringIO()
    commit = "d" * 40

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path),
        _contexto(
            modulo,
            entorno,
            ejecutar=_Ejecutor(modulo),
            consultar=_Consultar(),
            salida=salida,
            host="labredesfie",
            commit=commit,
        ),
    )

    assert codigo == 0
    host = (tmp_path / "evidencia" / "host.txt").read_text(encoding="utf-8")
    assert "host: labredesfie" in host
    assert f"commit: {commit}" in host
    corrida = _leer_corrida(tmp_path)
    assert corrida["host"] == "labredesfie"
    assert corrida["commit"] == commit
    assert corrida["ollama_version"] == "0.40.6"
    assert corrida["modelo"] == "llama3.2:3b"
    assert (tmp_path / "evidencia" / "transcripcion.log").is_file()


def test_los_secretos_no_viajan_por_argv(tmp_path: Path) -> None:
    modulo = _cargar_script()
    secreto = "secreto-que-no-va-por-argv"
    entorno = _entorno(
        tmp_path,
        AGENTE1_WORKSPACE_ACCESS_TOKEN=secreto,
    )
    ruta_clave = entorno["AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY"]
    ejecutor = _Ejecutor(modulo)
    salida = io.StringIO()

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path),
        _contexto(
            modulo,
            entorno,
            ejecutar=ejecutor,
            consultar=_Consultar(),
            salida=salida,
        ),
    )

    assert codigo == 0
    planos = [" ".join(comando) for comando in ejecutor.comandos]
    assert all(secreto not in comando for comando in planos)
    assert all(ruta_clave not in comando for comando in planos)


def test_version_de_ollama_distinta_corta_con_codigo_propio(
    tmp_path: Path,
) -> None:
    modulo = _cargar_script()
    entorno = _entorno(tmp_path)
    ejecutor = _Ejecutor(modulo)
    salida = io.StringIO()

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path),
        _contexto(
            modulo,
            entorno,
            ejecutar=ejecutor,
            consultar=_Consultar(version="0.40.7"),
            salida=salida,
        ),
    )

    assert codigo == modulo.EXIT_OLLAMA
    assert ejecutor.comandos == []
    assert "0.40.7" in salida.getvalue()
    assert "no actualices" in salida.getvalue()


def test_falla_de_gacetilla_corta_antes_de_hu014(tmp_path: Path) -> None:
    modulo = _cargar_script()
    entorno = _entorno(tmp_path)

    class _EjecutorGacetillaFallida(_Ejecutor):
        def __call__(self, comando, cwd, environ, timeout):
            nombre = Path(comando[1]).name
            if nombre == "workspace_e2e.py":
                self.comandos.append(list(comando))
                return self.modulo.ResultadoComando(
                    4, json.dumps({"estado": "FALLIDA"})
                )
            return super().__call__(comando, cwd, environ, timeout)

    ejecutor = _EjecutorGacetillaFallida(modulo)
    salida = io.StringIO()

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path),
        _contexto(
            modulo,
            entorno,
            ejecutar=ejecutor,
            consultar=_Consultar(),
            salida=salida,
        ),
    )

    assert codigo == modulo.EXIT_GACETILLA
    assert [Path(c[1]).name for c in ejecutor.comandos] == [
        "workspace_smoke.py",
        "workspace_e2e.py",
    ]


def test_ambiente_fuera_de_d2_d3_falla_en_preflight(tmp_path: Path) -> None:
    modulo = _cargar_script()
    entorno = _entorno(tmp_path, AGENTE1_WORKSPACE_AMBIENTE="D4")
    salida = io.StringIO()

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path),
        _contexto(
            modulo,
            entorno,
            ejecutar=_EjecutorQueFalla(),
            consultar=_ConsultarQueFalla(),
            salida=salida,
        ),
    )

    assert codigo == modulo.EXIT_PREFLIGHT
    assert "D4" in salida.getvalue()


def test_falla_inesperada_del_paso_corta_con_mensaje(tmp_path: Path) -> None:
    modulo = _cargar_script()
    entorno = _entorno(tmp_path)

    class _EjecutorRoto:
        def __call__(self, comando, cwd, environ, timeout):
            raise RuntimeError("boom")

    salida = io.StringIO()

    codigo = modulo.ejecutar(
        _opciones(modulo, tmp_path),
        _contexto(
            modulo,
            entorno,
            ejecutar=_EjecutorRoto(),
            consultar=_Consultar(),
            salida=salida,
        ),
    )

    assert codigo == modulo.EXIT_SMOKE
    assert "Falla inesperada del paso (RuntimeError)" in salida.getvalue()
    assert "Traceback" not in salida.getvalue()
