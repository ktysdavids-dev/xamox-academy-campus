from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Course",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=200)),
                ("slug", models.SlugField(blank=True, max_length=220, unique=True)),
                ("description", models.TextField(blank=True)),
                ("cover_image", models.URLField(blank=True)),
                ("active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="Purchase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("stripe_session_id", models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ("stripe_payment_intent", models.CharField(blank=True, max_length=255)),
                ("buyer_email", models.EmailField(max_length=254)),
                ("buyer_name", models.CharField(blank=True, max_length=180)),
                ("amount_cents", models.PositiveIntegerField(default=120000)),
                ("currency", models.CharField(default="eur", max_length=10)),
                ("seats", models.PositiveIntegerField(default=2)),
                ("status", models.CharField(choices=[("pending", "Pendiente"), ("paid", "Pagada"), ("refunded", "Reembolsada"), ("cancelled", "Cancelada")], default="pending", max_length=20)),
                ("course", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="purchases", to="core.course")),
            ],
        ),
        migrations.CreateModel(
            name="StudentProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("company", models.CharField(blank=True, max_length=160)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="student_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="ActivityLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("action", models.CharField(max_length=120)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="activity_logs", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Module",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("position", models.PositiveIntegerField(default=1)),
                ("published", models.BooleanField(default=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="modules", to="core.course")),
            ],
            options={"ordering": ["position", "id"]},
        ),
        migrations.CreateModel(
            name="Enrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[("active", "Activa"), ("paused", "Pausada"), ("completed", "Completada"), ("cancelled", "Cancelada")], default="active", max_length=20)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="enrollments", to="core.course")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="enrollments", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="SeatInvitation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("email", models.EmailField(max_length=254)),
                ("token", models.CharField(blank=True, max_length=80, unique=True)),
                ("status", models.CharField(choices=[("pending", "Pendiente"), ("accepted", "Aceptada"), ("revoked", "Revocada")], default="pending", max_length=20)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("accepted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="accepted_seat_invitations", to=settings.AUTH_USER_MODEL)),
                ("purchase", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="seat_invitations", to="core.purchase")),
            ],
        ),
        migrations.CreateModel(
            name="Lesson",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=220)),
                ("description", models.TextField(blank=True)),
                ("position", models.PositiveIntegerField(default=1)),
                ("duration_minutes", models.PositiveIntegerField(default=0)),
                ("video_url", models.URLField(blank=True, help_text="URL privada o embed de la grabación")),
                ("video_file", models.FileField(blank=True, null=True, upload_to="lessons/videos/%Y/%m/")),
                ("published", models.BooleanField(default=False)),
                ("release_at", models.DateTimeField(blank=True, null=True)),
                ("module", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lessons", to="core.module")),
            ],
            options={"ordering": ["position", "id"]},
        ),
        migrations.CreateModel(
            name="LessonProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed", models.BooleanField(default=False)),
                ("watched_seconds", models.PositiveIntegerField(default=0)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("lesson", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="progress_records", to="core.lesson")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lesson_progress", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Resource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=200)),
                ("resource_type", models.CharField(choices=[("pdf", "PDF"), ("file", "Archivo"), ("link", "Enlace"), ("template", "Plantilla")], default="pdf", max_length=20)),
                ("file", models.FileField(blank=True, null=True, upload_to="lessons/resources/%Y/%m/")),
                ("external_url", models.URLField(blank=True)),
                ("position", models.PositiveIntegerField(default=1)),
                ("published", models.BooleanField(default=True)),
                ("lesson", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="resources", to="core.lesson")),
            ],
            options={"ordering": ["position", "id"]},
        ),
        migrations.AlterUniqueTogether(name="module", unique_together={("course", "position")}),
        migrations.AlterUniqueTogether(name="enrollment", unique_together={("user", "course")}),
        migrations.AlterUniqueTogether(name="lesson", unique_together={("module", "position")}),
        migrations.AlterUniqueTogether(name="lessonprogress", unique_together={("user", "lesson")}),
    ]
