from django.core.management.base import BaseCommand
from gamification.models import Nivel, Logro


class Command(BaseCommand):
    help = "Crea configuración inicial editable sin reemplazar ajustes administrativos."

    def handle(self, **options):
        levels = [
            (1, "Pasajero", 0),
            (2, "Pasajero", 50),
            (3, "Pasajero", 120),
            (4, "Pasajero", 200),
            (5, "Frecuente", 300),
            (10, "Bondiero", 1000),
            (20, "Inspector", 3000),
            (30, "Coleccionista", 6000),
            (40, "Experto del AMBA", 10000),
            (50, "Leyenda del Bondi", 15000),
        ]
        # Interpola los niveles intermedios; los valores siguen siendo configuración.
        anchors = {n: (title, points) for n, title, points in levels}
        for n in range(1, 51):
            lower = max(x for x in anchors if x <= n)
            upper = min((x for x in anchors if x >= n), default=50)
            title, low_points = anchors[lower]
            points = (
                low_points
                if lower == upper
                else round(
                    low_points
                    + (anchors[upper][1] - low_points) * (n - lower) / (upper - lower)
                )
            )
            Nivel.objects.get_or_create(
                numero=n, defaults={"nombre": title, "puntos_minimos": points}
            )
        achievements = [
            (
                "primera-parada",
                "El primer bondi",
                "Tu primera parada en la colección.",
                "paradas",
                1,
            ),
            (
                "100-paradas",
                "Cien historias",
                "Transitá 100 paradas dentro de tus líneas.",
                "paradas",
                100,
            ),
            (
                "1000-paradas",
                "La ciudad es tuya",
                "Transitá 1.000 paradas dentro de tus líneas.",
                "paradas",
                1000,
            ),
            (
                "primer-sentido",
                "De punta a punta",
                "Completá tu primer sentido, en uno o varios viajes.",
                "sentidos",
                1,
            ),
            (
                "primer-ramal",
                "Ida y vuelta",
                "Completá todos los sentidos de un ramal.",
                "ramales",
                1,
            ),
            (
                "10-ramales",
                "Por todos los caminos",
                "Completá 10 ramales.",
                "ramales",
                10,
            ),
            (
                "primera-linea",
                "Una chapa más",
                "Completá tu primera línea.",
                "lineas",
                1,
            ),
            ("5-lineas", "Coleccionista urbano", "Completá 5 líneas.", "lineas", 5),
            ("10-lineas", "Conocés el camino", "Completá 10 líneas.", "lineas", 10),
        ]
        for slug, name, description, rule, target in achievements:
            Logro.objects.get_or_create(
                slug=slug,
                defaults={
                    "nombre": name,
                    "descripcion": description,
                    "regla": rule,
                    "objetivo": target,
                },
            )
        self.stdout.write("Niveles y logros iniciales disponibles.")
