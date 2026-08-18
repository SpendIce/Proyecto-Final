# Runbook — runner Workspace end-to-end del Agente 1

## Propósito y frontera

El runner compone `Sheets → validación HU-010/HU-011 → generator → copia de
plantilla en Drive → actualización en Docs → manifiesto`. Su única salida remota
es un **borrador pendiente de validación humana**. No comparte, publica, envía
correo ni cambia permisos.

El modo predeterminado es `offline_fake`: usa la solicitud sintética `SYN-001`,
un generator determinista y un destino en memoria. No abre conexiones de red.

## Verificación offline

Desde `Implementacion/Agente1`:

```bash
PYTHONPATH=src python scripts/workspace_e2e.py --tipo gacetilla
PYTHONPATH=src python scripts/workspace_e2e.py --tipo post --canal instagram
PYTHONPATH=src python scripts/workspace_e2e.py --tipo post --canal linkedin
```

Una repetición con la misma solicitud, tipo, canal y ambiente devuelve
`DUPLICADA` y no invoca nuevamente el destino. Para repetir una prueba offline
desde cero se debe usar un directorio nuevo con `--salida`; no se debe borrar un
registro live sin reconciliar antes el documento remoto.

HU-011 usa exclusivamente el pipeline estructurado v2 y los goldens de
`golden/posts_v2/`. La creatividad fake proviene del fixture JSON versionado
`data/workspace_e2e_creativity_v2.synthetic.json`; los hechos institucionales
son agregados por el renderer determinista, no por el generator.

## Precondiciones live D2/D3

1. DSI debe asignar identidad y autorización Workspace.
2. SEU debe confirmar planilla, rango, carpeta y plantilla.
3. El operador debe exportar la configuración documentada en
   `workspace_config.py`; los valores siguientes son marcadores, no IDs reales.
4. El access token efímero se entrega exclusivamente mediante
   `AGENTE1_WORKSPACE_ACCESS_TOKEN`. Nunca se pasa por CLI ni se conserva en el
   manifiesto.
5. Debe estar disponible Ollama en loopback con el modelo aprobado para la
   prueba.

Variables requeridas:

```text
AGENTE1_WORKSPACE_AMBIENTE=D2|D3
AGENTE1_WORKSPACE_SPREADSHEET_ID=<asignado-por-DSI-SEU>
AGENTE1_WORKSPACE_RANGO_A1=<hoja-y-rango-confirmados>
AGENTE1_WORKSPACE_FOLDER_ID=<asignado-por-SEU>
AGENTE1_WORKSPACE_TEMPLATE_ID=<asignado-por-SEU>
AGENTE1_WORKSPACE_TIMEOUT_S=10
AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES=1048576
AGENTE1_WORKSPACE_ACCESS_TOKEN=<token-efimero>
```

## Ejecución live explícita

El runner exige simultáneamente `--live` y `--confirm-write-workspace`:

```bash
PYTHONPATH=src python scripts/workspace_e2e.py \
  --live --confirm-write-workspace \
  --tipo gacetilla \
  --id-solicitud <id-confirmado>
```

Para HU-011 se agrega `--tipo post --canal instagram|linkedin`. No existe un
flag para publicar, compartir, modificar permisos o enviar contenido.

## Auditoría e idempotencia

- Cada ejecución genera exactamente un manifiesto privado en
  `<salida>/manifests/`.
- El manifiesto sólo contiene referencias opacas, hashes, estados y el
  `correlation_id`; no contiene texto, contacto, IDs Workspace, token ni paths.
- La reserva idempotente se crea atómicamente antes de invocar Drive.
- `COMPLETE` devuelve `DUPLICADA` y bloquea otra copia de la misma operación.
- `UNCERTAIN` o `IN_PROGRESS` devuelven `BLOQUEADA_RECONCILIACION`, nunca éxito,
  porque una caída o carrera podría haber creado un documento.
- La política es `manual_only`: no existe takeover automático por antigüedad.
  Timestamps ausentes, corruptos o futuros se degradan a `UNCERTAIN` y también
  requieren reconciliación manual.
- La clave incluye las versiones de pipeline, contratos y renderer; una
  migración de HU-011 v1 a v2 no colisiona con ejecuciones anteriores.
- Si Docs falla después de copiar la plantilla, el hash de reconciliación queda
  en el manifiesto y en el registro privado. Debe escalarse a DSI/SEU para
  identificar el documento con evidencia operativa autorizada; el runner nunca
  expone el ID remoto.

## Estados operativos

| Estado | Interpretación | Acción |
|---|---|---|
| `PENDIENTE_VALIDACION` | Borrador creado; no aprobado | Validación humana SEU |
| `DUPLICADA` | Escritura previa confirmada como completa | No repetir; reutilizar evidencia previa |
| `BLOQUEADA_RECONCILIACION` | Escritura en curso, incierta o registro inválido | Reconciliar manualmente; no repetir |
| `FALLIDA` sin registro de destino | Falló en fuente, validación o generación | Corregir causa y reintentar |
| `FALLIDA` con destino `UNCERTAIN` | Drive/Docs falló sin confirmar creación | Bloquear repetición y reconciliar |
| `FALLIDA` con reconciliación | Posible documento huérfano | Reconciliar antes de cualquier reintento |

La existencia de un manifiesto o una corrida exitosa no acredita Gate G2 ni
TRL 3; esa decisión continúa dependiendo de evidencia live y validación
institucional.
