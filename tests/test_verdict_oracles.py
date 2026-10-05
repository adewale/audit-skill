"""Self-tests for the severity/verdict oracles in evals/shared-benchmark.json.

Each audit-output case that grades a verdict must accept an output carrying the
case's expected verdict and reject outputs carrying a wrong one. The assertions
are graded with the pinned harness's own grader (skill_benchmark.assertion_result),
not a re-implementation, so run this file with the harness installed:

    uvx --from skill-eval-harness==0.6.0 python -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from skill_benchmark import assertion_result

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evals" / "shared-benchmark.json"
VERDICT_ASSERTIONS = {"has-severity-verdict", "no-wrong-verdict", "no-clean-verdict"}

BRANCH_BLOCKING = "## Verdict: **Blocking**\n\nFix before pushing: see the findings table."
BRANCH_MINOR = "## Verdict\n\n**Minor** -- low-risk hygiene issues, push at your discretion."
BRANCH_CLEAN = "## Verdict\n\n**Clean** -- no findings, safe to push."
SEV_HIGH = "### Finding 1\n\n**Severity:** High\n\nEvidence: src/app.py:12."
SEV_CRITICAL_TABLE = "| # | File | Issue | Severity |\n|---|---|---|---|\n| 1 | main.go | shared map written without a lock | Critical |"
SEV_MEDIUM = "### Finding 1\n\n**Severity:** Medium\n\nEvidence: src/app.py:12."
SEV_LOW = "### Finding 1\n\n**Severity:** Low\n\nEvidence: src/app.py:12."
UNRATED = "The code has an issue in src/app.py:12; consider fixing it."

# expected class -> (outputs that must pass, outputs that must fail)
CLASSES = {
    "branch-blocking": (
        [BRANCH_BLOCKING, "**Verdict: Blocking** -- leaked credential must be removed."],
        [BRANCH_CLEAN, BRANCH_MINOR, "**Verdict: Minor** (not Blocking) -- push at your discretion.", UNRATED],
    ),
    "branch-minor": (
        [BRANCH_MINOR, "## Verdict: Minor"],
        [BRANCH_CLEAN, BRANCH_BLOCKING, UNRATED],
    ),
    "deep-blocking": (
        [SEV_HIGH, SEV_CRITICAL_TABLE, BRANCH_BLOCKING],
        [SEV_LOW, SEV_MEDIUM, BRANCH_CLEAN, UNRATED],
    ),
    "deep-minor": (
        [SEV_LOW, SEV_MEDIUM, BRANCH_MINOR],
        [SEV_HIGH, SEV_CRITICAL_TABLE, BRANCH_CLEAN, UNRATED],
    ),
    "has-finding": (
        [SEV_LOW, SEV_HIGH, SEV_CRITICAL_TABLE, BRANCH_MINOR],
        [BRANCH_CLEAN, UNRATED],
    ),
}

EXPECTED_CLASS = {
    "pos-leaked-redacted-secret": "branch-blocking",
    "pos-skipped-test": "branch-blocking",
    "pos-unrelated-file-change": "branch-minor",
    "pos-unregistered-route": "deep-blocking",
    "pos-go-shared-map-race": "deep-blocking",
    "pos-python-unclosed-resource": "deep-blocking",
    "pos-audit-evidence-not-just-label": "deep-blocking",
    "pos-stale-readme-cli-flag": "deep-minor",
    "pos-n-plus-one-loop": "has-finding",
    "pos-weak-test-suite": "has-finding",
    "pos-ui-alignment-proximity": "has-finding",
}

# Negative-control (false-positive restraint) cases: a restrained answer must pass
# the objective assertions and a confident false positive must fail them. The bad
# samples are the false-positive answers PR #11 found passing the old oracles.
NEG_SAMPLES = {
    "neg-fake-secret-fixture": (
        ["## Verdict: **Clean**\n\n`sk_test_fake_123` is a test fixture, not a real credential, so there is no finding."],
        ["## Verdict: **Blocking**\n\nLeaked credential sk_test_fake_123 in tests/fixtures.py -- do not commit secrets."],
    ),
    "neg-lockfile-paired": (
        ["## Verdict: **Clean**\n\nThe lockfile change is paired with the package.json upgrade, as expected."],
        ["## Verdict: **Minor**\n\nUnexpected lockfile churn in package-lock.json. Expected only package.json."],
    ),
    "neg-no-design-philosophy": (
        ["This repo has no stated design philosophy, so I cannot assess conformance. Which principles should I audit against?"],
        ["### Finding 1 (High): violates SOLID.\n\nAsk the team to refactor the service layer."],
    ),
    "neg-toy-security-clean": (
        ["## Verdict: **Clean**\n\nNo input, auth, network or secrets: no findings."],
        ["## Verdict: **Blocking**\n\n**Severity:** High -- missing CSRF protection. Clean up the handler."],
    ),
}


def objective_assertions(case: dict) -> list[dict]:
    return [a for a in case.get("assertions", []) if a.get("type") != "judge"]


def verdict_assertions(case: dict) -> list[dict]:
    return [a for a in case.get("assertions", []) if a.get("name") in VERDICT_ASSERTIONS]


def passes(assertions: list[dict], text: str) -> bool:
    return all(assertion_result(a, text, ROOT / "output.md")["passed"] for a in assertions)


class VerdictOracleSelfTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cases = json.loads(MANIFEST.read_text(encoding="utf-8"))["cases"]
        cls.cases = {c["id"]: c for c in cases}

    def test_every_verdict_graded_case_has_an_expected_class(self) -> None:
        graded = {cid for cid, c in self.cases.items() if verdict_assertions(c)}
        self.assertEqual(graded, set(EXPECTED_CLASS))

    def test_expected_verdict_passes_and_wrong_verdict_fails(self) -> None:
        for cid, klass in EXPECTED_CLASS.items():
            good, bad = CLASSES[klass]
            assertions = verdict_assertions(self.cases[cid])
            for text in good:
                with self.subTest(case=cid, expect="pass", output=text[:60]):
                    self.assertTrue(passes(assertions, text))
            for text in bad:
                with self.subTest(case=cid, expect="fail", output=text[:60]):
                    self.assertFalse(passes(assertions, text))

    def test_negative_controls_reject_false_positive_answers(self) -> None:
        for cid, (good, bad) in NEG_SAMPLES.items():
            assertions = objective_assertions(self.cases[cid])
            self.assertTrue(assertions, cid)
            for text in good:
                with self.subTest(case=cid, expect="pass", output=text[:60]):
                    self.assertTrue(passes(assertions, text))
            for text in bad:
                with self.subTest(case=cid, expect="fail", output=text[:60]):
                    self.assertFalse(passes(assertions, text))


if __name__ == "__main__":
    unittest.main()
