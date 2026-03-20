from django.db import models
from django.conf import settings

class RestriccionAlimentaria(models.Model):
    nombre = models.CharField(max_length=100)
    intolerancias = models.TextField(blank=True, null=True)
    alergias = models.TextField(blank=True, null=True)
    objetivos = models.TextField(blank=True, null=True)   # bajar de peso, subir masa, tonificar, etc.
    enfermedades = models.TextField(blank=True, null=True) # opcional
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class FormularioNutricionGuardado(models.Model):

    OBJETIVO_CHOICES = [
        ("Aumentar", "Aumentar Masa Muscular"),
        ("Reducir", "Reducir Grasa Corporal"),
        ("Mantener", "Mantener Peso"),
    ]

    ACTIVIDAD_CHOICES = [
        ("sedentario", "Sedentario"),
        ("ligero", "Ligero"),
        ("moderado", "Moderado"),
        ("intenso", "Intenso"),
        ("muy_intenso", "Muy intenso"),
    ]

    CONDICION_CHOICES = [
        ("", "Sin condición médica"),
        ("diabetes", "Diabetes"),
        ("celiaco", "Celiaco / Sin gluten"),
        ("lactosa", "Intolerancia a la lactosa"),
        ("hipertension", "Hipertensión"),
        ("colesterol", "Colesterol alto"),
        ("gota", "Gota"),
        ("alergia_mani", "Alergia al maní"),
        ("alergia_mariscos", "Alergia a mariscos"),
        ("alergia_huevo", "Alergia al huevo"),
        ("vegetariano", "Vegetariano"),
        ("vegano", "Vegano"),
    ]

    SEXO_CHOICES = [
        ("M", "Masculino"),
        ("F", "Femenino"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="formularios_nutricion"
    )

    # 🔹 Datos personales
    sexo = models.CharField(
    max_length=1,
    choices=SEXO_CHOICES,
    null=True,
    blank=True)
    edad = models.IntegerField()
    peso = models.FloatField(help_text="Peso actual en kg")
    altura = models.FloatField(help_text="Altura en cm")

    # 🔹 Composición corporal (AUTO)
    imc = models.FloatField(editable=False, null=True)
    porcentaje_grasa = models.FloatField(editable=False, null=True)

    # 🔹 Objetivos
    objetivo = models.CharField(max_length=20, choices=OBJETIVO_CHOICES)
    peso_objetivo = models.FloatField(help_text="Peso deseado en kg")
    plazo_meses = models.IntegerField(help_text="Tiempo para alcanzar el objetivo en meses")

    # 🔹 Hábitos
    comidas_preferidas = models.CharField(max_length=200)
    nivel_actividad = models.CharField(max_length=20, choices=ACTIVIDAD_CHOICES)

    # Condición médica o alergia (genera exclusiones automáticas en recetas)
    condicion_medica = models.CharField(
        max_length=30, choices=CONDICION_CHOICES, blank=True, default=""
    )

    # Ingredientes que el usuario NO quiere ver en sus recetas (por gusto personal u otra razón)
    ingredientes_excluidos = models.TextField(
        blank=True, null=True,
        help_text="Lista de ingredientes separados por coma que el usuario no quiere en recetas"
    )

    # 🔹 Metadata
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """Calcula IMC y porcentaje de grasa automáticamente"""
        if self.peso and self.altura:
            altura_m = self.altura / 100
            self.imc = round(self.peso / (altura_m ** 2), 2)

            # Cálculo porcentaje de grasa (Deurenberg)
            if self.sexo == "M":
                grasa = (1.20 * self.imc) + (0.23 * self.edad) - 16.2
            else:
                grasa = (1.20 * self.imc) + (0.23 * self.edad) - 5.4

            self.porcentaje_grasa = round(grasa, 2)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Formulario de {self.usuario.username} - {self.creado_en.strftime('%d/%m/%Y')}"

    class Meta:
        verbose_name = "Formulario de Nutrición"
        verbose_name_plural = "Formularios de Nutrición"
        ordering = ['-creado_en']


from django.db import models
from django.conf import settings


class DietaGenerada(models.Model):
    """
    Guarda la dieta generada por IA y sus datos clave
    para seguimiento nutricional
    """

    formulario = models.OneToOneField(
        "nutricion.FormularioNutricionGuardado",
        on_delete=models.CASCADE,
        related_name="dieta_generada"
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dietas_generadas"
    )

    imc = models.FloatField(null=True, blank=True)
    porcentaje_grasa = models.FloatField(null=True, blank=True)

    tmb = models.FloatField(null=True, blank=True)
    tdee = models.FloatField(null=True, blank=True)

    calorias_diarias = models.IntegerField(null=True, blank=True)

    proteinas_gramos = models.IntegerField(null=True, blank=True)
    grasas_gramos = models.IntegerField(null=True, blank=True)
    carbohidratos_gramos = models.IntegerField(null=True, blank=True)

    contenido_dieta = models.JSONField()
    
    # Distribución de macros por comida para Spoonacular
    # Estructura: {"desayuno": {...}, "almuerzo": {...}, ...}
    distribucion_macros_comidas = models.JSONField(
        null=True,
        blank=True,
        help_text="Distribución de calorías y macros por cada comida"
    )
    
    objetivo = models.CharField(
        max_length=50,
        help_text="Objetivo nutricional (definido por el usuario)"
    )

    plazo_meses = models.PositiveIntegerField(
        help_text="Plazo estimado del objetivo en meses"
    )


    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dieta de {self.usuario.username} ({self.creado_en.strftime('%d/%m/%Y')})"

    class Meta:
        verbose_name = "Dieta Generada"
        verbose_name_plural = "Dietas Generadas"
        ordering = ["-creado_en"]
