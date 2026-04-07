from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nutricion', '0003_alter_formularionutricionguardado_ingredientes_excluidos'),
    ]

    operations = [
        migrations.AddField(
            model_name='formularionutricionguardado',
            name='condiciones_medicas_json',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Lista de condiciones médicas seleccionadas',
            ),
        ),
        # Migración de datos: poblar condiciones_medicas_json desde condicion_medica legado
        migrations.RunSQL(
            sql="""
                UPDATE nutricion_formularionutricionguardado
                SET condiciones_medicas_json = JSON_ARRAY(condicion_medica)
                WHERE condicion_medica IS NOT NULL AND condicion_medica != ''
                  AND (condiciones_medicas_json IS NULL OR JSON_LENGTH(condiciones_medicas_json) = 0);
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
