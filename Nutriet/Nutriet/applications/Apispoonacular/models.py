from django.db import models
from django.contrib.auth import get_user_model
import hashlib, json

User = get_user_model()


class RecetaFavorita(models.Model):
    usuario    = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe_id  = models.IntegerField()
    titulo     = models.CharField(max_length=255)
    imagen     = models.URLField(blank=True, null=True)
    creado_en  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("usuario", "recipe_id"),)

    def __str__(self):
        return f"{self.usuario} - {self.titulo}"


class RecetaCache(models.Model):

    clave       = models.CharField(max_length=64, unique=True)   # SHA-256 de params
    recetas_json = models.JSONField()                              # lista de recetas
    creado_en   = models.DateTimeField(auto_now_add=True)
    expira_en   = models.DateTimeField()

    @staticmethod
    def generar_clave(params: dict) -> str:
        raw = json.dumps(params, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def __str__(self):
        return f"Cache {self.clave[:12]}… ({self.creado_en.date()})"

    class Meta:
        verbose_name = "Caché de Recetas"
        verbose_name_plural = "Caché de Recetas"
