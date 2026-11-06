from django.db import models


class DataSource(models.Model):
    slug = models.SlugField(unique=True)
    nombre = models.CharField(max_length=150)
    url = models.URLField(blank=True, max_length=500)

    def __str__(self):
        return self.nombre


class ImportRun(models.Model):
    source = models.ForeignKey(
        DataSource, on_delete=models.PROTECT, related_name="runs"
    )
    kind = models.CharField(max_length=30)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    status = models.CharField(
        max_length=20,
        default="RUNNING",
        choices=[
            (x, x) for x in ["RUNNING", "SUCCESS", "PARTIAL", "FAILED", "UNCHANGED"]
        ],
    )
    created = models.PositiveIntegerField(default=0)
    updated = models.PositiveIntegerField(default=0)
    skipped = models.PositiveIntegerField(default=0)
    errors = models.PositiveIntegerField(default=0)
    checksum = models.CharField(max_length=64, blank=True, db_index=True)
    location = models.CharField(max_length=1000, blank=True)
    metrics = models.JSONField(default=dict, blank=True)


class ImportError(models.Model):
    run = models.ForeignKey(ImportRun, on_delete=models.CASCADE, related_name="issues")
    external_id = models.CharField(max_length=150, blank=True)
    message = models.CharField(max_length=500)


class StopMatchIssue(models.Model):
    run = models.ForeignKey(
        ImportRun, on_delete=models.CASCADE, related_name="match_issues"
    )
    parada = models.ForeignKey(
        "transport.Parada", on_delete=models.PROTECT, related_name="match_issues"
    )
    linea = models.CharField(max_length=5, blank=True)
    sentido = models.CharField(max_length=6, blank=True)
    reason = models.CharField(max_length=40)
    candidates = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=12,
        default="pending",
        choices=[("pending", "Pendiente"), ("resolved", "Resuelta")],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["linea", "sentido", "reason"],
                condition=models.Q(status="pending"),
                name="stop_issue_pending_lookup",
            )
        ]
