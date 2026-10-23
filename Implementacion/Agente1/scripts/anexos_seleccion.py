"""Qué se declara en los anexos del laboratorio, y por qué.

El perfil completo vive en ``Documentos/Laboratorio/Perfil-Calidad-…md`` y
``Perfil-Seguridad-…md``: es el **registro interno** y no se recorta. Lo que se
recorta es lo que **se declara** al laboratorio, porque cada ítem declarado es
un ítem que el laboratorio puede pedir ver funcionando en la reunión.

La vara la dio el ejemplo aprobado de 2025 (``Revision-Laboratorio-2025/
Ejemplo-Aprobado-2025/``): siete ítems de seguridad, dos páginas de presentación.
Este módulo declara **hasta tres por componente**, elegidos por este orden:

1. **Lo que el laboratorio siembra como ejemplo** en su propia plantilla:
   almacenamiento de contraseñas, cifrado en tránsito, identidad y roles,
   validación de entradas.
2. **Los controles que muestran el diseño del proyecto**: gate de salida
   fail-closed, doble aprobación, idempotencia durable, auditoría sólo-hashes.
3. **Lo demostrable en menos de dos minutos**, que es el paso en vivo del perfil.

Queda afuera, y se declara en la reunión si el laboratorio pregunta: lo previsto
y no implementado, lo no aplicable y las ausencias explícitas («sin límite de
tasa», «sin auditoría de dependencias»). Siguen en el perfil; dejan de ocupar una
fila en la lista de control.
"""

from __future__ import annotations

from typing import Any

# Tope de filas declaradas por componente. El ejemplo aprobado usó menos.
TOPE_POR_COMPONENTE = 3

# Atributos de calidad que se declaran, por estrato. El orden dentro de cada
# componente lo fija el perfil (el del estándar), no esta lista.
SELECCION_CALIDAD: dict[str, tuple[str, ...]] = {
    "Canal": (
        "Protección contra errores del usuario",
        "Robustez (25059)",
        "Transparencia (25059)",
    ),
    "Interpretación": (
        "Pertinencia funcional",
        "Robustez (25059)",
        "Transparencia (25059)",
    ),
    "Generación": (
        "Completitud funcional",
        "Corrección del contenido generado (25059)",
        "Robustez (25059)",
    ),
    "Gates": (
        "Corrección del sistema",
        "Controlabilidad (25059)",
        "Robustez (25059)",
    ),
    "Control de pagos": (
        "Corrección del sistema",
        "Tolerancia a fallos",
        "Exactitud sintáctica",
    ),
    "Aprobación": (
        "Controlabilidad (25059)",
        "Intervenibilidad (25059)",
        "Transparencia (25059)",
    ),
    "Cola y envío": (
        "Corrección del sistema",
        "Tolerancia a fallos",
        "Recuperabilidad",
    ),
    "Persistencia y auditoría": (
        "Transparencia (25059)",
        "Trazabilidad",
        "Tolerancia a fallos",
    ),
    "Integraciones": (
        "Interoperabilidad",
        "Robustez (25059)",
        "Consistencia",
    ),
    "Sistema": (
        "Modularidad",
        "Analizabilidad",
        "Instalabilidad",
    ),
}

# Ítems de seguridad que se declaran, por componente. El orden lo fijan el
# componente y el factor, como en el perfil.
SELECCION_SEGURIDAD: dict[str, tuple[str, ...]] = {
    "Canal": (
        "Identidad y rol del pedido",
        "La prosa del pedido es dato, nunca instrucción",
        "No persistencia de la prosa del pedido",
    ),
    "Interpretación": (
        "Catálogo cerrado de intenciones",
        "Fallback del intérprete validado contra contrato acotado",
        "Registro sin prosa ni identidad en claro",
    ),
    "Generación": (
        "Gate de salida fail-closed",
        "Marca de borrador revalidada en el destino",
        "Modelo local sin salida a internet",
    ),
    "Gates": (
        "Integridad del gate (SLO del 100 %)",
        "Fail-closed por tipo y origen",
    ),
    "Control de pagos": (
        "Situación de pago derivada, sin estado propio",
        "Buzón propio de sólo lectura",
        "Nada se persiste; adjuntos hasheados en memoria",
    ),
    "Aprobación": (
        "Identidad verificada por Google en el Form de decisiones",
        "Links alterados y objetos inexistentes se rechazan",
        "La aprobación ata el objeto por sha256",
    ),
    "Cola y envío": (
        "Doble aprobación obligatoria por máquina de estados",
        "Idempotencia durable y reconciliación",
        "Lista de prueba del envío",
    ),
    "Persistencia y auditoría": (
        "Almacenamiento de credenciales y contraseñas",
        "Auditoría y reportes sólo de códigos, conteos y hashes",
        "Registros durables fail-closed",
    ),
    "Integraciones": (
        "Cifrado en tránsito de las llamadas a Workspace (TLS)",
        "El token nunca se guarda ni se registra",
        "Allowlist de hosts del plano de datos",
    ),
    "Google Workspace": (
        "Mecanismo de identidad (eje 1, I)",
        "Custodia y transporte del secreto (eje 4, I + RA)",
        "Riesgo aceptado de la delegación sobre el dominio",
    ),
    "Sistema": (
        "Manifest de versión y arranque fail-closed",
        "Ejecución en contenedores endurecidos",
        "Secretos fuera del repo y del log",
    ),
}


def _verificar_tope(nombre: str, seleccion: dict[str, tuple[str, ...]]) -> None:
    for componente, declarados in seleccion.items():
        if len(declarados) > TOPE_POR_COMPONENTE:
            raise ValueError(
                f"{nombre}: {componente} declara {len(declarados)} filas, "
                f"el tope es {TOPE_POR_COMPONENTE}"
            )


_verificar_tope("calidad", SELECCION_CALIDAD)
_verificar_tope("seguridad", SELECCION_SEGURIDAD)


def _filtrar(
    filas: list[Any],
    seleccion: dict[str, tuple[str, ...]],
    atributo_de: Any,
) -> list[Any]:
    """Deja sólo las filas declaradas y falla si alguna no está en la fuente."""

    por_componente: dict[str, set[str]] = {}
    for fila in filas:
        por_componente.setdefault(fila.estrato, set()).add(atributo_de(fila))

    faltantes = [
        f"{componente} › {atributo}"
        for componente, declarados in seleccion.items()
        for atributo in declarados
        if atributo not in por_componente.get(componente, set())
    ]
    if faltantes:
        raise ValueError(
            "la selección nombra filas que la fuente no tiene: " + ", ".join(faltantes)
        )

    return [
        fila
        for fila in filas
        if atributo_de(fila) in seleccion.get(fila.estrato, ())
    ]


def seleccionar_calidad(filas: list[Any]) -> list[Any]:
    """Devuelve las filas del perfil de calidad que se declaran en los anexos."""

    return _filtrar(filas, SELECCION_CALIDAD, lambda fila: fila.atributo)


def seleccionar_seguridad(filas: list[Any]) -> list[Any]:
    """Devuelve las filas del perfil de seguridad que se declaran en los anexos."""

    return _filtrar(filas, SELECCION_SEGURIDAD, lambda fila: fila.item)
