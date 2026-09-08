"""Agente 1 — Extension Bot: API pública del paquete.

Se exporta sólo lo que consumen la CLI, los scripts de evidencia y las
pruebas: los pipelines de HU-010/HU-011/HU-012, los generadores y los tipos de
resultado. Todo lo demás (adapters de Workspace, auditoría, persistencia) se
importa por su módulo, para que quede explícito en el código quién sale a la
red y quién no.

Guía rápida de módulos:

- `procesamiento`  HU-010, gacetillas.
- `posts`          HU-011, posts por canal con contrato creativo y renderer.
- `confirmaciones` HU-012, confirmaciones de inscripción (offline, sin envío).
- `fuentes` / `destinos`      puertos de entrada y salida.
- `google_workspace`          adapters de Sheets, Drive y Docs.
- `workspace_e2e`             runner con idempotencia y manifests.
- `workspace_config`          configuración por entorno.
- `ollama`                    generador local.
- `politica_redes`            política de redes como reglas verificables.
- `persistencia`              puerto de persistencia auditable.
- `auditoria_d2`              auditoría offline de invariantes de seguridad.
- `operaciones_seguras`       health, retención y reconciliación.
- `insumos_agentes`           contrato candidato de insumos de A2-A5.
- `historia_viva`             puerto de consulta al acervo de A2 (offline).
- `origenes_inscripcion`      matriz de orígenes de inscripción (HU-012).
"""

from .confirmaciones import (
    AprobacionHumana,
    DestinoConfirmacionesFake,
    RegistroConfirmacionesMemoria,
    ResultadoConfirmacion,
    SolicitudConfirmacion,
    procesar_confirmacion,
)
from .ollama import OllamaGenerator
from .procesamiento import FakeGenerator, ResultadoProceso, procesar_fila_csv
from .posts import PoliticaPost, procesar_post, procesar_post_estructurado

__all__ = [
    "AprobacionHumana",
    "DestinoConfirmacionesFake",
    "FakeGenerator",
    "OllamaGenerator",
    "PoliticaPost",
    "RegistroConfirmacionesMemoria",
    "ResultadoConfirmacion",
    "ResultadoProceso",
    "SolicitudConfirmacion",
    "procesar_confirmacion",
    "procesar_fila_csv",
    "procesar_post",
    "procesar_post_estructurado",
]
