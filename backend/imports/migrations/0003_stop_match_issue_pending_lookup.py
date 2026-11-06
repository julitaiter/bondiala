from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("imports", "0002_importrun_location_importrun_metrics_stopmatchissue"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="stopmatchissue",
            index=models.Index(
                fields=["linea", "sentido", "reason"],
                condition=models.Q(status="pending"),
                name="stop_issue_pending_lookup",
            ),
        ),
    ]
