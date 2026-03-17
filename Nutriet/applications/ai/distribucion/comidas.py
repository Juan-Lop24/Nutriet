"""
esta funcio lo que va hacer es distribuir las calorías y macronutrientes para que la api de spoonacular pueda buscar recetas

El sistema adapta automáticamente los porcentajes según las comidas seleccionadas:
- Desayuno: 25% (si está disponible)
- Almuerzo: 35% (si está disponible)
- Cena: 30% (si está disponible)
- Snack: 10% (si está disponible)

Si alguna comida no está seleccionada, su porcentaje se redistribuye 
proporcionalmente entre las demás comidas.
"""

from typing import Dict, List
from decimal import Decimal, ROUND_HALF_UP


class DistribuidorComidas:


    PORCENTAJES_BASE = {
        "desayuno": 25.0,
        "almuerzo": 35.0,
        "cena": 30.0,
        "snack": 10.0,
    }

    def __init__(self):
        self.comidas_seleccionadas = []
        self.porcentajes_finales = {}

    def calcular_porcentajes_adaptables(self, comidas_seleccionadas: List[str]) -> Dict[str, float]:
      
        self.comidas_seleccionadas = [c.lower().strip() for c in comidas_seleccionadas]

        if not self.comidas_seleccionadas:
            raise ValueError("Debe seleccionar al menos una comida")

        # Filtra solo las comidas seleccionadas
        porcentajes_disponibles = {
            comida: porcentaje
            for comida, porcentaje in self.PORCENTAJES_BASE.items()
            if comida in self.comidas_seleccionadas
        }

        # Calcular el porcentaje total de comidas seleccionadas
        total_porcentaje_seleccionado = sum(porcentajes_disponibles.values())

        # Normalizar los porcentajes al 100%
        # Por ejemplo: si solo hay 3 comidas (sin snack):
        # Total = 25 + 35 + 30 = 90
        # Desayuno nuevo: (25/90) * 100 = 27.78%
        self.porcentajes_finales = {}
        for comida, porcentaje in porcentajes_disponibles.items():
            nuevo_porcentaje = (porcentaje / total_porcentaje_seleccionado) * 100
            self.porcentajes_finales[comida] = round(nuevo_porcentaje, 2)

        return self.porcentajes_finales

    def distribuir_calorias(
        self,
        calorias_totales: float,
        comidas_seleccionadas: List[str],
    ) -> Dict[str, float]:

        porcentajes = self.calcular_porcentajes_adaptables(comidas_seleccionadas)

        distribucion = {}
        for comida, porcentaje in porcentajes.items():
            calorias = round((calorias_totales * porcentaje) / 100, 1)
            distribucion[comida] = calorias

        return distribucion

    def distribuir_macronutrientes(
        self,
        proteinas_gramos: float,
        grasas_gramos: float,
        carbohidratos_gramos: float,
        comidas_seleccionadas: List[str],
    ) -> Dict[str, Dict[str, float]]:

        porcentajes = self.calcular_porcentajes_adaptables(comidas_seleccionadas)

        distribucion = {}
        for comida, porcentaje in porcentajes.items():
            distribucion[comida] = {
                "proteinas_g": round((proteinas_gramos * porcentaje) / 100, 1),
                "grasas_g": round((grasas_gramos * porcentaje) / 100, 1),
                "carbohidratos_g": round((carbohidratos_gramos * porcentaje) / 100, 1),
            }

        return distribucion

    def distribuir_completo(
        self,
        calorias_totales: float,
        proteinas_gramos: float,
        grasas_gramos: float,
        carbohidratos_gramos: float,
        comidas_seleccionadas: List[str],
    ) -> Dict[str, Dict]:

        porcentajes = self.calcular_porcentajes_adaptables(comidas_seleccionadas)

        distribucion = {}
        for comida, porcentaje in porcentajes.items():
            distribucion[comida] = {
                "porcentaje": porcentaje,
                "calorias": round((calorias_totales * porcentaje) / 100, 1),
                "proteinas_g": round((proteinas_gramos * porcentaje) / 100, 1),
                "grasas_g": round((grasas_gramos * porcentaje) / 100, 1),
                "carbohidratos_g": round((carbohidratos_gramos * porcentaje) / 100, 1),
            }

        return distribucion

    def validar_distribucion(self, distribucion: Dict[str, Dict]) -> bool:
        """
        Valida que la distribución sume correctamente (tolerancia de ±2 por redondeo).

        Args:
            distribucion: Dict retornado por distribuir_completo()

        Returns:
            True si la distribución es válida
        """
        total_porcentaje = sum(d.get("porcentaje", 0) for d in distribucion.values())
        return 98 <= total_porcentaje <= 102  # Tolerancia de ±2% por redondeo


# ============================================================================
# FUNCIONES DE INTEGRACIÓN CON EL MODELO
# ============================================================================


def distribuir_dieta_por_comidas(dieta_generada, comidas_seleccionadas: List[str]) -> Dict[str, Dict]:
    """
    Distribuye los datos de una DietaGenerada entre las comidas seleccionadas.

    Extrae calorías y macronutrientes del modelo DietaGenerada y los distribuye
    proporcionalmente según las comidas seleccionadas por el usuario.

    Args:
        dieta_generada: Instancia del modelo DietaGenerada
        comidas_seleccionadas: Lista de comidas seleccionadas del formulario

    Returns:
        Dict con la distribución completa por comida

    Ejemplo:
        >>> from aplicaciones.nutricion.models import DietaGenerada
        >>> dieta = DietaGenerada.objects.first()
        >>> comidas = ["desayuno", "almuerzo", "cena"]
        >>> distribucion = distribuir_dieta_por_comidas(dieta, comidas)
        >>> print(distribucion["almuerzo"]["calorias"])
        700.0
    """
    if not dieta_generada:
        raise ValueError("DietaGenerada no puede ser None")

    distribuidor = DistribuidorComidas()

    distribucion = distribuidor.distribuir_completo(
        calorias_totales=dieta_generada.calorias_diarias or 0,
        proteinas_gramos=dieta_generada.proteinas_gramos or 0,
        grasas_gramos=dieta_generada.grasas_gramos or 0,
        carbohidratos_gramos=dieta_generada.carbohidratos_gramos or 0,
        comidas_seleccionadas=comidas_seleccionadas,
    )

    return distribucion


def obtener_comidas_del_formulario(formulario_guardado) -> List[str]:

    if not formulario_guardado.comidas_preferidas:
        return []

    # Si es string, hacer split por comas
    if isinstance(formulario_guardado.comidas_preferidas, str):
        comidas = [c.strip() for c in formulario_guardado.comidas_preferidas.split(",")]
        return [c.lower() for c in comidas if c]

    # Si es lista (caso de MultipleChoiceField)
    if isinstance(formulario_guardado.comidas_preferidas, list):
        return [c.lower() for c in formulario_guardado.comidas_preferidas if c]

    return []


