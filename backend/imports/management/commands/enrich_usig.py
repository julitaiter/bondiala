from datetime import timedelta
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from imports.models import DataSource, ImportRun, ImportError
from transport.models import Parada


class Command(BaseCommand):
    help = "Enriquecimiento opcional, persistente y acotado. Contrato: docs/importaciones.md"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--max-age-days", type=int, default=90)

    def handle(self, **options):
        if urlparse(settings.USIG_URL).scheme != "https":
            raise CommandError(
                "Configurá USIG_URL como endpoint HTTPS compatible con el contrato documentado."
            )
        if not 1 <= options["limit"] <= 1000 or options["max_age_days"] < 1:
            raise CommandError(
                "limit debe estar entre 1 y 1000; max-age-days debe ser positivo."
            )
        source, _ = DataSource.objects.get_or_create(
            slug="usig", defaults={"nombre": "USIG (auxiliar)"}
        )
        run = ImportRun.objects.create(source=source, kind="enrichment")
        session = requests.Session()
        session.mount(
            "https://",
            HTTPAdapter(
                max_retries=Retry(
                    total=2, backoff_factor=0.5, status_forcelist=[429, 502, 503, 504]
                )
            ),
        )
        from django.db.models import Q

        query = Parada.objects.filter(
            Q(enriched_at=None)
            | Q(
                enriched_at__lt=timezone.now() - timedelta(days=options["max_age_days"])
            )
        ).order_by("pk")[: options["limit"]]
        try:
            for stop in query:
                try:
                    response = session.get(
                        settings.USIG_URL,
                        params={
                            "x": stop.ubicacion.x,
                            "y": stop.ubicacion.y,
                            "srid": 4326,
                        },
                        timeout=(5, 10),
                    )
                    response.raise_for_status()
                    if len(response.content) > 65536:
                        raise ValueError("Respuesta demasiado grande")
                    data = response.json()
                    if not isinstance(data, dict) or not any(
                        isinstance(data.get(f), str)
                        for f in ["direccion", "esquina", "barrio", "comuna"]
                    ):
                        raise ValueError("Contrato incompatible")
                    for field in ["direccion", "esquina", "barrio", "comuna"]:
                        if isinstance(data.get(field), str):
                            setattr(
                                stop,
                                field,
                                data[field][: stop._meta.get_field(field).max_length],
                            )
                    stop.enrichment = {
                        "source": "usig",
                        **{
                            f: getattr(stop, f)
                            for f in ["direccion", "esquina", "barrio", "comuna"]
                        },
                    }
                    stop.enriched_at = timezone.now()
                    stop.save()
                    run.updated += 1
                except Exception as exc:
                    run.errors += 1
                    ImportError.objects.create(
                        run=run,
                        external_id=str(stop.pk),
                        message=f"Enriquecimiento no disponible ({type(exc).__name__}).",
                    )
            run.status = "PARTIAL" if run.errors else "SUCCESS"
        finally:
            session.close()
            run.finished_at = timezone.now()
            run.save()
        self.stdout.write(
            f"Actualizadas={run.updated}; errores={run.errors}. El catálogo permanece disponible."
        )
