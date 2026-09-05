from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import AnswerOption, Challenge, Course, Enrollment, Module, Question, QuizAttempt


class XamoxChallengeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", email="student@example.com", password="test-pass-123")
        self.course = Course.objects.create(title="IA & Marketing Digital", slug="ia-marketing-digital", active=True)
        self.module = Module.objects.create(course=self.course, title="Fundamentos de IA", position=1, published=True)
        Enrollment.objects.create(user=self.user, course=self.course, status="active")
        self.challenge = Challenge.objects.create(
            module=self.module, title="Examen M1", slug="examen-m1", challenge_type="exam",
            question_count=1, pass_percent=70, max_attempts=3, xp_reward=100, published=True,
        )
        self.question = Question.objects.create(
            module=self.module, category="Fundamentos", question_type="single",
            prompt="¿Qué describe mejor un LLM?", explanation="Predice secuencias.", points=10, active=True,
        )
        self.correct = AnswerOption.objects.create(question=self.question, text="Predice secuencias", is_correct=True, position=1)
        AnswerOption.objects.create(question=self.question, text="Es una base de datos", is_correct=False, position=2)
        self.question.challenges.add(self.challenge)
        self.client.login(username="student", password="test-pass-123")

    def test_hub_is_available_for_enrolled_student(self):
        response = self.client.get(reverse("challenge_hub"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Examen M1")

    def test_passing_attempt_scores_and_awards_xp(self):
        response = self.client.post(reverse("challenge_start", args=[self.challenge.id]))
        self.assertEqual(response.status_code, 302)
        attempt = QuizAttempt.objects.get(user=self.user, challenge=self.challenge)
        response = self.client.post(reverse("challenge_submit", args=[attempt.id]), {f"q_{self.question.id}": str(self.correct.id)})
        self.assertEqual(response.status_code, 302)
        attempt.refresh_from_db()
        self.assertTrue(attempt.passed)
        self.assertEqual(attempt.percent, 100)
        self.assertEqual(attempt.xp_earned, 100)

    def test_attempt_limit_is_enforced(self):
        for _ in range(3):
            QuizAttempt.objects.create(user=self.user, challenge=self.challenge, completed_at="2026-09-05T12:00:00Z")
        response = self.client.post(reverse("challenge_start", args=[self.challenge.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(QuizAttempt.objects.filter(user=self.user, challenge=self.challenge).count(), 3)
