import json
from drf_spectacular.utils import extend_schema_field
from config.schema import ProgressSchema
from rest_framework import serializers
from .models import Linea, LineaColor, Recorrido, Parada, RecorridoParada
from .services import line_progress, route_availability


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaColor
        fields = [
            "color_principal",
            "color_secundario_1",
            "color_secundario_2",
            "color_texto",
        ]


class LineSerializer(serializers.ModelSerializer):
    colores = ColorSerializer(read_only=True)
    progreso = serializers.SerializerMethodField()
    ramales_count = serializers.SerializerMethodField()

    class Meta:
        model = Linea
        fields = ["id", "numero", "nombre", "colores", "ramales_count", "progreso"]

    @extend_schema_field(ProgressSchema)
    def get_progreso(self, obj):
        return line_progress(obj, self.context.get("visited", {}).get(obj.pk, set()))

    def get_ramales_count(self, obj) -> int:
        return len(obj.ramales.all())


class StopSerializer(serializers.ModelSerializer):
    coordenadas = serializers.SerializerMethodField()
    is_official = serializers.BooleanField(source="es_oficial", read_only=True)

    class Meta:
        model = Parada
        fields = [
            "id",
            "nombre",
            "direccion",
            "esquina",
            "barrio",
            "comuna",
            "coordenadas",
            "is_official",
        ]

    def get_coordenadas(self, obj) -> list[float]:
        return list(obj.ubicacion.coords)


class SequenceSerializer(serializers.ModelSerializer):
    parada = StopSerializer(read_only=True)
    transitada = serializers.SerializerMethodField()

    class Meta:
        model = RecorridoParada
        fields = ["id", "orden", "parada", "transitada"]

    def get_transitada(self, obj) -> bool:
        visited = self.context.get("visited_stops")
        if visited is None:
            visited = self.context.get("visited", {}).get(
                obj.recorrido.ramal.linea_id, set()
            )
        return obj.parada_id in visited


class RouteSerializer(serializers.ModelSerializer):
    linea = serializers.IntegerField(source="ramal.linea_id", read_only=True)
    ramal_nombre = serializers.CharField(source="ramal.nombre", read_only=True)
    linea_numero = serializers.CharField(source="ramal.linea.numero", read_only=True)
    colores = ColorSerializer(source="ramal.linea.colores", read_only=True)
    geometria = serializers.SerializerMethodField()
    paradas = SequenceSerializer(source="secuencia", many=True, read_only=True)
    desde = serializers.SerializerMethodField()
    hasta = serializers.SerializerMethodField()
    modalidad = serializers.SerializerMethodField()
    jurisdiccion = serializers.SerializerMethodField()
    camara = serializers.SerializerMethodField()
    paradas_oficiales_count = serializers.SerializerMethodField()
    puede_registrar_viaje = serializers.SerializerMethodField()
    estado_datos = serializers.SerializerMethodField()
    requiere_rematch = serializers.BooleanField(read_only=True)

    class Meta:
        model = Recorrido
        fields = [
            "id",
            "external_id",
            "ramal",
            "ramal_nombre",
            "linea",
            "linea_numero",
            "sentido",
            "desde",
            "hasta",
            "modalidad",
            "jurisdiccion",
            "camara",
            "colores",
            "geometria",
            "paradas",
            "paradas_oficiales_count",
            "puede_registrar_viaje",
            "estado_datos",
            "requiere_rematch",
        ]

    def get_paradas_oficiales_count(self, obj) -> int:
        return route_availability(obj)["paradas_oficiales_count"]

    def get_puede_registrar_viaje(self, obj) -> bool:
        return route_availability(obj)["puede_registrar_viaje"]

    def get_estado_datos(self, obj) -> str:
        return route_availability(obj)["estado_datos"]

    @extend_schema_field(
        {
            "type": "object",
            "nullable": True,
            "properties": {
                "type": {"type": "string", "enum": ["MultiLineString"]},
                "coordinates": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "number"}},
                    },
                },
            },
        }
    )
    def get_geometria(self, obj):
        return json.loads(obj.geometria.geojson) if obj.geometria is not None else None

    def get_desde(self, obj) -> str:
        return obj.metadata.get("desde", "")

    def get_hasta(self, obj) -> str:
        return obj.metadata.get("hasta", "")

    def get_modalidad(self, obj) -> str:
        return obj.metadata.get("modalidad") or ""

    def get_jurisdiccion(self, obj) -> str:
        return obj.metadata.get("jurisdicci") or ""

    def get_camara(self, obj) -> str:
        return obj.metadata.get("camara") or ""
