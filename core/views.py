from pathlib import Path
import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import connection
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.static import serve
from .decorators import staff_required
from .forms import StudentCreateForm
from .models import ActivityLog, Course, Enrollment, Lesson, LessonProgress, Purchase, Resource, SeatInvitation
from .services import course_progress


def home(request):
    return redirect("dashboard" if request.user.is_authenticated else "login")


@login_required
def dashboard(request):
    if request.user.is_staff:
        return redirect("admin_dashboard")
    enrollments = Enrollment.objects.filter(user=request.user, status="active").select_related("course")
    cards = [{"enrollment": e, "progress": course_progress(request.user, e.course)} for e in enrollments]
    next_lesson = None
    for enrollment in enrollments:
        lesson = Lesson.objects.filter(module__course=enrollment.course, published=True).exclude(
            progress_records__user=request.user,
            progress_records__completed=True,
        ).order_by("module__position", "position").first()
        if lesson:
            next_lesson = lesson
            break
    return render(request, "core/dashboard.html", {"cards": cards, "next_lesson": next_lesson})


@login_required
def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug, active=True)
    get_object_or_404(Enrollment, user=request.user, course=course, status="active")
    modules = course.modules.filter(published=True).prefetch_related("lessons")
    completed_ids = set(
        LessonProgress.objects.filter(user=request.user, completed=True).values_list("lesson_id", flat=True)
    )
    return render(
        request,
        "core/course_detail.html",
        {"course": course, "modules": modules, "completed_ids": completed_ids, "progress": course_progress(request.user, course)},
    )


@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(
        Lesson.objects.select_related("module", "module__course"),
        id=lesson_id,
        published=True,
    )
    get_object_or_404(Enrollment, user=request.user, course=lesson.module.course, status="active")
    if lesson.release_at and lesson.release_at > timezone.now():
        raise Http404
    progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
    ActivityLog.objects.create(
        user=request.user,
        action="lesson_viewed",
        metadata={"lesson_id": lesson.id},
        ip_address=request.META.get("REMOTE_ADDR") or None,
    )
    return render(
        request,
        "core/lesson_detail.html",
        {"lesson": lesson, "progress": progress, "resources": lesson.resources.filter(published=True)},
    )


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
    """Sirve vídeos y recursos solo a staff o alumnos matriculados en el curso correspondiente."""
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
    return render(
        request,
        "core/admin_students.html",
        {"students": User.objects.filter(is_staff=False).prefetch_related("enrollments__course").order_by("-date_joined")},
    )


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
    return render(
        request,
        "core/admin_student_detail.html",
        {
            "student": student,
            "enrollments": student.enrollments.select_related("course"),
            "progress_records": LessonProgress.objects.filter(user=student).select_related("lesson", "lesson__module").order_by("-updated_at"),
            "courses": Course.objects.filter(active=True).order_by("title"),
        },
    )


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


def buy_redirect(request):
    return redirect(settings.STRIPE_PAYMENT_LINK)


@csrf_exempt
def stripe_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not settings.STRIPE_WEBHOOK_SECRET:
        return JsonResponse({"error": "Webhook no configurado"}, status=503)
    try:
        event = stripe.Webhook.construct_event(
            request.body,
            request.META.get("HTTP_STRIPE_SIGNATURE", ""),
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except Exception:
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        email = (session.get("customer_details") or {}).get("email") or session.get("customer_email") or ""
        purchase, _ = Purchase.objects.update_or_create(
            stripe_session_id=session["id"],
            defaults={
                "stripe_payment_intent": session.get("payment_intent") or "",
                "buyer_email": email,
                "amount_cents": session.get("amount_total") or 0,
                "currency": session.get("currency") or "eur",
                "status": "paid",
                "seats": 2,
                "course": Course.objects.filter(active=True).first(),
            },
        )
        if email:
            SeatInvitation.objects.get_or_create(purchase=purchase, email=email)
    return HttpResponse(status=200)


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return JsonResponse({"status": "ok", "database": "ok"})
    except Exception:
        return JsonResponse({"status": "error", "database": "unavailable"}, status=503)
