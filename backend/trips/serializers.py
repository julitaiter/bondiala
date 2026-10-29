import uuid
from rest_framework import serializers
from accounts.serializers import StrictSerializer
from .models import RegistroViaje


class TripInputSerializer(StrictSerializer):
    recorrido = serializers.IntegerField(min_value=1)
    inicio = serializers.IntegerField(min_value=1)
    fin = serializers.IntegerField(min_value=1)
    idempotency_key = serializers.UUIDField(default=uuid.uuid4)


class TripSerializer(serializers.ModelSerializer):
    linea_numero = serializers.CharField(
        source="recorrido.ramal.linea.numero", read_only=True
    )
    ramal_nombre = serializers.CharField(
        source="recorrido.ramal.nombre", read_only=True
    )
    sentido = serializers.CharField(source="recorrido.sentido", read_only=True)
    inicio_nombre = serializers.CharField(source="inicio.parada.nombre", read_only=True)
    fin_nombre = serializers.CharField(source="fin.parada.nombre", read_only=True)

    class Meta:
        model = RegistroViaje
        fields = [
            "id",
            "recorrido",
            "linea_numero",
            "ramal_nombre",
            "sentido",
            "inicio",
            "fin",
            "inicio_nombre",
            "fin_nombre",
            "fecha",
            "resultado",
            "idempotency_key",
        ]
        read_only_fields = fields
