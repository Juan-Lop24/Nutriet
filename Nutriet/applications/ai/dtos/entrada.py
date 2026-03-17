"""
Contrato de datos de entrada para la IA
"""

from dataclasses import dataclass, field
from typing import List


RESTRICCIONES_POR_CONDICION = {
    "diabetes": ["sugar", "honey", "syrup", "candy", "soda", "azucar", "miel", "jarabe"],
    "celiaco": ["gluten", "wheat", "barley", "rye", "trigo", "cebada", "centeno"],
    "lactosa": ["milk", "cheese", "butter", "cream", "yogurt", "leche", "queso", "mantequilla"],
    "hipertension": ["salt", "sodium", "sal", "sodio"],
    "colesterol": ["butter", "bacon", "lard", "mantequilla", "tocino"],
    "gota": ["wine", "beer", "alcohol", "shellfish", "vino", "cerveza"],
    "alergia_mani": ["peanut", "peanut butter", "mani", "cacahuate"],
    "alergia_mariscos": ["shrimp", "lobster", "crab", "camaron", "langosta", "cangrejo"],
    "alergia_huevo": ["egg", "mayonnaise", "huevo", "mayonesa"],
    "vegetariano": ["meat", "chicken", "pork", "beef", "fish", "carne", "pollo", "cerdo", "pescado"],
    "vegano": ["meat", "chicken", "pork", "beef", "fish", "milk", "cheese", "egg", "honey",
               "carne", "pollo", "cerdo", "pescado", "leche", "queso", "huevo", "miel"],
}


@dataclass
class DatosEntrada:
    # Datos personales
    peso_kg: float
    altura_cm: float
    edad_anos: int
    sexo: str  # "M" o "F"

    # Objetivos y actividad
    objetivo: str  # "aumentar", "reducir", "mantener"
    nivel_actividad: str  # "sedentario", "ligero", "moderado", "intenso", "muy_intenso"

    # Preferencias de comidas del día
    comidas_preferidas: List[str] = field(default_factory=list)

    # Ingredientes a excluir por gusto personal
    restricciones_ingredientes: List[str] = field(default_factory=list)

    # Condiciones médicas / alergias
    condiciones_medicas: List[str] = field(default_factory=list)

    def validar(self):
        if self.peso_kg <= 0:
            raise ValueError("El peso debe ser mayor a 0")
        if self.altura_cm <= 0 or self.altura_cm > 350:
            raise ValueError("La altura debe estar entre 0 y 350 cm")
        if self.edad_anos < 10 or self.edad_anos > 110:
            raise ValueError("La edad debe estar entre 10 y 100 años")
        if self.sexo not in ["M", "F"]:
            raise ValueError("El sexo debe ser 'M' o 'F'")
        if self.objetivo not in ["aumentar", "reducir", "mantener"]:
            raise ValueError("Objetivo inválido")
        if self.nivel_actividad not in ["sedentario", "ligero", "moderado", "intenso", "muy_intenso"]:
            raise ValueError("Nivel de actividad inválido")

    def get_ingredientes_excluidos(self) -> List[str]:
        excluidos = set(i.lower().strip() for i in self.restricciones_ingredientes)
        for condicion in self.condiciones_medicas:
            cond = condicion.lower().strip()
            if cond in RESTRICCIONES_POR_CONDICION:
                excluidos.update(RESTRICCIONES_POR_CONDICION[cond])
        return list(excluidos)