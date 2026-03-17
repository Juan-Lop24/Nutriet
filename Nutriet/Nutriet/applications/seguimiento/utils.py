import math
import pandas as pd
from datetime import datetime, timedelta
from .models import MedicionFisica
from .models import MedicionFisica

def obtener_resumen_seguimiento(user):
    mediciones = (
        MedicionFisica.objects
        .filter(usuario=user)
        .order_by('-fecha')[:7]
    )

    mediciones = list(reversed(mediciones))  # orden cronológico

    dias_registrados = MedicionFisica.objects.filter(usuario=user).count()
    objetivo_dias = user.objetivo_dias if hasattr(user, 'objetivo_dias') else 30

    progreso = int((dias_registrados / objetivo_dias) * 100) if objetivo_dias else 0
    progreso = min(progreso, 100)

    fechas = [m.fecha.strftime('%d/%m') for m in mediciones]
    pesos = [m.peso for m in mediciones]

    return {
        'dias_registrados': dias_registrados,
        'objetivo_dias': objetivo_dias,
        'progreso': progreso,
        'fechas_mini': fechas,
        'pesos_mini': pesos,
    }


def obtener_resumen_seguimiento(user):
    mediciones = MedicionFisica.objects.filter(usuario=user).order_by('fecha')

    dias_registrados = mediciones.count()
    objetivo_dias = user.objetivo_dias if hasattr(user, 'objetivo_dias') else 30

    progreso = int((dias_registrados / objetivo_dias) * 100) if objetivo_dias > 0 else 0
    progreso = min(progreso, 100)

    return {
        'dias_registrados': dias_registrados,
        'objetivo_dias': objetivo_dias,
        'progreso': progreso
    }

# ============================
# CÁLCULO DE IMC
# ============================
def calcular_imc(peso_kg, altura_cm):
    altura_m = altura_cm / 100.0
    if altura_m <= 0:
        return None
    imc = peso_kg / (altura_m ** 2)
    return round(imc, 2)


def clasificar_imc(imc):
    """
    Clasifica el IMC según estándares de la OMS
    """
    if imc is None:
        return None
    
    if imc < 18.5:
        return "Bajo peso"
    elif imc < 25:
        return "Peso normal"
    elif imc < 30:
        return "Sobrepeso"
    else:
        return "Obesidad"


# ============================
# CÁLCULO DE GRASA CORPORAL
# ============================
def calcular_grasa_corporal(sexo, cintura_cm, cuello_cm, altura_cm, cadera_cm=None):
    try:
        cintura = float(cintura_cm)
        cuello = float(cuello_cm)
        altura = float(altura_cm)
    except Exception:
        return None

    if cintura <= 0 or cuello <= 0 or altura <= 0:
        return None

    if sexo == 'masculino':
        # Fórmula US Navy masculino
        try:
            densidad = (
                1.0324
                - 0.19077 * math.log10(cintura - cuello)
                + 0.15456 * math.log10(altura)
            )
            grasa = 495 / densidad - 450
            return round(grasa, 2)
        except ValueError:
            return None

    else:
        # Fórmula femenina
        if cadera_cm is None:
            return None

        try:
            cadera = float(cadera_cm)
            densidad = (
                1.29579
                - 0.35004 * math.log10(cintura + cadera - cuello)
                + 0.22100 * math.log10(altura)
            )
            grasa = 495 / densidad - 450
            return round(grasa, 2)
        except ValueError:
            return None


def construir_dataframe(mediciones_qs):
    lista = []
    for m in mediciones_qs.order_by('fecha'):
        grasa = getattr(m, 'grasa_corporal', None)
        
        if grasa is None and all(hasattr(m, attr) for attr in ['cintura', 'cuello', 'altura', 'sexo']):
            try:
                grasa = calcular_grasa_corporal(
                    sexo=m.sexo,
                    cintura_cm=m.cintura,
                    cuello_cm=m.cuello,
                    altura_cm=m.altura,
                    cadera_cm=getattr(m, 'cadera', None)
                )
            except:
                grasa = None
        
        lista.append({
            'fecha': pd.to_datetime(m.fecha),
            'peso': m.peso,
            'imc': getattr(m, 'imc', calcular_imc(m.peso, m.altura)),
            'grasa_corporal': grasa
        })
    
    if not lista:
        # Retornar DataFrame vacío pero con las columnas correctas
        return pd.DataFrame(columns=['fecha', 'peso', 'imc', 'grasa_corporal'])
    
    df = pd.DataFrame(lista)
    
    # Asegurarse de que la columna exista
    if 'grasa_corporal' not in df.columns:
        df['grasa_corporal'] = None
    
    return df




# ============================
# CALCULO DE PROGRESO DE PESO
# ============================
def calcular_progreso(peso_inicial, peso_actual, peso_objetivo):
    """
    Calcula el progreso hacia el peso objetivo en porcentaje.
    Devuelve 0 si ya se alcanzó o se superó el objetivo.
    """
    try:
        if peso_inicial == peso_objetivo:
            return 0
        progreso = (peso_inicial - peso_actual) / (peso_inicial - peso_objetivo) * 100
        progreso = max(0, min(100, progreso))  # asegurar que esté entre 0 y 100
        return round(progreso, 1)
    except Exception:
        return 0


# ============================
# VERIFICAR SI NECESITA MEDICIÓN
# ============================
def necesita_medicion(mediciones_qs, dias=15):
    """
    Verifica si hace más de X días no hay una medición.
    Retorna True si necesita medición, False en caso contrario.
    """
    if not mediciones_qs.exists():
        # Si no hay mediciones, siempre necesita
        return True
    
    ultima_medicion = mediciones_qs.latest('fecha')
    dias_desde_ultima = (datetime.now().date() - ultima_medicion.fecha).days
    
    return dias_desde_ultima >= dias
