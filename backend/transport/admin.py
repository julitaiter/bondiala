from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.db.models import Count, Q
from .models import Linea, LineaColor, Ramal, Recorrido, Parada, RecorridoParada


@admin.register(Linea)
class LineAdmin(admin.ModelAdmin):
    list_display = ["numero", "nombre", "activa", "source", "colores"]
    search_fields = ["numero", "nombre", "external_id"]
    list_filter = ["activa", "source"]
    readonly_fields = ["updated_at"]


@admin.register(LineaColor)
class ColorAdmin(admin.ModelAdmin):
    list_display = [
        "color_principal",
        "color_secundario_1",
        "color_secundario_2",
        "color_texto",
    ]


@admin.register(Ramal)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["linea", "nombre", "activo"]
    list_filter = ["activo"]
    search_fields = ["linea__numero", "nombre"]
    autocomplete_fields = ["linea"]


class SequenceInline(admin.TabularInline):
    model = RecorridoParada
    fields = [
        "orden",
        "parada",
        "activa",
        "metodo",
        "distancia_metros",
        "posicion_metros",
        "source",
    ]
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Recorrido)
class RouteAdmin(GISModelAdmin):
    list_display = [
        "external_id",
        "ramal",
        "sentido",
        "activo",
        "tiene_geometria",
        "cantidad_paradas",
        "paradas_oficiales",
    ]
    list_filter = ["activo", "sentido", "source"]
    search_fields = ["external_id", "ramal__linea__numero"]
    readonly_fields = [
        "source",
        "external_id",
        "ramal",
        "sentido",
        "checksum",
        "catalogue_format",
        "geometria_source",
        "updated_at",
    ]
    inlines = [SequenceInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("ramal__linea")
            .annotate(
                total_count=Count("secuencia", filter=Q(secuencia__activa=True)),
                official_count=Count(
                    "secuencia",
                    filter=Q(
                        secuencia__activa=True,
                        secuencia__parada__es_oficial=True,
                        secuencia__parada__activa=True,
                    ),
                ),
            )
        )

    @admin.display(boolean=True, description="Geometría")
    def tiene_geometria(self, obj):
        return obj.geometria is not None

    @admin.display(description="Paradas oficiales")
    def paradas_oficiales(self, obj):
        return f"{obj.official_count}/{obj.total_count}"

    @admin.display(description="Paradas activas")
    def cantidad_paradas(self, obj):
        return obj.total_count


@admin.register(Parada)
class StopAdmin(GISModelAdmin):
    list_display = [
        "external_id",
        "nombre",
        "es_oficial",
        "es_ilustrativa",
        "activa",
        "barrio",
        "comuna",
        "source",
    ]
    search_fields = ["external_id", "nombre", "direccion"]
    list_filter = ["es_oficial", "activa", "source", "barrio"]
    readonly_fields = [
        "external_id",
        "source",
        "enriched_at",
        "updated_at",
        "enrichment",
        "metadata",
        "es_oficial",
    ]
