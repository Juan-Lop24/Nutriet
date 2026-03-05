"""
api_services.py  –  Nutriet v4
Búsqueda inteligente de recetas en Spoonacular usando el perfil nutricional
del usuario (macros, tipo de dieta, restricciones, objetivo).

Estrategias para maximizar el catálogo con pocas peticiones:
  1. Parámetros nutricionales reales (minProtein, maxCalories, etc.)
  2. Banco de queries rotativas según objetivo y tipo de comida
  3. Caché en BD por 7 días, invalidado si cambia el perfil
  4. Traducción automática ES → EN para queries / EN → ES para resultados
"""

import requests
import random
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from deep_translator import GoogleTranslator

# ──────────────────────────────────────────────────────────────────────────────
# MAPEOS  (ES → EN para parámetros de Spoonacular)
# ──────────────────────────────────────────────────────────────────────────────

DIETA_MAP = {
    "vegetariano": "vegetarian",
    "vegano":      "vegan",
    "keto":        "ketogenic",
    "normal":      None,
    "paleo":       "paleo",
    "sin_gluten":  "gluten free",
}

# Intolerancias conocidas: si el campo restricciones_alimentarias contiene
# alguna de estas palabras clave, se añade al parámetro intolerances.
INTOLERANCIAS_MAP = {
    "lactosa":    "dairy",
    "gluten":     "gluten",
    "celiaco":    "gluten",
    "celíaco":    "gluten",
    "mariscos":   "shellfish",
    "mariscos":   "seafood",
    "nueces":     "tree nuts",
    "cacahuate":  "peanut",
    "maní":       "peanut",
    "soya":       "soy",
    "soja":       "soy",
    "huevo":      "egg",
    "huevos":     "egg",
    "pescado":    "seafood",
    "trigo":      "wheat",
    "sesamo":     "sesame",
    "sésamo":     "sesame",
}

TIPO_COMIDA_MAP = {
    "desayuno":  "breakfast",
    "almuerzo":  "main course",
    "cena":      "main course",
    "snack":     "snack",
    "merienda":  "snack",
}

# Banco de queries rotativas por objetivo (se elige una al azar + offset)
QUERIES_POR_OBJETIVO = {
    "Reducir": [
        "low calorie", "light meal", "salad", "grilled chicken",
        "vegetable soup", "lean protein", "steamed fish", "quinoa bowl",
        "zucchini", "cauliflower", "turkey", "egg white", "greek yogurt",
    ],
    "Aumentar": [
        "high protein", "muscle building", "chicken breast", "beef steak",
        "salmon", "tuna", "lentils", "cottage cheese", "oat", "brown rice",
        "pasta protein", "eggs", "tofu", "beans",
    ],
    "Mantener": [
        "balanced meal", "mediterranean", "whole grain", "mixed vegetables",
        "chicken rice", "fish", "legumes", "healthy pasta", "soup",
        "stir fry", "baked salmon", "avocado", "sweet potato",
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# TRADUCCIÓN  (usando deep_translator, free, sin cuota de peticiones)
# ──────────────────────────────────────────────────────────────────────────────

def _traducir(texto: str, src: str = "en", tgt: str = "es") -> str:
    if not texto or len(texto.strip()) < 2:
        return texto
    try:

        return GoogleTranslator(source=src, target=tgt).translate(texto) or texto
    except Exception:
        return texto


def traducir_texto(texto, idioma_destino="es"):
    return _traducir(texto, src="en", tgt=idioma_destino)


def traducir_receta(receta: dict) -> dict:
    """Traduce título, ingredientes e instrucciones de una receta EN→ES."""
    if not receta:
        return receta
    try:
        if receta.get("title"):
            receta["title"] = _traducir(receta["title"])

        for ing in receta.get("extendedIngredients", []):
            if ing.get("original"):
                ing["original"] = _traducir(ing["original"])
            if ing.get("name"):
                ing["name"] = _traducir(ing["name"])

        for grupo in receta.get("analyzedInstructions", []):
            for step in grupo.get("steps", []):
                if step.get("step"):
                    step["step"] = _traducir(step["step"])
    except Exception as e:
        print(f"[traducir_receta] {e}")
    return receta


# ──────────────────────────────────────────────────────────────────────────────
# EXTRACCIÓN DE INTOLERANCIAS desde texto libre
# ──────────────────────────────────────────────────────────────────────────────

def _extraer_intolerancias(texto_restricciones: str) -> str:
    """
    Devuelve string de intolerancias separadas por coma para Spoonacular.
    """
    if not texto_restricciones:
        return ""
    texto = texto_restricciones.lower()
    encontradas = set()
    for palabra_es, valor_en in INTOLERANCIAS_MAP.items():
        if palabra_es in texto:
            encontradas.add(valor_en)
    return ",".join(sorted(encontradas))


# ──────────────────────────────────────────────────────────────────────────────
# CONSTRUCCIÓN DE PARÁMETROS NUTRICIONALES
# ──────────────────────────────────────────────────────────────────────────────

def _params_nutricionales(calorias: float, proteinas: float,
                           grasas: float, carbos: float,
                           tolerancia: float = 0.25) -> dict:
    """
    Genera rangos min/max para la petición a Spoonacular.
    La tolerancia del 25 % da margen para encontrar más resultados.
    """
    params = {}
    if calorias:
        params["minCalories"] = int(calorias * (1 - tolerancia))
        params["maxCalories"] = int(calorias * (1 + tolerancia))
    if proteinas:
        params["minProtein"]  = int(proteinas * (1 - tolerancia))
        params["maxProtein"]  = int(proteinas * (1 + tolerancia))
    if grasas:
        params["minFat"]      = int(grasas * (1 - tolerancia))
        params["maxFat"]      = int(grasas * (1 + tolerancia))
    if carbos:
        params["minCarbs"]    = int(carbos * (1 - tolerancia))
        params["maxCarbs"]    = int(carbos * (1 + tolerancia))
    return params


# ──────────────────────────────────────────────────────────────────────────────
# CACHÉ EN BASE DE DATOS
# ──────────────────────────────────────────────────────────────────────────────

def _get_cache(clave: str):
    from .models import RecetaCache
    try:
        entrada = RecetaCache.objects.get(clave=clave, expira_en__gt=timezone.now())
        return entrada.recetas_json
    except RecetaCache.DoesNotExist:
        return None


def _set_cache(clave: str, recetas: list, dias: int = 7):
    from .models import RecetaCache
    expira = timezone.now() + timedelta(days=dias)
    RecetaCache.objects.update_or_create(
        clave=clave,
        defaults={"recetas_json": recetas, "expira_en": expira},
    )


# ──────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL — búsqueda inteligente por perfil
# ──────────────────────────────────────────────────────────────────────────────

def buscar_recetas_por_perfil(
    objetivo: str = "Mantener",
    tipo_dieta: str = "normal",
    restricciones: str = "",
    calorias_comida: float = 0,
    proteinas_comida: float = 0,
    grasas_comida: float = 0,
    carbos_comida: float = 0,
    tipo_comida: str = "",        # desayuno / almuerzo / cena / snack
    number: int = 12,
    offset_rotacion: int = 0,     # varía la query para diversificar
    usar_cache: bool = True,
) -> list:
    """
    Busca recetas personalizadas según el perfil nutricional del usuario.
    Usa caché en BD para no repetir peticiones.
    Devuelve lista de recetas (ya traducidas al español).
    """
    from .models import RecetaCache

    # — Elegir query rotativamente
    banco = QUERIES_POR_OBJETIVO.get(objetivo, QUERIES_POR_OBJETIVO["Mantener"])
    query = banco[offset_rotacion % len(banco)]

    # — Dieta e intolerancias
    diet         = DIETA_MAP.get(tipo_dieta)
    intolerances = _extraer_intolerancias(restricciones)
    meal_type    = TIPO_COMIDA_MAP.get(tipo_comida.lower(), "")

    # — Clave de caché
    cache_params = {
        "q": query, "diet": diet, "int": intolerances,
        "meal": meal_type, "kcal": round(calorias_comida),
        "prot": round(proteinas_comida), "n": number,
    }
    clave = RecetaCache.generar_clave(cache_params)

    if usar_cache:
        cached = _get_cache(clave)
        if cached is not None:
            return cached

    # — Petición a Spoonacular
    params = {
        "apiKey":               settings.SPOONACULAR_API_KEY,
        "query":                query,
        "number":               number,
        "addRecipeInformation": True,
        "fillNutrients":        True,
        "sort":                 "healthiness",
    }

    if diet:
        params["diet"] = diet
    if intolerances:
        params["intolerances"] = intolerances
    if meal_type:
        params["type"] = meal_type

    # Agrega rangos nutricionales si existen
    params.update(_params_nutricionales(
        calorias_comida, proteinas_comida, grasas_comida, carbos_comida
    ))

    try:
        resp = requests.get(
            settings.SPOONACULAR_BASE_URL + "recipes/complexSearch",
            params=params,
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        recetas = data.get("results", [])
    except Exception as e:
        print(f"[Spoonacular] Error en búsqueda: {e}")
        return []

    # Si Spoonacular no devuelve nada con los rangos nutricionales,
    # reintentamos sin ellos (más permisivo)
    if not recetas and calorias_comida:
        params_sin_macro = {k: v for k, v in params.items()
                            if not any(k.startswith(p) for p in ["min", "max"])}
        try:
            resp2 = requests.get(
                settings.SPOONACULAR_BASE_URL + "recipes/complexSearch",
                params=params_sin_macro,
                timeout=8,
            )
            recetas = resp2.json().get("results", [])
        except Exception:
            pass

    # Traducir títulos (los ingredientes se traducen en detalle al ver la receta)
    for r in recetas:
        if r.get("title"):
            r["title"] = _traducir(r["title"])

    # Guardar en caché
    if usar_cache and recetas:
        _set_cache(clave, recetas)

    return recetas


# ──────────────────────────────────────────────────────────────────────────────
# FUNCIÓN DE EXPLORACIÓN LIBRE (buscador del catálogo)
# ──────────────────────────────────────────────────────────────────────────────

def buscar_recetas(
    query: str = "healthy",
    number: int = 12,
    cuisine: str = None,
    diet: str = None,
    meal_type: str = None,
    maxCalories: int = None,
    intolerances: str = None,
    traducir: bool = True,
) -> dict | None:
    """Búsqueda libre para el explorador de recetas. Devuelve dict con 'results'."""
    # Si la query está en español, traducirla al inglés
    if query and any(c in query.lower() for c in
                     ["á","é","í","ó","ú","ñ","pollo","arroz","frijol","lenteja","atún"]):
        query = _traducir(query, src="es", tgt="en")

    params = {
        "apiKey":               settings.SPOONACULAR_API_KEY,
        "query":                query,
        "number":               number,
        "addRecipeInformation": True,
        "fillNutrients":        True,
    }
    if cuisine:      params["cuisine"]      = cuisine
    if diet:         params["diet"]         = diet
    if meal_type:    params["type"]         = meal_type
    if maxCalories:  params["maxCalories"]  = maxCalories
    if intolerances: params["intolerances"] = intolerances

    try:
        resp = requests.get(
            settings.SPOONACULAR_BASE_URL + "recipes/complexSearch",
            params=params, timeout=8,
        )
        resp.raise_for_status()
        resultado = resp.json()

        if traducir:
            for r in resultado.get("results", []):
                if r.get("title"):
                    r["title"] = _traducir(r["title"])

        return resultado
    except Exception as e:
        print(f"[buscar_recetas] {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# DETALLE DE RECETA
# ──────────────────────────────────────────────────────────────────────────────

def obtener_info_receta(recipe_id: int) -> dict | None:
    url    = f"{settings.SPOONACULAR_BASE_URL}recipes/{recipe_id}/information"
    params = {"apiKey": settings.SPOONACULAR_API_KEY, "includeNutrition": True}
    try:
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[obtener_info_receta] {recipe_id}: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# PLAN DE COMIDAS (legacy — se mantiene por compatibilidad)
# ──────────────────────────────────────────────────────────────────────────────

def buscar_plan_de_comidas(target_calories, diet=None, exclusions=None):
    url    = settings.SPOONACULAR_BASE_URL + "mealplanner/generate"
    params = {
        "apiKey":          settings.SPOONACULAR_API_KEY,
        "timeFrame":       "day",
        "targetCalories":  target_calories,
    }
    if diet:       params["diet"]    = diet
    if exclusions: params["exclude"] = exclusions

    try:
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        plan = resp.json()
        if plan and "meals" in plan:
            for comida in plan["meals"]:
                info = obtener_info_receta(comida["id"])
                if info:
                    info = traducir_receta(info)
                    comida.update({
                        "image":          info.get("image"),
                        "readyInMinutes": info.get("readyInMinutes", 0),
                        "servings":       info.get("servings", 1),
                        "title":          info.get("title", comida.get("title", "")),
                    })
        return plan
    except Exception as e:
        print(f"[buscar_plan_de_comidas] {e}")
        return None
