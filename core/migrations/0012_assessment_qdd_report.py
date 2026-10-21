from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0011_pdfannotation_gradechangelog")]
    operations = [migrations.AddField(
        model_name="assessment", name="qdd_report",
        field=models.FileField(blank=True, null=True, upload_to="qdd_reports/",
                               help_text="Word document report from QDD"),
    )]
