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
        # ✅ PostgreSQL: jsonb_array_length en lugar de JSON_LENGTH (MySQL)
        migrations.RunSQL(
            sql="""
                UPDATE nutricion_formularionutricionguardado
                SET condiciones_medicas_json = json_build_array(condicion_medica)
                WHERE condicion_medica IS NOT NULL
                  AND condicion_medica != ''
                  AND (
                      condiciones_medicas_json IS NULL
                      OR jsonb_array_length(condiciones_medicas_json::jsonb) = 0
                  );
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]