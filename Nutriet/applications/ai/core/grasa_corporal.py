"""
Calculador del Porcentaje de Grasa Corporal

Fórmula de Deurenberg
"""


def calcular_pgc(imc: float, edad_anos: int, sexo: str) -> float:
    """
    Calcula el porcentaje de grasa corporal usando fórmula de Deurenberg.
    
    Fórmula:
    - Hombre: %GC = (1.20 × IMC) + (0.23 × edad) - 16.2
    - Mujer:  %GC = (1.20 × IMC) + (0.23 × edad) - 5.4
    
    Args:
        imc: Índice de Masa Corporal
        edad_anos: Edad en años
        sexo: "M" (masculino) o "F" (femenino)
        
    Returns:
        Porcentaje de grasa corporal redondeado a 2 decimales
    """
    if imc <= 0 or edad_anos <= 0:
        raise ValueError("IMC y edad deben ser mayores a 0")
    
    if sexo.upper() == "M":
        pgc = (1.20 * imc) + (0.23 * edad_anos) - 16.2
    elif sexo.upper() == "F":
        pgc = (1.20 * imc) + (0.23 * edad_anos) - 5.4
    else:
        raise ValueError("Sexo debe ser 'M' o 'F'")
    
    return round(pgc, 2)


def calcular_grasa_corporal_deurenberg(imc: float, edad_anos: int, sexo: str) -> float:
    """Alias para compatibilidad con el código existente."""
    return calcular_pgc(imc, edad_anos, sexo)