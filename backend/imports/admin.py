from django.contrib import admin
from config.admin import AuditReadOnlyAdmin
from .models import DataSource, ImportRun, ImportError


@admin.register(DataSource)
class SourceAdmin(admin.ModelAdmin):
    list_display = ["slug", "nombre", "url"]
    search_fields = ["slug", "nombre"]


class ErrorInline(admin.TabularInline):
    model = ImportError
    readonly_fields = ["external_id", "message"]
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ImportRun)
class RunAdmin(AuditReadOnlyAdmin):
    list_display = [
        "id",
        "source",
        "kind",
        "status",
        "started_at",
        "created",
        "updated",
        "skipped",
        "errors",
    ]
    list_filter = ["source", "kind", "status"]
    inlines = [ErrorInline]


@admin.register(ImportError)
class ErrorAdmin(AuditReadOnlyAdmin):
    list_display = ["run", "external_id", "message"]
    search_fields = ["message", "external_id"]
