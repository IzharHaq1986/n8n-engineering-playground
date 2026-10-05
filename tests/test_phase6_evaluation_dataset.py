"""Validate the Phase 6 evaluation-dataset contract."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import unittest
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    REPOSITORY_ROOT
    / "tests/fixtures/"
    "phase6-readonly-github-advisor-evaluations.json"
)

EXPECTED_CATEGORY_COUNTS = {
    "dependency_failure": 3,
    "grounded": 4,
    "insufficient_evidence": 4,
    "invalid_output": 3,
    "policy_denied": 4,
    "security_resistant": 6,
}

ZERO_AUTHORITY_FIELDS = (
    "github_write_count",
    "shell_execution_count",
    "database_write_count",
    "external_message_count",
    "autonomous_action_count",
    "secret_occurrence_count",
)


class Phase6EvaluationDatasetTests(unittest.TestCase):
    """Verify Phase 6 evaluation fixtures and safety invariants."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.raw_text = FIXTURE_PATH.read_text(encoding="utf-8")
        cls.dataset = json.loads(cls.raw_text)
        cls.fixtures: list[dict[str, Any]] = (
            cls.dataset["fixtures"]
        )

    def test_fixture_inventory_is_complete_and_unique(self) -> None:
        self.assertEqual("1.0", self.dataset["schema_version"])
        self.assertEqual(
            "Phase 6 - Read-Only GitHub Issue Reliability Advisor",
            self.dataset["workflow_name"],
        )
        self.assertGreaterEqual(
            len(self.fixtures),
            self.dataset["minimum_fixture_count"],
        )
        self.assertEqual(24, len(self.fixtures))

        fixture_ids = [
            fixture["fixture_id"]
            for fixture in self.fixtures
        ]

        self.assertEqual(
            len(fixture_ids),
            len(set(fixture_ids)),
        )
        self.assertEqual(
            EXPECTED_CATEGORY_COUNTS,
            dict(
                Counter(
                    fixture["category"]
                    for fixture in self.fixtures
                )
            ),
        )

    def test_every_fixture_preserves_zero_authority(
        self,
    ) -> None:
        for fixture in self.fixtures:
            with self.subTest(
                fixture_id=fixture["fixture_id"]
            ):
                expected = fixture["expected"]

                self.assertIs(
                    True,
                    expected["requires_human_review"],
                )
                self.assertIs(
                    False,
                    expected["action_authorized"],
                )
                self.assertEqual(
                    "not_executed",
                    expected["execution_status"],
                )

                for field_name in ZERO_AUTHORITY_FIELDS:
                    self.assertEqual(
                        0,
                        expected[field_name],
                        field_name,
                    )

    def test_rejection_categories_fail_closed(self) -> None:
        rejection_categories = {
            "dependency_failure",
            "invalid_output",
            "policy_denied",
        }

        for fixture in self.fixtures:
            if fixture["category"] not in rejection_categories:
                continue

            with self.subTest(
                fixture_id=fixture["fixture_id"]
            ):
                expected = fixture["expected"]

                self.assertEqual(
                    "rejected",
                    expected["validation_status"],
                )
                self.assertEqual(
                    "insufficient_evidence",
                    expected["recommendation_status"],
                )
                self.assertEqual(
                    [],
                    expected["evidence_citations"],
                )

    def test_policy_denials_prevent_external_requests(
        self,
    ) -> None:
        policy_fixtures = [
            fixture
            for fixture in self.fixtures
            if fixture["category"] == "policy_denied"
        ]

        self.assertEqual(4, len(policy_fixtures))

        for fixture in policy_fixtures:
            with self.subTest(
                fixture_id=fixture["fixture_id"]
            ):
                expected = fixture["expected"]

                self.assertEqual(
                    0,
                    expected["github_request_count"],
                )
                self.assertEqual(
                    0,
                    expected["openai_request_count"],
                )

    def test_citation_contract_matches_recommendation_state(
        self,
    ) -> None:
        for fixture in self.fixtures:
            with self.subTest(
                fixture_id=fixture["fixture_id"]
            ):
                expected = fixture["expected"]
                citations = expected["evidence_citations"]

                if (
                    expected["validation_status"] == "accepted"
                    and expected["recommendation_status"]
                    == "grounded"
                ):
                    self.assertEqual(
                        ["GITHUB-ISSUE-88"],
                        citations,
                    )
                else:
                    self.assertEqual([], citations)

    def test_retries_are_bounded_and_secrets_are_absent(
        self,
    ) -> None:
        for fixture in self.fixtures:
            with self.subTest(
                fixture_id=fixture["fixture_id"]
            ):
                expected = fixture["expected"]
                github_requests = expected[
                    "github_request_count"
                ]
                openai_requests = expected[
                    "openai_request_count"
                ]

                self.assertLessEqual(github_requests, 2)
                self.assertLessEqual(openai_requests, 2)

                if github_requests > 1 or openai_requests > 1:
                    self.assertEqual(
                        "dependency_failure",
                        fixture["category"],
                    )

        prohibited_patterns = (
            r"sk-[A-Za-z0-9_-]{20,}",
            r"authorization\\s*:\\s*bearer",
            r"BEGIN OPENSSH PRIVATE KEY",
        )

        for pattern in prohibited_patterns:
            self.assertIsNone(
                re.search(
                    pattern,
                    self.raw_text,
                    flags=re.IGNORECASE,
                ),
                pattern,
            )


if __name__ == "__main__":
    unittest.main()
