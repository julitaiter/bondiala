from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from drf_spectacular.utils import extend_schema
from config.schema import ProgressSchema
from transport.services import catalog, line_progress, visited_by_line
from .models import RegistroViaje
from .serializers import TripSerializer, TripInputSerializer
from .services import register_trip


class TripViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TripSerializer
    throttle_scope = "trip"
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return RegistroViaje.objects.none()
        return RegistroViaje.objects.filter(usuario=self.request.user).select_related(
            "recorrido__ramal__linea", "inicio__parada", "fin__parada"
        )

    @extend_schema(
        request=TripInputSerializer,
        responses={201: TripSerializer, 200: TripSerializer},
    )
    def create(self, request):
        serializer = TripInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip, created = register_trip(request.user, **serializer.validated_data)
        return Response(
            TripSerializer(trip).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


@extend_schema(responses=ProgressSchema(many=True))
@api_view(["GET"])
def progress(request):
    visited = visited_by_line(request.user)
    return Response(
        [
            line_progress(line, visited[line.pk])
            for line in catalog().filter(pk__in=visited)
        ]
    )
