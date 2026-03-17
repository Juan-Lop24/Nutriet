"""
📊 core/ — Fórmulas puras de cálculo nutricional

Solo matemáticas, sin lógica de negocio.
Sin dependencias de Django ni modelos.

Funciones disponibles:
- calcular_imc: Índice de Masa Corporal
- calcular_grasa_corporal_deurenberg: Porcentaje de grasa corporal (Deurenberg)
- calcular_tmb: Tasa Metabólica Basal (Harris-Benedict)
- calcular_tdee: Tasa de Gasto Energético Diario
"""

from .imc import calcular_imc
from .grasa_corporal import calcular_grasa_corporal_deurenberg, calcular_pgc
from .tmb import calcular_tmb
from .tdee import calcular_tdee

__all__ = [
    'calcular_imc',
    'calcular_grasa_corporal_deurenberg',
    'calcular_pgc',
    'calcular_tmb',
    'calcular_tdee',
]
