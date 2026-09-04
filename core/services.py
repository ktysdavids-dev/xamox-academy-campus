from .models import Lesson, LessonProgress

def course_progress(user, course):
    lessons = Lesson.objects.filter(module__course=course, published=True)
    total = lessons.count()
    if total == 0: return 0
    completed = LessonProgress.objects.filter(user=user, lesson__in=lessons, completed=True).count()
    return round((completed / total) * 100)
