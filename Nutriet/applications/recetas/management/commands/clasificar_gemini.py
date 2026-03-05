# applications/recetas/management/commands/clasificar_gemini.py
"""
Management command que clasifica en batch las recetas de TheMealDB usando Gemini.

Para cada RecetaMealDB sin clasificar:
  1. Llama a Gemini con el prompt de clasificación
  2. Guarda macros en RecetaMealDB
  3. Crea/actualiza ClasificacionReceta

Uso:
    python manage.py clasificar_gemini                # Procesa todas las sin clasificar
    python manage.py clasificar_gemini --limite 100   # Solo 100 recetas
    python manage.py clasificar_gemini --reclasificar # Reclasifica aunque ya estén
    python manage.py clasificar_gemini --receta 12345 # Solo una receta específica
"""

import time
from django.core.management.base import BaseCommand
from applications.recetas.models import RecetaMealDB
from applications.recetas.services.gemini_clasificador import (
    clasificar_receta,
    aplicar_clasificacion,
    VERSION_PROMPT,
)


class Command(BaseCommand):
    help = "Clasifica recetas de MealDB con Gemini (restricciones + macros)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limite", type=int, default=0,
            help="Máximo de recetas a clasificar en esta ejecución (0 = sin límite)"
        )
        parser.add_argument(
            "--reclasificar", action="store_true",
            help="Reclasifica recetas que ya tienen clasificación"
        )
        parser.add_argument(
            "--receta", type=str, default=None,
            help="meal_id de una receta específica para clasificar/probar"
        )
        parser.add_argument(
            "--delay", type=float, default=1.5,
            help="Segundos entre llamadas a Gemini para respetar rate limits (default: 1.5)"
        )
        parser.add_argument(
            "--verbose", action="store_true",
            help="Mostrar el resultado de cada clasificación en detalle"
        )

    def handle(self, *args, **options):
        limite       = options["limite"]
        reclasificar = options["reclasificar"]
        meal_id_solo = options["receta"]
        delay        = options["delay"]
        verbose      = options["verbose"]

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n🤖 Clasificando recetas con Gemini...\n"
        ))

        # ── Seleccionar recetas a procesar ────────────────────────────────────
        if meal_id_solo:
            qs = RecetaMealDB.objects.filter(meal_id=meal_id_solo)
            if not qs.exists():
                self.stderr.write(f"❌ No se encontró la receta con meal_id={meal_id_solo}")
                return
        elif reclasificar:
            qs = RecetaMealDB.objects.all().order_by("id")
        else:
            qs = RecetaMealDB.objects.filter(clasificado=False).order_by("id")

        if limite:
            qs = qs[:limite]

        total = qs.count()
        self.stdout.write(f"→ Recetas a clasificar: {total}\n")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("✅ No hay recetas pendientes de clasificar."))
            return

        # ── Estadísticas ──────────────────────────────────────────────────────
        ok        = 0
        errores   = 0
        omitidas  = 0

        for idx, receta in enumerate(qs, 1):
            # Omitir si ya está clasificada con la versión actual (a menos que --reclasificar)
            if (not reclasificar and receta.clasificado and
                    hasattr(receta, "clasificacion") and
                    receta.clasificacion.version_prompt == VERSION_PROMPT):
                omitidas += 1
                continue

            try:
                time.sleep(delay)
                resultado = clasificar_receta(receta)

                if verbose:
                    self.stdout.write(f"\n   📋 {receta.nombre}")
                    self.stdout.write(f"      Nombre ES: {resultado.get('nombre_es')}")
                    incompatibles = [
                        k for k, v in resultado.get("restricciones", {}).items() if v
                    ]
                    self.stdout.write(
                        f"      Incompatible con: {', '.join(incompatibles) if incompatibles else 'ninguna'}"
                    )
                    m = resultado.get("macros", {})
                    self.stdout.write(
                        f"      Macros: {m.get('calorias')} kcal | "
                        f"P:{m.get('proteinas_g')}g C:{m.get('carbohidratos_g')}g G:{m.get('grasas_g')}g"
                    )
                else:
                    if idx % 25 == 0 or idx == total:
                        self.stdout.write(
                            f"   [{idx}/{total}] ✅ {receta.nombre[:45]}"
                        )

                aplicar_clasificacion(receta, resultado)
                ok += 1

            except Exception as e:
                errores += 1
                # Guardar error en el modelo para no reintentar en la próxima corrida
                receta.error_clasificacion = str(e)[:500]
                receta.save(update_fields=["error_clasificacion"])
                self.stderr.write(
                    f"   [{idx}/{total}] ❌ Error en '{receta.nombre}': {e}"
                )

        # ── Resumen ───────────────────────────────────────────────────────────
        from applications.recetas.models import ClasificacionReceta
        total_clasificadas = ClasificacionReceta.objects.count()

        self.stdout.write("\n" + "─" * 50)
        self.stdout.write(self.style.SUCCESS(
            f"✅ Clasificación completada:\n"
            f"   Procesadas OK:      {ok}\n"
            f"   Errores:            {errores}\n"
            f"   Omitidas (ya OK):   {omitidas}\n"
            f"   Total clasificadas en BD: {total_clasificadas}\n"
            f"   Pendientes:         "
            f"{RecetaMealDB.objects.filter(clasificado=False).count()}"
        ))
