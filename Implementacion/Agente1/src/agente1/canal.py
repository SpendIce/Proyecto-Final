"""HU-013 (#24): el canal de interacción, por encima del seam de interpretación.

`interpretacion.py` (#20) es el núcleo: entra un mensaje, sale un
`ResultadoInterpretacion`, sin saber nada de dónde vino el pedido ni adónde va
la respuesta. Este módulo agrega esa parte de afuera: un **puerto de canal**
(`CanalInteraccion`) y un **bucle delgado** (`atender_canal`) que lee un
pedido pendiente, se lo pasa al núcleo y escribe la respuesta.

El bucle deliberadamente no clasifica, no resuelve actividades ni arma
prompts: toda esa lógica ya vive en `interpretacion.interpretar_solicitud`, y
repetirla acá — aunque sea parcialmente — sería duplicar el único lugar donde
la spec (#18, ADR 0001) exige que la entrada no confiable se interprete. Si
alguna vez este módulo necesita mirar el contenido del texto del pedido para
decidir algo, esa lógica se fue del diseño acordado y pertenece al núcleo.

Se entregan dos implementaciones del puerto:

- `CanalInteraccionFake`, en memoria, para ejercitar el bucle en pruebas sin
  disco ni transporte (mismo patrón que `HistoriaVivaFake` en
  `historia_viva.py`).
- `CanalPlanillaOffline` (`canal_planilla.py`), un adapter offline contra un
  directorio temporal: lee pedidos de un CSV y escribe respuestas en otro. Es
  la única evidencia disponible hoy sobre el criterio de interfaz usable por
  personal no técnico, porque permite una prueba guiada con una persona de la
  SEU sin OAuth ni credenciales (ver
  `evidencias/recorrido-prueba-guiada-canal-planilla.md`).

El adapter institucional (Google Chat, correo, interfaz web) queda pendiente
de su bloqueante externo de identidad y no se implementa acá.

Decisiones que no se ven en el código:

- **La identidad se transporta, nunca se verifica acá tampoco.** `PedidoCanal`
  lleva una `IdentidadSolicitante` ya construida — la misma que exige el
  núcleo — porque es el canal quien la afirma. Ni este módulo ni el núcleo
  tienen forma de comprobar que sea cierta. Ver ADR 0002
  (`docs/adr/0002-identidad-afirmada-por-el-canal-no-verificada.md`): recibir
  un pedido por un buzón no otorga los permisos de ese buzón, y ninguna
  evidencia producida por este canal acredita control de acceso.
- **Un pedido respondido no se re-despacha.** El bucle confía en que
  `CanalInteraccion.responder` deja al puerto en un estado donde ese mismo
  pedido no vuelve a aparecer en una lectura futura de `leer_pendientes`; cada
  adapter decide cómo (en memoria, marcando una fila). El bucle no lleva su
  propio registro de qué ya atendió.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .destinos import DestinoBorradores
from .fuentes import FuenteSolicitudes
from .interpretacion import (
    IdentidadSolicitante,
    ResultadoInterpretacion,
    interpretar_solicitud,
)
from .procesamiento import Generator


@dataclass(frozen=True)
class PedidoCanal:
    """Un pedido pendiente tal como lo entrega el canal, listo para el núcleo.

    `id_pedido` es propio del canal (una fila, un mensaje): el núcleo no lo ve
    ni lo necesita, es lo que permite al adapter saber qué respuesta
    corresponde a qué pedido. Sin saltos de línea, por la misma razón que el
    resto de los identificadores del proyecto: termina en logs y en archivos
    de respuesta, y un salto permitiría inyectar una fila falsa.
    """

    id_pedido: str
    solicitante: IdentidadSolicitante
    texto: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.id_pedido, str)
            or not self.id_pedido.strip()
            or "\r" in self.id_pedido
            or "\n" in self.id_pedido
        ):
            raise ValueError("id de pedido de canal inválido")
        if not isinstance(self.solicitante, IdentidadSolicitante):
            raise ValueError("pedido de canal sin identidad de solicitante válida")
        if not isinstance(self.texto, str):
            raise ValueError("pedido de canal sin texto")


class CanalInteraccion(Protocol):
    """Puerto de canal: leer pedidos pendientes, escribir su respuesta.

    Dos operaciones y ninguna más — en particular no hay forma de que el
    canal empuje un pedido hacia el núcleo: siempre es `atender_canal` quien
    inicia la lectura. `responder` recibe el `ResultadoInterpretacion`
    completo porque es la única fuente de lo que hay que comunicar: el bucle
    no decide qué mostrar, sólo lo transporta.
    """

    def leer_pendientes(self) -> tuple[PedidoCanal, ...]: ...

    def responder(self, pedido: PedidoCanal, resultado: ResultadoInterpretacion) -> None: ...


class CanalInteraccionFake:
    """Implementación en memoria del puerto, sin disco ni transporte.

    Sirve para ejercitar `atender_canal` en pruebas contra el núcleo real, sin
    pasar por un archivo. `respuestas` queda como bitácora ordenada de qué se
    respondió a qué pedido, para que la prueba pueda afirmar sobre ambos lados
    a la vez.
    """

    def __init__(self, *, pedidos: tuple[PedidoCanal, ...] = ()) -> None:
        self._pendientes: list[PedidoCanal] = list(pedidos)
        self.respuestas: list[tuple[PedidoCanal, ResultadoInterpretacion]] = []

    def leer_pendientes(self) -> tuple[PedidoCanal, ...]:
        return tuple(self._pendientes)

    def responder(self, pedido: PedidoCanal, resultado: ResultadoInterpretacion) -> None:
        self.respuestas.append((pedido, resultado))
        self._pendientes = [
            pendiente for pendiente in self._pendientes if pendiente.id_pedido != pedido.id_pedido
        ]


def atender_canal(
    canal: CanalInteraccion,
    *,
    fuente: FuenteSolicitudes,
    directorio_salida: Path,
    generator: Generator,
    destino: DestinoBorradores | None = None,
) -> tuple[ResultadoInterpretacion, ...]:
    """Bucle delgado de lectura y respuesta. Sin lógica de interpretación.

    Por cada pedido pendiente: lo pasa tal cual a `interpretar_solicitud` (el
    núcleo) y escribe la respuesta a través del mismo puerto. No clasifica
    intenciones, no resuelve actividades, no construye prompts — eso vive
    enteramente en `interpretacion.py`. Devuelve los resultados en el mismo
    orden en que se leyeron los pedidos, para que quien invoque el bucle
    pueda auditar la corrida sin volver a leer el canal.
    """

    resultados: list[ResultadoInterpretacion] = []
    for pedido in canal.leer_pendientes():
        resultado = interpretar_solicitud(
            texto=pedido.texto,
            solicitante=pedido.solicitante,
            fuente=fuente,
            directorio_salida=directorio_salida,
            generator=generator,
            destino=destino,
        )
        canal.responder(pedido, resultado)
        resultados.append(resultado)
    return tuple(resultados)
