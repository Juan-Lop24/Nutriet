"""
🔍 riesgo/ — Evaluación nutricional

Interpreta resultados y clasifica riesgos.
"""

from .evaluacion import (
    clasificar_imc,
    evaluar_riesgo,
    get_recomendacion
)

__all__ = [
    'clasificar_imc',
    'evaluar_riesgo',
    'get_recomendacion',
]
