from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView
from rest_framework.routers import DefaultRouter
from accounts.views import (
    csrf,
    RegisterView,
    LoginView,
    logout_view,
    me,
    ProfileViewSet,
    ResetView,
    ResetConfirmView,
)
from transport.views import LineViewSet, RouteViewSet, StopViewSet
from trips.views import TripViewSet, progress
from gamification.views import RankingView, AchievementView
from social.views import FollowViewSet
from config.catalog_views import status

router = DefaultRouter()
for prefix, view, name in [
    ("lineas", LineViewSet, "linea"),
    ("recorridos", RouteViewSet, "recorrido"),
    ("paradas", StopViewSet, "parada"),
    ("viajes", TripViewSet, "viaje"),
    ("perfiles", ProfileViewSet, "perfil"),
    ("amigos", FollowViewSet, "amigo"),
]:
    router.register(prefix, view, basename=name)


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT PostGIS_Version()")
            cursor.fetchone()
        return JsonResponse({"status": "ok", "database": "postgis"})
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),
    path("api/v1/auth/csrf/", csrf),
    path("api/v1/auth/registro/", RegisterView.as_view()),
    path("api/v1/auth/login/", LoginView.as_view()),
    path("api/v1/auth/logout/", logout_view),
    path("api/v1/auth/recuperar/", ResetView.as_view()),
    path("api/v1/auth/restablecer/", ResetConfirmView.as_view()),
    path("api/v1/me/", me),
    path("api/v1/progreso/", progress),
    path("api/v1/estado/", status),
    path("api/v1/rankings/", RankingView.as_view()),
    path("api/v1/logros/", AchievementView.as_view()),
    path("api/v1/schema/", SpectacularAPIView.as_view()),
    path("api/v1/", include(router.urls)),
]
