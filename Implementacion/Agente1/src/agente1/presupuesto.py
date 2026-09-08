"""Dimensiona el presupuesto de decodificación contra el contrato vigente.

El defecto `DEF-A1-013` no fue un problema de calidad del modelo sino de
medición: con `num_predict=112` la salida del contrato v3 se cortaba antes de
cerrar el objeto JSON, el parser la rechazaba como `json_invalid` y el
benchmark atribuía la falla al modelo. Un presupuesto mal dimensionado no
produce un error visible: produce un diagnóstico equivocado.

Por eso el presupuesto no se elige a ojo. Se deriva del contrato: se construye
el documento JSON más grande que el esquema admite y se lo convierte a tokens
con la relación de caracteres por token menos favorable que se haya medido
sobre el mismo tokenizador.

**Medición del 2026-09-08**, `llama3.2:3b` local, vía `/api/generate` con
`raw: true` y `num_predict: 1`, leyendo `prompt_eval_count` —que tokeniza el
texto enviado sin aplicar plantilla de chat—, sobre el documento máximo del
contrato v3 (924 caracteres):

| Estilo del texto | tokens | caracteres por token |
|---|---|---|
| Prosa institucional | 233 | 3,966 |
| Prosa con acentuación densa | 228 | 4,053 |
| Palabras de una y dos letras | 308 | 3,000 |
| Mayúsculas y signos de puntuación | 482 | 1,917 |

Los mismos números están en `MEDICION_DOCUMENTO_MAXIMO_V3`, para que la
constante se pueda verificar contra la medición y no contra sí misma.

El rango es la razón por la que un presupuesto "que anduvo" no sirve como
justificación: el mismo documento, dentro del mismo contrato, cuesta entre 228
y 482 tokens según cómo esté escrito. `CHARS_POR_TOKEN_MENOS_FAVORABLE` toma el
extremo malo, no el promedio, y lo redondea hacia abajo: 1,917 medido se
versiona como 1,91, para que el presupuesto derivado nunca quede por debajo de
lo que la medición ya observó.

Esto acota, no elimina: ningún presupuesto finito garantiza que toda salida
posible termine. El control complementario está en el adapter, que detecta
`done_reason == "length"` y reporta el agotamiento como tal en lugar de dejar
que aparezca como JSON inválido.
"""

from __future__ import annotations

import json
import math


TOKENIZADOR_MEDIDO = "llama3.2:3b"
FECHA_MEDICION = "2026-09-08"
# La medición queda como dato y no sólo como prosa: así la constante se puede
# verificar contra lo observado en vez de contra sí misma, y
# `scripts/medir_presupuesto_decodificacion.py` puede comparar una corrida
# nueva con este registro. Caracteres y tokens del documento máximo del
# contrato v3, por estilo de redacción.
MEDICION_DOCUMENTO_MAXIMO_V3 = {
    "prosa institucional": (924, 233),
    "prosa con acentuacion densa": (924, 228),
    "palabras de una y dos letras": (924, 308),
    "mayusculas y signos": (924, 482),
}
# Extremo malo de esa medición, redondeado hacia abajo: 924/482 da 1,917 y se
# versiona como 1,91, para que el presupuesto derivado nunca quede por debajo
# de lo que la medición ya observó. Bajarlo sin volver a medir convierte una
# cota en una suposición.
CHARS_POR_TOKEN_MENOS_FAVORABLE = 1.91


# El resultado y el mensaje viven acá, con la excepción, porque los dos
# pipelines los tienen que escribir igual: si HU-010 y HU-011 nombran distinto
# el mismo caso, la evidencia deja de ser comparable entre ellos.
RESULTADO_PRESUPUESTO_AGOTADO = "presupuesto_agotado"
MENSAJE_PRESUPUESTO_AGOTADO = "El presupuesto de decodificación no alcanzó para la salida"


class ContratoNoDimensionable(ValueError):
    """El esquema no acota su salida, así que no se le puede fijar presupuesto."""


class PresupuestoAgotadoError(RuntimeError):
    """El modelo se quedó sin tokens antes de terminar la respuesta.

    Vive acá y no en el adapter porque es parte del contrato del puerto
    `Generator`: cualquier implementación que decodifique con un tope puede
    agotarlo, y el pipeline necesita distinguir ese caso de un fallo de
    transporte. Confundirlos fue lo que produjo `DEF-A1-013`, donde una salida
    truncada llegaba al parser y quedaba registrada como `json_invalid`.

    El mensaje no lleva prompt, contenido ni datos de la actividad.
    """


def documento_maximo(schema: dict[str, object]) -> str:
    """Construye el documento JSON más grande que el esquema admite.

    Sólo entiende la forma que usan los contratos creativos vigentes: campos
    de texto con `maxLength` y arreglos de enum sin repetición. Cualquier otra
    forma es un contrato que todavía no acota su salida, y eso tiene que
    interrumpir el cálculo en vez de devolver un número optimista.
    """

    propiedades = schema["properties"]
    documento: dict[str, object] = {}
    for campo in schema["required"]:
        definicion = propiedades[campo]
        tipo = definicion.get("type")
        if tipo == "string":
            largo = definicion.get("maxLength")
            if not isinstance(largo, int) or largo <= 0:
                raise ContratoNoDimensionable(f"{campo} no declara maxLength")
            # El relleno sólo aporta longitud: el costo en tokens lo aporta
            # después CHARS_POR_TOKEN_MENOS_FAVORABLE, medido sobre texto real.
            documento[campo] = "x" * largo
        elif tipo == "array":
            items = definicion.get("items", {})
            valores = items.get("enum")
            if not valores or not definicion.get("uniqueItems"):
                raise ContratoNoDimensionable(f"{campo} no acota su cantidad de items")
            documento[campo] = list(valores)
        else:
            raise ContratoNoDimensionable(f"{campo} tiene un tipo no dimensionable")
    return json.dumps(documento, ensure_ascii=False, separators=(",", ":"))


def presupuesto_minimo_num_predict(schema: dict[str, object]) -> int:
    """Tokens que hacen falta para que ninguna salida válida quede truncada.

    Es una cota sobre el contrato, no sobre una corrida: si una versión futura
    sube un `maxLength`, este número sube solo y la regresión avisa antes de
    que la baseline acepte un presupuesto que ya no alcanza.
    """

    caracteres = len(documento_maximo(schema))
    return math.ceil(caracteres / CHARS_POR_TOKEN_MENOS_FAVORABLE)
