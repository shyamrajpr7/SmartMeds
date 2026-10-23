"""Forms for prescriptions and medicines."""

from django import forms
from django.forms import inlineformset_factory

from .models import Medicine, Prescription


class BootstrapFormMixin:
    def _apply_bootstrap(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            elif isinstance(widget, forms.FileInput):
                widget.attrs.setdefault("class", "form-control")
            else:
                widget.attrs.setdefault("class", "form-control")
            if field.required:
                widget.attrs.setdefault("required", "required")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


class PrescriptionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ("doctor_name", "hospital_clinic", "date_issued", "notes", "file")
        widgets = {
            "date_issued": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class MedicineForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ("name", "dosage", "frequency", "duration", "instructions", "order")
        widgets = {
            "instructions": forms.Textarea(attrs={"rows": 2}),
            "order": forms.HiddenInput(),
        }


MedicineFormSet = inlineformset_factory(
    Prescription,
    Medicine,
    form=MedicineForm,
    extra=2,
    can_delete=True,
    min_num=0,
    validate_min=False,
)
