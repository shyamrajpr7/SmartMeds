"""URL configuration for SmartMeds."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts.views import DashboardView

from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from accounts.forms import StyledPasswordResetForm, StyledSetPasswordForm

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", DashboardView.as_view(), name="dashboard"),
    path("accounts/", include("accounts.urls")),
    path("prescriptions/", include("prescriptions.urls")),
    path("assistant/", include("assistant.urls")),
    # Password reset (non-namespaced for Django's default URL resolution)
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/password_reset_email.txt",
            subject_template_name="accounts/password_reset_subject.txt",
            form_class=StyledPasswordResetForm,
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            form_class=StyledSetPasswordForm,
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


from django.views.generic import TemplateView

urlpatterns += [
    path("privacy-policy/", TemplateView.as_view(template_name="pages/privacy_policy.html"), name="privacy_policy"),
    path("cookie-policy/", TemplateView.as_view(template_name="pages/cookie_policy.html"), name="cookie_policy"),
    path("terms/", TemplateView.as_view(template_name="pages/terms_of_service.html"), name="terms_of_service"),
    path("terms-of-service/", TemplateView.as_view(template_name="pages/terms_of_service.html"), name="terms"),
    path("about/", TemplateView.as_view(template_name="pages/about_us.html"), name="about_us"),
    path("about-us/", TemplateView.as_view(template_name="pages/about_us.html"), name="about"),
    path("pricing/", TemplateView.as_view(template_name="pages/pricing.html"), name="pricing"),
    path("contact/", TemplateView.as_view(template_name="pages/contact.html"), name="contact"),
    path("support/", TemplateView.as_view(template_name="pages/contact.html"), name="support"),
    path("faq/", TemplateView.as_view(template_name="pages/faq.html"), name="faq"),
    path("help/", TemplateView.as_view(template_name="pages/faq.html"), name="help_center"),
]
