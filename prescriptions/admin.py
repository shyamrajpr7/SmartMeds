"""Admin for prescriptions."""

from django.contrib import admin

from .models import Medicine, Prescription


class MedicineInline(admin.TabularInline):
    model = Medicine
    extra = 1


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "doctor_name", "date_issued", "hospital_clinic", "created_at")
    list_filter = ("date_issued", "doctor_name")
    search_fields = ("user__username", "doctor_name", "hospital_clinic", "notes")
    readonly_fields = ("created_at", "updated_at")
    inlines = [MedicineInline]


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ("name", "prescription", "dosage", "frequency", "duration")
    search_fields = ("name", "prescription__doctor_name")
