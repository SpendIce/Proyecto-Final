#!/usr/bin/env python3
"""Servidor del canal web del Agente 1 (issue #149, ADR 0014/0016).

Levanta la app FastAPI con uvicorn. Todo lo institucional llega por
entorno; el repositorio no guarda client IDs, dominios ni credenciales:

- `AGENTE1_POSTGRES_DSN` (obligatoria): DSN de la base con las
  migraciones 0004+ aplicadas; en producción conecta como `agente1_app`.
- `AGENTE1_WEB_GOOGLE_CLIENT_ID` (obligatoria en modo real): el client
  ID que DSI entrega (#62). Declarado junto a `AGENTE1_WEB_MODO_PRUEBA=si`
  es un fallo de arranque: el modo prueba no convive con un client ID.
- `AGENTE1_WEB_DOMINIO` (obligatoria en modo real): dominio `hd`
  institucional exigido al token. Sin dominio el canal cierra el
  arranque, porque `hd` es el único límite de la cuenta.
- `AGENTE1_PADRON_ROLES_CSV` (obligatoria): padrón de roles (ADR 0005).
- `AGENTE1_TABLA` (obligatoria): CSV de actividades de la fuente, para el
  select condicional del pedido.
- `AGENTE1_WEB_MODO_PRUEBA=si`: verificador fake sin Google — el token
  `prueba:<correo>` ingresa con ese correo sintético. Sólo desarrollo y
  evidencia: el arranque se niega si corre con cookie `Secure`, con host
  que no sea loopback o dentro del contenedor (`AGENTE1_CONTENEDOR=si`,
  que declara el compose).
- `AGENTE1_WEB_MODO_DEMO=si` (ADR 0019): demostración sin verificación de
  Google — `/ingresar` ofrece elegir una identidad de una lista cerrada
  del padrón. Exige `AGENTE1_WEB_DEMO_HASTA=AAAA-MM-DD` (último día
  válido, a lo sumo 14 días adelante) y `AGENTE1_WEB_DEMO_CORREOS`
  (correos separados por coma, todos con rol en el padrón). No convive
  con el modo prueba ni con un client ID de Google, y exige cookie
  `Secure`. A diferencia del modo prueba sí corre dentro del contenedor
  y en `0.0.0.0`: la exposición la limita el compose (el puerto se
  publica sólo en `127.0.0.1` del host) y el acceso entra por
  `tailscale serve` dentro del tailnet o por túnel SSH.
- `AGENTE1_WEB_COOKIE_SECURE=no`: permite probar por HTTP local. Default
  `si`, como exige la cookie `Secure` del diseño.
- `AGENTE1_WEB_HOST` / `AGENTE1_WEB_PORT`: escucha (default 127.0.0.1:8080).
- `AGENTE1_WEB_CORREOS_PRUEBA`: correos sintéticos habilitados por el
  verificador fake, separados por coma (`a@example.invalid,b@…`).
- `AGENTE1_WEB_DOCS=si` (#153): el servidor construye el exportador de
  Docs sobre Drive real con la config `AGENTE1_WORKSPACE_*` — la misma
  que usa el worker con `--destino-docs`— y habilita «Traer cambios» y
  «Aprobar/Descartar». Si la config falta o es inválida el arranque
  cierra con `web_workspace_config_invalid`; sin la variable los botones
  no aparecen y los POST responden `exportador_ausente`.
- `AGENTE1_AUDIENCIAS_PATH` (ADR 0021): ruta del catálogo externo de
  audiencias institucionales (fuera del repo, como el padrón). Declarada,
  habilita la preselección de públicos en el pedido, el bloque «Preparar
  correo» tras la aprobación y la ruta `/solicitudes/{id}/correo`. Si el
  archivo no carga o le falta el mapeo de un público del contrato el
  arranque cierra con `web_audiencias_invalid`; sin la variable el
  prellenado queda apagado y `/correo` muestra el motivo.

Uso:

    python scripts/servidor_web.py
"""

from __future__ import annotations

import argparse
import functools
import os
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _invalida(code: str) -> int:
    import json

    print(json.dumps({"status": "INVALID", "error_code": code}, sort_keys=True))
    return 2


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Servidor del canal web del Agente 1 (ADR 0014/0016)."
    )
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument(
        "--una-ruta",
        action="store_true",
        help="Construye la app y verifica el arranque sin levantar uvicorn.",
    )
    args = parser.parse_args(argv)
    entorno = environ if environ is not None else os.environ

    dsn = entorno.get("AGENTE1_POSTGRES_DSN")
    padron_csv = entorno.get("AGENTE1_PADRON_ROLES_CSV")
    tabla = entorno.get("AGENTE1_TABLA")
    if not dsn or not padron_csv or not tabla:
        return _invalida("web_config_incomplete")

    from agente1.canal_form import cargar_padron_roles_csv
    from agente1.fuentes import CsvFuenteSolicitudes
    from agente1.web.app import (
        CLIENT_ID_PRUEBA,
        ConfiguracionInvalida,
        ConfiguracionWeb,
        crear_app,
    )
    from agente1.web.persistencia import RepositorioWeb, conectar

    modo_prueba = entorno.get("AGENTE1_WEB_MODO_PRUEBA", "").lower() == "si"
    modo_demo = entorno.get("AGENTE1_WEB_MODO_DEMO", "").lower() == "si"
    demo_hasta = None
    demo_correos: tuple[str, ...] = ()
    if modo_demo:
        # La fecha se parsea acá para que una cadena mal armada cierre el
        # arranque con su propio código antes de armar la config.
        cruda = entorno.get("AGENTE1_WEB_DEMO_HASTA", "")
        try:
            demo_hasta = (
                datetime.strptime(cruda.strip(), "%Y-%m-%d").date()
                if cruda.strip()
                else None
            )
        except ValueError:
            return _invalida("web_demo_hasta_invalid")
        demo_correos = tuple(
            correo.strip()
            for correo in entorno.get(
                "AGENTE1_WEB_DEMO_CORREOS", ""
            ).split(",")
            if correo.strip()
        )
    if modo_demo or modo_prueba:
        # Ninguno de los dos modos verifica con Google: el fake cubre el
        # puerto `VerificadorIdToken`, aunque el modo demo resuelve el
        # ingreso por su propia rama y nunca llega a `verificar`.
        from agente1.web.identidad import VerificadorFake

        verificador = VerificadorFake({})
    if modo_demo:
        # El client ID viaja a la config tal como lo declara el entorno:
        # si hay uno, `validar_configuracion` cierra el arranque — el
        # modo demo no convive con la verificación de Google (ADR 0019).
        client_id = entorno.get("AGENTE1_WEB_GOOGLE_CLIENT_ID") or ""
    elif modo_prueba:
        from agente1.web.identidad import (
            IdentidadVerificada,
            VerificadorFake,
        )

        identidades = {}
        for correo in entorno.get(
            "AGENTE1_WEB_CORREOS_PRUEBA", ""
        ).split(","):
            correo = correo.strip()
            if correo:
                identidades[f"prueba:{correo}"] = IdentidadVerificada(
                    sub=f"prueba-sub-{correo}", correo=correo, hd=None
                )
        verificador = VerificadorFake(identidades)
        # Si el entorno declara un client ID de Google a la vez que el
        # modo prueba, la config llega con él y `validar_configuracion`
        # cierra el arranque: el modo prueba no convive con un client ID.
        client_id = (
            entorno.get("AGENTE1_WEB_GOOGLE_CLIENT_ID") or CLIENT_ID_PRUEBA
        )
    else:
        from agente1.web.identidad import VerificadorGoogle

        client_id = entorno.get("AGENTE1_WEB_GOOGLE_CLIENT_ID")
        dominio = entorno.get("AGENTE1_WEB_DOMINIO")
        if not client_id:
            return _invalida("web_google_client_id_ausente")
        if not dominio:
            return _invalida("web_dominio_ausente")
        verificador = VerificadorGoogle(
            client_id=client_id, dominio=dominio
        )

    try:
        padron = cargar_padron_roles_csv(Path(padron_csv))
    except Exception:
        return _invalida("web_padron_invalid")
    try:
        actividades = CsvFuenteSolicitudes(Path(tabla)).enumerar()
    except Exception:
        return _invalida("web_fuente_invalid")

    host = args.host or entorno.get("AGENTE1_WEB_HOST", "127.0.0.1")
    config = ConfiguracionWeb(
        google_client_id=client_id,
        dominio_hd=entorno.get("AGENTE1_WEB_DOMINIO") or None,
        modo_prueba=modo_prueba,
        modo_demo=modo_demo,
        demo_hasta=demo_hasta,
        demo_correos=demo_correos,
        cookie_secure=entorno.get("AGENTE1_WEB_COOKIE_SECURE", "si") != "no",
    )
    repositorio = RepositorioWeb(functools.partial(conectar, dsn))
    from agente1.certificados_emision import recursos_firma_opcional
    from agente1.web.certificados_web import RepositorioLotes

    lotes = RepositorioLotes(functools.partial(conectar, dsn))
    recursos_firma = recursos_firma_opcional(
        entorno.get("AGENTE1_CERTIFICADOS_RECURSOS_DIR")
    )
    # La página del lote informa el estado real de la plantilla y asienta
    # la aprobación en el registro que lee la emisión (#168). Sin las
    # variables, la página no puede verificarlas y lo declara.
    plantillas_aprobadas = None
    if entorno.get("AGENTE1_PLANTILLAS_APROBADAS_PATH"):
        from agente1.plantillas_aprobadas import cargar_plantillas_aprobadas
        from agente1.workspace_config import ConfiguracionWorkspaceError

        try:
            plantillas_aprobadas = cargar_plantillas_aprobadas(entorno)
        except ConfiguracionWorkspaceError:
            plantillas_aprobadas = None
    registro_decisiones = None
    if entorno.get("AGENTE1_DECISIONES_DIR"):
        from agente1.decisiones_form import RegistroDecisiones

        registro_decisiones = RegistroDecisiones(
            Path(entorno["AGENTE1_DECISIONES_DIR"])
        )
    catalogo = None
    audiencias_path = entorno.get("AGENTE1_AUDIENCIAS_PATH")
    if audiencias_path:
        # El catálogo externo es fail-closed igual que el padrón: si el
        # archivo declarado no carga, no hay despliegue válido que servir.
        try:
            from agente1.audiencias import cargar_audiencias

            catalogo = cargar_audiencias(audiencias_path)
        except Exception:
            return _invalida("web_audiencias_invalid")
    exportador = None
    if entorno.get("AGENTE1_WEB_DOCS", "").lower() == "si":
        # El Doc por solicitud (#153) se sirve sobre Drive real. Si la
        # config Workspace falta o es inválida el arranque cierra, igual
        # que el worker con `--destino-docs`: nunca cae en silencio a un
        # canal sin Doc.
        try:
            from agente1.workspace_auth import construir_token_provider
            from agente1.workspace_config import (
                ConfiguracionWorkspaceError,
                cargar_configuracion_workspace,
            )

            config_ws = cargar_configuracion_workspace(entorno)
            token_provider = construir_token_provider(
                entorno,
                timeout_s=config_ws.timeout_s,
                directorio_auditoria=Path(
                    entorno.get("AGENTE1_ESTADO") or "."
                ),
            )
        except ConfiguracionWorkspaceError:
            return _invalida("web_workspace_config_invalid")
        from agente1.google_workspace import GoogleDocsDestinoPorMarca

        exportador = GoogleDocsDestinoPorMarca(
            plantilla_id=config_ws.template_id,
            carpeta_id=config_ws.folder_id,
            token_provider=token_provider,
            timeout_s=config_ws.timeout_s,
        )
    try:
        app = crear_app(
            config=config,
            verificador=verificador,
            padron=padron,
            repositorio=repositorio,
            actividades=actividades,
            host=host,
            en_contenedor=(
                entorno.get("AGENTE1_CONTENEDOR", "").lower() == "si"
            ),
            exportador=exportador,
            lotes=lotes,
            recursos_firma=recursos_firma,
            registro_decisiones=registro_decisiones,
            plantillas_aprobadas=plantillas_aprobadas,
            catalogo_audiencias=catalogo,
        )
    except ConfiguracionInvalida as error:
        # El motivo (p. ej. los ids de públicos sin audiencia mapeada) va a
        # stderr: nunca lleva direcciones, sólo ids del contrato.
        print(str(error), file=sys.stderr)
        return _invalida(error.code)
    if args.una_ruta:
        print('{"status": "OK"}')
        return 0

    import uvicorn

    uvicorn.run(
        app,
        host=host,
        port=args.port or int(entorno.get("AGENTE1_WEB_PORT", "8080")),
        log_level="warning",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
