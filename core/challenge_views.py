import random
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Max, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Achievement, Challenge, Module, QuestionAttempt, QuizAttempt, StudentAchievement
from .services import user_can_access_module


MODE_META = {
    "quiz": {"label": "Radar IA", "icon": "🧠", "description": "Preguntas de precisión para consolidar conceptos."},
    "roulette": {"label": "Ruleta Xamox", "icon": "🎡", "description": "La categoría cambia en cada giro: adapta tu criterio."},
    "speed": {"label": "Reto Relámpago", "icon": "⚡", "description": "Decide rápido sin sacrificar calidad."},
    "lab": {"label": "Laboratorio", "icon": "🧪", "description": "Resuelve casos reales y compara con una solución profesional."},
    "exam": {"label": "Boss Final", "icon": "🏆", "description": "Evaluación final sin pistas ni feedback hasta terminar."},
}


def _can_access(user, module):
    """El staff puede previsualizar; un alumno solo juega módulos que posee."""
    return user.is_staff or user_can_access_module(user, module)


def _game_mode(challenge):
    slug = (challenge.slug or "").lower()
    if challenge.challenge_type == "exam" or slug.endswith("-examen") or "examen" in slug:
        return "exam"
    if "ruleta" in slug:
        return "roulette"
    if "relampago" in slug or "rápido" in slug or "rapido" in slug:
        return "speed"
    if "-lab" in slug or "laboratorio" in slug:
        return "lab"
    return "quiz"


def _decorate_challenge(challenge):
    mode = _game_mode(challenge)
    challenge.game_mode = mode
    challenge.game_label = MODE_META[mode]["label"]
    challenge.game_icon = MODE_META[mode]["icon"]
    challenge.game_description = MODE_META[mode]["description"]
    return challenge


def _student_xp(user):
    quiz_xp = user.challenge_attempts.filter(completed_at__isnull=False).aggregate(total=Sum("xp_earned"))["total"] or 0
    badge_xp = StudentAchievement.objects.filter(user=user).aggregate(total=Sum("achievement__xp_bonus"))["total"] or 0
    return quiz_xp + badge_xp


def _best_attempt(user, challenge):
    return QuizAttempt.objects.filter(user=user, challenge=challenge, completed_at__isnull=False).order_by("-percent", "created_at").first()


def _display_name(row):
    first = (row.get("user__first_name") or "").strip()
    last = (row.get("user__last_name") or "").strip()
    username = (row.get("user__username") or "Alumno").strip()
    if first and last:
        return f"{first} {last[:1]}."
    return first or username.split("@")[0]


def _leaderboard(module=None, challenge=None, since=None, limit=20):
    qs = QuizAttempt.objects.filter(completed_at__isnull=False, user__is_staff=False)
    if module is not None:
        qs = qs.filter(challenge__module=module)
    if challenge is not None:
        qs = qs.filter(challenge=challenge)
    if since is not None:
        qs = qs.filter(completed_at__gte=since)

    if challenge is not None:
        rows = list(
            qs.values("user_id", "user__first_name", "user__last_name", "user__username")
            .annotate(xp=Sum("xp_earned"), wins=Count("id", filter=Q(passed=True)), best=Max("percent"))
            .order_by("-best", "-xp", "user_id")[:limit]
        )
    else:
        rows = list(
            qs.values("user_id", "user__first_name", "user__last_name", "user__username")
            .annotate(xp=Sum("xp_earned"), wins=Count("id", filter=Q(passed=True)))
            .order_by("-xp", "-wins", "user_id")[:limit]
        )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
        row["display_name"] = _display_name(row)
    return rows


def _my_rank(user):
    rows = list(
        QuizAttempt.objects.filter(completed_at__isnull=False, user__is_staff=False)
        .values("user_id")
        .annotate(xp=Sum("xp_earned"), wins=Count("id", filter=Q(passed=True)))
        .order_by("-xp", "-wins", "user_id")
    )
    for index, row in enumerate(rows, start=1):
        if row["user_id"] == user.id:
            return index
    return None


def _award_badges(user, attempt):
    awarded = []
    mode = _game_mode(attempt.challenge)

    def grant(code, name, description, icon, xp_bonus):
        badge, _ = Achievement.objects.get_or_create(
            code=code,
            defaults={"name": name, "description": description, "icon": icon, "xp_bonus": xp_bonus},
        )
        item, created = StudentAchievement.objects.get_or_create(user=user, achievement=badge)
        if created:
            awarded.append(item)

    if attempt.passed:
        grant("primer-reto", "Primer reto", "Has superado tu primer juego de Xamox Arena.", "🎯", 20)
        if mode == "roulette":
            grant("maestro-ruleta", "Maestro de la Ruleta", "Has dominado una Ruleta Xamox.", "🎡", 20)
        elif mode == "speed":
            grant("mente-rapida", "Mente Rápida", "Has superado un Reto Relámpago.", "⚡", 25)
        elif mode == "lab":
            grant("constructor-ia", "Constructor IA", "Has completado un caso práctico del Laboratorio.", "🧪", 30)

    if attempt.passed and mode == "exam":
        grant(
            f"modulo-{attempt.challenge.module.position}-master",
            f"Módulo {attempt.challenge.module.position} Master",
            f"Has superado el Boss Final de {attempt.challenge.module.title}.",
            "🏆",
            50,
        )

    # Insignias de progresión global. El XP de la insignia se suma después de comprobar el umbral.
    xp_now = _student_xp(user)
    if xp_now >= 500:
        grant("liga-500", "Liga 500", "Has alcanzado 500 Xamox Points.", "🔥", 25)
    if xp_now >= 1000:
        grant("liga-1000", "Liga 1000", "Has alcanzado 1.000 Xamox Points.", "💎", 50)
    return awarded


def _row_answered(row):
    return bool(row.selected_option_id or (row.text_answer or "").strip())


def _finalize_attempt(attempt):
    if attempt.completed_at:
        return attempt
    rows = list(attempt.answers.select_related("question"))
    if not rows or any(not _row_answered(row) for row in rows):
        return attempt

    score = sum(row.points_awarded for row in rows)
    max_score = sum(row.question.points for row in rows)
    percent = round((score / max_score) * 100) if max_score else 0
    passed = percent >= attempt.challenge.pass_percent
    reward = attempt.challenge.xp_reward if passed else max(5, round(attempt.challenge.xp_reward * percent / 200))

    # El modo Relámpago premia resolver rápido, pero nunca cambia la nota académica.
    mode = _game_mode(attempt.challenge)
    elapsed = max(1, round((timezone.now() - attempt.created_at).total_seconds()))
    if mode == "speed" and passed:
        target = max(1, len(rows) * 25)
        if elapsed <= round(target * 0.70):
            reward += round(attempt.challenge.xp_reward * 0.25)
        elif elapsed <= target:
            reward += round(attempt.challenge.xp_reward * 0.10)

    attempt.score = score
    attempt.max_score = max_score
    attempt.percent = percent
    attempt.passed = passed
    attempt.xp_earned = reward
    attempt.completed_at = timezone.now()
    attempt.save(update_fields=["score", "max_score", "percent", "passed", "xp_earned", "completed_at", "updated_at"])
    _award_badges(attempt.user, attempt)
    return attempt


@login_required
def challenge_hub(request):
    modules = Module.objects.filter(published=True, challenges__published=True).select_related("course").distinct().order_by("course_id", "position")
    allowed = []
    all_challenges = []
    for module in modules:
        if not _can_access(request.user, module):
            continue
        challenges = list(module.challenges.filter(published=True).order_by("position", "id"))
        for challenge in challenges:
            _decorate_challenge(challenge)
            challenge.best = _best_attempt(request.user, challenge)
            challenge.attempt_count = QuizAttempt.objects.filter(user=request.user, challenge=challenge, completed_at__isnull=False).count()
            challenge.remaining = max(0, challenge.max_attempts - challenge.attempt_count)
            all_challenges.append(challenge)
        module.challenge_list = challenges
        module.module_xp = (
            QuizAttempt.objects.filter(user=request.user, challenge__module=module, completed_at__isnull=False)
            .aggregate(total=Sum("xp_earned"))["total"] or 0
        )
        allowed.append(module)

    daily = None
    if all_challenges:
        daily = all_challenges[timezone.localdate().toordinal() % len(all_challenges)]

    badges = StudentAchievement.objects.filter(user=request.user).select_related("achievement").order_by("-awarded_at")
    weekly_since = timezone.now() - timedelta(days=7)
    return render(request, "core/challenge_hub.html", {
        "modules": allowed,
        "xp": _student_xp(request.user),
        "badges": badges,
        "daily": daily,
        "leaderboard": _leaderboard(limit=8),
        "weekly_leaderboard": _leaderboard(since=weekly_since, limit=5),
        "my_rank": _my_rank(request.user),
    })


@login_required
def challenge_leaderboard(request):
    weekly_since = timezone.now() - timedelta(days=7)
    return render(request, "core/challenge_leaderboard.html", {
        "leaderboard": _leaderboard(limit=50),
        "weekly_leaderboard": _leaderboard(since=weekly_since, limit=20),
        "my_rank": _my_rank(request.user),
        "xp": _student_xp(request.user),
    })


@login_required
def challenge_detail(request, challenge_id):
    challenge = get_object_or_404(Challenge.objects.select_related("module", "module__course"), id=challenge_id, published=True)
    if not _can_access(request.user, challenge.module):
        raise Http404
    _decorate_challenge(challenge)
    attempts = QuizAttempt.objects.filter(user=request.user, challenge=challenge, completed_at__isnull=False)
    best = attempts.order_by("-percent", "created_at").first()
    active_attempt = QuizAttempt.objects.filter(user=request.user, challenge=challenge, completed_at__isnull=True).order_by("-created_at").first()
    can_attempt = bool(active_attempt) or attempts.count() < challenge.max_attempts
    return render(request, "core/challenge_detail.html", {
        "challenge": challenge,
        "best": best,
        "attempts": attempts[:10],
        "can_attempt": can_attempt,
        "active_attempt": active_attempt,
        "remaining": max(0, challenge.max_attempts - attempts.count()),
        "top_players": _leaderboard(challenge=challenge, limit=8),
    })


@login_required
@require_POST
def challenge_start(request, challenge_id):
    challenge = get_object_or_404(Challenge.objects.select_related("module"), id=challenge_id, published=True)
    if not _can_access(request.user, challenge.module):
        raise Http404

    active = QuizAttempt.objects.filter(user=request.user, challenge=challenge, completed_at__isnull=True).order_by("-created_at").first()
    if active:
        return redirect("challenge_play", attempt_id=active.id)

    completed_count = QuizAttempt.objects.filter(user=request.user, challenge=challenge, completed_at__isnull=False).count()
    if completed_count >= challenge.max_attempts:
        messages.error(request, "Has utilizado todos los intentos disponibles para este juego.")
        return redirect("challenge_detail", challenge_id=challenge.id)

    mode = _game_mode(challenge)
    pool_qs = challenge.questions.filter(active=True, module=challenge.module).prefetch_related("options")
    if mode == "lab":
        pool_qs = pool_qs.filter(question_type="text")
    else:
        pool_qs = pool_qs.exclude(question_type="text")
    pool = list(pool_qs)
    if not pool:
        messages.error(request, "Este juego todavía no tiene ejercicios publicados.")
        return redirect("challenge_detail", challenge_id=challenge.id)

    random.shuffle(pool)
    selected = pool[: min(challenge.question_count, len(pool))]
    attempt = QuizAttempt.objects.create(user=request.user, challenge=challenge)
    QuestionAttempt.objects.bulk_create([QuestionAttempt(attempt=attempt, question=q) for q in selected])
    return redirect("challenge_play", attempt_id=attempt.id)


@login_required
def challenge_play(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("challenge", "challenge__module", "challenge__module__course"), id=attempt_id, user=request.user,
    )
    if not _can_access(request.user, attempt.challenge.module):
        raise Http404
    if attempt.completed_at:
        return redirect("challenge_result", attempt_id=attempt.id)

    _decorate_challenge(attempt.challenge)
    rows = list(attempt.answers.select_related("question").prefetch_related("question__options").order_by("id"))
    pending = [row for row in rows if not _row_answered(row)]
    if not pending:
        _finalize_attempt(attempt)
        return redirect("challenge_result", attempt_id=attempt.id)

    current = pending[0]
    answered_count = len(rows) - len(pending)
    progress = round((answered_count / len(rows)) * 100) if rows else 0
    return render(request, "core/challenge_play.html", {
        "attempt": attempt,
        "row": current,
        "question_number": answered_count + 1,
        "total_questions": len(rows),
        "progress": progress,
        "seconds": 25 if attempt.challenge.game_mode == "speed" else 0,
    })


def _save_row_answer(row, post_data):
    question = row.question
    row.is_correct = False
    row.points_awarded = 0

    if question.question_type == "text":
        text = (post_data.get("answer") or "").strip()
        if not text:
            return False, "Escribe una respuesta antes de continuar."
        row.text_answer = text
        # Los laboratorios no fingen una corrección automática: se premia completar el caso
        # y la solución profesional aparece inmediatamente después para autoevaluación.
        row.points_awarded = question.points
        row.save(update_fields=["text_answer", "is_correct", "points_awarded", "updated_at"])
        return True, None

    option_id = post_data.get("answer")
    timed_out = post_data.get("timed_out") == "1"
    if not option_id:
        if timed_out:
            row.text_answer = "__TIMEOUT__"
            row.save(update_fields=["text_answer", "is_correct", "points_awarded", "updated_at"])
            return True, None
        return False, "Selecciona una respuesta antes de continuar."

    selected = question.options.filter(id=option_id).first()
    if selected is None:
        return False, "La opción seleccionada no es válida."
    row.selected_option = selected
    if selected.is_correct:
        row.is_correct = True
        row.points_awarded = question.points
    row.save(update_fields=["selected_option", "is_correct", "points_awarded", "updated_at"])
    return True, None


@login_required
@require_POST
@transaction.atomic
def challenge_answer(request, attempt_id, row_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_for_update().select_related("challenge", "challenge__module"), id=attempt_id, user=request.user,
    )
    if attempt.completed_at:
        return redirect("challenge_result", attempt_id=attempt.id)
    if not _can_access(request.user, attempt.challenge.module):
        raise Http404

    row = get_object_or_404(
        QuestionAttempt.objects.select_for_update().select_related("question", "attempt"), id=row_id, attempt=attempt,
    )
    if _row_answered(row):
        return redirect("challenge_play", attempt_id=attempt.id)

    ok, error = _save_row_answer(row, request.POST)
    if not ok:
        messages.error(request, error)
        return redirect("challenge_play", attempt_id=attempt.id)

    mode = _game_mode(attempt.challenge)
    if mode == "exam":
        remaining = attempt.answers.filter(selected_option__isnull=True, text_answer="").exists()
        if not remaining:
            _finalize_attempt(attempt)
            return redirect("challenge_result", attempt_id=attempt.id)
        return redirect("challenge_play", attempt_id=attempt.id)

    return redirect("challenge_feedback", attempt_id=attempt.id, row_id=row.id)


@login_required
def challenge_feedback(request, attempt_id, row_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("challenge", "challenge__module"), id=attempt_id, user=request.user,
    )
    if not _can_access(request.user, attempt.challenge.module):
        raise Http404
    if _game_mode(attempt.challenge) == "exam":
        raise Http404
    row = get_object_or_404(
        QuestionAttempt.objects.select_related("question", "selected_option").prefetch_related("question__options"), id=row_id, attempt=attempt,
    )
    if not _row_answered(row):
        return redirect("challenge_play", attempt_id=attempt.id)

    all_rows = list(attempt.answers.order_by("id"))
    completed = sum(1 for item in all_rows if _row_answered(item))
    is_last = completed >= len(all_rows)
    if is_last:
        _finalize_attempt(attempt)
    _decorate_challenge(attempt.challenge)
    return render(request, "core/challenge_feedback.html", {
        "attempt": attempt,
        "row": row,
        "is_last": is_last,
        "progress": round((completed / len(all_rows)) * 100) if all_rows else 100,
    })


# Compatibilidad con la V1 y con tests antiguos: acepta un formulario con todas
# las preguntas a la vez y lo transforma en respuestas de la nueva Arena.
@login_required
@require_POST
@transaction.atomic
def challenge_submit(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_for_update().select_related("challenge", "challenge__module"), id=attempt_id, user=request.user,
    )
    if attempt.completed_at:
        return redirect("challenge_result", attempt_id=attempt.id)
    if not _can_access(request.user, attempt.challenge.module):
        raise Http404

    for row in attempt.answers.select_related("question").prefetch_related("question__options"):
        if _row_answered(row):
            continue
        question = row.question
        legacy_value = request.POST.get(f"q_{question.id}")
        if question.question_type == "text":
            payload = request.POST.copy()
            payload["answer"] = legacy_value or ""
        else:
            payload = request.POST.copy()
            payload["answer"] = legacy_value or ""
            if not legacy_value:
                payload["timed_out"] = "1"
        _save_row_answer(row, payload)

    _finalize_attempt(attempt)
    if attempt.completed_at:
        return redirect("challenge_result", attempt_id=attempt.id)
    return redirect("challenge_play", attempt_id=attempt.id)


@login_required
def challenge_result(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("challenge", "challenge__module"), id=attempt_id, user=request.user, completed_at__isnull=False,
    )
    if not _can_access(request.user, attempt.challenge.module):
        raise Http404
    _decorate_challenge(attempt.challenge)
    rows = attempt.answers.select_related("question", "selected_option").prefetch_related("question__options").order_by("id")
    earned_badges = StudentAchievement.objects.filter(
        user=request.user,
        awarded_at__gte=attempt.completed_at - timedelta(seconds=5),
    ).select_related("achievement")
    elapsed = max(1, round((attempt.completed_at - attempt.created_at).total_seconds()))
    return render(request, "core/challenge_result.html", {
        "attempt": attempt,
        "rows": rows,
        "xp": _student_xp(request.user),
        "earned_badges": earned_badges,
        "elapsed": elapsed,
        "top_players": _leaderboard(challenge=attempt.challenge, limit=5),
    })
