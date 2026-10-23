"""Admin configuration for accounts."""

from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "blood_group", "age", "timezone")
    list_filter = ("blood_group", "timezone")
    search_fields = ("user__username", "user__email", "full_name")
    autocomplete_fields = ()
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("user", "full_name", "age", "blood_group")}),
        ("Medical", {"fields": ("allergies", "chronic_conditions")}),
        (
            "Emergency contact",
            {"fields": ("emergency_contact_name", "emergency_contact_phone")},
        ),
        ("Preferences", {"fields": ("timezone",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
