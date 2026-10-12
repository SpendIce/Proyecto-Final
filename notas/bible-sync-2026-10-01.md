# Bible sync 2026-10-01

Fuente: export doc-id 1zI3wDVRO6jSZLan-KqqPbx0nNWhX-PiNEJXFi5A5pAo

Hunks totales: 41 | Relevantes a Agente 1: 7

```diff
@@ -1,7 +1,5 @@
 # **LÉAME**
 
-# **LÉAME**
-
 Se han agregado varias pestañas entre los documentos de DISEÑO: Supervisión humana, Verificación del Mapa de Procesos SEU y otras correspondientes con notas para cada Agente.
 
 Los documentos de DISEÑO se completan con los documentos del PROYECTO.
```

```diff
@@ -11,10 +9,6 @@
 Otro aspecto fundamental es la ciberseguridad del proyecto, que se define en la pestaña PROYECTO: **Ciberseguridad desde el Principio**.
 
 Este documento está en constante revisión ("vivo"). Las modificaciones se señalan con resaltado amarillo y, de ser necesario, se complementan con un comentario.
-
-# **DISEÑO**
-
-# **Modelo de Procesos SEU – FIE**
 
 # **1\. Enfoque metodológico adoptado**
 
```

```diff
@@ -373,8 +367,6 @@
 * Permite **escalabilidad hacia el Centenario**  
 * Está preparado para **automatización progresiva con IA**  
 * Reduce riesgos organizacionales y mejora la eficiencia operativa
-
-# **Integración Agentes \+ Procesos**
 
 A continuación se presenta el **mapeo integral Proceso → Software (open source \+ Google Workspace) → Agentes IA del Proyecto Centenario**, con criterio:
 
```

```diff
@@ -671,8 +663,6 @@
 * Permite implementar IA de forma **realista, incremental y sostenible**  
 * Responde directamente a criterios de calidad exigidos en evaluaciones universitarias
 
-# **Supervisión humana**
-
 En el marco del Proyecto Centenario, el principio de **supervisión humana ("human-in-the-loop")** es fundamental para garantizar la calidad institucional y mitigar riesgos reputacionales. Los procesos específicos que requieren validación humana obligatoria son:
 
 * **Gestión de Contenidos Críticos:** La arquitectura del sistema excluye explícitamente la automatización sin supervisión de cualquier **contenido definido como crítico** para la institución. Caso 1: Datos Personales, protegidos por la Ley DP.  
```

```diff
@@ -698,8 +688,6 @@
 
 **La comunicación de validación será la misma que en toda interacción entre un humano y el agente. Deberá ser mediante un email**, **que dispara el agente al humano quien recibe una invitación a chatear con el agente para validar / modificar / crear / etc.**
 
-# **Alcance y orquestación de Agentes**
-
 # **1\. Alcance del Sistema**
 
 ## **1.1 Propósito del sistema**
```

```diff
@@ -852,7 +840,7 @@
 
 ## ---
 
-### **Seguridad (se amplía en** [https://docs.google.com/document/d/1zI3wDVRO6jSZLan-KqqPbx0nNWhX-PiNEJXFi5A5pAo/edit?tab=t.rg4l86s64vzl](https://docs.google.com/document/d/1zI3wDVRO6jSZLan-KqqPbx0nNWhX-PiNEJXFi5A5pAo/edit?tab=t.rg4l86s64vzl) **)**
+### **Seguridad (se amplía en** [https\://docs.google.com/document/d/1zI3wDVRO6jSZLan-KqqPbx0nNWhX-PiNEJXFi5A5pAo/edit?tab=t.rg4l86s64vzl](https://docs.google.com/document/d/1zI3wDVRO6jSZLan-KqqPbx0nNWhX-PiNEJXFi5A5pAo/edit?tab=t.rg4l86s64vzl) **)**
 
 * ## Uso de APIs oficiales con control de integridad (Hashes)
 
```

```diff
@@ -1542,8 +1530,6 @@
 | Token expirado | refresh automático |
 | Datos incompletos | validación |
 
-# **Gestión de Identidades y Accesos**
-
 ### **Notas técnicas sobre Gestión de Identidades y Accesos (Identity and Access Management)**
 
 1. Para todos los Agentes se debe distinguir **entre identidad (quién es el agente) y el mecanismo de autenticación/autorización técnico (cómo demuestra su identidad ante la API)** para operar dentro de Google Workspace.
```

```diff
@@ -1565,11 +1551,11 @@
 
       4. Un **Usuario OAuth** requiere un *Client ID* y un *Client Secret* para redirigir a una pantalla de logueo de Google. \[1, 2, 3\]
 
-         \[1\] [https://developers.google.com](https://developers.google.com/identity/protocols/oauth2/service-account?hl=es-419)
-
-         \[2\] [https://docs.cloud.google.com](https://docs.cloud.google.com/iam/docs/service-account-creds?hl=es-419)
-
-         \[3\] [https://soporte.alumn-e.com](https://soporte.alumn-e.com/knowledge-base/configurar-cuenta-de-correo-google-por-oauth/)
+         \[1\] [https\://developers.google.com](https://developers.google.com/identity/protocols/oauth2/service-account?hl=es-419)
+
+         \[2\] [https\://docs.cloud.google.com](https://docs.cloud.google.com/iam/docs/service-account-creds?hl=es-419)
+
+         \[3\] [https\://soporte.alumn-e.com](https://soporte.alumn-e.com/knowledge-base/configurar-cuenta-de-correo-google-por-oauth/)
 
    3. **Segmentación de Capas (Canal de Interacción vs. Backend)**: No se deben solapar las capas intervinientes (Canal de Interacción vs. Backend): Si el Agente 1 recibe instrucciones porque alguien le escribe un correo a `agente1@empresa.com` (Canal), no se debe asumir *erróneamente* que ese mismo buzón es el que mágicamente tiene acceso a la base de datos de Google Workspace mediante código.
 
```

```diff
@@ -1578,8 +1564,6 @@
       1. **Si** usa *Cuenta de Servicio*, en los registros de auditoría de Google aparecerá que la aplicación modificó los archivos. Se utilizará cuando el agente realice acciones en segundo plano **24/7 sin que el usuario esté conectado.**
 
       2. **Si** usa *OAuth de Usuario*, las acciones aparecerán firmadas por el supervisor o el usuario final. Se debe adoptar este mecanismo cuando las consultas a la base de datos de Workspace están limitadas **estrictamente a la información que el supervisor humano tiene permitido ver**? (Apunta a *OAuth de Usuario* o *Delegación de Dominio restringida*).
-
-# **Verificación del Mapa de Procesos SEU**
 
 Como Analista Funcional y Arquitecto de Sistemas, he estructurado la verificación técnica del **Mapa de Procesos de la SEU** basándome en los lineamientos de calidad universitaria (CONEAU) y la arquitectura de agentes inteligentes definida en las fuentes.
 
```

```diff
@@ -1697,8 +1681,6 @@
 
 **Conclusión:** El análisis es exhaustivo y está técnicamente verificado. Cubre las dependencias críticas (como la HU-001 y HU-002 de la base de datos y scripts base) y define criterios de aceptación específicos para cada interacción, cumpliendo con los estándares de trazabilidad exigidos por CONEAU.
 
-# **Agente 1 \- Notas**
-
 Como Diseñador del Sistema de Agentes Inteligentes, tras revisar las notas y especificaciones técnicas de los agentes del Proyecto Centenario, he identificado los siguientes aspectos clave que deben incorporarse para clarificar alcances, interacciones y datos de procesos en sus respectivos documentos:
 
 ### **Agente 1: Extensión Bot (Comunicación Institucional)**
```

```diff
@@ -1811,8 +1793,6 @@
 
 De acuerdo con el **"Flujo 1 — Actividad → Comunicación"**, el sistema está configurado para que, tras la generación de contenido por parte del Agente 1, exista un paso obligatorio de **validación humana** antes de proceder a la publicación oficial. Este control es esencial para evitar riesgos reputacionales, como la publicación de errores o información inventada por la IA.
 
-# **Notas Diseño \- AI 1**
-
 # ![][image3]
 
 # Diseño de Sistemas Informáticos 2
```

```diff
@@ -1831,67 +1811,67 @@
 
 **[Índice	2](#índice)**
 
-[**Proyecto	5**](#proyecto)
-
-[**Problema	5**](#problema)
-
-[**Descripción de los Usuarios	5**](#descripción-de-los-usuarios)
-
-[**Modelo de Negocio	6**](#modelo-de-negocio)
-
-[**Requisitos del sistema	7**](#requisitos-del-sistema)
-
-[**● Funcionales	7**](#funcionales)
-
-[**● No Funcionales	7**](#no-funcionales)
-
-[**Interacción con Demás Agentes	8**](#interacción-con-demás-agentes)
-
-[**Metodología de desarrollo de software	8**](#metodología-de-desarrollo-de-software)
-
-[**Cronograma	9**](#cronograma)
-
-[**Diagrama de Gantt	10**](#diagrama-de-gantt)
+[**Proyecto	4**](#proyecto)
+
+[**Problema	4**](#problema)
+
+[**Descripción de los Usuarios	4**](#descripción-de-los-usuarios)
+
+[**Modelo de Negocio	5**](#modelo-de-negocio)
+
+[**Requisitos del sistema	6**](#requisitos-del-sistema)
+
+[**● Funcionales	6**](#funcionales)
+
+[**● No Funcionales	6**](#no-funcionales)
+
+[**Interacción con Demás Agentes	7**](#interacción-con-demás-agentes)
+
+[**Metodología de desarrollo de software	7**](#metodología-de-desarrollo-de-software)
+
+[**Cronograma	8**](#cronograma)
+
+[**Diagrama de Gantt	9**](#diagrama-de-gantt)
 
 [**Diagrama de Clases	10**](#diagrama-de-clases)
 
-[**Diagrama de Casos de Uso	11**](#heading=h.q3y7jqdy7piv)
+[**Diagrama de Casos de Uso	10**](#diagrama-de-casos-de-uso)
 
 [**Bloque 1: Generación de Contenido	11**](#bloque-1:-generación-de-contenido)
 
-[**CU01: Recibir Entradas	11**](#cu01:-recibir-entradas-\(actor:-apps-script\))
-
-[**CU02: Notificar Error	11**](#cu02:-notificar-error-\(actor:-apps-script\))
+[**CU01: Recibir Entradas (Actor: Apps Script)	11**](#cu01:-recibir-entradas-\(actor:-apps-script\))
+
+[**CU02: Notificar Error (Actor: Apps Script)	11**](#cu02:-notificar-error-\(actor:-apps-script\))
 
 [**CU03: Generar Contenido	12**](#cu03:-generar-contenido)
 
-[**CU04: Consultar repositorio	12**](#cu04:-consultar-repositorio-\(actor:-repositorio-institucional\))
-
-[**CU05: Persistir Borrador	12**](#cu05:-persistir-borrador-\(actor:-google-workspace\))
-
-[**CU06: Registrar Log de Auditoría	12**](#cu06:-registrar-log-de-auditoría-\(actor:-base-de-datos\))
+[**CU04: Consultar repositorio (Actor: Repositorio Institucional)	12**](#cu04:-consultar-repositorio-\(actor:-repositorio-institucional\))
+
+[**CU05: Persistir Borrador (Actor: Google Workspace)	12**](#cu05:-persistir-borrador-\(actor:-google-workspace\))
+
+[**CU06: Registrar Log de Auditoría (Actor: Base de Datos)	12**](#cu06:-registrar-log-de-auditoría-\(actor:-base-de-datos\))
 
 [**Bloque 2: Human in the Loop	12**](#bloque-2:-human-in-the-loop)
 
-[**CU07: Iniciar sesión	12**](#cu07:-iniciar-sesión-\(actores:-responsable-de-gestión-del-conocimiento,-coordinador-de-extensión\))
-
-[**CU08: Consultar borradores	13**](#cu08:-consultar-borradores-\(actores:-responsable-de-gestión-del-contenido,-coordinador-de-extensión\))
-
-[**CU09: Corregir Borrador	13**](#cu09:-corregir-borrador-\(actores:-responsable-de-gestión-del-contenido,-coordinador-de-extensión\))
-
-[**CU10: Aprobar Borrador	13**](#cu10:-aprobar-borrador-\(actores:-responsable-de-gestión-del-contenido,-coordinador-de-extensión\))
-
-[**CU11: Cerrar sesión	13**](#cu11:-cerrar-sesión-\(actores:-responsable-de-gestión-del-conocimiento,-coordinador-de-extensión\))
+[**CU07: Iniciar sesión (Actores: Responsable de Gestión del Conocimiento, Coordinador de Extensión)	12**](#cu07:-iniciar-sesión-\(actores:-responsable-de-gestión-del-conocimiento,-coordinador-de-extensión\))
+
+[**CU08: Consultar borradores (Actores: Responsable de Gestión del Contenido, Coordinador de Extensión)	13**](#cu08:-consultar-borradores-\(actores:-responsable-de-gestión-del-contenido,-coordinador-de-extensión\))
+
+[**CU09: Corregir Borrador (Actores: Responsable de Gestión del Contenido, Coordinador de Extensión)	13**](#cu09:-corregir-borrador-\(actores:-responsable-de-gestión-del-contenido,-coordinador-de-extensión\))
+
+[**CU10: Aprobar Borrador (Actores: Responsable de Gestión del Contenido, Coordinador de Extensión)	13**](#cu10:-aprobar-borrador-\(actores:-responsable-de-gestión-del-contenido,-coordinador-de-extensión\))
+
+[**CU11: Cerrar sesión (Actores: Responsable de Gestión del Conocimiento, Coordinador de Extensión)	13**](#cu11:-cerrar-sesión-\(actores:-responsable-de-gestión-del-conocimiento,-coordinador-de-extensión\))
 
 [**Bloque 3: Difusión de Contenido	13**](#bloque-3:-difusión-de-contenido)
 
-[**CU12: Planificar Fecha de Publicación	13**](#cu12:-planificar-fecha-de-publicación-\(actor:-coordinador-de-extensión\))
-
-[**CU13: Publicar Contenido Programado	13**](#cu13:-publicar-contenido-programado-\(actores:-canales-de-publicación,-scheduler\))
+[**CU12: Planificar Fecha de Publicación (Actor: Coordinador de Extensión)	13**](#cu12:-planificar-fecha-de-publicación-\(actor:-coordinador-de-extensión\))
+
+[**CU13: Publicar Contenido Programado (Actores: Canales de Publicación, Scheduler)	13**](#cu13:-publicar-contenido-programado-\(actores:-canales-de-publicación,-scheduler\))
 
 [**Bloque 4: Soporte	14**](#bloque-4:-soporte)
 
-[**CU14: Mantener el sistema	14**](#cu14:-mantener-el-sistema-\(actor:-responsable-técnico\))
+[**CU14: Mantener el sistema (Actor: Responsable Técnico)	14**](#cu14:-mantener-el-sistema-\(actor:-responsable-técnico\))
 
 [**Lista de Actores para los Casos de Uso:	14**](#lista-de-actores-para-los-casos-de-uso:)
 
```

```diff
@@ -1899,9 +1879,9 @@
 
 [**Diagrama de Despliegue	15**](#diagrama-de-despliegue)
 
-[**Diagrama de Estados	15**](#diagrama-de-estados)
-
-[**Diagrama de Actividades	16**](#diagrama-de-actividades)
+[**Diagrama de Estados	16**](#diagrama-de-estados)
+
+[**Diagrama de Actividades	17**](#diagrama-de-actividades)
 
 [**Diagrama de Secuencia	18**](#diagrama-de-secuencia)
 
```

```diff
@@ -1965,23 +1945,105 @@
 
 [**Resultados esperados:	25**](#resultados-esperados:)
 
-[**EP02: Flujo de Aprobación y Publicación del Contenido Generado	25**](#ep02:-flujo-de-aprobación-y-publicación-del-contenido-generado)
+[**EP02: Flujo de Aprobación y Publicación del Contenido Generado	26**](#ep02:-flujo-de-aprobación-y-publicación-del-contenido-generado)
 
 [**Flujo:	26**](#flujo:-1)
 
-[**Resultados esperados:	26**](#resultados-esperados:-1)
-
-[**EP03: Flujo de Rechazo, Corrección y Ajuste por IA	27**](#ep03:-flujo-de-rechazo,-corrección-y-ajuste-por-ia)
+[**Resultados esperados:	27**](#resultados-esperados:-1)
+
+[**EP03: Flujo de Rechazo, Corrección y Ajuste por IA	28**](#ep03:-flujo-de-rechazo,-corrección-y-ajuste-por-ia)
 
 [**Resultados esperados:	28**](#resultados-esperados:-2)
 
-[**EP04: Estrés por Concurrencia en el Modelo Local de IA	28**](#ep04:-estrés-por-concurrencia-en-el-modelo-local-de-ia)
-
-[**Flujo:	29**](#flujo:-2)
-
-[**Resultados esperados:	29**](#resultados-esperados:-3)
-
-[**Interfaz de Usuario	29**](#interfaz-de-usuario)
+[**EP04: Estrés por Concurrencia en el Modelo Local de IA	30**](#ep04:-estrés-por-concurrencia-en-el-modelo-local-de-ia)
+
+[**Flujo:	30**](#flujo:-2)
+
+[**Resultados esperados:	30**](#resultados-esperados:-3)
+
+[**Interfaz de Usuario	30**](#interfaz-de-usuario)
+
+[**Hitos y Tareas	32**](#hitos-y-tareas)
+
+[**Resumen de Hitos del Proyecto:	39**](#resumen-de-hitos-del-proyecto:)
+
+[**Estimación de Costos	39**](#estimación-de-costos)
+
+[**Mano de obra	39**](#mano-de-obra)
+
+[**Costos de hardware	40**](#costos-de-hardware)
+
+[**Gastos de oficina	40**](#gastos-de-oficina)
+
+[**Presupuesto total	40**](#presupuesto-total)
+
+[**Administración de Riesgos	40**](#administración-de-riesgos)
+
+[**Modelos Adoptados	41**](#modelos-adoptados)
+
+[**Matriz de Riesgos	41**](#matriz-de-riesgos)
+
+[**R-01: Incompatibilidad de contratos de interfaz entre ExtensiónBot y los Agentes 2 a 5 durante la integración (Integration Failure)	43**](#heading=h.qt404ut5wkyy)
+
+[**R-02: Desviación del alcance por incorporación no controlada de nuevas funcionalidades solicitadas por otras áreas (Scope Creep)	45**](#heading=h.vuir5y44yyta)
+
+[**R-03: Retraso en cronograma por dependencia entre fases (ej. Motor de IA bloqueando UI)	46**](#heading=h.ydlwxenfm4ta)
+
+[**R-04: Sobrecosto por subestimación de tareas de integración con Agentes 2–5	47**](#heading=h.f6f0v659o2a3)
+
+[**R-05: Incremento del costo del hardware especializado (GPU/microprocesador IA) por variaciones del mercado o del tipo de cambio	48**](#heading=h.3unoda27zu7o)
+
+[**R-06: Identificación incompleta de riesgos emergentes durante las nuevas fases del proyecto	49**](#heading=h.d7ddh5cc5516)
+
+[**R-07: Contenido generado que no cumple con la Definición de Terminado (DoD) llega a instancias de validación por falencias en el plan de pruebas	50**](#heading=h.le1qs9eoquqn)
+
+[**R-08: Falta de alineación entre los equipos de desarrollo de los distintos agentes por deficiencias en el plan de comunicaciones	51**](#heading=h.pg6hm4dnbixe)
+
+[**R-09: Baja adopción por parte del personal de Extensión (resistencia al cambio, uso ocasional de IA)	52**](#heading=h.orawkrqiq0fe)
+
+[**R-10: Dependencia de licencias/servicios cloud de terceros (Google Workspace, APIs de redes)	53**](#heading=h.6tfi4qo225ny)
+
+[**R-11: Demora en la adquisición de infraestructura cloud, servidores o licencias necesarias para el desarrollo (Procurement Delay)	54**](#heading=h.lxllr4mquzym)
+
+[**R-12: Rotación o indisponibilidad de estudiantes de 4° y 5° año que integran el equipo de desarrollo	55**](#heading=h.f1n3fkpysvb9)
+
+[**R-13: Personal inadecuado o con perfil insuficiente para las tecnologías críticas del proyecto (LLMs locales, seguridad de agentes, arquitectura multiagente)	56**](#heading=h.voz7aw4x736c)
+
+[**R-14: Elaboración excesiva de requisitos y documentación de diseño más allá de lo necesario para el MVP (gold plating)	57**](#heading=h.baxw73kjstr8)
+
+[**R-15: Cronograma de 24 meses o presupuesto total (\$260.850 USD) subestimados frente a la complejidad real del sistema multiagente	58**](#heading=h.ahqmh1e56c2e)
+
+[**R-16: Diseño de clases y componentes aún no validado oficialmente que resulte inadecuado para la implementación real	59**](#heading=h.5ppgsbibh8z0)
+
+[**R-17: Inmadurez del proceso de desarrollo y del ambiente de trabajo compartido entre los múltiples equipos de agentes (Scrum multi-equipo, Google Workspace, Jira)	60**](#heading=h.fm76juhbi8so)
+
+[**R-18: Adopción de tecnologías de IA generativa local (Ollama, RAG, prompt engineering) nuevas para el equipo de desarrollo	61**](#heading=h.d1iy6waj5ce7)
+
+[**R-19: Expectativa de que el motor de IA resuelva por sí solo la generación de contenido sin controles ni supervisión humana adecuados (falsa sensación de solución mágica)	62**](#heading=h.jl9h7wsfxam8)
+
+[**R-20: Demora en poner el sistema operativo frente a las necesidades actuales de la Secretaría de Extensión, perdiendo vigencia u oportunidad frente al problema original	63**](#heading=h.vefp3h3m97gw)
+
+[**R-21: Dificultad para conseguir el respaldo institucional necesario para escalar ExtensiónBot al resto de la Facultad en el marco del Plan de escalabilidad hacia el Centenario	64**](#heading=h.i2y93dho3ppy)
+
+[**R-22: Falta de apoyo político/institucional sostenido de las autoridades de la FIE para la continuidad presupuestaria del proyecto	65**](#heading=h.ppbd5irugh9f)
+
+[**R-23: Suplantación de identidad de ExtensiónBot para acceder a APIs internas (Spoofing)	66**](#heading=h.ukd76ep39v93)
+
+[**R-24: Inyección de prompts indirecta vía RAG/Repositorio Institucional que altera instrucciones (Tampering)	67**](#heading=h.196zvlqqcug7)
+
+[**R-25: Imposibilidad de determinar si una acción dañina fue error de lógica o ataque (Repudiation)	68**](#heading=h.uffldlj3lrdq)
+
+[**R-26: Fuga de datos confidenciales o PII en una respuesta generada (Information Disclosure)	69**](#heading=h.d0ri93ygzvj4)
+
+[**R-27: Agente engañado para ejecutar acción fuera de su autorización (Elevation of Privilege)	70**](#heading=h.a8b68n37hrnq)
+
+[**R-28: Falla de integridad en datos de entrenamiento/RAG (Data Poisoning)	71**](#heading=h.r0b8nhchigrp)
+
+[**R-29: Credenciales de API hardcodeadas o compartidas entre desarrolladores	72**](#heading=h.8m9hsvsyvxf1)
+
+[**R-30: Saturación del agente por ráfaga de solicitudes agotando ventana de contexto (Denial of Service)	73**](#heading=h.8d8krh6tw355)
+
+[**R-31: Caída o inestabilidad del modelo local Ollama (timeout, falta de GPU)	74**](#heading=h.m9tlj1y9g05)
 
 # 
 
```

```diff
@@ -2104,7 +2166,7 @@
 
 ![][image5]
 
-# [Diagrama de Casos de Uso](https://drive.google.com/file/d/1tKj5cJBYBIKRFnbD6AL265OpZjdiNXFQ/view?usp=drive_link)
+# [Diagrama de Casos de Uso](https://drive.google.com/file/d/1tKj5cJBYBIKRFnbD6AL265OpZjdiNXFQ/view?usp=drive_link) {#diagrama-de-casos-de-uso}
 
 En el link adjunto anterior se puede acceder al diagrama de casos de uso del ExtensiónBot.
 
```

```diff
@@ -2576,187 +2638,210 @@
 | ![][image15] | ![][image16] |
 | ![][image17] | ![][image18] |
 
-# [Hitos y Tareas](https://docs.google.com/spreadsheets/u/0/d/1DoZePv7EQVJgeBqLWTRjt9R8q6gY8WsQRaVyW0Pnix4/edit)
+# [Hitos y Tareas](https://docs.google.com/spreadsheets/u/0/d/1DoZePv7EQVJgeBqLWTRjt9R8q6gY8WsQRaVyW0Pnix4/edit) {#hitos-y-tareas}
 
 | ID | Tarea | Responsable/s | Duración | Meses |
 | :---: | :---: | :---: | :---: | :---: |
 | T-000 | Relevar necesidades y requisitos del departamento de Secretaría Extensión | Analista Funcional | 6 días | Agosto |
-| T-001 | Definir el modelo de negocio | Analista de Negocio, Lider de Proyecto | 4 días | Agosto |
+| T-001 | Definir el modelo de negocio | Analista de Negocio, Líder de Proyecto | 4 días | Agosto |
 | T-002 | Definir modelo de dominio | Analista Funcional, Arquitecto de Software | 4 días | Agosto |
-| T-003 | Elaborar el enunciado del alcance del proyecto | Lider de Proyecto, Analista Funcional | 2 días | Agosto |
-| T-004 | Elaborar la Estructura de Desglose del Trabajo (EDT/WBS) | Lider de Proyecto | 3 días | Agosto |
-| T-005 | Planificar tareas y responsables mediante una matriz RACI | Lider de Proyecto | 2 días | Agosto |
-| T-006 | Elaborar el cronograma del proyecto y definir la ruta crítica | Lider de Proyecto | 3 días | Agosto |
-| T-007 | Planificar Recursos Humanos | Lider de Proyecto, Gestión de RRHH | 2 días | Agosto |
-| T-008 | Definir roles, organigrama del equipo y plan de incorporación | Lider de Proyecto, Gestión de RRHH | 3 días | Agosto |
-| T-009 | Planificar costos | Lider de Proyecto | 2 días | Agosto |
-| T-010 | Estimar los costos del proyecto por actividad | Lider de Proyecto | 4 días | Agosto |
-| T-011 | Elaborar el presupuesto base y la línea base de costos | Lider de Proyecto | 2 días | Septiembre |
-| T-012 | Elaborar el plan de gestión de adquisiciones (licencias, servicios cloud, etc) | Lider de Proyecto | 2 días | Septiembre |
-| T-013 | Realizar matriz de riesgos | Lider de Proyecto, Gestor de Riesgos | 3 días | Septiembre |
-| T-014 | Definir estrategias de respuesta a riesgos y plan de monitoreo y control | Lider de Proyecto, Gestor de Riesgos | 2 días | Septiembre |
-| T-015 | Planificar la Administración de Calidad mediante DoD y Evidencia Viva | Líder de QA | 2 días | Agosto |
-| T-016 | Elaborar el plan de gestión de comunicaciones (matriz de interesados, canales y frecuencia) | Lider de Proyecto, Analista Funcional | 2 días | Septiembre |
-| T-017 | Realizar diagramas UML pertinentes | Arquitecto de Software, Diseñador de Sistemas | 9 días | Agosto |
-| T-018 | Realizar el plan y escenarios de pruebas | Lider de QA, Analista de QA, QA tester | 6 días | Agosto, Septiembre |
-| T-019 | Validar el documento de desarrollo del proyecto con el director del proyecto | Lider de Proyecto, Director del Proyecto | 1 día | Septiembre |
-| **HT-000** | **Acta del Proyecto Aprobada** |  |  |  |
-| T-020 | Definir plantillas básicas | Analista Funcional, Diseñador UX | 5 días | Septiembre |
-| T-021 | Crear estructura de carpetas en Google workspace | Administrador de Google Workspace | 1 día | Septiembre |
-| T-022 | Configurar roles | Administrador de Sistemas, Especialista en Ciberseguridad | 2 días | Septiembre |
-| T-023 | Configurar permisos de acceso | Administrador de Sistemas, Especialista en Ciberseguridad | 2 días | Septiembre |
-| T-024 | Validar el control de acceso basado en roles (RBAC) y prompt injection | Especialista en Ciberseguridad, Arquitecto de Software | 5 días | Septiembre |
-| T-025 | Configurar cuentas de servicio y credenciales API para integraciones externas | Desarrollador Backend, Ingeniero Especialista en Servicios en la Nube | 3 días | Septiembre |
-| T-026 | Adquirir y contratar la infraestructura cloud, servidores y licencias de herramientas necesarias | Lider de Proyecto, Administrador de Sistemas | 6 días | Septiembre |
-| **HT-001** | **Estructura Base en Google Workspace Lista** |  |  |  |
-| T-027 | Implementar manejo de errores | Desarrollador Backend | 4 días | Septiembre |
-| T-028 | Implementar logs básicos | Desarrollador Backend | 2 días | Septiembre |
-| T-029 | Configurar triggers (time \+ onEdit) | Desarrollador Backend, Especialista en Automatizaciones | 2 días | Octubre |
-| T-030 | Validar usabilidad interna y ejecución de automatizaciones | Analista de QA | 2 días | Octubre |
-| **HT-002** | **Automatizaciones con Apps Script Establecidas** |  |  |  |
-| T-031 | Diseñar plantillas de prompt engineering ajustadas por tipo de contenido | Ingeniero de Prompts, Diseñador UX | 6 días | Octubre |
-| T-032 | Configurar el motor de inferencia local (Ollama con Llama 3/Mistral) | Especialista en IA | 5 días | Octubre |
-| T-033 | Relacionar al motor de inferencia con el Repositorio Institucional para consultas | Arquitecto de Software, Ingeniero de Datos | 4 días | Octubre |
-| T-034 | Configurar la cola de tareas (Celery \+ Redis) | Desarrollador Backend | 4 días | Octubre |
-| T-035 | Implementar prototipo de generación de contenido, prompts y fallback | Desarrollador Backend, Especialista en IA | 8 días | Octubre, Noviembre |
-| T-036 | Validar precisión, usabilidad y tiempo de respuesta del motor | Analista de QA | 5 días | Noviembre |
-| **HT-003** | **Motor de IA y Colas de Tareas Desplegados** |  |  |  |
-| T-037 | Configurar una base de datos para almacenar los logs | Administrador de Base de Datos (DBA), Especialista en Ciberseguridad | 2 días | Noviembre |
-| T-038 | Diseñar el esquema relacional para la persistencia de estados de borradores y aprobaciones | Arquitecto de Software, Diseñador de Base de Datos | 5 días | Noviembre |
-| T-039 | Configurar logs detallados (Con fecha, proceso, estado y error) | Desarrollador Backend | 2 días | Noviembre |
-| T-040 | Conectar y relacionar eventos de la base de datos con los triggers de Apps Script | Desarrollador Backend, Integrador de Sistemas | 4 días | Noviembre |
-| T-041 | Validar la trazabilidad, auditoría de evidencias y seguridad de los registros | Especialista en Ciberseguridad, Líder de QA | 4 días | Noviembre |
-| **HT-004** | **Trazabilidad Implementada** |  |  |  |
-| T-042 | Monitorear y controlar los costos reales del proyecto mediante gestión del valor ganado (EVM) | Lider de Proyecto | 2 días | Diciembre |
-| **HT-005** | **Control de Costos del Proyecto Validado** |  |  |  |
-| T-043 | Relacionar plantillas correspondientes | Diseñador UX, Analista Funcional | 2 días | Diciembre |
-| T-044 | Implementar parser para los formatos de entrada | Desarrollador Backend | 5 días | Diciembre |
-| T-045 | Configurar entradas desde Google Sheets | Desarrollador Backend | 2 días | Diciembre |
-| T-046 | Implementar flujo de generación automática de documentos | Desarrollador Backend | 7 días | Diciembre |
-| T-047 | Validar prueba controlada de generación de contenidos | Analista de QA | 4 días | Diciembre |
-| **HT-006** | **Generación de Gacetillas, Newsletters y Certificados Lista** |  |  |  |
-| T-048 | Definir estilo, tono, hashtags y longitud de posts según la red social en el motor de generación | Analista Funcional, Ingeniero de Prompts, Diseñador UX, Creador de Contenido | 5 días | Diciembre |
-| T-049 | Implementar prototipo de generación de posts por canal | Desarrollador Backend | 5 días | Enero |
-| **HT-007** | **Generación de Post para Redes Sociales Lista** |  |  |  |
-| T-050 | Desarrollar interfaz de log in | Desarrollador Frontend, Diseñador UI | 5 días | Enero |
-| T-051 | Desarrollar la autenticación por roles | Desarrollador Backend, Especialista en Ciberseguridad | 4 días | Enero |
-| T-052 | Desarrollar interfaz de revisión de borradores y validación semántica/utilitaria | Desarrollador Frontend, Diseñador UX, Diseñador UI | 9 días | Enero |
-| T-053 | Desarrollar módulo de revisión y validación de borradores | Desarrollador Backend, Analista Funcional | 5 días | Enero, Febrero |
-| T-054 | Implementar regeneración con correcciones | Desarrollador Backend | 4 días | Febrero |
-| T-055 | Validar usabilidad interna, flujo de interacción humana y evidencias | Analista de QA | 4 días | Febrero |
-| T-056 | Capacitar internamente al equipo de desarrollo en el uso de la interfaz y el flujo de trabajo del sistema | Capacitador, Líder de Proyecto | 2 días | Febrero |
-| **HT-008** | **UI e Interacción Humana Desplegadas** |  |  |  |
-| T-057 | Analizar contratos de interfaz para cada agente | Arquitecto de Software, Analista Funcional | 4 días | Febrero |
-| T-058 | Desarrollar la interfaz con el Agente 2 | Desarrollador Backend, Integrador de Sistemas | 4 días | Febrero, Marzo |
-| T-059 | Desarrollar la interfaz con el Agente 3 | Desarrollador Backend, Integrador de Sistemas | 4 días | Febrero, Marzo |
-| T-060 | Desarrollar la interfaz con el Agente 4 | Desarrollador Backend, Integrador de Sistemas | 4 días | Febrero, Marzo |
-| T-061 | Desarrollar la interfaz con el Agente 5 | Desarrollador Backend, Integrador de Sistemas | 4 días | Febrero, Marzo |
-| T-062 | Pruebas de integración end-to-end entre todos los agentes del sistema | Líder de QA, Integrador de Sistemas | 6 días | Marzo |
-| T-063 | Validar calidad, seguridad y trazabilidad de la integración | Analista de QA, Especialista en Ciberseguridad | 4 días | Marzo |
-| **HT-009** | **Interfaces con otros Agentes Listas** |  |  |  |
-| T-064 | Analizar requisitos y contratos de integración con APIs de canales de difusión | Arquitecto de Software, Analista Funcional | 4 días | Marzo |
-| T-065 | Conectar el sistema con las APIs de los canales de difusión externos | Desarrollador Backend, Integrador de Sistemas | 5 días | Marzo |
-| T-066 | Integrar el Scheduler | Desarrollador Backend | 3 días | Marzo |
-| T-067 | Configurar logs de publicación exitosa | Desarrollador Backend | 2 días | Marzo |
-| T-068 | Validar flujo end-to-end de publicación programada y evidencias | Analista de QA | 4 días | Marzo, Abril |
-| T-069 | Emitir informe de avance del proyecto y comunicar resultados a los interesados clave | Lider de Proyecto, Analista Funcional | 1 día | Abril |
-| **HT-010** | **Publicación en Canales de Difusión Operativa** |  |  |  |
-| T-070 | Redactar el manual de usuario y operación del sistema | Redactor Técnico, Analista Funcional | 6 días | Abril |
-| T-071 | Realizar demostración funcional del Agente 1 | Analista Funcional, Lider de Proyecto | 1 día | Abril |
-| T-072 | Brindar jornadas de capacitación al personal de la Secretaría de Extensión | Capacitador, Analista Funcional | 5 días | Abril |
-| T-073 | Implementar la transferencia operativa del sistema y acompañamiento | Lider de Proyecto | 10 días | Abril, Mayo |
-| T-074 | Validar la adopción operativa y recopilar evidencia de conformidad | Líder de QA | 4 días | Mayo |
-| T-075 | Elaborar el informe final de cierre y lecciones aprendidas y comunicarlo formalmente a los interesados | Lider de Proyecto | 2 días | Mayo |
-| T-076 | Cerrar contratos y adquisiciones con proveedores externos (licencias, servicios cloud) | Lider de Proyecto | 1 día | Mayo |
-| T-077 | Realizar el cierre financiero del proyecto y comparar costos reales vs. presupuestados | Lider de Proyecto | 2 días | Mayo |
-| **HT-011** | **Finalización del Proyecto** |  |  |  |
-
-## **Resumen de Hitos del Proyecto:**
-
-* HT-000: Acta del Proyecto Aprobada  
-* HT-001: Estructura Base en Google Workspace Lista  
-* HT-002: Automatizaciones con Apps Script Establecidas  
-* HT-003: Motor de IA y Colas de Tareas Desplegados  
-* HT-004: Trazabilidad Implementada  
-* HT-005: Control de Costos del Proyecto Validado  
-* HT-006: Generación de Gacetillas, Newsletters y Certificados Lista  
-* HT-007: Generación de Post para Redes Sociales Lista  
-* HT-008: UI e Interacción Humana Desplegadas  
-* HT-009: Interfaces con otros Agentes Listas  
-* HT-010: Publicación en Canales de Difusión Operativa  
-* HT-011: Finalización del Proyecto
-
-# Estimación de Costos
-
-## **Mano de obra**
+| T-003 | Elaborar el enunciado del alcance del proyecto | Líder de Proyecto, Analista Funcional | 2 días | Agosto |
+| T-004 | Elaborar la Estructura de Desglose del Trabajo (EDT/WBS) | Líder de Proyecto | 3 días | Agosto |
+| T-005 | Planificar tareas y responsables mediante una matriz RACI | Líder de Proyecto | 2 días | Agosto |
+| T-006 | Elaborar el cronograma del proyecto y definir la ruta crítica | Líder de Proyecto | 3 días | Agosto |
+| T-007 | Planificar Recursos Humanos | Líder de Proyecto, Gestión de RRHH | 2 días | Agosto |
+| T-008 | Definir roles, organigrama del equipo y plan de incorporación | Líder de Proyecto, Gestión de RRHH | 3 días | Agosto |
+| T-009 | Planificar costos | Líder de Proyecto | 2 días | Agosto |
+| T-010 | Estimar los costos del proyecto por actividad | Líder de Proyecto | 4 días | Agosto |
+| T-011 | Elaborar el presupuesto base y la línea base de costos | Líder de Proyecto | 2 días | Septiembre |
+| T-012 | Elaborar el plan de gestión de adquisiciones (licencias, servicios cloud, etc) | Líder de Proyecto | 2 días | Septiembre |
+| T-013 | Elaborar el Plan de Gestión de Riesgos según PMBOK y ROAM | Líder de Proyecto, Gestor de Riesgos | 2 días | Septiembre |
+| T-014 | Definir críterios y escalas de gestión de riesgos apra el proyecto | Gestor de Riesgos, Líder de Proyecto | 2 días | Septiembre |
+| T-015 | Identificar y documentar riesgos iniciales y emergentes | Gestor de Riesgos, Líder de Proyecto | 3 días | Septiembre |
+| T-016 | Realizar matriz de riesgos | Líder de Proyecto, Gestor de Riesgos | 3 días | Septiembre |
+| T-017 | Realizar el análisis cualitativo de riesgos y actualizar la exposición de la matriz | Gestor de Riesgos, Líder de Proyecto | 2 días | Septiembre |
+| T-018 | Realizar el análisis cuantitativo de los riesgos prioritarios y relacionarlo con reservas, cronograma y EVM | Gestor de Riesgos, Líder de Proyecto | 3 días | Septiembre, Octubre |
+| T-019 | Definir estrategias de respuesta a riesgos y plan de monitoreo y control | Líder de Proyecto, Gestor de Riesgos | 2 días | Septiembre |
+| T-020 | Asignar propietario del riesgo, responsable de la respuesta y estado ROAM para cada riesgo activo | Gestor de Riesgos, Líder de Proyecto | 2 días | Septiembre |
+| **HT-000** | **Plan y Registro de Riesgos Baseline Aprobados** |  |  |  |
+| T-021 | Planificar la Administración de Calidad mediante DoD y Evidencia Viva | Líder de QA | 2 días | Agosto |
+| T-022 | Elaborar el plan de gestión de comunicaciones (matriz de interesados, canales y frecuencia) | Líder de Proyecto, Analista Funcional | 2 días | Septiembre |
+| T-023 | Realizar diagramas UML pertinentes | Arquitecto de Software, Diseñador de Sistemas | 9 días | Agosto |
+| T-024 | Realizar el plan y escenarios de pruebas | Líder de QA, Analista de QA, QA tester | 6 días | Agosto, Septiembre |
+| T-025 | Validar el documento de desarrollo del proyecto con el director del proyecto | Líder de Proyecto, Director del Proyecto | 1 día | Septiembre |
+| **HT-001** | **Acta del Proyecto Aprobada** |  |  |  |
+| T-026 | Definir plantillas básicas | Analista Funcional, Diseñador UX | 5 días | Septiembre |
+| T-027 | Crear estructura de carpetas en Google workspace | Administrador de Google Workspace | 1 día | Septiembre |
+| T-028 | Configurar roles | Administrador de Sistemas, Especialista en Ciberseguridad | 2 días | Septiembre |
+| T-029 | Configurar permisos de acceso | Administrador de Sistemas, Especialista en Ciberseguridad | 2 días | Septiembre |
+| T-030 | Validar el control de acceso basado en roles (RBAC) y prompt injection | Especialista en Ciberseguridad, Arquitecto de Software | 5 días | Septiembre |
+| T-031 | Configurar cuentas de servicio y credenciales API para integraciones externas | Desarrollador Backend, Ingeniero Especialista en Servicios en la Nube | 3 días | Septiembre |
+| T-032 | Adquirir y contratar la infraestructura cloud, servidores y licencias de herramientas necesarias | Líder de Proyecto, Administrador de Sistemas | 6 días | Septiembre |
+| **HT-002** | **Estructura Base en Google Workspace Lista** |  |  |  |
+| T-033 | Implementar manejo de errores | Desarrollador Backend | 4 días | Septiembre |
+| T-034 | Implementar logs básicos | Desarrollador Backend | 2 días | Septiembre |
+| T-035 | Configurar triggers (time \+ onEdit) | Desarrollador Backend, Especialista en Automatizaciones | 2 días | Octubre |
+| T-036 | Validar usabilidad interna y ejecución de automatizaciones | Analista de QA | 2 días | Octubre |
+| **HT-003** | **Automatizaciones con Apps Script Establecidas** |  |  |  |
+| T-037 | Diseñar plantillas de prompt engineering ajustadas por tipo de contenido | Ingeniero de Prompts, Diseñador UX | 6 días | Octubre |
+| T-038 | Configurar el motor de inferencia local (Ollama con Llama 3/Mistral) | Especialista en IA | 5 días | Octubre |
+| T-039 | Relacionar al motor de inferencia con el Repositorio Institucional para consultas | Arquitecto de Software, Ingeniero de Datos | 4 días | Octubre |
+| T-040 | Configurar la cola de tareas (Celery \+ Redis) | Desarrollador Backend | 4 días | Octubre |
+| T-041 | Implementar prototipo de generación de contenido, prompts y fallback | Desarrollador Backend, Especialista en IA | 8 días | Octubre, Noviembre |
+| T-042 | Validar precisión, usabilidad y tiempo de respuesta del motor | Analista de QA | 5 días | Noviembre |
+| **HT-004** | **Motor de IA y Colas de Tareas Desplegados** |  |  |  |
+| T-043 | Implementar y verificar las acciones de respuesta preventiva/mitigación definidas para los riesgos priorizados | Gestor de Riesgos, Líder de Proyecto | 5 días | Octubre, Noviembre |
+| T-044 | Implementar y validar los controles de seguridad asociados a riesgos críticos/altos | Especialista en Ciberseguridad, Arquitecto de Software, Desarrollador Backend, Ingeniero de Datos | 8 días | Octubre, Noviembre, Diciembre |
+| T-045 | Realizar revisión ROAM de riesgos al inicio/cierre de cada Sprint y registrar decisiones | Gestor de Riesgos, Líder de Proyecto | 1 día por Sprint | Octubre, Noviembre, Diciembre, Enero, Febrero, Marzo, Abril |
+| T-046 | Actualizar la matriz/registro de riesgos después de cada Sprint, cambio relevante o incidente | Gestor de Riesgos | 1 día por Sprint | Octubre, Noviembre, Diciembre, Enero, Febrero, Marzo, Abril, Mayo |
+| T-047 | Monitorear disparadores, indicadores de riesgo y exposición residual; escalar desvíos según umbrales definidos | Gestor de Riesgos, Líder de Proyecto | 1 día por Sprint | Octubre, Noviembre, Diciembre, Enero, Febrero, Marzo, Abril, Mayo |
+| T-048 | Ejecutar y documentar planes de contingencia cuando se active un disparador de riesgo | Gestor de Riesgos, Líder de Proyecto | 2 días por evento | Octubre, Noviembre, Diciembre, Enero, Febrero, Marzo, Abril, Mayo |
+| T-049 | Configurar una base de datos para almacenar los logs | Administrador de Base de Datos (DBA), Especialista en Ciberseguridad | 2 días | Noviembre |
+| T-050 | Diseñar el esquema relacional para la persistencia de estados de borradores y aprobaciones | Arquitecto de Software, Diseñador de Base de Datos | 5 días | Noviembre |
+| T-051 | Configurar logs detallados (Con fecha, proceso, estado y error) | Desarrollador Backend | 2 días | Noviembre |
+| T-052 | Conectar y relacionar eventos de la base de datos con los triggers de Apps Script | Desarrollador Backend, Integrador de Sistemas | 4 días | Noviembre |
+| T-053 | Validar la trazabilidad, auditoría de evidencias y seguridad de los registros | Especialista en Ciberseguridad, Líder de QA | 4 días | Noviembre |
+| **HT-005** | **Trazabilidad Implementada** |  |  |  |
+| T-054 | Auditar la efectividad de los controles de riesgo y conservar evidencia de tratamiento, decisiones, excepciones y riesgos residuales | Gestor de Riesgos, Líder de QA, Especialista en Ciberseguridad | 3 días | Noviembre, Enero, Marzo, Mayo |
+| **HT-006** | **Monitoreo, Tratamiento y Seguimiento ROAM Operativos** |  |  |  |
+| T-055 | Monitorear y controlar los costos reales del proyecto mediante gestión del valor ganado (EVM) | Líder de Proyecto | 2 días | Diciembre |
+| **HT-007** | **Control de Costos del Proyecto Validado** |  |  |  |
+| T-056 | Relacionar plantillas correspondientes | Diseñador UX, Analista Funcional | 2 días | Diciembre |
+| T-057 | Implementar parser para los formatos de entrada | Desarrollador Backend | 5 días | Diciembre |
+| T-058 | Configurar entradas desde Google Sheets | Desarrollador Backend | 2 días | Diciembre |
+| T-059 | Implementar flujo de generación automática de documentos | Desarrollador Backend | 7 días | Diciembre |
+| T-060 | Validar prueba controlada de generación de contenidos | Analista de QA | 4 días | Diciembre |
+| **HT-008** | **Generación de Gacetillas, Newsletters y Certificados Lista** |  |  |  |
+| T-061 | Definir estilo, tono, hashtags y longitud de posts según la red social en el motor de generación | Analista Funcional, Ingeniero de Prompts, Diseñador UX, Creador de Contenido | 5 días | Diciembre |
+| T-062 | Implementar prototipo de generación de posts por canal | Desarrollador Backend | 5 días | Enero |
+| **HT-009** | **Generación de Post para Redes Sociales Lista** |  |  |  |
+| T-063 | Desarrollar interfaz de log in | Desarrollador Frontend, Diseñador UI | 5 días | Enero |
+| T-064 | Desarrollar la autenticación por roles | Desarrollador Backend, Especialista en Ciberseguridad | 4 días | Enero |
+| T-065 | Desarrollar interfaz de revisión de borradores y validación semántica/utilitaria | Desarrollador Frontend, Diseñador UX, Diseñador UI | 9 días | Enero |
+| T-066 | Desarrollar módulo de revisión y validación de borradores | Desarrollador Backend, Analista Funcional | 5 días | Enero, Febrero |
+| T-067 | Implementar regeneración con correcciones | Desarrollador Backend | 4 días | Febrero |
+| T-068 | Validar usabilidad interna, flujo de interacción humana y evidencias | Analista de QA | 4 días | Febrero |
+| T-069 | Capacitar internamente al equipo de desarrollo en el uso de la interfaz y el flujo de trabajo del sistema | Capacitador, Líder de Proyecto | 2 días | Febrero |
+| **HT-010** | **UI e Interacción Humana Desplegadas** |  |  |  |
+| T-070 | Analizar contratos de interfaz para cada agente | Arquitecto de Software, Analista Funcional | 4 días | Febrero |
+| T-071 | Desarrollar la interfaz con el Agente 2 | Desarrollador Backend, Integrador de Sistemas | 4 días | Febrero, Marzo |
+| T-072 | Desarrollar la interfaz con el Agente 3 | Desarrollador Backend, Integrador de Sistemas | 4 días | Febrero, Marzo |
+| T-073 | Desarrollar la interfaz con el Agente 4 | Desarrollador Backend, Integrador de Sistemas | 4 días | Febrero, Marzo |
+| T-074 | Desarrollar la interfaz con el Agente 5 | Desarrollador Backend, Integrador de Sistemas | 4 días | Febrero, Marzo |
+| T-075 | Pruebas de integración end-to-end entre todos los agentes del sistema | Líder de QA, Integrador de Sistemas | 6 días | Marzo |
+| T-076 | Validar calidad, seguridad y trazabilidad de la integración | Analista de QA, Especialista en Ciberseguridad | 4 días | Marzo |
+| **HT-011** | **Interfaces con otros Agentes Listas** |  |  |  |
+| T-077 | Analizar requisitos y contratos de integración con APIs de canales de difusión | Arquitecto de Software, Analista Funcional | 4 días | Marzo |
+| T-078 | Conectar el sistema con las APIs de los canales de difusión externos | Desarrollador Backend, Integrador de Sistemas | 5 días | Marzo |
+| T-079 | Integrar el Scheduler | Desarrollador Backend | 3 días | Marzo |
+| T-080 | Configurar logs de publicación exitosa | Desarrollador Backend | 2 días | Marzo |
+| T-081 | Validar flujo end-to-end de publicación programada y evidencias | Analista de QA | 4 días | Marzo, Abril |
+| T-082 | Emitir informe de avance del proyecto y comunicar resultados a los interesados clave | Líder de Proyecto, Analista Funcional | 1 día | Abril |
+| **HT-012** | **Publicación en Canales de Difusión Operativa** |  |  |  |
+| T-083 | Redactar el manual de usuario y operación del sistema | Redactor Técnico, Analista Funcional | 6 días | Abril |
+| T-084 | Realizar demostración funcional del Agente 1 | Analista Funcional, Líder de Proyecto | 1 día | Abril |
+| T-085 | Brindar jornadas de capacitación al personal de la Secretaría de Extensión | Capacitador, Analista Funcional | 5 días | Abril |
+| T-086 | Implementar la transferencia operativa del sistema y acompañamiento | Líder de Proyecto | 10 días | Abril, Mayo |
+| T-087 | Validar la adopción operativa y recopilar evidencia de conformidad | Líder de QA | 4 días | Mayo |
+| T-088 | Cerrar, transferir o aceptar formalmente los riesgos residuales y documentar lecciones aprendidas del ciclo de riesgos | Gestor de Riesgos, Líder de Proyecto | 2 días | Mayo |
+| **HT-013** | **Ciclo de Administración de Riesgos Cerrado y Lecciones Aprendidas Registradas** |  |  |  |
+| T-089 | Elaborar el informe final de cierre y lecciones aprendidas y comunicarlo formalmente a los interesados | Líder de Proyecto | 2 días | Mayo |
+| T-090 | Realizar el cierre financiero del proyecto y comparar costos reales vs. presupuestados | Líder de Proyecto | 2 días | Mayo |
+| **HT-014** | **Finalización del Proyecto** |  |  |  |
+
+## **Resumen de Hitos del Proyecto:** {#resumen-de-hitos-del-proyecto:}
+
+* HT-000: Plan y Registro de Riesgos Baseline Aprobados  
+* HT-001: Acta del Proyecto Aprobada  
+* HT-002: Estructura Base en Google Workspace Lista  
+* HT-003: Automatizaciones con Apps Script Establecidas  
+* HT-004: Motor de IA y Colas de Tareas Desplegados  
+* HT-005: Trazabilidad Implementada  
+* HT-006: Monitoreo, Tratamiento y Seguimiento ROAM Operativos  
+* HT-007: Control de Costos del Proyecto Validado  
+* HT-008: Generación de Gacetillas, Newsletters y Certificados Lista  
+* HT-009: Generación de Post para Redes Sociales Lista  
+* HT-010: UI e Interacción Humana Desplegadas  
+* HT-011: Interfaces con otros Agentes Listas  
+* HT-012: Publicación en Canales de Difusión Operativa  
+* HT-013: Ciclo de Administración de Riesgos Cerrado y Lecciones Aprendidas Registradas  
+* HT-014: Finalización del Proyecto
+
+# Estimación de Costos {#estimación-de-costos}
+
+## **Mano de obra** {#mano-de-obra}
 
 Considerando la disponibilidad del listado de [Hitos y Tareas](https://docs.google.com/spreadsheets/u/0/d/1DoZePv7EQVJgeBqLWTRjt9R8q6gY8WsQRaVyW0Pnix4/edit) con los responsables de cada una de ellas especificados se decidió estimar los costos de mano de obra del proyecto de la siguiente manera:
 
-1. Se observó el diagrama de Gantt (estimación de los tiempos) y el/los meses en los que las tareas están asignadas ya que no es relevante la duración exacta de las tareas sino los meses en los que transcurren.  
-2. Una vez que se asociaron los meses a las tareas a estas se les asignaron roles responsables, llevando a un conteo de la cantidad de meses que se debería pagar el sueldo a cada uno.  
-3. Ya se tenía un estimado de cuánto cobra cada rol por día, así que asumiendo meses de 4 semanas y semanas de 4 días, se obtuvo el sueldo mensual para cada uno.  
+1. Se observó el diagrama de Gantt y los meses en los que las tareas están asignadas ya que los meses en los que transcurren determinarán el tiempo de contratación de los roles.  
+2. Una vez que se asociaron los meses a las tareas, a estas se les asignaron roles responsables, llevando a un conteo de la cantidad de meses que se debería pagar el sueldo a cada uno.  
+* Para los roles de conducción y supervisión, como el Director del Proyecto, Líder de Proyecto, Administrador de Sistemas, etc, se optó por mantener su contratación durante la totalidad del proyecto, dado que su disponibilidad continua es necesaria para la coordinación, el monitoreo y la resolución de contingencias más allá de que sus tareas puntuales documentadas se concentren en meses específicos.  
+3. Ya se tenía un estimado de cuánto cobra cada rol por día laboral (8 hs), así que asumiendo meses de 4 semanas y semanas de 5 días, se obtuvo el sueldo mensual para cada uno.  
 4. Teniendo en cuenta el sueldo mensual de cada rol se multiplicó este por la cantidad de meses que el proyecto lo necesita.  
-5. Se sumó la cantidad de todos los responsables y se obtuvo el costo estimado de mano de obra. **El total fue de $252.800 USD.**
+5. Se sumó la cantidad de todos los responsables y se obtuvo el costo estimado de mano de obra, alcanzando un total de **\$493.600** 
 
 Véase que por el momento se asume un empleado por rol, futuras adiciones pueden alterar el costo.
 
-## **Costos de hardware**
+## **Costos de hardware** {#costos-de-hardware}
 
 Considerando los requerimientos del Hardware de despliegue, el costo de los componentes sería:
 
-* GPU (NVIDIA RTX 4090): \~ $4.500 USD  
-* Procesador (Intel Core Ultra 7 270K): \~ $415 USD  
-* Memoria RAM (Kingston Fury Beast RGB 32GB 3200 Mhz DDR4): \~ $660 USD  
-* Almacenamiento (SSD WD Green SN3000 NVMe de 2TB): \~ $485 USD  
-* Gabinete, Fuente y Refrigeración: \~ $400 USD
-
-Si se realiza una sola compra inicial **el costo de hardware total sería de $6.460 USD**
-
-## **Gastos de oficina**
+* GPU (NVIDIA RTX 4090): \~ \$4.500 USD  
+* Procesador (Intel Core Ultra 7 270K): \~ \$415 USD  
+* Memoria RAM (Kingston Fury Beast RGB 32GB 3200 Mhz DDR4): \~ \$660 USD  
+* Almacenamiento (SSD WD Green SN3000 NVMe de 2TB): \~ \$485 USD  
+* Gabinete, Fuente y Refrigeración: \~ \$400 USD
+
+Si se realiza una sola compra inicial **el costo de hardware total sería de \$6.460 USD**
+
+## **Gastos de oficina** {#gastos-de-oficina}
 
 Energía Eléctrica:
 
-* Costo mensual: $120 USD  
-* Costos 10 meses: $1.200 USD
+* Costo mensual: \$120 USD  
+* Costos 10 meses: \$1.200 USD
 
 Agua:
 
-* Costo mensual estimado: $25 USD  
-* Costos 10 meses: $250 USD
+* Costo mensual estimado: \$25 USD  
+* Costos 10 meses: \$250 USD
 
 Internet de Alta Velocidad:
 
-* Costo mensual: $60 USD  
-* Costos 10 meses: $600 USD
+* Costo mensual: \$60 USD  
+* Costos 10 meses: \$600 USD
 
 Agencia de limpieza (dos veces por semana):
 
-* Costo mensual: $200 USD USD  
-* Costos 10 meses: $2.000 USD
+* Costo mensual: \$200 USD USD  
+* Costos 10 meses: \$2.000 USD
 
 Costos Misceláneos (Agua mineral, insumos de papelería institucional, etc):
 
-* Costo mensual: $70 USD  
-* Costos 10 meses: $700 USD
-
-**Total gastos de oficina (los 10 meses): $4.750 USD**
-
-## **Presupuesto total**
-
-Mano de obra \+ Costos de Hardware \+ Gastos de Oficina \= Presupuesto Total
-
-**$252.800 USD \+ $6.460 USD \+ $4.750 USD \= $264.010 USD**
-
-# Administración de Riesgos
-
-## **Modelos Adoptados**
+* Costo mensual: \$70 USD  
+* Costos 10 meses: \$700 USD
+
+**Total gastos de oficina (los 10 meses): \$4.750 USD**
+
+## **Presupuesto Total** {#presupuesto-total}
+
+Mano de obra \+ Costos de Hardware \+ Gastos de Oficina \= Costos y Gastos Totales  
+**\$493.600  USD \+ \$6.460 USD \+ \$4.750 USD \= \$504.810 USD**  
+**La ganancia deseada será un 40% del presupuesto total** 
+
+**$Presupuesto\ Total\ =\ \frac{Costos\ y\ Gastos\ Totales}{1\ -\ Ganancia}{\ }$**  
+**$=\ \frac{$504.810\ USD\ }{0.6}=$841.350\ USD$**
+
+# Administración de Riesgos {#administración-de-riesgos}
+
+## **Modelos Adoptados** {#modelos-adoptados}
 
 Se optó por combinar dos modelos de administración de riesgos en pos de cubrir las necesidades particulares del proyecto:
 
 1. **PMBOK**: Se incluyó este modelo para operar los riesgos de planificación y ejecución del proyecto al contar con herramientas dedicadas como EVM (Earned Value Management) para costos, la Estructura de División del Trabajo y cronogramas.  
 2. **ROAM**: El proyecto en general sigue una metodología ágil, el modelo ROAM es el estándar para gestionar riesgos en proyectos que siguen la filosofía Agile y permitirá incluir planificación de riesgos en cada Sprint.
 
-## [**Matriz de Riesgos**](https://docs.google.com/spreadsheets/d/1M3McczY4MFl_HmHHzSWTcSU3uLb9mBZpbMkfibwepV8/edit?usp=sharing)
+## [**Matriz de Riesgos**](https://docs.google.com/spreadsheets/d/1M3McczY4MFl_HmHHzSWTcSU3uLb9mBZpbMkfibwepV8/edit?usp=sharing) {#matriz-de-riesgos}
 
 Para escalar las probabilidades e impactos de cada riesgo se optó por la siguiente escala:
 
```

```diff
@@ -2765,199 +2850,127 @@
 * Alto (Entre 80% y 90%)  
 * Crítico (Más del 90%)
 
-
-| ID | Riesgo | Categoría | Probabilidad | Impacto | Nivel | Tratamiento |
-| :---: | ----- | :---: | :---: | :---: | :---: | :---: |
-| R-01 | Incompatibilidad de contratos de interfaz entre ExtensiónBot y los Agentes 2 a 5 durante la integración | Integración | Media | Alto | Alto | Reducir |
-| R-02 | Desviación del alcance por incorporación no controlada de nuevas funcionalidades solicitadas por otras áreas | Alcance | Media | Medio | Medio | Reducir |
-| R-03 | Retraso en cronograma por dependencia entre fases | Proyecto | Media | Alto | Alto | Reducir |
-| R-04 | Sobrecosto por subestimación de tareas de integración con Agentes 2–5 | Proyecto | Media | Medio | Medio | Aceptar |
-| R-05 | Incremento del costo del hardware especializado por variaciones del mercado o del tipo de cambio | Costos | Media | Medio | Medio | Aceptar |
-| R-06 | Identificación incompleta de riesgos emergentes durante las nuevas fases del proyecto | Riesgos | Media | Medio | Medio | Reducir |
-| R-07 | Contenido generado que no cumple con la Definición de Terminado (DoD) llega a instancias de validación por falencias en el plan de pruebas | Calidad | Media | Medio | Medio | Reducir |
-| R-08 | Falta de alineación entre los equipos de desarrollo de los distintos agentes por deficiencias en el plan de comunicaciones | Comunicaciones | Media | Medio | Medio | Reducir |
-| R-09 | Baja adopción por parte del personal de Extensión (resistencia al cambio) | Negocio / Adopción | Alta | Medio | Alto | Reducir |
-| R-10 | Dependencia de licencias/servicios cloud de terceros (Google Workspace, APIs de redes) | Proveedores | Media | Medio | Medio | Aceptar |
-| R-11 | Demora en la adquisición de infraestructura cloud, servidores o licencias necesarias para el desarrollo | Adquisiciones | Media | Medio | Medio | Reducir |
-| R-12 | Rotación o indisponibilidad de estudiantes de 4° y 5° año que integran el equipo de desarrollo | Recursos Humanos | Alta | Medio | Alto | Reducir |
-| R-13 | Personal inadecuado o con perfil insuficiente para las tecnologías críticas del proyecto | Recursos Humanos | Media | Alto | Alto | Reducir |
-| R-14 | Elaboración excesiva de requisitos y documentación de diseño más allá de lo necesario para el MVP | Alcance | Baja | Medio | Bajo | Aceptar |
-| R-15 | Cronograma o presupuesto total subestimados frente a la complejidad real del sistema multiagente | Proyecto | Media | Alto | Alto | Reducir |
-| R-16 | Diseño de clases y componentes aún no validado oficialmente que resulte inadecuado para la implementación real | Diseño | Media | Alto | Alto | Reducir |
-| R-17 | Inmadurez del proceso de desarrollo y del ambiente de trabajo compartido entre los múltiples equipos de agentes (Scrum multi-equipo, Google Workspace, Jira) | Proceso | Media | Medio | Medio | Reducir |
-| R-18 | Adopción de tecnologías de IA generativa local (Ollama, RAG, prompt engineering) nuevas para el equipo de desarrollo | Técnico | Alta | Medio | Alto | Reducir |
-| R-19 | Expectativa de que el motor de IA resuelva por sí solo la generación de contenido sin controles ni supervisión humana adecuados | Negocio / Adopción | Baja | Medio | Bajo | Aceptar |
-| R-20 | Demora en poner el sistema operativo frente a las necesidades actuales de la Secretaría de Extensión, perdiendo vigencia u oportunidad frente al problema original | Negocio / Adopción | Media | Medio | Medio | Reducir |
-| R-21 | Dificultad para conseguir el respaldo institucional necesario para escalar ExtensiónBot al resto de la Facultad en el marco del Plan de escalabilidad hacia el Centenario | Negocio / Adopción | Media | Medio | Medio | Aceptar |
-| R-22 | Falta de apoyo político/institucional sostenido de las autoridades de la FIE para la continuidad presupuestaria del proyecto | Negocio / Adopción | Baja | Alto | Medio | Aceptar |
-| R-23 | Suplantación de identidad de ExtensiónBot para acceder a APIs internas (Spoofing) | Seguridad | Media | Alto | Alto | Reducir |
-| R-24 | Inyección de prompts indirecta vía RAG/Repositorio Institucional que altera instrucciones (Tampering) | Seguridad | Alta | Alto | Crítico | Reducir |
-| R-25 | Imposibilidad de determinar si una acción dañina fue error de lógica o ataque (Repudiation) | Seguridad | Baja | Alto | Medio | Reducir |
-| R-26 | Fuga de datos confidenciales o PII en una respuesta generada (Information Disclosure) | Seguridad | Media | Alto | Alto | Reducir |
-| R-27 | Agente engañado para ejecutar acción fuera de su autorización (Elevation of Privilege) | Seguridad | Baja | Alto | Medio | Reducir |
-| R-28 | Falla de integridad en datos de entrenamiento/RAG (Data Poisoning) | Seguridad | Baja | Alto | Medio | Reducir |
-| R-29 | Credenciales de API hardcodeadas o compartidas entre desarrolladores | Seguridad | Media | Alto | Alto | Reducir |
-| R-30 | Saturación del agente por ráfaga de solicitudes agotando ventana de contexto (Denial of Service) | Seguridad / Infraestructura | Media | Medio | Medio | Reducir |
-| R-31 | Caída o inestabilidad del modelo local Ollama (timeout, falta de GPU) | Técnico / Infraestructura | Media | Medio | Medio | Reducir |
+| ID | Riesgo | Categoría | Probabilidad | Impacto | Nivel |
+| :---: | ----- | :---: | :---: | :---: | :---: |
+| R-01 | Incompatibilidades y problemas de integración con las interfaces de los demás agentes | Integración | Media | Alto | Alto |
+| R-02 | Retraso en cronograma por dependencia entre fases | Proyecto | Media | Alto | Alto |
+| R-03 | Sobrecosto por subestimación de tareas de integración con Agentes 2–5 | Proyecto | Media | Medio | Medio |
+| R-04 | Incremento del costo del hardware especializado por variaciones del mercado o del tipo de cambio | Costos | Media | Medio | Medio |
+| R-05 | Falta de alineación entre los equipos de desarrollo de los distintos agentes | Comunicaciones | Media | Medio | Medio |
+| R-06 | Baja adopción por parte del personal de Extensión (resistencia al cambio) | Negocio / Adopción | Alta | Medio | Alto |
+| R-07 | Demora en la adquisición de infraestructura cloud, servidores o licencias necesarias para el desarrollo | Adquisiciones | Media | Medio | Medio |
+| R-08 | Personal inadecuado o con perfil insuficiente para las tecnologías críticas del proyecto | Recursos Humanos | Media | Alto | Alto |
+| R-09 | Cronograma o presupuesto total subestimados frente a la complejidad real del sistema multiagente | Proyecto | Media | Alto | Alto |
+| R-10 | Diseño de clases y componentes aún no validado oficialmente que resulte inadecuado para la implementación real | Diseño | Media | Alto | Alto |
+| R-11 | Retrasos o resultados de precisión insuficientes en el motor de IA por la falta de experiencia previa del equipo con tecnologías de IA generativa local | Técnico | Alta | Medio | Alto |
+| R-12 | Demora en poner el sistema operativo frente a las necesidades actuales de la Secretaría de Extensión | Negocio / Adopción | Media | Medio | Medio |
+| R-13 | Falta de apoyo sostenido de las autoridades de la FIE para la continuidad presupuestaria del proyecto | Negocio / Adopción | Baja | Alto | Medio |
+| R-14 | Suplantación de identidad de ExtensiónBot para acceder a APIs internas (Spoofing) | Seguridad | Media | Alto | Alto |
+| R-15 | Inyección de prompts indirecta vía RAG/Repositorio Institucional que altera instrucciones (Tampering) | Seguridad | Alta | Alto | Crítico |
+| R-16 | Imposibilidad de determinar si una acción dañina fue error de lógica o ataque (Repudiation) | Seguridad | Baja | Alto | Medio |
+| R-17 | Fuga de datos confidenciales o PII en una respuesta generada (Information Disclosure) | Seguridad | Media | Alto | Alto |
+| R-18 | Agente engañado para ejecutar acción fuera de su autorización (Elevation of Privilege) | Seguridad | Baja | Alto | Medio |
+| R-19 | Falla de integridad en datos de entrenamiento/RAG (Data Poisoning) | Seguridad | Baja | Alto | Medio |
+| R-20 | Saturación del agente por ráfaga de solicitudes agotando ventana de contexto (Denial of Service) | Seguridad / Infraestructura | Media | Medio | Medio |
 
 En pos de facilitar la visualización en el documento, se procedió a agregarla en formato de lista:
 
-## **R-01: Incompatibilidad de contratos de interfaz entre ExtensiónBot y los Agentes 2 a 5 durante la integración (Integration Failure)**
+## **R-01: Incompatibilidades y problemas de integración con las interfaces de los demás agentes**
 
 | Causa de Origen | Definición independiente de los contratos de interfaz por parte de cada equipo de agente sin una validación cruzada temprana. |
 | :---: | :---- |
-| **Disparadores** | Fallos en las pruebas de integración end-to-end (T-062). Errores de formato de datos entre agentes reportados en logs. |
+| **Disparadores** | Fallos en las pruebas de integración end-to-end (T-075). Errores de formato de datos entre agentes reportados en logs. |
 | **Plan de Contingencia** | Congelar el contrato de interfaz en conflicto. Convocar una reunión de sincronización entre los equipos responsables de los agentes involucrados. Versionar el contrato afectado y re ejecutar las pruebas de integración. |
 | **Categoría** | Integración |
 | **Probabilidad** | Media |
 | **Impacto** | Alto |
 | **Nivel** | Alto |
 | **Tratamiento** | Reducir |
-| **Control Asociado** | Análisis de contratos de interfaz (T-057) y pruebas de integración end-to-end (T-062) |
+| **Control Asociado** | Análisis de contratos de interfaz (T-070) y pruebas de integración end-to-end (T-075) |
 | **Responsable** | Arquitecto de Software / Integrador de Sistemas |
 | **Estado (ROAM)** | Owned |
 
-## **R-02: Desviación del alcance por incorporación no controlada de nuevas funcionalidades solicitadas por otras áreas (Scope Creep)**
-
-| Causa de Origen | Ausencia de un proceso formal de control de cambios de alcance vinculado al EDT/WBS definido en T-004. |
+## **R-02: Retraso en cronograma por dependencia entre fases**
+
+| Causa de Origen | Encadenamiento estricto de hitos en la ruta crítica (HT-004 → HT-010) sin buffers suficientes entre fases dependientes. |
 | :---: | :---- |
-| **Disparadores** | Solicitudes de nuevas funcionalidades por parte de la Secretaría de Extensión o de otros agentes fuera de los requisitos funcionales definidos. Incremento del backlog de Jira sin relación con los CU documentados. |
-| **Plan de Contingencia** | Evaluar la solicitud a través de un comité de cambios. Documentar el impacto en cronograma y costo antes de aprobar. Rechazar o diferir la incorporación a una iteración futura si no está alineada al alcance aprobado. |
-| **Categoría** | Alcance |
-| **Probabilidad** | Media |
-| **Impacto** | Medio |
-| **Nivel** | Medio |
-| **Tratamiento** | Reducir |
-| **Control Asociado** | Control de cambios formal vinculado al EDT/WBS (T-004) |
-| **Responsable** | Líder de Proyecto / Analista Funcional |
-| **Estado (ROAM)** | Owned |
-
-## **R-03: Retraso en cronograma por dependencia entre fases (ej. Motor de IA bloqueando UI)**
-
-| Causa de Origen | Encadenamiento estricto de hitos en la ruta crítica (HT-003 → HT-008) sin buffers suficientes entre fases dependientes. |
-| :---- | :---- |
-| **Disparadores** | Desvío del avance real respecto del planificado en el Gantt superior al 15%. Hito HT-003 no alcanzado en la fecha prevista. |
-| **Plan de Contingencia** | Re-priorizar el backlog de Jira para desacoplar tareas de UI que no dependan estrictamente del motor de IA. Reasignar recursos desde tareas de menor prioridad. Comunicar el desvío a interesados clave en el próximo informe de avance (T-069). |
+| **Disparadores** | Desvío del avance real respecto del planificado en el Gantt superior al 15%. Hito HT-004 no alcanzado en la fecha prevista. |
+| **Plan de Contingencia** | Re-priorizar el backlog de Jira para desacoplar tareas de UI que no dependan estrictamente del motor de IA. Reasignar recursos desde tareas de menor prioridad. Comunicar el desvío a interesados clave en el próximo informe de avance (T-082). |
 | **Categoría** | Proyecto |
 | **Probabilidad** | Media |
 | **Impacto** | Alto |
 | **Nivel** | Alto |
 | **Tratamiento** | Reducir |
-| **Control Asociado** | Ruta crítica definida en Gantt, buffers entre hitos (HT-003→HT-008) |
+| **Control Asociado** | Ruta crítica definida en Gantt, buffers entre hitos (HT-004→HT-010) |
 | **Responsable** | Líder de Proyecto |
 | **Estado (ROAM)** | Owned |
 
-## **R-04: Sobrecosto por subestimación de tareas de integración con Agentes 2–5**
+## **R-03: Sobrecosto por subestimación de tareas de integración con Agentes 2–5**
 
 | Causa de Origen | Estimación de costos basada en meses-hombre sin contemplar iteraciones adicionales por incompatibilidades de contrato de interfaz entre agentes. |
-| :---- | :---- |
-| **Disparadores** | Valor Ganado (EV) por debajo del Valor Planificado (PV) en más de un 10% durante T-057 a T-063. Retrabajo reportado en pruebas de integración end-to-end (T-062). |
+| :---: | :---- |
+| **Disparadores** | Valor Ganado (EV) por debajo del Valor Planificado (PV) en más de un 10% durante T-070 a T-076. Retrabajo reportado en pruebas de integración end-to-end (T-075). |
 | **Plan de Contingencia** | Utilizar la reserva de contingencia presupuestada. Renegociar alcance de la Fase 9 (Interfaces con Agentes) si el sobrecosto supera la reserva disponible. |
 | **Categoría** | Proyecto |
 | **Probabilidad** | Media |
 | **Impacto** | Medio |
 | **Nivel** | Medio |
-| **Tratamiento** | Aceptar |
-| **Control Asociado** | Reserva de contingencia vía EVM (T-042) |
+| **Tratamiento** | Reducir |
+| **Control Asociado** | Reserva de contingencia vía EVM (T-055) |
 | **Responsable** | Líder de Proyecto |
 | **Estado (ROAM)** | Accepted |
 
-## **R-05: Incremento del costo del hardware especializado (GPU/microprocesador IA) por variaciones del mercado o del tipo de cambio**
-
-| Causa de Origen | El presupuesto de hardware ($3.300 USD) se estimó en un momento puntual sin margen para fluctuaciones de precios internacionales de componentes de IA. |
-| :---- | :---- |
-| **Disparadores** | Cotización de proveedores de GPU/hardware superior a la presupuestada al momento de ejecutar T-026. Alertas del control de costos EVM (T-042) mostrando variación de costos (CV) negativa en la fase de adquisición. |
-| **Plan de Contingencia** | Utilizar la reserva de contingencia presupuestada. Evaluar proveedores alternativos o componentes de especificación equivalente de menor costo. Informar el sobrecosto a los interesados mediante el informe de avance (T-069). |
+## **R-04: Incremento del costo del hardware especializado por variaciones del mercado o del tipo de cambio**
+
+| Causa de Origen | El presupuesto de hardware (\$6.460 USD) se estimó en un momento puntual sin margen para fluctuaciones de precios internacionales de componentes de IA. |
+| :---: | :---- |
+| **Disparadores** | Cotización de proveedores de GPU/hardware superior a la presupuestada al momento de ejecutar T-032. Alertas del control de costos EVM (T-055) mostrando variación de costos (CV) negativa en la fase de adquisición. |
+| **Plan de Contingencia** | Utilizar la reserva de contingencia presupuestada. Evaluar proveedores alternativos o componentes de especificación equivalente de menor costo. Informar el sobrecosto a los interesados mediante el informe de avance (T-082). |
 | **Categoría** | Costos |
 | **Probabilidad** | Media |
 | **Impacto** | Medio |
 | **Nivel** | Medio |
 | **Tratamiento** | Aceptar |
-| **Control Asociado** | Gestión del valor ganado (EVM) y reserva de contingencia (T-042) |
+| **Control Asociado** | Gestión del valor ganado (EVM) y reserva de contingencia (T-055) |
 | **Responsable** | Líder de Proyecto |
 | **Estado (ROAM)** | Accepted |
 
-## **R-06: Identificación incompleta de riesgos emergentes durante las nuevas fases del proyecto**
-
-| Causa de Origen | La matriz de riesgos se definió en la planificación inicial (T-013) sin un proceso periódico de revisión conforme avanzan las fases de implementación. |
-| :---- | :---- |
-| **Disparadores** | Aparición de incidentes o desvíos no contemplados en la matriz vigente durante los hitos HT-003 a HT-010. Retrospectivas Scrum donde el equipo señala riesgos no documentados. |
-| **Plan de Contingencia** | Convocar una revisión extraordinaria de la matriz de riesgos junto al Gestor de Riesgos. Incorporar los riesgos emergentes identificados. Comunicar los cambios al equipo y a los interesados clave. |
-| **Categoría** | Riesgos |
-| **Probabilidad** | Media |
-| **Impacto** | Medio |
-| **Nivel** | Medio |
-| **Tratamiento** | Reducir |
-| **Control Asociado** | Revisión periódica de la matriz de riesgos en reuniones Scrum |
-| **Responsable** | Líder de Proyecto / Gestor de Riesgos |
-| **Estado (ROAM)** | Owned |
-
-## **R-07: Contenido generado que no cumple con la Definición de Terminado (DoD) llega a instancias de validación por falencias en el plan de pruebas**
-
-| Causa de Origen | Cobertura insuficiente de los casos de prueba (CP01-CP22) frente a variantes reales de solicitudes de contenido. |
-| :---- | :---- |
-| **Disparadores** | Reportes del RGC o del Coordinador sobre borradores con errores no detectados previamente en QA. Incremento de solicitudes de corrección (CU09) superior al esperado. |
-| **Plan de Contingencia** | Suspender el paso a validación humana del tipo de contenido afectado. Ampliar el plan de pruebas con los casos no contemplados. Re ejecutar el ciclo de pruebas antes de reactivar el flujo. |
-| **Categoría** | Calidad |
-| **Probabilidad** | Media |
-| **Impacto** | Medio |
-| **Nivel** | Medio |
-| **Tratamiento** | Reducir |
-| **Control Asociado** | DoD y Evidencia Viva (T-015), plan y escenarios de pruebas (T-018) |
-| **Responsable** | Líder de QA |
-| **Estado (ROAM)** | Owned |
-
-## **R-08: Falta de alineación entre los equipos de desarrollo de los distintos agentes por deficiencias en el plan de comunicaciones**
+## **R-05: Falta de alineación entre los equipos de desarrollo de los distintos agentes**
 
 | Causa de Origen | Canales y frecuencia de comunicación entre equipos no formalizados más allá de las reuniones Scrum, replicando el mismo problema de coordinación que motivó al proyecto. |
-| :---- | :---- |
-| **Disparadores** | Decisiones de diseño contradictorias entre equipos detectadas tarde (por ejemplo, durante T-057 análisis de contratos de interfaz). Interesados clave que reportan desconocimiento del estado del proyecto. |
-| **Plan de Contingencia** | Convocar una reunión de sincronización extraordinaria entre líderes de equipo. Reforzar la matriz de interesados y frecuencia de comunicación definida. Emitir un informe de estado extraordinario (similar a T-069). |
+| :---: | :---- |
+| **Disparadores** | Decisiones de diseño contradictorias entre equipos detectadas tarde (por ejemplo, durante T-070 análisis de contratos de interfaz). Interesados clave que reportan desconocimiento del estado del proyecto. |
+| **Plan de Contingencia** | Convocar una reunión de sincronización extraordinaria entre líderes de equipo. Reforzar la matriz de interesados y frecuencia de comunicación definida. Emitir un informe de estado extraordinario. |
 | **Categoría** | Comunicaciones |
 | **Probabilidad** | Media |
 | **Impacto** | Medio |
 | **Nivel** | Medio |
 | **Tratamiento** | Reducir |
-| **Control Asociado** | Plan de gestión de comunicaciones y matriz de interesados (T-016) |
+| **Control Asociado** | Plan de gestión de comunicaciones y matriz de interesados (T-022) |
 | **Responsable** | Líder de Proyecto |
 | **Estado (ROAM)** | Mitigated |
 
-## **R-09: Baja adopción por parte del personal de Extensión (resistencia al cambio, uso ocasional de IA)**
+## **R-06: Baja adopción por parte del personal de Extensión (resistencia al cambio)**
 
 | Causa de Origen | Solo la mitad del personal usa herramientas de IA regularmente; familiarización media con la tecnología según el relevamiento inicial. |
-| :---- | :---- |
-| **Disparadores** | Baja tasa de uso del sistema tras HT-008 (UI desplegada). Encuestas de feedback con señales de insatisfacción o desuso. Borradores acumulados sin validar por más de 48hs. |
-| **Plan de Contingencia** | Reforzar jornadas de capacitación (T-072) con sesiones de seguimiento. Designar un referente interno de acompañamiento. Simplificar el flujo de validación si se identifican fricciones puntuales de usabilidad. |
+| :---: | :---- |
+| **Disparadores** | Baja tasa de uso del sistema tras HT-010 (UI desplegada). Encuestas de feedback con señales de insatisfacción o desuso. Borradores acumulados sin validar por más de 48hs. |
+| **Plan de Contingencia** | Reforzar jornadas de capacitación (T-085) con sesiones de seguimiento. Designar un referente interno de acompañamiento. Simplificar el flujo de validación si se identifican fricciones puntuales de usabilidad. |
 | **Categoría** | Negocio / Adopción |
 | **Probabilidad** | Alta |
 | **Impacto** | Medio |
 | **Nivel** | Alto |
 | **Tratamiento** | Reducir |
-| **Control Asociado** | Capacitaciones (T-072), acompañamiento operativo (T-073) |
+| **Control Asociado** | Capacitaciones (T-085), acompañamiento operativo (T-086) |
 | **Responsable** | Capacitador / Líder de Proyecto |
 | **Estado (ROAM)** | Owned |
 
-## **R-10: Dependencia de licencias/servicios cloud de terceros (Google Workspace, APIs de redes)**
-
-| Causa de Origen | El sistema delega la persistencia de borradores y la publicación final a servicios externos fuera del control directo del equipo. |
-| :---- | :---- |
-| **Disparadores** | Caída reportada del servicio del proveedor. Cambios no anunciados en la API que rompen la integración (breaking changes). |
-| **Plan de Contingencia** | Activar canal de publicación alternativo o diferir la publicación programada hasta restablecer el servicio. Notificar al Coordinador de Extensión del retraso. Revisar cláusulas de SLA con el proveedor. |
-| **Categoría** | Proveedores |
-| **Probabilidad** | Media |
-| **Impacto** | Medio |
-| **Nivel** | Medio |
-| **Tratamiento** | Aceptar |
-| **Control Asociado** | Cláusulas contractuales de disponibilidad (SLA) |
-| **Responsable** | Líder de Proyecto |
-| **Estado (ROAM)** | Accepted |
-
-## **R-11: Demora en la adquisición de infraestructura cloud, servidores o licencias necesarias para el desarrollo (Procurement Delay)**
+## **R-07: Demora en la adquisición de infraestructura cloud, servidores o licencias necesarias para el desarrollo**
 
 | Causa de Origen | Proceso de compra institucional sujeto a trámites administrativos de la FIE con tiempos no controlados directamente por el equipo de proyecto. |
-| :---- | :---- |
-| **Disparadores** | Desvío de la tarea T-026 (Adquirir infraestructura cloud, servidores y licencias) respecto a la fecha planificada en el Gantt. Hito HT-001 (Estructura Base en Google Workspace) en riesgo de no cumplirse a tiempo. |
-| **Plan de Contingencia** | Escalar el trámite de compra ante la Facultad. Evaluar alternativas temporales de menor costo (por ejemplo. Entornos de prueba en la nube) mientras se concreta la adquisición definitiva. Ajustar el cronograma de las fases dependientes. |
+| :---: | :---- |
+| **Disparadores** | Desvío de la tarea T-032 (Adquirir infraestructura cloud, servidores y licencias) respecto a la fecha planificada en el Gantt. Hito HT-002 (Estructura Base en Google Workspace) en riesgo de no cumplirse a tiempo. |
+| **Plan de Contingencia** | Escalar el trámite de compra ante la Facultad. Evaluar alternativas temporales de menor costo (por ejemplo, entornos de prueba en la nube) mientras se concreta la adquisición definitiva. Ajustar el cronograma de las fases dependientes. |
 | **Categoría** | Adquisiciones |
 | **Probabilidad** | Media |
 | **Impacto** | Medio |
```

```diff
@@ -2967,72 +2980,42 @@
 | **Responsable** | Líder de Proyecto |
 | **Estado (ROAM)** | Accepted |
 
-## **R-12: Rotación o indisponibilidad de estudiantes de 4° y 5° año que integran el equipo de desarrollo**
-
-| Causa de Origen | El equipo depende de recursos humanos con obligaciones académicas paralelas (cursada, exámenes), sin roles de respaldo definidos para tareas críticas. |
-| :---- | :---- |
-| **Disparadores** | Ausencias prolongadas o abandono de un integrante durante períodos de exámenes. Tareas de la ruta crítica sin responsable disponible. |
-| **Plan de Contingencia** | Activar el plan de incorporación (T-008) para reasignar o sumar un reemplazo. Redistribuir temporalmente las tareas críticas entre el resto del equipo. Documentar el conocimiento perdido mediante el manual operativo (T-070). |
-| **Categoría** | Recursos Humanos |
-| **Probabilidad** | Alta |
-| **Impacto** | Medio |
-| **Nivel** | Alto |
-| **Tratamiento** | Reducir |
-| **Control Asociado** | Plan de incorporación y organigrama del equipo (T-008) |
-| **Responsable** | Líder de Proyecto / Gestión de RRHH |
-| **Estado (ROAM)** | Owned |
-
-## **R-13: Personal inadecuado o con perfil insuficiente para las tecnologías críticas del proyecto (LLMs locales, seguridad de agentes, arquitectura multiagente)**
+## **R-08: Personal inadecuado o con perfil insuficiente para las tecnologías críticas del proyecto**
 
 | Causa de Origen | El equipo está compuesto mayormente por estudiantes de grado sin experiencia previa en modelos de IA generativa, arquitecturas multiagente o ciberseguridad de agentes (NHI, prompt injection); los roles se definieron más por disponibilidad que por especialización. |
-| :---- | :---- |
-| **Disparadores** | Retrabajo recurrente en las tareas de IA (T-031 a T-036) o de seguridad (T-022 a T-024). Estimaciones de esfuerzo superadas de forma sistemática en dichas tareas. |
+| :---: | :---- |
+| **Disparadores** | Retrabajo recurrente en las tareas de IA (T-037 a T-042) o de seguridad (T-028 a T-030). Estimaciones de esfuerzo superadas de forma sistemática en dichas tareas. |
 | **Plan de Contingencia** | Reforzar la capacitación específica del equipo asignado a las tareas críticas. Incorporar mentoría del profesor/tutor o de un especialista externo puntual. Redistribuir tareas críticas hacia los integrantes con mayor afinidad demostrada. |
 | **Categoría** | Recursos Humanos |
 | **Probabilidad** | Media |
 | **Impacto** | Alto |
 | **Nivel** | Alto |
 | **Tratamiento** | Reducir |
-| **Control Asociado** | Plan de incorporación y organigrama del equipo (T-008), capacitación interna (T-056) |
+| **Control Asociado** | Plan de incorporación y organigrama del equipo (T-008), capacitación interna (T-069) |
 | **Responsable** | Líder de Proyecto / Gestión de RRHH |
 | **Estado (ROAM)** | Owned |
 
-## **R-14: Elaboración excesiva de requisitos y documentación de diseño más allá de lo necesario para el MVP (gold plating)**
-
-| Causa de Origen | La cantidad de diagramas UML, escenarios de prueba y artefactos definidos en la etapa de planificación (T-017, T-018) supera lo estrictamente necesario para validar el alcance mínimo viable del agente. |
-| :---- | :---- |
-| **Disparadores** | Tiempo dedicado a documentación y diagramas superior al estimado en el Gantt sin avance proporcional en el desarrollo. Retrasos detectados antes de HT-000. |
-| **Plan de Contingencia** | Priorizar los requisitos y diagramas imprescindibles para el MVP. Diferir el detalle de artefactos secundarios a iteraciones posteriores. Validar con el profesor/director el nivel de detalle realmente requerido. |
-| **Categoría** | Alcance |
-| **Probabilidad** | Baja |
-| **Impacto** | Medio |
-| **Nivel** | Bajo |
-| **Tratamiento** | Aceptar |
-| **Control Asociado** | Validación del documento de desarrollo con el director del proyecto (T-019) |
-| **Responsable** | Líder de Proyecto / Analista Funcional |
-| **Estado (ROAM)** | Accepted |
-
-## **R-15: Cronograma de 24 meses o presupuesto total ($260.850 USD) subestimados frente a la complejidad real del sistema multiagente**
+## **R-09: Cronograma o presupuesto total subestimados frente a la complejidad real del sistema multiagente**
 
 | Causa de Origen | La estimación de tiempos y costos (T-006, T-009 a T-011) se realizó en la etapa de planificación inicial sin contar aún con un prototipo funcional del motor de IA que validara los tiempos reales de desarrollo. |
-| :---- | :---- |
-| **Disparadores** | Valor Ganado (EV) sistemáticamente por debajo del Valor Planificado (PV) en varias fases consecutivas. Hitos tempranos (HT-001 a HT-003) con atrasos acumulados. |
-| **Plan de Contingencia** | Revisar la línea base de costos y cronograma con datos reales de las primeras fases. Ajustar el presupuesto o alcance de fases posteriores. Informar el desvío a los interesados clave mediante el informe de avance (T-069). |
+| :---: | :---- |
+| **Disparadores** | Valor Ganado (EV) sistemáticamente por debajo del Valor Planificado (PV) en varias fases consecutivas. Hitos tempranos (HT-002 a HT-004) con atrasos acumulados. |
+| **Plan de Contingencia** | Revisar la línea base de costos y cronograma con datos reales de las primeras fases. Ajustar el presupuesto o alcance de fases posteriores. Informar el desvío a los interesados clave mediante el informe de avance (T-082). |
 | **Categoría** | Proyecto |
 | **Probabilidad** | Media |
 | **Impacto** | Alto |
 | **Nivel** | Alto |
 | **Tratamiento** | Reducir |
-| **Control Asociado** | Línea base de costos y cronograma (T-006, T-011), gestión del valor ganado (T-042) |
+| **Control Asociado** | Línea base de costos y cronograma (T-006, T-011), gestión del valor ganado (T-055) |
 | **Responsable** | Líder de Proyecto |
 | **Estado (ROAM)** | Owned |
 
-## **R-16: Diseño de clases y componentes aún no validado oficialmente que resulte inadecuado para la implementación real**
+## **R-10: Diseño de clases y componentes aún no validado oficialmente que resulte inadecuado para la implementación real**
 
 | Causa de Origen | El propio documento de diseño advierte que el diagrama de clases y de componentes está sujeto a modificaciones constantes y no debe considerarse definitivo hasta su validación oficial. |
-| :---- | :---- |
-| **Disparadores** | Cambios frecuentes solicitados sobre el diagrama de clases durante el desarrollo (T-023, T-033). Incompatibilidades detectadas entre el diseño de clases y el motor de IA o el modelo de datos real. |
-| **Plan de Contingencia** | Congelar una versión validada del diseño antes de iniciar el desarrollo de cada fase (HT-002 a HT-004). Documentar y versionar los cambios de diseño. Revalidar con el Arquitecto de Software antes de propagar cambios a otras fases. |
+| :---: | :---- |
+| **Disparadores** | Cambios frecuentes solicitados sobre el diagrama de clases durante el desarrollo (T-029, T-039). Incompatibilidades detectadas entre el diseño de clases y el motor de IA o el modelo de datos real. |
+| **Plan de Contingencia** | Congelar una versión validada del diseño antes de iniciar el desarrollo de cada fase (HT-003 a HT-005). Documentar y versionar los cambios de diseño. Revalidar con el Arquitecto de Software antes de propagar cambios a otras fases. |
 | **Categoría** | Diseño |
 | **Probabilidad** | Media |
 | **Impacto** | Alto |
```

```diff
@@ -3042,100 +3025,57 @@
 | **Responsable** | Arquitecto de Software / Diseñador de Sistemas |
 | **Estado (ROAM)** | Owned |
 
-## **R-17: Inmadurez del proceso de desarrollo y del ambiente de trabajo compartido entre los múltiples equipos de agentes (Scrum multi-equipo, Google Workspace, Jira)**
-
-| Causa de Origen | Es la primera implementación conjunta de Scrum coordinando múltiples equipos independientes (uno por agente) sobre una infraestructura compartida (Google Workspace, base de datos, colas Redis) sin experiencia previa del grupo en proyectos de esta escala. |
-| :---- | :---- |
-| **Disparadores** | Conflictos de acceso o permisos en la Estructura Base de Google Workspace (HT-001). Retrasos en las ceremonias Scrum o falta de sincronización entre sprints de distintos equipos. |
-| **Plan de Contingencia** | Definir con mayor detalle las convenciones de trabajo compartido (permisos. Nomenclatura) antes de HT-001. Reforzar las reuniones de sincronización entre equipos. Ajustar el proceso Scrum según las lecciones aprendidas de los primeros sprints. |
-| **Categoría** | Proceso |
-| **Probabilidad** | Media |
-| **Impacto** | Medio |
-| **Nivel** | Medio |
-| **Tratamiento** | Reducir |
-| **Control Asociado** | Estructura base en Google Workspace (T-021 a T-023), reuniones Scrum periódicas |
-| **Responsable** | Líder de Proyecto |
-| **Estado (ROAM)** | Mitigated |
-
-## **R-18: Adopción de tecnologías de IA generativa local (Ollama, RAG, prompt engineering) nuevas para el equipo de desarrollo**
+## **R-11: Retrasos o resultados de precisión insuficientes en el motor de IA por la falta de experiencia previa del equipo con tecnologías de IA generativa local**
 
 | Causa de Origen | Ausencia de experiencia previa del equipo con modelos de inferencia local (Llama 3/Mistral), arquitecturas RAG y técnicas de prompt engineering aplicadas a un caso institucional real. |
-| :---- | :---- |
-| **Disparadores** | Tiempos de configuración del motor de IA (T-032 a T-036) superiores a los estimados. Resultados de precisión del motor por debajo de lo esperado en las primeras pruebas (T-036). |
+| :---: | :---- |
+| **Disparadores** | Tiempos de configuración del motor de IA (T-038 a T-042) superiores a los estimados. Resultados de precisión del motor por debajo de lo esperado en las primeras pruebas (T-042). |
 | **Plan de Contingencia** | Destinar tiempo adicional de capacitación e investigación previa a la configuración definitiva del motor. Apoyarse en documentación oficial y comunidades de Ollama/Llama. Realizar pruebas de concepto acotadas antes de integrar el motor al flujo completo. |
 | **Categoría** | Técnico |
 | **Probabilidad** | Alta |
 | **Impacto** | Medio |
 | **Nivel** | Alto |
 | **Tratamiento** | Reducir |
-| **Control Asociado** | Prototipo de generación de contenido y validación de precisión (T-035, T-036) |
+| **Control Asociado** | Prototipo de generación de contenido y validación de precisión (T-041, T-042) |
 | **Responsable** | Especialista en IA |
 | **Estado (ROAM)** | Owned |
 
-## **R-19: Expectativa de que el motor de IA resuelva por sí solo la generación de contenido sin controles ni supervisión humana adecuados (falsa sensación de solución mágica)**
-
-| Causa de Origen | Sobreestimación de la capacidad del modelo local de IA para reemplazar el criterio humano, subestimando la necesidad real del esquema Human-in-the-Loop definido en el proyecto. |
-| :---- | :---- |
-| **Disparadores** | Interesados o usuarios que solicitan reducir o eliminar las instancias de validación humana (CU10) esperando que el bot opere de forma completamente autónoma. Borradores aprobados sin revisión adecuada. |
-| **Plan de Contingencia** | Reforzar en la capacitación (T-072) y en la documentación (T-070) que el sistema requiere validación humana obligatoria. Comunicar explícitamente a los interesados las limitaciones reales del motor de IA local. |
-| **Categoría** | Negocio / Adopción |
-| **Probabilidad** | Baja |
-| **Impacto** | Medio |
-| **Nivel** | Bajo |
-| **Tratamiento** | Aceptar |
-| **Control Asociado** | Esquema Human-in-the-Loop obligatorio (CU10), manual operativo (T-070) |
-| **Responsable** | Analista Funcional / Líder de Proyecto |
-| **Estado (ROAM)** | Accepted |
-
-## **R-20: Demora en poner el sistema operativo frente a las necesidades actuales de la Secretaría de Extensión, perdiendo vigencia u oportunidad frente al problema original**
+## **R-12: Demora en poner el sistema operativo frente a las necesidades actuales de la Secretaría de Extensión**
 
 | Causa de Origen | El cronograma se extiende a 24 meses mientras las tareas manuales que el sistema busca automatizar continúan generando sobrecarga al personal de Extensión durante todo ese período. |
-| :---- | :---- |
-| **Disparadores** | Reclamos del personal de Extensión sobre la persistencia de tareas manuales antes de HT-010. Desvíos del cronograma que posterguen aún más la puesta en operación. |
-| **Plan de Contingencia** | Priorizar la entrega de un subconjunto funcional útil (por ejemplo. Generación de gacetillas y certificados) en una fase temprana (HT-006) para entregar valor antes de completar el sistema completo. Comunicar avances parciales a la Secretaría. |
+| :---: | :---- |
+| **Disparadores** | Reclamos del personal de Extensión sobre la persistencia de tareas manuales antes de HT-012. Desvíos del cronograma que posterguen aún más la puesta en operación. |
+| **Plan de Contingencia** | Priorizar la entrega de un subconjunto funcional útil (por ejemplo, generación de gacetillas y certificados) en una fase temprana (HT-008) para entregar valor antes de completar el sistema completo. Comunicar avances parciales a la Secretaría. |
 | **Categoría** | Negocio / Adopción |
 | **Probabilidad** | Media |
 | **Impacto** | Medio |
 | **Nivel** | Medio |
 | **Tratamiento** | Reducir |
-| **Control Asociado** | Entrega incremental por hitos (HT-000 a HT-011) |
+| **Control Asociado** | Entrega incremental por hitos (HT-001 a HT-014) |
 | **Responsable** | Líder de Proyecto |
-| **Estado (ROAM)** | Mitigated |
-
-## **R-21: Dificultad para conseguir el respaldo institucional necesario para escalar ExtensiónBot al resto de la Facultad en el marco del Plan de escalabilidad hacia el Centenario**
-
-| Causa de Origen | La continuidad del proyecto más allá del piloto depende de que otras áreas de la FIE (más allá de Extensión) perciban valor suficiente en el sistema como para destinar presupuesto e infraestructura adicionales. |
-| :---- | :---- |
-| **Disparadores** | Baja participación de otras áreas en la evaluación de impacto institucional (meses 19 a 24 del cronograma). Falta de aprobación presupuestaria para la fase de escalabilidad. |
-| **Plan de Contingencia** | Presentar resultados concretos y medibles del piloto (evaluación de impacto institucional) a las autoridades de la FIE. Involucrar tempranamente a otras áreas potencialmente beneficiadas en la fase de evaluación. |
-| **Categoría** | Negocio / Adopción |
-| **Probabilidad** | Media |
-| **Impacto** | Medio |
-| **Nivel** | Medio |
-| **Tratamiento** | Aceptar |
-| **Control Asociado** | Evaluación de impacto institucional planificada en el cronograma |
-| **Responsable** | Líder de Proyecto |
-| **Estado (ROAM)** | Accepted |
-
-## **R-22: Falta de apoyo político/institucional sostenido de las autoridades de la FIE para la continuidad presupuestaria del proyecto**
+| **Estado (ROAM)** | Owned |
+
+## 
+
+## **R-14: Falta de apoyo sostenido de las autoridades de la FIE para la continuidad presupuestaria del proyecto**
 
 | Causa de Origen | El financiamiento del proyecto depende de la inversión que realice la FIE de acuerdo a su presupuesto institucional, sujeta a prioridades cambiantes de la conducción de la Facultad. |
-| :---- | :---- |
+| :---: | :---- |
 | **Disparadores** | Recortes o demoras presupuestarias no vinculadas al desempeño del proyecto. Cambios de autoridades o prioridades institucionales durante los 24 meses de desarrollo. |
-| **Plan de Contingencia** | Mantener informadas a las autoridades mediante los informes de avance periódicos (T-069). Asociar los entregables del proyecto a objetivos institucionales visibles (por ejemplo. El Centenario). Buscar el respaldo formal de la conducción antes de cada hito presupuestario relevante. |
+| **Plan de Contingencia** | Mantener informadas a las autoridades mediante los informes de avance periódicos (T-082). Asociar los entregables del proyecto a objetivos institucionales visibles (por ejemplo, el Centenario). Buscar el respaldo formal de la conducción antes de cada hito presupuestario relevante. |
 | **Categoría** | Negocio / Adopción |
 | **Probabilidad** | Baja |
 | **Impacto** | Alto |
 | **Nivel** | Medio |
 | **Tratamiento** | Aceptar |
-| **Control Asociado** | Informes de avance periódicos a interesados clave (T-069) |
+| **Control Asociado** | Informes de avance periódicos a interesados clave (T-082) |
 | **Responsable** | Líder de Proyecto |
 | **Estado (ROAM)** | Accepted |
 
-## **R-23: Suplantación de identidad de ExtensiónBot para acceder a APIs internas (Spoofing)**
+## **R-15: Suplantación de identidad de ExtensiónBot para acceder a APIs internas (Spoofing)**
 
 | Causa de Origen | Ausencia de identidad de máquina única por agente; uso de credenciales compartidas entre servicios. |
-| :---- | :---- |
+| :---: | :---- |
 | **Disparadores** | Detección de llamadas a API desde IPs o certificados no reconocidos. Alertas de mTLS por certificado inválido o expirado. |
 | **Plan de Contingencia** | Revocar inmediatamente el certificado comprometido. Rotar credenciales de todos los agentes relacionados. Activar Kill Switch del agente afectado y auditar logs de las últimas 24hs para descartar acciones no autorizadas ya ejecutadas. |
 | **Categoría** | Seguridad |
```

```diff
@@ -3145,12 +3085,12 @@
 | **Tratamiento** | Reducir |
 | **Control Asociado** | Aplicar mTLS y tokens de corta duración (NHI) |
 | **Responsable** | Especialista en Ciberseguridad |
-| **Estado (ROAM)** | Mitigated |
-
-## **R-24: Inyección de prompts indirecta vía RAG/Repositorio Institucional que altera instrucciones (Tampering)**
+| **Estado (ROAM)** | Owned |
+
+## **R-16: Inyección de prompts indirecta vía RAG/Repositorio Institucional que altera instrucciones (Tampering)**
 
 | Causa de Origen | Falta de separación estricta entre el plano de control (prompt del sistema) y el plano de datos (contenido recuperado del repositorio). |
-| :---- | :---- |
+| :---: | :---- |
 | **Disparadores** | Respuestas del agente con contenido fuera de su alcance funcional. Fallos en aserciones de Promptfoo/Garak durante CI/CD. Usuarios validadores reportan contenido incoherente o con instrucciones extrañas. |
 | **Plan de Contingencia** | Bloquear la fuente de datos contaminada en el Repositorio Institucional. Revertir a la última versión validada de la plantilla/documento. Ejecutar un ciclo completo de Prompt Security Testing antes de reactivar la fuente. Notificar al RGC y Coordinador de los borradores afectados en curso. |
 | **Categoría** | Seguridad |
```

```diff
@@ -3162,10 +3102,10 @@
 | **Responsable** | Arquitecto de Software |
 | **Estado (ROAM)** | Owned |
 
-## **R-25: Imposibilidad de determinar si una acción dañina fue error de lógica o ataque (Repudiation)**
+## **R-17: Imposibilidad de determinar si una acción dañina fue error de lógica o ataque (Repudiation)**
 
 | Causa de Origen | Logs insuficientemente detallados o no vinculados criptográficamente al estado del agente en el momento de la acción. |
-| :---- | :---- |
+| :---: | :---- |
 | **Disparadores** | Reporte de un usuario sobre contenido publicado que nadie aprobó. Discrepancia entre el estado registrado en base de datos y el contenido real difundido. |
 | **Plan de Contingencia** | Congelar el log inmutable del período en cuestión. Reconstruir la cadena de decisiones (prompt original → decisión → acción) con el ledger WORM. Escalar a Responsable Técnico y Líder de QA para peritaje interno. |
 | **Categoría** | Seguridad |
```

```diff
@@ -3175,12 +3115,12 @@
 | **Tratamiento** | Reducir |
 | **Control Asociado** | Logs inmutables con hash de estado (WORM) |
 | **Responsable** | DBA / Especialista en Ciberseguridad |
-| **Estado (ROAM)** | Mitigated |
-
-## **R-26: Fuga de datos confidenciales o PII en una respuesta generada (Information Disclosure)**
+| **Estado (ROAM)** | Owned |
+
+## **R-18: Fuga de datos confidenciales o PII en una respuesta generada (Information Disclosure)**
 
 | Causa de Origen | Filtros de salida (Regex/NER) incompletos o desactualizados frente a nuevos formatos de datos sensibles. |
-| :---- | :---- |
+| :---: | :---- |
 | **Disparadores** | Alertas del clasificador de salida. Auditoría detecta PII en un borrador persistido en Google Drive/Gmail. Reporte de RGC durante validación semántica. |
 | **Plan de Contingencia** | Eliminar o poner en cuarentena el borrador afectado. Notificar al responsable de datos personales de la Facultad. Revisar y actualizar reglas de anonimización. Re-ejecutar el borrador desde cero con los filtros corregidos. |
 | **Categoría** | Seguridad |
```

```diff
@@ -3192,10 +3132,10 @@
 | **Responsable** | Especialista en IA |
 | **Estado (ROAM)** | Owned |
 
-## **R-27: Agente engañado para ejecutar acción fuera de su autorización (Elevation of Privilege)**
+## **R-19: Agente engañado para ejecutar acción fuera de su autorización (Elevation of Privilege)**
 
 | Causa de Origen | Falta de autorización dual (usuario \+ agente) en las APIs de destino; agente con permisos de escritura directa en base de datos. |
-| :---- | :---- |
+| :---: | :---- |
 | **Disparadores** | Intento de mutación de datos bloqueado por ABAC pero registrado en logs. Patrón de solicitudes que buscan reiteradamente acciones de alto riesgo. |
 | **Plan de Contingencia** | Bloquear temporalmente al agente mediante Kill Switch. Revisar el esquema ABAC del rol involucrado. Auditar si hubo ejecución efectiva antes del bloqueo del permiso. |
 | **Categoría** | Seguridad |
```

```diff
@@ -3207,10 +3147,10 @@
 | **Responsable** | Especialista en Ciberseguridad |
 | **Estado (ROAM)** | Owned |
 
-## **R-28: Falla de integridad en datos de entrenamiento/RAG (Data Poisoning)**
+## **R-20: Falla de integridad en datos de entrenamiento/RAG (Data Poisoning)**
 
 | Causa de Origen | Ausencia de verificación de procedencia y hash de integridad en los documentos ingeridos por el Repositorio Institucional. |
-| :---- | :---- |
+| :---: | :---- |
 | **Disparadores** | Contenido generado con datos inconsistentes con la fuente oficial. Discrepancia detectada en auditoría de las referencias consultadas por el agente. |
 | **Plan de Contingencia** | Aislar y remover la fuente de datos sospechosa del repositorio. Restaurar desde el último snapshot validado. Ejecutar Model Integrity Check sobre embeddings afectados. |
 | **Categoría** | Seguridad |
```

```diff
@@ -3220,27 +3160,12 @@
 | **Tratamiento** | Reducir |
 | **Control Asociado** | Verificación de procedencia de fuentes RAG |
 | **Responsable** | Ingeniero de Datos |
-| **Estado (ROAM)** | Mitigated |
-
-## **R-29: Credenciales de API hardcodeadas o compartidas entre desarrolladores**
-
-| Causa de Origen | Falta de adopción temprana de bóveda de secretos (Vault) durante el desarrollo inicial del backend. |
-| :---- | :---- |
-| **Disparadores** | Alertas de Secret Scanning (TruffleHog/GitGuardian) en Pull Requests. Hallazgo de claves en commits históricos del repositorio. |
-| **Plan de Contingencia** | Revocar y rotar inmediatamente la credencial expuesta. Purgar el historial de Git si es necesario. Migrar la inyección de secretos a HashiCorp Vault en el entorno afectado. |
-| **Categoría** | Seguridad |
-| **Probabilidad** | Media |
-| **Impacto** | Alto |
-| **Nivel** | Alto |
-| **Tratamiento** | Reducir |
-| **Control Asociado** | Secretos dinámicos (HashiCorp Vault), Secret Scanning en CI |
-| **Responsable** | Desarrollador Backend |
 | **Estado (ROAM)** | Owned |
 
-## **R-30: Saturación del agente por ráfaga de solicitudes agotando ventana de contexto (Denial of Service)**
+## **R-20: Saturación del agente por ráfaga de solicitudes agotando ventana de contexto (Denial of Service)**
 
 | Causa de Origen | Ausencia de límites de tasa (rate limiting) o cuotas de tokens configuradas a nivel de API Gateway. |
-| :---- | :---- |
+| :---: | :---- |
 | **Disparadores** | Cola de Redis con crecimiento sostenido sin drenar. Uso de CPU/RAM del servidor Ollama por encima del 90% sostenido. Timeouts reportados en CP09. |
 | **Plan de Contingencia** | Activar rate limiting de emergencia. Escalar solicitudes en cola a procesamiento diferido. Notificar a Apps Script para pausar el disparo de nuevas entradas hasta normalizar consumo. |
 | **Categoría** | Seguridad / Infraestructura |
```

```diff
@@ -3250,24 +3175,83 @@
 | **Tratamiento** | Reducir |
 | **Control Asociado** | Rate limiting, cola Redis y Celery, token-bucket |
 | **Responsable** | Desarrollador Backend |
-| **Estado (ROAM)** | Mitigated |
-
-## **R-31: Caída o inestabilidad del modelo local Ollama (timeout, falta de GPU)**
-
-| Causa de Origen | Hardware local con capacidad limitada (RAM/GPU) frente a picos de demanda concurrente. |
-| :---- | :---- |
-| **Disparadores** | Timeouts reiterados en la generación de contenido. Alertas de monitoreo de infraestructura sobre uso de GPU/RAM. |
-| **Plan de Contingencia** | Reintentar la solicitud con backoff exponencial. Notificar al Responsable Técnico. Mantener la petición en cola sin pérdida de datos (CP09). Evaluar escalado vertical de hardware si la falla es recurrente. |
-| **Categoría** | Técnico / Infraestructura |
-| **Probabilidad** | Media |
-| **Impacto** | Medio |
-| **Nivel** | Medio |
-| **Tratamiento** | Reducir |
-| **Control Asociado** | Reintentos, notificación a Responsable Técnico, fallback (CP09) |
-| **Responsable** | Especialista en IA |
-| **Estado (ROAM)** | Mitigated |
-
-# **Agente 2 \- Notas**
+| **Estado (ROAM)** | Owned |
+
+# Administración de Calidad
+
+## **Modelo Adoptado**
+
+Se optó por implementar, junto a **PMBOK** como modelo general, el modelo de **CMMI-DEV**  para la Administración de Calidad, ya que es una variante dedicada al desarrollo de software del reconocido modelo Capability Maturity Model Integration (CMMI) y este a su vez es adecuado para proyectos multi-equipo de más de 25 personas que requieren coordinación de procesos entre distintos grupos de desarrollo.
+
+El plan de Administración de Calidad presentado buscará asegurar el alcance del nivel de madurez organizacional 2, **Gestionado**.
+
+## 
+
+## **Áreas de Proceso Aplicadas**
+
+CMMI-DEV propone áreas de procesos y categorías que las agrupan.  
+En la siguiente tabla se muestran dichas categorías y las decisiones tomadas en el proyecto para cubrir la calidad de las mismas:
+
+| Categoría | Área de Proceso | Aplicación en el proyecto |
+| :---: | ----- | ----- |
+| ***Gestión de Procesos*** | OPF – Organizational Process Focus | Lecciones aprendidas (T-088, T-089) |
+|  | OT – Organizational Training | Capacitación interna del equipo (T-069) Capacitación de usuarios (T-085) |
+| ***Gestión de Proyectos*** | PP – Planificación de Proyectos | EDT/WBS Cronograma Estimación de costos (T-004 a T-011) |
+|  | PMC – Monitoreo y Control | Gestión del Valor Ganado (EVM) Revisión de avance (T-055, T-082) |
+|  | IPM – Gestión Integrada | Coordinación entre los equipos de desarrollo de los 5 agentes |
+|  | RSKM – Gestión de Riesgos | Matriz de Riesgos Ciclo ROAM (T-013 a T-020, T-043 a T-048) |
+| ***Ingeniería*** | REQM – Gestión de Requisitos | Requisitos Funcionales/No Funcionales Casos de Uso Casos de Prueba |
+|  | RD – Desarrollo de Requisitos | Relevamiento de necesidades (T-000) Modelo de negocio y dominio |
+|  | TS – Solución Técnica | Diseño de clases Diagrama de componentes Selección del motor de IA (T-023, T-037–T-042) |
+|  | PI – Integración de Producto | Desarrollo de interfaces con Agentes 2–5 (T-070 a T-076) |
+|  | VER – Verificación | Plan de Pruebas Unitarias |
+|  | VAL – Validación | Escenarios de Prueba Reuniones con Secretaría Académica |
+| ***Soporte*** | CM – Gestión de Configuración | Versionado de diagramas UML Diseño de interfaces con Agentes 2–5 |
+|  | PPQA – Aseguramiento de Calidad de Procesos y Productos | Revisiones regulares en cada Sprint |
+|  | MA – Medición y Análisis | Métricas de calidad de producto y proceso |
+|  | DAR – Análisis de Decisiones | Documento del Proyecto |
+
+## 
+
+## **Definición de Roles y Responsabilidades de Calidad**
+
+En la siguiente tabla se listan los roles y sus responsabilidades referentes a la administración de calidad:
+
+| Rol | Responsabilidad principal |
+| :---: | ----- |
+| ***Líder de QA*** | Define el DoD, el plan y escenarios de prueba (T-021, T-024); aprueba el cierre de cada hito de calidad |
+| ***Analista de QA*** | Ejecuta validaciones de usabilidad, flujo y trazabilidad (T-036, T-042, T-053, T-060, T-068, T-081) |
+| ***QA Tester*** | Ejecuta los casos de prueba (CP01–CP22) y registra resultados en el Plan de Pruebas |
+| ***Especialista en Ciberseguridad*** | Valida controles de seguridad asociados a riesgos críticos (RBAC, prompt injection, PII) |
+| ***Arquitecto de Software*** | Valida oficialmente los diagramas UML antes de que sean tomados como base de desarrollo |
+| ***Gestor de Riesgos*** | Articula el tratamiento de riesgos de calidad con el ciclo ROAM |
+| ***Líder de Proyecto*** | Aprueba desviaciones de alcance/cronograma que impacten el DoD |
+
+## **Definition of Done (DoD)**
+
+Además de comprender la [DoD global](), se considera específicamente que un agregado a ExtensiónBot está terminado cuando cumple con las siguientes condiciones:
+
+1. Cumple los requisitos funcionales o no funcionales que le dieron origen.  
+2. Superó los [casos de prueba unitarios](#plan-de-pruebas-unitarias) correspondientes (CP01–CP22) sin excepciones no resueltas.  
+3. En caso de ser contenido generado, superó la doble validación humana (CU10).  
+4. Generó su log de auditoría correspondiente (CU06).  
+5. No introduce ni reactiva ningún riesgo de nivel Alto/Crítico sin su plan de contingencia definido en la sección de Administración de Riesgo.  
+6. Fue revisado por un par o por el Arquitecto de Software.
+
+## 
+
+## **Métricas de calidad de producto y proceso**
+
+Se han establecido las siguientes métricas para evaluar y controlar la calidad del proyecto:
+
+| Métrica | Fuente | Meta / Umbral Objetivo | Control | Responsable |
+| :---: | ----- | ----- | ----- | ----- |
+| ***Tiempo de generación de contenido*** | Logs del motor de IA | \< 30 segundos (RNF-1) | Continuo (en cada solicitud) |  |
+| ***Disponibilidad del sistema*** | Monitoreo de infraestructura | ≥ 99% (RNF-8) | Mensual |  |
+| ***% de Casos de Prueba exitosos por etapa*** | Plan de Pruebas Unitarias | 100% antes de cerrar el hito correspondiente | Por hito |  |
+| ***% de Escenarios de Prueba exitosos*** | Escenarios de Prueba | 100% antes de HT-012 (Publicación en canales de difusión) | Semanal |  |
+| ***Desviación de cronograma y costo*** | Aplicación de Earned Value Management (T-055) | Dentro de la reserva de contingencia y duración total del proyecto | Mensual |  |
+| ***Adopción por parte del personal de Extensión*** | Encuestas, registros de uso del sistema | Sin acumulación de borradores \> 48hs sin validar (control de R-06) | Luego del HT-010 |  |
 
 Como Diseñador del Sistema de Agentes Inteligentes, tras revisar las notas y especificaciones técnicas de los agentes del Proyecto Centenario, he identificado los siguientes aspectos clave que deben incorporarse para clarificar alcances, interacciones y datos de procesos en sus respectivos documentos:
 
```

```diff
@@ -3411,8 +3395,6 @@
 
 En resumen, Ollama provee la **"inteligencia" local** que transforma los documentos estáticos del repositorio en contenidos dinámicos y útiles para la comunicación de la Facultad.
 
-# **Agente 3 \- Notas**
-
 Como Diseñador del Sistema de Agentes Inteligentes, tras revisar las notas y especificaciones técnicas de los agentes del Proyecto Centenario, he identificado los siguientes aspectos clave que deben incorporarse para clarificar alcances, interacciones y datos de procesos en sus respectivos documentos:
 
 ### **Agente 3: Vinculación y Congresos**
```

```diff
@@ -3455,8 +3437,6 @@
 ### **Resumen de Orquestación**
 
 Técnicamente, estas conexiones se materializan mediante un **modelo híbrido basado en eventos**. El Agente 3 monitorea fuentes, genera oportunidades y las registra en un bus de datos centralizado (Google Sheets), permitiendo que la Secretaría de Extensión funcione como una organización basada en datos donde la vinculación alimenta sistemáticamente la oferta académica y los eventos institucionales.
-
-# **Agente 4- Notas**
 
 Como Diseñador del Sistema de Agentes Inteligentes, tras revisar las notas y especificaciones técnicas de los agentes del Proyecto Centenario, he identificado los siguientes aspectos clave que deben incorporarse para clarificar alcances, interacciones y datos de procesos en sus respectivos documentos:
 
```

```diff
@@ -3503,8 +3483,6 @@
 ### **4\. Presupuesto y Sostenibilidad**
 
 Dado que esta funcionalidad depende de servicios externos, el proyecto prevé una erogación presupuestaria específica en el Año 2 para el mantenimiento de la **WhatsApp Business API**, estimada entre **USD 120 y USD 300 anuales**. Este costo se considera una inversión estratégica para alcanzar el nivel de madurez tecnológica **TRL 5-6**, validando el sistema en un entorno operativo real con usuarios externos.
-
-# **Agente 5 \- Notas**
 
 Como Diseñador del Sistema de Agentes Inteligentes, tras revisar las notas y especificaciones técnicas de los agentes del Proyecto Centenario, he identificado los siguientes aspectos clave que deben incorporarse para clarificar alcances, interacciones y datos de procesos en sus respectivos documentos:
 
```

```diff
@@ -3655,29 +3633,25 @@
 
 \--------------------------------------------------------------------------------------------------------------------------
 
-# **PROYECTO**
-
-# **Ciberseguridad desde el Principio**
-
 # **Política de seguridad del Proyecto Centenario**
 
 De manera **radical**, como una impronta **distintiva** de este proyecto y siendo **disruptiva** para la cultura organizacional y profesional actual, la política de seguridad para agentes inteligentes debe ser demostrable y efectiva, integrando como **Línea Base de Ciberseguridad (al menos)**:
 
-* Controles de higiene digital tradicionales basados en CIS Controls  ([https://www.cisecurity.org/controls/cis-controls-navigator](https://www.cisecurity.org/controls/cis-controls-navigator)) con la  
+* Controles de higiene digital tradicionales basados en CIS Controls  ([https\://www\.cisecurity.org/controls/cis-controls-navigator](https://www.cisecurity.org/controls/cis-controls-navigator)) con la  
 * gestión de riesgos específicos, combinando la [Guía de Acompañamiento para Agentes de IA del CIS](https://www.cisecurity.org/insights/white-papers/controls-v8-1-ai-agents-companion-guide) y el [OWASP Top 10 para Aplicaciones Agénticas](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/). 
 
 Los pilares fundamentales incluyen el **inventario estricto de activos**, la **gestión de identidades no humanas**, el **principio de privilegio mínimo**, **límites de autonomía con validación humana** y la **protección de contexto contra inyecciones de prompts**. 
 
 **Sitios de apoyo:** 
 
-\[1\] [https://www.cisecurity.org](https://www.cisecurity.org/insights/white-papers/controls-v8-1-ai-agents-companion-guide)
-
-\[2\] [https://nhimg.org](https://nhimg.org)  
-En específico: [https://astrix.security/learn/blog/securing-llms-ai-agents-and-mcp-unpacking-the-new-cis-companion-guides/?utm\_source=nhimg\&utm\_medium=NHIForum](https://astrix.security/learn/blog/securing-llms-ai-agents-and-mcp-unpacking-the-new-cis-companion-guides/?utm_source=nhimg&utm_medium=NHIForum) 
-
-\[3\] [https://cheatsheetseries.owasp.org](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)
-
-\[4\] [https://genai.owasp.org](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
+\[1\] [https\://www\.cisecurity.org](https://www.cisecurity.org/insights/white-papers/controls-v8-1-ai-agents-companion-guide)
+
+\[2\] [https\://nhimg.org](https://nhimg.org)  
+En específico: [https\://astrix.security/learn/blog/securing-llms-ai-agents-and-mcp-unpacking-the-new-cis-companion-guides/?utm\_source=nhimg\&utm\_medium=NHIForum](https://astrix.security/learn/blog/securing-llms-ai-agents-and-mcp-unpacking-the-new-cis-companion-guides/?utm_source=nhimg&utm_medium=NHIForum) 
+
+\[3\] [https\://cheatsheetseries.owasp.org](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)
+
+\[4\] [https\://genai.owasp.org](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
 
 ---
 
```

```diff
@@ -3690,7 +3664,7 @@
 * **Trazabilidad de Modelos:** Rastrear el origen de los pesos del modelo y los conjuntos de datos de ajuste fino (*fine-tuning*).  
 * **Ciclo de Vida:** Definir procesos automáticos para la baja y revocación de credenciales de agentes inactivos.
 
-**2\. Gestión de Identidades No Humanas (NHI) (Ver, además,** [https://docs.google.com/document/d/1zI3wDVRO6jSZLan-KqqPbx0nNWhX-PiNEJXFi5A5pAo/edit?tab=t.rg4l86s64vzl](https://docs.google.com/document/d/1zI3wDVRO6jSZLan-KqqPbx0nNWhX-PiNEJXFi5A5pAo/edit?tab=t.rg4l86s64vzl)**)**
+**2\. Gestión de Identidades No Humanas (NHI) (Ver, además,** [https\://docs.google.com/document/d/1zI3wDVRO6jSZLan-KqqPbx0nNWhX-PiNEJXFi5A5pAo/edit?tab=t.rg4l86s64vzl](https://docs.google.com/document/d/1zI3wDVRO6jSZLan-KqqPbx0nNWhX-PiNEJXFi5A5pAo/edit?tab=t.rg4l86s64vzl)**)**
 
 * **Identidades Únicas:** Asignar una identidad de máquina (Machine Identity) única por agente mediante certificados o tokens.  
 * **Rotación de Credenciales:** Prohibir el uso de claves de API compartidas o grabadas en código duro (*hardcoded*).  
```

```diff
@@ -3945,8 +3919,6 @@
 
 ---
 
-# **Backlog técnico (Jira)**
-
 # **LÉAME**
 
 Se organiza un **backlog técnico estilo Jira**, listo para cargar, con:
```

```diff
@@ -4682,8 +4654,6 @@
 
 ---
 
-# **DoD específico por historia**
-
 # **1\. DoD Global (base obligatoria para TODAS las historias)**
 
 Una historia se considera DONE solo si cumple:
```

```diff
@@ -4927,8 +4897,6 @@
 \[ \] Validación funcional (SEU)  
 \[ \] Documentación mínima  
 \[ \] Cumple DoD específico del tipo de historia
-
-# **Validación con SEU**
 
 # **LÉAME**
 
```

```diff
@@ -5207,8 +5175,6 @@
 | HU-050 | Agente 4 | Consultas usuarios | Atención | Respuestas correctas | Prueba usuario | Captura | Usuario final |  |  |
 | HU-051 | Agente 4 | FAQ automático | Atención | Reduce consultas manuales | Observación | Registro consultas | Coordinación |  |  |
 
-# **INFRAESTRUCTURA, PRODUCTOS Y SERVICIOS**
-
 La propuesta tecnológica para la pestaña de **INFRAESTRUCTURA, PRODUCTOS Y SERVICIOS** del Proyecto Centenario se basa en un modelo de **IA local, soberanía de datos y bajo costo**, utilizando herramientas de código abierto (*open source*) altamente interoperables y seguras.
 
 ### **1\. Estimación de Recursos de Hardware**
```

```diff
@@ -5297,9 +5263,7 @@
 
 ## **Ambientes DEVSECOPS**
 
-[https://docs.google.com/document/d/1IvJ7wkGzLIYY8EPde0vpV2jjDaNvtLvX7nhxkPYzfUw/edit?usp=sharing](https://docs.google.com/document/d/1IvJ7wkGzLIYY8EPde0vpV2jjDaNvtLvX7nhxkPYzfUw/edit?usp=sharing) 
-
-# **Año 1**
+[https\://docs.google.com/document/d/1IvJ7wkGzLIYY8EPde0vpV2jjDaNvtLvX7nhxkPYzfUw/edit?usp=sharing](https://docs.google.com/document/d/1IvJ7wkGzLIYY8EPde0vpV2jjDaNvtLvX7nhxkPYzfUw/edit?usp=sharing) 
 
 # **Infraestructura, productos y servicios – Año 1**
 
```

```diff
@@ -5527,9 +5491,9 @@
 
 | Categoría | Costo |
 | ----- | ----- |
-| Hardware base | $0 |
-| Software base | $0 |
-| IA local | $0 |
+| Hardware base | \$0 |
+| Software base | \$0 |
+| IA local | \$0 |
 | Cloud low-cost | USD 0–180 |
 | APIs IA | USD 120–600 |
 | Backups | USD 60–120 |
```

```diff
@@ -5545,8 +5509,6 @@
 * Arquitectura diseñada para escalar sin rehacer el sistema  
 * Viabilidad garantizada incluso sin presupuesto adicional
 
-# **Año 2**
-
 # **Infraestructura, productos y servicios – Año 2**
 
 **Etapa: Consolidación y escalado (TRL 5–6)**  
```

```diff
@@ -5560,7 +5522,7 @@
 
 * **Propósito y Despliegue:** Este microprocesador está destinado al **servidor de Implementación y Despliegue** de los **5 agentes inteligentes funcionales** (Extensión Bot, Historia Viva, Vinculación, Atención y Analíticas) para su uso productivo por parte de la Secretaría.  
 * **Capacidad y Rendimiento:** El objetivo es ampliar la capacidad instalada de los servidores existentes (Lenovo ThinkSystem o IBM legacy) para disponer de un **poder de cómputo de IA** que soporte la ejecución de modelos de lenguaje de forma local y fluida.  
-* **Presupuesto Asignado:** El proyecto contempla una erogación de **$500.000** para este equipamiento específico en el Año 2\.  
+* **Presupuesto Asignado:** El proyecto contempla una erogación de **\$500.000** para este equipamiento específico en el Año 2\.  
 * **Filosofía Tecnológica:** La recomendación se enmarca en el uso de **tecnologías de bajo costo y accesibles**, priorizando hardware que permita la ejecución local mediante **Ollama** (para modelos como LLaMA 3 o Mistral) sin depender obligatoriamente de aceleradores de alto costo o equipamiento especializado de gran escala.
 
 En resumen, la recomendación técnica para el Año 2 es la transición de una infraestructura de desarrollo (basada en ampliación de RAM) a una de **producción consolidada** mediante la incorporación de este procesador con capacidades de cálculo optimizadas para tareas de inteligencia artificial.
```

```diff
@@ -5780,9 +5742,9 @@
 
 | Categoría | Costo |
 | ----- | ----- |
-| Hardware base | $0 |
-| Software base | $0 |
-| IA local | $0 |
+| Hardware base | \$0 |
+| Software base | \$0 |
+| IA local | \$0 |
 | Cloud low-cost | USD 180–360 |
 | APIs IA | USD 360–1.200 |
 | Mensajería | USD 120–300 |
```

```diff
@@ -5812,8 +5774,6 @@
 * independencia tecnológica  
 * sostenibilidad institucional  
 * alineación con objetivos estratégicos de la Facultad
-
-# **Agentes \- Infraestructura**
 
 A continuación se dispone la **vinculación explícita entre infraestructura ↔ agentes (1–5) ↔ semestres**, alineada con:
 
```

