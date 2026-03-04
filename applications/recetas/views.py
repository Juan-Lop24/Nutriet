# applications/recetas/views.py
"""
Vistas para el módulo de recetas MealDB.

Endpoints:
  /recetas/                    → explorador de recetas para el usuario
  /recetas/api/para-usuario/   → JSON de recetas filtradas por perfil
  /recetas/api/detalle/<id>/   → JSON con detalle de una receta
  /recetas/api/stats/          → estadísticas de la BD (para admin/debug)
"""

import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Q

from Nutriet.utils import verificar_formulario_completo
from applications.nutricion.models import FormularioNutricionGuardado
from .models import RecetaMealDB, ClasificacionReceta, RESTRICCIONES


# ── Mapa de texto libre → clave interna de restricción ───────────────────────
# Se usa para parsear el campo restricciones_alimentarias del formulario
TEXTO_A_RESTRICCION = {
    "diabetes":           "diabetes",
    "diabete":            "diabetes",
    "lactosa":            "intolerancia_lactosa",
    "lácteo":             "intolerancia_lactosa",
    "lacteo":             "intolerancia_lactosa",
    "celiaca":            "celiaca",
    "celíaca":            "celiaca",
    "celiaco":            "celiaca",
    "celíaco":            "celiaca",
    "gluten":             "celiaca",
    "maní":               "alergia_mani",
    "mani":               "alergia_mani",
    "cacahuate":          "alergia_mani",
    "fructosa":           "intolerancia_fructosa",
    "hipertension":       "hipertension",
    "hipertensión":       "hipertension",
    "presion alta":       "hipertension",
    "presión alta":       "hipertension",
    "colesterol":         "hipercolesterolemia",
    "hipercolesterol":    "hipercolesterolemia",
    "huevo":              "alergia_huevo",
    "marisco":            "alergia_marisco",
    "mariscos":           "alergia_marisco",
    "crustaceo":          "alergia_marisco",
    "crustáceo":          "alergia_marisco",
    "camaron":            "alergia_marisco",
    "camarón":            "alergia_marisco",
}


def _parsear_restricciones_usuario(texto: str) -> list[str]:
    """
    Convierte el texto libre de restricciones del formulario
    en lista de claves internas. Ej: "tengo diabetes y soy celíaco"
    → ["diabetes", "celiaca"]
    """
    if not texto:
        return []
    texto_lower = texto.lower()
    encontradas = set()
    for palabra, clave in TEXTO_A_RESTRICCION.items():
        if palabra in texto_lower:
            encontradas.add(clave)
    return list(encontradas)


def _filtrar_recetas_por_perfil(formulario, limit: int = 20, offset: int = 0,
                                 categoria: str = None, busqueda: str = None,
                                 ordenar: str = "nombre") -> dict:
    """
    Filtra recetas de la BD según el perfil del usuario.
    Solo devuelve recetas YA clasificadas por Gemini.
    """
    restricciones = _parsear_restricciones_usuario(
        formulario.restricciones_alimentarias or ""
    )

    # Objetivo para filtrar por macros (preparado para futura integración)
    objetivo = getattr(formulario, "objetivo", "Mantener")

    # Base: solo recetas clasificadas
    qs = RecetaMealDB.objects.filter(
        clasificado=True,
        clasificacion__isnull=False,
    ).select_related("clasificacion")

    # ── Excluir incompatibles ─────────────────────────────────────────────────
    for restriccion in restricciones:
        filtro = {f"clasificacion__{restriccion}": True}
        qs = qs.exclude(**filtro)

    # ── Filtros adicionales ───────────────────────────────────────────────────
    if categoria:
        qs = qs.filter(categoria__iexact=categoria)

    if busqueda:
        qs = qs.filter(
            Q(nombre__icontains=busqueda) |
            Q(nombre_es__icontains=busqueda) |
            Q(categoria__icontains=busqueda)
        )

    # ── Ordenar ───────────────────────────────────────────────────────────────
    orden_map = {
        "nombre":    "nombre_es",
        "calorias":  "calorias_estimadas",
        "proteinas": "-proteinas_g",
        "tiempo":    "clasificacion__tiempo_prep_min",
    }
    qs = qs.order_by(orden_map.get(ordenar, "nombre_es"))

    total = qs.count()
    recetas = qs[offset: offset + limit]

    return {
        "total": total,
        "restricciones_aplicadas": restricciones,
        "recetas": recetas,
    }


# ── VISTAS ────────────────────────────────────────────────────────────────────

@login_required
@verificar_formulario_completo
def explorador_recetas(request):
    """Vista HTML del explorador de recetas filtradas para el usuario."""
    formulario = FormularioNutricionGuardado.objects.filter(
        usuario=request.user
    ).last()

    busqueda  = request.GET.get("q", "").strip()
    categoria = request.GET.get("categoria", "").strip() or None
    ordenar   = request.GET.get("ordenar", "nombre")
    pagina    = max(1, int(request.GET.get("pagina", 1)))
    por_pagina = 24
    offset     = (pagina - 1) * por_pagina

    resultado = _filtrar_recetas_por_perfil(
        formulario  = formulario,
        limit       = por_pagina,
        offset      = offset,
        categoria   = categoria,
        busqueda    = busqueda,
        ordenar     = ordenar,
    )

    # Categorías disponibles para el filtro
    categorias_disponibles = (
        RecetaMealDB.objects
        .filter(clasificado=True)
        .values_list("categoria", flat=True)
        .distinct()
        .order_by("categoria")
    )

    total_paginas = max(1, (resultado["total"] + por_pagina - 1) // por_pagina)

    return render(request, "recetas/explorador.html", {
        "recetas":                resultado["recetas"],
        "total":                  resultado["total"],
        "restricciones_aplicadas": resultado["restricciones_aplicadas"],
        "restricciones_labels": dict(RESTRICCIONES),
        "categorias_disponibles": categorias_disponibles,
        "busqueda":               busqueda,
        "categoria":              categoria,
        "ordenar":                ordenar,
        "pagina":                 pagina,
        "total_paginas":          total_paginas,
        "formulario":             formulario,
        # Estadísticas de la BD
        "total_en_bd":     RecetaMealDB.objects.count(),
        "total_clasif":    RecetaMealDB.objects.filter(clasificado=True).count(),
    })


@login_required
@require_GET
def api_recetas_usuario(request):
    """
    API JSON: recetas filtradas según el perfil del usuario autenticado.
    Query params: q, categoria, ordenar, limit, offset
    """
    formulario = FormularioNutricionGuardado.objects.filter(
        usuario=request.user
    ).last()

    if not formulario:
        return JsonResponse(
            {"error": "El usuario no tiene formulario nutricional"}, status=400
        )

    busqueda  = request.GET.get("q", "").strip()
    categoria = request.GET.get("categoria", "").strip() or None
    ordenar   = request.GET.get("ordenar", "nombre")
    limit     = min(int(request.GET.get("limit", 20)), 100)
    offset    = max(0, int(request.GET.get("offset", 0)))

    resultado = _filtrar_recetas_por_perfil(
        formulario=formulario,
        limit=limit, offset=offset,
        categoria=categoria, busqueda=busqueda, ordenar=ordenar,
    )

    recetas_data = []
    for r in resultado["recetas"]:
        clasif = getattr(r, "clasificacion", None)
        recetas_data.append({
            "id":             r.id,
            "meal_id":        r.meal_id,
            "nombre":         r.nombre,
            "nombre_es":      r.nombre_es or r.nombre,
            "categoria":      r.categoria,
            "area":           r.area,
            "imagen_url":     r.imagen_url,
            "youtube_url":    r.youtube_url,
            "macros": {
                "calorias":       r.calorias_estimadas,
                "proteinas_g":    r.proteinas_g,
                "carbohidratos_g": r.carbohidratos_g,
                "grasas_g":       r.grasas_g,
                "fibra_g":        r.fibra_g,
                "sodio_mg":       r.sodio_mg,
            },
            "dificultad":     clasif.dificultad if clasif else None,
            "tiempo_prep_min": clasif.tiempo_prep_min if clasif else None,
            "incompatible_con": clasif.restricciones_incompatibles() if clasif else [],
        })

    return JsonResponse({
        "total":                  resultado["total"],
        "limit":                  limit,
        "offset":                 offset,
        "restricciones_aplicadas": resultado["restricciones_aplicadas"],
        "recetas":                recetas_data,
    })


@login_required
@require_GET
def api_detalle_receta(request, receta_id: int):
    """API JSON: detalle completo de una receta."""
    try:
        r = RecetaMealDB.objects.select_related("clasificacion").get(id=receta_id)
    except RecetaMealDB.DoesNotExist:
        return JsonResponse({"error": "Receta no encontrada"}, status=404)

    clasif = getattr(r, "clasificacion", None)

    return JsonResponse({
        "id":             r.id,
        "meal_id":        r.meal_id,
        "nombre":         r.nombre,
        "nombre_es":      r.nombre_es or r.nombre,
        "categoria":      r.categoria,
        "area":           r.area,
        "imagen_url":     r.imagen_url,
        "youtube_url":    r.youtube_url,
        "fuente_url":     r.fuente_url,
        "etiquetas":      r.etiquetas,
        "ingredientes":   r.ingredientes_json,
        "instrucciones":  r.instrucciones_raw,
        "macros": {
            "calorias":          r.calorias_estimadas,
            "proteinas_g":       r.proteinas_g,
            "carbohidratos_g":   r.carbohidratos_g,
            "grasas_g":          r.grasas_g,
            "fibra_g":           r.fibra_g,
            "sodio_mg":          r.sodio_mg,
            "azucares_g":        r.azucares_g,
            "grasas_saturadas_g": r.grasas_saturadas_g,
        },
        "clasificacion": {
            "dificultad":      clasif.dificultad if clasif else None,
            "tiempo_prep_min": clasif.tiempo_prep_min if clasif else None,
            "incompatible_con": clasif.restricciones_incompatibles() if clasif else [],
            "justificacion":   clasif.justificacion if clasif else {},
        } if clasif else None,
    })


@login_required
@require_GET
def api_stats(request):
    """API JSON: estadísticas de la BD de recetas (para admin/debug)."""
    if not request.user.is_staff:
        return JsonResponse({"error": "No autorizado"}, status=403)

    from django.db.models import Count

    stats_cat = (
        RecetaMealDB.objects
        .values("categoria")
        .annotate(total=Count("id"), clasificadas=Count("id", filter=Q(clasificado=True)))
        .order_by("-total")
    )

    restricciones_stats = {}
    for key, label in RESTRICCIONES:
        count = ClasificacionReceta.objects.filter(**{key: True}).count()
        restricciones_stats[key] = {
            "label": label,
            "incompatibles": count,
        }

    return JsonResponse({
        "total_recetas":     RecetaMealDB.objects.count(),
        "clasificadas":      RecetaMealDB.objects.filter(clasificado=True).count(),
        "pendientes":        RecetaMealDB.objects.filter(clasificado=False).count(),
        "con_error":         RecetaMealDB.objects.exclude(error_clasificacion="").exclude(error_clasificacion__isnull=True).count(),
        "por_categoria":     list(stats_cat),
        "por_restriccion":   restricciones_stats,
    })
