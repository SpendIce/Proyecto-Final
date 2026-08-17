# Auditoría offline de seguridad D2/D3

## Objetivo

El harness `scripts/auditar_seguridad_d2.py` verifica, sobre observaciones
sintéticas provistas mediante un manifest, las siguientes invariantes:

1. logs sin tokens, prompts completos, contactos ni cuerpos remotos;
2. recursos Workspace dentro de una allowlist explícita;
3. errores remotos expresados sólo mediante códigos redactados;
4. ausencia de endpoints de compartir, enviar o publicar;
5. revocación simulada con resultado bloqueado y sin borrador creado;
6. toda salida generada marcada `BORRADOR — NO PUBLICAR` y en estado
   `PENDIENTE_VALIDACION`.

El reporte contiene únicamente el hash SHA-256 del `run_id`, códigos y
resultados booleanos. No replica IDs de recursos, contenidos ni valores
sensibles del manifest.

## Ejecución reproducible

Desde `Implementacion/Agente1/`:

```bash
python scripts/auditar_seguridad_d2.py \
  --manifest data/security_d2_manifest.synthetic.json \
  --reporte /tmp/reporte-seguridad-d2.json
```

Códigos de salida:

- `0`: todas las invariantes pasan;
- `1`: al menos una invariante falla;
- `2`: manifest inválido o reporte no escribible.

La ejecución es **offline por diseño**: el contrato exige
`mode: offline_fake`, no acepta credenciales y no contiene código de red. Un
smoke live deberá ser otro adaptador explícito y opt-in; no se habilita
implícitamente desde este harness.

## Contrato mínimo del manifest

- `schema_version`: `security-d2-manifest-v1`;
- `run_id`: correlación de la corrida, sólo emitida como hash;
- `mode`: únicamente `offline_fake`;
- `allowlist`: listas separadas para `spreadsheet`, `folder` y `template`;
- `sensitive`: valores sintéticos a detectar en `tokens`, `prompts`,
  `contacts` y `bodies`;
- `resources`, `http_calls`, `logs`, `remote_errors`, `outputs`;
- `revocation_probe`: evidencia simulada del bloqueo por revocación.

## Límites de la evidencia

- Demuestra comportamiento del harness y de los fakes registrados en el
  manifest; **no demuestra permisos, revocación ni aislamiento reales** de
  Google Workspace.
- No reemplaza el smoke D2/D3 live ni la validación de Vera/DSI.
- La allowlist del fixture usa IDs inequívocamente sintéticos. Los IDs
  institucionales siguen pendientes y no deben versionarse sin una decisión
  explícita sobre su clasificación.
- La ausencia de endpoints de distribución se verifica sobre las llamadas
  observadas. La captura del transporte real queda como integración pendiente.
- El reporte PASS no habilita compartir, enviar ni publicar borradores.
