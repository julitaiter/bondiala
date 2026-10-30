import re
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


def normalize_line(value):
    text = str(value).strip()
    if not re.fullmatch(r"[0-9]{1,5}", text) or int(text) <= 0:
        raise ValueError("Número de línea inválido")
    return str(int(text))


hex_color = RegexValidator(
    r"^#[0-9A-Fa-f]{6}$", "Usá un color hexadecimal de seis dígitos."
)


class LineaColor(models.Model):
    color_principal = models.CharField(max_length=7, validators=[hex_color])
    color_secundario_1 = models.CharField(max_length=7, validators=[hex_color])
    color_secundario_2 = models.CharField(max_length=7, validators=[hex_color])
    color_texto = models.CharField(max_length=7, validators=[hex_color])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "color_principal",
                    "color_secundario_1",
                    "color_secundario_2",
                    "color_texto",
                ],
                name="unique_linea_color_palette",
            )
        ]

    def save(self, *args, **kwargs):
        for field in (
            "color_principal",
            "color_secundario_1",
            "color_secundario_2",
            "color_texto",
        ):
            setattr(self, field, getattr(self, field).upper())
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.color_principal} / {self.color_secundario_1} / {self.color_secundario_2}"


class Linea(models.Model):
    numero = models.CharField(max_length=5, unique=True)
    nombre = models.CharField(max_length=200, blank=True)
    colores = models.ForeignKey(
        LineaColor,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lineas",
    )
    source = models.ForeignKey(
        "imports.DataSource", null=True, on_delete=models.PROTECT
    )
    external_id = models.CharField(max_length=100, blank=True, db_index=True)
    activa = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        try:
            self.numero = normalize_line(self.numero)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Línea {self.numero}"


class Ramal(models.Model):
    linea = models.ForeignKey(Linea, on_delete=models.PROTECT, related_name="ramales")
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=250, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["linea", "nombre"], name="ramal_linea_nombre_unique"
            )
        ]

    def __str__(self):
        return f"{self.linea} · {self.nombre}"


class Recorrido(models.Model):
    ramal = models.ForeignKey(
        Ramal, on_delete=models.PROTECT, related_name="recorridos"
    )
    sentido = models.CharField(
        max_length=6, choices=[("IDA", "Ida"), ("VUELTA", "Vuelta")]
    )
    external_id = models.CharField(max_length=100, db_index=True)
    source = models.ForeignKey("imports.DataSource", on_delete=models.PROTECT)
    geometria = models.MultiLineStringField(srid=4326, null=True, blank=True)
    geometria_source = models.ForeignKey(
        "imports.DataSource",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="geometrias",
    )
    catalogue_format = models.CharField(
        max_length=7,
        choices=[("csv", "CSV"), ("geojson", "GeoJSON")],
        default="geojson",
    )
    metadata = models.JSONField(default=dict, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    activo = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                name="recorrido_source_external_unique",
            ),
            models.UniqueConstraint(
                fields=["ramal", "sentido"], name="recorrido_ramal_sentido_unique"
            ),
        ]

    def __str__(self):
        return f"{self.ramal} · {self.sentido}"


class Parada(models.Model):
    source = models.ForeignKey("imports.DataSource", on_delete=models.PROTECT)
    external_id = models.CharField(max_length=100, db_index=True)
    nombre = models.CharField(max_length=250, blank=True)
    ubicacion = models.PointField(srid=4326)
    direccion = models.CharField(max_length=250, blank=True)
    esquina = models.CharField(max_length=200, blank=True)
    barrio = models.CharField(max_length=100, blank=True)
    comuna = models.CharField(max_length=30, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    enrichment = models.JSONField(default=dict, blank=True)
    enriched_at = models.DateTimeField(null=True, blank=True)
    es_oficial = models.BooleanField(default=False, db_index=True)
    activa = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"], name="parada_source_external_unique"
            )
        ]

    def __str__(self):
        return self.nombre or self.external_id

    @property
    def es_ilustrativa(self):
        return not self.es_oficial and (
            self.source.slug == "muestra-paradas"
            or self.metadata.get("illustrative", False)
        )


class RecorridoParada(models.Model):
    recorrido = models.ForeignKey(
        Recorrido, on_delete=models.CASCADE, related_name="secuencia"
    )
    parada = models.ForeignKey(
        Parada, on_delete=models.PROTECT, related_name="recorridos"
    )
    orden = models.PositiveIntegerField()
    activa = models.BooleanField(default=True)
    metodo = models.CharField(
        max_length=12,
        default="explicit",
        choices=[
            ("explicit", "Relación explícita"),
            ("spatial", "Proyección espacial"),
            ("legacy", "Histórica ilustrativa"),
        ],
    )
    source = models.ForeignKey(
        "imports.DataSource", null=True, blank=True, on_delete=models.PROTECT
    )
    distancia_metros = models.FloatField(null=True, blank=True)
    posicion_metros = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["orden"]
        constraints = [
            models.UniqueConstraint(
                fields=["recorrido", "orden"], name="recorrido_orden_unique"
            ),
            models.UniqueConstraint(
                fields=["recorrido", "parada"],
                condition=models.Q(metodo="spatial"),
                name="spatial_recorrido_parada_unique",
            ),
        ]
