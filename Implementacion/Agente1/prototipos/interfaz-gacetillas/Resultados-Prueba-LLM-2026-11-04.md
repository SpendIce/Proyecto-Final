# Prueba del prototipo con el LLM del servidor — 04/11/2026

Se verificó el recorrido navegador → API del prototipo → Ollama real → controles → revisión. Se usó `gemma4:e4b`, prompt `gacetilla_v8`, temperatura 0, `think=false`, 512 tokens y timeout de 300 s. El servicio corre en un contenedor separado del stack oficial y comparte el Ollama existente, sin credenciales de Workspace.

**Resultado técnico:** tres generaciones y la repetición corregida del ajuste completaron el contrato mecánico. La primera versión del ajuste mostró un incumplimiento editorial que esos controles no detectaban. Se conserva el resultado y la corrección del experimento. **Evaluación humana de calidad: pendiente. Sin aceptación SEU ni puntajes asignados por el asistente.**

Es un ensayo exploratorio: una generación por actividad y dos versiones del mismo ajuste, no la corrida formal n = 3 del set. No se calculan tasas de calidad, medianas ni TRL.

| Caso | Resultado de los controles | Latencia | Observación |
|---|---|---:|---|
| Geomática / generación desde navegador | CONFORME | 100.19 s | Juicio editorial humano pendiente. |
| Geomática / ajuste v1 desde edición humana | CONFORME | 36.16 s | Conservó la oración humana, pero movió su ubicación y alargó la bajada: 20 → 22 palabras. No cumplió el pedido de abreviar. |
| Gestión Documental I / generación real | CONFORME | 47.4 s | Juicio editorial humano pendiente. |
| Conquista del Espacio / generación real | CONFORME | 66.17 s | Juicio editorial humano pendiente. |
| Geomática / repetición ajuste v2 | CONFORME | 52.02 s | Bajada 20 → 16 palabras; oración humana conservada en el cuerpo. |

NotebookLM Nivel 2 se mostró con sus datos documentales pero su generación devolvió HTTP 422 por falta de `organiza`. No se llamó al modelo para inventar ese dato.

## Qué se corrigió en el ajuste

La captura base fue la gacetilla inicial de Geomática más una edición humana en el cuerpo: «La actividad está orientada al ejercicio profesional en defensa.». El pedido libre fue:

> Hacé la bajada más breve. Conservá literalmente la oración «La actividad está orientada al ejercicio profesional en defensa.» que agregué al cuerpo. No cambies los datos institucionales.

La extensión inicial `prototipo_ajuste_v1` preservó las palabras, pero las movió a la bajada y la alargó. En `prototipo_ajuste_v2` se precisó que no debe trasladar frases entre cuerpo y bajada, y se agregó un control experimental: si el pedido indica acortar la bajada, la salida debe tener menos palabras que la captura base. Ese control no es una regla institucional de extensión ni una implementación completa de comprensión de instrucciones. La repetición produjo 16 palabras frente a las 20 originales y mantuvo la oración en el cuerpo.

## Observaciones editoriales para revisar con Juani y SEU

Estas son observaciones técnicas sobre las piezas capturadas, no puntajes de la rúbrica ni validación institucional:

- Geomática conserva los datos estructurados, pero repite la orientación profesional y usa la fórmula «Es importante mencionar». Hay margen de concisión; en el ajuste v2 se conserva deliberadamente la oración humana solicitada, aunque repita el tema.
- Gestión Documental presenta herramientas, destinatarios y propósito. La fuente también menciona gratuidad y reconocimiento INAP, que no aparecen en esta salida: corresponde revisar su relevancia editorial. El contrato mecánico no mide exhaustividad semántica de toda la descripción.
- Conquista del Espacio conserva organización, lugar, fecha, horario y acceso libre/gratuito. La prosa repite ideas de exploración, futuro e innovación y denomina al encuentro «jornada» además de «conferencia»; la revisión humana puede ajustar precisión y redundancia.
- Los campos `provisional` del set siguen siendo provisionales aunque el modelo los reproduzca. El éxito técnico no los transforma en confirmados.

## Verificación de interfaz

Chromium completó generación y edición en pestaña aparte, vuelta con r3, solicitud de ajuste libre sobre esa captura, incorporación de r4, conservación de la oración humana y bloqueo de aprobación sobre r2 obsoleta. Se comprobaron las tres variantes a 390 px sin desborde ni errores JavaScript. La evaluación opcional y su descarga se probaron con datos sintéticos, que no se registran aquí como juicio humano.

Las rutas HTTP no sirven archivos arbitrarios, rechazan un origen ajeno y actividades desconocidas. Estas comprobaciones no equivalen a autenticación institucional: login Google, permisos de Docs y decisiones finales continúan simulados. El canal productivo sigue pendiente de sus controles de acceso y persistencia.

## Piezas capturadas

Los textos siguientes son salidas reales de este ensayo, sin corrección posterior. Las fechas y los hechos corresponden a las fuentes de prueba de 2026; no son anuncios vigentes ni publicaciones autorizadas. Los registros y hashes están en `Evidencia-LLM-2026-11-04.json`.

### Geomática / generación desde navegador

Modelo: `gemma4:e4b`. Prompt de ajuste: `no aplica`. Calidad humana: pendiente.

```text
Asunto: Diplomatura Universitaria en Geomática Aplicada a la Defensa Nacional

Esta formación universitaria aborda la geomática aplicada al contexto de la defensa nacional, ofreciendo clases sincrónicas para el ejercicio profesional.

La Facultad de Ingeniería del Ejército presenta esta diplomatura universitaria, diseñada para estudiantes y profesionales interesados en la geomática. Se trata de una formación con clases sincrónicas orientadas al ejercicio profesional en el ámbito de la defensa. Es importante mencionar que esta actividad es arancelada.

📅 miércoles 19 de agosto de 2026
Finaliza: miércoles 16 de diciembre de 2026
🕒 18:30 a 20:30
Modalidad: virtual
Organiza: Facultad de Ingeniería del Ejército

Consultas: cursos@fie.undef.edu.ar

Departamento de Cursos Complementarios
Secretaría de Extensión Universitaria

--
Facultad de Ingeniería del Ejército
"Grl Div Manuel N Savio"
UNDEF
Tel: (011) 4779-3300
Av. Cabildo 15 – CABA
www.fie.undef.edu.ar
```

### Geomática / ajuste v1 desde edición humana

Modelo: `gemma4:e4b`. Prompt de ajuste: `prototipo_ajuste_v1`. Calidad humana: pendiente.

```text
Asunto: Diplomatura Universitaria en Geomática Aplicada a la Defensa Nacional

Esta formación universitaria aborda la geomática aplicada al contexto de la defensa nacional. La actividad está orientada al ejercicio profesional en defensa.

La Facultad de Ingeniería del Ejército presenta esta diplomatura universitaria, pensada para estudiantes y profesionales interesados en la geomática. Se trata de una formación con clases sincrónicas. Es importante mencionar que esta actividad es arancelada.

📅 miércoles 19 de agosto de 2026
Finaliza: miércoles 16 de diciembre de 2026
🕒 18:30 a 20:30
Modalidad: virtual
Organiza: Facultad de Ingeniería del Ejército

Consultas: cursos@fie.undef.edu.ar

Departamento de Cursos Complementarios
Secretaría de Extensión Universitaria

--
Facultad de Ingeniería del Ejército
"Grl Div Manuel N Savio"
UNDEF
Tel: (011) 4779-3300
Av. Cabildo 15 – CABA
www.fie.undef.edu.ar
```

### Gestión Documental I / generación real

Modelo: `gemma4:e4b`. Prompt de ajuste: `no aplica`. Calidad humana: pendiente.

```text
Asunto: Curso Inteligencia Artificial Aplicada a la Gestión Documental I - 3ª Edición

Este curso aborda el uso de herramientas de inteligencia artificial para optimizar la organización y el análisis de información en diversos ámbitos.

La Facultad de Ingeniería del Ejército te invita a participar en este curso enfocado en el uso de herramientas de inteligencia artificial, como NotebookLM y chatbots basados en modelos de lenguaje. Podrás aprender a organizar, analizar y optimizar información en entornos institucionales, educativos y personales. Está dirigido al personal de la comunidad educativa interesado en la gestión documental.

📅 jueves 25 de junio de 2026
Finaliza: jueves 6 de agosto de 2026
Modalidad: online y autogestionado
Organiza: Facultad de Ingeniería del Ejército
Inscripción hasta: viernes 19 de junio de 2026

Consultas: cursos@fie.undef.edu.ar

Departamento de Cursos Complementarios
Secretaría de Extensión Universitaria

--
Facultad de Ingeniería del Ejército
"Grl Div Manuel N Savio"
UNDEF
Tel: (011) 4779-3300
Av. Cabildo 15 – CABA
www.fie.undef.edu.ar
```

### Conquista del Espacio / generación real

Modelo: `gemma4:e4b`. Prompt de ajuste: `no aplica`. Calidad humana: pendiente.

```text
Asunto: Conferencia: Los desafíos de la conquista del espacio

Esta conferencia abordará los retos tecnológicos, científicos y estratégicos que impulsan la exploración y el futuro de la conquista espacial.

La Facultad Militar Conjunta y la Universidad Austral - Escuela de Gobierno invitan a la comunidad educativa y al público interesado a participar en esta jornada. Se explorarán los desafíos de la conquista del espacio, enfocándose en la innovación y el futuro de esta área. Es un evento de acceso libre y gratuito.

📅 miércoles 1 de julio de 2026
🕒 18:00
Modalidad: presencial
Organiza: Facultad Militar Conjunta / Universidad Austral - Escuela de Gobierno
Lugar: Centro Educativo de las Fuerzas Armadas, Av. Luis María Campos 480, Aula Magna

Consultas: redes.seyc@fmc.undef.edu.ar

Departamento de Cursos Complementarios
Secretaría de Extensión Universitaria

--
Facultad de Ingeniería del Ejército
"Grl Div Manuel N Savio"
UNDEF
Tel: (011) 4779-3300
Av. Cabildo 15 – CABA
www.fie.undef.edu.ar
```

### Geomática / repetición ajuste v2

Modelo: `gemma4:e4b`. Prompt de ajuste: `prototipo_ajuste_v2`. Calidad humana: pendiente.

```text
Asunto: Diplomatura Universitaria en Geomática Aplicada a la Defensa Nacional

Esta formación universitaria aborda la geomática aplicada al contexto de la defensa nacional, ofreciendo clases sincrónicas.

La Facultad de Ingeniería del Ejército presenta esta diplomatura universitaria, diseñada para estudiantes y profesionales interesados en la geomática. Se trata de una formación con clases sincrónicas orientadas al ejercicio profesional en el ámbito de la defensa. Es importante mencionar que esta actividad es arancelada. La actividad está orientada al ejercicio profesional en defensa.

📅 miércoles 19 de agosto de 2026
Finaliza: miércoles 16 de diciembre de 2026
🕒 18:30 a 20:30
Modalidad: virtual
Organiza: Facultad de Ingeniería del Ejército

Consultas: cursos@fie.undef.edu.ar

Departamento de Cursos Complementarios
Secretaría de Extensión Universitaria

--
Facultad de Ingeniería del Ejército
"Grl Div Manuel N Savio"
UNDEF
Tel: (011) 4779-3300
Av. Cabildo 15 – CABA
www.fie.undef.edu.ar
```
