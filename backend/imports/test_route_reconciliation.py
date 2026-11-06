"""The reviewed variants are catalogue additions, never aliases of old routes."""

import io
import json
import tempfile
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.gis.geos import LineString, MultiLineString
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from imports.models import ImportError
from imports.route_geometries import run_geometry_import
from imports.official_stops import import_official_stops
from imports.test_official_stops import official
from gamification.models import EventoPuntos
from transport.models import Linea, Ramal, Recorrido
from trips.models import RegistroViaje, UsuarioLineaParada
from trips.services import register_trip


class ReviewedRouteIdentityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.catalogue = Path(settings.BADATA_RECORRIDOS_FILE)
        cls.review = json.loads(
            cls.catalogue.with_name("recorridos.reconciliation.json").read_text()
        )
        call_command(
            "import_badata_recorridos", file=str(cls.catalogue),
            stdout=io.StringIO(),
        )

    def features(self):
        return [
            {"type": "Feature", "properties": feature["properties"],
             "geometry": {"type":"LineString", "coordinates":[[-58.4,-34.6],[-58.41,-34.61]]}}
            for case in self.review["cases"] for feature in case["geojson_features"]
        ]

    def import_shapes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reviewed.geojson"
            path.write_text(json.dumps({"type":"FeatureCollection", "features":self.features()}))
            return run_geometry_import(str(path))

    def test_reviewed_identities_without_csv_entries_still_cannot_create_aliases(self):
        identifiers = [feature["properties"]["l_r_s"] for feature in self.features()]
        # Reconstruct the prior catalogue in this isolated test database.
        Recorrido.objects.filter(external_id__in=identifiers).delete()
        # Even identical geometry must not turn a different branch/line into an
        # alias. Only properties are real here; the small geometry is a fixture.
        shape = MultiLineString(
            LineString([[-58.4, -34.6], [-58.41, -34.61]]), srid=4326,
        )
        Recorrido.objects.filter(
            ramal__linea__numero__in=["12", "42", "50", "102", "151"]
        ).update(geometria=shape, requiere_rematch=False)
        models = (Linea, Ramal, Recorrido)
        before = [list(model.objects.order_by("pk").values()) for model in models]
        features = self.features()
        for feature in features:
            feature["geometry"] = json.loads(shape.geojson)
        self.assertEqual(len(features), 16)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reviewed.geojson"
            path.write_text(json.dumps({"type":"FeatureCollection", "features":features}))
            run = run_geometry_import(str(path))
        self.assertEqual(run.status, "SUCCESS")
        self.assertEqual(run.metrics["sin_match"], 16)
        self.assertEqual(run.metrics["match_exacto"], 0)
        self.assertEqual(run.metrics["match_secundario"], 0)
        self.assertEqual((run.created, run.updated, run.errors), (0, 0, 0))
        self.assertEqual(
            before, [list(model.objects.order_by("pk").values()) for model in models]
        )
        self.assertEqual(
            set(ImportError.objects.filter(run=run).values_list("external_id", flat=True)),
            {feature["properties"]["l_r_s"] for feature in features},
        )

    def test_added_csv_variants_match_exactly_and_preserve_existing_identities(self):
        before = list(Recorrido.objects.order_by("pk").values(
            "pk", "ramal_id", "external_id", "sentido", "metadata", "checksum", "source_id",
        ))
        run = self.import_shapes()
        self.assertEqual((run.created, run.updated, run.errors), (16, 0, 0))
        self.assertEqual(run.metrics["match_exacto"], 16)
        self.assertEqual(run.metrics["sin_match"], 0)
        self.assertEqual((Linea.objects.count(), Ramal.objects.count(), Recorrido.objects.count()),
                         (135, 565, 1120))
        self.assertEqual(before, list(Recorrido.objects.order_by("pk").values(
            "pk", "ramal_id", "external_id", "sentido", "metadata", "checksum", "source_id",
        )))
        repeat = self.import_shapes()
        self.assertEqual(repeat.status, "UNCHANGED")
        call_command("import_badata_recorridos", stdout=io.StringIO())
        self.assertEqual((Linea.objects.count(), Ramal.objects.count(), Recorrido.objects.count()),
                         (135, 565, 1120))

    def test_ebus_api_search_filter_trip_progress_and_rematch_preserve_history(self):
        self.import_shapes()
        line = Linea.objects.get(numero="EBUS")
        route = line.ramales.get(nombre="A").recorridos.get(sentido="IDA")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stops.geojson"
            path.write_text(json.dumps({"type":"FeatureCollection", "features":[
                official(x=-58.401, y=-34.601, line="eBus"),
                official(x=-58.402, y=-34.602, address="Av. Prueba 200", line="EBUS"),
            ]}))
            import_official_stops(str(path), match=True)
            client = APIClient()
            search = client.get("/api/v1/lineas/?search=ebus")
            self.assertEqual(search.status_code, 200)
            self.assertEqual(search.data["count"], 1)
            self.assertEqual(search.data["results"][0]["numero"], "EBUS")
            found = client.get(f"/api/v1/recorridos/?linea={line.pk}")
            self.assertEqual(found.status_code, 200)
            self.assertEqual(found.data["count"], 2)
            self.assertTrue(all(item["linea_numero"] == "EBUS" for item in found.data["results"]))
            detail = client.get(f"/api/v1/recorridos/{route.pk}/")
            self.assertTrue(detail.data["puede_registrar_viaje"])
            sequence = list(route.secuencia.filter(activa=True).order_by("orden"))
            user = get_user_model().objects.create_user(username="ebus-trip", email="ebus@example.test")
            call_command("seed_game", stdout=io.StringIO())
            key = uuid.uuid4()
            trip, created = register_trip(user, route.pk, sequence[0].pk, sequence[1].pk, key)
            self.assertTrue(created)
            self.assertEqual(trip.resultado["nuevas_paradas"], 2)
            history = (RegistroViaje, UsuarioLineaParada, EventoPuntos)
            before = [list(model.objects.order_by("pk").values()) for model in history]
            import_official_stops(str(path), rematch=True)
            register_trip(user, route.pk, sequence[0].pk, sequence[1].pk, key)
            self.assertEqual(before, [list(model.objects.order_by("pk").values()) for model in history])
            client.force_authenticate(user)
            progress = client.get(f"/api/v1/lineas/{line.pk}/").data["progreso"]
            self.assertEqual(progress["numero"], "EBUS")
            self.assertEqual(progress["transitadas"], 2)

    def test_mixed_line_codes_sort_numbers_numerically_before_alphanumeric_codes(self):
        client = APIClient()
        url = "/api/v1/lineas/"
        codes = []
        while url:
            response = client.get(url)
            self.assertEqual(response.status_code, 200)
            codes.extend(item["numero"] for item in response.data["results"])
            url = response.data["next"]
        self.assertEqual(len(codes), 135)
        self.assertEqual(codes[-1], "EBUS")
        self.assertEqual(codes[:-1], sorted(codes[:-1], key=int))
