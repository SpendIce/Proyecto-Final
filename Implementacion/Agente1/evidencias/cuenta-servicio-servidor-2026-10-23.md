# Cuenta de servicio en el servidor y baja de la OAuth

**Fecha:** 2026-10-23. **Host:** `labredesfie` (servidor de la facultad, D3 provisional). **Ticket:** #99.

## Resultado

El agente opera contra Workspace sólo con la cuenta de servicio de DSI, que se hace pasar por la cuenta técnica (ADR 0011). La credencial OAuth anterior quedó revocada y sus archivos se borraron.

## Evidencia

### Smoke live sin variables OAuth (23/10)

En el servidor, con el checkout en `dbcbcde`, se cargó `~/.config/agente1/workspace-d2.env`. Antes y después de cargarlo, el entorno tenía **0** variables `AGENTE1_WORKSPACE_OAUTH_*`.

```
.venv/bin/python scripts/workspace_smoke.py --live --id-solicitud FIE-DIF-08
{"ambiente": "D2", "correlation_id": "f0ac65e3-02b0-42c2-9ea2-7260abcecabe", "modo": "live_read_only", "resultado": "lectura_confirmada"}
exit 0
```

### E2E live con la cuenta de servicio (21/10)

Los registros que quedaron en el servidor muestran cuatro corridas de gacetilla con `gemma4:e4b` y `version_agente` 0.4.0, todas con `resultado: borrador_generado` y `estado: PENDIENTE_VALIDACION` hacia `google_drive_template`. Cada corrida tiene al lado su `cuenta-suplantada.jsonl` con los tokens emitidos por la cuenta de servicio (`resultado: emitido`, cuenta por hash):

| Hora (UTC) | Corrida | Latencia |
|---|---|---|
| 21/10 03:25 | E2E headless, actividad `FIE-DIF-08` | 64,2 s |
| 21/10 03:26 | E2E headless | 33,6 s |
| 21/10 03:30 | Consola visual (ensayo) | 41,0 s |
| 21/10 12:35 | Consola visual, **demo de la presentación de avance** | 56,9 s |

Los logs viven en directorios temporales del servidor y no se versionan: tienen ids de recursos.

### Baja de la OAuth (23/10)

- Refresh token revocado en `oauth2.googleapis.com/revoke` (HTTP 200). Un intercambio posterior devuelve `invalid_grant: Token has been expired or revoked.`
- Borrados con `shred`: `workspace-d2-planb.env` del servidor, y `workspace-d2-planb.env`, `workspace-d2.env` y `workspace-d2.env.bak` (la era OAuth) de la laptop.
- La copia de la clave de la cuenta de servicio que había en la laptop se borró después de comprobar que el sha256 coincidía con la del servidor. La clave existe sólo en `~/.config/agente1/cuenta-servicio.json` del servidor.

## Límites

- **Proyecto de Google Cloud del autor:** queda eliminarlo desde la consola de Google (no hay `gcloud` instalado). Con el token revocado ya no da acceso a nada.
- **Correo con la clave adjunta:** borrarlo del buzón y de la papelera es un paso manual. En `~/Downloads` no había copia.
- **Disco sin cifrar:** `labredesfie` no tiene LUKS. Ver la fila de custodia del inventario.
- **Laptop con btrfs:** `shred` no garantiza sobrescribir los bloques en un sistema copy-on-write. Si hay snapshots del home, la copia vieja de la clave puede seguir en alguno.
- Los scripts del plan B (`run-demo-planb.sh`, `corrida_plan_b_oauth.sh`, `demo_visual_plan_b.sh`) quedan en el repo sin credencial que los alimente. La consola `demo_visual_plan_b.py` sigue en uso por el plan A.
