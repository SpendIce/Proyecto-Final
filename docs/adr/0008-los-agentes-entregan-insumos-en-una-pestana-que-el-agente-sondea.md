---
status: accepted
---

# Los agentes entregan insumos en una pestana que el Agente 1 sondea; Historia Viva se consulta

El anteproyecto promete el Agente 1 como **nodo de comunicacion institucional**, con "recepcion de insumos de A2, A3, A4 y A5". En 2026 no existe ninguno de esos agentes en un estado que pueda entregar algo, y el sistema de demostracion no admite fakes.

Decidimos que A3, A4 y A5 entregan sus **insumos de agente** como filas en una pestana "Insumos de agentes" de la planilla de D2, con el envelope `agente1.insumo.v1`. El Agente 1 las lee con una corrida que un scheduler local dispara cada pocos minutos (y que tambien se puede correr a mano). A cada fila le **responde con el estado de su insumo** (borrador generado con su enlace, o rechazado con el codigo del contrato), nunca con la pieza: la pieza sigue esperando la validacion humana. Cada `correlation_id` se procesa una sola vez.

**Historia Viva (A2) no entrega insumos: se consulta.** El Agente 1 compone la efemeride con los fragmentos que le pide por el puerto `HistoriaViva`. Por eso A2 sale del envelope de insumos.

Mientras un agente no exista, un **productor provisional** declarado carga sus filas con `data_origin = provisional_producer`. Para el 18/11 se muestra en vivo solo A3 `evento` → borrador de gacetilla (HU-010). A2 → post de efemeride (HU-011) se muestra por HTTP real solo si la instancia de Ignacio, con el contrato acordado, esta disponible antes de la entrega de los anexos al laboratorio. A4 y A5 quedan como contrato.

## Considered Options

- **Push desde el otro agente (webhook o Apps Script que llama al Agente 1).** Se descarto porque el Agente 1 corre en una laptop sin entrada publica, y porque recibir pedidos rompe el modelo en el que el Agente 1 inicia toda lectura (ADR 0006, cliente pull de Historia Viva).
- **Trigger de Apps Script por fila nueva.** Se descarto para 2026 porque suma un componente sin cambiar lo que se ve: el scheduler local da la misma reaccion. Se puede volver a evaluar cuando el Agente 1 corra en un host de la FIE.
- **Solo mostrar el contrato (validacion de envelopes) sin flujo.** Se descarto porque deja sin mostrar el objetivo del nodo, y con un productor provisional el mecanismo ya es el productivo.
- **A2 como fila del bus, con tipo `efemeride`.** Se descarto porque convierte a Historia Viva en generador de efemerides, cosa que el glosario excluye, y porque usa un mecanismo distinto del definitivo, asi que la fila no seria un insumo provisional.

## Consequences

El bus de Sheets que el anteproyecto asigna a la capa de orquestacion conjunta no tiene que existir antes: la pestana es el punto de entrada propio del Agente 1, y cuando el bus conjunto exista, el agente productor escribe ahi. Sumar un flujo nuevo (A3 HU-041, alertas de A5, alta de curso de P5) solo pide un tipo de payload nuevo, pero eso es continuidad P100 y necesita un contrato con el dueno de cada agente.
