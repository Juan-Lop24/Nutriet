# applications/recetas/urls.py
from django.urls import path
from . import views

app_name = "recetas"

urlpatterns = [
    # Vista HTML del explorador
    path("", views.explorador_recetas, name="explorador"),

    # APIs JSON
    path("api/para-usuario/",    views.api_recetas_usuario,  name="api_usuario"),
    path("api/detalle/<int:receta_id>/", views.api_detalle_receta, name="api_detalle"),
    path("api/stats/",           views.api_stats,            name="api_stats"),
]
