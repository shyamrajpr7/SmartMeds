"""Models for user profiles."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

BLOOD_GROUP_CHOICES = [
    ("", "Not specified"),
    ("A+", "A+"),
    ("A-", "A-"),
    ("B+", "B+"),
    ("B-", "B-"),
    ("AB+", "AB+"),
    ("AB-", "AB-"),
    ("O+", "O+"),
    ("O-", "O-"),
]

COMMON_TIMEZONES = [
    "Asia/Kolkata",
    "Asia/Dubai",
    "Asia/Singapore",
    "Asia/Tokyo",
    "Australia/Sydney",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "UTC",
]


class Profile(models.Model):
    """Medical profile attached to a Django user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    full_name = models.CharField(max_length=150, blank=True)
    age = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(120)],
    )
    blood_group = models.CharField(
        max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True
    )
    allergies = models.TextField(
        blank=True,
        help_text="One per line or comma separated, e.g. penicillin, peanuts.",
    )
    chronic_conditions = models.TextField(
        blank=True,
        help_text="Ongoing conditions, e.g. diabetes, hypertension.",
    )
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=30, blank=True)
    timezone = models.CharField(
        max_length=64,
        default="Asia/Kolkata",
        help_text="IANA time zone name used to display reminder times.",
    )
    phone_number = models.CharField(
        max_length=30,
        blank=True,
        help_text="WhatsApp number with country code, e.g. +919876543210",
    )
    whatsapp_alerts_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self) -> str:
        return self.full_name or self.user.get_username()

    def get_absolute_url(self) -> str:
        return reverse("accounts:profile")

    @property
    def is_complete(self) -> bool:
        """True when the fields a doctor needs are filled in."""
        return all(
            [
                self.full_name,
                self.age,
                self.blood_group,
                self.emergency_contact_name,
                self.emergency_contact_phone,
            ]
        )
