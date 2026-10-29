from django.contrib import admin
from config.admin import AuditReadOnlyAdmin
from .models import Nivel, Logro, UsuarioLogro, EventoPuntos


@admin.register(Nivel)
class LevelAdmin(admin.ModelAdmin):
    list_display = ["numero", "nombre", "puntos_minimos"]


@admin.register(Logro)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ["nombre", "regla", "objetivo", "puntos", "activo"]
    list_filter = ["regla", "activo"]
    search_fields = ["nombre", "slug"]


@admin.register(EventoPuntos)
class PointsAdmin(AuditReadOnlyAdmin):
    list_display = ["usuario", "tipo", "puntos", "fecha"]
    list_filter = ["tipo", "fecha"]
    search_fields = ["usuario__username", "clave"]


@admin.register(UsuarioLogro)
class EarnedAdmin(AuditReadOnlyAdmin):
    list_display = ["usuario", "logro", "fecha"]
    search_fields = ["usuario__username", "logro__nombre"]
