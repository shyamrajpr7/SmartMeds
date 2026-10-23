"""
Vercel entry point for the SmartMeds API.

Vercel looks for a FastAPI instance named ``app`` at the project root (or at
the module configured with ``tool.vercel.entrypoint`` in ``pyproject.toml``)
and routes every request to it.
"""

import os
import sys

# Make the project root importable so `smartmeds` resolves on the server.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smartmeds.api.app import app  # noqa: E402

__all__ = ["app"]
