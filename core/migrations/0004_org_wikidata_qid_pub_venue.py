from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_publication_authorship_collaboration"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="wikidata_qid",
            field=models.CharField(blank=True, max_length=20, verbose_name="Wikidata QID"),
        ),
        migrations.AddField(
            model_name="publication",
            name="venue",
            field=models.CharField(
                blank=True,
                help_text="Journal or conference name",
                max_length=500,
            ),
        ),
    ]
