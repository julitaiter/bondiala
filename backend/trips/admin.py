from django.contrib import admin
from config.admin import AuditReadOnlyAdmin
from .models import RegistroViaje, UsuarioLineaParada


@admin.register(RegistroViaje)
class TripAdmin(AuditReadOnlyAdmin):
    list_display = ["id", "usuario", "recorrido", "fecha"]
    list_filter = ["fecha"]
    search_fields = ["usuario__username", "recorrido__external_id"]


@admin.register(UsuarioLineaParada)
class VisitedAdmin(AuditReadOnlyAdmin):
    list_display = ["usuario", "linea", "parada", "primera_fecha"]
    search_fields = ["usuario__username", "linea__numero", "parada__nombre"]
