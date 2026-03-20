# applications/recetas/admin.py

from django.contrib import admin
from .models import RecetaMealDB, ClasificacionReceta


# ==============================
# INLINE CLASIFICACIÓN
# ==============================

class ClasificacionInline(admin.StackedInline):
    model = ClasificacionReceta
    can_delete = False
    extra = 0
    readonly_fields = ("clasificado_en", "version_prompt")


# ==============================
# ADMIN RECETA
# ==============================

@admin.register(RecetaMealDB)
class RecetaMealDBAdmin(admin.ModelAdmin):

    list_display = (
        "nombre",
        "categoria",
        "area",
        "clasificado",
        "calorias_estimadas",
        "proteinas_g",
        "carbohidratos_g",
        "grasas_g",
    )

    list_filter = ("clasificado", "categoria", "area")

    search_fields = ("nombre", "nombre_es", "meal_id")

    readonly_fields = (
        "meal_id",
        "importado_en",
        "actualizado_en",
        "clasificado_en",
        "error_clasificacion",
    )

    inlines = [ClasificacionInline]


# ==============================
# ADMIN CLASIFICACIÓN
# ==============================

@admin.register(ClasificacionReceta)
class ClasificacionRecetaAdmin(admin.ModelAdmin):

    list_display = (
        "receta",
        "dificultad",
        "tiempo_prep_min",
        "restricciones_simple",
        "clasificado_en",
    )

    list_filter = (
        "dificultad",
        "diabetes", "intolerancia_lactosa", "celiaca",
        "hipertension", "hipercolesterolemia", "dislipidemia",
        "indigestion", "hipertiroidismo", "anemia_ferropenica",
        "alergia_huevo", "alergia_marisco", "alergia_mani",
    )

    search_fields = ("receta__nombre",)

    readonly_fields = ("clasificado_en",)

    def restricciones_simple(self, obj):
        incompatibles = obj.restricciones_incompatibles()

        if not incompatibles:
            return "Sin restricciones"

        return ", ".join(incompatibles)

    restricciones_simple.short_description = "Incompatible con"