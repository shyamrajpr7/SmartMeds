"""Views for authentication and the patient profile."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, UpdateView

from prescriptions.models import Medicine, Prescription

from .forms import ProfileForm, SignupForm
from .models import Profile


class DashboardView(LoginRequiredMixin, TemplateView):
    """Landing page after login. Extended by later apps."""

    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        prescriptions = Prescription.objects.filter(user=self.request.user)
        context["profile"] = profile
        context["prescription_count"] = prescriptions.count()
        context["medicine_count"] = Medicine.objects.filter(
            prescription__user=self.request.user
        ).count()
        context["recent_prescriptions"] = list(
            prescriptions.prefetch_related("medicines")[:5]
        )
        return context


class SignupView(CreateView):
    """Register a new account and log the user straight in."""

    form_class = SignupForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(
            self.request,
            "Welcome to SmartMeds! Complete your profile to get the most out of it.",
        )
        return response


class ProfileUpdateView(
    LoginRequiredMixin, SuccessMessageMixin, UpdateView
):
    """Edit the profile of the signed-in user only."""

    model = Profile
    form_class = ProfileForm
    template_name = "accounts/profile_form.html"
    success_url = reverse_lazy("accounts:profile")
    success_message = "Your profile has been updated."

    def get_object(self, queryset=None) -> Profile:
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile
