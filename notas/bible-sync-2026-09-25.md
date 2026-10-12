# Bible sync 2026-09-25

Fuente: export doc-id 1zI3wDVRO6jSZLan-KqqPbx0nNWhX-PiNEJXFi5A5pAo

Hunks totales: 8 | Relevantes a Agente 1: 1

```diff
@@ -2692,11 +2692,12 @@
 
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
+5. Se sumó la cantidad de todos los responsables y se obtuvo el costo estimado de mano de obra, alcanzando un total de **\$417.000 USD**.
 
 Véase que por el momento se asume un empleado por rol, futuras adiciones pueden alterar el costo.
 
```

```diff
@@ -2704,48 +2705,48 @@
 
 Considerando los requerimientos del Hardware de despliegue, el costo de los componentes sería:
 
-* GPU (NVIDIA RTX 4090): \~ $4.500 USD  
-* Procesador (Intel Core Ultra 7 270K): \~ $415 USD  
-* Memoria RAM (Kingston Fury Beast RGB 32GB 3200 Mhz DDR4): \~ $660 USD  
-* Almacenamiento (SSD WD Green SN3000 NVMe de 2TB): \~ $485 USD  
-* Gabinete, Fuente y Refrigeración: \~ $400 USD
-
-Si se realiza una sola compra inicial **el costo de hardware total sería de $6.460 USD**
+* GPU (NVIDIA RTX 4090): \~ \$4.500 USD  
+* Procesador (Intel Core Ultra 7 270K): \~ \$415 USD  
+* Memoria RAM (Kingston Fury Beast RGB 32GB 3200 Mhz DDR4): \~ \$660 USD  
+* Almacenamiento (SSD WD Green SN3000 NVMe de 2TB): \~ \$485 USD  
+* Gabinete, Fuente y Refrigeración: \~ \$400 USD
+
+Si se realiza una sola compra inicial **el costo de hardware total sería de \$6.460 USD**
 
 ## **Gastos de oficina**
 
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
+* Costo mensual: \$70 USD  
+* Costos 10 meses: \$700 USD
+
+**Total gastos de oficina (los 10 meses): \$4.750 USD**
 
 ## **Presupuesto total**
 
 Mano de obra \+ Costos de Hardware \+ Gastos de Oficina \= Presupuesto Total
 
-**$252.800 USD \+ $6.460 USD \+ $4.750 USD \= $264.010 USD**
+**\$417.000 USD \+ \$6.460 USD \+ \$4.750 USD \= \$428.210 USD**
 
 # Administración de Riesgos
 
```

```diff
@@ -2766,39 +2767,39 @@
 * Crítico (Más del 90%)
 
 
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
+| ID | Riesgo | Categoría | Probabilidad | Impacto | Exposición |
+| ----- | ----- | ----- | ----- | ----- | ----- |
+| R-01 | Incompatibilidad de contratos de interfaz entre ExtensiónBot y los Agentes 2 a 5 durante la integración | Integración | Media | Alto | Alto |
+| R-02 | Sobrecosto por subestimación de tareas de integración con Agentes 2–5 | Proyecto | Media | Medio | Medio |
+| R-03 | Incremento del costo del hardware especializado por variaciones del mercado o del tipo de cambio | Costos | Media | Medio | Medio |
+| R-04 | Falta de alineación entre los equipos de desarrollo de los distintos agentes por deficiencias en el plan de comunicaciones | Comunicaciones | Media | Medio | Medio |
+| R-05 | Baja adopción por parte del personal de Extensión (resistencia al cambio) | Negocio / Adopción | Alta | Medio | Alto |
+| R-06 | Dependencia de licencias/servicios cloud de terceros (Google Workspace, APIs de redes) | Proveedores | Media | Medio | Medio |
+| R-07 | Demora en la adquisición de infraestructura cloud, servidores o licencias necesarias para el desarrollo | Adquisiciones | Media | Medio | Medio |
+| R-08 | Rotación o indisponibilidad de estudiantes de 4° y 5° año que integran el equipo de desarrollo | Recursos Humanos | Alta | Medio | Alto |
+| R-09 | Personal inadecuado o con perfil insuficiente para las tecnologías críticas del proyecto | Recursos Humanos | Media | Alto | Alto |
+| R-10 | Cronograma o presupuesto total subestimados frente a la complejidad real del sistema multiagente | Proyecto | Media | Alto | Alto |
+| R-11 | Diseño de clases y componentes aún no validado oficialmente que resulte inadecuado para la implementación real | Diseño | Media | Alto | Alto |
+| R-12 | Adopción de tecnologías de IA generativa local (Ollama, RAG, prompt engineering) nuevas para el equipo de desarrollo | Técnico | Alta | Medio | Alto |
+| R-13 | Demora en poner el sistema operativo frente a las necesidades actuales de la Secretaría de Extensión, perdiendo vigencia u oportunidad frente al problema original | Negocio / Adopción | Media | Medio | Medio |
+| R-14 | Dificultad para conseguir el respaldo institucional necesario para escalar ExtensiónBot al resto de la Facultad en el marco del Plan de escalabilidad hacia el Centenario | Negocio / Adopción | Media | Medio | Medio |
+| R-15 | Falta de apoyo político/institucional sostenido de las autoridades de la FIE para la continuidad presupuestaria del proyecto | Negocio / Adopción | Baja | Alto | Medio |
+| R-16 | Suplantación de identidad de ExtensiónBot para acceder a APIs internas (Spoofing) | Seguridad | Media | Alto | Alto |
+| R-17 | Inyección de prompts indirecta vía RAG/Repositorio Institucional que altera instrucciones (Tampering) | Seguridad | Alta | Alto | Crítico |
+| R-18 | Imposibilidad de determinar si una acción dañina fue error de lógica o ataque (Repudiation) | Seguridad | Baja | Alto | Medio |
+| R-19 | Fuga de datos confidenciales o PII en una respuesta generada (Information Disclosure) | Seguridad | Media | Alto | Alto |
+| R-20 | Agente engañado para ejecutar acción fuera de su autorización (Elevation of Privilege) | Seguridad | Baja | Alto | Medio |
+| R-21 | Falla de integridad en datos de entrenamiento/RAG (Data Poisoning) | Seguridad | Baja | Alto | Medio |
+| R-22 | Saturación del agente por ráfaga de solicitudes agotando ventana de contexto (Denial of Service) | Seguridad / Infraestructura | Media | Medio | Medio |
+|  |  |  |  |  |  |
+|  |  |  |  |  |  |
+|  |  |  |  |  |  |
+|  |  |  |  |  |  |
+|  |  |  |  |  |  |
+|  |  |  |  |  |  |
+|  |  |  |  |  |  |
+|  |  |  |  |  |  |
+|  |  |  |  |  |  |
 
 En pos de facilitar la visualización en el documento, se procedió a agregarla en formato de lista:
 
```

```diff
@@ -2864,7 +2865,7 @@
 
 ## **R-05: Incremento del costo del hardware especializado (GPU/microprocesador IA) por variaciones del mercado o del tipo de cambio**
 
-| Causa de Origen | El presupuesto de hardware ($3.300 USD) se estimó en un momento puntual sin margen para fluctuaciones de precios internacionales de componentes de IA. |
+| Causa de Origen | El presupuesto de hardware (\$3.300 USD) se estimó en un momento puntual sin margen para fluctuaciones de precios internacionales de componentes de IA. |
 | :---- | :---- |
 | **Disparadores** | Cotización de proveedores de GPU/hardware superior a la presupuestada al momento de ejecutar T-026. Alertas del control de costos EVM (T-042) mostrando variación de costos (CV) negativa en la fase de adquisición. |
 | **Plan de Contingencia** | Utilizar la reserva de contingencia presupuestada. Evaluar proveedores alternativos o componentes de especificación equivalente de menor costo. Informar el sobrecosto a los interesados mediante el informe de avance (T-069). |
```

```diff
@@ -3012,7 +3013,7 @@
 | **Responsable** | Líder de Proyecto / Analista Funcional |
 | **Estado (ROAM)** | Accepted |
 
-## **R-15: Cronograma de 24 meses o presupuesto total ($260.850 USD) subestimados frente a la complejidad real del sistema multiagente**
+## **R-15: Cronograma de 24 meses o presupuesto total (\$260.850 USD) subestimados frente a la complejidad real del sistema multiagente**
 
 | Causa de Origen | La estimación de tiempos y costos (T-006, T-009 a T-011) se realizó en la etapa de planificación inicial sin contar aún con un prototipo funcional del motor de IA que validara los tiempos reales de desarrollo. |
 | :---- | :---- |
```

```diff
@@ -5527,9 +5528,9 @@
 
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
@@ -5560,7 +5561,7 @@
 
 * **Propósito y Despliegue:** Este microprocesador está destinado al **servidor de Implementación y Despliegue** de los **5 agentes inteligentes funcionales** (Extensión Bot, Historia Viva, Vinculación, Atención y Analíticas) para su uso productivo por parte de la Secretaría.  
 * **Capacidad y Rendimiento:** El objetivo es ampliar la capacidad instalada de los servidores existentes (Lenovo ThinkSystem o IBM legacy) para disponer de un **poder de cómputo de IA** que soporte la ejecución de modelos de lenguaje de forma local y fluida.  
-* **Presupuesto Asignado:** El proyecto contempla una erogación de **$500.000** para este equipamiento específico en el Año 2\.  
+* **Presupuesto Asignado:** El proyecto contempla una erogación de **\$500.000** para este equipamiento específico en el Año 2\.  
 * **Filosofía Tecnológica:** La recomendación se enmarca en el uso de **tecnologías de bajo costo y accesibles**, priorizando hardware que permita la ejecución local mediante **Ollama** (para modelos como LLaMA 3 o Mistral) sin depender obligatoriamente de aceleradores de alto costo o equipamiento especializado de gran escala.
 
 En resumen, la recomendación técnica para el Año 2 es la transición de una infraestructura de desarrollo (basada en ampliación de RAM) a una de **producción consolidada** mediante la incorporación de este procesador con capacidades de cálculo optimizadas para tareas de inteligencia artificial.
```

```diff
@@ -5780,9 +5781,9 @@
 
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

