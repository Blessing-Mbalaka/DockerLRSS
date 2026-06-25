from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_assessment_workflow_notes"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PdfAnnotation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "role",
                    models.CharField(blank=True, default="", max_length=30),
                ),
                (
                    "ann_type",
                    models.CharField(
                        choices=[
                            ("tick", "Tick"),
                            ("cross", "Cross"),
                            ("comment", "Comment"),
                        ],
                        max_length=10,
                    ),
                ),
                ("page", models.PositiveIntegerField()),
                ("x", models.FloatField()),
                ("y", models.FloatField()),
                ("text", models.TextField(blank=True, default="")),
                ("colour", models.CharField(default="#000000", max_length=7)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_annotations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "submission",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="annotations",
                        to="core.examsubmission",
                    ),
                ),
            ],
            options={
                "ordering": ["page", "created_at"],
                "indexes": [
                    models.Index(
                        fields=["submission", "created_by"],
                        name="core_pdfann_submiss_569b8b_idx",
                    ),
                    models.Index(
                        fields=["submission", "role"],
                        name="core_pdfann_submiss_f7e32d_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="GradeChangeLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tier",
                    models.CharField(
                        choices=[
                            ("marker", "Assessor Marker"),
                            ("internal", "Internal Moderator"),
                            ("external", "External Moderator (QALA)"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "old_marks",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                (
                    "new_marks",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                ("old_feedback", models.TextField(blank=True, default="")),
                ("new_feedback", models.TextField(blank=True, default="")),
                ("note", models.TextField(blank=True, default="")),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="grade_change_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "submission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="grade_changes",
                        to="core.examsubmission",
                    ),
                ),
            ],
            options={
                "ordering": ["-changed_at"],
                "indexes": [
                    models.Index(
                        fields=["submission", "tier"],
                        name="core_gradec_submiss_574120_idx",
                    ),
                    models.Index(
                        fields=["changed_by", "changed_at"],
                        name="core_gradec_changed_d22b0c_idx",
                    ),
                ],
            },
        ),
    ]
