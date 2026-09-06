"""Permite `python -m agente1`. La lógica vive en `cli.main`.

El código de salida se propaga tal cual: `0` sólo si quedó un borrador
pendiente de validación, `2` en cualquier otro desenlace.
"""

from .cli import main

raise SystemExit(main())
