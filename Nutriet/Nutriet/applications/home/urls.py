from django.urls import path
from . import views

urlpatterns = [
    path('', views.indexviews.as_view(), name='home'),
    path('main/', views.main, name='main'),
    path('redes/', views.socialviews.as_view(), name='redes_sociales'),
    path('contacto/', views.contacto, name='contacto'),
    path('info/', views.informacionviews.as_view(), name='informacion'),



]