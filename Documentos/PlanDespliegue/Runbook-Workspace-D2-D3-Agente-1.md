# Runbook Workspace D2/D3 — Agente 1

- **Estado:** preparación técnica offline; integración live no confirmada
- **Corte:** 17/08/2026
- **Alcance:** Google Sheets de entrada y recursos reservados para carpeta/plantilla de borradores

## 1. Propósito y límites

Este runbook deja una configuración cerrada y un smoke **read-only** listo para
usar cuando DSI entregue la identidad técnica, los permisos y los IDs. No crea
cuentas, no obtiene OAuth, no escribe en Drive, no comparte documentos y no
publica contenidos.

La existencia del dominio `@fie.undef.edu.ar` y Google Workspace no demuestra
por sí sola que las APIs estén habilitadas ni que la identidad tenga acceso. La
ejecución live será evidencia técnica solamente; no reemplaza validación de SEU
ni aprobación de Gate G2/TRL 3.

## 2. Frontera de configuración

Cada ambiente debe aportar estas variables en el gestor de secretos o mecanismo
operativo definido por DSI. No se versionan archivos `.env` con valores reales.

| Variable | Contenido | Regla |
|---|---|---|
| `AGENTE1_WORKSPACE_AMBIENTE` | `D2` o `D3` | No existe valor implícito |
| `AGENTE1_WORKSPACE_SPREADSHEET_ID` | ID de la planilla | ID opaco, no URL |
| `AGENTE1_WORKSPACE_RANGO_A1` | Rango tabular | Ej. conceptual: `'Hoja'!A1:I200`; el valor real queda pendiente |
| `AGENTE1_WORKSPACE_FOLDER_ID` | ID de carpeta | Obligatorio aunque la escritura live todavía no esté habilitada |
| `AGENTE1_WORKSPACE_TEMPLATE_ID` | ID de plantilla | Obligatorio aunque la copia live todavía no esté habilitada |
| `AGENTE1_WORKSPACE_TIMEOUT_S` | Segundos | Mayor que 0 y hasta 120 |
| `AGENTE1_WORKSPACE_MAX_RESPONSE_BYTES` | `1048576` | Límite efectivo actual: 1 MiB |
| `AGENTE1_WORKSPACE_ACCESS_TOKEN` | Token efímero | Sólo para el proceso live; nunca como argumento de CLI |

Los hosts están compilados y no son configurables:

- `sheets.googleapis.com`;
- `docs.googleapis.com`;
- `www.googleapis.com` (reservado para Drive).

Los resúmenes operativos exponen hashes SHA-256 de referencias, no IDs, rango,
token, contenido de filas ni datos de contacto.

## 3. Provisión coordinada con DSI/SEU

1. DSI designa administrador y mecanismo de autenticación autorizado.
2. SEU/Josefina entrega o confirma planilla, rango, carpeta y plantilla.
3. DSI otorga a la identidad técnica el mínimo acceso necesario a esos recursos.
4. El operador carga D2 en un proceso aislado, sin copiar secretos al historial.
5. Ejecuta primero validación offline:

   ```bash
   cd Implementacion/Agente1
   PYTHONPATH=src python scripts/workspace_smoke.py
   ```

6. Conserva el JSON seguro: debe indicar `configuracion_valida` y hashes de
   recursos. Esto no prueba acceso remoto.
7. Sólo con autorización, carga el token efímero en el entorno del proceso y
   ejecuta la lectura live explícita:

   ```bash
   PYTHONPATH=src python scripts/workspace_smoke.py --live --id-solicitud ID_AUTORIZADO
   ```

El script no acepta token por flag. `--live` sólo lee Sheets: NO prueba Docs,
Drive, carpeta, plantilla ni publicación.

## 4. Códigos operativos

| Exit code | Significado |
|---:|---|
| `0` | Configuración local válida o lectura live confirmada |
| `2` | Configuración/argumentos inválidos o incompletos |
| `3` | Token efímero ausente o inseguro, detectado antes de red |
| `4` | Falla cerrada de autenticación, permisos, recurso, rate limit, red o contrato remoto |

Los códigos de resultado del JSON (`workspace_auth_denied`,
`workspace_source_not_found`, `workspace_rate_limited`, entre otros) son aptos
para diagnóstico sin incluir cuerpo remoto, token o IDs.

## 5. Pruebas positivas y negativas requeridas

En D2, registrar por `correlation_id`, fecha, ambiente y resultado:

1. configuración válida sin red;
2. lectura autorizada de una solicitud sintética;
3. ID de solicitud inexistente;
4. token ausente o vencido;
5. identidad sin acceso a la planilla;
6. planilla o rango incorrecto;
7. revocación: repetir la lectura después de quitar el permiso y confirmar falla
   cerrada;
8. restauración: devolver el permiso mínimo y confirmar lectura.

No registrar valores de configuración, fila devuelta, email, cuerpo HTTP ni
token. D3 se ejecuta recién después de aprobar D2 y con recursos separados.

## 6. Revocación

1. Interrumpir el proceso que contiene el token efímero.
2. Quitar a la identidad el acceso a planilla, carpeta y plantilla desde el
   control administrativo de Workspace.
3. Revocar la credencial o sesión según el mecanismo que defina DSI.
4. Ejecutar el negativo read-only autorizado y registrar sólo código y
   `correlation_id`.
5. Rotar la identidad si se sospecha exposición. No guardar el token anterior
   como evidencia.

## 7. Diagnóstico

| Resultado | Revisar sin exponer secretos |
|---|---|
| `workspace_config_incomplete` | Existencia de las siete variables no secretas |
| `workspace_config_invalid` | Ambiente, formato A1, IDs opacos, timeout y límite de 1 MiB |
| `workspace_config_unknown_key` | Typo dentro del namespace `AGENTE1_WORKSPACE_` |
| `workspace_auth_unavailable` | Presencia/validez temporal del token y mecanismo DSI |
| `workspace_auth_denied` | Compartición del recurso, rol mínimo y tenant correcto |
| `workspace_source_not_found` | ID de planilla confirmado y recurso no eliminado |
| `sheets_headers_invalid` | Encabezados exactos del contrato de nueve columnas |
| `workspace_unavailable` | DNS/TLS/API habilitada/conectividad; no reintentar a ciegas |

## 8. Evidencia pendiente para cierre

- nombre y responsable de la identidad técnica;
- mecanismo autorizado de emisión del token;
- IDs y rango confirmados por DSI/SEU, fuera del repositorio público;
- resultados positivos y negativos D2;
- prueba posterior de Docs/Drive/copia de plantilla, implementada por separado;
- repetición controlada en D3;
- validación humana SEU y criterio formal de César para Gate G2/TRL 3.
