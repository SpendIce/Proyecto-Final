#!/usr/bin/env python3
"""Recorrido offline del post de efeméride HU-011 desde Historia Viva (#85).

Corre el flujo A2 → borrador sin red ni credenciales, en una sola corrida:

1. **Generación** — `procesar_post_efemeride` consulta el puerto
   `HistoriaViva` con un `HistoriaVivaFake` alimentado desde
   `--fragmentos` (`data/fragmentos_historia_viva_sinteticos.json`),
   compone el material con `componer_material_efemeride` y genera el post
   con `FakeGenerator`: la creatividad es la salida de muestra del script.
   El borrador queda `PENDIENTE_VALIDACION` en
   `<directorio>/borradores/`, con las citas `pieza / fragmento
   (expresión temporal)` de cada fragmento y la línea `_Procedencia:_
   `synthetic_test`: el material es sintético aunque tenga la forma del
   insumo de A2.
2. **Decisión** — el borrador se declara `publicacion` pendiente en el
   registro de decisiones (`<directorio>/estado-decisiones/`) y se mintean
   los links `publique`/`descarte`, igual que haría el correo de «borrador
   listo» del canal. Nada publica: es la misma compuerta humana de siempre.
3. **Sin material** — la misma pieza sobre un período sin fragmentos
   (`--desde-vacio`/`--hasta-vacio`) termina `INCOMPLETA` /
   `material_insuficiente` sin invocar al generador ni escribir borrador:
   la efeméride sin sustento no se disimula con prosa inventada.

Salida: un JSON por fase con estados, ids y enlaces — nunca el texto del
post ni el contenido de los fragmentos en stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from agente1 import FakeGenerator, procesar_post_efemeride
from agente1.decisiones_form import (
    DecisionesFormError,
    EnlacesDecisiones,
    RegistroDecisiones,
)
from agente1.historia_viva import (
    Fragmento,
    HistoriaVivaFake,
    RangoHistorico,
)
from agente1.posts_efemeride import PROCEDENCIA_SINTETICA

ROOT = Path(__file__).resolve().parents[1]

# Ids de mentira del Form de decisiones en offline: los mismos que usan
# `scripts/atender_canal_form.py`, `scripts/registrar_form_decisiones.py` y
# `scripts/plantilla_actividad_lote_demo.py` para que el estado compartido
# sea compatible.
_FORM_ID_OFFLINE = "form_decisiones_offline"
_ENTRY_TIPO_OFFLINE = "entry.000000021"
_ENTRY_OBJETO_OFFLINE = "entry.000000022"
_ENTRY_DECISION_OFFLINE = "entry.000000023"

# Salidas del generador fake por canal: cumplen el contrato creativo de
# efeméride y ningún hecho del material — los fragmentos, las citas y la
# fecha los intercala el renderer. La misma regla que en la matriz HU-011:
# sin un dígito, una fecha ni un hecho de la fuente en la zona creativa.
_SALIDA_POR_CANAL = {
    "instagram": json.dumps(
        {
            "gancho": "Un día como hoy quedó escrito en nuestra historia.",
            "prosa": "Cada efeméride convoca a la comunidad a mirar el "
            "camino recorrido y a reconocerse en esa memoria compartida.",
            "cta": "El enlace con más contexto está en nuestro perfil.",
            "hashtags": ["#FIE", "#Efemerides", "#Centenario"],
        },
        ensure_ascii=False,
    ),
    "linkedin": json.dumps(
        {
            "gancho": "Un día como hoy quedó escrito en nuestra historia.",
            "prosa": "Cada efeméride convoca a la comunidad a mirar el "
            "camino recorrido y a reconocerse en esa memoria compartida.",
            "cta": "Hay más contexto en el enlace de esta publicación.",
            "hashtags": ["#FIE", "#Efemerides", "#Centenario"],
        },
        ensure_ascii=False,
    ),
}


class _ParserSeguro(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, "error: argumentos inválidos\n")


def _emitir(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _fecha(valor: str) -> date:
    return date.fromisoformat(valor)


def _cargar_fragmentos(path: Path) -> tuple[Fragmento, ...]:
    """Carga el fixture sintético a objetos del dominio del puerto.

    La validación la hacen los dataclasses —un id fuera de la allowlist o
    un rango invertido rompen la carga— igual que haría `ClienteHistoriaViva`
    contra el contrato crudo cuando el transporte exista.
    """

    crudo = json.loads(path.read_text(encoding="utf-8"))
    fragmentos = []
    for entrada in crudo["fragmentos"]:
        rango = entrada["rango"]
        fragmentos.append(
            Fragmento(
                fragmento_id=entrada["fragmento_id"],
                pieza_id=entrada["pieza_id"],
                texto=entrada["texto"],
                rango=RangoHistorico(
                    desde=_fecha(rango["desde"]),
                    hasta=_fecha(rango["hasta"]),
                    precision=rango["precision"],
                ),
                tipo=entrada["tipo"],
                resumen_pieza=entrada["resumen_pieza"],
                url_original=entrada["url_original"],
                validada_el=_fecha(entrada["validada_el"]),
                ubicacion=entrada.get("ubicacion"),
            )
        )
    return tuple(fragmentos)


def main(argv: list[str] | None = None) -> int:
    parser = _ParserSeguro(
        description=(
            "Recorrido offline del post de efeméride desde Historia Viva "
            "(#85): consulta al puerto, generación con citas, decisión de "
            "publicación y el caso sin material."
        )
    )
    parser.add_argument(
        "--directorio",
        type=Path,
        default=ROOT / "salida" / "post-efemeride-demo",
        help="Directorio de trabajo: borradores, logs y estado de decisiones.",
    )
    parser.add_argument(
        "--fragmentos",
        type=Path,
        default=ROOT / "data" / "fragmentos_historia_viva_sinteticos.json",
        help="Fixture JSON con los fragmentos sintéticos del acervo.",
    )
    parser.add_argument(
        "--canal",
        choices=sorted(_SALIDA_POR_CANAL),
        default="instagram",
        help="Canal del post.",
    )
    parser.add_argument(
        "--desde",
        type=_fecha,
        default=date(1926, 8, 1),
        help="Inicio del período consultado (AAAA-MM-DD).",
    )
    parser.add_argument(
        "--hasta",
        type=_fecha,
        default=date(1926, 8, 31),
        help="Fin del período consultado (AAAA-MM-DD).",
    )
    parser.add_argument(
        "--precision",
        choices=["dia", "mes", "anio", "decada"],
        default="mes",
        help="Precisión declarada del período: cuánto puede decir la efeméride.",
    )
    parser.add_argument(
        "--tema",
        help="Tema opcional de la búsqueda; se audita como hash, nunca en claro.",
    )
    parser.add_argument(
        "--desde-vacio",
        type=_fecha,
        default=date(1900, 1, 1),
        help="Inicio del período sin material (AAAA-MM-DD).",
    )
    parser.add_argument(
        "--hasta-vacio",
        type=_fecha,
        default=date(1900, 12, 31),
        help="Fin del período sin material (AAAA-MM-DD).",
    )
    try:
        args = parser.parse_args(argv)
        directorio = args.directorio
        historia_viva = HistoriaVivaFake(
            fragmentos=_cargar_fragmentos(args.fragmentos)
        )

        # --- Fase 1: generación ---------------------------------------
        resultado = procesar_post_efemeride(
            historia_viva=historia_viva,
            desde=args.desde,
            hasta=args.hasta,
            canal=args.canal,
            directorio_salida=directorio,
            generator=FakeGenerator(_SALIDA_POR_CANAL[args.canal]),
            precision=args.precision,
            tema=args.tema,
            procedencia=PROCEDENCIA_SINTETICA,
        )
        objeto_id = (
            resultado.borrador_path.stem if resultado.borrador_path else None
        )
        _emitir(
            {
                "fase": "generacion",
                "estado": resultado.estado,
                "borrador": (
                    str(resultado.borrador_path)
                    if resultado.borrador_path
                    else None
                ),
                "objeto_id": objeto_id,
                "fragmentos_consultados": len(historia_viva.consultas),
                "error": resultado.error,
            }
        )
        if resultado.estado != "PENDIENTE_VALIDACION":
            return 1
        assert objeto_id is not None

        # --- Fase 2: decisión de publicación ---------------------------
        enlazador = EnlacesDecisiones(
            registro=RegistroDecisiones(directorio / "estado-decisiones"),
            form_id=_FORM_ID_OFFLINE,
            entry_tipo=_ENTRY_TIPO_OFFLINE,
            entry_objeto=_ENTRY_OBJETO_OFFLINE,
            entry_decision=_ENTRY_DECISION_OFFLINE,
        )
        enlaces = enlazador.enlaces_publicacion(
            objeto_id=objeto_id,
            pieza="post",
            correlation_id=resultado.correlation_id,
        )
        _emitir(
            {
                "fase": "decision",
                "objeto_id": objeto_id,
                "enlaces": enlaces,
            }
        )

        # --- Fase 3: la misma consulta sin material --------------------
        vacio = procesar_post_efemeride(
            historia_viva=historia_viva,
            desde=args.desde_vacio,
            hasta=args.hasta_vacio,
            canal=args.canal,
            directorio_salida=directorio,
            generator=FakeGenerator(_SALIDA_POR_CANAL[args.canal]),
            procedencia=PROCEDENCIA_SINTETICA,
        )
        _emitir(
            {
                "fase": "sin_material",
                "estado": vacio.estado,
                "borrador": (
                    str(vacio.borrador_path) if vacio.borrador_path else None
                ),
                "error": vacio.error,
            }
        )
        return 0 if vacio.estado == "INCOMPLETA" else 1
    except DecisionesFormError as exc:
        _emitir({"estado": "RECHAZADA", "resultado": exc.code})
        return 2
    except Exception:
        _emitir({"estado": "FALLIDA", "resultado": "runner_unavailable"})
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
