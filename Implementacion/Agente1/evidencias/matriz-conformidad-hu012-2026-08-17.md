# HU-012 — Matriz de conformidad offline (2026-08-17)

**Estado:** PENDIENTE de validación SEU.  
**Naturaleza:** evidencia contractual simulada; no se envió correo real.  
**TRL 3:** no acreditado.

| Caso | Estado esperado | Control observado |
|---|---|---|
| Borrador base | `PENDIENTE_VALIDACION` | Golden determinista, sin entrega |
| Texto con instrucciones | `PENDIENTE_VALIDACION` | Se preserva como dato literal, sin entrega |
| Aprobación simulada | `APROBADA` | No entrega sin pedido explícito |
| Rechazo simulado | `RECHAZADA` | Bloquea entrega aunque se solicite |
| Entrega fake | `ENVIADA_SIMULADA` | Una entrega sólo en memoria |
| Repetición idéntica | `DUPLICADA` | No regenera ni vuelve a entregar |
| Email inválido | `INVALIDA` | No genera borrador |
| Fecha ausente | `INCOMPLETA` | No genera borrador |

## Reproducción

```bash
bash scripts/smoke_confirmaciones.sh /tmp/smoke-hu012
```

El resumen machine-readable queda en `/tmp/smoke-hu012/matriz.json`. Incluye hashes del contrato, la plantilla y el runner, pero no PII ni contenido del mensaje.

## Lectura correcta

`ENVIADA_SIMULADA` significa que un test double guardó una estructura en memoria. NO significa que exista integración de correo ni autorización de SEU. Los estados `APROBADA` y `RECHAZADA` de esta matriz usan identidades simuladas. La decisión institucional continúa PENDIENTE y la evidencia no acredita Gate G2 ni TRL 3.
