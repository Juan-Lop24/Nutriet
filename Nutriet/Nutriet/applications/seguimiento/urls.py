from django.urls import path
from . import views


app_name = 'seguimiento'
urlpatterns = [
    path('', views.tablero, name='tablero'),
    path("agregar/", views.nueva_medicion, name="agregar"),
    path("seguimiento/", views.seguimiento, name="seguimiento"),
    path("borrar/<int:pk>/", views.borrar_medicion, name="borrar"),
    path("nueva_medicion/", views.nueva_medicion, name="nueva_medicion"),
    path("preferencia/", views.guardar_preferencia, name="guardar_preferencia"),
    path("recomendaciones-ia/", views.recomendaciones_ia, name="recomendaciones_ia"),
]