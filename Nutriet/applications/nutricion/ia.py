import json
from django.conf import settings
from google import genai


client = genai.Client(api_key=settings.GEMINI_API_KEY)


def generar_explicacion_nutricional(data):
    condicion = data.get("condicion_medica", "") or "ninguna"
    objetivo = data.get("objetivo", "No definido")
    sexo = data.get("sexo", "M")
    edad = data.get("edad", "")
    peso = data.get("peso", "")
    altura = data.get("altura", "")
    nivel_actividad = data.get("ejercicio", "")
    plazo = data.get("plazo_meses", "")

    prompt = f"""
Eres un nutricionista clínico profesional de alto nivel.
Tu tarea es generar una evaluación nutricional completa, detallada y personalizada para el paciente.

REGLAS CRÍTICAS:
- No generes recetas ni planes de comidas.
- Habla con tono profesional, clínico y empático, como en una consulta real.
- Sé MUY específico según la condición médica del paciente — es lo más importante.
- Incluye recomendaciones de hidratación (consumo de agua) basadas en peso, actividad y condición.
- Cada sección debe tener contenido real, concreto y útil — no frases genéricas.
- Responde en español.
- Responde SOLO JSON estricto (sin texto extra, sin markdown, sin ```).

DATOS DEL PACIENTE:
Sexo: {sexo}
Edad: {edad} años
Peso actual: {peso} kg
Altura: {altura} cm
Objetivo: {objetivo}
Plazo: {plazo} meses
Nivel de actividad: {nivel_actividad}
Condición médica / restricción: {condicion}

RESULTADOS CALCULADOS:
IMC: {data.get("imc")}
Porcentaje de grasa corporal: {data.get("porcentaje_grasa")} %
TMB (kcal): {data.get("tmb")}
TDEE (kcal): {data.get("tdee")}
Calorías recomendadas por día: {data.get("calorias_diarias")}
Proteínas: {data.get("proteinas_gramos")} g
Grasas: {data.get("grasas_gramos")} g
Carbohidratos: {data.get("carbohidratos_gramos")} g

INSTRUCCIONES ESPECIALES SEGÚN CONDICIÓN MÉDICA:
- Si la condición es "diabetes": Explica control glucémico, índice glucémico bajo, reducción de azúcares simples, carbohidratos complejos, fibra, horarios de comida estables. Alimentos permitidos y prohibidos específicos para diabéticos.
- Si es "hipertension": Dieta DASH, reducción de sodio (<1500 mg/día), potasio, magnesio, alimentos que suben la presión, importancia de la hidratación.
- Si es "colesterol": Grasas saturadas vs insaturadas, omega-3, fibra soluble, alimentos que suben el LDL, importancia del aceite de oliva, aguacate, pescado azul.
- Si es "dislipidemia": Control de triglicéridos, eliminar harinas refinadas y alcohol, omega-3, fibra.
- Si es "celiaco": Gluten oculto, cross-contamination, alimentos naturalmente sin gluten, importancia de leer etiquetas.
- Si es "lactosa": Alternativas de calcio, alimentos con lactosa oculta, suplementación de vitamina D y calcio.
- Si es "indigestion": Alimentos irritantes (café, picante, alcohol, grasas), frecuencia de comidas, masticación lenta, horarios.
- Si es "hipertiroidismo": Control calórico alto, proteínas para preservar músculo, alimentos bociógenos, yodo.
- Si es "anemia": Hierro hemo vs no hemo, vitamina C para absorción, alimentos que inhiben el hierro (café, té, calcio en exceso).
- Si es "gota": Purinas, evitar carnes rojas, mariscos, alcohol, fructosa. Hidratación intensa.
- Si es "alergia_mani", "alergia_mariscos" o "alergia_huevo": Alternativas proteicas, riesgo de contaminación cruzada, leer etiquetas.
- Si es "vegetariano" o "vegano": Proteínas completas, B12, hierro no hemo, zinc, omega-3 vegetal, combinación de legumbres y cereales.
- Si no hay condición (ninguna): Da recomendaciones generales de calidad según objetivo.

Responde con este JSON exacto (todos los campos son obligatorios y deben tener contenido real y detallado):
{{
  "evaluacion_inicial": "Párrafo de bienvenida clínico: estado actual del paciente basado en IMC, grasa, edad, sexo y objetivo. Mínimo 3 oraciones concretas.",

  "diagnostico_corporal": {{
    "clasificacion_imc": "Clasificación exacta del IMC con lo que implica clínicamente para este paciente.",
    "interpretacion_grasa": "Qué significa su % de grasa, si es saludable, alto o bajo para su sexo y edad.",
    "riesgo_metabolico": "Evaluación del riesgo metabólico actual basado en todos los datos."
  }},

  "explicacion_calorica": "Explicación detallada de por qué necesita exactamente esas calorías. Relaciona TMB, TDEE y el déficit/superávit aplicado según objetivo y plazo.",

  "explicacion_macronutrientes": "Explica para qué sirve cada macronutriente en este paciente específico, por qué esa distribución, y cómo impacta su objetivo.",

  "hidratacion": {{
    "litros_recomendados": "Número exacto de litros/día recomendados (ej: 2.8 litros)",
    "calculo_explicado": "Explica cómo se calculó: peso, actividad física y condición médica si aplica.",
    "consejos_hidratacion": ["Consejo 1 específico", "Consejo 2 específico", "Consejo 3 específico", "Consejo 4 específico"],
    "señales_deshidratacion": ["Señal 1", "Señal 2", "Señal 3"]
  }},

  "recomendaciones_por_condicion": {{
    "titulo": "Recomendaciones para paciente con condición: {condicion}",
    "explicacion_condicion": "Qué implica esta condición médica para la nutrición de este paciente. Explicación clínica seria.",
    "impacto_en_objetivo": "Cómo afecta esta condición al objetivo nutricional del paciente y qué ajustes se hicieron.",
    "pautas_criticas": ["Pauta clínica 1 muy específica", "Pauta clínica 2", "Pauta clínica 3", "Pauta clínica 4", "Pauta clínica 5"],
    "nutrientes_clave": "Qué nutrientes son especialmente importantes o deben controlarse dada la condición."
  }},

  "alimentos": {{
    "recomendados": ["Alimento 1 con razón breve", "Alimento 2 con razón", "Alimento 3", "Alimento 4", "Alimento 5", "Alimento 6", "Alimento 7", "Alimento 8"],
    "a_evitar": ["Alimento 1 con razón", "Alimento 2 con razón", "Alimento 3", "Alimento 4", "Alimento 5", "Alimento 6"]
  }},

  "habitos_clinicos": {{
    "frecuencia_comidas": "Cuántas veces al día debe comer y por qué, según su condición y objetivo.",
    "horarios": "Recomendación sobre horarios específicos de comida.",
    "velocidad_comida": "Importancia de masticar despacio, duración mínima de cada comida.",
    "suplementos": "Si necesita suplementación (vitamina D, B12, hierro, omega-3, etc.) basada en condición y dieta."
  }},

  "ejercicio_y_nutricion": "Cómo debe coordinar alimentación y actividad física. Qué comer antes y después del ejercicio según su nivel de actividad.",

  "explicacion_del_cambio_fisico": "Descripción clínica realista de cómo y cuándo verá cambios. Ritmo esperado de cambio en el plazo definido.",

  "recomendaciones_generales": "5 a 7 recomendaciones prácticas del día a día que un nutricionista daría en consulta. Específicas, no genéricas.",

  "recomendaciones_profesionales": "Consejo clínico avanzado: qué exámenes de laboratorio se recomiendan, con qué frecuencia ir al nutricionista, si debe ver algún especialista según su condición.",

  "errores_comunes_a_evitar": ["Error específico 1 para esta persona", "Error 2", "Error 3", "Error 4", "Error 5"],

  "nota_importante": "Nota clínica final: recordatorio de que este plan es orientativo y debe ser revisado por un profesional de salud, especialmente si tiene condición médica activa."
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
