"""Anexo 2 del laboratorio — tabla de calidad por atributo.

Lee la tabla marcada ``TABLA-FUENTE`` de
``Documentos/Laboratorio/Perfil-Calidad-Sistema-Demostracion-v1.md`` y emite la
tabla del Anexo 2 por atributo, en el orden de ISO/IEC 25010:2023, con las
subcaracterísticas aplicables de ISO/IEC 25059:2023, el conjunto reducido de
ISO/IEC 25012 y la fila única de Seguridad que remite al Anexo 3.

Dos salidas, con dos propósitos distintos:

- **Proyección en Markdown** (``Anexo2-Calidad-Proyeccion-v1.md``): la vista de
  trabajo, con la declaración completa del autor —estado, motivo, evidencia y
  paso en vivo—. Es interna: no se entrega.
- **Entrega sobre la plantilla oficial** (``--plantilla``): el ``.docx`` que sí
  va al laboratorio, volcado sobre ``3.2 - Anexo 2 - Calidad 2025.docx``.

El reparto de columnas lo fijan el correo del laboratorio del 14/10 y la nota al
pie de la plantilla: el equipo de proyecto completa ``Factor de calidad`` y
``Atributo``, y el laboratorio completa ``Nivel de Competencia``, ``Nivel de
Competencia Global`` y ``Comentarios``. Por eso **el script no escribe la
declaración del autor en las columnas del laboratorio**: el estado, el motivo y
la evidencia viven en el Anexo 1.

Uso:

    uv run python scripts/anexo2_calidad.py
        # escribe Documentos/Laboratorio/Anexo2-Calidad-Proyeccion-v1.md

    uv run --with python-docx python scripts/anexo2_calidad.py \\
        --plantilla "Contenido/DocumentacionAnteproyecto/Revision-Laboratorio-2025/3.2 - Anexo 2 - Calidad 2025.docx" \\
        --docx Documentos/Laboratorio/Entrega-2026-10-23/Anexo2-Calidad.docx
        # escribe la entrega sobre la plantilla oficial. Requiere python-docx.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from plantilla_laboratorio import (  # noqa: E402
    TITULO_PROYECTO,
    abrir_plantilla,
    agregar_fila,
    conservar_filas,
    guardar,
    reemplazar_en_celdas,
    reemplazar_parrafo,
    verificar_columnas,
)

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent.parent
FUENTE = REPO / "Documentos" / "Laboratorio" / "Perfil-Calidad-Sistema-Demostracion-v1.md"
SALIDA_MD = REPO / "Documentos" / "Laboratorio" / "Anexo2-Calidad-Proyeccion-v1.md"

# Encabezado de la plantilla oficial «3.2 - Anexo 2 - Calidad 2025», para
# verificar que la plantilla es la esperada antes de escribir.
COLUMNAS_ENCABEZADO = [
    "Factor de calidad",
    "Atributo",
    "Nivel de Competencia",
    "Nivel de Competencia Global",
    "Comentarios",
]

# Título de la tabla: la plantilla pide «<Citar estándar aplicado>».
TITULO_TABLA = (
    "Factores de Calidad — ISO/IEC 25010:2023, con subcaracterísticas de "
    "ISO/IEC 25059:2023 y el conjunto reducido de ISO/IEC 25012:2023. "
    "Seguridad remite al Anexo 3"
)

# Filas de la plantilla que se conservan: el título combinado y el encabezado.
FILAS_ENCABEZADO_PLANTILLA = 2

MARCADOR_INICIO = "<!-- TABLA-FUENTE:INICIO -->"
MARCADOR_FIN = "<!-- TABLA-FUENTE:FIN -->"

# Orden canónico de ISO/IEC 25010:2023, con las subcaracterísticas de
# ISO/IEC 25059:2023 dentro de su factor y el bloque reducido de
# ISO/IEC 25012 al final. La fila de Seguridad remite al Anexo 3.
ORDEN_CARACTERISTICAS = [
    ("Adecuación funcional", [
        "Completitud funcional",
        "Corrección del sistema",
        "Corrección del contenido generado (25059)",
        "Pertinencia funcional",
        "Adaptabilidad funcional (25059)",
    ]),
    ("Eficiencia de desempeño", [
        "Comportamiento temporal",
        "Utilización de recursos",
        "Capacidad",
    ]),
    ("Compatibilidad", [
        "Interoperabilidad",
        "Coexistencia",
    ]),
    ("Capacidad de interacción", [
        "Reconocibilidad de la adecuación",
        "Aprendizaje",
        "Operabilidad",
        "Protección contra errores del usuario",
        "Compromiso del usuario",
        "Inclusividad",
        "Asistencia al usuario",
        "Controlabilidad (25059)",
        "Transparencia (25059)",
        "Intervenibilidad (25059)",
    ]),
    ("Fiabilidad", [
        "Ausencia de fallos",
        "Disponibilidad",
        "Tolerancia a fallos",
        "Recuperabilidad",
        "Robustez (25059)",
    ]),
    ("Seguridad", [
        "Seguridad (factor completo)",
    ]),
    ("Mantenibilidad", [
        "Modularidad",
        "Reusabilidad",
        "Analizabilidad",
        "Modificabilidad",
        "Capacidad de prueba",
    ]),
    ("Flexibilidad", [
        "Adaptabilidad",
        "Instalabilidad",
        "Reemplazabilidad",
        "Escalabilidad",
    ]),
    ("Safety", [
        "Safety (factor completo)",
    ]),
    ("Calidad de datos (25012)", [
        "Completitud",
        "Consistencia",
        "Exactitud sintáctica",
        "Exactitud semántica",
        "Credibilidad",
        "Actualidad",
        "Trazabilidad",
    ]),
]

ORDEN_ESTADOS = ["A", "B", "C", "No aplica", "Remite"]


class FilaFuente:
    def __init__(self, celdas: list[str]) -> None:
        if len(celdas) != 7:
            raise ValueError(f"fila con {len(celdas)} celdas, se esperaban 7: {celdas!r}")
        (
            self.estrato,
            self.caracteristica,
            self.atributo,
            self.estado,
            self.motivo,
            self.evidencia,
            self.paso,
        ) = celdas


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


def proyectar(filas: list[FilaFuente]) -> list[tuple[str, str, str, str, str, str]]:
    """Agrupa por (característica, atributo) en el orden del estándar.

    Devuelve filas de seis celdas: característica, atributo, estado declarado,
    motivo consolidado por estrato, evidencia y paso en vivo.
    """

    por_clave: dict[tuple[str, str], list[FilaFuente]] = {}
    for fila in filas:
        por_clave.setdefault((fila.caracteristica, fila.atributo), []).append(fila)

    conocidas = {
        (caracteristica, atributo)
        for caracteristica, atributos in ORDEN_CARACTERISTICAS
        for atributo in atributos
    }
    sobrantes = sorted(set(por_clave) - conocidas)
    if sobrantes:
        raise ValueError(
            "atributos de la fuente sin lugar en el orden del estándar: "
            + ", ".join(f"{c}/{a}" for c, a in sobrantes)
        )
    faltantes = sorted(conocidas - set(por_clave))
    if faltantes:
        raise ValueError(
            "atributos del orden canónico sin fila en la fuente: "
            + ", ".join(f"{c}/{a}" for c, a in faltantes)
        )

    salida: list[tuple[str, str, str, str, str, str]] = []
    for caracteristica, atributos in ORDEN_CARACTERISTICAS:
        for atributo in atributos:
            grupo = por_clave[(caracteristica, atributo)]
            estados = sorted(
                {
                    parte.strip()
                    for f in grupo
                    for parte in f.estado.split("/")
                },
                key=lambda e: ORDEN_ESTADOS.index(e) if e in ORDEN_ESTADOS else len(ORDEN_ESTADOS),
            )
            estado = "/".join(estados)
            if len(grupo) == 1:
                motivo = grupo[0].motivo
            else:
                motivo = " / ".join(f"{f.estrato}: {f.motivo}" for f in grupo)
            evidencias = []
            for f in grupo:
                for item in f.evidencia.split(";"):
                    item = item.strip()
                    if item and item != "—" and item not in evidencias:
                        evidencias.append(item)
            pasos = []
            for f in grupo:
                if f.paso != "—" and f.paso not in pasos:
                    pasos.append(f.paso)
            salida.append(
                (
                    caracteristica,
                    atributo,
                    estado,
                    motivo,
                    "; ".join(evidencias) if evidencias else "—",
                    " / ".join(pasos) if pasos else "—",
                )
            )
    return salida


def emitir_markdown(filas: list[tuple[str, str, str, str, str, str]]) -> str:
    lineas = [
        "# Anexo 2 — Tabla de calidad por atributo (proyección)",
        "",
        "Documento generado por `Implementacion/Agente1/scripts/anexo2_calidad.py`",
        "desde la tabla fuente `Documentos/Laboratorio/Perfil-Calidad-Sistema-Demostracion-v1.md`",
        "(foto del inventario en el commit de base `98be859`, 2026-10-12).",
        "",
        "Columnas de la plantilla oficial «3.2 - Anexo 2 - Calidad 2025.docx»:",
        "Factor de calidad | Atributo | Nivel de Competencia | Nivel de Competencia",
        "Global | Comentarios. La entrega la completa el equipo de proyecto con el",
        "factor y el atributo; las tres últimas columnas las completa el laboratorio",
        "al evaluar. Las columnas de esta proyección son la vista de trabajo del",
        "autor y no viajan a la plantilla. Seguridad remite al Anexo 3 (#58).",
        "",
        "| Factor de calidad | Atributo | Estado declarado (autor) | Motivo | Evidencia versionada | Paso en vivo (< 2 min) |",
        "|---|---|---|---|---|---|",
    ]
    for caracteristica, atributo, estado, motivo, evidencia, paso in filas:
        lineas.append(
            f"| {caracteristica} | {atributo} | {estado} | {motivo} | {evidencia} | {paso} |"
        )
    lineas.append("")
    return "\n".join(lineas)


def emitir_plantilla(
    filas: list[tuple[str, str, str, str, str, str]], plantilla: Path, destino: Path
) -> None:
    """Volca los atributos del Anexo 2 sobre la plantilla oficial de la cátedra.

    Sólo completa las columnas del equipo de proyecto —`Factor de calidad` y
    `Atributo`—: las del laboratorio quedan vacías para que las marque al
    evaluar.
    """

    doc = abrir_plantilla(plantilla)
    reemplazar_parrafo(doc, "<Título del Proyecto<", TITULO_PROYECTO)
    reemplazar_en_celdas(doc, "Factores de Calidad", TITULO_TABLA)
    if len(doc.tables) != 1:
        raise SystemExit(
            f"la plantilla del Anexo 2 tiene {len(doc.tables)} tablas; se esperaba 1"
        )
    tabla = doc.tables[0]
    verificar_columnas(tabla, COLUMNAS_ENCABEZADO)
    conservar_filas(tabla, FILAS_ENCABEZADO_PLANTILLA)
    for caracteristica, atributo, _estado, _motivo, _evidencia, _paso in filas:
        agregar_fila(tabla, [caracteristica, atributo])
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
        help="Destino de la proyección en Markdown.",
    )
    parser.add_argument(
        "--plantilla",
        type=Path,
        default=None,
        help="Plantilla oficial del Anexo 2; con --docx escribe la entrega sobre ella.",
    )
    parser.add_argument(
        "--docx",
        type=Path,
        default=None,
        help="Destino de la entrega (requiere python-docx y --plantilla).",
    )
    args = parser.parse_args()

    filas_fuente = parsear_fuente(args.fuente.read_text(encoding="utf-8"))
    filas = proyectar(filas_fuente)

    args.salida_md.parent.mkdir(parents=True, exist_ok=True)
    args.salida_md.write_text(emitir_markdown(filas), encoding="utf-8")
    print(f"{len(filas)} atributos proyectados desde {len(filas_fuente)} filas -> {args.salida_md}")

    if args.docx is not None:
        if args.plantilla is None:
            raise SystemExit(
                "--docx requiere --plantilla: la entrega va sobre la plantilla "
                "oficial de la cátedra, con las columnas del laboratorio vacías."
            )
        emitir_plantilla(filas, args.plantilla, args.docx)
        print(f"entrega sobre la plantilla oficial escrita en {args.docx}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
