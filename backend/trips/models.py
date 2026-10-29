import uuid
from django.conf import settings
from django.db import models


class RegistroViaje(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="viajes"
    )
    recorrido = models.ForeignKey("transport.Recorrido", on_delete=models.PROTECT)
    inicio = models.ForeignKey(
        "transport.RecorridoParada",
        on_delete=models.PROTECT,
        related_name="viajes_iniciados",
    )
    fin = models.ForeignKey(
        "transport.RecorridoParada",
        on_delete=models.PROTECT,
        related_name="viajes_finalizados",
    )
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    idempotency_key = models.UUIDField(default=uuid.uuid4)
    resultado = models.JSONField(default=dict)

    class Meta:
        ordering = ["-fecha", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "idempotency_key"], name="trip_user_key_unique"
            )
        ]


class UsuarioLineaParada(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="paradas_transitadas",
    )
    linea = models.ForeignKey("transport.Linea", on_delete=models.PROTECT)
    parada = models.ForeignKey("transport.Parada", on_delete=models.PROTECT)
    primer_viaje = models.ForeignKey(RegistroViaje, on_delete=models.PROTECT)
    primera_fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "linea", "parada"],
                name="usuario_linea_parada_unique",
            )
        ]
