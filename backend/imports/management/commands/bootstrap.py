from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Carga catálogo CSV y complementos de desarrollo offline; no crea usuarios."

    def handle(self, **options):
        if not settings.DEBUG:
            raise CommandError(
                "bootstrap está permitido únicamente con DJANGO_DEBUG=True."
            )
        data = Path(settings.BASE_DIR).parent / "data"
        call_command("seed_game")
        call_command("import_badata_recorridos", file=settings.BADATA_RECORRIDOS_FILE)
        call_command(
            "import_badata_recorridos",
            file=str(data / "recorridos.sample.geojson"),
            source="badata",
        )
        call_command(
            "import_badata_paradas",
            file=str(data / "paradas.sample.geojson"),
            source="muestra-paradas",
        )
        call_command(
            "import_line_colors", str(data.parent / "colores_lineas_bondiala.json")
        )
        self.stdout.write(
            "Catálogo CSV cargado. Los trazados de muestra lo complementan; sus paradas son ilustrativas."
        )
