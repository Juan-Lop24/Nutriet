from django.urls import path
from . import views

urlpatterns = [
    path('', views.calendario_view, name='calendario'),
    path('eventos/', views.obtener_eventos, name='obtener_eventos'),
    path('agregar/', views.agregar_evento, name='agregar_evento'),
    path('editar/<int:evento_id>/', views.editar_evento, name='editar_evento'),
    path('eliminar/<int:evento_id>/', views.eliminar_evento, name='eliminar_evento'),
]
