from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('calendario', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='actividad',
            name='usuario',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='actividades_calendario',
                to=settings.AUTH_USER_MODEL,
                help_text='Usuario dueño de esta actividad',
            ),
        ),
        migrations.AddField(
            model_name='actividad',
            name='notificacion_enviada',
            field=models.BooleanField(
                default=False,
                help_text='True cuando ya se envió la notificación previa de este evento',
            ),
        ),
        migrations.AddIndex(
            model_name='actividad',
            index=models.Index(fields=['usuario', 'fecha'], name='cal_usuario_fecha_idx'),
        ),
        migrations.AddIndex(
            model_name='actividad',
            index=models.Index(fields=['fecha', 'hora'], name='cal_fecha_hora_idx'),
        ),
    ]
