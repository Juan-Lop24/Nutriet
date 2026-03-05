from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Usuarios', '0005_verificacioncodigo'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='notificaciones_configuradas',
            field=models.BooleanField(default=False),
        ),
    ]
