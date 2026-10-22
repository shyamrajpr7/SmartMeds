"""
SmartMeds — Intelligent Medication Management System
"""

__version__ = "0.1.0"
__author__ = "shyamrajpr7"
__license__ = "MIT"

from smartmeds.core.medication import Medication
from smartmeds.core.scheduler import MedicationScheduler

__all__ = ["Medication", "MedicationScheduler", "__version__"]
