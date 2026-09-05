from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = ("Borra TODOS los alumnos (usuarios no-staff): sus cuentas, matrículas, "
            "accesos por módulo y progreso. NO borra el historial de compras (Purchase) "
            "ni los registros de actividad (quedan sin usuario asociado, para tu contabilidad). "
            "Requiere --confirm para evitar borrados accidentales.")

    def add_arguments(self, parser):
        parser.add_argument("--confirm", action="store_true", help="Confirmar el borrado (obligatorio)")

    def handle(self, *args, **opts):
        students = User.objects.filter(is_staff=False)
        count = students.count()

        if count == 0:
            self.stdout.write(self.style.WARNING("No hay alumnos que borrar."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(f"Se van a borrar {count} alumnos:"))
        for s in students:
            self.stdout.write(f"  - {s.get_full_name() or s.username} ({s.email})")

        if not opts["confirm"]:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "Nada borrado todavía. Repite el comando añadiendo --confirm para confirmar:"
            ))
            self.stdout.write("  python manage.py wipe_students --confirm")
            return

        deleted_count, _ = students.delete()
        self.stdout.write(self.style.SUCCESS(f"✓ {count} alumnos eliminados ({deleted_count} registros en total, incluye matrículas/progreso)."))
        self.stdout.write("  Las compras (Purchase) y el historial de actividad se mantienen intactos.")
