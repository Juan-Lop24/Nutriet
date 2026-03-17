import json
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from Nutriet.utils import verificar_formulario_completo
from .models import MedicionFisica, PreferenciaMedicion
from .forms import FormularioMedicion
from .engine import analizar
from .utils import necesita_medicion
from applications.nutricion.models import FormularioNutricionGuardado, DietaGenerada


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _obtener_preferencia(usuario):
    return PreferenciaMedicion.objects.get_or_create(
        usuario=usuario,
        defaults={'frecuencia_dias': 15, 'configurada': False}
    )


def _puede_medir(usuario):
    """
    Retorna (puede:bool, segundos_restantes:int, proxima_datetime|None)
    Usa creado_en (DateTimeField) para calcular segundos exactos sin romper las gráficas.
    """
    ultima = MedicionFisica.objects.filter(usuario=usuario).order_by('-creado_en').first()
    if not ultima:
        return True, 0, None

    pref, _ = _obtener_preferencia(usuario)
    proxima = ultima.creado_en + timedelta(days=pref.frecuencia_dias)
    ahora   = timezone.now()

    if ahora >= proxima:
        return True, 0, None

    segundos_restantes = int((proxima - ahora).total_seconds())
    return False, segundos_restantes, proxima


# ─────────────────────────────────────────────
# AJAX: guardar preferencia
# ─────────────────────────────────────────────

@never_cache
@login_required
@require_POST
def guardar_preferencia(request):
    try:
        data = json.loads(request.body)
        frecuencia = int(data.get('frecuencia_dias', 15))
        if frecuencia not in [1, 15, 30]:
            return JsonResponse({'ok': False, 'error': 'Frecuencia inválida'}, status=400)
        pref, _ = PreferenciaMedicion.objects.get_or_create(usuario=request.user)
        pref.frecuencia_dias = frecuencia
        pref.configurada = True
        pref.save()
        return JsonResponse({'ok': True, 'frecuencia_dias': frecuencia})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


# ─────────────────────────────────────────────
# Vistas
# ─────────────────────────────────────────────
@never_cache
@verificar_formulario_completo
@login_required
def tablero(request):
    usuario    = request.user
    formulario = FormularioNutricionGuardado.objects.filter(usuario=usuario).last()
    mediciones = MedicionFisica.objects.filter(usuario=usuario).order_by('fecha')
    analisis      = None
    analisis_json = "{}"
    if formulario:
        try:
            analisis      = analizar(formulario, mediciones)
            analisis_json = json.dumps(analisis)
        except Exception as e:
            messages.warning(request, f"Error al calcular análisis: {e}")
    pref, _ = _obtener_preferencia(usuario)
    return render(request, 'seguimiento/tablero.html', {
        'analisis':                analisis,
        'analisis_json':           analisis_json,
        'mediciones':              mediciones,
        'formulario':              formulario,
        'necesita_medicion':       necesita_medicion(mediciones, dias=15),
        'frecuencia_dias':         pref.frecuencia_dias,
        'mostrar_popup_frecuencia': not pref.configurada,
    })

@never_cache
@login_required
@verificar_formulario_completo
def nueva_medicion(request):
    puede, segundos_restantes, proxima_fecha = _puede_medir(request.user)
    pref, _ = _obtener_preferencia(request.user)
    ultima   = MedicionFisica.objects.filter(usuario=request.user).order_by('-fecha').first()

    ctx_base = {
        'form':                    FormularioMedicion(),
        'bloqueado':               not puede,
        'proxima_fecha':           proxima_fecha,
        'ultima_fecha':            ultima.creado_en if ultima else None,
        'segundos_restantes':      segundos_restantes,
        'frecuencia_dias':         pref.frecuencia_dias,
        'frecuencia_label':        pref.get_frecuencia_dias_display(),
        'mostrar_popup_frecuencia': not pref.configurada,
    }

    if not puede:
        if request.method == "POST":
            messages.error(request, f"⏳ Próxima medición disponible el {proxima_fecha}.")
        return render(request, 'seguimiento/agregar_medicion.html', ctx_base)

    if request.method == "POST":
        form = FormularioMedicion(request.POST)
        if form.is_valid():
            medicion = form.save(commit=False)
            medicion.usuario = request.user
            formulario = FormularioNutricionGuardado.objects.filter(usuario=request.user).last()
            if not formulario:
                messages.error(request, "Primero debes completar el formulario de nutrición.")
                return redirect("nutricion:formulario")
            medicion.altura = formulario.altura
            from applications.ai.core import calcular_imc, calcular_grasa_corporal_deurenberg
            imc = calcular_imc(float(medicion.peso), float(medicion.altura))
            medicion.imc = imc
            medicion.grasa_corporal = max(
                0.0,
                calcular_grasa_corporal_deurenberg(imc, formulario.edad, formulario.sexo or "M")
            )
            try:
                medicion.full_clean()
                medicion.save()
                messages.success(request, "✅ Medición registrada correctamente.")
                return redirect('seguimiento:tablero')

            except ValidationError as e:
                form.add_error(None, e)

            ctx_base['form'] = form
            return render(request, 'seguimiento/agregar_medicion.html', ctx_base)
    else:
        form = FormularioMedicion()
    
    ctx_base['form'] = form
    return render(request, 'seguimiento/agregar_medicion.html', ctx_base)

@never_cache
@login_required
@verificar_formulario_completo
def borrar_medicion(request, pk):
    medicion = get_object_or_404(MedicionFisica, pk=pk, usuario=request.user)
    if request.method == 'POST':
        medicion.delete()
        messages.success(request, "Medición eliminada.")
        return redirect('seguimiento:tablero')
    return render(request, 'seguimiento/borrar_medicion.html', {'medicion': medicion})

@never_cache
@login_required
@verificar_formulario_completo
def seguimiento(request):
    import json as _json
    usuario    = request.user
    mediciones = MedicionFisica.objects.filter(usuario=usuario).order_by('fecha')
    dias_registrados = mediciones.count()
    objetivo_dias    = 30
    progreso = min(int((dias_registrados / objetivo_dias) * 100), 100) if objetivo_dias else 0
    fechas_peso, pesos, fechas_grasa, grasas = [], [], [], []
    for m in mediciones:
        if m.peso:
            fechas_peso.append(m.fecha.strftime('%d %b'))
            pesos.append(float(m.peso))
        if m.grasa_corporal:
            fechas_grasa.append(m.fecha.strftime('%d %b'))
            grasas.append(float(m.grasa_corporal))
    formulario = FormularioNutricionGuardado.objects.filter(usuario=usuario).last()
    analisis   = None
    if formulario and mediciones.exists():
        try:
            analisis = analizar(formulario, mediciones)
        except Exception:
            pass
    pref, _ = _obtener_preferencia(usuario)
    return render(request, 'seguimiento/seguimiento.html', {
        'dias_registrados':         dias_registrados,
        'objetivo_dias':            objetivo_dias,
        'progreso':                 progreso,
        'fechas_peso':              _json.dumps(fechas_peso),
        'pesos':                    _json.dumps(pesos),
        'fechas_grasa':             _json.dumps(fechas_grasa),
        'grasas':                   _json.dumps(grasas),
        'analisis':                 analisis,
        'mostrar_popup_frecuencia': not pref.configurada,
        'frecuencia_dias':          pref.frecuencia_dias,
    })

@never_cache
@login_required
@verificar_formulario_completo
def recomendaciones_ia(request):
    usuario    = request.user
    dieta      = DietaGenerada.objects.filter(usuario=usuario).order_by('-creado_en').first()
    formulario = FormularioNutricionGuardado.objects.filter(usuario=usuario).last()

    texto = None
    if dieta and dieta.contenido_dieta:
        texto = dieta.contenido_dieta if isinstance(dieta.contenido_dieta, dict) else None

    return render(request, 'seguimiento/recomendaciones_ia.html', {
        'dieta':      dieta,
        'formulario': formulario,
        'texto':      texto,
    })