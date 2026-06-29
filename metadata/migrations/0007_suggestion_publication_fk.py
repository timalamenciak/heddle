import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_publication_authorship_collaboration"),
        ("metadata", "0006_seed_publication_checks"),
    ]

    operations = [
        migrations.AddField(
            model_name="metadatasuggestion",
            name="publication",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="suggestions",
                to="core.publication",
            ),
        ),
    ]
