# applications/recetas/models.py
"""
Modelos para almacenar y clasificar recetas de TheMealDB.

Flujo:
  1. management/commands/importar_mealdb.py  → llena RecetaMealDB
  2. management/commands/clasificar_gemini.py → llena ClasificacionReceta
  3. views / API                              → filtra recetas según perfil usuario
"""

from django.db import models


# ── Restricciones soportadas (13 condiciones clínicas + alergias) ─────────────
RESTRICCIONES = [
    ("diabetes",             "Diabetes mellitus"),
    ("intolerancia_lactosa", "Intolerancia a la lactosa"),
    ("celiaca",              "Enfermedad celíaca"),
    ("alergia_mani",         "Alergia al maní"),
    ("intolerancia_fructosa","Intolerancia a la fructosa"),
    ("hipertension",         "Hipertensión arterial"),
    ("hipercolesterolemia",  "Hipercolesterolemia"),
    ("dislipidemia",         "Dislipidemias"),
    ("indigestion",          "Indigestión / gastritis"),
    ("hipertiroidismo",      "Hipertiroidismo"),
    ("anemia_ferropenica",   "Anemia ferropénica"),
    ("alergia_huevo",        "Alergia al huevo"),
    ("alergia_marisco",      "Alergia al marisco"),
]

RESTRICCION_KEYS = [r[0] for r in RESTRICCIONES]


class RecetaMealDB(models.Model):
    """
    Receta importada de TheMealDB.
    Guarda los campos crudos del JSON + campos calculados por Gemini.
    """
    # ── Identificación ────────────────────────────────────────────────────────
    meal_id     = models.CharField(max_length=20, unique=True, db_index=True)
    nombre      = models.CharField(max_length=255, db_index=True)
    nombre_es   = models.CharField(max_length=255, blank=True, null=True,
                                   help_text="Nombre traducido al español por Gemini")
    categoria   = models.CharField(max_length=100, blank=True, null=True)
    area        = models.CharField(max_length=100, blank=True, null=True,
                                   help_text="Cocina regional (Italian, Mexican, etc.)")
    imagen_url  = models.URLField(max_length=500, blank=True, null=True)
    youtube_url = models.URLField(max_length=500, blank=True, null=True)
    fuente_url  = models.URLField(max_length=500, blank=True, null=True)
    etiquetas   = models.CharField(max_length=500, blank=True, null=True)

    # ── Contenido crudo (almacenado tal cual viene del JSON) ──────────────────
    instrucciones_raw = models.TextField(blank=True, null=True)
    ingredientes_json = models.JSONField(
        default=list, blank=True,
        help_text='Lista de {"ingrediente": "...", "medida": "..."}'
    )

    # ── Macronutrientes (estimados por Gemini) ────────────────────────────────
    # Por porción estándar (100g o la ración típica del plato)
    calorias_estimadas  = models.FloatField(null=True, blank=True)
    proteinas_g         = models.FloatField(null=True, blank=True)
    carbohidratos_g     = models.FloatField(null=True, blank=True)
    grasas_g            = models.FloatField(null=True, blank=True)
    fibra_g             = models.FloatField(null=True, blank=True)
    sodio_mg            = models.FloatField(null=True, blank=True)
    azucares_g          = models.FloatField(null=True, blank=True)
    grasas_saturadas_g  = models.FloatField(null=True, blank=True)

    # ── Control de clasificación ──────────────────────────────────────────────
    clasificado         = models.BooleanField(default=False, db_index=True)
    clasificado_en      = models.DateTimeField(null=True, blank=True)
    error_clasificacion = models.TextField(blank=True, null=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    importado_en  = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Receta MealDB"
        verbose_name_plural = "Recetas MealDB"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} [{self.meal_id}]"

    @property
    def ingredientes_texto(self):
        """Lista de ingredientes como texto plano para prompts."""
        return ", ".join(
            f"{i['ingrediente']} ({i['medida']})"
            for i in self.ingredientes_json
            if i.get("ingrediente")
        )


class ClasificacionReceta(models.Model):
    """
    Resultado del análisis de Gemini sobre compatibilidad de una receta
    con las restricciones médicas/alimentarias.

    Una fila por receta. Los 9 campos booleanos indican si la receta
    es INCOMPATIBLE con esa restricción (True = no apto).
    """
    receta = models.OneToOneField(
        RecetaMealDB,
        on_delete=models.CASCADE,
        related_name="clasificacion"
    )

    # ── Incompatibilidades (True = receta NO es apta para esa condición) ──────
    diabetes              = models.BooleanField(default=False)
    intolerancia_lactosa  = models.BooleanField(default=False)
    celiaca               = models.BooleanField(default=False)
    alergia_mani          = models.BooleanField(default=False)
    intolerancia_fructosa = models.BooleanField(default=False)
    hipertension          = models.BooleanField(default=False)
    hipercolesterolemia   = models.BooleanField(default=False)
    dislipidemia          = models.BooleanField(default=False)
    indigestion           = models.BooleanField(default=False)
    hipertiroidismo       = models.BooleanField(default=False)
    anemia_ferropenica    = models.BooleanField(default=False)
    alergia_huevo         = models.BooleanField(default=False)
    alergia_marisco       = models.BooleanField(default=False)

    # ── Justificación de Gemini (para auditoría / debug) ─────────────────────
    justificacion = models.JSONField(
        default=dict, blank=True,
        help_text="Dict {restriccion: razon_texto} explicando cada decisión"
    )

    # ── Nivel de dificultad y tiempo (bonus de Gemini) ────────────────────────
    dificultad        = models.CharField(
        max_length=20, blank=True, null=True,
        choices=[("facil", "Fácil"), ("media", "Media"), ("dificil", "Difícil")]
    )
    tiempo_prep_min   = models.IntegerField(null=True, blank=True)

    clasificado_en    = models.DateTimeField(auto_now_add=True)
    version_prompt    = models.CharField(max_length=10, default="v1",
                                         help_text="Versión del prompt usado para reclasificar si cambia")

    class Meta:
        verbose_name = "Clasificación de Receta"
        verbose_name_plural = "Clasificaciones de Recetas"

    def __str__(self):
        return f"Clasificación: {self.receta.nombre}"

    def restricciones_incompatibles(self) -> list[str]:
        """Devuelve lista de claves de restricciones donde la receta es incompatible."""
        return [key for key in RESTRICCION_KEYS if getattr(self, key, False)]

    def es_apta_para(self, restricciones_usuario: list[str]) -> bool:
        """
        True si la receta es compatible con TODAS las restricciones del usuario.
        restricciones_usuario: lista de claves como ["diabetes", "celiaca"]
        """
        for r in restricciones_usuario:
            if getattr(self, r, False):
                return False
        return True
