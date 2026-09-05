import secrets
import time

from django.core.management.base import BaseCommand, CommandError

from core.models import Module
from core.services import ensure_access_email, get_active_course, invite_second_seat, process_paid_session, seats_status


class Command(BaseCommand):
    help = ("Simula una compra pagada (sin cobrar) para probar el flujo end-to-end: "
            "compra -> matricula -> email de acceso y, opcionalmente, invitacion 2x1. "
            "Por defecto simula la compra del CURSO COMPLETO. Usa --modulo N para "
            "simular la compra de un módulo suelto (requiere que ese Module tenga "
            "stripe_price_id ya configurado).")

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Email del comprador")
        parser.add_argument("--nombre", default="", help="Nombre completo del comprador")
        parser.add_argument("--modulo", type=int, default=None,
                             help="Posición del módulo (1-4) para simular una compra SUELTA en vez del curso completo")
        parser.add_argument("--price-id", default="", help="Forzar un Price ID de Stripe concreto (para pruebas)")
        parser.add_argument("--invitado-email", default="", help="Email del alumno 2 (solo aplica al curso completo)")
        parser.add_argument("--invitado-nombre", default="", help="Nombre del alumno 2")
        parser.add_argument("--amount", type=int, default=None, help="Importe en céntimos (por defecto el precio real del producto)")

    def handle(self, *args, **opts):
        email = opts["email"].strip().lower()
        curso = get_active_course()
        if not curso:
            raise CommandError("No hay curso activo (¿corriste seed_academy?)")

        if opts["price_id"]:
            price_id = opts["price_id"]
            default_amount = 0
        elif opts["modulo"]:
            module = Module.objects.filter(course=curso, position=opts["modulo"]).first()
            if not module:
                raise CommandError(f"No existe el módulo con posición {opts['modulo']}")
            if not module.stripe_price_id:
                raise CommandError(
                    f"El módulo «{module.title}» no tiene stripe_price_id configurado. "
                    "Créalo en Stripe y pégalo en Django Admin > Modules primero."
                )
            price_id = module.stripe_price_id
            default_amount = 0
        else:
            if not curso.stripe_price_id:
                raise CommandError(
                    "El curso no tiene stripe_price_id configurado. "
                    "Pégalo en Django Admin > Courses primero (o usa --price-id para forzarlo en la prueba)."
                )
            price_id = curso.stripe_price_id
            default_amount = 120000

        stamp = f"{int(time.time())}_{secrets.token_hex(4)}"
        session = {
            "id": f"cs_sim_{stamp}",
            "payment_intent": f"pi_sim_{stamp}",
            "payment_status": "paid",
            "amount_total": opts["amount"] if opts["amount"] is not None else default_amount,
            "currency": "eur",
            "customer_details": {"email": email, "name": opts["nombre"]},
        }

        self.stdout.write("─" * 52)
        self.stdout.write(self.style.MIGRATE_HEADING("SIMULACIÓN DE COMPRA · Xamox Academy"))
        purchase, user = process_paid_session(session, price_id=price_id)
        scope_label = "módulo suelto" if purchase.scope == "module" else "curso completo"
        self.stdout.write(self.style.SUCCESS(f"✓ Compra registrada  · purchase_id={purchase.id} ({scope_label})"))
        if purchase.module:
            self.stdout.write(self.style.SUCCESS(f"✓ Acceso concedido   · módulo: {purchase.module.title}"))
        self.stdout.write(self.style.SUCCESS(f"✓ Alumno matriculado · {user.email} (user_id={user.id})"))

        try:
            sent = ensure_access_email(user, purchase)
            if sent:
                self.stdout.write(self.style.SUCCESS(f"✓ Email de acceso ENVIADO a {user.email}"))
            else:
                self.stdout.write(self.style.WARNING("• Email de acceso ya se había enviado antes (no reenviado)"))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"✗ FALLO al enviar el email de acceso: {exc}"))

        if opts["invitado_email"] and purchase.scope == "full":
            try:
                inv = invite_second_seat(purchase, opts["invitado_nombre"], opts["invitado_email"])
                self.stdout.write(self.style.SUCCESS(f"✓ Invitación 2ª plaza ENVIADA a {inv.email}"))
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"✗ FALLO invitación 2ª plaza: {exc}"))
            st = seats_status(purchase)
            self.stdout.write(f"  Plazas usadas: {st['used']}/{st['total']}")
        elif opts["invitado_email"]:
            self.stdout.write(self.style.WARNING("• --invitado-email se ignora: la promo 2x1 solo aplica al curso completo"))

        self.stdout.write("─" * 52)
        self.stdout.write(self.style.SUCCESS("Listo. Revisa la bandeja de entrada (y spam)."))
