import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, LineString, MultiLineString
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Sum
from django.test import TestCase, override_settings

from gamification.models import EventoPuntos
from imports.models import DataSource, ImportRun, ImportError, StopMatchIssue
from imports.official_stops import import_official_stops
from transport.models import Linea, Ramal, Recorrido, Parada, RecorridoParada
from trips.models import RegistroViaje, UsuarioLineaParada


def official(
    x=-58.4, y=-34.6, address="Av. Prueba 100", line="060", sense="I", **extra
):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [x, y]},
        "properties": {
            "CALLE": "Av. Prueba",
            "ALT PLANO": 100,
            "DIRECCION": address,
            "COMUNA": 1,
            "BARRIO": "Prueba",
            "L1": line,
            "l1_sen": sense,
            **extra,
        },
    }


class OfficialStopsTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "paradas.geojson"
        self.source = DataSource.objects.create(slug="badata", nombre="Catálogo CSV")
        self.line = Linea.objects.create(numero="60", source=self.source)
        self.route = self.route_for()

    def route_for(self, name="A", line=None, direction="IDA", coordinates=None):
        line = line or self.line
        branch, _ = Ramal.objects.get_or_create(linea=line, nombre=name)
        coords = coordinates or [[[-58.405, -34.6], [-58.395, -34.6]]]
        geom = MultiLineString(*[LineString(c) for c in coords], srid=4326)
        return Recorrido.objects.create(
            ramal=branch,
            sentido=direction,
            source=self.source,
            external_id=f"{line.numero}{name}{direction}",
            geometria=geom,
        )

    def run_import(self, features=None, **kwargs):
        if features is not None:
            self.path.write_text(
                json.dumps({"type": "FeatureCollection", "features": features})
            )
        return import_official_stops(str(self.path), **kwargs)

    def test_valid_geojson_point_and_normalized_line(self):
        run = self.run_import([official()], match=True)
        stop = Parada.objects.get()
        self.assertTrue(stop.es_oficial)
        self.assertEqual(stop.ubicacion.srid, 4326)
        self.assertEqual(stop.metadata["lineas"], [{"numero": "60", "sentido": "IDA"}])
        self.assertEqual(stop.barrio, "Prueba")
        self.assertEqual(run.created, 1)
        self.assertEqual(RecorridoParada.objects.get().recorrido, self.route)

    def test_reimport_checksum_and_rematch_are_idempotent(self):
        self.run_import(
            [official(), official(x=-58.398, address="Prueba 200")], match=True
        )
        ids = list(RecorridoParada.objects.values_list("pk", flat=True))
        run = self.run_import(match=True)
        self.assertEqual(run.status, "UNCHANGED")
        self.run_import(rematch=True)
        self.assertEqual(Parada.objects.count(), 2)
        self.assertEqual(
            list(RecorridoParada.objects.values_list("pk", flat=True)), ids
        )

    def test_rematch_recovers_ebus_without_losing_consolidated_services(self):
        ebus = Linea.objects.create(numero=" eBus ", source=self.source)
        route = self.route_for(line=ebus)
        self.run_import([official(line="eBUS")])
        stop = Parada.objects.get()
        # This is the previous parser's state plus a service merged from another
        # physical duplicate: origen contains EBUS, but lineas only retained 60.
        stop.metadata["lineas"] = [{"numero":"60", "sentido":"IDA"}]
        stop.save(update_fields=["metadata"])
        before_identity = (stop.pk, stop.external_id, bytes(stop.ubicacion.wkb))
        preview = self.run_import(rematch=True, dry_run=True)
        self.assertEqual(preview.metrics["paradas_servicios_actualizados"], 1)
        stop.refresh_from_db()
        self.assertEqual(stop.metadata["lineas"], [{"numero":"60", "sentido":"IDA"}])
        self.assertFalse(RecorridoParada.objects.exists())
        run = self.run_import(rematch=True)
        stop.refresh_from_db()
        self.assertEqual(run.metrics["paradas_servicios_actualizados"], 1)
        self.assertEqual(stop.metadata["lineas"], [
            {"numero":"60", "sentido":"IDA"}, {"numero":"EBUS", "sentido":"IDA"},
        ])
        self.assertEqual((stop.pk, stop.external_id, bytes(stop.ubicacion.wkb)), before_identity)
        self.assertEqual(set(RecorridoParada.objects.filter(activa=True).values_list("recorrido_id", flat=True)),
                         {self.route.pk, route.pk})
        before = list(RecorridoParada.objects.order_by("pk").values())
        repeat = self.run_import(rematch=True)
        self.assertEqual(repeat.metrics["paradas_servicios_actualizados"], 0)
        self.assertEqual(list(RecorridoParada.objects.order_by("pk").values()), before)

    def test_duplicate_physical_rows_merge_line_memberships(self):
        line2 = Linea.objects.create(numero="24", source=self.source)
        self.route_for(line=line2)
        run = self.run_import(
            [official(), official(address=" AV. PRUEBA   100 ", line=24)], match=True
        )
        self.assertEqual(Parada.objects.count(), 1)
        self.assertEqual(RecorridoParada.objects.count(), 2)
        self.assertEqual(run.metrics["duplicados_fisicos"], 1)

    def test_invalid_point_isolated_and_traced(self):
        bad = official()
        bad["geometry"] = {
            "type": "LineString",
            "coordinates": [[-58.4, -34.6], [-58.3, -34.5]],
        }
        run = self.run_import([bad, official()])
        self.assertEqual(Parada.objects.count(), 1)
        self.assertEqual(run.errors, 1)
        self.assertEqual(ImportError.objects.count(), 1)

    def test_out_of_range_coordinates_do_not_create_stop(self):
        run = self.run_import([official(x=200)])
        self.assertEqual(run.errors, 1)
        self.assertFalse(Parada.objects.exists())

    def test_unknown_line_keeps_physical_stop_without_match(self):
        run = self.run_import([official(line=999)], match=True)
        self.assertEqual(Parada.objects.count(), 1)
        self.assertFalse(RecorridoParada.objects.exists())
        self.assertEqual(run.metrics["paradas_sin_linea_reconocida"], 1)
        self.assertEqual(StopMatchIssue.objects.get().reason, "unknown_line")

    def test_sense_filters_candidates(self):
        vuelta = self.route_for(direction="VUELTA")
        self.run_import([official(sense="v")], match=True)
        self.assertEqual(RecorridoParada.objects.get().recorrido, vuelta)

    def test_different_parallel_corridors_are_not_chosen_by_distance_gap(self):
        other = self.route_for(
            name="B", coordinates=[[[-58.405, -34.6004], [-58.395, -34.6004]]]
        )
        self.run_import([official()], match=True)
        self.assertFalse(RecorridoParada.objects.exists())
        self.assertFalse(other.secuencia.exists())
        self.assertTrue(StopMatchIssue.objects.filter(reason="ambiguous_branches").exists())

    def test_identical_oriented_corridor_can_serve_both_branches(self):
        self.route_for(name="B")
        run = self.run_import([official()], match=True)
        self.assertEqual(RecorridoParada.objects.count(), 2)
        self.assertEqual(run.metrics["asociaciones_ambiguas"], 0)
        self.assertEqual(run.metrics["asociaciones_corredor_compartido"], 2)

    @override_settings(PARADA_MATCH_MAX_DISTANCE_METERS=20)
    def test_maximum_distance_uses_meters(self):
        self.run_import([official(y=-34.6004)], match=True)
        self.assertFalse(RecorridoParada.objects.exists())
        self.assertEqual(StopMatchIssue.objects.get().reason, "outside_threshold")

    def test_missing_geometry_is_auditable(self):
        self.route.geometria = None
        self.route.save()
        run = self.run_import([official()], match=True)
        self.assertEqual(StopMatchIssue.objects.get().reason, "no_geometry")
        self.assertEqual(run.metrics["recorridos_sin_geometria"], 1)

    def test_geometry_projection_orders_stops_not_coordinates(self):
        self.route.geometria = MultiLineString(
            LineString(
                [[-58.4, -34.6], [-58.39, -34.6], [-58.39, -34.61], [-58.4, -34.61]]
            ),
            srid=4326,
        )
        self.route.save()
        self.run_import(
            [
                official(x=-58.398, y=-34.61, address="Last"),
                official(x=-58.398, address="First"),
                official(x=-58.39, y=-34.605, address="Middle"),
            ],
            match=True,
        )
        self.assertEqual(
            list(self.route.secuencia.values_list("parada__direccion", flat=True)),
            ["First", "Middle", "Last"],
        )

    def test_multiline_cumulative_order_respects_stored_components(self):
        self.route.geometria = MultiLineString(
            LineString([[-58.4, -34.6], [-58.39, -34.6]]),
            LineString([[-58.3, -34.6], [-58.31, -34.6]]),
            srid=4326,
        )
        self.route.save()
        self.run_import(
            [
                official(x=-58.305, address="Second component"),
                official(x=-58.395, address="First component"),
            ],
            match=True,
        )
        rows = list(self.route.secuencia.all())
        self.assertEqual(
            [x.parada.direccion for x in rows], ["First component", "Second component"]
        )
        self.assertGreater(rows[1].posicion_metros, rows[0].posicion_metros)

    def test_self_intersection_position_ambiguity_is_not_silently_chosen(self):
        self.route.geometria = MultiLineString(
            LineString(
                [
                    [-58.405, -34.605],
                    [-58.395, -34.595],
                    [-58.405, -34.595],
                    [-58.395, -34.605],
                ]
            ),
            srid=4326,
        )
        self.route.save()
        self.run_import([official()], match=True)
        self.assertFalse(RecorridoParada.objects.exists())
        self.assertEqual(StopMatchIssue.objects.get().reason, "ambiguous_position")

    def test_physical_stop_can_serve_both_senses(self):
        self.route_for(direction="VUELTA")
        self.run_import([official(L2="60", l2_sen="V")], match=True)
        self.assertEqual(Parada.objects.count(), 1)
        self.assertEqual(RecorridoParada.objects.count(), 2)

    def test_unknown_sense_does_not_drop_valid_physical_row_or_other_services(self):
        run = self.run_import([official(sense="A-B", L2="60", l2_sen="V")], match=True)
        self.assertEqual(Parada.objects.count(), 1)
        self.assertEqual(run.errors, 0)
        self.assertEqual(run.metrics["advertencias_servicios"], 1)
        self.assertTrue(ImportError.objects.exists())
        self.assertTrue(
            StopMatchIssue.objects.filter(reason="unknown_direction").exists()
        )

    def test_dry_run_persists_nothing_including_audit(self):
        before = (
            DataSource.objects.count(),
            ImportRun.objects.count(),
            Parada.objects.count(),
            RecorridoParada.objects.count(),
        )
        run = self.run_import([official()], match=True, dry_run=True)
        self.assertEqual(run.created, 1)
        self.assertEqual(
            (
                DataSource.objects.count(),
                ImportRun.objects.count(),
                Parada.objects.count(),
                RecorridoParada.objects.count(),
            ),
            before,
        )
        self.assertFalse(StopMatchIssue.objects.exists())

    def legacy(self, x=-58.4, order=1):
        source, _ = DataSource.objects.get_or_create(
            slug="muestra-paradas", defaults={"nombre": "Ilustrativa"}
        )
        stop = Parada.objects.create(
            source=source, external_id=f"legacy-{order}", ubicacion=Point(x, -34.6)
        )
        occurrence = RecorridoParada.objects.create(
            recorrido=self.route, parada=stop, orden=order
        )
        return stop, occurrence

    def test_reconcile_unused_illustrative_preserves_occurrence_pk(self):
        old, occurrence = self.legacy()
        run = self.run_import([official()], match=True)
        occurrence.refresh_from_db()
        old.refresh_from_db()
        self.assertTrue(occurrence.parada.es_oficial)
        self.assertEqual(occurrence.metodo, "spatial")
        self.assertTrue(Parada.objects.filter(pk=old.pk).exists())
        self.assertTrue(old.metadata["legacy"])
        self.assertEqual(run.metrics["paradas_ilustrativas_reconciliadas"], 1)

    def historical(self):
        old, start = self.legacy()
        _, end = self.legacy(x=-58.398, order=2)
        user = get_user_model().objects.create_user(
            username="history",
            email="history@example.test",
            password="Strong-secret-42",
        )
        trip = RegistroViaje.objects.create(
            usuario=user, recorrido=self.route, inicio=start, fin=end
        )
        UsuarioLineaParada.objects.create(
            usuario=user, linea=self.line, parada=old, primer_viaje=trip
        )
        EventoPuntos.objects.create(
            usuario=user,
            tipo="PARADA_TRANSITADA",
            puntos=1,
            clave=f"parada:{self.line.pk}:{old.pk}",
            linea=self.line,
            parada=old,
            viaje=trip,
        )
        return old, start, end, user, trip

    def test_reconcile_historical_progress_does_not_change_ledger_or_trips(self):
        old, start, end, user, trip = self.historical()
        before = list(EventoPuntos.objects.values())
        beforetrip = list(RegistroViaje.objects.values())
        beforeprogress = list(UsuarioLineaParada.objects.values())
        self.run_import([official(), official(x=-58.398, address="Second")], match=True)
        start.refresh_from_db()
        old.refresh_from_db()
        self.assertEqual(start.parada_id, old.pk)
        self.assertTrue(old.metadata["official_equivalences"].get("60"))
        self.assertEqual(list(EventoPuntos.objects.values()), before)
        self.assertEqual(list(RegistroViaje.objects.values()), beforetrip)
        self.assertEqual(list(UsuarioLineaParada.objects.values()), beforeprogress)
        self.assertEqual(EventoPuntos.objects.aggregate(n=Sum("puntos"))["n"], 1)

    def test_reconcile_collision_preserves_both_historical_progress_rows(self):
        old, start, end, user, trip = self.historical()
        self.run_import([official(), official(x=-58.398, address="Second")])
        official_stop = Parada.objects.get(es_oficial=True, direccion="Av. Prueba 100")
        UsuarioLineaParada.objects.create(
            usuario=user, linea=self.line, parada=official_stop, primer_viaje=trip
        )
        self.run_import(rematch=True)
        self.assertEqual(UsuarioLineaParada.objects.count(), 2)
        self.assertEqual(EventoPuntos.objects.count(), 1)
        self.assertEqual(RegistroViaje.objects.count(), 1)

    def test_unresolved_illustrative_is_preserved_as_inactive_legacy(self):
        old, occurrence = self.legacy(x=-58.404)
        self.run_import([official(), official(x=-58.398, address="Second")], match=True)
        occurrence.refresh_from_db()
        old.refresh_from_db()
        self.assertFalse(occurrence.activa)
        self.assertFalse(old.es_oficial)
        self.assertEqual(occurrence.metodo, "legacy")
        self.assertTrue(
            StopMatchIssue.objects.filter(
                reason="legacy_unresolved", parada=old
            ).exists()
        )

    def test_existing_official_and_legacy_occurrences_do_not_become_duplicate_active(
        self,
    ):
        self.run_import([official(), official(x=-58.398, address="Second")], match=True)
        old, occurrence = self.legacy(order=100)
        _, end = self.legacy(x=-58.398, order=101)
        user = get_user_model().objects.create_user(
            username="late-history",
            email="late@example.test",
            password="Strong-secret-42",
        )
        trip = RegistroViaje.objects.create(
            usuario=user, recorrido=self.route, inicio=occurrence, fin=end
        )
        UsuarioLineaParada.objects.create(
            usuario=user, linea=self.line, parada=old, primer_viaje=trip
        )
        original_ids = list(self.route.secuencia.values_list("pk", flat=True))
        self.run_import(rematch=True)
        occurrence.refresh_from_db()
        self.assertFalse(occurrence.activa)
        self.assertEqual(occurrence.metodo, "legacy")
        self.assertEqual(
            self.route.secuencia.filter(activa=True, parada__es_oficial=True).count(), 2
        )
        self.assertEqual(
            set(self.route.secuencia.values_list("pk", flat=True)), set(original_ids)
        )
        self.assertEqual(RegistroViaje.objects.get().inicio_id, occurrence.pk)

    def test_repeated_legacy_physical_occurrence_remains_unresolved(self):
        old, first = self.legacy()
        second = RecorridoParada.objects.create(
            recorrido=self.route, parada=old, orden=2
        )
        run = self.run_import(
            [official(), official(x=-58.398, address="Second")], match=True
        )
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.parada_id, old.pk)
        self.assertEqual(second.parada_id, old.pk)
        self.assertFalse(first.activa)
        self.assertFalse(second.activa)
        self.assertEqual(run.metrics["paradas_ilustrativas_reconciliadas"], 0)

    def test_unexpected_matching_error_rolls_back_all_data(self):
        with patch(
            "imports.official_stops.match_routes",
            side_effect=RuntimeError("forced fault"),
        ):
            with self.assertRaises(CommandError):
                self.run_import([official()], match=True)
        self.assertFalse(Parada.objects.exists())
        self.assertFalse(RecorridoParada.objects.exists())
        self.assertEqual(ImportRun.objects.get().status, "FAILED")

    def test_empty_source_preserves_existing_catalogue(self):
        self.run_import([official()], match=True)
        with self.assertRaises(CommandError):
            self.run_import([])
        self.assertEqual(Parada.objects.count(), 1)
        self.assertEqual(RecorridoParada.objects.count(), 1)

    def test_import_only_then_match_identical_feed_does_not_skip_phase(self):
        self.run_import([official()])
        run = self.run_import(match=True)
        self.assertNotEqual(run.status, "UNCHANGED")
        self.assertEqual(RecorridoParada.objects.count(), 1)

    def test_moved_candidate_rematch_deactivates_previous_link_keeps_history(self):
        self.run_import([official()], match=True)
        occurrence = RecorridoParada.objects.get()
        self.route.geometria = MultiLineString(
            LineString([[-58.4, -34.7], [-58.3, -34.7]]), srid=4326
        )
        self.route.save()
        self.run_import(rematch=True)
        occurrence.refresh_from_db()
        self.assertFalse(occurrence.activa)
        self.assertEqual(RecorridoParada.objects.count(), 1)

    def test_default_official_url_and_command_dryrun(self):
        self.path.write_text(
            json.dumps({"type": "FeatureCollection", "features": [official()]})
        )
        with patch(
            "imports.official_stops.load_document",
            return_value=(json.loads(self.path.read_text()), "a" * 64),
        ) as loader:
            call_command("import_badata_paradas", dry_run=True, stdout=io.StringIO())
        self.assertTrue(
            loader.call_args.args[0].endswith("paradas-de-colectivo.geojson")
        )
        self.assertFalse(Parada.objects.exists())


class OfflineBootstrapIntegrationTests(TestCase):
    @override_settings(DEBUG=True)
    def test_documented_variants_and_ebus_fixtures_work_offline(self):
        from django.conf import settings
        from transport.services import official_sequence, route_availability, routes_with_quality

        output = io.StringIO()
        data = Path(settings.BADATA_RECORRIDOS_FILE).parent
        call_command("bootstrap", stdout=output)
        call_command("import_badata_recorridos", geojson=True,
                     file=str(data / "recorridos.variants.sample.geojson"), stdout=output)
        call_command("import_badata_paradas", match_routes=True,
                     file=str(data / "paradas.catalogue.sample.geojson"), stdout=output)
        self.assertEqual(Recorrido.objects.exclude(geometria=None).count(), 40)
        ebus = routes_with_quality().filter(ramal__linea__numero="EBUS").prefetch_related("secuencia__parada")
        self.assertEqual(ebus.count(), 2)
        for route in ebus:
            self.assertTrue(route_availability(route)["puede_registrar_viaje"])
            self.assertGreaterEqual(official_sequence().filter(recorrido=route).count(), 3)
        before = list(official_sequence().order_by("pk").values())
        call_command("bootstrap", stdout=output)
        self.assertEqual(before, list(official_sequence().order_by("pk").values()))
        self.assertEqual(Recorrido.objects.exclude(geometria=None).count(), 40)
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(RegistroViaje.objects.exists())
        self.assertFalse(EventoPuntos.objects.exists())

    @override_settings(DEBUG=True)
    def test_official_fixture_and_bootstrap_restart_preserve_public_sequences(self):
        """Exercise the exact offline catalogue/import path used by the E2E CI job."""
        from django.conf import settings
        from transport.services import catalog, official_sequence, route_availability

        output = io.StringIO()
        fixture = (
            Path(settings.BASE_DIR).parent / "data" / "paradas.official.sample.geojson"
        )
        call_command("bootstrap", stdout=output)
        self.assertEqual(Linea.objects.count(), 135)
        self.assertEqual(Recorrido.objects.count(), 1120)
        self.assertEqual(Recorrido.objects.exclude(geometria=None).count(), 24)
        self.assertEqual(
            Parada.objects.filter(source__slug="muestra-paradas").count(), 202
        )

        call_command(
            "import_badata_paradas",
            file=str(fixture),
            match_routes=True,
            stdout=output,
        )
        usable = sum(
            route_availability(route)["puede_registrar_viaje"]
            for line in catalog()
            for branch in line.ramales.all()
            for route in branch.recorridos.all()
        )
        self.assertGreaterEqual(usable, 3)
        official_before = list(
            official_sequence()
            .order_by("pk")
            .values_list("pk", "parada_id", "recorrido_id", "orden")
        )
        inactive_legacy = set(
            RecorridoParada.objects.filter(
                parada__source__slug="muestra-paradas", activa=False
            ).values_list("pk", flat=True)
        )
        self.assertTrue(inactive_legacy)
        stop_ids = set(Parada.objects.values_list("pk", flat=True))

        call_command(
            "import_badata_paradas",
            file=str(fixture),
            match_routes=True,
            stdout=output,
        )
        self.assertEqual(
            ImportRun.objects.filter(source__slug="badata-paradas").latest("pk").status,
            "UNCHANGED",
        )
        # Container restart runs bootstrap again; it must leave imported data intact.
        call_command("bootstrap", stdout=output)
        self.assertEqual(
            list(
                official_sequence()
                .order_by("pk")
                .values_list("pk", "parada_id", "recorrido_id", "orden")
            ),
            official_before,
        )
        self.assertEqual(set(Parada.objects.values_list("pk", flat=True)), stop_ids)
        self.assertFalse(
            RecorridoParada.objects.filter(pk__in=inactive_legacy, activa=True).exists()
        )
        self.assertTrue(
            all(
                occurrence.parada.es_oficial
                for line in catalog()
                for branch in line.ramales.all()
                for route in branch.recorridos.all()
                for occurrence in route.secuencia.all()
            )
        )
