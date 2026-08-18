# Runbook de operaciones seguras D2/D3 — Agente 1

**Versión:** 1.0  
**Fecha de corte:** 2026-08-17  
**Estado:** preparado offline; probes live pendientes de autorización e identidad DSI.

## Propósito y frontera

Este paquete permite evaluar salud, clasificar referencias potencialmente
huérfanas, consolidar defectos y planificar retención usando exclusivamente
manifests sanitizados. No acepta IDs de Google Workspace, contactos, prompts,
cuerpos ni credenciales. Tampoco expone operaciones para publicar, compartir,
enviar o borrar.

Los reportes prueban comportamiento técnico del tooling. No constituyen
validación SEU, aprobación institucional ni evidencia suficiente de TRL 3.

## Contratos

| Operación | Entrada | Salida | Efecto |
|---|---|---|---|
| `health` | hashes SHA-256, estados de configuración/runtime/artefactos | checks y estado agregado | ninguno por defecto |
| `reconcile` | hashes de borrador/manifest y estado | `SIN_ACCION` o `REVISAR_MANUAL` | ninguno |
| `consolidate` | schema, estado y códigos seguros | conteos por estado/código | ninguno |
| `retention` | hash, ruta relativa allowlisted, fecha y estado | plan `dry_run` | ninguno; conserva los archivos |

Los contratos son fail-closed: una clave extra, hash inválido, estado no
permitido, email, bearer token o estructura malformada se rechazan o contabilizan
como entrada inválida. Los errores públicos son códigos estables y no repiten la
entrada.

## Health-check offline

Desde `Implementacion/Agente1`:

```bash
python scripts/operaciones_seguras.py health data/health_operativo.synthetic.json
```

El ejemplo es completamente sintético. Para producir un manifest real se deben
hashar localmente las referencias y omitir sus valores originales. Un `PASS`
offline sólo confirma que la configuración fue validada por su productor, el
runtime fue marcado disponible y los artefactos declarados están presentes.

### Frontera live

La librería define el puerto mínimo `ProbeLectura.probar_lectura()`. El probe no
recibe IDs ni admite escritura. Para ejecutarlo se requieren simultáneamente
`live=True`, `live_opt_in=True` y una implementación inyectada. El CLI entregado
no conecta este puerto: `--live` falla con
`health_live_probe_adapter_unavailable` hasta que DSI autorice la identidad y se
implemente una lectura real. NO se debe reemplazar ese bloqueo por un probe de
escritura.

## Reconciliación de referencias

La entrada es una lista de objetos con exactamente:

```json
{
  "draft_hash": "<sha256>",
  "manifest_hash": "<sha256>",
  "state": "SIN_REFERENCIA"
}
```

Estados admitidos: `PERSISTIDO`, `REFERENCIADO`, `SIN_REFERENCIA`. Este último
produce una instrucción `REVISAR_MANUAL`; no produce un ID ni intenta reparar,
mover o borrar el documento.

## Retención y eventual borrado

La política sólo acepta rutas relativas bajo `salida/` o `evidencias/`. Rechaza
rutas absolutas, traversal, archivos inexistentes y symlinks. Una evidencia
vencida en estado `CERRADO` queda marcada
`CANDIDATO_BORRADO_MANUAL`; `PENDIENTE_VALIDACION` siempre se conserva.

Ejemplo:

```bash
python scripts/operaciones_seguras.py retention /tmp/retention-input.json \
  --base-dir . --now 2026-08-17T00:00:00Z --retention-days 30
```

El comando no borra archivos. Antes de cualquier mecanismo futuro de borrado se
requiere decisión institucional sobre plazo, responsable, legal hold, evidencia
de validación y aprobación humana separada del plan.

## Consolidación de defectos

`consolidate` consume una lista mínima con `schema_version`, `status` y
`error_codes`. Sólo emite conteos ordenados. No incorpora correlation IDs,
actividades, contenido o datos personales. Un manifest completo debe proyectarse
primero a este contrato mínimo; pasar el manifest completo se rechaza para evitar
que el reporte se convierta en otro canal de fuga.

## Respuesta ante fallas

1. Conservar el manifest original únicamente en su ubicación controlada.
2. Registrar el `error_code` seguro del comando.
3. No copiar la entrada completa a tickets, chats o logs.
4. Corregir el productor del manifest; no relajar el contrato consumidor.
5. Repetir offline. Sólo luego evaluar un probe live read-only autorizado.
