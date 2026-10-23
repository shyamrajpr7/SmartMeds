"""Views for prescriptions vault."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import MedicineFormSet, PrescriptionForm
from .models import Prescription


class PrescriptionListView(LoginRequiredMixin, ListView):
    model = Prescription
    template_name = "prescriptions/prescription_list.html"
    context_object_name = "prescriptions"
    paginate_by = 12

    def get_queryset(self):
        qs = Prescription.objects.filter(user=self.request.user).prefetch_related(
            "medicines"
        )
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(doctor_name__icontains=q)
                | Q(hospital_clinic__icontains=q)
                | Q(medicines__name__icontains=q)
            ).distinct()
        doctor = self.request.GET.get("doctor")
        if doctor:
            qs = qs.filter(doctor_name__iexact=doctor)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        context["doctor_filter"] = self.request.GET.get("doctor", "")
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
