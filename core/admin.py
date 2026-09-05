from django.contrib import admin
from .models import (
    StudentProfile, Course, Module, Lesson, Resource, Enrollment, LessonProgress,
    ModuleAccess, Purchase, SeatInvitation, ActivityLog, Challenge, Question,
    AnswerOption, QuizAttempt, QuestionAttempt, Achievement, StudentAchievement,
)

class ModuleInline(admin.TabularInline):
    model = Module; extra = 0

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title","active","stripe_price_id","created_at"); prepopulated_fields = {"slug":("title",)}; inlines = [ModuleInline]

class LessonInline(admin.TabularInline):
    model = Lesson; extra = 0

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title","course","position","published","stripe_price_id"); list_filter = ("course","published"); inlines = [LessonInline]

class ResourceInline(admin.TabularInline):
    model = Resource; extra = 0

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title","module","position","published","release_at","duration_minutes")
    list_filter = ("published","module__course","module"); search_fields = ("title","description"); inlines = [ResourceInline]

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user","phone","active","created_at"); list_filter = ("active",); search_fields = ("user__email","user__first_name","user__last_name")

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user","course","status","started_at","expires_at"); list_filter = ("status","course"); search_fields = ("user__email",)

@admin.register(ModuleAccess)
class ModuleAccessAdmin(admin.ModelAdmin):
    list_display = ("user","module","purchase","created_at"); list_filter = ("module__course","module"); search_fields = ("user__email",)

admin.site.register(Resource)
admin.site.register(LessonProgress)

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("buyer_email","scope","course","module","amount_cents","status","created_at")
    list_filter = ("scope","status","course"); search_fields = ("buyer_email","stripe_session_id")

class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 4

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("short_prompt", "module", "category", "question_type", "difficulty", "points", "active")
    list_filter = ("module__course", "module", "category", "question_type", "difficulty", "active")
    search_fields = ("prompt", "explanation", "model_answer")
    filter_horizontal = ("challenges",)
    inlines = [AnswerOptionInline]
    def short_prompt(self, obj): return obj.prompt[:70]
    short_prompt.short_description = "Pregunta"

@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "challenge_type", "position", "question_count", "pass_percent", "max_attempts", "xp_reward", "published")
    list_filter = ("module__course", "module", "challenge_type", "published")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "challenge", "percent", "passed", "xp_earned", "completed_at")
    list_filter = ("passed", "challenge__module", "challenge")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    readonly_fields = ("score", "max_score", "percent", "passed", "xp_earned", "completed_at")

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("icon", "name", "code", "xp_bonus", "active")
    list_filter = ("active",)
    search_fields = ("name", "code", "description")

@admin.register(StudentAchievement)
class StudentAchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "achievement", "awarded_at")
    search_fields = ("user__email", "achievement__name")

admin.site.register(QuestionAttempt)
admin.site.register(SeatInvitation)
admin.site.register(ActivityLog)
admin.site.site_header = "Xamox Academy · Administración"
admin.site.site_title = "Xamox Academy Admin"
admin.site.index_title = "Control del Campus"
