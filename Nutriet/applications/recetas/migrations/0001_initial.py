from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="RecetaMealDB",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("meal_id",            models.CharField(db_index=True, max_length=20, unique=True)),
                ("nombre",             models.CharField(db_index=True, max_length=255)),
                ("nombre_es",          models.CharField(blank=True, max_length=255, null=True)),
                ("categoria",          models.CharField(blank=True, max_length=100, null=True)),
                ("area",               models.CharField(blank=True, max_length=100, null=True)),
                ("imagen_url",         models.URLField(blank=True, max_length=500, null=True)),
                ("youtube_url",        models.URLField(blank=True, max_length=500, null=True)),
                ("fuente_url",         models.URLField(blank=True, max_length=500, null=True)),
                ("etiquetas",          models.CharField(blank=True, max_length=500, null=True)),
                ("instrucciones_raw",  models.TextField(blank=True, null=True)),
                ("ingredientes_json",  models.JSONField(blank=True, default=list)),
                ("calorias_estimadas", models.FloatField(blank=True, null=True)),
                ("proteinas_g",        models.FloatField(blank=True, null=True)),
                ("carbohidratos_g",    models.FloatField(blank=True, null=True)),
                ("grasas_g",           models.FloatField(blank=True, null=True)),
                ("fibra_g",            models.FloatField(blank=True, null=True)),
                ("sodio_mg",           models.FloatField(blank=True, null=True)),
                ("azucares_g",         models.FloatField(blank=True, null=True)),
                ("grasas_saturadas_g", models.FloatField(blank=True, null=True)),
                ("clasificado",        models.BooleanField(db_index=True, default=False)),
                ("clasificado_en",     models.DateTimeField(blank=True, null=True)),
                ("error_clasificacion",models.TextField(blank=True, null=True)),
                ("importado_en",       models.DateTimeField(auto_now_add=True)),
                ("actualizado_en",     models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Receta MealDB", "verbose_name_plural": "Recetas MealDB", "ordering": ["nombre"]},
        ),
        migrations.CreateModel(
            name="ClasificacionReceta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("receta",                models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="clasificacion", to="recetas.recetamealdb")),
                ("diabetes",              models.BooleanField(default=False)),
                ("intolerancia_lactosa",  models.BooleanField(default=False)),
                ("celiaca",               models.BooleanField(default=False)),
                ("alergia_mani",          models.BooleanField(default=False)),
                ("intolerancia_fructosa", models.BooleanField(default=False)),
                ("hipertension",          models.BooleanField(default=False)),
                ("hipercolesterolemia",   models.BooleanField(default=False)),
                ("alergia_huevo",         models.BooleanField(default=False)),
                ("alergia_marisco",       models.BooleanField(default=False)),
                ("justificacion",         models.JSONField(blank=True, default=dict)),
                ("dificultad",            models.CharField(blank=True, choices=[("facil", "Fácil"), ("media", "Media"), ("dificil", "Difícil")], max_length=20, null=True)),
                ("tiempo_prep_min",       models.IntegerField(blank=True, null=True)),
                ("clasificado_en",        models.DateTimeField(auto_now_add=True)),
                ("version_prompt",        models.CharField(default="v1", max_length=10)),
            ],
            options={"verbose_name": "Clasificación de Receta", "verbose_name_plural": "Clasificaciones de Recetas"},
        ),
    ]
