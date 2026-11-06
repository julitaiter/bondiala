from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("transport", "0003_parada_activa_parada_es_oficial_and_more")]

    operations = [
        migrations.AddField(
            model_name="recorrido",
            name="requiere_rematch",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="recorridoparada",
            name="evidencia",
            field=models.JSONField(default=dict, blank=True),
        ),
    ]
