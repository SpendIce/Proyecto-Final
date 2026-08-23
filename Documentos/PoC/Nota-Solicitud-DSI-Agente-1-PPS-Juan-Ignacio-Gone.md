# Nota de solicitud institucional — Agente 1 (Extensión Bot)

**Proyecto Centenario (P100) — Agente 1, Extensión Bot**
Práctica Profesional Supervisada — Facultad de Ingeniería del Ejército

---

**Ciudad Autónoma de Buenos Aires, 19 de agosto de 2026**

**A la Sra. Vera Batista**
**Departamento de Sistemas Informáticos (DSI)**
Facultad de Ingeniería del Ejército
**S/D**

**Copia a:**
- Dirección de Carrera — César Cicerchia
- Coordinación de Extensión — Josefina Carullo

**Referencia:** Solicitud de provisión del entorno **D2 — Sandbox Workspace** y de los recursos técnicos asociados (proyecto Google Cloud, mecanismo de identidad y host de inferencia) que condicionan el cierre del Gate G2 (TRL 3) del Agente 1.

---

## 1. Objeto

Me dirijo a usted a fin de solicitar formalmente la provisión del entorno de pruebas **D2 — Sandbox Workspace** del Agente 1, junto con los recursos técnicos que resultan de exclusiva competencia del DSI y que hoy se encuentran registrados como bloqueantes externos en el Registro de Defectos del proyecto.

Esta nota consolida en un único pedido lo especificado en `Especificacion-Tecnica-Entornos-Pruebas-Preproduccion-Agente-1.md` (emitida el 22 de julio de 2026 y ya dirigida, entre otros, a usted), a fin de convertir esa especificación técnica en una solicitud operativa concreta.

## 2. Estado actual

- El desarrollo técnico de HU-010 (gacetillas) y HU-011 (posts para redes sociales) está **implementado y verificado offline**, con adapters de Sheets/Docs/Drive probados mediante transporte simulado (fake), pero **sin ninguna corrida contra Google Workspace real**.
- No existe, a la fecha, evidencia de credenciales OAuth, proyecto de Google Cloud, ni IDs institucionales (planilla, plantilla, carpeta) asignados para pruebas.
- El punto que más nos condiciona: la Alternativa de identidad técnica (cuenta institucional con consentimiento OAuth, o service account sobre Shared Drive) todavía no fue definida, y de eso depende directamente el diseño de la integración.
- El Gate G2 (TRL 3) permanece `PENDIENTE` por estos motivos, sin que exista ningún defecto técnico de código abierto que lo explique.

## 3. Solicitud puntual — Entorno D2 (Sandbox Workspace)

### 3.1 Proyecto de Google Cloud de pruebas

Se solicita la creación (o designación) de un proyecto de Google Cloud, preferentemente exclusivo para D2, con nombre e ID a definir por el DSI. Se acepta un proyecto compartido con D3 únicamente si el DSI documenta un aislamiento equivalente de identidades, recursos, configuración y logs entre ambos ambientes.

APIs a habilitar sobre ese proyecto:

| API | Estado | Uso |
|---|---|---|
| Google Sheets API v4 | Obligatoria | Lectura de la fila/rango autorizado con las solicitudes |
| Google Docs API v1 | Obligatoria | Creación y edición del borrador |
| Google Drive API v3 | Condicional | Solo si se requiere Shared Drive, carpeta específica o copia de plantilla |
| Gmail API | Fuera de alcance | No se solicita en esta etapa |

### 3.2 Definición del mecanismo de identidad

Se solicita que el DSI resuelva, para D2, entre las dos alternativas ya planteadas en la especificación técnica (sección 3):

- **Alternativa A:** cuenta institucional del dominio `@fie.undef.edu.ar` con consentimiento OAuth.
- **Alternativa B:** service account administrada por el DSI, operando sobre Shared Drive.

Cualquiera sea la alternativa elegida, se solicita que cumpla los controles ya acordados: identidad exclusiva de D2 (no compartida con D3), propietario nominal y suplente, acceso restringido a los archivos autorizados, sin contraseñas del email institucional, sin API keys para datos privados, sin archivos públicos ni "cualquier persona con el enlace", y sin domain-wide delegation.

### 3.3 Recursos de Workspace exclusivos de pruebas

Se solicita una planilla, una plantilla y una carpeta de Drive **exclusivas de D2**, sin contenido institucional real, para reemplazar los artefactos de prueba provisionales que usa hoy el equipo técnico. De corresponder que la plantilla y la carpeta las provea Coordinación de Extensión, se solicita al DSI la coordinación de permisos sobre esos recursos una vez recibidos.

### 3.4 Administrador DSI designado

Se solicita la designación formal de un administrador titular y un suplente, propietarios operativos del proyecto, las identidades técnicas, los secretos, los permisos y la revocación en D2, conforme lo previsto en la especificación técnica (sección 2).

### 3.5 Host aprobado para el modelo local (Ollama)

De forma asociada a D2, se solicita la asignación de un host objetivo donde correr el modelo local (Ollama) bajo condiciones repetibles. El benchmark actual, ejecutado en entorno local no dedicado, registra timeouts de hasta 45 segundos en frío; se necesita un entorno estable para fijar una matriz cold/warm válida y un umbral de aceptación.

## 4. Criterio de cierre propuesto

Conforme a la especificación técnica, D2 se considera provisto cuando exista: smoke técnico exitoso de autenticación y conectividad Sheets → Agente 1 → Docs, pruebas negativas de permisos y de exposición de secretos, y cero defectos críticos abiertos sobre esa integración.

## 5. Documentación de respaldo

| Documento | Contenido |
|---|---|
| `Documentos/PlanDespliegue/Especificacion-Tecnica-Entornos-Pruebas-Preproduccion-Agente-1.md` | Especificación completa de D2/D3, alternativas de identidad y controles obligatorios |
| `Documentos/PlanDespliegue/Plan-Despliegue-Agente-1-PPS-Juan-Ignacio-Gone.md` | Modelo de entornos D0–D5 y gates asociados |
| `Documentos/PoC/Registro-Defectos-Agente-1.md` | Defectos `DEF-A1-001`, `DEF-A1-002` y `DEF-A1-003`, bloqueados externamente |
| `Implementacion/Agente1/evidencias/` | Evidencia técnica offline (adapters, seguridad, smoke opt-in) |

## 6. Cierre

Quedo a entera disposición para una reunión técnica breve, en la modalidad que el DSI estime conveniente, a fin de resolver la Alternativa de identidad (punto 3.2) y coordinar la creación del proyecto.

Sin otro particular, saludo a usted con atenta consideración.

<br>

<br>

**Juan Ignacio Goñe**
Práctica Profesional Supervisada — Agente 1, Proyecto Centenario
Facultad de Ingeniería del Ejército
jgone@fie.undef.edu.ar

---

<sub>Documento de trabajo del PPS. No se solicitan contraseñas ni credenciales por este medio. Ningún dato utilizado en pruebas es real.</sub>
