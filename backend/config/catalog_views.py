from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from imports.models import DataSource
from drf_spectacular.utils import extend_schema
from config.schema import StatusSchema


@extend_schema(responses=StatusSchema)
@api_view(["GET"])
@permission_classes([AllowAny])
def status(request):
    return Response(
        {"muestra": DataSource.objects.filter(slug="muestra-paradas").exists()}
    )
