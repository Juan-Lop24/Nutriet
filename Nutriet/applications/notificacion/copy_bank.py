# applications/notificacion/copy_bank.py
"""
Banco de copy para notificaciones push de NutriET.
Tono: amistoso, colombiano, sin ser tóxico ni repetitivo.
Cada lista tiene variantes para rotar y evitar que el usuario vea siempre lo mismo.
"""

import random

# ─────────────────────────────────────────────
# CATEGORÍA 1 · Recordatorios de comidas
# ─────────────────────────────────────────────

COMIDAS_DESAYUNO = [
    ("¡Buenos días! ☀️", "¿Ya desayunaste? Tu cuerpo lo espera."),
    ("Hora del desayuno 🍳", "Empieza el día con energía, vale la pena."),
    ("La mañana pide combustible 💪", "¿Qué tienes para desayunar hoy?"),
    ("Desayuno pendiente ⏰", "No te olvides, el día empieza mejor con algo rico."),
    ("¡Arriba ese desayuno! 🌅", "Un buen comienzo marca todo el día."),
]

COMIDAS_MEDIA_MANANA = [
    ("Media mañana lista 🍎", "Un snack y sigues volando el resto del día."),
    ("¿Ya comiste algo? 🕐", "Es hora de tu snack de media mañana."),
    ("Snack time 🥜", "Algo pequeño ahora y llegas perfecto al almuerzo."),
    ("La energía baja a esta hora 📉", "Un snack nutritivo te salva la mañana."),
    ("Recuerda tu merienda 🍌", "Tu cuerpo te lo agradece más tarde."),
]

COMIDAS_ALMUERZO = [
    ("Almuerzo al frente 🍽️", "¡A recargarse para la tarde! No te lo saltes."),
    ("Son las 12 ☀️", "Perfecto para tu almuerzo, ¿ya planeaste qué vas a comer?"),
    ("La hora del almuerzo llegó 🥗", "Come bien hoy y tu tarde va a ser otra historia."),
    ("¿Listo para almorzar? 🍲", "Tómate tu tiempo, un buen almuerzo vale todo."),
    ("Almuerzo pendiente 🌮", "Recuerda registrar lo que comiste para llevar el control."),
]

COMIDAS_MERIENDA = [
    ("La merienda te llama 🫐", "Cuida esa energía de la tarde con algo rico."),
    ("Snack de la tarde ☕", "Un pequeño antojo saludable no le hace daño a nadie."),
    ("¿Bajón de las 3? 😴", "Tu merienda llega justo a tiempo."),
    ("Merienda time 🍇", "Algo fresquito y a seguir el día con todo."),
    ("Tarde productiva 💡", "Un snack nutritivo y sigues con energía."),
]

COMIDAS_CENA = [
    ("Hora de cenar 🌙", "Algo liviano y rico, ¿ya tienes listo qué cenar?"),
    ("La cena no puede faltar 🌛", "Tu descanso también depende de comer bien."),
    ("Cena pendiente 🍜", "Cierra el día con una comida rica y balanceada."),
    ("¿Ya cenaste? 🌙", "No te vayas a dormir sin registrar tu última comida."),
    ("Última comida del día 🌜", "Liviano y nutritivo, así el cuerpo descansa bien."),
]

# Map para acceso por nombre
COMIDAS_MAP = {
    "desayuno": COMIDAS_DESAYUNO,
    "media_manana": COMIDAS_MEDIA_MANANA,
    "almuerzo": COMIDAS_ALMUERZO,
    "merienda": COMIDAS_MERIENDA,
    "cena": COMIDAS_CENA,
}

# ─────────────────────────────────────────────
# CATEGORÍA 2 · Hidratación
# ─────────────────────────────────────────────

HIDRATACION = [
    ("💧 Hidratación check", "Han pasado 2 horas, ¿tomaste agua?"),
    ("Agua, por favor 💦", "Tu cuerpo ya lo está pidiendo, un vasito y ya."),
    ("El agua también nutre 💧", "Un vaso más y vas muy bien en tu meta de hoy."),
    ("¿Agua o jugo natural? 🥤", "Ambos cuentan — elige uno y dale."),
    ("Momento de hidratarte 🌊", "Pequeños sorbos, grandes beneficios para tu día."),
    ("💧 La sed llega tarde", "No esperes sentirla — toma agua ahora."),
    ("¡Vas muy bien! 💦", "Pero no bajes la guardia con el agua hoy."),
    ("Infusión, agua con limón o sola 💧", "Lo que sea, hidrátate. Tu cuerpo te lo agradece."),
    ("¿Hace calor hoy? 🌡️", "Recuerda aumentar tu consumo de agua en días calurosos."),
    ("Agua antes de comer 🫙", "Un vaso antes de tu próxima comida es una gran idea."),
    ("Meta de agua 💧", "¿Ya revisaste cuántos vasos llevas hoy?"),
]

# ─────────────────────────────────────────────
# CATEGORÍA 3 · Eventos y seguimiento
# ─────────────────────────────────────────────

EVENTOS_ACTIVIDAD = [
    ("📅 Actividad programada", "Hoy tienes {actividad} agendada. ¡Listo pa' darle!"),
    ("Tu sesión de hoy 🏃", "{actividad} está en el plan. ¿Ya estás listo?"),
    ("Hora de mover el cuerpo 💪", "{actividad} hoy — lo lograrás, no lo dudes."),
    ("Actividad en camino 🏋️", "Recuerda: {actividad} está en tu calendario."),
]

EVENTOS_REGISTRO_PROGRESO = [
    ("📊 Día de seguimiento", "Revisa tus metas y celébralas, así sea lo pequeño."),
    ("Registro de progreso 📋", "¿Ya anotaste cómo vas esta semana?"),
    ("Hoy toca revisar ✅", "Mira cómo vas y ajusta lo que necesites, sin drama."),
    ("¿Cómo vas? 📈", "Es momento de revisar tu plan de nutrición."),
    ("Chequeo semanal 🔍", "Cinco minutos revisando tu progreso cambian mucho."),
]

EVENTOS_REGISTRO_COMIDA = [
    ("📝 ¿Registraste hoy?", "Llevar el control de tus comidas hace la diferencia."),
    ("Registro pendiente ✍️", "No se te olvide anotar lo que comiste hoy."),
    ("¿Ya registraste? 📋", "Solo toma un momento y ayuda un montón."),
    ("Control al día 📝", "Registrar tus comidas es el primer paso del cambio."),
]

# ─────────────────────────────────────────────
# CATEGORÍA 4 · Recetas y menú
# ─────────────────────────────────────────────

RECETAS = [
    ("Nueva receta disponible 🍜", "Algo rico y saludable te espera hoy en NutriET."),
    ("¿Cansado de lo mismo? 🔄", "Tenemos una variación del menú que te va a encantar."),
    ("Inspiración culinaria 🥘", "Hoy te proponemos algo distinto y muy fácil de hacer."),
    ("Nueva opción saludable 🥗", "Sin sacrificar el sabor — te lo prometemos."),
    ("Receta del día 👨‍🍳", "Lista en menos de 20 minutos, ¿le entramos?"),
    ("Menú actualizado 📋", "Mira las novedades de esta semana en tu plan."),
    ("¿Sabías que puedes variar? 💡", "Pequeños cambios en tu menú hacen una gran diferencia."),
    ("Algo nuevo para hoy 🍳", "Un pequeño cambio en el menú y la semana se siente diferente."),
]

# ─────────────────────────────────────────────
# CATEGORÍA 5 · Motivación y consistencia
# ─────────────────────────────────────────────

MOTIVACION = [
    ("💚 ¡Vas muy bien!", "Un día difícil no borra todo lo que ya lograste."),
    ("No es perfección 🌱", "Es consistencia. Sigue a tu ritmo y lo lograrás."),
    ("Pequeños pasos 🚶", "Cambios reales — vas mejor de lo que crees."),
    ("Hoy también cuenta 💪", "Cada buena decisión que tomas suma, siempre."),
    ("¿Tuviste un mal día? 🌅", "Mañana es una nueva oportunidad, sin culpa."),
    ("Te estás cuidando ✨", "Y eso importa más de lo que crees. Orgullo de ti."),
    ("Consistencia > perfección 💚", "Recuérdalo siempre que sientas que no es suficiente."),
    ("Sin presión 🌿", "Sin culpa, solo tú y tu proceso a tu ritmo."),
    ("Celebra lo de hoy 🎉", "Aunque sea pequeño, suma y mucho."),
    ("Cada día que registras 📊", "Es un paso más cerca de tu objetivo. Sigue así."),
    ("No te rindas hoy 💪", "El proceso tiene altibajos — lo que importa es seguir."),
]

# ─────────────────────────────────────────────
# CATEGORÍA 6 · Resumen diario
# ─────────────────────────────────────────────

RESUMEN_DIARIO = [
    ("Resumen del día 📊", "Revisa cómo te fue hoy en tu plan nutricional."),
    ("Día completado ✅", "Mañana arrancamos con todo otra vez. ¡Bien hecho!"),
    ("Tu resumen está listo 📈", "Toca para ver cómo te fue hoy."),
    ("Fin del día 🌙", "¿Registraste todo? Revisa y descansa bien."),
    ("Buen trabajo hoy 🌟", "Tu consistencia habla por sí sola. Sigue así."),
    ("¿Cómo fue tu día? 📋", "Revisa tu resumen y ajusta si es necesario."),
    ("Cierre del día ✨", "Un vistazo rápido a tu progreso y a descansar."),
]


# ─────────────────────────────────────────────
# HELPER: selección aleatoria
# ─────────────────────────────────────────────

def get_copy_comida(tipo_comida: str) -> tuple[str, str]:
    """
    Retorna (titulo, mensaje) aleatorio para una comida específica.
    tipo_comida: 'desayuno' | 'media_manana' | 'almuerzo' | 'merienda' | 'cena'
    """
    opciones = COMIDAS_MAP.get(tipo_comida, COMIDAS_ALMUERZO)
    return random.choice(opciones)


def get_copy_hidratacion() -> tuple[str, str]:
    return random.choice(HIDRATACION)


def get_copy_actividad(nombre_actividad: str = "") -> tuple[str, str]:
    nombre = nombre_actividad.strip() if nombre_actividad else ""
    if nombre:
        titulo, msg = random.choice(EVENTOS_ACTIVIDAD)
        msg = msg.replace("{actividad}", nombre)
        return titulo, msg
    else:
        # Variantes sin placeholder cuando no se conoce el nombre de la actividad
        opciones_sin_nombre = [
            ("📅 Actividad programada", "Tienes una actividad agendada hoy. ¡Listo pa darle!"),
            ("Tu sesión de hoy 🏃", "Revisa tu calendario, tienes algo pendiente hoy."),
            ("Hora de mover el cuerpo 💪", "Tienes una actividad planeada — lo lograrás, no lo dudes."),
            ("Actividad en camino 🏋️", "Recuerda revisar tu calendario de hoy."),
        ]
        return random.choice(opciones_sin_nombre)


def get_copy_registro_progreso() -> tuple[str, str]:
    return random.choice(EVENTOS_REGISTRO_PROGRESO)


def get_copy_registro_comida() -> tuple[str, str]:
    return random.choice(EVENTOS_REGISTRO_COMIDA)


def get_copy_receta(nombre_receta: str = "") -> tuple[str, str]:
    titulo, msg = random.choice(RECETAS)
    if nombre_receta:
        msg = f"{nombre_receta} — {msg}"
    return titulo, msg


def get_copy_motivacion() -> tuple[str, str]:
    return random.choice(MOTIVACION)


def get_copy_resumen() -> tuple[str, str]:
    return random.choice(RESUMEN_DIARIO)


# ─────────────────────────────────────────────
# CATEGORÍA 7 · Recordatorio de medición próxima
# ─────────────────────────────────────────────

MEDICION_PROXIMA = [
    ("📏 Se acerca tu medición", "En un día toca registrar tu peso y medidas. ¿Listo?"),
    ("⏰ Mañana es el día", "Recuerda que mañana registras tu medición. Sigue así 💪"),
    ("📊 Casi es hora", "En menos de 24 horas toca tu próxima medición. ¡Vamos!"),
    ("Checklist pendiente 📋", "Tu próxima medición está a la vuelta de la esquina."),
    ("¿Ya te pesaste? ⚖️", "Mañana toca registrar tu progreso. No te lo pierdas."),
]

MEDICION_HOY = [
    ("📏 ¡Hoy es tu día de medición!", "Registra tu peso y medidas para ver tu avance. ¡Puedes!"),
    ("⚖️ Toca medirse hoy", "Haz tu registro de hoy y revisa cuánto has avanzado."),
    ("📊 Día de seguimiento", "Hoy corresponde tu medición física. Entra a registrarla."),
    ("¡Es hoy! 🎯", "Tu fecha de medición llegó. Registra y celebra tu progreso."),
    ("Día de check-in 📋", "Es tu momento de ver el avance real. ¿Entramos?"),
]

MOTIVACION_PROGRESO = [
    ("💪 ¡{progreso}% del camino recorrido!", "Ya llevas {dias} registros. Sigue así que se nota el esfuerzo."),
    ("🎯 {progreso}% hacia tu meta", "Cada registro cuenta. Llevas {dias} días apostando por ti."),
    ("📈 Vas muy bien: {progreso}%", "Con {dias} mediciones ya se ve el patrón. Confía en el proceso."),
    ("🌱 {dias} días de compromiso", "Eso no es poca cosa. Tu progreso actual: {progreso}%. ¡Orgulloso/a!"),
    ("¡{progreso}% logrado! 🏅", "Llevas {dias} registros seguidos. Eso es constancia real."),
]


def get_copy_medicion_proxima() -> tuple[str, str]:
    return random.choice(MEDICION_PROXIMA)


def get_copy_medicion_hoy() -> tuple[str, str]:
    return random.choice(MEDICION_HOY)


def get_copy_motivacion_progreso(progreso: int = 0, dias: int = 0) -> tuple[str, str]:
    titulo, msg = random.choice(MOTIVACION_PROGRESO)
    titulo = titulo.replace("{progreso}", str(progreso)).replace("{dias}", str(dias))
    msg = msg.replace("{progreso}", str(progreso)).replace("{dias}", str(dias))
    return titulo, msg