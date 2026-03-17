"""
Calculador de Tasa Metabólica Basal (TMB)

Fórmula de Harris-Benedict (1919)
"""


def calcular_tmb(peso_kg: float, altura_cm: float, edad_anos: int, sexo: str) -> float:
    """
    Calcula la Tasa Metabólica Basal (TMB).
    
    Usa fórmula de Harris-Benedict (1919).
    
    Fórmulas:
    - Hombre: TMB = 88.362 + (13.397 × peso) + (4.799 × altura) - (5.677 × edad)
    - Mujer:  TMB = 447.593 + (9.247 × peso) + (3.098 × altura) - (4.330 × edad)
    
    Args:
        peso_kg: Peso en kilogramos
        altura_cm: Altura en centímetros
        edad_anos: Edad en años
        sexo: "M" (masculino) o "F" (femenino)
        
    Returns:
        TMB en kcal/día, redondeado a 2 decimales
    """
    if peso_kg <= 0 or altura_cm <= 0 or edad_anos <= 0:
        raise ValueError("Peso, altura y edad deben ser mayores a 0")
    
    if sexo.upper() == "M":
        tmb = 88.362 + (13.397 * peso_kg) + (4.799 * altura_cm) - (5.677 * edad_anos)
    elif sexo.upper() == "F":
        tmb = 447.593 + (9.247 * peso_kg) + (3.098 * altura_cm) - (4.330 * edad_anos)
    else:
        raise ValueError("Sexo debe ser 'M' o 'F'")
    
    return round(tmb, 2)
