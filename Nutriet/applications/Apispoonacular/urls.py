# applications/Apispoonacular/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('generar-dieta/', views.generador_dieta, name='generar_dieta'),
    path('explorar/', views.explorar_recetas, name='explorar_recetas'),
    path('receta/<int:recipe_id>/', views.receta_detalle, name='receta_detalle'),
    path('ver-receta/<int:recipe_id>/', views.receta_detalle, name='ver_receta'),
    path('toggle-favorito/', views.toggle_favorito, name='toggle_favorito'),
    path('mis-favoritos/', views.recetas_favoritas, name='recetas_favoritas'),
    path('eliminar-favorito/<int:recipe_id>/', views.eliminar_favorito, name='eliminar_favorito'),
    path('traducir-instrucciones/', views.traducir_instrucciones, name='traducir_instrucciones'),
]