from django.core.management.base import BaseCommand

from prescriptions.models import Medicine
from prescriptions.notifications import send_refill_alert


class Command(BaseCommand):
    help = "Send WhatsApp refill alerts for medicines running low"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Don't actually send")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        count = 0
        medicines = Medicine.objects.filter(
            refill_reminder_enabled=True,
            pills_remaining__isnull=False,
        ).select_related("prescription__user__profile")

        for med in medicines:
            if med.needs_refill:
                user = med.prescription.user
                if dry_run:
                    self.stdout.write(f"Would alert {user} for {med.name} ({med.pills_remaining} left)")
                    count += 1
                    continue
                if send_refill_alert(med, user):
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f"Sent alert to {user} for {med.name}"))
        self.stdout.write(f"Done. {count} alerts sent.")
