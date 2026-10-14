# Cuenta de servicio con delegación y lista cerrada de cuentas suplantables (#98, ADR 0011)

- **Estado:** implementado y verificado offline; el paso en vivo y la baja de
  la OAuth quedan para el operador designado y para el issue #99
- **Alcance:** provider de credencial con cuenta de servicio y *domain-wide
  delegation* (`CuentaServicioDelegadaProvider`), lista cerrada de cuentas
  suplantables (`contracts/cuentas_suplantables_v1.json`) y auditoría de por
  quién se pidió cada token
- **Relacionados:** ADR 0011, enmienda de ADR 0004, ADR 0010,
  `docs/seguridad/modelo-seguridad-cuenta-google-agente-1.md` §1 y §4,
  `docs/adr/0004-...md` (enmienda), issue #98, `src/agente1/workspace_auth.py`,
  `tests/test_workspace_cuenta_servicio.py`

## 1. Qué se construyó

`CuentaServicioDelegadaProvider` reemplaza al provider OAuth como mecanismo
vigente. Firma un *assertion* JWT RS256 con `sub` = la cuenta por la que el
agente se hace pasar y lo intercambia en `oauth2.googleapis.com/token` (el
mismo host exclusivo de hoy) con `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer`.
Pide los scopes autorizados en la delegación (`drive`, `gmail.send`,
`gmail.readonly`) y conserva el *deadline*, el tope de respuesta, la ausencia
de reintentos y los códigos `workspace_token_exchange_*`.

- **Lista cerrada.** `contracts/cuentas_suplantables_v1.json` guarda el
  sha256 de cada dirección normalizada (sin minúscula/espacios, sin la
  dirección en claro). Entra en el manifest de la versión (ADR 0010) porque el
  barrido de `src/**` de #92 lo levanta solo. Hoy lleva **una** entrada: la
  cuenta técnica. Si el entorno indica una cuenta que no está en la lista, el
  provider no se construye y el modo operación no arranca
  (`workspace_impersonation_not_allowed`).
- **Firma sin dependencias de runtime.** El *assertion* se firma con el
  binario `openssl` del host (`/usr/bin/openssl 3.6.4`). La clave privada se le
  pasa por un *pipe* (`/dev/fd/N`): nunca por `argv`, por el entorno ni por un
  archivo temporal. Si el binario falta o la firma no sale, el agente se
  detiene con `workspace_auth_signing_unavailable` (fail-closed).
- **Auditoría por token.** Cada emisión agrega una línea a
  `logs/cuenta-suplantada.jsonl` con el sha256 de la cuenta suplantada y la
  versión del agente (`record: agente1_cuenta_suplantada_v1`). Se escribe antes
  de devolver el token: si no se puede escribir, la emisión falla
  (`workspace_cuenta_audit_unavailable`).
- **`construir_token_provider()` elige la cuenta de servicio.** El camino OAuth
  por refresh token queda como respaldo explícito —no silencioso: un par de
  cuenta de servicio a medias falla, no cae a OAuth— hasta que cierre #99.
- **Un solo camino de token.** Un test recorre `src/agente1/**` y falla si
  `grant_type`, `jwt-bearer`, `assertion`, `refresh_token`, `client_secret` o
  `private_key` aparecen fuera de `workspace_auth.py`: no hay una segunda vía
  que firme un *assertion* o intercambie un token.

## 2. Reproducción offline ejecutada (2026-10-14)

Clave RSA generada localmente (no registrada en Google) y transporte falso:
el intercambio nunca sale a la red. Salida real:

```
clave local: openssl genrsa 2048 -> /tmp/.../clave.json
cuentas en la lista cerrada: 1
sha256(bot_ia1@fie.undef.edu.ar): 72f622324288fdc8ad001256509608e96e7865452d79a990505511ff1332881b

== A. clave local no registrada: Google deniega ==
el agente se detiene con: workspace_token_exchange_denied
borradores producidos: 0
lineas de auditoría: 0

== B. intercambio emitido (transporte falso) ==
token: ya29.sintetico
host/target: oauth2.googleapis.com /token
grant_type: urn:ietf:params:oauth:grant-type:jwt-bearer
header: {'alg': 'RS256', 'typ': 'JWT'}
sub: bot_ia1@fie.undef.edu.ar
scope: https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly
aud: https://oauth2.googleapis.com/token
auditoría: {"cuenta_suplantada_sha256": "72f622324288fdc8ad001256509608e96e7865452d79a990505511ff1332881b", "ejecutado_en": "2026-10-14T14:18:13.893533+00:00", "record": "agente1_cuenta_suplantada_v1", "resultado": "emitido", "version": "0.1.0"}
```

El caso A reproduce la **prueba de clave inválida** que reemplaza la prueba de
revocación conjunta que DSI no hace: con una clave no registrada, el agente se
detiene en el intercambio (`workspace_token_exchange_denied`), sin reintento y
sin producir salida. La clave se genera con `openssl genrsa 2048`; el
transporte falso devuelve la respuesta de Google para una clave no registrada
(`400 invalid_grant`).

La suite cubre lo mismo de forma reproducible en
`tests/test_workspace_cuenta_servicio.py`: cuenta fuera de la lista (no
arranca), clave ausente/ilegible/malformada (fallo con código, sin filtrar
contenido), intercambio denegado sin reintento, verificación de la firma RS256
con la clave pública, la auditoría por token y el guard de camino único. La
firma se verifica con `openssl dgst -sha256 -verify` contra la clave pública
derivada del JSON de prueba.

Marcas de alcance: esta reproducción es **offline y declarada** —no acredita
una corrida contra Google ni el paso en el host—. No usa un fake del provider:
usa el provider real, la lista cerrada real y la auditoría real; lo falso es el
transporte (la red) y la clave, que se genera localmente.

## 3. Paso en vivo para el host (issue #99)

Precondición: DSI instaló la clave de la cuenta de servicio en
`~/.config/agente1/` con `chmod 600` (modelo de seguridad §4) y el host tiene
el entorno de la cuenta de servicio (`AGENTE1_WORKSPACE_SERVICE_ACCOUNT_KEY` y
`AGENTE1_WORKSPACE_IMPERSONATED_ACCOUNT`).

1. **Arranca.** Correr el disparo programado del runbook (`--live`). En la
   auditoría:

   ```bash
   tail -n 1 "$DIRECTORIO_SALIDA/logs/cuenta-suplantada.jsonl"
   # cuenta_suplantada_sha256=<hash de la cuenta técnica>, version=<la instalada>
   ```

2. **Clave inválida.** DSI deshabilita o borra la clave (o quita la
   delegación). Repetir el disparo: sale con código 2 y el error
   `workspace_token_exchange_denied`; no se produce ninguna salida.
3. **Reanudación.** DSI habilita una clave nueva, se reinstala y se repite el
   disparo. La corrección no es en caliente (ADR 0011, §7).

## 4. Supuestos y decisiones abiertas

- **Dirección de la cuenta técnica (supuesto).** El ADR 0011 y el correo de
  DSI del 13/10 nombran la cuenta técnica como `bot_ia1@`; el dominio de la FIE
  en el repo es `fie.undef.edu.ar`. El hash del contrato es
  `sha256("bot_ia1@fie.undef.edu.ar")`. Si la dirección real difiere, el agente
  **no arranca** (dirección segura) y el hash se recomputa antes del paso en
  vivo con:

  ```bash
  uv run python -c "from agente1.workspace_auth import sha256_cuenta; print(sha256_cuenta('<direccion>'))"
  ```

  Sumar una cuenta a la lista es un cambio controlado que aprueba la SEU
  (ADR 0011).
- **Firma con `openssl`: alternativa abierta para Juani.** El proyecto tiene
  hoy cero dependencias de runtime (superficie de *supply chain* nula). Firmar
  con `openssl` evita sumar una dependencia de criptografía y fijarla en
  `uv.lock`. Si se prefiere una dependencia (p. ej. `cryptography`), el cambio
  es acotado a `_firmar_rs256`, pero cambia la superficie de *supply chain*;
  por eso no se implementa acá.
- **Regeneración del manifest.** Agregar
  `contracts/cuentas_suplantables_v1.json` bajo `src/` exige regenerar
  `manifest-version.json` al cortar la versión (ADR 0010, #93), no en este
  ticket: el manifest se regenera en el corte, no en cada cambio.

## 5. Límites

- No acredita la corrida live contra Google: es la reproducción offline del
  mismo provider y la auditoría, más el procedimiento para el host.
- Los demás puntos de entrada (`workspace_smoke.py`,
  `exportar_actividades_d2.py`, el wizard del shell) conservan el provider sin
  directorio de auditoría hasta #99; el camino de operación (`cli_insumos`,
  el scheduler y los scripts operativos) ya lo pasa.
- La baja del refresh token OAuth y la eliminación del cliente/proyecto del
  autor son del issue #99.
