from django.db.models.functions import Cast
from django.db.models import Case, F, IntegerField, Prefetch, When
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .models import Recorrido, Parada
from .services import catalog, visited_by_line, official_sequence, routes_with_quality
from .serializers import LineSerializer, RouteSerializer, StopSerializer


class LineViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LineSerializer
    permission_classes = [permissions.AllowAny]
    search_fields = ["numero", "nombre"]

    def get_queryset(self):
        query = (
            catalog()
            .annotate(numero_entero=Case(
                When(numero__regex=r"^[0-9]+$", then=Cast("numero", IntegerField())),
                output_field=IntegerField(),
            ))
            .order_by(F("numero_entero").asc(nulls_last=True), "numero", "pk")
        )
        if (
            self.request.query_params.get("estado") == "recorridas"
            and self.request.user.is_authenticated
        ):
            query = query.filter(
                pk__in=self.request.user.paradas_transitadas.values("linea_id")
            )
        return query

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            "visited": visited_by_line(self.request.user),
        }

    @extend_schema(responses=RouteSerializer(many=True))
    @action(detail=True)
    def recorridos(self, request, pk=None):
        line = self.get_object()
        routes = [r for b in line.ramales.all() for r in b.recorridos.all()]
        visited = visited_by_line(request.user)[line.pk]
        return Response(
            RouteSerializer(routes, many=True, context={"visited_stops": visited}).data
        )


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RouteSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        query = (
            routes_with_quality().filter(
                activo=True, ramal__activo=True, ramal__linea__activa=True
            )
            .select_related("ramal__linea__colores")
            .prefetch_related(
                Prefetch("secuencia", queryset=official_sequence().select_related("parada"))
            )
            .order_by("pk")
        )
        for param, lookup in [("linea", "ramal__linea_id"), ("ramal", "ramal_id")]:
            value = self.request.query_params.get(param)
            if value:
                if not value.isdigit():
                    return query.none()
                query = query.filter(**{lookup: value})
        return query

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["visited"] = visited_by_line(self.request.user)
        return context


class StopViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StopSerializer
    permission_classes = [permissions.AllowAny]
    search_fields = ["nombre", "direccion", "barrio"]

    def get_queryset(self):
        query = Parada.objects.filter(activa=True, es_oficial=True).order_by("pk")
        route = self.request.query_params.get("recorrido")
        if route:
            query = (
                query.filter(
                    recorridos__recorrido_id=route, recorridos__activa=True,
                    recorridos__recorrido__requiere_rematch=False,
                )
                if route.isdigit()
                else query.none()
            )
        return query.distinct()
