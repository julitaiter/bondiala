import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from imports.services import run_import, import_stop
from imports.official_stops import import_official_stops


class Command(BaseCommand):
    help = "Importa paradas oficiales BA Data y, opcionalmente, asocia recorridos mediante PostGIS."

    def add_arguments(self, parser):
        location = parser.add_mutually_exclusive_group()
        location.add_argument("--file")
        location.add_argument("--url")
        parser.add_argument("--source")
        parser.add_argument("--force", action="store_true")
        parser.add_argument(
            "--format", choices=["auto", "official", "normalized"], default="auto"
        )
        parser.add_argument("--match-routes", action="store_true")
        parser.add_argument("--rematch", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, **options):
        location = (
            options["file"] or options["url"] or settings.BA_DATA_PARADAS_GEOJSON_URL
        )
        normalized = (
            options["format"] == "normalized" or options["source"] == "muestra-paradas"
        )
        if options["format"] == "auto" and options["file"]:
            try:
                if Path(location).stat().st_size > settings.IMPORT_MAX_BYTES:
                    raise ValueError("El archivo supera el tamaño permitido.")
                doc = json.loads(Path(location).read_bytes())
                features = doc.get("features", []) if isinstance(doc, dict) else []
                normalized = normalized or any(
                    isinstance(f, dict)
                    and isinstance(f.get("properties"), dict)
                    and ("recorridos" in f["properties"] or "l_r_s" in f["properties"])
                    for f in features[:10]
                )
            except (ValueError, OSError):
                pass  # The selected loader logs malformed input as a failed import.
        if normalized:
            if options["rematch"] or options["match_routes"]:
                raise CommandError(
                    "El adaptador normalizado ya requiere relaciones explícitas; no acepta matching espacial."
                )
            location = options["file"] or options["url"] or settings.BADATA_PARADAS_URL
            if not location:
                raise CommandError("Indicá --file/--url para el adaptador normalizado.")
            with transaction.atomic():
                run = run_import(
                    location,
                    "paradas",
                    import_stop,
                    options["source"] or "badata",
                    options["force"],
                )
                if options["dry_run"]:
                    transaction.set_rollback(True)
            self.stdout.write(
                f"Importación {run.pk} {run.status}: creadas={run.created} actualizadas={run.updated} omitidas={run.skipped} errores={run.errors}"
            )
            if run.errors:
                raise CommandError(
                    "Se registraron relaciones ambiguas o inválidas. Revisá el admin."
                )
            return
        run = import_official_stops(
            location,
            options["source"] or "badata-paradas",
            options["force"],
            match=options["match_routes"],
            rematch=options["rematch"],
            dry_run=options["dry_run"],
        )
        self.stdout.write(
            f"{'DRY RUN · ' if options['dry_run'] else ''}Importación {run.pk} {run.status}: creadas={run.created} actualizadas={run.updated} omitidas={run.skipped} errores={run.errors}"
        )
        self.stdout.write(json.dumps(run.metrics, ensure_ascii=False, sort_keys=True))
