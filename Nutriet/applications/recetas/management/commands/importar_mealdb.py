# applications/recetas/management/commands/importar_mealdb.py
"""
Management command para importar recetas de TheMealDB a la BD local.

TheMealDB API (con API key premium) permite:
  - /api/json/v2/{API_KEY}/categories.php     → categorías
  - /api/json/v2/{API_KEY}/filter.php?c={cat} → IDs de recetas por categoría
  - /api/json/v2/{API_KEY}/lookup.php?i={id}  → detalle completo de una receta

Sin API key premium, usa la key "1" (versión free, misma estructura).

Uso:
    python manage.py importar_mealdb
    python manage.py importar_mealdb --api-key TU_KEY_PREMIUM
    python manage.py importar_mealdb --categoria Chicken --limite 50
    python manage.py importar_mealdb --solo-faltantes   # Solo las que no están en BD
"""

import time
import requests
from django.core.management.base import BaseCommand
from applications.recetas.models import RecetaMealDB


# ── Endpoints TheMealDB ───────────────────────────────────────────────────────
BASE_URL = "https://www.themealdb.com/api/json/v2/{key}"

HEADERS = {
    "User-Agent": "Nutriet-App/1.0",
    "Accept": "application/json",
}


def _get(url: str, params: dict = None, reintentos: int = 3) -> dict | None:
    """GET con reintentos y timeout."""
    for intento in range(reintentos):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            if r.status_code == 429:
                # Rate limit — esperar y reintentar
                wait = 5 * (intento + 1)
                time.sleep(wait)
            else:
                raise e
        except Exception as e:
            if intento < reintentos - 1:
                time.sleep(2)
            else:
                raise e
    return None


def _parsear_ingredientes(meal: dict) -> list[dict]:
    """
    TheMealDB guarda ingredientes como strIngredient1..20 y medidas strMeasure1..20.
    Los convierte en lista de dicts [{ingrediente, medida}].
    """
    resultado = []
    for i in range(1, 21):
        ing = (meal.get(f"strIngredient{i}") or "").strip()
        med = (meal.get(f"strMeasure{i}") or "").strip()
        if ing:
            resultado.append({"ingrediente": ing, "medida": med})
    return resultado


class Command(BaseCommand):
    help = "Importa recetas de TheMealDB a la base de datos local"

    def add_arguments(self, parser):
        parser.add_argument(
            "--api-key", default="1",
            help="API key de TheMealDB (default: '1' = versión free)"
        )
        parser.add_argument(
            "--categoria", default=None,
            help="Importar solo una categoría específica (ej: Chicken)"
        )
        parser.add_argument(
            "--limite", type=int, default=0,
            help="Máximo de recetas a importar (0 = sin límite)"
        )
        parser.add_argument(
            "--solo-faltantes", action="store_true",
            help="Solo importar recetas que no están en la BD"
        )
        parser.add_argument(
            "--delay", type=float, default=0.3,
            help="Segundos entre peticiones para no sobrecargar la API (default: 0.3)"
        )

    def handle(self, *args, **options):
        api_key        = options["api_key"]
        solo_categoria = options["categoria"]
        limite         = options["limite"]
        solo_faltantes = options["solo_faltantes"]
        delay          = options["delay"]

        base = BASE_URL.format(key=api_key)

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n🍽️  Importando recetas de TheMealDB (key: {api_key[:4]}...)\n"
        ))

        # ── 1. Obtener categorías ─────────────────────────────────────────────
        self.stdout.write("→ Obteniendo categorías...")
        data = _get(f"{base}/categories.php")
        if not data or not data.get("categories"):
            self.stderr.write("❌ No se pudieron obtener las categorías.")
            return

        categorias = [c["strCategory"] for c in data["categories"]]

        if solo_categoria:
            if solo_categoria not in categorias:
                self.stderr.write(
                    f"❌ Categoría '{solo_categoria}' no encontrada. "
                    f"Disponibles: {', '.join(categorias)}"
                )
                return
            categorias = [solo_categoria]

        self.stdout.write(f"   Categorías a procesar: {', '.join(categorias)}\n")

        # ── 2. Obtener IDs por categoría ──────────────────────────────────────
        todos_los_ids = []
        for cat in categorias:
            time.sleep(delay)
            data = _get(f"{base}/filter.php", {"c": cat})
            if data and data.get("meals"):
                ids_cat = [m["idMeal"] for m in data["meals"]]
                todos_los_ids.extend(ids_cat)
                self.stdout.write(f"   {cat}: {len(ids_cat)} recetas")
            else:
                self.stdout.write(f"   {cat}: sin resultados")

        # Deduplicar
        todos_los_ids = list(dict.fromkeys(todos_los_ids))

        # Filtrar ya importadas si se pide
        if solo_faltantes:
            ya_en_bd = set(
                RecetaMealDB.objects.values_list("meal_id", flat=True)
            )
            antes = len(todos_los_ids)
            todos_los_ids = [i for i in todos_los_ids if i not in ya_en_bd]
            self.stdout.write(
                f"\n   Ya en BD: {len(ya_en_bd)} | Faltantes: {len(todos_los_ids)} "
                f"(de {antes} totales)"
            )

        if limite:
            todos_los_ids = todos_los_ids[:limite]

        total = len(todos_los_ids)
        self.stdout.write(f"\n→ Total a importar: {total} recetas\n")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("✅ Nada que importar."))
            return

        # ── 3. Importar detalle de cada receta ────────────────────────────────
        creadas = 0
        actualizadas = 0
        errores = 0

        for idx, meal_id in enumerate(todos_los_ids, 1):
            time.sleep(delay)
            try:
                data = _get(f"{base}/lookup.php", {"i": meal_id})
                if not data or not data.get("meals"):
                    self.stdout.write(f"   [{idx}/{total}] {meal_id}: sin datos")
                    errores += 1
                    continue

                meal = data["meals"][0]
                ingredientes = _parsear_ingredientes(meal)

                defaults = {
                    "nombre":             meal.get("strMeal", ""),
                    "categoria":          meal.get("strCategory", ""),
                    "area":               meal.get("strArea", ""),
                    "imagen_url":         meal.get("strMealThumb", ""),
                    "youtube_url":        meal.get("strYoutube", ""),
                    "fuente_url":         meal.get("strSource", ""),
                    "etiquetas":          meal.get("strTags", ""),
                    "instrucciones_raw":  meal.get("strInstructions", ""),
                    "ingredientes_json":  ingredientes,
                }

                obj, created = RecetaMealDB.objects.update_or_create(
                    meal_id  = meal_id,
                    defaults = defaults,
                )

                status = "✅ NUEVA" if created else "♻️  ACT"
                if created:
                    creadas += 1
                else:
                    actualizadas += 1

                if idx % 50 == 0 or idx == total:
                    self.stdout.write(
                        f"   [{idx}/{total}] {status} — {meal.get('strMeal', meal_id)[:50]}"
                    )

            except Exception as e:
                errores += 1
                self.stderr.write(f"   [{idx}/{total}] ❌ Error en {meal_id}: {e}")

        # ── Resumen ───────────────────────────────────────────────────────────
        self.stdout.write("\n" + "─" * 50)
        self.stdout.write(self.style.SUCCESS(
            f"✅ Importación completada:\n"
            f"   Nuevas:       {creadas}\n"
            f"   Actualizadas: {actualizadas}\n"
            f"   Errores:      {errores}\n"
            f"   Total en BD:  {RecetaMealDB.objects.count()}"
        ))
