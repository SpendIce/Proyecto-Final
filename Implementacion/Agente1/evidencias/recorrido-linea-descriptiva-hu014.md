# Recorrido — línea descriptiva del certificado HU-014 (#74)

## Qué demuestra

- Que el modelo redacta **una línea descriptiva por actividad** con gates
  deterministas, y que una salida no conforme (carga horaria escrita por el
  modelo, más de una línea, extensión excesiva, hechos del registro como
  modalidad o fechas) se rechaza antes de llegar a validación.
- Que la línea se aprueba **una vez por actividad** por el Form de
  decisiones con el mismo circuito que una plantilla: `apruebo_semantica`
  del RGC y `apruebo_utilitaria` del Coordinador de Extensión sobre el
  objeto `linea_descriptiva-<id_actividad>-<hash de la línea>`.
- Que `procesar_certificado` no emite ningún PDF con línea si falta el
  `RegistroDecisiones`, el lote de cierre declarado, cualquiera de las dos
  aprobaciones de la línea o la `apruebo_lote` del lote, y que cada falta
  devuelve un código distinto.
- Que con todo aprobado el documento sale por el fake con la línea y las
  variables del registro (modalidad, carga horaria) interpoladas por la
  plantilla determinista, nunca escritas por el modelo.
- Que la aprobación ata el texto exacto: modificar la línea después de
  aprobarla produce otro objeto de decisión, sin decisiones registradas.

## Qué NO demuestra

El recorrido offline no acredita la verificación de identidad de Google ni
la hoja real del Form: las respuestas se leen de un CSV igual que en #72, y
el atributo «verificado por Google» sólo existe cuando el Form real lo
recolecta. La autorización por rol sí se ensaya de verdad contra el padrón
externo.

No demuestra la emisión en vivo del certificado: eso es alcance de #75, que
consume la misma clave de decisión documentada acá y en el README. Tampoco
genera la línea con un modelo real en este recorrido: el pipeline de
generación se ejercita en `tests/test_linea_descriptiva.py` con el
generador fake, y el paso 1 de abajo usa el mismo puerto con cualquier
generador que se le inyecte (Ollama en la corrida live del operador).

## Antes de empezar

- No hace falta cuenta de Google ni credenciales: las respuestas del Form
  son un CSV y el registro vive en `<directorio>/estado-decisiones/`.
- Una terminal en `Implementacion/Agente1` y un directorio de trabajo
  compartido entre los runners, como en
  `evidencias/recorrido-registro-decisiones-form.md`.
- El padrón es un CSV `correo,rol` externo al repo con correos inventados;
  en producción lo arma la SEU.

## Paso a paso (offline)

### 1. Generar la línea de una actividad

```bash
cd Implementacion/Agente1
PYTHONPATH=src python - <<'EOF'
from pathlib import Path
from agente1.linea_descriptiva import generar_linea_descriptiva
from agente1.procesamiento import FakeGenerator

fila = {
    "id_actividad": "SYN-001",
    "titulo": "Taller de robótica educativa",
    "descripcion": "Taller de práctica para acercar la ingeniería "
                   "a la comunidad con propuestas de extensión abiertas.",
    "publico": "estudiantes de todas las carreras",
}
resultado = generar_linea_descriptiva(
    fila=fila,
    directorio_salida=Path("/tmp/demo-hu014-linea"),
    generator=FakeGenerator(
        "Espacio de formación docente en tecnología aplicada a la enseñanza."
    ),
)
print(resultado.estado)       # PENDIENTE_VALIDACION
print(resultado.linea)        # la línea normalizada
print(resultado.objeto_id)    # linea_descriptiva-SYN-001-<sha256>
EOF
```

El prompt sólo recibió `titulo`, `descripcion` y `publico`: fecha, carga,
modalidad y contacto nunca entran, así que el modelo no puede copiar un
hecho que no vio. La auditoría quedó en
`/tmp/demo-hu014-linea/logs/lineas-descriptivas.jsonl` con
`input_hash`/`output_hash` y el objeto, sin el texto.

Para ver el gate rechazar la carga horaria escrita por el modelo, el caso
negativo del ticket:

```bash
PYTHONPATH=src python - <<'EOF'
from pathlib import Path
from agente1.linea_descriptiva import generar_linea_descriptiva
from agente1.procesamiento import FakeGenerator

resultado = generar_linea_descriptiva(
    fila={"id_actividad": "SYN-001", "titulo": "X", "descripcion": "Y"},
    directorio_salida=Path("/tmp/demo-hu014-linea"),
    generator=FakeGenerator("Formación con una carga de 40 horas."),
)
print(resultado.estado)              # FALLIDA
print(resultado.validation_errors)   # ('unauthorized_number', 'unauthorized_duration')
EOF
```

### 2. Declarar la línea y el lote de cierre como objetos de decisión

```bash
mkdir -p /tmp/demo-decisiones
cat > /tmp/demo-decisiones/padron.csv <<'EOF'
correo,rol
rgc@example.invalid,RESPONSABLE_GESTION_CONOCIMIENTO
coord@example.invalid,COORDINADOR_EXTENSION
EOF

OBJETO=$(PYTHONPATH=src python - <<'EOF'
from agente1.linea_descriptiva import objeto_id_linea_descriptiva
print(objeto_id_linea_descriptiva(
    "SYN-001",
    "Espacio de formación docente en tecnología aplicada a la enseñanza.",
))
EOF
)

# La "hoja" vacía de respuestas: el runner la exige en offline aunque sólo
# se esté declarando.
cat > /tmp/demo-decisiones/vacio.csv <<'EOF'
Marca temporal,Correo,Tipo de decisión,Objeto de la decisión,Decisión
EOF

PYTHONPATH=src python scripts/registrar_form_decisiones.py \
  --directorio /tmp/demo-decisiones \
  --respuestas-csv /tmp/demo-decisiones/vacio.csv \
  --padron /tmp/demo-decisiones/padron.csv \
  --declarar "linea_descriptiva:$OBJETO" \
  --declarar "lote:lote-cierre-syn-001"
```

El runner imprime el objeto y los links prellenados de las dos decisiones
de la línea (semántica y utilitaria) más el del lote. En el flujo real el
emisor del correo los declara con `declarar_linea_pendiente` y los adjunta
en el aviso al par de roles; sin esta declaración la respuesta del Form se
rechaza como `objeto_inexistente`.

### 3. Registrar las tres decisiones del Form

```bash
cat > /tmp/demo-decisiones/respuestas.csv <<EOF
Marca temporal,Correo,Tipo de decisión,Objeto de la decisión,Decisión
2026-10-11 09:00:00,rgc@example.invalid,linea_descriptiva,$OBJETO,apruebo_semantica
2026-10-11 09:05:00,coord@example.invalid,linea_descriptiva,$OBJETO,apruebo_utilitaria
2026-10-11 09:10:00,coord@example.invalid,lote,lote-cierre-syn-001,apruebo_lote
EOF

PYTHONPATH=src python scripts/registrar_form_decisiones.py \
  --directorio /tmp/demo-decisiones \
  --respuestas-csv /tmp/demo-decisiones/respuestas.csv \
  --padron /tmp/demo-decisiones/padron.csv
```

Las tres salen `registrada` y quedan en
`/tmp/demo-decisiones/estado-decisiones/decisiones-procesadas.jsonl` con
identidad hasheada y rol. Una cuarta fila con la semántica firmada por
`coord@example.invalid` saldría `rechazada` con `rol_no_corresponde`: la
semántica no la da el Coordinador ni la utilitaria el RGC.

### 4. Emitir el certificado con todo el circuito

```bash
PYTHONPATH=src python - <<'EOF'
from pathlib import Path
from agente1.certificados import (
    DestinoCertificadosFake, RegistroCertificadosMemoria,
    SolicitudCertificado, procesar_certificado,
)
from agente1.confirmaciones import (
    AprobacionHumana, ROL_APROBACION_SEMANTICA, ROL_APROBACION_UTILITARIA,
)
from agente1.decisiones_form import RegistroDecisiones

decisiones = RegistroDecisiones("/tmp/demo-decisiones/estado-decisiones")
registro = RegistroCertificadosMemoria()
destino = DestinoCertificadosFake()
solicitud = SolicitudCertificado(
    id_certificado="CERT-001",
    nombre_titular="Ana Pérez",
    documento_titular="30123456",
    tipo_certificado="APROBACION",
    actividad="Taller de robótica educativa",
    fecha="28 de agosto de 2026",
    organiza="Secretaría de Extensión Universitaria",
    firmante="Coordinación de Extensión",
    id_actividad="SYN-001",
    linea_descriptiva=(
        "Espacio de formación docente en tecnología aplicada a la enseñanza."
    ),
    modalidad="presencial",
    carga_horaria="6 horas",
)

def aprobacion(rol):
    return AprobacionHumana(
        aprobada=True, validador=f"Simulado {rol}", rol=rol,
        fecha_iso="2026-10-11T12:00:00+00:00",
    )

procesar_certificado(
    solicitud=solicitud, directorio_salida=Path("/tmp/demo-hu014"),
    registro=registro, aprobacion=aprobacion(ROL_APROBACION_SEMANTICA),
)
resultado = procesar_certificado(
    solicitud=solicitud, directorio_salida=Path("/tmp/demo-hu014"),
    registro=registro, aprobacion=aprobacion(ROL_APROBACION_UTILITARIA),
    emitir=True, destino=destino,
    decisiones=decisiones, lote_cierre="lote-cierre-syn-001",
)
print(resultado.estado)  # EMITIDA_SIMULADA
EOF
```

El PDF simulado queda en el fake con la línea aprobada, `Modalidad:` y
`Carga horaria:` interpoladas por la plantilla. La auditoría de
`/tmp/demo-hu014/logs/certificados-hu014.jsonl` registra
`descriptive_line_hash`, `linea_objeto_id` y `closing_batch_id`, nunca el
texto.

### 5. Los casos negativos bloquean la emisión

El mismo script con variantes muestra cada código:

- Sin `decisiones` ni `lote_cierre`: `decisions_registry_required` y
  `closing_batch_required` respectivamente.
- Con sólo la fila de `apruebo_semantica` en el CSV del paso 3:
  `descriptive_line_unapproved` (la aprobación parcial no habilita).
- Con las dos de la línea pero sin la fila del lote:
  `closing_batch_unapproved`.
- Con `linea_descriptiva` distinta de la aprobada: también
  `descriptive_line_unapproved`, porque el hash cambia el objeto.
- Con `linea_descriptiva="Formación con una carga de 40 horas."` u otra
  que no pase los gates: `descriptive_line_invalid` en la entrada, antes
  de tocar el registro.

`scripts/matriz_hu014.py` corre los 20 casos del ciclo (los 12 del
lifecycle más los 8 del circuito de la línea) y deja el resumen en
`salida/matriz-hu014/matriz.json`:

```bash
PYTHONPYCACHEPREFIX=/tmp/agente1-pycache \
  python scripts/matriz_hu014.py --salida salida/matriz-hu014
```

## Corrida live (operador, D2)

Queda pendiente de la ejecución del operador en D2, igual que en #72: el
Form real con correo verificado y padrón institucional, la línea generada
contra el modelo del ambiente y las tres decisiones cargadas por las
personas. La emisión en vivo del certificado con lista de participantes es
alcance de #75; este recorrido deja verificable la precondición que esa
emisión va a exigir.
