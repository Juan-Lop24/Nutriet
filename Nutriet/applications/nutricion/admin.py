from django.contrib import admin
from .models import (
    FormularioNutricionGuardado,
    DietaGenerada,
    RestriccionAlimentaria
)


# ===============================
# FORMULARIO NUTRICIÓN
# ===============================
@admin.register(FormularioNutricionGuardado)
class FormularioNutricionAdmin(admin.ModelAdmin):

    list_display = (
        'usuario',
        'edad',
        'peso',
        'altura',
        'objetivo',
        'peso_objetivo',
        'plazo_meses',
        'nivel_actividad',
        'condicion_medica',
        'creado_en'
    )

    list_filter = (
        'objetivo',
        'condicion_medica',
        'nivel_actividad',
        'creado_en'
    )

    search_fields = (
        'usuario__username',
        'usuario__email'
    )

    readonly_fields = (
        'creado_en',
        'actualizado_en'
    )

    fieldsets = (
        ('👤 Usuario', {
            'fields': ('usuario',)
        }),
        ('📊 Datos físicos', {
            'fields': ('sexo', 'edad', 'peso', 'altura')
        }),
        ('🎯 Objetivos', {
            'fields': ('objetivo', 'peso_objetivo', 'plazo_meses')
        }),
        ('🥗 Hábitos y preferencias', {
            'fields': (
                'nivel_actividad',
                'comidas_preferidas',
                'condicion_medica',
                'ingredientes_excluidos',
            )
        }),
        ('🕒 Metadata', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )


# ===============================
# DIETA GENERADA (IA)
# ===============================
@admin.register(DietaGenerada)
class DietaGeneradaAdmin(admin.ModelAdmin):

    list_display = (
        'usuario',
        'formulario',
        'calorias_diarias',
        'objetivo_usuario',
        'plazo_meses',
        'creado_en'
    )

    list_filter = (
        'creado_en',
        'usuario'
    )

    search_fields = (
        'usuario__username',
        'usuario__email'
    )

    readonly_fields = (
        'creado_en',
        'formulario',
        'contenido_dieta'
    )

    fieldsets = (
        ('👤 Usuario', {
            'fields': ('usuario', 'formulario')
        }),
        ('🔥 Resumen nutricional (IA)', {
            'fields': ('contenido_dieta',)
        }),
        ('🕒 Metadata', {
            'fields': ('creado_en',),
            'classes': ('collapse',)
        }),
    )

    def calorias_diarias(self, obj):
        return obj.contenido_dieta.get('calorias_diarias_recomendadas', '—')
    calorias_diarias.short_description = 'Calorías'

    def objetivo_usuario(self, obj):
        return obj.formulario.objetivo
    objetivo_usuario.short_description = 'Objetivo'

    def plazo_meses(self, obj):
        return f"{obj.formulario.plazo_meses} meses"


# ===============================
# RESTRICCIONES
# ===============================
@admin.register(RestriccionAlimentaria)
class RestriccionAlimentariaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'creado')
    search_fields = ('nombre',)
    readonly_fields = ('creado',)
