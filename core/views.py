import logging
from pathlib import Path

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.db import connection
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.static import serve

from .decorators import staff_required
from .forms import AcceptInvitationForm, InviteSeatForm, LessonForm, PostPurchaseForm, ResourceForm, StudentCreateForm
from .models import ActivityLog, Course, Enrollment, Lesson, LessonProgress, Module, Purchase, Resource, SeatInvitation
from .services import (
    accept_seat_invitation,
    course_progress,
    ensure_access_email,
    get_active_course,
    get_stream_iframe_src,
    invite_second_seat,
    process_paid_session,
    seats_status,
    set_single_seat,
)

logger = logging.getLogger("core")


def home(request):
    return redirect("dashboard" if request.user.is_authenticated else "login")


def _buyer_purchase(user):
    return Purchase.objects.filter(buyer_email__iexact=user.email, status="paid").order_by("-created_at").first()


@login_required
def dashboard(request):
    if request.user.is_staff:
        return redirect("admin_dashboard")
    enrollments = Enrollment.objects.filter(user=request.user, status="active").select_related("course")
    cards = [{"enrollment": e, "progress": course_progress(request.user, e.course)} for e in enrollments]
    next_lesson = None
    for enrollment in enrollments:
        lesson = Lesson.objects.filter(module__course=enrollment.course, published=True).exclude(
            progress_records__user=request.user, progress_records__completed=True,
        ).order_by("module__position", "position").first()
        if lesson:
            next_lesson = lesson
            break

    purchase = _buyer_purchase(request.user)
    seat_info = seats_status(purchase) if purchase else None
    return render(request, "core/dashboard.html", {
        "cards": cards, "next_lesson": next_lesson,
        "purchase": purchase, "seat_info": seat_info, "invite_form": InviteSeatForm(),
    })


@login_required
@require_POST
def invite_seat(request):
    purchase = _buyer_purchase(request.user)
    if not purchase:
        raise Http404
    form = InviteSeatForm(request.POST)
    if form.is_valid():
        try:
            invite_second_seat(purchase, form.cleaned_data["guest_name"], form.cleaned_data["guest_email"])
            messages.success(request, "Invitación enviada al segundo alumno.")
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception:
            logger.exception("Fallo enviando invitación de plaza")
            messages.error(request, "No se pudo enviar la invitación. Inténtalo de nuevo o escribe a soporte.")
    else:
        messages.error(request, "Revisa el nombre y el email del segundo alumno.")
    return redirect("dashboard")


@login_required
def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug, active=True)
    get_object_or_404(Enrollment, user=request.user, course=course, status="active")
    modules = course.modules.filter(published=True).prefetch_related("lessons")
    completed_ids = set(
        LessonProgress.objects.filter(user=request.user, completed=True).values_list("lesson_id", flat=True)
    )
    return render(request, "core/course_detail.html", {
        "course": course, "modules": modules, "completed_ids": completed_ids,
        "progress": course_progress(request.user, course),
    })


@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson.objects.select_related("module", "module__course"), id=lesson_id, published=True)
    get_object_or_404(Enrollment, user=request.user, course=lesson.module.course, status="active")
    if lesson.release_at and lesson.release_at > timezone.now():
        raise Http404
    progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
    ActivityLog.objects.create(
        user=request.user, action="lesson_viewed", metadata={"lesson_id": lesson.id},
        ip_address=request.META.get("REMOTE_ADDR") or None,
    )
    stream_src = None
    stream_error = False
    if lesson.cf_stream_uid:
        stream_src = get_stream_iframe_src(lesson.cf_stream_uid)
        stream_error = stream_src is None
    return render(request, "core/lesson_detail.html", {
        "lesson": lesson, "progress": progress, "resources": lesson.resources.filter(published=True),
        "stream_src": stream_src, "stream_error": stream_error,
    })


@login_required
@require_POST
def complete_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, published=True)
    get_object_or_404(Enrollment, user=request.user, course=lesson.module.course, status="active")
    progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
    progress.mark_complete()
    messages.success(request, "Clase marcada como completada")
    return redirect("lesson_detail", lesson_id=lesson.id)


@login_required
def protected_media(request, path):
    media_root = Path(settings.MEDIA_ROOT).resolve()
    requested_file = (media_root / path).resolve()
    if requested_file != media_root and media_root not in requested_file.parents:
        raise Http404

    if not request.user.is_staff:
        course = None
        lesson = Lesson.objects.select_related("module__course").filter(video_file=path, published=True).first()
        if lesson:
            if lesson.release_at and lesson.release_at > timezone.now():
                raise Http404
            course = lesson.module.course
        else:
            resource = Resource.objects.select_related("lesson__module__course").filter(file=path, published=True).first()
            if resource:
                if not resource.lesson.published:
                    raise Http404
                if resource.lesson.release_at and resource.lesson.release_at > timezone.now():
                    raise Http404
                course = resource.lesson.module.course

        if not course or not Enrollment.objects.filter(user=request.user, course=course, status="active").exists():
            raise Http404

    return serve(request, path, document_root=settings.MEDIA_ROOT, show_indexes=False)


# ---------------------------------------------------------------------------
# Post-compra: formulario de nombres + elección promo / 1 persona
# ---------------------------------------------------------------------------
def post_purchase(request):
    session_id = (request.GET.get("session_id") or request.POST.get("session_id") or "").strip()
    if not session_id:
        raise Http404

    if not settings.STRIPE_SECRET_KEY:
        return render(request, "core/post_compra.html", {"error": "Pagos no configurados. Escríbenos a soporte."})

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        logger.exception("No se pudo recuperar la sesión de Stripe %s", session_id)
        raise Http404

    if session.get("payment_status") != "paid":
        return render(request, "core/post_compra.html", {"pending": True})
    if settings.STRIPE_PAYMENT_LINK_ID and session.get("payment_link") != settings.STRIPE_PAYMENT_LINK_ID:
        raise Http404

    purchase = Purchase.objects.filter(stripe_session_id=session_id).first()
    if not purchase:
        try:
            purchase, buyer = process_paid_session(session)
        except Exception:
            logger.exception("No se pudo procesar la sesión pagada %s", session_id)
            return render(request, "core/post_compra.html", {"error": "Estamos registrando tu compra. Vuelve a intentarlo en un minuto."})

    # Aseguramos el email de acceso del comprador (best-effort, no bloquea el formulario)
    from django.contrib.auth import get_user_model
    buyer_user = get_user_model().objects.filter(email__iexact=purchase.buyer_email).first()
    if buyer_user:
        try:
            ensure_access_email(buyer_user, purchase)
        except Exception:
            logger.exception("Email de acceso pendiente para purchase_id=%s", purchase.id)

    if request.method == "POST":
        form = PostPurchaseForm(request.POST, buyer_email=purchase.buyer_email)
        if form.is_valid():
            if buyer_user and form.cleaned_data["buyer_name"]:
                from .services import _apply_name
                _apply_name(buyer_user, form.cleaned_data["buyer_name"])
                buyer_user.save(update_fields=["first_name", "last_name"])
            purchase.buyer_name = form.cleaned_data["buyer_name"]
            purchase.save(update_fields=["buyer_name", "updated_at"])

            if form.cleaned_data["plan"] == "promo":
                try:
                    invite_second_seat(purchase, form.cleaned_data["guest_name"], form.cleaned_data["guest_email"])
                    messages.success(request, "¡Listo! Hemos enviado la invitación al segundo alumno.")
                except Exception as exc:
                    logger.exception("Fallo invitando segunda plaza")
                    messages.error(request, f"Tu acceso está activo, pero la invitación falló: {exc}")
            else:
                set_single_seat(purchase)
                messages.success(request, "¡Listo! Tu acceso está activo.")
            return render(request, "core/post_compra.html", {"done": True, "purchase": purchase, "seat_info": seats_status(purchase)})
    else:
        form = PostPurchaseForm(buyer_email=purchase.buyer_email, initial={"buyer_name": purchase.buyer_name})

    return render(request, "core/post_compra.html", {"form": form, "purchase": purchase, "session_id": session_id})


def accept_invitation(request, token):
    invitation = get_object_or_404(SeatInvitation, token=token)
    if invitation.status != "pending":
        return render(request, "registration/accept_invitation.html", {"unavailable": True})

    if request.method == "POST":
        form = AcceptInvitationForm(request.POST)
        if form.is_valid():
            try:
                user = accept_seat_invitation(invitation, form.cleaned_data["full_name"], form.cleaned_data["password1"])
            except Exception as exc:
                logger.exception("Fallo aceptando invitación")
                messages.error(request, f"No se pudo completar el acceso: {exc}")
                return render(request, "registration/accept_invitation.html", {"form": form, "invitation": invitation})
            login(request, user, backend="core.auth_backend.EmailOrUsernameBackend")
            messages.success(request, "Cuenta activada. Bienvenido a Xamox Academy.")
            return redirect("dashboard")
    else:
        form = AcceptInvitationForm(initial={"full_name": invitation.invited_name})

    return render(request, "registration/accept_invitation.html", {"form": form, "invitation": invitation})


# ---------------------------------------------------------------------------
# Panel admin propio
# ---------------------------------------------------------------------------
@staff_required
def admin_dashboard(request):
    stats = {
        "students": User.objects.filter(is_staff=False, enrollments__status="active").distinct().count(),
        "enrollments": Enrollment.objects.filter(status="active").count(),
        "purchases": Purchase.objects.filter(status="paid").count(),
        "lessons": Lesson.objects.filter(published=True).count(),
    }
    students = User.objects.filter(is_staff=False).annotate(
        active_enrollments=Count("enrollments", filter=Q(enrollments__status="active"))
    ).order_by("-date_joined")[:10]
    purchases = Purchase.objects.order_by("-created_at")[:8]
    return render(request, "core/admin_dashboard.html", {"stats": stats, "students": students, "purchases": purchases})


@staff_required
def admin_students(request):
    return render(request, "core/admin_students.html", {
        "students": User.objects.filter(is_staff=False).prefetch_related("enrollments__course").order_by("-date_joined"),
    })


@staff_required
def admin_student_create(request):
    form = StudentCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"Alumno {user.email} creado")
        return redirect("admin_students")
    return render(request, "core/admin_student_form.html", {"form": form})


@staff_required
def admin_student_detail(request, user_id):
    student = get_object_or_404(User, id=user_id, is_staff=False)
    return render(request, "core/admin_student_detail.html", {
        "student": student,
        "enrollments": student.enrollments.select_related("course"),
        "progress_records": LessonProgress.objects.filter(user=student).select_related("lesson", "lesson__module").order_by("-updated_at"),
        "courses": Course.objects.filter(active=True).order_by("title"),
    })


@staff_required
@require_POST
def admin_enroll_student(request, user_id):
    student = get_object_or_404(User, id=user_id, is_staff=False)
    course = get_object_or_404(Course, id=request.POST.get("course_id"))
    enrollment, _ = Enrollment.objects.get_or_create(user=student, course=course, defaults={"status": "active"})
    if enrollment.status != "active":
        enrollment.status = "active"
        enrollment.save()
    messages.success(request, f"{student.email} matriculado en {course.title}")
    return redirect("admin_student_detail", user_id=student.id)



# ---------------------------------------------------------------------------
# Panel de contenido: clases y recursos (sustituye depender de Django Admin)
# ---------------------------------------------------------------------------
@staff_required
def admin_content(request):
    course = get_active_course()
    if not course:
        raise Http404
    modules = course.modules.order_by("position").prefetch_related("lessons__resources")
    return render(request, "core/admin_content.html", {"course": course, "modules": modules})


@staff_required
def admin_lesson_create(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module
            last_position = module.lessons.count()
            lesson.position = last_position + 1
            lesson.save()
            messages.success(request, f"Clase «{lesson.title}» creada.")
            return redirect("admin_lesson_edit", lesson_id=lesson.id)
    else:
        form = LessonForm()
    return render(request, "core/admin_lesson_form.html", {"form": form, "module": module, "lesson": None})


@staff_required
def admin_lesson_edit(request, lesson_id):
    lesson = get_object_or_404(Lesson.objects.select_related("module"), id=lesson_id)
    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, "Clase actualizada.")
            return redirect("admin_lesson_edit", lesson_id=lesson.id)
    else:
        form = LessonForm(instance=lesson)
    resource_form = ResourceForm()
    return render(request, "core/admin_lesson_form.html", {
        "form": form, "module": lesson.module, "lesson": lesson,
        "resources": lesson.resources.order_by("position"), "resource_form": resource_form,
    })


@staff_required
@require_POST
def admin_lesson_toggle_publish(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    lesson.published = not lesson.published
    lesson.save(update_fields=["published", "updated_at"])
    messages.success(request, f"Clase {'publicada' if lesson.published else 'ocultada'}.")
    return redirect("admin_content")


@staff_required
@require_POST
def admin_lesson_delete(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    module_id = lesson.module_id
    lesson.delete()
    messages.success(request, "Clase eliminada.")
    return redirect("admin_content")


@staff_required
@require_POST
def admin_resource_create(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    form = ResourceForm(request.POST, request.FILES)
    if form.is_valid():
        resource = form.save(commit=False)
        resource.lesson = lesson
        resource.position = lesson.resources.count() + 1
        resource.save()
        messages.success(request, f"Recurso «{resource.title}» añadido.")
    else:
        messages.error(request, "Revisa el recurso: " + " / ".join(
            f"{field}: {', '.join(errs)}" for field, errs in form.errors.items()
        ))
    return redirect("admin_lesson_edit", lesson_id=lesson.id)


@staff_required
@require_POST
def admin_resource_delete(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)
    lesson_id = resource.lesson_id
    resource.delete()
    messages.success(request, "Recurso eliminado.")
    return redirect("admin_lesson_edit", lesson_id=lesson_id)


def activate_account(request, uidb64, token):
    user = None
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid, is_active=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        pass

    valid = bool(user and default_token_generator.check_token(user, token))
    form = SetPasswordForm(user, request.POST or None) if valid else None

    if valid and request.method == "POST" and form.is_valid():
        form.save()
        login(request, user, backend="core.auth_backend.EmailOrUsernameBackend")
        ActivityLog.objects.create(user=user, action="account_activated")
        messages.success(request, "Cuenta activada. Bienvenido a Xamox Academy.")
        return redirect("dashboard")

    return render(request, "registration/activate.html", {"form": form, "valid": valid})


def buy_redirect(request):
    return redirect(settings.STRIPE_PAYMENT_LINK)


@csrf_exempt
def stripe_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not settings.STRIPE_WEBHOOK_SECRET:
        return JsonResponse({"error": "STRIPE_WEBHOOK_SECRET no configurado"}, status=503)
    if not settings.STRIPE_PAYMENT_LINK_ID:
        return JsonResponse({"error": "STRIPE_PAYMENT_LINK_ID no configurado"}, status=503)

    try:
        event = stripe.Webhook.construct_event(
            request.body, request.META.get("HTTP_STRIPE_SIGNATURE", ""), settings.STRIPE_WEBHOOK_SECRET,
        )
    except Exception:
        logger.exception("Firma Stripe inválida")
        return HttpResponse(status=400)

    if event["type"] not in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        return HttpResponse(status=200)

    session = event["data"]["object"]
    if session.get("payment_link") != settings.STRIPE_PAYMENT_LINK_ID:
        return JsonResponse({"status": "ignored", "reason": "payment_link"}, status=200)
    if session.get("payment_status") != "paid":
        return JsonResponse({"status": "pending"}, status=200)

    try:
        purchase, user = process_paid_session(session)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except LookupError as exc:
        return JsonResponse({"error": str(exc)}, status=503)

    try:
        ensure_access_email(user, purchase)
    except Exception:
        logger.exception("No se pudo enviar el email de acceso para purchase_id=%s", purchase.id)
        return JsonResponse({"error": "Compra registrada; email pendiente"}, status=500)

    return JsonResponse({"status": "ok", "purchase_id": purchase.id, "student_id": user.id}, status=200)


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        tables = set(connection.introspection.table_names())
        required = {"auth_user", "django_session", "django_migrations", "core_course"}
        missing = sorted(required - tables)
        if missing:
            return JsonResponse({"status": "error", "database": "ok", "schema": "incomplete", "missing_tables": missing}, status=503)
        return JsonResponse({"status": "ok", "database": "ok", "schema": "ok"})
    except Exception:
        logger.exception("Healthcheck de base de datos fallido")
        return JsonResponse({"status": "error", "database": "unavailable", "schema": "unknown"}, status=503)
