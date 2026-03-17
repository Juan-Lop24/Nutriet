"""
📝 dtos/ — Contratos de datos

Define qué entra y qué sale de la IA.
"""

from .entrada import DatosEntrada
from .resultado import ResultadoIA

__all__ = [
    'DatosEntrada',
    'ResultadoIA',
]