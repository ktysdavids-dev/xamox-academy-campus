import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import ActivityLog, Enrollment, Lesson, LessonProgress, StudentProfile

logger = logging.getLogger("core")


def course_progress(user, course):
    lessons = Lesson.objects.filter(module__course=course, published=True)
    total = lessons.count()
    if total == 0:
        return 0
    completed = LessonProgress.objects.filter(user=user, lesson__in=lessons, completed=True).count()
    return round((completed / total) * 100)


def provision_buyer_access(purchase, buyer_name=""):
    """Crea/actualiza el alumno comprador y activa su matrícula."""
    email = (purchase.buyer_email or "").strip().lower()
    if not email or not purchase.course:
        raise ValueError("La compra no tiene email o curso válido")

    User = get_user_model()
    user = User.objects.filter(email__iexact=email).order_by("id").first()
    created = False

    if user is None:
        username = email[:150]
        user = User(username=username, email=email)
        user.set_unusable_password()
        created = True

    if buyer_name:
        parts = buyer_name.strip().split(None, 1)
        if parts:
            user.first_name = parts[0][:150]
        if len(parts) > 1:
            user.last_name = parts[1][:150]

    user.is_active = True
    user.save()
    StudentProfile.objects.get_or_create(user=user, defaults={"active": True})

    enrollment, _ = Enrollment.objects.get_or_create(
        user=user,
        course=purchase.course,
        defaults={"status": "active"},
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


def build_activation_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f"{settings.APP_URL}/activar/{uid}/{token}/"


def send_purchase_access_email(user, purchase):
    """Envía el acceso inicial al Campus. Lanza excepción si SMTP no está configurado."""
    if not settings.EMAIL_HOST or not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        raise RuntimeError("SMTP no configurado: faltan EMAIL_HOST/EMAIL_HOST_USER/EMAIL_HOST_PASSWORD")

    activation_url = build_activation_url(user)
    context = {
        "user": user,
        "purchase": purchase,
        "activation_url": activation_url,
        "login_url": f"{settings.APP_URL}/login/",
        "support_email": settings.SUPPORT_EMAIL,
        "app_url": settings.APP_URL,
    }
    subject = "Tu acceso a Xamox Academy ya está listo"
    text_body = render_to_string("emails/purchase_access.txt", context)
    html_body = render_to_string("emails/purchase_access.html", context)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
        reply_to=[settings.SUPPORT_EMAIL],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)

    ActivityLog.objects.create(
        user=user,
        action="access_email_sent",
        metadata={"purchase_id": purchase.id, "email": user.email},
    )
    logger.info("Email de acceso enviado para purchase_id=%s", purchase.id)
