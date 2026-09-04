from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("activar/<uidb64>/<token>/", views.activate_account, name="activate_account"),
    path("post-compra/", views.post_purchase, name="post_purchase"),
    path("invitacion/<token>/", views.accept_invitation, name="accept_invitation"),
    path("campus/", views.dashboard, name="dashboard"),
    path("campus/invitar/", views.invite_seat, name="invite_seat"),
    path("campus/curso/<slug:slug>/", views.course_detail, name="course_detail"),
    path("campus/clase/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),
    path("campus/clase/<int:lesson_id>/completar/", views.complete_lesson, name="complete_lesson"),
    path("media/<path:path>", views.protected_media, name="protected_media"),
    path("comprar/", views.buy_redirect, name="buy_redirect"),
    path("webhooks/stripe/", views.stripe_webhook, name="stripe_webhook"),
    path("admin-panel/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-panel/alumnos/", views.admin_students, name="admin_students"),
    path("admin-panel/alumnos/nuevo/", views.admin_student_create, name="admin_student_create"),
    path("admin-panel/alumnos/<int:user_id>/", views.admin_student_detail, name="admin_student_detail"),
    path("admin-panel/alumnos/<int:user_id>/matricular/", views.admin_enroll_student, name="admin_enroll_student"),
]
