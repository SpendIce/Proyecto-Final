"""Anexo 1 del laboratorio: presentación del proyecto por estrato.

Lee la tabla fuente del perfil de calidad (la misma que alimenta el Anexo 2,
``Documentos/Laboratorio/Perfil-Calidad-Sistema-Demostracion-v1.md``) y emite la
presentación del sistema de demostración organizada por **estrato** (componente),
en el orden del inventario, con el estado de implementación y el motivo de cada
atributo declarado por el autor.

La salida no inventa datos: las tablas por estrato se derivan de la tabla fuente
y las cifras y los estados son los mismos que usa el Anexo 2, así que no hay dos
números para lo mismo. La sección de seguridad **remite** al Anexo 3 y no la
reescribe (issue #58/#108).

Este anexo es donde vive la declaración del autor: los Anexos 2 y 3 sólo llevan
los ítems que después completa el laboratorio, así que el estado, el motivo y la
evidencia quedan acá, en las tablas por componente y en la Lista de Control.

Dos salidas, con dos propósitos distintos:

- **Proyección en Markdown** (``Anexo1-Presentacion-v1.md``): la vista de
  trabajo. Es interna: no se entrega.
- **Entrega sobre la plantilla oficial** (``--plantilla``): el ``.docx`` que sí
  va al laboratorio, volcado sobre ``3.1 - Anexo 1 - Presentación 2025.docx``.

Uso:

    uv run python scripts/anexo1_presentacion.py
        # escribe Documentos/Laboratorio/Anexo1-Presentacion-v1.md

    uv run --with python-docx python scripts/anexo1_presentacion.py \\
        --plantilla "Contenido/DocumentacionAnteproyecto/Revision-Laboratorio-2025/3.1 - Anexo 1 - Presentación 2025.docx" \\
        --docx Documentos/Laboratorio/Entrega/Anexo1-Presentacion.docx
        # escribe la entrega sobre la plantilla oficial. Requiere python-docx.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from anexo2_calidad import FilaFuente, parsear_fuente  # noqa: E402
from anexos_seleccion import (  # noqa: E402
    TOPE_POR_COMPONENTE,
    seleccionar_calidad,
)
from plantilla_laboratorio import (  # noqa: E402
    TITULO_PROYECTO,
    abrir_plantilla,
    buscar_parrafo,
    guardar,
    reemplazar_parrafo,
)

FUENTE = REPO / "Documentos" / "Laboratorio" / "Perfil-Calidad-Sistema-Demostracion-v1.md"
SALIDA_MD = REPO / "Documentos" / "Laboratorio" / "Anexo1-Presentacion-v1.md"

# Orden de los estratos del inventario de componentes del sistema de
# demostración. `Sistema` agrupa los atributos transversales que ninguna capa
# ejerce sola.
ORDEN_ESTRATOS = [
    "Canal",
    "Interpretación",
    "Generación",
    "Gates",
    "Control de pagos",
    "Aprobación",
    "Cola y envío",
    "Persistencia y auditoría",
    "Integraciones",
    "Sistema",
]

ETIQUETA_ESTRATO = {
    "Sistema": "Sistema (atributos transversales)",
}

DESCRIPCION_ESTRATO = {
    "Canal": (
        "Transporta pedidos de la SEU hacia el agente y resultados hacia la "
        "persona. No es una conversación abierta y no verifica identidad: la "
        "identidad llega afirmada por el canal y el rol sale de un padrón "
        "externo."
    ),
    "Interpretación": (
        "Clasifica la solicitud a una intención de un catálogo cerrado (o la "
        "rechaza) y resuelve la actividad por identificador, por búsqueda "
        "difusa determinística o por repregunta; nunca aproxima a la intención "
        "más parecida."
    ),
    "Generación": (
        "Produce las piezas como borrador (gacetilla, post, plantilla de correo "
        "por actividad y certificado con línea descriptiva) con gate mecánico "
        "de salida antes de escribir."
    ),
    "Gates": (
        "Controles fail-closed que deciden antes de generar, escribir o tocar el "
        "registro: política de redes, catálogo cerrado de tipos de notificación "
        "y matriz de orígenes de inscripción."
    ),
    "Control de pagos": (
        "Deriva la situación de pago de cada preinscripto desde las fuentes en "
        "cada corrida, como función pura sin estado propio, y planifica el lote "
        "de recordatorios y los candidatos a confirmación de inscripción."
    ),
    "Aprobación": (
        "Registra la validación humana: aprobaciones semántica y utilitaria por "
        "actividad, aprobación de lote y decisión de publicación, con identidad "
        "verificada por Google y rol tomado de un padrón."
    ),
    "Cola y envío": (
        "Encola y entrega lo aprobado con idempotencia durable, reconciliación "
        "de reservas colgadas a envío indeterminado y retención acotada del "
        "registro; el único envío automático es la confirmación de inscripción."
    ),
    "Persistencia y auditoría": (
        "Audita y opera las evidencias del sistema: invariantes de seguridad "
        "sobre manifiestos sanitizados, contratos operativos fail-closed y "
        "medición del nivel verificado de los SLO. Expone códigos, conteos y "
        "hashes, nunca contenido ni destinatarios."
    ),
    "Integraciones": (
        "Fuentes, destinos y servicios externos detrás de puertos: planilla de "
        "actividades, Docs y Drive, Gmail (envío y buzón propio), Google Forms, "
        "Ollama local y los insumos de los agentes A3 a A5."
    ),
    "Sistema": (
        "Atributos transversales que ninguna capa ejerce sola: ausencia de "
        "fallos, disponibilidad, operabilidad, mantenibilidad, instalabilidad y "
        "los atributos de calidad de datos que dependen del dueño funcional."
    ),
}

MOTIVO_SEGURIDAD_REMITE = (
    "El perfil de seguridad de este estrato se declara en el Anexo 3 del "
    "laboratorio (perfil de seguridad del sistema de demostración, issues #58 y "
    "#108); este anexo lo remite y no lo reescribe."
)

INTRO_DETALLE = (
    "Atributos tenidos en cuenta en cada componente, con el estado de "
    "implementación declarado por el autor y su motivo. La escala de estados es "
    "la de la revisión de laboratorio: A implementado satisfactoriamente, B "
    "implementado con observaciones, C tenido en cuenta sin implementar y D "
    "desconocido o ignorado expresamente (D lo asigna el laboratorio). Los "
    "factores de (ciber)seguridad de cada estrato se declaran en el Anexo 3."
)

ATRIBUTO_SEGURIDAD = "Factores de (ciber)seguridad del estrato"

# Anchos en centímetros de las columnas `Atributo | Estado | Motivo` (el ancho
# útil de la plantilla es de 15 cm). La plantilla oficial los define desiguales;
# el `Motivo` es el que lleva texto, así que se queda con la mayor parte. Se
# guardan en centímetros y se convierten dentro del emisor para no importar
# `python-docx`, que es dependencia opcional, al cargar el módulo.
ANCHOS_COLUMNAS_CM = (5.0, 1.7, 8.3)

# Cuerpo de las tablas por componente, en puntos.
TAMANO_TABLA_PT = 9

# --- Prosa del documento -----------------------------------------------------
# Estos textos se reproducen en el Markdown versionado y en el Word. No
# introducen cifras nuevas: las cifras y los estados de las tablas salen de la
# tabla fuente, y las fechas institucionales son las del anteproyecto y del
# glosario (`CONTEXT.md`).

REFERENCIA_FOTO = (
    "Las tablas de este anexo se derivan de la tabla fuente del perfil de "
    "calidad del sistema de demostración "
    "(`Documentos/Laboratorio/Perfil-Calidad-Sistema-Demostracion-v1.md`), la "
    "misma que alimenta el Anexo 2: foto del corte del 23/10/2026, versión del "
    "agente 0.5.4 (tag `agente1-v0.5.4`), con el sistema corriendo en "
    "contenedores en el servidor de la facultad (ADR 0013), los siete tipos de "
    "gacetilla declarados (#121), el set de evaluación de dos ejes (#111), el "
    "tipo en el canal (#122) y el modelo `gemma4:e4b` (#51). El perfil de "
    "seguridad no se declara acá: cada estrato remite al Anexo 3."
)

CONCEPTO_GENERAL = [
    (
        "El Agente 1 (Extensión Bot) es el agente de comunicación institucional "
        "del Proyecto Centenario (P100) de la Facultad de Ingeniería del "
        "Ejército (FIE), Universidad de la Defensa Nacional. Prepara piezas "
        "comunicacionales para la Secretaría de Extensión Universitaria (SEU) "
        "dentro del Proceso 4: gacetillas, publicaciones para redes sociales, "
        "correos y confirmaciones, y certificados. Su producto es "
        "siempre un borrador: el agente no publica, no difunde ni decide; toda "
        "pieza que llega a un destinatario o a una publicación pasó por una "
        "validación humana registrada, y cada salida queda marcada como "
        "pendiente de validación."
    ),
    (
        "El proyecto se desarrolla a lo largo de un año académico (dos "
        "semestres de 2026) con maduración progresiva por niveles TRL: el "
        "objetivo del primer semestre es TRL 3 y el del segundo, TRL 4, en "
        "ambos casos sujeto a la decisión del gate correspondiente. Se ejecuta "
        "sobre tecnologías de código abierto y sobre la suite institucional "
        "Google Workspace; los modelos de lenguaje corren localmente (Ollama) "
        "como medida de diseño para preservar la soberanía de los datos "
        "institucionales. La estimación de costos del año de alcance se ubica "
        "en el rango de USD 0 a USD 1.400, según se utilicen o no componentes "
        "opcionales de infraestructura, respaldo o contingencia."
    ),
    (
        "Este documento es el Anexo 1 de la revisión de laboratorio: presenta el "
        "sistema de demostración (el Agente 1 en todo su alcance declarado, "
        "funcionando de punta a punta en vivo) y su perfil de calidad por "
        "estrato. El detalle por atributo, en el orden del estándar, está en el "
        "Anexo 2; el perfil de seguridad, en el Anexo 3."
    ),
]

ENFOQUE = [
    (
        "**Enfoque iterativo-incremental con gates por semestre.** El proyecto "
        "sigue los cinco pasos metodológicos del Director del Proyecto "
        "(relevamiento, diseño, prototipado, validación y documentación) y se "
        "gestiona con un tablero Kanban. Cada semestre cierra en un gate de "
        "evaluación TRL con su paquete de evidencia; ningún gate se declara "
        "cerrado sólo por documentación narrativa ni por demostración informal."
    ),
    (
        "**Validación humana obligatoria.** El mecanismo es estructural y no "
        "puede deshabilitarse sin modificar el código: las piezas de difusión "
        "(gacetillas y posts) requieren la decisión de publicación registrada por "
        "quien publica o descarta el borrador; las piezas que el agente envía o "
        "emite (confirmaciones y certificados) requieren la plantilla aprobada "
        "más la aprobación de lote previa al envío."
    ),
    (
        "**Ejecución local, aislada y fail-closed.** Los modelos corren en "
        "infraestructura propia, en un contenedor sin salida a internet, y el "
        "agente falla cerrado en cada frontera: lo que no cumple se rechaza "
        "antes de generar, escribir o tocar el registro, y el contenedor no "
        "arranca si un archivo controlado no coincide con su versión. La "
        "auditoría guarda códigos, conteos y hashes, nunca contenido ni datos "
        "personales en claro."
    ),
    (
        "**Sistema de demostración sin capacidades detenidas.** El sistema corre "
        "en el servidor de la facultad, en contenedores desplegados desde el "
        "repositorio al cortar cada versión (ADR 0013): el modelo local "
        "(`gemma4:e4b` sobre Ollama) en un contenedor sin salida a internet y "
        "el agente sobre Google Workspace D2 con la cuenta de servicio de DSI. "
        "Lo que depende de un tercero (plantillas, firmas, política de redes, "
        "identidad del personal, unidad compartida de D3) corre contra un "
        "destino de prueba o un insumo provisional declarado, por el mismo "
        "mecanismo productivo y nunca contra un fake, con la meta de conseguir "
        "el original."
    ),
    (
        "**Alcance acotado y excluido.** El agente se limita a la comunicación "
        "institucional del Proceso 4 y a las historias HU-010 a HU-014. Queda "
        "fuera el reemplazo de personal, la publicación o el envío sin "
        "validación humana, la analítica y el scraping, la atención masiva al "
        "público, la infraestructura de alto costo y toda integración externa "
        "compleja no definida."
    ),
]

ESTADO_TRL_INTRO = (
    "Este anexo declara el estado de las capacidades contra el **gate TRL 4**. "
    "Las cifras y los estados de las tablas por estrato son los de la foto "
    "declarada en el corte del 23/10/2026, versión 0.5.4 (tag "
    "`agente1-v0.5.4`). La nota sobre fechas y "
    "estado verificado del anteproyecto conserva el corte del 21/09/2026; "
    "cuando uno y otro citan un número, corresponde a su propia fecha, y la "
    "revisión de laboratorio evalúa la foto de este anexo."
)

ESTADO_TRL_DEMOSTRADO = (
    "**Demostrado sobre el sistema de demostración.** El 23/10/2026, desde el "
    "contenedor del servidor y con la cuenta de servicio: smoke de lectura, "
    "gacetilla y posts de Instagram y LinkedIn de extremo a extremo con "
    "borrador real en la carpeta autorizada (sin modificar nada existente), "
    "el circuito completo de HU-012/HU-013 y de HU-014 contra destinos de "
    "prueba, el scheduler procesando un insumo de A3, el respaldo con su "
    "restauración, la vuelta atrás de versión y la recuperación ante una "
    "caída del proceso. HU-010 a HU-014 están "
    "implementadas dentro del alcance declarado: la gacetilla declara los "
    "siete tipos del corpus, dos que generan prosa con prompt propio "
    "(difusión de actividad y saludo o efeméride) y cinco que extraen y "
    "confirman sin prosa del modelo (crónica de evento, aviso de otra área, "
    "convocatoria interna, fallecimiento y newsletter), cada tipo con su forma "
    "declarada, su contrato de entrada y su gate, y un renderer único que "
    "escribe las partes institucionales fijas, que el modelo nunca escribe "
    "(#121); además post, plantilla de correo por actividad y certificado con "
    "línea descriptiva y circuito de lote. La suite y las "
    "matrices por historia las ejercitan, y cada fila A o "
    "B de las tablas por estrato cita su evidencia versionada y su paso en vivo."
)

ESTADO_TRL_NO_DEMOSTRADO = [
    (
        "La forma declarada de los siete tipos de gacetilla y su modo por tipo "
        "siguen sin aprobación institucional de la SEU: los archivos de forma "
        "están marcados `PROVISIONAL_NO_INSTITUCIONAL` y la aprobación entra "
        "por la validación humana obligatoria (issue #121)."
    ),
    (
        "La validación de calidad por referentes de la SEU: la operabilidad, la "
        "reconocibilidad de la adecuación y la prueba guiada de HU-013 están "
        "previstas y su validación registrada sigue pendiente (issue #56; la "
        "prueba guiada con una persona real de la SEU no se concretó)."
    ),
    (
        "El envío real por Gmail y los Forms reales de HU-012, HU-013 y HU-014: "
        "el circuito completo corre contra destinos de prueba declarados y la "
        "lista de prueba de Gmail; los Forms y las variables de la emisión real "
        "no están configurados en el servidor."
    ),
    (
        "La unidad compartida institucional de D3: el cómputo corre en el "
        "servidor de la facultad, pero los recursos de Google siguen siendo los "
        "de D2 (issue #100). El scheduler del contenedor queda apagado hasta "
        "configurar la pestaña de insumos."
    ),
    (
        "Los niveles verificados de los SLO de disponibilidad, tiempo de "
        "atención, aprobación a envío y RPO/RTO no tienen medición a la fecha "
        "(issue #88); la latencia por pieza sí está medida en el servidor. El "
        "perfil declara la ausencia en lugar de un número."
    ),
    (
        "El criterio formal del gate: la Dirección de carrera no fijó un criterio "
        "formal, la evidencia se presenta contra el TRL 4 de la documentación del "
        "P100 y el go/no-go lo fija el informe del laboratorio."
    ),
]

ESTADO_TRL_BRECHA = (
    "**Brecha de HU-011 cerrada en el gate, abierta en la validación.** Con el "
    "modelo de la demo (`gemma4:e4b`, issue #51) los posts en redacción libre "
    "superan el control de contenido: gacetilla y posts 48/48 en la medición "
    "del servidor, y los dos canales generados en vivo desde el contenedor el "
    "23/10/2026. Las mediciones anteriores con `llama3.2:3b` (1/6) quedaron "
    "superadas. Lo que sigue abierto es la validación editorial de la SEU, que "
    "entra por la validación humana obligatoria."
)

ESTADO_TRL_CIERRE = (
    "**El gate no está cerrado.** Este anexo declara estados por atributo, no el "
    "cierre del gate. El gate TRL 4 se acredita con el informe de la revisión de "
    "laboratorio, que habilita, habilita con condiciones o no habilita la "
    "presentación de cursada del 18 de noviembre de 2026. Hasta ese informe, este "
    "anexo no declara TRL 4 alcanzado."
)

LISTA_CONTROL = [
    (
        "Correr la suite completa (`uv run pytest -q`) y ver las matrices "
        "reproducibles por historia de usuario (`scripts/matriz_hu010.py`, "
        "`scripts/matriz_hu011_v2.py`, `scripts/matriz_hu012.py`, "
        "`scripts/matriz_hu014.py`). "
        "Evidencia: `tests/` y `evidencias/` del Agente 1."
    ),
    (
        "Recorrer el canal con un pedido ambiguo y ver la repregunta con "
        "candidatas sin persistir la prosa del pedido. "
        "Evidencia: `src/agente1/canal_form.py`, `src/agente1/interpretacion.py`; "
        "`tests/test_canal_form.py`, `tests/test_interpretacion.py`."
    ),
    (
        "Verificar el gate de generación sobre los casos adversariales: variable "
        "fuera de catálogo, dígito, fecha, importe, correo, enlace o hecho "
        "escritos por el modelo, eco de prompting y salida truncada. "
        "Evidencia: `src/agente1/procesamiento.py`, `src/agente1/politica_redes.py`; "
        "`tests/test_plantillas_actividad.py`, `tests/test_posts.py`, "
        "`tests/test_linea_descriptiva.py`, `tests/test_procesar_gacetilla.py`."
    ),
    (
        "Verificar la doble aprobación (semántica y utilitaria) y la aprobación "
        "de lote: sin las dos decisiones no hay encolado ni emisión, y editar la "
        "lista de cierre o la plantilla cambia el objeto y la aprobación previa "
        "deja de aplicar. "
        "Evidencia: `src/agente1/confirmaciones.py`, "
        "`src/agente1/linea_descriptiva.py`; `tests/test_confirmaciones.py`, "
        "`tests/test_linea_descriptiva.py`."
    ),
    (
        "Verificar la idempotencia durable y la reconciliación: una reserva "
        "colgada pasa a envío indeterminado sin reenviar y una re-corrida "
        "termina duplicada. "
        "Evidencia: `src/agente1/confirmaciones.py`; "
        "`tests/test_confirmaciones_durables.py`; "
        "`evidencias/recuperacion-hu012-idempotencia-durable-2026-09-08.md`."
    ),
    (
        "Verificar que la auditoría y los reportes exponen sólo códigos, conteos "
        "y hashes, sin destinatarios ni cuerpos. "
        "Evidencia: `src/agente1/auditoria_d2.py`, "
        "`src/agente1/operaciones_seguras.py`; "
        "`tests/test_auditoria_seguridad_d2.py`, `tests/test_operaciones_seguras.py`."
    ),
    (
        "Verificar los límites de escritura: escribir es siempre crear nuevo y "
        "el envío por Gmail opera cercado por la lista de prueba, con rechazo "
        "antes de tocar token o red. "
        "Evidencia: `src/agente1/destinos.py`, `src/agente1/gmail_envio.py`; "
        "`tests/test_destinos.py`, `tests/test_gmail_envio.py`."
    ),
    (
        "Verificar los insumos provisionales declarados: el sistema corre con "
        "ellos por el mecanismo productivo y ninguno queda como fake ni como "
        "capacidad detenida. "
        "Evidencia: el inventario de componentes del sistema de demostración "
        "(issue #67) y la columna Estado de los dos perfiles."
    ),
    (
        "Contrastar los estados declarados por estrato en este anexo con la "
        "proyección del Anexo 2 y con la del Anexo 3, de las que salen los ítems "
        "que evalúa el laboratorio. "
        "Evidencia: `Documentos/Laboratorio/Anexo2-Calidad-Proyeccion-v1.md`, "
        "`Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md`."
    ),
]


def proyectar_por_estrato(
    filas: list[FilaFuente],
) -> list[tuple[str, list[tuple[str, str, str, str]]]]:
    """Agrupa la tabla fuente por estrato, en el orden del inventario.

    Devuelve una lista de ``(estrato, filas)`` donde cada fila es
    ``(característica, atributo, estado, motivo)``. La seguridad se remite al
    Anexo 3 con una fila propia en cada estrato que no la declare ya en la
    fuente, así el perfil de (ciber)seguridad queda presente en todos y no se
    reescribe.
    """

    por_estrato: dict[str, list[FilaFuente]] = {}
    for fila in filas:
        por_estrato.setdefault(fila.estrato, []).append(fila)

    desconocidos = sorted(set(por_estrato) - set(ORDEN_ESTRATOS))
    if desconocidos:
        raise ValueError(
            "estratos de la fuente sin lugar en el inventario: "
            + ", ".join(desconocidos)
        )
    faltantes = [e for e in ORDEN_ESTRATOS if e not in por_estrato]
    if faltantes:
        raise ValueError(
            "estratos del inventario sin fila en la fuente: " + ", ".join(faltantes)
        )

    salida: list[tuple[str, list[tuple[str, str, str, str]]]] = []
    for estrato in ORDEN_ESTRATOS:
        rows = [
            (f.caracteristica, f.atributo, f.estado, f.motivo)
            for f in por_estrato[estrato]
        ]
        if not any(caracteristica == "Seguridad" for caracteristica, *_ in rows):
            rows.append(
                ("Seguridad", ATRIBUTO_SEGURIDAD, "Remite", MOTIVO_SEGURIDAD_REMITE)
            )
        salida.append((estrato, rows))
    return salida


def _celda(texto: str) -> str:
    return " ".join(texto.split()).replace("|", "\\|")


def emitir_markdown(por_estrato: list[tuple[str, list[tuple[str, str, str, str]]]]) -> str:
    lineas: list[str] = [
        "# Evaluación del Proyecto: Presentación",
        "",
        "Anexo 1 de la revisión de laboratorio (iLab/rLab). Documento generado por "
        "`Implementacion/Agente1/scripts/anexo1_presentacion.py`.",
        "",
        "Vista de trabajo del anexo: declara una **selección** de hasta "
        f"{TOPE_POR_COMPONENTE} atributos por componente (`scripts/anexos_seleccion.py`). "
        "El perfil completo, con todo lo evaluado, queda en "
        "`Documentos/Laboratorio/Perfil-Calidad-Sistema-Demostracion-v1.md`.",
        "",
        "## Título del Proyecto",
        "",
        TITULO_PROYECTO,
        "",
        "## Concepto General del Proyecto",
        "",
        "*(abstract)*",
        "",
    ]
    for parrafo in CONCEPTO_GENERAL:
        lineas += [parrafo, ""]

    lineas += ["## Enfoque del proyecto", ""]
    lineas += [f"- {item}" for item in ENFOQUE]
    lineas += [""]

    lineas += [
        "## Estado de las capacidades contra el gate TRL 4",
        "",
        ESTADO_TRL_INTRO,
        "",
        ESTADO_TRL_DEMOSTRADO,
        "",
        "**No demostrado.**",
        "",
    ]
    lineas += [f"- {item}" for item in ESTADO_TRL_NO_DEMOSTRADO]
    lineas += ["", ESTADO_TRL_BRECHA, "", ESTADO_TRL_CIERRE, ""]

    lineas += [
        "## Esquema general de los componentes del sistema y perfil de calidad de cada uno de ellos",
        "",
        "El perfil se declara por **estrato**, la capa del inventario de "
        "componentes sobre la que se lee el perfil de calidad. `Sistema` agrupa "
        "los atributos transversales que ninguna capa ejerce sola. El orden de "
        "los estratos es el del inventario:",
        "",
    ]
    for estrato in ORDEN_ESTRATOS:
        lineas.append(f"- **{ETIQUETA_ESTRATO.get(estrato, estrato)}:** {DESCRIPCION_ESTRATO[estrato]}")
    lineas.append("")

    lineas += [
        "## Detalle de atributos de calidad por componente",
        "",
        REFERENCIA_FOTO,
        "",
        INTRO_DETALLE,
        "",
    ]
    for estrato, rows in por_estrato:
        lineas += [
            f"### {ETIQUETA_ESTRATO.get(estrato, estrato)}",
            "",
            "| Característica (ISO/IEC 25010:2023) | Atributo | Estado | Motivo |",
            "|---|---|---|---|",
        ]
        for caracteristica, atributo, estado, motivo in rows:
            lineas.append(
                f"| {_celda(caracteristica)} | {_celda(atributo)} | {_celda(estado)} | {_celda(motivo)} |"
            )
        lineas.append("")

    lineas += [
        "## Lista de Control",
        "",
        "*(Versión inicial prevista; se podrán agregar los puntos a considerar "
        "que el laboratorio estime convenientes.)*",
        "",
    ]
    lineas += [f"- {item}" for item in LISTA_CONTROL]
    lineas.append("")
    return "\n".join(lineas)


def _plano(texto: str) -> str:
    """Quita el marcado de Markdown que no tiene sentido en un .docx."""

    return texto.replace("**", "").replace("`", "")


def _encadenar(doc: Any, ancla: Any, texto: str) -> Any:
    """Agrega un párrafo inmediatamente después del elemento `ancla`."""

    nuevo = doc.add_paragraph(_plano(texto))
    ancla.addnext(nuevo._p)
    return nuevo._p


def emitir_plantilla(
    por_estrato: list[tuple[str, list[tuple[str, str, str, str]]]],
    plantilla: Path,
    destino: Path,
) -> None:
    """Vuelca la presentación sobre la plantilla oficial «3.1 - Anexo 1».

    Conserva los títulos y las viñetas de la plantilla y agrega el contenido
    debajo de cada uno: el título, el concepto general, el enfoque, el esquema
    de estratos, una tabla `Atributo | Estado | Motivo` por componente y la
    Lista de Control.
    """

    from docx.shared import Cm, Pt

    doc = abrir_plantilla(plantilla)

    # La plantilla trae una única tabla de ejemplo; se reemplaza por una tabla
    # por estrato, así que se retira del documento.
    for tabla in list(doc.tables):
        tabla._tbl.getparent().remove(tabla._tbl)

    ancla = buscar_parrafo(doc, "Título del Proyecto")._p
    ancla = _encadenar(doc, ancla, TITULO_PROYECTO)

    reemplazar_parrafo(doc, "(abstract)", CONCEPTO_GENERAL[0])
    ancla = buscar_parrafo(doc, CONCEPTO_GENERAL[0])._p
    for parrafo in CONCEPTO_GENERAL[1:]:
        ancla = _encadenar(doc, ancla, parrafo)

    ancla = buscar_parrafo(doc, "Enfoque del proyecto")._p
    for item in ENFOQUE:
        ancla = _encadenar(doc, ancla, f"• {item}")

    ancla = _encadenar(doc, ancla, "Estado de las capacidades contra el gate TRL 4")
    for parrafo in (ESTADO_TRL_INTRO, ESTADO_TRL_DEMOSTRADO, "No demostrado."):
        ancla = _encadenar(doc, ancla, parrafo)
    for item in ESTADO_TRL_NO_DEMOSTRADO:
        ancla = _encadenar(doc, ancla, f"• {item}")
    for parrafo in (ESTADO_TRL_BRECHA, ESTADO_TRL_CIERRE):
        ancla = _encadenar(doc, ancla, parrafo)

    ancla = buscar_parrafo(doc, "Esquema general de los componentes")._p
    for estrato in ORDEN_ESTRATOS:
        etiqueta = ETIQUETA_ESTRATO.get(estrato, estrato)
        ancla = _encadenar(doc, ancla, f"• {etiqueta}: {DESCRIPCION_ESTRATO[estrato]}")

    ancla = buscar_parrafo(doc, "Detalle de atributos de calidad")._p
    ancla = _encadenar(doc, ancla, INTRO_DETALLE)
    for estrato, rows in por_estrato:
        etiqueta = ETIQUETA_ESTRATO.get(estrato, estrato)
        # La plantilla rotula cada tabla con una fila combinada con el nombre
        # del componente: no hace falta repetirlo en un párrafo aparte.
        tabla = doc.add_table(rows=2, cols=3)
        tabla.style = "Table Grid"
        # Anchos explícitos: la plantilla usa columnas desiguales, y dejar
        # `add_table` en tercios iguales le da un tercio de la hoja a `Estado`,
        # que es una letra, y envuelve el `Motivo` en una franja angosta.
        tabla.autofit = False
        for fila in tabla.rows:
            for indice, ancho_cm in enumerate(ANCHOS_COLUMNAS_CM):
                fila.cells[indice].width = Cm(ancho_cm)
        tabla.rows[0].cells[0].merge(tabla.rows[0].cells[2]).text = etiqueta
        for i, encabezado in enumerate(("Atributo", "Estado", "Motivo")):
            tabla.rows[1].cells[i].text = encabezado
        for caracteristica, atributo, estado, motivo in rows:
            celdas = tabla.add_row().cells
            celdas[0].text = _plano(f"{caracteristica} · {atributo}")
            celdas[1].text = _plano(estado)
            celdas[2].text = _plano(motivo)
        # Las tablas son el grueso del anexo: con el cuerpo de la plantilla
        # ocupaban doce de las dieciséis páginas.
        for fila in tabla.rows:
            for celda in fila.cells:
                for parrafo in celda.paragraphs:
                    for run in parrafo.runs:
                        run.font.size = Pt(TAMANO_TABLA_PT)
        ancla.addnext(tabla._tbl)
        ancla = tabla._tbl

    ancla = buscar_parrafo(doc, "Lista de Control")._p
    for item in LISTA_CONTROL:
        ancla = _encadenar(doc, ancla, f"• {item}")

    guardar(doc, destino)



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fuente",
        type=Path,
        default=FUENTE,
        help="Markdown con la tabla fuente marcada TABLA-FUENTE.",
    )
    parser.add_argument(
        "--salida-md",
        type=Path,
        default=SALIDA_MD,
        help="Destino de la presentación en Markdown.",
    )
    parser.add_argument(
        "--plantilla",
        type=Path,
        default=None,
        help="Plantilla oficial del Anexo 1; con --docx escribe la entrega sobre ella.",
    )
    parser.add_argument(
        "--docx",
        type=Path,
        default=None,
        help="Destino de la entrega (requiere python-docx y --plantilla).",
    )
    args = parser.parse_args()

    filas_fuente = parsear_fuente(args.fuente.read_text(encoding="utf-8"))
    por_estrato = proyectar_por_estrato(seleccionar_calidad(filas_fuente))

    args.salida_md.parent.mkdir(parents=True, exist_ok=True)
    args.salida_md.write_text(emitir_markdown(por_estrato), encoding="utf-8")
    total = sum(len(rows) for _, rows in por_estrato)
    print(
        f"{len(por_estrato)} estratos y {total} atributos proyectados "
        f"desde {len(filas_fuente)} filas -> {args.salida_md}"
    )

    if args.docx is not None:
        if args.plantilla is None:
            raise SystemExit(
                "--docx requiere --plantilla: la entrega va sobre la plantilla "
                "oficial de la cátedra, con las columnas del laboratorio vacías."
            )
        emitir_plantilla(por_estrato, args.plantilla, args.docx)
        print(f"entrega sobre la plantilla oficial escrita en {args.docx}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
