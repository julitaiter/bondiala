from django.contrib import admin
from config.admin import AuditReadOnlyAdmin
from .models import Follow


@admin.register(Follow)
class FollowAdmin(AuditReadOnlyAdmin):
    list_display = ["usuario", "seguido", "fecha"]
    search_fields = ["usuario__username", "seguido__username"]
