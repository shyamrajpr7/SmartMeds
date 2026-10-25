"""Models for prescriptions and medicines."""

import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def prescription_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"prescriptions/{instance.user_id}/{uuid.uuid4().hex}{ext}"


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
FILE_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf"}


def _validate_file(file, allowed_ext, allowed_label):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed_ext:
        raise ValidationError(f"Only {allowed_label} files are allowed.")
    if getattr(file, "_committed", False):
        return
    max_size_mb = getattr(settings, "MAX_UPLOAD_SIZE_MB", 10)
    try:
        size = file.size
    except (FileNotFoundError, OSError):
        return
    if size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"File too large. Max size is {max_size_mb} MB.")


def validate_prescription_file(file):
    _validate_file(file, FILE_EXTENSIONS, "JPG, PNG, WebP, or PDF")


def validate_prescription_image(file):
    _validate_file(file, IMAGE_EXTENSIONS, "JPG, PNG, or WebP")


class Prescription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="prescriptions"
    )
    doctor_name = models.CharField(max_length=150, blank=True)
    hospital_clinic = models.CharField(max_length=150, blank=True)
    date_issued = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    file = models.FileField(
        upload_to=prescription_upload_path,
        blank=True,
        null=True,
        validators=[validate_prescription_file],
    )
    image = models.FileField(
        upload_to=prescription_upload_path,
        blank=True,
        null=True,
        validators=[validate_prescription_image],
        help_text="Optional JPG, PNG, or WebP image of the prescription.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_issued", "-created_at"]

    def __str__(self):
        label = self.doctor_name or "Prescription"
        if self.date_issued:
            return f"{label} ({self.date_issued})"
        return label

    @property
    def file_is_image(self):
        if not self.file:
            return False
        ext = os.path.splitext(self.file.name)[1].lower()
        return ext in IMAGE_EXTENSIONS

    @property
    def file_is_pdf(self):
        if not self.file:
            return False
        return os.path.splitext(self.file.name)[1].lower() == ".pdf"

    def _attachment_available(self, field):
        if not field:
            return False
        try:
            return field.storage.exists(field.name)
        except Exception:
            return False

    @property
    def file_available(self):
        return self._attachment_available(self.file)

    @property
    def image_available(self):
        return self._attachment_available(self.image)


class StoredMedia(models.Model):
    """An uploaded file kept in the database for durable, portable storage."""

    name = models.CharField(max_length=255, unique=True)
    content_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveIntegerField(default=0)
    data = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "stored media"

    def __str__(self) -> str:
        return self.name


class Medicine(models.Model):
    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name="medicines"
    )
    name = models.CharField(max_length=150)
    dosage = models.CharField(max_length=100, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    time = models.TimeField(null=True, blank=True, help_text="Time of day to take this medicine.")
    instructions = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    quantity = models.PositiveIntegerField(null=True, blank=True, help_text="Total quantity prescribed.")
    pills_remaining = models.PositiveIntegerField(null=True, blank=True, help_text="Pills left to take.")
    refill_threshold = models.PositiveIntegerField(default=5, help_text="Alert when pills remaining fall to or below this number.")
    refill_reminder_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name

    @property
    def needs_refill(self):
        if self.pills_remaining is None or self.refill_threshold is None:
            return False
        return self.pills_remaining <= self.refill_threshold

    @property
    def days_remaining(self):
        if self.pills_remaining is None:
            return None
        # Try to estimate based on frequency - simple heuristic
        return self.pills_remaining
