import json
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from imports.route_geometries import run_geometry_import
from imports.services import run_import, import_catalogue_route, load_csv_document


class Command(BaseCommand):
    help = "Importa el catálogo CSV maestro o complementa geometrías GeoJSON sin crear recorridos."

    def add_arguments(self, parser):
        location = parser.add_mutually_exclusive_group()
        location.add_argument("--file")
        location.add_argument("--url")
        parser.add_argument("--source", default="badata")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--geojson", action="store_true")
        parser.add_argument(
            "--only-missing",
            action="store_true",
            help="Carga muestras sin reemplazar geometrías existentes.",
        )
        parser.add_argument(
            "--format", choices=["auto", "csv", "geojson"], default="auto"
        )

    def handle(self, **options):
        if options["geojson"] and options["format"] == "csv":
            raise CommandError("--geojson no puede combinarse con --format csv.")
        format_name = "geojson" if options["geojson"] else options["format"]
        default = (
            settings.BA_DATA_RECORRIDOS_GEOJSON_URL
            if format_name == "geojson"
            else settings.BADATA_RECORRIDOS_FILE
        )
        location = options["file"] or options["url"] or default
        if format_name == "auto":
            format_name = (
                "csv"
                if Path(urlparse(location).path).suffix.lower() == ".csv"
                else "geojson"
            )
        if format_name == "geojson":
            run = run_geometry_import(
                location,
                options["source"],
                options["force"],
                options["dry_run"],
                options["only_missing"],
            )
            self.stdout.write(
                f"{'DRY RUN · ' if options['dry_run'] else ''}Importación {run.pk} {run.status}: geometrías nuevas={run.created} actualizadas={run.updated} omitidas={run.skipped} errores={run.errors}"
            )
            self.stdout.write(
                json.dumps(run.metrics, sort_keys=True, ensure_ascii=False)
            )
        else:
            failure = None
            with transaction.atomic():
                try:
                    run = run_import(
                        location,
                        "catalogo_csv",
                        import_catalogue_route,
                        options["source"],
                        options["force"],
                        loader=load_csv_document,
                    )
                except CommandError as exc:
                    failure = exc
                if options["dry_run"]:
                    transaction.set_rollback(True)
            if failure:
                raise failure
            self.stdout.write(
                f"{'DRY RUN · ' if options['dry_run'] else ''}Importación {run.pk} {run.status}: creados={run.created} actualizados={run.updated} omitidos={run.skipped} errores={run.errors}"
            )
        if run.errors or run.metrics.get("conflictos"):
            raise CommandError(
                "Se registraron errores o conflictos. Revisá ImportRun en el admin."
            )
