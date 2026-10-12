"""Subcomando `control-pagos`: la corrida de control de pagos por línea de
comandos.

Envoltura delgada de `pagos.correr_control_pagos`: carga el plan y el padrón
desde sus CSV, las novedades del Departamento desde su CSV cuando se pasa
`--novedades`, apunta el buzón a una carpeta `.eml` y vuelca el informe a
stdout como JSON con claves ordenadas — la misma convención de la CLI
principal, para poder comparar la salida entre corridas y guardarla como
evidencia. El informe nombra a cada preinscripto con su «k de N» desglosado,
marca la bonificación no verificable (D14), lista las respuestas no asociadas
y las novedades aplicadas junto con las que se informan como error, para que
una persona las resuelva, y enumera el lote de recordatorios planeado y los
candidatos a confirmación de inscripción (cuota 1 `PAGO_CONFIRMADO` o
`BONIFICADA`, D9); no se escribe ningún archivo ni se persiste estado
(ADR 0003).

La bandera `--planilla` cambia el soporte de las tres fuentes tabulares: en
lugar de CSV, plan, padrón y novedades se leen de las pestañas de la planilla
D2 por `GoogleSheetsFuentePagos` (demo en vivo). En ese modo los argumentos
`--plan`, `--padron` y `--novedades` no aplican — el buzón sigue siendo la
carpeta `.eml` de `--buzon` — y la configuración sale del entorno:
`AGENTE1_WORKSPACE_SPREADSHEET_ID` y `AGENTE1_WORKSPACE_ACCESS_TOKEN`, más
`AGENTE1_PAGOS_RANGO_PLAN`, `AGENTE1_PAGOS_RANGO_PADRON` y
`AGENTE1_PAGOS_RANGO_NOVEDADES`.

El código de salida distingue estados igual que la CLI principal: `0` si la
corrida produjo informe, `2` si cualquier entrada falló — plan, padrón,
novedades, buzón, fecha o configuración — con el código de error cerrado y
sin datos internos en `error`.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

from .buzon import BuzonPropioEml, BuzonPropioError
from .google_workspace import TransporteHttp
from .pagos import (
    ESTADO_BONIFICADA,
    ESTADO_COMPROBANTE_PRESENTADO,
    ESTADO_PAGO_CONFIRMADO,
    Comprobante,
    ControlPagosError,
    InformeCorridaPagos,
    NovedadPago,
    cargar_novedades_csv,
    cargar_padron_csv,
    cargar_plan_pagos_csv,
    correr_control_pagos,
    fecha_de_corrida,
)
from .pagos_sheets import GoogleSheetsFuentePagos
from .workspace_config import ConfiguracionWorkspaceError, TokenEntornoProvider


def main(
    argv: Sequence[str] | None = None,
    *,
    transport: TransporteHttp | None = None,
) -> int:
    """Corre el control de pagos y devuelve el código de salida del proceso.

    `transport` es la misma costura que tienen los adapters de Workspace: en
    producción queda `None` y el adapter usa HTTPS real; en las pruebas se
    inyecta el transporte falso y el modo `--planilla` se ejercita entero sin
    red.
    """

    parser = argparse.ArgumentParser(
        prog="agente1 control-pagos",
        description=(
            "Corrida de control de pagos: informa las cuotas de cada "
            "preinscripto, las respuestas no asociadas y las novedades "
            "aplicadas o informadas como error."
        ),
    )
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--padron", type=Path)
    parser.add_argument("--buzon", required=True, type=Path)
    parser.add_argument(
        "--novedades",
        type=Path,
        default=None,
        help="CSV de la pestaña «Novedades de pago» del Departamento (opcional).",
    )
    parser.add_argument(
        "--planilla",
        action="store_true",
        help=(
            "lee plan, padrón y novedades de las pestañas de la planilla D2 "
            "en lugar de CSV (configuración por entorno; ver docstring)."
        ),
    )
    parser.add_argument(
        "--fecha",
        type=_fecha_arg,
        default=None,
        metavar="AAAA-MM-DD",
        help=(
            "Día de la corrida; sin el flag se toma la fecha de calendario de "
            "America/Argentina/Buenos_Aires al momento de ejecutar."
        ),
    )
    args = parser.parse_args(argv)

    # Las dos formas de alimentar la corrida son excluyentes y cada una exige
    # las suyas: CSV pide sus dos archivos (novedades opcional), la planilla
    # lee las tres pestañas y no admite rutas.
    if args.planilla:
        if (
            args.plan is not None
            or args.padron is not None
            or args.novedades is not None
        ):
            parser.error("--planilla no admite --plan, --padron ni --novedades")
    elif args.plan is None or args.padron is None:
        parser.error("sin --planilla se exigen --plan y --padron")

    try:
        if args.planilla:
            fuente = GoogleSheetsFuentePagos.desde_entorno(
                token_provider=TokenEntornoProvider(),
                transport=transport,
            )
            plan = fuente.cargar_plan()
            padron = fuente.cargar_padron(actividad_id=plan.actividad_id)
            novedades = fuente.cargar_novedades()
        else:
            plan = cargar_plan_pagos_csv(args.plan)
            padron = cargar_padron_csv(
                args.padron, actividad_id=plan.actividad_id
            )
            novedades = (
                cargar_novedades_csv(args.novedades)
                if args.novedades is not None
                else []
            )
        informe = correr_control_pagos(
            plan=plan,
            padron=padron,
            buzon=BuzonPropioEml(args.buzon),
            hoy=args.fecha if args.fecha is not None else fecha_de_corrida(),
            novedades=novedades,
        )
    except (
        ControlPagosError,
        BuzonPropioError,
        ConfiguracionWorkspaceError,
    ) as exc:
        return _invalida(exc.code)
    except OSError:
        return _invalida("entrada_inaccesible")
    print(json.dumps(informe_a_dict(informe), ensure_ascii=False, sort_keys=True))
    return 0


def informe_a_dict(informe: InformeCorridaPagos) -> dict[str, object]:
    """Serializa el informe: el «k de N» por preinscripto con su desglose, la
    marca de bonificación no verificable, las no asociadas, las novedades —
    aplicadas y con error —, el lote planeado de recordatorios y los
    candidatos a confirmación de inscripción con la razón cerrada que los
    habilita. Metadatos solamente: el contenido de cuerpos y adjuntos no
    forma parte del modelo, así que no puede aparecer acá."""

    return {
        "estado": "OK",
        "actividad_id": informe.actividad_id,
        "actividad": informe.actividad,
        "contrato_plan": informe.contract_version,
        "contrato_novedades": informe.novedades_contract_version,
        "hoy": informe.hoy.isoformat(),
        "preinscriptos": [
            {
                "id_inscripcion": situacion.id_inscripcion,
                "nombre_destinatario": situacion.nombre_destinatario,
                "email_destinatario": situacion.email_destinatario,
                "cuotas_cubiertas": (
                    f"{situacion.cuotas_cubiertas} de {len(situacion.cuotas)}"
                ),
                "detalle": _detalle_cobertura(situacion),
                "bonificacion_no_verificable": (
                    situacion.bonificacion_no_verificable
                ),
                "cuotas": [
                    {
                        "nro": cuota.nro_cuota,
                        "estado": cuota.estado,
                        "fecha_referencia": cuota.fecha_referencia.isoformat(),
                        "vencida": cuota.vencida,
                        "comprobante": (
                            _comprobante_a_dict(cuota.comprobante)
                            if cuota.comprobante is not None
                            else None
                        ),
                    }
                    for cuota in situacion.cuotas
                ],
                "comprobantes_sin_cuota": [
                    _comprobante_a_dict(comprobante)
                    for comprobante in situacion.comprobantes_sin_cuota
                ],
            }
            for situacion in informe.situaciones
        ],
        "respuestas_no_asociadas": [
            {
                "message_id": respuesta.message_id,
                "remitente": respuesta.remitente,
                "asunto": respuesta.asunto,
                "fecha": _fecha_a_texto(respuesta.fecha),
                "motivo": respuesta.motivo,
            }
            for respuesta in informe.no_asociadas
        ],
        "novedades_aplicadas": [
            _novedad_a_dict(novedad) for novedad in informe.novedades_aplicadas
        ],
        "novedades_con_error": [
            {
                **_novedad_a_dict(error.novedad),
                "motivo": error.motivo,
            }
            for error in informe.novedades_con_error
        ],
        "recordatorios": _lote_a_dict(informe.recordatorios),
        "candidatos_confirmacion": [
            {
                "id_inscripcion": candidato.id_inscripcion,
                "nombre_destinatario": candidato.nombre_destinatario,
                "email_destinatario": candidato.email_destinatario,
                "razon": candidato.razon,
            }
            for candidato in informe.candidatos_confirmacion
        ],
    }


def _lote_a_dict(lote) -> dict[str, object]:
    """El lote planeado del día: qué ítems se recordarían y su clave de lote.

    Son metadatos de la planificación — quién, qué cuota, con cuánta
    anticipación — sin datos de pago sensibles: los medios de pago y links se
    renderizan en el cuerpo del recordatorio dentro del circuito, no acá.
    """

    return {
        "actividad_id": lote.actividad_id,
        "hoy": lote.hoy.isoformat(),
        "clave_lote": lote.clave_lote,
        "items": [
            {
                "id_inscripcion": item.id_inscripcion,
                "nombre_destinatario": item.nombre_destinatario,
                "email_destinatario": item.email_destinatario,
                "nro_cuota": item.nro_cuota,
                "anticipacion_d": item.anticipacion_d,
                "fecha_referencia": item.fecha_referencia.isoformat(),
                "monto": item.monto,
                "bonificacion_no_verificable": item.bonificacion_no_verificable,
                "idempotency_key": item.idempotency_key,
            }
            for item in lote.items
        ],
    }


def _invalida(code: str) -> int:
    print(
        json.dumps(
            {"estado": "INVALIDA", "error": code},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 2


_ROTULOS_ESTADO = {
    ESTADO_BONIFICADA: "bonificada",
    ESTADO_PAGO_CONFIRMADO: "confirmada por la Fundación",
    ESTADO_COMPROBANTE_PRESENTADO: "con comprobante presentado",
}


def _detalle_cobertura(situacion) -> str:
    """El desglose del «k» en prosa, como pide §3.2 del diseño («1 confirmada
    por la Fundación, 1 con comprobante presentado»). Las pendientes no se
    detallan: ya quedan en N."""
    partes = []
    for estado, rotulo in _ROTULOS_ESTADO.items():
        cantidad = sum(1 for c in situacion.cuotas if c.estado == estado)
        if not cantidad:
            continue
        forma = rotulo if cantidad == 1 else _plural_rotulo(rotulo)
        partes.append(f"{cantidad} {forma}")
    return ", ".join(partes)


def _plural_rotulo(rotulo: str) -> str:
    plurales = {
        "bonificada": "bonificadas",
        "confirmada por la Fundación": "confirmadas por la Fundación",
        "con comprobante presentado": "con comprobante presentado",
    }
    return plurales[rotulo]


def _comprobante_a_dict(comprobante: Comprobante) -> dict[str, object]:
    return {
        "sha256": comprobante.sha256,
        "tipo": comprobante.tipo,
        "nombre": comprobante.nombre,
        "fecha": _fecha_a_texto(comprobante.fecha),
        "message_id": comprobante.message_id,
    }


def _novedad_a_dict(novedad: NovedadPago) -> dict[str, object]:
    """La novedad con su trazabilidad: fila de origen, fecha y responsable."""
    return {
        "fila": novedad.fila,
        "id_inscripcion": novedad.id_inscripcion,
        "tipo": novedad.tipo,
        "valor": novedad.valor,
        "fecha": novedad.fecha,
        "responsable": novedad.responsable,
    }


def _fecha_a_texto(fecha: datetime | None) -> str | None:
    return fecha.isoformat() if fecha is not None else None


def _fecha_arg(valor: str) -> date:
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "la fecha debe tener formato AAAA-MM-DD"
        ) from None
