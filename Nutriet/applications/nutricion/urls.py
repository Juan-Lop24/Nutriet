app_name = 'nutricion'

from django.urls import path
from .views import formulario_view, historial_formularios_view, detalle_formulario_view
from . import views

urlpatterns = [
    path("formulario", formulario_view, name="formulario"),
    path("generando/", views.cargando_view, name="generando"),
    path("resultado/", views.resultado_view, name="resultado"),
    path("historial/", historial_formularios_view, name="historial_formularios"),
    path("detalle/<int:id>/", detalle_formulario_view, name="detalle_formulario"),
]
