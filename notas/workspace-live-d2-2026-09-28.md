# Evidencia live Workspace D2 — 2026-09-28

Primera ejecución live del camino MVP del Agente 1 contra Google Workspace
real, con la cuenta institucional provista por DSI/FIE.

## Identidad y recursos

- **Identidad:** cuenta técnica dedicada creada para el Agente 1 por
  DSI/FIE (corresponde a la Alternativa A del paquete del issue #15). El
  correo de la identidad se mantiene fuera del repo por política.
  Token OAuth efímero (~1h) obtenido vía OAuth 2.0 Playground, entregado al
  proceso por `AGENTE1_WORKSPACE_ACCESS_TOKEN`. No persiste en el repo ni en
  logs; la config vive en `~/.config/agente1/workspace-d2.env` (chmod 600,
  fuera del repositorio).
- **Scopes efectivos:** `drive`, `documents`, `spreadsheets`.
- **Carpeta destino:** `folder_ref_hash`
  `1a85343be217109294d0a174c1032828a14458bec8d98440398f770a4038320f`.
- **Recursos provisionados por API (sintéticos):**
  - Planilla `Solicitudes Agente 1 (D2 sintético)` con encabezado exacto de
    `COLUMNAS_GACETILLA` y fila `SYN-001`.
    `spreadsheet_ref_hash fb11fbe18b5fbc3b70890f856c7e5c45b0bcb9867533515ec4051eb5d6eab3c3`
  - Doc plantilla `PLANTILLA — Gacetilla SEU (provisional, PENDIENTE_SEU)`.
    `template_ref_hash b2234cfa059bb16df5ec7624e2b913773227a751715734705a9c7aa0687a1a3f`

## Resultados

| Caso | Resultado |
|---|---|
| Validación de configuración (sin red) | `configuracion_valida` |
| Smoke live lectura `SYN-001` | `lectura_confirmada` |
| Smoke live id inexistente | `source_request_not_found` (falla cerrada) |
| Smoke live sin token | `workspace_auth_unavailable` (bloquea antes de abrir red) |
| E2E `--live --confirm-write-workspace` gacetilla | **`PENDIENTE_VALIDACION`** |

E2E exitoso: `correlation_id 8f19dff6-02ed-4633-8e9d-b3192197beca`, pipeline
`workspace_hu010_gacetilla_v1`, contrato `gacetilla_input_v1`, prompt
`gacetilla_v4`, modelo `llama3.2:3b` (Ollama local), `num_predict` 512,
latencia de generación 18.6s, destino `google_drive_template` con
`status: COMPLETE` y `destination.ref_hash`
`381dfaf2656a80e195573fc5bce392fb987b2e6fa711924e1a767b37d2e84bb5`.

Verificado por `drive.files.list` sobre la carpeta: existe el documento
`BORRADOR — NO PUBLICAR — SYN-001` (copia de la plantilla con el texto
volcado). El agente no compartió, publicó ni envió nada.

## Observaciones y límites

- **Latencia de generación:** dos corridas previas terminaron `FALLIDA`
  (`error_generacion`) por timeout a 45s exactos — host cargado + modelo
  frío (~11 tok/s en CPU). Con `timeout_s=110` en `OllamaGenerator` (knob
  documentado; el CLI del runner no lo expone, se invocó la API del módulo
  con un wrapper efímero fuera del repo) completó en 18.6s. Es un dato de
  capacidad del host, no del contrato.
- **No se probó revocación:** retirar el permiso y reintentar requiere al
  admin de la org; queda `PENDIENTE_DSI` en la matriz del issue #15.
- **Credencial provisional:** la identidad es la definitiva (cuenta técnica
  dedicada del Agente 1), pero el token efímero de Playground no es el
  mecanismo definitivo: caduca ~1h y requiere consentimiento manual. Para
  producción quedan dos caminos compatibles con el puerto
  `AccessTokenProvider`: refresh token de app OAuth internal, o service
  account con carpeta compartida (mintea tokens por JWT sin humano ni
  caducidad; compatible con `files.copy` + `parents=[carpeta]` porque la SA
  carece de My Drive propio). La elección es decisión DSI del issue #15.
- **Plantilla provisional:** la definitiva sigue `PENDIENTE_SEU`.
- Esto acredita el camino técnico live en D2. **No** cierra el issue #15
  (faltan decisiones formales: admin titular, matriz de scopes aprobada,
  procedimiento de revocación, host) ni habilita Gate G2 / TRL 3 por sí solo.

## Reproducir

```bash
set -a; source ~/.config/agente1/workspace-d2.env; set +a
cd Implementacion/Agente1
PYTHONPATH=src python3 scripts/workspace_smoke.py --live --id-solicitud SYN-001
PYTHONPATH=src python3 scripts/workspace_e2e.py --live --confirm-write-workspace \
  --tipo gacetilla --id-solicitud SYN-001 --salida <dir-nuevo>
```

El token caduca ~1h tras obtenerse; renovarlo re-corriendo el wizard
`/tmp/wizard-workspace-d2.sh` (efímero, no versionado).
