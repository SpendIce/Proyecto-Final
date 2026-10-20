#!/usr/bin/env python3
"""Recorrido offline de la plantilla de correo por actividad (#73).

Corre el circuito completo sin red, en una sola corrida y con los runners
reales:

1. **Generación** — `procesar_plantilla_actividad` con el generador fake:
   la actividad sale del CSV (`--csv`, `--actividad`) y el plan de pago,
   si se declara, de `--plan-csv`. El resultado es un borrador
   `PENDIENTE_VALIDACION` en `<directorio>/borradores/` más los ids de los
   dos objetos de decisión: la plantilla (`tpl-…`) y el lote (`lote-…`).
2. **Decisión** — los dos objetos se declaran pendientes en el registro de
   decisiones (`<directorio>/estado-decisiones/`), igual que haría el
   correo de «borrador listo» del canal. Después una "hoja de respuestas"
   CSV — `--respuestas-csv`, o la que el propio script escribe con las tres
   aprobaciones del circuito— pasa por `CanalFormDecisiones`, que valida
   rol y catálogo igual que el Form real. El correo de cada respuesta se
   resuelve contra el padrón (`--padron-roles`), nunca contra un supuesto.
3. **Lote** — con las tres decisiones `registrada`, `correr_lote_actividad`
   renderiza el correo de cada preinscripto del padrón de la actividad
   (`--padron-csv`), encola con clave idempotente y drena la cola contra
   `DestinoConfirmacionesFake`. Las entregas simuladas quedan en
   `<directorio>/entregas-simuladas/` para inspección: llevan la marca
   `BORRADOR — NO ENVIAR` y no son correos reales.

La segunda corrida con el mismo documento es `DUPLICADA` y no reenvía:
la clave cubre actividad, inscripción y hash del documento aprobado.

Salida: un JSON por fase con estados, ids y conteos — nunca correos ni
cuerpos en stdout.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from agente1 import FakeGenerator
from agente1.canal_form import (
    CanalFormError,
    LectorValoresCsv,
    cargar_padron_roles_csv,
)
from agente1.confirmaciones import (
    ColaEnviosArchivo,
    DestinoConfirmacionesFake,
    RegistroConfirmacionesArchivo,
)
from agente1.decisiones_form import (
    DECISION_APRUEBO_LOTE,
    DECISION_APRUEBO_SEMANTICA,
    DECISION_APRUEBO_UTILITARIA,
    TIPO_LOTE,
    TIPO_PLANTILLA,
    CanalFormDecisiones,
    DecisionesFormError,
    EnlacesDecisiones,
    RegistroDecisiones,
)
from agente1.fuentes import CsvFuenteSolicitudes, FuenteSolicitudesError
from agente1.pagos import (
    ControlPagosError,
    cargar_padron_csv,
    cargar_plan_pagos_csv,
)
from agente1.plantillas_actividad import (
    DestinatarioActividad,
    correr_lote_actividad,
    procesar_plantilla_actividad,
)
from agente1.workspace_config import ConfiguracionWorkspaceError
from agente1.workspace_e2e import RunnerWorkspaceError

ROOT = Path(__file__).resolve().parents[1]

# Ids de mentira del segundo Form en offline: el contrato de links se
# ensaya igual, sin red. Son los mismos que usan
# `scripts/atender_canal_form.py` y `scripts/registrar_form_decisiones.py`
# para que el estado compartido sea compatible.
_FORM_ID_OFFLINE = "form_decisiones_offline"
_ENTRY_TIPO_OFFLINE = "entry.000000021"
_ENTRY_OBJETO_OFFLINE = "entry.000000022"
_ENTRY_DECISION_OFFLINE = "entry.000000023"

# Correos del padrón de roles sintético de la demo: sólo existen en el
# CSV `--padron-roles` que el recorrido documenta. `responsable` firma la
# aprobación semántica y `coordinador` la utilitaria y el lote.
_CORREO_SEMANTICA = "rgc@example.invalid"
_CORREO_UTILITARIA = "coord@example.invalid"

# Salida del generador fake: desde `plantilla_actividad_v2` (#140) el
# modelo devuelve sólo un párrafo de prosa descriptiva, sin un solo dato ni
# variable. El saludo, las variables, el bloque de pago (con plan) y el
# contacto los compone el pipeline.
_PROSA_PLANTILLA = (
    "La propuesta acerca contenidos y herramientas de la facultad a la "
    "comunidad, con un formato abierto y pensado para quienes se acercan "
    "por primera vez. Las instancias de trabajo combinan encuentros "
    "guiados con espacios de consulta, y el equipo docente acompaña a "
    "cada participante durante todo el recorrido."
)


class _ParserSeguro(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, "error: argumentos inválidos\n")


def _emitir(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _respuestas_sinteticas(path: Path, *, plantilla_id: str, lote_id: str) -> None:
    """La "hoja" del Form de decisiones con las tres aprobaciones.

    La escribe el script porque los ids son dinámicos (derivan del hash
    del documento): en la demostración real una persona copiaría los
    links del correo de aviso. El archivo queda en el directorio de
    trabajo como evidencia de qué se leyó.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(
            ["Marca temporal", "Correo", "Tipo", "Objeto", "Decisión"]
        )
        escritor.writerow(
            [
                "2026-10-11 09:00:00",
                _CORREO_SEMANTICA,
                TIPO_PLANTILLA,
                plantilla_id,
                DECISION_APRUEBO_SEMANTICA,
            ]
        )
        escritor.writerow(
            [
                "2026-10-11 09:05:00",
                _CORREO_UTILITARIA,
                TIPO_PLANTILLA,
                plantilla_id,
                DECISION_APRUEBO_UTILITARIA,
            ]
        )
        escritor.writerow(
            [
                "2026-10-11 09:10:00",
                _CORREO_UTILITARIA,
                TIPO_LOTE,
                lote_id,
                DECISION_APRUEBO_LOTE,
            ]
        )


def main(argv: list[str] | None = None) -> int:
    parser = _ParserSeguro(
        description=(
            "Recorrido offline de la plantilla por actividad (#73): "
            "generación, decisiones del Form y lote de envíos simulado."
        )
    )
    parser.add_argument(
        "--directorio",
        type=Path,
        default=ROOT / "tmp" / "plantilla-actividad-demo",
        help="Directorio de trabajo: borradores, logs, estado y entregas simuladas.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Dataset de actividades (formato actividades_v2).",
    )
    parser.add_argument(
        "--actividad",
        required=True,
        help="id_actividad de la fila del dataset.",
    )
    parser.add_argument(
        "--plan-csv",
        type=Path,
        help="Plan de pago en formato largo. Con plan, el cuerpo compuesto lleva las variables de cuotas y medios.",
    )
    parser.add_argument(
        "--padron-csv",
        type=Path,
        required=True,
        help="Padrón de preinscriptos de la actividad (id_inscripcion, actividad_id, nombre, email, bonificado).",
    )
    parser.add_argument(
        "--padron-roles",
        type=Path,
        required=True,
        help="Padrón de roles del circuito de decisiones (CSV correo,rol).",
    )
    parser.add_argument(
        "--respuestas-csv",
        type=Path,
        help=(
            "CSV que imita la hoja del Form de decisiones. Sin él, el "
            "script escribe en <directorio>/respuestas-decisiones.csv las "
            "tres aprobaciones del circuito con los correos del padrón "
            "sintético del recorrido."
        ),
    )
    try:
        args = parser.parse_args(argv)

        directorio = args.directorio
        directorio_decisiones = directorio / "estado-decisiones"
        registro_decisiones = RegistroDecisiones(directorio_decisiones)

        plan = (
            cargar_plan_pagos_csv(args.plan_csv)
            if args.plan_csv is not None
            else None
        )
        if plan is not None and plan.actividad_id != args.actividad:
            raise RunnerWorkspaceError("plan_actividad_distinta")

        # --- Fase 1: generación ---------------------------------------
        resultado = procesar_plantilla_actividad(
            fuente=CsvFuenteSolicitudes(args.csv),
            id_solicitud=args.actividad,
            directorio_salida=directorio,
            generator=FakeGenerator(_PROSA_PLANTILLA),
            planes_pago=(
                {args.actividad: plan} if plan is not None else None
            ),
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
                "plantilla_id": resultado.plantilla_id,
                "lote_id": resultado.lote_id,
                "error": resultado.error,
            }
        )
        if resultado.estado != "PENDIENTE_VALIDACION":
            return 1
        assert resultado.documento is not None
        documento = resultado.documento
        plantilla_id = resultado.plantilla_id
        lote_id = resultado.lote_id

        # --- Fase 2: decisión ------------------------------------------
        enlazador = EnlacesDecisiones(
            registro=registro_decisiones,
            form_id=_FORM_ID_OFFLINE,
            entry_tipo=_ENTRY_TIPO_OFFLINE,
            entry_objeto=_ENTRY_OBJETO_OFFLINE,
            entry_decision=_ENTRY_DECISION_OFFLINE,
        )
        enlaces_plantilla = enlazador.declarar_y_enlaces(
            tipo=TIPO_PLANTILLA,
            objeto_id=plantilla_id,
            detalle={"actividad": args.actividad},
        )
        enlaces_lote = enlazador.declarar_y_enlaces(
            tipo=TIPO_LOTE,
            objeto_id=lote_id,
            detalle={"actividad": args.actividad},
        )
        _emitir(
            {
                "fase": "declaracion",
                "plantilla": {
                    "objeto_id": plantilla_id,
                    "enlaces": enlaces_plantilla,
                },
                "lote": {"objeto_id": lote_id, "enlaces": enlaces_lote},
            }
        )

        respuestas = args.respuestas_csv
        if respuestas is None:
            respuestas = directorio / "respuestas-decisiones.csv"
            _respuestas_sinteticas(
                respuestas, plantilla_id=plantilla_id, lote_id=lote_id
            )
        padron_roles = cargar_padron_roles_csv(args.padron_roles)
        canal = CanalFormDecisiones(
            lector=LectorValoresCsv(respuestas),
            padron=padron_roles,
            registro=registro_decisiones,
        )
        procesadas = canal.atender()
        _emitir(
            {
                "fase": "decisiones",
                "respuestas": str(respuestas),
                "procesadas": [
                    {
                        "tipo": r.tipo,
                        "objeto_id": r.objeto_id,
                        "decision": r.decision,
                        "resultado": r.resultado,
                        "rechazo_codigo": r.rechazo_codigo,
                        "rol": r.rol,
                    }
                    for r in procesadas
                ],
            }
        )

        # --- Fase 3: lote ----------------------------------------------
        fila = CsvFuenteSolicitudes(args.csv).obtener(args.actividad)
        preinscriptos = cargar_padron_csv(
            args.padron_csv, actividad_id=args.actividad
        )
        destinatarios = tuple(
            DestinatarioActividad(
                id_inscripcion=p.id_inscripcion,
                nombre_destinatario=p.nombre_destinatario,
                email_destinatario=p.email_destinatario,
            )
            for p in preinscriptos
        )
        registro = RegistroConfirmacionesArchivo(
            directorio / "registro-confirmaciones"
        )
        cola = ColaEnviosArchivo(directorio / "cola-envios")
        destino = DestinoConfirmacionesFake()
        resultado_lote, drenajes = correr_lote_actividad(
            documento=documento,
            fila=fila,
            plan=plan,
            destinatarios=destinatarios,
            decisiones=registro_decisiones,
            registro=registro,
            cola=cola,
            destino=destino,
            directorio_salida=directorio,
        )

        directorio_entregas = directorio / "entregas-simuladas"
        directorio_entregas.mkdir(parents=True, exist_ok=True)
        for indice, entrega in enumerate(destino.entregas, start=1):
            (directorio_entregas / f"entrega-{indice:02d}.txt").write_text(
                "ENTREGA SIMULADA — no es un correo real\n"
                f"destinatario: {entrega.destinatario}\n"
                f"asunto: {entrega.asunto}\n\n"
                f"{entrega.cuerpo}",
                encoding="utf-8",
            )
        _emitir(
            {
                "fase": "lote",
                "estado": resultado_lote.estado,
                "error": resultado_lote.error,
                "items": len(resultado_lote.items),
                "drenajes": [d.resolucion for d in drenajes],
                "entregas_simuladas": len(destino.entregas),
                "directorio_entregas": str(directorio_entregas),
            }
        )
        return 0 if resultado_lote.estado == "ENVIO_ENCOLADO" else 1
    except (
        RunnerWorkspaceError,
        DecisionesFormError,
        CanalFormError,
        ConfiguracionWorkspaceError,
    ) as exc:
        _emitir({"estado": "RECHAZADA", "resultado": exc.code})
        return 2
    except (FuenteSolicitudesError, ControlPagosError) as exc:
        _emitir({"estado": "FALLIDA", "resultado": exc.code})
        return 3
    except Exception:
        _emitir({"estado": "FALLIDA", "resultado": "runner_unavailable"})
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
