"""
Orquestador principal de la IA nutricional
VERSIÓN ACTUALIZADA - sin tipo_dieta
"""

from applications.ai.core import (
    calcular_imc,
    calcular_grasa_corporal_deurenberg,
    calcular_tmb,
    calcular_tdee
)
from applications.ai.macros.calculo import calcular_macros
from applications.ai.riesgo.evaluacion import clasificar_imc, evaluar_riesgo
from applications.ai.distribucion.comidas import DistribuidorComidas
from applications.ai.dtos.entrada import DatosEntrada
from applications.ai.dtos.resultado import ResultadoIA


class ProcesadorNutricion:

    def procesar(self, datos: DatosEntrada) -> ResultadoIA:
        datos.validar()

        imc = calcular_imc(datos.peso_kg, datos.altura_cm)
        porcentaje_grasa = calcular_grasa_corporal_deurenberg(imc, datos.edad_anos, datos.sexo)
        tmb = calcular_tmb(datos.peso_kg, datos.altura_cm, datos.edad_anos, datos.sexo)
        tdee = calcular_tdee(tmb, datos.nivel_actividad)
        calorias_recomendadas = self._ajustar_calorias_por_objetivo(tdee, datos.objetivo)

        # Sin tipo_dieta - usa distribución estándar
        proteinas, grasas, carbohidratos = calcular_macros(
            calorias_recomendadas,
            datos.objetivo
        )

        clasificacion = clasificar_imc(imc)
        riesgo = evaluar_riesgo(imc, porcentaje_grasa, datos.sexo)

        distribuidor = DistribuidorComidas()
        comidas = datos.comidas_preferidas if hasattr(datos, 'comidas_preferidas') else []
        if isinstance(comidas, str):
            comidas = [c.strip().lower() for c in comidas.split(",") if c.strip()]
        else:
            comidas = [c.lower() if isinstance(c, str) else c for c in comidas]

        distribucion_macros = {}
        if comidas:
            distribucion_macros = distribuidor.distribuir_completo(
                calorias_totales=calorias_recomendadas,
                proteinas_gramos=proteinas,
                grasas_gramos=grasas,
                carbohidratos_gramos=carbohidratos,
                comidas_seleccionadas=comidas
            )

        return ResultadoIA(
            imc=imc,
            porcentaje_grasa=porcentaje_grasa,
            tmb=tmb,
            tdee=tdee,
            calorias_recomendadas=calorias_recomendadas,
            proteinas_g=proteinas,
            grasas_g=grasas,
            carbohidratos_g=carbohidratos,
            clasificacion_imc=clasificacion,
            nivel_riesgo=riesgo,
            objetivo=datos.objetivo,
            distribucion_macros_comidas=distribucion_macros,
            ingredientes_excluidos=datos.get_ingredientes_excluidos(),
        )

    def _ajustar_calorias_por_objetivo(self, tdee: float, objetivo: str) -> float:
        obj = objetivo.lower().strip()
        if obj == "aumentar":
            return tdee + 400
        elif obj == "reducir":
            return tdee - 400
        return tdee