"""
Calculador del Índice de Masa Corporal (IMC)

Fórmula: IMC = peso_kg / (altura_m ^ 2)
"""


def calcular_imc(peso_kg: float, altura_cm: float) -> float:
    """
    Calcula el Índice de Masa Corporal.
    
    Args:
        peso_kg: Peso en kilogramos
        altura_cm: Altura en centímetros
        
    Returns:
        IMC redondeado a 2 decimales
    """
    if peso_kg <= 0 or altura_cm <= 0:
        raise ValueError("Peso y altura deben ser mayores a 0")
    
    altura_m = altura_cm / 100
    imc = peso_kg / (altura_m ** 2)
    return round(imc, 2)