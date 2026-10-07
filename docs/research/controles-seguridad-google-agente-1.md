# Controles de seguridad de Google aplicables a la identidad del Agente 1

- **Ticket:** «Controles de seguridad de Google aplicables a la identidad del Agente 1»
- **Fecha de consulta de todas las fuentes:** 2026-10-07 (la mayoría de las páginas de Google mostraban "Last updated 2026-10-07 UTC").
- **Alcance:** solo hechos documentados por Google, con el link de cada uno. Este documento **no recomienda** ninguna alternativa; la elección se toma en otro ticket.
- **Fuentes:** `developers.google.com`, `support.google.com/a`, `cloud.google.com` y `knowledge.workspace.google.com` (subdominio de `workspace.google.com`, donde Google publica hoy las tablas comparativas de ediciones). Hay dos excepciones, marcadas donde aparecen: `support.google.com/cloud` (ayuda de Google Cloud Console) y `support.google.com/accounts` (ayuda de la cuenta de Google). Las dos son de Google, pero quedan fuera de la lista de dominios del ticket.
- **Método:** se descargó cada página y se extrajo el texto literal. Las citas en inglés son textuales.

---

## Resumen

1. **Identidad.** Google documenta tres caminos: (a) usuario dedicado con OAuth y refresh token, (b) service account sin delegación que trabaja sobre una unidad compartida, y (c) service account con domain-wide delegation (DWD). Para (a), Google advierte en su página general de OAuth: "you must not use, or encourage the use of, user credentials for server-to-server deployment". La advertencia aparece en el contexto de las políticas de sesión de Google Cloud. Para (c), la guía de Workspace dice "Avoid using domain-wide delegation if you can accomplish your task directly using a service account or by using OAuth consent", y aclara que con DWD "the app has access to the data belonging to all of your users". Para (b), las service accounts "don't have storage quota and can't own files" y "aren't subject to domain policies set by Google Workspace administrators".
2. **Scopes.** `drive.file` es **non-sensitive**. `spreadsheets`, `documents` y `gmail.send` son **sensitive**. `drive` y `gmail.readonly` son **restricted**. Una app de tipo **Internal** dentro de la organización no necesita verificación de Google, ni siquiera con scopes sensitive o restricted. En cambio, la consola de administración trata `gmail.send`, `gmail.readonly`, `drive` y `documents` como scopes **high-risk**: si el admin pone Gmail o Drive en *Restricted*, la app debe estar marcada como *Trusted*, o tiene que estar activada la opción "Trust internal apps".
3. **Refresh token.** La regla de 7 días aplica solo a proyectos con user type **External** y estado **Testing**. Sin uso durante 6 meses, el token deja de funcionar. Un cambio de contraseña lo invalida si incluye scopes de Gmail. Hay un tope de 100 refresh tokens por cuenta y por client ID, y al pasarlo se invalida el más viejo sin aviso. El usuario y el admin pueden revocarlo, y el admin también puede invalidarlo restringiendo el servicio en API Controls. La duración de sesión web de Google **no** invalida refresh tokens de APIs que no son de Google Cloud.
4. **Sin costo en Education Fundamentals:** 2SV y llaves de seguridad (el modo "Only security key" acepta también passkeys), API Controls (Trusted/Limited/Blocked, restricción de servicios, "Trust internal apps"), configuración de uso compartido externo de Drive y de unidades compartidas, *Restrict delivery* de Gmail, DLP de Drive y Gmail, alert center, *audit and investigation tool* con los registros Admin, Drive, Gmail, OAuth y User (login), y activity rules **solo de notificación**.
5. **Requieren Education Standard o Education Plus:** Context-Aware Access, trust rules de Drive, security investigation tool, eventos **API call** del registro OAuth, activity rules con acciones o umbrales, export a BigQuery y reportes del dashboard de seguridad (por ejemplo, "OAuth grants to new apps"). El **Teaching and Learning add-on** no agrega controles de seguridad ni de auditoría de los relevados acá.
6. **Retención:** los registros Admin, Drive, Gmail, OAuth Token y User se conservan 6 meses. Email log search, 30 días. El admin no puede cambiar ni borrar esos plazos.
7. **Claves de service account:** Google las trata como riesgo. Las restricciones de creación y subida de claves vienen activadas por defecto en organizaciones GCP creadas desde el 2024-05-03. Para DWD, Google indica usar `signJwt` en lugar de claves. Para hosts fuera de Google Cloud, documenta Workload Identity Federation (incluye certificados X.509 y AD on-premises), HSM o TPM, o un key store por software. Desaconseja dejar la clave como archivo y guardarla en Secret Manager u otro secret store en la nube.

---

## 1. Opciones de identidad y riesgos que documenta Google

### 1.a Cuenta de usuario dedicada + OAuth (app Internal) + refresh token

- **Qué es una app Internal:** "can configure **Internal** users to limit authorization requests to members of the organization." [support.google.com/cloud/answer/15549945](https://support.google.com/cloud/answer/15549945?hl=en) *(dominio support.google.com/cloud)*
- **Verificación:** no hace falta si "The app is only used by people in your Google Workspace or Cloud Identity organization", el proyecto pertenece a la organización y el consent screen es Internal. Además, "Your app will not be subject to the unverified app screen or the 100-user cap if it's designated as internal-only." [support.google.com/cloud/answer/13464323](https://support.google.com/cloud/answer/13464323?hl=en) *(dominio support.google.com/cloud)*
- "For apps used only internally by your Google Workspace organization, scopes aren't listed on the consent screen and use of restricted or sensitive scopes doesn't require further review by Google." [developers.google.com/workspace/guides/configure-oauth-consent](https://developers.google.com/workspace/guides/configure-oauth-consent)
- **Proyecto dentro de la organización:** "it is strongly recommended that your developer project is created inside a organization resource within your Google Workspace or Cloud Identity account. This lets you use enterprise management features [...] without tying it to an individual developer account. Otherwise, it might be difficult (or impossible) to transfer to a new owner in the future." [developers.google.com/identity/protocols/oauth2/production-readiness/google-workspace](https://developers.google.com/identity/protocols/oauth2/production-readiness/google-workspace?hl=en)
- **Riesgo documentado: credenciales de usuario en un servidor.** "Equally, you must not use, or encourage the use of, user credentials for server-to-server deployment. If user credentials are deployed on a server for long running jobs or operations and a customer applies session control policies on such users, the server application will fail as there will be no way to re-authenticate the user when the session duration expires." [developers.google.com/identity/protocols/oauth2](https://developers.google.com/identity/protocols/oauth2?hl=en) (sección *Dealing with session control policies for Google Cloud Platform (GCP) organizations*). La sección se refiere a la *Google Cloud session control*, que afecta a apps "that requires the Cloud Platform scope". Ver §3.
- **Riesgo documentado: robo de tokens.** "User tokens include both refresh tokens and access tokens [...] Store tokens securely at rest and never transmit them in plain text." Google ofrece **DPoP** para atar el refresh token a una clave del cliente: "Google's OAuth 2.0 implementation supports DPoP binding for refresh tokens. Issued access tokens remain standard Bearer tokens". [developers.google.com/identity/protocols/oauth2/resources/best-practices](https://developers.google.com/identity/protocols/oauth2/resources/best-practices?hl=en)
- La cuenta de usuario **sí** queda sujeta a las políticas del dominio: 2SV, API Controls, uso compartido de Drive, Context-Aware Access según la edición, Advanced Protection. Ver §4.

### 1.b Service account sin delegación, con acceso a una unidad compartida

- "Note: Service accounts don't have storage quota and can't own files. Instead, they must upload files and folders into shared drives, or use OAuth 2.0 to upload items on behalf of a human user." [developers.google.com/workspace/drive/api/guides/about-shareddrives](https://developers.google.com/workspace/drive/api/guides/about-shareddrives?hl=en). La misma nota figura en [handle-errors](https://developers.google.com/workspace/drive/api/guides/handle-errors?hl=en).
- "Personal Google Accounts (@gmail.com) cannot create shared drives, but they can be added as members if the organization permits external sharing. There is no additional fee per shared drive created." (mismo link de about-shareddrives).
- **Riesgo documentado: queda fuera de las políticas del dominio.** "Although you can use service accounts in applications that run from a Google Workspace domain, service accounts are not members of your Google Workspace account and aren't subject to domain policies set by Google Workspace administrators. For example, a policy set in the Google Workspace Admin console to restrict the ability of Google Workspace end users to share documents outside of the domain wouldn't apply to service accounts." [developers.google.com/identity/protocols/oauth2/service-account](https://developers.google.com/identity/protocols/oauth2/service-account?hl=en)
- **Riesgo documentado: la clave privada.** "having access to the private key is similar to knowing a user's password." Las amenazas que Google enumera son credential leakage, privilege escalation, information disclosure y non-repudiation. [cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys](https://cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys?hl=en)
- Context-Aware Access "can control app access only from end user accounts. They don't restrict access to Google APIs from service accounts." [support.google.com/a/answer/9275380](https://support.google.com/a/answer/9275380?hl=en). Para un matiz sobre Drive, ver §4.6.
- El indicador de "archivo externo" de Drive "is always shown if any service accounts can access the file, regardless of whether the service account is owned by someone inside or outside of your organization." [support.google.com/a/answer/60781](https://support.google.com/a/answer/60781?hl=en)
- Las trust rules sí alcanzan a las service accounts: "service accounts are included in the condition Anyone with a Google Account". [support.google.com/a/answer/10621317](https://support.google.com/a/answer/10621317?hl=en)
- **Gmail:** ver "No documentado / ambiguo". No se encontró una página que diga explícitamente si una service account sin DWD puede usar la Gmail API.

### 1.c Service account con domain-wide delegation (DWD)

- "Domain-wide delegation is a powerful feature that lets you grant client applications permission to access your Workspace users' data without requiring their consent." y "With domain-wide delegation, the app has access to the data belonging to all of your users. We recommend setting up a regular review of service accounts and deleting any accounts no [longer needed]". Configurarla requiere super admin. [support.google.com/a/answer/162106](https://support.google.com/a/answer/162106?hl=en)
- Best practices de Google:
  - "Avoid using domain-wide delegation if you can accomplish your task directly using a service account or by using OAuth consent."
  - "Although OAuth scopes don't restrict which users the service account can impersonate, they restrict the types of user data that the service account can access."
  - "Use organization policies to restrict key creation and upload for service accounts with domain-wide delegation."
  - "Host service accounts in dedicated Google Cloud projects."
  - "Using service account keys is not necessary to perform domain-wide delegation. Use the signJwt API instead."
  - "Minimize the number of people that have edit access to Google Cloud projects with domain-wide delegation set up."

  Fuente: [support.google.com/a/answer/14437356](https://support.google.com/a/answer/14437356?hl=en)
- El acceso queda acotado por el usuario suplantado: "The service account's access is constrained by two factors: the permissions of the impersonated user and the OAuth scopes you authorize in the Admin console." [developers.google.com/identity/protocols/oauth2/service-account](https://developers.google.com/identity/protocols/oauth2/service-account?hl=en)
- "While DWD does not change token lifetimes, it allows administrators to pre-authorize apps, bypassing user consent". [production-readiness/google-workspace](https://developers.google.com/identity/protocols/oauth2/production-readiness/google-workspace?hl=en)

---

## 2. Scopes mínimos y su clasificación

| Scope | Descripción oficial (resumida) | Clasificación de Google | ¿"High-risk" en API Controls? | Fuente |
|---|---|---|---|---|
| `drive.file` | Solo archivos creados o abiertos por la app, o compartidos con ella vía Picker | **Non-sensitive** ("Recommended") | No figura en la lista | [Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth) |
| `drive` | "View and manage all your Drive files" | **Restricted** | Sí | [Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth) · [13152743](https://support.google.com/a/answer/13152743?hl=en) |
| `spreadsheets` | "See, edit, create, and delete all your Google Sheets spreadsheets" | **Sensitive** | No figura en la lista | [Sheets scopes](https://developers.google.com/workspace/sheets/api/scopes) |
| `documents` | "See, edit, create, and delete all your Google Docs documents" | **Sensitive** | **Sí** (figura en la lista de Drive) | [Docs scopes](https://developers.google.com/workspace/docs/api/auth) · [13152743](https://support.google.com/a/answer/13152743?hl=en) |
| `gmail.send` | "Send email on your behalf" | **Sensitive** | **Sí** | [Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes) · [13152743](https://support.google.com/a/answer/13152743?hl=en) |
| `gmail.readonly` | "View your email messages and settings" | **Restricted** | **Sí** | [Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes) · [13152743](https://support.google.com/a/answer/13152743?hl=en) |

- Las APIs de Sheets y Docs también aceptan `drive.file` (non-sensitive) como alternativa a `spreadsheets` o `documents`. [Sheets scopes](https://developers.google.com/workspace/sheets/api/scopes) · [Docs scopes](https://developers.google.com/workspace/docs/api/auth)
- Guía general: "you should choose the most narrowly focused scope possible and avoid requesting scopes that your app doesn't require." [Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)
- **Restricted y apps externas:** "If you store restricted scope data on servers (or transmit), then you must go through a security assessment." [Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)
- **Implicancia para apps Internal:** no requieren verificación ni revisión de scopes sensitive o restricted (ver §1.a). La página de scopes de Gmail **no** menciona la excepción para apps Internal; esa excepción está en las páginas de verificación citadas en §1.a.
- **Implicancia en API Controls (separada de la clasificación):**
  - "For Gmail and Google Drive, you can specifically restrict access to high-risk services". Si el admin cambia el servicio a *Restricted*, "any previously installed apps that you haven't trusted stop working and tokens are revoked".
  - Opción del admin: "For apps that are not trusted, allow users to give access to OAuth scopes that aren't classified as high-risk (for example, scopes that allow apps to access user-selected files in Drive)".
  - "Trusted—Trusting an app overrides a service restriction."
  - "If you build internal apps (owned by your organization), you can trust all apps to access restricted Google Workspace APIs" (casilla **Trust internal apps**).

  Fuente: [support.google.com/a/answer/13152743](https://support.google.com/a/answer/13152743?hl=en)

---

## 3. Ciclo de vida del refresh token

Fuente principal: [developers.google.com/identity/protocols/oauth2 — Refresh token expiration](https://developers.google.com/identity/protocols/oauth2?hl=en#expiration)

| Causa de invalidación | Texto de Google |
|---|---|
| Revocación por el usuario | "The user has revoked your app's access." |
| Inactividad | "The refresh token has not been used for six months." |
| Cambio de contraseña | "The user changed passwords and the refresh token contains Gmail scopes." |
| Tope de tokens | "The user account has exceeded a maximum number of granted (live) refresh tokens." |
| Acceso por tiempo | "The user granted time-based access to your app and the access expired." |
| Acción del admin | "If an admin set any of the services requested in your app's scopes to Restricted (the error is `admin_policy_enforced`)." |
| Sesión de Google Cloud | "For Google Cloud Platform APIs - the session length set by the admin could have been exceeded." |

- **Regla de 7 días:** "A Google Cloud Platform project with an OAuth consent screen configured for an **external** user type and a publishing status of "Testing" is issued a refresh token expiring in 7 days, unless the only OAuth scopes requested are a subset of name, email address, and user profile". El texto la limita a *External + Testing*. Ninguna página consultada dice que un proyecto Internal tenga refresh tokens con vencimiento fijo. La página de audiencia confirma: "Authorizations by a test user will expire seven days from the time of consent." [support.google.com/cloud/answer/15549945](https://support.google.com/cloud/answer/15549945?hl=en) *(dominio support.google.com/cloud)*
- **Tope por cliente:** "There is currently a limit of 100 refresh tokens per Google Account per OAuth 2.0 client ID. If the limit is reached, creating a new refresh token automatically invalidates the oldest refresh token without warning. This limit does not apply to service accounts."
- **Tope global:** "There is also a larger limit on the total number of refresh tokens a user account or service account can have across all clients." El valor no está publicado.
- **Contraseña (lado admin):** "the password change invalidates access tokens as well as refresh tokens". Según el FAQ, si la misma contraseña se vuelve a fijar vía Directory API con el mismo hash, "this will not be treated as a password change". [support.google.com/a/answer/6328616](https://support.google.com/a/answer/6328616?hl=en)
- **Revocación por el usuario:** desde la configuración de su cuenta. [Third-party apps with account access](https://support.google.com/accounts/answer/13533235?hl=en) *(dominio support.google.com/accounts)*. La app también puede revocar por programa: "Revocation removes all OAuth 2.0 scopes previously granted to a project, invalidating any issued access or [refresh tokens]". [developers.google.com/identity/protocols/oauth2/web-server](https://developers.google.com/identity/protocols/oauth2/web-server?hl=en)
- **Revocación por el admin:**
  - Desde la página de seguridad del usuario: "The Security page allows you to see all active 3-legged OAuth 2.0 tokens for a given user for a given application. The token listing and revocation is by user by app." [support.google.com/a/answer/2538798](https://support.google.com/a/answer/2538798?hl=en)
  - Por API: `tokens.delete`, que "Deletes all access tokens issued by a user for an application." [Directory API tokens.delete](https://developers.google.com/workspace/admin/directory/reference/rest/v1/tokens/delete)
  - Indirectamente: "Administrators can block apps, limit their access to certain services, or revoke access entirely, which renders associated refresh tokens invalid." [production-readiness/google-workspace](https://developers.google.com/identity/protocols/oauth2/production-readiness/google-workspace?hl=en)
- **Duración de sesión:**
  - "General Google Services Session Control [...] typically does not invalidate OAuth refresh tokens granted to third-party applications for accessing API data (such as Gmail, Drive, or Calendar APIs), unless the scopes are specifically Google Cloud related."
  - "Google Cloud Session Control [...] Exceeding this session length can invalidate refresh tokens associated with those Google Cloud scopes."

  Fuente: [production-readiness/google-workspace](https://developers.google.com/identity/protocols/oauth2/production-readiness/google-workspace?hl=en)

---

## 4. Controles de la consola de administración

### 4.1 2SV obligatoria, llaves de seguridad y passkeys
- El admin puede exigir 2SV y un método concreto: "you can enforce a method for certain users or groups". "Google is enforcing 2SV for administrator accounts." [support.google.com/a/answer/9176657](https://support.google.com/a/answer/9176657?hl=en)
- Modo **Only security key**: "Since the addition of passkeys, the Only security key option now supports both security keys and passkeys as a 2SV method." "If 2SV is enforced in Only security key mode, users cannot generate their own backup verification codes. An admin must provide these codes to the user." (mismo link)
- "Security keys are the most secure form of 2SV and protect against phishing threats." [support.google.com/a/answer/175197](https://support.google.com/a/answer/175197?hl=en)
- **Cuenta técnica sin uso interactivo:** ninguna página consultada explica cómo 2SV o la exigencia de llave interactúan con un refresh token ya emitido para una cuenta que solo usa APIs. Ver "No documentado / ambiguo".
- **Edición:** según la tabla comparativa, "2-Step Verification" y "Security keys for 2-Step Verification" están en Education Fundamentals, Standard y Plus. [Compare Education editions](https://knowledge.workspace.google.com/admin/getting-started/editions/compare-education-editions)

### 4.2 API access control (apps de confianza o bloqueadas)
- Cada app se puede marcar como **Trusted**, **Limited** ("Can access only unrestricted Google services") o **Blocked** ("Can't access any Google service"). Cada servicio (Gmail, Drive, etc.) puede quedar *Unrestricted* o *Restricted*.
- "Block all third-party API access": en ediciones Education, la casilla es "Don't allow users to access any third-party apps with their account". "Some settings override API settings. For example, users will still be able to access apps configured with Trusted or Limited access".
- "Allow access to third-party apps that only require Google sign-in [...] Note: This option is not available in Workspace Education editions."
- Se puede activar **Trust internal apps**.

  Fuente: [support.google.com/a/answer/13152743](https://support.google.com/a/answer/13152743?hl=en)
- En Education se pueden fijar valores distintos para usuarios mayores y menores de 18 años. [support.google.com/a/answer/7281227](https://support.google.com/a/answer/7281227?hl=en)
- **Edición:** ninguna de las dos páginas tiene bloque de "Supported editions", y ambas describen opciones propias de las ediciones Education. La tabla comparativa no tiene una fila específica para API Controls.

### 4.3 Uso compartido externo de Drive
- "Supported for all Google Workspace, Cloud Identity, and G Suite editions": controlar si se comparte fuera de la organización, allowlist de dominios ("Users can't share files with personal accounts") e indicador de archivos externos. [support.google.com/a/answer/60781](https://support.google.com/a/answer/60781?hl=en)
- **Trust rules** dan control más fino por usuario, grupo, unidad organizativa o dominio. Ediciones: "Frontline Plus; Enterprise Standard and Enterprise Plus; Education Standard and Education Plus; Enterprise Essentials Plus." [support.google.com/a/answer/10621317](https://support.google.com/a/answer/10621317?hl=en)

### 4.4 Unidades compartidas y propiedad de los archivos
- "Files in shared drives are owned by your organization, rather than an individual. They persist even if the person who created the file leaves your organization". Ediciones: incluye Education Fundamentals, Standard y Plus. [support.google.com/a/answer/7337469](https://support.google.com/a/answer/7337469?hl=en)
- Configuración del admin para unidades compartidas: "Allow users outside your organization to access files in shared drives—When unchecked, external users can't have access [...] This setting also blocks shared drive managers from adding external users as members." También "Allow people who aren't shared drive members to be added to files" y "Allow viewers and commenters to download, print, and copy files". Ediciones: incluye Education Fundamentals. [support.google.com/a/answer/7662202](https://support.google.com/a/answer/7662202?hl=en)
- Archivos de una service account: no puede ser dueña (ver §1.b).

### 4.5 Restringir destinatarios de Gmail (para la lista permitida de envío)
- *Restrict delivery* (Compliance): "People in your organization who try to send messages to an unauthorized domain get a bounce message". Se aplica por unidad organizativa y con listas de direcciones o dominios. La página no muestra bloque de ediciones. [support.google.com/a/answer/2640542](https://support.google.com/a/answer/2640542?hl=en)

### 4.6 Context-Aware Access (CAA)
- Ediciones: "Frontline Standard and Frontline Plus; Enterprise Standard and Enterprise Plus; **Education Standard and Education Plus**; Enterprise Essentials Plus; Cloud Identity Premium." Solo aplica a usuarios con licencia de esas ediciones.
- "Context-Aware Access policies can control app access only from end user accounts. They don't restrict access to Google APIs from service accounts."
- A la vez: "Context-Aware Access policies applied to Google Drive also apply to background automated systems [...] make sure your security policies allow the tool's network IP subnets or exempt its service account."

  Fuente: [support.google.com/a/answer/9275380](https://support.google.com/a/answer/9275380?hl=en)

### 4.7 Advanced Protection Program (APP)
- "It's available for consumer as well as enterprise Google accounts." Aplica, entre otras cosas, "Strong authentication with security keys or passkeys" y "Restrictions on third-party access to account data. Apps that require high-risk scopes are blocked unless they're explicitly trusted by admins or on the default list of trusted apps." La página no tiene bloque de ediciones. [support.google.com/a/answer/9378686](https://support.google.com/a/answer/9378686?hl=en)

---

## 5. Auditoría y alertas

| Registro | Qué cubre (relevante para A1) | Retención | Fuente |
|---|---|---|---|
| Admin log events | Cambios hechos por admins en la consola | 6 meses | [4579579](https://support.google.com/a/answer/4579579?hl=en) · [7061566](https://support.google.com/a/answer/7061566?hl=en) |
| Drive log events | Actividad sobre archivos de Docs, Sheets y otros. "Not all activities in Drive are logged." "Most Drive audit events are logged only for files owned by users with supported editions." | 6 meses | [4579696](https://support.google.com/a/answer/4579696?hl=en) · [7061566](https://support.google.com/a/answer/7061566?hl=en) |
| OAuth (Token) log events | Concesión y revocación de acceso por app. Campos *API name* y *API method*. **"API call events are available only for Enterprise Plus, Education Plus, Enterprise Standard, Education Standard, and Cloud Identity Premium."** | 6 meses | [6124308](https://support.google.com/a/answer/6124308?hl=en) · [7061566](https://support.google.com/a/answer/7061566?hl=en) |
| User log events (antes "Login audit") | Inicios de sesión y eventos de cuenta | 6 meses | [4580120](https://support.google.com/a/answer/4580120?hl=en) · [7061566](https://support.google.com/a/answer/7061566?hl=en) |
| Gmail log events | Actividad de Gmail de usuarios y admins | 6 meses | [11479100](https://support.google.com/a/answer/11479100?hl=en) · [7061566](https://support.google.com/a/answer/7061566?hl=en) |
| Email log search | Búsqueda de entrega de mensajes | 30 días | [7061566](https://support.google.com/a/answer/7061566?hl=en) |

- "Administrators cannot delete log event data or change the length of time that the data is available for." Demoras hasta que el dato aparece: Admin, Drive, Gmail y login, "near real time"; OAuth, "up to a few hours"; Token, "a couple of hours". [support.google.com/a/answer/7061566](https://support.google.com/a/answer/7061566?hl=en)
- **Activity rules** ([support.google.com/a/answer/11341109](https://support.google.com/a/answer/11341109?hl=en)):
  - "All Workspace editions can create activity rules that automatically send notifications based on events."
  - Según la tabla de la página, **Education Fundamentals y Education Standard** tienen solo *Notifications*. **Education Plus** tiene *Notifications*, *Actions* y *Thresholds*.
  - "By default, up to five alerts are sent per hour."
  - "You can't create activity rules based on live-state data sources".
- **Alert center:** disponible en las tres ediciones Education ("Alert center: Notifications of potential security issues"). [Compare Education editions](https://knowledge.workspace.google.com/admin/getting-started/editions/compare-education-editions). Incluye alertas como "Suspicious login", "Suspicious programmatic login" y "Leaked password". [support.google.com/a/answer/9104586](https://support.google.com/a/answer/9104586?hl=en)
- **Retener más tiempo:** export a BigQuery solo en Education Standard y Plus. [Compare Education editions](https://knowledge.workspace.google.com/admin/getting-started/editions/compare-education-editions). Compartir con Google Cloud Logging: Admin y User log events en general; OAuth y SAML solo en Enterprise, Education Standard o Plus, Voice Premier o Cloud Identity Premium. Allí, "retained according to the Google Cloud admin audit log retention policy". [support.google.com/a/answer/9320190](https://support.google.com/a/answer/9320190)

---

## 6. Credenciales de service account y secretos en un host fuera de la nube

Fuente principal: [cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys](https://cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys?hl=en)

- "Service account keys can become a security risk if not managed carefully. You should choose a more secure alternative for authentication whenever possible."
- **Restricción por org policy:** "apply the Disable service account key creation and Disable service account key upload constraints to establish a default where service account keys are disallowed. Note: If your organization was created on or after May 3, 2024, these constraints are enforced by default." Las constraints son `iam.disableServiceAccountKeyCreation` (legacy) e `iam.managed.disableServiceAccountKeyCreation` (managed), más las de upload. [cloud.google.com/resource-manager/docs/organization-policy/restricting-service-accounts](https://cloud.google.com/resource-manager/docs/organization-policy/restricting-service-accounts?hl=en) · [secure-by-default-organizations](https://cloud.google.com/resource-manager/docs/secure-by-default-organizations?hl=en)
- **Vencimiento de claves:** "By default, service account keys [...] don't have an expiry time and stay valid until you delete them." La constraint `iam.serviceAccountKeyExpiryHours` acepta valores de 1 h a 2160 h. Google desaconseja usar expiry en "Production workloads" y propone rotar en su lugar. (links anteriores)
- **Claves filtradas:** con `iam.serviceAccountKeyExposureResponse` = `DISABLE_KEY`, "Google Cloud will automatically disable any leaked keys that it detects". Aclara que "Google Cloud doesn't guarantee that it will detect leaked keys."
- **Almacenamiento en el host:**
  - "Whenever possible, avoid storing service account keys on a file system. If you can't avoid storing keys on disk, make sure to restrict access to the key file, configure file access auditing, and encrypt the underlying disk."
  - "Use an HSM or TPM to store keys": se genera el par en HSM o TPM y se sube el certificado. "An HSM or TPM lets you use a private key without ever revealing the key in clear text."
  - "Use a software-based key store", revisando cómo se protege la master key y el proceso de unseal.
  - "Don't store keys in Secret Manager or other cloud-based secret stores", porque si la app ya tiene identidad reconocida por la nube puede usarla en lugar de la clave.
  - "Don't leave service account keys in temporary locations" (por ejemplo, la carpeta de descargas).
- **Sin claves fuera de Google Cloud:** "Using Workload Identity Federation, you can provide on-premises or multicloud workloads with access to Google Cloud resources by using federated identities instead of a service account key", con "X.509 client certificates", "on-premises Active Directory" o un IdP OIDC o SAML. [cloud.google.com/iam/docs/workload-identity-federation](https://cloud.google.com/iam/docs/workload-identity-federation?hl=en)
- **DWD sin claves:** autenticar con WIF y luego "Construct a JWT and use the sub claim [...] Use the signJwt API to sign the JWT". (best-practices-for-managing-service-account-keys, sección *Avoid using service account keys for domain-wide delegation*)
- **Client secret y tokens OAuth (camino 1.a):** "Only store these credentials in secure storage, for example using a secret manager [...] Do not hardcode the credentials, commit them to a code repository or publish them publicly." Para servidores: "encrypt them at rest and ensure that your datastore is not publicly accessible to the Internet." [oauth2/resources/best-practices](https://developers.google.com/identity/protocols/oauth2/resources/best-practices?hl=en)

---

## 7. Matriz control → edición de Workspace requerida

Fuente de la matriz, salvo que la fila diga otra cosa: [Compare Education editions](https://knowledge.workspace.google.com/admin/getting-started/editions/compare-education-editions), leída de las celdas HTML de la tabla. ✔ = incluido · — = no incluido · ? = la fuente no lo indica.

| Control | Ed. Fundamentals (sin costo) | Teaching & Learning add-on | Ed. Standard | Ed. Plus | Business / Enterprise | Fuente adicional |
|---|---|---|---|---|---|---|
| 2SV obligatoria | ✔ | no agrega | ✔ | ✔ | todas | [9176657](https://support.google.com/a/answer/9176657?hl=en) |
| Llaves de seguridad / passkeys ("Only security key") | ✔ | no agrega | ✔ | ✔ | ? | [9176657](https://support.google.com/a/answer/9176657?hl=en) |
| Session length (Google Cloud y Google services) | ✔ | no agrega | ✔ | ✔ | ? | — |
| API Controls (Trusted/Limited/Blocked, servicios restringidos, Trust internal apps) | ✔ (sin bloque de ediciones; tiene opciones propias de Education) | no agrega | ✔ | ✔ | todas (ídem) | [13152743](https://support.google.com/a/answer/13152743?hl=en) |
| Domain-wide delegation | ✔ (sin bloque de ediciones) | — | ✔ | ✔ | ? | [162106](https://support.google.com/a/answer/162106?hl=en) |
| Uso compartido externo de Drive + allowlist | ✔ | no agrega | ✔ | ✔ | todas | [60781](https://support.google.com/a/answer/60781?hl=en) |
| Unidades compartidas y su configuración de acceso externo | ✔ | ✔ | ✔ | ✔ | Business Starter con salvedades; Standard, Plus y Enterprise | [7662202](https://support.google.com/a/answer/7662202?hl=en) |
| Trust rules de Drive | — | — | ✔ | ✔ | Frontline Plus, Enterprise Standard/Plus, Enterprise Essentials Plus | [10621317](https://support.google.com/a/answer/10621317?hl=en) |
| DLP de Drive y Gmail | ✔ | ✔ | ✔ | ✔ | ? | [TLA](https://knowledge.workspace.google.com/admin/getting-started/editions/teaching-and-learning-add-on) |
| Restrict delivery (Gmail) | ? (sin bloque de ediciones) | ? | ? | ? | ? | [2640542](https://support.google.com/a/answer/2640542?hl=en) |
| Context-Aware Access | — | — | ✔ | ✔ | Frontline Std/Plus, Enterprise Std/Plus, Ent. Essentials Plus, Cloud Identity Premium | [9275380](https://support.google.com/a/answer/9275380?hl=en) |
| Advanced Protection Program | ? (la página no muestra ediciones; "consumer as well as enterprise") | ? | ? | ? | ? | [9378686](https://support.google.com/a/answer/9378686?hl=en) |
| Multi-party approval para acciones sensibles | — | — | ✔ | ✔ | ? | — |
| Alert center | ✔ | — | ✔ | ✔ | ? | [9105393](https://support.google.com/a/answer/9105393?hl=en) |
| Audit & investigation tool (Admin, Drive, Gmail, OAuth, User log events) | ✔ | ✔ ("Advanced Drive logs") | ✔ | ✔ | ? | [4579696](https://support.google.com/a/answer/4579696?hl=en) |
| Eventos **API call** en OAuth log | — | — | ✔ | ✔ | Enterprise Standard/Plus, Cloud Identity Premium | [6124308](https://support.google.com/a/answer/6124308?hl=en) |
| Security investigation tool | — | — | ✔ | ✔ | Frontline Std/Plus, Enterprise Std/Plus, Ent. Essentials Plus, CI Premium | [4579579](https://support.google.com/a/answer/4579579?hl=en) |
| Activity rules: notificaciones | ✔ | — | ✔ | ✔ | todas salvo Essentials Starter | [11341109](https://support.google.com/a/answer/11341109?hl=en) |
| Activity rules: acciones y umbrales | — | — | — (según la tabla de 11341109) | ✔ | Enterprise Plus, Frontline Plus, Ent. Essentials Plus; Enterprise Standard solo para algunas fuentes | [11341109](https://support.google.com/a/answer/11341109?hl=en) |
| Reportes "OAuth grant activity" / "OAuth grants to new apps" | — | — | ✔ | ✔ | ? | — |
| Export de logs a BigQuery | — | — | ✔ | ✔ | Frontline Std/Plus, Enterprise Std/Plus, Ent. Essentials Plus | [9079365](https://support.google.com/a/answer/9079365?hl=en) |
| Compartir OAuth log con Cloud Logging | — (solo Admin y User) | — | ✔ | ✔ | Enterprise Std/Plus, Voice Premier, CI Premium | [9320190](https://support.google.com/a/answer/9320190) |
| Retención de logs (6 meses; email log search 30 días) | igual en todas | igual | igual | igual | igual | [7061566](https://support.google.com/a/answer/7061566?hl=en) |
| Org policies de claves de service account / WIF | No dependen de la edición de Workspace (son de Google Cloud) | | | | | [restricting-service-accounts](https://cloud.google.com/resource-manager/docs/organization-policy/restricting-service-accounts?hl=en) |

Nota: el **Teaching and Learning add-on** se suma a Fundamentals o Standard. Su tabla de beneficios solo marca, en lo que toca a este tema, "Advanced data exports" y "Additional pooled storage". "Advanced Drive logs and reports", "Shared drives" y "Drive DLP" figuran ✔ también en Fundamentals. [Teaching and Learning add-on](https://knowledge.workspace.google.com/admin/getting-started/editions/teaching-and-learning-add-on)

---

## No documentado / ambiguo

1. **Gmail con service account sin DWD.** No se encontró una página oficial que diga explícitamente si una service account sin DWD puede llamar a la Gmail API sobre un buzón. Las páginas consultadas solo describen el acceso a Gmail por service account a través de DWD ([delegate_settings](https://developers.google.com/workspace/gmail/api/guides/delegate_settings)).
2. **2SV o llave obligatoria en una cuenta sin uso interactivo.** Las páginas de 2SV no dicen si exigir 2SV o "Only security key" invalida o desafía un refresh token ya emitido, ni cómo afecta a una cuenta que solo usa APIs. Tampoco se encontró una política de "excepción" para cuentas técnicas.
3. **Refresh token de app Internal.** La regla de 7 días está escrita para "external user type" en estado "Testing". Ninguna página consultada afirma de forma positiva que un proyecto Internal no tenga vencimiento; solo se le aplican las causas generales de §3.
4. **Valor del tope global de refresh tokens por cuenta.** Google dice que existe ("a larger limit") pero no publica el número.
5. **API Controls y service accounts.** [production-readiness/google-workspace](https://developers.google.com/identity/protocols/oauth2/production-readiness/google-workspace?hl=en) dice que API Controls restringe "customer-owned and third-party applications and service accounts". En cambio, [service-account](https://developers.google.com/identity/protocols/oauth2/service-account?hl=en) dice que las service accounts "aren't subject to domain policies". No queda claro qué control de API aplica a una service account **sin** DWD.
6. **CAA y service accounts en Drive.** [9275380](https://support.google.com/a/answer/9275380?hl=en) dice que CAA "don't restrict access to Google APIs from service accounts". En el mismo artículo, sobre Drive, propone "exempt its service account" para herramientas automatizadas. Tampoco documenta si CAA evalúa las llamadas de API de un **usuario** hechas desde un servidor con refresh token.
7. **Agregar una service account a una unidad compartida con el uso compartido externo bloqueado.** Las trust rules la tratan como "Anyone with a Google Account" y el indicador la marca siempre como externa. Pero [60781](https://support.google.com/a/answer/60781?hl=en) y [7662202](https://support.google.com/a/answer/7662202?hl=en) no dicen si "Allow users outside your organization to access files in shared drives" impide agregar una service account de un proyecto de la propia organización.
8. **Scopes de Sheets y Docs en API Controls.** `documents` figura en la lista high-risk de **Drive**. `spreadsheets` no figura en ninguna lista high-risk, y no está documentado si restringir el servicio Drive alcanza a la Sheets API (solo se aclara que alcanza a la Forms API).
9. **Ediciones de Advanced Protection, Restrict delivery, DWD y API Controls.** Sus artículos no tienen bloque de "Supported editions" y la tabla comparativa de Education no tiene filas específicas para ellos. La matriz los marca como "sin bloque" en vez de suponer.
10. **Activity rules en Education Standard.** La tabla de [11341109](https://support.google.com/a/answer/11341109?hl=en) pone a Education Standard junto a Fundamentals (solo notificaciones), aunque Standard sí tiene el security investigation tool según [Compare Education editions](https://knowledge.workspace.google.com/admin/getting-started/editions/compare-education-editions), que lista "Automate security threat response with activity rules" dentro de esa herramienta. Las dos fuentes no son del todo consistentes.
11. **Drive log events por edición.** [4579696](https://support.google.com/a/answer/4579696?hl=en) dice que "Most Drive audit events are logged only for files owned by users with supported editions", pero no lista esas ediciones. La tabla comparativa marca Drive log events ✔ en Fundamentals.
12. **Revocación por el usuario.** El procedimiento está en `support.google.com/accounts`, fuera de la lista de dominios del ticket.
