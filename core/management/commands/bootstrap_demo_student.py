import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Course, Enrollment, StudentProfile


class Command(BaseCommand):
    help = "Crea/actualiza un alumno demo cuando DEMO_STUDENT_PASSWORD está configurada."

    def handle(self, *args, **options):
        password = os.getenv("DEMO_STUDENT_PASSWORD", "")
        if not password:
            self.stdout.write("bootstrap_demo_student omitido: falta DEMO_STUDENT_PASSWORD")
            return

        email = os.getenv("DEMO_STUDENT_EMAIL", "alumno.demo@xamoxacademy.local").strip().lower()
        full_name = os.getenv("DEMO_STUDENT_NAME", "Alumno Demo").strip() or "Alumno Demo"
        course = Course.objects.filter(slug="ia-marketing-digital", active=True).first()
        if not course:
            self.stderr.write("bootstrap_demo_student: curso no encontrado")
            return

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User(username=email[:150], email=email)

        parts = full_name.split(None, 1)
        user.first_name = parts[0][:150]
        user.last_name = parts[1][:150] if len(parts) > 1 else ""
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.set_password(password)
        user.save()

        StudentProfile.objects.update_or_create(user=user, defaults={"active": True, "notes": "Cuenta demo para revisar el portal de alumno."})
        enrollment, _ = Enrollment.objects.get_or_create(user=user, course=course, defaults={"status": "active"})
        if enrollment.status != "active":
            enrollment.status = "active"
            enrollment.save(update_fields=["status", "updated_at"])

        self.stdout.write(self.style.SUCCESS(f"Alumno demo listo: {email}"))
