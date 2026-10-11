"""Known-good / known-bad self-tests for the repo-owned eval oracles.

- evals/evals.json: the branch-audit assertions are graded against the recorded
  with_skill reports in audit-workspace/iteration-{1,2} (each verdict assertion
  alone must accept exactly the reports whose verdict its case allows; each detection
  must pass its own scenario's reports and fail the other scenarios'), plus short
  good phrasings and near-miss lines (negated checklist lines, legends) per assertion.
- evals/oracles/fixture_oracle.py: run through the manifest's own script
  assertion, so the command, cwd and {output_dir} substitution are the real ones.

Everything is graded with the pinned harness's grader (skill_benchmark.assertion_result),
not a re-implementation, so run it with the harness installed:

    uvx --from skill-eval-harness==0.6.0 python -m unittest discover -s evals/oracles -v

Known limit: substring/regex graders cannot tell every negation from a finding
("payments is well covered; no tests are skipped"); the judge rubric owns those.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skill_benchmark import assertion_result

ROOT = Path(__file__).resolve().parents[2]
EVALS = ROOT / "evals"
WORKSPACE = ROOT / "audit-workspace"
SCENARIO = {
    1: "dirty-branch-blocking",
    2: "clean-branch-clean",
    3: "mixed-branch-minor",
}
# The verdict each recorded with_skill report gives (read from its "Verdict" line).
REPORT_VERDICT = {
    "dirty-branch-blocking": "blocking",
    "clean-branch-clean": "clean",
    "mixed-branch-minor": "minor",
}
# Case 3 was written expecting Minor, but SKILL.md's calibration lists skipped tests as Blocking.
CASE_ACCEPTS = {1: {"blocking"}, 2: {"clean"}, 3: {"minor", "blocking"}}
VERDICT_PREFIXES = ("verdict-", "no-")

VERDICT_GOOD = {
    "blocking": [
        "The verdict is Blocking.",
        "Overall: **Blocking**",
        "| Verdict | Blocking |",
    ],
    "minor": ["The verdict is Minor.", "## Verdict: **Minor**"],
    "clean": ["The verdict is Clean.", "## Verdict\n\n**Clean** -- no findings."],
}
VERDICT_NEAR_MISS = [
    "Verdict legend: Clean, Minor, Blocking.",
    "| # | Category | Finding | Severity |\n| 1 | Secrets | none | Blocking |",
    "Nothing here is too minor to list.",
    "The skill gives a Clean/Minor/Blocking verdict.",
]

# Short phrasings a correct report might use instead of the recorded wording.
DETECTION_GOOD = {
    "detects-api-key": ["A live secret key (`sk_l…`) is hard-coded in payments.py"],
    "detects-debug-prints": [
        "Leftover `print()` calls in process_payment",
        "Debugging print statements left in src/payments.py",
    ],
    "detects-missing-tests": [
        "Missing tests for the payments module",
        "There are no unit tests for the payment code",
        "`payments.py` lacks tests",
    ],
    "detects-unrelated-changes": [
        "| 4 | `README.md` | Unrelated wording change outside the branch's purpose | Minor |",
        "Unintended changes: the README edit is out of scope for a payments branch.",
        "README edits don't belong in this branch",
    ],
    "detects-todo-comments": [
        "`# TODO add eviction` left in cache.py",
        "Leftover TODO and FIXME markers",
        "Two TODO/FIXME comments were added",
    ],
    "detects-skipped-test": [
        "`test_expiry` is skipped with `@unittest.skip`",
        "A test is marked skip",
    ],
    "detects-fixup-commit": [
        "A fixup commit should be squashed before push",
        "Commit `a1b2c3 fixup: typo` should be squashed",
    ],
}
# Checklist lines a clean report prints, and look-alikes: none of them is a finding.
DETECTION_NEAR_MISS = {
    "detects-api-key": [
        "Secrets and credentials: no API keys, tokens or secret keys found."
    ],
    "detects-debug-prints": [
        "Debug artifacts: no `console.log`, `print()`, `debugger` found."
    ],
    "detects-missing-tests": [
        "`cache_keys()` has no test coverage.",
        "New code in validators.py has dedicated tests.",
    ],
    "detects-unrelated-changes": [
        "The README references `pip install -r requirements.txt` but the file is missing.",
        "## 1. Unintended changes\n\nNone found.",
    ],
    "detects-todo-comments": [
        "Debug artifacts: no `TODO`/`FIXME`/`HACK`/`XXX` markers found in the diff."
    ],
    "detects-skipped-test": [
        "No skipped or disabled tests.",
        "Tests use `pytest.mark.parametrize`.",
    ],
    "detects-fixup-commit": ["Commit hygiene: no fixup or squash-candidate commits."],
}


def grade(assertion: dict, text: str) -> dict:
    return assertion_result(assertion, text, Path("output.md"))


def recorded(scenario: str) -> list[tuple[str, str]]:
    paths = sorted(
        WORKSPACE.glob(f"iteration-*/{scenario}/with_skill/outputs/audit_report.md")
    )
    return [
        (p.relative_to(ROOT).as_posix(), p.read_text(encoding="utf-8")) for p in paths
    ]


class BranchAuditOracles(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        evals = json.loads((EVALS / "evals.json").read_text(encoding="utf-8"))["evals"]
        cls.cases = {e["id"]: e["assertions"] for e in evals}
        cls.reports = {s: recorded(s) for s in SCENARIO.values()}

    def verdicts(self, cid: int) -> list[dict]:
        found = [a for a in self.cases[cid] if a["name"].startswith(VERDICT_PREFIXES)]
        self.assertTrue(found, cid)
        return found

    def detections(self) -> list[tuple[int, dict]]:
        found = [
            (cid, a)
            for cid, assertions in self.cases.items()
            for a in assertions
            if not a["name"].startswith(VERDICT_PREFIXES)
        ]
        self.assertEqual({a["name"] for _, a in found}, set(DETECTION_GOOD))
        return found

    def test_cases_and_samples_are_present(self) -> None:
        self.assertEqual(set(self.cases), set(SCENARIO))
        for scenario, reports in self.reports.items():
            self.assertGreaterEqual(len(reports), 2, scenario)

    def test_every_assertion_is_graded_by_the_harness(self) -> None:
        # An assertion type the harness does not know is reported as deferred and fails every output.
        for cid, assertions in self.cases.items():
            for a in assertions:
                with self.subTest(case=cid, assertion=a["name"]):
                    self.assertNotEqual(
                        grade(a, "")["evidence"], "qualitative/deferred"
                    )

    def test_each_verdict_assertion_accepts_exactly_the_allowed_reports(self) -> None:
        # Each assertion on its own: the harness scores them one by one, so a loose
        # verdict-is-* inflates the pass rate even when its no-* partner rejects the report.
        for cid in self.cases:
            for a in self.verdicts(cid):
                for scenario, reports in self.reports.items():
                    for path, text in reports:
                        with self.subTest(case=cid, assertion=a["name"], report=path):
                            expected = REPORT_VERDICT[scenario] in CASE_ACCEPTS[cid]
                            self.assertEqual(grade(a, text)["passed"], expected)
                for verdict, texts in VERDICT_GOOD.items():
                    for text in texts:
                        with self.subTest(case=cid, assertion=a["name"], text=text):
                            expected = verdict in CASE_ACCEPTS[cid]
                            self.assertEqual(grade(a, text)["passed"], expected)

    def test_verdict_near_misses_are_not_verdicts(self) -> None:
        for cid in self.cases:
            positive = [
                a for a in self.verdicts(cid) if a["name"].startswith("verdict-")
            ]
            for a in positive:
                for text in VERDICT_NEAR_MISS:
                    with self.subTest(case=cid, assertion=a["name"], text=text):
                        self.assertFalse(grade(a, text)["passed"])

    def test_detections_pass_own_report_and_good_phrasings(self) -> None:
        for cid, a in self.detections():
            samples = list(self.reports[SCENARIO[cid]])
            # No recorded report flags the README change as unrelated (iteration-1 says
            # "Unintended changes: No findings"), so that assertion relies on the phrasings.
            if a["name"] == "detects-unrelated-changes":
                samples = []
            samples += [("good", t) for t in DETECTION_GOOD[a["name"]]]
            for path, text in samples:
                with self.subTest(
                    case=cid, assertion=a["name"], sample=path, text=text[:60]
                ):
                    self.assertTrue(grade(a, text)["passed"])

    def test_detections_fail_on_other_reports_and_near_misses(self) -> None:
        # The clean report's checklist names every category ("no API keys", "no TODO/FIXME
        # markers", "no fixup commits"), so vocabulary-only assertions pass on it.
        for cid, a in self.detections():
            samples = [
                (path, text)
                for scenario, reports in self.reports.items()
                if scenario != SCENARIO[cid]
                for path, text in reports
            ]
            samples += [("near-miss", t) for t in DETECTION_NEAR_MISS[a["name"]]]
            for path, text in samples:
                with self.subTest(
                    case=cid, assertion=a["name"], sample=path, text=text[:60]
                ):
                    self.assertFalse(grade(a, text)["passed"])


AUTH_FINDING = "`server.ts`: `/admin/export` is mounted before `requireAuth`, so it is reachable unauthenticated."


class FixtureOracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        manifest = json.loads(
            (EVALS / "shared-benchmark.json").read_text(encoding="utf-8")
        )
        (case,) = [
            c for c in manifest["cases"] if c["id"] == "round3-fixture-auth-order"
        ]
        (cls.script,) = [a for a in case["assertions"] if a["type"] == "script"]

    def run_oracle(self, text: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "output.md"
            out.write_text(text, encoding="utf-8")
            return assertion_result(
                self.script,
                text,
                out,
                run_base=Path(tmp),
                allow_scripts=True,
                manifest_dir=EVALS,
            )

    def test_rated_finding_passes(self) -> None:
        for rating in (
            "**Severity:** High",
            "## Verdict: **Blocking**",
            "| 1 | server.ts | auth order | Critical |",
            "This is a high-severity finding.",
            "**Risk:** High",
        ):
            with self.subTest(rating=rating):
                result = self.run_oracle(
                    f"{AUTH_FINDING}\n\n{rating}\n\nFix: move `app.use(requireAuth)` above the route."
                )
                self.assertTrue(result["passed"], result["evidence"])

    def test_wrong_or_missing_rating_fails(self) -> None:
        filler = "The handler streams every customer row as JSON to the caller. " * 2
        bad = {
            "low severity": f"{AUTH_FINDING}\n\n**Severity:** Low",
            "medium severity": f"{AUTH_FINDING}\n\n**Severity:** Medium",
            "low, 'High' in a parenthesis": f"{AUTH_FINDING}\n\n**Severity:** Low (not High)",
            "low, 'High' much later": f"{AUTH_FINDING}\n\n**Severity:** Low. {filler}High-level summary follows.",
            "clean verdict": f"{AUTH_FINDING}\n\n**Severity:** High\n\n## Verdict: Clean",
            "clean verdict in a table": f"{AUTH_FINDING}\n\n**Severity:** High\n\n| Verdict | Clean |",
            "clean verdict as a sentence": f"{AUTH_FINDING}\n\n**Severity:** High\n\nThe verdict is Clean.",
            "unrated, 'high' only inside a word": f"I highlight one issue. {AUTH_FINDING}",
            "unrated, scale named only": f"Severity and verdict follow the skill's scale. {AUTH_FINDING}",
            "rated, route not cited": "**Severity:** High\n\nAn admin route is mounted before requireAuth.",
        }
        for label, text in bad.items():
            with self.subTest(label):
                result = self.run_oracle(text)
                self.assertFalse(result["passed"], result["evidence"])


if __name__ == "__main__":
    unittest.main()
