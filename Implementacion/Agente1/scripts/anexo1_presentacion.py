"""Anexo 1 del laboratorio — presentación del proyecto por estrato.

Lee la tabla fuente del perfil de calidad —la misma que alimenta el Anexo 2,
``Documentos/Laboratorio/Perfil-Calidad-Sistema-Demostracion-v1.md``— y emite la
presentación del sistema de demostración organizada por **estrato** (componente),
en el orden del inventario, con el estado de implementación y el motivo de cada
atributo declarado por el autor.

La salida no inventa datos: las tablas por estrato se derivan de la tabla fuente
y las cifras y los estados son los mismos que usa el Anexo 2, así que no hay dos
números para lo mismo. La sección de seguridad **remite** al Anexo 3 y no la
reescribe (issue #58/#108).

Uso:

    uv run python scripts/anexo1_presentacion.py
        # escribe Documentos/Laboratorio/Anexo1-Presentacion-v1.md

    uv run --with python-docx python scripts/anexo1_presentacion.py \
        --docx Documentos/Laboratorio/Anexo1-Presentacion-v1.docx
        # además genera el .docx con el encabezado de la plantilla oficial
        # «3.1 - Anexo 1 - Presentación 2025»; requiere python-docx en el
        # entorno y no es la plantilla institucional (que llega con el
        # material de cátedra), sólo el contenido derivado de la tabla fuente.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from anexo2_calidad import FilaFuente, parsear_fuente  # noqa: E402

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
        "Clasifica la solicitud a una intención de un catálogo cerrado —o la "
        "rechaza— y resuelve la actividad por identificador, por búsqueda "
        "difusa determinística o por repregunta; nunca aproxima a la intención "
        "más parecida."
    ),
    "Generación": (
        "Produce las piezas como borrador —gacetilla, post, plantilla de correo "
        "por actividad y certificado con línea descriptiva— con gate mecánico "
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
        "Ollama local y los insumos de los agentes A3–A5."
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

ATRIBUTO_SEGURIDAD = "Factores de (ciber)seguridad del estrato"

# --- Prosa del documento -----------------------------------------------------
# Estos textos se reproducen en el Markdown versionado y en el Word. No
# introducen cifras nuevas: las cifras y los estados de las tablas salen de la
# tabla fuente, y las fechas institucionales son las del anteproyecto y del
# glosario (`CONTEXT.md`).

TITULO_PROYECTO = (
    "Proyecto Centenario — Agente 1: Extensión Bot para la Secretaría de "
    "Extensión Universitaria de la FIE (Facultad de Ingeniería del Ejército, "
    "Universidad de la Defensa Nacional)"
)

REFERENCIA_FOTO = (
    "Las tablas de este anexo se derivan de la tabla fuente del perfil de "
    "calidad del sistema de demostración "
    "(`Documentos/Laboratorio/Perfil-Calidad-Sistema-Demostracion-v1.md`), la "
    "misma que alimenta el Anexo 2: foto del inventario de componentes en el "
    "commit de base `98be859` (12/10/2026). El perfil de seguridad no se declara "
    "acá: cada estrato remite al Anexo 3."
)

CONCEPTO_GENERAL = [
    (
        "El Agente 1 (Extensión Bot) es el agente de comunicación institucional "
        "del Proyecto Centenario (P100) de la Facultad de Ingeniería del "
        "Ejército (FIE), Universidad de la Defensa Nacional. Prepara piezas "
        "comunicacionales para la Secretaría de Extensión Universitaria (SEU) "
        "—gacetillas, publicaciones para redes sociales, correos y "
        "confirmaciones, y certificados— dentro del Proceso 4. Su producto es "
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
        "sistema de demostración —el Agente 1 en todo su alcance declarado, "
        "funcionando de punta a punta en vivo— y su perfil de calidad por "
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
        "**Ejecución local y fail-closed.** Los modelos corren en "
        "infraestructura propia y el agente falla cerrado en cada frontera: lo "
        "que no cumple se rechaza antes de generar, escribir o tocar el "
        "registro. La auditoría guarda códigos, conteos y hashes, nunca "
        "contenido ni datos personales en claro."
    ),
    (
        "**Sistema de demostración sin capacidades detenidas.** El sistema corre "
        "en la laptop del autor con modelo local y sobre Google Workspace D2 con "
        "la cuenta técnica. Lo que depende de un tercero —plantillas, firmas, "
        "política de redes, identidad del personal, host D3— corre contra un "
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
    "declarada (commit de base `98be859`, 12/10/2026). La nota sobre fechas y "
    "estado verificado del anteproyecto conserva el corte del 21/09/2026; "
    "cuando uno y otro citan un número, corresponde a su propia fecha, y la "
    "revisión de laboratorio evalúa la foto de este anexo."
)

ESTADO_TRL_DEMOSTRADO = (
    "**Demostrado sobre el sistema de demostración.** El sistema corre de punta "
    "a punta en la laptop del autor con modelo local (Ollama) y sobre Google "
    "Workspace D2 con la cuenta técnica; la corrida live del 28/09/2026 quedó "
    "verificada con smoke de lectura, casos negativos y un extremo a extremo de "
    "gacetilla cuyo borrador real quedó en la carpeta autorizada, sin modificar "
    "nada existente. HU-010 a HU-014 están implementadas dentro del alcance "
    "declarado —gacetilla, post, plantilla de correo por actividad y certificado "
    "con línea descriptiva y circuito de lote—, la suite y las matrices por "
    "historia las ejercitan, y cada fila A o B de las tablas por estrato cita su "
    "evidencia versionada y su paso en vivo."
)

ESTADO_TRL_NO_DEMOSTRADO = [
    (
        "La validación de calidad por referentes de la SEU: la operabilidad, la "
        "reconocibilidad de la adecuación y la prueba guiada de HU-013 están "
        "previstas y su validación registrada sigue pendiente (issue #56; la "
        "prueba guiada con una persona real de la SEU no se concretó)."
    ),
    (
        "La ejecución live de los canales y del registro de decisiones como paso "
        "de la revisión: la evidencia versionada es offline y las corridas live "
        "se declaran como paso."
    ),
    (
        "La operación sobre el host D3: no hay ejecución live porque el host "
        "todavía no llegó (DEF-A1-001 parcial)."
    ),
    (
        "Los niveles verificados de los SLO —disponibilidad, latencia por pieza, "
        "utilización de recursos, tiempo de atención y aprobación a envío— no "
        "tienen medición a la fecha (issues #50, #51 y #88); el perfil declara la "
        "ausencia en lugar de un número."
    ),
    (
        "El criterio formal del gate: la Dirección de carrera no fijó un criterio "
        "formal, la evidencia se presenta contra el TRL 4 de la documentación del "
        "P100 y el go/no-go lo fija el informe del laboratorio."
    ),
]

ESTADO_TRL_BRECHA = (
    "**Brecha técnica abierta de HU-011.** El contrato creativo de redacción "
    "libre para los posts todavía no supera el control de contenido: el gate "
    "detecta hechos de la fuente filtrados al texto creativo y registro "
    "lingüístico no rioplatense, de modo que la variedad comunicacional depende "
    "de criterios editoriales que la SEU aún no definió. El nivel medido de "
    "conformidad al gate en redacción libre es de 1/6 con `llama3.2:3b` y 4/6 "
    "con `llama3.1:8b` (23/09/2026); el incumplimiento residual es de obediencia "
    "del modelo, lo contienen el gate fail-closed y la validación humana "
    "obligatoria, y la medición se refresca con el modelo definitivo (issue #51)."
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
        "`matriz_hu011_v2.py`, `matriz_hu012.py`, `matriz_hu014.py`)."
    ),
    (
        "Recorrer el canal con un pedido ambiguo y ver la repregunta con "
        "candidatas sin persistir la prosa del pedido."
    ),
    (
        "Verificar el gate de generación sobre los casos adversariales: variable "
        "fuera de catálogo, dígito, fecha, importe, correo, enlace o hecho "
        "escritos por el modelo, eco de prompting y salida truncada."
    ),
    (
        "Verificar la doble aprobación (semántica y utilitaria) y la aprobación "
        "de lote: sin las dos decisiones no hay encolado ni emisión, y editar la "
        "lista de cierre o la plantilla cambia el objeto y la aprobación previa "
        "deja de aplicar."
    ),
    (
        "Verificar la idempotencia durable y la reconciliación: una reserva "
        "colgada pasa a envío indeterminado sin reenviar y una re-corrida "
        "termina duplicada."
    ),
    (
        "Verificar que la auditoría y los reportes exponen sólo códigos, conteos "
        "y hashes, sin destinatarios ni cuerpos."
    ),
    (
        "Verificar los límites de escritura: escribir es siempre crear nuevo y "
        "el envío por Gmail opera cercado por la lista de prueba, con rechazo "
        "antes de tocar token o red."
    ),
    (
        "Verificar los insumos provisionales declarados: el sistema corre con "
        "ellos por el mecanismo productivo y ninguno queda como fake ni como "
        "capacidad detenida."
    ),
    (
        "Contrastar los estados declarados por estrato con el detalle por "
        "atributo del Anexo 2 y con el perfil de seguridad del Anexo 3."
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
        "# Evaluación del Proyecto – Presentación",
        "",
        "Anexo 1 de la revisión de laboratorio (iLab/rLab). Documento generado por "
        "`Implementacion/Agente1/scripts/anexo1_presentacion.py`.",
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
        "Atributos tenidos en cuenta en cada componente, con el estado de "
        "implementación declarado por el autor y su motivo. La escala de estados "
        "y las reglas que los rigen están en el Anexo 2; los factores de "
        "(ciber)seguridad de cada estrato se declaran en el Anexo 3.",
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


def emitir_docx(por_estrato: list[tuple[str, list[tuple[str, str, str, str]]]], destino: Path) -> None:
    try:
        from docx import Document
    except ImportError:
        raise SystemExit(
            "python-docx no está instalado; correr con "
            "`uv run --with python-docx python scripts/anexo1_presentacion.py --docx …` "
            "o instalar la dependencia en el entorno."
        )

    doc = Document()
    doc.core_properties.author = "Proyecto Centenario P100 — FIE/UNDEF"
    doc.core_properties.last_modified_by = ""
    doc.core_properties.title = "Anexo 1 — Presentación por estrato"
    doc.core_properties.comments = "generado por scripts/anexo1_presentacion.py"

    doc.add_heading("Evaluación del Proyecto – Presentación", level=1)

    doc.add_heading("Título del Proyecto", level=2)
    doc.add_paragraph(TITULO_PROYECTO)

    doc.add_heading("Concepto General del Proyecto", level=2)
    doc.add_paragraph("(abstract)")
    for parrafo in CONCEPTO_GENERAL:
        doc.add_paragraph(parrafo)

    doc.add_heading("Enfoque del proyecto", level=2)
    for item in ENFOQUE:
        doc.add_paragraph(item.replace("**", ""), style="List Bullet")

    doc.add_heading("Estado de las capacidades contra el gate TRL 4", level=2)
    doc.add_paragraph(ESTADO_TRL_INTRO)
    doc.add_paragraph(ESTADO_TRL_DEMOSTRADO.replace("**", ""))
    doc.add_paragraph("No demostrado.")
    for item in ESTADO_TRL_NO_DEMOSTRADO:
        doc.add_paragraph(item.replace("**", ""), style="List Bullet")
    doc.add_paragraph(ESTADO_TRL_BRECHA.replace("**", ""))
    doc.add_paragraph(ESTADO_TRL_CIERRE.replace("**", ""))

    doc.add_heading(
        "Esquema general de los componentes del sistema y perfil de calidad de cada uno de ellos",
        level=2,
    )
    doc.add_paragraph(
        "El perfil se declara por estrato, la capa del inventario de componentes "
        "sobre la que se lee el perfil de calidad. «Sistema» agrupa los atributos "
        "transversales que ninguna capa ejerce sola. El orden de los estratos es "
        "el del inventario:"
    )
    for estrato in ORDEN_ESTRATOS:
        etiqueta = ETIQUETA_ESTRATO.get(estrato, estrato)
        doc.add_paragraph(f"{etiqueta}: {DESCRIPCION_ESTRATO[estrato]}", style="List Bullet")

    doc.add_heading("Detalle de atributos de calidad por componente", level=2)
    doc.add_paragraph(REFERENCIA_FOTO)
    doc.add_paragraph(
        "Atributos tenidos en cuenta en cada componente, con el estado de "
        "implementación declarado por el autor y su motivo. La escala de estados "
        "y las reglas que los rigen están en el Anexo 2; los factores de "
        "(ciber)seguridad de cada estrato se declaran en el Anexo 3."
    )
    for estrato, rows in por_estrato:
        doc.add_heading(ETIQUETA_ESTRATO.get(estrato, estrato), level=3)
        tabla = doc.add_table(rows=1, cols=4)
        tabla.style = "Table Grid"
        encabezados = ["Característica (ISO/IEC 25010:2023)", "Atributo", "Estado", "Motivo"]
        for i, texto in enumerate(encabezados):
            tabla.rows[0].cells[i].text = texto
        for caracteristica, atributo, estado, motivo in rows:
            celdas = tabla.add_row().cells
            celdas[0].text = caracteristica
            celdas[1].text = atributo
            celdas[2].text = estado
            celdas[3].text = motivo

    doc.add_heading("Lista de Control", level=2)
    doc.add_paragraph(
        "(Versión inicial prevista; se podrán agregar los puntos a considerar que "
        "el laboratorio estime convenientes.)"
    )
    for item in LISTA_CONTROL:
        doc.add_paragraph(item, style="List Bullet")

    destino.parent.mkdir(parents=True, exist_ok=True)
    doc.save(destino)


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
        "--docx",
        type=Path,
        default=None,
        help="Destino del .docx derivado (requiere python-docx).",
    )
    args = parser.parse_args()

    filas_fuente = parsear_fuente(args.fuente.read_text(encoding="utf-8"))
    por_estrato = proyectar_por_estrato(filas_fuente)

    args.salida_md.parent.mkdir(parents=True, exist_ok=True)
    args.salida_md.write_text(emitir_markdown(por_estrato), encoding="utf-8")
    total = sum(len(rows) for _, rows in por_estrato)
    print(
        f"{len(por_estrato)} estratos y {total} atributos proyectados "
        f"desde {len(filas_fuente)} filas -> {args.salida_md}"
    )

    if args.docx is not None:
        emitir_docx(por_estrato, args.docx)
        print(f"docx derivado escrito en {args.docx}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
