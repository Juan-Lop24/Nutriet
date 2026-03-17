"""
📍 distribucion/ — Reparto por comidas

Traduce macros diarios → comidas reales.

Distribuye de forma proporcional:
- Si no se selecciona una comida, sus calorías se redistribuyen
- Mantiene proporciones de macros en cada comida
"""

from .comidas import (
    DistribuidorComidas,
    distribuir_dieta_por_comidas,
    obtener_comidas_del_formulario
)

__all__ = [
    "DistribuidorComidas",
    "distribuir_dieta_por_comidas",
    "obtener_comidas_del_formulario",
]
