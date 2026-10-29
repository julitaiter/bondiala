from datetime import timedelta
from django.db.models import Q, Sum, Value, IntegerField, Count
from django.db.models.functions import Coalesce
from django.utils import timezone
from accounts.models import User
from .models import EventoPuntos, Nivel, Logro, UsuarioLogro

POINTS = {
    "PARADA_TRANSITADA": 1,
    "SENTIDO_COMPLETADO": 5,
    "RAMAL_COMPLETADO": 15,
    "LINEA_COMPLETADA": 50,
}


def total_points(user):
    return user.eventos.aggregate(total=Sum("puntos"))["total"] or 0


def level_for(points, levels=None):
    levels = list(Nivel.objects.all()) if levels is None else levels
    current = next(
        (level for level in reversed(levels) if level.puntos_minimos <= points), None
    )
    upcoming = next((level for level in levels if level.puntos_minimos > points), None)
    return {
        "numero": current.numero if current else 1,
        "nombre": current.nombre if current else "Pasajero",
        "puntos_minimos": current.puntos_minimos if current else 0,
        "siguiente": {
            "numero": upcoming.numero,
            "puntos_minimos": upcoming.puntos_minimos,
        }
        if upcoming
        else None,
    }


def award(user, kind, key, viaje, **references):
    return EventoPuntos.objects.get_or_create(
        usuario=user,
        clave=key,
        defaults={"tipo": kind, "puntos": POINTS[kind], "viaje": viaje, **references},
    )[1]


def achievement_metrics(user):
    counts = dict(
        user.eventos.values("tipo").annotate(n=Count("pk")).values_list("tipo", "n")
    )
    stops = user.paradas_transitadas
    return {
        "paradas": stops.count(),
        "sentidos": counts.get("SENTIDO_COMPLETADO", 0),
        "ramales": counts.get("RAMAL_COMPLETADO", 0),
        "lineas": counts.get("LINEA_COMPLETADA", 0),
        "barrios": stops.exclude(parada__barrio="")
        .values("parada__barrio")
        .distinct()
        .count(),
        "comunas": stops.exclude(parada__comuna="")
        .values("parada__comuna")
        .distinct()
        .count(),
    }


def evaluate_achievements(user, viaje):
    metrics = achievement_metrics(user)
    obtained = []
    for achievement in Logro.objects.filter(activo=True):
        if metrics.get(achievement.regla, 0) < achievement.objetivo:
            continue
        _, created = UsuarioLogro.objects.get_or_create(usuario=user, logro=achievement)
        if created:
            obtained.append({"slug": achievement.slug, "nombre": achievement.nombre})
            if achievement.puntos:
                EventoPuntos.objects.get_or_create(
                    usuario=user,
                    clave=f"logro:{achievement.pk}",
                    defaults={
                        "tipo": "LOGRO",
                        "puntos": achievement.puntos,
                        "logro": achievement,
                        "viaje": viaje,
                    },
                )
    return obtained


def week_bounds():
    today = timezone.localtime()
    start = (today - timedelta(days=today.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return start, start + timedelta(days=7)


def ranking(scope="global", user=None):
    users = User.objects.filter(is_active=True, public_profile=True)
    condition = Q()
    if scope == "semanal":
        start, end = week_bounds()
        condition = Q(eventos__fecha__gte=start, eventos__fecha__lt=end)
    if scope == "amigos":
        ids = user.following.values_list("seguido_id", flat=True)
        users = users.filter(Q(pk__in=ids) | Q(pk=user.pk))
    return users.annotate(
        puntos=Coalesce(
            Sum("eventos__puntos", filter=condition),
            Value(0),
            output_field=IntegerField(),
        )
    ).order_by("-puntos", "pk")


def rank_position(user, scope="global"):
    if not user.public_profile:
        return None
    board = ranking(scope, user)
    entry = board.filter(pk=user.pk).first()
    if not entry:
        return None
    return (
        board.filter(
            Q(puntos__gt=entry.puntos) | Q(puntos=entry.puntos, pk__lt=user.pk)
        ).count()
        + 1
    )
