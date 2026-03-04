from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('seguimiento', '0003_alter_medicionfisica_options'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PreferenciaMedicion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('frecuencia_dias', models.PositiveIntegerField(
                    choices=[(1, 'Cada 24 horas'), (15, 'Cada 15 días'), (30, 'Cada mes')],
                    default=15,
                    verbose_name='Frecuencia de medición (días)'
                )),
                ('configurada', models.BooleanField(
                    default=False,
                    verbose_name='El usuario ya eligió su frecuencia'
                )),
                ('usuario', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='preferencia_medicion',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Preferencia de Medición',
                'verbose_name_plural': 'Preferencias de Medición',
            },
        ),
    ]
