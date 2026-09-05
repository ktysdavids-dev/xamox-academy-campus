from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import StudentProfile


class StudentCreateForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre")
    last_name = forms.CharField(label="Apellidos", required=False)
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Contraseña temporal", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "password")

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe un usuario con este email")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"].lower().strip()
        user.email = user.username
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            StudentProfile.objects.get_or_create(user=user)
        return user


class PostPurchaseForm(forms.Form):
    PLAN_CHOICES = [
        ("solo", "Solo yo (una plaza)"),
        ("promo", "Promoción 2 personas (dos plazas)"),
    ]
    plan = forms.ChoiceField(
        choices=PLAN_CHOICES, widget=forms.RadioSelect, initial="promo", label="¿Cómo usarás tu compra?"
    )
    buyer_name = forms.CharField(label="Tu nombre completo", max_length=180)
    guest_name = forms.CharField(label="Nombre del segundo alumno", max_length=180, required=False)
    guest_email = forms.EmailField(label="Email del segundo alumno", required=False)

    def __init__(self, *args, buyer_email="", **kwargs):
        self.buyer_email = (buyer_email or "").strip().lower()
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("plan") == "promo":
            if not cleaned.get("guest_name"):
                self.add_error("guest_name", "Indica el nombre del segundo alumno")
            guest_email = (cleaned.get("guest_email") or "").strip().lower()
            if not guest_email:
                self.add_error("guest_email", "Indica el email del segundo alumno")
            elif guest_email == self.buyer_email:
                self.add_error("guest_email", "Debe ser un email distinto al tuyo")
        return cleaned


class InviteSeatForm(forms.Form):
    guest_name = forms.CharField(label="Nombre del segundo alumno", max_length=180)
    guest_email = forms.EmailField(label="Email del segundo alumno")


class AcceptInvitationForm(forms.Form):
    full_name = forms.CharField(label="Tu nombre completo", max_length=180)
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repite la contraseña", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden")
        if p1:
            try:
                validate_password(p1)
            except forms.ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned

# ---------------------------------------------------------------------------
# Panel de contenido: clases y recursos
# ---------------------------------------------------------------------------
from django.core.validators import FileExtensionValidator
from .models import Lesson, Resource

VIDEO_EXTENSIONS = ["mp4", "mov", "webm", "m4v"]
DOC_EXTENSIONS = ["pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "zip", "png", "jpg", "jpeg"]


class LessonForm(forms.ModelForm):
    MAX_UPLOAD_MB = 300

    video_file = forms.FileField(
        label="Subir archivo (solo clips cortos, máx. 300 MB)", required=False,
        validators=[FileExtensionValidator(allowed_extensions=VIDEO_EXTENSIONS)],
        widget=forms.ClearableFileInput(attrs={"accept": "video/*"}),
        help_text="Para grabaciones largas (ej. 3h) usa Cloudflare Stream, no este campo.",
    )
    cf_stream_uid = forms.CharField(
        label="ID de vídeo en Cloudflare Stream", required=False,
        help_text="Recomendado para grabaciones de clase completas. Sube el vídeo en el "
                   "dashboard de Cloudflare Stream y pega aquí el 'Video UID'.",
        widget=forms.TextInput(attrs={"placeholder": "Ej. 31c9291a...b2f4"}),
    )
    release_at = forms.DateTimeField(
        label="Publicar a partir de (opcional)", required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M"],
    )

    class Meta:
        model = Lesson
        fields = ["title", "description", "duration_minutes", "video_url", "video_file",
                  "cf_stream_uid", "published", "release_at"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Ej. 01 · Qué es un modelo de lenguaje"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Resumen breve de la clase"}),
            "duration_minutes": forms.NumberInput(attrs={"min": 0}),
            "video_url": forms.URLInput(attrs={"placeholder": "https:// (YouTube/Vimeo no listado, etc.)"}),
        }
        labels = {"video_url": "URL del vídeo (enlace externo)", "duration_minutes": "Duración (minutos)"}

    def clean_video_file(self):
        video_file = self.cleaned_data.get("video_file")
        if video_file and video_file.size > self.MAX_UPLOAD_MB * 1024 * 1024:
            raise forms.ValidationError(
                f"El archivo pesa demasiado ({video_file.size // (1024*1024)} MB). "
                f"Límite {self.MAX_UPLOAD_MB} MB aquí — para grabaciones largas usa Cloudflare Stream."
            )
        return video_file

    def clean(self):
        cleaned = super().clean()
        has_video = (
            cleaned.get("video_url") or cleaned.get("video_file") or cleaned.get("cf_stream_uid")
            or (self.instance and (self.instance.video_file or self.instance.cf_stream_uid))
        )
        if not has_video:
            raise forms.ValidationError(
                "Indica un vídeo: ID de Cloudflare Stream (recomendado), URL externa, o sube un archivo corto."
            )
        return cleaned


class ResourceForm(forms.ModelForm):
    file = forms.FileField(
        label="Archivo", required=False,
        validators=[FileExtensionValidator(allowed_extensions=DOC_EXTENSIONS)],
    )

    class Meta:
        model = Resource
        fields = ["title", "resource_type", "file", "external_url", "published"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Ej. Plantilla de prompts"}),
            "external_url": forms.URLInput(attrs={"placeholder": "https:// (si es un enlace)"}),
        }

    def clean(self):
        cleaned = super().clean()
        rtype = cleaned.get("resource_type")
        if rtype in ("pdf", "file") and not cleaned.get("file") and not (self.instance and self.instance.file):
            self.add_error("file", "Sube un archivo para este tipo de recurso.")
        if rtype in ("link", "template") and not cleaned.get("external_url") and not cleaned.get("file"):
            self.add_error("external_url", "Indica un enlace o sube un archivo.")
        return cleaned

