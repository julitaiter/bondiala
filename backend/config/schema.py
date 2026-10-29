from rest_framework import serializers
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class SessionScheme(OpenApiAuthenticationExtension):
    target_class = "config.security.CsrfSessionAuthentication"
    name = "djangoSession"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "sessionid",
            "description": "Sesión Django. Operaciones de escritura requieren también X-CSRFToken obtenido en auth/csrf/.",
        }


class FractionSchema(serializers.Serializer):
    total = serializers.IntegerField()
    transitadas = serializers.IntegerField()
    porcentaje = serializers.FloatField()
    completo = serializers.BooleanField()


class DirectionSchema(FractionSchema):
    id = serializers.IntegerField()
    sentido = serializers.CharField()


class BranchSchema(FractionSchema):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    recorridos = DirectionSchema(many=True)


class ProgressSchema(FractionSchema):
    linea = serializers.IntegerField()
    numero = serializers.CharField()
    ramales = BranchSchema(many=True)


class UserSummarySchema(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    nickname = serializers.CharField()
    avatar = serializers.URLField(allow_blank=True)
    follow_id = serializers.IntegerField(allow_null=True, required=False)


class NextLevelSchema(serializers.Serializer):
    numero = serializers.IntegerField()
    puntos_minimos = serializers.IntegerField()


class LevelSchema(NextLevelSchema):
    nombre = serializers.CharField()
    siguiente = NextLevelSchema(allow_null=True)


class ProfileSchema(UserSummarySchema):
    puntos = serializers.IntegerField()
    nivel = LevelSchema()
    paradas = serializers.IntegerField()
    lineas_recorridas = serializers.IntegerField()
    ramales_completos = serializers.IntegerField()
    lineas_completas = serializers.IntegerField()
    ranking_global = serializers.IntegerField(allow_null=True)
    ranking_semanal = serializers.IntegerField(allow_null=True)
    lineas = ProgressSchema(many=True)
    logros = serializers.ListField(child=serializers.DictField())
    email = serializers.EmailField(required=False)
    public_profile = serializers.BooleanField(required=False)
    theme = serializers.CharField(required=False)
    ranking_amigos = serializers.IntegerField(required=False, allow_null=True)


class MeSchema(serializers.Serializer):
    user = ProfileSchema(allow_null=True)


class MessageSchema(serializers.Serializer):
    detail = serializers.CharField()


class StatusSchema(serializers.Serializer):
    muestra = serializers.BooleanField()


class CsrfSchema(serializers.Serializer):
    csrfToken = serializers.CharField()


class RankingSchema(UserSummarySchema):
    posicion = serializers.IntegerField()
    puntos = serializers.IntegerField()
    nivel = LevelSchema()


class RankingPageSchema(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = RankingSchema(many=True)


class AchievementSchema(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField()
    nombre = serializers.CharField()
    descripcion = serializers.CharField()
    regla = serializers.CharField()
    objetivo = serializers.IntegerField()
    puntos = serializers.IntegerField()
    progreso = serializers.IntegerField()
    obtenido = serializers.BooleanField()
    fecha = serializers.DateTimeField(allow_null=True)


class AchievementPageSchema(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = AchievementSchema(many=True)


class FollowSchema(serializers.Serializer):
    id = serializers.IntegerField()
    usuario = UserSummarySchema()


class FollowPageSchema(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = FollowSchema(many=True)
