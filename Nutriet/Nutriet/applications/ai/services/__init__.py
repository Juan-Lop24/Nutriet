"""
🔌 services/ — Puentes con otras apps

Adaptadores, no lógica.
"""

from .adaptadores import (
    AdaptadorVistas,
    AdaptadorRecetas,
    AdaptadorJSON,
    AdaptadorDieta,
    CanalResultado,
)

__all__ = [
    "AdaptadorVistas",
    "AdaptadorRecetas",
    "AdaptadorJSON",
    "AdaptadorDieta",
    "CanalResultado",
]
