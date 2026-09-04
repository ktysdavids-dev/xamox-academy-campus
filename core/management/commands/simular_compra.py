import time

from django.conf import settings
from django.core.management.base import BaseCommand

from core.services import ensure_access_email, invite_second_seat, process_paid_session, seats_status


class Command(BaseCommand):
    help = ("Simula una compra pagada (sin cobrar) para probar el flujo end-to-end: "
            "compra -> matricula -> email de acceso y, opcionalmente, invitacion 2x1.")

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Email del comprador (alumno 1)")
        parser.add_argument("--nombre", default="", help="Nombre completo del comprador")
        parser.add_argument("--invitado-email", default="", help="Email del alumno 2 (activa la promo 2x1)")
        parser.add_argument("--invitado-nombre", default="", help="Nombre del alumno 2")
        parser.add_argument("--amount", type=int, default=120000, help="Importe en céntimos (por defecto 120000 = 1.200 €)")

    def handle(self, *args, **opts):
        email = opts["email"].strip().lower()
        stamp = int(time.time())
        session = {
            "id": f"cs_sim_{stamp}",
            "payment_intent": f"pi_sim_{stamp}",
            "payment_status": "paid",
            "payment_link": settings.STRIPE_PAYMENT_LINK_ID or "plink_sim",
            "amount_total": opts["amount"],
            "currency": "eur",
            "customer_details": {"email": email, "name": opts["nombre"]},
        }

        self.stdout.write("─" * 52)
        self.stdout.write(self.style.MIGRATE_HEADING("SIMULACIÓN DE COMPRA · Xamox Academy"))
        purchase, user = process_paid_session(session)
        self.stdout.write(self.style.SUCCESS(
            f"✓ Compra registrada  · purchase_id={purchase.id}"))
        self.stdout.write(self.style.SUCCESS(
            f"✓ Alumno matriculado · {user.email} (user_id={user.id})"))

        try:
            sent = ensure_access_email(user, purchase)
            if sent:
                self.stdout.write(self.style.SUCCESS(f"✓ Email de acceso ENVIADO a {user.email}"))
            else:
                self.stdout.write(self.style.WARNING("• Email de acceso ya se había enviado antes (no reenviado)"))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"✗ FALLO al enviar el email de acceso: {exc}"))
            self.stderr.write(self.style.ERROR("  Revisa las variables EMAIL_* de IONOS en Railway."))

        if opts["invitado_email"]:
            try:
                inv = invite_second_seat(purchase, opts["invitado_nombre"], opts["invitado_email"])
                self.stdout.write(self.style.SUCCESS(f"✓ Invitación 2ª plaza ENVIADA a {inv.email}"))
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"✗ FALLO invitación 2ª plaza: {exc}"))

        st = seats_status(purchase)
        self.stdout.write(f"  Plazas usadas: {st['used']}/{st['total']}")
        self.stdout.write("─" * 52)
        self.stdout.write(self.style.SUCCESS("Listo. Revisa la bandeja de entrada (y spam)."))
