import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea o actualiza un superusuario desde variables ADMIN_USERNAME, ADMIN_EMAIL y ADMIN_PASSWORD."

    def handle(self, *args, **options):
        username = os.getenv("ADMIN_USERNAME", "").strip()
        email = os.getenv("ADMIN_EMAIL", "").strip()
        password = os.getenv("ADMIN_PASSWORD", "")

        if not username or not password:
            self.stdout.write("bootstrap_admin omitido: faltan ADMIN_USERNAME o ADMIN_PASSWORD")
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )

        changed = False
        if email and user.email != email:
            user.email = email
            changed = True
        if not user.is_staff:
            user.is_staff = True
            changed = True
        if not user.is_superuser:
            user.is_superuser = True
            changed = True

        user.set_password(password)
        changed = True
        if changed:
            user.save()

        status = "creado" if created else "actualizado"
        self.stdout.write(self.style.SUCCESS(f"Superusuario {username} {status}"))
