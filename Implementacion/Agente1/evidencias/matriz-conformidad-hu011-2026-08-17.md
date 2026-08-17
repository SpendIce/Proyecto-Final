# Matriz de conformidad contractual simulada — HU-011

- **Fecha de corte:** 17 de agosto de 2026
- **Estado:** evidencia técnica reproducible
- **Origen:** `SIMULADA`
- **Generador:** `FAKE_DETERMINISTA`
- **Revisión humana:** `PENDIENTE`
- **Calidad institucional evaluada:** no
- **TRL 3 acreditado:** no

## Objetivo

Verificar offline que el flujo público de HU-011 genera borradores separados
para Instagram y LinkedIn, aplica el contrato mecánico provisional, conserva
trazabilidad y rechaza actividades incompletas antes de invocar al generador.

## Cobertura

| Perfil | Actividades | Canales por actividad | Ejecuciones | Resultado esperado |
|---|---:|---:|---:|---|
| Completas | 3 | 2 | 6 | `PENDIENTE_VALIDACION`, borrador idéntico al golden |
| Incompletas | 2 | 2 | 4 | `INCOMPLETA`, sin generador y sin borrador |
| **Total** | **5** | — | **10** | **6 pendientes + 4 incompletas** |

Los seis borradores contractuales están versionados en `golden/posts/`. Cada
ejecución registra correlation ID y hashes de entrada/salida, además de las
versiones efectivas de contrato, política y prompt. El resumen `matriz.json`
no copia textos, contactos, prompts ni datos fuente.

## Reproducción

Desde `Implementacion/Agente1`:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python scripts/matriz_hu011.py --salida salida/matriz-hu011
```

Smoke acotado a una actividad completa en ambos canales:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  bash scripts/smoke_posts.sh salida/smoke-hu011
```

La evidencia recuperable de una corrida está en el directorio de salida
ignorado por Git: `matriz.json`, logs JSONL y borradores. Los goldens y el
runner permiten repetir la comprobación sin depender de servicios externos.

## Frontera epistemológica

- El gate implementa un **grounding mecánico conservador**: exige la fecha y
  los hechos críticos literales de la fuente, y rechaza patrones cerrados de
  hechos o acciones no autorizados.
- Ese gate no realiza una evaluación semántica integral ni garantiza la
  ausencia de alucinaciones; la revisión humana de la SEU es obligatoria.
- El fake prueba contrato, controles y reproducibilidad; **no evalúa la calidad de Ollama**.
- La igualdad con goldens no constituye una evaluación humana ni valida tono institucional.
- Las políticas de longitud y hashtags siguen marcadas como `PROVISIONAL_NO_INSTITUCIONAL`.
- No se invocan APIs de Instagram o LinkedIn y no se publica, comparte ni envía contenido.
- No existe validación atribuible a la SEU en esta evidencia.
- HU-011 no cumple todavía su DoD institucional y esta matriz no acredita el Gate TRL 3.

La evaluación pendiente debe usar
`checklist-validacion-humana-hu011.md` por cada borrador/canal y registrar al
revisor designado, la decisión y una referencia recuperable.
