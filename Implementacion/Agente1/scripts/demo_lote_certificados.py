#!/usr/bin/env python3
"""Carga un lote de certificados ficticio para la demo del canal web (#168).

La web del Agente 1 muestra el lote de HU-014 en la bandeja, con la lista de
cierre, el certificado de muestra marcado borrador y la decisión atada al
hash. En producción ese lote lo crea el circuito de emisión; para la
presentación sin Drive ni la Sheet D2, este script siembra un lote de demo
directamente sobre la base del canal.

Qué carga:

- La actividad sale del CSV del prototipo —`AGENTE1_TABLA`, el `--tabla` o
  los datasets del repo—: `FIE-DIF-02` por defecto. Si la fila no declara
  la carga horaria, se usa `24` como dato de demo declarado en la salida.
- 6 personas ficticias (`Persona Ficticia 1`…), con DNI de mentira, sin
  correos reales (`@example.invalid`) y condición `aprobacion`.
- Una línea descriptiva de demo, sin cifras ni hechos institucionales.
- El generador es el correo que después tiene que ingresar a la demo para
  aprobar: `--generador` o el primero de `AGENTE1_WEB_DEMO_CORREOS`.

El alta es idempotente por el hash canónico de la lista: correrlo dos veces
devuelve el mismo lote. Uso dentro del contenedor `web` (o `worker`), que ya
tiene el DSN del canal en el entorno:

    docker exec -it agente1-web-1 \
        python scripts/demo_lote_certificados.py --generador <correo demo>

Salida: una línea JSON con el id, el hash y la URL del lote, y el correo con
el que hay que ingresar. Nunca imprime los correos de las personas de la
lista ni escribe fuera de la base.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente1.canal_form import hash_correo  # noqa: E402
from agente1.certificados_emision import (  # noqa: E402
    ListaCierreError,
    PersonaCierre,
)
from agente1.fuentes import (  # noqa: E402
    CsvFuenteSolicitudes,
    FuenteSolicitudesError,
)
from agente1.web.certificados_web import (  # noqa: E402
    LoteCertificadosError,
    RepositorioLotes,
)
from agente1.web.persistencia import conectar  # noqa: E402

ACTIVIDAD_DEMO = "FIE-DIF-02"
CANTIDAD_DEMO = 6
CANTIDAD_MINIMA = 5
CANTIDAD_MAXIMA = 8
HORAS_DEMO = "24"
MODALIDAD_DEMO = "presencial"
CORPUS_ACTIVIDADES = ROOT / "data" / "corpus-fie-informa-difusiones.csv"
ACTIVIDADES_SINTETICAS = ROOT / "data" / "actividades_sinteticas.csv"
LINEA_DEMO = (
    "Curso introductorio sobre herramientas de inteligencia artificial "
    "para organizar y analizar información institucional."
)
_CAMPOS_ACTIVIDAD = (
    "titulo",
    "duracion_horas",
    "modalidad",
    "fecha_inicio",
    "fecha_fin",
    "organiza",
)


def _personas_demo(cantidad: int = CANTIDAD_DEMO) -> tuple[PersonaCierre, ...]:
    """Filas ficticias, marcadas como tales y sin correos reales."""
    return tuple(
        PersonaCierre(
            nombre=f"Persona Ficticia {indice}",
            apellido="Demo",
            dni=f"900000{indice:02d}",
            mail=f"persona.ficticia.{indice}@example.invalid",
            tratamiento="Sra." if indice % 2 == 0 else "Sr.",
            condicion="aprobacion",
        )
        for indice in range(1, cantidad + 1)
    )


def _cargar_actividad(
    id_actividad: str, rutas: list[Path | str | None]
) -> tuple[dict[str, str], str, bool]:
    """Primera fila válida de la actividad en los CSV candidatos.

    Devuelve `(datos, ruta_de_origen, horas_demo)`. `horas_demo` avisa que
    la carga horaria no estaba en la fila y se completó con el valor de
    demo; el resto de los campos institucionales sale del CSV.
    """
    for ruta in rutas:
        if ruta is None or not str(ruta).strip():
            continue
        path = Path(str(ruta))
        try:
            fila = CsvFuenteSolicitudes(path).obtener(id_actividad)
        except (FuenteSolicitudesError, OSError):
            continue
        datos = {
            campo: str(fila.get(campo, "") or "").strip()
            for campo in _CAMPOS_ACTIVIDAD
        }
        horas_demo = False
        if not datos["duracion_horas"]:
            datos["duracion_horas"] = HORAS_DEMO
            horas_demo = True
        if not datos["modalidad"]:
            datos["modalidad"] = MODALIDAD_DEMO
        if all(datos[campo] for campo in ("titulo", "fecha_inicio", "organiza")):
            return datos, str(path), horas_demo
    raise LoteCertificadosError("demo_actividad_ausente")


def _invalida(code: str) -> int:
    print(json.dumps({"status": "INVALID", "error_code": code}, sort_keys=True))
    return 2


def _generador(entorno: Mapping[str, str], explicito: str | None) -> str:
    if explicito and explicito.strip():
        return explicito.strip()
    correos = [
        correo.strip()
        for correo in entorno.get("AGENTE1_WEB_DEMO_CORREOS", "").split(",")
        if correo.strip()
    ]
    return correos[0] if correos else ""


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actividad", default=ACTIVIDAD_DEMO)
    parser.add_argument(
        "--tabla",
        default=None,
        help="CSV de actividades; si no, AGENTE1_TABLA y los datasets del repo.",
    )
    parser.add_argument("--cantidad", type=int, default=CANTIDAD_DEMO)
    parser.add_argument(
        "--generador",
        default=None,
        help="Correo que genera el lote y después lo aprueba en la web.",
    )
    parser.add_argument(
        "--dsn",
        default=None,
        help="DSN del canal; por defecto AGENTE1_POSTGRES_DSN.",
    )
    args = parser.parse_args(argv)
    entorno = environ if environ is not None else os.environ

    dsn = (args.dsn or entorno.get("AGENTE1_POSTGRES_DSN") or "").strip()
    if not dsn:
        return _invalida("demo_dsn_ausente")
    generador = _generador(entorno, args.generador)
    if "@" not in generador:
        return _invalida("demo_generador_ausente")
    if not CANTIDAD_MINIMA <= args.cantidad <= CANTIDAD_MAXIMA:
        return _invalida("demo_cantidad_invalida")

    rutas = [
        args.tabla,
        entorno.get("AGENTE1_TABLA"),
        CORPUS_ACTIVIDADES,
        ACTIVIDADES_SINTETICAS,
    ]
    try:
        actividad, origen, horas_demo = _cargar_actividad(
            args.actividad, rutas
        )
    except LoteCertificadosError as error:
        return _invalida(error.code)

    repositorio = RepositorioLotes(functools.partial(conectar, dsn))
    try:
        lote = repositorio.crear(
            id_actividad=args.actividad,
            actividad=actividad,
            personas=_personas_demo(args.cantidad),
            linea_descriptiva=LINEA_DEMO,
            generada_por_hash=hash_correo(generador),
        )
    except (LoteCertificadosError, ListaCierreError) as error:
        return _invalida(error.code)

    print(
        json.dumps(
            {
                "status": "OK",
                "datos_demo": True,
                "id_lote": lote.id_lote,
                "id_actividad": lote.id_actividad,
                "personas": lote.cantidad_personas,
                "hash_lote": lote.objeto_lote,
                "estado": lote.estado,
                "actividad_origen": origen,
                "horas_demo": horas_demo,
                "generador": generador,
                "url": f"/certificados/{lote.id_lote}",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0



if __name__ == "__main__":
    sys.exit(main())
