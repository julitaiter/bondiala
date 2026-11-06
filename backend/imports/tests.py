import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.contrib.gis.geos import Point
from imports.models import DataSource, ImportRun, ImportError
from transport.models import (
    Linea,
    LineaColor,
    Ramal,
    Recorrido,
    Parada,
    RecorridoParada,
)


def feature():
    return {
        "type": "Feature",
        "properties": {
            "linea": "002",
            "recorrido": "B",
            "sentido": "IDA",
            "l_r_s": "002BIDA",
            "desde": "Inicio",
            "hasta": "Fin",
        },
        "geometry": {
            "type": "MultiLineString",
            "coordinates": [[[-58.4, -34.6], [-58.41, -34.61]]],
        },
    }


class ImportTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "source.geojson"
        self.output = io.StringIO()

    def write(self, features):
        self.path.write_text(
            json.dumps({"type": "FeatureCollection", "features": features})
        )

    def routes(self, features=None, **kwargs):
        if features is not None:
            self.write(features)
            if features and not Recorrido.objects.exists():
                source, _ = DataSource.objects.get_or_create(
                    slug="badata", defaults={"nombre": "CSV"}
                )
                line = Linea.objects.create(numero="2", source=source)
                branch = Ramal.objects.create(linea=line, nombre="B")
                Recorrido.objects.create(
                    ramal=branch,
                    sentido="IDA",
                    external_id="002BIDA",
                    source=source,
                    catalogue_format="csv",
                    metadata=feature()["properties"],
                    checksum="csv-unchanged",
                )
        call_command(
            "import_badata_recorridos",
            file=str(self.path),
            stdout=self.output,
            **kwargs,
        )

    def test_route_import_normalizes_line_and_preserves_geometry(self):
        self.routes([feature()])
        route = Recorrido.objects.get()
        self.assertEqual(route.ramal.linea.numero, "2")
        self.assertEqual(route.external_id, "002BIDA")
        self.assertEqual(route.geometria.srid, 4326)
        self.assertEqual(route.geometria.coords[0][0], (-58.4, -34.6))

    def test_reimport_checksum_and_force_do_not_duplicate(self):
        self.routes([feature()])
        self.routes()
        self.assertEqual(Recorrido.objects.count(), 1)
        self.assertEqual(ImportRun.objects.latest("pk").status, "UNCHANGED")
        self.routes(force=True)
        self.assertEqual(Recorrido.objects.count(), 1)
        self.assertEqual(ImportRun.objects.latest("pk").skipped, 1)

    def test_geojson_metadata_does_not_replace_csv_metadata(self):
        self.routes([feature()])
        changed = feature()
        changed["properties"]["hasta"] = "Nuevo destino"
        self.routes([changed])
        self.assertEqual(Recorrido.objects.count(), 1)
        self.assertEqual(Recorrido.objects.get().metadata["hasta"], "Fin")
        self.assertEqual(ImportRun.objects.latest("pk").updated, 0)

    def test_linestring_converted_safely(self):
        row = feature()
        row["geometry"] = {
            "type": "LineString",
            "coordinates": row["geometry"]["coordinates"][0],
        }
        self.routes([row])
        self.assertEqual(Recorrido.objects.get().geometria.geom_type, "MultiLineString")

    def test_empty_feed_preserves_catalog(self):
        self.routes([feature()])
        with self.assertRaises(CommandError):
            self.routes([])
        self.assertEqual(Recorrido.objects.count(), 1)
        self.assertEqual(ImportRun.objects.latest("pk").status, "FAILED")

    def test_invalid_geometry_is_logged_without_partial_entities(self):
        row = feature()
        row["geometry"]["coordinates"][0][0] = [999, -34]
        with self.assertRaises(CommandError):
            self.routes([row])
        self.assertEqual(Linea.objects.count(), 1)
        self.assertIsNone(Recorrido.objects.get().geometria)
        self.assertEqual(ImportRun.objects.get().errors, 1)
        self.assertEqual(ImportError.objects.count(), 1)

    def test_invalid_feature_does_not_rollback_valid_features(self):
        bad = feature()
        bad["properties"]["sentido"] = "DESCONOCIDO"
        with self.assertRaises(CommandError):
            self.routes([feature(), bad])
        self.assertEqual(Recorrido.objects.count(), 1)
        self.assertEqual(ImportRun.objects.get().status, "PARTIAL")

    def test_bad_json_and_wrong_collection_are_traced(self):
        self.path.write_text("{error")
        with self.assertRaises(CommandError):
            self.routes()
        self.assertEqual(ImportRun.objects.latest("pk").status, "FAILED")
        self.path.write_text('{"type":"Feature","features":[]}')
        with self.assertRaises(CommandError):
            self.routes()

    def stop(self, relations):
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-58.4, -34.6]},
            "properties": {
                "id": "physical-1",
                "nombre": "Parada física",
                "recorridos": relations,
            },
        }

    def test_stops_have_explicit_order_and_are_idempotent(self):
        self.routes([feature()])
        self.write([self.stop([{"l_r_s": "002BIDA", "orden": 3}])])
        for _ in range(2):
            call_command(
                "import_badata_paradas", file=str(self.path), stdout=self.output
            )
        self.assertEqual(Parada.objects.count(), 1)
        self.assertEqual(RecorridoParada.objects.get().orden, 3)

    def test_ambiguous_stops_are_not_silently_associated(self):
        self.routes([feature()])
        self.write([self.stop([])])
        with self.assertRaises(CommandError):
            call_command(
                "import_badata_paradas", file=str(self.path), stdout=self.output
            )
        self.assertEqual(Parada.objects.count(), 0)
        self.assertEqual(RecorridoParada.objects.count(), 0)

    def test_reordering_never_overwrites_historical_stop_occurrence(self):
        self.routes([feature()])
        row = self.stop([{"l_r_s": "002BIDA", "orden": 1}])
        self.write([row])
        call_command("import_badata_paradas", file=str(self.path), stdout=self.output)
        row["properties"]["id"] = "different-stop"
        self.write([row])
        with self.assertRaises(CommandError):
            call_command(
                "import_badata_paradas",
                file=str(self.path),
                stdout=self.output,
                force=True,
            )
        self.assertEqual(Parada.objects.count(), 1)
        self.assertEqual(RecorridoParada.objects.get().parada.external_id, "physical-1")

    def test_colors_share_palette_without_creating_lines(self):
        for n in [2, 60]:
            Linea.objects.create(numero=str(n))
        colors = {
            "color_principal": "#BE1F1C",
            "color_secundario_1": "#CCC7B1",
            "color_secundario_2": "#1D3B78",
            "color_texto": "#FFFFFF",
        }
        self.path.write_text(
            json.dumps([{"linea": n, **colors} for n in ["002", "060", "999"]])
        )
        for _ in range(2):
            call_command("import_line_colors", str(self.path), stdout=self.output)
        self.assertEqual(LineaColor.objects.count(), 1)
        self.assertEqual(Linea.objects.count(), 2)
        self.assertEqual(
            Linea.objects.get(numero="2").colores_id,
            Linea.objects.get(numero="60").colores_id,
        )

    def test_unconfigured_normalized_stop_source_is_explicit(self):
        with override_settings(BADATA_PARADAS_URL=""), self.assertRaises(CommandError):
            call_command("import_badata_paradas", format="normalized")

    @override_settings(USIG_URL="https://example.test/enrich")
    @patch("imports.management.commands.enrich_usig.requests.Session")
    def test_usig_is_persistent_and_does_not_break_catalog(self, session_class):
        source = DataSource.objects.create(slug="test", nombre="Test")
        stop = Parada.objects.create(
            source=source, external_id="p", ubicacion=Point(-58.4, -34.6)
        )
        response = Mock(content=b"{}")
        response.json.return_value = {"barrio": "Palermo", "comuna": "14"}
        session_class.return_value.get.return_value = response
        call_command("enrich_usig", stdout=self.output)
        stop.refresh_from_db()
        self.assertEqual(stop.barrio, "Palermo")
        self.assertIsNotNone(stop.enriched_at)
        session_class.return_value.get.reset_mock()
        call_command("enrich_usig", stdout=self.output)
        session_class.return_value.get.assert_not_called()
