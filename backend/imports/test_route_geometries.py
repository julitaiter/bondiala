import io
import json
import socket
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString, MultiLineString, Point
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings

from gamification.models import EventoPuntos
from imports.models import DataSource, ImportRun, ImportError
from imports.route_geometries import run_geometry_import
from imports.services import load_bytes, validate_download_url, validate_geojson
from imports.tests import feature
from transport.models import Linea, Ramal, Recorrido, Parada, RecorridoParada
from trips.models import RegistroViaje, UsuarioLineaParada


class RouteGeometryTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "geometries.geojson"
        self.source = DataSource.objects.create(slug="badata", nombre="CSV maestro")
        self.line = Linea.objects.create(numero="2", source=self.source)
        branch = Ramal.objects.create(linea=self.line, nombre="B")
        self.route = Recorrido.objects.create(
            ramal=branch,
            sentido="IDA",
            source=self.source,
            external_id="002BIDA",
            catalogue_format="csv",
            checksum="csv-checksum",
            metadata={"desde": "Cabecera CSV", "modalidad": "COMUN"},
        )

    def run_import(self, features=None, **kwargs):
        if features is not None:
            self.path.write_text(
                json.dumps({"type": "FeatureCollection", "features": features})
            )
        return run_geometry_import(str(self.path), **kwargs)

    def test_exact_match_enriches_only_geometry_and_provenance(self):
        before = (
            self.route.pk,
            self.route.source_id,
            self.route.metadata,
            self.route.checksum,
        )
        run = self.run_import([feature()])
        self.route.refresh_from_db()
        self.assertEqual(
            (
                self.route.pk,
                self.route.source_id,
                self.route.metadata,
                self.route.checksum,
            ),
            before,
        )
        self.assertEqual(run.metrics["match_exacto"], 1)
        self.assertEqual(run.metrics["geometrias_nuevas"], 1)
        self.assertEqual(self.route.geometria.srid, 4326)
        self.assertTrue(self.route.requiere_rematch)
        self.assertEqual(self.route.geometria_source, self.source)
        self.assertTrue(run.metrics["cambios"][0]["nuevo_sha256"])

    def test_exact_match_normalizes_case_whitespace_and_leading_zeros(self):
        row = feature()
        row["properties"].update(
            linea="0002", recorrido=" b ", sentido=" ida ", l_r_s=" 0002 b ida "
        )
        run = self.run_import([row])
        self.assertEqual(run.metrics["match_exacto"], 1)
        self.assertEqual(Recorrido.objects.count(), 1)

    def test_unique_logical_fallback_when_external_identifier_is_unknown(self):
        row = feature()
        row["properties"]["l_r_s"] = "opaque-provider-id"
        run = self.run_import([row])
        self.assertEqual(run.metrics["match_secundario"], 1)
        self.assertEqual(run.metrics["match_exacto"], 0)
        self.assertEqual(run.created, 1)

    def test_unmatched_valid_feature_never_creates_catalogue_entities(self):
        row = feature()
        row["properties"].update(linea="999", recorrido="Z", l_r_s="999ZIDA")
        run = self.run_import([row])
        self.assertEqual(run.metrics["sin_match"], 1)
        self.assertEqual(run.errors, 0)
        self.assertEqual(
            (Linea.objects.count(), Ramal.objects.count(), Recorrido.objects.count()),
            (1, 1, 1),
        )
        self.assertTrue(ImportError.objects.filter(run=run).exists())
        self.route.refresh_from_db()
        self.assertIsNone(self.route.geometria)

    def test_exact_identifier_conflicting_with_attributes_is_audited(self):
        row = feature()
        row["properties"]["linea"] = "60"
        run = self.run_import([row])
        self.assertEqual(run.metrics["conflictos"], 1)
        self.route.refresh_from_db()
        self.assertIsNone(self.route.geometria)

    def test_ambiguous_normalized_external_identifiers_do_not_fall_back(self):
        branch = Ramal.objects.create(linea=self.line, nombre="C")
        Recorrido.objects.create(
            ramal=branch,
            sentido="IDA",
            source=self.source,
            external_id="2BIDA",
            catalogue_format="csv",
        )
        row = feature()
        row["properties"]["l_r_s"] = "00002BIDA"
        run = self.run_import([row])
        self.assertEqual(run.metrics["conflictos"], 1)
        self.assertFalse(Recorrido.objects.exclude(geometria=None).exists())

    def test_linestring_converted_and_multiline_component_order_preserved(self):
        row = feature()
        row["geometry"] = {
            "type": "LineString",
            "coordinates": [[-58.4, -34.6], [-58.41, -34.61]],
        }
        self.run_import([row])
        self.route.refresh_from_db()
        self.assertEqual(self.route.geometria.geom_type, "MultiLineString")
        row["geometry"] = {
            "type": "MultiLineString",
            "coordinates": [
                [[-58.3, -34.5], [-58.31, -34.51]],
                [[-58.4, -34.6], [-58.41, -34.61]],
            ],
        }
        self.run_import([row])
        self.route.refresh_from_db()
        self.assertEqual(self.route.geometria.coords[0][0], (-58.3, -34.5))
        self.assertEqual(self.route.geometria.coords[1][-1], (-58.41, -34.61))

    def test_invalid_geometry_isolated_without_nulling_existing_shape(self):
        self.run_import([feature()])
        self.route.refresh_from_db()
        before = bytes(self.route.geometria.wkb)
        row = feature()
        row["geometry"] = None
        run = self.run_import([row])
        self.route.refresh_from_db()
        self.assertEqual(bytes(self.route.geometria.wkb), before)
        self.assertEqual(run.errors, 1)

    def test_missing_feature_does_not_remove_other_geometry(self):
        branch = Ramal.objects.create(linea=self.line, nombre="C")
        other = Recorrido.objects.create(
            ramal=branch,
            sentido="IDA",
            source=self.source,
            external_id="002CIDA",
            catalogue_format="csv",
            geometria=MultiLineString(
                LineString([[-58.4, -34.6], [-58.41, -34.61]]), srid=4326
            ),
        )
        before = bytes(other.geometria.wkb)
        self.run_import([feature()])
        other.refresh_from_db()
        self.assertEqual(bytes(other.geometria.wkb), before)

    def test_checksum_and_force_reimport_are_idempotent(self):
        self.run_import([feature()])
        self.route.refresh_from_db()
        before = self.route.updated_at
        run = self.run_import()
        self.assertEqual(run.status, "UNCHANGED")
        run = self.run_import(force=True)
        self.route.refresh_from_db()
        self.assertEqual(run.skipped, 1)
        self.assertEqual(self.route.updated_at, before)
        self.assertEqual(Recorrido.objects.count(), 1)

    def test_catalogue_change_reprocesses_previously_unmatched_unchanged_feed(self):
        row = feature()
        row["properties"].update(recorrido="C", l_r_s="002CIDA")
        self.run_import([row])
        branch = Ramal.objects.create(linea=self.line, nombre="C")
        route = Recorrido.objects.create(
            ramal=branch,
            sentido="IDA",
            source=self.source,
            external_id="002CIDA",
            catalogue_format="csv",
        )
        run = self.run_import()
        route.refresh_from_db()
        self.assertNotEqual(run.status, "UNCHANGED")
        self.assertIsNotNone(route.geometria)

    def test_conflicting_duplicate_features_preserve_previous_geometry(self):
        self.run_import([feature()])
        self.route.refresh_from_db()
        before = bytes(self.route.geometria.wkb)
        changed = feature()
        changed["geometry"]["coordinates"][0][0] = [-58.42, -34.62]
        run = self.run_import([feature(), changed])
        self.route.refresh_from_db()
        self.assertEqual(run.metrics["conflictos"], 2)
        self.assertEqual(bytes(self.route.geometria.wkb), before)

    def test_dry_run_rolls_back_sources_runs_errors_and_shapes(self):
        before = (
            DataSource.objects.count(),
            ImportRun.objects.count(),
            ImportError.objects.count(),
        )
        run = self.run_import(
            [feature()], source_slug="official-shape-test", dry_run=True
        )
        self.assertEqual(run.created, 1)
        self.route.refresh_from_db()
        self.assertIsNone(self.route.geometria)
        self.assertEqual(
            (
                DataSource.objects.count(),
                ImportRun.objects.count(),
                ImportError.objects.count(),
            ),
            before,
        )

    def test_unexpected_update_failure_rolls_back_and_logs_failure(self):
        with patch.object(
            Recorrido, "save", side_effect=RuntimeError("forced failure")
        ):
            with self.assertRaises(CommandError):
                self.run_import([feature()])
        self.route.refresh_from_db()
        self.assertIsNone(self.route.geometria)
        self.assertEqual(ImportRun.objects.get().status, "FAILED")

    def test_geojson_flag_uses_new_configurable_default(self):
        document = {"type": "FeatureCollection", "features": [feature()]}
        with patch(
            "imports.route_geometries.load_document", return_value=(document, "a" * 64)
        ) as loader:
            with override_settings(
                BA_DATA_RECORRIDOS_GEOJSON_URL="https://cdn.buenosaires.gob.ar/custom.geojson"
            ):
                call_command(
                    "import_badata_recorridos",
                    geojson=True,
                    dry_run=True,
                    stdout=io.StringIO(),
                )
        self.assertEqual(
            loader.call_args.args[0], "https://cdn.buenosaires.gob.ar/custom.geojson"
        )
        self.assertFalse(ImportRun.objects.exists())

    def test_only_missing_preserves_shape_and_rematch_flag_with_independent_checksum(
        self,
    ):
        self.route.geometria = MultiLineString(
            LineString([[-58.5, -34.7], [-58.51, -34.71]]), srid=4326
        )
        self.route.requiere_rematch = False
        self.route.save()
        original = bytes(self.route.geometria.wkb)
        sample = self.run_import([feature()], only_missing=True)
        self.route.refresh_from_db()
        self.assertEqual(bytes(self.route.geometria.wkb), original)
        self.assertFalse(self.route.requiere_rematch)
        self.assertEqual(sample.kind, "geometrias_muestra")
        self.assertEqual(sample.skipped, 1)
        full = self.run_import()
        self.assertNotEqual(full.status, "UNCHANGED")
        self.assertEqual(full.kind, "geometrias")
        self.assertEqual(full.updated, 1)

    def test_numeric_branch_external_identity_uses_known_line_prefix(self):
        self.line.numero = "60"
        self.line.save()
        self.route.ramal.nombre = "1"
        self.route.ramal.save()
        self.route.external_id = "0601IDA"
        self.route.save()
        row = feature()
        row["properties"].update(linea="060", recorrido="1", l_r_s="0601IDA")
        run = self.run_import([row])
        self.assertEqual(run.metrics["match_exacto"], 1)
        self.assertEqual(run.created, 1)

    def test_ebus_absent_from_csv_is_unmatched_without_creating_catalogue(self):
        row = feature()
        row["properties"].update(linea="EBUS", recorrido="A", l_r_s="EBUSAIDA")
        run = self.run_import([row])
        self.assertEqual(run.metrics["sin_match"], 1)
        self.assertEqual(run.errors, 0)
        self.assertEqual(Linea.objects.count(), 1)

    def test_ebus_exact_identity_normalizes_case_and_spaces(self):
        self.line.numero = "EBUS"
        self.line.save()
        self.route.external_id = "EBUSBIDA"
        self.route.save()
        row = feature()
        row["properties"].update(linea="eBus", recorrido=" b ", sentido="i", l_r_s=" ebus b ida ")
        run = self.run_import([row])
        self.assertEqual(run.metrics["match_exacto"], 1)
        self.assertEqual(run.created, 1)
        self.assertEqual(Linea.objects.get().numero, "EBUS")

    def test_geometry_change_preserves_every_historical_record(self):
        self.run_import([feature()])
        stop = Parada.objects.create(
            source=self.source, external_id="old", ubicacion=Point(-58.4, -34.6)
        )
        occurrences = [
            RecorridoParada.objects.create(recorrido=self.route, parada=stop, orden=n)
            for n in [1, 2]
        ]
        user = get_user_model().objects.create_user(
            username="history-shape", email="history-shape@example.test"
        )
        trip = RegistroViaje.objects.create(
            usuario=user,
            recorrido=self.route,
            inicio=occurrences[0],
            fin=occurrences[1],
        )
        UsuarioLineaParada.objects.create(
            usuario=user, linea=self.line, parada=stop, primer_viaje=trip
        )
        EventoPuntos.objects.create(
            usuario=user,
            tipo="PARADA_TRANSITADA",
            puntos=1,
            clave="old-point",
            viaje=trip,
            parada=stop,
            linea=self.line,
        )
        before = [
            list(model.objects.values())
            for model in [
                RegistroViaje,
                UsuarioLineaParada,
                EventoPuntos,
                RecorridoParada,
            ]
        ]
        row = feature()
        row["geometry"]["coordinates"][0][0] = [-58.42, -34.62]
        self.run_import([row])
        self.assertEqual(
            [
                list(model.objects.values())
                for model in [
                    RegistroViaje,
                    UsuarioLineaParada,
                    EventoPuntos,
                    RecorridoParada,
                ]
            ],
            before,
        )


class ImportDownloadSecurityTests(SimpleTestCase):
    def public_dns(self, host, port, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    def response(self, body=b"{}", status=200, headers=None):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status_code = status
        response.headers = {"Content-Type": "application/geo+json", **(headers or {})}
        response.iter_content.return_value = [body]
        return response

    @override_settings(DEBUG=False, IMPORT_ALLOWED_HOSTS=["cdn.buenosaires.gob.ar"])
    def test_production_rejects_unlisted_host_and_plain_http_before_network(self):
        with patch("imports.services.socket.getaddrinfo") as dns:
            for url in [
                "https://example.com/data.json",
                "http://cdn.buenosaires.gob.ar/data.json",
            ]:
                with self.assertRaises(ValueError):
                    validate_download_url(url)
        dns.assert_not_called()

    @override_settings(DEBUG=True)
    def test_private_loopback_and_reserved_dns_addresses_are_rejected(self):
        for address in [
            "127.0.0.1",
            "10.0.0.1",
            "169.254.169.254",
            "::1",
            "::ffff:127.0.0.1",
        ]:
            with patch(
                "imports.services.socket.getaddrinfo",
                return_value=[
                    (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))
                ],
            ):
                with self.assertRaises(ValueError):
                    validate_download_url("https://example.test/source")

    @override_settings(DEBUG=False, IMPORT_ALLOWED_HOSTS=["cdn.buenosaires.gob.ar"])
    def test_public_https_is_loaded_with_bounded_stream_and_no_environment_proxy(self):
        with patch(
            "imports.services.socket.getaddrinfo", side_effect=self.public_dns
        ), patch("imports.services.requests.Session") as factory:
            session = factory.return_value.__enter__.return_value
            session.get.return_value = self.response(b'{"ok":true}')
            raw, checksum = load_bytes("https://cdn.buenosaires.gob.ar/data.geojson")
            self.assertEqual(raw, b'{"ok":true}')
            self.assertEqual(len(checksum), 64)
            self.assertFalse(session.trust_env)
            self.assertFalse(session.get.call_args.kwargs["allow_redirects"])
            self.assertTrue(session.get.call_args.kwargs["stream"])

    @override_settings(DEBUG=True)
    def test_redirect_is_revalidated_before_following(self):
        with patch(
            "imports.services.socket.getaddrinfo", side_effect=self.public_dns
        ), patch("imports.services.requests.Session") as factory:
            session = factory.return_value.__enter__.return_value
            session.get.return_value = self.response(
                status=302, headers={"Location": "file:///etc/passwd"}
            )
            with self.assertRaises(ValueError):
                load_bytes("https://cdn.buenosaires.gob.ar/data.geojson")
            self.assertEqual(session.get.call_count, 1)

    @override_settings(DEBUG=True, IMPORT_MAX_BYTES=8)
    def test_download_size_and_mime_are_validated(self):
        for response in [
            self.response(b"too-large-payload"),
            self.response(headers={"Content-Length": "500"}),
            self.response(headers={"Content-Type": "text/html"}),
        ]:
            with patch(
                "imports.services.socket.getaddrinfo", side_effect=self.public_dns
            ), patch("imports.services.requests.Session") as factory:
                factory.return_value.__enter__.return_value.get.return_value = response
                with self.assertRaises(ValueError):
                    load_bytes("https://cdn.buenosaires.gob.ar/data.geojson")

    def test_non_http_scheme_is_not_a_local_path(self):
        with self.assertRaises(ValueError):
            load_bytes("file:///etc/passwd")

    @override_settings(IMPORT_MAX_FEATURES=1)
    def test_feature_count_is_bounded(self):
        with self.assertRaises(ValueError):
            validate_geojson(
                {"type": "FeatureCollection", "features": [feature(), feature()]}
            )
