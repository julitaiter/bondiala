from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=60)
    avatar = models.URLField(blank=True)
    public_profile = models.BooleanField(default=True)
    theme = models.CharField(
        max_length=6,
        choices=[("system", "Sistema"), ("light", "Claro"), ("dark", "Oscuro")],
        default="system",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="user_email_ci_unique"),
            models.UniqueConstraint(Lower("username"), name="user_username_ci_unique"),
        ]
