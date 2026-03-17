"""
Calculador de Tasa de Gasto Energético Diario (TDEE)

TDEE = TMB × Factor de Actividad
"""


def calcular_tdee(tmb: float, nivel_actividad: str) -> float:
    """
    Calcula el Gasto Energético Diario Total (TDEE).
    
    Fórmula: TDEE = TMB × Factor de Actividad
    
    Factores de actividad:
    - sedentario: 1.2 (poco o nada de ejercicio)
    - ligero: 1.375 (ejercicio 1-3 días/semana)
    - moderado: 1.55 (ejercicio 3-5 días/semana)
    - intenso: 1.725 (ejercicio 6-7 días/semana)
    - muy_intenso: 1.9 (entrenamiento diario intenso)
    
    Args:
        tmb: Tasa Metabólica Basal en kcal/día
        nivel_actividad: Nivel de actividad física
        
    Returns:
        TDEE en kcal/día, redondeado a 2 decimales
    """
    if tmb <= 0:
        raise ValueError("TMB debe ser mayor a 0")
    
    factores_actividad = {
        "sedentario": 1.2,
        "ligero": 1.375,
        "moderado": 1.55,
        "intenso": 1.725,
        "muy_intenso": 1.9,
    }
    
    nivel_normalizado = nivel_actividad.lower().strip()
    factor = factores_actividad.get(nivel_normalizado, 1.55)
    
    tdee = tmb * factor
    return round(tdee, 2)
    