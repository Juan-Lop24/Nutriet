from django.shortcuts import redirect
from django.urls import reverse

# Asegúrate de que esta ruta de importación sea correcta para tu modelo
from applications.nutricion.models import FormularioNutricionGuardado



URL_FORMULARIO = 'nutricion:formulario' 

URL_DASHBOARD = 'main'

def verificar_formulario_completo(view_func):
    """
    Decorador que verifica si el usuario autenticado tiene al menos un 
    FormularioNutricionGuardado.
    Si no lo tiene, lo redirige al formulario.
    """
    def wrapper(request, *args, **kwargs):
        # 1. Solo aplica si el usuario está autenticado
        if request.user.is_authenticated:
            # Si el usuario ya está en la vista del formulario, no lo redirigimos
            # para evitar un bucle infinito, y lo dejamos seguir.
            if request.resolver_match and request.resolver_match.url_name == 'formulario':
                return view_func(request, *args, **kwargs)

            # 2. Consulta la existencia del formulario
            formulario_existe = FormularioNutricionGuardado.objects.filter(usuario=request.user).exists()
            
            # 3. Decisión de Redirección
            if not formulario_existe:
                # Si NO existe, lo enviamos a llenar el formulario
                return redirect(reverse(URL_FORMULARIO)) 

        # Si el formulario existe, o si la vista actual es la del formulario, 
        # o si no está autenticado (protección via @login_required), permite el acceso a la vista original.
        return view_func(request, *args, **kwargs)

    return wrapper