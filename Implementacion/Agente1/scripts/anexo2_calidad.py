"""Anexo 2 del laboratorio: tabla de calidad por atributo.

Lee la tabla marcada ``TABLA-FUENTE`` de
``Documentos/Laboratorio/Perfil-Calidad-Sistema-Demostracion-v1.md`` y emite la
tabla del Anexo 2 por atributo, en el orden de ISO/IEC 25010:2023, con las
subcaracterísticas aplicables de ISO/IEC 25059:2023, el conjunto reducido de
ISO/IEC 25012 y la fila única de Seguridad que remite al Anexo 3.

Dos salidas, con dos propósitos distintos:

- **Proyección en Markdown** (``Anexo2-Calidad-Proyeccion-v1.md``): la vista de
  trabajo, con la declaración completa del autor (estado, motivo, evidencia y
  paso en vivo). Es interna: no se entrega.
- **Entrega sobre la plantilla oficial** (``--plantilla``): el ``.docx`` que sí
  va al laboratorio, volcado sobre ``3.2 - Anexo 2 - Calidad 2025.docx``.

El reparto de columnas lo fija el correo del laboratorio del 27/10 (Maiorano):
el equipo de proyecto completa ``Factor de calidad`` y ``Atributo`` y
**transcribe el estado que declara** en ``Nivel de Competencia`` (por atributo)
y ``Nivel de Competencia Global`` (por factor, el peor de sus atributos); el
laboratorio completa sólo ``Comentarios``, a modo de checklist. El correo del
14/10 había dejado los niveles al laboratorio; el del 27/10 lo cambió. El
motivo y la evidencia siguen en el Anexo 1. La redacción de los niveles es la
del ejemplo aprobado de 2025.

Uso:

    uv run python scripts/anexo2_calidad.py
        # escribe Documentos/Laboratorio/Anexo2-Calidad-Proyeccion-v1.md

    uv run --with python-docx python scripts/anexo2_calidad.py \\
        --plantilla "Contenido/DocumentacionAnteproyecto/Revision-Laboratorio-2025/3.2 - Anexo 2 - Calidad 2025.docx" \\
        --docx Documentos/Laboratorio/Entrega/Anexo2-Calidad.docx
        # escribe la entrega sobre la plantilla oficial. Requiere python-docx.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from anexos_seleccion import seleccionar_calidad  # noqa: E402
from plantilla_laboratorio import (  # noqa: E402
    TITULO_PROYECTO,
    abrir_plantilla,
    actualizar_ciclo_lectivo,
    agregar_fila,
    conservar_filas,
    fijar_anchos,
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

# Texto bajo «Referencias:»: los estándares que se aplicaron.
REFERENCIAS = (
    "ISO/IEC 25010:2023 (calidad del producto), ISO/IEC 25059:2023 (calidad "
    "de sistemas de IA) e ISO/IEC 25012 (calidad de datos). El estado y el "
    "motivo que declara el autor por atributo están en el Anexo 1."
)

# Título de la tabla: la plantilla pide «<Citar estándar aplicado>».
TITULO_TABLA = (
    "Factores de Calidad: ISO/IEC 25010:2023, con subcaracterísticas de "
    "ISO/IEC 25059:2023 y el conjunto reducido de ISO/IEC 25012:2023. "
    "Seguridad remite al Anexo 3"
)

# Anchos de columna en twips (el total es el de la plantilla, 9344). La
# plantilla deja 3 cm para el nivel y «satisfactoriamente» se partía en dos.
ANCHOS_COLUMNAS = [1700, 1736, 2200, 1500, 2208]

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

# Texto de cada estado en las columnas de nivel, con la redacción del ejemplo
# aprobado de 2025 y la escala del procedimiento (`3.0 - Procedimiento 2025`).
# Sólo se transcriben estados de atributos declarados: `No aplica` y `Remite`
# no tienen nivel y hacen fallar el volcado.
NIVEL_POR_ESTADO = {
    "A": "A - Implementado satisfactoriamente",
    "B": "B - Implementado con observaciones",
    "C": "C - Previsto, no implementado",
}
NIVEL_GLOBAL_POR_ESTADO = {
    "A": "Muy bueno",
    "B": "Bueno",
    "C": "Previsto, no implementado",
}


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


def proyectar(
    filas: list[FilaFuente], permitir_faltantes: bool = False
) -> list[tuple[str, str, str, str, str, str]]:
    """Agrupa por (característica, atributo) en el orden del estándar.

    Devuelve filas de seis celdas: característica, atributo, estado declarado,
    motivo consolidado por estrato, evidencia y paso en vivo.

    ``permitir_faltantes`` lo usa el recorte de la selección: la fuente completa
    se valida entera y después se proyecta sólo lo que se declara.
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
    if faltantes and not permitir_faltantes:
        raise ValueError(
            "atributos del orden canónico sin fila en la fuente: "
            + ", ".join(f"{c}/{a}" for c, a in faltantes)
        )

    salida: list[tuple[str, str, str, str, str, str]] = []
    for caracteristica, atributos in ORDEN_CARACTERISTICAS:
        for atributo in atributos:
            grupo = por_clave.get((caracteristica, atributo))
            if not grupo:
                # El recorte de la selección deja atributos afuera: no se
                # declaran, pero siguen en el perfil.
                continue
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


def _partes(estado: str) -> list[str]:
    """`A/B/C` -> `[A, B, C]`; `A + RA` -> `[A]`. Falla con un estado sin nivel."""

    partes = [parte.split("+", 1)[0].strip() for parte in estado.split("/")]
    sin_nivel = [parte for parte in partes if parte not in NIVEL_POR_ESTADO]
    if sin_nivel:
        raise ValueError(
            f"el estado {estado!r} no tiene nivel de competencia; "
            "un atributo No aplica o Remite no se declara en el Anexo 2"
        )
    return partes


def _peor(estados: list[str]) -> str:
    return max(estados, key=list(NIVEL_POR_ESTADO).index)


def nivel_de_competencia(estado: str) -> str:
    """Nivel por atributo. Un atributo mixto toma su peor parte implementada."""

    partes = _partes(estado)
    implementadas = [parte for parte in partes if parte in ("A", "B")]
    texto = NIVEL_POR_ESTADO[_peor(implementadas or partes)]
    if len(partes) > 1:
        texto += (
            f" (partes en {', '.join(partes[:-1])} y {partes[-1]}; "
            "el detalle está en el Anexo 1)"
        )
    return texto


def niveles_globales(
    filas: list[tuple[str, str, str, str, str, str]],
) -> dict[str, str]:
    """Nivel global por factor: el peor nivel de sus atributos declarados."""

    por_factor: dict[str, list[str]] = {}
    for caracteristica, _atributo, estado, *_ in filas:
        partes = _partes(estado)
        implementadas = [parte for parte in partes if parte in ("A", "B")]
        por_factor.setdefault(caracteristica, []).append(_peor(implementadas or partes))
    return {
        factor: NIVEL_GLOBAL_POR_ESTADO[_peor(estados)]
        for factor, estados in por_factor.items()
    }


def emitir_markdown(filas: list[tuple[str, str, str, str, str, str]]) -> str:
    lineas = [
        "# Anexo 2: Tabla de calidad por atributo (proyección)",
        "",
        "Documento generado por `Implementacion/Agente1/scripts/anexo2_calidad.py`",
        "desde la tabla fuente `Documentos/Laboratorio/Perfil-Calidad-Sistema-Demostracion-v1.md`",
        "(foto del corte del 26/10/2026, versión 0.5.9, tag `agente1-v0.5.9`: el "
        "sistema en contenedores en el servidor de la facultad (ADR 0013), los siete "
        "tipos de gacetilla declarados (#121), el set de evaluación de dos ejes (#111), "
        "el tipo en el canal (#122) y el modelo `gemma4:e4b` (#51)).",
        "",
        "Declara una **selección** de hasta 3 atributos por componente "
        "(`scripts/anexos_seleccion.py`); el perfil completo queda en la fuente.",
        "",
        "Columnas de la plantilla oficial «3.2 - Anexo 2 - Calidad 2025.docx»:",
        "Factor de calidad | Atributo | Nivel de Competencia | Nivel de Competencia",
        "Global | Comentarios. El equipo de proyecto completa el factor, el atributo",
        "y transcribe el estado declarado en los dos niveles (A: «Implementado",
        "satisfactoriamente» / «Muy bueno»; B: «Implementado con observaciones» /",
        "«Bueno»; el global es el peor del factor). El laboratorio completa sólo",
        "`Comentarios` (correo del 27/10). Seguridad remite al Anexo 3 (#58).",
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

    Completa factor, atributo y los dos niveles de competencia con el estado
    declarado. `Comentarios` queda vacía: es la del laboratorio.
    """

    doc = abrir_plantilla(plantilla)
    reemplazar_parrafo(doc, "<Título del Proyecto<", TITULO_PROYECTO)
    actualizar_ciclo_lectivo(doc)
    # La aclaración «datos puntuales a modo de ejemplo» es de la plantilla, y
    # la instrucción al equipo de proyecto cede su lugar a las referencias.
    reemplazar_parrafo(doc, "Factores de calidad considerados (Se incluyen", "Factores de calidad considerados:")
    reemplazar_parrafo(doc, "El Equipo de Proyecto completará", REFERENCIAS)
    reemplazar_en_celdas(doc, "Factores de Calidad", TITULO_TABLA)
    if len(doc.tables) != 1:
        raise SystemExit(
            f"la plantilla del Anexo 2 tiene {len(doc.tables)} tablas; se esperaba 1"
        )
    tabla = doc.tables[0]
    verificar_columnas(tabla, COLUMNAS_ENCABEZADO)
    conservar_filas(tabla, FILAS_ENCABEZADO_PLANTILLA)
    globales = niveles_globales(filas)
    for caracteristica, atributo, estado, _motivo, _evidencia, _paso in filas:
        agregar_fila(
            tabla,
            [caracteristica, atributo, nivel_de_competencia(estado), globales[caracteristica]],
        )
    fijar_anchos(tabla, ANCHOS_COLUMNAS, desde_fila=1)
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
    proyectar(filas_fuente)  # la fuente completa se valida entera
    filas = proyectar(seleccionar_calidad(filas_fuente), permitir_faltantes=True)

    args.salida_md.parent.mkdir(parents=True, exist_ok=True)
    args.salida_md.write_text(emitir_markdown(filas), encoding="utf-8")
    print(f"{len(filas)} atributos proyectados desde {len(filas_fuente)} filas -> {args.salida_md}")

    if args.docx is not None:
        if args.plantilla is None:
            raise SystemExit(
                "--docx requiere --plantilla: la entrega va sobre la plantilla "
                "oficial de la cátedra, con los comentarios del laboratorio vacíos."
            )
        emitir_plantilla(filas, args.plantilla, args.docx)
        print(f"entrega sobre la plantilla oficial escrita en {args.docx}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
