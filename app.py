"""
Vercel entry point for SmartMeds.

The Django web application is served at the root of the domain while the
FastAPI JSON API stays available under ``/api`` (plus ``/health`` and
``/docs``). Both are ASGI applications, so a small dispatcher is enough.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from smartmeds.api.app import app as api_app  # noqa: E402

_django_app = None

_API_PATHS = {
    "/api",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def _get_django_app():
    global _django_app
    if _django_app is None:
        from django.core.asgi import get_asgi_application

        _django_app = get_asgi_application()
    return _django_app


async def app(scope, receive, send):
    """Route API requests to FastAPI and everything else to Django."""
    if scope["type"] == "http":
        path = scope.get("path", "")
        if path in _API_PATHS or path.startswith("/api/"):
            await api_app(scope, receive, send)
            return
        await _get_django_app()(scope, receive, send)
        return

    await api_app(scope, receive, send)


__all__ = ["app"]
