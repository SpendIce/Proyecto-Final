"""Agente 1 — Extension Bot: API pública del paquete.

Se exporta sólo lo que consumen la CLI, los scripts de evidencia y las
pruebas: los pipelines de HU-010/HU-011/HU-012, los generadores y los tipos de
resultado. Todo lo demás (adapters de Workspace, auditoría, persistencia) se
importa por su módulo, para que quede explícito en el código quién sale a la
red y quién no.

Guía rápida de módulos:

- `procesamiento`  HU-010, gacetillas.
- `posts`          HU-011, posts por canal con contrato creativo y renderer.
- `confirmaciones` HU-012, notificaciones a inscriptos (fake, o Gmail con
                             lista de prueba).
- `fuentes` / `destinos`      puertos de entrada y salida.
- `google_workspace`          adapters de Sheets, Drive y Docs.
- `gmail_envio`               adapter de `gmail.send` con lista de prueba.
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
- `tipos_notificacion`        catálogo de tipos de notificación (HU-012).
- `interpretacion`            HU-013, interpretación en lenguaje natural (#20, #22).
- `canal`                     HU-013, puerto de canal y bucle de atención (#24).
- `canal_planilla`            HU-013, adapter de planilla offline del canal (#24).
- `pagos`                     HU-012, corrida de control de pagos (offline).
- `buzon`                     puerto del buzón propio del agente (ADR 0004).
"""

from .confirmaciones import (
    AprobacionHumana,
    ColaEnviosArchivo,
    ColaEnviosMemoria,
    DestinoConfirmacionesFake,
    EntregaRechazadaError,
    ItemEnvio,
    RegistroConfirmacionesArchivo,
    RegistroConfirmacionesMemoria,
    ReservaReconciliada,
    ResultadoConfirmacion,
    ResultadoEnvioEncolado,
    ROL_APROBACION_SEMANTICA,
    ROL_APROBACION_UTILITARIA,
    SolicitudConfirmacion,
    drenar_envios,
    procesar_confirmacion,
    reconciliar_envios_reservados,
)
from .interpretacion import (
    IdentidadSolicitante,
    ResultadoInterpretacion,
    interpretar_solicitud,
)
from .buzon import BuzonPropio, BuzonPropioEml, BuzonPropioMemoria
from .ollama import OllamaGenerator
from .pagos import correr_control_pagos
from .procesamiento import FakeGenerator, ResultadoProceso, procesar_fila_csv
from .posts import PoliticaPost, procesar_post, procesar_post_estructurado

__all__ = [
    "AprobacionHumana",
    "BuzonPropio",
    "BuzonPropioEml",
    "BuzonPropioMemoria",
    "ColaEnviosArchivo",
    "ColaEnviosMemoria",
    "DestinoConfirmacionesFake",
    "EntregaRechazadaError",
    "FakeGenerator",
    "IdentidadSolicitante",
    "ItemEnvio",
    "OllamaGenerator",
    "PoliticaPost",
    "ROL_APROBACION_SEMANTICA",
    "ROL_APROBACION_UTILITARIA",
    "RegistroConfirmacionesArchivo",
    "RegistroConfirmacionesMemoria",
    "ReservaReconciliada",
    "ResultadoConfirmacion",
    "ResultadoEnvioEncolado",
    "ResultadoInterpretacion",
    "ResultadoProceso",
    "SolicitudConfirmacion",
    "correr_control_pagos",
    "drenar_envios",
    "interpretar_solicitud",
    "procesar_confirmacion",
    "procesar_fila_csv",
    "procesar_post",
    "procesar_post_estructurado",
    "reconciliar_envios_reservados",
]
