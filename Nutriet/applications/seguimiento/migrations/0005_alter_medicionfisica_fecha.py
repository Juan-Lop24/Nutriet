from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('seguimiento', '0004_preferencia_medicion'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicionfisica',
            name='creado_en',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
