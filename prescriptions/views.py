"""Views for prescriptions vault."""

import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from accounts.models import Profile

from .forms import MedicineFormSet, PrescriptionForm
from .models import Medicine, Prescription, StoredMedia


class PrescriptionMediaView(LoginRequiredMixin, View):
    """Serve an uploaded prescription file to its owner."""

    def get(self, request, name):
        owner_prefix = f"prescriptions/{request.user.pk}/"
        if not (request.user.is_staff or name.startswith(owner_prefix)):
            raise Http404

        try:
            media = StoredMedia.objects.get(name=name)
        except StoredMedia.DoesNotExist as exc:
            raise Http404 from exc

        response = HttpResponse(
            bytes(media.data),
            content_type=media.content_type or "application/octet-stream",
        )
        response["Content-Disposition"] = (
            f'inline; filename="{os.path.basename(name)}"'
        )
        response["Cache-Control"] = "private, max-age=3600"
        return response


class PrescriptionListView(LoginRequiredMixin, ListView):
    model = Prescription
    template_name = "prescriptions/prescription_list.html"
    context_object_name = "prescriptions"
    paginate_by = 12

    def get_queryset(self):
        qs = Prescription.objects.filter(user=self.request.user).prefetch_related(
            "medicines"
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(doctor_name__icontains=q)
                | Q(hospital_clinic__icontains=q)
                | Q(medicines__name__icontains=q)
            ).distinct()
        doctor = self.request.GET.get("doctor", "").strip()
        if doctor:
            qs = qs.filter(doctor_name__iexact=doctor)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "").strip()
        context["doctor_filter"] = self.request.GET.get("doctor", "").strip()
        context["has_prescriptions"] = Prescription.objects.filter(
            user=self.request.user
        ).exists()
        doctors = (
            Prescription.objects.filter(user=self.request.user)
            .exclude(doctor_name="")
            .values_list("doctor_name", flat=True)
            .distinct()
            .order_by("doctor_name")
        )
        context["doctors"] = doctors
        return context


class PrescriptionTimelineView(LoginRequiredMixin, ListView):
    model = Prescription
    template_name = "prescriptions/prescription_timeline.html"
    context_object_name = "prescriptions"

    def get_queryset(self):
        return Prescription.objects.filter(user=self.request.user).prefetch_related(
            "medicines"
        )


class MedicineReminderListView(LoginRequiredMixin, View):
    """Return the signed-in user's daily medicine times as JSON."""

    def get(self, request):
        try:
            timezone = request.user.profile.timezone
        except Profile.DoesNotExist:
            timezone = settings.TIME_ZONE

        medicines = []
        prescriptions = Prescription.objects.filter(user=request.user).prefetch_related(
            "medicines"
        )
        for prescription in prescriptions:
            for medicine in prescription.medicines.all():
                if not medicine.time:
                    continue
                medicines.append(
                    {
                        "id": str(medicine.pk),
                        "name": medicine.name,
                        "dosage": medicine.dosage,
                        "time": medicine.time.strftime("%H:%M"),
                        "prescription_id": str(prescription.pk),
                        "doctor": prescription.doctor_name,
                    }
                )

        medicines.sort(
            key=lambda medicine: (medicine["time"], medicine["name"].lower())
        )
        response = JsonResponse(
            {
                "timezone": timezone or settings.TIME_ZONE,
                "medicines": medicines,
            }
        )
        response["Cache-Control"] = "no-store"
        return response


class RefillAlertsView(LoginRequiredMixin, ListView):
    model = Medicine
    template_name = "prescriptions/refill_alerts.html"
    context_object_name = "medicines"

    def get_queryset(self):
        return (
            Medicine.objects.filter(
                prescription__user=self.request.user,
                refill_reminder_enabled=True,
                pills_remaining__isnull=False,
            )
            .select_related("prescription")
            .order_by("pills_remaining", "name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        meds = context["medicines"]
        context["low_meds"] = [m for m in meds if m.needs_refill]
        context["all_meds"] = meds
        return context


class PrescriptionDetailView(LoginRequiredMixin, DetailView):
    model = Prescription
    template_name = "prescriptions/prescription_detail.html"
    context_object_name = "prescription"

    def get_queryset(self):
        return Prescription.objects.filter(user=self.request.user).prefetch_related(
            "medicines"
        )


class PrescriptionFormsetMixin:
    def save_formset(self, formset):
        formset.save()
        for index, medicine in enumerate(
            self.object.medicines.order_by("order", "id")
        ):
            if medicine.order != index:
                medicine.order = index
                medicine.save(update_fields=["order"])


class PrescriptionCreateView(LoginRequiredMixin, PrescriptionFormsetMixin, CreateView):
    model = Prescription
    form_class = PrescriptionForm
    template_name = "prescriptions/prescription_form.html"

    def get_success_url(self):
        return reverse_lazy(
            "prescriptions:detail", kwargs={"pk": self.object.pk}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = MedicineFormSet(self.request.POST)
        else:
            context["formset"] = MedicineFormSet()
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        context = self.get_context_data()
        formset = context["formset"]
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            self.save_formset(formset)
            messages.success(self.request, "Prescription added to your vault.")
            return redirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(form=form))


class PrescriptionUpdateView(LoginRequiredMixin, PrescriptionFormsetMixin, UpdateView):
    model = Prescription
    form_class = PrescriptionForm
    template_name = "prescriptions/prescription_form.html"

    def get_queryset(self):
        return Prescription.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy(
            "prescriptions:detail", kwargs={"pk": self.object.pk}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = MedicineFormSet(self.request.POST, instance=self.object)
        else:
            context["formset"] = MedicineFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            self.save_formset(formset)
            messages.success(self.request, "Prescription updated.")
            return redirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(form=form))


class PrescriptionDeleteView(LoginRequiredMixin, DeleteView):
    model = Prescription
    template_name = "prescriptions/prescription_confirm_delete.html"
    success_url = reverse_lazy("prescriptions:list")

    def get_queryset(self):
        return Prescription.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Prescription deleted.")
        return super().form_valid(form)
