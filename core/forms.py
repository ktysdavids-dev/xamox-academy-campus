from django import forms
from django.contrib.auth.models import User
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
        if User.objects.filter(email__iexact=email).exists(): raise forms.ValidationError("Ya existe un usuario con este email")
        return email
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"].lower().strip(); user.email = user.username; user.set_password(self.cleaned_data["password"])
        if commit:
            user.save(); StudentProfile.objects.get_or_create(user=user)
        return user
