from django.shortcuts import get_object_or_404
from rest_framework import viewsets, serializers
from rest_framework.response import Response
from accounts.models import User
from accounts.serializers import StrictSerializer
from .models import Follow
from drf_spectacular.utils import extend_schema, inline_serializer
from config.schema import FollowPageSchema


class FollowInputSerializer(StrictSerializer):
    seguido = serializers.IntegerField(min_value=1)


class FollowViewSet(viewsets.ViewSet):
    serializer_class = FollowInputSerializer
    queryset = Follow.objects.none()

    @extend_schema(responses=FollowPageSchema)
    def list(self, request):
        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        relations = (
            Follow.objects.filter(
                usuario=request.user,
                seguido__public_profile=True,
                seguido__is_active=True,
            )
            .select_related("seguido")
            .order_by("pk")
        )
        page = paginator.paginate_queryset(relations, request)
        return paginator.get_paginated_response(
            [
                {
                    "id": f.pk,
                    "usuario": {
                        "id": f.seguido_id,
                        "username": f.seguido.username,
                        "nickname": f.seguido.nickname or f.seguido.username,
                        "avatar": f.seguido.avatar,
                    },
                }
                for f in page
            ]
        )

    @extend_schema(
        responses={
            201: inline_serializer("FollowCreated", {"id": serializers.IntegerField()})
        }
    )
    def create(self, request):
        serializer = FollowInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = get_object_or_404(
            User,
            pk=serializer.validated_data["seguido"],
            public_profile=True,
            is_active=True,
        )
        if target.pk == request.user.pk:
            raise serializers.ValidationError("No podés seguirte a vos mismo.")
        relation, created = Follow.objects.get_or_create(
            usuario=request.user, seguido=target
        )
        return Response({"id": relation.pk}, status=201 if created else 200)

    @extend_schema(responses={204: None})
    def destroy(self, request, pk=None):
        relation = get_object_or_404(Follow, pk=pk, usuario=request.user)
        relation.delete()
        return Response(status=204)
