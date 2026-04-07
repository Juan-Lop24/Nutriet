from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import FormularioNutricionForm
from .models import FormularioNutricionGuardado, DietaGenerada
from .ia import generar_explicacion_nutricional
from ..seguimiento.models import MedicionFisica
from ..ai.engine.ia import ProcesadorNutricion
from ..ai.dtos.entrada import DatosEntrada
import json
import logging

logger = logging.getLogger(__name__)


@login_required(login_url='login')
def formulario_view(request):
    if FormularioNutricionGuardado.objects.filter(usuario=request.user).exists():
        return redirect("main")

    if request.method == "POST":
        form = FormularioNutricionForm(request.POST)

        if form.is_valid():
            formulario = form.save(commit=False)
            formulario.usuario = request.user

            # ✅ Guardar múltiples condiciones médicas
            condiciones_lista = form.cleaned_data.get('condiciones_medicas', [])
            formulario.condiciones_medicas_json = list(condiciones_lista)
            # Campo legado: guardar la primera condición para compatibilidad
            formulario.condicion_medica = condiciones_lista[0] if condiciones_lista else ""
            formulario.save()

            MedicionFisica.objects.create(
                usuario=request.user,
                peso=formulario.peso,
                altura=formulario.altura
            )

            request.session["formulario_id"] = formulario.id
            request.session["datos_form"] = {
                "sexo": formulario.sexo,
                "edad": formulario.edad,
                "peso": float(formulario.peso),
                "altura": float(formulario.altura),
                "objetivo": formulario.objetivo,
                "expectativa": float(formulario.peso_objetivo),
                "plazo_meses": formulario.plazo_meses,
                "comidas_preferidas": formulario.comidas_preferidas,
                "ejercicio": formulario.nivel_actividad,
                # ✅ Guardamos lista completa de condiciones en sesión
                "condiciones_medicas": condiciones_lista,
                # legado para compatibilidad con ia.py (toma la primera)
                "condicion_medica": condiciones_lista[0] if condiciones_lista else "",
                "ingredientes_excluidos": formulario.ingredientes_excluidos or ""
            }

            return redirect("nutricion:generando")

    else:
        form = FormularioNutricionForm()

    return render(request, "nutricion/formulario.html", {"form": form})


# =======================================================


@login_required(login_url='login')
def cargando_view(request):
    datos = request.session.get("datos_form")
    formulario_id = request.session.get("formulario_id")

    if not datos or not formulario_id:
        messages.error(request, "No hay datos para generar la dieta.")
        return redirect("nutricion:formulario")

    try:
        procesador = ProcesadorNutricion()

        ingredientes_excluidos_raw = datos.get('ingredientes_excluidos', '')
        ingredientes_excluidos = [
            i.strip().lower() for i in ingredientes_excluidos_raw.split(',') if i.strip()
        ] if ingredientes_excluidos_raw else []

        # ✅ Obtener lista completa de condiciones médicas
        condiciones_lista = datos.get('condiciones_medicas', [])
        if not condiciones_lista:
            # fallback al campo legado
            condicion_medica = datos.get('condicion_medica', '')
            condiciones_lista = [condicion_medica] if condicion_medica else []

        datos_entrada = DatosEntrada(
            edad_anos=datos.get('edad'),
            peso_kg=datos.get('peso'),
            altura_cm=datos.get('altura'),
            sexo=datos.get('sexo', 'M'),
            objetivo=datos.get('objetivo', 'mantener').lower(),
            nivel_actividad=datos.get('ejercicio', 'sedentario').lower(),
            comidas_preferidas=datos.get('comidas_preferidas', []),
            restricciones_ingredientes=ingredientes_excluidos,
            condiciones_medicas=condiciones_lista,  # ✅ lista completa
        )

        resultado_ia = procesador.procesar(datos_entrada)

        # ✅ Pasar condiciones múltiples a la IA generativa
        datos_para_ia = dict(datos)
        datos_para_ia['condicion_medica'] = (
            ", ".join(condiciones_lista) if condiciones_lista else "ninguna"
        )
        texto_openai = generar_explicacion_nutricional(datos_para_ia)

        formulario = FormularioNutricionGuardado.objects.get(id=formulario_id)

        dieta = DietaGenerada.objects.create(
            formulario=formulario,
            usuario=request.user,
            objetivo=formulario.objetivo,
            plazo_meses=formulario.plazo_meses,
            imc=resultado_ia.imc,
            porcentaje_grasa=resultado_ia.porcentaje_grasa,
            tmb=resultado_ia.tmb,
            tdee=resultado_ia.tdee,
            calorias_diarias=int(resultado_ia.calorias_recomendadas),
            proteinas_gramos=resultado_ia.proteinas_g,
            grasas_gramos=resultado_ia.grasas_g,
            carbohidratos_gramos=resultado_ia.carbohidratos_g,
            distribucion_macros_comidas=resultado_ia.distribucion_macros_comidas,
            contenido_dieta=texto_openai
        )

        request.session["dieta_generada"] = {
            "calculos": {
                "imc": resultado_ia.imc,
                "porcentaje_grasa": resultado_ia.porcentaje_grasa,
                "tmb": resultado_ia.tmb,
                "tdee": resultado_ia.tdee,
                "calorias_diarias": resultado_ia.calorias_recomendadas,
                "macros": {
                    "proteinas": resultado_ia.proteinas_g,
                    "grasas": resultado_ia.grasas_g,
                    "carbohidratos": resultado_ia.carbohidratos_g,
                },
                "distribucion_macros_comidas": resultado_ia.distribucion_macros_comidas
            },
            "texto": texto_openai
        }

    except Exception as e:
        logger.exception(e)
        messages.error(request, "Error generando la dieta.")
        return redirect("nutricion:formulario")

    request.session.pop("datos_form", None)

    return redirect("nutricion:resultado")


# =======================================================


@login_required(login_url='login')
def resultado_view(request):
    dieta = request.session.get("dieta_generada")

    if not dieta:
        messages.error(request, "No hay dieta generada.")
        return redirect("nutricion:formulario")
    
    request.session['mostrar_advertencia'] = True

    return render(request, "nutricion/resultado.html", {
        "dieta": dieta
    })


# =======================================================


@login_required(login_url='login')
def historial_formularios_view(request):
    formularios = FormularioNutricionGuardado.objects.filter(
        usuario=request.user
    ).order_by("-creado_en")

    return render(request, "nutricion/historial.html", {
        "formularios": formularios
    })


@login_required(login_url='login')
def detalle_formulario_view(request, id):
    formulario = get_object_or_404(
        FormularioNutricionGuardado,
        id=id,
        usuario=request.user
    )

    dieta = DietaGenerada.objects.filter(formulario=formulario).first()

    return render(request, "nutricion/detalle_formulario.html", {
        "formulario": formulario,
        "dieta": dieta
    })


def extraer_calculos(dieta_json: dict) -> dict:
    calculos = dieta_json.get("calculos", {})
    macros = calculos.get("macros", {})
    return {
        "tmb": calculos.get("tmb"),
        "tdee": calculos.get("tdee"),
        "calorias_diarias": calculos.get("calorias_diarias"),
        "proteinas": macros.get("proteinas"),
        "grasas": macros.get("grasas"),
        "carbohidratos": macros.get("carbohidratos"),
    }
