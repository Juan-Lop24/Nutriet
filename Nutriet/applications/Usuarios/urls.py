from django.urls import path
from .views import RegisterView,PasswordView, verificacion_login
from django.contrib.auth.views import LogoutView
from applications.home.urls import urlpatterns as home_urls
from .views import LoginView


#nuevas rls
from . import views

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('recuperar/', PasswordView.as_view(), name='recuperar'),
#NUEVOS PATH
    path('recover/', views.send_verification_code, name='send_verification_code'),
    path('verificar/', views.verify_code, name='verify_code'),
    path('cambiar/', views.change_password, name='change_password'),
    
    path('logout/', LogoutView.as_view(next_page='/usuarios/login/'), name='logout'),
    path("perfil/", views.perfil_usuario, name="perfil"),

    path('reenviar-codigo/', views.reenviar_codigo, name='reenviar_codigo'),
    path("verificacion-login/", verificacion_login, name="verificacion_login"),
    path("marcar-notificaciones/", views.marcar_notificaciones_configuradas, name="marcar_notificaciones"),

] + home_urls
    