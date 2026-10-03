"""Known-good / known-bad self-tests for the repo-owned eval oracles.

- evals/evals.json: the branch-audit assertions are graded against the recorded
  reports in audit-workspace/iteration-{1,2}. A report must pass its own case's
  verdict assertions and fail every other case's; the clean-branch report (which
  states that none of the planted issues exist) must fail every detection assertion.
- evals/oracles/fixture_oracle.py: run through the manifest's own script
  assertion, so the command, cwd and {output_dir} substitution are the real ones.

Everything is graded with the pinned harness's grader (skill_benchmark.assertion_result),
not a re-implementation, so run it with the harness installed:

    uvx --from skill-eval-harness==0.6.0 python -m unittest discover -s evals/oracles -v
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
VERDICT_PREFIXES = ("verdict-", "no-")


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

    def test_verdict_passes_own_report_and_fails_every_other(self) -> None:
        for cid, assertions in self.cases.items():
            verdict = [a for a in assertions if a["name"].startswith(VERDICT_PREFIXES)]
            self.assertTrue(verdict, cid)
            for scenario, reports in self.reports.items():
                for path, text in reports:
                    with self.subTest(case=cid, report=path):
                        passed = all(grade(a, text)["passed"] for a in verdict)
                        self.assertEqual(passed, scenario == SCENARIO[cid])

    def test_detections_pass_own_report(self) -> None:
        for cid, assertions in self.cases.items():
            for a in assertions:
                # No recorded report flags the README change as unrelated; see the synthetic samples below.
                if (
                    a["name"].startswith(VERDICT_PREFIXES)
                    or a["name"] == "detects-unrelated-changes"
                ):
                    continue
                for path, text in self.reports[SCENARIO[cid]]:
                    with self.subTest(case=cid, assertion=a["name"], report=path):
                        self.assertTrue(
                            grade(a, text)["passed"], grade(a, text)["evidence"]
                        )

    def test_detections_fail_on_clean_report(self) -> None:
        # The clean report's checklist names every category ("no API keys", "no TODO/FIXME markers",
        # "no fixup commits"), so vocabulary-only assertions pass on it.
        for cid in (1, 3):
            for a in self.cases[cid]:
                if a["name"].startswith(VERDICT_PREFIXES):
                    continue
                for path, text in self.reports[SCENARIO[2]]:
                    with self.subTest(case=cid, assertion=a["name"], report=path):
                        self.assertFalse(grade(a, text)["passed"])

    def test_unrelated_change_needs_a_judgement_not_a_mention(self) -> None:
        (a,) = [a for a in self.cases[1] if a["name"] == "detects-unrelated-changes"]
        good = [
            "| 4 | `README.md` | Unrelated wording change outside the branch's purpose | Minor |",
            "Unintended changes: the README edit is out of scope for a payments branch.",
        ]
        bad = [
            "The README references `pip install -r requirements.txt` but the file is missing."
        ]
        for text in good:
            with self.subTest(expect="pass", text=text):
                self.assertTrue(grade(a, text)["passed"])
        for text in bad:
            with self.subTest(expect="fail", text=text):
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
        ):
            with self.subTest(rating=rating):
                result = self.run_oracle(
                    f"{AUTH_FINDING}\n\n{rating}\n\nFix: move `app.use(requireAuth)` above the route."
                )
                self.assertTrue(result["passed"], result["evidence"])

    def test_wrong_or_missing_rating_fails(self) -> None:
        bad = {
            "low severity": f"{AUTH_FINDING}\n\n**Severity:** Low",
            "clean verdict": f"{AUTH_FINDING}\n\n**Severity:** High\n\n## Verdict: Clean",
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
