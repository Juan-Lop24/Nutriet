from django.contrib import admin
from .models import RecetaFavorita, RecetaCache


@admin.register(RecetaFavorita)
class RecetaFavoritaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "recipe_id", "titulo", "creado_en")
    list_filter = ("creado_en",)
    search_fields = ("titulo", "usuario__username", "usuario__email", "recipe_id")
    ordering = ("-creado_en",)


@admin.register(RecetaCache)
class RecetaCacheAdmin(admin.ModelAdmin):
    list_display = ("clave_corta", "creado_en", "expira_en")
    list_filter = ("creado_en", "expira_en")
    search_fields = ("clave",)
    ordering = ("-creado_en",)
    readonly_fields = ("clave", "creado_en")

    def clave_corta(self, obj):
        return obj.clave[:12] + "..."
    clave_corta.short_description = "Clave"
