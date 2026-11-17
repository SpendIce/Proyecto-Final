"""Fábrica de `EmisionCertificadosWeb` desde el entorno del proceso (#168).

`construir_emision_certificados_web` siempre devuelve un servicio, aunque
la configuración real esté incompleta: la fábrica no abre la base ni la
red — los repositorios reciben el `conexion_factory` y nadie lo llama en
construcción — y lo que falta (padrón, plantillas, credenciales Gmail)
queda como bloqueo visible en la pantalla o como fallo `destino_*` en la
cola, nunca como una excepción que deje la web caída.

El padrón se relee en cada operación (`padron` va como fábrica), así la
revalidación del rol pega sin reiniciar el proceso. El destino Gmail se
construye dentro del worker, después de todas las barreras de dominio;
`crear_destino_gmail` no hace red hasta `entregar`, pero armarlo tarde
además mantiene la regla de no tocar nada externo en la fábrica.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ..canal_form import PadronRoles, cargar_padron_roles_csv
from ..decisiones_form import RegistroDecisiones
from ..emisiones_certificados import (
    RepositorioEmisiones,
    bloqueos_envio,
    crear_destino_gmail,
    recursos_firma_opcional,
)
from ..gmail_envio import cargar_modo_envio
from ..plantillas_aprobadas import (
    cargar_plantillas_aprobadas,
)
from ..workspace_config import ConfiguracionWorkspaceError
from .certificados_web import RepositorioLotes
from .emision_certificados import EmisionCertificadosWeb


def construir_emision_certificados_web(
    environ: Mapping[str, str] | None = None,
    *,
    conexion_factory: Callable[[], Any],
) -> EmisionCertificadosWeb:
    """Arma el servicio declarado por el entorno, sin tocar red ni DB.

    `conexion_factory` es la única pieza obligatoria: la firma del
    contrato la exige porque la cola vive en PostgreSQL. Todo lo demás
    degrada a bloqueo, no a error de arranque.
    """
    env = dict(os.environ if environ is None else environ)
    modo_demo = env.get("AGENTE1_WEB_MODO_DEMO", "").strip().lower() == "si"

    try:
        modo_envio = cargar_modo_envio(env)
    except ConfiguracionWorkspaceError:
        # El código exacto (`gmail_mode_invalid`) ya va en bloqueos_envio.
        modo_envio = None

    padron_path = env.get("AGENTE1_PADRON_ROLES_CSV")

    def _padron_fresco() -> PadronRoles | None:
        if not padron_path or not padron_path.strip():
            return None
        try:
            return cargar_padron_roles_csv(Path(padron_path.strip()))
        except Exception:
            return None

    registro_decisiones = None
    decisiones_dir = env.get("AGENTE1_DECISIONES_DIR")
    if decisiones_dir and decisiones_dir.strip():
        registro_decisiones = RegistroDecisiones(Path(decisiones_dir.strip()))

    plantillas_aprobadas = None
    bloqueos_config: list[str] = list(bloqueos_envio(env))
    if env.get("AGENTE1_PLANTILLAS_APROBADAS_PATH"):
        try:
            plantillas_aprobadas = cargar_plantillas_aprobadas(env)
        except ConfiguracionWorkspaceError as error:
            bloqueos_config.append(error.code)
    # El destino se construye recién cuando el worker lo pide: armarlo
    # acá sería trabajo muerto en la web y tocaría archivos de
    # credenciales en cada arranque.
    directorio_salida = (
        Path(env["AGENTE1_ESTADO"].strip()) / "emisiones"
        if env.get("AGENTE1_ESTADO", "").strip()
        else Path("emisiones")
    )

    return EmisionCertificadosWeb(
        lotes=RepositorioLotes(conexion_factory),
        emisiones=RepositorioEmisiones(conexion_factory),
        padron=_padron_fresco,
        registro_decisiones=registro_decisiones,
        directorio_salida=directorio_salida,
        fabrica_destino=lambda: crear_destino_gmail(
            env, directorio_auditoria=directorio_salida
        ),
        recursos_firma=recursos_firma_opcional(
            env.get("AGENTE1_CERTIFICADOS_RECURSOS_DIR")
        ),
        plantillas_aprobadas=plantillas_aprobadas,
        modo_demo=modo_demo,
        modo_envio=modo_envio,
        bloqueos_config=tuple(bloqueos_config),
    )


__all__ = ["construir_emision_certificados_web"]
