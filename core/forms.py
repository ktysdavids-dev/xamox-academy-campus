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
