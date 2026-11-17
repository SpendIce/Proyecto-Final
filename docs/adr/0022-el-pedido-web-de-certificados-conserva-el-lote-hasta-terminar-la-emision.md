---
status: accepted
---

# El pedido web de certificados conserva el lote hasta terminar su emisión y separa la demostración del envío institucional

Para completar el recorrido web de HU-014 (#168, pedido de Juani del 17/11/2026), la persona con rol `APROBADOR_CONTENIDO` selecciona una actividad existente y aporta una exportación CSV de la lista de cierre del responsable. El Agente 1 valida la lista completa y conserva la instantánea de actividad, titulares y línea descriptiva que se muestra al revisar. No infiere condiciones académicas ni completa datos institucionales ausentes. La aprobación de la línea exacta y del lote la registra quien lo genera, conforme a los ADR 0018 y 0020.

La emisión solicitada desde la web queda en una cola durable del mismo PostgreSQL del canal: el pedido HTTP no entrega correos. Una reserva transaccional evita que dos workers ejecuten el mismo trabajo. Si una interrupción deja incierto un envío, el trabajo pasa a `EMISION_INDETERMINADA` y no se reintenta automáticamente: la cabecera de idempotencia que recibe Gmail no garantiza deduplicación. Se prefirió esta regla a reintentar el lote completo, que podría entregar dos veces un certificado ya enviado. Las colas de otros canales conservan sus mecanismos actuales; no se migran ni se duplican aquí.

La lista y su línea descriptiva siguen siendo datos transitorios, pero aprobar deja de ser motivo suficiente para purgarlas en un pedido nuevo: todavía se necesitan para emitir. Se conservan mientras la operación esté abierta o deba reconciliarse; al terminar se aplica la retención mínima del canal y se mantienen sólo los hashes, la decisión y el resultado. Los abandonados conservan el plazo de treinta días. Un respaldo restaurado debe marcar indeterminados los trabajos reales que pudieron ejecutarse después de la copia, dentro de la misma transacción de restauración y antes de habilitar los workers.

El origen de la solicitud se conserva: un pedido creado en modo demo no se convierte en institucional al apagar ese modo. Tras su aprobación, la demostración genera archivos PDF en un ZIP, siempre sin validez y sin enviar correos ni registrar aprobaciones en el circuito institucional. La emisión institucional conserva el motor y los controles existentes: identidad verificada, rol vigente, generador autorizado, aprobaciones por hash, plantillas y recursos de firma disponibles y destinatarios permitidos. Este cambio técnico no autoriza el uso institucional de insumos que sólo fueron habilitados para pruebas.
