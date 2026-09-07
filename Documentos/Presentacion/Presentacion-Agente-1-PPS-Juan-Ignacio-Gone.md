---
marp: true
theme: default
paginate: true
size: 16:9
title: "Agente 1 - Extension Bot"
description: "Presentacion ejecutiva para mostrar y vender el Agente 1 del Proyecto Centenario"
---

# Agente 1 - Extension Bot

## Comunicacion institucional asistida por IA para la SEU

Proyecto Centenario P100 - FIE / UNDEF  
Juan Ignacio Gone

<!--
Notas de orador:
Abrir con una idea simple: este proyecto no intenta reemplazar a la Secretaria ni publicar solo. El objetivo es sacar trabajo repetitivo del medio, ordenar la comunicacion y dejar evidencia auditable.
-->

---

# El problema

La comunicacion de Extension depende demasiado del trabajo manual.

- Cada gacetilla, post o mail se arma desde cero.
- El tono y el formato cambian segun quien redacte.
- Las inscripciones y certificados generan tareas repetitivas.
- Falta trazabilidad sistematica de que se genero, quien valido y cuando.

**Resultado:** se pierde tiempo operativo y se vuelve dificil sostener consistencia institucional.

<!--
Notas de orador:
No vender "IA" como magia. Vender reduccion de friccion: menos redaccion repetitiva, mas control, mas consistencia y mas evidencia.
-->

---

# La oportunidad

La SEU ya trabaja con herramientas conocidas: Google Sheets, Docs, Drive, Gmail y formularios.

El Agente 1 aprovecha esa base para transformar datos operativos en piezas de comunicacion listas para revisar.

**Entrada:** datos de actividad, inscripcion o documento institucional.  
**Proceso:** generacion asistida por IA con reglas de tono, canal y plantilla.  
**Salida:** borradores, mails, posts o certificados pendientes de validacion.

<!--
Notas de orador:
Remarcar bajo costo y adopcion: no se pide cambiar toda la forma de trabajar, sino conectar mejor lo que ya existe.
-->

---

# La solucion

**Extension Bot** es el agente de comunicacion institucional del P100.

Hace:

- gacetillas institucionales;
- posts para Instagram y LinkedIn;
- newsletters y correos institucionales;
- confirmaciones automaticas de inscripcion;
- certificados en PDF con validacion previa;
- interaccion interna en lenguaje natural.

No hace:

- scraping;
- analitica o dashboards;
- atencion masiva al publico;
- publicacion en redes y envio de gacetillas o newsletters: eso lo hace la SEU a mano sobre el borrador aprobado;
- publicacion sin aprobacion humana.

<!--
Notas de orador:
Esta slide tiene que despejar alcance. Si alguien pregunta "tambien podria hacer X?", responder: si X es comunicacion institucional, puede evaluarse; si es analitica, scraping o atencion publica, corresponde a otros agentes.
-->

---

# Propuesta de valor

| Para la SEU | Valor concreto |
|---|---|
| Menos carga manual | Borradores generados desde datos ya cargados |
| Mas consistencia | Plantillas, tono institucional y reglas por canal |
| Mas control | Human-in-the-loop antes de publicar, enviar o emitir |
| Mas evidencia | Logs, estados, validadores y outputs recuperables |
| Menor costo | Stack open source y Google Workspace institucional |

<!--
Notas de orador:
Esto es lo que se vende: tiempo, consistencia, control y evidencia. La IA es el medio, no el argumento central.
-->

---

# Flujo principal

## Actividad -> Comunicacion

1. La SEU carga una actividad en Google Sheets o Forms.
2. Un trigger detecta la solicitud.
3. El Agente 1 genera gacetilla y posts por canal.
4. El contenido queda como borrador.
5. Un responsable humano revisa, observa o aprueba.
6. La publicacion o envio ocurre solo despues de esa validacion, y la ejecuta la SEU de forma manual. Unica excepcion: el mail de confirmacion de inscripcion (HU-012), que el agente envia automaticamente una vez aprobado.

**Regla no negociable:** ningun contenido oficial sale sin aprobacion humana registrada.

<!--
Notas de orador:
Decirlo fuerte: esta regla reduce riesgo reputacional y hace defendible el proyecto. No es una limitacion, es una garantia institucional.
-->

---

# Demo sugerida

Mostrar un caso corto, no una arquitectura larga.

**Caso:** nueva actividad de Extension.

1. Datos minimos en una planilla.
2. Click o trigger de generacion.
3. Google Doc con gacetilla institucional.
4. Dos versiones de post: Instagram y LinkedIn.
5. Estado "pendiente de validacion".
6. Registro con fecha, solicitud, output y validador.

**Cierre de demo:** antes tardaba redaccion manual; ahora queda un borrador revisable y auditable.

<!--
Notas de orador:
La demo tiene que mostrar antes/despues. Si se muestra solo tecnologia, se pierde la venta. La audiencia necesita ver una tarea real resuelta.
-->

---

# Roadmap 2026

| Periodo | Objetivo | Evidencia |
|---|---|---|
| S1 2026 | MVP de gacetillas y posts | TRL 3: prototipo controlado, outputs, logs y checklist SEU |
| S2 2026 | Confirmaciones, lenguaje natural interno y certificados | TRL 4: validacion con usuarios internos reales |
| Feb 2027 | Demo, cierre y transferencia | Paquete final y continuidad hacia P100 |

El P100 completo sigue en 2027 con integracion multiagente, pero este PPS se concentra en el Agente 1 durante el primer año.

<!--
Notas de orador:
No prometer operacion total multiagente desde el primer dia. La madurez TRL es el argumento de seriedad: primero prototipo controlado, despues validacion real.
-->

---

# Por que empezar por A1

El Agente 1 es el primer punto visible de valor institucional.

- Convierte actividades en difusion.
- Recibe insumos de A2, A3, A4 y A5 sin orquestarlos.
- Mejora el Proceso 4, que da visibilidad a cursos, eventos y programas.
- Permite demostrar IA con bajo riesgo: borradores, validacion y evidencia.

**A1 no centraliza el P100: lo hace comunicable.**

<!--
Notas de orador:
Esta frase ayuda a evitar una confusion comun: A1 es hub de comunicacion, no cerebro central. Es una pieza visible y defendible para arrancar.
-->

---

# Riesgos y controles

| Riesgo | Control |
|---|---|
| Informacion inventada | fuentes visibles, prompts restrictivos y revision humana |
| Tono no institucional | plantillas y checklist SEU |
| Publicacion indebida | estados bloqueantes: borrador, pendiente, aprobado, rechazado |
| Falta de evidencia TRL | logs, outputs, defectos, actas y checklist |
| Expansion de alcance | matriz BPM-HU-DoD y exclusiones A4/A5 |

**El proyecto no se defiende prometiendo autonomia total; se defiende demostrando control.**

<!--
Notas de orador:
Si alguien objeta "la IA se equivoca", la respuesta es: exactamente por eso el diseño no publica solo. La herramienta asiste; la institucion decide.
-->

---

# Decision que se necesita

Para avanzar con una demostracion convincente, la SEU debe confirmar:

- una plantilla inicial de gacetilla;
- reglas de tono para Instagram y LinkedIn;
- campos minimos de la planilla de actividades;
- responsables de validacion por tipo de pieza;
- una muestra sintética o semirreal autorizada para probar el MVP.

Con eso se puede cerrar un caso demostrable de punta a punta.

<!--
Notas de orador:
Esta slide convierte la presentacion en accion. No pedir "aprobacion general"; pedir insumos concretos para una demo real.
-->

---

# Cierre

Extension Bot no reemplaza a la SEU.

**Le da una linea de produccion comunicacional con control humano, bajo costo y evidencia academica.**

El objetivo del primer año es claro:

- automatizar gacetillas y posts;
- incorporar confirmaciones, interaccion interna y certificados;
- demostrar TRL 3 y TRL 4 con evidencia;
- dejar una base transferible al Proyecto Centenario.

<!--
Notas de orador:
Cerrar con una frase ejecutiva: "No estamos vendiendo un chatbot; estamos proponiendo una capacidad institucional repetible, auditable y gobernada".
-->

---

# Respuestas a objeciones

**"La IA puede equivocarse."**  
Si. Por eso el agente no publica ni emite sin validacion humana registrada.

**"Esto reemplaza personal?"**  
No. Automatiza borradores y tareas repetitivas; la responsabilidad institucional sigue en la SEU.

**"No es demasiado grande?"**  
El alcance esta acotado a HU-010 a HU-014 durante 2026. S3-S4 son continuidad P100.

**"Que pasa si no hay datos completos?"**  
El sistema marca la solicitud como incompleta y no genera comunicacion oficial.

<!--
Notas de orador:
Usar esta slide solo si hay preguntas. No hace falta mostrarla en una presentacion corta.
-->

---

# Fuentes del deck

- `Agentes/extension_bot_experto.md`
- `Contenido/Definicion/arquitectura-multiagente.md`
- `Contenido/bible/Procesos y Agentes.md`
- `Documentos/Anteproyecto/Anteproyecto-PPS-Juan-Ignacio-Gone.tex`
- `Documentos/CasosUso/Casos-de-Uso-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanCalidad/Plan-Calidad-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/PlanRiesgos/Plan-Riesgos-Agente-1-PPS-Juan-Ignacio-Gone.md`
- `Documentos/Gantt/README.md`

<!--
Notas de orador:
Esta slide sostiene trazabilidad. No hace falta mostrarla salvo en contexto academico o si preguntan de donde sale el alcance.
-->
