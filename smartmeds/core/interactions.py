"""
Drug interaction checker module.

This module provides functionality to check potential interactions
between medications. In production, this would interface with a
medical database API (e.g., RxNorm, DrugBank, or OpenFDA).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set

from smartmeds.utils.logger import get_logger

logger = get_logger(__name__)


class InteractionSeverity(str, Enum):
    """Severity levels for drug interactions."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CONTRAINDICATED = "contraindicated"


@dataclass
class DrugInteraction:
    """Represents an interaction between two medications."""

    drug_a: str
    drug_b: str
    severity: InteractionSeverity
    description: str
    recommendation: str

    def __str__(self) -> str:
        return (
            f"⚠️  [{self.severity.value.upper()}] {self.drug_a} + {self.drug_b}\n"
            f"   {self.description}\n"
            f"   Recommendation: {self.recommendation}"
        )


# Sample interaction database (would be replaced with real API in production)
_KNOWN_INTERACTIONS: Dict[frozenset, DrugInteraction] = {
    frozenset({"warfarin", "aspirin"}): DrugInteraction(
        drug_a="Warfarin",
        drug_b="Aspirin",
        severity=InteractionSeverity.HIGH,
        description="Increased risk of bleeding when combined.",
        recommendation="Avoid concurrent use. Consult your doctor.",
    ),
    frozenset({"metformin", "alcohol"}): DrugInteraction(
        drug_a="Metformin",
        drug_b="Alcohol",
        severity=InteractionSeverity.MODERATE,
        description="May increase risk of lactic acidosis.",
        recommendation="Limit or avoid alcohol consumption.",
    ),
    frozenset({"simvastatin", "amiodarone"}): DrugInteraction(
        drug_a="Simvastatin",
        drug_b="Amiodarone",
        severity=InteractionSeverity.HIGH,
        description="Risk of myopathy and rhabdomyolysis.",
        recommendation="Use alternative statin or reduce dose.",
    ),
}


class InteractionChecker:
    """
    Checks for potential drug interactions between medications.

    Example:
        >>> checker = InteractionChecker()
        >>> interactions = checker.check(["warfarin", "aspirin", "metformin"])
        >>> for interaction in interactions:
        ...     print(interaction)
    """

    def __init__(self) -> None:
        self._interactions = _KNOWN_INTERACTIONS.copy()

    def check(self, medication_names: List[str]) -> List[DrugInteraction]:
        """
        Check for interactions among a list of medication names.

        Args:
            medication_names: List of medication names to check.

        Returns:
            List of DrugInteraction objects found.
        """
        found_interactions: List[DrugInteraction] = []
        normalized = [name.lower().strip() for name in medication_names]

        for i, drug_a in enumerate(normalized):
            for drug_b in normalized[i + 1 :]:
                key = frozenset({drug_a, drug_b})
                if key in self._interactions:
                    found_interactions.append(self._interactions[key])
                    logger.warning(
                        "Interaction found: %s + %s [%s]",
                        drug_a,
                        drug_b,
                        self._interactions[key].severity.value,
                    )

        return found_interactions

    def has_high_risk_interaction(self, medication_names: List[str]) -> bool:
        """
        Check if any high-risk or contraindicated interactions exist.

        Args:
            medication_names: List of medication names to check.

        Returns:
            True if high-risk interactions are present.
        """
        interactions = self.check(medication_names)
        return any(
            i.severity in (InteractionSeverity.HIGH, InteractionSeverity.CONTRAINDICATED)
            for i in interactions
        )

    def add_interaction(self, interaction: DrugInteraction) -> None:
        """
        Add a custom interaction to the checker's database.

        Args:
            interaction: The DrugInteraction to add.
        """
        key = frozenset({interaction.drug_a.lower(), interaction.drug_b.lower()})
        self._interactions[key] = interaction
        logger.info("Added interaction: %s + %s", interaction.drug_a, interaction.drug_b)
