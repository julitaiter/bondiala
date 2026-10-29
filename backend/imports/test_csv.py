import csv
import io
import tempfile
import uuid
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from imports.models import ImportRun, ImportError
from imports.tests import feature
from transport.models import Linea, Ramal, Recorrido, RecorridoParada, Parada
from trips.services import register_trip
from gamification.services import total_points
from django.contrib.gis.geos import Point


class CsvCatalogueTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "catalogue.csv"
        self.output = io.StringIO()
        self.row = {
            **feature()["properties"],
            "fid": "1",
            "modalidad": "EXPRESO",
            "jurisdicci": "NACIONAL",
            "camara": "CEAP",
        }

    def write(self, rows=None):
        with self.path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.row))
            writer.writeheader()
            writer.writerows(rows if rows is not None else [self.row])

    def run_csv(self, **kwargs):
        call_command(
            "import_badata_recorridos",
            file=str(self.path),
            stdout=self.output,
            **kwargs,
        )

    def geojson(self, source="badata", row=None):
        import json

        path = Path(self.temp.name) / "routes.geojson"
        path.write_text(
            json.dumps({"type": "FeatureCollection", "features": [row or feature()]})
        )
        call_command(
            "import_badata_recorridos",
            file=str(path),
            source=source,
            stdout=self.output,
        )

    def test_csv_imports_catalogue_without_inventing_geometry_or_stops(self):
        self.write()
        self.run_csv()
        route = Recorrido.objects.get()
        self.assertEqual(route.ramal.linea.numero, "2")
        self.assertEqual(route.ramal.nombre, "B")
        self.assertEqual(route.sentido, "IDA")
        self.assertEqual(route.external_id, "002BIDA")
        self.assertEqual(route.metadata["modalidad"], "EXPRESO")
        self.assertEqual(route.metadata["jurisdicci"], "NACIONAL")
        self.assertIsNone(route.geometria)
        self.assertEqual(route.catalogue_format, "csv")
        self.assertFalse(Parada.objects.exists())
        response = APIClient().get(f"/api/v1/recorridos/{route.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["geometria"])
        self.assertEqual(response.data["modalidad"], "EXPRESO")
        self.assertEqual(response.data["paradas"], [])

    def test_csv_is_default_and_reimport_is_idempotent(self):
        self.write()
        with self.settings(BADATA_RECORRIDOS_FILE=str(self.path)):
            call_command("import_badata_recorridos", stdout=self.output)
            call_command("import_badata_recorridos", stdout=self.output)
        self.assertEqual(Recorrido.objects.count(), 1)
        self.assertEqual(ImportRun.objects.latest("pk").status, "UNCHANGED")
        self.assertEqual(ImportRun.objects.first().kind, "catalogo_csv")

    def test_original_checksum_after_new_revision_is_not_wrongly_skipped(self):
        self.write()
        self.run_csv()
        self.write([{**self.row, "hasta": "Destino revisado"}])
        self.run_csv()
        self.write()
        self.run_csv()
        self.assertEqual(Recorrido.objects.get().metadata["hasta"], self.row["hasta"])
        self.assertEqual(ImportRun.objects.latest("pk").updated, 1)

    def test_csv_updates_preserve_geometry_and_ordered_stops(self):
        self.geojson()
        route = Recorrido.objects.get()
        original_pk, original_geometry = route.pk, route.geometria.wkb
        for order in range(2):
            stop = Parada.objects.create(
                source=route.source,
                external_id=f"p{order}",
                ubicacion=Point(-58.4 - order / 1000, -34.6),
            )
            RecorridoParada.objects.create(recorrido=route, parada=stop, orden=order)
        sequence = list(route.secuencia.values_list("pk", flat=True))
        self.write()
        self.run_csv()
        route.refresh_from_db()
        self.assertEqual(route.pk, original_pk)
        self.assertEqual(route.geometria.wkb, original_geometry)
        self.assertEqual(list(route.secuencia.values_list("pk", flat=True)), sequence)

    def test_geojson_enriches_csv_without_replacing_catalogue_metadata(self):
        self.write()
        self.run_csv()
        before = Recorrido.objects.get().checksum
        self.geojson()
        route = Recorrido.objects.get()
        self.assertIsNotNone(route.geometria)
        self.assertEqual(route.metadata["modalidad"], "EXPRESO")
        self.assertEqual(route.checksum, before)
        self.assertEqual(route.catalogue_format, "csv")
        self.assertEqual(route.geometria_source, route.source)
        with self.settings(BADATA_RECORRIDOS_URL=str(Path(self.temp.name) / "routes.geojson")):
            call_command("import_badata_recorridos", format="geojson", stdout=self.output)
        self.assertEqual(ImportRun.objects.latest("pk").status, "UNCHANGED")
        self.run_csv()
        self.assertEqual(ImportRun.objects.latest("pk").status, "UNCHANGED")

    def test_legacy_sample_is_promoted_preserving_trips_and_points(self):
        self.geojson(source="badata-muestra")
        route = Recorrido.objects.get()
        original_pk = route.pk
        original_source = route.source
        for order in range(2):
            stop = Parada.objects.create(
                source=original_source,
                external_id=f"sample-{order}",
                ubicacion=Point(-58.4 - order / 1000, -34.6),
            )
            RecorridoParada.objects.create(recorrido=route, parada=stop, orden=order)
        sequence = list(route.secuencia.all())
        user = User.objects.create_user(
            username="coleccionista", email="coleccionista@example.test"
        )
        trip, _ = register_trip(
            user, route.pk, sequence[0].pk, sequence[1].pk, uuid.uuid4()
        )
        points = total_points(user)
        self.write()
        self.run_csv()
        route.refresh_from_db()
        trip.refresh_from_db()
        self.assertEqual(route.pk, original_pk)
        self.assertEqual(trip.recorrido_id, original_pk)
        self.assertEqual(route.source.slug, "badata")
        self.assertEqual(route.geometria_source, original_source)
        self.assertEqual(total_points(user), points)
        self.assertEqual(user.paradas_transitadas.count(), 2)

    def test_unrelated_source_is_never_silently_reassigned(self):
        self.geojson(source="otro-proveedor")
        self.write()
        with self.assertRaises(CommandError):
            self.run_csv()
        self.assertEqual(Recorrido.objects.get().source.slug, "otro-proveedor")

    def test_empty_or_headerless_csv_preserves_existing_catalogue(self):
        self.write()
        self.run_csv()
        for content in ["", "a,b\n1,2\n", ",".join(self.row) + "\n"]:
            self.path.write_text(content)
            with self.assertRaises(CommandError):
                self.run_csv()
            self.assertEqual(Recorrido.objects.count(), 1)
            self.assertEqual(ImportRun.objects.latest("pk").status, "FAILED")

    def test_malformed_rows_and_identity_mismatch_are_traced(self):
        self.write([{**self.row, "l_r_s": "060ZIDA"}, self.row])
        with self.assertRaises(CommandError):
            self.run_csv()
        self.assertEqual(Recorrido.objects.count(), 1)
        self.assertEqual(ImportRun.objects.get().status, "PARTIAL")
        self.assertEqual(ImportError.objects.count(), 1)

    def test_duplicate_headers_are_rejected(self):
        self.path.write_text("linea,linea,recorrido,sentido,l_r_s\n2,2,B,IDA,002BIDA\n")
        with self.assertRaises(CommandError):
            self.run_csv()
        self.assertFalse(Recorrido.objects.exists())

    def test_quoted_names_and_variant_branches_are_preserved(self):
        self.write(
            [
                {
                    **self.row,
                    "recorrido": "F-variante",
                    "l_r_s": "002F-varianteIDA",
                    "desde": 'Terminal, sector "norte"',
                }
            ]
        )
        self.run_csv()
        route = Recorrido.objects.get()
        self.assertEqual(route.ramal.nombre, "F-variante")
        self.assertEqual(route.metadata["desde"], 'Terminal, sector "norte"')

    def test_provided_csv_counts_and_color_coverage(self):
        call_command("import_badata_recorridos", stdout=self.output)
        self.assertEqual(Linea.objects.count(), 134)
        self.assertEqual(Ramal.objects.count(), 557)
        self.assertEqual(Recorrido.objects.count(), 1104)
        self.assertEqual(Recorrido.objects.exclude(geometria=None).count(), 0)
        colors = (
            Path(settings.BADATA_RECORRIDOS_FILE).parent.parent
            / "colores_lineas_bondiala.json"
        )
        call_command("import_line_colors", str(colors), stdout=self.output)
        self.assertEqual(Linea.objects.exclude(colores=None).count(), 102)
