"""
Evaluación nutricional e interpretación de riesgos

Clasifica resultados usando reglas claras.
"""


def clasificar_imc(imc: float) -> str:
    """
    Clasifica el IMC en categorías.
    
    Args:
        imc: Índice de Masa Corporal
        
    Returns:
        Clasificación: "bajo_peso", "normal", "sobrepeso", "obesidad"
    """
    if imc < 18.5:
        return "bajo_peso"
    elif imc < 25:
        return "normal"
    elif imc < 30:
        return "sobrepeso"
    else:
        return "obesidad"


def evaluar_riesgo(imc: float, porcentaje_grasa: float, sexo: str) -> str:
    """
    Evalúa el nivel de riesgo nutricional.
    
    Usa combinación de IMC y grasa corporal.
    
    Args:
        imc: Índice de Masa Corporal
        porcentaje_grasa: Porcentaje de grasa corporal
        sexo: "M" o "F"
        
    Returns:
        Nivel de riesgo: "bajo", "moderado", "alto"
    """
    # Umbrales de grasa corporal
    if sexo == "M":
        grasa_saludable_max = 25
        grasa_alto_riesgo = 35
    else:
        grasa_saludable_max = 32
        grasa_alto_riesgo = 42
    
    # Evaluación combinada
    if imc >= 30 or porcentaje_grasa >= grasa_alto_riesgo:
        return "alto"
    elif imc >= 25 or porcentaje_grasa >= grasa_saludable_max:
        return "moderado"
    else:
        return "bajo"


def get_recomendacion(clasificacion_imc: str, nivel_riesgo: str) -> str:
    """
    Genera recomendación basada en clasificación y riesgo.
    
    Args:
        clasificacion_imc: Clasificación IMC
        nivel_riesgo: Nivel de riesgo
        
    Returns:
        Texto de recomendación
    """
    recomendaciones = {
        ("bajo_peso", "bajo"): "Necesitas aumentar de peso de manera saludable",
        ("bajo_peso", "moderado"): "Aumenta calorías con alimentos nutritivos",
        ("normal", "bajo"): "Mantén tu actual estilo de vida saludable",
        ("normal", "moderado"): "Mejora composición corporal con ejercicio",
        ("sobrepeso", "moderado"): "Reduce calorías gradualmente",
        ("sobrepeso", "alto"): "Consulta con un profesional de salud",
        ("obesidad", "alto"): "Requiere atención profesional urgente",
    }
    
    clave = (clasificacion_imc, nivel_riesgo)
    return recomendaciones.get(clave, "Consulta con un nutricionista")
