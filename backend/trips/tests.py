import uuid
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from django.contrib.gis.geos import Point, MultiLineString, LineString
from django.db import IntegrityError, transaction, close_old_connections, connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient
from accounts.models import User
from transport.models import (
    Linea,
    Ramal,
    Recorrido,
    Parada,
    RecorridoParada,
    normalize_line,
)
from transport.services import catalog, line_progress
from imports.models import DataSource
from gamification.models import EventoPuntos, UsuarioLogro, Logro
from gamification.services import ranking, week_bounds, total_points
from social.models import Follow
from .models import RegistroViaje, UsuarioLineaParada
from .services import register_trip


def network():
    source = DataSource.objects.create(slug="test", nombre="Test")
    line = Linea.objects.create(numero="060", source=source)
    other = Linea.objects.create(numero="152", source=source)
    stops = [
        Parada.objects.create(
            source=source,
            external_id=str(i),
            nombre=f"Parada {i}",
            ubicacion=Point(-58.4 + i / 1000, -34.6, srid=4326),
        )
        for i in range(5)
    ]
    routes = []
    for route_line, branch, direction, indexes in [
        (line, "A", "IDA", [0, 1, 2]),
        (line, "A", "VUELTA", [2, 3, 0]),
        (line, "B", "IDA", [0, 1, 4]),
        (other, "A", "IDA", [0, 1, 2]),
    ]:
        ramal, _ = Ramal.objects.get_or_create(linea=route_line, nombre=branch)
        route = Recorrido.objects.create(
            ramal=ramal,
            sentido=direction,
            external_id=f"{route_line.numero}{branch}{direction}",
            source=source,
            geometria=MultiLineString(
                LineString([stops[i].ubicacion.coords for i in indexes]), srid=4326
            ),
        )
        for order, index in enumerate(indexes):
            RecorridoParada.objects.create(
                recorrido=route, parada=stops[index], orden=order
            )
        routes.append(route)
    return line, other, stops, routes


class ProgressTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="juli",
            nickname="Juli",
            email="juli@example.test",
            password="Bondi-seguro-2026!",
        )
        self.line, self.other, self.stops, self.routes = network()
        call_command("seed_game", verbosity=0)

    def trip(self, route_index=0, start=0, end=2, key=None):
        route = self.routes[route_index]
        items = list(route.secuencia.all())
        return register_trip(
            self.user, route.pk, items[start].pk, items[end].pk, key or uuid.uuid4()
        )[0]

    def test_normalization(self):
        self.assertEqual(self.line.numero, "60")
        for value, expected in [("002", "2"), ("060", "60"), (152, "152")]:
            self.assertEqual(normalize_line(value), expected)
        for value in [None, "", "-1", "a60", "0", "1.5"]:
            with self.assertRaises(ValueError):
                normalize_line(value)

    def test_inclusive_segment_and_points(self):
        trip = self.trip(end=1)
        self.assertEqual(trip.resultado["nuevas_paradas"], 2)
        self.assertEqual(total_points(self.user), 2)

    def test_repeat_trip_never_duplicates_points(self):
        self.trip()
        before = total_points(self.user)
        repeat = self.trip()
        self.assertEqual(repeat.resultado["nuevas_paradas"], 0)
        self.assertEqual(repeat.resultado["puntos"], 0)
        self.assertEqual(total_points(self.user), before)

    def test_idempotency_key_reuses_trip(self):
        key = uuid.uuid4()
        first = self.trip(key=key)
        again = self.trip(key=key)
        self.assertEqual(first.pk, again.pk)
        self.assertEqual(RegistroViaje.objects.count(), 1)

    def test_idempotency_key_payload_mismatch(self):
        key = uuid.uuid4()
        self.trip(key=key)
        with self.assertRaisesMessage(Exception, "clave"):
            self.trip(end=1, key=key)

    def test_shared_stops_count_across_branches(self):
        self.trip(end=1)
        progress = line_progress(
            catalog().get(pk=self.line.pk),
            set(self.user.paradas_transitadas.values_list("parada_id", flat=True)),
        )
        branch_b = next(b for b in progress["ramales"] if b["nombre"] == "B")
        self.assertEqual(branch_b["transitadas"], 2)
        self.assertFalse(branch_b["completo"])

    def test_stops_do_not_count_for_other_line(self):
        self.trip()
        self.assertFalse(
            UsuarioLineaParada.objects.filter(
                usuario=self.user, linea=self.other
            ).exists()
        )
        second = self.trip(3)
        self.assertEqual(second.resultado["nuevas_paradas"], 3)
        self.assertEqual(second.resultado["puntos"], 73)

    def test_completion_and_bonuses(self):
        self.trip()
        self.assertEqual(total_points(self.user), 8)
        self.trip(1)
        self.assertEqual(total_points(self.user), 29)
        final = self.trip(2)
        self.assertTrue(final.resultado["progreso"]["completo"])
        self.assertEqual(total_points(self.user), 100)
        self.assertEqual(
            EventoPuntos.objects.filter(tipo="LINEA_COMPLETADA").count(), 1
        )

    def test_completion_across_multiple_out_of_order_trips(self):
        self.trip(start=1)
        self.trip(end=1)
        self.assertEqual(
            EventoPuntos.objects.filter(tipo="SENTIDO_COMPLETADO").count(), 1
        )

    def test_empty_direction_does_not_complete(self):
        self.routes[0].secuencia.all().delete()
        progress = line_progress(
            catalog().get(pk=self.line.pk), {s.pk for s in self.stops}
        )
        self.assertFalse(progress["completo"])

    def test_achievements_are_idempotent(self):
        self.trip()
        count = UsuarioLogro.objects.count()
        self.trip()
        self.assertEqual(UsuarioLogro.objects.count(), count)
        self.assertTrue(
            UsuarioLogro.objects.filter(logro__slug="primera-parada").exists()
        )

    def test_achievement_bonus_is_ledger_event(self):
        Logro.objects.create(
            slug="bonus",
            nombre="Bonus",
            descripcion="Prueba",
            regla="paradas",
            objetivo=1,
            puntos=7,
        )
        self.trip(end=1)
        self.trip(end=1)
        self.assertEqual(total_points(self.user), 9)
        self.assertEqual(EventoPuntos.objects.filter(tipo="LOGRO").count(), 1)

    @patch(
        "trips.services.evaluate_achievements",
        side_effect=RuntimeError("fallo de prueba"),
    )
    def test_trip_rolls_back_everything_if_award_pipeline_fails(self, evaluate):
        with self.assertRaises(RuntimeError):
            self.trip()
        self.assertEqual(RegistroViaje.objects.count(), 0)
        self.assertEqual(UsuarioLineaParada.objects.count(), 0)
        self.assertEqual(EventoPuntos.objects.count(), 0)

    def test_reverse_or_foreign_stops_are_rejected(self):
        with self.assertRaises(Exception):
            self.trip(start=2, end=0)
        with self.assertRaises(Exception):
            register_trip(
                self.user,
                self.routes[0].pk,
                self.routes[1].secuencia.first().pk,
                self.routes[0].secuencia.last().pk,
                uuid.uuid4(),
            )
        self.assertEqual(RegistroViaje.objects.count(), 0)

    def test_db_constraints(self):
        trip = self.trip()
        with self.assertRaises(IntegrityError), transaction.atomic():
            UsuarioLineaParada.objects.create(
                usuario=self.user,
                linea=self.line,
                parada=self.stops[0],
                primer_viaje=trip,
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            EventoPuntos.objects.create(
                usuario=self.user,
                clave=self.user.eventos.first().clave,
                tipo="LOGRO",
                puntos=100,
            )

    def test_weekly_ranking_uses_argentina_monday(self):
        self.trip()
        start, end = week_bounds()
        self.assertEqual(start.weekday(), 0)
        self.assertEqual(start.hour, 0)
        self.assertEqual(start.utcoffset().total_seconds(), -10800)
        self.assertEqual((end - start).days, 7)
        event = self.user.eventos.first()
        EventoPuntos.objects.filter(pk=event.pk).update(
            fecha=start - timezone.timedelta(seconds=1)
        )
        self.assertEqual(
            ranking("semanal").get(pk=self.user.pk).puntos,
            total_points(self.user) - event.puntos,
        )

    def test_friend_ranking_excludes_other_users_and_private_profiles(self):
        friend = User.objects.create_user(username="amiga", email="amiga@example.test")
        stranger = User.objects.create_user(username="otro", email="otro@example.test")
        Follow.objects.create(usuario=self.user, seguido=friend)
        self.assertSetEqual(
            set(ranking("amigos", self.user).values_list("pk", flat=True)),
            {self.user.pk, friend.pk},
        )
        friend.public_profile = False
        friend.save()
        self.assertFalse(ranking().filter(pk=friend.pk).exists())
        self.assertFalse(ranking("amigos", self.user).filter(pk=stranger.pk).exists())


@override_settings(
    REST_FRAMEWORK={
        **__import__("django.conf", fromlist=["settings"]).settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_CLASSES": [],
    }
)
class SecurityTests(TestCase):
    trip = ProgressTests.trip

    def setUp(self):
        ProgressTests.setUp(self)
        self.other_user = User.objects.create_user(
            username="otra",
            nickname="Otra",
            email="otra@example.test",
            password="Clave-segura-123!",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_cannot_read_other_users_private_trip(self):
        trip = self.trip()
        self.client.force_authenticate(self.other_user)
        self.assertEqual(self.client.get(f"/api/v1/viajes/{trip.pk}/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/viajes/").data["count"], 0)

    def test_cannot_modify_or_delete_another_users_trip(self):
        trip = self.trip()
        self.client.force_authenticate(self.other_user)
        for method in [self.client.patch, self.client.delete]:
            self.assertIn(
                method(f"/api/v1/viajes/{trip.pk}/", {}, format="json").status_code,
                [404, 405],
            )
        self.assertTrue(RegistroViaje.objects.filter(pk=trip.pk).exists())

    def test_forged_points_and_ownership_rejected(self):
        route = self.routes[0]
        items = list(route.secuencia.all())
        payload = {
            "recorrido": route.pk,
            "inicio": items[0].pk,
            "fin": items[-1].pk,
            "puntos": 100000,
            "usuario": self.other_user.pk,
        }
        self.assertEqual(
            self.client.post("/api/v1/viajes/", payload, format="json").status_code, 400
        )
        self.assertEqual(EventoPuntos.objects.count(), 0)

    def test_api_trip_and_repeat(self):
        items = list(self.routes[0].secuencia.all())
        payload = {
            "recorrido": self.routes[0].pk,
            "inicio": items[0].pk,
            "fin": items[-1].pk,
            "idempotency_key": str(uuid.uuid4()),
        }
        first = self.client.post("/api/v1/viajes/", payload, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post("/api/v1/viajes/", payload, format="json")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["id"], second.data["id"])

    def test_normal_user_cannot_use_admin(self):
        self.client.force_authenticate(None)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/admin/transport/linea/").status_code, 302)
        self.assertIn(
            self.client.post(
                "/admin/transport/linea/add/", {"numero": "999"}
            ).status_code,
            [302, 403],
        )
        self.assertFalse(Linea.objects.filter(numero="999").exists())

    def test_public_profile_never_exposes_email_or_trips(self):
        response = self.client.get(f"/api/v1/perfiles/{self.user.username}/")
        self.assertEqual(response.status_code, 200)
        for field in ["email", "viajes", "theme", "public_profile"]:
            self.assertNotIn(field, response.data)
        self.user.public_profile = False
        self.user.save()
        self.assertEqual(
            self.client.get(f"/api/v1/perfiles/{self.user.username}/").status_code, 404
        )

    def test_private_progress_requires_authentication(self):
        self.client.force_authenticate(None)
        for endpoint in ["viajes", "progreso", "amigos"]:
            self.assertIn(
                self.client.get(f"/api/v1/{endpoint}/").status_code, [401, 403]
            )

    def test_public_lists_are_paginated(self):
        User.objects.bulk_create(
            [
                User(
                    username=f"persona{i}",
                    email=f"persona{i}@example.test",
                    nickname=f"Persona {i}",
                )
                for i in range(30)
            ]
        )
        response = self.client.get("/api/v1/rankings/")
        self.assertEqual(len(response.data["results"]), 24)
        self.assertIsNotNone(response.data["next"])
        next_page = self.client.get("/api/v1/rankings/?page=2")
        self.assertEqual(next_page.data["results"][0]["posicion"], 25)

    def test_follow_is_owned_and_idempotent(self):
        first = self.client.post(
            "/api/v1/amigos/", {"seguido": self.other_user.pk}, format="json"
        )
        second = self.client.post(
            "/api/v1/amigos/", {"seguido": self.other_user.pk}, format="json"
        )
        self.assertEqual(first.data["id"], second.data["id"])
        self.client.force_authenticate(self.other_user)
        self.assertEqual(
            self.client.delete(f"/api/v1/amigos/{first.data['id']}/").status_code, 404
        )

    def test_login_requires_csrf_and_rotates_session(self):
        client = APIClient(enforce_csrf_checks=True)
        credentials = {"identifier": self.user.email, "password": "Bondi-seguro-2026!"}
        self.assertEqual(
            client.post("/api/v1/auth/login/", credentials, format="json").status_code,
            403,
        )
        token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        response = client.post(
            "/api/v1/auth/login/", credentials, format="json", HTTP_X_CSRFTOKEN=token
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(client.cookies["sessionid"]["httponly"])
        self.assertEqual(client.get("/api/v1/me/").data["user"]["id"], self.user.pk)
        new_token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        self.assertEqual(
            client.post(
                "/api/v1/auth/logout/", {}, format="json", HTTP_X_CSRFTOKEN=new_token
            ).status_code,
            204,
        )

    def test_registration_validates_password_and_unique_email(self):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        data = {
            "username": "nueva",
            "nickname": "Nueva",
            "email": "nueva@example.test",
            "password": "123",
        }
        self.assertEqual(
            client.post(
                "/api/v1/auth/registro/", data, format="json", HTTP_X_CSRFTOKEN=token
            ).status_code,
            400,
        )
        data["password"] = "Bondiala-Explorar-2026!"
        self.assertEqual(
            client.post(
                "/api/v1/auth/registro/", data, format="json", HTTP_X_CSRFTOKEN=token
            ).status_code,
            201,
        )
        self.assertEqual(User.objects.filter(email=data["email"]).count(), 1)


class ConcurrentTripTests(TransactionTestCase):
    def test_concurrent_trips_award_only_once(self):
        user = User.objects.create_user(
            username="concurrent", email="concurrent@example.test"
        )
        line, _, _, routes = network()
        route = routes[0]
        items = list(route.secuencia.all())

        def submit(_):
            close_old_connections()
            try:
                register_trip(
                    User.objects.get(pk=user.pk),
                    route.pk,
                    items[0].pk,
                    items[-1].pk,
                    uuid.uuid4(),
                )
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(submit, range(2)))
        self.assertEqual(
            UsuarioLineaParada.objects.filter(usuario=user, linea=line).count(), 3
        )
        self.assertEqual(total_points(user), 8)
