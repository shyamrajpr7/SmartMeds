"""URL routes for prescriptions."""

from django.urls import path

from .views import (
    MedicineReminderListView,
    PrescriptionCreateView,
    PrescriptionDeleteView,
    PrescriptionDetailView,
    PrescriptionListView,
    PrescriptionTimelineView,
    PrescriptionUpdateView,
)

app_name = "prescriptions"

urlpatterns = [
    path("", PrescriptionListView.as_view(), name="list"),
    path("timeline/", PrescriptionTimelineView.as_view(), name="timeline"),
    path("add/", PrescriptionCreateView.as_view(), name="add"),
    path("reminders/", MedicineReminderListView.as_view(), name="reminders"),
    path("<str:pk>/", PrescriptionDetailView.as_view(), name="detail"),
    path("<str:pk>/edit/", PrescriptionUpdateView.as_view(), name="edit"),
    path("<str:pk>/delete/", PrescriptionDeleteView.as_view(), name="delete"),
]
