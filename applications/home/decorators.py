from functools import wraps
from django.views.decorators.cache import never_cache
from django.shortcuts import redirect

def no_cache(view_func):
    @wraps(view_func)
    @never_cache
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper
