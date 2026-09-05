from django.contrib import admin
from .models import StudentProfile, Course, Module, Lesson, Resource, Enrollment, LessonProgress, ModuleAccess, Purchase, SeatInvitation, ActivityLog

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
admin.site.register(SeatInvitation)
admin.site.register(ActivityLog)
admin.site.site_header = "Xamox Academy · Administración"
admin.site.site_title = "Xamox Academy Admin"
admin.site.index_title = "Control del Campus"
