# Paquete operativo para gestionar con DSI — Issue #15

**Proyecto:** Proyecto Centenario (P100), Agente 1 — Extensión Bot
**Issue:** `SpendIce/Proyecto-Final#15`, «Obtener identidad, permisos y recursos de DSI»
**Estado del issue al consolidar:** `OPEN`, etiqueta `ready-for-human`
**Fecha de consolidación:** 2026-09-05
**Corte de la evidencia técnica:** 2026-08-26
**Aprobación DSI/SEU:** no consta; el paquete queda pendiente de respuesta y evidencia humana.

## 1. Alcance y límite de este paquete

Este documento convierte el pedido del issue en una agenda de coordinación,
un formulario de respuesta segura y un runbook de pruebas. Le permite a Juan
Ignacio Gone gestionar la intervención de DSI/SEU sin pedir secretos por este
repositorio ni afirmar que existe infraestructura que todavía no fue
entregada.

El paquete **no** crea cuentas, proyectos, archivos o permisos; no obtiene
OAuth; no contacta personas; no ejecuta pruebas contra Workspace; y no
autoriza producción, publicación, envío, sharing ni declaración de TRL 3.
Los valores marcados `PENDIENTE_DSI`, `PENDIENTE_SEU` o `PENDIENTE_AUTORIZACION`
son bloqueantes reales, no placeholders que puedan completarse por inferencia.

### Estado verificable al corte

- La configuración y los adapters de Sheets/Docs/Drive están preparados y
  verificados con transportes fake.
- El smoke Workspace live es opt-in; el runner E2E live puede escribir un
  borrador remoto y requiere una autorización separada.
- No hay en el repositorio valores OAuth, tokens, IDs institucionales, URLs
  privadas, scopes efectivos ni permisos entregados por DSI.
- D2 — Sandbox Workspace y D3 — Piloto SEU controlado siguen sin estar
  provisionados. El Gate G2 / TRL 3 permanece `PENDIENTE`.

## 2. Pedido consolidado para DSI/SEU

Juan puede llevar el siguiente pedido a la coordinación institucional. El
texto es una guía de gestión local: **no implica que haya sido enviado**.

> Se solicita coordinar la provisión controlada de D2 — Sandbox Workspace para
> el Agente 1, y dejar documentadas las condiciones de D3 — Piloto SEU
> controlado. Para cada ambiente necesitamos: (1) administrador DSI titular y
> suplente; (2) decisión del mecanismo de identidad —cuenta institucional con
> consentimiento OAuth o service account sobre recursos compartidos—; (3)
> identidad separada por ambiente, permisos mínimos, rotación y revocación; (4)
> proyecto Google Cloud y APIs habilitadas; (5) planilla, plantilla y carpeta
> de prueba con datos sintéticos; (6) host aprobado para Ollama; y (7) ventana
> de prueba autorizada. Los IDs, tokens, URLs privadas y cualquier secreto se
> entregarán únicamente por el mecanismo seguro que defina DSI y no se
> copiarán al issue, al repositorio ni a los logs.

### Decisiones que debe aportar DSI

| Tema | Pedido concreto | Estado documental | Dueño de la decisión |
|---|---|---|---|
| Responsable | Administrador DSI titular, suplente, owner técnico y procedimiento de incidente | `PENDIENTE_DSI` | DSI |
| Identidad | Alternativa A (OAuth de cuenta institucional) o B (service account + Shared Drive/recursos compartidos) por ambiente | `PENDIENTE_DSI` | DSI, con coordinación institucional |
| Separación | Identidad y recursos distintos para D2 y D3; si se comparte proyecto, aislamiento equivalente documentado | `PENDIENTE_DSI` | DSI |
| Google Cloud | Proyecto por ambiente preferentemente; Project ID reservado para canal seguro | `PENDIENTE_DSI` | DSI |
| APIs | Sheets API y Docs API; Drive API sólo si la solución aprobada necesita plantilla, carpeta o Shared Drive; Gmail API fuera de este alcance | `PENDIENTE_DSI` | DSI |
| Scopes | Scopes efectivos, justificación de cada uno y confirmación de que no se usa domain-wide delegation | `PENDIENTE_DSI` | DSI |
| Recursos | Planilla, rango, plantilla y carpeta sintéticos, exclusivos por ambiente | `PENDIENTE_DSI` + `PENDIENTE_SEU` | DSI + SEU |
| Secretos | Gestor o mecanismo aprobado, alta, rotación, revocación y destrucción sin exponer el secreto | `PENDIENTE_DSI` | DSI |
| Host | Host objetivo para Ollama, capacidad asignada, supervisión, reinicio y egress permitido | `PENDIENTE_DSI` | DSI |
| Pruebas | Ventana, operador autorizado, casos positivos/negativos y canal para escalar una falla | `PENDIENTE_AUTORIZACION` | DSI + Juan |

La cuenta de correo institucional identifica el tenant, pero por sí sola no
autentica llamadas a APIs privadas. La elección entre OAuth de usuario y
service account debe considerar propiedad de los documentos, Shared Drive,
custodia del refresh token o clave privada y capacidad de revocación.

## 3. Formulario de respuesta segura

DSI puede devolver el siguiente formulario por su canal institucional seguro.
La copia que se conserve en el repositorio debe contener sólo estados,
referencias opacas o hashes aprobados; nunca los valores de las columnas
marcadas como privadas.

| Campo de respuesta | D2 | D3 | Clasificación de la respuesta |
|---|---|---|---|
| Mecanismo de identidad (A/B) | `PENDIENTE_DSI` | `PENDIENTE_DSI` | Pública en el acta, sin principal ni email |
| Administrador titular/suplente | `PENDIENTE_DSI` | `PENDIENTE_DSI` | Rol y referencia institucional; no secreto |
| Referencia de identidad técnica | `NO_INCLUIR_EN_REPO` | `NO_INCLUIR_EN_REPO` | Privada; nunca email/token/clave |
| Proyecto Google Cloud | `NO_INCLUIR_EN_REPO` | `NO_INCLUIR_EN_REPO` | Project ID privado; no versionar |
| APIs habilitadas | `PENDIENTE_DSI` | `PENDIENTE_DSI` | Puede registrarse en el acta |
| Scopes efectivos y justificación | `PENDIENTE_DSI` | `PENDIENTE_DSI` | Puede registrarse; revisar mínimos |
| Delegación de dominio | `PENDIENTE_DSI` | `PENDIENTE_DSI` | Debe constar `NO_USADA`, salvo autorización expresa |
| Spreadsheet y rango | `NO_INCLUIR_EN_REPO` | `NO_INCLUIR_EN_REPO` | ID, URL y contenido privados |
| Folder/template/Shared Drive | `NO_INCLUIR_EN_REPO` | `NO_INCLUIR_EN_REPO` | IDs y URLs privados |
| Host Ollama | `PENDIENTE_DSI` | `PENDIENTE_DSI` | Registrar sólo alias o características no sensibles |
| Gestor de secretos | `PENDIENTE_DSI` | `PENDIENTE_DSI` | Registrar nombre del mecanismo, no ubicación/valor secreto |
| Rotación y revocación | `PENDIENTE_DSI` | `PENDIENTE_DSI` | Procedimiento y responsable |
| Ventana y autorización de prueba | `PENDIENTE_AUTORIZACION` | `PENDIENTE_AUTORIZACION` | Referencia de acta, sin token ni URL privada |

El inventario privado puede conservarse fuera del repositorio bajo custodia de
DSI. Para la evidencia pública o versionada alcanza con `ambiente`, fecha,
resultado, código de error seguro, versión del adapter, hash de la referencia
opaca y `correlation_id` sanitizado.

## 4. Diseño de ambientes solicitado

| Control | D2 — Sandbox Workspace | D3 — Piloto SEU controlado |
|---|---|---|
| Propósito | Autenticación, conectividad, contratos y permisos con datos sintéticos | Flujo limitado y representativo con SEU, sólo tras D2 |
| Identidad | Exclusiva de D2 | Exclusiva de D3; no promover la credencial de D2 |
| Datos | Sintéticos o anonimizados irreversiblemente | Sintéticos y, sólo con autorización registrada, muestra real mínima |
| Recursos | Planilla, plantilla y carpeta exclusivas de prueba | Recursos separados aprobados por SEU; no producción |
| Salida | `BORRADOR — NO PUBLICAR`, `PENDIENTE_VALIDACION` | Borradores y evidencia; no publicación ni envío automático |
| Acceso | Sólo la identidad, responsables DSI y operador autorizado | Identidad D3 y validadores SEU designados |
| Criterio de avance | Positivos/negativos de permisos y smoke técnico recuperable | D2 aprobado, validación SEU y criterio de Gate informado |

La pestaña y el rango A1 son controles de la aplicación, no una frontera de
autorización de Google. La frontera efectiva debe ser un spreadsheet dedicado y
compartido sólo con la identidad del ambiente.

## 5. Runbook de ejecución controlada

### 5.1 Preparación offline — sí ejecutable por Juan

1. Verificar que DSI todavía no haya entregado credenciales o IDs dentro del
   checkout. Si aparecen, detener la preparación y solicitar su retiro por el
   canal seguro correspondiente.
2. Ejecutar la configuración sin red desde `Implementacion/Agente1`:

   ```bash
   PYTHONPYCACHEPREFIX=/tmp/agente1-pycache PYTHONPATH=src \
     python scripts/workspace_smoke.py
   ```

3. Ejecutar el harness sintético de seguridad:

   ```bash
   PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
     python scripts/auditar_seguridad_d2.py \
       --manifest data/security_d2_manifest.synthetic.json \
       --reporte /tmp/reporte-seguridad-d2.json
   ```

4. Conservar únicamente el resultado sanitizado. Un `PASS` offline prueba el
   harness y los fakes, no la identidad, permisos, revocación o aislamiento
   institucionales.

### 5.2 Precondiciones antes de cualquier `--live`

No se debe ejecutar una prueba live hasta que exista una autorización
institucional recuperable que indique ambiente, recursos, operador, ventana,
casos y límites. Además, deben estar resueltos estos puntos:

- identidad y método de autenticación elegidos por DSI;
- token efímero entregado por el mecanismo seguro, sin persistencia ni copia;
- configuración cargada fuera del repositorio;
- recursos sintéticos confirmados y alcance de lectura/escritura documentado;
- host Ollama disponible y egress aprobado;
- procedimiento para reconciliar un documento creado si falla una operación
  posterior;
- contacto operativo institucional para detener o revocar la prueba.

La sesión debe iniciar con el proceso en primer plano, sin pasar secretos por
CLI, y debe poder interrumpirse. Si falta una precondición, el resultado es
`NO-GO`; no se compensa con una prueba sobre el Workspace personal de Juan.

### 5.3 Secuencia live autorizada

| Paso | Acción | Evidencia sanitizada | Efecto remoto |
|---:|---|---|---|
| 1 | Validar configuración cerrada | `configuracion_valida`, ambiente, hash de referencias | Ninguno |
| 2 | Ejecutar `workspace_smoke.py --live` con solicitud sintética autorizada | método, resultado, código seguro, correlation ID | Sólo lectura de Sheets |
| 3 | Ejecutar negativos de recurso y permiso | resultado `DENEGADA`/`NO_ENCONTRADA`, código seguro | Sólo lectura; no alterar recursos |
| 4 | Revocar permiso según procedimiento DSI y repetir negativo | acta de revocación, código seguro, correlation ID | Revocación administrativa |
| 5 | Restaurar el permiso mínimo y repetir positivo | resultado y versión del adapter | Restauración administrativa |
| 6 | Sólo con autorización adicional, ejecutar el runner E2E con confirmación de escritura | estado del borrador, hashes y reconciliación; nunca ID/URL | Crea/edita un borrador sintético |
| 7 | Reconciliar cualquier estado `UNCERTAIN` antes de reintentar | decisión manual y código seguro | Ningún reintento ciego |

El smoke live de Workspace sólo prueba lectura de Sheets. El runner E2E puede
crear un documento remoto y su modo live exige simultáneamente `--live` y
`--confirm-write-workspace`; por eso la autorización de lectura no habilita la
escritura. Ningún paso prueba ni habilita publicar, compartir, enviar email o
modificar permisos desde la aplicación.

### 5.4 Casos positivos y negativos mínimos

| Caso | Resultado esperado | Responsable de preparar el caso | Estado |
|---|---|---|---|
| Configuración completa | Validación local exitosa, sin red | Juan + DSI | `PENDIENTE_AUTORIZACION` |
| Solicitud sintética autorizada | Lectura de Sheets y contrato válido | DSI + Juan | `PENDIENTE_DSI` |
| Solicitud inexistente | Falla cerrada, sin contenido remoto en logs | Juan | `PENDIENTE_DSI` |
| Token ausente/vencido | Bloqueo antes o durante autenticación, sin reintento inseguro | DSI + Juan | `PENDIENTE_DSI` |
| Identidad sin acceso | `workspace_auth_denied` o código equivalente | DSI | `PENDIENTE_DSI` |
| Spreadsheet/rango incorrecto | Rechazo controlado | DSI + Juan | `PENDIENTE_DSI` |
| Revocación | Nueva lectura denegada después de retirar el permiso | DSI | `PENDIENTE_DSI` |
| Restauración mínima | Lectura vuelve a funcionar con el permiso acordado | DSI | `PENDIENTE_DSI` |
| Docs/Drive autorizado | Borrador sintético y manifest sin ID/URL expuestos | DSI + Juan | `PENDIENTE_AUTORIZACION` |
| Falla intermedia de Docs/Drive | Estado incierto bloquea reintento y exige reconciliación | Juan + DSI | `PENDIENTE_AUTORIZACION` |

## 6. Evidencia aceptable y evidencia prohibida

### Registro sanitizado sugerido

El siguiente esquema es ilustrativo y deliberadamente no contiene valores
institucionales. No debe completarse con IDs reales dentro del repo:

```json
{
  "schema_version": "workspace-dsi-evidence-v1",
  "issue": 15,
  "ambiente": "D2",
  "authorization_ref": "HASH_DE_ACTA",
  "identity_mode": "A_O_B_CONFIRMADO_POR_DSI",
  "resource_refs": {
    "spreadsheet": "HASH_DE_REFERENCIA",
    "folder": "HASH_DE_REFERENCIA",
    "template": "HASH_DE_REFERENCIA"
  },
  "api_methods": ["sheets.values.get"],
  "result": "PENDIENTE",
  "error_code": null,
  "correlation_id": "HASH_O_ID_SANITIZADO",
  "secrets_exposed": false
}
```

Se puede conservar: ambiente, versión de código, fecha/hora según la política
institucional, método de API, scope aprobado, estado, código de error seguro,
hashes y correlation ID sanitizado. No se puede conservar: token, refresh
token, clave privada, contraseña, Project ID, Spreadsheet/Folder/Template ID,
URL privada, email de la identidad, contenido de filas/Docs, PII, cuerpos HTTP
ni capturas que los contengan.

## 7. Checklist de aceptación del issue #15

| Criterio del issue | Evidencia requerida | Estado actual |
|---|---|---|
| Responsable técnico y administrador institucional identificados | Acta o respuesta DSI con titular, suplente, owner técnico e incidente | `PENDIENTE_DSI` |
| Identidad por ambiente, OAuth, scopes, rotación y revocación definidos | Decisión A/B, matriz de scopes, ciclo de vida y procedimiento | `PENDIENTE_DSI` |
| Recursos D2/D3 provisionados o referenciados de forma segura | Confirmación DSI/SEU y referencias privadas fuera del repo | `PENDIENTE_DSI` + `PENDIENTE_SEU` |
| Pruebas positivas y negativas acordadas y evidencia sanitizada | Autorización, matriz de casos, resultados y acta de revocación | `PENDIENTE_AUTORIZACION` |
| Host objetivo distinguido del runtime local | Alias/capacidad del host y responsable operativo DSI | `PENDIENTE_DSI` |
| No exponer credenciales, IDs, URLs ni secretos | Revisión del paquete, issue y manifests; reporte de secretos `false` | `CUMPLIDO_DOCUMENTAL`; verificar en cada evidencia nueva |

### Condición de cierre legítima

El issue recién puede considerarse listo para cierre cuando DSI/SEU aporte
evidencia institucional recuperable para cada fila anterior. El hecho de que
el código offline, un fake o un smoke local finalicen correctamente no satisface
los criterios de identidad, permisos, recursos, host ni revocación reales.

## 8. Bloqueantes para reportar a Juan

1. **Sin administrador DSI designado:** no hay responsable institucional para
   alta, custodia, rotación, revocación ni incidente.
2. **Sin decisión de identidad:** no se puede fijar el adapter ni validar scopes
   efectivos, propiedad de Docs o ubicación en Shared Drive.
3. **Sin recursos D2/D3:** no existen planilla, rango, plantilla ni carpeta
   institucionales asignados de forma segura.
4. **Sin host objetivo:** los benchmarks locales no representan capacidad ni
   disponibilidad del host institucional.
5. **Sin autorización de prueba:** ejecutar `--live` o escribir un Doc remoto
   sería una acción no autorizada.
6. **Cobertura Drive pendiente:** las operaciones de plantilla/carpeta y la
   compatibilidad de service account están verificadas sólo con fake; no deben
   declararse cubiertas por la preparación offline.

Por estos bloqueantes, el resultado correcto para el issue es
`ready-for-human` / `PENDIENTE`, no `CERRADO`.

## 9. Fuentes de respaldo

- [`Especificacion-Tecnica-Entornos-Pruebas-Preproduccion-Agente-1.md`](../PlanDespliegue/Especificacion-Tecnica-Entornos-Pruebas-Preproduccion-Agente-1.md): alternativas de identidad, D2/D3, APIs, scopes, seguridad, host, smoke y RACI.
- [`Runbook-Workspace-D2-D3-Agente-1.md`](../PlanDespliegue/Runbook-Workspace-D2-D3-Agente-1.md): configuración, límites del smoke y pruebas positivas/negativas.
- [`runbook-workspace-e2e.md`](../../Implementacion/Agente1/evidencias/runbook-workspace-e2e.md): precondiciones de escritura, idempotencia y reconciliación.
- [`auditoria-seguridad-d2-d3.md`](../../Implementacion/Agente1/evidencias/auditoria-seguridad-d2-d3.md): alcance de la evidencia offline y límites de los fakes.
- [`Registro-Defectos-Agente-1.md`](Registro-Defectos-Agente-1.md): `DEF-A1-001` (Workspace no provisionado) y estado del Gate G2.
- [`Nota-Solicitud-DSI-Agente-1-PPS-Juan-Ignacio-Gone.md`](Nota-Solicitud-DSI-Agente-1-PPS-Juan-Ignacio-Gone.md): pedido institucional previo de D2 y recursos asociados.
- `Contenido/bible/Procesos y Agentes.md`: Google Workspace, identidad, mínimo privilegio y validación humana del Proceso 4.
- `Contenido/bible/Correo de Facultad de Ingenieria del Ejercito - Proyecto Agentes IA.md`: respaldo institucional sobre apoyo de infraestructura DSI.

La especificación técnica enlaza, además, la documentación oficial de Google
para credenciales, scopes, Shared Drives y permisos. Este paquete no agrega
recursos ni decisiones que no estén confirmados por esas fuentes.
