from django.conf import settings
from django.db import models


class Nivel(models.Model):
    numero = models.PositiveIntegerField(unique=True)
    nombre = models.CharField(max_length=80)
    puntos_minimos = models.PositiveIntegerField(unique=True)

    class Meta:
        ordering = ["puntos_minimos"]

    def __str__(self):
        return f"{self.numero} · {self.nombre}"


class Logro(models.Model):
    slug = models.SlugField(unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=250)
    regla = models.CharField(
        max_length=30,
        choices=[
            (x, x)
            for x in ["paradas", "sentidos", "ramales", "lineas", "barrios", "comunas"]
        ],
    )
    objetivo = models.PositiveIntegerField(default=1)
    puntos = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)


class UsuarioLogro(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="logros"
    )
    logro = models.ForeignKey(Logro, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "logro"], name="usuario_logro_unique"
            )
        ]


class EventoPuntos(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="eventos"
    )
    tipo = models.CharField(
        max_length=25,
        choices=[
            (x, x)
            for x in [
                "PARADA_TRANSITADA",
                "SENTIDO_COMPLETADO",
                "RAMAL_COMPLETADO",
                "LINEA_COMPLETADA",
                "LOGRO",
            ]
        ],
    )
    puntos = models.PositiveIntegerField()
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    clave = models.CharField(max_length=150)
    linea = models.ForeignKey(
        "transport.Linea", null=True, blank=True, on_delete=models.PROTECT
    )
    ramal = models.ForeignKey(
        "transport.Ramal", null=True, blank=True, on_delete=models.PROTECT
    )
    recorrido = models.ForeignKey(
        "transport.Recorrido", null=True, blank=True, on_delete=models.PROTECT
    )
    parada = models.ForeignKey(
        "transport.Parada", null=True, blank=True, on_delete=models.PROTECT
    )
    viaje = models.ForeignKey(
        "trips.RegistroViaje", null=True, blank=True, on_delete=models.PROTECT
    )
    logro = models.ForeignKey(Logro, null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "clave"], name="evento_usuario_clave_unique"
            )
        ]
        indexes = [models.Index(fields=["usuario", "fecha"])]
