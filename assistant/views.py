"""HTTP views for the SmartMeds assistant."""

import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from .services import (
    MAX_MESSAGE_LENGTH,
    AssistantError,
    AssistantNotConfigured,
    AssistantRateLimited,
    run_assistant,
)

logger = logging.getLogger(__name__)


class AssistantChatView(LoginRequiredMixin, View):
    """Accept a chat message and return the assistant's reply."""

    http_method_names = ["post"]

    def post(self, request):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _error("Invalid request body.", status=400)

        if not isinstance(payload, dict):
            return _error("Invalid request body.", status=400)

        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            return _error("Please enter a message.", status=400)

        message = message.strip()
        if len(message) > MAX_MESSAGE_LENGTH:
            return _error(
                f"Messages must be {MAX_MESSAGE_LENGTH} characters or fewer.",
                status=400,
            )

        history = payload.get("history")
        try:
            result = run_assistant(request.user, message, history)
        except AssistantNotConfigured as exc:
            return _error(str(exc), status=503)
        except AssistantRateLimited as exc:
            return _error(str(exc), status=429)
        except AssistantError as exc:
            return _error(str(exc), status=502)
        except Exception:
            logger.exception("Unexpected assistant error")
            return _error(
                "Something went wrong while contacting the assistant. Please try again.",
                status=500,
            )

        return JsonResponse(result, headers={"Cache-Control": "no-store"})


def _error(message: str, status: int) -> JsonResponse:
    return JsonResponse(
        {"error": message},
        status=status,
        headers={"Cache-Control": "no-store"},
    )
