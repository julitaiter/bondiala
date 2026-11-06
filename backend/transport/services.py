from collections import defaultdict
from django.db.models import Exists, OuterRef, Prefetch
from django.db.models.functions import JSONArray, JSONObject
from .models import Linea, Ramal, Recorrido, RecorridoParada
from trips.models import UsuarioLineaParada


def catalog():
    sequence = official_sequence().select_related("parada").order_by("orden")
    routes = routes_with_quality().filter(activo=True).prefetch_related(
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
        activa=True, parada__activa=True, parada__es_oficial=True,
        recorrido__requiere_rematch=False,
    )


def routes_with_quality(queryset=None):
    from imports.models import StopMatchIssue

    issues = StopMatchIssue.objects.filter(
        status="pending", linea=OuterRef("ramal__linea__numero"),
        sentido=OuterRef("sentido"),
    )
    query = queryset if queryset is not None else Recorrido.objects.all()
    return query.annotate(
        critical_association=Exists(issues.filter(
            reason="ambiguous_position",
            candidates__contains=JSONArray(JSONObject(
                recorrido=OuterRef("pk"), position_ambiguous=True,
            )),
        )),
        partial_association=Exists(issues.filter(
            reason="ambiguous_branches",
            candidates__contains=JSONArray(JSONObject(recorrido=OuterRef("pk"))),
        )),
    )


def route_availability(route):
    # Usa el prefetch del catálogo/API para no consultar una vez por recorrido.
    count = getattr(route, "official_count", None)
    if count is None:
        count = sum(
            item.activa and item.parada.activa and item.parada.es_oficial
            for item in route.secuencia.all()
        )
    critical = getattr(route, "critical_association", False)
    pending = getattr(route, "requiere_rematch", False)
    partial = getattr(route, "partial_association", False)
    usable = route.geometria is not None and count >= 2 and not critical and not pending
    state = (
        "sin_geometria"
        if route.geometria is None
        else "ambiguo"
        if critical
        else "parcial"
        if pending
        else "sin_paradas"
        if not count
        else "parcial"
        if not usable or partial
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
        for line, number, stop, metadata in UsuarioLineaParada.objects.filter(usuario=user).values_list(
            "linea_id", "linea__numero", "parada_id", "parada__metadata"
        ):
            found[line].add(stop)
            aliases = metadata.get("official_equivalences", {})
            equivalent = aliases.get(number) if isinstance(aliases, dict) else None
            if isinstance(equivalent, int) and not isinstance(equivalent, bool) and equivalent > 0:
                found[line].add(equivalent)
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
                    "completo": fraction(required, visited)["completo"] and route_availability(route)["puede_registrar_viaje"],
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
