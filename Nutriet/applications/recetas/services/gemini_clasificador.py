import json
from django.conf import settings
from google import genai

# Cliente Gemini (singleton)
_client = None

def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


# ── Prompt (versión v2) ───────────────────────────────────────────────────────
VERSION_PROMPT = "v2"

PROMPT_TEMPLATE = """
Eres un nutricionista clínico experto. Analiza la siguiente receta y responde SOLO con JSON válido, sin markdown, sin texto extra.

RECETA:
Nombre: {nombre}
Categoría: {categoria}
Área/Cocina: {area}
Ingredientes: {ingredientes}
Instrucciones (resumen): {instrucciones}

TAREA 1 — RESTRICCIONES MÉDICAS
Para cada restricción, indica true si la receta es INCOMPATIBLE (no apta) para esa condición:
- diabetes: Contiene azúcares simples altos, harinas refinadas o ingredientes de alto índice glucémico que la hacen inadecuada para diabéticos
- intolerancia_lactosa: Contiene lácteos (leche, queso, mantequilla, crema, yogur, etc.)
- celiaca: Contiene gluten (trigo, cebada, centeno, avena contaminada, salsas con harina)
- alergia_mani: Contiene maní, mantequilla de maní o puede tener trazas de maní
- intolerancia_fructosa: Contiene fructosa libre alta (miel, jarabe de maíz, frutas en grandes cantidades, HFCS)
- hipertension: Contiene sodio alto (sal en exceso, salsa de soya, embutidos, quesos curados, snacks salados)
- hipercolesterolemia: Contiene grasas saturadas altas o trans (mantequilla, crema, carnes grasas, aceite de palma)
- dislipidemia: Contiene grasas saturadas o trans, colesterol alto o azúcares que elevan triglicéridos
- indigestion: Contiene ingredientes irritantes gástricos (picante, ajo crudo en exceso, fritura abundante, acidez alta)
- hipertiroidismo: Contiene ingredientes que estimulan la tiroides o interfieren (soya, algas marinas, yodo alto)
- anemia_ferropenica: Contiene inhibidores de la absorción de hierro (té, café, lácteos en exceso) o es bajo en hierro biodisponible
- alergia_huevo: Contiene huevo o derivados del huevo (mayonesa, claras, yemas, etc.)
- alergia_marisco: Contiene mariscos, crustáceos o moluscos (camarones, cangrejo, mejillones, almejas, calamares, etc.)

TAREA 2 — MACRONUTRIENTES ESTIMADOS (por porción estándar del plato)
Estima los valores nutricionales aproximados basándote en los ingredientes.

TAREA 3 — NOMBRE EN ESPAÑOL
Traduce el nombre de la receta al español de forma natural.

TAREA 4 — DIFICULTAD Y TIEMPO
Estima la dificultad (facil/media/dificil) y el tiempo total de preparación en minutos.

RESPONDE EXACTAMENTE con este JSON (sin nada más):
{{
  "nombre_es": "",
  "restricciones": {{
    "diabetes": false,
    "intolerancia_lactosa": false,
    "celiaca": false,
    "alergia_mani": false,
    "intolerancia_fructosa": false,
    "hipertension": false,
    "hipercolesterolemia": false,
    "dislipidemia": false,
    "indigestion": false,
    "hipertiroidismo": false,
    "anemia_ferropenica": false,
    "alergia_huevo": false,
    "alergia_marisco": false
  }},
  "justificacion": {{
    "diabetes": "Razón breve",
    "intolerancia_lactosa": "Razón breve",
    "celiaca": "Razón breve",
    "alergia_mani": "Razón breve",
    "intolerancia_fructosa": "Razón breve",
    "hipertension": "Razón breve",
    "hipercolesterolemia": "Razón breve",
    "dislipidemia": "Razón breve",
    "indigestion": "Razón breve",
    "hipertiroidismo": "Razón breve",
    "anemia_ferropenica": "Razón breve",
    "alergia_huevo": "Razón breve",
    "alergia_marisco": "Razón breve"
  }},
  "macros": {{
    "calorias": 0,
    "proteinas_g": 0,
    "carbohidratos_g": 0,
    "grasas_g": 0,
    "fibra_g": 0,
    "sodio_mg": 0,
    "azucares_g": 0,
    "grasas_saturadas_g": 0
  }},
  "dificultad": "media",
  "tiempo_prep_min": 30
}}
"""


def clasificar_receta(receta) -> dict:
    """
    Clasifica una instancia de RecetaMealDB usando Gemini.

    Devuelve el dict JSON parseado o lanza excepción si falla.
    """
    instrucciones_cortas = (receta.instrucciones_raw or "")[:800]

    prompt = PROMPT_TEMPLATE.format(
        nombre       = receta.nombre,
        categoria    = receta.categoria or "Desconocida",
        area         = receta.area or "Desconocida",
        ingredientes = receta.ingredientes_texto or "No disponible",
        instrucciones = instrucciones_cortas or "No disponible",
    )

    client   = _get_client()
    response = client.models.generate_content(
        model    = "models/gemini-2.5-flash",
        contents = prompt,
    )

    texto = response.text.strip()

    # Limpiar markdown si Gemini lo agrega
    if "```" in texto:
        inicio = texto.find("{")
        fin    = texto.rfind("}")
        if inicio != -1 and fin != -1:
            texto = texto[inicio:fin + 1]

    return json.loads(texto)


def aplicar_clasificacion(receta, resultado: dict):
    """
    Guarda el resultado de Gemini en la BD:
      - Actualiza macros en RecetaMealDB
      - Crea/actualiza ClasificacionReceta
    """
    from applications.recetas.models import ClasificacionReceta
    from django.utils import timezone

    # ── Macros → RecetaMealDB ─────────────────────────────────────────────────
    macros = resultado.get("macros", {})
    receta.calorias_estimadas  = macros.get("calorias")
    receta.proteinas_g         = macros.get("proteinas_g")
    receta.carbohidratos_g     = macros.get("carbohidratos_g")
    receta.grasas_g            = macros.get("grasas_g")
    receta.fibra_g             = macros.get("fibra_g")
    receta.sodio_mg            = macros.get("sodio_mg")
    receta.azucares_g          = macros.get("azucares_g")
    receta.grasas_saturadas_g  = macros.get("grasas_saturadas_g")
    receta.nombre_es           = resultado.get("nombre_es") or receta.nombre
    receta.clasificado         = True
    receta.clasificado_en      = timezone.now()
    receta.error_clasificacion = None
    receta.save()

    # ── Clasificación → ClasificacionReceta ───────────────────────────────────
    restricciones = resultado.get("restricciones", {})
    ClasificacionReceta.objects.update_or_create(
        receta = receta,
        defaults = {
            "diabetes":              bool(restricciones.get("diabetes", False)),
            "intolerancia_lactosa":  bool(restricciones.get("intolerancia_lactosa", False)),
            "celiaca":               bool(restricciones.get("celiaca", False)),
            "alergia_mani":          bool(restricciones.get("alergia_mani", False)),
            "intolerancia_fructosa": bool(restricciones.get("intolerancia_fructosa", False)),
            "hipertension":          bool(restricciones.get("hipertension", False)),
            "hipercolesterolemia":   bool(restricciones.get("hipercolesterolemia", False)),
            "dislipidemia":          bool(restricciones.get("dislipidemia", False)),
            "indigestion":           bool(restricciones.get("indigestion", False)),
            "hipertiroidismo":       bool(restricciones.get("hipertiroidismo", False)),
            "anemia_ferropenica":    bool(restricciones.get("anemia_ferropenica", False)),
            "alergia_huevo":         bool(restricciones.get("alergia_huevo", False)),
            "alergia_marisco":       bool(restricciones.get("alergia_marisco", False)),
            "justificacion":         resultado.get("justificacion", {}),
            "dificultad":            resultado.get("dificultad"),
            "tiempo_prep_min":       resultado.get("tiempo_prep_min"),
            "version_prompt":        VERSION_PROMPT,
        }
    )
