import random
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from Nutriet.utils import verificar_formulario_completo
from applications.nutricion.models import DietaGenerada, FormularioNutricionGuardado
from applications.recetas.models import RecetaMealDB, ClasificacionReceta, RESTRICCION_KEYS
import json
from .models import RecetaFavorita
from django.core.paginator import Paginator

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

CATEGORIAS_ES = {
    "Beef":          "Res",
    "Breakfast":     "Desayuno",
    "Chicken":       "Pollo",
    "Dessert":       "Postre",
    "Goat":          "Cabra",
    "Lamb":          "Cordero",
    "Miscellaneous": "Variado",
    "Pasta":         "Pasta",
    "Pork":          "Cerdo",
    "Seafood":       "Mariscos",
    "Side":          "Acompañamiento",
    "Starter":       "Entrada",
    "Vegan":         "Vegano",
    "Vegetarian":    "Vegetariano",
    "Turkey":        "Pavo",
    "Unknown":       "Desconocido",
}

TEXTO_A_RESTRICCION = {
    "diabetes": "diabetes", "diabete": "diabetes",
    "lactosa": "intolerancia_lactosa", "lácteo": "intolerancia_lactosa",
    "lacteo": "intolerancia_lactosa",
    "celiaca": "celiaca", "celíaca": "celiaca", "celiaco": "celiaca",
    "celíaco": "celiaca", "gluten": "celiaca",
    "maní": "alergia_mani", "mani": "alergia_mani", "cacahuate": "alergia_mani",
    "fructosa": "intolerancia_fructosa",
    "hipertension": "hipertension", "hipertensión": "hipertension",
    "colesterol": "hipercolesterolemia",
    "huevo": "alergia_huevo",
    "marisco": "alergia_marisco", "mariscos": "alergia_marisco",
}


def _parsear_restricciones(texto):
    if not texto:
        return []
    t = texto.lower()
    encontradas = set()
    for palabra, clave in TEXTO_A_RESTRICCION.items():
        if palabra in t:
            encontradas.add(clave)
    return list(encontradas)


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


def _aplicar_tipo_dieta(qs, tipo_dieta):
    CARNES = ["Beef", "Chicken", "Lamb", "Pork", "Seafood"]
    if tipo_dieta == "vegetariano":
        qs = qs.exclude(categoria__in=CARNES)
    elif tipo_dieta == "vegano":
        qs = qs.exclude(categoria__in=CARNES)
        qs = qs.exclude(clasificacion__intolerancia_lactosa=True)
        qs = qs.exclude(clasificacion__alergia_huevo=True)
    elif tipo_dieta == "keto":
        qs = qs.filter(carbohidratos_g__isnull=False, carbohidratos_g__lte=20)
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
@never_cache
@login_required
def generador_dieta(request):
    usuario = request.user
    dieta = DietaGenerada.objects.filter(usuario=usuario).order_by("-creado_en").first()

    if not dieta:
        return render(request, "Apispoonacular/dieta_generada.html", {
            "error": "Primero debes completar el formulario nutricional"
        })

    formulario    = dieta.formulario
    tipo_dieta    = formulario.condicion_medica or ""
    restricciones = _parsear_restricciones(formulario.condicion_medica or "")
    objetivo      = dieta.objetivo
    distribucion  = dieta.distribucion_macros_comidas or {}

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
            qs = _aplicar_tipo_dieta(qs, tipo_dieta)

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

            # Si sin resultados, fallback sin rango calórico
            if not recetas_qs:
                qs2 = _qs_base()
                qs2 = _aplicar_restricciones(qs2, restricciones)
                qs2 = _aplicar_tipo_dieta(qs2, tipo_dieta)
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
        qs = _aplicar_tipo_dieta(qs, tipo_dieta)

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

    return render(request, "Apispoonacular/dieta_generada.html", {
        "datos_dieta":             datos_dieta,
        "dieta":                   dieta,
        "formulario":              formulario,
        "distribucion":            distribucion,
        "recetas_por_comida":      recetas_por_comida,
        "objetivo":                objetivo,
        "restricciones_aplicadas": restricciones,
        "favoritos_ids":           favoritos_ids,
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

    restricciones = _parsear_restricciones(
        formulario.ingredientes_excluidos or "" if formulario else ""
    )
    tipo_dieta = formulario.tipo_dieta if formulario else "normal"

    busqueda  = request.GET.get("q", "").strip()
    categoria = request.GET.get("categoria")
    if not categoria or categoria == "None":
        categoria = None
    ordenar   = request.GET.get("ordenar", "random")

    qs = _qs_base()
    qs = _aplicar_restricciones(qs, restricciones)
    qs = _aplicar_tipo_dieta(qs, tipo_dieta)

    print("TOTAL FINAL:", qs.count())

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

    # Aplicar orden
    if ordenar in orden_map:
        qs = qs.order_by(orden_map[ordenar])
    else:
        qs = _shuffle_qs(qs, total)  # barajar todo

    # PAGINACIÓN
    paginator = Paginator(qs, 8)  #8 recetas por página
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Convertimos SOLO las recetas de la página actual
    recetas = [_receta_a_dict(r) for r in page_obj]

    _cats_raw = (
        RecetaMealDB.objects.filter(clasificado=True)
        .values_list("categoria", flat=True).distinct().order_by("categoria")
    )
    categorias_disponibles = [
        {"valor": c, "etiqueta": CATEGORIAS_ES.get(c, c)}
        for c in _cats_raw if c
    ]

    from .models import RecetaFavorita
    favoritos_qs = RecetaFavorita.objects.filter(usuario=request.user).order_by("-creado_en")
    favoritos_ids = set(f.recipe_id for f in favoritos_qs)

    return render(request, "Apispoonacular/explorar_recetas.html", {
        "recetas":                 recetas,
        "page_obj":                page_obj,
        "total_recetas":           total,
        "query":                   busqueda,
        "categoria":               categoria,
        "ordenar":                 ordenar,
        "restricciones_aplicadas": restricciones,
        "categorias_disponibles":  list(categorias_disponibles),
        "total_bd":                RecetaMealDB.objects.filter(clasificado=True).count(),
        "favoritos_ids":           list(favoritos_ids),
        "favoritos":               list(favoritos_qs),
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

    from .models import RecetaFavorita
    es_favorita = RecetaFavorita.objects.filter(
        usuario=request.user, recipe_id=recipe_id
    ).exists() if receta else False

    return render(request, "Apispoonacular/receta_detalle.html", {
        "receta": receta,
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

@csrf_exempt
@require_POST
def toggle_favorito(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "no autenticado"}, status=401)
    try:
        from .models import RecetaFavorita
        data      = json.loads(request.body)
        recipe_id = int(data.get("recipe_id"))
        titulo    = data.get("titulo", "")
        imagen    = data.get("imagen", "")

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


@csrf_exempt
def traducir_instrucciones(request):
    """Traduce instrucciones de cocina EN→ES usando deep_translator (GoogleTranslator)."""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    try:
        data = json.loads(request.body)
        texto = data.get('texto', '').strip()
        if not texto:
            return JsonResponse({'ok': False, 'error': 'Sin texto'}, status=400)

        from .api_services import _traducir
        # Traducir párrafo por párrafo para respetar el límite de GoogleTranslator
        lineas = [l.strip() for l in texto.split('\n') if l.strip()]
        traducidas = []
        for linea in lineas:
            traducidas.append(_traducir(linea, src='en', tgt='es'))

        return JsonResponse({'ok': True, 'traduccion': '\n'.join(traducidas)})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)