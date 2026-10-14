# Changelog — Agente 1

Historial de las **versiones del agente** que se instalan en el host. Cada
versión lleva un tag `agente1-vX.Y.Z` sobre `main` y una entrada acá con los
cambios controlados que la componen, su clase y la referencia del issue o rama
que los introdujo.

La versión sale de un solo lugar, `pyproject.toml` (`[project].version`); el
manifest de versión, la auditoría de cada pieza y esta entrada la citan, no la
repiten. El procedimiento para cortar una versión está en
[`PROCEDIMIENTO-CORTE-DE-VERSION.md`](PROCEDIMIENTO-CORTE-DE-VERSION.md).

**Clases** (resolución del issue #66):

- **Mayor** — cambia un contrato de interfaz.
- **Menor** — capacidad nueva, prompt o política.
- **Parche** — corrección.

> La referencia identifica el cambio controlado. Este repositorio integra por
> ramas `ticket/NN` con merge local; todavía no hay números de PR de GitHub, así
> que se cita el issue o la rama.

## [0.1.0] - 2026-10-14

Primera versión etiquetada. Es el sistema de demostración completo del Agente 1
antes de la revisión de laboratorio y de la mesa final del 18/11/2026. Consolida
los cambios controlados incorporados a `main` hasta esta fecha.

### Mayor — contratos de interfaz

- Contrato v2 de la planilla de actividades, consumido por HU-010 (gacetilla),
  HU-011 (posts) y HU-013 (interpretación) (#77).
- Contrato creativo estructurado de HU-011 y su renderer determinista (#85).
- Contrato `/v1` de consulta a Historia Viva: cliente y transporte HTTP
  (#12, #13, #17).

### Menor — capacidades, prompts y políticas

- Pipeline HU-010: gacetilla desde un evento A3 (#83).
- Pipeline HU-011: posts y post de efeméride desde Historia Viva (#85, #89).
- Confirmaciones HU-012 y su circuito de doble aprobación por rol (#28).
- Recordatorios de pago, pagos desde la planilla e instrucciones de pago
  (#44, #45, #46).
- Plantilla de correo por actividad HU-012 (#73).
- Certificados HU-014: línea descriptiva, lote de cierre y emisión (#74, #75).
- Canal de pedidos por Form, registro de decisiones y canal de planilla
  (#71, #72).
- Scheduler local de las corridas programadas (#84).
- Respaldo diario del estado local en Drive (#86).
- Purga de datos personales del registro al cerrar el ciclo (#87).
- Medición del nivel verificado de los SLO (#88).
- Corrida de insumos de agentes A2-A5 sobre la pestaña «Insumos de agentes»
  (#82).
- Buzón Gmail de sólo lectura (#43).
- Manifest de versión y verificación de integridad al arrancar (#92).
- Versión del agente en la auditoría, tag y este changelog (#93).

### Parche — correcciones

- Gacetillas sin lugar: el gate y el render acuerdan el campo (#6).
- Reintento con feedback en HU-011 (#85).
- Idempotencia de HU-012 ante una caída (#9).
- Presupuesto de decodificación dimensionado por el contrato (#4).

### Infraestructura

- Suite, cobertura y linter del Agente 1 en GitHub Actions (#90).

## Configuración

Cambios que el responsable técnico o el operador le piden a **DSI** en la consola
de Google (Workspace y credenciales): IDs de planillas y Forms, scopes, cuenta
técnica, unidad compartida. **No generan versión del agente** —no cambian el
código, los prompts ni las políticas— y se anotan **al pedir el cambio**, con
fecha, motivo y quién lo aprobó (issue #66, adenda del 13/10). El log de la
consola de Google los guarda 6 meses; esta tabla es el registro que sobrevive.

| Fecha | Cambio pedido | Motivo | Aprobó |
|---|---|---|---|
| — | _Sin cambios pedidos a DSI todavía._ | — | — |
