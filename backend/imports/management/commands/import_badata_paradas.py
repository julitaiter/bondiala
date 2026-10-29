from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from imports.services import run_import, import_stop


class Command(BaseCommand):
    help = "Importa paradas con relaciones explícitas a recorridos y orden."

    def add_arguments(self, parser):
        parser.add_argument("--file")
        parser.add_argument("--url")
        parser.add_argument("--source", default="badata")
        parser.add_argument("--force", action="store_true")

    def handle(self, **options):
        location = options["file"] or options["url"] or settings.BADATA_PARADAS_URL
        if not location:
            raise CommandError(
                "Configurá BADATA_PARADAS_URL o indicá --file/--url. Formato: docs/importaciones.md"
            )
        run = run_import(
            location, "paradas", import_stop, options["source"], options["force"]
        )
        self.stdout.write(
            f"Importación {run.pk} {run.status}: creadas={run.created} actualizadas={run.updated} omitidas={run.skipped} errores={run.errors}"
        )
        if run.errors:
            raise CommandError(
                "Se registraron relaciones ambiguas o inválidas. Revisá el admin."
            )
