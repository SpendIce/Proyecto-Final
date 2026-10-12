---
status: accepted (provisional, a confirmar con Direccion de Carrera)
---

# Identidad verificada por el formulario, rol por padron

En el **sistema de demostracion**, el **canal de interaccion** de HU-013 es un Google Form de pedidos restringido al dominio de la FIE y con recopilacion de correos verificados. Las decisiones humanas (aprobacion de plantilla, **aprobacion de lote** y **decision de publicacion**) se registran por un segundo Form, al que se llega por links prellenados en los correos del agente. Google autentica el correo de quien responde; el rol no lo autentica nadie.

Decidimos que el Agente 1 tome la **identidad del correo verificado por Google** y el **rol de un padron** fuera del repositorio, mantenido por la SEU (provisionalmente por el autor del PPS). Quien no esta en el padron, o no tiene el rol que la decision exige, queda rechazado y registrado. Para este canal, esta decision reemplaza al ADR 0002. El nucleo no cambia: sigue recibiendo una identidad con rol, y ahora el adapter la llena con una identidad verificada.

## Considered Options

Se evaluo mantener el rol afirmado en un campo del formulario, como en el ADR 0002. Se descarto porque, con la identidad ya verificada, dejar que cada persona declare su propio rol desperdicia la unica verificacion disponible.

El ADR 0002 habia descartado el padron porque mapeaba una identidad no verificada, y eso era la misma afirmacion disfrazada de control. Con correo verificado esa objecion cae: verificar la identidad y autorizar por padron es control de acceso comun.

## Consequences

El padron es un recurso nuevo que alguien de la SEU tiene que mantener, y Direccion de Carrera todavia no lo confirmo: se consulta a Cicerchia porque le suma una carga a la SEU despues del PPS. Si se rechaza, el canal vuelve al rol afirmado del ADR 0002 sin tocar el nucleo.

Los roles del padron son los que la SEU designo por escrito (acta del 22/09). El sistema no asigna roles a partir de una lectura del organigrama.

Las evidencias producidas por este canal acreditan identidad verificada y autorizacion por padron declarado. Los otros canales (planilla offline, prototipo web) siguen bajo el ADR 0002.
