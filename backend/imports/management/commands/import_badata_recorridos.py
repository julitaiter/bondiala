from django.conf import settings
from pathlib import Path
from urllib.parse import urlparse
from django.core.management.base import BaseCommand, CommandError
from imports.services import (
    run_import,
    import_route,
    import_catalogue_route,
    load_document,
    load_csv_document,
)


class Command(BaseCommand):
    help = "Importa catálogo CSV de BA Data; GeoJSON opcional para geometrías. No elimina datos."

    def add_arguments(self, parser):
        parser.add_argument("--file")
        parser.add_argument("--url")
        parser.add_argument("--source", default="badata")
        parser.add_argument("--force", action="store_true")
        parser.add_argument(
            "--format", choices=["auto", "csv", "geojson"], default="auto"
        )

    def handle(self, **options):
        default_location = (
            settings.BADATA_RECORRIDOS_URL
            if options["format"] == "geojson"
            else settings.BADATA_RECORRIDOS_FILE
        )
        location = options["file"] or options["url"] or default_location
        format_name = options["format"]
        if format_name == "auto":
            format_name = (
                "csv"
                if Path(urlparse(location).path).suffix.lower() == ".csv"
                else "geojson"
            )
        is_csv = format_name == "csv"
        run = run_import(
            location,
            "catalogo_csv" if is_csv else "recorridos",
            import_catalogue_route if is_csv else import_route,
            options["source"],
            options["force"],
            loader=load_csv_document if is_csv else load_document,
        )
        self.stdout.write(
            f"Importación {run.pk} {run.status}: creados={run.created} actualizados={run.updated} omitidos={run.skipped} errores={run.errors}"
        )
        if run.errors:
            raise CommandError("Se registraron errores. Revisá ImportRun en el admin.")
