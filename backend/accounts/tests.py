from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from .models import User


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RecoveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="bondiero",
            email="bondiero@example.test",
            password="Original-segura-2026!",
        )
        self.client = APIClient(enforce_csrf_checks=True)

    def post(self, endpoint, data):
        token = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        return self.client.post(endpoint, data, format="json", HTTP_X_CSRFTOKEN=token)

    def test_reset_sends_frontend_link_and_does_not_reveal_account(self):
        first = self.post("/api/v1/auth/recuperar/", {"email": self.user.email})
        second = self.post("/api/v1/auth/recuperar/", {"email": "absent@example.test"})
        self.assertEqual(first.data, second.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/restablecer?uid=", mail.outbox[0].body)

    def test_reset_token_cannot_be_reused(self):
        token = default_token_generator.make_token(self.user)
        payload = {
            "uid": urlsafe_base64_encode(force_bytes(self.user.pk)),
            "token": token,
            "password": "Una-clave-totalmente-nueva-2026!",
        }
        self.assertEqual(
            self.post("/api/v1/auth/restablecer/", payload).status_code, 200
        )
        self.assertEqual(
            self.post("/api/v1/auth/restablecer/", payload).status_code, 400
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(payload["password"]))
