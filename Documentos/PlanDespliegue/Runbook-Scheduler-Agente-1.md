# Runbook del scheduler local — Agente 1

- **Estado:** implementado en código con unidades `systemd --user`
  versionadas como plantillas; instalación y operación pendientes del
  operador designado
- **Alcance:** corridas programadas de la pestaña «Insumos de agentes» en
  el host de la demo, dentro de la ventana de operación
- **Relacionados:** ADR 0007 (traspaso), ADR 0008 (insumos por pestaña),
  ADR 0009 (retención y respaldo), issues #82, #84, #86, #87, #88

## 1. Propósito y límites

El scheduler dispara la corrida de insumos de agentes (#82) cada pocos
minutos para que el Agente 1 reaccione cuando un productor carga una fila
en la pestaña de D2. El disparo automático **sólo produce borradores
`PENDIENTE_VALIDACION`**: no publica, no envía, no habilita ningún canal
nuevo y la validación humana queda intacta. La corrida manual
(`insumos-agentes`) sigue disponible y es la vía de contingencia.

El scheduler es el mismo proceso que la corrida manual: el subcomando
`agente1 scheduler` comparte los flags de `insumos-agentes` (misma tabla
offline, mismo doble opt-in live, mismo directorio de salida) y agrega la
agenda: intervalo, ventana de operación, lock contra solapamientos y el
log de corridas programadas.

Nada de este documento instala ni activa unidades: las de
`Implementacion/Agente1/systemd/` son **plantillas instalables** que el
operador copia y ajusta en el host (ADR 0007: la operación es del operador
designado, no del autor del código).

## 2. Mecanismos de disparo

Se elige **un** mecanismo por host. Los dos ejecutan el mismo `disparar`
con la misma agenda, el mismo lock y el mismo log, así que la elección es
operativa, no de comportamiento.

### 2.1 Timer `systemd --user` (mecanismo natural en la demo)

Un `.timer` dispara un `.service` oneshot cada intervalo:

- `systemd/agente1-scheduler.timer`: `OnCalendar=*:0/5` con
  `Persistent=true` (un tick atrasado por host apagado corre al encender,
  respondiendo al tick más reciente, sin ponerse al día).
- `systemd/agente1-scheduler.service`: `Type=oneshot` que corre
  `agente1 scheduler --una-corrida` y termina.

Cada disparo responde al **tick de agenda** más reciente anterior al
disparo dentro de la ventana (`inicio_previsto` en el log). Un timer que
se atrasa deja el atraso a la vista; un timer más fino que el intervalo
configurado genera disparos `omitida_duplicada`, nunca corridas repetidas.

### 2.2 Bucle con `sleep` (alternativa)

`agente1-scheduler-loop.service` corre `agente1 scheduler --loop` como
proceso único: espera al próximo tick, corre dentro de la ventana y
repite. Es la opción para hosts sin systemd usable y la forma de ensayar
la agenda con `--max-disparos N` en una terminal. Con `Restart=on-failure`
un proceso caído vuelve solo.

Los dos mecanismos conviviendo no duplican filas (ver §4), pero el log
mezclaría dos agendas: en producción se habilita **uno solo**.

## 3. Configuración

Todo por variables de entorno con prefijo `AGENTE1_SCHEDULER_`, declaradas
en un env file del operador (`%h/.config/agente1/scheduler.env` en las
plantillas, **nunca versionado**). Una variable del prefijo desconocida o
con valor vacío/inválido hace fallar el disparo con
`scheduler_config_invalid` / `scheduler_config_unknown_key`: la agenda que
corre es la que está escrita, no un default silencioso.

| Variable | Contenido | Default |
|---|---|---|
| `AGENTE1_SCHEDULER_INTERVALO_S` | Segundos entre ticks | `300` (provisional: «cada pocos minutos» de #84) |
| `AGENTE1_SCHEDULER_VENTANA_DIAS` | Días ISO por coma, lunes = 1 | `1,2,3,4,5` |
| `AGENTE1_SCHEDULER_VENTANA_DESDE` | `HH:MM` local, inclusivo | `08:00` |
| `AGENTE1_SCHEDULER_VENTANA_HASTA` | `HH:MM` local, exclusivo | `16:00` |
| `AGENTE1_SCHEDULER_TZ` | Zona IANA de la ventana | `America/Argentina/Buenos_Aires` |
| `AGENTE1_SCHEDULER_REPO` | Raíz del checkout en el host | derivada de la instalación del paquete |
| `AGENTE1_SCHEDULER_REGISTRO_CONFIRMACIONES` | Directorio del registro durable HU-012 que la purga diaria procesa | sin valor: el paso `purga` no se declara |

La ventana es `[desde, hasta)`: los ticks son `desde + k * intervalo` de
cada día permitido. Los defaults replican la ventana declarada para el SLO
de disponibilidad (días hábiles de 8 a 16) y son **provisionales**: la SEU
los confirma en #56.

El resto de la configuración es la de siempre: `AGENTE1_WORKSPACE_*`,
`AGENTE1_INSUMOS_RANGO_A1` para el camino live y los flags de la corrida
en el `ExecStart` de la unidad.

**Relación timer ↔ intervalo:** la cadencia del `OnCalendar` debe ser
igual o menor que `INTERVALO_S`. Con timer cada 5 minutos e intervalo de
300 s ambas agendas coinciden; un intervalo mayor simplemente asienta
disparos de más como `omitida_duplicada`.

## 4. Solapamiento e idempotencia

Tres capas independientes impiden procesar dos veces la misma fila:

1. **Lock de corrida** (`flock` no bloqueante sobre
   `<directorio>/scheduler-corrida.lock`): un segundo disparo concurrente
   no espera, se asienta `omitida_lock` y no ejecuta nada.
2. **Deduplicación por tick**: un tick ya `completada` no vuelve a correr;
   el disparo extra queda `omitida_duplicada`.
3. **La corrida misma** (#82): filas con `estado` no vacío no se tocan y
   la idempotencia por `correlation_id` absorbe redespachos, incluso si
   una corrida manual y una programada se cruzan.

## 5. Log de corridas programadas (formato versionado)

`<directorio>/logs/scheduler-corridas.jsonl`: una línea JSON por disparo,
append-only. Es la fuente que #88 usa para medir disponibilidad dentro de
la ventana, así que el formato está versionado y validado al releerlo (una
línea ilegible invalida el archivo con `scheduler_log_invalid`, igual que
el registro de insumos: se prefiere no procesar a procesar dos veces).

```json
{
  "record": "scheduler_corrida_v1",
  "correlation_id": "<uuid opaco del disparo>",
  "fecha": "2026-10-05",
  "zona": "America/Argentina/Buenos_Aires",
  "en_ventana": true,
  "inicio_previsto": "2026-10-05T10:05:00-03:00",
  "inicio_real": "2026-10-05T10:05:01-03:00",
  "fin": "2026-10-05T10:05:11-03:00",
  "resultado": "completada",
  "corrida": {
    "estado": "OK",
    "filas_leidas": 3,
    "filas_nuevas": 1,
    "filas_escritas": 1,
    "filas_omitidas": 2,
    "filas_bloqueadas": 0,
    "filas_fallidas": 0
  },
  "mantenimiento": { "purga": "completada", "respaldo": "pendiente" }
}
```

| Campo | Significado |
|---|---|
| `record` | Versión del formato: `scheduler_corrida_v1` |
| `correlation_id` | Identificador opaco del disparo (no es de fila) |
| `fecha` | Día local de operación; agrupa el slot diario |
| `en_ventana` | `true` si el disparo respondió a un tick de agenda (denominador del SLO) |
| `inicio_previsto` | Tick al que respondió (`null` fuera de ventana) |
| `inicio_real` / `fin` | Ejecución real, para atraso y duración |
| `resultado` | `completada`, `falla`, `omitida_ventana`, `omitida_lock`, `omitida_duplicada` |
| `detalle` | Sólo en `falla`: código cerrado (`entrada_inaccesible`, `scheduler_corrida_error`, el `code` de la corrida) |
| `corrida` | Sólo en `completada`: conteos cerrados del informe, **sin** el detalle por fila |
| `mantenimiento` | Sólo cuando corrió el slot diario: `purga`/`respaldo` con `completada`, `falla` o `pendiente` |

El log nunca lleva payload, contenido generado, filas ni datos de
contacto. Las omitidas se asientan porque #88 mide la agenda comprometida
contra lo ejecutado, no contra lo que ocurrió.

## 6. Mantenimiento diario

La primera corrida en ventana de cada fecha corre el **slot diario**:

1. `purga` (#87): invoca `scripts/purgar_registro.py` como subproceso con
   `--registro $AGENTE1_SCHEDULER_REGISTRO_CONFIRMACIONES --salida
   <directorio>`; deja su propio log en
   `logs/confirmaciones-hu012.jsonl`. Una purga fallida se reintenta en el
   tick siguiente del mismo día.
2. `respaldo` (#86): **futuro**. El scheduler lo declara `pendiente` cada
   día para que el hueco quede a la vista hasta que el comando exista;
   cuando se implemente, entra como paso posterior a la purga (ADR 0009:
   ningún respaldo conserva texto que la retención ya venció).

## 7. Instalación en el host (operador designado)

Con la identidad técnica y las `AGENTE1_WORKSPACE_*` ya provistas por DSI
(runbook D2/D3):

```bash
# 1. Checkout en el host y dependencias
cd <CHECKOUT>/Implementacion/Agente1 && uv sync --frozen

# 2. Verificar el camino manual primero (misma invocación que el timer)
PYTHONPATH=src python -m agente1 insumos-agentes \
  --directorio ~/agente1/salida --live --confirm-write-workspace \
  --ollama-model <modelo>

# 3. Env file del scheduler (no versionar: va la config completa)
mkdir -p ~/.config/agente1
$EDITOR ~/.config/agente1/scheduler.env   # AGENTE1_* según §3
chmod 600 ~/.config/agente1/scheduler.env

# 4. Unidades: copiar las plantillas y reemplazar __CHECKOUT__/__MODELO_OLLAMA__
mkdir -p ~/.config/systemd/user
cp systemd/agente1-scheduler.{service,timer} ~/.config/systemd/user/
$EDITOR ~/.config/systemd/user/agente1-scheduler.service
systemctl --user daemon-reload
systemctl --user enable --now agente1-scheduler.timer

# 5. Para que el timer corra sin sesión iniciada (host de demo)
loginctl enable-linger "$USER"
```

Alternativa con bucle: instalar `agente1-scheduler-loop.service` en lugar
del par service+timer y `enable --now` esa unidad. No habilitar ambas.

Ensayo sin instalar nada (cambia `--live` por `--tabla` para offline):

```bash
uv run python -m agente1 scheduler --una-corrida --ahora 2026-10-05T10:00:00-03:00 \
  --tabla insumos.csv --directorio ~/agente1/salida --fake-output "salida"
```

## 8. Parar, diagnosticar, migrar

| Acción | Comando |
|---|---|
| Parar el timer | `systemctl --user disable --now agente1-scheduler.timer` |
| Parar el bucle | `systemctl --user disable --now agente1-scheduler-loop` |
| Estado | `systemctl --user status agente1-scheduler.timer`, `journalctl --user -u agente1-scheduler.service` |
| Log de corridas | `<directorio>/logs/scheduler-corridas.jsonl` (ver §5) |
| Corrida manual de contingencia | `python -m agente1 insumos-agentes ...` (README §insumos) |

Fallas frecuentes (el `detalle` del log o el JSON de salida):

| Código | Revisar |
|---|---|
| `scheduler_config_invalid` / `scheduler_config_unknown_key` | Variables `AGENTE1_SCHEDULER_*` del env file |
| `entrada_inaccesible` | `--tabla` inexistente (offline) |
| `workspace_*` / `insumos_config_*` | Variables Workspace e identidad técnica (runbook D2/D3) |
| `scheduler_corrida_error` | Corrida fallida sin código propio: ver journal |
| `scheduler_log_invalid` | El JSONL está corrupto: no se procesa hasta revisarlo |
| `omitida_lock` sostenida | Un disparo anterior sigue corriendo o murió con el lock (es de archivo: se libera con el proceso) |

**Migrar a otro host** (ADR 0007): la operación es del operador designado
en cada host; el functional ownership es de la SEU y la evolución de los
estudiantes que continúan.

1. En el host nuevo: checkout, `uv sync`, verificar el camino manual y la
   lectura live con la identidad técnica vigente.
2. Copiar el env file (con las credenciales por el canal que DSI autorice)
   y las unidades ajustando `__CHECKOUT__`.
3. Habilitar el timer, esperar una corrida `completada` en el log y sólo
   entonces `disable --now` la unidad del host viejo.
4. El directorio de salida (registro de idempotencia, borradores, log) se
   migra con los mecanismos de DSI; si se empieza vacío, las filas ya
   procesadas quedan protegidas por el `estado` escrito en la pestaña (la
   corrida no vuelve a tocarlas) y el `correlation_id` de cada fila sigue
   registrando despachos nuevos desde cero.
