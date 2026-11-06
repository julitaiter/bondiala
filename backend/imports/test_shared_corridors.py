"""Shared corridor evidence and exact preservation during expanded rematching."""
import json
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString, MultiLineString, Point
from django.test import TestCase, override_settings

from gamification.models import EventoPuntos
from imports.models import DataSource, ImportRun, StopMatchIssue
from imports.official_stops import import_official_stops
from imports.test_official_stops import official
from transport.models import Linea, Parada, Ramal, Recorrido, RecorridoParada
from trips.models import RegistroViaje, UsuarioLineaParada


class SharedCorridorTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "stops.geojson"
        self.catalogue = DataSource.objects.create(slug="badata", nombre="CSV")
        self.line = Linea.objects.create(numero="60", source=self.catalogue)
        self.route = self.add_route("A")

    def add_route(self, name, components=None, direction="IDA"):
        branch, _ = Ramal.objects.get_or_create(linea=self.line, nombre=name)
        components = components or [[[-58.405, -34.6], [-58.395, -34.6]]]
        return Recorrido.objects.create(
            ramal=branch, sentido=direction, source=self.catalogue,
            external_id=f"060{name}{direction}",
            geometria=MultiLineString(*[LineString(c) for c in components], srid=4326),
        )

    def load(self, features=None, **options):
        if features is not None:
            self.path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
        return import_official_stops(str(self.path), **options)

    def active(self):
        return RecorridoParada.objects.filter(activa=True, parada__es_oficial=True)

    def test_overlapping_branches_create_multiple_audited_associations(self):
        second = self.add_route("B")
        run = self.load([official()], match=True)
        self.assertEqual(set(self.active().values_list("recorrido_id", flat=True)), {self.route.pk, second.pk})
        self.assertEqual(run.metrics["asociaciones_ambiguas"], 0)
        self.assertEqual(run.metrics["asociaciones_corredor_compartido"], 2)
        evidence = self.active().first().evidencia
        self.assertEqual(evidence["policy"], "shared_corridor")
        self.assertEqual(evidence["candidate_routes"], [self.route.pk, second.pk])
        self.assertTrue(evidence["comparisons"][0]["accepted"])
        self.assertGreaterEqual(evidence["comparisons"][0]["support_meters"], 90)

    def test_small_cartographic_offset_still_shares_oriented_corridor(self):
        self.add_route("B", [[[-58.405, -34.60005], [-58.395, -34.60005]]])
        self.load([official()], match=True)
        self.assertEqual(self.active().count(), 2)
        self.assertLess(self.active().first().evidencia["comparisons"][0]["maximum_separation_meters"], 12)

    def test_parallel_streets_are_ambiguous_even_with_large_nearest_gap(self):
        self.add_route("B", [[[-58.405, -34.6004], [-58.395, -34.6004]]])
        run = self.load([official()], match=True)
        self.assertFalse(self.active().exists())
        self.assertEqual(run.metrics["asociaciones_ambiguas"], 1)
        issue = StopMatchIssue.objects.get(reason="ambiguous_branches", status="pending")
        self.assertGreater(issue.candidates[1]["distancia_metros"] - issue.candidates[0]["distancia_metros"], 15)
        self.assertEqual(issue.candidates[0]["corridor_evidence"][0]["reason"], "divergent_corridors")

    def test_crossing_at_stop_is_not_a_shared_corridor(self):
        self.add_route("B", [[[-58.4, -34.605], [-58.4, -34.595]]])
        self.load([official()], match=True)
        self.assertFalse(self.active().exists())
        self.assertTrue(StopMatchIssue.objects.filter(reason="ambiguous_branches").exists())

    def test_shared_subset_with_divergent_third_remains_ambiguous(self):
        self.add_route("B")
        self.add_route("C", [[[-58.4, -34.605], [-58.4, -34.595]]])
        self.load([official()], match=True)
        self.assertFalse(self.active().exists())
        comparisons = StopMatchIssue.objects.get(reason="ambiguous_branches").candidates[0]["corridor_evidence"]
        self.assertEqual(len(comparisons), 3)
        self.assertTrue(any(pair["accepted"] for pair in comparisons))
        self.assertTrue(any(not pair["accepted"] for pair in comparisons))

    def test_same_local_tangent_but_nearby_fork_is_not_shared(self):
        self.add_route("B", [[[-58.405, -34.6], [-58.3998, -34.6], [-58.3995, -34.5995], [-58.395, -34.5995]]])
        self.load([official()], match=True)
        self.assertFalse(self.active().exists())
        self.assertTrue(StopMatchIssue.objects.filter(reason="ambiguous_branches").exists())

    def test_opposite_geometry_direction_is_not_shared_despite_same_sense_label(self):
        self.add_route("B", [[[-58.395, -34.6], [-58.405, -34.6]]])
        self.load([official()], match=True)
        self.assertFalse(self.active().exists())
        comparison = StopMatchIssue.objects.get(reason="ambiguous_branches").candidates[0]["corridor_evidence"][0]
        self.assertGreater(comparison["maximum_heading_degrees"], 170)

    def test_short_coincidence_without_longitudinal_support_is_ambiguous(self):
        components = [[[-58.4002, -34.6], [-58.3998, -34.6]]]
        self.route.geometria = MultiLineString(LineString(components[0]), srid=4326)
        self.route.save()
        self.add_route("B", components)
        self.load([official()], match=True)
        self.assertFalse(self.active().exists())
        comparison = StopMatchIssue.objects.get(reason="ambiguous_branches").candidates[0]["corridor_evidence"][0]
        self.assertEqual(comparison["reason"], "insufficient_window")

    def test_multiline_cumulative_order_and_rematch_are_stable(self):
        components = [[[-58.405, -34.6], [-58.4, -34.6]], [[-58.4, -34.6], [-58.395, -34.6]]]
        self.route.geometria = MultiLineString(*[LineString(c) for c in components], srid=4326)
        self.route.save()
        self.add_route("B", components)
        run = self.load([official(x=-58.398, address="Second"), official(x=-58.402, address="First")], match=True)
        self.assertEqual(run.metrics["asociaciones_corredor_compartido"], 4)
        rows = list(self.route.secuencia.order_by("orden"))
        self.assertEqual([x.parada.direccion for x in rows], ["First", "Second"])
        self.assertGreater(rows[1].posicion_metros, rows[0].posicion_metros + 300)
        before = list(RecorridoParada.objects.order_by("pk").values())
        self.load(rematch=True)
        self.assertEqual(list(RecorridoParada.objects.order_by("pk").values()), before)

    def test_other_sense_and_missing_geometry_do_not_compete(self):
        opposite = self.add_route("B", direction="VUELTA")
        absent = self.add_route("C")
        absent.geometria = None
        absent.save()
        self.load([official()], match=True)
        self.assertEqual(self.active().get().recorrido_id, self.route.pk)
        self.assertFalse(opposite.secuencia.exists())
        self.assertEqual(self.active().get().evidencia["policy"], "single_candidate")

    def test_coverage_does_not_count_critical_loop_as_usable_with_two_known_stops(self):
        self.route.geometria = MultiLineString(LineString([
            [-58.405, -34.605], [-58.395, -34.595],
            [-58.405, -34.595], [-58.395, -34.605],
        ]), srid=4326)
        self.route.save()
        run = self.load([
            official(x=-58.404, y=-34.604, address="Before crossing"),
            official(x=-58.396, y=-34.604, address="After crossing"),
            official(),
        ], match=True)
        self.assertEqual(self.active().count(), 2)
        self.assertTrue(StopMatchIssue.objects.filter(reason="ambiguous_position").exists())
        self.assertEqual(run.metrics["recorridos_con_secuencia_utilizable"], 0)

    def test_rematch_dry_run_changes_neither_associations_nor_audit(self):
        self.load([official()], match=True)
        self.add_route("B")
        before = list(RecorridoParada.objects.order_by("pk").values())
        runs = ImportRun.objects.count()
        issues = StopMatchIssue.objects.count()
        run = self.load(rematch=True, dry_run=True)
        self.assertEqual(run.metrics["asociaciones_corredor_compartido"], 2)
        self.assertEqual(list(RecorridoParada.objects.order_by("pk").values()), before)
        self.assertEqual(ImportRun.objects.count(), runs)
        self.assertEqual(StopMatchIssue.objects.count(), issues)

    def test_historical_legacy_rows_are_exact_and_equivalence_is_only_alias(self):
        self.load([official(), official(x=-58.398, address="Second")])
        source = DataSource.objects.create(slug="muestra-paradas", nombre="Legacy")
        old = Parada.objects.create(source=source, external_id="old", ubicacion=Point(-58.4, -34.6))
        end = Parada.objects.create(source=source, external_id="end", ubicacion=Point(-58.398, -34.6))
        first = RecorridoParada.objects.create(recorrido=self.route, parada=old, orden=1)
        last = RecorridoParada.objects.create(recorrido=self.route, parada=end, orden=2)
        user = get_user_model().objects.create_user(username="history", password="Long-password-42")
        trip = RegistroViaje.objects.create(usuario=user, recorrido=self.route, inicio=first, fin=last)
        UsuarioLineaParada.objects.create(usuario=user, linea=self.line, parada=old, primer_viaje=trip)
        target = Parada.objects.get(es_oficial=True, direccion="Av. Prueba 100")
        UsuarioLineaParada.objects.create(usuario=user, linea=self.line, parada=target, primer_viaje=trip)
        EventoPuntos.objects.create(usuario=user, tipo="PARADA_TRANSITADA", puntos=1,
                                   clave="legacy-point", linea=self.line, parada=old, viaje=trip)
        before = {model: list(model.objects.order_by("pk").values()) for model in [RegistroViaje, UsuarioLineaParada, EventoPuntos]}
        self.add_route("B")
        self.load(rematch=True)
        for model, snapshot in before.items():
            self.assertEqual(list(model.objects.order_by("pk").values()), snapshot)
        first.refresh_from_db()
        last.refresh_from_db()
        old.refresh_from_db()
        self.assertEqual(first.parada_id, old.pk)
        self.assertEqual(last.parada_id, end.pk)
        self.assertEqual(old.metadata["official_equivalences"], {"60": target.pk})
        self.assertFalse(first.activa)
        self.assertTrue(StopMatchIssue.objects.filter(reason="legacy_history_preserved").exists())
