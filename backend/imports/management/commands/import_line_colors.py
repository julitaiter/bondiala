import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from imports.models import DataSource, ImportRun, ImportError
from transport.models import Linea, LineaColor, normalize_line


class Command(BaseCommand):
    help = "Asigna paletas reutilizables, sin crear líneas."

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, **options):
        source, _ = DataSource.objects.get_or_create(
            slug="bondiala-colores", defaults={"nombre": "Colores de Bondiala"}
        )
        run = ImportRun.objects.create(source=source, kind="colores")
        missing = 0
        try:
            entries = json.loads(Path(options["path"]).read_text())
            if not isinstance(entries, list) or not entries:
                raise ValueError("El JSON debe contener una lista no vacía.")
            for index, entry in enumerate(entries):
                try:
                    with transaction.atomic():
                        line = Linea.objects.filter(
                            numero=normalize_line(entry["linea"])
                        ).first()
                        if not line:
                            missing += 1
                            run.skipped += 1
                            continue
                        colors = {
                            field: str(entry[field]).upper()
                            for field in [
                                "color_principal",
                                "color_secundario_1",
                                "color_secundario_2",
                                "color_texto",
                            ]
                        }
                        candidate = LineaColor(**colors)
                        candidate.full_clean(
                            validate_unique=False, validate_constraints=False
                        )
                        palette, created = LineaColor.objects.get_or_create(**colors)
                        run.created += int(created)
                        if line.colores_id != palette.pk:
                            line.colores = palette
                            line.save(update_fields=["colores", "updated_at"])
                            run.updated += 1
                        else:
                            run.skipped += 1
                except Exception as exc:
                    run.errors += 1
                    ImportError.objects.create(
                        run=run,
                        external_id=str(index),
                        message=f"Paleta inválida ({type(exc).__name__}).",
                    )
            run.status = "PARTIAL" if run.errors else "SUCCESS"
        except Exception as exc:
            run.status = "FAILED"
            run.errors += 1
            ImportError.objects.create(
                run=run, message="Archivo de colores inválido o inaccesible."
            )
            raise CommandError("No se pudo leer el archivo de colores.") from exc
        finally:
            run.finished_at = timezone.now()
            run.save()
        self.stdout.write(
            f"{run.updated} líneas actualizadas; {Linea.objects.filter(colores=None).count()} sin colores; {missing} entradas sin línea; {LineaColor.objects.count()} paletas únicas; {run.errors} errores"
        )
        if run.errors:
            raise CommandError("Revisá los errores de paletas en el admin.")
