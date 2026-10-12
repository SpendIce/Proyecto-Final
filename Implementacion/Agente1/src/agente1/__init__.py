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
- `canal_form`                HU-013, adapter del canal de pedidos por Google
                              Form con padrón de roles y aviso por Gmail (#71).
- `pagos`                     HU-012, corrida de control de pagos (offline).
- `recordatorios`             HU-012, circuito por lote de `recordatorio_pago`.
- `instrucciones_pago`        HU-012, builders de `instrucciones_pago` (D8) y
                              de la confirmación de inscripción por pago (D9).
- `buzon`                     puerto del buzón propio del agente (ADR 0004).
"""

from .confirmaciones import (
    AprobacionHumana,
    ColaEnviosArchivo,
    ColaEnviosMemoria,
    CuotaInstrucciones,
    DatosInstruccionesPago,
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
    TIPO_INSTRUCCIONES_PAGO,
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
from .instrucciones_pago import (
    solicitud_confirmacion_inscripcion,
    solicitud_instrucciones_pago,
)
from .ollama import OllamaGenerator
from .pagos import (
    CandidatoConfirmacion,
    correr_control_pagos,
    planificar_confirmaciones,
)
from .recordatorios import (
    AprobacionLote,
    aprobar_plantilla_recordatorio,
    correr_lote_recordatorios,
    encolar_lote_recordatorios,
    registrar_plantilla_recordatorio,
)
from .procesamiento import FakeGenerator, ResultadoProceso, procesar_fila_csv
from .posts import PoliticaPost, procesar_post, procesar_post_estructurado

__all__ = [
    "AprobacionHumana",
    "AprobacionLote",
    "BuzonPropio",
    "BuzonPropioEml",
    "BuzonPropioMemoria",
    "CandidatoConfirmacion",
    "ColaEnviosArchivo",
    "ColaEnviosMemoria",
    "CuotaInstrucciones",
    "DatosInstruccionesPago",
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
    "TIPO_INSTRUCCIONES_PAGO",
    "aprobar_plantilla_recordatorio",
    "correr_control_pagos",
    "correr_lote_recordatorios",
    "drenar_envios",
    "encolar_lote_recordatorios",
    "interpretar_solicitud",
    "planificar_confirmaciones",
    "procesar_confirmacion",
    "procesar_fila_csv",
    "procesar_post",
    "procesar_post_estructurado",
    "reconciliar_envios_reservados",
    "registrar_plantilla_recordatorio",
    "solicitud_confirmacion_inscripcion",
    "solicitud_instrucciones_pago",
]
