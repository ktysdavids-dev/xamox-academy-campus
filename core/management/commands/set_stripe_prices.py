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
        parser.add_argument("--m1-link", default="", help="Payment Link (buy.stripe.com/...) del Módulo 1")
        parser.add_argument("--m2-link", default="", help="Payment Link del Módulo 2")
        parser.add_argument("--m3-link", default="", help="Payment Link del Módulo 3")
        parser.add_argument("--m4-link", default="", help="Payment Link del Módulo 4")
        parser.add_argument("--m1-price", default="", help="Precio a mostrar del Módulo 1, ej. '305 €'")
        parser.add_argument("--m2-price", default="", help="Precio a mostrar del Módulo 2")
        parser.add_argument("--m3-price", default="", help="Precio a mostrar del Módulo 3")
        parser.add_argument("--m4-price", default="", help="Precio a mostrar del Módulo 4")

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
            link = opts.get(f"m{i}_link")
            price_display = opts.get(f"m{i}_price")
            if not price_id and not link and not price_display:
                self.stdout.write(self.style.WARNING(f"• Módulo {i}: nada indicado, se deja como estaba"))
                continue
            module = Module.objects.filter(course=curso, position=i).first()
            if not module:
                self.stderr.write(self.style.ERROR(f"✗ No existe el módulo con posición {i}"))
                continue
            fields = []
            if price_id:
                module.stripe_price_id = price_id
                fields.append("stripe_price_id")
            if link:
                module.stripe_payment_link = link
                fields.append("stripe_payment_link")
            if price_display:
                module.price_display = price_display
                fields.append("price_display")
            module.save(update_fields=fields + ["updated_at"])
            self.stdout.write(self.style.SUCCESS(f"✓ Módulo {i} ({module.title}) actualizado: {', '.join(fields)}"))

        self.stdout.write("─" * 52)
        self.stdout.write(self.style.MIGRATE_HEADING("Estado final:"))
        curso.refresh_from_db()
        self.stdout.write(f"  Curso completo: {curso.stripe_price_id or '(vacío)'}")
        for m in Module.objects.filter(course=curso).order_by("position"):
            self.stdout.write(f"  Módulo {m.position} ({m.title}): {m.stripe_price_id or '(vacío)'}")
        self.stdout.write("─" * 52)
        self.stdout.write(self.style.SUCCESS("Listo."))
