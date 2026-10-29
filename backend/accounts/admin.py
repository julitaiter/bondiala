from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class BondialaUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Bondiala", {"fields": ["nickname", "avatar", "public_profile", "theme"]}),
    )
    list_display = ["username", "nickname", "email", "is_staff", "is_active"]
    search_fields = ["username", "nickname", "email"]
