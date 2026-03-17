from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # Ajusta este número al último migration que tengas
        ('nutricion', '0001_initial'),
    ]

    operations = [
        # 1. Quitar tipo_dieta
        migrations.RemoveField(
            model_name='formularionutricionguardado',
            name='tipo_dieta',
        ),
        # 2. Renombrar restricciones_alimentarias -> ingredientes_excluidos
        migrations.RenameField(
            model_name='formularionutricionguardado',
            old_name='restricciones_alimentarias',
            new_name='ingredientes_excluidos',
        ),
        # 3. Agregar condicion_medica
        migrations.AddField(
            model_name='formularionutricionguardado',
            name='condicion_medica',
            field=models.CharField(
                blank=True,
                default='',
                max_length=30,
                choices=[
                    ('', 'Sin condición médica'),
                    ('diabetes', 'Diabetes'),
                    ('celiaco', 'Celiaco / Sin gluten'),
                    ('lactosa', 'Intolerancia a la lactosa'),
                    ('hipertension', 'Hipertensión'),
                    ('colesterol', 'Colesterol alto'),
                    ('gota', 'Gota'),
                    ('alergia_mani', 'Alergia al maní'),
                    ('alergia_mariscos', 'Alergia a mariscos'),
                    ('alergia_huevo', 'Alergia al huevo'),
                    ('vegetariano', 'Vegetariano'),
                    ('vegano', 'Vegano'),
                ],
            ),
        ),
    ]
