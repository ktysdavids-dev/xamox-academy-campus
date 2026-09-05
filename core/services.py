import logging
import secrets
import time

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import ActivityLog, Course, Enrollment, Lesson, LessonProgress, Purchase, SeatInvitation, StudentProfile

logger = logging.getLogger("core")

COURSE_SLUG = "ia-marketing-digital"


def get_active_course():
    return Course.objects.filter(slug=COURSE_SLUG, active=True).first()


def course_progress(user, course):
    lessons = Lesson.objects.filter(module__course=course, published=True)
    total = lessons.count()
    if total == 0:
        return 0
    completed = LessonProgress.objects.filter(user=user, lesson__in=lessons, completed=True).count()
    return round((completed / total) * 100)


# ---------------------------------------------------------------------------
# Cloudflare Stream: vídeo largo servido fuera de Railway (subida y
# reproducción no pasan por nuestro Gunicorn de un solo worker).
# ---------------------------------------------------------------------------
def get_stream_iframe_src(cf_stream_uid, valid_hours=4):
    """Pide a Cloudflare un token de reproducción firmado (de un solo uso,
    caduca en `valid_hours`) y devuelve la URL del iframe privado. Devuelve
    None si Cloudflare no está configurado o falla la llamada."""
    if not cf_stream_uid:
        return None
    if not settings.CF_ACCOUNT_ID or not settings.CF_STREAM_API_TOKEN:
        logger.error("Cloudflare Stream no configurado: faltan CF_ACCOUNT_ID/CF_STREAM_API_TOKEN")
        return None

    url = f"https://api.cloudflare.com/client/v4/accounts/{settings.CF_ACCOUNT_ID}/stream/{cf_stream_uid}/token"
    try:
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {settings.CF_STREAM_API_TOKEN}"},
            json={"exp": int(time.time()) + valid_hours * 3600},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            logger.error("Cloudflare Stream token rechazado: %s", data.get("errors"))
            return None
        token = data["result"]["token"]
        return f"https://iframe.videodelivery.net/{token}"
    except Exception:
        logger.exception("Fallo pidiendo token de Cloudflare Stream para uid=%s", cf_stream_uid)
        return None


# ---------------------------------------------------------------------------
# Provisión del comprador (alumno 1)
# ---------------------------------------------------------------------------
def _apply_name(user, full_name):
    parts = (full_name or "").strip().split(None, 1)
    if parts:
        user.first_name = parts[0][:150]
    if len(parts) > 1:
        user.last_name = parts[1][:150]


def provision_buyer_access(purchase, buyer_name=""):
    """Crea/actualiza el alumno comprador y activa su matrícula. Idempotente."""
    email = (purchase.buyer_email or "").strip().lower()
    if not email or not purchase.course:
        raise ValueError("La compra no tiene email o curso válido")

    User = get_user_model()
    user = User.objects.filter(email__iexact=email).order_by("id").first()
    created = False
    if user is None:
        user = User(username=email[:150], email=email)
        user.set_unusable_password()
        created = True

    if buyer_name:
        _apply_name(user, buyer_name)

    user.is_active = True
    user.save()
    StudentProfile.objects.get_or_create(user=user, defaults={"active": True})

    enrollment, _ = Enrollment.objects.get_or_create(
        user=user, course=purchase.course, defaults={"status": "active"}
    )
    if enrollment.status != "active":
        enrollment.status = "active"
        enrollment.save(update_fields=["status", "updated_at"])

    ActivityLog.objects.create(
        user=user,
        action="purchase_access_provisioned",
        metadata={"purchase_id": purchase.id, "new_user": created},
    )
    return user


def process_paid_session(session):
    """Registra la compra pagada y provisiona al comprador. Reutilizable por
    el webhook y por la página post-compra. NO envía el email (ver ensure_access_email).
    Devuelve (purchase, user)."""
    customer_details = session.get("customer_details") or {}
    email = (customer_details.get("email") or session.get("customer_email") or "").strip().lower()
    buyer_name = (customer_details.get("name") or "").strip()
    if not email:
        raise ValueError("Stripe no devolvió email del comprador")

    course = get_active_course()
    if not course:
        raise LookupError("Curso Xamox Academy no encontrado")

    with transaction.atomic():
        purchase, _ = Purchase.objects.update_or_create(
            stripe_session_id=session["id"],
            defaults={
                "stripe_payment_intent": session.get("payment_intent") or "",
                "buyer_email": email,
                "buyer_name": buyer_name,
                "amount_cents": session.get("amount_total") or 0,
                "currency": session.get("currency") or "eur",
                "status": "paid",
                "seats": 2,
                "course": course,
            },
        )
        user = provision_buyer_access(purchase, buyer_name=buyer_name)
    return purchase, user


# ---------------------------------------------------------------------------
# Email de acceso (alumno 1)
# ---------------------------------------------------------------------------
def build_activation_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f"{settings.APP_URL}/activar/{uid}/{token}/"


def _require_smtp():
    if not settings.EMAIL_HOST or not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        raise RuntimeError("SMTP no configurado: faltan EMAIL_HOST/EMAIL_HOST_USER/EMAIL_HOST_PASSWORD")


def send_purchase_access_email(user, purchase):
    _require_smtp()
    context = {
        "user": user,
        "purchase": purchase,
        "activation_url": build_activation_url(user),
        "login_url": f"{settings.APP_URL}/login/",
        "support_email": settings.SUPPORT_EMAIL,
        "app_url": settings.APP_URL,
    }
    subject = "Tu acceso a Xamox Academy ya está listo"
    message = EmailMultiAlternatives(
        subject=subject,
        body=render_to_string("emails/purchase_access.txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
        reply_to=[settings.SUPPORT_EMAIL],
    )
    message.attach_alternative(render_to_string("emails/purchase_access.html", context), "text/html")
    message.send(fail_silently=False)
    ActivityLog.objects.create(
        user=user, action="access_email_sent", metadata={"purchase_id": purchase.id, "email": user.email}
    )
    logger.info("Email de acceso enviado para purchase_id=%s", purchase.id)


def ensure_access_email(user, purchase):
    """Envía el email de acceso solo si aún no se envió. Devuelve True si lo envió."""
    already = ActivityLog.objects.filter(
        user=user, action="access_email_sent", metadata__purchase_id=purchase.id
    ).exists()
    if already:
        return False
    send_purchase_access_email(user, purchase)
    return True


# ---------------------------------------------------------------------------
# Segunda plaza (promo 2x1)
# ---------------------------------------------------------------------------
def seats_status(purchase):
    invitation = purchase.seat_invitations.exclude(status="revoked").order_by("-created_at").first()
    used = 1 + (1 if invitation and invitation.status == "accepted" else 0)
    return {"used": used, "total": purchase.seats, "invitation": invitation}


def invite_second_seat(purchase, name, email):
    """Crea/reutiliza la invitación de la 2ª plaza y envía el email. Devuelve la invitación."""
    email = (email or "").strip().lower()
    name = (name or "").strip()
    if not email:
        raise ValueError("Falta el email del segundo alumno")
    if email == (purchase.buyer_email or "").strip().lower():
        raise ValueError("El segundo alumno debe tener un email distinto al del comprador")

    existing = purchase.seat_invitations.order_by("-created_at").first()
    if existing and existing.status == "accepted":
        raise ValueError("La segunda plaza ya fue aceptada por otro alumno")

    if existing:
        invitation = existing
        invitation.email = email
        invitation.invited_name = name
        invitation.status = "pending"
        invitation.token = secrets.token_urlsafe(32)
        invitation.save()
    else:
        invitation = SeatInvitation.objects.create(
            purchase=purchase, email=email, invited_name=name, status="pending"
        )

    if purchase.seats < 2:
        purchase.seats = 2
        purchase.save(update_fields=["seats", "updated_at"])

    send_seat_invitation_email(invitation)
    ActivityLog.objects.create(
        user=None, action="seat_invitation_sent",
        metadata={"purchase_id": purchase.id, "invitation_id": invitation.id, "email": email},
    )
    return invitation


def set_single_seat(purchase):
    """El comprador elige usar una sola plaza. Revoca invitaciones pendientes."""
    purchase.seat_invitations.filter(status="pending").update(status="revoked")
    if purchase.seats != 1:
        purchase.seats = 1
        purchase.save(update_fields=["seats", "updated_at"])


def build_invitation_url(invitation):
    return f"{settings.APP_URL}/invitacion/{invitation.token}/"


def send_seat_invitation_email(invitation):
    _require_smtp()
    purchase = invitation.purchase
    context = {
        "invitation": invitation,
        "purchase": purchase,
        "invited_name": invitation.invited_name,
        "buyer_name": purchase.buyer_name,
        "accept_url": build_invitation_url(invitation),
        "support_email": settings.SUPPORT_EMAIL,
        "app_url": settings.APP_URL,
    }
    subject = "Te han invitado al Campus de Xamox Academy"
    message = EmailMultiAlternatives(
        subject=subject,
        body=render_to_string("emails/seat_invitation.txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[invitation.email],
        reply_to=[settings.SUPPORT_EMAIL],
    )
    message.attach_alternative(render_to_string("emails/seat_invitation.html", context), "text/html")
    message.send(fail_silently=False)
    logger.info("Email de invitación enviado para invitation_id=%s", invitation.id)


def accept_seat_invitation(invitation, full_name, password):
    """Crea/activa al alumno 2, lo matricula y marca la invitación como aceptada. Devuelve el user."""
    if invitation.status != "pending":
        raise ValueError("Esta invitación ya no está disponible")

    validate_password(password)
    email = (invitation.email or "").strip().lower()
    course = invitation.purchase.course or get_active_course()
    if not course:
        raise LookupError("Curso Xamox Academy no encontrado")

    User = get_user_model()
    with transaction.atomic():
        user = User.objects.filter(email__iexact=email).order_by("id").first()
        if user is None:
            user = User(username=email[:150], email=email)
        _apply_name(user, full_name or invitation.invited_name)
        user.is_active = True
        user.set_password(password)
        user.save()
        StudentProfile.objects.get_or_create(user=user, defaults={"active": True})

        enrollment, _ = Enrollment.objects.get_or_create(
            user=user, course=course, defaults={"status": "active"}
        )
        if enrollment.status != "active":
            enrollment.status = "active"
            enrollment.save(update_fields=["status", "updated_at"])

        invitation.status = "accepted"
        invitation.accepted_by = user
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["status", "accepted_by", "accepted_at", "updated_at"])

    ActivityLog.objects.create(
        user=user, action="seat_invitation_accepted",
        metadata={"purchase_id": invitation.purchase_id, "invitation_id": invitation.id},
    )
    return user
