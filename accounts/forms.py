"""Forms for authentication and the patient profile."""

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import COMMON_TIMEZONES, Profile


class BootstrapFormMixin:
    """Adds Bootstrap 5 classes to every widget of a form."""

    def _apply_bootstrap(self) -> None:
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")
            if field.required:
                widget.attrs.setdefault("required", "required")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


class SignupForm(BootstrapFormMixin, UserCreationForm):
    """Create an account with a unique email address."""

    email = forms.EmailField(
        required=True, help_text="Used for password resets and reminders."
    )
    full_name = forms.CharField(
        max_length=150, required=False, label="Full name"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "full_name")

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.full_name = self.cleaned_data.get("full_name", "")
            profile.save(update_fields=["full_name"])
        return user


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    """Edit the medical profile."""

    class Meta:
        model = Profile
        fields = (
            "full_name",
            "age",
            "blood_group",
            "allergies",
            "chronic_conditions",
            "emergency_contact_name",
            "emergency_contact_phone",
            "timezone",
        )
        widgets = {
            "allergies": forms.Textarea(attrs={"rows": 3}),
            "chronic_conditions": forms.Textarea(attrs={"rows": 3}),
            "timezone": forms.TextInput(
                attrs={
                    "list": "timezone-options",
                    "placeholder": "Asia/Kolkata",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["timezone"].help_text = (
            "IANA time zone, e.g. Asia/Kolkata. "
            f"Common choices: {', '.join(COMMON_TIMEZONES[:6])}."
        )


class BootstrapAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    """Login form with Bootstrap styling."""

    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class StyledPasswordResetForm(BootstrapFormMixin, PasswordResetForm):
    """Password reset request form."""


class StyledSetPasswordForm(BootstrapFormMixin, SetPasswordForm):
    """New password form used after following a reset link."""
