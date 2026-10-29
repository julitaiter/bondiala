import logging
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from config.schema import (
    ProfileSchema,
    MeSchema,
    MessageSchema,
    UserSummarySchema,
    CsrfSchema,
)
from .models import User
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    PreferencesSerializer,
    ResetSerializer,
    ResetConfirmSerializer,
)
from .services import profile_data

logger = logging.getLogger("bondiala.security")


@extend_schema(responses=CsrfSchema)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
@ensure_csrf_cookie
def csrf(request):
    response = JsonResponse({"csrfToken": get_token(request)})
    response["Cache-Control"] = "no-store"
    return response


class AuthView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"


class RegisterView(AuthView):
    serializer_class = RegisterSerializer

    @extend_schema(responses={201: ProfileSchema})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.create_user(**serializer.validated_data)
        except IntegrityError as exc:
            raise ValidationError(
                "No se pudo crear la cuenta con estos datos."
            ) from exc
        login(request, user)
        logger.info("registration user_id=%s", user.pk)
        return Response(
            profile_data(user, private=True), status=status.HTTP_201_CREATED
        )


class LoginView(AuthView):
    serializer_class = LoginSerializer

    @extend_schema(responses=ProfileSchema)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"]
        candidate = User.objects.filter(
            Q(email__iexact=identifier) | Q(username__iexact=identifier)
        ).first()
        user = authenticate(
            request,
            username=candidate.username if candidate else identifier,
            password=serializer.validated_data["password"],
        )
        if not user:
            logger.info("login_failed")
            return Response(
                {"error": {"detail": "El usuario o la contraseña no coinciden."}},
                status=400,
            )
        login(request, user)
        logger.info("login_success user_id=%s", user.pk)
        return Response(profile_data(user, private=True))


@extend_schema(request=None, responses={204: None})
@api_view(["POST"])
def logout_view(request):
    logout(request)
    return Response(status=204)


@extend_schema(methods=["GET"], responses=MeSchema)
@extend_schema(methods=["PATCH"], request=PreferencesSerializer, responses=MeSchema)
@api_view(["GET", "PATCH"])
@permission_classes([permissions.AllowAny])
def me(request):
    if not request.user.is_authenticated:
        return (
            Response({"user": None})
            if request.method == "GET"
            else Response(status=403)
        )
    if request.method == "PATCH":
        serializer = PreferencesSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
    return Response({"user": profile_data(request.user, private=True)})


class ProfileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSummarySchema
    permission_classes = [permissions.AllowAny]
    search_fields = ["username", "nickname"]
    lookup_field = "username"
    queryset = User.objects.filter(is_active=True, public_profile=True).order_by(
        "username"
    )

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        from social.models import Follow

        following = (
            dict(
                Follow.objects.filter(
                    usuario=request.user, seguido_id__in=[u.pk for u in page]
                ).values_list("seguido_id", "pk")
            )
            if request.user.is_authenticated
            else {}
        )
        rows = [
            {
                "id": u.pk,
                "username": u.username,
                "nickname": u.nickname or u.username,
                "avatar": u.avatar,
                "follow_id": following.get(u.pk),
            }
            for u in page
        ]
        return self.get_paginated_response(rows)

    @extend_schema(responses=ProfileSchema)
    def retrieve(self, request, *args, **kwargs):
        return Response(profile_data(self.get_object()))


class ResetView(AuthView):
    throttle_scope = "reset"
    serializer_class = ResetSerializer

    @extend_schema(responses=MessageSchema)
    def post(self, request):
        serializer = ResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        form = PasswordResetForm(serializer.validated_data)
        if form.is_valid():
            form.save(
                request=request,
                use_https=not settings.DEBUG,
                email_template_name="registration/password_reset_email.txt",
                subject_template_name="registration/password_reset_subject.txt",
                extra_email_context={"frontend_url": settings.FRONTEND_URL},
            )
        logger.info("password_reset_requested")
        return Response(
            {
                "detail": "Si existe una cuenta con ese email, vas a recibir un enlace para recuperar tu contraseña."
            }
        )


class ResetConfirmView(AuthView):
    serializer_class = ResetConfirmSerializer

    @extend_schema(responses=MessageSchema)
    def post(self, request):
        serializer = ResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            uid = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=uid)
        except (
            ValueError,
            TypeError,
            OverflowError,
            UnicodeDecodeError,
            User.DoesNotExist,
        ):
            user = None
        if (
            not user
            or not user.is_active
            or not default_token_generator.check_token(user, data["token"])
        ):
            raise ValidationError(
                "El enlace venció o ya fue utilizado. Pedí uno nuevo."
            )
        form = SetPasswordForm(
            user, {"new_password1": data["password"], "new_password2": data["password"]}
        )
        if not form.is_valid():
            raise ValidationError(form.errors)
        form.save()
        logger.info("password_reset_completed user_id=%s", user.pk)
        return Response({"detail": "Contraseña actualizada. Ya podés iniciar sesión."})
