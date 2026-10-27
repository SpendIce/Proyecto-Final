"""Anexo 3 del laboratorio: perfil de seguridad por componente.

Lee la tabla marcada ``TABLA-FUENTE`` de
``Documentos/Laboratorio/Perfil-Seguridad-Sistema-Demostracion-v1.md`` y emite
la tabla del Anexo 3 por componente. Dos salidas, con dos propósitos distintos:

- **Proyección en Markdown** (``Anexo3-Seguridad-Proyeccion-v1.md``): la vista
  de trabajo, con la declaración completa del autor (estado, motivo, evidencia
  y paso en vivo). Es interna: no se entrega.
- **Entrega sobre la plantilla oficial** (``--plantilla``): el ``.docx`` que sí
  va al laboratorio, volcado sobre ``3.3 - Anexo 3 - Seguridad 2025.docx``.

El reparto de columnas lo fija el correo del laboratorio del 27/10 (Maiorano):
el equipo de proyecto completa ``Componente`` e ``Ítem`` **y marca con una X**
el estado que declara (``Implementado MB|B``, ``Previsto``), transcripto del
perfil; el laboratorio completa sólo ``Comentario``, a modo de checklist. El
correo del 14/10 había dejado las marcas al laboratorio; el del 27/10 lo
cambió. Las columnas ``M`` y ``No previsto`` no las marca nunca el autor: son
la categoría D del procedimiento, que asigna el laboratorio.

Uso:

    uv run python scripts/anexo3_seguridad.py
        # escribe Documentos/Laboratorio/Anexo3-Seguridad-Proyeccion-v1.md

    uv run --with python-docx python scripts/anexo3_seguridad.py \\
        --plantilla "Contenido/DocumentacionAnteproyecto/Revision-Laboratorio-2025/3.3 - Anexo 3 - Seguridad 2025.docx" \\
        --docx Documentos/Laboratorio/Entrega/Anexo3-Seguridad.docx
        # escribe la entrega sobre la plantilla oficial. Requiere python-docx.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from anexos_seleccion import seleccionar_seguridad  # noqa: E402
from plantilla_laboratorio import (  # noqa: E402
    TITULO_PROYECTO,
    abrir_plantilla,
    actualizar_ciclo_lectivo,
    agregar_fila,
    conservar_filas,
    guardar,
    reemplazar_en_celdas,
    reemplazar_parrafo,
    verificar_columnas,
)

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent.parent
FUENTE = (
    REPO / "Documentos" / "Laboratorio" / "Perfil-Seguridad-Sistema-Demostracion-v1.md"
)
SALIDA_MD = REPO / "Documentos" / "Laboratorio" / "Anexo3-Seguridad-Proyeccion-v1.md"

# Encabezado de la fila de grupos de la plantilla oficial «3.3 - Anexo 3 -
# Seguridad 2025», para verificar que la plantilla es la esperada antes de
# escribir. `Implementado` está combinado sobre sus tres sub-columnas MB|B|M, y
# `Previsto` y `No previsto` sobre `No es necesario` y `Debe Implem`.
COLUMNAS_ENCABEZADO = [
    "Componente",
    "Ítem",
    "Implementado",
    "Implementado",
    "Implementado",
    "Previsto",
    "Previsto",
    "No previsto",
    "No previsto",
    "Comentario",
]

# Texto bajo «Referencias:»: los estándares que se aplicaron.
REFERENCIAS = (
    "NIST Cybersecurity Framework (CSF) 2.0, OWASP Top 10 (2021), OWASP Top "
    "10 for LLM Applications y MITRE ATT&CK."
)

# Título de la tabla: la plantilla pide «<Citar estándar aplicado>».
TITULO_TABLA = (
    "Factores de Seguridad: NIST CSF (a nivel Sistema), OWASP Top 10 y "
    "OWASP Top 10 for LLM por ítem, MITRE ATT&CK para las técnicas habilitadas"
)

# Filas de la plantilla que se conservan: el título combinado y los dos
# encabezados (grupos y sub-columnas). El resto son las filas de ejemplo.
FILAS_ENCABEZADO_PLANTILLA = 3

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

# Columna de la tabla (índice) donde va la X según el estado declarado. La
# equivalencia está en la sección 2 del perfil de seguridad. `No aplica` va a
# «Previsto / No es necesario»: el ítem se tuvo en cuenta y se descartó con
# motivo; «No previsto» es la categoría D («ignorado»), que asigna el
# laboratorio. `C` y `Remite` no tienen columna fija: la calificación de un `C`
# («requerido» o no) está en el motivo, y una fila que remite no se declara acá.
COLUMNA_MB = 2
COLUMNA_B = 3
COLUMNA_PREVISTO_NO_NECESARIO = 5
COLUMNA_POR_ESTADO = {
    "A": COLUMNA_MB,
    "B": COLUMNA_B,
    "No aplica": COLUMNA_PREVISTO_NO_NECESARIO,
}
MARCA = "X"

# Estados base que el autor puede declarar. `D` no se asigna nunca acá: lo
# asigna el laboratorio (resolución de #58). `RA` califica a `A` o `B`.
ESTADOS_BASE = ("A", "B", "C", "No aplica", "Remite")


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


def emitir_markdown(filas: list[FilaFuente]) -> str:
    lineas = [
        "# Anexo 3: Perfil de seguridad por componente (proyección)",
        "",
        "Documento generado por `Implementacion/Agente1/scripts/anexo3_seguridad.py`",
        "desde la tabla fuente `Documentos/Laboratorio/Perfil-Seguridad-Sistema-Demostracion-v1.md`.",
        "Los tres anexos declaran una sola foto, la del día del envío.",
        "",
        "Declara una **selección** de hasta 3 ítems por componente "
        "(`scripts/anexos_seleccion.py`); el perfil completo queda en la fuente.",
        "",
        "Vista de trabajo del autor: no se entrega y no reemplaza a la plantilla oficial",
        "«3.3 - Anexo 3 - Seguridad 2025», sobre la que se escribe la entrega con `--plantilla`.",
        "En la entrega, el estado se marca con una X (A: `MB`, B: `B`, No aplica: «Previsto / No es necesario»);",
        "el `Comentario` lo completa el laboratorio (correo del 27/10).",
        "",
        "| Componente | Ítem | Estado declarado (autor) | Motivo | Evidencia versionada | Paso en vivo (< 2 min) | Marco |",
        "|---|---|---|---|---|---|---|",
    ]
    for fila in filas:
        lineas.append(
            "| "
            + " | ".join(
                [
                    fila.estrato,
                    fila.item,
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


def marcas(fila: FilaFuente) -> list[str]:
    """Las siete casillas de estado de la plantilla, con la X del estado declarado.

    Falla con un estado sin columna fija (`C`, `Remite`) en vez de adivinar.
    """

    columna = COLUMNA_POR_ESTADO.get(fila.estado_base)
    if columna is None:
        raise ValueError(
            f"el estado {fila.estado!r} no tiene casilla fija en el Anexo 3 "
            f"({fila.estrato} › {fila.item}); definirla antes de declarar la fila"
        )
    casillas = [""] * 7
    casillas[columna - COLUMNA_MB] = MARCA
    return casillas


def emitir_plantilla(filas: list[FilaFuente], plantilla: Path, destino: Path) -> None:
    """Volca los ítems del Anexo 3 sobre la plantilla oficial de la cátedra.

    Completa `Componente` e `Ítem` y marca con una X el estado declarado. La
    columna `Comentario` queda vacía: es la del laboratorio.
    """

    doc = abrir_plantilla(plantilla)
    reemplazar_parrafo(doc, "<Título del Proyecto<", TITULO_PROYECTO)
    actualizar_ciclo_lectivo(doc)
    # La aclaración «datos puntuales a modo de ejemplo» es de la plantilla, y
    # la instrucción al equipo de proyecto cede su lugar a las referencias.
    reemplazar_parrafo(doc, "Para los factores de Seguridad (Se incluyen", "Para los factores de Seguridad:")
    reemplazar_parrafo(doc, "El Equipo de Proyecto completará", REFERENCIAS)
    reemplazar_en_celdas(doc, "Factores de Seguridad", TITULO_TABLA)
    if len(doc.tables) != 1:
        raise SystemExit(
            f"la plantilla del Anexo 3 tiene {len(doc.tables)} tablas; se esperaba 1"
        )
    tabla = doc.tables[0]
    verificar_columnas(tabla, COLUMNAS_ENCABEZADO)
    conservar_filas(tabla, FILAS_ENCABEZADO_PLANTILLA)
    for fila in filas:
        agregar_fila(tabla, [fila.estrato, fila.item, *marcas(fila)], centradas=range(2, 9))
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
        help="Plantilla oficial del Anexo 3; con --docx escribe la entrega sobre ella.",
    )
    parser.add_argument(
        "--docx",
        type=Path,
        default=None,
        help="Destino de la entrega (requiere python-docx y --plantilla).",
    )
    args = parser.parse_args()

    filas = ordenar(
        seleccionar_seguridad(parsear_fuente(args.fuente.read_text(encoding="utf-8")))
    )

    args.salida_md.parent.mkdir(parents=True, exist_ok=True)
    args.salida_md.write_text(emitir_markdown(filas), encoding="utf-8")
    print(f"{len(filas)} ítems proyectados -> {args.salida_md}")

    if args.docx is not None:
        if args.plantilla is None:
            raise SystemExit(
                "--docx requiere --plantilla: la entrega va sobre la plantilla "
                "oficial de la cátedra, con el comentario del laboratorio vacío."
            )
        emitir_plantilla(filas, args.plantilla, args.docx)
        print(f"entrega sobre la plantilla oficial escrita en {args.docx}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
