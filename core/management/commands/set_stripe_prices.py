from django.core.management.base import BaseCommand, CommandError

from core.models import Module
from core.services import get_active_course


class Command(BaseCommand):
    help = ("Configura de una sola vez los Price ID de Stripe del curso completo "
            "y de los 4 módulos sueltos, sin tener que entrar al Django Admin "
            "campo por campo.")

    def add_arguments(self, parser):
        parser.add_argument("--curso", default="", help="Price ID (price_...) del curso completo")
        parser.add_argument("--m1", default="", help="Price ID del Módulo 1")
        parser.add_argument("--m2", default="", help="Price ID del Módulo 2")
        parser.add_argument("--m3", default="", help="Price ID del Módulo 3")
        parser.add_argument("--m4", default="", help="Price ID del Módulo 4")

    def handle(self, *args, **opts):
        curso = get_active_course()
        if not curso:
            raise CommandError("No hay curso activo (¿corriste seed_academy?)")

        self.stdout.write("─" * 52)
        self.stdout.write(self.style.MIGRATE_HEADING("CONFIGURANDO PRICE ID · Xamox Academy"))

        if opts["curso"]:
            curso.stripe_price_id = opts["curso"]
            curso.save(update_fields=["stripe_price_id", "updated_at"])
            self.stdout.write(self.style.SUCCESS(f"✓ Curso completo → {opts['curso']}"))
        else:
            self.stdout.write(self.style.WARNING("• --curso no indicado, se deja como estaba"))

        for i in (1, 2, 3, 4):
            price_id = opts.get(f"m{i}")
            if not price_id:
                self.stdout.write(self.style.WARNING(f"• --m{i} no indicado, se deja como estaba"))
                continue
            module = Module.objects.filter(course=curso, position=i).first()
            if not module:
                self.stderr.write(self.style.ERROR(f"✗ No existe el módulo con posición {i}"))
                continue
            module.stripe_price_id = price_id
            module.save(update_fields=["stripe_price_id", "updated_at"])
            self.stdout.write(self.style.SUCCESS(f"✓ Módulo {i} ({module.title}) → {price_id}"))

        self.stdout.write("─" * 52)
        self.stdout.write(self.style.MIGRATE_HEADING("Estado final:"))
        curso.refresh_from_db()
        self.stdout.write(f"  Curso completo: {curso.stripe_price_id or '(vacío)'}")
        for m in Module.objects.filter(course=curso).order_by("position"):
            self.stdout.write(f"  Módulo {m.position} ({m.title}): {m.stripe_price_id or '(vacío)'}")
        self.stdout.write("─" * 52)
        self.stdout.write(self.style.SUCCESS("Listo."))
