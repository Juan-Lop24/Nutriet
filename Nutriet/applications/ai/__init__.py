"""
🧠 Módulo IA - Arquitectura Limpia de Nutrición

Sistema profesional de cálculos nutricionales con separación de concerns.
Sigue estándares nivel 1 con fórmulas estándar de nutrición.

ESTRUCTURA:
  • core/        - Fórmulas matemáticas puras
  • macros/      - Reglas nutricionales
  • distribucion/- Reparto por comidas
  • riesgo/      - Evaluación de salud
  • engine/      - Orquestador principal
  • dtos/        - Contratos de datos
  • services/    - Adaptadores

FLUJO PRINCIPAL:
  DatosEntrada → ProcesadorNutricion → ResultadoIA → CanalResultado

USO:
  from applications.ai import ProcesadorNutricion, DatosEntrada
  
  datos = DatosEntrada(peso_kg=75, altura_cm=180, edad_anos=30, ...)
  procesador = ProcesadorNutricion()
  resultado = procesador.procesar(datos)
  
  print(resultado.a_json())
"""

# Importar lo más importante para uso fácil
from .core import (
    calcular_imc,
    calcular_grasa_corporal_deurenberg,
    calcular_tmb,
    calcular_tdee,
)
from .macros import AjustadorDieta, calcular_macros
from .engine import ProcesadorNutricion
from .distribucion import DistribuidorComidas, distribuir_dieta_por_comidas
from .dtos import DatosEntrada, ResultadoIA
from .services import (
    AdaptadorVistas,
    AdaptadorRecetas,
    AdaptadorJSON,
    AdaptadorDieta,
    CanalResultado,
)

__all__ = [
    # Core
    "calcular_imc",
    "calcular_grasa_corporal_deurenberg",
    "calcular_tmb",
    "calcular_tdee",
    
    # Macros
    "AjustadorDieta",
    "calcular_macros",
    
    # Engine
    "ProcesadorNutricion",
    
    # Distribucion
    "DistribuidorComidas",
    "distribuir_dieta_por_comidas",
    
    # DTOs
    "DatosEntrada",
    "ResultadoIA",
    
    # Services
    "AdaptadorVistas",
    "AdaptadorRecetas",
    "AdaptadorJSON",
    "AdaptadorDieta",
    "CanalResultado",
]
