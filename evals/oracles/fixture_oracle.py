#!/usr/bin/env python3
"""Fixture-backed output oracle for shared Skill Eval Harness script assertions."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CHECKS = {
  "round3-fixture-auth-order": {
    "all": [
      "server.ts",
      "/admin/export"
    ],
    "any": [
      [
        "before requireAuth",
        "before auth",
        "unauthenticated",
        "mounted before"
      ]
    ],
    # An unauthenticated admin export is a reachable security hole: the rating must be
    # Blocking/Critical/High (directly after a verdict/severity/risk label, as a
    # "high-severity" phrase, or as a table cell), and the overall verdict must not be Clean.
    "regex": [
      (
        r"\b(?:verdict|severity|risk|impact)\b(?:\W+is)?\W{0,12}(?:blocking|critical|high)\b"
        r"|\b(?:blocking|critical|high)[- ]severity\b"
        r"|\|\s*\**(?:blocking|critical|high)\**\s*\|"
      )
    ],
    "forbid": [
      r"\bverdict\b(?:\W+is)?\W{0,12}clean\b"
    ]
  }
}

def contains(text: str, needle: str) -> bool:
    return needle.casefold() in text.casefold()

def main() -> int:
    if len(sys.argv) != 3:
        print("usage: fixture_oracle.py OUTPUT_DIR CASE_ID", file=sys.stderr)
        return 2
    output_dir = Path(sys.argv[1])
    case_id = sys.argv[2]
    spec = CHECKS.get(case_id)
    if not spec:
        print(f"unknown case id: {case_id}", file=sys.stderr)
        return 2
    out = output_dir / "output.md"
    if not out.exists():
        print(f"missing output: {out}", file=sys.stderr)
        return 2
    text = out.read_text(encoding="utf-8", errors="replace")
    failures: list[str] = []
    checks = 0
    for needle in spec.get("all", []):
        checks += 1
        if not contains(text, needle):
            failures.append(f"missing required text: {needle!r}")
    for group in spec.get("any", []):
        checks += 1
        if not any(contains(text, needle) for needle in group):
            failures.append("missing one of: " + ", ".join(repr(x) for x in group))
    for pattern in spec.get("regex", []):
        checks += 1
        if not re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL):
            failures.append(f"missing regex: {pattern}")
    for pattern in spec.get("forbid", []):
        checks += 1
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL):
            failures.append(f"forbidden regex present: {pattern}")
    score = max(checks - len(failures), 0)
    print(json.dumps({"score": score, "max_score": checks or 1, "case_id": case_id}))
    if failures:
        print("FAIL fixture oracle")
        for failure in failures:
            print("- " + failure)
        return 1
    print("OK fixture oracle: " + case_id)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
