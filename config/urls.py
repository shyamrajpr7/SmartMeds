"""URL configuration for SmartMeds."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts.views import DashboardView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", DashboardView.as_view(), name="dashboard"),
    path("accounts/", include("accounts.urls")),
    path("prescriptions/", include("prescriptions.urls")),
    path("assistant/", include("assistant.urls")),
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
