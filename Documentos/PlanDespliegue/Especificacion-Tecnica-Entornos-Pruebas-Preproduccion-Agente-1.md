# Especificación técnica de entornos de pruebas y preproducción — Agente 1

**Proyecto:** Proyecto Centenario (P100) — FIE/UNDEF

**Componente:** Agente 1 — Extension Bot

**Destinatarios:** César Cicerchia; Vera Batista; administrador a designar por el Departamento de Sistemas Informáticos (DSI)

**Fecha de emisión:** 22 de julio de 2026
**Estado:** propuesta técnica para coordinación; no autoriza operación productiva

## 1. Propósito

Esta especificación detalla las necesidades para habilitar dos ambientes separados del Agente 1:

1. un **entorno de pruebas**, destinado a verificar la integración técnica con Google Workspace usando exclusivamente datos sintéticos o anonimizados; y
2. un **entorno de preproducción**, destinado a validar un flujo institucional limitado con personal designado por la Secretaría de Extensión Universitaria (SEU), sin publicación ni envío automático.

El documento permite que el DSI, con coordinación de Vera Batista, determine la infraestructura y el mecanismo de identidad definitivos. El dominio institucional confirmado es `fie.undef.edu.ar` y utiliza Google Workspace. No se solicitan contraseñas ni credenciales por correo y no se presuponen direcciones de cuenta concretas, IDs, capacidad instalada o acuerdos de nivel de servicio que todavía no fueron informados.

## 2. Decisiones y dependencias institucionales confirmadas

De acuerdo con la respuesta de César Cicerchia:

| Tema | Definición confirmada | Consecuencia técnica |
|---|---|---|
| Modalidad referida para el acceso del primer release | Email institucional del dominio `@fie.undef.edu.ar`, provisto mediante Google Workspace | Queda confirmada la plataforma y el tenant institucional. Falta aclarar si esa cuenta será el principal que autoriza mediante OAuth, el inicio de sesión, el canal de interacción o si se utilizará una service account separada. En ningún caso una dirección de email, por sí sola, autentica llamadas a APIs privadas. |
| Evolución | Arquitectura escalable a OAuth durante 2027 | El primer release debe preservar puertos desacoplados y evitar dependencias que impidan incorporar OAuth de usuario posteriormente. |
| Administración | Administrador designado por el DSI | El DSI será propietario operativo de proyectos, identidades técnicas, secretos, permisos y revocación, una vez designada la persona. |
| Planilla, carpeta y plantilla | Se solicitarán en agosto a Josefina Carullo, Coordinadora de Extensión | Hasta recibirlos se usarán artefactos de prueba claramente identificados y un contrato provisional. |
| Validadores | Serán designados por la SEU a partir del 4 de agosto | La preproducción no puede cerrar aceptación antes de registrar validadores titulares o suplentes. |
| Evidencia y TRL | Criterio pendiente de respuesta de César Cicerchia | Ninguna prueba técnica aislada habilita a declarar cumplido el Gate TRL 3. |

## 3. Aclaración sobre email, OAuth e identidad técnica

César Cicerchia indicó “email institucional” como modalidad para el acceso del primer release. Se confirmó posteriormente que pertenece al dominio `@fie.undef.edu.ar` y que la institución utiliza Google Workspace. Esto identifica el tenant y la plataforma, pero no define todavía el principal técnico ni el flujo de autorización: falta aclarar si la cuenta institucional autorizará a la aplicación, si tendrá otra función operativa o si se usará una service account separada. Una dirección de email, por sí sola, no autentica una aplicación ante las APIs de Google Sheets, Docs o Drive; esas APIs requieren credenciales y tokens emitidos mediante los mecanismos de Google Cloud/Workspace.

Aunque se difiera una experiencia OAuth multiusuario para 2027, **toda llamada privada a las APIs de Workspace necesita OAuth 2.0 por debajo**. Una service account también obtiene access tokens mediante un flujo OAuth 2.0 server-to-server; no es una alternativa “sin OAuth”. Para el primer release, Vera Batista/DSI deberá elegir entre:

- **Alternativa A — cuenta institucional y consentimiento OAuth:** una cuenta designada del dominio `@fie.undef.edu.ar` autoriza a la aplicación. Si el archivo se crea en su My Drive, esa cuenta es propietaria; si se crea en un Shared Drive, el archivo pertenece a la organización asociada al Shared Drive. Esta alternativa introduce consentimiento, refresh token, custodia y dependencia de una identidad humana o funcional.
- **Alternativa B — service account y recursos compartidos:** una identidad no humana administrada por el DSI accede sólo a archivos concretos y, para crear nuevos documentos sin impersonar usuarios, opera sobre un Shared Drive u otra modalidad que el DSI compruebe compatible. Reduce dependencia de una persona, pero requiere resolver explícitamente la ubicación/propiedad de los Docs y probablemente incorporar Drive API.

Una service account no posee cuota de almacenamiento y no debe asumirse que puede crear documentos nuevos en un My Drive propio. La implementación actual usa `documents.create` y todavía no resuelve Shared Drive, plantilla ni movimiento a carpeta. Por lo tanto, la alternativa B exige un cambio técnico y una prueba de integración antes de declararse viable. Google sí documenta que una service account puede acceder a archivos específicos compartidos con su dirección técnica sin recibir roles administrativos ni delegación sobre todo el dominio. La decisión final corresponde a Vera Batista y al administrador designado por el DSI. Véanse la [guía oficial para crear y elegir credenciales de Google Workspace](https://developers.google.com/workspace/guides/create-credentials) y la [descripción oficial de Shared Drives](https://developers.google.com/workspace/drive/api/guides/about-shareddrives).

### 3.1 Controles obligatorios de identidad

- Una identidad técnica distinta por ambiente, o una justificación formal si el DSI dispone otra separación equivalente.
- Propietario institucional nominal y suplente para alta, rotación, revocación e incidentes.
- Acceso de la identidad sólo a los archivos o carpetas expresamente autorizados.
- Prohibición de usar la contraseña del email institucional como credencial de la aplicación.
- Prohibición de usar API keys para acceder a documentos privados; Google reserva las API keys para acceso anónimo a datos públicos.
- Prohibición de archivos compartidos públicamente o mediante “cualquier persona con el enlace”.
- Prohibición de **domain-wide delegation** en este alcance, salvo necesidad posterior documentada, análisis de riesgo y autorización explícita del DSI. El acceso a archivos concretos no la requiere.
- Prohibición de compartir credenciales, tokens o claves privadas por email, chat, repositorio o documentación de evidencias.

## 4. Alcance funcional inicial

El alcance técnico inmediato cubre HU-010, generación de borradores de gacetillas:

```text
Google Sheets controlado
        |
        v
validación de datos y contrato
        |
        v
Ollama local — generación del borrador
        |
        v
validación mecánica de salida
        |
        v
Google Docs — BORRADOR / PENDIENTE_VALIDACION
        |
        v
revisión humana SEU
```

No se habilitan en esta etapa:

- publicación en web o redes sociales;
- envío automático de emails;
- aprobación automática;
- acceso general al Drive institucional;
- lectura de Gmail o impersonación de usuarios;
- uso de datos reales fuera de la muestra autorizada;
- integraciones de terceros no aprobadas.

La función del “email institucional” en el primer release está pendiente de aclaración. Si finalmente sólo notifica o convoca al validador, no se necesita Gmail API para probar HU-010. Si se pretende leer o enviar correo automáticamente, deberá elaborarse una ampliación de alcance con permisos, plantilla, idempotencia, destinatarios, logging, aprobación humana y kill switch propios.

## 5. Separación de ambientes

### 5.1 Entorno de pruebas

| Aspecto | Especificación |
|---|---|
| Objetivo | Comprobar autenticación, conectividad, contratos, permisos mínimos, manejo de errores y trazabilidad de Sheets → Agente 1 → Docs. |
| Datos | Sólo datos sintéticos o anonimizados. No usar información personal, sensible ni comunicaciones oficiales. |
| Usuarios | Juan Ignacio Gone, responsable técnico autorizado y administrador DSI. Validadores SEU sólo si se requiere una prueba guiada. |
| Google Cloud | Se prefiere un proyecto exclusivo de pruebas, con nombre e ID a definir por el DSI. Puede usarse un proyecto compartido sólo si el DSI aprueba y documenta aislamiento equivalente de identidades, recursos, configuración y logs. APIs habilitadas sólo según la sección 6. |
| Workspace | Planilla, plantilla y carpeta exclusivas de pruebas, sin contenido institucional real. |
| Identidad | Alternativa A o B de la sección 3, a decidir por Vera Batista/DSI. Si se elige service account, la prueba debe incluir el mecanismo de creación en Shared Drive antes de generar Docs. |
| LLM | Ollama local con modelo versionado; sin envío de prompts o datos a APIs LLM externas. |
| Salidas | Documentos marcados `BORRADOR — NO PUBLICAR` y estado `PENDIENTE_VALIDACION`. |
| Evidencia | Logs redactados, correlation ID, hashes, versiones, resultados de pruebas y checklist. |
| Criterio de cierre | Smoke técnico exitoso, pruebas negativas de permisos y secretos, y cero defectos críticos abiertos. |

### 5.2 Entorno de preproducción

| Aspecto | Especificación |
|---|---|
| Objetivo | Validar HU-010 en un flujo controlado y representativo de la SEU antes de cualquier operación productiva. |
| Datos | Casos sintéticos y, sólo con autorización registrada, una muestra real limitada, minimizada y preferentemente anonimizada. |
| Usuarios | Validadores designados por la SEU desde el 4 de agosto; administrador DSI; Juan Ignacio Gone como ejecutor y custodio de evidencia. |
| Google Cloud | Se prefiere un proyecto de preproducción separado del de pruebas, con nombre e ID a definir por el DSI. El DSI puede aprobar un proyecto compartido únicamente con aislamiento equivalente documentado. |
| Workspace | Planilla, plantilla y carpeta de preproducción provistas o aprobadas por Josefina Carullo; no reutilizar recursos operativos de producción. |
| Identidad | Identidad exclusiva de preproducción, según la alternativa aprobada y con permisos mínimos sobre esos recursos. No se promoverá automáticamente la credencial de pruebas. |
| LLM | Ollama local sobre host aprobado por el DSI, con versión de modelo y configuración fijadas en el manifest de cada prueba. |
| Salidas | Sólo borradores. La aprobación humana queda registrada, pero no dispara publicación ni envío automático en este alcance. |
| Evidencia | Casos ejecutados, tiempos, checklist individual, observaciones SEU, defectos, logs y decisión de aceptación. |
| Criterio de cierre | Validación SEU documentada, trazabilidad reconstruible, permisos revisados y criterio de evidencia/TRL definido por César Cicerchia. |

En términos del plan de despliegue, pruebas corresponde a **D2 — Sandbox Workspace** y preproducción a **D3 — Piloto SEU controlado**. No son dos nombres para el mismo ambiente.

### 5.3 Aislamiento requerido

- Los dos ambientes no deben compartir credenciales, archivos de trabajo ni logs.
- Los IDs de proyectos, planillas, carpetas y plantillas se inyectarán como configuración; nunca se incorporarán al código fuente si revelan recursos institucionales.
- Una falla o revocación en pruebas no debe interrumpir preproducción.
- Ningún ambiente se considera producción ni puede publicar contenido.

## 6. Proyectos Google Cloud y APIs

Se prefiere un proyecto Google Cloud por ambiente bajo administración institucional del DSI. Esta separación reduce errores de configuración, permisos cruzados y mezcla de auditoría. No es un requisito absoluto: Vera Batista/DSI puede aprobar un proyecto compartido si documenta un aislamiento equivalente entre D2 y D3 mediante identidades distintas, recursos diferentes, configuración separada y logs identificados por ambiente. No se definen nombres ni IDs en este documento.

### 6.1 APIs requeridas

| API | Estado | Uso |
|---|---|---|
| Google Sheets API v4 | Obligatoria | Lectura de la fila o rango autorizado que contiene solicitudes. |
| Google Docs API v1 | Obligatoria | Creación y edición del borrador. |
| Google Drive API v3 | Condicional | Necesaria si se debe crear el Doc dentro de un Shared Drive, ubicarlo en una carpeta específica, copiar una plantilla o consultar metadatos. No se habilitará para compartir automáticamente. Estas operaciones todavía no están implementadas. |
| Gmail API | Fuera del alcance actual | Requiere una especificación y autorización adicional si el email institucional se automatiza. |

El adapter actual usa `spreadsheets.values.get` para Sheets y `documents.create` seguido de `documents.batchUpdate` para Docs. La [referencia REST de Sheets](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/get) y la [referencia REST de Docs](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents) constituyen la base del contrato técnico.

### 6.2 Permisos y scopes mínimos a evaluar

- Para la fuente Sheets de sólo lectura: `https://www.googleapis.com/auth/spreadsheets.readonly`. Este scope permite leer todos los spreadsheets a los que tenga acceso la identidad; no queda limitado por sí mismo al archivo, pestaña o rango configurado.
- Para crear/modificar documentos: `https://www.googleapis.com/auth/drive.file` es un candidato de menor alcance, pero Vera Batista/DSI debe validarlo contra la alternativa de identidad, la forma de selección/creación del archivo y el Shared Drive. No se lo declara suficiente antes de esa prueba.
- Evitar `https://www.googleapis.com/auth/drive`, `drive.readonly` y otros scopes amplios o restringidos mientras el caso pueda resolverse mediante archivos compartidos directamente.
- La frontera efectiva para Sheets debe ser un **spreadsheet dedicado por ambiente**, compartido sólo con la identidad correspondiente. La pestaña y el rango A1 configurados son controles de la aplicación, no límites de autorización de Google. Un `ProtectedRange` puede impedir modificaciones, pero no restringe la lectura y no agrega protección a una identidad que ya opera en modo read-only. Véanse los [scopes de Google Sheets](https://developers.google.com/workspace/sheets/api/scopes), los [scopes de Google Docs](https://developers.google.com/workspace/docs/api/auth) y los [scopes de Google Drive](https://developers.google.com/workspace/drive/api/guides/api-specific-auth).

Los scopes definitivos deben ser revisados por Vera Batista/DSI contra el método de identidad y el tipo de Drive seleccionado. La aplicación no administrará permisos ni compartirá archivos; esa provisión será realizada por el DSI o el responsable autorizado mediante la interfaz de Workspace.

## 7. Recursos de Google Workspace a provisionar

### 7.1 Google Sheets

Para cada ambiente se deberá informar por canal seguro:

- Spreadsheet ID;
- nombre de pestaña y rango A1 autorizado;
- fila de encabezados;
- política ante filas duplicadas, corregidas o eliminadas;
- permisos de lectura para la identidad técnica;
- propietario funcional y propietario técnico.

Encabezados provisionales implementados actualmente:

```text
id_solicitud,titulo,descripcion,fecha,publico,organiza,contacto,fuente,lugar
```

Estos encabezados están marcados `PROVISIONAL_NO_INSTITUCIONAL`. Josefina Carullo deberá confirmar los campos definitivos, obligatoriedad, formatos y vocabularios controlados. Los cambios se versionarán; no se modificará silenciosamente el contrato de una prueba en curso.

### 7.2 Google Docs y Drive

Para cada ambiente se deberá informar:

- Template ID o documento modelo aprobado;
- Folder ID de destino;
- ubicación en My Drive o Shared Drive, condicionada por la alternativa de identidad;
- convención de nombre del borrador;
- responsables con rol de lectura, comentario, edición y validación;
- política de documentos huérfanos o vacíos ante una falla intermedia;
- procedimiento de baja o archivo de evidencias.

Google Drive basa el acceso en permisos por archivo/carpeta y los permisos de una carpeta pueden heredarse hacia sus hijos; por eso la carpeta elegida no debe otorgar acceso lateral a material no relacionado. Véase la [guía oficial de permisos y uso compartido](https://developers.google.com/workspace/drive/api/guides/manage-sharing).

La operación `documents.create` y la inserción posterior no forman una única transacción. Si se crea un documento pero falla su actualización, el sistema registra un hash de reconciliación y no reintenta ciegamente la creación. El adapter actual **no copia plantillas ni mueve documentos a carpetas**. Si el diseño aprobado exige Shared Drive, plantilla o carpeta, primero habrá que implementar el flujo Drive correspondiente y definir qué ocurre si falla después de crear el archivo. El responsable técnico deberá revisar o eliminar cualquier documento huérfano según el procedimiento acordado.

## 8. Secretos y credenciales

### 8.1 Requisitos

- Almacenamiento fuera del repositorio, imágenes, scripts, logs y documentos de evidencia.
- Lectura en runtime desde un mecanismo aprobado por el DSI.
- Acceso limitado al proceso y a administradores designados.
- Permisos de archivo restrictivos si excepcionalmente se utiliza una clave local.
- Fecha de alta, propietario, ambiente, propósito, última rotación y procedimiento de revocación registrados sin copiar el secreto.
- Revocación inmediata ante exposición o baja del responsable.
- Tokens y claves redactados de errores, trazas y capturas.

Si el DSI autoriza temporalmente una clave JSON de service account, deberá definir almacenamiento cifrado, distribución, rotación y destrucción segura. Siempre que la infraestructura lo permita, se preferirá un mecanismo sin clave privada persistente; la selección concreta queda a cargo de Vera Batista/DSI. Google mantiene recomendaciones específicas para la [gestión de credenciales de Workspace](https://developers.google.com/workspace/guides/manage-credentials).

### 8.2 Elementos prohibidos

- contraseña del email institucional en variables, archivos o código;
- API key pública para documentos privados;
- credenciales embebidas en imágenes, repositorio o URLs;
- reuso de credenciales entre pruebas, preproducción y producción;
- domain-wide delegation sin expediente técnico y autorización;
- envío de secretos por email o mensajería;
- exposición de tokens, IDs sensibles o cuerpos remotos en logs.

## 9. Runtime local de Ollama

El primer release mantiene inferencia local para evitar transferir prompts y datos institucionales a un proveedor LLM externo.

### 9.1 Baseline técnico provisional

La implementación está probada con:

- Ollama local accesible únicamente por loopback (`127.0.0.1`, `localhost` o `::1`);
- modelo `llama3.2:3b` versionado en la evidencia;
- inferencia CPU, sin GPU obligatoria;
- timeout total configurable, actualmente 45 segundos por defecto;
- salida limitada y sometida a un gate mecánico antes de escribir en Workspace.

Como referencia de dimensionamiento —no como afirmación sobre infraestructura disponible ni requerimiento de compra— el PoC fue ejecutado sobre un host x86_64 de 4 núcleos/8 hilos y aproximadamente 16 GiB de RAM. Para provisionar un host institucional se propone medir primero con una capacidad equivalente o superior, reservar espacio para runtime, modelo, logs y actualizaciones, y registrar CPU, RAM, disco libre y latencia observada. Vera Batista/DSI deberá confirmar el host, sistema operativo, supervisión del proceso y capacidad asignada.

### 9.2 Controles operativos

- Ollama no se expondrá a la red institucional ni a Internet en esta etapa.
- El modelo y el binario no se almacenarán en Git.
- Cada evidencia registrará versión del runtime, modelo, parámetros, hash del prompt y latencia.
- Un timeout o una salida no conforme terminarán en `FALLIDA` sin crear borrador.
- No se promete un SLA: las corridas locales actuales distinguen carga cold de caché warm y todavía requieren baseline institucional.

## 10. Red y conectividad

### 10.1 Egress requerido

El host del Agente 1 necesita salida HTTPS/TCP 443, resuelta por DNS y con hora del sistema sincronizada, hacia los endpoints oficiales necesarios:

- `oauth2.googleapis.com` y endpoints de autenticación que determine el mecanismo elegido;
- `sheets.googleapis.com`;
- `docs.googleapis.com`;
- `www.googleapis.com` sólo si se habilita Drive API.

La allowlist final debe validarse con el DSI. No se requiere acceso a una API LLM externa.

### 10.2 Ingress

El flujo manual/CLI actual no requiere un endpoint público entrante. Si luego se incorpora un trigger de Apps Script, webhook o recepción automatizada de email, deberá agregarse una especificación de ingreso con TLS, autenticación, allowlist, rate limit, protección anti-replay y kill switch. No se expondrá Ollama como servicio remoto.

## 11. Logging, auditoría y privacidad

Cada ejecución deberá generar un evento estructurado con, como mínimo:

- timestamp y ambiente;
- correlation ID;
- hash del identificador de solicitud;
- historia de usuario y estado final;
- versiones de contrato, prompt, aplicación, modelo y parámetros;
- latencia y resultado técnico;
- códigos cerrados de error o validación;
- referencia opaca a evidencia y revisión humana.

No se registrarán:

- tokens, claves, passwords o cabeceras de autorización;
- prompt completo, fila fuente, datos personales o borrador completo;
- cuerpos de error de Google;
- URLs completas con IDs de recursos;
- email del validador si no es indispensable para la evidencia; en ese caso se usará identificador institucional controlado.

La retención de logs, borradores, backups y manifests está **pendiente de definición institucional**. Antes de preproducción, Vera Batista/DSI y la SEU deberán acordar plazo, custodio, ubicación, cifrado, restauración, acceso y eliminación. Hasta entonces no se almacenarán muestras reales de forma persistente fuera de los recursos autorizados.

## 12. Datos permitidos

| Ambiente | Datos permitidos | Datos prohibidos |
|---|---|---|
| Pruebas | Ficticios, sintéticos o anonimizados de forma irreversible | Datos personales reales, material sensible, contraseñas, documentos oficiales no autorizados |
| Preproducción | Sintéticos y muestra real mínima expresamente autorizada | Datos masivos, sensibles no necesarios, padrones completos, secretos, información fuera del propósito HU-010 |

La SEU deberá confirmar qué campos pueden contener datos personales y su necesidad. La minimización rige sobre planillas, prompts, outputs, logs, capturas y backups.

## 13. Smoke tests y aceptación

### 13.1 Pruebas de provisión

1. Obtener token sin imprimir ni persistir el secreto.
2. Leer únicamente el spreadsheet/rango configurado.
3. Verificar que otra planilla no autorizada sea rechazada.
4. Crear un documento de prueba marcado `BORRADOR — NO PUBLICAR`.
5. Insertar contenido sintético. Si se implementó y autorizó Drive API, comprobar por separado la creación/ubicación en Shared Drive o carpeta; no darla por cubierta por el adapter actual.
6. Verificar que el sistema no pueda publicar, enviar email ni compartir archivos.
7. Revocar el acceso y confirmar que una nueva ejecución falle de forma controlada y auditada.

### 13.2 Pruebas funcionales mínimas

- caso completo que termina en `PENDIENTE_VALIDACION`;
- caso incompleto rechazado antes de invocar el modelo;
- identificador inexistente o inválido;
- timeout o caída de Ollama;
- respuesta no conforme del modelo;
- error de Sheets;
- creación de Doc exitosa y actualización fallida, con reconciliación;
- redacción de credenciales y datos en logs;
- prueba de prompt injection sin ejecución de acciones no autorizadas.

### 13.3 Aceptación de preproducción

La aceptación requiere:

- entre tres y cinco casos representativos definidos con la SEU;
- checklist por caso sobre precisión, tono, estructura, extensión y alucinaciones;
- validador nominal y fecha de decisión;
- salida siempre en borrador;
- 100 % de ejecuciones con correlation ID y evidencia recuperable;
- cero secretos expuestos;
- cero defectos críticos abiertos;
- permisos mínimos revisados por el DSI;
- criterio de evidencia y Gate TRL informado por César Cicerchia.

Un smoke técnico exitoso no equivale a aceptación institucional ni a TRL 3.

## 14. Responsabilidades — RACI provisional

**R:** responsable de ejecutar. **A:** accountable/aprueba. **C:** consultado. **I:** informado.

| Actividad | César Cicerchia | Vera Batista / DSI | Administrador DSI designado | Josefina Carullo / SEU | Validadores SEU | Juan Ignacio Gone |
|---|---:|---:|---:|---:|---:|---:|
| Definir criterio de evidencia y TRL | A/R | C | I | C | I | C |
| Seleccionar identidad técnica y arquitectura de credenciales | I | A | R | I | I | C |
| Crear proyectos, habilitar APIs y custodiar secretos | I | A | R | I | I | C |
| Proveer planilla, carpeta, plantilla y campos | I | C | C | A/R | C | C |
| Designar validadores y suplentes | I | I | I | A/R | I | C |
| Preparar aplicación, pruebas y evidencias | I | C | C | C | C | A/R |
| Revisar permisos mínimos y conectividad | I | A | R | I | I | C |
| Validar borradores de preproducción | I | I | I | A | R | C |
| Autorizar avance de ambiente | A | C | C | C | C | R |
| Revocar accesos ante incidente | I | A | R | I | I | C |

La tabla es provisional hasta que el DSI designe al administrador y la SEU designe validadores a partir del 4 de agosto.

## 15. Checklist de provisión para Vera Batista / DSI

### 15.1 Por cada ambiente

- [ ] Crear o designar el o los proyectos Google Cloud institucionales, preferentemente uno por ambiente; si se comparte un proyecto, documentar y aprobar el aislamiento equivalente.
- [ ] Registrar Project ID por canal seguro, sin incorporarlo a evidencias públicas.
- [ ] Habilitar Sheets API y Docs API.
- [ ] Decidir si Drive API es necesaria para carpeta/plantilla.
- [ ] Crear identidad técnica y registrar propietario/suplente.
- [ ] Definir mecanismo de credenciales, almacenamiento, rotación y revocación.
- [ ] Compartir sólo la planilla, plantilla y carpeta correspondientes.
- [ ] Confirmar scopes efectivos y justificar cualquier scope amplio.
- [ ] Confirmar que no existe domain-wide delegation.
- [ ] Habilitar egress HTTPS únicamente hacia endpoints requeridos.
- [ ] Confirmar host de Ollama, capacidad asignada y responsable operativo.
- [ ] Definir ubicación de configuración no sensible y de secretos.
- [ ] Definir retención, backup, restauración y eliminación.
- [ ] Ejecutar smoke de permisos positivos y negativos.
- [ ] Registrar procedimiento de revocación y fallback manual.

### 15.2 Antes de preproducción

- [ ] Recibir planilla, carpeta y plantilla aprobadas por Josefina Carullo.
- [ ] Versionar encabezados, campos obligatorios y reglas de validación.
- [ ] Registrar validadores titulares/suplentes designados por la SEU.
- [ ] Aprobar muestra de datos y condiciones de anonimización.
- [ ] Ejecutar checklist de seguridad y prompt injection.
- [ ] Confirmar que no existe publicación, envío o sharing automático.
- [ ] Acordar criterio de evidencia/TRL con César Cicerchia.

## 16. Preguntas pendientes para coordinación

### 16.1 Para Vera Batista / DSI

1. ¿Se elige la alternativa A —cuenta `@fie.undef.edu.ar` con consentimiento OAuth— o la alternativa B —service account con Shared Drive/recursos compartidos— para cada ambiente?
2. Si se elige A, ¿quién custodia el refresh token y los archivos se crearán en My Drive —con propiedad de la cuenta— o en un Shared Drive —con pertenencia institucional—?
3. Si se elige B, ¿qué Shared Drive institucional alojará los Docs y qué rol mínimo tendrá la service account?
4. ¿Se habilitará Drive API para crear/ubicar/copiar documentos o la carpeta se administrará manualmente?
5. ¿Qué mecanismo institucional se utilizará para secretos y rotación?
6. ¿Qué host podrá ejecutar Ollama y quién operará/reiniciará el servicio?
7. ¿Qué restricciones de firewall, proxy, DNS y certificados deben contemplarse?
8. ¿Qué retención, backup, monitoreo e incident response se exigirán?

### 16.2 Para Josefina Carullo / SEU

1. ¿Cuál es la planilla y cuáles son los encabezados, formatos y campos obligatorios definitivos?
2. ¿Cuál es la plantilla aprobada de gacetilla y su carpeta de borradores?
3. ¿Qué roles tendrán lectura, comentario, edición y aprobación?
4. ¿Cómo se registrarán `APROBADA`, `OBSERVADA` y `RECHAZADA`?
5. ¿Qué tres a cinco casos representativos podrán utilizarse sin exponer información innecesaria?
6. ¿Qué función concreta tendrá el email institucional en el primer release?

### 16.3 Para César Cicerchia

1. ¿Qué evidencia mínima y qué firmantes exige para considerar cumplido el Gate TRL 3?
2. ¿HU-010 y HU-011 deben aprobarse conjuntamente para ese gate?
3. ¿Qué documento o acta formalizará el go/no-go de preproducción?

## 17. Entregables esperados de la coordinación

La coordinación con Vera Batista deberá producir, sin incluir secretos:

1. decisión de identidad y diagrama de acceso;
2. proyectos y APIs por ambiente;
3. inventario de recursos con responsables e IDs entregados por canal seguro;
4. matriz de scopes y permisos efectivos;
5. procedimiento de alta, rotación, revocación e incidente;
6. baseline del host Ollama y prueba de conectividad;
7. acta de smoke técnico;
8. pendientes y condiciones de avance a preproducción.

## 18. Fuentes

### 18.1 Fuentes institucionales del proyecto

- `Contenido/bible/PROYECTO-FIE 2026-2027 - Cicerchia Cesar.md` — infraestructura mínima, preproducción y madurez tecnológica.
- `Contenido/bible/Procesos y Agentes.md` — Proceso 4, Google Workspace, Agente 1 y validación humana.
- `Contenido/bible/Correo de Facultad de Ingenieria del Ejercito - Proyecto Agentes IA.md` — apoyo de infraestructura de Vera Batista.
- `Documentos/PlanDespliegue/Plan-Despliegue-Agente-1-PPS-Juan-Ignacio-Gone.md` — ambientes, gates, seguridad, evidencia y roles.
- `Implementacion/Agente1/README.md` — estado técnico verificable de los adapters y del runtime local.

### 18.2 Documentación oficial de Google

- [Crear y elegir credenciales para Google Workspace](https://developers.google.com/workspace/guides/create-credentials).
- [Administrar credenciales de Google Workspace](https://developers.google.com/workspace/guides/manage-credentials).
- [Scopes de Google Sheets](https://developers.google.com/workspace/sheets/api/scopes).
- [Scopes de Google Docs](https://developers.google.com/workspace/docs/api/auth).
- [Scopes de Google Drive](https://developers.google.com/workspace/drive/api/guides/api-specific-auth).
- [Permisos y uso compartido en Google Drive](https://developers.google.com/workspace/drive/api/guides/manage-sharing).

---

**Criterio de uso:** esta especificación permite provisionar pruebas y preparar preproducción. No autoriza producción, publicación, envío automático, acceso general al dominio ni declaración de TRL.
