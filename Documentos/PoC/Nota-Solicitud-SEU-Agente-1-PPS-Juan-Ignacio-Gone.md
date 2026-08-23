# Nota de solicitud institucional — Agente 1 (Extensión Bot)

**Proyecto Centenario (P100) — Agente 1, Extensión Bot**
Práctica Profesional Supervisada — Facultad de Ingeniería del Ejército

---

**Ciudad Autónoma de Buenos Aires, 18 de agosto de 2026**

**Al Señor Secretario de Extensión Universitaria**
Facultad de Ingeniería del Ejército
**S/D**

**Copia a:**
- Coordinación de Extensión — Josefina Carullo
- Dirección de Carrera — César Cicerchia
- Dirección de Sistemas e Informática — Vera Batista

**Referencia:** Solicitud de designación de validadores, criterios de comunicación institucional y recursos para el cierre del Gate G2 (TRL 3) del Agente 1.

---

## 1. Objeto

Me dirijo a usted a fin de solicitar formalmente la designación de personal
validador, la definición de criterios de comunicación institucional y la
provisión de recursos que actualmente condicionan el avance del **Agente 1 —
Extensión Bot**, componente de comunicación institucional del Proyecto
Centenario.

La presente nota consolida en un único pedido los requerimientos que hasta hoy
se encuentran registrados como bloqueantes externos en el Registro de Defectos
del proyecto, a fin de evitar consultas fragmentadas a las distintas áreas.

## 2. Estado actual

Corresponde informar, con carácter de estado y no de reclamo, que:

- El desarrollo de las historias de usuario **HU-010 (gacetillas)**,
  **HU-011 (posts para redes sociales)** y **HU-012 (confirmaciones)** se
  encuentra **implementado y verificado técnicamente**, con una suite de 451
  pruebas automatizadas en su totalidad en verde.
- El paquete de validación humana se encuentra **preparado y a disposición**:
  nueve borradores, diecisiete referencias documentales, protocolo de sesión,
  instrumento de evaluación y acta de decisión.
- El hito **m2 — MVP con evidencia / Gate TRL 3**, previsto para el
  **17 de agosto de 2026**, permanece **PENDIENTE**.

**El hito no se encuentra demorado por causas técnicas.** Los cuatro defectos
que lo condicionan están clasificados como bloqueantes externos y requieren
decisiones institucionales que exceden el alcance del desarrollo.

Asimismo se deja constancia de que **no se ha publicado ni enviado contenido
alguno**. Todos los borradores conservan la marca `BORRADOR — NO PUBLICAR` y el
estado `PENDIENTE_VALIDACION`, y el sistema carece deliberadamente de mecanismos
de publicación automática.

---

## 3. Solicitudes que corresponden a la Secretaría de Extensión

### 3.1 Designación de personal validador

Se solicita la designación formal de:

| Rol | Alcance |
|---|---|
| Persona validadora **titular** | Evaluación de los nueve borradores |
| Persona validadora **suplente** | Cobertura ante ausencia |
| Responsable de Gestión del Conocimiento | Criterios de contenido institucional |
| Responsable de Redes Sociales | Criterios por canal (punto 4.1) |

Para cada designación se requiere **nombre, rol institucional y área**, dado que
el acta de validación exige identidad verificable y no admite cierre mediante
conformidad informal.

### 3.2 Agenda de la sesión de validación

Se solicita la fijación de fecha y horario para una sesión de revisión.
Características de la sesión:

- **Material:** nueve borradores derivados de tres actividades **sintéticas**
  (`SYN-001`, `SYN-003`, `SYN-005`), cada una con una gacetilla, un post para
  Instagram y un post para LinkedIn.
- **Datos:** íntegramente simulados. **No se utilizan datos personales reales,
  actividades reales ni identidades institucionales.**
- **Duración estimada:** aproximadamente 90 minutos, sujeta a confirmación.
- **Modalidad:** presencial o remota, indistinta.

### 3.3 Alcance explícito de la decisión solicitada

Se deja constancia, para evitar toda ambigüedad sobre lo que se pide aprobar,
que la decisión solicitada se limita a determinar si los borradores
**constituyen una base de trabajo utilizable**. La decisión:

- **no** autoriza publicación ni envío;
- **no** aprueba un flujo operativo;
- **no** compromete a la Secretaría respecto de contenido institucional real.

Cada muestra admite una de tres decisiones: `APROBADO_COMO_BORRADOR`,
`REQUIERE_AJUSTES` o `RECHAZADO`.

---

## 4. Solicitudes que corresponden a Coordinación de Extensión

Se detallan a continuación por integrar el mismo pedido consolidado, sin
perjuicio de que su resolución corresponde a Coordinación.

### 4.1 Criterios de comunicación por canal

El sistema opera actualmente con parámetros **provisionales definidos por el
equipo técnico**, sin respaldo institucional. Los valores vigentes son
idénticos para Instagram y LinkedIn, lo que evidencia su carácter de marcador de
posición y no de criterio editorial.

Se solicita definición sobre:

| # | Punto | Situación actual |
|---|---|---|
| 4.1.1 | Extensión máxima del texto por canal | 1.000 caracteres en ambos canales, valor arbitrario |
| 4.1.2 | Cantidad mínima y máxima de etiquetas por canal | 1 a 10 en ambos canales |
| 4.1.3 | **Listado de etiquetas institucionales autorizadas** | Cuatro etiquetas genéricas propuestas por el equipo técnico, ninguna institucional |
| 4.1.4 | **Registro lingüístico: voseo rioplatense o tuteo neutro** | Sin definición; el sistema produce tuteo neutro |
| 4.1.5 | Tono editorial por canal | Sin definición institucional |
| 4.1.6 | Uso de emoticones | Sin regla |
| 4.1.7 | Admisibilidad de llamados a la acción de inscripción | Sin definición (ver punto 5.1) |

Se destaca especialmente el punto **4.1.4**. En las pruebas realizadas, el
sistema genera expresiones como «Inscríbete» y «Únete», propias del español
neutro. Corresponde a la Secretaría determinar si ese registro resulta adecuado
para la comunicación institucional de la Facultad.

### 4.2 Plantilla institucional de gacetilla

Se solicita la plantilla oficial de gacetilla en formato documento, con
indicación de secciones, encabezado, pie y orden de campos, así como si existe
más de una plantilla según el tipo de actividad.

### 4.3 Flujo de corrección y aprobación

Se solicita definición del circuito por el cual un borrador observado se
corrige, se vuelve a presentar y se aprueba, con indicación de los roles
intervinientes.

---

## 5. Consultas de alcance

Las siguientes consultas no constituyen pedidos de recursos, pero sus
respuestas determinan el diseño del sistema. Se solicita respuesta aun cuando
sea negativa.

### 5.1 Circuito de inscripción

**¿Existe actualmente un circuito de inscripción a actividades de extensión?**

La HU-012 (confirmaciones de inscripción) se diseñó suponiendo su existencia. De
no existir, corresponde reformular su alcance antes del Sprint 4, previsto para
el 31 de agosto. En caso afirmativo, se requiere: casilla remitente
institucional, asunto del correo, firma y pie, y tratamiento del caso en que el
lugar de la actividad aún no esté definido.

### 5.2 Origen real de la información

**¿Dónde se registra actualmente la información de las actividades de
extensión?** (planilla, formulario, correo, sistema)

La totalidad de las pruebas se realizó con datos sintéticos. La respuesta a esta
consulta determina el mecanismo de ingreso de información al sistema y
constituye un requisito para cualquier operación institucional real.

### 5.3 Volumen y periodicidad

**¿Cuántas gacetillas y publicaciones se producen mensualmente?**

Esta información permite determinar si los tiempos de procesamiento actuales
—entre 15 y 45 segundos por pieza— resultan adecuados o requieren una
modificación de la arquitectura. Actualmente el punto se encuentra registrado
como defecto abierto por ausencia de criterio de aceptación.

---

## 6. Impacto sobre el cronograma

| Hito | Fecha prevista | Estado |
|---|---|---|
| m2 — MVP con evidencia / Gate TRL 3 | 17/08/2026 | **PENDIENTE** |
| m3 — Base robustecida | 28/08/2026 | En ejecución |
| m4 — HU-012 operativa | 14/09/2026 | Condicionado por consulta 5.1 |

Se solicita, de resultar posible, contar con respuesta a los puntos **3.1**,
**3.2**, **4.1.3**, **4.1.4** y **5.1** antes del **29 de agosto de 2026**, a fin
de no comprometer el hito m4. Los restantes puntos admiten un plazo mayor.

Se deja constancia de que la fecha propuesta constituye una solicitud y no una
fecha acordada.

---

## 7. Documentación de respaldo

La documentación técnica que fundamenta cada punto se encuentra disponible y a
disposición de la Secretaría:

| Documento | Contenido |
|---|---|
| `Documentos/PoC/Validacion-SEU/` | Paquete completo de validación: protocolo, instrumento, acta y referencias |
| `Documentos/PoC/Registro-Defectos-Agente-1.md` | Registro de defectos con clasificación y responsables |
| `Documentos/PoC/Matriz-HU-DoD-Evidencia-Responsable-Agente-1.md` | Matriz de trazabilidad por historia de usuario |
| `Implementacion/Agente1/evidencias/` | Evidencia técnica de las pruebas realizadas |

---

## 8. Cierre

Quedo a entera disposición para ampliar cualquiera de los puntos expuestos,
presentar el sistema en funcionamiento o participar de la sesión de validación
en la modalidad que la Secretaría estime conveniente.

Sin otro particular, saludo a usted con atenta consideración.

<br>

<br>

**Juan Ignacio Goñe**
Práctica Profesional Supervisada — Agente 1, Proyecto Centenario
Facultad de Ingeniería del Ejército
jgone@fie.undef.edu.ar

---

<sub>Documento de trabajo del PPS. Los datos utilizados en las pruebas
referidas son sintéticos. No se ha publicado ni enviado contenido institucional
alguno.</sub>
