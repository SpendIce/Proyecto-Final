"""HU-013 (#24): adapter de planilla offline del puerto `CanalInteraccion`.

Es la implementación que permite hacer una prueba guiada real con una persona
de la SEU sin identidad institucional ni OAuth: la persona escribe su pedido
en una fila de `pedidos.csv` y encuentra la respuesta en `respuestas.csv`,
ambos dentro de un mismo directorio. El recorrido paso a paso para esa prueba
guiada está en
`evidencias/recorrido-prueba-guiada-canal-planilla.md`.

Es, a propósito, un seam delgado y pobre en lógica (ver "Testing Decisions"
de #18): lee, arma un `PedidoCanal` y escribe una fila. No clasifica nada del
texto del pedido — eso es trabajo del núcleo (`interpretacion.py`), al que
este adapter nunca mira.

Decisiones que no se ven en el código:

- **La identidad afirmada llega tal cual, desde la planilla misma.** Las
  columnas `identificador` y `rol` de `pedidos.csv` son la única fuente de la
  `IdentidadSolicitante` que se transporta al núcleo. Nada en este adapter
  verifica que quien escribió esa fila sea quien dice ser: sigue siendo el
  canal quien la afirma, y sigue sin acreditar control de acceso (ADR 0002).
  En una planilla real, cualquiera con acceso de escritura al archivo puede
  poner el identificador y el rol que quiera en su propia fila; eso es
  exactamente la misma propiedad que ya tiene un correo o un mensaje de chat
  con remitente falseable, no un defecto nuevo de este adapter.
- **Una fila con identidad incompleta se omite, no se rechaza.** No hay
  manera de devolverle un error a alguien que todavía no mandó nada
  reconocible como pedido; se seguirá viendo como no leída hasta que la fila
  se complete. El rechazo por rol no habilitado sigue existiendo, pero lo
  decide el núcleo sobre una identidad bien formada, no este adapter sobre
  una fila vacía.
- **"Pendiente" se calcula comparando dos archivos, no editando el primero.**
  `pedidos.csv` nunca se reescribe: un pedido queda pendiente hasta que su
  `id_pedido` aparece en `respuestas.csv`. Esto evita que el adapter necesite
  bloqueos de escritura sobre el archivo que la persona de la SEU podría estar
  editando a mano en simultáneo.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .canal import PedidoCanal
from .interpretacion import IdentidadSolicitante, ResultadoInterpretacion


NOMBRE_PEDIDOS = "pedidos.csv"
NOMBRE_RESPUESTAS = "respuestas.csv"
COLUMNAS_PEDIDO = ("id_pedido", "identificador", "rol", "texto")
COLUMNAS_RESPUESTA = (
    "id_pedido",
    "estado",
    "referencia_borrador",
    "resumen",
    "error",
)


class CanalPlanillaOffline:
    """Adapter offline: lee `pedidos.csv`, escribe `respuestas.csv`.

    Ambos archivos viven en el mismo `directorio`, que en la prueba guiada es
    una carpeta compartida (por ejemplo, sincronizada) y en las pruebas
    automáticas es un directorio temporal.
    """

    def __init__(self, directorio: Path) -> None:
        self._directorio = directorio
        self._pedidos_path = directorio / NOMBRE_PEDIDOS
        self._respuestas_path = directorio / NOMBRE_RESPUESTAS

    def leer_pendientes(self) -> tuple[PedidoCanal, ...]:
        if not self._pedidos_path.exists():
            return ()
        ya_respondidos = self._ids_respondidos()
        pendientes: list[PedidoCanal] = []
        with self._pedidos_path.open(encoding="utf-8", newline="") as archivo:
            for fila in csv.DictReader(archivo):
                pedido = self._pedido_desde_fila(fila)
                if pedido is None or pedido.id_pedido in ya_respondidos:
                    continue
                pendientes.append(pedido)
        return tuple(pendientes)

    def responder(self, pedido: PedidoCanal, resultado: ResultadoInterpretacion) -> None:
        self._directorio.mkdir(parents=True, exist_ok=True)
        es_archivo_nuevo = not self._respuestas_path.exists()
        with self._respuestas_path.open("a", encoding="utf-8", newline="") as archivo:
            writer = csv.DictWriter(archivo, fieldnames=COLUMNAS_RESPUESTA)
            if es_archivo_nuevo:
                writer.writeheader()
            writer.writerow(
                {
                    "id_pedido": pedido.id_pedido,
                    "estado": resultado.estado,
                    "referencia_borrador": (
                        resultado.referencia_borrador.referencia
                        if resultado.referencia_borrador is not None
                        else ""
                    ),
                    "resumen": resultado.resumen or "",
                    "error": resultado.error or "",
                }
            )

    def _ids_respondidos(self) -> set[str]:
        if not self._respuestas_path.exists():
            return set()
        with self._respuestas_path.open(encoding="utf-8", newline="") as archivo:
            return {
                (fila.get("id_pedido") or "").strip()
                for fila in csv.DictReader(archivo)
            }

    def _pedido_desde_fila(self, fila: dict[str, str | None]) -> PedidoCanal | None:
        # Se lee por nombre de columna (`COLUMNAS_PEDIDO`), no por posición: una
        # planilla con columnas de más no rompe la lectura, y una fila sin
        # alguna de estas columnas cae al default vacío en lugar de levantar.
        valores = {columna: (fila.get(columna) or "").strip() for columna in COLUMNAS_PEDIDO}
        if not valores["id_pedido"]:
            return None
        try:
            solicitante = IdentidadSolicitante(
                identificador=valores["identificador"], rol=valores["rol"]
            )
            return PedidoCanal(
                id_pedido=valores["id_pedido"], solicitante=solicitante, texto=valores["texto"]
            )
        except ValueError:
            # Fila incompleta (identidad vacía, texto no legible, etc.): se
            # omite en lugar de romper la lectura del resto de la planilla.
            # No es un rechazo del núcleo, es un pedido que todavía no está
            # en condiciones de convertirse en uno.
            return None
