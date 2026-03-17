from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import VerificacionCodigo

User = get_user_model()

# Register your models here.
admin.site.register(User)

@admin.register(VerificacionCodigo)
class VerificacionCodigoAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "codigo",
        "verificado",
        "creado",
        "expirado_estado",
    )

    list_filter = (
        "verificado",
        "creado",
    )

    search_fields = (
        "usuario__username",
        "usuario__email",
        "codigo",
    )

    ordering = ("-creado",)

    readonly_fields = ("creado",)

    def expirado_estado(self, obj):
        if timezone.now() > obj.creado + timedelta(minutes=5):
            return "⛔ Expirado"
        return "✅ Vigente"

    expirado_estado.short_description = "Estado"
