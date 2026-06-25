from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_alter_assessment_status_alter_customuser_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessment",
            name="moderator_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="assessment",
            name="qcto_notes",
            field=models.TextField(blank=True),
        ),
    ]
