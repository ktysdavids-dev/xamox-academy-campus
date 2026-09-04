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
    def __str__(self): return self.user.get_full_name() or self.user.username

class Course(TimestampedModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    cover_image = models.URLField(blank=True)
    active = models.BooleanField(default=True)
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
    class Meta:
        ordering = ["position", "id"]
        unique_together = [("course", "position")]
    def __str__(self): return f"{self.course.title} · {self.position}. {self.title}"

class Lesson(TimestampedModel):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=1)
    duration_minutes = models.PositiveIntegerField(default=0)
    video_url = models.URLField(blank=True, help_text="URL privada o embed de la grabación")
    video_file = models.FileField(upload_to="lessons/videos/%Y/%m/", blank=True, null=True)
    published = models.BooleanField(default=False)
    release_at = models.DateTimeField(blank=True, null=True)
    class Meta:
        ordering = ["position", "id"]
        unique_together = [("module", "position")]
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
    class Meta: ordering = ["position", "id"]
    def __str__(self): return self.title

class Enrollment(TimestampedModel):
    STATUS = [("active","Activa"),("paused","Pausada"),("completed","Completada"),("cancelled","Cancelada")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=20, choices=STATUS, default="active")
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(blank=True, null=True)
    class Meta: unique_together = [("user", "course")]
    def __str__(self): return f"{self.user} · {self.course}"

class LessonProgress(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress_records")
    completed = models.BooleanField(default=False)
    watched_seconds = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(blank=True, null=True)
    class Meta: unique_together = [("user", "lesson")]
    def mark_complete(self):
        self.completed = True; self.completed_at = timezone.now(); self.save()
    def __str__(self): return f"{self.user} · {self.lesson}"

class Purchase(TimestampedModel):
    STATUS = [("pending","Pendiente"),("paid","Pagada"),("refunded","Reembolsada"),("cancelled","Cancelada")]
    stripe_session_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    stripe_payment_intent = models.CharField(max_length=255, blank=True)
    buyer_email = models.EmailField()
    buyer_name = models.CharField(max_length=180, blank=True)
    amount_cents = models.PositiveIntegerField(default=120000)
    currency = models.CharField(max_length=10, default="eur")
    seats = models.PositiveIntegerField(default=2)
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="purchases", blank=True, null=True)
    def __str__(self): return f"{self.buyer_email} · {self.status}"

class SeatInvitation(TimestampedModel):
    STATUS = [("pending","Pendiente"),("accepted","Aceptada"),("revoked","Revocada")]
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="seat_invitations")
    email = models.EmailField()
    token = models.CharField(max_length=80, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="accepted_seat_invitations")
    accepted_at = models.DateTimeField(blank=True, null=True)
    def save(self, *args, **kwargs):
        if not self.token: self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)
    def __str__(self): return f"{self.email} · {self.status}"

class ActivityLog(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    action = models.CharField(max_length=120)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    def __str__(self): return self.action
