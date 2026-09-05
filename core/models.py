import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class StudentProfile(TimestampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    phone = models.CharField(max_length=40, blank=True)
    company = models.CharField(max_length=160, blank=True)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    class Meta:
        verbose_name = "Perfil de alumno"
        verbose_name_plural = "Perfiles de alumnos"
    def __str__(self): return self.user.get_full_name() or self.user.username

class Course(TimestampedModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    cover_image = models.URLField(blank=True)
    active = models.BooleanField(default=True)
    stripe_price_id = models.CharField(max_length=64, blank=True, help_text="Price ID de Stripe (price_...) del curso completo. Necesario para que el webhook reconozca el pago.")
    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    def __str__(self): return self.title

class Module(TimestampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=1)
    published = models.BooleanField(default=True)
    stripe_price_id = models.CharField(max_length=64, blank=True, help_text="Price ID de Stripe (price_...) si este módulo se vende suelto.")
    stripe_payment_link = models.URLField(blank=True, help_text="URL del Payment Link de Stripe (buy.stripe.com/...) para el botón de compra suelta.")
    price_display = models.CharField(max_length=20, blank=True, help_text="Precio a mostrar en el botón de compra, ej. '405 €'.")
    class Meta:
        ordering = ["position", "id"]
        unique_together = [("course", "position")]
        verbose_name = "Módulo"
        verbose_name_plural = "Módulos"
    def __str__(self): return f"{self.course.title} · {self.position}. {self.title}"

class Lesson(TimestampedModel):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=1)
    duration_minutes = models.PositiveIntegerField(default=0)
    video_url = models.URLField(blank=True, help_text="URL privada o embed de la grabación")
    video_file = models.FileField(upload_to="lessons/videos/%Y/%m/", blank=True, null=True)
    cf_stream_uid = models.CharField(max_length=64, blank=True, help_text="UID del vídeo en Cloudflare Stream (recomendado para grabaciones largas, ej. 3h)")
    published = models.BooleanField(default=False)
    release_at = models.DateTimeField(blank=True, null=True)
    class Meta:
        ordering = ["position", "id"]
        unique_together = [("module", "position")]
        verbose_name = "Clase"
        verbose_name_plural = "Clases"
    @property
    def is_available(self): return self.published and (not self.release_at or self.release_at <= timezone.now())
    def __str__(self): return f"{self.module} · Clase {self.position}: {self.title}"

class Resource(TimestampedModel):
    TYPES = [("pdf","PDF"),("file","Archivo"),("link","Enlace"),("template","Plantilla")]
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="resources")
    title = models.CharField(max_length=200)
    resource_type = models.CharField(max_length=20, choices=TYPES, default="pdf")
    file = models.FileField(upload_to="lessons/resources/%Y/%m/", blank=True, null=True)
    external_url = models.URLField(blank=True)
    position = models.PositiveIntegerField(default=1)
    published = models.BooleanField(default=True)
    class Meta:
        ordering = ["position", "id"]
        verbose_name = "Recurso"
        verbose_name_plural = "Recursos"
    def __str__(self): return self.title

class Enrollment(TimestampedModel):
    STATUS = [("active","Activa"),("paused","Pausada"),("completed","Completada"),("cancelled","Cancelada")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=20, choices=STATUS, default="active")
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(blank=True, null=True)
    class Meta:
        unique_together = [("user", "course")]
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"
    def __str__(self): return f"{self.user} · {self.course}"

class LessonProgress(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress_records")
    completed = models.BooleanField(default=False)
    watched_seconds = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(blank=True, null=True)
    attended_live = models.BooleanField(default=False, help_text="Marcado manualmente por el admin: ¿asistió a la clase en directo?")
    attended_minutes = models.PositiveIntegerField(default=0, help_text="Minutos conectado en la clase en directo (manual, por ahora)")
    class Meta:
        unique_together = [("user", "lesson")]
        verbose_name = "Progreso de clase"
        verbose_name_plural = "Progreso de clases"
    def mark_complete(self):
        self.completed = True; self.completed_at = timezone.now(); self.save()
    def __str__(self): return f"{self.user} · {self.lesson}"

class Purchase(TimestampedModel):
    STATUS = [("pending","Pendiente"),("paid","Pagada"),("refunded","Reembolsada"),("cancelled","Cancelada")]
    SCOPE = [("full","Curso completo"),("module","Módulo suelto")]
    stripe_session_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    stripe_payment_intent = models.CharField(max_length=255, blank=True)
    buyer_email = models.EmailField()
    buyer_name = models.CharField(max_length=180, blank=True)
    amount_cents = models.PositiveIntegerField(default=120000)
    currency = models.CharField(max_length=10, default="eur")
    seats = models.PositiveIntegerField(default=2)
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    scope = models.CharField(max_length=10, choices=SCOPE, default="full")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="purchases", blank=True, null=True)
    module = models.ForeignKey(Module, on_delete=models.SET_NULL, related_name="purchases", blank=True, null=True, help_text="Solo si scope=module: qué módulo suelto se compró")
    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
    def __str__(self): return f"{self.buyer_email} · {self.status}"

class ModuleAccess(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="module_access")
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="access_grants")
    purchase = models.ForeignKey(Purchase, on_delete=models.SET_NULL, related_name="module_access", blank=True, null=True)
    class Meta:
        unique_together = [("user", "module")]
        verbose_name = "Acceso a módulo"
        verbose_name_plural = "Accesos a módulos"
    def __str__(self): return f"{self.user} → {self.module}"

class SeatInvitation(TimestampedModel):
    STATUS = [("pending","Pendiente"),("accepted","Aceptada"),("revoked","Revocada")]
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="seat_invitations")
    email = models.EmailField()
    invited_name = models.CharField(max_length=180, blank=True)
    token = models.CharField(max_length=80, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="accepted_seat_invitations")
    accepted_at = models.DateTimeField(blank=True, null=True)
    class Meta:
        verbose_name = "Invitación de plaza"
        verbose_name_plural = "Invitaciones de plaza"
    def save(self, *args, **kwargs):
        if not self.token: self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)
    def __str__(self): return f"{self.email} · {self.status}"

class ActivityLog(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    action = models.CharField(max_length=120)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    class Meta:
        verbose_name = "Registro de actividad"
        verbose_name_plural = "Registros de actividad"
    def __str__(self): return self.action

# ---------------------------------------------------------------------------
# Xamox Challenge · Evaluación gamificada
# ---------------------------------------------------------------------------
class Challenge(TimestampedModel):
    TYPES = [("practice", "Práctica"), ("exam", "Examen final")]
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="challenges")
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    challenge_type = models.CharField(max_length=20, choices=TYPES, default="practice")
    position = models.PositiveIntegerField(default=1)
    question_count = models.PositiveIntegerField(default=5)
    pass_percent = models.PositiveIntegerField(default=70)
    max_attempts = models.PositiveIntegerField(default=3)
    xp_reward = models.PositiveIntegerField(default=50)
    published = models.BooleanField(default=True)
    class Meta:
        ordering = ["module__position", "position", "id"]
        unique_together = [("module", "slug")]
        verbose_name = "Reto"
        verbose_name_plural = "Retos"
    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(self.title)
        self.pass_percent = max(0, min(100, self.pass_percent))
        super().save(*args, **kwargs)
    def __str__(self): return f"{self.module} · {self.title}"

class Question(TimestampedModel):
    TYPES = [("single", "Opción única"), ("true_false", "Verdadero / Falso"), ("text", "Respuesta práctica")]
    DIFFICULTY = [("easy", "Fácil"), ("medium", "Media"), ("hard", "Difícil")]
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="challenge_questions")
    challenges = models.ManyToManyField(Challenge, related_name="questions", blank=True)
    category = models.CharField(max_length=80, blank=True)
    question_type = models.CharField(max_length=20, choices=TYPES, default="single")
    prompt = models.TextField()
    explanation = models.TextField(blank=True)
    model_answer = models.TextField(blank=True, help_text="Solución orientativa para ejercicios de texto.")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY, default="medium")
    points = models.PositiveIntegerField(default=10)
    active = models.BooleanField(default=True)
    class Meta:
        ordering = ["module__position", "id"]
        verbose_name = "Pregunta Challenge"
        verbose_name_plural = "Preguntas Challenge"
    def __str__(self): return self.prompt[:80]

class AnswerOption(TimestampedModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=1)
    class Meta:
        ordering = ["position", "id"]
        verbose_name = "Opción de respuesta"
        verbose_name_plural = "Opciones de respuesta"
    def __str__(self): return self.text

class QuizAttempt(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="challenge_attempts")
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="attempts")
    score = models.PositiveIntegerField(default=0)
    max_score = models.PositiveIntegerField(default=0)
    percent = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)
    xp_earned = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(blank=True, null=True)
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Intento Challenge"
        verbose_name_plural = "Intentos Challenge"
    def __str__(self): return f"{self.user} · {self.challenge} · {self.percent}%"

class QuestionAttempt(TimestampedModel):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="attempt_answers")
    selected_option = models.ForeignKey(AnswerOption, on_delete=models.SET_NULL, blank=True, null=True)
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)
    points_awarded = models.PositiveIntegerField(default=0)
    class Meta:
        unique_together = [("attempt", "question")]
        verbose_name = "Respuesta de alumno"
        verbose_name_plural = "Respuestas de alumnos"

class Achievement(TimestampedModel):
    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=300, blank=True)
    icon = models.CharField(max_length=8, default="🏆")
    xp_bonus = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    class Meta:
        verbose_name = "Insignia"
        verbose_name_plural = "Insignias"
    def __str__(self): return self.name

class StudentAchievement(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name="students")
    awarded_at = models.DateTimeField(default=timezone.now)
    class Meta:
        unique_together = [("user", "achievement")]
        verbose_name = "Insignia obtenida"
        verbose_name_plural = "Insignias obtenidas"
    def __str__(self): return f"{self.user} · {self.achievement}"
