"""Builders de HU-012 para las dos piezas del corte 4 del diseño (D8/D9).

Este módulo no agrega circuito: arma las `SolicitudConfirmacion` que el
circuito por envío de `confirmaciones.py` ya sabe tramitar — borrador,
doble aprobación por pieza, entrega al destino habilitado — a partir de
las estructuras de dominio de `pagos.py`:

- `solicitud_instrucciones_pago`: el correo de preinscripción con las
  instrucciones de pago que hoy la SEU redacta a mano (D8). Tipo
  `instrucciones_pago` del catálogo v2; su `datos_pago` copia del plan las
  cuotas, los medios y las bonificaciones, y el `asunto_preinscripcion`
  del que sale el asunto del borrador — la llave con la que la corrida
  asocia después la respuesta con el comprobante (§4.2).
- `solicitud_confirmacion_inscripcion`: la confirmación de inscripción que
  la corrida habilita cuando la cuota 1 quedó `PAGO_CONFIRMADO` o
  `BONIFICADA` (D9). No es un tipo nuevo: es el tipo `inscripcion` de
  siempre, construido desde el `CandidatoConfirmacion` que planifica la
  corrida, así que un comprobante meramente presentado nunca llega a
  producir este borrador.

`organiza` y `contacto` llegan por parámetro porque son datos
institucionales del emisor, no del plan de pago — el módulo no inventa
datos de la SEU. `lugar` queda vacío y el render lo reemplaza por la
frase explícita «A confirmar por la Secretaría de Extensión»: ni el plan
ni el candidato lo informan, y un renglón inventado sería peor.
"""

from __future__ import annotations

from .confirmaciones import (
    TIPO_INSTRUCCIONES_PAGO,
    CuotaInstrucciones,
    DatosInstruccionesPago,
    SolicitudConfirmacion,
)
from .pagos import CandidatoConfirmacion, PlanPago, Preinscripto


def solicitud_instrucciones_pago(
    *,
    plan: PlanPago,
    preinscripto: Preinscripto,
    contacto: str,
) -> SolicitudConfirmacion:
    """La solicitud del correo de preinscripción con instrucciones (D8).

    Copia del plan los datos que el borrador lista — cuotas con montos y
    vencimientos, medios de pago, categorías bonificadas, fechas de inicio
    y límite — hacia `datos_pago`, la forma serializable que la solicitud
    porta y que la clave de idempotencia cubre entera. `asunto` no se pasa
    aparte: el render toma `asunto_preinscripcion` del plan, exacto.
    """

    return SolicitudConfirmacion(
        id_inscripcion=preinscripto.id_inscripcion,
        nombre_destinatario=preinscripto.nombre_destinatario,
        email_destinatario=preinscripto.email_destinatario,
        actividad=plan.actividad,
        # `fecha`, `lugar` y `organiza` no son campos que el catálogo exija
        # a este tipo ni el render consuma: quedan declarados vacíos.
        fecha="",
        lugar="",
        organiza="",
        contacto=contacto,
        tipo_notificacion=TIPO_INSTRUCCIONES_PAGO,
        datos_pago=DatosInstruccionesPago(
            asunto_preinscripcion=plan.asunto_preinscripcion,
            cuotas=tuple(
                CuotaInstrucciones(
                    nro=cuota.nro,
                    monto=cuota.monto,
                    vencimiento=(
                        cuota.vencimiento.isoformat()
                        if cuota.vencimiento is not None
                        else None
                    ),
                )
                for cuota in plan.cuotas
            ),
            medios_pago=tuple(plan.medios_pago),
            bonificaciones=tuple(plan.categorias_bonificadas),
            fecha_inicio=plan.fecha_inicio.isoformat(),
            fecha_limite_inscripcion=(
                plan.fecha_limite_inscripcion.isoformat()
                if plan.fecha_limite_inscripcion is not None
                else None
            ),
        ),
    )


def solicitud_confirmacion_inscripcion(
    *,
    plan: PlanPago,
    candidato: CandidatoConfirmacion,
    contacto: str,
    organiza: str,
) -> SolicitudConfirmacion:
    """La solicitud de confirmación de inscripción desde un candidato (D9).

    El candidato llega de `InformeCorridaPagos.candidatos_confirmacion`,
    así que la cuota 1 ya quedó habilitada por la Fundación o por la
    bonificación — este builder no vuelve a evaluar el pago, sólo traduce
    la planificación a la pieza del circuito. El tipo es `inscripcion`: la
    confirmación de inscripción de HU-012, ahora gatillada por el estado
    derivado del pago en lugar de un alta del SIU que todavía no existe.
    `fecha` es el inicio del plan y `lugar` queda para la frase explícita
    del render: ninguna de las dos fuentes lo informa.
    """

    return SolicitudConfirmacion(
        id_inscripcion=candidato.id_inscripcion,
        nombre_destinatario=candidato.nombre_destinatario,
        email_destinatario=candidato.email_destinatario,
        actividad=plan.actividad,
        fecha=plan.fecha_inicio.isoformat(),
        lugar="",
        organiza=organiza,
        contacto=contacto,
    )
