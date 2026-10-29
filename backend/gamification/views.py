from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError, NotAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from config.schema import RankingPageSchema, AchievementPageSchema
from .models import Logro, Nivel
from .services import ranking, level_for, achievement_metrics


class RankingView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter("tipo", str, enum=["global", "semanal", "amigos"]),
            OpenApiParameter("page", int),
        ],
        responses=RankingPageSchema,
    )
    def get(self, request):
        scope = request.query_params.get("tipo", "global")
        if scope not in {"global", "semanal", "amigos"}:
            raise ValidationError("Ranking inválido.")
        if scope == "amigos" and not request.user.is_authenticated:
            raise NotAuthenticated()
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(ranking(scope, request.user), request)
        offset = paginator.page.start_index()
        levels = list(Nivel.objects.all())
        rows = [
            {
                "posicion": offset + i,
                "id": u.pk,
                "username": u.username,
                "nickname": u.nickname or u.username,
                "avatar": u.avatar,
                "puntos": u.puntos,
                "nivel": level_for(u.puntos, levels),
            }
            for i, u in enumerate(page)
        ]
        return paginator.get_paginated_response(rows)


class AchievementView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter("obtenidos", bool), OpenApiParameter("page", int)],
        responses=AchievementPageSchema,
    )
    def get(self, request):
        metrics = (
            achievement_metrics(request.user) if request.user.is_authenticated else {}
        )
        earned = (
            dict(request.user.logros.values_list("logro_id", "fecha"))
            if request.user.is_authenticated
            else {}
        )
        paginator = PageNumberPagination()
        query = Logro.objects.filter(activo=True).order_by("objetivo", "pk")
        if request.query_params.get("obtenidos") == "true":
            query = query.filter(pk__in=earned)
        page = paginator.paginate_queryset(query, request)
        rows = [
            {
                "id": a.pk,
                "slug": a.slug,
                "nombre": a.nombre,
                "descripcion": a.descripcion,
                "regla": a.regla,
                "objetivo": a.objetivo,
                "puntos": a.puntos,
                "progreso": min(metrics.get(a.regla, 0), a.objetivo),
                "obtenido": a.pk in earned,
                "fecha": earned.get(a.pk),
            }
            for a in page
        ]
        return paginator.get_paginated_response(rows)
