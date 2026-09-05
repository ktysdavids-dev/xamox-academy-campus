from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_module_price_display_module_stripe_payment_link"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Achievement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.SlugField(max_length=80, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.CharField(blank=True, max_length=300)),
                ("icon", models.CharField(default="🏆", max_length=8)),
                ("xp_bonus", models.PositiveIntegerField(default=0)),
                ("active", models.BooleanField(default=True)),
            ],
            options={"verbose_name": "Insignia", "verbose_name_plural": "Insignias"},
        ),
        migrations.CreateModel(
            name="Challenge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=180)),
                ("slug", models.SlugField(blank=True, max_length=200)),
                ("description", models.TextField(blank=True)),
                ("challenge_type", models.CharField(choices=[("practice", "Práctica"), ("exam", "Examen final")], default="practice", max_length=20)),
                ("position", models.PositiveIntegerField(default=1)),
                ("question_count", models.PositiveIntegerField(default=5)),
                ("pass_percent", models.PositiveIntegerField(default=70)),
                ("max_attempts", models.PositiveIntegerField(default=3)),
                ("xp_reward", models.PositiveIntegerField(default=50)),
                ("published", models.BooleanField(default=True)),
                ("module", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="challenges", to="core.module")),
            ],
            options={"verbose_name": "Reto", "verbose_name_plural": "Retos", "ordering": ["module__position", "position", "id"], "unique_together": {("module", "slug")}},
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.CharField(blank=True, max_length=80)),
                ("question_type", models.CharField(choices=[("single", "Opción única"), ("true_false", "Verdadero / Falso"), ("text", "Respuesta práctica")], default="single", max_length=20)),
                ("prompt", models.TextField()),
                ("explanation", models.TextField(blank=True)),
                ("model_answer", models.TextField(blank=True, help_text="Solución orientativa para ejercicios de texto.")),
                ("difficulty", models.CharField(choices=[("easy", "Fácil"), ("medium", "Media"), ("hard", "Difícil")], default="medium", max_length=20)),
                ("points", models.PositiveIntegerField(default=10)),
                ("active", models.BooleanField(default=True)),
                ("module", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="challenge_questions", to="core.module")),
                ("challenges", models.ManyToManyField(blank=True, related_name="questions", to="core.challenge")),
            ],
            options={"verbose_name": "Pregunta Challenge", "verbose_name_plural": "Preguntas Challenge", "ordering": ["module__position", "id"]},
        ),
        migrations.CreateModel(
            name="AnswerOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("text", models.CharField(max_length=500)),
                ("is_correct", models.BooleanField(default=False)),
                ("position", models.PositiveIntegerField(default=1)),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="options", to="core.question")),
            ],
            options={"verbose_name": "Opción de respuesta", "verbose_name_plural": "Opciones de respuesta", "ordering": ["position", "id"]},
        ),
        migrations.CreateModel(
            name="QuizAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("score", models.PositiveIntegerField(default=0)),
                ("max_score", models.PositiveIntegerField(default=0)),
                ("percent", models.PositiveIntegerField(default=0)),
                ("passed", models.BooleanField(default=False)),
                ("xp_earned", models.PositiveIntegerField(default=0)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("challenge", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to="core.challenge")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="challenge_attempts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Intento Challenge", "verbose_name_plural": "Intentos Challenge", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="QuestionAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("text_answer", models.TextField(blank=True)),
                ("is_correct", models.BooleanField(default=False)),
                ("points_awarded", models.PositiveIntegerField(default=0)),
                ("attempt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="core.quizattempt")),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attempt_answers", to="core.question")),
                ("selected_option", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="core.answeroption")),
            ],
            options={"verbose_name": "Respuesta de alumno", "verbose_name_plural": "Respuestas de alumnos", "unique_together": {("attempt", "question")}},
        ),
        migrations.CreateModel(
            name="StudentAchievement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("awarded_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("achievement", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="students", to="core.achievement")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="achievements", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Insignia obtenida", "verbose_name_plural": "Insignias obtenidas", "unique_together": {("user", "achievement")}},
        ),
    ]
