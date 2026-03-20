from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recetas', '0002_alter_clasificacionreceta_justificacion_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='clasificacionreceta',
            name='dislipidemia',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='clasificacionreceta',
            name='indigestion',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='clasificacionreceta',
            name='hipertiroidismo',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='clasificacionreceta',
            name='anemia_ferropenica',
            field=models.BooleanField(default=False),
        ),
    ]
