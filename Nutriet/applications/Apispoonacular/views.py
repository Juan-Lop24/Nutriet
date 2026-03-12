import random
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.core.paginator import Paginator
from Nutriet.utils import verificar_formulario_completo
from applications.nutricion.models import DietaGenerada, FormularioNutricionGuardado
from applications.recetas.models import RecetaMealDB, ClasificacionReceta, RESTRICCION_KEYS
import json
from .models import RecetaFavorita


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
    "colesterol": "hipercolesterolemia",
    "huevo": "alergia_huevo",
    "marisco": "alergia_marisco", "mariscos": "alergia_marisco",
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
}


def _parsear_restricciones_combinadas(formulario):
    """
    Combina restricciones médicas (condicion_medica) para aplicar los filtros
    booleanos de ClasificacionReceta.
    """
    restricciones = set()
    condicion = getattr(formulario, 'condicion_medica', '') or ''
    if condicion in CONDICION_A_RESTRICCION:
        restricciones.add(CONDICION_A_RESTRICCION[condicion])
    return list(restricciones)


def _traducir_ingrediente_a_ingles(termino: str) -> list:
    """
    Dado un ingrediente en español, devuelve una lista de términos en inglés
    para buscar en la base de datos (que usa nombres en inglés de TheMealDB).
    Usa un diccionario de palabras comunes y, si no está, recurre a GoogleTranslator.
    Retorna lista para cubrir variaciones (ej: "rice" puede aparecer como "rice" o "white rice").
    """
    DICCIONARIO_ES_EN = {
        "arroz": ["rice"],
        "pollo": ["chicken"],
        "carne": ["beef", "meat"],
        "cerdo": ["pork"],
        "cordero": ["lamb"],
        "pescado": ["fish", "salmon", "tuna", "cod"],
        "atún": ["tuna"], "atun": ["tuna"],
        "salmón": ["salmon"], "salmon": ["salmon"],
        "camarones": ["shrimp", "prawn"], "camarón": ["shrimp", "prawn"],
        "mariscos": ["seafood", "shrimp", "prawn", "crab", "lobster"],
        "huevo": ["egg"],
        "leche": ["milk"],
        "queso": ["cheese"],
        "mantequilla": ["butter"],
        "crema": ["cream"],
        "harina": ["flour"],
        "azúcar": ["sugar"], "azucar": ["sugar"],
        "sal": ["salt"],
        "aceite": ["oil"],
        "cebolla": ["onion"],
        "ajo": ["garlic"],
        "tomate": ["tomato"],
        "papa": ["potato"], "patata": ["potato"],
        "zanahoria": ["carrot"],
        "lechuga": ["lettuce"],
        "espinaca": ["spinach"],
        "brócoli": ["broccoli"], "brocoli": ["broccoli"],
        "maíz": ["corn"], "maiz": ["corn"],
        "frijoles": ["beans"], "frijol": ["beans"],
        "lentejas": ["lentils"],
        "garbanzos": ["chickpeas"],
        "pasta": ["pasta", "spaghetti", "noodles"],
        "pan": ["bread"],
        "trigo": ["wheat"],
        "gluten": ["gluten", "wheat", "flour"],
        "maní": ["peanut"], "mani": ["peanut"], "cacahuate": ["peanut"],
        "nuez": ["walnut", "nut"], "nueces": ["walnut", "nut"],
        "almendra": ["almond"],
        "chocolate": ["chocolate"],
        "limón": ["lemon"], "limon": ["lemon"],
        "naranja": ["orange"],
        "manzana": ["apple"],
        "plátano": ["banana"], "platano": ["banana"],
        "piña": ["pineapple"], "pina": ["pineapple"],
        "fresa": ["strawberry"], "fresas": ["strawberry"],
        "uva": ["grape"],
        "pimiento": ["pepper", "bell pepper"],
        "chile": ["chili", "chile"],
        "cilantro": ["cilantro", "coriander"],
        "perejil": ["parsley"],
        "comino": ["cumin"],
        "pimienta": ["pepper", "black pepper"],
        "canela": ["cinnamon"],
        "vainilla": ["vanilla"],
        "vinagre": ["vinegar"],
        "salsa": ["sauce", "salsa"],
        "mostaza": ["mustard"],
        "mayonesa": ["mayonnaise"],
        "ketchup": ["ketchup"],
        "soya": ["soy", "soya"], "soja": ["soy", "soya"],
        "tocino": ["bacon"],
        "jamón": ["ham"], "jamon": ["ham"],
        "salchicha": ["sausage"],
        "pavo": ["turkey"],
        "pato": ["duck"],
        "conejo": ["rabbit"],
    }

    termino_lower = termino.strip().lower()

    # Buscar en diccionario directo
    if termino_lower in DICCIONARIO_ES_EN:
        return DICCIONARIO_ES_EN[termino_lower]

    # Buscar coincidencia parcial en el diccionario
    for es, en_list in DICCIONARIO_ES_EN.items():
        if es in termino_lower or termino_lower in es:
            return en_list

    # Fallback: traducir con GoogleTranslator
    try:
        from .api_services import _traducir
        traducido = _traducir(termino, src="es", tgt="en")
        if traducido and traducido.lower() != termino_lower:
            return [traducido.lower()]
    except Exception:
        pass

    # Si no se pudo traducir, usar el término original también
    return [termino_lower]


def _aplicar_ingredientes_excluidos(qs, ingredientes_texto):
    """
    Excluye recetas que contengan cualquier ingrediente escrito por el usuario.
    Traduce los ingredientes del español al inglés antes de buscar,
    ya que la base de datos (TheMealDB) almacena los ingredientes en inglés.
    Ej: "arroz, pollo" → traduce a ["rice"], ["chicken"] y excluye recetas con esos términos.
    """
    if not ingredientes_texto:
        return qs
    ingredientes_es = [
        i.strip().lower()
        for i in ingredientes_texto.split(",")
        if i.strip()
    ]
    for ingrediente_es in ingredientes_es:
        # Obtener los términos equivalentes en inglés
        terminos_en = _traducir_ingrediente_a_ingles(ingrediente_es)
        for termino_en in terminos_en:
            qs = qs.exclude(ingredientes_json__icontains=termino_en)
        # También excluir por el término original en español (por si acaso)
        qs = qs.exclude(ingredientes_json__icontains=ingrediente_es)
    return qs


def _detectar_ingredientes_no_reconocidos(ingredientes_texto):
    """
    Dado el texto de ingredientes excluidos (separados por coma), devuelve
    una lista con los ingredientes que NO pudieron reconocerse: es decir,
    aquellos que no están en el diccionario interno Y cuya traducción tampoco
    aparece en ningún ingrediente almacenado en la base de datos.

    Esta función es SOLO informativa: no bloquea ni altera ningún queryset.
    Se usa en las vistas para mostrar un mensaje de advertencia al usuario.
    """
    if not ingredientes_texto:
        return []

    no_reconocidos = []

    ingredientes_es = [
        i.strip().lower()
        for i in ingredientes_texto.split(",")
        if i.strip()
    ]

    for ingrediente_es in ingredientes_es:
        terminos_en = _traducir_ingrediente_a_ingles(ingrediente_es)

        # Si el único resultado es el propio término sin traducción exitosa,
        # verificamos si al menos una receta en la BD lo contiene
        encontrado = False
        todos_los_terminos = terminos_en + [ingrediente_es]
        for termino in todos_los_terminos:
            if RecetaMealDB.objects.filter(
                ingredientes_json__icontains=termino
            ).exists():
                encontrado = True
                break

        if not encontrado:
            no_reconocidos.append(ingrediente_es)

    return no_reconocidos


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


def _aplicar_condicion_dieta(qs, condicion_medica):
    CARNES = ["Beef", "Chicken", "Lamb", "Pork", "Seafood"]
    if condicion_medica == "vegetariano":
        qs = qs.exclude(categoria__in=CARNES)
    elif condicion_medica == "vegano":
        qs = qs.exclude(categoria__in=CARNES)
        qs = qs.exclude(clasificacion__intolerancia_lactosa=True)
        qs = qs.exclude(clasificacion__alergia_huevo=True)
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

    formulario       = dieta.formulario
    condicion_medica = getattr(formulario, 'condicion_medica', '') or ''
    ingredientes_excluidos = getattr(formulario, 'ingredientes_excluidos', '') or ''
    restricciones    = _parsear_restricciones_combinadas(formulario)
    objetivo         = dieta.objetivo
    distribucion     = dieta.distribucion_macros_comidas or {}

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
            qs = _aplicar_condicion_dieta(qs, condicion_medica)
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

            # Fallback sin rango calórico
            if not recetas_qs:
                qs2 = _qs_base()
                qs2 = _aplicar_restricciones(qs2, restricciones)
                qs2 = _aplicar_condicion_dieta(qs2, condicion_medica)
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
        qs = _aplicar_condicion_dieta(qs, condicion_medica)
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

    # ── Advertencia de ingredientes no reconocidos ──────────────────────────
    no_reconocidos = _detectar_ingredientes_no_reconocidos(ingredientes_excluidos)
    if no_reconocidos:
        from django.contrib import messages
        lista = ", ".join(no_reconocidos)
        messages.warning(
            request,
            f"No tenemos registrado(s) el/los siguiente(s) alimento(s): «{lista}». "
            f"Los demás ingredientes sí fueron aplicados correctamente."
        )
    # ────────────────────────────────────────────────────────────────────────

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

    restricciones          = _parsear_restricciones_combinadas(formulario) if formulario else []
    condicion_medica       = (getattr(formulario, 'condicion_medica', '') or '') if formulario else ''
    ingredientes_excluidos = (getattr(formulario, 'ingredientes_excluidos', '') or '') if formulario else ''

    busqueda  = request.GET.get("q", "").strip()
    categoria = request.GET.get("categoria")
    if not categoria or categoria == "None":
        categoria = None
    ordenar   = request.GET.get("ordenar", "random")

    qs = _qs_base()
    qs = _aplicar_restricciones(qs, restricciones)
    qs = _aplicar_condicion_dieta(qs, condicion_medica)
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
        paginator = Paginator(qs, 8)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        recetas = [_receta_a_dict(r) for r in page_obj]
    else:
        # Para random: paginamos sobre los IDs shuffleados
        import random as _random
        ids = list(qs.values_list("id", flat=True))
        _random.shuffle(ids)
        paginator = Paginator(ids, 8)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        page_ids = list(page_obj)
        recetas_qs = list(
            RecetaMealDB.objects.filter(id__in=page_ids).select_related("clasificacion")
        )
        # Preserve shuffle order
        id_order = {id_: i for i, id_ in enumerate(page_ids)}
        recetas_qs.sort(key=lambda r: id_order.get(r.id, 999))
        recetas = [_receta_a_dict(r) for r in recetas_qs]

    categorias_disponibles = (
        RecetaMealDB.objects.filter(clasificado=True)
        .values_list("categoria", flat=True).distinct().order_by("categoria")
    )

    from .models import RecetaFavorita
    favoritos_qs  = RecetaFavorita.objects.filter(usuario=request.user).order_by("-creado_en")
    favoritos_ids = set(f.recipe_id for f in favoritos_qs)

    # ── Advertencia de ingredientes no reconocidos ──────────────────────────
    no_reconocidos = _detectar_ingredientes_no_reconocidos(ingredientes_excluidos)
    if no_reconocidos:
        from django.contrib import messages
        lista = ", ".join(no_reconocidos)
        messages.warning(
            request,
            f"No tenemos registrado(s) el/los siguiente(s) alimento(s): «{lista}». "
            f"Los demás ingredientes sí fueron aplicados correctamente."
        )
    # ────────────────────────────────────────────────────────────────────────

    return render(request, "Apispoonacular/explorar_recetas.html", {
        "recetas":                 recetas,
        "total_recetas":           total,
        "page_obj":                page_obj,
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
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    try:
        data  = json.loads(request.body)
        texto = data.get('texto', '').strip()
        if not texto:
            return JsonResponse({'ok': False, 'error': 'Sin texto'}, status=400)

        from .api_services import _traducir
        lineas     = [l.strip() for l in texto.split('\n') if l.strip()]
        traducidas = [_traducir(linea, src='en', tgt='es') for linea in lineas]

        return JsonResponse({'ok': True, 'traduccion': '\n'.join(traducidas)})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)