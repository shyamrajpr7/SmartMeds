"""WhatsApp and notification helpers for refill alerts."""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send_whatsapp_message(to_number, body):
    """Send a WhatsApp message via Twilio if configured."""
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
    auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
    from_number = getattr(settings, "TWILIO_WHATSAPP_FROM", "")

    if not (account_sid and auth_token and to_number):
        logger.debug("WhatsApp not configured or missing recipient")
        return False

    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=f"whatsapp:{to_number.lstrip('+').replace('whatsapp:', '') if not to_number.startswith('whatsapp:') else to_number}" if False else _format_to(to_number, from_number),
        )
        logger.info("WhatsApp message sent: %s", message.sid)
        return True
    except Exception as exc:
        logger.exception("Failed to send WhatsApp message: %s", exc)
        return False


def _format_to(to_number, from_number):
    # Normalize
    num = str(to_number).strip()
    if num.startswith("whatsapp:"):
        return num
    if num.startswith("+"):
        return f"whatsapp:{num}"
    # If no plus, assume needs plus? but better just pass as is if user added +
    return f"whatsapp:{num}"


def send_refill_alert(medicine, user):
    profile = getattr(user, "profile", None)
    if not profile or not profile.whatsapp_alerts_enabled:
        return False
    phone = profile.phone_number or profile.emergency_contact_phone
    if not phone:
        return False

    body = (
        f"💊 SmartMeds Refill Alert\n\n"
        f"Medicine: {medicine.name}\n"
        f"Dosage: {medicine.dosage or 'N/A'}\n"
        f"Pills remaining: {medicine.pills_remaining}\n"
        f"Refill when ≤ {medicine.refill_threshold}\n\n"
        f"Please refill your prescription soon."
    )
    return send_whatsapp_message(phone, body)
