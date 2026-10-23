# Gmail, pestaña de insumos y carpeta de respaldo configurados en el servidor

**Fecha:** 2026-10-23. **Host:** `labredesfie`, stack `agente1` de Portainer. **Versión:** 0.5.4. **Tickets:** #147 y #48 (mapa).

## Resultado

Quedan configurados en el servidor tres destinos reales que hasta hoy se probaban con dobles locales:

| Destino | Configuración | Prueba en vivo |
|---|---|---|
| Gmail (modo prueba, D12) | `AGENTE1_GMAIL_DESTINATARIOS_PRUEBA` con dos direcciones: la del operador y la de la cuenta técnica | Correo marcado como borrador enviado al operador con `gmail.send`; una dirección fuera de la lista se rechazó (`recipient_off_test_list`) antes de tocar la red |
| Pestaña «Insumos de agentes» (ADR 0008) | Pestaña creada en la planilla D2 (de la cuenta técnica) con el encabezado `insumo, cargado_por, estado, detalle`; `AGENTE1_INSUMOS_RANGO_A1='Insumos de agentes'!A1:D500` | El scheduler tomó un insumo real de A3 desde la pestaña y escribió el estado y el enlace al Doc |
| Carpeta de respaldo (ADR 0009) | Carpeta nueva en la unidad de la cuenta técnica, sin compartir (un único permiso: el dueño); `AGENTE1_RESPALDO_CARPETA_ID`, `AGENTE1_RESPALDO_CONFIRMAR_ESCRITURA=SI`, `AGENTE1_RESPALDO_AVISO_DESTINATARIO` (el operador) | Respaldo subido, bajado y restaurado con los archivos idénticos |

También se agregaron `AGENTE1_CONFIG_ENTORNO_AVISO_DESTINATARIO` (aviso al operador cuando cambia la configuración) y `AGENTE1_SCHEDULER_REPO=/srv/p100` (la raíz del repo dentro de la imagen, para que el scheduler encuentre los scripts de purga y respaldo).

Todo vive en el env file del servidor (`~/.config/agente1/workspace-d2.env`, 600), con backup previo `workspace-d2.env.bak-20261023-config`. Ningún identificador ni dirección se versiona.

Los Forms (canal de pedidos y decisiones) siguen sin configurar: falta definirlos.

## Gmail

Desde `agente1-consola-1`, con el adaptador productivo `GmailDestinoConfirmaciones.desde_entorno` y la credencial de siempre (cuenta de servicio delegada en la cuenta técnica):

```
gmail modo: prueba
gmail: enviado
fuera de lista rechazado: EntregaRechazadaError recipient_off_test_list
```

El cuerpo empezó con `BORRADOR — NO ENVIAR` y salió con la marca `BORRADOR — NO PUBLICAR` antepuesta, como todo correo en modo prueba.

Qué activa el correo real con esta configuración:
- el aviso al operador cuando falla el respaldo;
- el aviso al operador cuando cambia la configuración;
- los flujos de Forms (canal y certificados), que siguen sin configurar.

La consola no envía correo.

## Respaldo en Drive

Sobre una copia del estado del ensayo del scheduler (`/state/evidencia/respaldo-drive-2026-10-23/salida`):

```
scripts/respaldar_estado.py --salida /state/evidencia/respaldo-drive-2026-10-23/salida
{"archivos": 3, "artefacto_sha256": "177b7a3ffea9e01fce9234292248cfc37275ee1440e74048dfd2adf815e20741",
 "eliminados": 0, "modo": "live", "nombre": "agente1-respaldo-2026-10-23.tar.gz", "status": "OK", "subido": true}
```

En Drive quedó `agente1-respaldo-2026-10-23.tar.gz` (1513 bytes), con `shared = false` y `appProperties {agente1_respaldo: v1}`. Se bajó con `alt=media`: el sha256 coincide con el del artefacto. La restauración en un directorio vacío:

```
scripts/restaurar_respaldo.py --artefacto .../descarga.tar.gz --salida .../restaurado
{"archivos_restaurados": 3, "conflictos": [], "indeterminados": 0, "status": "OK"}
```

Los tres archivos respaldados (`insumos-procesados.jsonl`, `logs/ejecuciones.jsonl`, `logs/scheduler-corridas.jsonl`) son idénticos a los originales. `logs/respaldo-diario.jsonl` no viaja en el artefacto: es la bitácora de la operación, y la restauración le agrega su propia línea.

## Insumos de agentes con el scheduler

Se cargó en la fila 2 de la pestaña el insumo real de A3 «Ingeniería por un día 2026» (fixture `tests/fixtures/insumos_agentes/a3_evento_ingenieria_por_un_dia_2026.json`, `data_origin = provisional_producer`, `cargado_por = ope-jgone`). Después se disparó el scheduler en vivo, con el mismo comando y directorio que usa el servicio:

```
contenedor_entrypoint.py scheduler --una-corrida --live --confirm-write-workspace \
  --ollama-model gemma4:e4b --ollama-timeout 300 --directorio /state/scheduler
{"corrida": {"estado": "OK", "filas_leidas": 1, "filas_nuevas": 1, "filas_escritas": 1, "filas_fallidas": 0},
 "en_ventana": true, "mantenimiento": {"respaldo": "completada"}, "resultado": "completada", "version_agente": "0.5.4"}
```

La corrida tardó 40 segundos, de 15:26:14 a 15:26:54.

En la planilla, la fila quedó con `estado = borrador generado` y el `detalle` con el enlace al Doc. El Doc «BORRADOR — Fie informa 23-10 Ingeniería por un día 2026» está en la carpeta D2 y empieza así:

```
# BORRADOR — NO PUBLICAR
[Procedencia: insumo de A3, tipo evento; productor provisional: sí; cargado_por: ope-jgone; correlation_id: corr-a3-ingenieria-por-un-dia-2026.]
Asunto: Ingeniería por un día 2026
...
```

El paso diario de respaldo corrió dentro del mismo disparo. Registró `respaldo_omitido_existente`: el respaldo del día ya se había subido en la prueba anterior y no se duplica, que es lo esperado. La purga no se declara: el scheduler no lleva el registro de HU-012.

## Pendiente

- **Encender el servicio `scheduler`:** redesplegar el stack con `COMPOSE_PROFILES=scheduler`. Hasta entonces, la pestaña sólo se procesa con disparos manuales y el respaldo diario no corre solo.
- **Forms del canal y de decisiones:** sin definir.
