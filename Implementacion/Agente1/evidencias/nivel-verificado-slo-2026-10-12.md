# Nivel verificado de los SLO desde la auditoría (#88)

- **Instante de corte:** 2026-10-13T00:09:49.440169+00:00 — los ticks y eventos posteriores a él no entran a las muestras.
- **Rango medido:** 2026-10-12 a 2026-10-12 (fechas locales de la ventana).
- **Configuración declarada:** intervalo de sondeo 10 s; ventana días [1, 2, 3, 4, 5, 6, 7] de 21:04 a 21:09 (America/Argentina/Buenos_Aires). Sale de `AGENTE1_SCHEDULER_*`, igual que el scheduler.
- **Muestra mínima declarada:** 20 observaciones por indicador; debajo de eso se declara `muestra insuficiente` en vez de publicar un número.
- **Comando que produjo este corte:**

```bash
medir_nivel_slo.py --directorio salida/slo-demo-2026-10-12 --desde 2026-10-12 --hasta 2026-10-12 --respuestas-csv salida/slo-demo-2026-10-12/respuestas-form-pedidos.csv --md evidencias/nivel-verificado-slo-2026-10-12.md
```

## Indicadores

| SLO | Definición | Objetivo | n | Nivel verificado | Cumple |
|---|---|---|---|---|---|
| disponibilidad | corridas programadas completadas a tiempo / corridas programadas, dentro de la ventana de operación | 99 % | 30 | 1.0000 | sí |
| tiempo_atencion | desde el envío del Form de pedido hasta el aviso con el resultado (incluye la espera hasta la corrida) | <= 310 s (intervalo de sondeo + 5 min) | 4 | muestra insuficiente (n=4) | — |
| latencia_por_pieza | p95 de la latencia de generación por tipo de pieza (interna, alimenta eficiencia de desempeño) | pendiente #50/#51 (se fija con la medición sobre el modelo elegido) | 3 | pendiente #50/#51 | — |
| aprobacion_envio | desde la doble aprobación (plantilla y lote) hasta el envío; ENVIO_INDETERMINADO cuenta como incidente fuera de la muestra | <= 20 s dentro de la ventana (2 x sondeo) | 3 | muestra insuficiente (n=3) | — |
| integridad_gate | piezas en validación humana que pasaron el gate: 100 %, y 0 no conformes presentadas como conformes | 100 % | 9 | muestra insuficiente (n=9) | — |

### disponibilidad

```json
{
  "atraso_inicio_s": {
    "max_s": 0.002,
    "min_s": 0.001,
    "n": 30,
    "p95_s": 0.002
  },
  "completadas_a_tiempo": 30,
  "completadas_tardias": 0,
  "corridas_disparadas": 30,
  "corridas_programadas": 30,
  "duracion_corrida_s": {
    "max_s": 0.009,
    "min_s": 0.0,
    "n": 30,
    "p95_s": 0.001
  },
  "entradas_fuera_de_agenda": 0,
  "entradas_fuera_de_ventana": 0,
  "estado_fuente": "ok",
  "falladas": 0,
  "fuente": "logs/scheduler-corridas.jsonl",
  "omitidas_sin_completar": 0,
  "sin_disparo": 0
}
```

### tiempo_atencion

```json
{
  "atendidos_en_rango": 5,
  "atendidos_sin_fila_en_csv": 0,
  "aviso_enviada": 5,
  "aviso_rechazada_o_fallida": 0,
  "deltas_negativos_descartados": 1,
  "estado_fuente": "ok",
  "filas_respuestas": 6,
  "fuente": "atendidos-canal-form.jsonl",
  "marcas_no_parseables": 0,
  "nota": "la marca temporal del CSV se interpreta en la zona de la ventana de operación cuando viene sin zona",
  "respuestas_csv": "respuestas-form-pedidos.csv",
  "respuestas_sin_atender": 0
}
```

### latencia_por_pieza

```json
{
  "por_tipo": {
    "gacetilla": {
      "estado_fuente": "ok",
      "log": "logs/ejecuciones.jsonl",
      "max_s": 0.0,
      "min_s": 0.0,
      "modelos": [
        "fake-determinista",
        "fake-offline"
      ],
      "n": 2,
      "p95_s": 0.0
    },
    "linea_descriptiva": {
      "estado_fuente": "ausente",
      "log": "logs/lineas-descriptivas.jsonl",
      "max_s": null,
      "min_s": null,
      "n": 0,
      "p95_s": null,
      "sin_latencia_s": true
    },
    "plantilla_correo_actividad": {
      "estado_fuente": "ok",
      "log": "logs/plantillas-actividad.jsonl",
      "max_s": 0.0,
      "min_s": 0.0,
      "modelos": [
        "fake-determinista"
      ],
      "n": 1,
      "p95_s": 0.0
    },
    "post": {
      "estado_fuente": "ok",
      "log": "logs/ejecuciones.jsonl",
      "max_s": null,
      "min_s": null,
      "n": 0,
      "p95_s": null
    }
  }
}
```

### aprobacion_envio

```json
{
  "delta_en_ventana_s": {
    "max_s": 0.0,
    "min_s": 0.0,
    "n": 3,
    "p95_s": 0.0
  },
  "delta_total_s": {
    "max_s": 0.079,
    "min_s": 0.059,
    "n": 3,
    "p95_s": 0.078
  },
  "fuentes": {
    "decisiones": "ok",
    "lotes": "ok",
    "registro": "ok"
  },
  "incidentes_fallida": 0,
  "incidentes_indeterminado": 0,
  "items_encolados_en_rango": 3,
  "items_entregados": 3,
  "items_pendientes": 0,
  "items_sin_ancla": 0,
  "items_sin_registro": 0,
  "lotes_autorizados": 1,
  "nota": "la muestra descuenta el tiempo fuera de la ventana de operación; `delta_total_s` muestra el reloj completo",
  "registros_fuera_del_circuito_entregados": 0,
  "registros_fuera_del_circuito_incidentes": 0
}
```

### integridad_gate

```json
{
  "verificaciones": [
    {
      "alcance": "generacion",
      "por_log": {
        "ejecuciones.jsonl": {
          "estado_fuente": "ok",
          "presentadas": 2,
          "violaciones": 0
        },
        "lineas-descriptivas.jsonl": {
          "estado_fuente": "ausente",
          "presentadas": 0,
          "violaciones": 0
        },
        "plantillas-actividad.jsonl": {
          "estado_fuente": "ok",
          "presentadas": 1,
          "violaciones": 0
        }
      },
      "presentadas": 3,
      "violaciones": 0
    },
    {
      "alcance": "artefactos_locales",
      "archivos": 3,
      "conformes": 3,
      "estado_fuente": "ok",
      "violaciones": 0
    },
    {
      "alcance": "envios",
      "conformes": 3,
      "emitidas_sin_traza": 0,
      "presentadas": 3,
      "violaciones": 0
    }
  ],
  "violaciones_detalle": [],
  "violaciones_total": 0
}
```

## Huecos declarados

- lineas-descriptivas.jsonl no registra `latencia_s`: la línea descriptiva queda sin medición aunque genere piezas

Los objetivos que dependen de #50/#51 quedan declarados `pendiente` y ningún indicador inventa un número: donde la muestra o la fuente no alcanza, la celda lo dice.
