from django.conf import settings
from django.db import models


class Follow(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following"
    )
    seguido = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="followers"
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "seguido"], name="follow_unique"
            ),
            models.CheckConstraint(
                condition=~models.Q(usuario=models.F("seguido")), name="no_self_follow"
            ),
        ]
