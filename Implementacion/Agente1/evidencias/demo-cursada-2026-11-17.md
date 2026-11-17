# Preparación de la presentación de cursada — 17/11/2026

## Estado inicial verificado

Base remota: `184481e` (versión 0.8.1). Se preservó el `main` local con sus cambios ajenos a esta intervención. Respaldo remoto existente: tag `demo-respaldo-2026-11-17` → `184481e`; rama `respaldo/deploy-2026-11-17` → `3fd017c`.

La suite base con PostgreSQL 16 efímero arrojó **2869 passed, 8 skipped** en 82,07 segundos. Los casos omitidos conservan sus condiciones de entorno; el resultado no acredita pruebas institucionales ni una puntuación de calidad humana.

## Defecto confirmado: ajuste sin cierre (#177)

El pedido observado permanecía `AJUSTANDO` y no existía `worker/logs/ajustes.jsonl`. La lectura de los logs del contenedor encontró cinco reinicios y esta cadena:

```text
worker.correr_una_vez → RepositorioWeb.completar_trabajo
→ UPDATE prosa_transitoria SET id_borrador = ...
→ psycopg.errors.InsufficientPrivilege: permission denied for table prosa_transitoria
```

La migración 0005 concedía SELECT e INSERT al rol `agente1_app`, mientras que el ajuste incorporado en 0009 requiere actualizar el vínculo de la indicación con su nuevo borrador. La generación llegó hasta la persistencia: atribuir este caso exclusivamente a la latencia de Ollama era una hipótesis insuficiente.

La solución elegida es una migración nueva que concede UPDATE únicamente sobre `id_borrador`. No se reescribe ninguna migración ya aplicada ni se permite modificar el texto transitorio con el rol de aplicación. Se conserva la compatibilidad con la imagen anterior.

## Usabilidad observada

Chromium del sistema, ventanas de 1440 y 390 px, contra el despliegue real. Nuevo pedido y bandeja no presentaban desborde horizontal. La vista del ajuste sí desbordaba a 390 px por la tabla de revisiones. Las capturas iniciales y el JSON de auditoría se conservaron fuera del repositorio; no contienen credenciales.

## Verificación final

La integración 0.9.0 pasó **2935 pruebas, 8 omitidas**, con PostgreSQL 16
efímero, en 83,09 segundos; Ruff no encontró hallazgos. Incluye el rol real
`agente1_app`, la denegación de cambios sobre prosa y auditoría, el ciclo de
migraciones, el timeout tipado del adapter y la normalización del asunto.

Se realizaron revisiones independientes de normas y especificación, además
de revisión cruzada entre DeepSeek y Devin. Se corrigieron la clasificación
de reversibilidad de 0011, la duplicación de la semilla ficticia, el asunto
duplicado, la identificación del timeout real y la atribución causal
incorrecta de un comentario. La herramienta específica `autoreview` no
estaba disponible; no se la declara ejecutada.

La revisión cruzada también reprodujo una decisión de lote ficticio fuera
de modo demo que ingresaba al registro institucional. Se bloqueó el POST
con 403 antes de modificar la fila y se excluyó la decisión ficticia de ese
registro incluso dentro de demo. Las pruebas de ruta con PostgreSQL cubren
ambos controles, las variantes del script y la conservación del circuito
real. No se observó emisión ni envío institucional durante esa revisión.

Los fallos del generador vuelven a `LISTA` sin multiplicar reservas. Un error
posterior de persistencia conserva la reserva para reconciliar un Doc que
ya puede haber sido escrito; no se declara intacto ese Doc por cerrar la
ejecución con la revisión anterior.

La prueba real posterior al despliegue se registra en el PR del corte. No
se declara resuelto el defecto a partir de la entrega de un worker.
