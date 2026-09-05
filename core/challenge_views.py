import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Achievement,
    Challenge,
    Module,
    Question,
    QuestionAttempt,
    QuizAttempt,
    StudentAchievement,
)
from .services import accessible_module_ids, user_can_access_module


def _student_xp(user):
    quiz_xp = user.challenge_attempts.filter(completed_at__isnull=False).aggregate(total=Sum("xp_earned"))["total"] or 0
    badge_xp = StudentAchievement.objects.filter(user=user).aggregate(total=Sum("achievement__xp_bonus"))["total"] or 0
    return quiz_xp + badge_xp


def _best_attempt(user, challenge):
    return QuizAttempt.objects.filter(user=user, challenge=challenge, completed_at__isnull=False).order_by("-percent", "created_at").first()


def _award_badges(user, attempt):
    earned = []
    if attempt.passed:
        first, _ = Achievement.objects.get_or_create(
            code="primer-reto",
            defaults={"name": "Primer reto", "description": "Has superado tu primer Xamox Challenge.", "icon": "🎯", "xp_bonus": 20},
        )
        _, created = StudentAchievement.objects.get_or_create(user=user, achievement=first)
        if created:
            earned.append(first)

    if attempt.passed and attempt.challenge.challenge_type == "exam":
        module_badge, _ = Achievement.objects.get_or_create(
            code=f"modulo-{attempt.challenge.module.position}-master",
            defaults={
                "name": f"Módulo {attempt.challenge.module.position} Master",
                "description": f"Has superado el examen de {attempt.challenge.module.title}.",
                "icon": "🏆",
                "xp_bonus": 50,
            },
        )
        _, created = StudentAchievement.objects.get_or_create(user=user, achievement=module_badge)
        if created:
            earned.append(module_badge)
    return earned


@login_required
def challenge_hub(request):
    if request.user.is_staff:
        return redirect("admin_dashboard")

    modules = Module.objects.filter(published=True, challenges__published=True).select_related("course").distinct()
    allowed = []
    for module in modules:
        if user_can_access_module(request.user, module):
            challenges = list(module.challenges.filter(published=True).order_by("position"))
            for challenge in challenges:
                challenge.best = _best_attempt(request.user, challenge)
                challenge.attempt_count = QuizAttempt.objects.filter(user=request.user, challenge=challenge).count()
            module.challenge_list = challenges
            allowed.append(module)

    badges = StudentAchievement.objects.filter(user=request.user).select_related("achievement").order_by("-awarded_at")
    return render(request, "core/challenge_hub.html", {
        "modules": allowed,
        "xp": _student_xp(request.user),
        "badges": badges,
    })


@login_required
def challenge_detail(request, challenge_id):
    challenge = get_object_or_404(Challenge.objects.select_related("module", "module__course"), id=challenge_id, published=True)
    if not user_can_access_module(request.user, challenge.module):
        raise Http404
    attempts = QuizAttempt.objects.filter(user=request.user, challenge=challenge, completed_at__isnull=False)
    best = attempts.order_by("-percent", "created_at").first()
    can_attempt = attempts.count() < challenge.max_attempts
    return render(request, "core/challenge_detail.html", {
        "challenge": challenge,
        "best": best,
        "attempts": attempts[:10],
        "can_attempt": can_attempt,
        "remaining": max(0, challenge.max_attempts - attempts.count()),
    })


@login_required
@require_POST
def challenge_start(request, challenge_id):
    challenge = get_object_or_404(Challenge.objects.select_related("module"), id=challenge_id, published=True)
    if not user_can_access_module(request.user, challenge.module):
        raise Http404

    completed_count = QuizAttempt.objects.filter(user=request.user, challenge=challenge, completed_at__isnull=False).count()
    if completed_count >= challenge.max_attempts:
        messages.error(request, "Has utilizado todos los intentos disponibles para este reto.")
        return redirect("challenge_detail", challenge_id=challenge.id)

    pool = list(challenge.questions.filter(active=True, module=challenge.module).prefetch_related("options"))
    if not pool:
        messages.error(request, "Este reto todavía no tiene preguntas publicadas.")
        return redirect("challenge_detail", challenge_id=challenge.id)

    random.shuffle(pool)
    selected = pool[: min(challenge.question_count, len(pool))]
    attempt = QuizAttempt.objects.create(user=request.user, challenge=challenge)
    QuestionAttempt.objects.bulk_create([QuestionAttempt(attempt=attempt, question=q) for q in selected])
    return redirect("challenge_play", attempt_id=attempt.id)


@login_required
def challenge_play(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("challenge", "challenge__module", "challenge__module__course"),
        id=attempt_id,
        user=request.user,
    )
    if attempt.completed_at:
        return redirect("challenge_result", attempt_id=attempt.id)
    if not user_can_access_module(request.user, attempt.challenge.module):
        raise Http404

    rows = attempt.answers.select_related("question").prefetch_related("question__options").order_by("id")
    return render(request, "core/challenge_play.html", {"attempt": attempt, "rows": rows})


@login_required
@require_POST
@transaction.atomic
def challenge_submit(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_for_update().select_related("challenge", "challenge__module"),
        id=attempt_id,
        user=request.user,
    )
    if attempt.completed_at:
        return redirect("challenge_result", attempt_id=attempt.id)
    if not user_can_access_module(request.user, attempt.challenge.module):
        raise Http404

    score = 0
    max_score = 0
    for row in attempt.answers.select_related("question").prefetch_related("question__options"):
        question = row.question
        row.is_correct = False
        row.points_awarded = 0

        if question.question_type == "text":
            row.text_answer = (request.POST.get(f"q_{question.id}") or "").strip()
            row.save(update_fields=["text_answer", "is_correct", "points_awarded", "updated_at"])
            continue

        max_score += question.points
        option_id = request.POST.get(f"q_{question.id}")
        selected = question.options.filter(id=option_id).first() if option_id else None
        row.selected_option = selected
        if selected and selected.is_correct:
            row.is_correct = True
            row.points_awarded = question.points
            score += question.points
        row.save(update_fields=["selected_option", "is_correct", "points_awarded", "updated_at"])

    percent = round((score / max_score) * 100) if max_score else 0
    attempt.score = score
    attempt.max_score = max_score
    attempt.percent = percent
    attempt.passed = percent >= attempt.challenge.pass_percent
    attempt.xp_earned = attempt.challenge.xp_reward if attempt.passed else max(5, round(attempt.challenge.xp_reward * percent / 200))
    attempt.completed_at = timezone.now()
    attempt.save(update_fields=["score", "max_score", "percent", "passed", "xp_earned", "completed_at", "updated_at"])

    _award_badges(request.user, attempt)
    return redirect("challenge_result", attempt_id=attempt.id)


@login_required
def challenge_result(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("challenge", "challenge__module"),
        id=attempt_id,
        user=request.user,
        completed_at__isnull=False,
    )
    rows = attempt.answers.select_related("question", "selected_option").prefetch_related("question__options").order_by("id")
    earned_badges = StudentAchievement.objects.filter(
        user=request.user,
        awarded_at__gte=attempt.completed_at - timezone.timedelta(seconds=5),
    ).select_related("achievement")
    return render(request, "core/challenge_result.html", {
        "attempt": attempt,
        "rows": rows,
        "xp": _student_xp(request.user),
        "earned_badges": earned_badges,
    })
