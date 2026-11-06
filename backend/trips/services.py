from django.contrib.auth import get_user_model
from django.db import connection, transaction
from rest_framework.exceptions import ValidationError
from transport.models import Recorrido
from transport.services import catalog, line_progress, official_sequence, routes_with_quality, route_availability, visited_by_line
from gamification.services import award, evaluate_achievements
from gamification.models import EventoPuntos
from .models import RegistroViaje, UsuarioLineaParada


@transaction.atomic
def register_trip(user, recorrido, inicio, fin, idempotency_key):
    # Se comparte entre viajes y excluye reconciliación/importación de secuencias.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock_shared(6132041)")
    # Serializa viajes concurrentes del mismo usuario, incluso con claves distintas.
    get_user_model().objects.select_for_update().get(pk=user.pk)
    previous = RegistroViaje.objects.filter(
        usuario=user, idempotency_key=idempotency_key
    ).first()
    if previous:
        if (previous.recorrido_id, previous.inicio_id, previous.fin_id) != (
            recorrido,
            inicio,
            fin,
        ):
            raise ValidationError("Esta clave ya se usó para otro viaje.")
        return previous, False
    route = (
        routes_with_quality().select_related("ramal__linea").prefetch_related("secuencia__parada")
        .filter(
            pk=recorrido, activo=True, ramal__activo=True, ramal__linea__activa=True
        )
        .first()
    )
    if route is None:
        raise ValidationError({"recorrido": "El recorrido no está disponible."})
    sequence = official_sequence().filter(recorrido=route)
    if not route_availability(route)["puede_registrar_viaje"]:
        raise ValidationError(
            {"recorrido": "Paradas oficiales aún no disponibles para registrar este viaje."}
        )
    occurrences = {
        x.pk: x
        for x in sequence.filter(pk__in=[inicio, fin])
    }
    if inicio not in occurrences or fin not in occurrences:
        raise ValidationError("Las paradas deben pertenecer al recorrido seleccionado.")
    start, end = occurrences[inicio], occurrences[fin]
    if start.orden >= end.orden:
        raise ValidationError(
            "La bajada debe estar después de la subida en este sentido."
        )
    trip = RegistroViaje.objects.create(
        usuario=user,
        recorrido=route,
        inicio=start,
        fin=end,
        idempotency_key=idempotency_key,
    )
    line = route.ramal.linea
    stops = sequence.filter(
        orden__gte=start.orden, orden__lte=end.orden
    ).values_list("parada_id", flat=True)
    new_count = 0
    visited = visited_by_line(user).get(line.pk, set())
    for stop in set(stops):
        if stop in visited:
            continue
        _, created = UsuarioLineaParada.objects.get_or_create(
            usuario=user, linea=line, parada_id=stop, defaults={"primer_viaje": trip}
        )
        if created:
            visited.add(stop)
            new_count += 1
            award(
                user,
                "PARADA_TRANSITADA",
                f"parada:{line.pk}:{stop}",
                trip,
                linea=line,
                parada_id=stop,
            )
    progress = line_progress(catalog().get(pk=line.pk), visited)
    for branch in progress["ramales"]:
        for direction in branch["recorridos"]:
            if direction["completo"]:
                award(
                    user,
                    "SENTIDO_COMPLETADO",
                    f"sentido:{direction['id']}",
                    trip,
                    linea=line,
                    ramal_id=branch["id"],
                    recorrido_id=direction["id"],
                )
        if branch["completo"]:
            award(
                user,
                "RAMAL_COMPLETADO",
                f"ramal:{branch['id']}",
                trip,
                linea=line,
                ramal_id=branch["id"],
            )
    if progress["completo"]:
        award(user, "LINEA_COMPLETADA", f"linea:{line.pk}", trip, linea=line)
    achievements = evaluate_achievements(user, trip)
    points = sum(
        EventoPuntos.objects.filter(viaje=trip).values_list("puntos", flat=True)
    )
    trip.resultado = {
        "nuevas_paradas": new_count,
        "puntos": points,
        "logros": achievements,
        "progreso": progress,
    }
    trip.save(update_fields=["resultado"])
    return trip, True
