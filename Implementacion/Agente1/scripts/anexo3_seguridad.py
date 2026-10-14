"""Proyección de la tabla fuente del perfil de seguridad al formato del Anexo 3.

Lee la tabla marcada ``TABLA-FUENTE`` de
``Documentos/Laboratorio/Perfil-Seguridad-Sistema-Demostracion-v1.md`` y emite
la tabla del Anexo 3 por componente, con las columnas del template del
procedimiento de revisión (``3.3 - Anexo 3 - Seguridad 2025``): Componente,
Ítem, Implementado (MB/B/M), Previsto, No previsto y Comentario.

La salida no agrega contenido: reordena y consolida la tabla fuente. Las
columnas de nivel y el nivel global los completa el laboratorio, que es quien
asigna el nivel de competencia; el autor sólo declara el estado y su motivo.

Uso:

    uv run python scripts/anexo3_seguridad.py
        # escribe Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md

    uv run --with python-docx python scripts/anexo3_seguridad.py \\
        --docx Documentos/Laboratorio/Anexo3-Seguridad-v1.docx
        # además genera el .docx con las columnas de la plantilla oficial.
        # Requiere python-docx disponible en el entorno; no es la plantilla
        # oficial institucional, sólo el contenido derivado de la tabla fuente.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent.parent
FUENTE = (
    REPO / "Documentos" / "Laboratorio" / "Perfil-Seguridad-Sistema-Demostracion-v1.md"
)
SALIDA_MD = REPO / "Documentos" / "Laboratorio" / "Anexo3-Seguridad-Proyeccion-v1.md"

MARCADOR_INICIO = "<!-- TABLA-FUENTE:INICIO -->"
MARCADOR_FIN = "<!-- TABLA-FUENTE:FIN -->"

# Orden canónico de los componentes/estratos del inventario, más el componente
# externo de plataforma (#64) y `Sistema` para lo transversal.
ORDEN_COMPONENTES = [
    "Canal",
    "Interpretación",
    "Generación",
    "Gates",
    "Control de pagos",
    "Aprobación",
    "Cola y envío",
    "Persistencia y auditoría",
    "Integraciones",
    "Google Workspace",
    "Sistema",
]

# Orden canónico de los factores de seguridad dentro de cada componente.
ORDEN_FACTORES = [
    "Autenticación",
    "Autorización",
    "Confidencialidad",
    "Integridad",
    "Disponibilidad",
    "Trazabilidad",
    "Robustez ante entradas no confiables",
]

# Estados base que el autor puede declarar. `D` no se asigna nunca acá: lo
# asigna el laboratorio (resolución de #58). `RA` califica a `A` o `B`.
ESTADOS_BASE = ("A", "B", "C", "No aplica", "Remite")

# Equivalencia con las etiquetas del template del Anexo 3 (tabla de la sección
# 2 del perfil). `Implementado` toma MB/B; `Previsto`/`No previsto` se marcan
# según el estado; el nivel final lo asigna el laboratorio.
IMPLEMENTADO_POR_ESTADO = {"A": "MB", "B": "B"}


class FilaFuente:
    def __init__(self, celdas: list[str]) -> None:
        if len(celdas) != 8:
            raise ValueError(
                f"fila con {len(celdas)} celdas, se esperaban 8: {celdas!r}"
            )
        (
            self.estrato,
            self.factor,
            self.item,
            self.estado,
            self.motivo,
            self.evidencia,
            self.paso,
            self.marco,
        ) = celdas

    @property
    def estado_base(self) -> str:
        """El estado sin la calificación: `A + RA` -> `A`."""

        return self.estado.split("+", 1)[0].strip()

    @property
    def es_riesgo_aceptado(self) -> bool:
        return "RA" in self.estado


def parsear_fuente(texto: str) -> list[FilaFuente]:
    """Extrae las filas de la tabla marcada como tabla fuente."""

    if MARCADOR_INICIO not in texto or MARCADOR_FIN not in texto:
        raise ValueError("la fuente no tiene los marcadores TABLA-FUENTE")
    seccion = texto.split(MARCADOR_INICIO, 1)[1].split(MARCADOR_FIN, 1)[0]

    filas: list[FilaFuente] = []
    for linea in seccion.splitlines():
        linea = linea.strip()
        if not linea.startswith("|"):
            continue
        if re.fullmatch(r"[|\s:-]+", linea):
            continue
        celdas = [c.strip() for c in linea.strip("|").split("|")]
        if celdas and celdas[0] == "Estrato":
            continue
        filas.append(FilaFuente(celdas))
    if not filas:
        raise ValueError("la tabla fuente no tiene filas de datos")
    return filas


def ordenar(filas: list[FilaFuente]) -> list[FilaFuente]:
    """Valida y ordena por componente y por factor canónicos."""

    desconocidos = sorted({f.estrato for f in filas} - set(ORDEN_COMPONENTES))
    if desconocidos:
        raise ValueError(
            "componentes de la fuente sin orden canónico: " + ", ".join(desconocidos)
        )
    faltantes = sorted(set(ORDEN_COMPONENTES) - {f.estrato for f in filas})
    if faltantes:
        raise ValueError(
            "componentes del orden canónico sin fila en la fuente: "
            + ", ".join(faltantes)
        )
    factores = sorted({f.factor for f in filas} - set(ORDEN_FACTORES))
    if factores:
        raise ValueError(
            "factores de la fuente sin orden canónico: " + ", ".join(factores)
        )
    for fila in filas:
        if fila.estado_base not in ESTADOS_BASE:
            raise ValueError(
                f"estado declarado fuera de la escala: {fila.estado!r} ({fila.item!r})"
            )
    return sorted(
        filas,
        key=lambda f: (
            ORDEN_COMPONENTES.index(f.estrato),
            ORDEN_FACTORES.index(f.factor),
        ),
    )


def columna_implementado(fila: FilaFuente) -> str:
    return IMPLEMENTADO_POR_ESTADO.get(fila.estado_base, "")


def columna_previsto(fila: FilaFuente) -> str:
    if fila.estado_base == "C":
        return "Debe Implem."
    return ""


def columna_no_previsto(fila: FilaFuente) -> str:
    if fila.estado_base == "No aplica":
        return "No es necesario"
    return ""


def comentario(fila: FilaFuente) -> str:
    partes = [f"Estado declarado por el autor: {fila.estado}."]
    if fila.es_riesgo_aceptado:
        partes.append("Riesgo aceptado (RA): ver el motivo para quién lo aceptó.")
    partes.append(f"Factor de seguridad: {fila.factor}.")
    partes.append(fila.motivo)
    if fila.evidencia != "—":
        partes.append(f"Evidencia versionada: {fila.evidencia}.")
    if fila.paso != "—":
        partes.append(f"Paso en vivo: {fila.paso}.")
    if fila.marco != "—":
        partes.append(f"Correspondencia: {fila.marco}.")
    return " ".join(partes)


def emitir_markdown(filas: list[FilaFuente]) -> str:
    lineas = [
        "# Anexo 3 — Perfil de seguridad por componente (proyección)",
        "",
        "Documento generado por `Implementacion/Agente1/scripts/anexo3_seguridad.py`",
        "desde la tabla fuente `Documentos/Laboratorio/Perfil-Seguridad-Sistema-Demostracion-v1.md`.",
        "Los tres anexos declaran una sola foto, la del día del envío.",
        "",
        "Columnas de la plantilla oficial «3.3 - Anexo 3 - Seguridad 2025»:",
        "Componente | Ítem | Implementado (MB/B/M) | Previsto | No previsto | Comentario.",
        "Las columnas de nivel las completa el laboratorio; la declaración del autor",
        "(estado, factor, motivo, evidencia y paso en vivo) va en Comentario.",
        "**Foto declarada por el autor; los niveles de competencia los asigna el laboratorio.**",
        "",
        "| Componente | Ítem | Implementado | Previsto | No previsto | Estado declarado (autor) | Motivo | Evidencia versionada | Paso en vivo (< 2 min) | Marco |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for fila in filas:
        lineas.append(
            "| "
            + " | ".join(
                [
                    fila.estrato,
                    fila.item,
                    columna_implementado(fila) or "—",
                    columna_previsto(fila) or "—",
                    columna_no_previsto(fila) or "—",
                    fila.estado,
                    fila.motivo,
                    fila.evidencia,
                    fila.paso,
                    fila.marco,
                ]
            )
            + " |"
        )
    lineas.append("")
    return "\n".join(lineas)


def emitir_docx(filas: list[FilaFuente], destino: Path) -> None:
    try:
        from docx import Document
    except ImportError:
        raise SystemExit(
            "python-docx no está instalado; correr con "
            "`uv run --with python-docx python scripts/anexo3_seguridad.py --docx …` "
            "o instalar la dependencia en el entorno."
        )

    doc = Document()
    doc.add_heading("Reporte de Evaluación — Anexo 3 (Seguridad)", level=1)
    doc.add_paragraph("Proyecto: Agente 1, Extension Bot (PPS Juan Ignacio Goñe)")
    doc.add_paragraph(
        "Contenido derivado de la tabla fuente "
        "Documentos/Laboratorio/Perfil-Seguridad-Sistema-Demostracion-v1.md. "
        "Las columnas de nivel las completa el laboratorio. "
        "Foto declarada por el autor; los niveles de competencia los asigna el laboratorio."
    )
    doc.add_paragraph(
        "Factores de Seguridad: NIST Cybersecurity Framework (declarado una vez a "
        "nivel Sistema); OWASP Top 10 y OWASP Top 10 for LLM Applications por ítem "
        "donde toca; MITRE ATT&CK sólo para las técnicas que el diseño habilita."
    )
    doc.add_paragraph(
        "Equivalencia de escalas: A = Implementado (MB, Muy Bueno / Satisfactorio); "
        "B = Implementado (B, Bueno / en proceso); C = Previsto (Debe Implem.); "
        "No aplica = No previsto (No es necesario); Remite = se declara en otro anexo; "
        "D lo asigna el laboratorio; RA es una calificación dentro de A o B."
    )

    tabla = doc.add_table(rows=1, cols=6)
    tabla.style = "Table Grid"
    encabezados = [
        "Componente",
        "Ítem",
        "Implementado",
        "Previsto",
        "No previsto",
        "Comentario",
    ]
    for i, texto in enumerate(encabezados):
        tabla.rows[0].cells[i].text = texto

    for fila in filas:
        celdas = tabla.add_row().cells
        celdas[0].text = fila.estrato
        celdas[1].text = fila.item
        celdas[2].text = columna_implementado(fila)
        celdas[3].text = columna_previsto(fila)
        celdas[4].text = columna_no_previsto(fila)
        celdas[5].text = comentario(fila)

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
        help="Destino de la proyección en Markdown.",
    )
    parser.add_argument(
        "--docx",
        type=Path,
        default=None,
        help="Destino del .docx derivado (requiere python-docx).",
    )
    args = parser.parse_args()

    filas = ordenar(parsear_fuente(args.fuente.read_text(encoding="utf-8")))

    args.salida_md.parent.mkdir(parents=True, exist_ok=True)
    args.salida_md.write_text(emitir_markdown(filas), encoding="utf-8")
    print(f"{len(filas)} ítems proyectados -> {args.salida_md}")

    if args.docx is not None:
        emitir_docx(filas, args.docx)
        print(f"docx derivado escrito en {args.docx}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
