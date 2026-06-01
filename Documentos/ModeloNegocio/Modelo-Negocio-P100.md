# Modelo de negocio institucional del Proyecto Centenario (P100)

Este artefacto representa el modelo de negocio del sistema general como modelo de valor institucional, no como modelo comercial de monetizacion. La documentacion del proyecto no define clientes pagos, precios ni ingresos; define una organizacion publica/universitaria que busca ampliar capacidad operativa, mejorar difusion, sistematizar informacion y sostener trazabilidad auditable.

## Diagrama

Fuente editable: [`diagrama-modelo-negocio-p100.mmd`](./diagrama-modelo-negocio-p100.mmd)

El diagrama muestra:

- La necesidad de negocio de la SEU/FIE: carga operativa manual, comunicacion multicanal, informacion dispersa y exigencia de evidencia.
- La propuesta de valor del P100: sistema modular de cinco agentes inteligentes, incremental, de bajo costo y con validacion humana.
- La plataforma compartida: Google Workspace, Sheets como bus de datos, Apps Script, scheduler, backend IA, logs y evidencia.
- El mapa de procesos P1-P9 y su relacion con los agentes A1-A5.
- Las interacciones entre agentes, especialmente el rol de A1 como hub de comunicacion y no como orquestador.
- Los resultados esperados: comunicaciones consistentes, memoria institucional, vinculacion fortalecida, atencion a usuarios, tableros de gestion y trazabilidad auditable.

## Criterios de lectura

- A1 concentra la comunicacion institucional: genera piezas, pero no publica ni envia sin validacion humana.
- A2 convierte documentos institucionales en memoria recuperable y contenido historico reutilizable.
- A3 sostiene vinculacion, oportunidades externas y eventos, alimentando al A1 cuando corresponde difundir.
- A4 atiende consultas y orienta a comunidad/aspirantes; puede solicitar al A1 respuestas o materiales mas elaborados.
- A5 mide, normaliza y transforma datos en evidencia, KPIs, dashboards y retroalimentacion para la planificacion.
- La orquestacion pertenece a la infraestructura y a los procesos: Apps Script, scheduler, bus de datos, colas y triggers. No hay un agente central funcional.

## Fuentes verificadas

- `CLAUDE.md`
- `.claude/persistence.md`
- `Agentes/arquitectura_multiagente_experto.md`
- `Agentes/extension_bot_experto.md`
- `Agentes/historia_viva_experto.md`
- `Contenido/Definicion/arquitectura-multiagente.md`
- `Contenido/bible/README.md`
- `Contenido/bible/PROYECTO-FIE 2026-2027 - Cicerchia Cesar.md`
- `Contenido/bible/Procesos y Agentes.md`
- `Contenido/bible/Correo de Facultad de Ingenieria del Ejercito - Proyecto Agentes IA.md`
