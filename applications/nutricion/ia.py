import json
from django.conf import settings
from google import genai


client = genai.Client(api_key=settings.GEMINI_API_KEY)


def generar_explicacion_nutricional(data):
    prompt = f"""
Eres un nutricionista profesional con enfoque clínico.
Tu tarea es explicar claramente al usuario los resultados obtenidos en su evaluación.

Reglas IMPORTANTES:
- No generes recetas.
- No hagas un plan por comidas.
- No seas motivacional.
- Habla como nutricionista real, profesional y claro.
- Explica con ejemplos simples.
- Responde en español.
- Responde SOLO JSON estricto (sin texto extra, sin markdown, sin ```).

DATOS DEL USUARIO:
Objetivo: {data.get("objetivo", "No definido")}
Plazo: {data.get("plazo_meses", "No definido")} meses

RESULTADOS CALCULADOS:
IMC: {data.get("imc")}
Porcentaje de grasa corporal: {data.get("porcentaje_grasa")} %
TMB (kcal): {data.get("tmb")}
TDEE (kcal): {data.get("tdee")}
Calorías recomendadas por día: {data.get("calorias_diarias")}

Macronutrientes diarios:
Proteínas: {data.get("proteinas_gramos")} g
Grasas: {data.get("grasas_gramos")} g
Carbohidratos: {data.get("carbohidratos_gramos")} g

Responde con este JSON exacto:
{{
  "explicacion_general": "",
  "explicacion_imc": "",
  "explicacion_grasa_corporal": "",
  "explicacion_tmb": "",
  "explicacion_tdee": "",
  "explicacion_calorias": "",
  "explicacion_macros": "",
  "recomendaciones": "",
  "como_lograr_el_objetivo": "",
  "errores_comunes": [],
  "nota_importante": ""
}}
"""

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt
        )

        texto = response.text.strip()

        # Limpieza por si mete texto extra
        inicio = texto.find("{")
        fin = texto.rfind("}")

        if inicio == -1 or fin == -1:
            raise ValueError("La respuesta no contiene JSON válido.")

        json_str = texto[inicio:fin+1]

        return json.loads(json_str)

    except Exception as e:
        print("Error generando explicación:", e)

        return {
            "explicacion_general": "No se pudo generar la explicación en este momento.",
            "explicacion_imc": "",
            "explicacion_grasa_corporal": "",
            "explicacion_tmb": "",
            "explicacion_tdee": "",
            "explicacion_calorias": "",
            "explicacion_macros": "",
            "recomendaciones": "",
            "como_lograr_el_objetivo": "",
            "errores_comunes": [],
            "nota_importante": ""
        }
