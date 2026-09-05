from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models import Purchase


class Command(BaseCommand):
    help = ("Borra TODOS los alumnos (usuarios no-staff): sus cuentas, matrículas, "
            "accesos por módulo y progreso. Por defecto NO borra el historial de "
            "compras (Purchase); usa --include-purchases si también son de prueba "
            "y quieres borrarlas. Requiere --confirm para evitar borrados accidentales.")

    def add_arguments(self, parser):
        parser.add_argument("--confirm", action="store_true", help="Confirmar el borrado (obligatorio)")
        parser.add_argument("--include-purchases", action="store_true",
                             help="También borra TODAS las compras (Purchase). Úsalo solo si son de prueba.")

    def handle(self, *args, **opts):
        students = User.objects.filter(is_staff=False)
        student_count = students.count()
        purchases = Purchase.objects.all()
        purchase_count = purchases.count()

        if student_count == 0 and (not opts["include_purchases"] or purchase_count == 0):
            self.stdout.write(self.style.WARNING("No hay nada que borrar."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(f"Se van a borrar {student_count} alumnos:"))
        for s in students:
            self.stdout.write(f"  - {s.get_full_name() or s.username} ({s.email})")

        if opts["include_purchases"]:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\nY TAMBIÉN se van a borrar {purchase_count} compras:"))
            for p in purchases:
                self.stdout.write(f"  - {p.buyer_email} · {p.get_status_display()} · {p.created_at:%d/%m/%Y %H:%M}")
        else:
            self.stdout.write(f"\n(Las {purchase_count} compras registradas NO se tocan. Añade --include-purchases si también quieres borrarlas.)")

        if not opts["confirm"]:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Nada borrado todavía. Repite el comando añadiendo --confirm:"))
            extra = " --include-purchases" if opts["include_purchases"] else ""
            self.stdout.write(f"  python manage.py wipe_students --confirm{extra}")
            return

        deleted_students, _ = students.delete()
        self.stdout.write(self.style.SUCCESS(f"✓ {student_count} alumnos eliminados ({deleted_students} registros en total)."))

        if opts["include_purchases"]:
            deleted_purchases, _ = purchases.delete()
            self.stdout.write(self.style.SUCCESS(f"✓ {purchase_count} compras eliminadas ({deleted_purchases} registros en total)."))
        else:
            self.stdout.write("  Las compras (Purchase) se mantienen intactas.")
