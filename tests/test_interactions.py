"""Tests for the InteractionChecker."""

from __future__ import annotations

import pytest

from smartmeds.core.interactions import (
    DrugInteraction,
    InteractionChecker,
    InteractionSeverity,
)


@pytest.fixture
def checker() -> InteractionChecker:
    return InteractionChecker()


class TestInteractionChecker:
    def test_detects_known_interaction(self, checker: InteractionChecker) -> None:
        interactions = checker.check(["warfarin", "aspirin"])
        assert len(interactions) == 1
        assert interactions[0].severity == InteractionSeverity.HIGH

    def test_no_interaction_for_safe_combo(self, checker: InteractionChecker) -> None:
        interactions = checker.check(["vitamin_c", "zinc"])
        assert len(interactions) == 0

    def test_case_insensitive_matching(self, checker: InteractionChecker) -> None:
        interactions = checker.check(["Warfarin", "Aspirin"])
        assert len(interactions) == 1

    def test_multiple_interactions(self, checker: InteractionChecker) -> None:
        interactions = checker.check(["warfarin", "aspirin", "metformin", "alcohol"])
        assert len(interactions) >= 2

    def test_single_medication_no_interaction(self, checker: InteractionChecker) -> None:
        interactions = checker.check(["warfarin"])
        assert len(interactions) == 0

    def test_empty_list(self, checker: InteractionChecker) -> None:
        interactions = checker.check([])
        assert len(interactions) == 0

    def test_has_high_risk_interaction(self, checker: InteractionChecker) -> None:
        result = checker.has_high_risk_interaction(["warfarin", "aspirin"])
        assert result is True

    def test_no_high_risk_for_moderate(self, checker: InteractionChecker) -> None:
        result = checker.has_high_risk_interaction(["metformin", "alcohol"])
        assert result is False

    def test_add_custom_interaction(self, checker: InteractionChecker) -> None:
        custom = DrugInteraction(
            drug_a="DrugX",
            drug_b="DrugY",
            severity=InteractionSeverity.LOW,
            description="Test interaction.",
            recommendation="Test recommendation.",
        )
        checker.add_interaction(custom)
        interactions = checker.check(["drugx", "drugy"])
        assert len(interactions) == 1
