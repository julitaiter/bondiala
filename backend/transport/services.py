from collections import defaultdict
from django.db.models import Prefetch
from .models import Linea, Ramal, Recorrido, RecorridoParada
from trips.models import UsuarioLineaParada


def catalog():
    sequence = official_sequence().select_related("parada").order_by("orden")
    routes = Recorrido.objects.filter(activo=True).prefetch_related(
        Prefetch("secuencia", queryset=sequence)
    )
    branches = Ramal.objects.filter(activo=True).prefetch_related(
        Prefetch("recorridos", queryset=routes)
    )
    return (
        Linea.objects.filter(activa=True)
        .select_related("colores")
        .prefetch_related(Prefetch("ramales", queryset=branches))
    )


def official_sequence():
    """Secuencia actual para consulta y viajes; el historial legacy se conserva."""
    return RecorridoParada.objects.filter(
        activa=True, parada__activa=True, parada__es_oficial=True
    )


def route_availability(route):
    # Usa el prefetch del catálogo/API para no consultar una vez por recorrido.
    stops = [
        item
        for item in route.secuencia.all()
        if item.activa and item.parada.activa and item.parada.es_oficial
    ]
    count = len(stops)
    usable = route.geometria is not None and count >= 2
    state = (
        "sin_geometria"
        if route.geometria is None
        else "sin_paradas"
        if not count
        else "parcial"
        if not usable
        else "disponible"
    )
    return {
        "paradas_oficiales_count": count,
        "puede_registrar_viaje": usable,
        "estado_datos": state,
    }


def visited_by_line(user):
    found = defaultdict(set)
    if user and user.is_authenticated:
        for line, stop in UsuarioLineaParada.objects.filter(usuario=user).values_list(
            "linea_id", "parada_id"
        ):
            found[line].add(stop)
    return found


def fraction(required, visited):
    total = len(required)
    done = len(required & visited)
    return {
        "total": total,
        "transitadas": done,
        "porcentaje": round(100 * done / total, 1) if total else 0,
        "completo": bool(total) and done == total,
    }


def line_progress(line, visited):
    branches = []
    all_stops = set()
    for branch in line.ramales.all():
        routes = []
        branch_stops = set()
        for route in branch.recorridos.all():
            required = {item.parada_id for item in route.secuencia.all()}
            branch_stops.update(required)
            routes.append(
                {
                    "id": route.pk,
                    "sentido": route.sentido,
                    **fraction(required, visited),
                }
            )
        all_stops.update(branch_stops)
        branches.append(
            {
                "id": branch.pk,
                "nombre": branch.nombre,
                **fraction(branch_stops, visited),
                "completo": bool(routes) and all(r["completo"] for r in routes),
                "recorridos": routes,
            }
        )
    return {
        "linea": line.pk,
        "numero": line.numero,
        **fraction(all_stops, visited),
        "completo": bool(branches) and all(b["completo"] for b in branches),
        "ramales": branches,
    }
