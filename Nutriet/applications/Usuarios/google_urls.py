from django.urls import path
from . import google_views

urlpatterns = [
    # Esta ruta es /api/auth/google/login/
    path('login/', google_views.google_login, name='google_login'), 
    # Esta ruta es /api/auth/google/callback/ (La que te daba 404)
    path('callback/', google_views.google_callback, name='google_callback'),
]

