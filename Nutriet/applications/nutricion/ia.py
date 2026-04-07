import json
from django.conf import settings
from google import genai


client = genai.Client(api_key=settings.GEMINI_API_KEY)


def generar_explicacion_nutricional(data):
    # ✅ Soporte para múltiples condiciones médicas
    condiciones_lista = data.get("condiciones_medicas", [])
    if condiciones_lista:
        condicion = ", ".join(condiciones_lista)
    else:
        condicion = data.get("condicion_medica", "") or "ninguna"
    objetivo = data.get("objetivo", "No definido")
    sexo = data.get("sexo", "M")
    edad = data.get("edad", "")
    peso = data.get("peso", "")
    altura = data.get("altura", "")
    nivel_actividad = data.get("ejercicio", "")
    plazo = data.get("plazo_meses", "")

    prompt = f"""
Eres un nutricionista clínico. Genera una evaluación nutricional concisa y personalizada.

REGLAS:
- Sin recetas ni planes de comidas.
- Tono profesional y directo. Máximo 2 oraciones por campo de texto.
- Sé específico según la condición médica — es lo más importante.
- Responde en español.
- Responde SOLO JSON estricto (sin markdown, sin ```).

DATOS DEL PACIENTE:
Sexo: {sexo} | Edad: {edad} años | Peso: {peso} kg | Altura: {altura} cm
Objetivo: {objetivo} | Plazo: {plazo} meses | Actividad: {nivel_actividad}
Condición médica: {condicion}

RESULTADOS:
IMC: {data.get("imc")} | Grasa: {data.get("porcentaje_grasa")}%
TMB: {data.get("tmb")} kcal | TDEE: {data.get("tdee")} kcal
Calorías/día: {data.get("calorias_diarias")} | Proteínas: {data.get("proteinas_gramos")}g | Grasas: {data.get("grasas_gramos")}g | Carbos: {data.get("carbohidratos_gramos")}g

GUÍA POR CONDICIÓN (aplica TODAS las que correspondan, ya que el paciente puede tener varias):
- diabetes: control glucémico, IG bajo, reducir azúcares simples, carbos complejos y fibra.
- hipertension: dieta DASH, sodio <1500mg/día, aumentar potasio y magnesio.
- colesterol: reducir grasas saturadas, aumentar omega-3 y fibra soluble.
- dislipidemia: eliminar harinas refinadas y alcohol, omega-3.
- celiaco: evitar gluten oculto, contaminación cruzada, leer etiquetas.
- lactosa: alternativas de calcio, suplementar vitamina D.
- indigestion: evitar irritantes (café, picante, alcohol), comer despacio.
- hipertiroidismo: alta proteína para preservar músculo, control de yodo.
- anemia: hierro hemo, vitamina C para absorción, evitar café con comidas.
- gota: evitar purinas, alcohol y fructosa. Hidratación alta.
- alergia_mani / alergia_mariscos / alergia_huevo: alternativas proteicas, evitar contaminación cruzada.
- vegetariano / vegano: proteínas completas, B12, hierro no hemo, omega-3 vegetal.
- ninguna: recomendaciones según objetivo.

JSON a responder (todos los campos obligatorios, textos cortos y directos):
{{
  "evaluacion_inicial": "2 oraciones clínicas sobre el estado actual del paciente según IMC, grasa y objetivo.",

  "diagnostico_corporal": {{
    "clasificacion_imc": "Clasificación del IMC y qué implica. 1 oración.",
    "interpretacion_grasa": "Si el % de grasa es saludable o no para su sexo/edad. 1 oración.",
    "riesgo_metabolico": "Nivel de riesgo metabólico actual. 1 oración."
  }},

  "explicacion_calorica": "Por qué ese número de calorías según TMB, TDEE y objetivo. 2 oraciones.",

  "explicacion_macronutrientes": "Para qué sirve cada macro en este paciente y por qué esa distribución. 2 oraciones.",

  "hidratacion": {{
    "litros_recomendados": "Ej: 2.8 litros",
    "calculo_explicado": "Cómo se calculó según peso y actividad. 1 oración.",
    "consejos_hidratacion": ["Consejo breve 1", "Consejo breve 2", "Consejo breve 3"],
    "señales_deshidratacion": ["Señal 1", "Señal 2", "Señal 3"]
  }},

  "recomendaciones_por_condicion": {{
    "titulo": "Recomendaciones para: {condicion}",
    "explicacion_condicion": "Qué implica esta condición para la nutrición. 2 oraciones.",
    "impacto_en_objetivo": "Cómo afecta al objetivo y qué ajustes se hicieron. 1 oración.",
    "pautas_criticas": ["Pauta clave 1", "Pauta clave 2", "Pauta clave 3", "Pauta clave 4"],
    "nutrientes_clave": "Nutrientes importantes o a controlar según la condición. 1 oración."
  }},

  "alimentos": {{
    "recomendados": ["Alimento 1", "Alimento 2", "Alimento 3", "Alimento 4", "Alimento 5", "Alimento 6"],
    "a_evitar": ["Alimento 1", "Alimento 2", "Alimento 3", "Alimento 4", "Alimento 5"]
  }},

  "habitos_clinicos": {{
    "frecuencia_comidas": "Cuántas veces al día y por qué. 1 oración.",
    "horarios": "Recomendación de horarios. 1 oración.",
    "velocidad_comida": "Consejo de masticación. 1 oración.",
    "suplementos": "Si necesita suplementación o no. 1 oración."
  }},

  "ejercicio_y_nutricion": "Cómo coordinar alimentación y ejercicio según su nivel de actividad. 2 oraciones.",

  "explicacion_del_cambio_fisico": "Cambio realista esperado en {plazo} meses. 2 oraciones.",

  "recomendaciones_generales": "4 a 5 recomendaciones prácticas concretas separadas por punto y seguido.",

  "recomendaciones_profesionales": "Qué exámenes hacerse y cada cuánto ir al nutricionista. 2 oraciones.",

  "errores_comunes_a_evitar": ["Error 1 específico", "Error 2", "Error 3", "Error 4"],

  "nota_importante": "Recordatorio de que este plan es orientativo y debe revisarse con un profesional. 1 oración."
}}
"""

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt
        )

        texto = response.text.strip()

        inicio = texto.find("{")
        fin = texto.rfind("}")

        if inicio == -1 or fin == -1:
            raise ValueError("La respuesta no contiene JSON válido.")

        json_str = texto[inicio:fin+1]

        return json.loads(json_str)

    except Exception as e:
        print("Error generando explicación:", e)

        return {
            "evaluacion_inicial": "No se pudo generar la evaluación en este momento.",
            "diagnostico_corporal": {
                "clasificacion_imc": "",
                "interpretacion_grasa": "",
                "riesgo_metabolico": ""
            },
            "explicacion_calorica": "",
            "explicacion_macronutrientes": "",
            "hidratacion": {
                "litros_recomendados": "",
                "calculo_explicado": "",
                "consejos_hidratacion": [],
                "señales_deshidratacion": []
            },
            "recomendaciones_por_condicion": {
                "titulo": "",
                "explicacion_condicion": "",
                "impacto_en_objetivo": "",
                "pautas_criticas": [],
                "nutrientes_clave": ""
            },
            "alimentos": {
                "recomendados": [],
                "a_evitar": []
            },
            "habitos_clinicos": {
                "frecuencia_comidas": "",
                "horarios": "",
                "velocidad_comida": "",
                "suplementos": ""
            },
            "ejercicio_y_nutricion": "",
            "explicacion_del_cambio_fisico": "",
            "recomendaciones_generales": "",
            "recomendaciones_profesionales": "",
            "errores_comunes_a_evitar": [],
            "nota_importante": ""
        }
