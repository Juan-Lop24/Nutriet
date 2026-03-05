"""
Calcula proteínas, grasas y carbohidratos diarios.

Se eliminó la dependencia de tipo_dieta (vegano, keto, etc.)
Ahora usa distribución nutricional estándar.
Las restricciones alimentarias se manejan como filtros en el explorador de recetas.
"""


class AjustadorDieta:
    """
    Mantiene el nombre AjustadorDieta por compatibilidad con imports existentes.
    Calcula macronutrientes usando distribución estándar.

    Distribución estándar (OMS / nutrición deportiva):
    - Proteínas: 30%
    - Grasas: 30%
    - Carbohidratos: 40%
    """

    MACROS_ESTANDAR = {
        "proteinas_porcentaje": 30.0,
        "grasas_porcentaje": 30.0,
        "carbohidratos_porcentaje": 40.0,
    }

    def __init__(self, tipo_dieta: str = "normal"):
        """Se acepta tipo_dieta por compatibilidad pero ya no modifica los macros."""
        pass

    def calcular_macronutrientes_ajustados(self, calorias_totales: float):
        """
        Calcula gramos de macronutrientes según distribución estándar.

        1g proteína = 4 kcal
        1g grasa = 9 kcal
        1g carbohidrato = 4 kcal

        Args:
            calorias_totales: Calorías diarias totales

        Returns:
            Tupla (proteinas_g, grasas_g, carbohidratos_g)
        """
        macros = self.MACROS_ESTANDAR

        calorias_proteinas = calorias_totales * (macros["proteinas_porcentaje"] / 100)
        calorias_grasas = calorias_totales * (macros["grasas_porcentaje"] / 100)
        calorias_carbs = calorias_totales * (macros["carbohidratos_porcentaje"] / 100)

        proteinas_g = int(calorias_proteinas / 4)
        grasas_g = int(calorias_grasas / 9)
        carbohidratos_g = int(calorias_carbs / 4)

        return proteinas_g, grasas_g, carbohidratos_g


def calcular_macros(calorias_diarias, objetivo, formulario=None, tipo_dieta=None):
    """
    Calcula proteínas, grasas y carbohidratos.

    Los parámetros formulario y tipo_dieta se mantienen por compatibilidad
    pero ya no modifican el resultado.

    Args:
        calorias_diarias: Total de calorías diarias
        objetivo: "aumentar", "reducir" o "mantener"
        formulario: (ignorado, compatibilidad)
        tipo_dieta: (ignorado, compatibilidad)

    Returns:
        (proteinas_g, grasas_g, carbohidratos_g)
    """
    try:
        calorias = float(calorias_diarias) if calorias_diarias else 2000.0
    except (TypeError, ValueError):
        calorias = 2000.0

    ajustador = AjustadorDieta()
    return ajustador.calcular_macronutrientes_ajustados(calorias)