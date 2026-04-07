import random
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q
from django.core.paginator import Paginator
from Nutriet.utils import verificar_formulario_completo
from applications.nutricion.models import DietaGenerada, FormularioNutricionGuardado
from applications.recetas.models import RecetaMealDB, ClasificacionReceta, RESTRICCION_KEYS
import json
from .models import RecetaFavorita

# ✅ FIX: eliminado el import de csrf_exempt — ya no se usa en ningún endpoint


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

TEXTO_A_RESTRICCION = {
    "diabetes": "diabetes", "diabete": "diabetes",
    "lactosa": "intolerancia_lactosa", "lácteo": "intolerancia_lactosa",
    "lacteo": "intolerancia_lactosa",
    "celiaca": "celiaca", "celíaca": "celiaca", "celiaco": "celiaca",
    "celíaco": "celiaca", "gluten": "celiaca",
    "maní": "alergia_mani", "mani": "alergia_mani", "cacahuate": "alergia_mani",
    "fructosa": "intolerancia_fructosa",
    "hipertension": "hipertension", "hipertensión": "hipertension",
    "presion alta": "hipertension", "presión alta": "hipertension",
    "colesterol": "hipercolesterolemia", "hipercolesterol": "hipercolesterolemia",
    "dislipidemia": "dislipidemia", "trigliceridos": "dislipidemia", "triglicéridos": "dislipidemia",
    "indigestion": "indigestion", "indigestión": "indigestion",
    "gastritis": "indigestion", "reflujo": "indigestion",
    "hipertiroidismo": "hipertiroidismo", "tiroides": "hipertiroidismo",
    "anemia": "anemia_ferropenica", "anemia ferropenica": "anemia_ferropenica",
    "huevo": "alergia_huevo",
    "marisco": "alergia_marisco", "mariscos": "alergia_marisco",
    "crustaceo": "alergia_marisco", "crustáceo": "alergia_marisco",
    "camaron": "alergia_marisco", "camarón": "alergia_marisco",
}

CONDICION_A_RESTRICCION = {
    "diabetes":         "diabetes",
    "celiaco":          "celiaca",
    "lactosa":          "intolerancia_lactosa",
    "hipertension":     "hipertension",
    "colesterol":       "hipercolesterolemia",
    "alergia_mani":     "alergia_mani",
    "alergia_mariscos": "alergia_marisco",
    "alergia_huevo":    "alergia_huevo",
    # Nuevas condiciones del formulario
    "gota":             "hipertension",   # La gota comparte restricciones con HTA (sodio, purinas)
    "dislipidemia":     "dislipidemia",
    "indigestion":      "indigestion",
    "hipertiroidismo":  "hipertiroidismo",
    "anemia":           "anemia_ferropenica",
}
TRADUCCIONES_CATEGORIAS = {
    "Beef": "Carne de res",
    "Breakfast": "Desayuno",
    "Chicken": "Pollo",
    "Dessert": "Postre",
    "Goat": "Cabra",
    "Lamb": "Cordero",
    "Miscellaneous": "Misceláneo",
    "Pasta": "Pasta",
    "Pork": "Cerdo",
    "Seafood": "Mariscos",
    "Side": "Acompañamiento",
    "Starter": "Entrada",
    "Vegan": "Vegano",
    "Vegetarian": "Vegetariano"
}

def _parsear_restricciones_combinadas(formulario):
    """
    ✅ Soporta múltiples condiciones médicas.
    Primero lee condiciones_medicas_json (lista), luego el campo legado condicion_medica.
    """
    restricciones = set()
    # Obtener lista de condiciones desde el método del modelo
    condiciones = []
    if hasattr(formulario, 'get_condiciones_lista'):
        condiciones = formulario.get_condiciones_lista()
    elif getattr(formulario, 'condiciones_medicas_json', None):
        condiciones = formulario.condiciones_medicas_json
    else:
        condicion_legado = getattr(formulario, 'condicion_medica', '') or ''
        if condicion_legado:
            condiciones = [condicion_legado]

    for condicion in condiciones:
        cond = condicion.strip().lower()
        if cond in CONDICION_A_RESTRICCION:
            restricciones.add(CONDICION_A_RESTRICCION[cond])
    return list(restricciones)


def _parsear_condiciones_dieta(formulario):
    """
    ✅ Retorna lista completa de condiciones para aplicar filtros de vegetariano/vegano.
    """
    if hasattr(formulario, 'get_condiciones_lista'):
        return formulario.get_condiciones_lista()
    if getattr(formulario, 'condiciones_medicas_json', None):
        return formulario.condiciones_medicas_json
    condicion = getattr(formulario, 'condicion_medica', '') or ''
    return [condicion] if condicion else []


def _traducir_ingrediente_a_ingles(termino: str) -> list:
    DICCIONARIO_ES_EN = {
        "arroz": ["rice"], "pollo": ["chicken"], "carne": ["beef", "meat"],
        "cerdo": ["pork"], "cordero": ["lamb"],
        "pescado": ["fish", "salmon", "tuna", "cod"],
        "atún": ["tuna"], "atun": ["tuna"],
        "salmón": ["salmon"], "salmon": ["salmon"],
        "camarones": ["shrimp", "prawn"], "camarón": ["shrimp", "prawn"],
        "mariscos": ["seafood", "shrimp", "prawn", "crab", "lobster"],
        "huevo": ["egg"], "leche": ["milk"], "queso": ["cheese"],
        "mantequilla": ["butter"], "crema": ["cream"], "harina": ["flour"],
        "azúcar": ["sugar"], "azucar": ["sugar"], "sal": ["salt"],
        "aceite": ["oil"], "cebolla": ["onion"], "ajo": ["garlic"],
        "tomate": ["tomato"], "papa": ["potato"], "patata": ["potato"],
        "zanahoria": ["carrot"], "lechuga": ["lettuce"], "espinaca": ["spinach"],
        "brócoli": ["broccoli"], "brocoli": ["broccoli"],
        "maíz": ["corn"], "maiz": ["corn"],
        "frijoles": ["beans"], "frijol": ["beans"], "lentejas": ["lentils"],
        "garbanzos": ["chickpeas"],
        "pasta": ["pasta", "spaghetti", "noodles"], "pan": ["bread"],
        "trigo": ["wheat"], "gluten": ["gluten", "wheat", "flour"],
        "maní": ["peanut"], "mani": ["peanut"], "cacahuate": ["peanut"],
        "nuez": ["walnut", "nut"], "nueces": ["walnut", "nut"],
        "almendra": ["almond"], "chocolate": ["chocolate"],
        "limón": ["lemon"], "limon": ["lemon"], "naranja": ["orange"],
        "manzana": ["apple"], "plátano": ["banana"], "platano": ["banana"],
        "piña": ["pineapple"], "pina": ["pineapple"],
        "fresa": ["strawberry"], "fresas": ["strawberry"], "uva": ["grape"],
        "pimiento": ["pepper", "bell pepper"], "chile": ["chili", "chile"],
        "cilantro": ["cilantro", "coriander"], "perejil": ["parsley"],
        "comino": ["cumin"], "pimienta": ["pepper", "black pepper"],
        "canela": ["cinnamon"], "vainilla": ["vanilla"], "vinagre": ["vinegar"],
        "salsa": ["sauce", "salsa"], "mostaza": ["mustard"],
        "mayonesa": ["mayonnaise"], "ketchup": ["ketchup"],
        "soya": ["soy", "soya"], "soja": ["soy", "soya"],
        "tocino": ["bacon"], "jamón": ["ham"], "jamon": ["ham"],
        "salchicha": ["sausage"], "pavo": ["turkey"], "pato": ["duck"],
        "conejo": ["rabbit"],
    }

    

    termino_lower = termino.strip().lower()
    if termino_lower in DICCIONARIO_ES_EN:
        return DICCIONARIO_ES_EN[termino_lower]
    for es, en_list in DICCIONARIO_ES_EN.items():
        if es in termino_lower or termino_lower in es:
            return en_list
    try:
        from .api_services import _traducir
        traducido = _traducir(termino, src="es", tgt="en")
        if traducido and traducido.lower() != termino_lower:
            return [traducido.lower()]
    except Exception:
        pass
    return [termino_lower]


def _aplicar_ingredientes_excluidos(qs, ingredientes_texto):
    if not ingredientes_texto:
        return qs
    ingredientes_es = [
        i.strip().lower()
        for i in ingredientes_texto.split(",")
        if i.strip()
    ]
    for ingrediente_es in ingredientes_es:
        terminos_en = _traducir_ingrediente_a_ingles(ingrediente_es)
        for termino_en in terminos_en:
            qs = qs.exclude(ingredientes_json__icontains=termino_en)
        qs = qs.exclude(ingredientes_json__icontains=ingrediente_es)
    return qs


def _qs_base():
    return (
        RecetaMealDB.objects
        .filter(clasificado=True, clasificacion__isnull=False)
        .select_related("clasificacion")
    )


def _aplicar_restricciones(qs, restricciones):
    for r in restricciones:
        if r in RESTRICCION_KEYS:
            qs = qs.exclude(**{f"clasificacion__{r}": True})
    return qs


def _aplicar_condicion_dieta(qs, condiciones):
    """
    ✅ Acepta lista de condiciones (o string legado) y aplica filtros vegetariano/vegano.
    """
    CARNES = ["Beef", "Chicken", "Lamb", "Pork", "Seafood"]
    # Normalizar: acepta string legado o lista
    if isinstance(condiciones, str):
        condiciones = [condiciones] if condiciones else []

    for condicion in condiciones:
        c = condicion.lower().strip()
        if c == "vegano":
            qs = qs.exclude(categoria__in=CARNES)
            qs = qs.exclude(clasificacion__intolerancia_lactosa=True)
            qs = qs.exclude(clasificacion__alergia_huevo=True)
        elif c == "vegetariano":
            qs = qs.exclude(categoria__in=CARNES)
    return qs


def _receta_a_dict(r):
    clasif = getattr(r, "clasificacion", None)
    return {
        "id":              r.id,
        "meal_id":         r.meal_id,
        "nombre":          r.nombre_es or r.nombre,
        "nombre_original": r.nombre,
        "categoria":       r.categoria or "",
        "area":            r.area or "",
        "imagen_url":      r.imagen_url or "",
        "youtube_url":     r.youtube_url or "",
        "instrucciones":   r.instrucciones_raw or "",
        "ingredientes":    r.ingredientes_json or [],
        "calorias":        round(r.calorias_estimadas) if r.calorias_estimadas else None,
        "proteinas_g":     round(r.proteinas_g, 1) if r.proteinas_g else None,
        "carbohidratos_g": round(r.carbohidratos_g, 1) if r.carbohidratos_g else None,
        "grasas_g":        round(r.grasas_g, 1) if r.grasas_g else None,
        "fibra_g":         round(r.fibra_g, 1) if r.fibra_g else None,
        "sodio_mg":        round(r.sodio_mg) if r.sodio_mg else None,
        "dificultad":      clasif.dificultad if clasif else None,
        "tiempo_min":      clasif.tiempo_prep_min if clasif else None,
        "incompatible_con": clasif.restricciones_incompatibles() if clasif else [],
    }


def _shuffle_qs(qs, n=24):
    ids = list(qs.values_list("id", flat=True))
    random.shuffle(ids)
    return list(
        RecetaMealDB.objects.filter(id__in=ids[:n]).select_related("clasificacion")
    )


# ──────────────────────────────────────────────────────────────────────────────
# GENERADOR DE DIETA
# ──────────────────────────────────────────────────────────────────────────────

@verificar_formulario_completo
@login_required
def generador_dieta(request):
    usuario = request.user
    dieta = DietaGenerada.objects.filter(usuario=usuario).order_by("-creado_en").first()

    if not dieta:
        return render(request, "Apispoonacular/dieta_generada.html", {
            "error": "Primero debes completar el formulario nutricional"
        })

    formulario             = dieta.formulario
    condiciones_dieta      = _parsear_condiciones_dieta(formulario)
    ingredientes_excluidos = getattr(formulario, 'ingredientes_excluidos', '') or ''
    restricciones          = _parsear_restricciones_combinadas(formulario)
    objetivo               = dieta.objetivo
    distribucion           = dieta.distribucion_macros_comidas or {}

    datos_dieta = {
        "calorias_diarias":     dieta.calorias_diarias or 0,
        "proteinas_gramos":     dieta.proteinas_gramos or 0,
        "grasas_gramos":        dieta.grasas_gramos or 0,
        "carbohidratos_gramos": dieta.carbohidratos_gramos or 0,
    }

    recetas_por_comida = {}

    if distribucion:
        for nombre_comida, macros in distribucion.items():
            cals  = macros.get("calorias", 0)
            prots = macros.get("proteinas_g", 0)

            qs = _qs_base()
            qs = _aplicar_restricciones(qs, restricciones)
            qs = _aplicar_condicion_dieta(qs, condiciones_dieta)
            qs = _aplicar_ingredientes_excluidos(qs, ingredientes_excluidos)

            if cals:
                qs = qs.filter(
                    calorias_estimadas__gte=cals * 0.60,
                    calorias_estimadas__lte=cals * 1.40,
                )
            if prots and prots > 5:
                qs = qs.filter(
                    proteinas_g__gte=prots * 0.55,
                    proteinas_g__lte=prots * 1.45,
                )

            recetas_qs = _shuffle_qs(qs, 6)

            if not recetas_qs:
                qs2 = _qs_base()
                qs2 = _aplicar_restricciones(qs2, restricciones)
                qs2 = _aplicar_condicion_dieta(qs2, condiciones_dieta)
                qs2 = _aplicar_ingredientes_excluidos(qs2, ingredientes_excluidos)
                recetas_qs = _shuffle_qs(qs2, 6)

            recetas_por_comida[nombre_comida] = {
                "macros":  macros,
                "recetas": [_receta_a_dict(r) for r in recetas_qs],
            }
    else:
        cals_c = datos_dieta["calorias_diarias"] / 3
        prot_c = datos_dieta["proteinas_gramos"] / 3

        qs = _qs_base()
        qs = _aplicar_restricciones(qs, restricciones)
        qs = _aplicar_condicion_dieta(qs, condiciones_dieta)
        qs = _aplicar_ingredientes_excluidos(qs, ingredientes_excluidos)

        if cals_c:
            qs = qs.filter(
                calorias_estimadas__gte=cals_c * 0.60,
                calorias_estimadas__lte=cals_c * 1.40,
            )

        recetas_por_comida["Recetas recomendadas"] = {
            "macros": {"calorias": round(cals_c), "proteinas_g": round(prot_c)},
            "recetas": [_receta_a_dict(r) for r in _shuffle_qs(qs, 12)],
        }

    favoritos_ids = list(
        RecetaFavorita.objects.filter(usuario=request.user).values_list("recipe_id", flat=True)
    )

    from applications.recetas.models import RESTRICCIONES as RESTRICCIONES_LIST
    restricciones_labels = dict(RESTRICCIONES_LIST)
    restricciones_con_labels = [
        {"key": r, "label": restricciones_labels.get(r, r.replace("_", " ").capitalize())}
        for r in restricciones
    ]

    CONDICION_LABELS = {
        "diabetes": "Diabetes", "celiaco": "Celiaco / Sin gluten",
        "lactosa": "Intolerancia a la lactosa", "hipertension": "Hipertensión",
        "colesterol": "Colesterol alto", "dislipidemia": "Dislipidemias",
        "indigestion": "Indigestión / Gastritis", "hipertiroidismo": "Hipertiroidismo",
        "anemia": "Anemia ferropénica", "gota": "Gota",
        "alergia_mani": "Alergia al maní", "alergia_mariscos": "Alergia a mariscos",
        "alergia_huevo": "Alergia al huevo", "vegetariano": "Vegetariano", "vegano": "Vegano",
    }
    condiciones_con_labels = [
        {"key": c, "label": CONDICION_LABELS.get(c, c.replace("_", " ").capitalize())}
        for c in condiciones_dieta
    ]

    return render(request, "Apispoonacular/dieta_generada.html", {
        "datos_dieta":              datos_dieta,
        "dieta":                    dieta,
        "formulario":               formulario,
        "distribucion":             distribucion,
        "recetas_por_comida":       recetas_por_comida,
        "objetivo":                 objetivo,
        "restricciones_aplicadas":  restricciones,
        "restricciones_con_labels": restricciones_con_labels,
        "condiciones_medicas":      condiciones_dieta,
        "condiciones_con_labels":   condiciones_con_labels,
        "favoritos_ids":            favoritos_ids,
    })


# ──────────────────────────────────────────────────────────────────────────────
# EXPLORAR RECETAS
# ──────────────────────────────────────────────────────────────────────────────

@never_cache
@login_required
@verificar_formulario_completo
def explorar_recetas(request):
    formulario = FormularioNutricionGuardado.objects.filter(
        usuario=request.user
    ).last()

    restricciones          = _parsear_restricciones_combinadas(formulario) if formulario else []
    condiciones_dieta      = _parsear_condiciones_dieta(formulario) if formulario else []
    ingredientes_excluidos = (getattr(formulario, 'ingredientes_excluidos', '') or '') if formulario else ''

    busqueda  = request.GET.get("q", "").strip()
    categoria = request.GET.get("categoria")
    if not categoria or categoria == "None":
        categoria = None
    ordenar = request.GET.get("ordenar", "random")

    qs = _qs_base()
    qs = _aplicar_restricciones(qs, restricciones)
    qs = _aplicar_condicion_dieta(qs, condiciones_dieta)
    qs = _aplicar_ingredientes_excluidos(qs, ingredientes_excluidos)

    if busqueda:
        qs = qs.filter(
            Q(nombre__icontains=busqueda) |
            Q(nombre_es__icontains=busqueda) |
            Q(categoria__icontains=busqueda) |
            Q(area__icontains=busqueda)
        )

    if categoria:
        qs = qs.filter(categoria__iexact=categoria)

    orden_map = {
        "nombre":    "nombre_es",
        "calorias":  "calorias_estimadas",
        "proteinas": "-proteinas_g",
        "tiempo":    "clasificacion__tiempo_prep_min",
    }

    total = qs.count()

    if ordenar in orden_map:
        qs = qs.order_by(orden_map[ordenar])
        paginator   = Paginator(qs, 8)
        page_number = request.GET.get("page")
        page_obj    = paginator.get_page(page_number)
        recetas     = [_receta_a_dict(r) for r in page_obj]
    else:
        import random as _random
        ids = list(qs.values_list("id", flat=True))
        _random.shuffle(ids)
        paginator   = Paginator(ids, 8)
        page_number = request.GET.get("page")
        page_obj    = paginator.get_page(page_number)
        page_ids    = list(page_obj)
        recetas_qs  = list(
            RecetaMealDB.objects.filter(id__in=page_ids).select_related("clasificacion")
        )
        id_order = {id_: i for i, id_ in enumerate(page_ids)}
        recetas_qs.sort(key=lambda r: id_order.get(r.id, 999))
        recetas = [_receta_a_dict(r) for r in recetas_qs]

    categorias_disponibles = (
        RecetaMealDB.objects.filter(clasificado=True)
        .values_list("categoria", flat=True).distinct().order_by("categoria")
    )

    categorias_traducidas = [
        {
            "original": cat,
            "nombre": TRADUCCIONES_CATEGORIAS.get(cat, cat)
        }
        for cat in categorias_disponibles if cat
    ]

    favoritos_qs  = RecetaFavorita.objects.filter(usuario=request.user).order_by("-creado_en")
    favoritos_ids = set(f.recipe_id for f in favoritos_qs)

    from applications.recetas.models import RESTRICCIONES as RESTRICCIONES_LIST
    restricciones_labels = dict(RESTRICCIONES_LIST)
    restricciones_con_labels = [
        {"key": r, "label": restricciones_labels.get(r, r.replace("_", " ").capitalize())}
        for r in restricciones
    ]

    CONDICION_LABELS = {
        "diabetes": "Diabetes", "celiaco": "Celiaco / Sin gluten",
        "lactosa": "Intolerancia a la lactosa", "hipertension": "Hipertensión",
        "colesterol": "Colesterol alto", "dislipidemia": "Dislipidemias",
        "indigestion": "Indigestión / Gastritis", "hipertiroidismo": "Hipertiroidismo",
        "anemia": "Anemia ferropénica", "gota": "Gota",
        "alergia_mani": "Alergia al maní", "alergia_mariscos": "Alergia a mariscos",
        "alergia_huevo": "Alergia al huevo", "vegetariano": "Vegetariano", "vegano": "Vegano",
    }
    condiciones_con_labels = [
        {"key": c, "label": CONDICION_LABELS.get(c, c.replace("_", " ").capitalize())}
        for c in condiciones_dieta
    ]

    return render(request, "Apispoonacular/explorar_recetas.html", {
        "recetas":                  recetas,
        "total_recetas":            total,
        "page_obj":                 page_obj,
        "query":                    busqueda,
        "categoria":                categoria,
        "ordenar":                  ordenar,
        "restricciones_aplicadas":  restricciones,
        "restricciones_con_labels": restricciones_con_labels,
        "condiciones_medicas":      condiciones_dieta,
        "condiciones_con_labels":   condiciones_con_labels,
        "categorias_disponibles": categorias_traducidas,
        "total_bd":                 RecetaMealDB.objects.filter(clasificado=True).count(),
        "favoritos_ids":            list(favoritos_ids),
        "favoritos":                list(favoritos_qs),
    })


# ──────────────────────────────────────────────────────────────────────────────
# DETALLE
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def receta_detalle(request, recipe_id):
    try:
        r = RecetaMealDB.objects.select_related("clasificacion").get(id=recipe_id)
        receta = _receta_a_dict(r)
    except RecetaMealDB.DoesNotExist:
        receta = None

    es_favorita = RecetaFavorita.objects.filter(
        usuario=request.user, recipe_id=recipe_id
    ).exists() if receta else False

    return render(request, "Apispoonacular/receta_detalle.html", {
        "receta":     receta,
        "es_favorita": es_favorita,
    })


@login_required
def receta_info_json(request, recipe_id):
    try:
        r = RecetaMealDB.objects.select_related("clasificacion").get(id=recipe_id)
        return JsonResponse(_receta_a_dict(r))
    except RecetaMealDB.DoesNotExist:
        return JsonResponse({"error": "Receta no encontrada"}, status=404)


# ──────────────────────────────────────────────────────────────────────────────
# FAVORITOS
# ──────────────────────────────────────────────────────────────────────────────

# ✅ FIX: eliminado @csrf_exempt y agregado @login_required explícito
# El frontend ya envía X-CSRFToken (igual que el calendario)
@login_required
@require_POST
def toggle_favorito(request):
    try:
        data      = json.loads(request.body)
        recipe_id = int(data.get("recipe_id"))
        titulo    = data.get("titulo", "")[:200]   # ✅ limitar longitud
        imagen    = data.get("imagen", "")[:500]   # ✅ limitar longitud

        favorito = RecetaFavorita.objects.filter(
            usuario=request.user, recipe_id=recipe_id
        ).first()

        if favorito:
            favorito.delete()
            return JsonResponse({"ok": True, "favorito": False})

        RecetaFavorita.objects.create(
            usuario=request.user, recipe_id=recipe_id,
            titulo=titulo, imagen=imagen,
        )
        return JsonResponse({"ok": True, "favorito": True})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)


@never_cache
@login_required
@verificar_formulario_completo
def calendario_view(request):
    return render(request, "explorar_recetas.html")


@never_cache
@login_required
def recetas_favoritas(request):
    favoritos = RecetaFavorita.objects.filter(usuario=request.user).order_by("-creado_en")
    return render(request, "Apispoonacular/recetas_favoritas.html", {
        "favoritos": favoritos,
    })


@login_required
@require_POST
def eliminar_favorito(request, recipe_id):
    RecetaFavorita.objects.filter(usuario=request.user, recipe_id=recipe_id).delete()
    return redirect("recetas_favoritas")


# ──────────────────────────────────────────────────────────────────────────────
# TRADUCIR INSTRUCCIONES
# ──────────────────────────────────────────────────────────────────────────────

# ✅ FIX CRÍTICO: esta función estaba completamente abierta sin autenticación.
# Cualquiera podía usarla para traducción masiva gratuita.
# Ahora requiere login y método POST con CSRF.
@login_required
@require_POST
def traducir_instrucciones(request):
    try:
        data  = json.loads(request.body)
        texto = data.get('texto', '').strip()
        if not texto:
            return JsonResponse({'ok': False, 'error': 'Sin texto'}, status=400)

        # ✅ FIX: limitar tamaño del texto a traducir (evita abuso)
        if len(texto) > 5000:
            return JsonResponse({'ok': False, 'error': 'Texto demasiado largo'}, status=400)

        from .api_services import _traducir
        lineas     = [l.strip() for l in texto.split('\n') if l.strip()]

        # ✅ FIX: limitar número de líneas a traducir
        if len(lineas) > 50:
            lineas = lineas[:50]

        traducidas = [_traducir(linea, src='en', tgt='es') for linea in lineas]

        return JsonResponse({'ok': True, 'traduccion': '\n'.join(traducidas)})
    
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=500)

# ──────────────────────────────────────────────────────────────────────────────
# TRADUCIR INGREDIENTES (batch)
# ──────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def traducir_ingredientes(request):
    """
    Recibe una lista de ingredientes [{medida, ingrediente}, ...]
    y devuelve la misma lista con los textos traducidos al español.
    """
    try:
        data = json.loads(request.body)
        ingredientes = data.get('ingredientes', [])

        if not isinstance(ingredientes, list) or len(ingredientes) > 60:
            return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)

        from .api_services import _traducir

        traducidos = []
        for item in ingredientes:
            medida     = (item.get('medida') or '').strip()
            ingrediente = (item.get('ingrediente') or '').strip()
            traducidos.append({
                'medida':      _traducir(medida, src='en', tgt='es') if medida else '',
                'ingrediente': _traducir(ingrediente, src='en', tgt='es') if ingrediente else '',
            })

        return JsonResponse({'ok': True, 'ingredientes': traducidos})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)