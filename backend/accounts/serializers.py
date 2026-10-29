from urllib.parse import urlparse
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import User


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {field: "Campo no admitido." for field in unknown}
            )
        return super().to_internal_value(data)


class RegisterSerializer(StrictSerializer):
    username = serializers.RegexField(r"^[A-Za-z0-9_]{3,30}$", max_length=30)
    nickname = serializers.CharField(max_length=60)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, max_length=128)

    def validate(self, data):
        if User.objects.filter(username__iexact=data["username"]).exists():
            raise serializers.ValidationError(
                {"username": "Este nombre de usuario ya está en uso."}
            )
        data["email"] = data["email"].lower()
        if User.objects.filter(email__iexact=data["email"]).exists():
            raise serializers.ValidationError(
                {"email": "No se pudo crear la cuenta con estos datos."}
            )
        try:
            password_validation.validate_password(
                data["password"],
                User(**{k: v for k, v in data.items() if k != "password"}),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return data


class LoginSerializer(StrictSerializer):
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(max_length=128, write_only=True)


class PreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["nickname", "avatar", "public_profile", "theme"]

    def validate_avatar(self, value):
        if value and urlparse(value).scheme != "https":
            raise serializers.ValidationError("El avatar debe usar HTTPS.")
        return value


class ResetSerializer(StrictSerializer):
    email = serializers.EmailField()


class ResetConfirmSerializer(StrictSerializer):
    uid = serializers.CharField(max_length=100)
    token = serializers.CharField(max_length=100)
    password = serializers.CharField(max_length=128, write_only=True)
